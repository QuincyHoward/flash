# -*- coding: utf-8 -*-
"""_re_dbg.py — 正则逐行调试"""
import re
from pathlib import Path

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")
p = CP / "n131" / "wsl_run_131.log"
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
l = lines[1]
print("repr:", repr(l))

pats = [
    r"^\s*(\d+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+\(",
    r"^\s*(\d+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+\(([^)]*)\)\s*\|\s*(.*)$",
]
for pat in pats:
    m = re.match(pat, l)
    print(pat[:50], "->", bool(m))
    if m:
        print("   groups:", m.groups())

# 最简：拆 token
m = re.match(r"^\s*(\d+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+\(([^)]*)\)\s*\|\s*(.*)$", l)
print("\ntokens after |:", m.group(5).split() if m else None)
print("coords:", m.group(4) if m else None)
