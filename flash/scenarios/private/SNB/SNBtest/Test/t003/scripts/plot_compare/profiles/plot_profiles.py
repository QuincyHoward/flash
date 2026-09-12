"""t003 对比绘图 (2/2) —— 上下两联「多时刻剖面系列图」

用途
----
对 7 个物理量各出一张 **上下两联** 图, 每联画 **10 个时刻** 的空间分布剖面:
    上联 = FL-SH (flux-limited Spitzer-Härm, local)
    下联 = SNB   (nonlocal electron heat transport)

时刻选取 (用户指定)
------------------
在**两腿共同时间窗**内**平均取 10 个时刻** (含端点, np.linspace)。
因 chk 帧数 (16) > 10, 每个目标时刻取**最近的真实帧**, 不做插值 —— 保证
曲线是真实仿真状态而非重采样产物。逐曲线标注实际时刻 (t = ... ns)。

轴 (用户指定, 线性)
------------------
    x 轴 = 空间 [µm], 线性
    y 轴 = 物理量, **默认线性** (唯 nele 因跨十余个数量级用对数 y 轴)

数据源
------
**chk 文件** (非 plt)。

用法 (在 t003 目录下)
---------------------
    python scripts/plot_compare/profiles/plot_profiles.py
    python scripts/plot_compare/profiles/plot_profiles.py --tag chk_full
    python scripts/plot_compare/profiles/plot_profiles.py --n-times 10 --vars tele dens
    python scripts/plot_compare/profiles/plot_profiles.py --xrange -60 30   # 局部放大
    python scripts/plot_compare/profiles/plot_profiles.py --xlog           # nele 也线性
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1] / "common"))

import numpy as np                      # noqa: E402
import matplotlib.pyplot as plt         # noqa: E402
from matplotlib.colors import LogNorm, Normalize  # noqa: E402
from matplotlib.lines import Line2D     # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

import plot_common as PC                # noqa: E402


# ══════════════════════════════════════════════════════════════
def _curve_data(frame: Dict[str, Any], var: str,
                xrange: Optional[Tuple[float, float]] = None
                ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """取某帧的 (x_um, 换算后的物理量), 可按 xrange 裁剪。"""
    v = PC.convert(frame, var)
    if v is None:
        return None
    x = np.asarray(frame["x_um"], dtype=float)
    v = np.asarray(v, dtype=float)
    if x.size != v.size:
        return None
    if xrange is not None:
        sel = (x >= xrange[0]) & (x <= xrange[1])
        if not np.any(sel):
            return None
        x, v = x[sel], v[sel]
    return x, v


def _leg_range(picks_m: List[Tuple[float, Dict[str, Any]]], var: str,
               xrange: Optional[Tuple[float, float]]
               ) -> Tuple[float, float]:
    """求某腿全部曲线的 (min, max)。无有效数据 → (inf, -inf)。"""
    lo, hi = np.inf, -np.inf
    for _, fr in picks_m:
        cd = _curve_data(fr, var, xrange)
        if cd is None:
            continue
        v = cd[1][np.isfinite(cd[1])]
        if v.size:
            lo = min(lo, float(v.min()))
            hi = max(hi, float(v.max()))
    return lo, hi


def plot_profiles(series: Dict[str, List[Dict[str, Any]]], var: str,
                  out_dir: Path, tag: str, n_times: int,
                  t_window: Tuple[float, float],
                  xrange: Optional[Tuple[float, float]], ylog: bool,
                  per_leg: bool = False
                  ) -> Optional[Path]:
    """单物理量 → 一张上下两联「10 时刻剖面系列图」。

    per_leg=False (默认): 两联**共享** y 范围 → 严格可比。
    per_leg=True         : 每联独立 y 范围 → 量值悬殊时各自结构清晰
                           (left label 会追加 independent scale 提示)。
    """
    picks: Dict[str, List[Tuple[float, Dict[str, Any]]]] = {}
    for m in ("flsh", "snb"):
        frs = series.get(m) or []
        if frs:
            picks[m] = PC.pick_even(frs, n_times, t_window)
    if not picks:
        PC.C.log(f"  {var}: 两腿均无数据, 跳过", "WARN")
        return None

    # ── y 轴范围: 共享 或 逐腿 ─────────────────────────────────
    ranges: Dict[str, Tuple[float, float]] = {}
    if per_leg:
        for m, lst in picks.items():
            lo, hi = _leg_range(lst, var, xrange)
            if not np.isfinite(lo):
                lo, hi = 0.0, 1.0
            ranges[m] = (lo, hi)
    else:
        lo, hi = np.inf, -np.inf
        for m, lst in picks.items():
            a, b = _leg_range(lst, var, xrange)
            lo, hi = min(lo, a), max(hi, b)
        if not np.isfinite(lo):
            PC.C.log(f"  {var}: 无有效数据, 跳过", "WARN")
            return None
        ranges = {m: (lo, hi) for m in picks}

    def _finish_ylim(lo: float, hi: float) -> Tuple[float, float]:
        if ylog and lo > 0:
            return max(lo, hi * 1e-9), hi
        pad = 0.04 * (hi - lo) if hi > lo else 0.05 * abs(hi) + 1e-30
        return lo - pad, hi + pad

    ylims = {m: _finish_ylim(*r) for m, r in ranges.items()}
    use_log_y = ylog and all(r[0] > 0 for r in ranges.values())
    if not per_leg:
        ymin, ymax = ylims[next(iter(ylims))]
    else:
        ymin, ymax = 0.0, 1.0          # 逐腿模式不用统一 ylim

    # ── 时刻 → 色阶 (viridis: 暗=早期, 亮=晚期, 感知单调) ────────
    # ★ matplotlib >= 3.9 移除了 matplotlib.cm.get_cmap, 必须用
    #   Colormap 对象直接调用 (plt.get_cmap 亦已弃用)。
    cmap = plt.get_cmap("viridis")
    # 以 FL-SH 的目标时刻为准配色 (两腿时刻几乎相同)
    ref_times = [tt for tt, _ in picks.get("flsh", picks.get("snb", []))]
    if not ref_times:
        return None
    t_lo, t_hi = min(ref_times), max(ref_times)
    trange = (t_hi - t_lo) or 1.0

    def col_of(tt: float):
        return cmap(0.06 + 0.90 * (tt - t_lo) / trange)

    fig, axes = plt.subplots(2, 1, figsize=(13.0, 12.4), sharex=True,
                             sharey=True, constrained_layout=False)
    # ★ 布局要点: suptitle 与上联 panel title 必须留足垂直间距, 否则两者重叠。
    fig.subplots_adjust(left=0.104, right=0.856, top=0.889, bottom=0.078,
                        hspace=0.15)

    legend_handles: List[Line2D] = []
    for ax, m in zip(axes, ("flsh", "snb")):
        got = picks.get(m)
        if not got:
            ax.text(0.5, 0.5, f"{PC.SHORT_LABELS[m]}: no data",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=22, color="0.4")
            ax.set_ylabel(PC.axis_label(var))
            continue
        for tt, fr in got:
            cd = _curve_data(fr, var, xrange)
            if cd is None:
                continue
            x, v = cd
            vp = np.where(v > 0, v, np.nan) if use_log_y else v
            c = col_of(tt)
            ax.plot(x, vp, color=c, lw=2.6, solid_capstyle="round",
                    label=f"{fr['t']*1e9:.3f} ns")
        ax.set_ylabel(PC.axis_label(var) +
                      ("\n(independent scale)" if per_leg else ""), fontsize=22)
        ax.set_title(PC.LABELS[m], fontsize=23, pad=9)
        ax.tick_params(axis="both", labelsize=20, width=2.0)
        for s in ax.spines.values():
            s.set_linewidth(2.0)
        ax.grid(alpha=0.25, lw=0.9, which="both")
        lo_m, hi_m = ylims.get(m, (ymin, ymax))
        if use_log_y:
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
            ax.yaxis.set_minor_locator(
                plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * 0.1)))
            ax.yaxis.set_minor_formatter(plt.NullFormatter())
            ax.set_ylim(lo_m, hi_m)
        else:
            ax.set_ylim(lo_m, hi_m)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
        # 每联自己出图例 (10 条曲线, 两列排布避免压住数据)
        ax.legend(loc="best", fontsize=15, ncol=2, framealpha=0.88,
                  handlelength=1.7, columnspacing=1.0, labelspacing=0.35,
                  title="Simulation time", title_fontsize=16, borderpad=0.55)

    axes[-1].set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=22)
    if xrange:
        axes[-1].set_xlim(*xrange)
    else:
        x_all = np.asarray(series["flsh"][0]["x_um"] if series.get("flsh")
                           else series["snb"][0]["x_um"], dtype=float)
        axes[-1].set_xlim(float(x_all.min()), float(x_all.max()))

    q = PC.QUANTITIES[var]
    ytype = "log" if use_log_y else "linear"
    scale_txt = "independent y" if per_leg else f"shared {ytype} y"
    fig.suptitle(f"{q['title']}  —  FL-SH vs SNB   "
                 f"({len(ref_times)} times, {scale_txt}, source: chk)",
                 fontsize=25, y=0.952)

    # ── 右侧独立色标条: 时刻颜色映射 ────────────────────────────
    cax = fig.add_axes([0.876, 0.078, 0.022, 0.806])
    sm = plt.cm.ScalarMappable(norm=Normalize(vmin=t_lo * 1e9, vmax=t_hi * 1e9),
                               cmap=cmap)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("Simulation time  [ns]", fontsize=22)
    cb.ax.tick_params(labelsize=20, width=2.0)
    cb.outline.set_linewidth(2.0)
    cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=7))

    # ★ 文件名必须区分 shared / per-leg, 否则逐腿定标版会**覆盖**共享定标版
    suf = "_perleg" if per_leg else ""
    out = out_dir / f"profiles_{var}_{tag}{suf}.png"
    return PC.save_fig(fig, out)


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(
        description="t003 上下两联多时刻剖面系列图 (chk 数据源)")
    ap.add_argument("--tag", default="chk_full", help="输出子目录 tag")
    ap.add_argument("--tag-flsh", default=None)
    ap.add_argument("--tag-snb", default=None)
    ap.add_argument("--vars", nargs="*", default=None,
                    help=f"要画的物理量 (默认全部: {' '.join(PC.QUANTITIES)})")
    ap.add_argument("--n-times", type=int, default=10,
                    help="平均选取的时刻数 (默认 10)")
    ap.add_argument("--name-suffix", default="",
                    help="输出文件名后缀 (数据 tag 与文件名解耦)")
    ap.add_argument("--out-sub", default="profiles", help="results/ 下的子目录")
    ap.add_argument("--xrange", nargs=2, type=float, default=None,
                    metavar=("XMIN", "XMAX"), help="x 轴裁剪范围 [µm]")
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--xlog", action="store_true",
                    help="强制 y 轴线性 (即使 nele)")
    ap.add_argument("--per-leg", action="store_true",
                    help="每联独立 y 范围 (两腿量值悬殊时用, 如 trad)")
    args = ap.parse_args()

    variables = list(PC.QUANTITIES) if not args.vars else list(args.vars)
    bad = [v for v in variables if v not in PC.QUANTITIES]
    if bad:
        PC.C.log(f"未知物理量: {bad}", "ERROR")
        return 2

    out_dir = PC.results_dir(args.out_sub)
    PC.C.log(f"输出目录: {out_dir}", "INFO")

    tag_map = {"flsh": args.tag_flsh or args.tag, "snb": args.tag_snb or args.tag}
    series: Dict[str, List[Dict[str, Any]]] = {}
    for m in ("flsh", "snb"):
        d = PC.resolve_outdir(m, tag_map[m])
        chks = PC.list_chk(d)
        PC.C.log(f"{PC.SHORT_LABELS[m]}: {d.name} → {len(chks)} chk 帧", "INFO")
        series[m] = PC.load_series(d, args.max_frames)

    if not any(series.values()):
        PC.C.log("两腿均无 chk 数据 —— 请先跑仿真", "ERROR")
        return 1

    # margin=0.0: 剖面图要覆盖完整时间窗端点, 不做内缩
    t0, t1 = PC.common_time_window(series, margin=0.0)
    PC.C.log(f"共同时间窗: {t0*1e9:.4f} .. {t1*1e9:.4f} ns   "
             f"平均取 {args.n_times} 时刻", "INFO")

    xrange = tuple(args.xrange) if args.xrange else None
    n_ok = 0
    for v in variables:
        ylog = bool(PC.QUANTITIES[v]["log"]) and not args.xlog
        p = plot_profiles(series, v, out_dir, args.tag + args.name_suffix, args.n_times,
                          (t0, t1), xrange, ylog, per_leg=args.per_leg)
        n_ok += 1 if p else 0

    print()
    PC.C.log(f"完成: {n_ok}/{len(variables)} 张剖面系列图 → {out_dir}", "OK")
    return 0 if n_ok else 1


if __name__ == "__main__":
    sys.exit(main())
