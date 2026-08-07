"""T×N 时序图 — Tele*Nele 时间演化 + 滑动窗口标注。

替代历史丢失的 ``analysis/txn.py``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


def plot_time_series(
    grid_s: np.ndarray,
    txn_arr: np.ndarray,
    tele_arr: Optional[np.ndarray] = None,
    nele_arr: Optional[np.ndarray] = None,
    txn_window: Optional[Dict[str, Any]] = None,
    save_prefix: str | Path = "analysis_txn",
    dens_series: Optional[np.ndarray] = None,
    dpi: int = 300,
) -> Dict[str, Path]:
    """绘制 T×N (Tele×Nele) 时序图, 标注最佳窗口。

    Args:
        grid_s: 时间轴 (s)
        txn_arr: T×N 序列 (Nt,) 或 (Nt, Nx) (取中心列)
        tele_arr / nele_arr: 可选, 叠加显示 (中心列)
        txn_window: sliding_window_txn 的返回 (用于标注窗口)
        save_prefix: 输出前缀 (将生成 <prefix>.png 等)
        dens_series: 可选, 中心密度序列 (叠加右轴)
        dpi: 输出 DPI

    Returns:
        {"txn": Path, "txn_window": Path} — 生成的图片路径
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def _center1d(a):
        a = np.asarray(a, dtype=np.float64)
        if a.ndim == 2:
            return a[:, a.shape[1] // 2]
        return a

    grid_s = np.asarray(grid_s, dtype=np.float64)
    t_ns = grid_s * 1e9
    txn = _center1d(txn_arr)
    tele = _center1d(tele_arr) if tele_arr is not None else None
    nele = _center1d(nele_arr) if nele_arr is not None else None
    dens = _center1d(dens_series) if dens_series is not None else None

    save_prefix = Path(save_prefix)
    save_prefix.parent.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Path] = {}

    # ── 图 1: T×N 主图 ──
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(t_ns, txn, "b-", lw=2.2, label="T×N (Tele×Nele)")
    ax1.set_xlabel("Time (ns)", fontweight="bold")
    ax1.set_ylabel("T×N (arb. units)", color="b", fontweight="bold")
    ax1.tick_params(axis="y", labelcolor="b")

    if txn_window and txn_window.get("best_start_ns") is not None:
        s, e = txn_window["best_start_ns"], txn_window["best_end_ns"]
        ax1.axvspan(s, e, alpha=0.18, color="orange",
                    label=f"window [{s:.2f}, {e:.2f}] ns")
        ax1.axvline(txn_window.get("peak_ns", s), color="red", ls="--", lw=1.5,
                    alpha=0.7, label=f"peak {txn_window.get('peak_ns', 0):.2f} ns")

    if tele is not None:
        ax2 = ax1.twinx()
        ax2.plot(t_ns, tele, "g-", lw=1.5, alpha=0.7, label="Tele (K)")
        ax2.set_ylabel("Tele (K)", color="g", fontweight="bold")
        ax2.tick_params(axis="y", labelcolor="g")
        if nele is not None:
            ax3 = ax1.twinx()
            ax3.spines["right"].set_position(("outward", 60))
            ax3.plot(t_ns, nele, "m-", lw=1.2, alpha=0.6, label="Nele (cm⁻³)")
            ax3.set_ylabel("Nele (cm⁻³)", color="m", fontweight="bold")
            ax3.tick_params(axis="y", labelcolor="m")

    if dens is not None:
        axd = ax1.twinx()
        axd.spines["right"].set_position(("outward", 120))
        axd.plot(t_ns, dens, "k--", lw=1.2, alpha=0.6, label="Density")
        axd.set_ylabel("Density (g/cm³)", color="k", fontweight="bold")

    ax1.set_title("T×N Time Series (Center)", fontweight="bold")
    lines1, labels1 = ax1.get_legend_handles_labels()
    ax1.legend(lines1, labels1, loc="upper left", fontsize=10)
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    p1 = save_prefix.parent / f"{save_prefix.stem}.png"
    fig.savefig(str(p1), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    results["txn"] = p1

    return results
