# -*- coding: utf-8 -*-
"""
eosop_pro 统一物理量单位约定
============================

默认 CGS; 指定单位: 时间 ns, 位置 um, 速度 um/ns, 温度 eV, 压力 Mbar。

cn4 原始表单位 -> 显示单位 (multiply):
    P (J/cm^3)       -> Mbar       : 1e-5    (1 J/cm^3 = 10^7 erg/cm^3
                                             = 10^7 dyne/cm^2 = 10 bar = 1e-5 Mbar)
    dP/dT (J/cm^3/eV)-> Mbar/eV    : 1e-5
    e (J/g)          -> erg/g      : 1e7     (1 J = 10^7 erg; CGS 默认)
    cv (J/g/eV)      -> erg/g/eV   : 1e7
    v (cm/s)         -> um/ns      : 1e-5    (1 cm = 10^4 um, 1 s = 10^9 ns)
    t (s)            -> ns         : 1e9
    x (cm)           -> um         : 1e4

不变 (已是 CGS / 指定单位):
    n_i (cm^-3), rho (g/cm^3), T (eV), opacity (cm^2/g), zbar (无量纲)
"""

# ── 转换因子 (cn4/内部单位 -> 显示单位) ──
P_JCM3_TO_MBAR   = 1.0e-5    # 压力: J/cm^3 -> Mbar
DPDT_TO_MBAR_EV  = 1.0e-5    # 压力温度导数: J/cm^3/eV -> Mbar/eV
E_JG_TO_ERG_G    = 1.0e7     # 比内能: J/g -> erg/g (CGS)
CV_TO_ERG_G_EV   = 1.0e7     # 比热: J/g/eV -> erg/g/eV (CGS)
V_CMS_TO_UM_NS   = 1.0e-5    # 速度: cm/s -> um/ns
T_S_TO_NS        = 1.0e9     # 时间: s -> ns
X_CM_TO_UM       = 1.0e4     # 长度: cm -> um


def pressure_mbar(P_jcm3):
    """压力 J/cm^3 -> Mbar"""
    return P_jcm3 * P_JCM3_TO_MBAR


def energy_ergg(e_jg):
    """比内能 J/g -> erg/g"""
    return e_jg * E_JG_TO_ERG_G


def heat_cgs(cv_jgev):
    """比热 J/g/eV -> erg/g/eV"""
    return cv_jgev * CV_TO_ERG_G_EV


def velocity_umns(v_cms):
    """速度 cm/s -> um/ns"""
    return v_cms * V_CMS_TO_UM_NS


def time_ns(t_s):
    """时间 s -> ns"""
    return t_s * T_S_TO_NS


def length_um(x_cm):
    """长度 cm -> um"""
    return x_cm * X_CM_TO_UM
