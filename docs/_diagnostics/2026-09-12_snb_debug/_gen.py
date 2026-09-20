# -*- coding: utf-8 -*-
"""只跑 input 生成 (不编译/不运行), 确认新键落到 par。"""
import subprocess, os, time

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
SC = os.path.join(WS, "flash", "scenarios", "private", "tracer", "SNB", "SNBOneCH_ml", "SNBOneCH_ml.py")

cmd = [PY, SC, "--generate-only"]
t0 = time.time()
r = subprocess.run(cmd, capture_output=True, timeout=900, cwd=WS)
o = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
print(f"RC={r.returncode} WALL={time.time()-t0:.1f}s")
print(o[-5000:])
