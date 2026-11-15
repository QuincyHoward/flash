#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plot_maps — 物理量时空彩图 + shok 激波核查图.

输入: data/spacetime.npz (core.fields MAP_FIELDS 时空场, 真实逐帧时间)
输出: figures/spacetime_maps.png  2×4: ρ / n_e / n_i / T_e / p / p_e / Γ_i / Θ_e
      figures/map_shok.png        shok 标志时空图 + 全部候选区质心散点
                                  (人工核查用) + 筛选后 x_s / x_a 叠加

风格: 全英文, Times New Roman, 字号 >= 18 pt。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent          # plots/
ROOT = HERE.parent                              # InterfaceEvolution/
DATA = ROOT / "data"
FIGS = ROOT / "figures"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.fields import MAP_FIELDS

XMIN, XMAX = -100.0, 100.0

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 18,
    "axes.labelsize": 18,
    "axes.titlesize": 19,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "figure.dpi": 150,
})


def load_interfaces():
    with open(DATA / "interfaces.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    col = lambda r, k: float(r[k]) if r.get(k, "") not in ("", "nan") else np.nan
    d = {k: np.array([col(r, k) for r in rows]) for k in
         ("xa_left_um", "xa_right_um", "xs_left_um", "xs_right_um")}
    return d


def panel(ax, t_ns, x_um, field, label, log10=True, vmin=None, vmax=None):
    X, T = np.meshgrid(x_um, t_ns)                 # 真实逐帧时间 (pcolormesh 纪律)
    Z = np.log10(np.maximum(field, 1e-30)) if log10 else field
    Z = np.ma.masked_invalid(Z)
    if vmin is None or vmax is None:
        finite = Z.compressed()
        if finite.size:
            vmin, vmax = finite.min(), finite.max()   # 全量程 (百分位截断会饱和冷区)
    pc = ax.pcolormesh(X, T, Z, cmap="viridis", shading="nearest",
                       vmin=vmin, vmax=vmax, rasterized=True)
    cbar = plt.colorbar(pc, ax=ax, pad=0.01)
    cbar.set_label(label, fontsize=15)
    cbar.ax.tick_params(labelsize=14)
    ax.set_xlabel("x  (μm)")
    ax.set_ylabel("t  (ns)")
    ax.set_xlim(XMIN, XMAX)


def main():
    bg = np.load(DATA / "spacetime.npz")
    t_ns, x_um = bg["t_ns"], bg["x_um"]
    d = load_interfaces()
    FIGS.mkdir(exist_ok=True)
    print(f"[maps] frames={t_ns.size}  grid={x_um.size}")

    # ── 图 1: 2×4 物理量时空彩图 ──
    fig, axes = plt.subplots(2, 4, figsize=(24, 10), sharex=True, sharey=True)
    for ax, (key, label, log10) in zip(axes.ravel(), MAP_FIELDS):
        panel(ax, t_ns, x_um, bg[key], label, log10=log10)
        ax.set_title(key, fontsize=17)
    fig.suptitle("SandwichTxN spacetime maps (run 000002, log10 color scale)",
                 fontsize=20)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIGS / "spacetime_maps.png", dpi=150)
    plt.close(fig)
    print("[maps] OK  figures/spacetime_maps.png")

    # ── 图 2: shok 核查图 ──
    fig, ax = plt.subplots(figsize=(12, 8))
    panel(ax, t_ns, x_um, np.maximum(bg["shok"], 0.0),
          "shok flag (0–1)", log10=False, vmin=0.0, vmax=1.0)
    # 原始 shok>0.5 格元 (薄层标志场, pcolormesh 像素级不可见, 用散点呈现)
    st, sx = bg["shok_cells_t"], bg["shok_cells_x"]
    if st.size:
        m = (sx >= XMIN) & (sx <= XMAX)
        ax.scatter(sx[m], st[m], s=9, c="yellow", marker="s", alpha=0.9,
                   label="shok > 0.5 cells (raw)")
    # 全部候选区质心 (人工核对): 每帧 shok 连续区 shok 加权质心
    ct, cx = bg["shok_cands_t"], bg["shok_cands_x"]
    m = (cx >= XMIN) & (cx <= XMAX)
    ax.scatter(cx[m], ct[m], s=26, marker="x", c="white", lw=1.2,
               label="shok region centroids (all candidates)")
    ax.plot(d["xa_left_um"], t_ns, "-", color="orange", lw=2.0,
            label=r"ablation front $x_a$")
    ax.plot(d["xa_right_um"], t_ns, "-", color="orange", lw=2.0)
    ax.plot(d["xs_left_um"], t_ns, ":", color="lime", lw=3.0,
            label=r"selected shock front $x_s$")
    ax.plot(d["xs_right_um"], t_ns, ":", color="lime", lw=3.0)
    ax.set_title("shok spacetime map — manual verification")
    ax.legend(loc="upper left", framealpha=0.85, fontsize=15)
    fig.tight_layout()
    fig.savefig(FIGS / "map_shok.png", dpi=150)
    plt.close(fig)
    print("[maps] OK  figures/map_shok.png")


if __name__ == "__main__":
    main()
