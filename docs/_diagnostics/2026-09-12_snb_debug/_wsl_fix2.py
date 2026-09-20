# -*- coding: utf-8 -*-
"""修复后 WSL 端到端复现: rt_mgdFlMode=fl_larsen + RiemannSolver=HLL。
判定标准 (与上次失败对比):
  ① [gr_hypreSolve] Nonconv 计数应显著下降 (上次 11)
  ② dt 不再钉在 dtmin=1e-16 (上次 step 400 起恒为 1e-16)
  ③ dt_hydro 不应崩到 1e-17 (上次 3.7e-17)
  ④ t 应能推进到 tmax=2.0e-10 (上次停在 1.26e-10)"""
import subprocess, io, time, os, sys

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_fix2.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
SC = os.path.join(WS, "flash", "scenarios", "private", "tracer", "SNB", "SNBOneCH_ml", "SNBOneCH_ml.py")

# --skip-build 会强制重编译 (因 par 变更 → 构建指纹不一致), 正确行为
cmd = [PY, SC, "--mode", "wsl", "--tmax", "2.0e-10", "--nproc", "4",
       "--distro", "Ubuntu-22.04"]

t0 = time.time()
with io.open(OUT, "w", encoding="utf-8") as fh:
    fh.write(f"# cmd: {' '.join(cmd)}\n# start {time.strftime('%H:%M:%S')}\n\n")
    fh.flush()
    r = subprocess.run(cmd, capture_output=True, timeout=5400, cwd=WS)
    o = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    fh.write(f"\n\nRC={r.returncode} WALL={time.time()-t0:.1f}s\n\n{o}")
print(f"RC={r.returncode} WALL={time.time()-t0:.1f}s -> {OUT}")
