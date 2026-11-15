# -*- coding: utf-8 -*-
"""criteria — 界面判据 (FLASH物理量说明.md §3.1/§3.2 + dens·targ 半高 + §3.3 候选切分)."""
from __future__ import annotations

import numpy as np

LAMBDA_UM = 0.351
N_C = 1.1155e21 / LAMBDA_UM**2      # ≈ 9.05e21 cm⁻³
ABL_LO, ABL_HI = 60.0, 600.0        # eV, 烧蚀前沿温区带
ABL_XMARGIN = 0.5                   # µm, 距 x_c 余量


def first_upcross(x_um, y, level):
    """升序数组首个 y≤level → y>level 向上穿越, 线性插值; 无则 NaN."""
    sgn = y > level
    idx = np.flatnonzero(~sgn[:-1] & sgn[1:])
    if idx.size == 0:
        return np.nan
    j = idx[0]
    a, b = y[j], y[j + 1]
    if b == a:
        return x_um[j]
    return x_um[j] + (level - a) / (b - a) * (x_um[j + 1] - x_um[j])


def xc_pair(x_um, nele):
    """临界密度面 x_c (§3.1): 左=升序首个上穿, 右=降序数组首个上穿 (真实坐标)."""
    xc_l = first_upcross(x_um, nele, N_C)
    xc_r = first_upcross(x_um[::-1].copy(), nele[::-1].copy(), N_C)
    return xc_l, xc_r


def xa_pair(x_um, nele, tele_eV, xc_l, xc_r):
    """烧蚀前沿 x_a (§3.2 双束镜像): 过密 + 温区带 + x_c 内侧 margin.

    左半域 argmin(dT/dx), 右半域 argmax(dT/dx); 有效格元 <3 → NaN.
    """
    gT = np.gradient(tele_eV, x_um)
    base = (nele > N_C) & (tele_eV > ABL_LO) & (tele_eV < ABL_HI)
    out = []
    for side in ("l", "r"):
        if side == "l":
            m = base & (x_um < 0.0)
            if np.isfinite(xc_l):
                m &= x_um > xc_l + ABL_XMARGIN
            sel = np.flatnonzero(m)
            j = sel[np.argmin(gT[sel])] if sel.size >= 3 else None
        else:
            m = base & (x_um > 0.0)
            if np.isfinite(xc_r):
                m &= x_um < xc_r - ABL_XMARGIN
            sel = np.flatnonzero(m)
            j = sel[np.argmax(gT[sel])] if sel.size >= 3 else None
        out.append(x_um[j] if j is not None else np.nan)
    return out[0], out[1]


def si_edges(x_um, dens_targ, targ):
    """Si 区域 = dens·targ 半高区段外缘 (线性插值).

    半高基准 = 0.5 × median(dens·targ | targ≥0.5) — 体区中位数排除激波压缩壳
    (targ≈1 但 ρ 数倍) 对全局 max 的抬高; 与 analyze_output.py fig7 的
    targ≥0.5 约定兼容。返回 (左缘, 右缘, 参考水平).
    """
    bulk = targ >= 0.5
    ref = float(np.median(dens_targ[bulk])) if bulk.any() else float(dens_targ.max())
    if ref <= 0:
        return np.nan, np.nan, ref
    half = 0.5 * ref
    above = dens_targ >= half
    if not above.any():
        return np.nan, np.nan, ref
    i0 = int(np.flatnonzero(above)[0])
    i1 = int(np.flatnonzero(above)[-1])
    if i0 == 0:
        xl = x_um[0]
    else:
        a, b = dens_targ[i0 - 1], dens_targ[i0]
        xl = x_um[i0 - 1] + (half - a) / (b - a) * (x_um[i0] - x_um[i0 - 1]) if b != a else x_um[i0]
    if i1 == len(x_um) - 1:
        xr = x_um[-1]
    else:
        a, b = dens_targ[i1], dens_targ[i1 + 1]
        xr = x_um[i1] + (half - a) / (b - a) * (x_um[i1 + 1] - x_um[i1]) if b != a else x_um[i1]
    return xl, xr, ref


def shok_candidates(x_um, shok, gap=2):
    """shok>0.5 连续区 (索引间隔>gap 切分) → shok 加权质心列表 (§3.3 步骤 1)."""
    idx = np.flatnonzero(shok > 0.5)
    if idx.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(idx) > gap)
    starts = np.concatenate(([0], cuts + 1))
    ends = np.concatenate((cuts + 1, [idx.size]))
    cands = []
    for s, e in zip(starts, ends):
        seg = idx[s:e]
        wgt = shok[seg]
        cands.append(float(np.sum(x_um[seg] * wgt) / np.sum(wgt)))
    return cands
