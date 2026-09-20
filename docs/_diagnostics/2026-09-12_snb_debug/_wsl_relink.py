# -*- coding: utf-8 -*-
"""在 WSL objdir 里手动补全 .cn4 链接并验证; 再重跑 flash4 短时。"""
import subprocess, io, time

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_relink.txt"
OBJ = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
SIM = "/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNBOneCH_ml"

def sh(c, tmo=900):
    t0 = time.time()
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True, timeout=tmo)
    o = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    return o.strip(), r.returncode, time.time() - t0

lines = []
# 1) 手动链接全部 cn4
o, rc, dt = sh(f'cd {OBJ} && for f in {SIM}/*.cn4; do ln -sf "$f" "$(basename "$f")"; done; '
               f'ls -l *.cn4 | sed "s#.*/##" ; echo RC=$?')
lines.append(f"===== RELINK rc={rc} {dt:.1f}s =====\n{o}\n")

# 2) 校验 par 中每个表名都有链接
o, rc, dt = sh(f'cd {OBJ} && for t in $(grep -ohE "(eos_|op_)[A-Za-z0-9]+(Table)?(File|Name) *= *\"[^\"]+\"" flash.par '
               f'| sed -E "s/.*\\"([^\\"]+)\\".*/\\1/" | sort -u); do '
               f'if [ -e "$t" ]; then echo "OK   $t"; else echo "MISS $t"; fi; done')
lines.append(f"===== TABLE CHECK =====\n{o}\n")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("WROTE", OUT)
