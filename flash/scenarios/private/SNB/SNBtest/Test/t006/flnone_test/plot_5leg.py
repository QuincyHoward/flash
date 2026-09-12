#!/usr/bin/env python3
"""t006/flnone_test 绘图 —— SNB×3 + FL-SH×2 五腿对比
═══════════════════════════════════════════════════════════════════════════════

五腿定义
--------
| # | 显示名                       | side | tag      |
|---|---|---|---|
| 1 | SNB radON (fl_harmonic)      | snb  | radon    |
| 2 | SNB radON (fl_none)          | snb  | flnone   |
| 3 | SNB radOFF (fl_harmonic)     | snb  | radoff   |
| 4 | FL-SH radON                  | flsh | radon    |
| 5 | FL-SH radOFF                 | flsh | radoff   |

产出（全部英文标注、PPT 演讲级: DPI 450 / 大字号 / 粗线）
--------------------------------------------------------
    fig1_flnone_vs_harmonic.png   ★ 核心判据: fl_none 与 fl_harmonic 是否逐位相同
    fig2_profiles_tele_5leg.png   电子温度剖面（5 腿 × N 时刻）
    fig3_profiles_dens_5leg.png   质量密度剖面
    fig4_metrics_5leg.png         烧蚀面轨迹 x_a(t) + 烧蚀速率 Ṁ 柱状对比
    fig5_xt_tele_5leg.png         电子温度时空图（5 联）
    fig6_profiles_trad_5leg.png   辐射温度剖面（辐射开关判据）
    metrics_5leg.csv / metrics_5leg.md   五腿定量表

数据源
------
chk（71 键 / float64）。读取逻辑复用核心模块 `SNB/scripts/analysis/compare_4way.py`
（+ug 叶块直读 / 复合 Dataset 解析），不重复实现。

用法
----
    python plot_5leg.py --scene <场景目录> --out <输出目录>
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                              # noqa: E402
from matplotlib.colors import LogNorm, Normalize             # noqa: E402
from matplotlib.ticker import MaxNLocator                    # noqa: E402

# ── 复用核心模块的 chk 读取与单位换算（唯一权威实现）────────────
_HERE = Path(__file__).resolve().parent


def _find_snb_core() -> Path:
    for anc in [_HERE] + list(_HERE.parents):
        for cand in (anc / "SNB", anc.parent / "SNB"):
            if (cand / "scripts").is_dir() and (cand / "source").is_dir():
                return cand
    raise SystemExit(f"[X] 未找到 SNB 核心模块 (从 {_HERE} 向上搜索)")


SNB = _find_snb_core()
sys.path.insert(0, str(SNB / "scripts" / "analysis"))
import compare_4way as C4                                   # noqa: E402

VARS = ["dens", "tele", "tion", "trad", "pele", "pres"]

# ── 五腿 ──────────────────────────────────────────────────────
LEGS5: List[Tuple[str, str, str]] = [
    ("SNB radON (fl_harmonic)", "snb", "radon"),
    ("SNB radON (fl_none)", "snb", "flnone"),
    ("SNB radOFF (fl_harmonic)", "snb", "radoff"),
    ("FL-SH radON", "flsh", "radon"),
    ("FL-SH radOFF", "flsh", "radoff"),
]

# 颜色/线型：SNB 用暖色，FL-SH 用冷色；radOFF 一律虚线
STYLE: Dict[str, Dict[str, Any]] = {
    "SNB radON (fl_harmonic)": {"c": "#C1440E", "ls": "-", "lw": 3.4},
    "SNB radON (fl_none)": {"c": "#E8A33D", "ls": "--", "lw": 3.0},
    "SNB radOFF (fl_harmonic)": {"c": "#C1440E", "ls": ":", "lw": 3.0},
    "FL-SH radON": {"c": "#1B5E9C", "ls": "-", "lw": 3.4},
    "FL-SH radOFF": {"c": "#1B5E9C", "ls": ":", "lw": 3.0},
}


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


def load_all(scene: Path) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for name, side, tag in LEGS5:
        d = scene / "flash_output" / f"sim_{side}" / tag
        fr: List[Dict[str, Any]] = []
        for p in C4.list_chk(d):
            try:
                fr.append(C4.load_chk(p, VARS))
            except Exception as exc:                        # noqa: BLE001
                log(f"{name}: 跳过 {p.name}: {exc}", "WARN")
        fr.sort(key=lambda r: r["t"])
        out[name] = fr
        log(f"{name:<26} {len(fr):>3} 帧   {d.relative_to(scene).as_posix()}",
            "OK" if fr else "ERROR")
    return out


def _grid(n: int, ncol: int = 3, figsize=(20.5, 11.6)):
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=figsize,
                             sharex=True, sharey=True)
    return fig, np.atleast_1d(axes).ravel()


def _style_ax(ax, title: str = "") -> None:
    if title:
        ax.set_title(title, fontsize=22, pad=8)
    ax.tick_params(labelsize=18, width=2.0)
    for s in ax.spines.values():
        s.set_linewidth(2.0)
    ax.grid(alpha=0.25, lw=0.9, which="both")


# ══════════════════════════════════════════════════════════════
# fig1 —— ★ 核心判据: fl_none vs fl_harmonic
# ══════════════════════════════════════════════════════════════
def fig1_flnone_vs_harmonic(series, out_dir: Path) -> Optional[Path]:
    a = series["SNB radON (fl_harmonic)"]
    b = series["SNB radON (fl_none)"]
    if not a or not b:
        log("fig1: 缺 SNB radON 数据，跳过", "WARN")
        return None

    # 逐帧（按时间戳配对后的）最大相对差
    ta = {round(r["t"], 20): r for r in a}
    tb = {round(r["t"], 20): r for r in b}
    common = sorted(set(ta) & set(tb))
    rel: Dict[str, List[float]] = {v: [] for v in ("dens", "tele", "trad")}
    ts_ns: List[float] = []
    for t in common:
        ra, rb = ta[t], tb[t]
        ts_ns.append(t * 1e9)
        for v in rel:
            va, vb = np.asarray(ra[v], float), np.asarray(rb[v], float)
            d = float(np.max(np.abs(va - vb)))
            sc = float(np.max(np.abs(vb))) or 1.0
            rel[v].append(d / sc)

    zero = all(all(x == 0.0 for x in rel[v]) for v in rel)

    fig, axes = plt.subplots(2, 2, figsize=(17.5, 12.4))
    fig.subplots_adjust(left=0.078, right=0.972, top=0.872, bottom=0.078,
                        hspace=0.26, wspace=0.24)

    last_a, last_b = a[-1], b[-1]
    for k, (ax, var) in enumerate(zip((axes[0][0], axes[0][1], axes[1][0]),
                                      ("tele", "dens", "trad"))):
        q = C4.QUANTITIES[var]
        va = C4.convert(last_a, var); vb = C4.convert(last_b, var)
        x = np.asarray(last_a["x_um"], float)
        ax.plot(x, va, color="#0B7285", lw=4.2, ls="-", alpha=0.95,
                label="fl_harmonic", solid_capstyle="round")
        ax.plot(x, vb, color="#E8590C", lw=2.0, ls="--", alpha=0.95,
                label="fl_none", dash_capstyle="round")
        dmax = float(np.max(np.abs(np.asarray(va, float) - np.asarray(vb, float))))
        ax.set_ylabel(f"{q['title']}  [{q['unit']}]", fontsize=21)
        _style_ax(ax, f"{q['title']}  @ t = {last_a['t']*1e9:.3f} ns")
        # max|Δ| 放到坐标轴内，避免标题过长互相挤压
        ax.text(0.035, 0.955, f"max|Δ| = {dmax:.1e}", transform=ax.transAxes,
                fontsize=17, va="top", ha="left",
                color="#1B5E9C" if dmax == 0.0 else "#C92A2A",
                bbox=dict(boxstyle="round,pad=0.32", fc="white",
                          ec="#1B5E9C" if dmax == 0.0 else "#C92A2A", lw=1.4,
                          alpha=0.92))
        ax.set_xlim(-60, 60)
        if k == 0:
            ax.legend(fontsize=18, loc="lower right", framealpha=0.9)

    # 右下: 相对差随时间的走势 —— 判据可视化
    ax = axes[1][1]
    for var, col in (("dens", "#2B8A3E"), ("tele", "#C92A2A"), ("trad", "#5F3DC4")):
        yv = np.array(rel[var], float)
        ax.plot(ts_ns, np.maximum(yv, 1e-18), color=col, lw=3.0, marker="o",
                ms=7, label=var)
    ax.set_yscale("log")
    ax.set_ylim(1e-18, 1e-2)
    ax.axhline(1e-16, color="0.35", lw=1.6, ls="--")
    ax.text(0.03, 1.35e-16, "double precision round-off  (~1e-16)",
            transform=ax.get_yaxis_transform(), fontsize=15, color="0.3", va="bottom")
    if zero:
        ax.text(0.5, 0.55,
                "Δ ≡ 0 exactly\n(bit-identical to the last digit)",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=23, color="#1B5E9C", weight="medium",
                bbox=dict(boxstyle="round,pad=0.5", fc="#E7F5FF",
                          ec="#1B5E9C", lw=1.6))
    ax.set_xlabel("Time  [ns]", fontsize=21)
    ax.set_ylabel("max relative difference", fontsize=21)
    _style_ax(ax, "fl_none vs fl_harmonic  —  difference history")
    ax.legend(fontsize=17, loc="upper left", framealpha=0.9)

    fig.suptitle("Core test — fl_none vs fl_harmonic  "
                 "(SNB radON; par differs in exactly one key)",
                 fontsize=23, y=0.947)
    return C4.save_fig(fig, out_dir / "fig1_flnone_vs_harmonic.png")


# ══════════════════════════════════════════════════════════════
# 通用: 5 腿剖面图
# ══════════════════════════════════════════════════════════════
def fig_profiles5(series, var: str, out_dir: Path, fname: str,
                  n_times: int = 8, title: str = "") -> Optional[Path]:
    q = C4.QUANTITIES[var]
    names = [n for n, _, _ in LEGS5]
    have = [n for n in names if series[n]]
    if not have:
        log(f"{var}: 无数据，跳过", "WARN")
        return None

    twin = (max(series[n][0]["t"] for n in have),
            min(series[n][-1]["t"] for n in have))
    cmap = plt.get_cmap("viridis")
    panels: Dict[str, List[Tuple[float, np.ndarray, np.ndarray]]] = {}
    ymin, ymax = np.inf, -np.inf
    for n in names:
        lst = []
        for f in C4.pick_even(series[n], n_times, twin):
            v = C4.convert(f, var)
            if v is None:
                continue
            v = np.asarray(v, float)
            fin = v[np.isfinite(v)]
            if fin.size:
                ymin, ymax = min(ymin, float(fin.min())), max(ymax, float(fin.max()))
            lst.append((f["t"], np.asarray(f["x_um"], float), v))
        panels[n] = lst
    if not np.isfinite(ymin):
        log(f"{var}: 无有效数据，跳过", "WARN")
        return None
    use_log = bool(q["log"]) and ymin > 0
    pad = 0.04 * (ymax - ymin + 1e-30)
    ylim = ((max(ymin, ymax * 1e-12), ymax) if use_log else (ymin - pad, ymax + pad))

    fig, axf = _grid(6, 3)
    fig.subplots_adjust(left=0.058, right=0.884, top=0.884, bottom=0.074,
                        hspace=0.22, wspace=0.15)
    t_all = [t for n in names for t, _, _ in panels[n]]
    t_lo, t_hi = (min(t_all), max(t_all)) if t_all else (0.0, 1.0)
    tr = (t_hi - t_lo) or 1.0

    for i, n in enumerate(names):
        ax = axf[i]
        lst = panels[n]
        if not lst:
            ax.text(.5, .5, "no data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=20, color="0.45")
            _style_ax(ax, n)
            continue
        for t, x, v in lst:
            vv = np.where(v > 0, v, np.nan) if use_log else v
            ax.plot(x, vv, color=cmap(0.06 + 0.90 * (t - t_lo) / tr), lw=2.6)
        if use_log:
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
            ax.yaxis.set_minor_locator(
                plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * .1)))
            ax.yaxis.set_minor_formatter(plt.NullFormatter())
        ax.set_ylim(ylim)
        ax.set_xlim(-60, 60)
        _style_ax(ax, n)

    # 末格: 说明文字；色标移到画布外侧，避免与文字重叠
    ax = axf[5]
    ax.axis("off")
    txt = ("five legs\n\n"
           "1  SNB radON   fl_harmonic\n"
           "2  SNB radON   fl_none\n"
           "3  SNB radOFF  fl_harmonic\n"
           "4  FL-SH radON\n"
           "5  FL-SH radOFF\n\n"
           "source: chk (float64)")
    ax.text(0.0, 0.98, txt, transform=ax.transAxes, va="top", ha="left",
            fontsize=15, color="0.25", linespacing=1.5)
    sm = plt.cm.ScalarMappable(norm=Normalize(t_lo * 1e9, t_hi * 1e9), cmap=cmap)
    sm.set_array([])
    cax = fig.add_axes([0.900, 0.20, 0.017, 0.58])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("Simulation time  [ns]", fontsize=19)
    cb.ax.tick_params(labelsize=16, width=2.0); cb.outline.set_linewidth(2.0)

    for i in (3, 4, 5):
        axf[i].set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=21)
    for i in (0, 3):
        axf[i].set_ylabel(f"{q['title']}  [{q['unit']}]", fontsize=21)
    fig.suptitle(title or f"{q['title']} — five legs, {n_times} times "
                           f"(source: chk)", fontsize=24, y=0.965)
    return C4.save_fig(fig, out_dir / fname)


# ══════════════════════════════════════════════════════════════
# fig4 —— 烧蚀指标
# ══════════════════════════════════════════════════════════════
def fig4_metrics(series, out_dir: Path) -> Tuple[Optional[Path], Dict[str, Dict[str, float]]]:
    met: Dict[str, List[Dict[str, float]]] = {}
    summ: Dict[str, Dict[str, float]] = {}
    for name, _, _ in LEGS5:
        rows = sorted([m for m in (C4.frame_metrics(f) for f in series[name]) if m],
                      key=lambda r: r["t_ns"])
        met[name] = rows
        if rows:
            M0, rate = C4.rate_abl(rows)
            summ[name] = {"M0": M0, "rate": rate, **rows[-1]}
    if not summ:
        log("fig4: 无数据，跳过", "WARN")
        return None, {}

    fig, axes = plt.subplots(1, 2, figsize=(21.0, 8.6))
    fig.subplots_adjust(left=0.062, right=0.985, top=0.855, bottom=0.115, wspace=0.20)

    ax = axes[0]
    for name, _, _ in LEGS5:
        rows = met[name]
        if not rows:
            continue
        st = STYLE[name]
        ax.plot([r["t_ns"] for r in rows], [r["x_a_um"] for r in rows],
                color=st["c"], ls=st["ls"], lw=st["lw"], label=name,
                marker="o", ms=6, markevery=2)
    ax.set_xlabel("Time  [ns]", fontsize=22)
    ax.set_ylabel(r"Ablation front  $x_a$  [$\mu$m]", fontsize=22)
    _style_ax(ax, "Ablation front trajectory")
    ax.legend(fontsize=15, loc="lower left", framealpha=0.9)

    ax = axes[1]
    names = [n for n, _, _ in LEGS5 if n in summ]
    ypos = np.arange(len(names))[::-1]
    vals = [summ[n]["rate"] for n in names]
    ax.barh(ypos, vals, height=0.62,
            color=[STYLE[n]["c"] for n in names],
            alpha=0.88, edgecolor="black", linewidth=1.6)
    for y, n in zip(ypos, names):
        r = summ[n]["rate"]
        ax.text(r * 1.015, y, f"{r:.3e}", va="center", fontsize=16)
    ax.set_yticks(ypos)
    ax.set_yticklabels(names, fontsize=16)
    ax.set_xlabel(r"Ablation rate  $\dot{M}$  [g cm$^{-2}$ s$^{-1}$]", fontsize=22)
    ax.set_xlim(0, max(vals) * 1.22)
    _style_ax(ax, "Ablation rate  (late-time linear fit)")

    fig.suptitle("Ablation metrics — five legs (source: chk)", fontsize=24, y=0.955)
    return C4.save_fig(fig, out_dir / "fig4_metrics_5leg.png"), summ


# ══════════════════════════════════════════════════════════════
# fig5 —— 时空图
# ══════════════════════════════════════════════════════════════
def fig5_xt(series, var: str, out_dir: Path, fname: str) -> Optional[Path]:
    grids: Dict[str, Any] = {}
    for name, _, _ in LEGS5:
        g = C4.build_xt_arrays(series[name], var) if series[name] else None
        if g is not None:
            grids[name] = g
    if not grids:
        log(f"{var}: 无数据，跳过", "WARN")
        return None
    q = C4.QUANTITIES[var]
    allv = np.concatenate([g[2].ravel() for g in grids.values()])
    allv = allv[np.isfinite(allv)]
    use_log = bool(q["log"])
    floor = None
    if use_log:
        pos = allv[allv > 0]
        floor = float(pos.min()) * 0.5 if pos.size else 1e-30
        norm = LogNorm(vmin=floor * 1.0000001, vmax=float(allv.max()))
        cbl = f"{q['title']}  [{q['unit']}]  (log)"
    else:
        vmin, vmax = float(allv.min()), float(allv.max())
        vmax = vmax if vmax > vmin else vmin + abs(vmin) * 1e-3 + 1e-30
        norm = Normalize(vmin=vmin, vmax=vmax)
        cbl = f"{q['title']}  [{q['unit']}]"

    fig, axf = _grid(5, 3, figsize=(21.0, 12.0))
    fig.subplots_adjust(left=0.058, right=0.905, top=0.885, bottom=0.062,
                        hspace=0.20, wspace=0.12)
    im = None
    for i, (name, _, _) in enumerate(LEGS5):
        ax = axf[i]
        if name not in grids:
            ax.text(.5, .5, "no data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=20, color="0.45")
            _style_ax(ax, name)
            continue
        t_ns, xg, Z = grids[name]
        if floor is not None:
            Z = np.where(np.isfinite(Z) & (Z > 0), Z, floor)
        # ★★ pcolormesh + **真实逐帧时间坐标**（不能用 imshow）：
        #    chk 按步数间隔输出 → Δt 随 dt 变化、高度不均匀（FL-SH 腿实测
        #    1.36e-12…7.19e-11，52.7×）；imshow 的等间距假设会把时间轴拉偏
        #    数千个百分点，造成"两腿前沿速度不同"的假象。
        X, T = np.meshgrid(xg, t_ns)
        im = ax.pcolormesh(X, T, Z, shading="auto",
                           cmap=q["cmap"], norm=norm, rasterized=True)
        ax.set_xlim(-60, 60)
        _style_ax(ax, name)
    for i in (0, 1, 2):
        axf[i].set_xlabel("")
    axf[5].axis("off")
    axf[5].text(0.02, 0.96,
                "source: chk (float64)\n\nrows:\n  row 1 — SNB legs\n"
                "  row 2 — SNB radOFF + FL-SH legs\n\n"
                "shared color scale",
                transform=axf[5].transAxes, va="top", ha="left",
                fontsize=16, color="0.25")
    for i in (0, 3):
        axf[i].set_ylabel("Time  [ns]", fontsize=21)
    for i in (3, 4):
        axf[i].set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=21)
    fig.suptitle(f"{q['title']} — x-t maps, five legs (source: chk)",
                 fontsize=24, y=0.958)
    if im is not None:
        cax = fig.add_axes([0.912, 0.062, 0.020, 0.823])
        cb = fig.colorbar(im, cax=cax); cb.set_label(cbl, fontsize=21)
        cb.ax.tick_params(labelsize=18, width=2.0); cb.outline.set_linewidth(2.0)
        if use_log:
            cb.ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
            cb.ax.yaxis.set_minor_locator(
                plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * .1)))
            cb.ax.yaxis.set_minor_formatter(plt.NullFormatter())
        else:
            cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
    return C4.save_fig(fig, out_dir / fname)


# ══════════════════════════════════════════════════════════════
def write_tables(summ: Dict[str, Dict[str, float]], out_dir: Path) -> None:
    if not summ:
        return
    csv_out = out_dir / "metrics_5leg.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["leg", "t_end_ns", "x_a_um", "x_c_um", "M0_gcm2",
                    "M_end_gcm2", "Mdot_gcm2s", "rho_max", "Te_max_eV",
                    "Ti_max_eV", "Trad_max_eV"])
        for name, _, _ in LEGS5:
            s = summ.get(name)
            if not s:
                w.writerow([name] + [""] * 10); continue
            w.writerow([name, f"{s['t_ns']:.4f}", f"{s['x_a_um']:.4f}",
                        f"{s['x_c_um']:.4f}", f"{s['M0']:.6e}",
                        f"{s['M_dense_gcm2']:.6e}", f"{s['rate']:.6e}",
                        f"{s['rho_max']:.4f}", f"{s['te_max']:.3f}",
                        f"{s['ti_max']:.3f}", f"{s['tr_max']:.4f}"])
    log(f"定量表 → {csv_out.name}", "OK")

    md = out_dir / "metrics_5leg.md"
    with md.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("| 腿 | t末[ns] | x_a[µm] | x_c[µm] | M0[g/cm²] | M末[g/cm²] | "
                 "Ṁ[g/cm²/s] | ρmax | Te_max[eV] | Trad_max[eV] |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for name, _, _ in LEGS5:
            s = summ.get(name)
            if not s:
                fh.write(f"| {name} | — | — | — | — | — | — | — | — | — |\n")
                continue
            fh.write(f"| {name} | {s['t_ns']:.3f} | {s['x_a_um']:.2f} | "
                     f"{s['x_c_um']:.2f} | {s['M0']:.4e} | "
                     f"{s['M_dense_gcm2']:.4e} | {s['rate']:.4e} | "
                     f"{s['rho_max']:.3f} | {s['te_max']:.1f} | "
                     f"{s['tr_max']:.3f} |\n")
    log(f"定量表 → {md.name}", "OK")


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="SNB×3 + FL-SH×2 五腿对比绘图")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--n-times", type=int, default=8)
    args = ap.parse_args()

    scene = Path(args.scene).resolve()
    out = Path(args.out).resolve() if args.out else scene / "images" / "flnone5"
    out.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 78)
    print(" SNB×3 + FL-SH×2 五腿对比绘图")
    print(f" 场景: {scene}")
    print(f" 输出: {out}")
    print("=" * 78)

    series = load_all(scene)
    if not any(series.values()):
        log("无任何 chk 数据", "ERROR")
        return 1

    fig1_flnone_vs_harmonic(series, out)
    fig_profiles5(series, "tele", out, "fig2_profiles_tele_5leg.png",
                  args.n_times, "Electron temperature — five legs, "
                  f"{args.n_times} times (source: chk)")
    fig_profiles5(series, "dens", out, "fig3_profiles_dens_5leg.png",
                  args.n_times, "Mass density — five legs, "
                  f"{args.n_times} times (source: chk)")
    _, summ = fig4_metrics(series, out)
    fig5_xt(series, "tele", out, "fig5_xt_tele_5leg.png")
    fig_profiles5(series, "trad", out, "fig6_profiles_trad_5leg.png",
                  args.n_times, "Radiation temperature — five legs, "
                  f"{args.n_times} times (source: chk)")
    write_tables(summ, out)

    print("\n" + "=" * 78)
    print(f" 完成 — 产出目录: {out}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
