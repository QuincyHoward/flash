# -*- coding: utf-8 -*-
"""_track.py — SNBVTi 1.6 ns 长跑轻量进度探针（单次调用，不阻塞）。

★ 为什么不直接用 03_run_16ns_pipeline.py --stage wait
------------------------------------------------------
`stage_wait` 是**单次探针**（running 时 rc=2 立即返回），而真正的阻塞轮询在
`SNBVTi.py --poll-timeout` 内部。长跑 6~8 h 若做成单个阻塞进程，一旦宿主
网络抖动/任务被回收就整体丢失。按用户铁律改为 **宿主侧 sleep-and-poll**：
每轮调用本脚本取一次快照 → 宿主休眠 → 再调。

输出（stdout, 供宿主正则解析）:
  TRACK_STATE=RUNNING|DONE|GONE|NOJOB|ERROR
  TRACK_NJOBS=...            (★ 队列中作业总数; >1 时额外打印 TRACK_WARN + TRACK_JOB=)
  TRACK_JOBID=...
  TRACK_WALL=H:MM            (squeue TIME)
  TRACK_NODE=...
  TRACK_N=...                (最后一行 step 的 n)
  TRACK_T=...                (秒, 科学计数)
  TRACK_DT=...
  TRACK_CHK=...              (chk 文件数)
  TRACK_PROG=PCT             (t/tmax ×100)
  TRACK_SPSTEP=...           (sec/step, 由本次 wall/n 估)
  TRACK_ETA_H=...            (剩余小时, 饱和模型区间估计)
  TRACK_DU=...

用法:
  python _track.py --account flash_ssh --tmax 1.6e-9
  python _track.py --json                      # 结构化输出
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _longrun_lib as L  # noqa: E402


def _parse_wall(s: str) -> float:
    """squeue TIME → 秒。支持 D-HH:MM:SS / HH:MM:SS / MM:SS。"""
    if not s:
        return 0.0
    s = s.strip()
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        days = int(d)
    parts = [int(x) for x in s.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="flash_ssh")
    ap.add_argument("--tmax", type=float, default=1.6e-9)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tail", type=int, default=800,
                    help="用于估 dt 趋势的日志行数")
    args = ap.parse_args()

    snap: dict = {"state": "ERROR", "tmax": args.tmax}

    try:
        with L.R._HpcRemote(args.account) as rm:
            snb_home = L.abs_snb_home(rm)
            obj = f"{snb_home}/{L.M.OBJDIR}"
            # ── 一条命令取全部: squeue / chk 数 / du / 日志尾部 ──
            cmd = (
                "echo Q1; squeue -u $USER -h -o '%i|%j|%T|%M|%N' 2>/dev/null; "
                "echo Q2; "
                f"cd {obj} 2>/dev/null && ls {L.M.BASENM}hdf5_chk_* 2>/dev/null | wc -l; "
                "echo Q3; "
                f"cd {obj} 2>/dev/null && du -sh . 2>/dev/null | cut -f1; "
                "echo Q4; "
                f"cd {obj} 2>/dev/null && grep 'step: n=' {L.M.LOG_FILE} "
                f"2>/dev/null | tail -{args.tail}; "
                "echo Q5; "
                f"cd {obj} 2>/dev/null && tail -5 {L.M.LOG_FILE} 2>/dev/null"
            )
            out, err, rc = rm.run(cmd, timeout=180)
            out = out or ""

            def seg(a: str, b: str) -> str:
                i = out.find(a)
                j = out.find(b)
                if i < 0:
                    return ""
                i += len(a)
                return out[i:j if j > 0 else None].strip()

            sq = seg("Q1", "Q2")
            chk = seg("Q2", "Q3")
            du = seg("Q3", "Q4")
            steplog = seg("Q4", "Q5")
            tail = seg("Q5", "")

            snap["chk"] = int(chk) if chk.isdigit() else 0
            snap["du"] = du

            # ── squeue 解析 ──
            # ★★★ 必须处理「多作业并发」(2026-09-13 事故)
            #   事故: 两个 SNB1CH_r_nce 同时跑(父进程网络断→远端作业存活→重提),
            #        旧实现 `break` 只取第一行 ⇒ 完全掩盖第二个作业, 且二者
            #        共用 objdir 导致 chk 交错覆盖, 却始终只看到 1 个 JobID。
            #   ⇒ 现在收全部行, 暴露 njobs/jobs; 优先选与本次场景同名的 run 作业。
            jobs = []
            for l in sq.splitlines():
                if "|" in l:
                    f = [x.strip() for x in l.split("|")]
                    if len(f) >= 5 and f[0]:
                        jobs.append(f)
            snap["njobs"] = len(jobs)
            snap["jobs"] = jobs
            line = ""
            if jobs:
                _tag = "bscc" if "flash_ssh_2" in args.account else "nce"
                want = f"SNB1CH_r_{_tag}"
                pick = [j for j in jobs if j[1] == want] or jobs
                line = "|".join(pick[0])
                snap["jobids"] = [j[0] for j in jobs]
                snap["jobnames"] = [j[1] for j in jobs]
            if line:
                f = line.split("|")
                snap["jobid"] = f[0].strip()
                snap["jobname"] = f[1].strip() if len(f) > 1 else ""
                snap["qstate"] = f[2].strip() if len(f) > 2 else ""
                snap["wall"] = f[3].strip() if len(f) > 3 else ""
                snap["node"] = f[4].strip() if len(f) > 4 else ""
                snap["wall_s"] = _parse_wall(snap["wall"])

            # ── step 日志解析 ──
            ns, ts, dts = [], [], []
            for l in steplog.splitlines():
                m = re.search(
                    r"step: n=(\d+)\s+t=([\d.eE+-]+)\s+dt=([\d.eE+-]+)", l)
                if m:
                    ns.append(int(m.group(1)))
                    ts.append(float(m.group(2)))
                    dts.append(float(m.group(3)))
            if ns:
                snap["n"] = ns[-1]
                snap["t"] = ts[-1]
                snap["dt"] = dts[-1]
                snap["dt_min"] = min(dts)
                snap["dt_max"] = max(dts)
                snap["n_win"] = len(ns)
                snap["prog"] = 100.0 * ts[-1] / args.tmax

            # ── 状态判定 ──
            qs = snap.get("qstate", "")
            if qs in ("RUNNING", "PENDING", "COMPLETING", "CONFIGURING"):
                snap["state"] = "RUNNING"
            elif qs:
                snap["state"] = "RUNNING"
            else:
                # squeue 无输出: 作业已离开队列 → 判断是否跑到 tmax
                snap["state"] = "GONE"
                if ts and ts[-1] >= args.tmax * 0.999:
                    snap["state"] = "DONE"

            # ── ETA（饱和区间估计，与人类可读说明一致）──
            if snap["state"] == "RUNNING" and ns and snap.get("wall_s"):
                sps = snap["wall_s"] / snap["n"]
                snap["spstep"] = sps
                rem_t = args.tmax - ts[-1]
                # A: dt 冻结；C: 饱和 dt_inf ∈ {1.5e-14, 1.0e-14}；B: 幂律上界
                lo = rem_t / dts[-1] * sps
                hi = rem_t / 1.0e-14 * sps
                snap["eta_lo_h"] = lo / 3600
                snap["eta_hi_h"] = hi / 3600
                # 幂律（信息用）
                if len(ns) > 50 and ts[0] > 0:
                    p = (math.log(dts[-1] / dts[0])) / (math.log(ts[-1] / ts[0]))
                    snap["dt_p"] = p

            snap["tail"] = tail
            snap["_rc"] = rc
    except Exception as e:  # noqa: BLE001
        snap["state"] = "ERROR"
        snap["error"] = f"{type(e).__name__}: {e}"

    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    else:
        print(f"TRACK_STATE={snap['state']}")
        print(f"TRACK_NJOBS={snap.get('njobs', 0)}")
        if snap.get("njobs", 0) > 1:
            print("TRACK_WARN=★ 队列中有多个作业! 可能并发写同一 objdir → chk 会交错覆盖")
            for jid, jn, jst, jtm, jnd in snap.get("jobs", []):
                print(f"TRACK_JOB={jid}|{jn}|{jst}|{jtm}|{jnd}")
        for k in ("jobid", "qstate", "wall", "node", "chk", "du",
                  "n", "t", "dt", "prog", "spstep", "eta_lo_h", "eta_hi_h",
                  "dt_p", "error"):
            if k in snap and snap[k] is not None:
                v = snap[k]
                if isinstance(v, float):
                    print(f"TRACK_{k.upper()}={v:.6g}")
                else:
                    print(f"TRACK_{k.upper()}={v}")
        if snap.get("tail"):
            print("--- LOG_TAIL ---")
            print(snap["tail"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
