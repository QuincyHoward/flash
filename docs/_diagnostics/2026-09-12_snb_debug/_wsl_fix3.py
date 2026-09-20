# -*- coding: utf-8 -*-
"""修复网格分辨率后的 WSL 本地验证 (nproc=4 -> nxb=8192, dx=0.0153um)。
判定标准:
  ① setup log 显示 -nxb=8192
  ② chk_0000 中 8 个物种质量分数**全部非零** (上次 shld/tar* 全为 0)
  ③ tele 不出现 1e12~1e14 K (上次 5e12)
  ④ dt_hydro 不<1e-16 且 t 能推进"""
import subprocess, io, time, os

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_fix3.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
SC = os.path.join(WS, "flash", "scenarios", "private", "tracer", "SNB", "SNBOneCH_ml", "SNBOneCH_ml.py")

# 先短跑 1e-11 快速看初始条件是否正确 (不浪费 20 分钟)
cmd = [PY, SC, "--mode", "wsl", "--tmax", "1.0e-11", "--nproc", "4",
       "--distro", "Ubuntu-22.04"]

t0 = time.time()
with io.open(OUT, "w", encoding="utf-8") as fh:
    fh.write(f"# cmd: {' '.join(cmd)}\n# start {time.strftime('%H:%M:%S')}\n\n")
    fh.flush()
    r = subprocess.run(cmd, capture_output=True, timeout=7200, cwd=WS)
    o = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    fh.write(f"\n\nRC={r.returncode} WALL={time.time()-t0:.1f}s\n\n{o}")
print(f"RC={r.returncode} WALL={time.time()-t0:.1f}s -> {OUT}")
