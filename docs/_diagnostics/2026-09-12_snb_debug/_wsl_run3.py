# -*- coding: utf-8 -*-
"""直接在 WSL objdir 重跑 flash4 短时 (不重新 setup/make), 抓 dt_Diff 与首帧状态。"""
import subprocess, io, time

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_run3.txt"
OBJ = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
LOG = f"{OBJ}/wsl_run3.log"

def sh(c, tmo=1200):
    t0 = time.time()
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True, timeout=tmo)
    return ((r.stdout.decode("utf-8", "replace") +
             r.stderr.decode("utf-8", "replace")).strip(), r.returncode, time.time() - t0)

lines = []
lines.append(f"CMD tmax=1.0e-12 nproc=4")

# 1) 确认 flash.par 的 tmax 与关键键
o, rc, dt = sh(f'grep -nE "^(tmax|gr_hypreUseFloor|dtmax)" {OBJ}/flash.par')
lines.append(f"===== PAR GATE =====\n{o}\n")

# 2) 重跑
cmd = (f'cd {OBJ} && rm -f snbonechug_* wsl_run3.log && '
       f'mpiexec -n 4 ./flash4 > wsl_run3.log 2>&1 ; echo "RUN_RC=$?" ; '
       f'tail -25 wsl_run3.log ; echo "---CHK---" ; ls snbonechug_* 2>/dev/null | wc -l')
o, rc, dt = sh(cmd)
lines.append(f"===== RUN ({dt:.1f}s) =====\n{o}\n")

# 3) 抓 dt / dt_Diff / rho 信息
o, rc, dt = sh(f'grep -nE "dt_Diff|dt *=" {LOG} | head -20')
lines.append(f"===== DT =====\n{o}\n")

o, rc, dt = sh(f'grep -nEi "error|abort|warn" {LOG} | head -20')
lines.append(f"===== ERR =====\n{o}\n")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("WROTE", OUT)
