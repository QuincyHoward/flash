"""时空插值引擎 — 将 FLASH AMR 块数据插值到变分辨率固定时空网格

使用 output_processors 的 FlashHDF5File 读取 FLASH HDF5，
通过 slice_1d() 获取排序后的块展平数据，再用 numpy.interp 插值到目标网格。

数据流:
  FLASH HDF5 → FlashHDF5File → slice_1d("dens") → (all_x, all_y)
                                                           ↓
  t_grid[], x_grid[] ← build_variable_grid()   →  np.interp → 时间插值 → result.h5

支持的输出字段 (默认从 chk 文件提取):
  - dens, tele, tion, trad, pres, velx  (标量物理量)
  - ye, sumy                            (电子/离子丰度)
  - poly, targ                          (物种质量分数)
  - pele, pion, prad                    (e⁻/i/辐射压力 — 不在 FLASH 中存储为 unk,
                                          需 EOS 计算; 此处设为占位, 从 chk 读取时不可用)
"""

from __future__ import annotations

import os, sys
import numpy as np
import h5py
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# FlashHDF5File: 读取 FLASH HDF5 (chk/plt) 的核心类
try:
    from output_processors.hdf5processor import FlashHDF5File
except ImportError:
    # 包内相对路径兜底
    from flash.output_processors.hdf5processor import FlashHDF5File

# Bootstrap: workspace root = sandwich/scenarios/flash/<root> (fixed depth, robust)
_ROOT = Path(__file__).resolve().parents[4]
_PARENT = _ROOT.parent
for _p in [str(_PARENT), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ============================================================
# 默认输出字段 (可从 chk 文件提取)
# ============================================================
# 注意: pele, pion, prad 不是 FLASH 标准 unk 变量，
# 它们由 EOS 计算得出。如需这些量，需在 flash_hdf5.py 中
# 注册后处理计算函数，或由上层脚本在读取后计算。
DEFAULT_OUTPUT_FIELDS = [
    "dens", "poly", "targ", "ye", "sumy",
    "tele", "tion", "trad",
    "pele", "pion", "prad", "pres", "velx",
]


# ============================================================
# 变分辨率空间网格
# ============================================================

def build_variable_grid(
    t_min: float = 0.0,
    t_max: float = 3.0e-9,
    t_step: float = 10e-12,
    x_bounds_um: Tuple[float, float] = (-450, 450),
) -> Tuple[np.ndarray, np.ndarray]:
    """生成变分辨率时空网格

    分段线性网格，核心区密集、外围稀疏，大幅减少数据量:
      ±1 um:    步长 0.01 um (核心, 最高精度)
      ±1~10 um: 步长 0.1 um
      ±10~50 um: 步长 1 um
      ±50~450 um: 步长 5 um

    Args:
        t_min, t_max, t_step: 均匀时间网格 (s)
        x_bounds_um: (xmin, xmax) in um

    Returns:
        (t_grid, x_grid): time [Nt] in s, space [Nx] in cm
    """
    # 时间均匀网格
    t_grid = np.arange(t_min, t_max + t_step * 0.5, t_step)

    # 变分辨率空间网格 (um → cm 转换: 1 um = 1e-4 cm)
    xmin_um, xmax_um = x_bounds_um
    segments = [
        (xmin_um, -50.0, 5.0, True),        # 左外区 (-450~-50 um), include_start
        (-50.0, -10.0, 1.0, False),          # 左中间区 (-50~-10 um)
        (-10.0, -1.0, 0.1, False),           # 左内区 (-10~-1 um)
        (-1.0, 1.0, 0.01, False),            # 核心区 (±1 um, 最高精度)
        (1.0, 10.0, 0.1, False),             # 右内区 (1~10 um)
        (10.0, 50.0, 1.0, False),            # 右中间区 (10~50 um)
        (50.0, xmax_um, 5.0, False),         # 右外区 (50~450 um)
    ]

    x_parts = []
    for lo, hi, step, include_first in segments:
        lo = max(lo, xmin_um)
        hi = min(hi, xmax_um)
        if lo >= hi:
            continue
        n_pts = int(round((hi - lo) / step)) + 1
        arr = np.linspace(lo, hi, n_pts)
        if not include_first:
            arr = arr[1:]  # 跳过起点避免与上一段终点重复
        x_parts.append(arr)

    x_um = np.concatenate(x_parts) if x_parts else np.array([0.0])
    # 转换为 cm
    x_grid = x_um * 1e-4

    return t_grid, x_grid


# ============================================================
# FLASH HDF5 读取 (使用 output_processors)
# ============================================================

def read_flash_slice(filepath: str, var_names: List[str]) -> Dict:
    """读取单个 FLASH HDF5, 返回按 x 排序的展平数据

    使用 FlashHDF5File 打开文件, 用 slice_1d() 获取排序后的
    (x, value) 数据, 适合直接输入 numpy.interp.

    Args:
        filepath: FLASH HDF5 文件路径
        var_names: 需要读取的变量名列表 (e.g. dens, tele, poly)

    Returns:
        {time, x, dens, tele, ye, sumy, poly, targ}
        - time: float, 仿真时间 (s)
        - x: ndarray, 所有块展平的 cell centers (cm, 已排序)
        - dens/tele/...: ndarray, 对应变量的值 (与 x 同长度)
    """
    ff = FlashHDF5File(filepath)

    result = {"time": ff.simulation_time}

    for vname in var_names:
        resolved = ff.resolve_var_name(vname)
        if resolved in ff.varnames:
            all_x, all_y = ff.slice_1d(resolved)
            # 缓存 x (所有变量共享同一网格)
            if "x" not in result:
                result["x"] = all_x
            result[vname] = all_y
        else:
            print(f"  [警告] 变量 '{vname}' 不在文件中, 填充0")
            if "x" in result:
                result[vname] = np.zeros_like(result["x"])
            else:
                result[vname] = np.array([])

    ff.close()
    return result


# ============================================================
# 核心插值逻辑
# ============================================================

def interpolate_flash_to_grid(
    flash_files: List[str],
    t_grid: np.ndarray,
    x_grid: np.ndarray,
    var_names: Optional[List[str]] = None,
    use_parallel: bool = True,
    max_workers: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """将 FLASH 输出文件系列插值到固定时空网格

    流程:
      1. 读取所有 FLASH HDF5 → 时间排序
      2. 预读取, 用 slice_1d() 获取排序后的 (x, value)
      3. 对每个目标时刻 t_i:
         a. 找到 FLASH 最近邻两个输出 t_a ≤ t_i ≤ t_b
         b. 对 t_a 和 t_b 分别做 1D 空间插值 (numpy.interp)
         c. 时间线性插值

    Args:
        flash_files: FLASH HDF5 文件路径列表
        t_grid: 目标时间网格 [Nt] (s)
        x_grid: 目标空间网格 [Nx] (cm)
        var_names: 需要插值的变量列表 (默认自动检测)
        use_parallel: 是否使用并行处理 (默认 True)
        max_workers: 最大并行数 (None=自动)

    Returns:
        {field_name: ndarray of shape (Nt, Nx)}
    """
    if not flash_files:
        raise ValueError("FLASH HDF5 文件列表为空")

    # --- 1. 读取所有 FLASH 输出 (可选并行) ---
    print(f"  读取 {len(flash_files)} 个 FLASH HDF5 文件...")
    flash_slices = []

    if use_parallel and len(flash_files) >= 4:
        from output_processors.parallel import parallel_load_folder
        from pathlib import Path

        folder = Path(flash_files[0]).parent
        raw_slices = parallel_load_folder(
            str(folder), pattern="*chk*",
            max_workers=max_workers, verbose=False,
        )
        # 只保留在 flash_files 列表中的文件
        file_set = {str(Path(f).resolve()) for f in flash_files}
        flash_slices = [s for s in raw_slices
                        if str(Path(s.get("filepath", "")).resolve()) in file_set]
        # 补充变量名
        if flash_slices and var_names is None:
            var_names = [k for k in flash_slices[0]
                         if k not in ("time", "x", "filepath", "step")]
        print(f"  [并行] 读取完成: {len(flash_slices)} 个文件")
    else:
        for fpath in sorted(flash_files):
            try:
                sl = read_flash_slice(fpath, DEFAULT_OUTPUT_FIELDS)
                flash_slices.append(sl)
            except Exception as e:
                print(f"  [跳过] {os.path.basename(fpath)}: {e}")

    if not flash_slices:
        raise RuntimeError("没有成功读取任何 FLASH HDF5 文件")

    # 按时间排序
    flash_slices.sort(key=lambda x: x["time"])
    n_flash = len(flash_slices)
    flash_times = np.array([s["time"] for s in flash_slices])
    print(f"  FLASH 时间范围: {flash_times[0]:.4e} ~ {flash_times[-1]:.4e} s ({n_flash} 个文件)")

    # 确定变量列表
    if var_names is None:
        var_names = [k for k in flash_slices[0] if k not in ("time", "x")]
    print(f"  插值变量: {var_names}")

    # --- 2. 预构建空间数据 ---
    flash_data = []
    for sl in flash_slices:
        entry = {"x": sl["x"]}
        for vn in var_names:
            entry[vn] = sl.get(vn, np.zeros_like(sl["x"]))
        flash_data.append(entry)

    # --- 3. 时空插值 (可选并行) ---
    Nt, Nx = len(t_grid), len(x_grid)

    if use_parallel and Nt >= 16 and len(flash_slices) >= 2:
        from output_processors.parallel import parallel_interpolate
        result = parallel_interpolate(
            flash_slices, t_grid, x_grid, var_names,
            max_workers=max_workers, verbose=True,
        )
    else:
        result: Dict[str, np.ndarray] = {vn: np.zeros((Nt, Nx), dtype=np.float32)
                                          for vn in var_names}
        for ti in range(Nt):
            t_target = t_grid[ti]
            if t_target <= flash_times[0]:
                ta_idx = tb_idx = 0
                alpha = 0.0
            elif t_target >= flash_times[-1]:
                ta_idx = tb_idx = n_flash - 1
                alpha = 0.0
            else:
                tb_idx = np.searchsorted(flash_times, t_target, side="right")
                ta_idx = tb_idx - 1
                dt = flash_times[tb_idx] - flash_times[ta_idx]
                alpha = (t_target - flash_times[ta_idx]) / dt if dt > 0 else 0.0
            for vn in var_names:
                fa = np.interp(x_grid, flash_data[ta_idx]["x"],
                               flash_data[ta_idx][vn], left=0.0, right=0.0)
                if ta_idx == tb_idx:
                    fb = fa
                else:
                    fb = np.interp(x_grid, flash_data[tb_idx]["x"],
                                   flash_data[tb_idx][vn], left=0.0, right=0.0)
                result[vn][ti, :] = (1.0 - alpha) * fa + alpha * fb
            if (ti + 1) % 50 == 0:
                print(f"    时间步 {ti+1}/{Nt}...")

    return result


# ============================================================
# HDF5 输出保存
# ============================================================

def save_output_hdf5(
    filepath: str,
    t_grid: np.ndarray,
    x_grid: np.ndarray,
    fields: Dict[str, np.ndarray],
    input_params: Optional[Dict] = None,
    compression: str = "gzip",
    compression_opts: int = 4,
) -> str:
    """保存插值后的数据到 HDF5 文件

    Args:
        filepath: 输出文件路径
        t_grid: 时间网格 (s)
        x_grid: 空间网格 (cm)
        fields: {field_name: ndarray (Nt, Nx)}
        input_params: 输入参数字典 (保存为属性)
        compression: HDF5 压缩类型

    Returns:
        filepath (str)
    """
    filepath = str(Path(filepath).resolve())
    with h5py.File(filepath, "w") as f:
        f.create_dataset("t", data=t_grid, dtype=np.float64)
        f.create_dataset("x", data=x_grid, dtype=np.float64)
        f["t"].attrs["unit"] = "s"
        f["t"].attrs["description"] = f"Time grid, {len(t_grid)} pts, step={np.mean(np.diff(t_grid))*1e12:.1f}ps"
        f["x"].attrs["unit"] = "cm"
        f["x"].attrs["description"] = f"Spatial grid (variable resolution), {len(x_grid)} pts"
        f["x"].attrs["min_um"] = float(x_grid[0] * 1e4)
        f["x"].attrs["max_um"] = float(x_grid[-1] * 1e4)
        f["x"].attrs["core_step_um"] = 0.01  # core resolution info

        for fname, data in fields.items():
            ds = f.create_dataset(fname, data=data, dtype=np.float32,
                                  compression=compression,
                                  compression_opts=compression_opts)
            ds.attrs["dim"] = "(t, x)"
            ds.attrs["shape"] = f"{data.shape}"

        if input_params:
            for key, value in input_params.items():
                try:
                    f.attrs[key] = str(value) if isinstance(value, (list, tuple)) else value
                except (TypeError, ValueError):
                    f.attrs[key] = str(value)

        f.attrs["Nt"] = len(t_grid)
        f.attrs["Nx"] = len(x_grid)
        f.attrs["generated_by"] = "thin_layer_sandwich.interpolator"
        f.attrs["grid_type"] = "variable_resolution"

    return filepath
