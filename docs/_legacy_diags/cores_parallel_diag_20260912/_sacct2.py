# -*- coding: utf-8 -*-
"""_sacct2.py — 尝试多种计时查询方式"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # SNBOneCH_ml
sys.path.insert(0, str(Path(__file__).resolve().parents[8]))   # 仓库根
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

import SNBOneCH_ml as M

ACCOUNT = "flash_ssh"
CMDS = [
    "sacct --version; echo RC=$?",
    "which sacct squeue scontrol 2>&1",
    "squeue -u $(id -un) -h -o '%i %j %T %M %N' 2>&1 | head -20",
    "scontrol show job 4864482 2>&1 | head -40",
    "sacct -j 4864482 -o JobID,State,Start,End,Elapsed -X 2>&1 | head -10",
    f"ls -la --time-style=full-iso {_RH}/QC/SNBOneCH_ml_deploy 2>&1 | head -20",
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
