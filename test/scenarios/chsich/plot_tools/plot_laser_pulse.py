"""
plot_laser_pulse.py — 从 .par 文件绘制激光脉冲图 (双击可执行)

读取 .par 中的 ed_time / ed_power 及 sim_rhoPoly / sim_polyHeight 等参数,
生成含 CH/Si 结构参数标注的 laser_pulse.png。

用法:
  python plot_laser_pulse.py                      # 自动查找最新 .par
  python plot_laser_pulse.py --par /path/to/file.par
  python plot_laser_pulse.py --save output.png --dpi 300
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


# Bootstrap: find flash package root + scenarios path
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
_SCENARIOS_ROOT = _ROOT / "test" / "scenarios"
if _SCENARIOS_ROOT.exists() and str(_SCENARIOS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCENARIOS_ROOT))


def plot_laser_pulse_from_par(
    par_path: str | Path,
    save_path: str | Path = "laser_pulse.png",
    dpi: int = 150,
) -> Path:
    """从 .par 文件读取参数, 绘制激光脉冲图。

    Args:
        par_path: .par 文件路径
        save_path: PNG 保存路径
        dpi: 输出 DPI
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # ── PPT-friendly plot style (fonts >= 18, English only) ──
    try:
        from output_processors.plotter.plot_style import apply_plot_style
        apply_plot_style()
    except ImportError:
        pass

    from chsich.plot_tools.par_reader import read_par

    p = read_par(par_path)

    # 读取结构参数
    rho_poly = float(p.get("sim_rhoPoly", 0.08))
    poly_h = float(p.get("sim_polyHeight", 4e-4))    # cm
    rho_targ = float(p.get("sim_rhoTarg", 2.33))
    targ_h = float(p.get("sim_targHeight", 2e-5))    # cm
    tele_cham = p.get("sim_teleCham", None)

    poly_h_um = poly_h * 1e4     # 半厚 um
    targ_h_um = targ_h * 1e4     # 半厚 um

    # 读取激光脉冲
    laser_t = p.get("laser_times", [0, 0.17e-9, 1.0e-9, 1.17e-9])
    laser_pw = p.get("laser_powers", [0, 3e14, 3e14, 0])

    # 绘图
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(np.array(laser_t) * 1e12, np.array(laser_pw) / 1e14, "r-", lw=3.0)
    ax.set_xlabel("Time (ps)")
    ax.set_ylabel("Power (\u00d710\u00b9\u2074 W/cm\u00b2)")
    ax.set_title("Laser Pulse & Target Configuration", fontweight="bold")
    ax.tick_params(labelsize=16)
    ax.grid(True, alpha=0.25, linestyle="--")

    annot_lines = [
        f"  CH foam: {poly_h_um:.1f} \u00b5m, {rho_poly:.3f} g/cm\u00b3",
        f"  Target:  {targ_h_um:.2f} \u00b5m, {rho_targ:.2f} g/cm\u00b3",
    ]
    if tele_cham is not None:
        annot_lines.append(f"  Te init:  {float(tele_cham):.0f} K")

    ax.text(0.5, 0.5, "\n".join(annot_lines),
            transform=ax.transAxes, color="#333333",
            verticalalignment="top", horizontalalignment="right",
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="gray", alpha=0.85))

    fig.savefig(str(save_path), dpi=dpi)
    plt.close(fig)

    sp = Path(save_path)
    print(f"  → {sp.resolve()}")
    print(f"  CH: {poly_h_um:.1f} \u00b5m, {rho_poly:.3f} g/cm\u00b3")
    print(f"  Si: {targ_h_um:.2f} \u00b5m, {rho_targ:.2f} g/cm\u00b3")
    print(f"  Peak: {max(laser_pw)/1e14:.2f}\u00d710\u00b9\u2074 W/cm\u00b2")
    return sp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 .par 绘制激光脉冲图")
    parser.add_argument("--par", type=str, default=None,
                        help=".par 文件路径 (默认自动查找)")
    parser.add_argument("--save", type=str, default="laser_pulse.png",
                        help="PNG 保存路径")
    parser.add_argument("--dpi", type=int, default=150,
                        help="输出 DPI")
    parser.add_argument("--run-id", type=str, default=None,
                        help="指定运行 ID, 如 000002 (默认最新)")
    args = parser.parse_args()

    if args.par is None:
        from chsich.plot_tools.par_reader import find_latest_par
        runs_dir = Path(__file__).resolve().parent.parent / "run_tools" / "runs_thin_layer_sandwich_si"
        args.par = find_latest_par(runs_dir, args.run_id)
        print(f"自动查找 .par: {args.par}")

    plot_laser_pulse_from_par(args.par, args.save, args.dpi)
