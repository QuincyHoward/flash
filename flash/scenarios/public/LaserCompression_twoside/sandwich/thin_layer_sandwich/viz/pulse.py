"""
pulse — 激光脉冲可视化

提供脉冲形状绘制功能, 支持原始/整形对比、最大上升斜率标注。
对应 chsich02/pulse_shaping.py 中 plot_pulse 的功能。
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

# 在模块级别设置 Agg 后端
import matplotlib as _mpl
_mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def plot_pulse(
    times_ns: np.ndarray,
    powers: np.ndarray,
    save_path: str,
    title: str = "Laser Pulse Shape",
    *,
    raw_times: Optional[np.ndarray] = None,
    raw_powers: Optional[np.ndarray] = None,
    i_max: float = 5e14,
    k_max_slope: float = 5e14 / 100e-12,
    e_max: float = 5e14 * 1e-9,
    annotations: Optional[dict] = None,
) -> None:
    """绘制脉冲形状, 支持原始/整形对比和参数标注。"""
    plt.close("all")

    k_max_ns = k_max_slope * 1e-9

    plt.rcParams.update({
        "font.size": 10, "axes.labelsize": 11,
        "axes.titlesize": 12,
    })

    fig, (ax_pulse, ax_slope, ax_energy) = plt.subplots(
        3, 1, figsize=(10, 8), sharex=True,
        gridspec_kw={"height_ratios": [2, 1, 1]},
    )

    # ── 子图1: 脉冲波形 ──
    ax = ax_pulse
    has_raw = raw_times is not None and raw_powers is not None

    if has_raw:
        ax.plot(raw_times * 1e3, raw_powers / 1e14, color="gray",
                ls="--", lw=1.0, alpha=0.7, label="Raw (Gaussian)")

    ax.plot(times_ns * 1e3, powers / 1e14, "b-", lw=2.0,
            label="Shaped (constrained)")

    ax.axhline(y=i_max / 1e14, color="red", ls="--", lw=1.0, alpha=0.7,
               label=f"I_max={i_max/1e14:.1f}e14 W/cm²")

    # 上升斜率标注
    if has_raw:
        dt = np.diff(raw_times)
        slopes = np.diff(raw_powers) / dt
        rising = slopes > 0
        if np.any(rising):
            idx = int(np.argmax(slopes * rising))
            max_t_ns = raw_times[idx]
            ax.plot(max_t_ns * 1e3, raw_powers[idx] / 1e14, "r*", markersize=14,
                    zorder=10, label=f"max slope @ {max_t_ns*1e3:.1f} ps")
            ax.annotate(
                f"k_raw={slopes[idx]/1e14:.2f}e14/ps\n"
                f"(×{slopes[idx]/k_max_ns:.1f} k_max)",
                xy=(max_t_ns * 1e3, raw_powers[idx] / 1e14),
                xytext=(max_t_ns * 1e3 + 30, raw_powers[idx] / 1e14 + 2.0),
                fontsize=9, color="red",
                arrowprops=dict(arrowstyle="->", color="red", lw=1.2),
            )

    # k_max 斜率参考线
    t_line_ps = np.array([0, 50])
    p_line = k_max_ns * (t_line_ps / 1e3)
    ax.plot(t_line_ps, p_line / 1e14, "orange", lw=1.5, ls=":",
            label="k_max slope line")

    # 参数标注文本框 (CH厚度, CH密度, Si厚度等)
    if annotations:
        annotation_text = "\n".join(
            [f"{k}: {v}" for k, v in annotations.items()]
        )
        # 移除 bbox 参数 (Windows FT2Font bug: bbox 触发 set_transform 崩溃)
        ax.text(
            0.98, 0.98, annotation_text,
            transform=ax.transAxes,
            fontsize=9, verticalalignment="top", horizontalalignment="right",
            color="black", fontweight="bold",
        )

    ax.set_ylabel("Power (e14 W/cm²)")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="upper left")

    # ── 子图2: 斜率 ──
    ax = ax_slope

    def _safe_slopes(tt, pp):
        return np.diff(pp) / np.diff(tt)

    if has_raw:
        rs = _safe_slopes(raw_times, raw_powers) / k_max_ns
        ax.plot(raw_times[:-1] * 1e3, rs, color="gray", ls="--",
                lw=0.8, alpha=0.6, label="Raw slope (×k_max)")

    ss = _safe_slopes(times_ns, powers) / k_max_ns
    ax.plot(times_ns[:-1] * 1e3, ss, "b-", lw=1.2, label="Shaped slope (×k_max)")
    ax.axhline(y=1.0, color="red", ls="--", lw=1.0, alpha=0.6, label="k_max limit")
    ax.axhline(y=0.0, color="gray", ls=":", lw=0.5)

    ax.set_ylabel("Slope (×k_max)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_ylim(-0.2, max(2.0, float(np.max(ss) * 1.2)) if len(ss) > 0 else 2.0)

    # ── 子图3: 累积能量 ──
    ax = ax_energy
    dt_t = np.diff(times_ns)
    ce = np.concatenate([[0.0], np.cumsum(powers[:-1] * dt_t * 1e-9)])

    ax.plot(times_ns * 1e3, ce / 1e5, "g-", lw=1.5, label="Shaped energy")
    ax.axhline(y=e_max / 1e5, color="red", ls="--", lw=1.0, alpha=0.7,
               label=f"E_max={e_max/1e5:.1f}e5 J/cm²")

    if has_raw:
        dt_r = np.diff(raw_times)
        ce_r = np.concatenate([[0.0], np.cumsum(raw_powers[:-1] * dt_r * 1e-9)])
        ax.plot(raw_times * 1e3, ce_r / 1e5, color="gray", ls="--",
                lw=0.8, alpha=0.6, label="Raw energy")

    ax.set_xlabel("Time (ps)")
    ax.set_ylabel("Energy (e5 J/cm²)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="upper left")

    plt.tight_layout()
    fig.savefig(save_path, dpi=72, bbox_inches=None)
    plt.close(fig)


def plot_pulse_with_profile(
    times_ns: np.ndarray,
    powers: np.ndarray,
    save_path: str,
    *,
    profile_params: Optional[dict] = None,
    title: str = "Laser Pulse",
) -> None:
    """简化版脉冲绘制 (无斜率/能量子图), 带结构参数标注。

    用于预诊断场景 (laser_pulse.png), 将靶结构参数
    (CH厚度、CH密度、Si厚度等) 打印在图上。
    """
    plt.close("all")

    plt.rcParams.update({
        "font.size": 14, "axes.labelsize": 16,
        "axes.titlesize": 18, "legend.fontsize": 14,
        "lines.linewidth": 2.0,
    })

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times_ns * 1e3, np.array(powers) / 1e14, "r-", lw=2.5)
    ax.set_xlabel("Time (ps)")
    ax.set_ylabel("Power (\u00d710\u00b9\u2074 W/cm\u00b2)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    # 标注靶结构参数 (移除 bbox 避免 Windows FT2Font bug)
    if profile_params:
        text_lines = [
            f"  {k}: {v}" for k, v in profile_params.items()
        ]
        annotation_text = "\n".join(text_lines)

        ax.text(
            0.6, -0.5, annotation_text,
            transform=ax.transAxes,
            fontsize=14, color="black", fontweight="bold",
            verticalalignment="top",
            horizontalalignment="right",
        )

    plt.tight_layout()
    fig.savefig(save_path, dpi=72, bbox_inches=None)
    plt.close(fig)
