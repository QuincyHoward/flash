# -*- coding: utf-8 -*-
"""fields — 时空场统一网格采样 + Si 区域平均量."""
from __future__ import annotations

import numpy as np

# 时空彩图字段 (key → (标签, 是否 log10 显示))
MAP_FIELDS = [
    ("dens_gcc",   r"Mass density  $\rho$  (g cm$^{-3}$)", True),
    ("nele",       r"Electron density  $n_e$  (cm$^{-3}$)", True),
    ("nion",       r"Ion density  $n_i$  (cm$^{-3}$)", True),
    ("tele_eV",    r"Electron temperature  $T_e$  (eV)", True),
    ("pres_Mbar",  r"Pressure  $p$  (Mbar)", True),
    ("pele_Mbar",  r"Electron pressure  $p_e$  (Mbar)", True),
    ("gamma",      r"Ion coupling  $\Gamma_i$", True),
    ("theta",      r"Degeneracy  $\Theta_e$", True),
]


def sample_field(x_um, values, xbg):
    """逐帧剖面 → 统一网格 (越界 NaN)."""
    return np.interp(xbg, x_um, values, left=np.nan, right=np.nan)


def sample_field_max(x_um, values, xbg):
    """max-pooling 采样: 稀薄薄层标志场 (shok) 用线性插值会整段错过,
    逐 bin 取覆盖格元的最大值。"""
    out = np.zeros(xbg.size)
    dx = xbg[1] - xbg[0]
    idx = np.round((x_um - xbg[0]) / dx).astype(int)
    m = (idx >= 0) & (idx < xbg.size)
    np.maximum.at(out, idx[m], values[m])
    return out


def sample_all(fr, xbg):
    """单帧全部 MAP_FIELDS + shok(max-pool) + targ + dens_targ → dict(1D)."""
    out = {}
    for key, _, _ in MAP_FIELDS:
        out[key] = sample_field(fr["x"], fr[key], xbg)
    out["shok"] = sample_field_max(fr["x"], fr["shok"], xbg)
    out["targ"] = sample_field(fr["x"], fr["targ"], xbg)
    out["dens_targ"] = sample_field(fr["x"], fr["dens_targ"], xbg)
    return out


# Si 区平均量额外字段 (FLYCHK 输入需要, 不进时空彩图)
SI_EXTRA_KEYS = ("tion_eV", "trad_eV", "dens_targ")


def si_region_stats(fr, si_l, si_r):
    """Si 区域 (x∈[si_l, si_r] 且 targ≥0.5) 内物理量算术平均 → dict.

    区域为空 (界面 NaN 或 targ 全 <0.5) → 全 NaN。
    """
    keys = [k for k, _, _ in MAP_FIELDS] + list(SI_EXTRA_KEYS)
    out = {f"{k}_mean": np.nan for k in keys}
    out["si_areal_mass_gcm2"] = np.nan        # size 范围内 ∫dens·targ dx [g/cm²]
    out["si_areal_mass_all_gcm2"] = np.nan    # 全域 targ≥0.5 积分 [g/cm²]
    if not (np.isfinite(si_l) and np.isfinite(si_r)):
        return out
    m = (fr["x"] >= si_l) & (fr["x"] <= si_r) & (fr["targ"] >= 0.5)
    dx = fr.get("dx_cm")
    if dx is not None:
        if m.any():
            out["si_areal_mass_gcm2"] = float(np.sum(fr["dens_targ"][m] * dx[m]))
        m_all = fr["targ"] >= 0.5
        if m_all.any():
            out["si_areal_mass_all_gcm2"] = float(
                np.sum(fr["dens_targ"][m_all] * dx[m_all]))
    if not m.any():
        return out
    if not m.any():
        return out
    for k in keys:
        v = fr[k][m]
        v = v[np.isfinite(v)]
        out[f"{k}_mean"] = float(v.mean()) if v.size else np.nan
    return out
