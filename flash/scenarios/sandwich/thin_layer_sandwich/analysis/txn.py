"""
txn — TXN (nele×tele) 反应产额分析

从 FLASH 输出中提取 nele 和 tele 中心时间序列, 执行滑动窗口分析,
生成 TXN 合并诊断图。

功能对应 chsich02/analysis/txn.py 的 compute_analysis 和绘图函数。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .core import (
    sliding_window_txn,
    interpolate_to_uniform_grid,
)
from ..io.flash_reader import read_flash_output_timeseries, NA
from ..io.result_saver import save_analysis_data


# ── TXN 合并时间序列图 (三行) ───────────────────────────

def plot_time_series(
    times_s: np.ndarray,
    txn_series: np.ndarray,
    tele_series: np.ndarray,
    nele_series: np.ndarray,
    window_result: Dict[str, Any],
    save_prefix: str,
    *,
    dens_series: Optional[np.ndarray] = None,
) -> Dict[str, str]:
    """绘制 txn/tele/nele 三行合并图, 标注最优 300ps 窗口。

    与 chsich02/analysis/txn.py 的 plot_time_series_with_window 接口兼容。

    Args:
        times_s: 时间数组 (s)
        txn_series: txn = nele × tele 序列
        tele_series: tele 序列 (K)
        nele_series: nele 序列 (cm⁻³)
        window_result: sliding_window_txn() 的结果字典
        save_prefix: 保存路径前缀 (不含扩展名)

    Returns:
        {变量名: 路径} 字典
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    times_ns = times_s * 1e9
    best_start_ns = window_result.get("best_start_ns", 0.0)
    best_end_ns = window_result.get("best_end_ns", 0.0)
    txn_eff = window_result.get("txn_effective", 0.0)
    tele_cv = window_result.get("tele_cv", 0.0)
    nele_cv = window_result.get("nele_cv", 0.0)
    tele_mean_w = window_result.get("tele_mean_window", 0.0)
    nele_mean_w = window_result.get("nele_mean_window", 0.0)

    n_rows = 4 if dens_series is not None else 3
    fig, axes = plt.subplots(n_rows, 1, figsize=(11, 9 + 2 * (n_rows - 3)),
                             sharex=True)

    # 1. txn vs time
    ax = axes[0]
    ax.plot(times_ns, txn_series, "b-", linewidth=1.5, label="txn(t)")
    ax.axvspan(best_start_ns, best_end_ns, color="green", alpha=0.2,
               label=f"Best window (txn_norm={txn_eff:.4f})")
    ax.axvline(x=best_start_ns, color="green", linestyle="--", alpha=0.7)
    ax.axvline(x=best_end_ns, color="green", linestyle="--", alpha=0.7)
    ax.set_ylabel("txn = nele × tele")
    ax.set_title("TXN Reaction Yield vs Time")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # 2. tele vs time
    ax = axes[1]
    ax.plot(times_ns, tele_series, "r-", linewidth=1.5, label="tele(t)")
    ax.axvspan(best_start_ns, best_end_ns, color="green", alpha=0.2,
               label=f"Best window (tele={tele_mean_w:.3e} K, CV={tele_cv:.4f})")
    ax.set_ylabel("tele (K)")
    ax.set_title("Electron Temperature vs Time")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # 3. nele vs time
    ax = axes[2]
    ax.plot(times_ns, nele_series, "purple", linewidth=1.5, label="nele(t)")
    ax.axvspan(best_start_ns, best_end_ns, color="green", alpha=0.2,
               label=f"Best window (nele={nele_mean_w:.3e} /cm³, CV={nele_cv:.4f})")
    ax.set_ylabel("nele (cm⁻³)")
    ax.set_title("Electron Density vs Time")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # 4. dens vs time (可选)
    if dens_series is not None:
        ax = axes[3]
        ax.plot(times_ns, dens_series, "orange", linewidth=1.5, label="dens(t)")
        ax.axvspan(best_start_ns, best_end_ns, color="green", alpha=0.2)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Density (g/cm³)")
        ax.set_title("Mass Density vs Time")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    else:
        axes[-1].set_xlabel("Time (ns)")

    plt.tight_layout()
    path = save_prefix + "_time_series.png"
    fig.savefig(path, dpi=150, bbox_inches=None)
    plt.close(fig)

    return {"combined": path}


# ── 完整分析管线 ────────────────────────────────────────

def compute_analysis(
    work_dir: Path,
    tele_base: float = 1.2e6,
    nele_base: float = 1.4e23,
    analysis_half_width_um: Optional[float] = None,
) -> Dict[str, Any]:
    """从 FLASH 运行结果计算完整的 TXN 分析结果。

    流程:
      1. 读取 FLASH HDF5 输出
      2. 插值到统一时间网格
      3. 300ps 滑动窗口分析
      4. 生成诊断图
      5. 保存 CSV / NPZ / JSON

    Args:
        work_dir: FLASH 运行目录 (含 flash_output 子目录)
        tele_base: 电子温度基线 (K)
        nele_base: 电子密度基线 (cm⁻³)
        analysis_half_width_um: 中心提取半宽 (um), 默认 1.0

    Returns:
        完整分析结果字典, 含 txn, txn_raw, tele_cv, nele_cv, max_cv, ...
    """
    if analysis_half_width_um is None:
        analysis_half_width_um = 1.0

    result: Dict[str, Any] = {
        "txn": 0.0,
        "txn_raw": 0.0,
        "tele_norm": 0.0,
        "nele_norm": 0.0,
        "tele_cv": 1e10,
        "nele_cv": 1e10,
        "max_cv": 1e10,
        "tele_mean_window": 0.0,
        "nele_mean_window": 0.0,
        "window_start_ns": 0.0,
        "window_end_ns": 0.0,
        "times_ns": [],
        "txn_series": [],
        "tele_series": [],
        "nele_series": [],
        "dens_series": [],
        "G": [0.0],
    }

    output_dir = work_dir / "flash_output"
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 优先尝试 result.h5 (引擎生成)
    result_h5 = work_dir / "result.h5"
    if not result_h5.exists():
        result_h5 = output_dir / "result.h5"

    if result_h5.exists():
        # 从引擎 result.h5 读取
        from ..io.flash_reader import build_raw_from_engine
        raw = build_raw_from_engine(
            result_h5, center_half_width_um=analysis_half_width_um,
            verbose=False,
        )
        t_arr = raw["times_s"]
        fields = raw["fields"]
        if len(t_arr) >= 2 and "tele" in fields and "ye" in fields and "dens" in fields:
            tele_arr = np.array(fields["tele"])
            nele_arr = np.array(fields["ye"]) * np.array(fields["dens"]) * NA
            txn_arr = tele_arr * nele_arr
            dens_arr = np.array(fields.get("dens", np.zeros_like(tele_arr)))
            return _complete_txn_analysis(
                t_arr, tele_arr, nele_arr, txn_arr, dens_arr,
                plots_dir, output_dir, tele_base, nele_base, result,
                analysis_half_width_um,
            )

    # 回退: 从 HDF5 plt 文件读取
    raw_data = read_flash_output_timeseries(
        output_dir, center_half_width_um=analysis_half_width_um, verbose=False,
    )
    t_arr = raw_data["times_s"]
    fields = raw_data["fields"]

    if len(t_arr) < 2:
        return result

    # 插值到统一网格
    grid_s, interp = interpolate_to_uniform_grid(t_arr, fields)
    tele_arr = interp.get("tele", np.zeros_like(grid_s))
    nele_arr = interp.get("nele",
                          interp.get("ye", np.zeros_like(grid_s))
                          * interp.get("dens", np.zeros_like(grid_s))
                          * NA)
    txn_arr = tele_arr * nele_arr
    dens_arr = interp.get("dens", np.zeros_like(grid_s))

    return _complete_txn_analysis(
        grid_s, tele_arr, nele_arr, txn_arr, dens_arr,
        plots_dir, output_dir, tele_base, nele_base, result,
        analysis_half_width_um,
    )


def _complete_txn_analysis(
    grid_s: np.ndarray,
    tele_arr: np.ndarray,
    nele_arr: np.ndarray,
    txn_arr: np.ndarray,
    dens_arr: np.ndarray,
    plots_dir: Path,
    output_dir: Path,
    tele_base: float,
    nele_base: float,
    default_result: Dict[str, Any],
    analysis_half_width_um: float = 1.0,
) -> Dict[str, Any]:
    """TXN 分析共享逻辑: 滑动窗口 → 绘图 → 保存。"""
    # 滑动窗口
    window_result = sliding_window_txn(
        grid_s, txn_arr, tele_arr, nele_arr,
        tele_base=tele_base, nele_base=nele_base,
    )

    tele_mean_w = window_result["tele_mean_window"]
    nele_mean_w = window_result["nele_mean_window"]
    tele_norm = tele_mean_w / tele_base if tele_base > 0 else 0.0
    nele_norm = nele_mean_w / nele_base if nele_base > 0 else 0.0

    # 软约束惩罚
    tele_defect = max(0.0, tele_base - tele_mean_w) / tele_base
    nele_defect = max(0.0, nele_base - nele_mean_w) / nele_base
    G_penalty = float(np.sqrt(tele_defect**2 + nele_defect**2))

    # 保存数据
    fields = {
        "tele_K": tele_arr, "nele_cm3": nele_arr,
        "txn": txn_arr, "dens_gcm3": dens_arr,
    }
    save_analysis_data(plots_dir, "analysis", grid_s, fields, {})

    # 绘图
    plot_prefix = str(plots_dir / "analysis")
    plot_paths = plot_time_series(
        grid_s, txn_arr, tele_arr, nele_arr, window_result, plot_prefix,
        dens_series=dens_arr,
    )

    nele_avg = float(np.mean(nele_arr))
    tele_avg = float(np.mean(tele_arr))

    result = {
        "txn": window_result["txn_effective"],
        "txn_raw": window_result["txn_raw"],
        "tele_norm": tele_norm,
        "nele_norm": nele_norm,
        "tele_cv": window_result["tele_cv"],
        "nele_cv": window_result["nele_cv"],
        "max_cv": window_result["max_cv"],
        "tele_mean_window": tele_mean_w,
        "nele_mean_window": nele_mean_w,
        "nele_avg": nele_avg,
        "tele_avg": tele_avg,
        "window_start_ns": window_result["best_start_ns"],
        "window_end_ns": window_result["best_end_ns"],
        "times_ns": (grid_s * 1e9).tolist(),
        "txn_series": txn_arr.tolist(),
        "tele_series": tele_arr.tolist(),
        "nele_series": nele_arr.tolist(),
        "dens_series": dens_arr.tolist(),
        "G": [G_penalty],
        "plots": plot_paths,
        "extraction_half_width_um": analysis_half_width_um,
    }

    # 保存 JSON
    from ..io.result_saver import save_analysis_json
    save_analysis_json(output_dir / "analysis_result.json", result)

    return result
