"""
gen_flychk_his.units — 单位换算与元素常量表
==========================================

FLASH 内部采用 **cgs + 温度以 K 表示**；FLYCHK history 输入采用
**温度以 eV 表示**，密度 g/cm^3 (rho) 或 cm^-3 (ne/ni)，长度 cm，时间 s。
本模块集中收敛所有换算系数，避免上游散落硬编码。

统一内部规范 (canonical units) — 见 `CANONICAL_UNITS`:
    temper/time/length/density/numdensity -> eV / s / cm / g/cm^3 / cm^-3

物理常量来源 (CODATA 2018):
    k_B = 8.617333262e-5 eV/K        -> 1 eV = 11604.518121550 K
    N_A = 6.02214076e23 1/mol
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

# ── 物理常量 ────────────────────────────────────────────────
KB_EV = 8.617333262e-5          # eV/K  (CODATA 2018)
K_PER_EV = 1.0 / KB_EV          # 11604.518121550082 K/eV
N_A = 6.02214076e23             # 1/mol (CODATA 2018, 精确值)

# 内部规范单位
CANONICAL_UNITS: Dict[str, str] = {
    "temper": "eV",       # te / ti / tr
    "time": "s",
    "length": "cm",
    "density": "g/cm^3",  # rho
    "numdensity": "cm^-3",  # ne / ni
    "intensity": "W/cm^2",
}

# ── 温度 ────────────────────────────────────────────────────
_TEMP_TO_EV = {
    "k": 1.0 / K_PER_EV,        # K  -> eV
    "kelvin": 1.0 / K_PER_EV,
    "ev": 1.0,
    "kev": 1.0e3,
}

# ── 长度 ────────────────────────────────────────────────────
_LEN_TO_CM = {
    "cm": 1.0,
    "mm": 0.1,
    "um": 1.0e-4,
    "micron": 1.0e-4,
    "nm": 1.0e-7,
    "m": 100.0,
}

# ── 时间 ────────────────────────────────────────────────────
_TIME_TO_S = {
    "s": 1.0,
    "sec": 1.0,
    "ms": 1.0e-3,
    "us": 1.0e-6,
    "ns": 1.0e-9,
    "ps": 1.0e-12,
    "fs": 1.0e-15,
}

# ── 密度 ────────────────────────────────────────────────────
_DENS_TO_CGS = {
    "g/cm^3": 1.0,
    "g/cc": 1.0,
    "gcm3": 1.0,
    "kg/m^3": 1.0e-3,
    "kg/m3": 1.0e-3,
    "mg/cm^3": 1.0e-3,
}

_NUMDENS_TO_CGS = {
    "cm^-3": 1.0,
    "cm-3": 1.0,
    "1/cm^3": 1.0,
    "m^-3": 1.0e-6,
    "m-3": 1.0e-6,
    "1/m^3": 1.0e-6,
}


def _normalize_key(unit: str) -> str:
    """单位字符串归一化: 去空白、转小写 (保留 e/E 指数写法)。"""
    return str(unit).strip().lower().replace(" ", "")


def _make_converter(table: Dict[str, float], kind: str):
    lookup = {_normalize_key(k): v for k, v in table.items()}

    def _convert(values, unit: str):
        key = _normalize_key(unit)
        if key not in lookup:
            raise ValueError(
                f"不支持{kind}单位 '{unit}'，可选: {sorted(lookup)}"
            )
        factor = lookup[key]
        if factor == 1.0:
            return np.asarray(values, dtype=np.float64)
        return np.asarray(values, dtype=np.float64) * factor

    return _convert


to_ev = _make_converter(_TEMP_TO_EV, "温度")
to_cm = _make_converter(_LEN_TO_CM, "长度")
to_s = _make_converter(_TIME_TO_S, "时间")
to_dens_cgs = _make_converter(_DENS_TO_CGS, "质量密度")
to_numdens_cgs = _make_converter(_NUMDENS_TO_CGS, "数密度")


def temp_to_ev(values, unit: str = "K"):
    """温度 -> eV。"""
    return to_ev(values, unit)


def ev_to_temp(values, unit: str = "K"):
    """eV -> 指定温度单位 (默认 K)。"""
    ev = np.asarray(values, dtype=np.float64)
    if _normalize_key(unit) in ("k", "kelvin"):
        return ev * K_PER_EV
    if _normalize_key(unit) == "ev":
        return ev
    if _normalize_key(unit) == "kev":
        return ev * 1.0e-3
    raise ValueError(f"不支持温度单位 '{unit}'")


def nele_from_rho(rho, zeff: float, aion: float):
    """由质量密度估算电子数密度: ne = rho * (Z/A) * N_A  [cm^-3]。

    Args:
        rho: 质量密度 (g/cm^3)
        zeff: 每离子平均电离电子数 (可含电离度修正的 Z_eff)
        aion: 离子平均原子量 (g/mol)
    """
    if aion <= 0:
        raise ValueError(f"aion 必须 > 0，当前 {aion}")
    return np.asarray(rho, dtype=np.float64) * (float(zeff) / float(aion)) * N_A


def nion_from_rho(rho, aion: float):
    """由质量密度估算离子数密度: ni = rho / A * N_A  [cm^-3]。"""
    return nele_from_rho(rho, 1.0, aion)


# ── 元素表 (Z / 原子量 / 常规谱窗) ──────────────────────────
# 原子量: IUPAC 2021 标准原子量。
# window: 本仓库既有产物中实际使用的谱窗 (eV)，仅为**约定记录/NOT 物理必需**，
#         来源为 flychk_runs 下产物命名 (如 grid_b0_Ti_Z22_out_[4655,4810].zip)
#         与 SPECTIME 谱窗配置；未验证者留 None。
#         参考 docs/FLYCHK_WINDOW_RETRY_WORKFLOW.md (窗口固化机制)。
__ATOMIC_WEIGHT = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81,
    "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.0855, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
    "Ti": 47.867, "V": 50.9415, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845,
    "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38,
    "Ag": 107.868, "Au": 196.967,
}

__Z = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5,
    "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15,
    "S": 16, "Cl": 17, "Ar": 18, "K": 19, "Ca": 20,
    "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
    "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30,
    "Ag": 47, "Au": 79,
}

# 谱窗记录: {元素: {"he": (lo, hi), "ly": (lo, hi)}}
__WINDOW = {
    "Al": {"he": (1580.0, 1740.0)},
    "Si": {"he": (1840.0, 2020.0)},
    "Mg": {"he": (1330.0, 1485.0)},
    "Ti": {"he": (4655.0, 4810.0), "ly": (4921.0, 5032.0)},
    "V": {"he": (5110.0, 5240.0)},
}


def element_z(element: str) -> int:
    """元素符号 -> 原子序数 (大小写不敏感)。"""
    key = _canonical_element(element)
    if key not in __Z:
        raise ValueError(
            f"未知元素 '{element}'，请在 units.ELEMENT_TABLE 中补充或显式传入 z"
        )
    return __Z[key]


def element_a(element: str) -> float:
    """元素符号 -> 标准原子量 (g/mol)。"""
    key = _canonical_element(element)
    if key not in __ATOMIC_WEIGHT:
        raise ValueError(f"未知元素 '{element}'，无法给出原子量")
    return __ATOMIC_WEIGHT[key]


def element_window(element: str, kind: str = "he") -> Optional[tuple]:
    """元素常规谱窗 (eV)。无记录时返回 None。"""
    return __WINDOW.get(_canonical_element(element), {}).get(kind)


def _canonical_element(element: str) -> str:
    s = str(element).strip()
    return s[:1].upper() + s[1:].lower() if s else s


def element_table() -> Dict[str, Dict[str, object]]:
    """返回元素表快照 (元素 -> {z, a, window})，供文档/CLI 展示。"""
    return {
        el: {"z": __Z[el], "a": __ATOMIC_WEIGHT[el], "window": __WINDOW.get(el)}
        for el in sorted(__Z, key=lambda k: __Z[k])
    }
