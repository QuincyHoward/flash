# -*- coding: utf-8 -*-
"""对照实验: 用已知能跑的参考场景 (SNB_1D_laser) 的 par 与 objdir log 做对比,
找出 SNBOneCH_ml 与它的关键差异 (dt_Diff 是否也 1e8x?)。"""
import subprocess, io, os

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_ref_cmp.txt"

def sh(c, tmo=180):
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True, timeout=tmo)
    return (r.stdout.decode("utf-8", "replace") +
            r.stderr.decode("utf-8", "replace")).strip()

L = []

# 1) 参考场景 par 中的热传导 / SNB 关键参数
REF_PAR = "/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNB_1D_laser/flash.par"
L.append("===== REF PAR: SNB_1D_laser (热传导/SNB 块) =====")
L.append(sh(f"grep -nEi 'hypre|useSNB|snp_|snb|diff_|cond|flux|tele|resist|dtmax|dt_shrink|dt_cutoff' {REF_PAR} 2>/dev/null | head -60"))

L.append("")
L.append("===== OUR PAR (同字段) =====")
OUR = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/flash.par"
L.append(sh(f"grep -nEi 'hypre|useSNB|snp_|snb|diff_|cond|flux|resist|dtmax|dt_shrink|dt_cutoff' {OUR} 2>/dev/null | head -80"))

io.open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("WROTE", OUT)
