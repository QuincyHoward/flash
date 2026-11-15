# -*- coding: utf-8 -*-
"""velocity — §3.4 统一速度差分链 (全库标准, phase_slope/ps_core.py:233-246).

x̃ = savgol(medfilt(x, 9), w, 3)
v = savgol(medfilt(∂x̃/∂t, 9), w, 3),  两端各截 3 点
w = min(51, max(7, n//4)), 取奇
"""
from __future__ import annotations

import numpy as np
from scipy.signal import medfilt, savgol_filter


def _win(n: int) -> int:
    w = min(51, max(7, n // 4))
    if w % 2 == 0:
        w -= 1
    return max(w, 5)


def smooth_series(x):
    """§3.4 前半链: medfilt(9) + savgol(w,3) — 用于轨迹位置平滑."""
    x = np.asarray(x, dtype=float)
    if x.size < 9:
        return x.copy()
    return savgol_filter(medfilt(x, 9), _win(x.size), 3)


def velocity_chain(t_ns, x_um):
    """§3.4 完整链 → v [µm/ns], 长度与输入一致, 两端 3 点为 NaN."""
    t_ns = np.asarray(t_ns, dtype=float)
    x_um = np.asarray(x_um, dtype=float)
    n = t_ns.size
    if n < 9:
        return np.full(n, np.nan)
    w = _win(n)
    xs = smooth_series(x_um)
    v = np.gradient(xs, t_ns)
    v = savgol_filter(medfilt(v, 9), w, 3)
    v[:3] = np.nan
    v[-3:] = np.nan
    return v
