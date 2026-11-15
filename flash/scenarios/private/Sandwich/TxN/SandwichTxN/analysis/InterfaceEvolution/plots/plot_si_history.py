#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plot_si_history — 中心 Si 区域平均物理量与区域尺寸随时间变化.

输入: data/si_history.csv (extract_interfaces.py 产物)
      Si 区域定义: dens·targ 半高区段 [si_left, si_right] 内 targ≥0.5 格元的算术平均
输出: figures/si_history.png  3×3: size / ρ_Si(dens·targ) / n_e / n_i / T_e /
      p / p_e / Γ_i / Θ_e — 全部线性坐标

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

PANELS = [
    ("size_um",        "Si region size  (μm)"),
    ("dens_targ_mean", r"mean $\rho_{\rm Si}$  = dens$\cdot$targ  (g cm$^{-3}$)"),
    ("nele_mean",      r"mean $n_e$  (cm$^{-3}$)"),
    ("nion_mean",      r"mean $n_i$  (cm$^{-3}$)"),
    ("tele_eV_mean",   r"mean $T_e$  (eV)"),
    ("pres_Mbar_mean", r"mean $p$  (Mbar)"),
    ("pele_Mbar_mean", r"mean $p_e$  (Mbar)"),
    ("gamma_mean",     r"mean $\Gamma_i$"),
    ("theta_mean",     r"mean $\Theta_e$"),
]

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 18,
    "axes.labelsize": 18,
    "axes.titlesize": 18,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "lines.linewidth": 2.0,
    "figure.dpi": 150,
})


def main():
    with open(DATA / "si_history.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    col = lambda k: np.array([float(r[k]) if r.get(k, "") not in ("", "nan")
                              else np.nan for r in rows])
    t = col("time_ns")
    FIGS.mkdir(exist_ok=True)

    fig, axes = plt.subplots(3, 3, figsize=(17, 13), sharex=True)
    for ax, (key, label) in zip(axes.ravel(), PANELS):
        y = col(key)
        m = np.isfinite(y)
        ax.plot(t[m], y[m], color="tab:blue")
        ax.set_ylabel(label)          # 全部线性坐标
        ax.grid(alpha=0.3)
        ax.set_title(key, fontsize=16)
    for ax in axes[-1]:
        ax.set_xlabel("Time  t  (ns)")
    fig.suptitle("Si-region averaged quantities vs time (run 000002, linear axes)",
                 fontsize=20)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGS / "si_history.png", dpi=150)
    plt.close(fig)
    print("[si_history] OK  figures/si_history.png")


if __name__ == "__main__":
    main()
