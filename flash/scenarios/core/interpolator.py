"""scenarios/interpolator.py — 场景共享的时空网格构建与插值

本模块提供 `SimulationScenario.build_grid` / `SimulationScenario.interpolate`
两个回调所需的通用实现，供所有场景复用：

  build_variable_grid(...)      → (t_grid, x_grid)
  interpolate_flash_to_grid(...) → {var_name: ndarray, shape (Nt, Nx)}

设计说明
────────
FLASH 的 AMR 输出在时间上是不均匀的（步长由 CFL 决定），在空间上是块结构
自适应网格。下游分析（绘图、对比、存档 result.h5）需要规整的
(时间 × 空间) 二维数组，因此需要把一组 checkpoint 重采样到统一网格上。

实现完全建立在本包已有且经过测试的设施之上，不引入新的数值方法：
  - `output_processors.parallel._load_single_chk`：纯 h5py 提取叶节点 1D 剖面
  - `output_processors.parallel.parallel_interpolate`：分块并行的双线性重采样

历史说明
────────
早期版本中这两个函数位于 `thin_layer_sandwich` 私有场景内的 `interpolator`
顶层模块中，该模块不随包分发，导致公开场景 `ch_center` 在克隆/发布环境中
无法导入。现将其提升为 `flash.scenarios` 的公开成员，任何场景均可依赖。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

__all__ = ["build_variable_grid", "interpolate_flash_to_grid", "load_flash_slices"]


# ── 网格构建 ────────────────────────────────────────────

def build_variable_grid(
    t_min: float = 0.0,
    t_max: float = 1.0e-9,
    t_step: float = 10e-12,
    xmin: float = -0.01,
    xmax: float = 0.01,
    nx: int = 2000,
) -> Tuple[np.ndarray, np.ndarray]:
    """构建输出用的 (时间, 空间) 目标网格。

    参数:
        t_min:  起始时刻 [s]
        t_max:  终止时刻 [s]（含端点）
        t_step: 时间步长 [s]
        xmin:   空间下界 [cm]
        xmax:   空间上界 [cm]
        nx:     空间采样点数

    返回:
        (t_grid, x_grid)，均为 float64 一维数组。
        t_grid 含端点，长度 = floor((t_max - t_min) / t_step) + 1。

    说明:
        时间轴按固定步长采样，使不同算例可直接逐点对比；
        空间轴为均匀网格，分辨率由 `nx` 控制（默认 2000 点，
        足以覆盖 lrefine_max=5~8 的等效最细网格）。
    """
    if t_step <= 0:
        raise ValueError(f"t_step 必须为正数, 实际 {t_step}")
    if t_max < t_min:
        raise ValueError(f"t_max ({t_max}) 不能小于 t_min ({t_min})")
    if xmax <= xmin:
        raise ValueError(f"xmax ({xmax}) 必须大于 xmin ({xmin})")
    if nx < 2:
        raise ValueError(f"nx 必须 >= 2, 实际 {nx}")

    n_t = int(np.floor((t_max - t_min) / t_step + 1e-9)) + 1
    t_grid = t_min + t_step * np.arange(n_t, dtype=np.float64)
    x_grid = np.linspace(float(xmin), float(xmax), int(nx), dtype=np.float64)
    return t_grid, x_grid


# ── FLASH 文件加载 ──────────────────────────────────────

def load_flash_slices(
    flash_files: Iterable[Union[str, Path]],
    var_names: Sequence[str],
    verbose: bool = False,
) -> List[Dict]:
    """把一组 FLASH checkpoint 读成按时间排序的剖面切片。

    参数:
        flash_files: checkpoint 路径序列
        var_names:   需要提取的变量名
        verbose:     是否打印跳过的文件

    返回:
        [{"time": float, "x": ndarray, var: ndarray, ...}, ...]，按 time 升序。
        无法读取的文件会被跳过（不抛异常），以便个别损坏文件不影响整批处理。
    """
    from ..output_processors.parallel import _load_single_chk

    slices: List[Dict] = []
    for f in flash_files:
        sl = _load_single_chk(str(f), var_names=list(var_names))
        if sl is None:
            if verbose:
                print(f"  [interpolator] 跳过无法读取的文件: {f}")
            continue
        x = sl.get("x")
        if x is None or np.asarray(x).size == 0:
            if verbose:
                print(f"  [interpolator] 跳过非 1D 或空网格文件: {f}")
            continue
        slices.append(sl)

    slices.sort(key=lambda s: s["time"])
    return slices


# ── 时空插值 ────────────────────────────────────────────

def interpolate_flash_to_grid(
    flash_files: Iterable[Union[str, Path]],
    t_grid: np.ndarray,
    x_grid: np.ndarray,
    var_names: Sequence[str],
    max_workers: Optional[int] = None,
    verbose: bool = False,
) -> Dict[str, np.ndarray]:
    """把一组 FLASH checkpoint 重采样到给定的 (t_grid, x_grid) 上。

    参数:
        flash_files: checkpoint 路径序列（顺序无关，内部按时间排序）
        t_grid:      目标时间网格 [Nt]
        x_grid:      目标空间网格 [Nx]
        var_names:   需要输出的变量名
        max_workers: 并行进程数（None = 自动）
        verbose:     是否打印进度

    返回:
        {var_name: ndarray, shape (Nt, Nx)}。
        当没有任何可用的输入文件时，返回全零数组（形状仍然正确），
        以保证下游保存与绘图逻辑不会因空输入而崩溃。
    """
    from ..output_processors.parallel import parallel_interpolate

    t_grid = np.asarray(t_grid, dtype=np.float64)
    x_grid = np.asarray(x_grid, dtype=np.float64)
    var_names = list(var_names)

    slices = load_flash_slices(flash_files, var_names, verbose=verbose)
    if not slices:
        return {
            vn: np.zeros((t_grid.size, x_grid.size), dtype=np.float32)
            for vn in var_names
        }

    if verbose:
        print(
            f"  [interpolator] {len(slices)} 个时间片 "
            f"→ ({t_grid.size} × {x_grid.size}) 网格"
        )

    return parallel_interpolate(
        flash_slices=slices,
        t_grid=t_grid,
        x_grid=x_grid,
        var_names=var_names,
        max_workers=max_workers,
        verbose=verbose,
    )
