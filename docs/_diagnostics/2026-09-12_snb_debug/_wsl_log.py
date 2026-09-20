# -*- coding: utf-8 -*-
"""拉取 WSL objdir 的 flash4 运行日志与 objdir 内 .cn4 链接状态。"""
import subprocess, sys, io

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_log.txt"

OBJ = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

cmds = [
    ("ERR", f"grep -nE 'ERROR|ABORT|FATAL|not found|Error' {OBJ}/wsl_run_snbonech.log | head -30"),
    ("TAIL", f"tail -40 {OBJ}/wsl_run_snbonech.log"),
    ("HEAD", f"head -60 {OBJ}/wsl_run_snbonech.log"),
    ("CN4", f"ls -l {OBJ}/*.cn4 2>/dev/null | head -20"),
    ("CN4SRC", "ls -l /root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNBOneCH_ml/*.cn4 2>/dev/null"),
    ("PARTABLES", f"grep -nE 'TableFile|FileName' {OBJ}/flash.par"),
]

lines = []
for tag, c in cmds:
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True)
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    lines.append(f"===== {tag} =====\n{out.strip()}\n")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("WROTE", OUT)
