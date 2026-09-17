#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""声速模块回归驱动 —— 薄调用包级固化实现（r16 固化后形态）。

计算与绘图已固化至包模块（2026-09-17，原 sv_physics/sv_plots 升格）：

* 计算：``eosop_pro.plotting.cn4_thermo``（γ 场 / 两项分解 / 占比 /
  γ_sound；声速唯一实现 = ``cn4_paths.sound_speed``）
* 绘图：``eosop_pro.plotting.cn4_plots.plot_quantity_heatmap``
  通用引擎（γ 场 / 声速 (n,T) 对数 / **声速 (ρ,T) cubehelix 线性** /
  热熵占比）+ ``plot_gamma_T_fit`` 折线

本文件只保留：样品装载 -> 计算 -> 报告 -> 自检 -> 出图驱动。
产物（``_out/``，已被 ``**/eosop_pro/test/**/_out/`` gitignore 覆盖）::

    gamma_ion_heatmap.png             离子有效 γ 场（线性 1-2，锚 5/3）
    gamma_ele_heatmap.png             电子有效 γ 场
    gamma_T_fit.png                   固定密度行 γ(T) 幂律拟合 + 5/3 线
    cs_isentropic_heatmap.png         声速场 (n,T)（zlog，um/ns）
    cs_isentropic_rho_cubehelix.png   声速场 (ρ,T)（cubehelix 线性）
    cs_thermal_fraction_heatmap.png   热熵项占 c_s^2 比值场（锚 0.40）
    summary.txt                       数值报告（与本 console 输出同文）

自检 5 条（[PASS]/[FAIL]，对齐 cross_validate_cn4 风格）：
1. γ_i / γ_e 有限点占比 > 90%
2. 高温区（T > 0.5·Tmax）γ_i 中位数 ∈ (1.4, 1.9)、γ_e ∈ (1.2, 1.9)
3. **内部恒等式**：cn4_thermo.cs_terms 两项之和 == (c_s)^2/1e7
   （cn4_paths.sound_speed，cm/s->J/g）逐点 rtol 1e-12 —— 两处
   独立差分实现的一致性守卫（ln10 类坐标 bug 的回归防线）
4. 严格等熵声速有限点全部 > 0
5. 热熵项占比有限点 ∈ [0,1]，且高温区 γ_sound = c_s^2·ρ/P
   中位数 ∈ (1.0, 1.72]（5/3 锚；ln10 修正前实测 3.00）
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
from eosop_pro.plotting.cn4_thermo import (         # noqa: E402
    gamma_ion, gamma_ele, gamma_powerlaw_fit,
    cs_terms, thermal_fraction, sound_gamma_eff,
)
from eosop_pro.plotting.cn4_plots import (          # noqa: E402
    plot_quantity_heatmap, plot_gamma_T_fit,
)

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
    say("Sound velocity module (r16 solidified) -- strict isentropic definition")
    say(SEP)
    say(f"sample : {_DEFAULT_CN4.name}")
    say(f"grid   : ntemp={tbl.ntemp} ndens={tbl.ndens} "
        f"T=[{_fmt(T.min())}, {_fmt(T.max())}] eV "
        f"n=[{_fmt(dens.min())}, {_fmt(dens.max())}] cm^-3")
    say(f"hot zone: T > 0.5*Tmax -> {n_hot}/{tbl.ntemp} columns")
    say("")

    # ── 计算（全部来自包级固化模块）─────────────────────────
    gi = gamma_ion(tbl)
    ge = gamma_ele(tbl)
    cs2_th, cs2_iso = cs_terms(tbl)
    frac = thermal_fraction(cs2_th, cs2_iso)
    g_sound = sound_gamma_eff(tbl)
    from eosop_pro.plotting.cn4_paths import sound_speed
    cs_umns_all = np.asarray(sound_speed(tbl), dtype=float)

    # ── γ(T) 拟合（中间密度行）─────────────────────────────
    idx_mid = tbl.ndens // 2
    fit_i = gamma_powerlaw_fit(T, gi[idx_mid])
    fit_e = gamma_powerlaw_fit(T, ge[idx_mid])

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
    fin_cs = cs_umns_all[np.isfinite(cs_umns_all)]
    say(f"  c_s (um/ns): min={_fmt(float(fin_cs.min()))} "
        f"max={_fmt(float(fin_cs.max()))} "
        f"median={_fmt(float(np.median(fin_cs)))}")
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

    # 内部恒等式：两项分解之和 == 唯一声速实现的 c_s^2（J/g）
    resid = (cs2_th + cs2_iso) - (cs_umns_all ** 2) * 1e-7
    m_finite = np.isfinite(resid)
    denom = (cs_umns_all ** 2) * 1e-7
    rel = float(np.max(np.abs(resid[m_finite]) / np.abs(denom[m_finite])))
    checks.append((rel < 1e-12,
                   f"cs_terms sum == sound_speed^2/1e7 (max rel {rel:.1e}; "
                   "coordinate-bug regression guard)"))

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

    # ── 绘图（6 张，全部走包级通用引擎）────────────────────
    say("[6] Figures -> _out/")
    outs = [
        plot_quantity_heatmap(tbl, "gamma_ion", cmap="viridis",
                              vmin=1.0, vmax=2.0,
                              outfile=str(_OUT / "gamma_ion_heatmap.png")),
        plot_quantity_heatmap(tbl, "gamma_ele", cmap="viridis",
                              vmin=1.0, vmax=2.0,
                              outfile=str(_OUT / "gamma_ele_heatmap.png")),
        plot_quantity_heatmap(tbl, "cs", cmap="viridis", zlog=True,
                              outfile=str(_OUT / "cs_isentropic_heatmap.png")),
        # 用户指定：物质密度轴 + cubehelix + 线性色标
        plot_quantity_heatmap(tbl, "cs", y_axis="rho", cmap="cubehelix",
                              zlog=False,
                              outfile=str(
                                  _OUT / "cs_isentropic_rho_cubehelix.png")),
        plot_quantity_heatmap(tbl, "cs_thermal_fraction", cmap="viridis",
                              vmin=0.0, vmax=1.0,
                              outfile=str(
                                  _OUT / "cs_thermal_fraction_heatmap.png")),
        plot_gamma_T_fit(tbl, gi[idx_mid], ge[idx_mid], fit_i, fit_e,
                         outfile=str(_OUT / "gamma_T_fit.png"),
                         row_note=f"n = {_fmt(dens[idx_mid])} cm^-3 "
                                  "(mid-density row)"),
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
