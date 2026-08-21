# -*- coding: utf-8 -*-
"""
IONMIX .cn4 数据函数关系拟合模块 (任务D)
========================================

检验物理量是否满足特定函数关系, 常用物理解析形式:

  1. 幂律    y = a * x^b                (log-log 线性回归)
             例: 轫致辐射不透明度 kappa_ff ~ rho * T^(-3.5) 的指数检验
  2. 指数    y = a * exp(b*x)           (半对数线性回归)
             例: 玻尔兹曼布居 exp(-E/T)
  3. 理想气体 P = (1+<Z>) n k_B T       (线性拟合斜率 vs 理论斜率)
  4. 通用    y = f(x; p0, p1, ...)      (scipy curve_fit 任意形式)

输出: 拟合参数 + R^2 + 拟合优度 + 拟合曲线图 (数据点 + 拟合线 + 残差)。

用法示例:
    from cn4_parser import load_cn4
    from fit_relations import fit_power_law, fit_ideal_gas, fit_generic

    d = load_cn4("Z06_0.50-Z01_0.50.cn4", atomwt=[12.011, 1.008])

    # 固定某密度行, 检验 e_ele 是否满足幂律 E ~ T^b
    fit_power_law(d.temperature, d.e_ele[5], xlabel="T (eV)",
                  ylabel="E_e (J/g)")

    # 检验 P = (1+<Z>) n k_B T
    fit_ideal_gas(d, T_idx=10)

    # 任意函数拟合: 检验 Saha 电离 Z(T)
    fit_generic(d.temperature, d.zbar[5],
                lambda T, A, B: A * np.exp(-B / T),
                p0=[5, 10.0])
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_utils import (setup_style, FONT_SIZE_LABEL, FONT_SIZE_TICK,
                         save_fig, compute_r2)

# 玻尔兹曼常数 (eV/K)
_KB_EV = 8.617333262e-5


def _report(name, params, r2, outfile):
    print(f"[fit] {name}: params={params}, R^2={r2:.6f}, plot={outfile}")


def _plot_fit(x, y, yfit, xlabel, ylabel, title, resid=True):
    setup_style()
    if resid:
        fig, (ax, axr) = plt.subplots(
            2, 1, figsize=(10.0, 9.0), gridspec_kw={"height_ratios": [3, 1]})
    else:
        fig, ax = plt.subplots(figsize=(10.0, 7.0))
        axr = None
    ax.plot(x, y, "o", ms=7, lw=0, label="Data")
    ax.plot(x, yfit, "-", lw=2.5, label="Fit")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=FONT_SIZE_TICK)
    if axr is not None:
        axr.plot(x, y - yfit, "s", ms=5, lw=0)
        axr.axhline(0, color="k", lw=1.5)
        axr.set_xlabel(xlabel)
        axr.set_ylabel("Residual")
    for a in (ax, axr) if axr is not None else (ax,):
        for spine in a.spines.values():
            spine.set_linewidth(2.0)
        a.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    fig.tight_layout()
    return fig


def fit_power_law(x, y, xlabel="x", ylabel="y", title="Power law fit",
                  outfile=None, resid=True):
    """
    幂律拟合: y = a * x^b
    方法: log10-log10 线性回归 (仅取 y>0 且 x>0 的点)。
    Returns: (a, b, R^2, outfile)
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
    lx, ly = np.log10(x[m]), np.log10(y[m])
    b, loga = np.polyfit(lx, ly, 1)
    a = 10.0 ** loga
    yfit = a * x ** b
    r2 = compute_r2(y[m], a * x[m] ** b)
    fig = _plot_fit(x, y, yfit, xlabel, ylabel,
                    f"{title}  ($y = {a:.4e} x^{{{b:.4f}}}$, $R^2$={r2:.4f})",
                    resid=resid)
    outfile = save_fig(fig, outfile, "power")
    _report(f"power law y=a*x^b (a={a:.4e}, b={b:.4f})", {"a": a, "b": b}, r2, outfile)
    return a, b, r2, outfile


def fit_exponential(x, y, xlabel="x", ylabel="y", title="Exponential fit",
                    outfile=None, resid=True):
    """
    指数拟合: y = a * exp(b*x)
    方法: 半对数 (ln y vs x) 线性回归 (仅取 y>0)。
    Returns: (a, b, R^2, outfile)
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = (y > 0) & np.isfinite(x) & np.isfinite(y)
    b, lna = np.polyfit(x[m], np.log(y[m]), 1)
    a = np.exp(lna)
    yfit = a * np.exp(b * x)
    r2 = compute_r2(y[m], a * np.exp(b * x[m]))
    fig = _plot_fit(x, y, yfit, xlabel, ylabel,
                    f"{title}  ($y = {a:.4e} e^{{{b:.4f}x}}$, $R^2$={r2:.4f})",
                    resid=resid)
    outfile = save_fig(fig, outfile, "exp")
    _report(f"exponential y=a*exp(bx) (a={a:.4e}, b={b:.4f})",
            {"a": a, "b": b}, r2, outfile)
    return a, b, r2, outfile


def fit_ideal_gas(data, T_idx=0, outfile=None):
    """
    检验理想气体状态方程: P = (1 + <Z>) n_tot k_B T
    对固定温度行 T_idx: 逐密度点比较 IONMIX 压力 p_ion+p_ele (J/cm^3)
    与理论 (1+<Z>)*n*kB*T, 做线性拟合 P_theory = s * P_ionmix。
    s=1 表示完全符合 (理想气体+电离修正)。
    Returns: (slope, R^2, outfile)
    """
    from cn4_parser import CN4Data
    T = data.temperature[T_idx]                 # eV
    P_model = data.p_ion[:, T_idx] + data.p_ele[:, T_idx]   # J/cm^3
    # 理论: P = (1+<Z>) n_tot k_B T;  eV -> J: *1.602176634e-19
    P_theory = (1.0 + data.zbar[:, T_idx]) * data.density * \
        _KB_EV * T * 1.602176634e-19
    slope, intercept = np.polyfit(P_theory, P_model, 1)
    yfit = slope * P_theory + intercept
    r2 = compute_r2(P_model, yfit)
    fig, ax = plt.subplots(figsize=(9.5, 7.5))
    setup_style()
    ax.plot(P_theory, P_model, "o", ms=7, label="IONMIX data")
    ax.plot(P_theory, yfit, "-", lw=2.5,
            label=f"Fit: slope={slope:.4f}")
    ax.plot(P_theory, P_theory, "--", lw=2.0, color="gray",
            label="Ideal gas (slope=1)")
    ax.set_xlabel(r"$(1+\langle Z\rangle)\, n_i k_B T$  (J/cm$^3$)")
    ax.set_ylabel("IONMIX pressure  (J/cm$^3$)")
    ax.set_title(f"Ideal gas check, T={T:.3e} eV (R$^2$={r2:.4f})")
    ax.legend(fontsize=FONT_SIZE_TICK)
    for spine in ax.spines.values():
        spine.set_linewidth(2.0)
    ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    fig.tight_layout()
    outfile = save_fig(fig, outfile, "ideal_gas")
    _report(f"ideal gas P=(1+<Z>)n k_B T (slope={slope:.4f})",
            {"slope": slope, "intercept": intercept}, r2, outfile)
    return slope, r2, outfile


def fit_generic(x, y, func, p0, xlabel="x", ylabel="y", title="Generic fit",
                outfile=None, resid=True):
    """
    通用函数拟合: y = func(x, *params), 使用 scipy curve_fit。
    Returns: (params, pcov, R^2, outfile)
    """
    from scipy.optimize import curve_fit
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    popt, pcov = curve_fit(func, x[m], y[m], p0=p0, maxfev=100000)
    yfit = func(x, *popt)
    r2 = compute_r2(y[m], yfit[m])
    fig = _plot_fit(x, y, yfit, xlabel, ylabel,
                    f"{title}  ($R^2$={r2:.4f})", resid=resid)
    outfile = save_fig(fig, outfile, "generic")
    _report(f"generic fit func (params={popt})",
            dict(zip([f"p{i}" for i in range(len(popt))], popt)), r2, outfile)
    return popt, pcov, r2, outfile


if __name__ == "__main__":
    # 自测: 幂律 + 指数 + 通用
    x = np.logspace(0, 3, 40)
    fit_power_law(x, 3.0 * x ** 1.5, xlabel="x", ylabel="y",
                  outfile="_test_fit.png")
    fit_exponential(x, 5.0 * np.exp(-0.002 * x), xlabel="x", ylabel="y",
                    outfile="_test_fit.png")
    os.remove("_test_fit.png")
    print("self-test ok")
