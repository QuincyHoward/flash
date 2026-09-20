# -*- coding: utf-8 -*-
"""_sacct2.py — 尝试多种计时查询方式"""
import sys
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")
import SNBOneCH_ml as M

ACCOUNT = "flash_ssh"
CMDS = [
    "sacct --version; echo RC=$?",
    "which sacct squeue scontrol 2>&1",
    "squeue -u scfa2696 -h -o '%i %j %T %M %N' 2>&1 | head -20",
    "scontrol show job 4864482 2>&1 | head -40",
    "sacct -j 4864482 -o JobID,State,Start,End,Elapsed -X 2>&1 | head -10",
    "ls -la --time-style=full-iso /publicfs01/fs1-e/home/scfa2696/QC/SNBOneCH_ml_deploy 2>&1 | head -20",
]
with M._HpcRemote(ACCOUNT) as remote:
    for c in CMDS:
        try:
            out, err, rc = remote.run(c, timeout=90)
        except Exception as e:
            print(f"### {c}\n  EXC {type(e).__name__}: {e}")
            continue
        print(f"### rc={rc}  {c}")
        print((out or "").strip()[:2500])
        if err and err.strip():
            print("  ERR:", err.strip()[:400])
        print("-" * 100)
