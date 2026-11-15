# -*- coding: utf-8 -*-
"""shock_track — §3.3 冲击波轨迹跟踪与物理筛选 (fronts_core.py:52-117,178-214,280-312).

流程:
  1. 逐帧候选区质心 (criteria.shok_candidates);
  2. 跨帧贪心最近邻连接成多条轨迹 (门限 TRACK_VMAX·dt, 断流 ≤ GAP_TOL 帧续接);
  3. 每条轨迹只保留向心发展段 (最近心逼近处截断, 回弹段剔除 — 双束对打下
     激波自两侧向中心发展, 与 x_a 同型);
  4. 物理筛选 (对向心段, §3.3):
       ① med(v_s) 与 med(v_a) 同号 (v_a 由 x_a 序列经 §3.4 差分链得到);
       ② |med(v_s)| > |med(v_a)|;
       ③ med(x_s − x_a)·med(v_a) > 0 (位于 x_a 运动方向前方);
       ④ 轨迹起点处 |x_s − x_a| ≤ X0_TOL (排除 Si/CH 材料界面静压触发伪迹);
     满足者中取点数最多、d0 最小者;
  5. 位置 SG(win=7, poly=3) 预平滑后线性插值回全时序网格 (§3.3 步骤 4)。
"""
from __future__ import annotations

import numpy as np
from scipy.signal import medfilt, savgol_filter

from .velocity import smooth_series, velocity_chain

TRACK_VMAX = 200.0      # µm/ns, 跟踪门限速度 (§3.3)
GAP_TOL = 5             # 断流容许帧数
MIN_PTS = 8             # 轨迹最少点数 (§3.3)
X0_TOL = 20.0           # µm, 初始位置距 x_a 容差 (§3.3 ④)
SG_WIN, SG_POLY = 7, 3  # 台阶轨迹预平滑


def build_trajectories(t_ns, cands_by_frame):
    """贪心最近邻连接 → list[dict(t=np.array, x=np.array, side='l'/'r')]."""
    active, done = [], []

    def close(traj, cand, t):
        gate = TRACK_VMAX * max(t - traj["t"][-1], 1e-6) * 1.5
        return abs(cand - traj["x"][-1]) <= gate

    for t, cands in zip(t_ns, cands_by_frame):
        used = set()
        for traj in active:
            if t - traj["t"][-1] > GAP_TOL * np.median(np.diff(t_ns)) * 1.5 + 1e-12:
                continue                                    # 断流过久, 冻结
            pool = [(abs(c - traj["x"][-1]), i) for i, c in enumerate(cands)
                    if i not in used and close(traj, c, t)
                    and np.sign(c) == np.sign(traj["x"][-1])]
            if pool:
                _, i = min(pool)
                traj["t"].append(t)
                traj["x"].append(cands[i])
                used.add(i)
        for i, c in enumerate(cands):
            if i not in used:
                active.append(dict(t=[t], x=[c],
                                   side="l" if c < 0 else "r"))
        # 冻结轨迹归档
        still = []
        for traj in active:
            if t - traj["t"][-1] > GAP_TOL * np.median(np.diff(t_ns)) * 1.5 + 1e-12:
                done.append(traj)
            else:
                still.append(traj)
        active = still
    done.extend(active)
    for traj in done:
        traj["t"] = np.array(traj["t"])
        traj["x"] = np.array(traj["x"])
    return done


def inward_leg(traj):
    """向心发展段: 截到最逼近中心处 (左: max x, 右: min x), 剔除回弹段."""
    x = traj["x"]
    j = int(np.argmax(x)) if traj["side"] == "l" else int(np.argmin(x))
    return traj["t"][: j + 1], x[: j + 1]


def _interp_valid(t_full, y_full):
    """取有限段构造线性插值器 (NaN 跳过); 返回 fn(t) 或 None."""
    m = np.isfinite(y_full)
    if m.sum() < 2:
        return None
    return lambda tq: np.interp(tq, t_full[m], y_full[m])


def select_shock(trajectories, side, t_full, xa_full, verbose=True):
    """物理筛选 → (选中轨迹的 t/x 向心段) 或 None.

    v_a: x_a 序列经 §3.4 差分链; v_s: 轨迹向心段经 §3.4 差分链。
    """
    results = []
    fn_xa = _interp_valid(t_full, xa_full)
    m = np.isfinite(xa_full)
    fn_va = None
    if m.sum() >= 9:
        va_win = velocity_chain(t_full[m], xa_full[m])
        fn_va = _interp_valid(t_full[m], va_win)
    if fn_xa is None or fn_va is None:
        if verbose:
            print(f"[shock:{side}] x_a 序列不足, 无法筛选")
        return None

    for traj in trajectories:
        if traj["side"] != side or traj["t"].size < MIN_PTS:
            continue
        t_leg, x_leg = inward_leg(traj)
        if t_leg.size < MIN_PTS:
            continue
        xa_leg = fn_xa(t_leg)
        d0 = abs(x_leg[0] - xa_leg[0]) if np.isfinite(xa_leg[0]) else np.inf
        v_s = velocity_chain(t_leg, x_leg)
        v_a = fn_va(t_leg)
        ms, ma = np.nanmedian(v_s), np.nanmedian(v_a)
        dx = np.nanmedian(x_leg - xa_leg)
        c1 = np.sign(ms) == np.sign(ma) and ma != 0
        c2 = abs(ms) > abs(ma)
        c3 = dx * ma > 0
        c4 = d0 <= X0_TOL
        ok = c1 and c2 and c3 and c4
        if verbose:
            print(f"[shock:{side}] traj t=[{t_leg[0]:.3f},{t_leg[-1]:.3f}] n={t_leg.size} "
                  f"d0={d0:.1f} v_s={ms:.1f} v_a={ma:.1f} dx_med={dx:.1f} "
                  f"①{c1} ②{c2} ③{c3} ④{c4} -> {'PASS' if ok else 'reject'}")
        if ok:
            results.append(dict(t=t_leg, x=x_leg, n=t_leg.size, d0=d0,
                                v_s=ms, v_a=ma))
    if not results:
        return None
    results.sort(key=lambda r: (-r["n"], r["d0"]))
    return results[0]


def final_series(sel, t_full):
    """选中轨迹 → 全网格 x_s 序列 (SG 预平滑 + 线性插值, 段外 NaN) + v_s (§3.4)."""
    x_sm = np.asarray(sel["x"], dtype=float)
    if x_sm.size >= 9:
        x_sm = savgol_filter(medfilt(x_sm, 9), SG_WIN, SG_POLY)
    xs_full = np.full(t_full.shape, np.nan)
    m = (t_full >= sel["t"][0]) & (t_full <= sel["t"][-1])
    xs_full[m] = np.interp(t_full[m], sel["t"], x_sm)
    fin = np.isfinite(xs_full)
    v_full = np.full(t_full.shape, np.nan)
    if fin.sum() >= 9:
        v_full[fin] = velocity_chain(t_full[fin], xs_full[fin])
    return xs_full, v_full
