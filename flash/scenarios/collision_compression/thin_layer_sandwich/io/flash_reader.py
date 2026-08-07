"""FLASH 结果读取器 — 从引擎 result.h5 构建分析用原始数据。

替代历史丢失的 ``io/flash_reader.py`` (从原始 chk 重建), 基于引擎已插值的
result.h5 提供相同接口::

    raw = build_raw_from_engine(result_h5, center_half_width_um=1.0)
    raw["times_s"]      # (Nt,) 时间 (s)
    raw["fields"]       # {name: ndarray (Nt, Nx_center)}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

# 阿伏伽德罗常数 (cm^-3 量级换算用)
NA = 6.02214076e23


def build_raw_from_engine(
    result_h5: str | Path,
    center_half_width_um: float = 1.0,
    verbose: bool = True,
) -> Dict[str, Any]:
    """从引擎 result.h5 构建中心区域原始数据。

    取 x ∈ [-center_half_width_um, +center_half_width_um] 的子区域,
    返回 (Nt, Nx_center) 数组, 供滑动窗口/插值/绘图使用。

    Args:
        result_h5: 引擎输出 result.h5 路径
        center_half_width_um: 中心区域半宽 (um)
        verbose: 打印读取信息

    Returns:
        {"times_s": ndarray (Nt,), "fields": {name: ndarray (Nt, Nx_center)}}
    """
    import h5py

    result_h5 = Path(result_h5)
    if verbose:
        print(f"  [flash_reader] 读取 {result_h5.name} ...")

    with h5py.File(str(result_h5), "r") as f:
        t = np.asarray(f["t"][:], dtype=np.float64)
        x = np.asarray(f["x"][:], dtype=np.float64)
        x_um = x * 1e4
        mask = np.abs(x_um) <= center_half_width_um
        if not np.any(mask):
            mask = np.abs(x_um) <= np.min(np.abs(x_um)) + 1e-9
        idx = np.where(mask)[0]

        fields: Dict[str, np.ndarray] = {}
        for name in f.keys():
            if name in ("t", "x"):
                continue
            arr = np.asarray(f[name][()], dtype=np.float64)
            if arr.ndim == 2 and arr.shape[1] == len(x):
                fields[name] = arr[:, idx]
            elif arr.ndim == 1 and len(arr) == len(x):
                fields[name] = arr[idx]

    return {"times_s": t, "fields": fields}
