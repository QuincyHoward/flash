# -*- coding: utf-8 -*-
"""_sacct.py — 查询三个 JobID 的 Start/End/Elapsed 以计算真实 s/step"""
import sys, json
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB")
import SNBOneCH_ml as M

ACCOUNT = "flash_ssh"
for jid in ("4864482", "4864483", "4864484"):
    with M._HpcRemote(ACCOUNT) as remote:
        cmd = (f"sacct -j {jid} --format=JobID,JobName%28,State,Start,End,Elapsed,ExitCode,NodeList "
               f"--units=S -P 2>/dev/null")
        out, err, rc = remote.run(cmd, timeout=120)
        print("=" * 100)
        print(f"JobID {jid}  rc={rc}")
        print(out or "(empty)")
        if err:
            print("ERR:", err[:300])
