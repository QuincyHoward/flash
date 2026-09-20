# -*- coding: utf-8 -*-
"""诊断: (1) 场景内 par 的完整 eos_/op_ 绑定; (2) 是否有 tar5; (3) SNBOneCH_ml_ml 与 cfg 表名。"""
import subprocess, io, re

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
SC = WS + r"\flash\scenarios\private\tracer\SNB\SNBOneCH_ml"
OUT = WS + r"\_par_diag.txt"

lines = []

# 1) 本地 flash_input/snbonech_ml.par
import os
for cand in ["flash_input/snbonech_ml.par", "flash_input/SNBOneCH_ml.par"]:
    p = os.path.join(SC, cand.replace("/", os.sep))
    if os.path.exists(p):
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        lines.append(f"===== LOCAL PAR: {cand} ({len(txt)} bytes) =====")
        for m in re.finditer(r'^\s*(eos_\w+TableFile|op_\w+FileName)\s*=\s*"([^"]*)"', txt, re.M):
            lines.append(f"  {m.group(1)} = {m.group(2)}")
        lines.append(f"  -- gr_hypreUseFloor: {re.findall(r'^s*gr_hypreUseFloor.*$', txt, re.M)}")
        lines.append(f"  -- tar5 present: {bool(re.search(r'tar5', txt))}")
        lines.append("")

# 2) 场景源里的 cfg 常量
for cand in ["SNBOneCH_ml.py"]:
    p = os.path.join(SC, cand)
    if os.path.exists(p):
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        lines.append(f"===== SCENARIO: {cand} =====")
        for m in re.finditer(r'^\s*"(ch_cn4|he_cn4)"\s*:\s*"([^"]*)"', txt, re.M):
            lines.append(f"  cfg {m.group(1)} = {m.group(2)}")
        for m in re.finditer(r'^\s*"(nprocs|tmax|t_initial|dtmax)"\s*:\s*([^,\n]+)', txt, re.M):
            lines.append(f"  cfg {m.group(1)} = {m.group(2).strip()}")
        lines.append("")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("WROTE", OUT)
