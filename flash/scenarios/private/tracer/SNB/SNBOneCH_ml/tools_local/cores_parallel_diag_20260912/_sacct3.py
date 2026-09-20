# -*- coding: utf-8 -*-
"""_sacct3.py — 获取三作业精确 Elapsed + 各腿结束时刻"""
import sys, re
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml")
import SNBOneCH_ml as M

ACCOUNT = "flash_ssh"
DEPLOY = "/publicfs01/fs1-e/home/scfa2696/QC/SNBOneCH_ml_deploy"
with M._HpcRemote(ACCOUNT) as remote:
    for jid in ("4864482", "4864483", "4864484"):
        out, _, _ = remote.run(
            f"sacct -j {jid} -o JobID,JobName%20,State,Start,End,Elapsed,ExitCode,NodeList -X -P 2>/dev/null",
            timeout=90)
        print(f"{jid}: {out.strip()}")
    print()
    # 各腿输出文件时间戳
    out, _, _ = remote.run(
        f"ls -la --time-style=full-iso {DEPLOY}/c*_out.txt {DEPLOY}/c*_err.txt 2>&1", timeout=90)
    print(out)
    print("---- 各腿 out.txt 内容 ----")
    for n in ("131", "192", "256"):
        o, _, _ = remote.run(f"cat {DEPLOY}/c{n}_486448{'2' if n=='131' else ('3' if n=='192' else '4')}_out.txt 2>&1", timeout=90)
        e, _, _ = remote.run(f"cat {DEPLOY}/c{n}_486448{'2' if n=='131' else ('3' if n=='192' else '4')}_err.txt 2>&1", timeout=90)
        print(f"\n### n{n} OUT:\n{(o or '').strip()[:1200]}")
        print(f"### n{n} ERR:\n{(e or '').strip()[:600]}")
