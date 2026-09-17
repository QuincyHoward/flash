#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cn4 热力学派生量 —— 有效 γ 场 / 声速两项分解 / 等熵指数。

固化自 ``test/sound_velocity``（r16，2026-09-17）：测试区三文件
（sv_physics/sv_plots）的实现升格为**包级唯一实现**，测试区改为
薄调用，消除双实现漂移风险（ln10 bug 教训：双实现"同错"曾使
互检失效，见 2026-09-15/17 日志）。

物理设计（r16 修订版，用户批准）
--------------------------------
1. **γ_e / γ_i 单点恒等式**（无差分）::

       γ = 1 + P/(ρ e)

   完全电离单原子区 → 5/3；部分电离 / 简并 / 库仑修正区偏离 ——
   γ 场是 EOS 非理想性诊断量，**不用于声速**。

2. **严格等熵声速**：唯一实现 = :func:`cn4_paths.sound_speed`
   （2026-09-17 已修 ln10 坐标 bug），本模块只做派生与分解，
   **不重复实现**::

       c_s^2 = (∂P/∂ρ)_s = (∂P/∂ρ)_T + T/(ρ^2 c_v)(∂P/∂T)_ρ^2

3. **c_s^2 两项分解**（均为严格量）：等温压缩项 (∂P/∂ρ)_T 与
   热熵项 T/(ρ²c_v)(∂P/∂T)_ρ²；单原子理想气体区热熵占比 =
   (γ-1)/γ = 2/5 = 0.4。

4. **等熵指数** γ_sound = c_s²ρ/P：理想气体极限下与 γ 恒等（5/3），
   电离/束缚效应使二者机理不同地偏离。

单位链
------
``(J/cm^3)/(g/cm^3) = J/g = 1e7 cm^2/s^2``；γ / 占比无量纲。
c_v 取表值 J/g/eV；ρ = n·<A>/N_A（g/cm^3）。

CLI
---
``python -m eosop_pro.plotting.cn4_thermo <sample.cn4> [--outdir DIR]``

生成 6 图 + ``summary.txt``（LF）：γ_i / γ_e 场（线性 1-2）、
声速 (n,T) 对数色标、**声速 (ρ,T) cubehelix 线性色标**（用户指定）、
热熵占比场（0-1）、γ(T) 幂律拟合。产物默认落
``config.OUTPUTS_DIR/cn4_thermo/<basename>/``（outputs/ 已 gitignore）。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .. import config
from ..parsers.cn4_io import CN4Table
from .cn4_paths import sound_speed
from .units import density_gcc_from_nion

__all__ = [
    "gamma_species", "gamma_ion", "gamma_ele",
    "gamma_powerlaw_fit",
    "cs_terms", "thermal_fraction", "sound_gamma_eff",
    "main",
]

#: c_v 的数值下限（防止 0 除；与 cn4_paths.sound_speed 的 clamp 一致）
_CV_FLOOR = 1e-30


# ── 内部辅助 ─────────────────────────────────────────────────
def _arr2d(tbl: CN4Table, name: str) -> np.ndarray:
    """二维场 -> ``(ndens, ntemp)`` 数组（行 = 密度，列 = 温度）。"""
    flat = np.asarray(tbl.field(name), dtype=float)
    return flat.reshape(tbl.ndens, tbl.ntemp)


def _rho_gcc(tbl: CN4Table) -> np.ndarray:
    """质量密度 ``(ndens, ntemp)`` g/cm^3 = n·<A>/N_A（沿温度广播）。"""
    aw = tbl.avgatw
    if aw is None:
        raise ValueError(
            "平均原子量未知（atomwt 缺失且无 ionmxinp）-> 无法换算质量密度")
    rho1d = np.asarray(
        density_gcc_from_nion(np.asarray(tbl.density, dtype=float), aw),
        dtype=float)
    return np.broadcast_to(rho1d[:, None], (tbl.ndens, tbl.ntemp))


# ── 1. γ_e / γ_i 反演（单点恒等式）───────────────────────────
def gamma_species(tbl: CN4Table, p_name: str, e_name: str) -> np.ndarray:
    """理想气体有效 γ 场 ``γ = 1 + P/(ρ e)``，形状 ``(ndens, ntemp)``。

    Args:
        p_name: 压强场名（``"p_ion"`` / ``"p_ele"``，J/cm^3）
        e_name: 比内能场名（``"e_ion"`` / ``"e_ele"``，J/g）

    Returns:
        γ 场；``e <= 0`` 或非有限处为 NaN（不静默填 0）。

    Raises:
        ValueError: 平均原子量未知。
    """
    p = _arr2d(tbl, p_name)
    e = _arr2d(tbl, e_name)
    rho = _rho_gcc(tbl)
    with np.errstate(divide="ignore", invalid="ignore"):
        gamma = 1.0 + p / (rho * e)
    gamma = np.where((e > 0) & np.isfinite(e) & np.isfinite(p), gamma, np.nan)
    return gamma


def gamma_ion(tbl: CN4Table) -> np.ndarray:
    """离子有效 γ_i = 1 + p_ion/(ρ e_ion)。"""
    return gamma_species(tbl, "p_ion", "e_ion")


def gamma_ele(tbl: CN4Table) -> np.ndarray:
    """电子有效 γ_e = 1 + p_ele/(ρ e_ele)。"""
    return gamma_species(tbl, "p_ele", "e_ele")


# ── 2. γ(T) 幂律拟合（纯数值，不出图；出图版见 cn4_fit.fit_power_law）──
def gamma_powerlaw_fit(T_row, gamma_row) -> tuple[float, float, float]:
    """固定密度行的 ``γ(T)`` log-log 幂律拟合 ``γ = a·T^b``。

    Returns:
        ``(a, b, r2)``；R^2 在原域计算（:func:`cn4_fit.compute_r2`
        惯例，常数数据 SS_tot=0 时为 NaN）。有效点 < 3 时返回
        ``(nan, nan, nan)``。
    """
    T = np.asarray(T_row, dtype=float)
    g = np.asarray(gamma_row, dtype=float)
    m = np.isfinite(T) & np.isfinite(g) & (T > 0) & (g > 0)
    if m.sum() < 3:
        return (float("nan"),) * 3
    from .cn4_fit import compute_r2
    b, log10a = np.polyfit(np.log10(T[m]), np.log10(g[m]), 1)
    a = 10.0 ** log10a
    r2 = compute_r2(g[m], a * T[m] ** b)
    return (float(a), float(b), float(r2))


# ── 3. c_s^2 两项分解（声速唯一实现复用 cn4_paths.sound_speed）──
def cs_terms(tbl: CN4Table) -> tuple[np.ndarray, np.ndarray]:
    """c_s^2 的两项分解（均为严格量，单位 J/g = 1e7 cm^2/s^2）。

    Returns:
        ``(cs2_thermal, cs2_isothermal)``：

        - ``cs2_isothermal = (∂P/∂ρ)_T``（等温压缩项）
        - ``cs2_thermal = T/(ρ^2 c_v) (∂P/∂T)_ρ^2``（热熵项）

        单原子理想气体区热熵项占比 = (γ-1)/γ = 0.4。

    ⚠️ 密度差分坐标必须用自然对数（``ln n``）：与
    :func:`cn4_paths.sound_speed` 同规约；若写成 log10(n) 会混入
    ``ln(10)≈2.303`` 因子（2026-09-15 诊断、09-17 修复，
    回归守卫 ``test_sound_speed_ideal_gas_gamma_anchor``）。
    """
    P = _arr2d(tbl, "p_ion") + _arr2d(tbl, "p_ele")        # J/cm^3
    rho = _rho_gcc(tbl)
    T = np.asarray(tbl.temperature, dtype=float)           # (ntemp,) eV
    lnn = np.log(np.asarray(tbl.density, dtype=float))     # ⚠️ ln 坐标

    dlnP_dlnn = np.gradient(np.log(P), lnn, axis=0)
    cs2_iso = (P / rho) * dlnP_dlnn                        # J/g
    dP_dT = np.gradient(P, T, axis=1)                      # J/cm^3/eV
    cv = np.maximum(_arr2d(tbl, "cv_ion") + _arr2d(tbl, "cv_ele"),
                    _CV_FLOOR)                             # J/g/eV
    dTdrho_s = (T[None, :] / (rho ** 2 * cv)) * dP_dT      # eV/(g/cm^3)
    cs2_th = dP_dT * dTdrho_s
    return cs2_th, cs2_iso


def thermal_fraction(cs2_thermal: np.ndarray,
                     cs2_isothermal: np.ndarray) -> np.ndarray:
    """热熵项占 c_s^2 比值场；分母 <= 0 或非有限处 NaN。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = cs2_thermal / (cs2_thermal + cs2_isothermal)
    valid = (np.isfinite(cs2_thermal) & np.isfinite(cs2_isothermal)
             & ((cs2_thermal + cs2_isothermal) > 0))
    return np.where(valid, frac, np.nan)


def sound_gamma_eff(tbl: CN4Table) -> np.ndarray:
    """等熵指数 ``γ_sound = c_s^2·ρ/P``（基于 cn4_paths 唯一声速实现）。

    与单点恒等式 ``γ_energy = 1 + P/(ρ e)`` 的对比量化电离/束缚
    效应：理想气体极限下两者相等（=5/3）。
    """
    cs2 = np.asarray(sound_speed(tbl), dtype=float) ** 2   # cm^2/s^2
    P = _arr2d(tbl, "p_ion") + _arr2d(tbl, "p_ele")        # J/cm^3
    rho = _rho_gcc(tbl)
    # c_s^2 [cm^2/s^2] -> J/g（x1e-7）后除以 P/rho [J/g]
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (cs2 * 1e-7) / (P / rho)
    valid = np.isfinite(cs2) & np.isfinite(P) & (P > 0)
    return np.where(valid, g, np.nan)


# ── CLI（python -m eosop_pro.plotting.cn4_thermo）────────────
def main(argv=None) -> int:
    """加载样品 -> 全套热力学诊断计算 -> 6 图 + summary.txt。"""
    parser = argparse.ArgumentParser(
        description="cn4 thermodynamic diagnostics: effective gamma fields, "
                    "isentropic sound speed (two-term decomposition) and "
                    "gamma_sound; writes 6 figures + summary.txt")
    parser.add_argument("sample", help="path to a .cn4 sample")
    parser.add_argument("--outdir", default=None,
                        help="output directory (default: "
                             "<OUTPUTS_DIR>/cn4_thermo/<basename>)")
    args = parser.parse_args(argv)

    from ..parsers.cn4_io import load_cn4
    from .cn4_plots import plot_gamma_T_fit, plot_quantity_heatmap

    tbl = load_cn4(args.sample)
    outdir = (Path(args.outdir) if args.outdir else
              Path(config.OUTPUTS_DIR) / "cn4_thermo" / tbl.basename)
    outdir.mkdir(parents=True, exist_ok=True)

    T = np.asarray(tbl.temperature, dtype=float)
    hot = T > 0.5 * T.max()

    gi = gamma_ion(tbl)
    ge = gamma_ele(tbl)
    cs2_th, cs2_iso = cs_terms(tbl)
    frac = thermal_fraction(cs2_th, cs2_iso)
    g_sound = sound_gamma_eff(tbl)
    idx_mid = tbl.ndens // 2
    fit_i = gamma_powerlaw_fit(T, gi[idx_mid])
    fit_e = gamma_powerlaw_fit(T, ge[idx_mid])

    fmt = lambda x: f"{float(x):.1e}"  # noqa: E731  (r15 图上/报告数值规约)
    lines = [
        "=" * 72,
        "cn4 thermo diagnostics (r16 solidified)",
        "=" * 72,
        f"sample : {tbl.basename}",
        f"grid   : ntemp={tbl.ntemp} ndens={tbl.ndens}",
        f"gamma_i: hot_median={fmt(np.nanmedian(gi[:, hot]))} "
        f"global_median={fmt(np.nanmedian(gi))}",
        f"gamma_e: hot_median={fmt(np.nanmedian(ge[:, hot]))} "
        f"global_median={fmt(np.nanmedian(ge))}",
        f"gamma(T) fit @ mid row: "
        f"gi a={fmt(fit_i[0])} b={fmt(fit_i[1])} R2={fmt(fit_i[2])}; "
        f"ge a={fmt(fit_e[0])} b={fmt(fit_e[1])} R2={fmt(fit_e[2])}",
        f"gamma_sound hot_median={fmt(np.nanmedian(g_sound[:, hot]))} "
        "(ideal-gas anchor 5/3)",
        f"thermal fraction: hot_median={fmt(np.nanmedian(frac[:, hot]))} "
        "(ideal-gas anchor 0.40)",
        "=" * 72,
    ]
    figures = [
        plot_quantity_heatmap(tbl, "gamma_ion", cmap="viridis",
                              vmin=1.0, vmax=2.0,
                              outfile=str(outdir / "gamma_ion_heatmap.png")),
        plot_quantity_heatmap(tbl, "gamma_ele", cmap="viridis",
                              vmin=1.0, vmax=2.0,
                              outfile=str(outdir / "gamma_ele_heatmap.png")),
        plot_quantity_heatmap(tbl, "cs", y_axis="nion", cmap="viridis",
                              zlog=True,
                              outfile=str(outdir / "cs_nt_log_heatmap.png")),
        # 用户指定：物质密度轴 + cubehelix + 线性色标（r16 追加）
        plot_quantity_heatmap(tbl, "cs", y_axis="rho", cmap="cubehelix",
                              zlog=False,
                              outfile=str(
                                  outdir / "cs_rho_cubehelix_linear.png")),
        plot_quantity_heatmap(tbl, "cs_thermal_fraction", cmap="viridis",
                              vmin=0.0, vmax=1.0,
                              outfile=str(outdir /
                                          "cs_thermal_fraction_heatmap.png")),
        plot_gamma_T_fit(tbl, gi[idx_mid], ge[idx_mid], fit_i, fit_e,
                         outfile=str(outdir / "gamma_T_fit.png")),
    ]
    lines.append("figures:")
    lines.extend(f"  {Path(f).name}" for f in figures)
    text = "\n".join(lines) + "\n"
    (outdir / "summary.txt").write_text(text, encoding="utf-8",
                                        newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":          # python -m eosop_pro.plotting.cn4_thermo
    raise SystemExit(main())
