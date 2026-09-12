"""t003 烧蚀速率定量分析 —— 从 chk 直接提取烧蚀面/临界密度面/烧蚀面密度

用途
----
用同一套判据同时处理 **SNB 腿** 与 **FL-SH 腿**(以及诊断变体), 输出可对照的
时间序列, 用于判断「SNB 烧蚀偏快」是物理还是代码。

判据定义 (全部基于质量密度 ρ(x) 与电子数密度 n_e(x), 二者均从 chk 读出)
--------------------------------------------------------------------------
1. **烧蚀面 x_a**: ρ 从固体密度向外跌落的"拐点"。取
     x_a(t) = argmax_x |dρ/dx|  且限定在 ρ > ρ_solid·cut_frac 的固体侧
   等价于密度剖面最陡处 (常规做法)。
2. **固体密度面 x_solid**: ρ = f_solid · ρ_solid 的位置 (默认 f=0.5)。
3. **临界密度面 x_c**: n_e = n_c (0.351 µm → 9.05e21 cm^-3), 线性插值。
4. **烧蚀面密度 M_abl**: 仍留在固体侧 (x < x_a) 的累计面密度
     M_abl(t) = ∫_{x_min}^{x_a} ρ dx   [g/cm²]
   烧蚀速率 Ṁ = dM_abl/dt。
5. **总面密度 M_tot**: ∫ ρ dx 全域, 用于守恒体检。

★ 单位: chk 原生 CGS (ρ [g/cm³], x [cm]) → 输出用 µm / g/cm²。

用法 (在 t003 目录下)
---------------------
    # 两腿对照
    python scripts/analysis/ablation_rate.py --tag full
    # SNB 诊断变体 vs FL-SH 基线
    python scripts/analysis/ablation_rate.py --tag-flsh full --tag-snb full_limiter \
        --label-snb "SNB(limiterON)" --out ablation_limiter.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_T003 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T003 / "scripts" / "plot_compare" / "common"))

import numpy as np                      # noqa: E402
import plot_common as PC                # noqa: E402
import t003_common as C                 # noqa: E402

NC_0351 = 9.05e21           # 临界电子数密度 [cm^-3] (0.351 µm)
RHO_SOLID = C.PARAMS["tar1"]["rho"]     # 1.04 g/cm^3


# ══════════════════════════════════════════════════════════════
def analyse_frame(fr: Dict[str, Any], f_solid: float = 0.5,
                  x_hi: float = 0.0) -> Optional[Dict[str, float]]:
    """对单帧算 §判据 1-5。x_hi = 固体侧上界 (CH 靶外表面, µm)。"""
    rho = fr.get("dens")
    if rho is None:
        return None
    x = np.asarray(fr["x_um"], dtype=float)
    rho = np.asarray(rho, dtype=float)
    sel = x <= x_hi                       # 只看 CH 靶一侧 (x<=0)
    if not np.any(sel):
        return None
    xs, rs = x[sel], rho[sel]
    if xs.size < 5:
        return None

    # ── 烧蚀面: 密度剖面最陡处 (限定在离开固体密度的过渡区) ──
    drho = np.abs(np.gradient(rs, xs))
    # 只在 ρ 介于 (0.02 .. 0.98)·ρ_solid 的过渡带里找最陡点, 避开 He 腔的噪声
    band = (rs > 0.02 * RHO_SOLID) & (rs < 0.98 * RHO_SOLID)
    if not np.any(band):
        x_a = np.nan
        slope = np.nan
    else:
        idxb = np.where(band)[0]
        j = idxb[int(np.argmax(drho[idxb]))]
        x_a = float(xs[j])
        slope = float(drho[j])

    # ── 固体密度面 ρ = f_solid·ρ_solid ──
    # ★ 必须**从外侧(x_hi)向内**扫: 靶板左端恒为固体, 从左侧扫会立刻命中边界,
    #   得到的不是烧蚀面而是域边界 (首版实现即犯此错)。
    target = f_solid * RHO_SOLID
    x_solid = np.nan
    above = np.where(rs >= target)[0]        # 索引升序 = x 升序
    if above.size:
        i1 = above[-1]                       # 最靠外侧的达标格点
        if i1 + 1 < rs.size and rs[i1 + 1] < target:
            r0, r1 = rs[i1], rs[i1 + 1]
            if r1 != r0:
                x_solid = float(xs[i1] + (target - r0) * (xs[i1 + 1] - xs[i1]) / (r1 - r0))
            else:
                x_solid = float(xs[i1])
        else:
            x_solid = float(xs[i1])

    # ── 稠密面密度 (鲁棒判据, 无需找面) ──
    #   M_dense(t) = ∫ ρ dx  over {ρ ≥ f_solid·ρ_solid}
    #   烧蚀把稠密物质移走 → M_dense 单调下降; 烧蚀速率 = -dM_dense/dt
    dense = rs >= target
    if np.count_nonzero(dense) >= 2:
        M_dense = float(np.trapezoid(rs[dense], xs[dense]) * 1e-4)   # [g/cm^2]
    else:
        M_dense = float("nan")

    # ── 临界密度面 n_e = n_c ──
    # ★ 三点关键 (三次迭代才收敛的判据):
    #   1) 必须取**最外侧**的跨越点 (solid CH 内部 n_e 远高于 n_c);
    #   2) 必须在 corona (x>0) 侧搜索 —— 若沿用 x<=0 的 sel 会被靶面截断;
    #   3) 但**不能全域搜** —— 激光入射口 (x≈233 µm) 会形成人为稠密斑,
    #      把"最外侧"拉到右边界。故限定在烧蚀面上方 80 µm 的 corona 窗口内。
    x_c = np.nan
    nele = PC.convert(fr, "nele")
    if nele is not None:
        ne_all = np.asarray(nele, dtype=float)
        lo = x_a if np.isfinite(x_a) else 0.0
        win = (x >= lo) & (x <= lo + 80.0)
        idx = np.where(win & (ne_all >= NC_0351))[0]
        if idx.size:
            i1 = idx[-1]                     # 窗口内最外侧达标点
            if i1 + 1 < ne_all.size and ne_all[i1 + 1] < NC_0351:
                n0, n1 = ne_all[i1], ne_all[i1 + 1]
                if n1 != n0:
                    x_c = float(x[i1] + (NC_0351 - n0) * (x[i1 + 1] - x[i1]) / (n1 - n0))
                else:
                    x_c = float(x[i1])
            else:
                x_c = float(x[i1])

    # ── 面密度 (梯形积分, 单位换算: g/cm^3 × µm → 1e-4 g/cm^2) ──
    def areal(xa: np.ndarray, ra: np.ndarray) -> float:
        if xa.size < 2:
            return float("nan")
        return float(np.trapezoid(ra, xa) * 1e-4)     # [g/cm^2]

    M_tot = areal(xs, rs)
    return {
        "t_ns": fr["t"] * 1e9,
        "x_a_um": x_a, "x_solid_um": x_solid, "x_c_um": x_c,
        "slope_max": slope,
        "M_dense_gcm2": M_dense, "M_tot_gcm2": M_tot,
        "rho_max": float(np.nanmax(rs)),
        "te_max_eV": float(np.nanmax(PC.convert(fr, "tele"))) if "tele" in fr else float("nan"),
    }


def analyse_leg(model: str, tag: str) -> List[Dict[str, float]]:
    d = PC.resolve_outdir(model, tag)
    frames = PC.load_series(d)
    if not frames:
        C.log(f"{model}/{tag}: 无 chk 数据", "WARN")
        return []
    out = [r for r in (analyse_frame(f) for f in frames) if r is not None]
    out.sort(key=lambda r: r["t_ns"])
    C.log(f"{PC.SHORT_LABELS[model]}/{tag}: {len(out)}/{len(frames)} 帧已分析", "OK")
    return out


def ablation_rate(rows: List[Dict[str, float]]) -> Tuple[float, float]:
    """稠密面密度的初始值 与 **末段** 平均烧蚀速率 [g/cm^2/s]。

    ★ 用**后 30% 时段**做线性拟合, 而非全程: 早期(激光上升沿前)几乎不烧蚀,
      全程拟合会把速率系统性拉低。
    """
    if len(rows) < 4:
        return float("nan"), float("nan")
    t = np.array([r["t_ns"] for r in rows]) * 1e-9
    M = np.array([r["M_dense_gcm2"] for r in rows])
    ok = np.isfinite(M) & np.isfinite(t)
    if ok.sum() < 4:
        return float("nan"), float("nan")
    t, M = t[ok], M[ok]
    M0 = float(M[0])
    n = len(t)
    i0 = max(0, n - max(3, n * 30 // 100))
    k = np.polyfit(t[i0:], M[i0:], 1)[0]
    return M0, -float(k)              # Ṁ_abl = -dM_dense/dt


def main() -> int:
    ap = argparse.ArgumentParser(description="t003 烧蚀速率定量分析")
    ap.add_argument("--tag", default="full")
    ap.add_argument("--tag-flsh", default=None)
    ap.add_argument("--tag-snb", default=None)
    ap.add_argument("--label-flsh", default="FL-SH")
    ap.add_argument("--label-snb", default="SNB")
    ap.add_argument("--f-solid", type=float, default=0.5)
    ap.add_argument("--out", default="ablation_rate.csv")
    args = ap.parse_args()

    tag_f = args.tag_flsh or args.tag
    tag_s = args.tag_snb or args.tag

    print("\n" + "=" * 74)
    print(f" t003 烧蚀速率定量分析   {C.stamp()}")
    print(f" 判据: 烧蚀面 = ρ 最陡处; 固体面 = {args.f_solid:.2f}ρ_solid; "
          f"n_c = {NC_0351:.2e} cm^-3")
    print("=" * 74)

    legs = [("flsh", tag_f, args.label_flsh), ("snb", tag_s, args.label_snb)]
    data = {name: analyse_leg(m, t) for m, t, name in legs}

    # ── 汇总表 ──────────────────────────────────────────────
    print()
    hdr = (f"{'腿':<14}{'帧数':>5}{'t末[ns]':>9}{'x_a[µm]':>9}"
           f"{'x_solid[µm]':>12}{'x_c[µm]':>9}"
           f"{'M0[1e-3]':>10}{'M末[1e-3]':>10}{'ΔM_abl[1e-3]':>12}{'Ṁ_abl[g/cm²/s]':>16}")
    print(hdr)
    print("-" * len(hdr))
    summary = {}
    for m, tag, name in legs:
        rows = data[name]
        if not rows:
            print(f"{name:<14}{'—':>5}  (无数据)")
            continue
        M0, rate = ablation_rate(rows)
        last = rows[-1]
        M_last = last["M_dense_gcm2"]
        dM = M0 - M_last
        print(f"{name:<14}{len(rows):>5}{last['t_ns']:>9.3f}"
              f"{last['x_a_um']:>9.2f}{last['x_solid_um']:>12.2f}"
              f"{last['x_c_um']:>9.2f}"
              f"{M0*1e3:>10.4f}{M_last*1e3:>10.4f}{dM*1e3:>12.4f}"
              f"{rate:>16.4e}")
        summary[name] = {"M0": M0, "rate": rate, "last": last, "dM": dM}

    # ── 比值 (核心判据) ─────────────────────────────────────
    if len(summary) == 2:
        a, b = summary[args.label_flsh], summary[args.label_snb]
        print()
        print("  ── 关键比值 ────────────────────────────────────────")
        for k, unit in (("rate", "g/cm²/s"),):
            ra, rb = a[k], b[k]
            if np.isfinite(ra) and np.isfinite(rb) and ra != 0:
                print(f"    {args.label_snb} / {args.label_flsh} 烧蚀速率 = "
                      f"{rb:.4e} / {ra:.4e} = **{rb/ra:.2f}×**")
            # 外推: 按平均速率烧穿 50 µm CH 板所需时间
            for nm, s in ((args.label_flsh, a), (args.label_snb, b)):
                r = s["rate"]
                if np.isfinite(r) and r > 0:
                    print(f"    {nm:<12} 线性外推烧穿 50 µm CH 需 "
                          f"{50e-4 / r * 1e9:.3f} ns")
        xa_a, xa_b = a["last"]["x_a_um"], b["last"]["x_a_um"]
        print(f"    末帧烧蚀面: {args.label_flsh} x_a={xa_a:.2f} µm  "
              f"vs {args.label_snb} x_a={xa_b:.2f} µm  (差 {abs(xa_b-xa_a):.2f} µm)")

    # ── 写 CSV ─────────────────────────────────────────────
    out = PC.results_dir("ablation") / args.out
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["leg", "tag", "t_ns", "x_a_um", "x_solid_um", "x_c_um",
                    "slope_max", "M_dense_gcm2", "M_tot_gcm2",
                    "rho_max", "te_max_eV"])
        for m, tag, name in legs:
            for r in data[name]:
                w.writerow([name, tag] + [r[k] for k in
                           ("t_ns", "x_a_um", "x_solid_um", "x_c_um",
                            "slope_max", "M_dense_gcm2", "M_tot_gcm2",
                            "rho_max", "te_max_eV")])
    print()
    C.log(f"时间序列表 → {out}", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
