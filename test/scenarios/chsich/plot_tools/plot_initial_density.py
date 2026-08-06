"""
plot_initial_density.py — 从 .par 文件绘制初始密度分布图 (双击可执行)

读取 .par 中的 sim_rhoPoly / sim_polyHeight / sim_rhoTarg / sim_targHeight 等参数,
生成双面板 initial_density.png (全范围 + 中心 ±1um 放大, 含 Si 标注)。

用法:
  python plot_initial_density.py                    # 自动查找最新 .par
  python plot_initial_density.py --par /path/to/file.par
  python plot_initial_density.py --save output.png
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


def plot_initial_density_from_par(
    par_path: str | Path,
    save_path: str | Path = "initial_density.png",
    zoom_um: float = 3.0,
    dpi: int = 150,
) -> Path:
    """从 .par 文件读取参数, 绘制初始密度分布图。

    Args:
        par_path: .par 文件路径
        save_path: PNG 保存路径
        zoom_um: 中心放大半宽 (um)
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

    xmin = float(p.get("xmin", -0.045))
    xmax = float(p.get("xmax", 0.045))
    half = (xmax - xmin) / 2
    rho_c = float(p.get("sim_rhoCham", 1e-6))
    rho_t = float(p.get("sim_rhoTarg", 2.33))
    rho_p = float(p.get("sim_rhoPoly", 0.08))
    targ_h = float(p.get("sim_targHeight", 2e-5))    # 半厚 cm
    poly_h = float(p.get("sim_polyHeight", 4e-4))     # 半厚 cm
    tele_cham = float(p.get("sim_teleCham", 3500.0))

    targ_h_um = targ_h * 1e4
    poly_h_um = poly_h * 1e4

    # ── 全范围密度 ──
    n = 2000
    x = np.linspace(-half, half, n)
    dens = np.full_like(x, rho_c)
    dens[np.abs(x) <= targ_h] = rho_t
    m_poly = (np.abs(x) > targ_h) & (np.abs(x) <= poly_h)
    dens[m_poly] = rho_p

    fig, (ax_full, ax_zoom) = plt.subplots(2, 1, figsize=(14, 10), sharey=False)

    # ── 上: 全范围 ──
    ax_full.plot(x * 1e4, dens, "k-", lw=2.5)
    ax_full.axvspan(-targ_h * 1e4, targ_h * 1e4, alpha=0.15, color="orange", label="Target")
    ax_full.axvspan(-poly_h * 1e4, poly_h * 1e4, alpha=0.10, color="green",
                     label=f"CH foam ({poly_h_um*2:.0f} um)")
    ax_full.set_ylabel("Density (g/cm^3)")
    ax_full.set_title("Initial Density Distribution (He-CH-Si-CH-He)", fontweight="bold")
    ax_full.legend()
    ax_full.set_xlim(-half * 1e4, half * 1e4)
    ax_full.set_ylim(0, max(dens) * 1.15)
    ax_full.grid(True, alpha=0.3)
    ax_full.tick_params(labelsize=18)
    ax_full.annotate(f"Si {rho_t:.2f} g/cm³\n({targ_h_um:.2f} μm)",
                     xy=(0, rho_t), xytext=(half * 0.3 * 1e4, rho_t * 1.05), color="orange", fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color="orange", lw=1.5))

    # ── 下: 中心放大 ±zoom_um ──
    nz = 2000
    xz = np.linspace(-zoom_um * 1e-4, zoom_um * 1e-4, nz)
    dens_z = np.full_like(xz, rho_c)
    dens_z[np.abs(xz) <= targ_h] = rho_t
    m_poly_z = (np.abs(xz) > targ_h) & (np.abs(xz) <= poly_h)
    dens_z[m_poly_z] = rho_p

    ax_zoom.plot(xz * 1e4, dens_z, "k-", lw=2.5)
    si_hm = targ_h * 1e4
    ax_zoom.axvspan(-si_hm, si_hm, alpha=0.30, color="orange")
    ax_zoom.axvline(x=0, color="orange", ls="--", alpha=0.7, lw=2)
    ax_zoom.axhline(y=rho_t, xmin=0.45, xmax=0.55, color="orange", ls=":", alpha=0.6, lw=2)
    ax_zoom.text(0, rho_t * 0.7, f"Si {rho_t:.2f}", color="orange", fontweight="bold",
                  ha="center", va="center",
                  bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                            edgecolor="orange", alpha=0.9))
    if poly_h > targ_h:
        phm = min(poly_h * 1e4, zoom_um)
        ax_zoom.axvspan(-phm, phm, alpha=0.08, color="green")
        ax_zoom.axhline(y=rho_p, xmin=0.1, xmax=0.9, color="green", ls=":", alpha=0.5, lw=1.5)
        ax_zoom.text(si_hm + 0.3, rho_p * 1.2, f"CH {rho_p:.2f}", color="green", fontweight="bold")

    ax_zoom.set_xlabel("x (μm)")
    ax_zoom.set_ylabel("Density (g/cm^3)")
    ax_zoom.set_title(f"Center ±{zoom_um:.0f} μm Zoom — Si layer visible", fontweight="bold")
    ax_zoom.set_xlim(-zoom_um, zoom_um)
    ax_zoom.set_ylim(0, max(dens_z) * 1.25)
    ax_zoom.grid(True, alpha=0.3)
    ax_zoom.tick_params(labelsize=14)

    plt.tight_layout()
    fig.savefig(str(save_path), dpi=dpi)
    plt.close(fig)

    sp = Path(save_path)
    print(f"  → {sp.resolve()}")
    print(f"  CH: {poly_h_um*2:.0f} um total, {rho_p:.3f} g/cm³")
    print(f"  Si: {targ_h_um:.2f} um half, {rho_t:.2f} g/cm³")
    print(f"  He: {rho_c:.1e} g/cm³, Te init: {tele_cham:.0f} K")
    return sp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 .par 绘制初始密度分布")
    parser.add_argument("--par", type=str, default=None,
                        help=".par 文件路径 (默认自动查找)")
    parser.add_argument("--save", type=str, default="initial_density.png",
                        help="PNG 保存路径")
    parser.add_argument("--zoom", type=float, default=3.0,
                        help="中心放大半宽 (um), 默认 3.0")
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

    plot_initial_density_from_par(args.par, args.save, args.zoom, args.dpi)
