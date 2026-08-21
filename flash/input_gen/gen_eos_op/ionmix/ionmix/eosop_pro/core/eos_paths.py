# -*- coding: utf-8 -*-
"""
IONMIX .cn4 物态方程 (EOS) 路径研究模块 (任务E)
================================================

基于 cn4 静态 (T, n_i) 表格研究典型热力学路径:
  1. 等温线 (isotherm) : T 固定, 输出 P(n_i), e(n_i)
  2. 等压线 (isobar)   : P 固定, 在 (T, n_i) 网格上提取 P=const 曲线
  3. 等熵线 (isentrope): 由热力学第一定律数值积分熵场, 提取 s=const 曲线
  4. 冲击雨贡纽 (Hugoniot): 给定参考态 (rho0,P0,e0), 求满足
     (e-e0) = (P+P0)(1/rho0 - 1/rho)/2 的状态点集, 并给出 Us-Up 关系

物理量组合 (来自 cn4 块):
    P  = p_ion + p_ele            (J/cm^3)
    e  = e_ion + e_ele            (J/g)
    rho = n_i * <A> / N_A         (g/cm^3)
    T  = temperature              (eV)

用法示例:
    from cn4_parser import load_cn4
    from eos_paths import (trace_isotherm, trace_isobar,
                           compute_entropy, trace_isentrope, trace_hugoniot)

    d = load_cn4("Z06_0.50-Z01_0.50.cn4", atomwt=[12.011, 1.008])

    trace_isotherm(d, T_idx=10, outfile="isotherm_T10.png")
    trace_isobar(d, P=1e10, outfile="isobar_P1e10.png")
    s = compute_entropy(d)
    trace_isentrope(d, s, s0_idx=(5, 10), outfile="isentrope.png")
    trace_hugoniot(d, ref_idx=(0, 0), outfile="hugoniot.png")
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cn4_parser import CN4Data
from plot_utils import (setup_style, FONT_SIZE_LABEL, FONT_SIZE_TICK,
                         save_fig, apply_axes_style)

_KB_J = 1.380649e-23          # J/K
_EV_J = 1.602176634e-19       # J/eV


def _press(data):
    """总压力 (ndens, ntemp) J/cm^3"""
    return data.p_ion + data.p_ele


def _energy(data):
    """总比内能 (ndens, ntemp) J/g"""
    return data.e_ion + data.e_ele


def _save(fig, outfile, tag):
    """保存图像: 默认输出到 cwd/eos_<tag>.png"""
    if outfile is None:
        outfile = os.path.join(os.getcwd(), f"eos_{tag}.png")
    return save_fig(fig, outfile, tag)


def _style(ax):
    """统一坐标轴样式 (PPT 演讲级边框/刻度线宽)"""
    apply_axes_style(ax)


# ---------------------------------------------------------------
# 1. 等温线
# ---------------------------------------------------------------

def trace_isotherm(data: CN4Data, T_idx=10, outfile=None, figsize=(10.0, 7.5)):
    """
    等温线: 固定温度 T_idx, 绘制 P 与 e 随离子数密度 n_i 的变化。
    左侧轴: P (J/cm^3, log), 右侧轴: e (J/g, log)。
    Returns: (nion, P, e)
    """
    setup_style()
    T = data.temperature[T_idx]
    nion = data.density
    P = _press(data)[:, T_idx]
    e = _energy(data)[:, T_idx]

    fig, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(nion, P, "o-", lw=2.5, ms=7, color="tab:red",
             label="Pressure $P$ (J/cm$^3$)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel(r"Ion Number Density $n_i$ (cm$^{-3}$)")
    ax1.set_ylabel("Pressure $P$ (J/cm$^3$)")
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax2 = ax1.twinx()
    ax2.plot(nion, e, "s-", lw=2.5, ms=7, color="tab:blue",
             label="Energy $e$ (J/g)")
    ax2.set_yscale("log")
    ax2.set_ylabel("Specific energy $e$ (J/g)")
    ax2.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_title(f"Isotherm, T = {T:.4e} eV")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=FONT_SIZE_TICK, loc="best")
    _style(ax1); _style(ax2)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isotherm_T{T_idx}")
    print(f"[eos] isotherm T={T:.4e} eV -> {outfile}")
    return nion, P, e, outfile


# ---------------------------------------------------------------
# 2. 等压线
# ---------------------------------------------------------------

def trace_isobar(data: CN4Data, P: float, outfile=None, figsize=(10.0, 7.5)):
    """
    等压线: 在 (T, n_i) 网格上提取 P=const 的曲线。
    对 P 场直接等高线; 提取段坐标为线性 (T, n_i)。
    输出 T - n_i 关系 (对数坐标)。
    Returns: (T_curve, nion_curve)
    """
    setup_style()
    Pgrid = _press(data)
    if not (Pgrid.min() <= P <= Pgrid.max()):
        raise ValueError(f"等压线 P={P:.3e} J/cm^3 超出数据范围 "
                         f"({Pgrid.min():.2e} ~ {Pgrid.max():.2e})")
    # 等高线提取 (线性场, seg 坐标即为线性 T, n_i)
    fig0, ax0 = plt.subplots()
    CS = ax0.contour(data.temperature, data.density, Pgrid, levels=[P])
    plt.close(fig0)
    if not CS.allsegs or not CS.allsegs[0]:
        raise ValueError(f"等压线 P={P:.3e} J/cm^3 未在网格内形成等值线")
    seg = CS.allsegs[0][0]
    T_c = seg[:, 0]
    n_c = seg[:, 1]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(T_c, n_c, "o-", lw=2.5, ms=6, color="tab:green")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Temperature $T$ (eV)")
    ax.set_ylabel(r"Ion Number Density $n_i$ (cm$^{-3}$)")
    ax.set_title(f"Isobar, P = {P:.3e} J/cm$^3$")
    _style(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isobar_P{P:.0e}")
    print(f"[eos] isobar P={P:.3e} J/cm^3 -> {outfile}")
    return T_c, n_c, outfile


# ---------------------------------------------------------------
# 3. 熵场与等熵线
# ---------------------------------------------------------------

def compute_entropy(data: CN4Data, ref_rho_idx=0, ref_T_idx=0):
    """
    数值积分熵场 s(T, n_i) [J/(g·eV)]。
    热力学:  de = T ds + (P/rho^2) drho
      -> 等容方向 (drho=0): ds = de / T
      -> 等温方向 (dT=0)  : ds = -(P / (rho^2 T)) drho
    从参考点 (ref_rho_idx, ref_T_idx) 沿矩形路径积分全场。
    Returns: s (ndens, ntemp) J/(g·eV)
    """
    T = data.temperature                       # (ntemp,) eV
    nion = data.density                        # (ndens,) cm^-3
    rho = data.rho                             # (ndens, ntemp) g/cm^3
    e = _energy(data)                          # (ndens, ntemp) J/g
    P = _press(data)                           # (ndens, ntemp) J/cm^3

    ndens, ntemp = e.shape
    s = np.zeros_like(e)
    i0, j0 = ref_rho_idx, ref_T_idx

    # 步骤1: 参考温度行 (j=j0), 沿密度方向积分 ds = -(P/(rho^2 T)) drho
    s[i0, j0] = 0.0
    for i in range(i0, 0, -1):                 # 从 i0 向下
        drho = rho[i, j0] - rho[i - 1, j0]
        Tj = T[j0]
        Pbar = 0.5 * (P[i, j0] + P[i - 1, j0])
        rhobar2 = (0.5 * (rho[i, j0] + rho[i - 1, j0])) ** 2
        s[i - 1, j0] = s[i, j0] - (Pbar / (rhobar2 * Tj)) * drho
    for i in range(i0, ndens - 1):             # 从 i0 向上
        drho = rho[i + 1, j0] - rho[i, j0]
        Tj = T[j0]
        Pbar = 0.5 * (P[i, j0] + P[i + 1, j0])
        rhobar2 = (0.5 * (rho[i, j0] + rho[i + 1, j0])) ** 2
        s[i + 1, j0] = s[i, j0] - (Pbar / (rhobar2 * Tj)) * drho

    # 步骤2: 每行沿温度方向积分 ds = de/T
    for i in range(ndens):
        for j in range(j0, 0, -1):
            de = e[i, j] - e[i, j - 1]
            Tbar = 0.5 * (T[j] + T[j - 1])
            s[i, j - 1] = s[i, j] - de / Tbar
        for j in range(j0, ntemp - 1):
            de = e[i, j + 1] - e[i, j]
            Tbar = 0.5 * (T[j] + T[j + 1])
            s[i, j + 1] = s[i, j] + de / Tbar

    # 相对参考态重新归一 (s 的绝对零点无物理意义)
    s -= s[i0, j0]
    return s


def trace_isentrope(data: CN4Data, s: np.ndarray, s0_idx=(5, 10),
                    outfile=None, figsize=(10.0, 7.5)):
    """
    等熵线: 从参考点 s0 = s[s0_idx] 出发, 提取 s = s0 的曲线 (T, n_i)。
    Returns: (T_curve, nion_curve)
    """
    setup_style()
    s0 = s[s0_idx]
    fig0, ax0 = plt.subplots()
    CS = ax0.contour(data.temperature, data.density, s,
                     levels=[s0])
    plt.close(fig0)
    if not CS.allsegs or not CS.allsegs[0]:
        raise ValueError("等熵线未找到 (数据范围不足)")
    seg = CS.allsegs[0][0]
    T_c, n_c = seg[:, 0], seg[:, 1]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(T_c, n_c, "o-", lw=2.5, ms=6, color="tab:purple")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Temperature $T$ (eV)")
    ax.set_ylabel(r"Ion Number Density $n_i$ (cm$^{-3}$)")
    ax.set_title(f"Isentrope, s = {s0:.4f} J/(g eV)")
    _style(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isentrope_s{s0:.2f}")
    print(f"[eos] isentrope s={s0:.4f} J/(g eV) -> {outfile}")
    return T_c, n_c, outfile


# ---------------------------------------------------------------
# 4. 冲击雨贡纽
# ---------------------------------------------------------------

def trace_hugoniot(data: CN4Data, ref_idx=(0, 0), outfile=None,
                   figsize=(12.0, 8.0)):
    """
    冲击雨贡纽: 给定参考态 (rho0, P0, e0) (网格索引 ref_idx),
    对全场计算 Hugoniot 残差
        H = (e - e0) - 0.5 (P + P0) (1/rho0 - 1/rho)
    满足 H=0 的状态点构成雨贡纽曲线; 并换算冲击速度 Us 与粒子速度 Up:
        Us^2 = (P - P0) / (rho0 (1 - rho0/rho))
        Up  = Us (1 - rho0/rho)
    输出: 两张图 (rho-P 雨贡纽, Us-Up 关系)。
    """
    setup_style()
    rho = data.rho
    P = _press(data)
    e = _energy(data)
    rho0 = rho[ref_idx]
    P0 = P[ref_idx]
    e0 = e[ref_idx]

    # Hugoniot 残差 H = (e-e0) - 0.5 (P+P0)(1/rho0 - 1/rho)
    H = (e - e0) - 0.5 * (P + P0) * (1.0 / rho0 - 1.0 / rho)

    # 在全场 (T, n_i) 网格上找 H 过零点 (每条密度行扫描温度方向)
    ndens, ntemp = H.shape
    crossings = []
    for i in range(ndens):
        Hrow = H[i]
        rho_row = rho[i]
        Pr_row = P[i]
        for j in range(ntemp - 1):
            if Hrow[j] * Hrow[j + 1] < 0:
                frac = Hrow[j] / (Hrow[j] - Hrow[j + 1])
                rho_c = 10 ** (np.log10(rho_row[j]) +
                               frac * (np.log10(rho_row[j + 1]) -
                                       np.log10(rho_row[j])))
                P_c = Pr_row[j] + frac * (Pr_row[j + 1] - Pr_row[j])
                T_c = data.temperature[j] + frac * (
                    data.temperature[j + 1] - data.temperature[j])
                crossings.append((rho_c, P_c, T_c))

    if not crossings:
        raise ValueError("全场未找到 Hugoniot 过零点, "
                         "请调整 ref_idx 或检查参考态物理性")

    rho_c = np.array([c[0] for c in crossings])
    P_c = np.array([c[1] for c in crossings])
    T_c = np.array([c[2] for c in crossings])
    # 只保留 rho_c > rho0 (冲击压缩分支)
    m = rho_c > rho0
    rho_c, P_c, T_c = rho_c[m], P_c[m], T_c[m]

    # Us-Up 关系
    Us = np.sqrt(np.maximum((P_c - P0) / (rho0 * (1.0 - rho0 / rho_c)), 0))
    Up = Us * (1.0 - rho0 / rho_c)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    # 左: rho-P 雨贡纽
    rho_full = rho[:, ref_idx[1]]
    Pr_full = P[:, ref_idx[1]]
    ax1.plot(rho_full, Pr_full, "-", lw=2.0, color="gray",
             label=f"Reference T-row (T={data.temperature[ref_idx[1]]:.3e} eV)")
    ax1.plot(rho_c, P_c, "o-", lw=2.5, ms=8, color="tab:red",
             label="Hugoniot")
    ax1.plot([rho0], [P0], "*", ms=18, color="black", label="Reference state")
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel(r"Mass density $\rho$ (g/cm$^3$)")
    ax1.set_ylabel("Pressure $P$ (J/cm$^3$)")
    ax1.set_title("Shock Hugoniot")
    ax1.legend(fontsize=FONT_SIZE_TICK)
    # 右: Us-Up
    ax2.plot(Up, Us, "s-", lw=2.5, ms=8, color="tab:blue")
    ax2.set_xlabel(r"Particle velocity $U_p$ (cm/s)")
    ax2.set_ylabel(r"Shock velocity $U_s$ (cm/s)")
    ax2.set_title(r"$U_s$-$U_p$ relation")
    for a in (ax1, ax2):
        _style(a)
    fig.tight_layout()
    outfile = _save(fig, outfile, "hugoniot")
    print(f"[eos] hugoniot: rho0={rho0:.4e} g/cm^3, P0={P0:.4e} J/cm^3 "
          f"-> {outfile}")
    return rho_c, P_c, Us, Up, outfile


if __name__ == "__main__":
    import sys
    from cn4_parser import load_cn4
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    d = load_cn4(sys.argv[1], atomwt=[12.011, 1.008])
    trace_isotherm(d, T_idx=10)
    trace_isobar(d, P=1e10)
    s = compute_entropy(d)
    trace_isentrope(d, s, s0_idx=(5, 10))
    trace_hugoniot(d, ref_idx=(0, 0))
