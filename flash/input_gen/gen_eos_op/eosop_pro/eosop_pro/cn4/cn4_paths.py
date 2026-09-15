# -*- coding: utf-8 -*-
"""cn4 物态方程 (EOS) 路径研究 —— 等温 / 等压 / 等熵 / 冲击雨贡纽。

从 cn4 静态 ``(T, n_ion)`` 表格出发研究典型热力学路径::

    1. 等温线 (isotherm) : T 固定, 输出 P(n_ion), e(n_ion)
    2. 等压线 (isobar)   : P 固定, 在 (T, n_ion) 网格上提取 P=const 曲线
    3. 等熵线 (isentrope): 由热力学第一定律数值积分熵场, 提取 s=const 曲线
    4. 冲击雨贡纽 (Hugoniot): 给定参考态 (rho0,P0,e0), 求满足
       ``(e-e0) = (P+P0)(1/rho0 - 1/rho)/2`` 的状态点集, 并给出 Us-Up 关系

物理量组合（来自 cn4 块）
-------------------------
======================  ==========================================
``P = p_ion + p_ele``   J/cm^3   (block 5 + 6)
``e = e_ion + e_ele``   J/g      (block 9 + 10)
``cv = cv_ion + cv_ele`` J/g/eV   (block 11 + 12)
``rho = n_ion*<A>/N_A``  g/cm^3  (block 2 + 头部原子量)
``T = temperature``     eV       (block 1)
======================  ==========================================

单位纪律
--------
本模块内部计算**一律使用 cn4 原始单位**（J/cm^3, J/g, cm^-3, eV），
仅在**绘图与返回值展示**处经 :mod:`eosop_pro.cn4.units` 换算到显示单位
（Mbar, erg/g, um/ns）。每个换算式均带注释说明依据。

绘图遵循项目 ``plotting.style`` 硬性约定: 全英文、字号 ≥18pt、
DPI ≥450、linewidth ≥2、markersize ≥8。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

from .. import config
from ..plotting.style import apply_style
from .cn4_io import NA, CN4Table, CN4ParseError
from .units import (
    P_JCM3_TO_MBAR,
    E_JG_TO_ERG_G,
    V_CMS_TO_UM_NS,
    density_gcc_from_nion,
    nion_from_rhogcc,
    pressure_mbar,
    energy_ergg,
    velocity_umns,
)

__all__ = [
    "nion_from_rho", "rho_from_nion", "interpolate_quantity",
    "trace_isotherm", "trace_isobar", "compute_entropy", "trace_isentrope",
    "trace_hugoniot", "plot_usup_vs_pressure", "plot_interpolated_probe",
    "sound_speed", "plot_pv_diagram",
]


# ── 内部辅助: 列表 ↔ numpy 视图 ─────────────────────────────────
def _arr2d(tbl: CN4Table, name: str) -> np.ndarray:
    """取二维场为 ``(ndens, ntemp)`` 的 numpy 数组（内部计算用）。"""
    flat = np.asarray(tbl.field(name), dtype=float)
    return flat.reshape(tbl.ndens, tbl.ntemp)


def _press(tbl: CN4Table) -> np.ndarray:
    """总压力 ``(ndens, ntemp)`` J/cm^3 —— block 5 + 6。"""
    return _arr2d(tbl, "p_ion") + _arr2d(tbl, "p_ele")


def _energy(tbl: CN4Table) -> np.ndarray:
    """总比内能 ``(ndens, ntemp)`` J/g —— block 9 + 10。"""
    return _arr2d(tbl, "e_ion") + _arr2d(tbl, "e_ele")


def _heatcp(tbl: CN4Table) -> np.ndarray:
    """总比热 ``(ndens, ntemp)`` J/g/eV —— block 11 + 12。"""
    return _arr2d(tbl, "cv_ion") + _arr2d(tbl, "cv_ele")


def _rho(tbl: CN4Table) -> np.ndarray:
    """质量密度 ``(ndens, ntemp)`` g/cm^3（沿温度广播）。"""
    aw = tbl.avgatw
    if aw is None:
        raise CN4ParseError(
            "平均原子量未知 -> 无法换算质量密度。"
            "请提供 atomwt 或在 cn4 同目录放置 ionmxinp。"
        )
    rho1d = density_gcc_from_nion(np.asarray(tbl.density, dtype=float), aw)
    return np.broadcast_to(rho1d[:, None], (tbl.ndens, tbl.ntemp))


def _style_ax(ax) -> None:
    """统一坐标轴视觉（PPT 级边框/刻度线宽）。"""
    ax.tick_params(which="both", direction="in", top=True, right=True)
    for s in ax.spines.values():
        s.set_linewidth(1.5)


def _save(fig, outfile, tag: str) -> str:
    """保存图像；``outfile=None`` 时写到 cwd。"""
    if outfile is None:
        outfile = os.path.join(os.getcwd(), f"eos_{tag}.png")
    outfile = str(outfile)
    Path(outfile).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outfile, dpi=config.PLOT_DPI, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return outfile


# ================================================================
# 0. rho-T 输入与二维插值
#    cn4 表格的密度轴是离子数密度 n_ion (cm^-3)，需先换算:
#        n_ion = rho * N_A / <A>
#    支持非网格点: 在 (log n_ion, log T) 上做二维线性插值。
# ================================================================

def nion_from_rho(tbl: CN4Table, rho):
    """质量密度 rho (g/cm^3) -> 离子数密度 n_ion (cm^-3)。"""
    aw = tbl.avgatw
    if aw is None:
        raise CN4ParseError("原子量未知, 无法换算 rho -> nion")
    return nion_from_rhogcc(np.asarray(rho, dtype=float), aw)


def rho_from_nion(tbl: CN4Table, nion):
    """离子数密度 n_ion (cm^-3) -> 质量密度 rho (g/cm^3)。"""
    aw = tbl.avgatw
    if aw is None:
        raise CN4ParseError("原子量未知, 无法换算 nion -> rho")
    return density_gcc_from_nion(np.asarray(nion, dtype=float), aw)


def interpolate_quantity(tbl: CN4Table, qname: str, rho, T,
                         clip: bool = True, field=None):
    """在 ``(log n_ion, log T)`` 网格上二维插值物理量，支持任意 (rho, T)。

    Args:
        tbl: :class:`CN4Table`
        qname: 物理量名（``tbl.field`` / 派生量 ``P`` / ``E`` / ``rho`` …）
        rho: 质量密度 (g/cm^3, 标量或数组)
        T: 温度 (eV, 标量或数组)
        clip: 越界时 clamp 到表边界（默认 True）
        field: 可选，直接传入物理量场 ``(ndens, ntemp)`` 覆盖 ``qname`` 查询
            （用于组合量 ``P = p_ion+p_ele`` 等）

    Returns:
        语义自动分派:
          * ``rho``、``T`` 均标量 -> ``float``
          * 其一为数组（广播）     -> 一维数组
          * 同形状数组             -> 同形状数组（逐点对应）
          * 异形状数组             -> ``(n_rho, n_T)`` 网格（笛卡尔积）
    """
    from scipy.interpolate import RegularGridInterpolator

    if field is not None:
        fld = np.asarray(field, dtype=float)
    elif qname in ("P", "p", "ptot"):
        fld = _press(tbl)
    elif qname in ("E", "e", "etot"):
        fld = _energy(tbl)
    elif qname in ("rho", "rhoe"):
        fld = _rho(tbl)
    elif qname in ("cv", "cvtot"):
        fld = _heatcp(tbl)
    else:
        fld = _arr2d(tbl, qname)

    if fld.shape != (tbl.ndens, tbl.ntemp):
        raise CN4ParseError(
            f"物理量场形状 {fld.shape} != (ndens={tbl.ndens}, ntemp={tbl.ntemp})"
        )
    if np.any(fld <= 0):
        # ⚠️ 2026-09 修正：原实现对**整场**拒绝（``raise``），过严 ——
        #    真实 EOS 在冷区（低温/低密）的能量含负值（结合能），
        #    这会把整张表判死刑，即使查询的高温等温线远离负值区。
        #    改为**掩码**：非正值 -> NaN，仅污染其邻域的插值点
        #    （双线性插值只涉及周围 4 格点），远离冷区的查询不受影响；
        #    受影响点返回 NaN，下游绘图自然断线 —— 语义诚实。
        fld = np.where(fld > 0, fld, np.nan)

    logn = np.log10(np.asarray(tbl.density, dtype=float))
    logT = np.log10(np.asarray(tbl.temperature, dtype=float))

    rho_a = np.asarray(rho, dtype=float)
    T_a = np.asarray(T, dtype=float)
    rho_scalar = (rho_a.ndim == 0)
    T_scalar = (T_a.ndim == 0)

    logn_in = np.log10(nion_from_rho(tbl, rho_a))
    logT_in = np.log10(T_a)

    if clip:
        lo_n, hi_n = logn[0], logn[-1]
        lo_T, hi_T = logT[0], logT[-1]
        if (np.any(logn_in < lo_n) or np.any(logn_in > hi_n)
                or np.any(logT_in < lo_T) or np.any(logT_in > hi_T)):
            aw = tbl.avgatw
            rho_lo = 10 ** lo_n * aw / NA
            rho_hi = 10 ** hi_n * aw / NA
            print(f"[cn4.interp] 输入越界, clamp 到表范围: "
                  f"rho in [{rho_lo:.3e},{rho_hi:.3e}] g/cm3, "
                  f"T in [{10 ** lo_T:.3e},{10 ** hi_T:.3e}] eV")
        logn_in = np.clip(logn_in, lo_n, hi_n)
        logT_in = np.clip(logT_in, lo_T, hi_T)

    interp = RegularGridInterpolator(
        (logn, logT), np.log10(fld), bounds_error=False, fill_value=None)

    if rho_scalar and T_scalar:
        return float(10.0 ** interp([[float(logn_in), float(logT_in)]])[0])
    if rho_scalar or T_scalar:
        R, TT = np.broadcast_arrays(logn_in, logT_in)
        pts = np.stack([R.ravel(), TT.ravel()], axis=1)
        v = 10.0 ** interp(pts).reshape(R.shape).squeeze()
        return float(v) if np.ndim(v) == 0 else v
    if rho_a.shape == T_a.shape:
        pts = np.stack([logn_in.ravel(), logT_in.ravel()], axis=1)
        return 10.0 ** interp(pts).reshape(logn_in.shape)
    Rg, Tg = np.meshgrid(logn_in, logT_in, indexing="ij")
    pts = np.stack([Rg.ravel(), Tg.ravel()], axis=1)
    return 10.0 ** interp(pts).reshape(Rg.shape)


# ================================================================
# 1. 等温线
# ================================================================

def trace_isotherm(tbl: CN4Table, T_idx: int = 10, T: Optional[float] = None,
                   x_axis: str = "rho", outfile=None,
                   figsize=(10.0, 7.5)):
    """等温线: 固定温度，绘制 ``P`` 与 ``e`` 随质量密度 ``rho``（默认）或 ``n_ion``。

    左轴 ``P`` (Mbar, log)，右轴 ``e`` (erg/g, log)。

    Args:
        T_idx: 温度网格索引（``T`` 未给定时使用）
        T: 温度数值 (eV)，支持非网格点（自动插值）
        x_axis: ``"rho"`` (g/cm^3) 或 ``"nion"`` (cm^-3)

    Returns:
        ``(x, P_mbar, e_ergg, outfile)``
    """
    import matplotlib.pyplot as plt
    apply_style()

    T_val = float(tbl.temperature[T_idx]) if T is None else float(T)
    # 加密 rho 轴: 表密度点 -> 精细对数网格, 充分利用插值
    # ⚠️ 只取**正**密度点：跨族转换表（如 .301 -> cn4）首点可为
    #    ``0.0`` 哨兵，``log10(0) = -inf`` 会污染整条 linspace（NaN 传播）。
    nion_tab = np.asarray(tbl.density, dtype=float)
    nion_pos = nion_tab[nion_tab > 0]
    if nion_pos.size < 2:
        raise CN4ParseError("表的正密度点不足 2 个, 无法画等温线")
    nion = 10 ** np.linspace(np.log10(nion_pos[0]),
                             np.log10(nion_pos[-1]), 200)
    rho_axis = rho_from_nion(tbl, nion)

    P = interpolate_quantity(tbl, "P", rho_axis, T_val, field=_press(tbl))
    e = interpolate_quantity(tbl, "E", rho_axis, T_val, field=_energy(tbl))

    use_rho = (x_axis == "rho")
    x = rho_axis if use_rho else nion
    xlabel = (r"Mass density $\rho$ (g/cm$^3$)" if use_rho
              else r"Ion number density $n_i$ (cm$^{-3}$)")

    P = pressure_mbar(P)      # J/cm3 -> Mbar
    e = energy_ergg(e)        # J/g   -> erg/g

    fig, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(x, P, "o-", lw=config.PLOT_LINEWIDTH, ms=6, color="tab:red",
             label=r"Pressure $P$ (Mbar)")
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(r"Pressure $P$ (Mbar)")
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax2 = ax1.twinx()
    ax2.plot(x, e, "s-", lw=config.PLOT_LINEWIDTH, ms=6, color="tab:blue",
             label=r"Specific energy $e$ (erg/g)")
    ax2.set_yscale("log")
    ax2.set_ylabel(r"Specific energy $e$ (erg/g)")
    ax2.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_title(rf"Isotherm, $T$ = {T_val:.4e} eV")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")
    _style_ax(ax1); _style_ax(ax2)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isotherm_T{T_val:.3e}")
    print(f"[cn4.eos] isotherm T={T_val:.4e} eV -> {outfile}")
    return x, P, e, outfile


# ================================================================
# 2. 等压线
# ================================================================

def trace_isobar(tbl: CN4Table, P: float, outfile=None, figsize=(10.0, 7.5)):
    """等压线: 在 ``(T, n_ion)`` 网格上提取 ``P = const`` 曲线。

    Args:
        P: 目标压力，**单位 J/cm^3**（cn4 原始单位；调用方可用
           ``P_mbar / P_JCM3_TO_MBAR`` 从 Mbar 换算）

    Returns:
        ``(T_curve, nion_curve, outfile)``
    """
    import matplotlib.pyplot as plt
    apply_style()

    Pgrid = _press(tbl)
    if not (Pgrid.min() <= P <= Pgrid.max()):
        raise ValueError(
            f"等压线 P={pressure_mbar(P):.3e} Mbar 超出数据范围 "
            f"({pressure_mbar(Pgrid.min()):.2e} ~ "
            f"{pressure_mbar(Pgrid.max()):.2e} Mbar)"
        )
    T_axis = np.asarray(tbl.temperature, dtype=float)
    n_axis = np.asarray(tbl.density, dtype=float)

    fig0, ax0 = plt.subplots()
    CS = ax0.contour(T_axis, n_axis, Pgrid, levels=[P])
    plt.close(fig0)
    if not CS.allsegs or not CS.allsegs[0]:
        raise ValueError(
            f"等压线 P={pressure_mbar(P):.3e} Mbar 未在网格内形成等值线"
        )
    seg = CS.allsegs[0][0]
    T_c, n_c = seg[:, 0], seg[:, 1]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(T_c, n_c, "o-", lw=config.PLOT_LINEWIDTH, ms=5, color="tab:green")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Temperature $T$ (eV)")
    ax.set_ylabel(r"Ion number density $n_i$ (cm$^{-3}$)")
    ax.set_title(rf"Isobar, $P$ = {pressure_mbar(P):.3e} Mbar")
    _style_ax(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isobar_P{pressure_mbar(P):.2e}Mbar")
    print(f"[cn4.eos] isobar P={pressure_mbar(P):.3e} Mbar -> {outfile}")
    return T_c, n_c, outfile


# ================================================================
# 3. 熵场与等熵线
# ================================================================

def compute_entropy(tbl: CN4Table, ref_rho_idx: int = 0,
                    ref_T_idx: int = 0) -> np.ndarray:
    """数值积分熵场 ``s(T, n_ion)``，单位 J/(g·eV)。

    热力学基础 ``de = T ds + (P/rho^2) drho``::

        等容方向 (drho=0): ds = de / T
        等温方向 (dT=0)  : ds = -(P / (rho^2 T)) drho

    从参考点沿矩形路径（先密度后温度）积分全场。熵的绝对零点无物理意义，
    故最后整体减去参考点值 —— **只用于比较**（如提取等熵线）。

    Returns:
        ``s``，形状 ``(ndens, ntemp)``，单位 J/(g·eV)
    """
    T = np.asarray(tbl.temperature, dtype=float)
    rho = _rho(tbl)
    e = _energy(tbl)
    P = _press(tbl)
    ndens, ntemp = e.shape
    s = np.zeros_like(e)
    i0, j0 = ref_rho_idx, ref_T_idx

    # 步骤 1: 参考温度行 (j=j0)，沿密度方向积分 ds = -(P/(rho^2 T)) drho
    s[i0, j0] = 0.0
    for i in range(i0, 0, -1):
        drho = rho[i, j0] - rho[i - 1, j0]
        Tj = T[j0]
        Pbar = 0.5 * (P[i, j0] + P[i - 1, j0])
        rhobar2 = (0.5 * (rho[i, j0] + rho[i - 1, j0])) ** 2
        s[i - 1, j0] = s[i, j0] - (Pbar / (rhobar2 * Tj)) * drho
    for i in range(i0, ndens - 1):
        drho = rho[i + 1, j0] - rho[i, j0]
        Tj = T[j0]
        Pbar = 0.5 * (P[i, j0] + P[i + 1, j0])
        rhobar2 = (0.5 * (rho[i, j0] + rho[i + 1, j0])) ** 2
        s[i + 1, j0] = s[i, j0] - (Pbar / (rhobar2 * Tj)) * drho

    # 步骤 2: 每行沿温度方向积分 ds = de/T
    for i in range(ndens):
        for j in range(j0, 0, -1):
            de = e[i, j] - e[i, j - 1]
            Tbar = 0.5 * (T[j] + T[j - 1])
            s[i, j - 1] = s[i, j] - de / Tbar
        for j in range(j0, ntemp - 1):
            de = e[i, j + 1] - e[i, j]
            Tbar = 0.5 * (T[j] + T[j + 1])
            s[i, j + 1] = s[i, j] + de / Tbar

    s -= s[i0, j0]
    return s


def trace_isentrope(tbl: CN4Table, s: np.ndarray, s0_idx: Tuple[int, int] = (5, 10),
                    outfile=None, figsize=(10.0, 7.5)):
    """等熵线: 从参考点 ``s0 = s[s0_idx]`` 出发，提取 ``s = s0`` 曲线 ``(T, n_ion)``。

    Returns:
        ``(T_curve, nion_curve, outfile)``
    """
    import matplotlib.pyplot as plt
    apply_style()

    s0 = float(s[s0_idx])
    T_axis = np.asarray(tbl.temperature, dtype=float)
    n_axis = np.asarray(tbl.density, dtype=float)

    fig0, ax0 = plt.subplots()
    CS = ax0.contour(T_axis, n_axis, s, levels=[s0])
    plt.close(fig0)
    if not CS.allsegs or not CS.allsegs[0]:
        raise ValueError("等熵线未找到 (数据范围不足)")
    seg = CS.allsegs[0][0]
    T_c, n_c = seg[:, 0], seg[:, 1]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(T_c, n_c, "o-", lw=config.PLOT_LINEWIDTH, ms=5, color="tab:purple")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Temperature $T$ (eV)")
    ax.set_ylabel(r"Ion number density $n_i$ (cm$^{-3}$)")
    ax.set_title(rf"Isentrope, $s$ = {energy_ergg(s0):.4f} erg/(g eV)")
    _style_ax(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, f"isentrope_s{energy_ergg(s0):.2e}")
    print(f"[cn4.eos] isentrope s={energy_ergg(s0):.4f} erg/(g eV) -> {outfile}")
    return T_c, n_c, outfile


# ================================================================
# 4. 冲击雨贡纽
# ================================================================

def _extract_hugoniot_curve(tbl: CN4Table, rho0: float, P0: float, e0: float,
                            n_rho: int = 400, n_T: int = 120, clip: bool = True):
    """在插值后的连续 ``(rho, T)`` 空间求 Hugoniot 残差 ``H = 0`` 曲线。

    残差定义::

        H(rho,T) = (e - e0) - 0.5 (P + P0) (1/rho0 - 1/rho)

    ``P(rho,T)``、``e(rho,T)`` 均由二维插值获得，因此参考态与曲线上任意点
    （包括 ``H`` 过零的最佳位置）都不必落在表格网格上。

    搜索策略（覆盖整个表格范围）:
      * ``rho`` 轴: 从参考密度 ``rho0`` 到表最高质量密度（对数均匀）
      * ``T`` 轴: 从表最低温到最高温（对数均匀）
      * 逐列（固定 rho）沿 T + 逐行（固定 T）沿 rho **双方向**扫描，
        保证平面上所有 ``H=0`` 分支都被捕捉

    Returns:
        ``(rho_c, P_c, T_c)`` 一维数组（仅压缩分支 ``rho > rho0``，按 rho 升序）
    """
    rho_hi = rho_from_nion(tbl, float(np.max(tbl.density)))
    rho_grid = 10 ** np.linspace(np.log10(rho0), np.log10(rho_hi), n_rho)
    T_grid = 10 ** np.linspace(
        np.log10(tbl.temperature[0]), np.log10(tbl.temperature[-1]), n_T)

    P_f = interpolate_quantity(tbl, "P", rho_grid, T_grid,
                               field=_press(tbl), clip=clip)
    e_f = interpolate_quantity(tbl, "E", rho_grid, T_grid,
                               field=_energy(tbl), clip=clip)
    H = (e_f - e0) - 0.5 * (P_f + P0) * (1.0 / rho0 - 1.0 / rho_grid[:, None])

    rho_pts, T_pts = [], []
    # 逐列扫描: 固定 rho, 沿 T 找 H 过零
    for i in range(n_rho):
        Hrow = H[i]
        for j in range(n_T - 1):
            if Hrow[j] * Hrow[j + 1] < 0:
                fr = Hrow[j] / (Hrow[j] - Hrow[j + 1])
                T_c = 10 ** (np.log10(T_grid[j]) +
                             fr * (np.log10(T_grid[j + 1]) - np.log10(T_grid[j])))
                rho_pts.append(rho_grid[i])
                T_pts.append(T_c)
    # 逐行扫描: 固定 T, 沿 rho 找 H 过零（补充捕捉多支）
    for j in range(n_T):
        Hcol = H[:, j]
        for i in range(n_rho - 1):
            if Hcol[i] * Hcol[i + 1] < 0:
                fr = Hcol[i] / (Hcol[i] - Hcol[i + 1])
                rho_c = 10 ** (np.log10(rho_grid[i]) +
                               fr * (np.log10(rho_grid[i + 1]) - np.log10(rho_grid[i])))
                rho_pts.append(rho_c)
                T_pts.append(T_grid[j])
    if not rho_pts:
        raise ValueError("插值区域中未找到 Hugoniot H=0 曲线, "
                         "请调整参考态或检查其物理性")

    rho_c = np.asarray(rho_pts, dtype=float)
    T_c = np.asarray(T_pts, dtype=float)
    P_c = interpolate_quantity(tbl, "P", rho_c, T_c, field=_press(tbl), clip=False)

    # 仅保留压缩分支 (rho > rho0)，按 rho 升序并去重
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


def trace_hugoniot(tbl: CN4Table, ref_idx: Tuple[int, int] = (0, 0),
                   rho0: Optional[float] = None, T0: Optional[float] = None,
                   outfile=None, figsize=(12.0, 8.0),
                   n_rho: int = 240, n_T: int = 80, clip: bool = True):
    """冲击雨贡纽: 给定参考态 ``(rho0, P0, e0)``，在连续 ``(rho, T)`` 空间求
    ``H = 0`` 曲线，并换算冲击速度 ``Us`` 与粒子速度 ``Up``。

    Rankine-Hugoniot 关系（质量与动量守恒 + 能量守恒）::

        Us^2 = (P - P0) / (rho0 (1 - rho0/rho))
        Up   = Us (1 - rho0/rho)

    ⚠️ **单位**: 上式要求 ``P`` 用 **dyne/cm^2**（即 erg/cm^3），而 cn4 的
    ``P`` 是 J/cm^3，故计算时乘 ``1e7``（``1 J = 1e7 erg``）后 ``Us`` 才是
    cm/s。展示时再经 ``V_CMS_TO_UM_NS`` 换算为 um/ns。

    参考态输入（二选一）:
      * ``ref_idx=(i, j)``: 直接取网格点（默认，向后兼容）
      * ``rho0`` (g/cm^3), ``T0`` (eV): 任意数值（支持非网格点），
        经二维插值求 ``P0``、``e0``；``T0`` 缺省取表最低温度

    Returns:
        ``(rho_c, P_c, Us_cms, Up_cms, outfile)``
    """
    import matplotlib.pyplot as plt
    apply_style()

    P = _press(tbl)
    e = _energy(tbl)
    rho = _rho(tbl)

    if rho0 is not None:
        T0_eff = float(tbl.temperature[0]) if T0 is None else float(T0)
        P0 = interpolate_quantity(tbl, "P", rho0, T0_eff, field=P)
        e0 = interpolate_quantity(tbl, "E", rho0, T0_eff, field=e)
        rho0_eff = float(rho0)
        print(f"[cn4.eos] hugoniot ref (interp): rho0={rho0_eff:.4e} g/cm3, "
              f"T0={T0_eff:.4e} eV, P0={pressure_mbar(P0):.4e} Mbar, "
              f"e0={energy_ergg(e0):.4e} erg/g")
    else:
        # 参考态取网格点 (i_dens, j_temp)。★ 注意 rho 需由 n_ion 换算,
        # 该函数作用域内没有名为 rho 的变量（历史 bug: NameError）。
        rho_grid = _rho(tbl)                     # (ndens, ntemp) g/cm^3
        rho0_eff = float(rho_grid[ref_idx])
        P0 = float(P[ref_idx])
        e0 = float(e[ref_idx])
        print(f"[cn4.eos] hugoniot ref (grid): rho0={rho0_eff:.4e} g/cm3, "
              f"P0={pressure_mbar(P0):.4e} Mbar")

    rho_c, P_c, T_c = _extract_hugoniot_curve(
        tbl, rho0_eff, P0, e0, n_rho=n_rho, n_T=n_T, clip=clip)

    # Us/Up: P 需从 J/cm^3 换成 dyne/cm^2 (= erg/cm^3) -> 乘 1e7
    Us = np.sqrt(np.maximum(
        (P_c - P0) * 1e7 / (rho0_eff * (1.0 - rho0_eff / rho_c)), 0))
    Up = Us * (1.0 - rho0_eff / rho_c)
    finite = (np.isfinite(Us) & np.isfinite(Up) & (Us > 0)
              & (rho_c > rho0_eff))
    rho_c, P_c, T_c = rho_c[finite], P_c[finite], T_c[finite]
    Us, Up = Us[finite], Up[finite]
    if len(rho_c) == 0:
        raise ValueError("压缩分支过滤后为空 (Us/Up 非有限)")

    # 三幅图: rho-P 雨贡纽 | Us-Up 线性拟合 | P-V 雨贡纽
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(figsize[0] * 1.5,
                                                       figsize[1]))
    # 左: rho-P 雨贡纽（P 显示 Mbar）
    rho_full = rho_from_nion(tbl, np.asarray(tbl.density, dtype=float))
    Pr_full = interpolate_quantity(tbl, "P", rho_full,
                                   float(tbl.temperature[0]), field=P, clip=True)
    ax1.plot(rho_full, pressure_mbar(Pr_full), "-", lw=2.0, color="gray",
             label="Table row (lowest T, interp)")
    ax1.plot(rho_c, pressure_mbar(P_c), "o", ms=6, mfc="tab:red",
             mec="none", alpha=0.85, label=f"Hugoniot ({len(rho_c)} pts)")
    ax1.plot([rho0_eff], [pressure_mbar(P0)], "*", ms=20, color="black",
             label="Reference state")
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel(r"Mass density $\rho$ (g/cm$^3$)")
    ax1.set_ylabel(r"Pressure $P$ (Mbar)")
    ax1.set_title("Shock Hugoniot")
    ax1.set_xlim(rho0_eff * 0.5, max(rho0_eff * 1.05, rho_c.max()) * 1.3)
    p_lo, p_hi = min(P0, P_c.min()), max(P0, P_c.max())
    ax1.set_ylim(pressure_mbar(p_lo) * 0.5, pressure_mbar(p_hi) * 2.0)
    ax1.legend(loc="best")

    # 中: Us-Up（显示 um/ns；仅用 Up <= 80 um/ns 做线性拟合）
    Us_u = velocity_umns(Us)
    Up_u = velocity_umns(Up)
    fit_win = 80.0
    m_fit = Up_u <= fit_win
    if m_fit.sum() >= 2:
        k, b = np.polyfit(Up_u[m_fit], Us_u[m_fit], 1)
        yfit = k * Up_u[m_fit] + b
        ss_res = float(np.sum((Us_u[m_fit] - yfit) ** 2))
        ss_tot = float(np.sum((Us_u[m_fit] - np.mean(Us_u[m_fit])) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    else:
        k, b, r2, yfit = np.nan, np.nan, float("nan"), None
    ax2.plot(Up_u, Us_u, "o", ms=5, mfc="tab:blue", mec="none",
             alpha=0.85, label=f"Data ({len(Us)} pts)")
    if yfit is not None:
        ax2.plot(Up_u[m_fit], yfit, "--", lw=2.0, color="black", alpha=0.75,
                 label=rf"Fit ($U_p\leq {fit_win:.0f}$)")
    ax2.text(0.05, 0.97,
             rf"$U_s = {k:.4f}\,U_p + {b:.4e}$ um/ns" "\n"
             rf"(window $U_p\in[0,{fit_win:.0f}]$, $R^2 = {r2:.4f}$)",
             transform=ax2.transAxes, ha="left", va="top",
             bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85))
    ax2.set_xlabel(r"Particle velocity $U_p$ (um/ns)")
    ax2.set_ylabel(r"Shock velocity $U_s$ (um/ns)")
    ax2.set_title(r"$U_s$-$U_p$ relation (linear fit)")
    ax2.legend(loc="best")
    ax2.set_xlim(0.0, fit_win)
    if m_fit.sum() >= 1:
        ax2.set_ylim(0.0, float(np.nanmax(Us_u[m_fit])) * 1.1)

    # 右: P-V 雨贡纽（V = 1/rho 比体积）
    V_c = 1.0 / rho_c
    V0 = 1.0 / rho0_eff
    ax3.plot(V_c, pressure_mbar(P_c), "o", ms=6, mfc="tab:green",
             mec="none", alpha=0.85, label=f"Hugoniot ({len(V_c)} pts)")
    ax3.plot([V0], [pressure_mbar(P0)], "*", ms=20, color="black",
             label="Reference state")
    ax3.set_xscale("log"); ax3.set_yscale("log")
    ax3.set_xlabel(r"Specific volume $V = 1/\rho$ (cm$^3$/g)")
    ax3.set_ylabel(r"Pressure $P$ (Mbar)")
    ax3.set_title("Hugoniot in P-V plane")
    ax3.set_xlim(V_c.min() * 0.8, V0 * 1.2)
    ax3.set_ylim(pressure_mbar(p_lo) * 0.5, pressure_mbar(p_hi) * 2.0)
    ax3.legend(loc="best")

    for a in (ax1, ax2, ax3):
        _style_ax(a)
    fig.tight_layout()
    outfile = _save(fig, outfile, "hugoniot")
    print(f"[cn4.eos] hugoniot: {len(rho_c)} interp compression pts, "
          f"rho0={rho0_eff:.4e} g/cm3 -> {outfile}")
    return rho_c, P_c, Us, Up, outfile


def plot_usup_vs_pressure(Us, Up, P, outfile=None, figsize=(9.0, 6.5)):
    """绘制 ``Us``、``Up`` 随压力 ``P`` 的关系。

    显示单位: ``P`` -> Mbar（对数轴）, ``Us``/``Up`` -> um/ns（线性轴，窗口 [0,100]）。

    Returns:
        输出文件路径
    """
    import matplotlib.pyplot as plt
    apply_style()

    Us_u = velocity_umns(np.asarray(Us, dtype=float))
    Up_u = velocity_umns(np.asarray(Up, dtype=float))
    P_m = pressure_mbar(np.asarray(P, dtype=float))

    keep = ((Us_u >= 0) & (Us_u <= 100.0) & (Up_u >= 0) & (Up_u <= 100.0))
    if keep.sum() == 0:
        keep = np.ones_like(keep, dtype=bool)
    P_w, Us_w, Up_w = P_m[keep], Us_u[keep], Up_u[keep]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(P_w, Us_w, "o", ms=6, mfc="tab:blue", mec="none", alpha=0.85,
            label=r"Shock velocity $U_s$ (um/ns)")
    ax.plot(P_w, Up_w, "s", ms=6, mfc="tab:orange", mec="none", alpha=0.85,
            label=r"Particle velocity $U_p$ (um/ns)")
    ax.set_xscale("log")
    ax.set_ylim(0.0, 100.0)
    ax.set_xlabel(r"Pressure $P$ (Mbar)")
    ax.set_ylabel(r"Velocity (um/ns)")
    ax.set_title(r"$U_s$ / $U_p$ vs Pressure $P$")
    if len(P_w):
        ax.set_xlim(P_w.min() * 0.5, P_w.max() * 2.0)
    ax.legend(loc="best")
    _style_ax(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, "hugoniot_usup_vs_P")
    print(f"[cn4.eos] Us/Up vs P (window [0,100] um/ns, {len(P_w)} pts) -> {outfile}")
    return outfile


def plot_interpolated_probe(tbl: CN4Table, rho_probe: float, T_probe: float,
                            outfile=None, figsize=(10.0, 7.5)):
    """插值探针图: 固定质量密度 ``rho_probe``（可非网格点），沿温度轴插值
    ``P`` 与 ``zbar``，并标记参考点 ``(rho_probe, T_probe)``。

    Returns:
        ``(outfile, info_dict)``
    """
    import matplotlib.pyplot as plt
    apply_style()

    Ts = np.asarray(tbl.temperature, dtype=float)
    P_probe = interpolate_quantity(tbl, "P", rho_probe, Ts, field=_press(tbl))
    e_probe = interpolate_quantity(tbl, "E", rho_probe, Ts, field=_energy(tbl))
    zb_probe = interpolate_quantity(tbl, "zbar", rho_probe, Ts)

    P_at = interpolate_quantity(tbl, "P", rho_probe, T_probe, field=_press(tbl))
    zb_at = interpolate_quantity(tbl, "zbar", rho_probe, T_probe)
    e_at = interpolate_quantity(tbl, "E", rho_probe, T_probe, field=_energy(tbl))

    P_probe = pressure_mbar(P_probe)
    e_probe = energy_ergg(e_probe)
    P_at = pressure_mbar(P_at)
    e_at = energy_ergg(e_at)

    fig, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(Ts, P_probe, "o-", lw=config.PLOT_LINEWIDTH, ms=5, color="tab:red",
             label=r"Pressure $P$ (Mbar)")
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel(r"Temperature $T$ (eV)")
    ax1.set_ylabel(r"Pressure $P$ (Mbar)")
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax2 = ax1.twinx()
    ax2.plot(Ts, zb_probe, "s-", lw=config.PLOT_LINEWIDTH, ms=5,
             color="tab:blue", label=r"Average charge $\langle Z \rangle$")
    ax2.set_xscale("log")
    ax2.set_ylabel(r"Average charge $\langle Z \rangle$")
    ax2.tick_params(axis="y", labelcolor="tab:blue")
    ax1.plot([T_probe], [P_at], "D", ms=14, color="black",
             label=rf"Probe ({rho_probe:.3g} g/cm$^3$, {T_probe:.4g} eV)")
    ax1.set_title(rf"Interpolated EOS at fixed $\rho$ = {rho_probe:.4g} g/cm$^3$")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")
    _style_ax(ax1); _style_ax(ax2)
    fig.tight_layout()
    outfile = _save(fig, outfile, "interp_probe_rhoT")
    print(f"[cn4.eos] interp probe rho={rho_probe:.4g} g/cm3 -> {outfile}")

    return outfile, {
        "rho_probe": rho_probe, "T_probe": T_probe,
        "P_probe_Mbar": P_at, "e_probe_ergg": e_at, "zbar_probe": zb_at,
    }


# ================================================================
# 5. 声速场
# ================================================================

def sound_speed(tbl: CN4Table) -> np.ndarray:
    """等熵声速场 ``c_s``，形状 ``(ndens, ntemp)``，单位 **cm/s**。

    热力学推导::

        c_s^2 = (dP/drho)_s
              = (dP/drho)_T + (dP/dT)_rho * (dT/drho)_s

    由 Maxwell 关系与热力学第一定律::

        (dT/drho)_s = T / (rho^2 c_v) * (dP/dT)_rho

    数值实现: 密度轴对数差分（``dlnP/dln n``），温度轴线性差分；``c_v`` 取表值。

    ⚠️ 量纲: ``dP/drho|_T`` 为 ``(J/cm^3)/(g/cm^3) = J/g = 1e7 cm^2/s^2``，
    故最后乘 ``1e7`` 得 cm^2/s^2。调用方若需 um/ns 再乘 ``V_CMS_TO_UM_NS``。
    """
    P = _press(tbl)
    rho = _rho(tbl)
    logn = np.log10(np.asarray(tbl.density, dtype=float))
    dlnP_dlnn = np.gradient(np.log(P), logn, axis=0)
    dPdRho_T = (P / rho) * dlnP_dlnn                      # J/g
    dP_dT = np.gradient(P, np.asarray(tbl.temperature, dtype=float), axis=1)
    cv = np.maximum(_heatcp(tbl), 1e-30)                  # J/g/eV
    dTdrho_s = (np.asarray(tbl.temperature, dtype=float)[None, :]
                / (rho ** 2 * cv)) * dP_dT                # eV/(g/cm^3)
    cs2 = dPdRho_T + dP_dT * dTdrho_s                     # J/g = 1e7 cm^2/s^2
    return np.sqrt(np.maximum(cs2, 0.0) * 1e7)            # cm/s


# ================================================================
# 6. P-V 图（等温线 + 等熵线 + 冲击绝热线）
# ================================================================

def plot_pv_diagram(tbl: CN4Table, T_ref: float, s_field: np.ndarray,
                    rho_ref: float, hug_rho, hug_P,
                    outfile=None, figsize=(10.0, 7.5)):
    """在 P-V 图（``V = 1/rho`` 比体积）中绘制三条典型路径，**均从同一参考态
    ``(rho_ref, T_ref)`` 出发**。

    物理预期: 三条曲线在参考态交汇；冲击压缩后 Hugoniot 位于最硬侧（熵增），
    等熵线次之，等温线最软。全部使用散点（不连线，避免非单调路径的误导连线）。

    Returns:
        输出文件路径
    """
    import matplotlib.pyplot as plt
    from scipy.interpolate import RegularGridInterpolator
    apply_style()

    rho_axis = rho_from_nion(tbl, np.asarray(tbl.density, dtype=float))
    rho_dense = 10 ** np.linspace(np.log10(rho_axis[0]),
                                  np.log10(rho_axis[-1]), 200)
    T_dense = 10 ** np.linspace(np.log10(tbl.temperature[0]),
                                np.log10(tbl.temperature[-1]), 120)
    V_dense = 1.0 / rho_dense
    V0 = 1.0 / float(rho_ref)
    P0 = interpolate_quantity(tbl, "P", rho_ref, T_ref, field=_press(tbl))
    P_iso = interpolate_quantity(tbl, "P", rho_dense, T_ref, field=_press(tbl))

    # 等熵线: 参考态处 s 归零 -> s_rel = s_field - s(rho_ref, T_ref)。
    # s_field 含负值（相对归零场），不能走 log 插值，故在 (log n, log T) 上
    # 直接线性插值到精细网格，再双方向扫描 s_rel = 0。
    s_gi = RegularGridInterpolator(
        (np.log10(np.asarray(tbl.density, dtype=float)),
         np.log10(np.asarray(tbl.temperature, dtype=float))),
        s_field, bounds_error=False, fill_value=None)
    aw = tbl.avgatw
    if aw is None:
        raise CN4ParseError("原子量未知, 无法定位等熵线参考态")
    nion_ref = float(rho_ref) * NA / aw
    s_ref = float(s_gi([np.log10(nion_ref), np.log10(float(T_ref))])[0])
    Rg, Tg = np.meshgrid(rho_dense, T_dense, indexing="ij")
    nion_grid = Rg * NA / aw
    s_fine = s_gi(np.stack([np.log10(nion_grid.ravel()),
                            np.log10(Tg.ravel())], axis=1)).reshape(Rg.shape)
    s_rel = s_fine - s_ref

    rho_pts, T_pts = [], []
    n_rho, n_T = s_rel.shape
    for i in range(n_rho):
        row = s_rel[i]
        for j in range(n_T - 1):
            if row[j] * row[j + 1] < 0:
                fr = row[j] / (row[j] - row[j + 1])
                T_c = 10 ** (np.log10(T_dense[j]) +
                             fr * (np.log10(T_dense[j + 1]) - np.log10(T_dense[j])))
                rho_pts.append(rho_dense[i])
                T_pts.append(T_c)
    for j in range(n_T):
        col = s_rel[:, j]
        for i in range(n_rho - 1):
            if col[i] * col[i + 1] < 0:
                fr = col[i] / (col[i] - col[i + 1])
                rho_c = 10 ** (np.log10(rho_dense[i]) +
                               fr * (np.log10(rho_dense[i + 1]) -
                                     np.log10(rho_dense[i])))
                rho_pts.append(rho_c)
                T_pts.append(T_dense[j])
    if rho_pts:
        rho_ent = np.asarray(rho_pts, dtype=float)
        T_ent = np.asarray(T_pts, dtype=float)
        P_ent = interpolate_quantity(tbl, "P", rho_ent, T_ent, field=_press(tbl))
        V_ent = 1.0 / rho_ent
    else:
        V_ent = P_ent = None

    V_h = 1.0 / np.asarray(hug_rho, dtype=float)
    P_h = np.asarray(hug_P, dtype=float)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(V_dense, pressure_mbar(P_iso), ".", ms=4, color="tab:red",
            alpha=0.7, label=rf"Isotherm $T={T_ref:.3e}$ eV")
    if V_ent is not None and len(V_ent) > 1:
        ax.plot(V_ent, pressure_mbar(P_ent), "^", ms=5, mfc="tab:purple",
                mec="none", alpha=0.85,
                label=r"Isentrope from ref. ($\Delta s = 0$)")
    if len(V_h) > 1:
        ax.plot(V_h, pressure_mbar(P_h), "o", ms=6, mfc="tab:blue",
                mec="none", alpha=0.85, label=f"Hugoniot ({len(V_h)} pts)")
    ax.plot([V0], [pressure_mbar(P0)], "*", ms=22, color="black",
            label="Reference state")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel(r"Specific volume $V = 1/\rho$ (cm$^3$/g)")
    ax.set_ylabel(r"Pressure $P$ (Mbar)")
    ax.set_title("EOS paths in P-V diagram (from common state)")
    v_min = V_h.min() if len(V_h) else V0 * 0.1
    if V_ent is not None and len(V_ent):
        v_min = min(v_min, V_ent.min())
    ax.set_xlim(v_min * 0.8, V0 * 1.5)
    ax.set_ylim(pressure_mbar(min(P0, P_h.min())) * 0.5,
                pressure_mbar(max(P0, P_h.max())) * 2.0)
    ax.legend(loc="best")
    _style_ax(ax)
    fig.tight_layout()
    outfile = _save(fig, outfile, "pv_diagram")
    print(f"[cn4.eos] P-V diagram -> {outfile}")
    return outfile


if __name__ == "__main__":  # pragma: no cover
    import sys
    from .cn4_io import parse_cn4

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    d = parse_cn4(sys.argv[1])
    print(d.summary())
    trace_isotherm(d, T_idx=min(10, d.ntemp - 1))
    s = compute_entropy(d)
    trace_isentrope(d, s, s0_idx=(0, 0))
    rho_c, P_c, Us, Up, _ = trace_hugoniot(d, ref_idx=(0, 0))
    plot_usup_vs_pressure(Us, Up, P_c)
