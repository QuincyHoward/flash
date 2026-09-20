# -*- coding: utf-8 -*-
"""_timing.py — 读取 _t_start/_t_end 获得纯积分墙钟"""
import sys
from datetime import datetime
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")
import SNBOneCH_ml as M

ACCOUNT = "flash_ssh"
DEPLOY = "/publicfs01/fs1-e/home/scfa2696/QC/SNBOneCH_ml_deploy"
NSTEP = {"131": 1997, "192": 1200, "256": 980}

with M._HpcRemote(ACCOUNT) as remote:
    for n in ("131", "192", "256"):
        d = f"{DEPLOY}/_unit_{n}"
        out, _, _ = remote.run(
            f"for f in _t_start _t_end; do echo -n \"$f=\"; cat {d}/$f 2>/dev/null || echo NA; done; "
            f"echo _t_steps=$(ls {d}/snbonechug_hdf5_chk_* 2>/dev/null | wc -l); "
            f"stat -c '%n %y' {d}/wsl_run_{n}.log 2>/dev/null", timeout=90)
        print(f"--- n{n} ---\n{(out or '').strip()}")
        try:
            lines = dict(l.split("=", 1) for l in (out or "").strip().splitlines() if "=" in l)
            t0 = float(lines["_t_start"]); t1 = float(lines["_t_end"])
            W = t1 - t0
            N = NSTEP[n]
            print(f"    WALL(run only) = {W:.1f} s   steps={N}   => {W/N:.4f} s/step")
            # 纯 CFL 段: step 100..N
            Wc = W * (N - 100) / N
            print(f"    若扣除启动 100 步: {Wc/(N-100):.4f} s/step")
        except Exception as e:
            print(f"    (解析失败: {type(e).__name__}: {e})")
