"""
core — 分析核心工具函数

提供滑动窗口分析、统一网格插值、基础统计计算等共享功能。

来源: chsich02/analysis/txn.py 和 analysis/dens.py 的滑动窗口和插值逻辑。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


# ── 基础统计 ────────────────────────────────────────────

def compute_mean(field: np.ndarray) -> float:
    """计算时间序列均值。"""
    return float(np.mean(field))


def compute_max(field: np.ndarray) -> float:
    """计算时间序列最大值。"""
    return float(np.max(field))


def compute_cv(field: np.ndarray) -> float:
    """计算变异系数 (std / mean)。均值为零时返回 inf。"""
    m = np.mean(field)
    if m == 0:
        return float("inf")
    return float(np.std(field) / m)


def compute_norm(field_mean: float, base: float) -> float:
    """计算归一化值 (mean / base)。"""
    return float(field_mean / base) if base != 0 else float("inf")


# ── 统一网格插值 ────────────────────────────────────────

def interpolate_to_uniform_grid(
    times_s: np.ndarray,
    series: Dict[str, np.ndarray],
    t_start_s: float = 0.0,
    t_step_s: float = 1e-11,   # 0.01 ns
    t_end_s: float = 3.0e-9,   # 3 ns
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """将所有时间序列线性插值到统一时间网格。

    Args:
        times_s: 原始时间数组 (s)
        series: {变量名: 值数组} 字典
        t_start_s: 网格起始时间 (s)
        t_step_s: 网格步长 (s)
        t_end_s: 网格结束时间 (s)

    Returns:
        (grid_s, interpolated):
            grid_s: 统一时间网格 (s)
            interpolated: {变量名: 插值后数组}
    """
    grid_s = np.arange(t_start_s, t_end_s + t_step_s / 2, t_step_s)
    interpolated = {}
    for name, values in series.items():
        interp = np.interp(grid_s, times_s, np.asarray(values),
                           left=0.0, right=0.0)
        interpolated[name] = interp
    return grid_s, interpolated


# ── 300ps 滑动窗口分析 (通用版) ────────────────────────

def sliding_window_300ps(
    times_s: np.ndarray,
    score_series: np.ndarray,
    *,
    metric_series: Optional[Dict[str, np.ndarray]] = None,
    window_ps: float = 300.0,
    step_ps: float = 10.0,
) -> Dict[str, Any]:
    """在时间序列上滑动固定宽度窗口, 找到最优窗口。

    窗口得分 = score_series 在窗口内的均值 (越大越好)。
    附加指标: metric_series 中各序列在最优窗口内的均值/CV。

    Args:
        times_s: 时间数组 (s)
        score_series: 得分序列 (窗口内均值作为窗口得分)
        metric_series: 附加指标序列字典, 如 {"tele": ..., "nele": ...}
        window_ps: 窗口宽度 (ps)
        step_ps: 滑动步长 (ps)

    Returns:
        dict:
            "best_score": float, 最优窗口得分
            "best_start_idx": int, 最优窗口起始索引
            "best_end_idx": int, 最优窗口结束索引
            "best_start_ns": float, 起始时间 (ns)
            "best_end_ns": float, 结束时间 (ns)
            "window_metrics": {指标名: {mean: ..., cv: ...}} 在最优窗口内的统计
    """
    result: Dict[str, Any] = {
        "best_score": 0.0,
        "best_start_idx": 0,
        "best_end_idx": 0,
        "best_start_ns": 0.0,
        "best_end_ns": 0.0,
        "window_metrics": {},
    }

    if len(times_s) < 2:
        return result

    window_size_s = window_ps * 1e-12
    step_size_s = step_ps * 1e-12

    best_score = -1.0
    best_start = 0
    best_end = min(1, len(times_s) - 1)

    start_idx = 0
    while start_idx < len(times_s):
        t_start = times_s[start_idx]
        t_end = t_start + window_size_s
        end_idx = int(np.searchsorted(times_s, t_end, side="left"))
        if end_idx > len(times_s):
            end_idx = len(times_s)
        actual_window = end_idx - start_idx

        if actual_window >= 2:
            score = float(np.mean(score_series[start_idx:end_idx]))
            if score > best_score:
                best_score = score
                best_start = start_idx
                best_end = end_idx

        next_t = times_s[start_idx] + step_size_s
        next_idx = int(np.searchsorted(times_s, next_t, side="left"))
        if next_idx <= start_idx:
            next_idx = start_idx + 1
        start_idx = next_idx

    result["best_score"] = best_score
    result["best_start_idx"] = best_start
    result["best_end_idx"] = best_end
    result["best_start_ns"] = float(times_s[best_start] * 1e9)
    result["best_end_ns"] = result["best_start_ns"] + window_ps / 1000.0

    # 最优窗口内的附加指标
    if metric_series:
        metrics = {}
        for name, array in metric_series.items():
            arr_w = np.asarray(array)[best_start:best_end]
            if len(arr_w) > 0:
                m = float(np.mean(arr_w))
                cv = float(np.std(arr_w) / m) if m > 0 else 1e10
                metrics[name] = {"mean": m, "cv": cv}
        result["window_metrics"] = metrics

    return result


# ── TXN 专用滑动窗口 (保持兼容) ─────────────────────────

def sliding_window_txn(
    times_s: np.ndarray,
    txn_series: np.ndarray,
    tele_series: np.ndarray,
    nele_series: np.ndarray,
    tele_base: float = 1.2e6,
    nele_base: float = 1.4e23,
    window_ps: float = 300.0,
    step_ps: float = 10.0,
) -> Dict[str, Any]:
    """TXN 专属 300ps 滑动窗口分析。

    窗口得分 = min(tele_norm, nele_norm)  最差基线比
    即: 在时间方向上寻找"短板最高"的 300ps 窗口。

    与 chsich02/analysis/txn.py 中 sliding_window_300ps 接口一致。

    Returns:
        dict: 含 txn_effective, txn_raw, tele_cv, nele_cv, max_cv,
              tele_mean_window, nele_mean_window, best_start/end_idx/ns
    """
    if len(times_s) < 2:
        return {"txn_effective": 0.0, "txn_raw": 0.0,
                "best_start_idx": 0, "best_end_idx": 0,
                "best_start_ns": 0.0, "best_end_ns": 0.0}

    window_size_s = window_ps * 1e-12
    step_size_s = step_ps * 1e-12

    best_score = -1.0
    best_start = 0
    best_end = min(1, len(times_s) - 1)

    start_idx = 0
    while start_idx < len(times_s):
        t_start = times_s[start_idx]
        t_end = t_start + window_size_s
        end_idx = int(np.searchsorted(times_s, t_end, side="left"))
        if end_idx > len(times_s):
            end_idx = len(times_s)
        actual_window = end_idx - start_idx

        if actual_window >= 2:
            tele_mean = float(np.mean(tele_series[start_idx:end_idx]))
            nele_mean = float(np.mean(nele_series[start_idx:end_idx]))
            tele_norm = tele_mean / tele_base
            nele_norm = nele_mean / nele_base
            score = min(tele_norm, nele_norm)  # 最差基线比
            if score > best_score:
                best_score = score
                best_start = start_idx
                best_end = end_idx

        next_t = times_s[start_idx] + step_size_s
        next_idx = int(np.searchsorted(times_s, next_t, side="left"))
        if next_idx <= start_idx:
            next_idx = start_idx + 1
        start_idx = next_idx

    # 最优窗口统计
    txn_best = txn_series[best_start:best_end]
    tele_best = tele_series[best_start:best_end]
    nele_best = nele_series[best_start:best_end]

    tele_mean = float(np.mean(tele_best)) if len(tele_best) > 0 else 0.0
    nele_mean = float(np.mean(nele_best)) if len(nele_best) > 0 else 0.0
    tele_std = float(np.std(tele_best)) if len(tele_best) > 1 else 0.0
    nele_std = float(np.std(nele_best)) if len(nele_best) > 1 else 0.0
    tele_cv = tele_std / tele_mean if tele_mean > 0 else 1e10
    nele_cv = nele_std / nele_mean if nele_mean > 0 else 1e10
    txn_raw_mean = float(np.mean(txn_best)) if len(txn_best) > 0 else 0.0

    best_start_ns = float(times_s[best_start] * 1e9)

    return {
        "txn_effective": best_score,
        "txn_raw": txn_raw_mean,
        "tele_cv": tele_cv,
        "nele_cv": nele_cv,
        "max_cv": max(tele_cv, nele_cv),
        "tele_mean_window": tele_mean,
        "nele_mean_window": nele_mean,
        "best_start_idx": int(best_start),
        "best_end_idx": int(best_end),
        "best_start_ns": best_start_ns,
        "best_end_ns": best_start_ns + window_ps / 1000.0,
    }


# ── Dens 专用滑动窗口 (保持兼容) ────────────────────────

def sliding_window_dens(
    times_s: np.ndarray,
    dens_series: np.ndarray,
    dens_base: float = 1.10,
    window_ps: float = 300.0,
    step_ps: float = 10.0,
) -> Dict[str, Any]:
    """Dens 专属 300ps 滑动窗口分析。

    窗口得分 = mean(dens) / dens_base。

    与 chsich02/analysis/dens.py 中 sliding_window_300ps 接口一致。

    Returns:
        dict: 含 dens_norm, dens_mean_window, dens_cv,
              best_start_idx, best_end_idx, best_start_ns, best_end_ns
    """
    if len(times_s) < 2:
        return {"dens_norm": 0.0, "dens_mean_window": 0.0, "dens_cv": 1e10,
                "best_start_idx": 0, "best_end_idx": 0,
                "best_start_ns": 0.0, "best_end_ns": 0.0}

    window_size_s = window_ps * 1e-12
    step_size_s = step_ps * 1e-12

    best_score = -1.0
    best_start = 0
    best_end = min(1, len(times_s) - 1)

    start_idx = 0
    while start_idx < len(times_s):
        t_start = times_s[start_idx]
        t_end = t_start + window_size_s
        end_idx = int(np.searchsorted(times_s, t_end, side="left"))
        if end_idx > len(times_s):
            end_idx = len(times_s)
        actual_window = end_idx - start_idx

        if actual_window >= 2:
            dens_mean = float(np.mean(dens_series[start_idx:end_idx]))
            score = dens_mean / dens_base
            if score > best_score:
                best_score = score
                best_start = start_idx
                best_end = end_idx

        next_t = times_s[start_idx] + step_size_s
        next_idx = int(np.searchsorted(times_s, next_t, side="left"))
        if next_idx <= start_idx:
            next_idx = start_idx + 1
        start_idx = next_idx

    dens_best = dens_series[best_start:best_end]
    dens_mean = float(np.mean(dens_best)) if len(dens_best) > 0 else 0.0
    dens_std = float(np.std(dens_best)) if len(dens_best) > 1 else 0.0
    dens_cv = dens_std / dens_mean if dens_mean > 0 else 1e10
    best_start_ns = float(times_s[best_start] * 1e9)

    return {
        "dens_norm": best_score,
        "dens_mean_window": dens_mean,
        "dens_cv": dens_cv,
        "best_start_idx": int(best_start),
        "best_end_idx": int(best_end),
        "best_start_ns": best_start_ns,
        "best_end_ns": best_start_ns + window_ps / 1000.0,
    }
