#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_interfaces — SandwichTxN 关键界面提取入口.

流程 (判据: flash/output_pro/FLASH物理量说明.md §3):
  1. 逐帧读取 chk (叶块过滤) → 派生量 (core.chk_io);
  2. 界面判据: x_c (§3.1) / x_a (§3.2 镜像) / Si 区域 dens·targ 半高 (core.criteria);
  3. shok 候选区 → 贪心轨迹 → 物理筛选 (v_s 与 v_a 同号且 |v_s|>|v_a|,
     位于 x_a 运动方向前方, 初始距 x_a ≤ 20 µm) → 只保留向心段 (§3.3, core.shock_track);
  4. x_a / x_s 速度统一 §3.4 差分链 (core.velocity);
  5. 时空场采样 (nele/nion/tele/pres/pele/Γ/Θ/shok/targ) + Si 区域平均
     (core.fields) → data/.

输出 (data/):
  interfaces.csv    逐帧界面位置 + v_a/v_s (µm, ns, µm/ns)
  spacetime.npz     统一网格时空场 (真实逐帧时间, pcolormesh 纪律)
  si_history.csv    Si 区域平均量 + size 随时间
  extraction_log.txt

用法: python extract_interfaces.py [--run 000002] [--quiet]
"""
from __future__ import annotations

import argparse
import csv
import sys
import time as _time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SCEN = HERE.parent.parent                      # .../SandwichTxN
DATA = HERE / "data"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from core import criteria, fields
from core.chk_io import list_chk, read_frame
from core.shock_track import (build_trajectories, final_series,
                              select_shock)

DEFAULT_RUN = "000002"
BG_XMIN_UM, BG_XMAX_UM, BG_NX = -100.0, 100.0, 801


def sanitize(a):
    """inf → NaN (Γ/Θ 在冷材/真空区可发散)."""
    a = np.asarray(a, dtype=float)
    a[~np.isfinite(a)] = np.nan
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default=DEFAULT_RUN, help="runs/ 下的运行编号")
    ap.add_argument("--quiet", action="store_true", help="抑制逐轨迹诊断输出")
    args = ap.parse_args()
    quiet = args.quiet

    run_dir = SCEN / "runs" / args.run / "sim_output"
    if not run_dir.is_dir():
        raise SystemExit(f"输出目录不存在: {run_dir}")
    frames = list_chk(run_dir)
    if not frames:
        raise SystemExit(f"无 chk 帧: {run_dir}")

    DATA.mkdir(exist_ok=True)
    log = [f"# InterfaceEvolution extraction  run={args.run}",
           f"# frames={len(frames)}  N_C={criteria.N_C:.4e} cm^-3",
           f"# ABL band=[{criteria.ABL_LO},{criteria.ABL_HI}] eV  "
           f"margin={criteria.ABL_XMARGIN} um"]
    print(f"[extract] run={args.run}  frames={len(frames)}  "
          f"N_C={criteria.N_C:.3e} cm^-3")

    xbg = np.linspace(BG_XMIN_UM, BG_XMAX_UM, BG_NX)
    t0 = _time.time()
    profiles, bg_fields, si_rows = [], [], []
    cands_by_frame, scell_t, scell_x = [], [], []

    # ── Pass 1: 逐帧判据 (x_c / x_a / Si / 候选区) + 时空场采样 ──
    for k, fp in enumerate(frames):
        fr = read_frame(fp)
        xc_l, xc_r = criteria.xc_pair(fr["x"], fr["nele"])
        xa_l, xa_r = criteria.xa_pair(fr["x"], fr["nele"], fr["tele_eV"],
                                      xc_l, xc_r)
        si_l, si_r, si_ref = criteria.si_edges(fr["x"], fr["dens_targ"],
                                               fr["targ"])
        cands = criteria.shok_candidates(fr["x"], fr["shok"])
        cands_by_frame.append(cands)
        # 原始 shok>0.5 格元 (核查图散点用)
        hit = np.flatnonzero(fr["shok"] > 0.5)
        if hit.size:
            scell_t.append(np.full(hit.size, fr["t_ns"]))
            scell_x.append(fr["x"][hit])
        stats = fields.si_region_stats(fr, si_l, si_r)
        profiles.append(dict(frame=k, t=fr["t_ns"],
                             xc=(xc_l, xc_r), xa=(xa_l, xa_r),
                             si=(si_l, si_r, si_ref), stats=stats))
        bg_fields.append(fields.sample_all(fr, xbg))
        si_rows.append(dict(frame=k, time_ns=fr["t_ns"], si_left_um=si_l,
                            si_right_um=si_r, size_um=si_r - si_l,
                            si_ref_gcc=si_ref, **stats))
        if k % 40 == 0 or k == len(frames) - 1:
            print(f"[extract] frame {k:4d}/{len(frames)-1}  t={fr['t_ns']:.4f} ns  "
                  f"xc=({xc_l:.2f},{xc_r:.2f})  xa=({xa_l:.2f},{xa_r:.2f})  "
                  f"si=({si_l:.3f},{si_r:.3f})")
    t_ns = np.array([p["t"] for p in profiles])
    log.append(f"pass1 (criteria + fields): {_time.time()-t0:.1f} s")

    # ── Pass 2: 冲击波轨迹跟踪 + 物理筛选 (§3.3) ──
    trajs = build_trajectories(t_ns, cands_by_frame)
    print(f"[extract] trajectories: {len(trajs)} "
          f"(l={sum(1 for t in trajs if t['side']=='l')}, "
          f"r={sum(1 for t in trajs if t['side']=='r')})")
    xa_l_full = np.array([p["xa"][0] for p in profiles])
    xa_r_full = np.array([p["xa"][1] for p in profiles])
    xs_out = {}
    for side, xa_full in (("l", xa_l_full), ("r", xa_r_full)):
        sel = select_shock(trajs, side, t_ns, xa_full, verbose=not quiet)
        if sel is None:
            xs_out[side] = (np.full(t_ns.shape, np.nan),
                            np.full(t_ns.shape, np.nan))
            log.append(f"shock {side}: no trajectory passed physical filter")
        else:
            xs_out[side] = final_series(sel, t_ns)
            log.append(f"shock {side}: n={sel['n']} t=[{sel['t'][0]:.3f},"
                       f"{sel['t'][-1]:.3f}] d0={sel['d0']:.2f} um "
                       f"v_s_med={sel['v_s']:.1f} v_a_med={sel['v_a']:.1f}")
    xs_l, vs_l = xs_out["l"]
    xs_r, vs_r = xs_out["r"]

    # ── x_a 速度 (§3.4 差分链, 有限段) ──
    def va_series(xa_full):
        v = np.full(t_ns.shape, np.nan)
        m = np.isfinite(xa_full)
        if m.sum() >= 9:
            from core.velocity import velocity_chain
            v[m] = velocity_chain(t_ns[m], xa_full[m])
        return v
    va_l, va_r = va_series(xa_l_full), va_series(xa_r_full)

    # ── 写 interfaces.csv ──
    cols = ["frame", "time_ns", "xc_left_um", "xc_right_um", "xa_left_um",
            "xa_right_um", "xs_left_um", "xs_right_um",
            "va_left_um_ns", "va_right_um_ns",
            "vs_left_um_ns", "vs_right_um_ns",
            "si_left_um", "si_right_um", "si_ref_gcc"]
    with open(DATA / "interfaces.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(cols)
        for i, p in enumerate(profiles):
            wr.writerow([p["frame"], f"{p['t']:.6g}",
                         *_fmt(p["xc"]), *_fmt(p["xa"]),
                         _f(xs_l[i]), _f(xs_r[i]),
                         _f(va_l[i]), _f(va_r[i]),
                         _f(vs_l[i]), _f(vs_r[i]),
                         *_fmt(p["si"])])

    # ── 写 spacetime.npz (真实逐帧时间, pcolormesh 纪律) ──
    stack = {k: sanitize(np.array([b[k] for b in bg_fields]))
             for k in bg_fields[0]}
    cand_t = [t for t, cb in zip(t_ns, cands_by_frame) for _ in cb]
    cand_x = [c for cb in cands_by_frame for c in cb]
    np.savez_compressed(
        DATA / "spacetime.npz",
        t_ns=t_ns, x_um=xbg, n_c=criteria.N_C, lambda_um=criteria.LAMBDA_UM,
        shok_cands_t=np.array(cand_t) if cand_t else np.empty(0),
        shok_cands_x=np.array(cand_x) if cand_x else np.empty(0),
        shok_cells_t=(np.concatenate(scell_t) if scell_t else np.empty(0)),
        shok_cells_x=(np.concatenate(scell_x) if scell_x else np.empty(0)),
        **stack,
    )

    # ── 写 si_history.csv ──
    si_cols = list(si_rows[0].keys())
    with open(DATA / "si_history.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(si_cols)
        for r in si_rows:
            wr.writerow([r[c] if not isinstance(r[c], float) else f"{r[c]:.6g}"
                         for c in si_cols])

    # ── 有效性统计 ──
    arrays = dict(xc_left_um=np.array([p["xc"][0] for p in profiles]),
                  xc_right_um=np.array([p["xc"][1] for p in profiles]),
                  xa_left_um=xa_l_full, xa_right_um=xa_r_full,
                  xs_left_um=xs_l, xs_right_um=xs_r,
                  si_left_um=np.array([p["si"][0] for p in profiles]),
                  si_right_um=np.array([p["si"][1] for p in profiles]))
    n_valid = {k: int(np.isfinite(v).sum()) for k, v in arrays.items()}
    log.append(f"runtime total: {_time.time()-t0:.1f} s")
    log.append("valid points: " + ", ".join(f"{k}={v}" for k, v in n_valid.items()))
    (DATA / "extraction_log.txt").write_text("\n".join(log) + "\n",
                                             encoding="utf-8")
    print(f"\n[extract] OK  data/  ({_time.time()-t0:.1f} s)")
    print("[extract] valid:", n_valid)


def _f(v):
    return f"{v:.6g}" if np.isfinite(v) else "nan"


def _fmt(tup):
    return [_f(v) for v in tup]


if __name__ == "__main__":
    main()
