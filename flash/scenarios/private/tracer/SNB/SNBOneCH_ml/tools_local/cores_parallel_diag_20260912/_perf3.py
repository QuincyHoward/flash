# -*- coding: utf-8 -*-
"""_perf3.py — 先用宽松正则定位步表行的精确格式"""
import re
from pathlib import Path

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")

for nd in sorted(CP.iterdir()):
    if not nd.is_dir():
        continue
    logs = list(nd.glob("wsl_run_*.log"))
    if not logs:
        continue
    lines = logs[0].read_text(encoding="utf-8", errors="replace").splitlines()
    print("=" * 100)
    print(nd.name, logs[0].name, "lines:", len(lines))
    # 找含有 "|" 且首个 token 是数字的行
    hits = [l for l in lines if "|" in l]
    print("  含 | 的行数:", len(hits))
    for l in hits[:3]:
        print("   RAW:", repr(l[:190]))
    # 找 1997 这类
    print("  --- 定位含 1.3313E-14 的行 ---")
    for l in lines:
        if "1.3313E-14" in l:
            print("   RAW:", repr(l[:190]))
            break
    # 尾部原始 repr
    print("  --- 尾部 6 行 RAW ---")
    for l in lines[-6:]:
        print("   RAW:", repr(l[:190]))
