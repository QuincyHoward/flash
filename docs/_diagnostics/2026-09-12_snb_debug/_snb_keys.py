# -*- coding: utf-8 -*-
"""检查 SNB 相关运行时键是否在 OUR par 中存在 (对比 REF)。SNB 依赖 rt_mgd* / snb_* / useSNB。"""
import subprocess, io, re

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_snb_keys.txt"

def sh(c, tmo=180):
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True, timeout=tmo)
    return (r.stdout.decode("utf-8", "replace") +
            r.stderr.decode("utf-8", "replace"))

REF = "/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNB_1D_laser/flash.par"
OUR = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/flash.par"

L = []
for tag, p in [("REF SNB_1D_laser", REF), ("OUR SNBOneCH_ml", OUR)]:
    L.append(f"===== {tag} : SNB/辐射/传导 键 =====")
    L.append(sh(f"grep -nEi 'snb|snp_|useSNB|mgd|rt_|dr_|larsen|thermalCond|conduction|eleCond|ionCond' {p} | head -70"))
    L.append("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("WROTE", OUT)
