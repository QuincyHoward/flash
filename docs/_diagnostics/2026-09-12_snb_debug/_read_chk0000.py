# -*- coding: utf-8 -*-
"""读 WSL 端 chk_0000, 检查 8 个物种是否都被写入, 以及 tele/pres 范围。"""
import io
import os
import subprocess

DISTRO = "Ubuntu-22.04"
OBJDIR = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
LOCAL_TMP = "/root/_probe/chk0000.h5"
WIN_OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_chk0000_species.txt"

# 把 chk_0000 复制到 /tmp 并从 Windows 侧用 h5py 读 (避免 WSL 无 h5py)
PY = r'''
import h5py, numpy as np
f = h5py.File(r"%s", "r")
sp = ["cham","shld","samp","tar1","tar2","tar3","tar4","tar6"]
print("%-6s %10s %10s %12s %14s" % ("spec","nonzero","total","min","max"))
for s in sp:
    k = "spec_%s mass scalars" % s
    if k not in f:
        print("%-6s  [MISSING KEY %s]" % (s, k)); continue
    a = f[k][:]
    nz = int(np.count_nonzero(a))
    print("%-6s %10d %10d %12.3e %14.3e" % (s, nz, a.size, a.min(), a.max()))
print()
for k in ("dens","pres","tele","tion","trad","velx"):
    if k in f:
        a = f[k][:]
        print("%-6s min=%12.5e max=%12.5e  n=%d" % (k, a.min(), a.max(), a.size))
print()
print("keys with 'mass scalars':", [x for x in f.keys() if "mass scalars" in x])
'''

SCRIPT = f'''
set -e
cp -f "{OBJDIR}/snbonechug_hdf5_chk_0000" "{LOCAL_TMP}"
ls -la "{LOCAL_TMP}"
echo "COPY_OK"
'''


def wsl(cmd, timeout=300):
    p = subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc", cmd],
                       capture_output=True, timeout=timeout)
    return (p.stdout or b"").decode("utf-8", "replace"), \
           (p.stderr or b"").decode("utf-8", "replace"), p.returncode


sh = os.path.join(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash",
                  "_copy_chk.sh")
io.open(sh, "w", encoding="utf-8", newline="\n").write(SCRIPT)
subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc",
                "cp -f /mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/"
                "_copy_chk.sh /root/_probe/c.sh && sed -i 's/\\r$//' "
                "/root/_probe/c.sh && bash /root/_probe/c.sh"],
               capture_output=True, timeout=300)
o, e, rc = wsl('echo HOME=$HOME; ls -la /root/_probe/ | head', 120)
print(o, e)

# UNC 上 h5py 会因文件锁失败 → 一律先复制到 E: 盘再读
loc_e = (r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
         r"\_chk0000_wsl.h5")
cmd = (f'cp -f "{LOCAL_TMP}" '
       '/mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/'
       '_chk0000_wsl.h5 && echo COPIED_TO_E')
o, e, rc = wsl(cmd, 300)
print("[copy]", o.strip(), e.strip())
target = loc_e

print("reading:", target)
import h5py
import numpy as np
f = h5py.File(target, "r")
sp = ["cham","shld","samp","tar1","tar2","tar3","tar4","tar6"]
lines = []
lines.append("%-6s %10s %10s %12s %14s" % ("spec","nonzero","total","min","max"))
for s in sp:
    k = "spec_%s mass scalars" % s
    if k not in f:
        lines.append("%-6s  [MISSING KEY %s]" % (s, k)); continue
    a = f[k][:]
    nz = int(np.count_nonzero(a))
    lines.append("%-6s %10d %10d %12.3e %14.3e" % (s, nz, a.size, a.min(), a.max()))
lines.append("")
for k in ("dens","pres","tele","tion","trad","velx"):
    if k in f:
        a = f[k][:]
        lines.append("%-6s min=%12.5e max=%12.5e  n=%d" % (k, a.min(), a.max(), a.size))
lines.append("")
lines.append("mgd keys: " + ", ".join(sorted(x for x in f.keys() if x.startswith("rt_"))[:20]))
txt = "\n".join(lines)
print(txt)
io.open(WIN_OUT, "w", encoding="utf-8").write(txt)
