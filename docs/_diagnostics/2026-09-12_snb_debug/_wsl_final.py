# -*- coding: utf-8 -*-
"""干净的 WSL 端到端验证: --tmax 2.0e-10 (与 NC-E 短时测试同口径) --nproc 4。
验证: ① 无 IONMIX4 abort ② dt 单调增长 ③ 到达 tmax ④ 产出 chk/plt。"""
import subprocess, io, time, os

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_final.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
SC = os.path.join(WS, "flash", "scenarios", "private", "tracer", "SNB", "SNBOneCH_ml", "SNBOneCH_ml.py")

cmd = [PY, SC, "--mode", "wsl", "--tmax", "2.0e-10", "--nproc", "4",
       "--distro", "Ubuntu-22.04", "--skip-build"]

t0 = time.time()
r = subprocess.run(cmd, capture_output=True, timeout=3600)
wall = time.time() - t0
o = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
io.open(OUT, "w", encoding="utf-8").write(f"RC={r.returncode} WALL={wall:.1f}s\n\n{o}")
print(f"RC={r.returncode} WALL={wall:.1f}s")
