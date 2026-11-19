# -*- coding: utf-8 -*-
"""plot_fe_groups — 19 群台阶 fe(E) 演化绘图（含/不含 fe 两套 zip 的配套图）。

读取 out/fe_group_data.npz（由 make_fe_group_zips.py 落盘），产出 plots/：
  fig1_fe_group_evolution.png    (a) 逐群增强比 n1_g/n0(E_g) 热图 (logE x t)
                                 (b) 群通量占比 q_g/q_SH 热图 (diverging)
  fig2_fe_stairs_keyframes.png   4 个特征帧: 19 群 stairs vs 细网格连续 fe_snb
  fig3_contact_sheet_fe_stairs.png  175 帧台阶总览 (stairs vs 麦氏核心)
  fig4_history_none_preview.png  不含 fe 版 zip 的 history 内容预览
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
ANALYSIS = HERE.parent / "scripts" / "analysis"
for p in (str(ROOT), str(ANALYSIS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib                                    # noqa: E402
matplotlib.use("Agg")                                # noqa: E402
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.colors import LogNorm, TwoSlopeNorm  # noqa: E402

from style import setup_style                        # noqa: E402

OUT = HERE / "out"
PLOTS = HERE / "plots"
NPZ = OUT / "fe_group_data.npz"
HIST_CSV = ANALYSIS / "flychk_history_175" / "history_175.csv"


def _stairs_edges(E_eV: np.ndarray) -> np.ndarray:
    """19 个能量点（群上边界）→ 20 条显示边界（首群下边界 = 0.1/10^(1/3)）。"""
    return np.concatenate([[E_eV[0] / 10 ** (1 / 3)], E_eV])


def _mesh_edges(E_eV: np.ndarray) -> np.ndarray:
    """19 个群中心 → 20 条 pcolormesh 边界（几何均值外推）。"""
    mid = np.sqrt(E_eV[:-1] * E_eV[1:])
    lo = E_eV[0] / 10 ** (1 / 6)
    hi = E_eV[-1] * 10 ** (1 / 6)
    return np.concatenate([[lo], mid, [hi]])


def _mesh_yedges(t: np.ndarray) -> np.ndarray:
    """均匀时间采样点 → 176 条 pcolormesh y 边界。"""
    dt = float(t[1] - t[0])
    return np.linspace(t[0] - dt / 2, t[-1] + dt / 2, len(t) + 1)


def fig1(z: dict) -> Path:
    """台阶高度演化的两张热图（含 fe 版核心图）。"""
    E, t = z["E_eV"], z["t_ns"]
    xe, ye = _mesh_edges(E), _mesh_yedges(t)
    n0 = z["n0_stairs"]
    # n0 相对地板（1e-10 * 逐帧峰值, 同 t12 口径）: 麦氏核心下溢处 n1/n0 无意义
    n0_floor = 1e-10 * np.max(n0, axis=1, keepdims=True)
    ratio = np.where(n0 > n0_floor, z["ratio"], np.nan)
    ratio = np.maximum(ratio, 1e-16)
    # q_g/q_SH: 帧级 |q_SH| < 1e-3*全局峰处整行无意义（与闸门 B 同口径）
    qsh = z["qsh"]
    row_ok = np.abs(qsh) > 1e-3 * np.max(np.abs(qsh))
    qf = np.where(row_ok[:, None], z["qg_frac"], np.nan)
    finite = np.isfinite(ratio) & (ratio > 0)
    vmax = float(np.nanpercentile(ratio[finite], 98))
    vmin = max(float(np.nanpercentile(ratio[finite], 5)), vmax * 1e-6)
    qf_f = np.abs(qf[np.isfinite(qf)])
    qmax = float(np.nanpercentile(qf_f, 95)) if qf_f.size else 1.0

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 11), sharex=True)
    cmap = plt.cm.magma.copy()
    cmap.set_bad("0.92")
    im = ax.pcolormesh(xe, ye, ratio, cmap=cmap,
                       norm=LogNorm(vmin=vmin, vmax=vmax))
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label(r"$n_1/n_0$ per group (excess enhancement)")
    ax.set_xscale("log")
    ax.set_ylabel("t [ns]")
    ax.set_title(r"(a) 19-group staircase height evolution: $n_1/n_0(E_g)$"
                 "   (grey = Maxwellian core below 1e-10 floor)")
    for g in range(1, 19):
        ax.axvline(E[g - 1], color="w", lw=0.4, alpha=0.25)

    cmap2 = plt.cm.RdBu_r.copy()
    cmap2.set_bad("0.92")
    im2 = ax2.pcolormesh(xe, ye, qf, cmap=cmap2,
                         norm=TwoSlopeNorm(vcenter=0.0, vmin=-qmax, vmax=qmax))
    cb2 = fig.colorbar(im2, ax=ax2, pad=0.02)
    cb2.set_label(r"$q_g / q_{SH}$ (signed group flux fraction)")
    ax2.set_xscale("log")
    ax2.set_xlabel("E [eV]  (19 SNB group upper boundaries)")
    ax2.set_ylabel("t [ns]")
    ax2.set_title(r"(b) signed group flux fraction $q_g/q_{SH}$"
                  "   (grey = |q_SH| below 1e-3 floor)")
    for g in range(1, 19):
        ax2.axvline(E[g - 1], color="k", lw=0.4, alpha=0.2)

    fig.suptitle("SNB 19-group staircase evolution — SNBVTi2um_hot, "
                 "175 samples over [0, 1.6] ns", fontsize=19)
    fig.subplots_adjust(left=0.10, right=0.90, top=0.91, bottom=0.09,
                        hspace=0.22)
    p = PLOTS / "fig1_fe_group_evolution.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def fig2(z: dict) -> Path:
    """特征帧 stairs vs 连续参考线。"""
    E, t = z["E_eV"], z["t_ns"]
    Ef = _stairs_edges(E)
    E_fine = np.geomspace(0.1, 1e5, 121)     # fe_fine 的能量轴（与 make 脚本一致）
    targets = [0.20, 0.50, 1.10, 1.50]
    fig, axes = plt.subplots(2, 2, figsize=(15, 10.5), sharex=True)
    for ax, tt in zip(axes.ravel(), targets):
        k = int(np.argmin(np.abs(t - tt)))
        fe = np.maximum(z["fe_stairs"][k], 1e-300)
        fe0 = np.maximum(z["fe0_stairs"][k], 1e-300)
        ff = np.maximum(z["fe_fine"][k], 1e-300)
        ax.stairs(fe, Ef, baseline=None, color="k", lw=2.4,
                  label=r"fe$(E_g)$ 19-group stairs (with-fe zip)")
        ax.loglog(E_fine, ff, "r--", lw=1.8,
                  label=r"fine-grid fe(E) = $f_0+f_1$ (reference)")
        ax.stairs(fe0, Ef, baseline=None, color="#1f77b4", lw=1.6, ls=":",
                  label=r"Maxwellian core $f_0$ (without-fe baseline)")
        ax.set_ylim(fe.max() * 3e-8, fe.max() * 30)
        ax.set_xlim(Ef[0], Ef[-1])
        ax.set_title(f"t = {t[k]:.3f} ns   "
                     rf"$T_e$ = {z['Te_eV'][k]:.4g} eV   "
                     rf"$n_{{1,tot}}/n_e$ = {z['n1_tot'][k] / z['ne'][k]:.2e}")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=13, loc="best")
    for ax in axes[1, :]:
        ax.set_xlabel("E [eV]")
    for ax in axes[:, 0]:
        ax.set_ylabel(r"$f_e$ [cm$^{-3}$ eV$^{-3/2}$]")
    fig.suptitle("19-group staircase fe(E) vs continuous reconstruction — "
                 "key frames", fontsize=19)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.90, bottom=0.08,
                        hspace=0.18, wspace=0.16)
    p = PLOTS / "fig2_fe_stairs_keyframes.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def fig3(z: dict) -> Path:
    """175 帧台阶总览 contact sheet。"""
    E, t = z["E_eV"], z["t_ns"]
    Ef = _stairs_edges(E)
    ncol, nrow = 15, 12
    fig, axes = plt.subplots(nrow, ncol, figsize=(1.85 * ncol, 1.42 * nrow))
    for ax in np.ravel(axes):
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.4)
    for k in range(175):
        ax = np.ravel(axes)[k]
        fe = np.maximum(z["fe_stairs"][k], 1e-300)
        fe0 = np.maximum(z["fe0_stairs"][k], 1e-300)
        ax.stairs(fe, Ef, baseline=None, color="k", lw=0.9)
        ax.stairs(fe0, Ef, baseline=None, color="#1f77b4", lw=0.6, ls=":")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(Ef[0], Ef[-1])
        ax.set_ylim(max(fe.max() * 1e-6, 1e-300), fe.max() * 12)
        ax.set_title(f"#{k:03d} {t[k]:.2f}ns", fontsize=8, pad=1)
    # log 轴会重新挂上 LogLocator/LogFormatter，绘制完成后再次清除
    # （与 fe_fit_frames._contact_sheet 同一坑）
    from matplotlib.ticker import NullFormatter, NullLocator
    for ax in np.ravel(axes):
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_locator(NullLocator())
            axis.set_minor_locator(NullLocator())
            axis.set_major_formatter(NullFormatter())
            axis.set_minor_formatter(NullFormatter())
    fig.suptitle("19-group staircase fe(E) (black) vs Maxwellian core "
                 "(blue dotted) — 175 samples over [0, 1.6] ns", fontsize=22)
    fig.subplots_adjust(left=0.012, right=0.992, bottom=0.022, top=0.945,
                        wspace=0.06, hspace=0.32)
    p = PLOTS / "fig3_contact_sheet_fe_stairs.png"
    fig.savefig(p, dpi=72)
    plt.close(fig)
    return p


def fig4() -> Path:
    """不含 fe 版 zip 的 history 内容（两版 zip 中 history 逐字节相同）。"""
    with HIST_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    t = np.array([float(r["time"]) for r in rows]) * 1e9
    cols = [("te", "te [eV]"), ("ti", "ti [eV]"), ("tr", "tr [eV]"),
            ("rho", r"$\rho$ [g/cm$^3$]"), ("size", "size [cm]")]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    axes = axes.ravel()
    for ax, (c, lab) in zip(axes, cols):
        v = np.array([float(r[c]) for r in rows])
        ax.semilogy(t, np.maximum(v, 1e-300), "o-", ms=3, lw=1.4)
        ax.set_xlabel("t [ns]")
        ax.set_title(lab, fontsize=17)
        ax.grid(alpha=0.3)
    axes[-1].axis("off")
    axes[-1].text(0.02, 0.92,
                  'zip pair (identical\n  history data):\n'
                  '"with fe"    = runfile +\n  history + fe file\n'
                  '"without fe" = runfile +\n  history\n'
                  "fe file adds the 19-group\n  staircase EEDF;\n"
                  "history columns:\n  time/rho/size/te/ti/tr\n"
                  "(Maxwellian background;\n  no fhot/thot — the non-\n"
                  "  Maxwellian part is the\n  fe file itself).",
                  fontsize=13, va="top", transform=axes[-1].transAxes)
    fig.suptitle("History data shared by both zips (175 steps, [0, 1.6] ns) — "
                 "content of the without-fe zip", fontsize=19)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.10,
                        wspace=0.24, hspace=0.30)
    p = PLOTS / "fig4_history_none_preview.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def main() -> int:
    PLOTS.mkdir(parents=True, exist_ok=True)
    with np.load(NPZ, allow_pickle=False) as z:
        z = {k: z[k] for k in z.files}
    outs = [fig1(z), fig2(z), fig3(z), fig4()]
    for p in outs:
        print(f"[plot] {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
