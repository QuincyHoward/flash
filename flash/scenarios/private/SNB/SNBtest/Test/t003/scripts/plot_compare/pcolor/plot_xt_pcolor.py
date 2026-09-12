"""t003 对比绘图 (1/2) —— 上下两联时空彩图 (x-t color map)

用途
----
对 7 个物理量各出一张 **上下两联** 图:
    上联 = FL-SH (flux-limited Spitzer-Härm, local)
    下联 = SNB   (nonlocal electron heat transport)

轴与色标 (用户指定, 全部线性):
    x 轴 = 空间 [µm], 线性
    y 轴 = 时间 [ns], 线性
    色标 = 物理量, 默认**线性**; 唯 `nele` 用**对数**色标

数据源
------
**chk 文件** (非 plt)。chk = FLASH 完整重启快照, 变量覆盖度 71 键 vs plt 的 ~25,
且不受 plot_var 12 项白名单上限约束。

单位换算
--------
FLASH 原生 CGS → 绘图单位, 见 plot_common.QUANTITIES / convert():
    tele/tion/trad : K        → eV      (/ 1.1604519e4)
    dens           : g/cm^3   → g/cm^3  (原样)
    pele/pres      : erg/cm^3 → Mbar    (* 1e-12)
    nele           : 离线推导 Ye·6.02e23·dens → cm^-3 (对数色标)

用法 (在 t003 目录下)
---------------------
    python scripts/plot_compare/pcolor/plot_xt_pcolor.py
    python scripts/plot_compare/pcolor/plot_xt_pcolor.py --tag chk_full
    python scripts/plot_compare/pcolor/plot_xt_pcolor.py --vars tele dens nele
    python scripts/plot_compare/pcolor/plot_xt_pcolor.py --symlog   # 非 nele 也用对数
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
from matplotlib.colors import LogNorm, Normalize, SymLogNorm  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

import plot_common as PC                # noqa: E402

CM_TO_UM = PC.CM_TO_UM
NS_PER_S = PC.NS_PER_S


# ══════════════════════════════════════════════════════════════
def _make_norm(data: np.ndarray, var: str, log_force: bool,
               log_floor: Optional[float]) -> Tuple[Any, str, Optional[float]]:
    """依物理量性质构造色标归一化器 → (norm, 色标标签, 高亮线位置)。

    ★ 设计原则: **线性色标优先** (用户默认要求)。仅当 (a) 该量在表中标记 log
      (nele), 或 (b) 显式 --symlog 时才用对数型。
      对数色标下必须处理 <=0 的退化格点 (真空中 dens→1e-6, nele→1e18 仍 >0,
      但 AMR/边界可能产生严格 0) —— 否则 LogNorm 会静默丢弃整片区域。
    """
    q = PC.QUANTITIES[var]
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return Normalize(), f"{q['label']}  [{q['unit']}]", None

    vmin, vmax = float(finite.min()), float(finite.max())

    use_log = bool(q["log"]) or log_force
    if use_log:
        floor = log_floor
        if floor is None:
            pos = finite[finite > 0]
            floor = (float(pos.min()) if pos.size else 1e-30) * 0.5
        d = np.maximum(data, floor)                    # 钳到正下界
        lo = max(float(d.min()), floor * 1.0000001)
        hi = float(d.max())
        if not (hi > lo > 0):
            hi = lo * 10.0
        norm = LogNorm(vmin=lo, vmax=hi)
        lbl = f"{q['label']}  [{q['unit']}]  (log)"
        return norm, lbl, floor
    if vmin == vmax:
        vmax = vmin + abs(vmin) * 1e-3 + 1e-30
    return Normalize(vmin=vmin, vmax=vmax), f"{q['label']}  [{q['unit']}]", None


def _apply_floor(Z: np.ndarray, floor: Optional[float]) -> np.ndarray:
    """对数色标时把非正值钳到 floor, 避免 LogNorm 吞掉数据。"""
    if floor is None:
        return Z
    return np.where(np.isfinite(Z) & (Z > 0), Z, floor)


def plot_quantity(series: Dict[str, List[Dict[str, Any]]], var: str,
                  out_dir: Path, tag: str, log_force: bool,
                  shading: str, vlines: Tuple[float, ...] = (),
                  per_leg: bool = False) -> Optional[Path]:
    """单物理量 → 一张上下两联时空彩图。

    per_leg=False (默认): 两联**共享**色标 → 严格可比, 但量值悬殊时弱腿会糊掉。
    per_leg=True         : 每联独立自动定标 → 各自结构清晰, 但色标不可直接比较
                           (title 会标注 independent scale 提醒读者)。
    """
    grids: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for m in ("flsh", "snb"):
        if not series.get(m):
            continue
        g = PC.build_xt(series[m], var)
        if g is not None:
            grids[m] = g
    if not grids:
        PC.C.log(f"  {var}: 两腿均无数据, 跳过", "WARN")
        return None

    # ── 色标归一化: 共享 或 逐腿 ────────────────────────────────
    norms: Dict[str, Any] = {}
    floors: Dict[str, Optional[float]] = {}
    cbl = f"{PC.QUANTITIES[var]['label']}  [{PC.QUANTITIES[var]['unit']}]"
    if per_leg:
        for m, (_, _, Z) in grids.items():
            n, l, fl = _make_norm(Z.ravel(), var, log_force, None)
            norms[m], floors[m] = n, fl
        cbl += "  (per-leg scale)"
    else:
        allv = np.concatenate([g[2].ravel() for g in grids.values()])
        allv = allv[np.isfinite(allv)]
        ref_norm, cbl, floor = _make_norm(allv, var, log_force, None)
        for m in grids:
            norms[m] = ref_norm
            floors[m] = floor
        if isinstance(ref_norm, LogNorm):
            cbl += "  (log)"

    fig, axes = plt.subplots(2, 1, figsize=(13.0, 12.2), sharex=True,
                             constrained_layout=False)
    # ★ 布局要点: suptitle 与上联 panel title 必须留足垂直间距, 否则两者重叠。
    #   top=0.892 留出 ~0.07 的标题带, hspace=0.16 隔开两联的 x 刻度与下联标题。
    fig.subplots_adjust(left=0.106, right=0.868, top=0.892, bottom=0.078,
                        hspace=0.16)

    extent = None
    ims: List[Any] = []
    for ax, m in zip(axes, ("flsh", "snb")):
        if m not in grids:
            ax.text(0.5, 0.5, f"{PC.SHORT_LABELS[m]}: no data",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=22, color="0.4")
            ax.set_ylabel("Time  [ns]")
            continue
        t_ns, x_um, Z = grids[m]
        Z = _apply_floor(Z, floors[m])
        norm = norms[m]
        if isinstance(norm, LogNorm):
            norm = LogNorm(vmin=norm.vmin, vmax=norm.vmax)
        # ★★ pcolormesh + **真实逐帧时间坐标**（不能用 imshow）:
        #    chk 按步数间隔输出 -> dt 变化 -> 帧时间间隔高度不均匀
        #    (实测 AMR 腿 1.36e-12..7.19e-11, 52.7x). imshow 的等间距假设
        #    会把时间轴局部拉偏数千个百分点, 造成"前沿速度不同"的假象.
        X, T = np.meshgrid(x_um, t_ns)
        im = ax.pcolormesh(X, T, Z, shading="auto",
                           cmap=PC.QUANTITIES[var]["cmap"], norm=norm,
                           rasterized=True)
        ims.append((m, im))
        for xv in vlines:
            ax.axvline(xv, color="w", lw=1.6, ls="--", alpha=0.75)
        ax.set_ylabel("Time  [ns]", fontsize=22)
        ax.tick_params(axis="both", labelsize=20, width=2.0)
        for s in ax.spines.values():
            s.set_linewidth(2.0)
        # 逐腿定标时把该腿的数值区间写进 panel title, 补偿色标不可比
        ttl = PC.LABELS[m]
        if per_leg:
            nz = Z[np.isfinite(Z)]
            if nz.size:
                ttl += f"   [{nz.min():.3g} .. {nz.max():.3g}]"
        ax.set_title(ttl, fontsize=23, pad=9)

    axes[-1].set_xlabel(r"Position  $x$  [$\mu$m]", fontsize=22)
    q = PC.QUANTITIES[var]
    fig.suptitle(f"{q['title']}  —  FL-SH vs SNB   (x-t diagram, source: chk)",
                 fontsize=25, y=0.955)

    if ims:
        pos = np.linspace(0.078, 0.892, len(ims) + 1)
        bar_h = (0.814 - 0.020 * (len(ims) - 1)) / len(ims)
        for i, (m, im) in enumerate(ims):
            y0 = 0.892 - (i + 1) * (bar_h + 0.020) + 0.020
            cax = fig.add_axes([0.888, max(y0, 0.078), 0.024, bar_h])
            cb = fig.colorbar(im, cax=cax)
            cb.set_label(cbl if len(ims) == 1 else "", fontsize=18)
            cb.ax.tick_params(labelsize=16, width=2.0)
            cb.outline.set_linewidth(2.0)
            nrm = norms.get(m)
            if isinstance(nrm, LogNorm):
                cb.ax.yaxis.set_major_locator(plt.LogLocator(base=10.0))
                cb.ax.yaxis.set_minor_locator(
                    plt.LogLocator(base=10.0, subs=tuple(np.arange(2, 10) * 0.1)))
                cb.ax.yaxis.set_minor_formatter(plt.NullFormatter())
            else:
                cb.ax.yaxis.set_major_locator(MaxNLocator(nbins=6))

    out = out_dir / f"xt_{var}_{tag}{'_perleg' if per_leg else ''}.png"
    return PC.save_fig(fig, out)


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="t003 上下两联时空彩图 (chk 数据源)")
    ap.add_argument("--tag", default="chk_full", help="输出子目录 tag")
    ap.add_argument("--tag-flsh", default=None, help="FL-SH 腿独立 tag (默认同 --tag)")
    ap.add_argument("--tag-snb", default=None, help="SNB 腿独立 tag (默认同 --tag)")
    ap.add_argument("--vars", nargs="*", default=None,
                    help=f"要画的物理量 (默认全部: {' '.join(PC.QUANTITIES)})")
    ap.add_argument("--name-suffix", default="",
                    help="输出文件名后缀 (数据 tag 与文件名解耦)")
    ap.add_argument("--out-sub", default="pcolor", help="results/ 下的子目录")
    ap.add_argument("--max-frames", type=int, default=0,
                    help="最大帧数 (0=全部; 建议 0 以保证时间分辨率)")
    ap.add_argument("--symlog", action="store_true",
                    help="对非 nele 量也强制对数色标")
    ap.add_argument("--per-leg", action="store_true",
                    help="每联独立自动定标 (两腿量值悬殊时用, 如 trad; "
                         "代价是色标不可直接比较)")
    ap.add_argument("--shading", default=PC.DEFAULT_SHADING,
                    choices=["nearest", "bilinear", "gaussian", "auto"])
    args = ap.parse_args()

    variables = list(PC.QUANTITIES) if not args.vars else list(args.vars)
    bad = [v for v in variables if v not in PC.QUANTITIES]
    if bad:
        PC.C.log(f"未知物理量: {bad}", "ERROR")
        return 2

    out_dir = PC.results_dir(args.out_sub)
    PC.C.log(f"输出目录: {out_dir}", "INFO")

    tag_map = {"flsh": args.tag_flsh or args.tag, "snb": args.tag_snb or args.tag}
    series = {}
    for m in ("flsh", "snb"):
        d = PC.resolve_outdir(m, tag_map[m])
        chks = PC.list_chk(d)
        PC.C.log(f"{PC.SHORT_LABELS[m]}: {d.name} → {len(chks)} chk 帧", "INFO")
        series[m] = PC.load_series(d, args.max_frames)

    if not any(series.values()):
        PC.C.log("两腿均无 chk 数据 —— 请先跑仿真", "ERROR")
        return 1
    t0, t1 = PC.common_time_window(series, margin=0.0)
    PC.C.log(f"共同时间窗: {t0*1e9:.4f} .. {t1*1e9:.4f} ns", "INFO")

    n_ok = 0
    for v in variables:
        p = plot_quantity(series, v, out_dir, args.tag + args.name_suffix, args.symlog,
                          args.shading, per_leg=args.per_leg)
        n_ok += 1 if p else 0

    print()
    PC.C.log(f"完成: {n_ok}/{len(variables)} 张时空彩图 → {out_dir}", "OK")
    return 0 if n_ok else 1


if __name__ == "__main__":
    sys.exit(main())
