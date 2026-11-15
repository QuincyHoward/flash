#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plot_interfaces — 界面演化图 (x 位置 µm, y 时间 ns), Si 区域仅画边界线.

输入: data/interfaces.csv + data/spacetime.npz
输出: figures/interface_evolution_full.png (±100 µm)
      figures/interface_evolution_zoom.png (±20 µm)

风格: 全英文, Times New Roman (回退 Liberation/DejaVu Serif), 字号 >= 18 pt。
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent          # plots/
ROOT = HERE.parent                              # InterfaceEvolution/
DATA = ROOT / "data"
FIGS = ROOT / "figures"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 18,
    "axes.labelsize": 20,
    "axes.titlesize": 20,
    "legend.fontsize": 15,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
    "lines.linewidth": 1.8,
    "figure.dpi": 150,
})

FOAM_EDGE = 51.46     # CH 泡沫外边界初始位置 (µm)
SI_INIT = 0.46        # Si 初始半厚 (µm)


def load():
    with open(DATA / "interfaces.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    col = lambda r, k: float(r[k]) if r.get(k, "") not in ("", "nan") else np.nan
    t = np.array([col(r, "time_ns") for r in rows])
    d = {k: np.array([col(r, k) for r in rows]) for k in
         ("xc_left_um", "xc_right_um", "xa_left_um", "xa_right_um",
          "xs_left_um", "xs_right_um", "si_left_um", "si_right_um")}
    bg = np.load(DATA / "spacetime.npz")
    return t, d, bg


def jump_mask(x, max_step_um=15.0):
    """相邻有效点位移 > max_step → 置 NaN, 避免跨跳变连线伪影."""
    xm = x.copy()
    idx = np.flatnonzero(np.isfinite(xm))
    if idx.size < 2:
        return xm
    for a, b in zip(idx[:-1], idx[1:]):
        if abs(xm[b] - xm[a]) > max_step_um:
            xm[b] = np.nan
    return xm


def plot_panel(ax, t, d, bg, xlim, title):
    xg, tg = bg["x_um"], bg["t_ns"]
    logd = np.log10(np.maximum(bg["dens_gcc"], 1e-8))
    X, T = np.meshgrid(xg, tg)                     # 真实逐帧时间 (pcolormesh 纪律)
    pc = ax.pcolormesh(X, T, logd, cmap="viridis", vmin=-8, vmax=1.0,
                       shading="nearest", rasterized=True)
    cbar = plt.colorbar(pc, ax=ax, pad=0.01)
    cbar.set_label(r"log$_{10}$ $\rho$  (g cm$^{-3}$)", fontsize=18)
    cbar.ax.tick_params(labelsize=16)

    for xb in (-FOAM_EDGE, FOAM_EDGE, -SI_INIT, SI_INIT):
        if xlim[0] <= xb <= xlim[1]:
            ax.axvline(xb, color="white", ls=":", lw=1.0, alpha=0.6)

    # Si 区域: 仅边界线 (无阴影)
    ax.plot(jump_mask(d["si_left_um"]), t, "-", color="crimson", lw=2.4,
            label="Si region edges (dens·targ half-max)")
    ax.plot(jump_mask(d["si_right_um"]), t, "-", color="crimson", lw=2.4)

    ax.plot(jump_mask(d["xa_left_um"]), t, "-", color="orange",
            label=r"ablation front $x_a$")
    ax.plot(jump_mask(d["xa_right_um"]), t, "-", color="orange")
    ax.plot(jump_mask(d["xc_left_um"]), t, "--", color="deepskyblue",
            label=r"critical surface $x_c$")
    ax.plot(jump_mask(d["xc_right_um"]), t, "--", color="deepskyblue")
    ax.plot(d["xs_left_um"], t, ":", color="lime", lw=2.8,
            label=r"shock front $x_s$ (shok, filtered)")
    ax.plot(d["xs_right_um"], t, ":", color="lime", lw=2.8)

    ax.set_xlim(*xlim)
    ax.set_ylim(tg.min(), tg.max())
    ax.set_xlabel("Position  x  (μm)")
    ax.set_ylabel("Time  t  (ns)")
    ax.set_title(title)
    ax.legend(loc="upper left", framealpha=0.85)


def main():
    t, d, bg = load()
    FIGS.mkdir(exist_ok=True)
    print(f"[plot] frames={len(t)}  t=[{t.min():.3f},{t.max():.3f}] ns")

    fig, ax = plt.subplots(figsize=(12, 8))
    plot_panel(ax, t, d, bg, (-100, 100),
               "SandwichTxN interface evolution (run 000002)")
    fig.tight_layout()
    fig.savefig(FIGS / "interface_evolution_full.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 8))
    plot_panel(ax, t, d, bg, (-20, 20),
               "SandwichTxN interface evolution — target region")
    fig.tight_layout()
    fig.savefig(FIGS / "interface_evolution_zoom.png", dpi=150)
    plt.close(fig)
    print("[plot] OK  figures/interface_evolution_full.png / _zoom.png")


if __name__ == "__main__":
    main()
