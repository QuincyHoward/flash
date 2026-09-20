# -*- coding: utf-8 -*-
"""对 SNB_1D_laser 参考 par 与我们的 par 做键级差分 (只比较 key=value, 忽略注释/空格)。"""
import subprocess, io, re

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_par_diff.txt"

def sh(c, tmo=180):
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True, timeout=tmo)
    return (r.stdout.decode("utf-8", "replace") +
            r.stderr.decode("utf-8", "replace"))

REF = "/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNB_1D_laser/flash.par"
OUR = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/flash.par"

def load(p):
    txt = sh(f"cat {p}")
    d = {}
    for ln in txt.splitlines():
        ln = ln.split("#")[0].strip()
        if not ln or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        d[k.strip()] = v.strip()
    return d

ref, our = load(REF), load(OUR)

L = [f"REF keys={len(ref)}  OUR keys={len(our)}", ""]

L.append(f"===== 只在 REF 中 (OUR 缺失) =====")
onlyref = sorted(set(ref) - set(our))
for k in onlyref:
    L.append(f"  {k} = {ref[k]}")

L.append("")
L.append(f"===== 只在 OUR 中 (REF 没有) =====")
onlyour = sorted(set(our) - set(ref))
for k in onlyour[:120]:
    L.append(f"  {k} = {our[k]}")
L.append(f"  ... total {len(onlyour)}")

L.append("")
L.append(f"===== 值不同 (共同键) =====")
both = sorted(set(ref) & set(our))
ndiff = 0
for k in both:
    a, b = ref[k], our[k]
    na = a.strip('"\'').lower()
    nb = b.strip('"\'').lower()
    if na != nb:
        L.append(f"  {k}: REF={a}  |  OUR={b}")
        ndiff += 1
L.append(f"  ... total diff {ndiff} / common {len(both)}")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("WROTE", OUT)
