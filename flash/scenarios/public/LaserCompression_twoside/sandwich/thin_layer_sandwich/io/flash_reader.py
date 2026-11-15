"""
flash_reader — FLASH HDF5 输出读取

从 FLASH checkpoint / plot HDF5 文件中提取中心区域的
密度、电子温度、电子密度时间序列。

独立于优化框架，可被仿真脚本或分析管线直接调用。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# ── 物理常量 ────────────────────────────────────────────
NA = 6.02214076e23  # 阿伏伽德罗常数 (cm⁻³)


# ══════════════════════════════════════════════════════════
# 单文件读取
# ══════════════════════════════════════════════════════════

def read_flash_hdf5_center(
    hdf5_path: Path,
    center_half_width_um: float = 1.0,
) -> Dict[str, float]:
    """读取单个 FLASH HDF5 (plt 或 chk) 文件, 提取中心区域的物理量均值。

    Args:
        hdf5_path: HDF5 文件路径
        center_half_width_um: 中心提取区域半宽 (um), 默认 ±1 um

    Returns:
        dict: {变量名: 均值}, 键包括 dens, tele, ye, nele (计算量), tion, trad, lase
    """
    import h5py

    result: Dict[str, float] = {}

    with h5py.File(str(hdf5_path), "r") as f:
        # 读取坐标
        coords = f["coordinates"][:]
        x = coords[:, 0] if coords.ndim == 2 else coords

        # 读取时间
        time_val = 0.0
        if "timestep" in f:
            time_val = float(f["timestep"].attrs.get("time", 0.0))
        elif "time" in f.attrs:
            time_val = float(f.attrs["time"])
        result["time_s"] = time_val

        # 中心区域掩码
        half_cm = center_half_width_um * 1e-4
        center_mask = np.abs(x) <= half_cm
        if np.sum(center_mask) == 0:
            # 单格点回退: 取最中心点
            center_mask = np.zeros(len(x), dtype=bool)
            center_mask[len(x) // 2] = True

        # 提取各物理量
        for varname in ["dens", "tele", "ye", "tion", "trad", "lase", "sumy"]:
            if varname in f:
                data = f[varname][:]
                result[varname] = float(np.mean(data[center_mask]))

        # 计算电子密度: nele = ye * dens * NA
        if "ye" in result and "dens" in result:
            result["nele"] = result["ye"] * result["dens"] * NA

    return result


# ══════════════════════════════════════════════════════════
# 多文件时间序列读取
# ══════════════════════════════════════════════════════════

def read_flash_output_timeseries(
    output_dir: Path,
    center_half_width_um: float = 1.0,
    verbose: bool = True,
) -> Dict[str, Any]:
    """从 FLASH 输出目录读取所有 plt HDF5 文件, 构建中心区域时间序列。

    Args:
        output_dir: FLASH 输出目录
        center_half_width_um: 中心提取区域半宽 (um)
        verbose: 是否打印进度

    Returns:
        dict: {
            "times_s": ndarray,       # 时间数组 (s)
            "fields": {               # 各物理量时间序列
                "dens": ndarray,
                "tele": ndarray,
                "nele": ndarray,
                ...
            }
        }
        失败或无数据时返回含单时间步的默认数组。
    """
    # 查找 plt / chk 文件
    plot_files = sorted(output_dir.glob("**/*hdf5_plt_cnt*"))
    if not plot_files:
        plot_files = sorted(output_dir.glob("**/*plt_cnt*"))
    if not plot_files:
        plot_files = sorted(output_dir.glob("**/*.h5"))

    if not plot_files:
        if verbose:
            print(f"  Warning: No HDF5 files found in {output_dir}")
        # 返回默认数据 (避免调用方崩溃)
        return {
            "times_s": np.array([0.0, 1e-12, 2e-12], dtype=float),
            "fields": {
                "dens": np.array([0.08, 0.08, 0.08], dtype=float),
                "tele": np.array([1e6, 1e6, 1e6], dtype=float),
                "nele": np.array([1e23, 1e23, 1e23], dtype=float),
            },
        }

    times_list: List[float] = []
    fields_dict: Dict[str, List[float]] = {}

    for pf in plot_files:
        try:
            point = read_flash_hdf5_center(pf, center_half_width_um)
            t = point.pop("time_s", 0.0)
            times_list.append(t)
            for key, val in point.items():
                if key not in fields_dict:
                    fields_dict[key] = []
                fields_dict[key].append(float(val))
        except Exception:
            continue

    if len(times_list) < 2:
        return {
            "times_s": np.array([0.0], dtype=float),
            "fields": {k: np.array([v[0] if v else 0.0], dtype=float)
                       for k, v in fields_dict.items()},
        }

    # 按时间排序
    sort_idx = np.argsort(times_list)
    times_arr = np.array(times_list, dtype=float)[sort_idx]

    sorted_fields: Dict[str, np.ndarray] = {}
    for key, vals in fields_dict.items():
        sorted_fields[key] = np.array(vals, dtype=float)[sort_idx]

    return {"times_s": times_arr, "fields": sorted_fields}


# ══════════════════════════════════════════════════════════
# 从引擎输出构建 raw_output
# ══════════════════════════════════════════════════════════

def build_raw_from_engine(
    result_h5_path: Path,
    center_half_width_um: float = 0.0,
    verbose: bool = True,
) -> Dict[str, Any]:
    """从引擎生成的 result.h5 构建 raw_output 字典。

    引擎输出 result.h5 已包含插值到均匀网格的时间序列,
    这是一个轻量级包装, 直接提取中心区域数据。

    Args:
        result_h5_path: result.h5 路径
        center_half_width_um: 空间窗口半宽 (um)
            =0 → 仅取中心单格点
            >0 → 空间窗口平均
        verbose: 是否打印信息

    Returns:
        dict: {"times_s": ndarray, "fields": {"tele": ..., "nele": ..., "dens": ...}}
    """
    import os
    import h5py

    h5_path = str(result_h5_path)
    if not os.path.exists(h5_path):
        if verbose:
            print(f"  Warning: result.h5 not found: {h5_path}")
        return {"times_s": np.array([0.0]), "fields": {}}

    with h5py.File(h5_path, "r") as f:
        t = f["t"][:]
        x = f["x"][:]
        fields = {}
        for vn in ["dens", "tele", "ye", "tion", "trad"]:
            if vn in f:
                fields[vn] = f[vn][()]

    n_t = len(t)

    if "ye" in fields and "dens" in fields:
        ye = np.array(fields["ye"])
        dens = np.array(fields["dens"])
        fields["nele"] = ye * dens * NA

    # 空间窗口
    center_idx = len(x) // 2

    if center_half_width_um > 0:
        dx_um = center_half_width_um * 1e-4
        x_center = float(x[center_idx])
        mask = (x >= x_center - dx_um) & (x <= x_center + dx_um)
        idx_in_window = np.where(mask)[0]

        def _spatial_mean(arr: np.ndarray) -> np.ndarray:
            if arr.ndim == 2 and arr.shape[1] > 0:
                return np.mean(arr[:, idx_in_window], axis=1)
            return arr

        raw_fields = {
            k: _spatial_mean(np.array(v)) if isinstance(v, np.ndarray) else v
            for k, v in fields.items()
        }
        if verbose and len(idx_in_window) > 0:
            x_min_um = float(x[idx_in_window[0]] * 1e4)
            x_max_um = float(x[idx_in_window[-1]] * 1e4)
            print(f"  空间窗口: [{x_min_um:.1f}, {x_max_um:.1f}] um, "
                  f"{len(idx_in_window)} 格点平均")
    else:
        raw_fields = {}
        for k, v in fields.items():
            arr = np.array(v)
            raw_fields[k] = arr[:, center_idx] if arr.ndim == 2 else arr

    return {"times_s": np.array(t), "fields": raw_fields}
