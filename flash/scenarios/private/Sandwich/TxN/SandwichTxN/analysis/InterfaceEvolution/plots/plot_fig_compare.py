"""plot_fig_compare — 参考数据 (fig_data/fig 数字化 csv) vs 当前 FLASH run 000002 对比图.

三个物理量: nele / tele / rho(=dens*targ, Si 区平均)。
参考 csv 为 WebPlotDigitizer 数字化文献数据 (无表头: 时间 ns, 数值);
FLASH 数据取 data/si_history.csv 的 nele_mean / tele_eV_mean / dens_targ_mean。
输出: figures/fig_compare_nele_tele_rho.png
风格: 全英文, Times New Roman, 字号 >= 18 pt。
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
FIGS = ROOT / "figures"
FIG_SRC = ROOT / "fig_data" / "fig"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 18,
    "axes.labelsize": 19,
    "axes.titlesize": 19,
    "xtick.labelsize": 17,
    "ytick.labelsize": 17,
    "legend.fontsize": 15,
    "lines.linewidth": 2.2,
    "figure.dpi": 150,
})


def load_ref_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """无表头数字化 csv: 时间 ns, 数值."""
    arr = np.loadtxt(path, delimiter=",")
    return arr[:, 0], arr[:, 1]


def load_flash(path: Path, key: str) -> tuple[np.ndarray, np.ndarray]:
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    t = np.array([float(r["time_ns"]) for r in rows])
    v = np.array([float(r[key]) if r.get(key, "") not in ("", "nan")
                  else np.nan for r in rows])
    m = np.isfinite(v)
    return t[m], v[m]


PANELS = [
    ("nele_vs_time.csv", "nele_mean",
     r"$n_e$  (cm$^{-3}$)", True),
    ("tele_vs_time.csv", "tele_eV_mean",
     r"$T_e$  (eV)", False),
    ("rho_vs_time.csv", "dens_targ_mean",
     r"$\rho_{\rm Si}$ = dens$\cdot$targ  (g cm$^{-3}$)", False),
]


def main():
    FIGS.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(21, 6.6))

    for ax, (fname, key, ylabel, log10) in zip(axes, PANELS):
        tr, vr = load_ref_csv(FIG_SRC / fname)
        tf, vf = load_flash(DATA / "si_history.csv", key)
        ax.plot(tr, vr, "o", ms=4.5, mfc="none", mec="#C0392B", mew=1.4,
                alpha=0.75, label="Reference (digitized csv)",
                zorder=2)
        ax.plot(tf, vf, "-", color="#1F4E79",
                label="FLASH run 000002 (Si-region mean)", zorder=3)
        if log10:
            ax.set_yscale("log")
        ax.set_xlabel("Time  t  (ns)")
        ax.set_ylabel(ylabel)
        ax.set_xlim(0, 2.0)
        ax.grid(alpha=0.3)
        ax.legend(framealpha=0.9, loc="best")

    fig.suptitle(
        "Si-region averaged quantities: reference csv vs FLASH run 000002",
        fontsize=21)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = FIGS / "fig_compare_nele_tele_rho.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"[fig_compare] OK  {out.relative_to(ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
