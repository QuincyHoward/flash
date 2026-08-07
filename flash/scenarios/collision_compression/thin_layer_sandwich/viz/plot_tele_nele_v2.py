"""Tele(eV) + Nele 双轴精修时序图 — 从 result.h5 绘制。

替代历史丢失的 ``viz/plot_tele_nele_v2.py``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np


def plot_tele_nele_v2(
    h5_path: str | Path,
    save_path: str | Path = "analysis_time_series.png",
    *,
    center_half_width_um: float = 1.0,
    window_start_ns: Optional[float] = None,
    window_end_ns: Optional[float] = None,
    xlim_ns: Optional[Tuple[float, float]] = None,
    ylim_tele_eV: Optional[Tuple[float, float]] = None,
    ylim_nele: Optional[Tuple[float, float]] = None,
    tele_base_K: float = 1.2e6,
    nele_base: float = 1.4e23,
    dpi: int = 300,
) -> Path:
    """绘制 CH 中心区域 Tele(eV) + Nele(cm⁻³) 时序图。

    Args:
        h5_path: 引擎 result.h5 路径
        save_path: PNG 保存路径
        center_half_width_um: 中心区域半宽 (um)
        window_start_ns / window_end_ns: 高亮窗口 (ns), None=自动全范围
        xlim_ns: 横轴范围 (ns)
        ylim_tele_eV: Tele 左轴范围 (eV)
        ylim_nele: Nele 右轴范围 (cm⁻³)
        tele_base_K: Tele 基线 (K) — 用于以 eV 显示时换算
        nele_base: Nele 基线 (cm⁻³) — 未直接输出 ye 时估算
        dpi: 输出 DPI

    Returns:
        save_path (Path)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import h5py

    h5_path = Path(h5_path)
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(str(h5_path), "r") as f:
        t = np.asarray(f["t"][:], dtype=np.float64)
        x = np.asarray(f["x"][:], dtype=np.float64)
        tele = np.asarray(f["tele"][()], dtype=np.float64) if "tele" in f else None
        ye = np.asarray(f["ye"][()], dtype=np.float64) if "ye" in f else None
        dens = np.asarray(f["dens"][()], dtype=np.float64) if "dens" in f else None

    if tele is None:
        raise RuntimeError("result.h5 缺少 tele 字段")

    x_um = x * 1e4
    mask = np.abs(x_um) <= center_half_width_um
    idx = np.where(mask)[0]
    if len(idx) == 0:
        idx = np.array([len(x) // 2])

    t_ns = t * 1e9
    tele_center = tele[:, idx].mean(axis=1)
    tele_eV = tele_center / 11604.5  # K → eV

    if ye is not None and dens is not None:
        ye_center = ye[:, idx].mean(axis=1)
        dens_center = dens[:, idx].mean(axis=1)
        nele = ye_center * dens_center * 6.02214076e23  # cm^-3
    else:
        # 无 ye: 用基线估算
        nele = np.full_like(tele_center, nele_base)

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(t_ns, tele_eV, "r-", lw=2.2, label="Tele (eV)")
    ax1.set_xlabel("Time (ns)", fontweight="bold")
    ax1.set_ylabel("Tele (eV)", color="r", fontweight="bold")
    ax1.tick_params(axis="y", labelcolor="r")
    if ylim_tele_eV is not None:
        ax1.set_ylim(*ylim_tele_eV)

    ax2 = ax1.twinx()
    ax2.plot(t_ns, nele, "b-", lw=1.8, alpha=0.8, label="Nele (cm⁻³)")
    ax2.set_ylabel("Nele (cm⁻³)", color="b", fontweight="bold")
    ax2.tick_params(axis="y", labelcolor="b")
    if ylim_nele is not None:
        ax2.set_ylim(*ylim_nele)

    if window_start_ns is not None and window_end_ns is not None:
        ax1.axvspan(window_start_ns, window_end_ns, alpha=0.15, color="orange",
                    label=f"window [{window_start_ns:.2f}, {window_end_ns:.2f}] ns")
    if xlim_ns is not None:
        ax1.set_xlim(*xlim_ns)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=10)
    ax1.set_title("Tele (eV) & Nele (cm⁻³) — Center", fontweight="bold")
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(str(save_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return save_path
