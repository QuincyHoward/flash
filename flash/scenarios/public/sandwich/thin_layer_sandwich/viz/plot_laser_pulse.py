"""
plot_laser_pulse.py — 激光脉冲预诊断图 (含 CH/Si 结构参数标注)

从参数字典生成 laser_pulse.png。无需 FLASH 仿真，直接由 .par 参数绘制。
可作为独立脚本运行或手动精修。

用法:
  python plot_laser_pulse.py --rho-poly 0.1 --poly-height 90e-4 --rho-targ 2.33 --targ-height 0.15e-4 --power 3e14

依赖:
  - flash 包 (thin_layer_sandwich 模块)
  - matplotlib, numpy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def plot_laser_pulse(
    save_path: str | Path,
    *,
    sim_rhoPoly: float = 0.08,
    sim_polyHeight: float = 4e-4,
    sim_rhoTarg: float = 2.33,
    sim_targHeight: float = 2e-5,
    sim_rhoCham: float = 1e-6,
    sim_teleCham: float | None = 3500.0,
    laser_times_s: list[float] | None = None,
    laser_powers: list[float] | None = None,
    title: str = "Laser Pulse & Target Configuration",
    dpi: int = 150,
) -> Path:
    """绘制激光脉冲图 (含 CH/Si 结构参数标注)。

    Args:
        save_path: PNG 保存路径
        sim_rhoPoly: CH 密度 (g/cm³)
        sim_polyHeight: CH 半厚 (cm)
        sim_rhoTarg: Si/Al 密度 (g/cm³)
        sim_targHeight: Si/Al 半厚 (cm)
        sim_rhoCham: He 填充密度 (g/cm³)
        sim_teleCham: 初始电子温度 (K)
        laser_times_s: 激光时间点 (s)
        laser_powers: 激光功率 (W/cm²)
        title: 图标题
        dpi: 输出 DPI
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if laser_times_s is None:
        laser_times_s = [0, 0.17e-9, 1.0e-9, 1.17e-9]
    if laser_powers is None:
        laser_powers = [0, 3e14, 3e14, 0]

    poly_h_um = sim_polyHeight * 1e4       # 半厚 (um)
    targ_h_um = sim_targHeight * 1e4       # 半厚 (um)

    fig, ax = plt.subplots(figsize=(14, 7))

    # 脉冲波形
    ax.plot(np.array(laser_times_s) * 1e12, np.array(laser_powers) / 1e14,
            "r-", lw=3.0)
    ax.set_xlabel("Time (ps)", fontsize=20)
    ax.set_ylabel("Power (×10¹⁴ W/cm²)", fontsize=20)
    ax.set_title(title, fontsize=22, fontweight="bold")
    ax.tick_params(labelsize=16)
    ax.grid(True, alpha=0.25, linestyle="--")

    # 结构参数标注
    annot_lines = [
        f"  CH foam: {poly_h_um:.1f} μm, {sim_rhoPoly:.3f} g/cm³",
        f"  Target:  {targ_h_um:.2f} μm, {sim_rhoTarg:.2f} g/cm³",
    ]
    if sim_teleCham is not None:
        annot_lines.append(f"  Te init:  {sim_teleCham:.0f} K")

    ax.text(0.97, 0.97, "\n".join(annot_lines),
            transform=ax.transAxes,
            fontsize=15, color="#333333",
            verticalalignment="top", horizontalalignment="right",
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="gray", alpha=0.85))

    fig.savefig(str(save_path), dpi=dpi)
    plt.close(fig)

    sp = Path(save_path)
    print(f"  → {sp.resolve()}")
    print(f"  CH: {poly_h_um:.1f} μm, {sim_rhoPoly:.3f} g/cm³")
    print(f"  Si: {targ_h_um:.2f} μm, {sim_rhoTarg:.2f} g/cm³")
    print(f"  Peak: {max(laser_powers)/1e14:.2f}×10¹⁴ W/cm²")
    return sp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="绘制激光脉冲预诊断图 (含结构参数)")
    parser.add_argument("--save", default="laser_pulse.png",
                        help="保存路径")
    parser.add_argument("--rho-poly", type=float, default=0.08,
                        help="CH 密度 (g/cm³)")
    parser.add_argument("--poly-height", type=float, default=4e-4,
                        help="CH 半厚 (cm), 如 90e-4 = 90 μm")
    parser.add_argument("--rho-targ", type=float, default=2.33,
                        help="Si 密度 (g/cm³)")
    parser.add_argument("--targ-height", type=float, default=2e-5,
                        help="Si 半厚 (cm), 如 0.15e-4 = 0.15 μm")
    parser.add_argument("--rho-cham", type=float, default=1e-6,
                        help="He 密度 (g/cm³)")
    parser.add_argument("--te-init", type=float, default=3500.0,
                        help="初始电子温度 (K)")
    parser.add_argument("--peak-power", type=float, default=3e14,
                        help="峰值功率 (W/cm²)")
    parser.add_argument("--pulse-start", type=float, default=0.17e-9,
                        help="脉冲起始时间 (s)")
    parser.add_argument("--pulse-end", type=float, default=1.0e-9,
                        help="脉冲结束时间 (s)")
    parser.add_argument("--dpi", type=int, default=150,
                        help="输出 DPI")
    args = parser.parse_args()

    t_on = args.pulse_start
    t_off = args.pulse_end
    # 方波: 0 → 峰值 → 峰值 → 0
    laser_t = [0, t_on, t_off, t_off + 0.17e-9]
    laser_p = [0, args.peak_power, args.peak_power, 0]

    plot_laser_pulse(
        args.save,
        sim_rhoPoly=args.rho_poly,
        sim_polyHeight=args.poly_height,
        sim_rhoTarg=args.rho_targ,
        sim_targHeight=args.targ_height,
        sim_rhoCham=args.rho_cham,
        sim_teleCham=args.te_init,
        laser_times_s=laser_t,
        laser_powers=laser_p,
        dpi=args.dpi,
    )
