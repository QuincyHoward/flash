#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SNBVTi 极短时间测试 (tmax=1e-11 s) 结果绘图.

规则 (用户硬约束):
  * 全英文字符
  * 所有字号 > 18 pt
  * DPI >= 450, linewidth >= 2
  * x-t 图禁止 imshow -> 使用 pcolormesh + 真实逐帧时间

运行:
  python plot_shorttest.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
SCENE = HERE.parent.parent                      # .../SNBVTi
OUTDIR = SCENE / "flash_output" / "hpc_flash_ssh"
FIGDIR = SCENE / "flash_output" / "shorttest_figs"
FIGDIR.mkdir(parents=True, exist_ok=True)

NSPECIES = 4
SPECIES = ("cham", "shld", "samp", "tar2")
COLORS = {"cham": "#1f77b4", "shld": "#d62728",
          "samp": "#2ca02c", "tar2": "#9467bd"}

# 绘图规范
plt.rcParams.update({
    "font.size": 20,
    "axes.titlesize": 26,
    "axes.labelsize": 22,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "legend.fontsize": 19,
    "axes.linewidth": 1.8,
    "savefig.dpi": 500,
    "figure.dpi": 130,
    "font.family": "DejaVu Sans",
})


# --------------------------------------------------------------------------
def read_block_geometry(fh):
    """从 chk 还原 1-D 统一网格 (真实坐标, 单位 um)."""
    c = fh["coordinates"][:]
    nxb = int({r["name"].decode().strip(): r["value"]
               for r in fh["integer scalars"][:]}["nxb"])
    nblk = c.shape[0]
    blockstep = c[1, 0] - c[0, 0]
    dx = blockstep / nxb
    x = np.concatenate([c[i, 0] + np.arange(nxb) * dx + 0.5 * dx
                        for i in range(nblk)])
    return x * 1e4, dx, nxb, nblk       # um, cm, -, -


def load_frame(path):
    with h5py.File(path, "r") as fh:
        x, dx, nxb, nblk = read_block_geometry(fh)
        t = {r["name"].decode().strip(): r["value"]
             for r in fh["real scalars"][:]}["time"]
        ns = {r["name"].decode().strip(): r["value"]
              for r in fh["integer scalars"][:]}["nstep"]
        res = {"x": x, "dx": dx, "t": t, "nstep": ns}
        for v in ("dens", "tele", "tion", "trad", "velx", "nele", "ye"):
            if v in fh:
                res[v] = fh[v][:, :, 0, :].reshape(-1).astype(np.float64)
        if "unknown names" in fh:
            names = [n.tobytes().decode("utf-8", "replace").strip()
                     for n in fh["unknown names"][:]]
            for s in SPECIES:
                if s in names:
                    res[s] = fh[s][:, :, 0, :].reshape(-1).astype(np.float64)
    return res


# --------------------------------------------------------------------------
def fig_species_layout(fr):
    """物种分层示意 (末帧)."""
    fig, ax = plt.subplots(figsize=(13, 5.2))
    x = fr["x"]
    for i, s in enumerate(SPECIES):
        if s not in fr:
            continue
        y = fr[s]
        ax.fill_between(x, i * 0.9, i * 0.9 + 0.85 * (y > 0.5),
                        color=COLORS[s], alpha=0.85, step="mid", linewidth=0)
        ax.text(x[0] - 8, i * 0.9 + 0.42, s, ha="right", va="center",
                fontsize=21, color=COLORS[s], fontweight="bold")
    ax.set_xlim(-60, 80)
    ax.set_ylim(-0.35, 4 * 0.9)
    ax.set_yticks([])
    ax.set_xlabel("x [um]")
    ax.set_title("SNBVTi Species Layout (4 species, end frame)")
    ax.grid(axis="x", alpha=0.3, linewidth=1.2)
    for sp in ("left", "right", "top"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    p = FIGDIR / "fig1_species_layout.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_profiles(fr0, fr1):
    """初始 vs 末帧 密度/温度 剖面."""
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.2))
    x = fr1["x"]
    m = (x >= -10) & (x <= 20)

    ax = axes[0]
    ax.plot(x[m], fr0["dens"][m], "-", lw=2.6, color="#444444",
            label="t = 0")
    ax.plot(x[m], fr1["dens"][m], "-", lw=2.6, color="#d62728",
            label="t = %.3e s" % fr1["t"])
    ax.set_yscale("log")
    ax.set_xlabel("x [um]")
    ax.set_ylabel("Density [g/cm$^3$]")
    ax.set_title("Density Profile")
    ax.grid(alpha=0.3, linewidth=1.2, which="both")
    ax.legend(frameon=True, fontsize=19)

    ax = axes[1]
    ax.plot(x[m], fr0["tele"][m], "-", lw=2.6, color="#444444",
            label="t = 0")
    ax.plot(x[m], fr1["tele"][m], "-", lw=2.6, color="#d62728",
            label="t = %.3e s" % fr1["t"])
    if "tion" in fr1:
        ax.plot(x[m], fr1["tion"][m], "--", lw=2.4, color="#1f77b4",
                label="T$_{ion}$ (end)")
    ax.set_yscale("log")
    ax.set_xlabel("x [um]")
    ax.set_ylabel("Temperature [eV]")
    ax.set_title("Electron / Ion Temperature")
    ax.grid(alpha=0.3, linewidth=1.2, which="both")
    ax.legend(frameon=True, fontsize=19)

    fig.tight_layout()
    p = FIGDIR / "fig2_profiles.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_laser(datfile):
    """激光能量沉积曲线."""
    arr = np.loadtxt(datfile)
    t = arr[:, 1]
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.2))

    ax = axes[0]
    ax.plot(t * 1e12, arr[:, 2] * 1e-12, "-", lw=2.8, color="#d62728")
    ax.set_xlabel("Time [ps]")
    ax.set_ylabel("Deposited Energy [J/cm$^2$]")
    ax.set_title("Laser Energy Deposition")
    ax.grid(alpha=0.3, linewidth=1.2)

    ax = axes[1]
    for c, lb, cl in [(3, "Absorbed", "#1f77b4"),
                      (4, "Incident", "#ff7f0e"),
                      (5, "Reflected", "#2ca02c")]:
        ax.plot(t * 1e12, arr[:, c], "-", lw=2.6, color=cl, label=lb)
    ax.set_yscale("log")
    ax.set_xlabel("Time [ps]")
    ax.set_ylabel("Intensity [a.u.]")
    ax.set_title("Laser Power History")
    ax.grid(alpha=0.3, linewidth=1.2, which="both")
    ax.legend(frameon=True, fontsize=19)

    fig.tight_layout()
    p = FIGDIR / "fig3_laser.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_xt(paths):
    """x-t 图: pcolormesh + 真实逐帧时间 (禁用 imshow)."""
    frames = [load_frame(p) for p in paths]
    ts = np.array([f["t"] for f in frames]) * 1e12          # ps
    x = frames[0]["x"]
    m = (x >= -60) & (x <= 80)
    xw = x[m]

    for var, unit, title in (("tele", "eV", "Electron Temperature"),
                             ("dens", "g/cm$^3$", "Density")):
        Z = np.array([f[var][m] for f in frames])
        fig, ax = plt.subplots(figsize=(12.5, 7.0))
        pm = ax.pcolormesh(xw, ts, Z, shading="nearest",
                           cmap="inferno", rasterized=True)
        cb = fig.colorbar(pm, ax=ax, pad=0.02)
        cb.set_label("%s [%s]" % (title, unit), fontsize=22)
        cb.ax.tick_params(labelsize=20)
        ax.set_xlabel("x [um]")
        ax.set_ylabel("Time [ps]")
        ax.set_title("%s : x-t Evolution (real per-frame times)" % title)
        fig.tight_layout()
        p = FIGDIR / ("fig4_xt_%s.png" % var)
        fig.savefig(p, bbox_inches="tight")
        plt.close(fig)

    return FIGDIR / "fig4_xt_tele.png"


# --------------------------------------------------------------------------
def main():
    chks = sorted(OUTDIR.glob("snbvtiug_hdf5_chk_0*"))
    chks = [p for p in chks if p.stat().st_size > 0]
    if not chks:
        print("NO_CHECKPOINT"); return 1
    print("checkpoints: %d" % len(chks))

    fr0 = load_frame(chks[0])
    fr1 = load_frame(chks[-1])
    print("t0 = %.6e s  nstep= %d" % (fr0["t"], fr0["nstep"]))
    print("t1 = %.6e s  nstep= %d" % (fr1["t"], fr1["nstep"]))
    print("species present: %s" % [s for s in SPECIES if s in fr1])

    outs = []
    outs.append(fig_species_layout(fr1))
    outs.append(fig_profiles(fr0, fr1))

    dat = OUTDIR / "snbvtiug_LaserEnergyProfile.dat"
    if dat.is_file():
        outs.append(fig_laser(dat))

    if len(chks) >= 2:
        outs.append(fig_xt(chks))

    for p in outs:
        print("FIG %s  %d B" % (p.name, p.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
