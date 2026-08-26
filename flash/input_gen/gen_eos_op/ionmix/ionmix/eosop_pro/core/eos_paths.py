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
from units import (pressure_mbar, energy_ergg, velocity_umns)

_KB_J = 1.380649e-23          # J/K
_EV_J = 1.602176634e-19       # J/eV
_NAV = 6.02214076e23          # 阿伏伽德罗常数 (1/mol)


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
# 0. rho-T 输入与二维插值 (任务E默认输入为质量密度 rho + 温度 T)
#    cn4 表格的密度轴是离子数密度 n_i (cm^-3), 需先换算:
#        n_i = rho * N_A / <A>
#    支持非网格点: 在 (log n_i, log T) 上做二维线性插值。
# ---------------------------------------------------------------

def nion_from_rho(data: CN4Data, rho):
    """质量密度 rho (g/cm^3) -> 离子数密度 n_i (cm^-3)"""
    aw = data.avgatw
    if aw is None:
        raise ValueError("原子量未知, 无法换算 rho -> nion")
    return np.asarray(rho, dtype=float) * _NAV / aw


def rho_from_nion(data: CN4Data, nion):
    """离子数密度 n_i (cm^-3) -> 质量密度 rho (g/cm^3)"""
    aw = data.avgatw
    if aw is None:
        raise ValueError("原子量未知, 无法换算 nion -> rho")
    return np.asarray(nion, dtype=float) * aw / _NAV


def interpolate_quantity(data: CN4Data, qname: str, rho, T,
                         clip: bool = True, field=None):
    """
    在 (log n_i, log T) 网格上二维插值物理量, 支持任意 (rho, T) 数值。

    Args:
        data: CN4Data
        qname: 物理量名 (data.quantity 别名, 如 'zbar'/'p_ion'/'e_ele'/'rho')
        rho:   质量密度 (g/cm^3, 标量或数组)
        T:     温度 (eV, 标量或数组)
        clip:  越界时 clamp 到表边界 (默认 True); False 则外推 (可能不稳)
        field: 可选, 直接传入物理量场 (ndens, ntemp) 覆盖 qname 查询
               (用于总压 P = p_ion+p_ele, 总内能 e = e_ion+e_ele 等组合量)

    Returns:
        插值结果, 语义自动分派:
          - rho、T 均为标量      -> float (单点)
          - 其一为数组 (广播)     -> 一维数组 (逐点对应)
          - rho、T 同形状数组    -> 同形状数组 (逐点对应, 如曲线点对)
          - rho、T 异形状数组    -> (n_rho, n_T) 网格 (笛卡尔积, 如场重建)
    """
    from scipy.interpolate import RegularGridInterpolator

    fld = data.quantity(qname) if field is None else np.asarray(field)
    if fld.shape != (data.ndens, data.ntemp):
        raise ValueError(f"物理量场形状 {fld.shape} != (ndens,ntemp)")
    if np.any(fld <= 0):
        raise ValueError(f"物理量 '{qname}' 含非正值, 无法做对数插值")

    logn = np.log10(data.density)          # 网格: log n_i
    logT = np.log10(data.temperature)      # 网格: log T

    rho_a = np.asarray(rho, dtype=float)
    T_a = np.asarray(T, dtype=float)
    rho_scalar = (rho_a.ndim == 0)
    T_scalar = (T_a.ndim == 0)

    nion_a = nion_from_rho(data, rho_a)
    logn_in = np.log10(nion_a)
    logT_in = np.log10(T_a)

    if clip:
        lo_n, hi_n = logn[0], logn[-1]
        lo_T, hi_T = logT[0], logT[-1]
        if (np.any(logn_in < lo_n) or np.any(logn_in > hi_n)
                or np.any(logT_in < lo_T) or np.any(logT_in > hi_T)):
            rho_lo = 10 ** lo_n * data.avgatw / _NAV
            rho_hi = 10 ** hi_n * data.avgatw / _NAV
            print(f"[interp] 输入越界, clamp 到表范围: "
                  f"rho∈[{rho_lo:.3e},{rho_hi:.3e}] g/cm^3, "
                  f"T∈[{10**lo_T:.3e},{10**hi_T:.3e}] eV")
        logn_in = np.clip(logn_in, lo_n, hi_n)
        logT_in = np.clip(logT_in, lo_T, hi_T)

    interp = RegularGridInterpolator(
        (logn, logT), np.log10(fld), bounds_error=False, fill_value=None)

    # ── 语义分派 ──
    if rho_scalar and T_scalar:
        # 单点
        val = float(10.0 ** interp([[float(logn_in), float(logT_in)]])[0])
        return val
    if rho_scalar or T_scalar:
        # 标量广播到数组: 逐点对应
        R, TT = np.broadcast_arrays(logn_in, logT_in)
        pts = np.stack([R.ravel(), TT.ravel()], axis=1)
        v = 10.0 ** interp(pts).reshape(R.shape).squeeze()
        return float(v) if v.ndim == 0 else v
    if rho_a.shape == T_a.shape:
        # 同形状数组: 逐点对应 (如 Hugoniot 曲线点对 (rho_i, T_i))
        pts = np.stack([logn_in.ravel(), logT_in.ravel()], axis=1)
        return 10.0 ** interp(pts).reshape(logn_in.shape)
    # 异形状数组: 笛卡尔积网格 (rho x T 场重建)
    Rg, Tg = np.meshgrid(logn_in, logT_in, indexing="ij")
    pts = np.stack([Rg.ravel(), Tg.ravel()], axis=1)
    return 10.0 ** interp(pts).reshape(Rg.shape)


# ---------------------------------------------------------------
# 1. 等温线
# ---------------------------------------------------------------

def trace_isotherm(data: CN4Data, T_idx=10, T=None, x_axis="rho",
                   outfile=None, figsize=(10.0, 7.5)):
    """
    等温线: 固定温度, 绘制 P 与 e 随质量密度 rho (默认) 或离子数密度 n_i 的变化。
    左侧轴: P (J/cm^3, log), 右侧轴: e (J/g, log)。
    T_idx: 温度网格索引 (T 未给定时使用); T: 温度数值 (eV, 非网格点也支持, 自动插值)。
    Returns: (x, P, e, outfile), x 为 rho 或 nion 轴
    """
    setup_style()
    T_val = float(data.temperature[T_idx]) if T is None else float(T)
    nion = data.density
    rho_axis = rho_from_nion(data, nion)
    P = interpolate_quantity(data, "p", rho_axis, T_val, field=_press(data))
    e = interpolate_quantity(data, "e", rho_axis, T_val, field=_energy(data))

    use_rho = (x_axis == "rho")
    x = rho_axis if use_rho else nion
    xlabel = (r"Mass density $\rho$ (g/cm$^3$)"
              if use_rho else r"Ion Number Density $n_i$ (cm$^{-3}$)")

    # 显示单位: P -> Mbar, e -> erg/g (CGS)
    P = pressure_mbar(P)
    e = energy_ergg(e)

    fig, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(x, P, "o-", lw=2.5, ms=7, color="tab:red",
             label="Pressure $P$ (Mbar)")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel("Pressure $P$ (Mbar)")
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax2 = ax1.twinx()
    ax2.plot(x, e, "s-", lw=2.5, ms=7, color="tab:blue",
             label="Energy $e$ (erg/g)")
    ax2.set_yscale("log")
    ax2.set_ylabel("Specific energy $e$ (erg/g)")
    ax2.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_title(f"Isotherm, T = {T_val:.4e} eV")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=FONT_SIZE_TICK, loc="best")
    _style(ax1); _style(ax2)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isotherm_T{T_val:.3e}")
    print(f"[eos] isotherm T={T_val:.4e} eV -> {outfile}")
    return x, P, e, outfile


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
        raise ValueError(f"等压线 P={pressure_mbar(P):.3e} Mbar 超出数据范围 "
                         f"({pressure_mbar(Pgrid.min()):.2e} ~ "
                         f"{pressure_mbar(Pgrid.max()):.2e} Mbar)")
    # 等高线提取 (线性场, seg 坐标即为线性 T, n_i)
    fig0, ax0 = plt.subplots()
    CS = ax0.contour(data.temperature, data.density, Pgrid, levels=[P])
    plt.close(fig0)
    if not CS.allsegs or not CS.allsegs[0]:
        raise ValueError(f"等压线 P={pressure_mbar(P):.3e} Mbar 未在网格内形成等值线")
    seg = CS.allsegs[0][0]
    T_c = seg[:, 0]
    n_c = seg[:, 1]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(T_c, n_c, "o-", lw=2.5, ms=6, color="tab:green")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Temperature $T$ (eV)")
    ax.set_ylabel(r"Ion Number Density $n_i$ (cm$^{-3}$)")
    ax.set_title(f"Isobar, P = {pressure_mbar(P):.3e} Mbar")
    _style(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isobar_P{pressure_mbar(P):.2e}Mbar")
    print(f"[eos] isobar P={pressure_mbar(P):.3e} Mbar -> {outfile}")
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
    ax.set_title(f"Isentrope, s = {energy_ergg(s0):.4f} erg/(g eV)")
    _style(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isentrope_s{energy_ergg(s0):.2e}")
    print(f"[eos] isentrope s={energy_ergg(s0):.4f} erg/(g eV) -> {outfile}")
    return T_c, n_c, outfile


# ---------------------------------------------------------------
# 4. 冲击雨贡纽
# ---------------------------------------------------------------

def _extract_hugoniot_curve(data: CN4Data, rho0: float, P0: float, e0: float,
                            n_rho=240, n_T=80, clip=True):
    """
    在插值后的连续 (rho, T) 空间求 Hugoniot 残差 H=0 曲线。

    P(rho,T)、e(rho,T) 均由二维插值 (log n_i x log T) 获得, 因此曲线上
    任意点、以及 H 过零的"最佳位置"都不必落在表格网格上:
        H(rho,T) = (e - e0) - 0.5 (P + P0) (1/rho0 - 1/rho)
    在精细 (rho, T) 网格 (对数均匀) 上计算 H 场, 用 contour 提取 H=0
    等值线段 -> 数据点密集且位于插值区域内部。

    Returns: (rho_c, P_c, T_c) 一维数组 (仅压缩分支 rho>rho0, 按 rho 升序)
    """
    rho_hi = rho_from_nion(data, data.density[-1])
    rho_grid = 10 ** np.linspace(np.log10(rho0), np.log10(rho_hi), n_rho)
    T_grid = 10 ** np.linspace(
        np.log10(data.temperature[0]), np.log10(data.temperature[-1]), n_T)

    P_f = interpolate_quantity(data, "p", rho_grid, T_grid,
                               field=_press(data), clip=clip)
    e_f = interpolate_quantity(data, "e", rho_grid, T_grid,
                               field=_energy(data), clip=clip)
    H = (e_f - e0) - 0.5 * (P_f + P0) * (1.0 / rho0 - 1.0 / rho_grid[:, None])

    fig0, ax0 = plt.subplots()
    CS = ax0.contour(T_grid, rho_grid, H, levels=[0.0])
    plt.close(fig0)

    segs = CS.allsegs[0] if (CS.allsegs and CS.allsegs[0]) else []
    if not segs:
        raise ValueError("插值区域中未找到 Hugoniot H=0 曲线, "
                         "请调整参考态或检查其物理性")

    rho_list, P_list, T_list = [], [], []
    for seg in segs:
        if len(seg) < 2:
            continue
        T_s = seg[:, 0]
        rho_s = seg[:, 1]
        P_s = interpolate_quantity(data, "p", rho_s, T_s,
                                   field=_press(data), clip=False)
        rho_list.append(rho_s)
        P_list.append(P_s)
        T_list.append(T_s)
    if not rho_list:
        raise ValueError("Hugoniot 等值线段为空")
    rho_c = np.concatenate(rho_list)
    P_c = np.concatenate(P_list)
    T_c = np.concatenate(T_list)

    # 仅保留压缩分支 (rho > rho0), 按 rho 升序并去重
    m = rho_c > rho0 * (1.0 + 1e-9)
    rho_c, P_c, T_c = rho_c[m], P_c[m], T_c[m]
    order = np.argsort(rho_c)
    rho_c, P_c, T_c = rho_c[order], P_c[order], T_c[order]
    if len(rho_c) > 1:
        keep = np.ones(len(rho_c), dtype=bool)
        keep[1:] = np.diff(np.log10(rho_c)) > 1e-5
        rho_c, P_c, T_c = rho_c[keep], P_c[keep], T_c[keep]
    if len(rho_c) == 0:
        raise ValueError("参考态上方无压缩分支 (rho > rho0 为空)")
    return rho_c, P_c, T_c


def trace_hugoniot(data: CN4Data, ref_idx=(0, 0), rho0=None, T0=None,
                   outfile=None, figsize=(12.0, 8.0),
                   n_rho=240, n_T=80, clip=True):
    """
    冲击雨贡纽: 给定参考态 (rho0, P0, e0), 在插值后的连续 (rho, T) 空间
    求 Hugoniot 残差 H=0 曲线:
        H(rho,T) = (e - e0) - 0.5 (P + P0) (1/rho0 - 1/rho)
    其中 P(rho,T)、e(rho,T) 均由二维插值获得 —— 参考态与曲线上任意点
    (包括 H 过零的"最佳残差位置") 都不必落在表格网格上, 数据点密集。
    并换算冲击速度 Us 与粒子速度 Up:
        Us^2 = (P - P0) / (rho0 (1 - rho0/rho))
        Up  = Us (1 - rho0/rho)

    参考态输入 (二选一):
      - ref_idx=(i, j): 直接取网格点 (默认, 向后兼容)
      - rho0 (g/cm^3), T0 (eV): 任意数值 (支持非网格点), 通过二维插值
        求 P0、e0; T0 缺省时取表最低温度。

    n_rho/n_T: 插值残差场的精细网格密度 (决定 Hugoniot 曲线点数)。

    输出: 主图 (rho-P 雨贡纽 + Us-Up 关系并排); 另有独立函数
    plot_usup_vs_pressure 绘制 Us/Up 随压力 P 的关系。
    """
    setup_style()
    P = _press(data)
    e = _energy(data)

    if rho0 is not None:
        T0_eff = float(data.temperature[0]) if T0 is None else float(T0)
        P0 = interpolate_quantity(data, "p", rho0, T0_eff, field=P)
        e0 = interpolate_quantity(data, "e", rho0, T0_eff, field=e)
        rho0_eff = float(rho0)
        print(f"[eos] hugoniot 参考态 (插值): rho0={rho0_eff:.4e} g/cm^3, "
              f"T0={T0_eff:.4e} eV, P0={pressure_mbar(P0):.4e} Mbar, "
              f"e0={energy_ergg(e0):.4e} erg/g")
    else:
        rho0_eff = float(rho[ref_idx])
        P0 = float(P[ref_idx])
        e0 = float(e[ref_idx])
        print(f"[eos] hugoniot 参考态 (网格点): rho0={rho0_eff:.4e} g/cm^3, "
              f"P0={pressure_mbar(P0):.4e} Mbar")

    # 在插值连续空间求 H=0 曲线 (数据点位于插值区域内, 非网格点)
    rho_c, P_c, T_c = _extract_hugoniot_curve(
        data, rho0_eff, P0, e0, n_rho=n_rho, n_T=n_T, clip=clip)

    # Us-Up 关系 (过滤非有限值, 弱冲击极限处 Us 发散)
    Us = np.sqrt(np.maximum((P_c - P0) / (rho0_eff * (1.0 - rho0_eff / rho_c)), 0))
    Up = Us * (1.0 - rho0_eff / rho_c)
    finite = np.isfinite(Us) & np.isfinite(Up) & (Us > 0) & (rho_c > rho0_eff)
    rho_c, P_c, T_c, Us, Up = rho_c[finite], P_c[finite], T_c[finite], Us[finite], Up[finite]
    if len(rho_c) == 0:
        raise ValueError("压缩分支过滤后为空 (Us/Up 非有限)")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    # 左: rho-P 雨贡纽 (P 显示 Mbar)。
    #   - Hugoniot 用散点 (H=0 等值线在 (T,rho) 平面非单调, 同一 rho 可能对应
    #     多个 T, 连线会来回跳跃, 散点如实展示)。
    #   - 轴范围聚焦从参考态开始的压缩分支 (而非全表范围)。
    rho_full = rho_from_nion(data, data.density)
    Pr_full = interpolate_quantity(data, "p", rho_full,
                                   data.temperature[0], field=P, clip=True)
    ax1.plot(rho_full, pressure_mbar(Pr_full), "-", lw=2.0, color="gray",
             label="Table row (lowest T, interp)")
    ax1.plot(rho_c, pressure_mbar(P_c), "o", ms=5, mfc="tab:red",
             mec="none", alpha=0.85,
             label=f"Hugoniot ({len(rho_c)} pts)")
    ax1.plot([rho0_eff], [pressure_mbar(P0)], "*", ms=20, color="black",
             label="Reference state")
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel(r"Mass density $\rho$ (g/cm$^3$)")
    ax1.set_ylabel("Pressure $P$ (Mbar)")
    ax1.set_title("Shock Hugoniot")
    # 放大到参考态附近 (覆盖 Hugoniot 压缩分支, 留 20~50% 边距)
    rho_hi = max(rho0_eff * 1.05, rho_c.max())
    ax1.set_xlim(rho0_eff * 0.5, rho_hi * 1.3)
    p_lo = min(P0, P_c.min())
    p_hi = max(P0, P_c.max())
    ax1.set_ylim(pressure_mbar(p_lo) * 0.5, pressure_mbar(p_hi) * 2.0)
    ax1.legend(fontsize=FONT_SIZE_TICK)
    # 右: Us-Up (显示单位 um/ns; 按 rho 排序后 Up/Us 均单调, 连线可读)
    ax2.plot(velocity_umns(Up), velocity_umns(Us), "o", ms=4,
             mfc="tab:blue", mec="none", alpha=0.85,
             label=f"{len(Us)} pts")
    ax2.set_xlabel(r"Particle velocity $U_p$ (um/ns)")
    ax2.set_ylabel(r"Shock velocity $U_s$ (um/ns)")
    ax2.set_title(r"$U_s$-$U_p$ relation")
    ax2.legend(fontsize=FONT_SIZE_TICK)
    for a in (ax1, ax2):
        _style(a)
    fig.tight_layout()
    outfile = _save(fig, outfile, "hugoniot")
    print(f"[eos] hugoniot: {len(rho_c)} 个插值压缩点, "
          f"rho0={rho0_eff:.4e} g/cm^3 -> {outfile}")
    return rho_c, P_c, Us, Up, outfile


def plot_usup_vs_pressure(Us, Up, P, outfile=None, figsize=(9.0, 6.5)):
    """
    绘制 Us、Up 随压力 P 的关系图 (log-log, 双曲线 + 图例)。
    显示单位: P -> Mbar, Us/Up -> um/ns。
    用于 Hugoniot 后处理: 展示冲击/粒子速度与压力的关联。
    Returns: 输出文件路径
    """
    setup_style()
    P_mbar = pressure_mbar(np.asarray(P, dtype=float))
    Us_umns = velocity_umns(np.asarray(Us, dtype=float))
    Up_umns = velocity_umns(np.asarray(Up, dtype=float))
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(P_mbar, Us_umns, "o", ms=5, mfc="tab:blue", mec="none",
            alpha=0.85, label=r"Shock velocity $U_s$ (um/ns)")
    ax.plot(P_mbar, Up_umns, "s", ms=5, mfc="tab:orange", mec="none",
            alpha=0.85, label=r"Particle velocity $U_p$ (um/ns)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Pressure $P$ (Mbar)")
    ax.set_ylabel("Velocity (um/ns)")
    ax.set_title(r"$U_s$ / $U_p$ vs Pressure $P$")
    ax.legend(fontsize=FONT_SIZE_TICK)
    _style(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, "hugoniot_usup_vs_P")
    print(f"[eos] Us/Up vs P -> {outfile}")
    return outfile


def plot_interpolated_probe(data: CN4Data, rho_probe: float, T_probe: float,
                            outfile=None, figsize=(10.0, 7.5)):
    """
    插值探针图: 固定质量密度 rho_probe (g/cm^3, 可非网格点),
    沿温度轴插值 P 与 zbar, 并标记参考点 (rho_probe, T_probe)。
    验证 rho-T 输入 + 二维插值对任意 (rho, T) 的可用性。
    Returns: (outfile, info_dict)
    """
    setup_style()
    Ts = data.temperature
    P_probe = interpolate_quantity(data, "p", rho_probe, Ts, field=_press(data))
    e_probe = interpolate_quantity(data, "e", rho_probe, Ts, field=_energy(data))
    zb_probe = interpolate_quantity(data, "zbar", rho_probe, Ts)

    P_at = interpolate_quantity(data, "p", rho_probe, T_probe,
                                field=_press(data))
    zb_at = interpolate_quantity(data, "zbar", rho_probe, T_probe)
    e_at = interpolate_quantity(data, "e", rho_probe, T_probe,
                                field=_energy(data))

    # 显示单位: P -> Mbar, e -> erg/g
    P_probe = pressure_mbar(P_probe)
    e_probe = energy_ergg(e_probe)
    P_at = pressure_mbar(P_at)
    e_at = energy_ergg(e_at)

    fig, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(Ts, P_probe, "o-", lw=2.5, ms=6, color="tab:red",
             label="Pressure $P$ (Mbar)")
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel(r"Temperature $T$ (eV)")
    ax1.set_ylabel("Pressure $P$ (Mbar)")
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax2 = ax1.twinx()
    ax2.plot(Ts, zb_probe, "s-", lw=2.5, ms=6, color="tab:blue",
             label="Average charge $\\langle Z \\rangle$")
    ax2.set_xscale("log")
    ax2.set_ylabel(r"Average charge $\langle Z \rangle$")
    ax2.tick_params(axis="y", labelcolor="tab:blue")
    ax1.plot([T_probe], [P_at], "D", ms=14, color="black",
             label=f"Probe ({rho_probe:.3g} g/cm$^3$, {T_probe:.4g} eV)")
    ax1.set_title(f"Interpolated EOS at fixed $\\rho$ = {rho_probe:.4g} g/cm$^3$")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=FONT_SIZE_TICK, loc="best")
    _style(ax1); _style(ax2)
    fig.tight_layout()
    outfile = _save(fig, outfile, "interp_probe_rhoT")
    print(f"[eos] interp probe rho={rho_probe:.4g} g/cm^3 -> {outfile}")

    info = {
        "rho_probe": rho_probe, "T_probe": T_probe,
        "P_probe_Mbar": P_at, "e_probe_ergg": e_at, "zbar_probe": zb_at,
    }
    return outfile, info


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
