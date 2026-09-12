"""t004 四腿对比 —— 辐射开关 2×2 矩阵的图与定量表

四腿
----
    FL-SH radON   (flsh/radon)      FL-SH radOFF (flsh/radoff)
    SNB   radON   (snb /radon)      SNB   radOFF (snb /radoff)

产出 (分门别类存放)
------------------
    results/pcolor/   xt4_<var>_<tag>.png     ← 2×2 四联时空彩图 (每物理量一张)
    results/profiles/ prof4_<var>_<tag>.png   ← 2×2 四联 10 时刻剖面 (辐射开/关叠加)
    results/ablation/ ablation_4way_<tag>.csv ← 烧蚀面/临界面/面密度时间序列
    results/compare/  summary_4way_<tag>.{md,csv} ← 四腿定量汇总表

数据源: **chk** (非 plt)。单位换算与判据同 t003:
    K→eV, erg/cm³→Mbar, nele 离线推导; 烧蚀面=ρ 最陡处, 致密面=0.5ρ_solid 外侧跨越。

用法 (在 t004 目录下):
    python scripts/analysis/compare_4way.py --tag-prefix ""        # 正式
    python scripts/analysis/compare_4way.py --tag-prefix smoke_    # 短测
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_T004 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T004 / "scripts" / "plot_compare" / "common"))

import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from matplotlib.colors import LogNorm, Normalize  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

import plot_common as PC                # noqa: E402
import t004_common as C                 # noqa: E402

# 四腿定义: (显示名, model, tag)  — 顺序即 2×2 网格顺序
LEGS4: List[Tuple[str, str, str]] = [
    ("FL-SH radON",  "flsh", "radon"),
    ("FL-SH radOFF", "flsh", "radoff"),
    ("SNB radON",    "snb",  "radon"),
    ("SNB radOFF",   "snb",  "radoff"),
]
# 2×2 网格: rows = 模型, cols = 辐射
GRID_ORDER = [["FL-SH radON", "FL-SH radOFF"], ["SNB radON", "SNB radOFF"]]

NC_0351 = 9.05e21
RHO_SOLID = C.PARAMS["tar1"]["rho"]


# ══════════════════════════════════════════════════════════════
def load_all(prefix: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for name, model, tag in LEGS4:
        d = PC.resolve_outdir(model, f"{prefix}{tag}")
        frs = PC.load_series(d)
        out[name] = frs
        C.log(f"{name:<14} {d.parent.name}/{d.name}: {len(frs)} chk 帧",
              "OK" if frs else "WARN")
    return out


def t_window(series: Dict[str, List[Dict[str, Any]]]) -> Tuple[float, float]:
    """四腿共同时间交集 (严格: 取 max 起点 / min 终点), 便于公平比较。"""
    s = [f[0]["t"] for f in series.values() if f]
    e = [f[-1]["t"] for f in series.values() if f]
    if not s:
        return 0.0, 1.0
    t0, t1 = max(s), min(e)
    return (t0, t1) if t1 > t0 else (min(s), max(e))


# ══════════════════════════════════════════════════════════════
# 图 1: 2×2 四联时空彩图
# ══════════════════════════════════════════════════════════════
def fig_pcolor4(series: Dict[str, List[Dict[str, Any]]], var: str,
                out_dir: Path, tag: str) -> Optional[Path]:
    grids: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for name, _, _ in LEGS4:
        if series.get(name):
            g = PC.build_xt(series[name], var)
            if g is not None:
                grids[name] = g
    if not grids:
        C.log(f"  {var}: 无数据, 跳过", "WARN")
        return None

    q = PC.QUANTITIES[var]
    allv = np.concatenate([g[2].ravel() for g in grids.values()])
    allv = allv[np.isfinite(allv)]
    use_log = bool(q["log"])
    if use_log:
        pos = allv[allv > 0]
        floor = (float(pos.min()) * 0.5) if pos.size else 1e-30
        norm = LogNorm(vmin=max(float(np.maximum(allv, floor).min()), floor * 1.0000001),
                       vmax=float(np.maximum(allv, floor).max()))
        cbl = f"{q['label']}  [{q['unit']}]  (log)"
    else:
        vmin, vmax = float(allv.min()), float(allv.max())
        vmax = vmax if vmax > vmin else vmin + abs(vmin) * 1e-3 + 1e-30
        floor = None
        norm = Normalize(vmin=vmin, vmax=vmax)
        cbl = f"{q['label']}  [{q['unit']}]"

    fig, axes = plt.subplots(2, 2, figsize=(17.5, 12.6), sharex=True, sharey=True,
                             constrained_layout=False)
    fig.subplots_adjust(left=0.072, right=0.885, top=0.888, bottom=0.070,
                        hspace=0.14, wspace=0.10)
    im = None
    for r, row in enumerate(GRID_ORDER):
        for c, name in enumerate(row):
            ax = axes[r][c]
            if name not in grids:
                ax.text(0.5, 0.5, "no data", ha="center", va="center",
                        transform=ax.transAxes, fontsize=20, color="0.45")
                continue
            t_ns, x_um, Z = grids[name]
            if floor is not None:
                Z = np.where(np.isfinite(Z) & (Z > 0), Z, floor)
            ext = (float(x_um.min()), float(x_um.max()),
                   float(t_ns.min()), float(t_ns.max()))
            im = ax.imshow(Z, origin="lower", aspect="auto", extent=ext,
                           cmap=q["cmap"], norm=norm,
                           interpolation=PC.DEFAULT_SHADING, rasterized=True)
            ax.set_title(name, fontsize=22, pad=7)
            ax.tick_params(labelsize=18, width=2.0)
            for s in ax.spines.values():
                s.set_linewidth(2.0)
            if c == 0:
                ax.set_ylabel("Time  [ns]", fontsize=21)
            if r == 1:
                ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=21)

    fig.suptitle(f"{q['title']} — radiation-ON/OFF 2x2 matrix   "
                 f"(x-t, source: chk)", fontsize=24, y=0.952)
    if im is not None:
        cax = fig.add_axes([0.900, 0.070, 0.022, 0.818])
        cb = fig.colorbar(im, cax=cax)
        cb.set_label(cbl, fontsize=21)
        cb.ax.tick_params(labelsize=18, width=2.0)
        cb.outline.set_linewidth(2.0)
        if use_log:
            cb.ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
            cb.ax.yaxis.set_minor_locator(
                plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * 0.1)))
            cb.ax.yaxis.set_minor_formatter(plt.NullFormatter())
        else:
            cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
    return PC.save_fig(fig, out_dir / f"xt4_{var}_{tag}.png")


# ══════════════════════════════════════════════════════════════
# 图 2: 2×2 四联 10 时刻剖面 (同格内 radON 实线 / radOFF 虚线 叠加)
# ══════════════════════════════════════════════════════════════
def fig_profiles4(series: Dict[str, List[Dict[str, Any]]], var: str,
                  out_dir: Path, tag: str, n_times: int, twin: Tuple[float, float],
                  xrange: Optional[Tuple[float, float]]) -> Optional[Path]:
    q = PC.QUANTITIES[var]
    use_log_y = bool(q["log"])

    # 预取曲线: panels[(model, rad)] = [(t_actual, x, v), ...]
    panels: Dict[Tuple[str, str], List[Tuple[float, np.ndarray, np.ndarray]]] = {}
    ymin, ymax = np.inf, -np.inf
    for name, model, rad in LEGS4:
        frs = series.get(name) or []
        if not frs:
            continue
        picks = PC.pick_even(frs, n_times, twin)
        lst: List[Tuple[float, np.ndarray, np.ndarray]] = []
        for _, fr in picks:
            v = PC.convert(fr, var)
            if v is None:
                continue
            x = np.asarray(fr["x_um"], dtype=float)
            v = np.asarray(v, dtype=float)
            if xrange:
                m = (x >= xrange[0]) & (x <= xrange[1])
                if not np.any(m):
                    continue
                x, v = x[m], v[m]
            fin = v[np.isfinite(v)]
            if fin.size:
                ymin, ymax = min(ymin, float(fin.min())), max(ymax, float(fin.max()))
            lst.append((fr["t"], x, v))
        panels[(model, rad)] = lst
    if not np.isfinite(ymin):
        C.log(f"  {var}: 无有效数据, 跳过", "WARN")
        return None

    if use_log_y and ymin > 0:
        ylim = (max(ymin, ymax * 1e-9), ymax)
    else:
        pad = 0.04 * (ymax - ymin) if ymax > ymin else 0.05 * abs(ymax) + 1e-30
        ylim = (ymin - pad, ymax + pad)
        use_log_y = False

    cmap = plt.get_cmap("viridis")
    t_all = [t for lst in panels.values() for t, _, _ in lst]
    t_lo, t_hi = (min(t_all), max(t_all)) if t_all else (0.0, 1.0)
    trange = (t_hi - t_lo) or 1.0

    fig, axes = plt.subplots(2, 2, figsize=(17.5, 12.8), sharex=True, sharey=True,
                             constrained_layout=False)
    fig.subplots_adjust(left=0.070, right=0.878, top=0.884, bottom=0.070,
                        hspace=0.13, wspace=0.10)
    for r, row in enumerate(GRID_ORDER):
        for c, name in enumerate(row):
            ax = axes[r][c]
            model, rad = name.split()[0], ("radON" if "radON" in name else "radOFF")
            mkey = "flsh" if "FL-SH" in name else "snb"
            rkey = "radon" if "radON" in name else "radoff"
            lst = panels.get((mkey, rkey), [])
            if not lst:
                ax.text(0.5, 0.5, "no data", ha="center", va="center",
                        transform=ax.transAxes, fontsize=20, color="0.45")
                continue
            ls = "-" if rkey == "radon" else "--"
            for t, x, v in lst:
                vp = np.where(v > 0, v, np.nan) if use_log_y else v
                frac = 0.06 + 0.90 * (t - t_lo) / trange
                ax.plot(x, vp, color=cmap(frac), lw=2.6, ls=ls,
                        solid_capstyle="round")
            ax.set_title(name, fontsize=22, pad=7)
            ax.tick_params(labelsize=18, width=2.0)
            for s in ax.spines.values():
                s.set_linewidth(2.0)
            ax.grid(alpha=0.25, lw=0.9, which="both")
            if use_log_y:
                ax.set_yscale("log")
                ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
                ax.yaxis.set_minor_locator(
                    plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * 0.1)))
                ax.yaxis.set_minor_formatter(plt.NullFormatter())
            ax.set_ylim(ylim)
            if c == 0:
                ax.set_ylabel(PC.axis_label(var), fontsize=21)
            if r == 1:
                ax.set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=21)

    fig.suptitle(f"{q['title']} — 4 legs, {n_times} times   "
                 f"(solid = radON, dashed = radOFF; source: chk)",
                 fontsize=24, y=0.950)
    cax = fig.add_axes([0.892, 0.070, 0.020, 0.814])
    sm = plt.cm.ScalarMappable(norm=Normalize(vmin=t_lo * 1e9, vmax=t_hi * 1e9),
                               cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("Simulation time  [ns]", fontsize=21)
    cb.ax.tick_params(labelsize=18, width=2.0)
    cb.outline.set_linewidth(2.0)
    cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
    return PC.save_fig(fig, out_dir / f"prof4_{var}_{tag}.png")


# ══════════════════════════════════════════════════════════════
# 定量: 烧蚀面 / 致密面密度 / Trad
# ══════════════════════════════════════════════════════════════
def frame_metrics(fr: Dict[str, Any]) -> Optional[Dict[str, float]]:
    rho = fr.get("dens")
    if rho is None:
        return None
    x = np.asarray(fr["x_um"], float)
    rho = np.asarray(rho, float)
    sel = x <= 0.0                       # CH 靶侧
    if not np.any(sel):
        return None
    xs, rs = x[sel], rho[sel]
    if xs.size < 5:
        return None
    drho = np.abs(np.gradient(rs, xs))
    band = (rs > 0.02 * RHO_SOLID) & (rs < 0.98 * RHO_SOLID)
    x_a = float(xs[np.where(band)[0][int(np.argmax(drho[band]))]]) \
        if np.any(band) else np.nan

    target = 0.5 * RHO_SOLID
    x_solid = np.nan
    above = np.where(rs >= target)[0]
    if above.size:
        i1 = above[-1]
        if i1 + 1 < rs.size and rs[i1 + 1] < target and rs[i1 + 1] != rs[i1]:
            x_solid = float(xs[i1] + (target - rs[i1]) * (xs[i1 + 1] - xs[i1])
                            / (rs[i1 + 1] - rs[i1]))
        else:
            x_solid = float(xs[i1])
    dense = rs >= target
    M_dense = (float(np.trapezoid(rs[dense], xs[dense]) * 1e-4)
               if np.count_nonzero(dense) >= 2 else np.nan)

    nele = PC.convert(fr, "nele")
    x_c = np.nan
    if nele is not None:
        ne = np.asarray(nele, float)
        lo = x_a if np.isfinite(x_a) else 0.0
        idx = np.where((x >= lo) & (x <= lo + 80.0) & (ne >= NC_0351))[0]
        if idx.size:
            i1 = idx[-1]
            if i1 + 1 < ne.size and ne[i1 + 1] < NC_0351 and ne[i1 + 1] != ne[i1]:
                x_c = float(x[i1] + (NC_0351 - ne[i1]) * (x[i1 + 1] - x[i1])
                            / (ne[i1 + 1] - ne[i1]))
            else:
                x_c = float(x[i1])
    return {
        "t_ns": fr["t"] * 1e9, "x_a_um": x_a, "x_solid_um": x_solid,
        "x_c_um": x_c, "M_dense_gcm2": M_dense,
        "rho_max": float(np.nanmax(rs)),
        "Mt": float(np.trapezoid(rho, x) * 1e-4),
        "te_max": float(np.nanmax(PC.convert(fr, "tele"))) if "tele" in fr else np.nan,
        "ti_max": float(np.nanmax(PC.convert(fr, "tion"))) if "tion" in fr else np.nan,
        "tr_max": float(np.nanmax(PC.convert(fr, "trad"))) if "trad" in fr else np.nan,
    }


def rate_abl(rows: List[Dict[str, float]]) -> Tuple[float, float]:
    """(M0, Ṁ_abl) — 后 30% 时段线性拟合 Ṁ = -dM_dense/dt。"""
    if len(rows) < 4:
        return float("nan"), float("nan")
    t = np.array([r["t_ns"] for r in rows]) * 1e-9
    M = np.array([r["M_dense_gcm2"] for r in rows])
    ok = np.isfinite(M) & np.isfinite(t)
    if ok.sum() < 4:
        return float("nan"), float("nan")
    t, M = t[ok], M[ok]
    M0 = float(M[0])
    i0 = max(0, len(t) - max(3, len(t) * 30 // 100))
    return M0, -float(np.polyfit(t[i0:], M[i0:], 1)[0])


def main() -> int:
    ap = argparse.ArgumentParser(description="t004 四腿对比 (图 + 定量)")
    ap.add_argument("--tag-prefix", default="")
    ap.add_argument("--n-times", type=int, default=10)
    ap.add_argument("--xrange", nargs=2, type=float, default=None,
                    metavar=("XMIN", "XMAX"))
    ap.add_argument("--vars", nargs="*", default=None)
    args = ap.parse_args()

    tag = args.tag_prefix.rstrip("_") or "full"
    variables = list(PC.QUANTITIES) if not args.vars else list(args.vars)

    print("\n" + "=" * 78)
    print(f" t004 四腿对比 (辐射开关 2×2)   {C.stamp()}   数据 tag = '{args.tag_prefix}'")
    print("=" * 78)

    series = load_all(args.tag_prefix)
    have = [n for n, _, _ in LEGS4 if series.get(n)]
    if not have:
        C.log("四腿均无 chk 数据", "ERROR")
        return 1
    twin = t_window(series)
    C.log(f"四腿共同时间窗: {twin[0]*1e9:.4f} .. {twin[1]*1e9:.4f} ns "
          f"(已有数据 {len(have)}/4 腿)", "INFO")

    pdir = C.results_dir("pcolor")
    rdir = C.results_dir("profiles")
    adir = C.results_dir("ablation")
    cdir = C.results_dir("compare")
    xrange = tuple(args.xrange) if args.xrange else None

    # 图
    for v in variables:
        fig_pcolor4(series, v, pdir, tag)
        fig_profiles4(series, v, rdir, tag, args.n_times, twin, xrange)

    # ── 定量 ────────────────────────────────────────────────
    metrics: Dict[str, List[Dict[str, float]]] = {}
    for name, model, rad in LEGS4:
        rows = [m for m in (frame_metrics(f) for f in (series.get(name) or []))
                if m is not None]
        rows.sort(key=lambda r: r["t_ns"])
        metrics[name] = rows

    hdr = (f"{'腿':<14}{'帧':>4}{'t末[ns]':>9}{'x_a[µm]':>9}{'M0[1e-3]':>10}"
           f"{'M末[1e-3]':>11}{'Ṁ[g/cm²/s]':>13}{'ρmax':>8}"
           f"{'Te_max':>9}{'Tr_max':>10}")
    print("\n" + hdr)
    print("-" * len(hdr))
    summary: Dict[str, Dict[str, float]] = {}
    for name, model, rad in LEGS4:
        rows = metrics[name]
        if not rows:
            print(f"{name:<14}  (无数据)")
            continue
        M0, rate = rate_abl(rows)
        L = rows[-1]
        summary[name] = {"M0": M0, "rate": rate, **L}
        print(f"{name:<14}{len(rows):>4}{L['t_ns']:>9.3f}{L['x_a_um']:>9.2f}"
              f"{M0*1e3:>10.4f}{L['M_dense_gcm2']*1e3:>11.4f}"
              f"{rate:>13.4e}{L['rho_max']:>8.3f}{L['te_max']:>9.1f}"
              f"{L['tr_max']:>10.3f}")

    # ── 归属分解 ────────────────────────────────────────────
    print("\n  ── 辐射开关的效应 (同模型内 radON/radOFF) ──────────")
    for model, tag_on, tag_off, ref in (("FL-SH", "FL-SH radON", "FL-SH radOFF", "flsh"),
                                        ("SNB", "SNB radON", "SNB radOFF", "snb")):
        a, b = summary.get(tag_on), summary.get(tag_off)
        if not a or not b:
            continue
        if np.isfinite(a["rate"]) and np.isfinite(b["rate"]) and a["rate"]:
            print(f"    {model}: Ṁ 辐射开 {a['rate']:.4e} / 辐射关 {b['rate']:.4e} "
                  f"→ 关辐射使其 **{b['rate']/a['rate']:.3f}×**")
        print(f"          x_a: {a['x_a_um']:.2f} vs {b['x_a_um']:.2f} µm； "
              f"Trad_max: {a['tr_max']:.3f} vs {b['tr_max']:.3f} eV")

    print("\n  ── 模型效应 (同为 radON 时 SNB vs FL-SH) ───────────")
    a, b = summary.get("FL-SH radON"), summary.get("SNB radON")
    if a and b and np.isfinite(a["rate"]) and np.isfinite(b["rate"]) and a["rate"]:
        print(f"    radON : SNB/FL-SH = {b['rate']/a['rate']:.3f}×  "
              f"(x_a {b['x_a_um']:.2f} vs {a['x_a_um']:.2f} µm)")
    a, b = summary.get("FL-SH radOFF"), summary.get("SNB radOFF")
    if a and b and np.isfinite(a["rate"]) and np.isfinite(b["rate"]) and a["rate"]:
        print(f"    radOFF: SNB/FL-SH = {b['rate']/a['rate']:.3f}×  "
              f"(x_a {b['x_a_um']:.2f} vs {a['x_a_um']:.2f} µm)")

    # ── 落盘 ────────────────────────────────────────────────
    csv_out = adir / f"ablation_4way_{tag}.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["leg", "t_ns", "x_a_um", "x_solid_um", "x_c_um",
                    "M_dense_gcm2", "Mt", "rho_max", "te_max", "ti_max", "tr_max"])
        for name, _, _ in LEGS4:
            for r in metrics[name]:
                w.writerow([name] + [r[k] for k in
                           ("t_ns", "x_a_um", "x_solid_um", "x_c_um",
                            "M_dense_gcm2", "Mt", "rho_max", "te_max",
                            "ti_max", "tr_max")])
    C.log(f"时间序列表 → {csv_out}", "OK")

    sm = cdir / f"summary_4way_{tag}.md"
    with sm.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# t004 四腿定量汇总 (辐射开关 2×2)\n\n")
        fh.write(f"数据 tag: `{args.tag_prefix}`；共同时间窗 "
                 f"{twin[0]*1e9:.4f}–{twin[1]*1e9:.4f} ns\n\n")
        fh.write("| 腿 | 帧 | t末 [ns] | x_a [µm] | M0 [1e-3 g/cm²] | "
                 "M末 [1e-3 g/cm²] | Ṁ_abl [g/cm²/s] | ρ_max | Te_max [eV] | Trad_max [eV] |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for name, _, _ in LEGS4:
            s = summary.get(name)
            if not s:
                fh.write(f"| {name} | — | — | — | — | — | — | — | — | — |\n")
                continue
            fh.write(f"| {name} | {len(metrics[name])} | {s['t_ns']:.3f} | "
                     f"{s['x_a_um']:.2f} | {s['M0']*1e3:.4f} | "
                     f"{s['M_dense_gcm2']*1e3:.4f} | {s['rate']:.4e} | "
                     f"{s['rho_max']:.3f} | {s['te_max']:.1f} | {s['tr_max']:.3f} |\n")
        fh.write("\n## 归属分解\n\n")
        for model, kon, koff in (("FL-SH", "FL-SH radON", "FL-SH radOFF"),
                                 ("SNB", "SNB radON", "SNB radOFF")):
            a, b = summary.get(kon), summary.get(koff)
            if a and b and np.isfinite(a["rate"]) and a["rate"]:
                fh.write(f"- **{model}**: 关辐射 → Ṁ 变为 **{b['rate']/a['rate']:.3f}×** "
                         f"({a['rate']:.4e} → {b['rate']:.4e} g/cm²/s)\n")
        a, b = summary.get("FL-SH radON"), summary.get("SNB radON")
        if a and b and np.isfinite(a["rate"]) and a["rate"]:
            fh.write(f"- **辐射开时 SNB/FL-SH** = **{b['rate']/a['rate']:.3f}×**\n")
        a, b = summary.get("FL-SH radOFF"), summary.get("SNB radOFF")
        if a and b and np.isfinite(a["rate"]) and a["rate"]:
            fh.write(f"- **辐射关时 SNB/FL-SH** = **{b['rate']/a['rate']:.3f}×**\n")
    C.log(f"汇总表 → {sm}", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
