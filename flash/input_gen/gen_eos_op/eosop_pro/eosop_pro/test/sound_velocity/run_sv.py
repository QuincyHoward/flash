#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""声速模块 —— 驱动：载入样品 -> 计算 -> 绘图 -> 自检 -> 报告。

用法::

    C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe \\
        eosop_pro/eosop_pro/test/sound_velocity/run_sv.py

产物（``_out/``，已被 ``**/eosop_pro/test/**/_out/`` gitignore 覆盖）::

    gamma_ion_heatmap.png             离子有效 γ 场（线性 1-2，锚 5/3）
    gamma_ele_heatmap.png             电子有效 γ 场
    gamma_T_fit.png                   固定密度行 γ(T) 幂律拟合 + 5/3 线
    cs_isentropic_heatmap.png         严格等熵声速场（zlog，um/ns）
    cs_thermal_fraction_heatmap.png   热熵项占 c_s^2 比值场（锚 0.40）
    summary.txt                       数值报告（与本 console 输出同文）

自检 5 条（[PASS]/[FAIL]，对齐 cross_validate_cn4 风格）：
1. γ_i / γ_e 有限点占比 > 90%
2. 高温区（T > 0.5·Tmax）γ_i 中位数 ∈ (1.4, 1.9)、γ_e ∈ (1.2, 1.9)
3. 双实现对照：本模块 vs cn4_paths.sound_speed max rel diff < 1e-9
   （ln10 bug 2026-09-17 主线修复后此断言恢复有效；修正前必 FAIL）
4. 严格等熵声速有限点全部 > 0
5. 热熵项占比有限点 ∈ [0,1]，且高温区 γ_sound = c_s^2·ρ/P
   中位数 ∈ (1.0, 1.72]（5/3 锚；修正前实测 3.00 = 2.303 污染
   iso + 0.697 正确 th 的对账量）
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

# ── 路径（直接执行本文件时把 gen_eos_op/eosop_pro 塞进 sys.path）──
_HERE = Path(__file__).resolve()
_PKG_PARENT = _HERE.parents[3]          # .../gen_eos_op/eosop_pro（其下有 eosop_pro/ 包）
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from eosop_pro.parsers.cn4_io import load_cn4       # noqa: E402
from eosop_pro.plotting import cn4_paths            # noqa: E402  (dual-impl report)
from eosop_pro.plotting.units import velocity_umns  # noqa: E402

import sv_physics as sv                             # noqa: E402
import sv_plots                                     # noqa: E402

# ── 样品（cross_validate_cn4.py:47-51 先例：硬指 + 存在性断言）──
_REPO = _PKG_PARENT.parent                          # .../gen_eos_op
_DEFAULT_CN4 = (
    _REPO / "eos_op_data" / "Gen_eos_op_data"
    / "Z06_0.50-Z01_0.50-20260708_0850"
    / "Z06_0.50-Z01_0.50-20260708_0850.cn4"
)

_OUT = _HERE.parent / "_out"

SEP = "=" * 72


def _fmt(x: float) -> str:
    """报告数值格式：图上/报告统一 :.1e（r15 规约）。"""
    return f"{x:.1e}"


def main() -> int:
    assert _DEFAULT_CN4.exists(), f"样品不存在: {_DEFAULT_CN4}"
    _OUT.mkdir(parents=True, exist_ok=True)

    tbl = load_cn4(_DEFAULT_CN4)
    T = np.asarray(tbl.temperature, dtype=float)
    dens = np.asarray(tbl.density, dtype=float)
    hot = T > 0.5 * T.max()
    n_hot = int(hot.sum())

    lines: list[str] = []
    say = lines.append

    say(SEP)
    say("Sound velocity module (r16) -- strict isentropic definition")
    say(SEP)
    say(f"sample : {_DEFAULT_CN4.name}")
    say(f"grid   : ntemp={tbl.ntemp} ndens={tbl.ndens} "
        f"T=[{_fmt(T.min())}, {_fmt(T.max())}] eV "
        f"n=[{_fmt(dens.min())}, {_fmt(dens.max())}] cm^-3")
    say(f"hot zone: T > 0.5*Tmax -> {n_hot}/{tbl.ntemp} columns")
    say("")

    # ── 计算 ────────────────────────────────────────────────
    gi = sv.gamma_ion(tbl)
    ge = sv.gamma_ele(tbl)
    cs_umns = sv.cs_isentropic_umns(tbl)
    cs2_th, cs2_iso = sv.cs_terms(tbl)
    frac = sv.thermal_fraction(cs2_th, cs2_iso)
    g_sound = sv.sound_gamma_eff(tbl)
    dual_diff = sv.validate_against_cn4_paths(tbl)

    # ── γ(T) 拟合（中间密度行）─────────────────────────────
    idx_mid = tbl.ndens // 2
    fit_i = sv.fit_gamma_powerlaw(T, gi[idx_mid])
    fit_e = sv.fit_gamma_powerlaw(T, ge[idx_mid])

    # ── 报告 ────────────────────────────────────────────────
    say("[1] Effective gamma fields (single-point identity, no differencing)")
    for name, g in (("gamma_i", gi), ("gamma_ele", ge)):
        fin = float(np.isfinite(g).mean())
        say(f"  {name}: finite={fin:.3f} "
            f"hot_median={_fmt(float(np.nanmedian(g[:, hot])))} "
            f"global_median={_fmt(float(np.nanmedian(g)))}")
    say("")

    say("[2] gamma(T) power-law fits at mid-density row "
        f"(n = {_fmt(dens[idx_mid])} cm^-3)")
    say(f"  gamma_i: a={_fmt(fit_i[0])} b={_fmt(fit_i[1])} R2={_fmt(fit_i[2])}"
        "   (R2 low expected: gamma is nearly constant -> SS_tot tiny)")
    say(f"  gamma_e: a={_fmt(fit_e[0])} b={_fmt(fit_e[1])} R2={_fmt(fit_e[2])}")
    say("")

    say("[3] Strict isentropic sound speed c_s^2 = (dP/drho)_s")
    fin_cs = cs_umns[np.isfinite(cs_umns)]
    say(f"  c_s (um/ns): min={_fmt(float(fin_cs.min()))} "
        f"max={_fmt(float(fin_cs.max()))} "
        f"median={_fmt(float(np.median(fin_cs)))}")
    # 双实现对照：cn4_paths.sound_speed 的 ln(10) 因子 bug 已于
    # 2026-09-17 主线修复（log10→ln），修正后 ratio 预期 ≈ 1.0；
    # ratio = 0.75 阶段（2026-09-15~17）曾定量锁定该 bug。
    # 注意 cn4_paths 返回 cm/s，须先转 um/ns 再比（同单位）。
    cs_cn4_umns = velocity_umns(
        np.asarray(cn4_paths.sound_speed(tbl), dtype=float))
    ratio = cs_umns / cs_cn4_umns
    m_ratio = np.isfinite(ratio) & (ratio > 0)
    ratio_hot = float(np.median(ratio[:, hot][m_ratio[:, hot]]))
    say(f"  dual-impl max_rel_diff={_fmt(dual_diff)} "
        f"hot_median_ratio={_fmt(ratio_hot)} "
        "[cn4_paths ln10 bug fixed 2026-09-17]")
    say("")

    say("[4] c_s^2 two-term decomposition (strict quantities)")
    fin_frac = frac[np.isfinite(frac)]
    gs_hot = float(np.nanmedian(g_sound[:, hot]))
    say(f"  thermal fraction: hot_median={_fmt(float(np.nanmedian(frac[:, hot])))} "
        f"range=[{_fmt(float(fin_frac.min()))}, {_fmt(float(fin_frac.max()))}]")
    say(f"  gamma_sound = c_s^2*rho/P: hot_median={_fmt(gs_hot)}")
    say("  (0.40 thermal-fraction anchor holds only in the fully "
        "unionized ideal-gas limit; CH mixture deviates via ionization)")
    say("")

    # ── 自检 ────────────────────────────────────────────────
    say("[5] Self checks")
    checks: list[tuple[bool, str]] = []

    fin_i, fin_e = float(np.isfinite(gi).mean()), float(np.isfinite(ge).mean())
    checks.append((fin_i > 0.9 and fin_e > 0.9,
                   f"gamma finite fraction > 0.9 (gi={fin_i:.3f}, "
                   f"ge={fin_e:.3f})"))

    med_i = float(np.nanmedian(gi[:, hot]))
    med_e = float(np.nanmedian(ge[:, hot]))
    checks.append((1.4 < med_i < 1.9 and 1.2 < med_e < 1.9,
                   f"hot-zone gamma medians in range "
                   f"(gi={_fmt(med_i)}, ge={_fmt(med_e)})"))

    checks.append((dual_diff < 1e-9,
                   f"dual-implementation max_rel_diff < 1e-9 "
                   f"(got {_fmt(dual_diff)}; ln10 bug fixed 2026-09-17)"))

    checks.append((bool(np.all(fin_cs > 0)),
                   "isentropic c_s strictly positive at all finite points"))

    frac_ok = bool(np.all((fin_frac >= 0) & (fin_frac <= 1)))
    checks.append((frac_ok and 1.0 < gs_hot <= 1.72,
                   f"thermal fraction in [0,1] and hot-zone gamma_sound "
                   f"in (1.0, 1.72] (got {_fmt(gs_hot)}; 5/3 anchor)"))

    n_pass = 0
    for ok, desc in checks:
        tag = "[PASS]" if ok else "[FAIL]"
        n_pass += int(ok)
        say(f"  {tag} {desc}")
    say("")
    summary = (f"TOTAL: {n_pass}/{len(checks)} checks passed")
    say(SEP)
    say(summary)
    say(SEP)

    # ── 绘图（5 张）────────────────────────────────────────
    say("[6] Figures -> _out/")
    outs = [
        sv_plots.plot_gamma_field(tbl, gi, "ion",
                                  _OUT / "gamma_ion_heatmap.png"),
        sv_plots.plot_gamma_field(tbl, ge, "ele",
                                  _OUT / "gamma_ele_heatmap.png"),
        sv_plots.plot_gamma_T_fit(tbl, gi[idx_mid], ge[idx_mid],
                                  fit_i, fit_e,
                                  _OUT / "gamma_T_fit.png"),
        sv_plots.plot_cs_field(tbl, cs_umns,
                               _OUT / "cs_isentropic_heatmap.png"),
        sv_plots.plot_thermal_fraction_field(tbl, frac,
                                             _OUT / "cs_thermal_fraction_heatmap.png"),
    ]
    for p in outs:
        say(f"  saved: {Path(p).name}")
    say(SEP)
    say("DONE")
    say(SEP)

    text = "\n".join(lines) + "\n"
    (_OUT / "summary.txt").write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
