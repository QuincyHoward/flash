# -*- coding: utf-8 -*-
"""关系拟合 —— 幂律 / 指数 / 理想气体 / 通用非线性。

迁移自参考实现 ``core/fit_relations.py``。四类拟合：

======================  =================================================
函数                     模型
======================  =================================================
:func:`fit_power_law`     ``y = a * x^b``（log-log 线性回归）
:func:`fit_exponential`   ``y = a * exp(b * x)``（半对数线性回归）
:func:`fit_ideal_gas`     检验 ``P = (1 + <Z>) n_ion k_B T``
:func:`fit_generic`       任意 ``func``（``scipy.optimize.curve_fit``）
======================  =================================================

单位纪律
--------
``fit_ideal_gas`` 需要玻尔兹曼常数。本项目**单一来源规则**要求物理常数
取自 :mod:`..config`（``config.EV_PER_K`` = eV/K，CODATA），不在本模块
另写数字（守护测试 ``test_config_single_source``）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from .. import config
from ..parsers.cn4_io import CN4ParseError, CN4Table
from .units import P_JCM3_TO_MBAR

__all__ = [
    "compute_r2", "fit_power_law", "fit_exponential",
    "fit_ideal_gas", "fit_generic",
]


def _plt():
    from .style import apply_style
    return apply_style()


def compute_r2(y, yfit) -> float:
    """决定系数 ``R^2 = 1 - SS_res / SS_tot``。"""
    y = np.asarray(y, dtype=float)
    yfit = np.asarray(yfit, dtype=float)
    ss_res = float(np.sum((y - yfit) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def _save(fig, outfile, tag: str) -> str:
    from .style import assert_ascii
    if outfile is None:
        outfile = os.path.join(os.getcwd(), f"fit_{tag}.png")
    outfile = str(outfile)
    Path(outfile).parent.mkdir(parents=True, exist_ok=True)
    assert_ascii(fig)
    fig.savefig(outfile, dpi=config.PLOT_DPI, bbox_inches="tight")
    _plt().close(fig)
    return outfile


def _plot_fit(x, y, yfit, *, xlabel, ylabel, title, resid: bool = True,
              outfile=None, tag: str = "fit") -> str:
    """数据 + 拟合线 (+ 残差子图) 的标准版式。"""
    plt = _plt()
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    yfit = np.asarray(yfit, dtype=float)

    if resid:
        fig, (ax, axr) = plt.subplots(
            2, 1, figsize=(10.0, 8.0), sharex=True,
            gridspec_kw={"height_ratios": [3, 1]})
    else:
        fig, ax = plt.subplots(figsize=(10.0, 7.5))
        axr = None

    ax.plot(x, y, "o", ms=config.PLOT_MARKERSIZE, mfc="tab:blue",
            mec="none", alpha=0.85, label="Data")
    order = np.argsort(x)
    ax.plot(x[order], yfit[order], "-", lw=config.PLOT_LINEWIDTH,
            color="tab:red", label="Fit")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    ax.tick_params(which="both", direction="in", top=True, right=True,
                   labelsize=config.PLOT_TICK_FONTSIZE, width=1.5, length=6)
    for s in ax.spines.values():
        s.set_linewidth(1.5)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE)

    if axr is not None:
        axr.axhline(0.0, color="#888888", lw=1.2, ls=":")
        axr.plot(x, y - yfit, "o", ms=config.PLOT_MARKERSIZE - 3,
                 mfc="tab:green", mec="none", alpha=0.85)
        axr.set_xlabel(xlabel)
        axr.set_ylabel("Residual")
        axr.grid(True, which="both", alpha=0.3)
        axr.tick_params(which="both", direction="in", top=True, right=True,
                        labelsize=config.PLOT_TICK_FONTSIZE, width=1.5, length=6)
        for s in axr.spines.values():
            s.set_linewidth(1.5)
    else:
        ax.set_xlabel(xlabel)

    fig.tight_layout()
    return _save(fig, outfile, tag)


# ================================================================
# 1. 幂律 y = a * x^b
# ================================================================

def fit_power_law(x, y, *, xlabel="x", ylabel="y", title=None,
                  outfile=None, tag="power_law"):
    """log-log 线性回归拟合 ``y = a * x^b``。

    Returns:
        ``(a, b, r2, outfile)``
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if m.sum() < 2:
        raise CN4ParseError("幂律拟合至少需要 2 个正的有效点")
    lx, ly = np.log10(x[m]), np.log10(y[m])
    b, log10a = np.polyfit(lx, ly, 1)
    a = 10.0 ** log10a
    yfit = a * x ** b
    r2 = compute_r2(y[m], yfit[m])
    out = _plot_fit(
        x[m], y[m], yfit[m],
        xlabel=xlabel, ylabel=ylabel,
        title=title or f"Power law: $y = {a:.4g}\\,x^{{{b:.4f}}}$  "
                       f"($R^2$ = {r2:.4f})",
        outfile=outfile, tag=tag)
    print(f"[fit] power law a={a:.6g}, b={b:.6f}, R2={r2:.6f} -> {out}")
    return a, b, r2, out


# ================================================================
# 2. 指数 y = a * exp(b x)
# ================================================================

def fit_exponential(x, y, *, xlabel="x", ylabel="y", title=None,
                    outfile=None, tag="exponential"):
    """半对数线性回归拟合 ``y = a * exp(b x)``。

    Returns:
        ``(a, b, r2, outfile)``
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y) & (y > 0)
    if m.sum() < 2:
        raise CN4ParseError("指数拟合至少需要 2 个正的有效点")
    b, log_a = np.polyfit(x[m], np.log10(y[m]), 1)
    # 注意 polyfit 给出的是 log10 斜率 -> 换算回自然指数: b_ln = b * ln(10)
    b_nat = b * np.log(10.0)
    a = 10.0 ** log_a
    yfit = a * np.exp(b_nat * x)
    r2 = compute_r2(y[m], yfit[m])
    out = _plot_fit(
        x[m], y[m], yfit[m],
        xlabel=xlabel, ylabel=ylabel,
        title=title or f"Exponential: $y = {a:.4g}\\,e^{{{b_nat:.4f}x}}$  "
                       f"($R^2$ = {r2:.4f})",
        outfile=outfile, tag=tag)
    print(f"[fit] exponential a={a:.6g}, b={b_nat:.6f}, R2={r2:.6f} -> {out}")
    return a, b_nat, r2, out


# ================================================================
# 3. 理想气体律 P = (1 + <Z>) n_ion k_B T
# ================================================================

def fit_ideal_gas(tbl: CN4Table, *, T_idx: int = 0,
                  outfile=None, figsize=(10.0, 7.5)):
    """检验理想气体律 ``P = (1 + <Z>) n_ion k_B T`` 的符合度。

    物理依据
    --------
    总压 ``P = p_ion + p_ele``；对完全电离等离子体，粒子总数密度为
    ``n_ion + n_e = n_ion (1 + <Z>)``，故

    .. math::
        P = (1 + \\langle Z \\rangle)\\, n_{ion}\\, k_B T

    这里 ``<Z> = zbar``，``n_ion`` 为钙4 密度轴（cm^-3），``T`` 为温度 (eV)。
    把 ``k_B`` 用 **eV/K** 表示（``config.EV_PER_K``）时，``k_B T`` 直接得 J。

    做法：固定温度行，绘 ``P`` vs ``n_ion(1+<Z>)``，理论斜率应为
    ``k_B T``。返回实测斜率与 ``R^2``。

    Returns:
        ``(slope_mbar_per_unit, r2, outfile)``；斜率单位为 **Mbar** 每
        ``n_ion(1+<Z>)`` 单位（显示单位，便于与理论值对照打印）。
    """
    plt = _plt()
    T = float(tbl.temperature[T_idx])
    p_ion = np.asarray(tbl.field("p_ion"), dtype=float).reshape(tbl.ndens, tbl.ntemp)
    p_ele = np.asarray(tbl.field("p_ele"), dtype=float).reshape(tbl.ndens, tbl.ntemp)
    zbar = np.asarray(tbl.field("zbar"), dtype=float).reshape(tbl.ndens, tbl.ntemp)
    n_ion = np.asarray(tbl.density, dtype=float)

    P = p_ion[:, T_idx] + p_ele[:, T_idx]          # J/cm^3
    z = zbar[:, T_idx]
    x = n_ion * (1.0 + z)                           # cm^-3

    # 理论斜率: k_B[erg/K] * T[K]; T[eV] * EV_PER_K -> K
    k_B_erg = config.EV_PER_K * 1.602176634e-12     # erg/K (1 eV = 1.602e-12 erg)
    T_K = T / config.EV_PER_K
    slope_theory_jcm3 = k_B_erg * T_K * 1e-7        # erg/cm^3 -> J/cm^3

    # 线性过原点拟合: P = slope * x
    denom = float(np.sum(x ** 2))
    slope = float(np.sum(P * x) / denom) if denom > 0 else float("nan")
    yfit = slope * x
    r2 = compute_r2(P, yfit)

    # 显示单位：J/cm^3 -> Mbar
    slope_mbar = slope * P_JCM3_TO_MBAR
    theory_mbar = slope_theory_jcm3 * P_JCM3_TO_MBAR

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(x, P * P_JCM3_TO_MBAR, "o", ms=config.PLOT_MARKERSIZE,
            mfc="tab:blue", mec="none", alpha=0.85, label="Data")
    order = np.argsort(x)
    ax.plot(x[order], yfit[order] * P_JCM3_TO_MBAR, "-",
            lw=config.PLOT_LINEWIDTH, color="tab:red",
            label=f"Fit: slope = {slope_mbar:.4e} Mbar/cc")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$(1 + \langle Z\rangle)\; n_i$ (cm$^{-3}$)")
    ax.set_ylabel("Pressure $P$ (Mbar)")
    ax.set_title(f"Ideal-gas test at $T$ = {T:.4e} eV  ($R^2$ = {r2:.4f})")
    ax.grid(True, which="both", alpha=0.3)
    ax.tick_params(which="both", direction="in", top=True, right=True,
                   labelsize=config.PLOT_TICK_FONTSIZE, width=1.5, length=6)
    for s in ax.spines.values():
        s.set_linewidth(1.5)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE)
    fig.tight_layout()

    if outfile is None:
        d = os.path.dirname(os.path.abspath(tbl.filepath))
        outfile = os.path.join(d, f"{tbl.basename}_ideal_gas_T{T_idx}.png")
    out = _save(fig, outfile, f"ideal_gas_T{T_idx}")
    print(f"[fit] ideal gas T={T:.4e} eV: slope={slope_mbar:.6e} Mbar/cc, "
          f"theory={theory_mbar:.6e}, R2={r2:.6f} -> {out}")
    return slope_mbar, r2, out


# ================================================================
# 4. 通用非线性拟合
# ================================================================

def fit_generic(x, y, func: Callable, p0=None, *, xlabel="x", ylabel="y",
                title=None, outfile=None, tag="generic",
                maxfev: int = 100000):
    """任意模型 ``func(x, *params)`` 的非线性最小二乘拟合。

    Returns:
        ``(popt, pcov, r2, outfile)``
    """
    from scipy.optimize import curve_fit

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 2:
        raise CN4ParseError("通用拟合至少需要 2 个有效点")
    popt, pcov = curve_fit(func, x[m], y[m], p0=p0, maxfev=maxfev)
    yfit = func(x, *popt)
    r2 = compute_r2(y[m], yfit[m])
    out = _plot_fit(
        x[m], y[m], yfit[m], xlabel=xlabel, ylabel=ylabel,
        title=title or f"Generic fit ({len(popt)} params)  "
                       f"($R^2$ = {r2:.4f})",
        outfile=outfile, tag=tag)
    print(f"[fit] generic popt={np.asarray(popt)}, R2={r2:.6f} -> {out}")
    return popt, pcov, r2, out
