#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""声速模块 —— 纯计算层：γ_e/γ_i 反演拟合 + 严格等熵声速（无近似）。

本模块是 ``eosop_pro/test/sound_velocity/`` 功能验证的三文件之一
（计算 / 绘图 / 驱动），只做数值计算，不涉及绘图。

物理设计（用户 2026-09-17 第十六轮修订版）
------------------------------------------
1. **γ_e / γ_i 反演**（单点恒等式，不需要差分）：理想气体关系
   ``P = (γ - 1) ρ e`` 的反解 ``γ = 1 + P/(ρ e)`` 逐网格点计算::

       γ_i = 1 + p_ion / (ρ e_ion)      γ_e = 1 + p_ele / (ρ e_ele)

   完全电离单原子区 γ -> 5/3；部分电离 / 简并 / 库仑修正区偏离 ——
   γ 场本身就是 EOS 非理想性诊断图。**不用于声速**（第十六轮修订：
   声速不再走理想气体近似）。

2. **严格等熵声速**（声速唯一算法，纯热力学恒等式，无任何近似）::

       c_s^2 = (∂P/∂ρ)_s = (∂P/∂ρ)_T + T/(ρ^2 c_v) · (∂P/∂T)_ρ^2

   推导：第一定律 ``T ds = de + P d(1/ρ)`` + Maxwell 型关系
   ``(∂e/∂ρ)_T = [P - T (∂P/∂T)_ρ]/ρ^2``，令 ``ds = 0`` 得等熵斜率
   ``(dT/dρ)_s = T/(ρ^2 c_v) (∂P/∂T)_ρ``，代入链式法则即上式。
   对任意 EOS（电离 / 简并 / 库仑修正）成立；隐含 T_e = T_i 平衡近似
   （cn4 表为单温轴，总 P / 总 c_v 自洽）。

   输入全部来自 cn4 表的 ρ-T 网格场：P = p_ion + p_ele（J/cm^3）、
   c_v = cv_ion + cv_ele（J/g/eV）、ρ = n_ion·<A>/N_A（g/cc 质量密度）。

3. **c_s^2 两项分解**（严格量的诊断拆分）：等温压缩项 (∂P/∂ρ)_T 与
   热熵项之比。单原子理想气体区热熵项占比 = (γ-1)/γ = 2/5 = 0.4。

单位链
------
 ``(J/cm^3) / (g/cm^3) = J/g = 1e7 cm^2/s^2``；声速最后乘 1e7 得 cm/s
（再由调用方用 ``units.velocity_umns`` 转 um/ns）。γ 无量纲。

数值约定
--------
所有场形状 ``(ndens, ntemp)``（行 = 密度，列 = 温度），与
``cn4_paths`` 一致；e ≤ 0 / c_v ≤ 0 / 非正 c_s^2 一律 NaN 掩膜，
不静默填 0。
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

# ── 包导入（直接执行本文件时把 gen_eos_op/eosop_pro 塞进 sys.path）──
_HERE = Path(__file__).resolve()
_PKG_PARENT = _HERE.parents[3]          # .../gen_eos_op/eosop_pro（其下有 eosop_pro/ 包）
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from eosop_pro.parsers.cn4_io import CN4Table        # noqa: E402
from eosop_pro.plotting.cn4_fit import compute_r2    # noqa: E402
from eosop_pro.plotting import cn4_paths             # noqa: E402
from eosop_pro.plotting.units import (               # noqa: E402
    density_gcc_from_nion,
    velocity_umns,
)

__all__ = [
    "gamma_species", "gamma_ion", "gamma_ele",
    "fit_gamma_powerlaw",
    "sound_speed_isentropic", "cs_terms", "thermal_fraction",
    "cs_isentropic_umns", "sound_gamma_eff",
    "validate_against_cn4_paths",
]

#: c_v 的数值下限（防止 0 除；与 cn4_paths._heatcp 的 clamp 一致）
_CV_FLOOR = 1e-30


# ── 内部辅助 ─────────────────────────────────────────────────
def _arr2d(tbl: CN4Table, name: str) -> np.ndarray:
    """二维场 -> ``(ndens, ntemp)`` 数组（行 = 密度，列 = 温度）。"""
    flat = np.asarray(tbl.field(name), dtype=float)
    return flat.reshape(tbl.ndens, tbl.ntemp)


def _rho_gcc(tbl: CN4Table) -> np.ndarray:
    """质量密度 ``(ndens, ntemp)`` g/cm^3 = n_ion·<A>/N_A（沿温度广播）。"""
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


# ── 2. γ(T) 幂律拟合 ─────────────────────────────────────────
def fit_gamma_powerlaw(T_row, gamma_row) -> tuple[float, float, float]:
    """固定密度行的 ``γ(T)`` log-log 幂律拟合 ``γ = a·T^b``。

    Returns:
        ``(a, b, r2)``；R^2 在原域计算（与 ``cn4_fit.fit_power_law``
        惯例一致）。有效点 < 3 或拟合退化时返回 ``(nan, nan, nan)``。
    """
    T = np.asarray(T_row, dtype=float)
    g = np.asarray(gamma_row, dtype=float)
    m = np.isfinite(T) & np.isfinite(g) & (T > 0) & (g > 0)
    if m.sum() < 3:
        return (float("nan"),) * 3
    b, log10a = np.polyfit(np.log10(T[m]), np.log10(g[m]), 1)
    a = 10.0 ** log10a
    r2 = compute_r2(g[m], a * T[m] ** b)
    return (float(a), float(b), float(r2))


# ── 3. 严格等熵声速（唯一声速算法，无近似）────────────────────
def sound_speed_isentropic(tbl: CN4Table) -> np.ndarray:
    """严格等熵声速场 ``(ndens, ntemp)``，单位 **cm/s**。

    纯热力学恒等式（推导见模块 docstring），无理想气体近似::

        c_s^2 = (∂P/∂ρ)_T + T/(ρ^2 c_v) · (∂P/∂T)_ρ^2

    数值实现：密度轴 log 差分（``dlnP/dln n``）、温度轴线性差分，
    与 ``cn4_paths.sound_speed`` 同构（双实现互检，见
    :func:`validate_against_cn4_paths`）。
    """
    P = _arr2d(tbl, "p_ion") + _arr2d(tbl, "p_ele")       # J/cm^3
    rho = _rho_gcc(tbl)                                    # g/cm^3
    T = np.asarray(tbl.temperature, dtype=float)           # (ntemp,) eV
    # ⚠️ 自然对数坐标（ln n）：np.gradient(np.log(P), lnn) 才是
    # dlnP/dlnn。若坐标用 log10(n) 会混入 ln(10)≈2.303 因子
    # （2026-09-15 诊断确认；cn4_paths.sound_speed 同模式已于
    # 2026-09-17 主线修复，回归守卫 test_sound_speed_ideal_gas_gamma_anchor）
    lnn = np.log(np.asarray(tbl.density, dtype=float))

    dlnP_dlnn = np.gradient(np.log(P), lnn, axis=0)
    dPdRho_T = (P / rho) * dlnP_dlnn                       # J/g
    dP_dT = np.gradient(P, T, axis=1)                      # J/cm^3/eV
    cv = np.maximum(_arr2d(tbl, "cv_ion") + _arr2d(tbl, "cv_ele"),
                    _CV_FLOOR)                             # J/g/eV
    dTdrho_s = (T[None, :] / (rho ** 2 * cv)) * dP_dT      # eV/(g/cm^3)

    cs2 = dPdRho_T + dP_dT * dTdrho_s                      # J/g = 1e7 cm^2/s^2
    return np.sqrt(np.maximum(cs2, 0.0) * 1e7)             # cm/s


def cs_terms(tbl: CN4Table) -> tuple[np.ndarray, np.ndarray]:
    """c_s^2 的两项分解（均为严格量，单位 J/g = 1e7 cm^2/s^2）。

    Returns:
        ``(cs2_thermal, cs2_isothermal)``：

        - ``cs2_isothermal = (∂P/∂ρ)_T``（等温压缩项）
        - ``cs2_thermal = T/(ρ^2 c_v) (∂P/∂T)_ρ^2``（热熵项）

        单原子理想气体区热熵项占比 = (γ-1)/γ = 0.4。
    """
    P = _arr2d(tbl, "p_ion") + _arr2d(tbl, "p_ele")
    rho = _rho_gcc(tbl)
    T = np.asarray(tbl.temperature, dtype=float)
    lnn = np.log(np.asarray(tbl.density, dtype=float))  # 自然对数坐标

    dlnP_dlnn = np.gradient(np.log(P), lnn, axis=0)
    cs2_iso = (P / rho) * dlnP_dlnn
    dP_dT = np.gradient(P, T, axis=1)
    cv = np.maximum(_arr2d(tbl, "cv_ion") + _arr2d(tbl, "cv_ele"), _CV_FLOOR)
    dTdrho_s = (T[None, :] / (rho ** 2 * cv)) * dP_dT
    cs2_th = dP_dT * dTdrho_s
    return cs2_th, cs2_iso


def thermal_fraction(cs2_thermal: np.ndarray,
                     cs2_isothermal: np.ndarray) -> np.ndarray:
    """热熵项占 c_s^2 比值场；分母 ≤ 0 或非有限处 NaN。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        frac = cs2_thermal / (cs2_thermal + cs2_isothermal)
    valid = (np.isfinite(cs2_thermal) & np.isfinite(cs2_isothermal)
             & ((cs2_thermal + cs2_isothermal) > 0))
    return np.where(valid, frac, np.nan)


def cs_isentropic_umns(tbl: CN4Table) -> np.ndarray:
    """严格等熵声速，单位 **um/ns**（绘图/报告用）。"""
    return velocity_umns(sound_speed_isentropic(tbl))


def sound_gamma_eff(tbl: CN4Table) -> np.ndarray:
    """等熵指数 ``γ_sound = c_s^2·ρ/P``（严格声速的派生量，无近似）。

    与单点恒等式 ``γ_energy = 1 + P/(ρ e)`` 的对比量化电离/束缚
    效应强度：理想气体极限下两者相等（=5/3）；电离能抬高 c_v / e
    时 γ_sound 与 γ_energy 均下降但机理不同。单原子理想气体区
    热熵项占比 (γ_sound-1)/γ_sound = 0.4 仅在此极限成立。
    """
    cs2 = sound_speed_isentropic(tbl) ** 2          # cm^2/s^2
    P = _arr2d(tbl, "p_ion") + _arr2d(tbl, "p_ele") # J/cm^3
    rho = _rho_gcc(tbl)                             # g/cm^3
    # c_s^2 [cm^2/s^2] -> J/g（×1e-7）后除以 P/ρ [J/g]
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (cs2 * 1e-7) / (P / rho)
    valid = np.isfinite(cs2) & np.isfinite(P) & (P > 0)
    return np.where(valid, g, np.nan)


# ── 4. 双实现对照验证 ────────────────────────────────────────
def validate_against_cn4_paths(tbl: CN4Table) -> float:
    """本模块实现 vs ``cn4_paths.sound_speed`` 逐点相对偏差（有限点）。

    Returns:
        有限点上 ``max |a - b| / |b|``。两实现同公式同差分，
        预期为 0（bit 一致）；> 1e-9 说明任一实现被改动。
    """
    a = sound_speed_isentropic(tbl)
    b = np.asarray(cn4_paths.sound_speed(tbl), dtype=float)
    m = np.isfinite(a) & np.isfinite(b) & (b != 0)
    if not m.any():
        return float("inf")
    return float(np.max(np.abs(a[m] - b[m]) / np.abs(b[m])))
