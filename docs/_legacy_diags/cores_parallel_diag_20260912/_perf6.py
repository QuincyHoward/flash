# -*- coding: utf-8 -*-
"""_perf6.py — 用日志内嵌时间戳 / SLURM 记录推算各腿真实 s/step"""
import re, json
from pathlib import Path
import numpy as np

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")

for nd in sorted(CP.iterdir()):
    if not nd.is_dir():
        continue
    logs = list(nd.glob("wsl_run_*.log"))
    if not logs:
        continue
    t = logs[0].read_text(encoding="utf-8", errors="replace")
    lines = t.splitlines()
    print("=" * 110)
    print(f"### {nd.name}  ({logs[0].name})")
    # 所有含时间戳/JobID/CANCELLED/elapsed 的行
    pats = [r"CANCELLED", r"JobID", r"Job \d+", r"Submitted", r"elapsed", r"RunTime",
            r"WALL_SECONDS", r"StartTime", r"EndTime", r"sbatch", r"^slurm", r"time limit",
            r"DRIVER_ABORT", r"step aborted", r"RUN_EXIT"]
    seen = 0
    for l in lines:
        for p in pats:
            if re.search(p, l, re.I):
                print("   |", l.strip()[:165]); seen += 1; break
        if seen > 25:
            print("   | ... (截断)"); break
    # 头部 12 行
    print("   -- head --")
    for l in lines[:12]:
        print("   >", l.strip()[:165])
