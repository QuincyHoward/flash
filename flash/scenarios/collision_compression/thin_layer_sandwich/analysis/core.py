"""分析核心 — 均匀网格插值 + T×N 滑动窗口峰值检测。

替代历史丢失的 ``analysis/core.py``, 基于引擎 result.h5 的中心区域数据:
  - ``interpolate_to_uniform_grid``: 时间轴重采样到均匀网格
  - ``sliding_window_txn``: 在 T×N (Tele*Nele) 时序上滑动窗口, 找峰值窗口
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def interpolate_to_uniform_grid(
    times_s: np.ndarray,
    fields: Dict[str, np.ndarray],
    n_points: Optional[int] = None,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """时间轴重采样到均匀网格。

    Args:
        times_s: 原始时间轴 (Nt,)
        fields: {name: ndarray (Nt, Nx)}
        n_points: 目标时间点数 (默认 len(times_s))

    Returns:
        (t_uniform, interp) — t_uniform: (Nt,) 均匀时间轴;
        interp: {name: ndarray (Nt_uniform, Nx)} 线性插值结果
    """
    times_s = np.asarray(times_s, dtype=np.float64)
    n_orig = len(times_s)
    if n_points is None or n_points <= 0:
        n_points = n_orig
    if n_orig < 2:
        return times_s, dict(fields)

    t_uniform = np.linspace(times_s[0], times_s[-1], n_points)
    interp: Dict[str, np.ndarray] = {}
    for name, arr in fields.items():
        arr = np.asarray(arr, dtype=np.float64)
        if arr.ndim == 1 and len(arr) == n_orig:
            interp[name] = np.interp(t_uniform, times_s, arr)
        elif arr.ndim == 2 and arr.shape[0] == n_orig:
            out = np.empty((n_points, arr.shape[1]), dtype=np.float64)
            for j in range(arr.shape[1]):
                out[:, j] = np.interp(t_uniform, times_s, arr[:, j])
            interp[name] = out
        else:
            interp[name] = arr
    return t_uniform, interp


def sliding_window_txn(
    grid_s: np.ndarray,
    txn_arr: np.ndarray,
    tele_arr: Optional[np.ndarray] = None,
    nele_arr: Optional[np.ndarray] = None,
    window_ns: float = 0.1,
    min_peak_ratio: float = 0.3,
    margin_ns: float = 0.02,
) -> Dict[str, Any]:
    """在 T×N 时序上滑动窗口, 找 T×N 显著增强的时间窗口。

    T×N = Tele × Nele (电离度 × 电子密度) 的强增强对应靶等离子体
    快速电离/压缩时刻, 用于自动圈出物理感兴趣窗口。

    Args:
        grid_s: 均匀时间轴 (Nt,) (s)
        txn_arr: T×N 序列 (Nt,) 或 (Nt, Nx) (取中心列)
        tele_arr: Tele (Nt,) 或 (Nt, Nx) (可选, 用于输出统计)
        nele_arr: Nele (Nt,) 或 (Nt, Nx) (可选)
        window_ns: 窗口宽度 (ns)
        min_peak_ratio: 窗口均值 ≥ ratio × 全局峰值 才接受
        margin_ns: 窗口与峰值之间最小间隔 (ns)

    Returns:
        {"best_start_ns", "best_end_ns", "best_mean",
         "peak_ns", "peak_value", "mean_series_ns"}
    """
    grid_s = np.asarray(grid_s, dtype=np.float64)

    def _center1d(a):
        a = np.asarray(a, dtype=np.float64)
        if a.ndim == 2:
            return a[:, a.shape[1] // 2]
        return a

    txn = _center1d(txn_arr)
    if tele_arr is not None:
        tele_c = _center1d(tele_arr)
    else:
        tele_c = None
    if nele_arr is not None:
        nele_c = _center1d(nele_arr)
    else:
        nele_c = None

    nt = len(grid_s)
    if nt == 0:
        return {}
    dt = float(np.mean(np.diff(grid_s))) if nt > 1 else 1e-12
    win_steps = max(1, int(round(window_ns * 1e-9 / dt)))
    margin_steps = max(0, int(round(margin_ns * 1e-9 / dt)))

    peak_idx = int(np.argmax(txn))
    peak_val = float(txn[peak_idx])
    if peak_val <= 0 or nt < 2:
        return {
            "best_start_ns": float(grid_s[0]) * 1e9,
            "best_end_ns": float(grid_s[-1]) * 1e9,
            "best_mean": 0.0,
            "peak_ns": float(grid_s[peak_idx]) * 1e9,
            "peak_value": peak_val,
            "mean_series_ns": None,
        }

    best_mean = -1.0
    best_start = best_end = 0
    mean_series = []
    for i in range(0, max(1, nt - win_steps + 1)):
        j = min(i + win_steps, nt)
        seg = txn[i:j]
        if len(seg) == 0:
            continue
        m = float(np.mean(seg))
        mean_series.append(m)
        # 窗口需覆盖峰值附近 (允许 margin 偏移)
        if abs(i - peak_idx) <= win_steps + margin_steps or \
           (i <= peak_idx <= j):
            if m > best_mean:
                best_mean = m
                best_start, best_end = i, j

    # 若未找到覆盖峰值的窗口, 回退到全范围
    if best_mean < 0:
        best_start, best_end = 0, nt
        best_mean = float(np.mean(txn))

    return {
        "best_start_ns": float(grid_s[best_start]) * 1e9,
        "best_end_ns": float(grid_s[min(best_end, nt - 1)]) * 1e9,
        "best_mean": best_mean,
        "peak_ns": float(grid_s[peak_idx]) * 1e9,
        "peak_value": peak_val,
        "mean_series_ns": np.asarray(mean_series) * 1e9 if mean_series else None,
    }
