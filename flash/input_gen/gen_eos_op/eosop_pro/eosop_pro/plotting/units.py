# -*- coding: utf-8 -*-
"""cn4 原始单位 → 显示单位换算（每个因子附完整推导链与文档出处）。

单位纪律
========
本模块**不引入任何未在源码或文档中出现过的单位主张**。
每个换算因子下方都给出:
  1. **物理量名与来源文件/行号**
  2. **推导链**（等价关系逐步展开）
  3. **依据文档**

cn4 原始单位的一手来源
----------------------
``ionmix/ionmix/src/Ionmix/abjt_03.f``:

===================  ==============  =============================  ==========
块 / 量               原始单位         源码依据                        行号
===================  ==============  =============================  ==========
block 1 温度          eV              ``write the temperature        4683
                                      points (in ev)``
block 2 密度          cm^-3           ``write the number density     4685
                                      points (in cm^-3)``
block 5 离子压力      J/cm^3          赋值 ``densnn*tplsma*1.602E-19`` 4693
block 9 离子比内能     J/g             注释 ``(in Joules/gram)``        4705
block 11 离子比热     J/g/eV          注释 ``(in Joules/gram/eV)``     4710
block 15 能群边界     eV              注释 ``(in ev)``                 4728
block 16–18 不透明度  cm^2/g          注释 ``(cm^2/g)``                4732
===================  ==============  =============================  ==========

压力块的单位**未直接标注**，但由赋值表达式可**推定**（非猜测）::

    densnn(id) * tplsma(it) * 1.602E-19
    [cm^-3]    * [eV]       * [J/eV]     = J/cm^3

其中 ``1.602E-19`` 即元电荷 ``1.602176634e-19`` J/eV 的 Fortran 简写
（理想气体律 ``P = n k_B T`` 的 ``k_B`` 在 eV-K/J 单位制下的表达）。
块 7/8（压力温度导数）同为 ``J/cm^3/eV``（源码 line 4698 明写）。

配套文字规格: ``ionmix/ionmix/docs/IONMIX用户指南.md`` §5.4 表格
（该表逐块列出"维度 / 单位 / 说明"，与源码完全一致）。

显示单位约定
------------
本项目显示层统一: **压力 Mbar、比内能 erg/g、比热 erg/g/eV、
速度 um/ns、时间 ns、长度 um**；不变的: ``n_ion`` cm^-3、``rho`` g/cm^3、
``T`` eV、不透明度 cm^2/g、``zbar`` 无量纲。
"""

from __future__ import annotations

# ── 换算因子 ────────────────────────────────────────────────────

#: 压力: J/cm^3 -> Mbar
#:
#: 推导链::
#:
#:     1 J/cm^3 = 10^7 erg/cm^3
#:              = 10^7 dyne/cm^2          (1 erg/cm^3 = 1 dyne/cm^2)
#:              = 10^7 * 1e-6 bar         (1 bar = 10^6 dyne/cm^2)
#:              = 10 bar
#:              = 10 * 1e-6 Mbar          (1 Mbar = 10^6 bar)
#:              = 1e-5 Mbar
#:
#: 依据: ``abjt_03.f`` line 4693 赋值得 J/cm^3；
#:       ``docs/15_单位换算.md`` 亦声明该链。
P_JCM3_TO_MBAR = 1.0e-5

#: 压力温度导数: J/cm^3/eV -> Mbar/eV（与压力同因子，因分母 eV 不变）
#: 依据: ``abjt_03.f`` line 4698 注释 ``(in Joules/cm^3/eV)``
DPDT_TO_MBAR_EV = 1.0e-5

#: 比内能: J/g -> erg/g
#:
#: 推导链::
#:
#:     1 J = 10^7 erg
#:     => 1 J/g = 10^7 erg/g
#:
#: 依据: ``abjt_03.f`` line 4705/4707 注释 ``(in Joules/gram)``
E_JG_TO_ERG_G = 1.0e7

#: 比热: J/g/eV -> erg/g/eV（与比内能同因子，因分母 eV 不变）
#: 依据: ``abjt_03.f`` line 4710/4712 注释 ``(in Joules/gram/eV)``
CV_TO_ERG_G_EV = 1.0e7

#: 速度: cm/s -> um/ns
#:
#: 推导链::
#:
#:     1 cm = 10^4 um ;  1 s = 10^9 ns
#:     => 1 cm/s = 10^4 um / 10^9 ns = 1e-5 um/ns
#:
#: 依据: 单位制定义（cgs 长度 cm、时间 s；本项目显示层用 um / ns）
V_CMS_TO_UM_NS = 1.0e-5

#: 时间: s -> ns
#: 推导链: ``1 s = 10^9 ns``
T_S_TO_NS = 1.0e9

#: 长度: cm -> um
#: 推导链: ``1 cm = 10^4 um``
X_CM_TO_UM = 1.0e4

#: 阿伏伽德罗常数 (1/mol), CODATA 2018 定义值。
#: 用于 ``rho <-> n_ion`` 换算: ``rho = n_ion * <A> / N_A``。
#: 依据: ``docs/IONMIX用户指南.md`` §5.1 "Mass density" 行
#:       ``rho = n_tot * sum(f_k A_k) / N_A``
#:
#: ⚠️ 单一来源规则: 复用 ``config.N_A``（eosop_pro/config.py line 109），
#: 不得在此硬编码（测试 test_no_conversion_constant_hardcoded_outside_config）。
from ..config import N_A as NA


# ── 换算函数 ───────────────────────────────────────────────────
def pressure_mbar(p_jcm3):
    """压力 J/cm^3 -> Mbar。"""
    return p_jcm3 * P_JCM3_TO_MBAR


def energy_ergg(e_jg):
    """比内能 J/g -> erg/g。"""
    return e_jg * E_JG_TO_ERG_G


def heat_cgs(cv_jgev):
    """比热 J/g/eV -> erg/g/eV。"""
    return cv_jgev * CV_TO_ERG_G_EV


def velocity_umns(v_cms):
    """速度 cm/s -> um/ns。"""
    return v_cms * V_CMS_TO_UM_NS


def time_ns(t_s):
    """时间 s -> ns。"""
    return t_s * T_S_TO_NS


def length_um(x_cm):
    """长度 cm -> um。"""
    return x_cm * X_CM_TO_UM


def density_gcc_from_nion(n_ion, avg_atomwt):
    """离子数密度 -> 质量密度 ``rho = n_ion * <A> / N_A`` (g/cm^3)。

    依据: ``docs/IONMIX用户指南.md`` §5.1 输出量表 "Mass density" 行；
    以及 ``abjt_03.f`` 中 ``avgatw``（平均原子量）与 ``avgdro`` 的使用。
    """
    return n_ion * avg_atomwt / NA


def nion_from_rhogcc(rho, avg_atomwt):
    """质量密度 -> 离子数密度 ``n_ion = rho * N_A / <A>`` (cm^-3)。"""
    return rho * NA / avg_atomwt


#: 显示单位速查（供报告与表头使用）。值 = **本项目显示层单位**。
DISPLAY_UNITS: dict[str, str] = {
    "T": "eV",
    "n_ion": "cm-3",
    "rho": "g/cm3",
    "zbar": "- (dimensionless)",
    "P": "Mbar",
    "dP_dT": "Mbar/eV",
    "e": "erg/g",
    "cv": "erg/g/eV",
    "opacity": "cm2/g",
    "group_bound": "eV",
    "velocity": "um/ns",
    "time": "ns",
    "length": "um",
}

#: cn4 **原始（文件内）单位**速查 —— 与 ``DISPLAY_UNITS`` 严格区分。
RAW_UNITS: dict[str, str] = {
    "T": "eV",
    "n_ion": "cm-3",
    "zbar": "- (dimensionless)",
    "dzdt": "1/eV",
    "p_ion": "J/cm3",
    "p_ele": "J/cm3",
    "dpion_dt": "J/cm3/eV",
    "dpele_dt": "J/cm3/eV",
    "e_ion": "J/g",
    "e_ele": "J/g",
    "cv_ion": "J/g/eV",
    "cv_ele": "J/g/eV",
    "deion_dn": "J*cm3/g",
    "deele_dn": "J*cm3/g",
    "group_bound": "eV",
    "opac_rosseland": "cm2/g",
    "opac_planck_abs": "cm2/g",
    "opac_planck_ems": "cm2/g",
}

#: 每个原始单位的**依据**（源码行号或文档章节）—— 供报告直接引用。
RAW_UNIT_EVIDENCE: dict[str, str] = {
    "T": "abjt_03.f L4683 `write the temperature points (in ev)`",
    "n_ion": "abjt_03.f L4685 `write the number density points (in cm^-3)`",
    "zbar": "abjt_03.f L4687 `write out the zbar at each temperature/density ponit (nele/nion)` -> 无量纲比值",
    "dzdt": "abjt_03.f L4691（d(zbar)/dT，T 以 eV 计）-> 1/eV",
    "p_ion": "abjt_03.f L4693 赋值 `densnn*tplsma*1.602E-19` = cm^-3*eV*(J/eV) = J/cm3",
    "p_ele": "abjt_03.f L4696 赋值 `densne*tplsma*1.602E-19` = cm^-3*eV*(J/eV) = J/cm3",
    "dpion_dt": "abjt_03.f L4698 注释 `(in Joules/cm^3/eV)`",
    "dpele_dt": "abjt_03.f L4702（同 dpion_dt 单位）",
    "e_ion": "abjt_03.f L4705 注释 `(in Joules/gram)`",
    "e_ele": "abjt_03.f L4707 注释 `(in Joules/gram)`",
    "cv_ion": "abjt_03.f L4710 注释 `(in Joules/gram/eV)`",
    "cv_ele": "abjt_03.f L4712 注释 `(in Joules/gram/eV)`",
    "deion_dn": "abjt_03.f L4715 注释 `(not sure)` + L4716-4719 换算式（源码自身存疑，见下）",
    "deele_dn": "abjt_03.f L4720 注释 `(not sure)` + L4721-4725 换算式（源码自身存疑，见下）",
    "group_bound": "abjt_03.f L4728 注释 `(in ev)`",
    "opac_rosseland": "abjt_03.f L4732 注释 `(cm^2/g)` + L4516 输入变量说明 `opgp - Planck group opacities (cm**2/g)`",
    "opac_planck_abs": "abjt_03.f L4736（同 Rosseland，cm^2/g）",
    "opac_planck_ems": "abjt_03.f L4739（同 Rosseland，cm^2/g）",
}

#: ⚠️ 源码自身标注 "not sure" 的量 —— **诚实标注，不代为断言**。
UNCERTAIN_UNITS: dict[str, str] = {
    "deion_dn": (
        "block 13 d(eion)/d(nion): 源码 L4715 注释写 `(not sure)`，"
        "且 L4716-4719 经过 `condd = -6.242e18*avgatw/avgdro` 的换算，"
        "最终写出量为 `dedden_ion*condd*densnn/tplsma**2`。"
        "该组合的物理量纲**无法从源码独立确认** —— 标注 unknown。"
    ),
    "deele_dn": (
        "block 14 d(eele)/d(nele): 同 block 13，源码 L4720 注释 `(not sure)`。"
        "标注 unknown。"
    ),
}
