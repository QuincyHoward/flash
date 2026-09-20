# -*- coding: utf-8 -*-
"""_perf_parse.py — 从 wsl_run_*.log 提取每步耗时 / 物理时间 / 核数"""
import re, json
from pathlib import Path

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")

# 典型 FLASH 输出行:
#  step:      401  t=  8.43389E-11  dt=  1.36528E-13
#  或 "cycle = 401  ... time = ..."
PAT_STEP = re.compile(
    r"step[s]?\s*[:=]\s*(\d+).*?t\s*=\s*([0-9.eE+-]+).*?dt\s*=\s*([0-9.eE+-]+)", re.I)
PAT_STEP2 = re.compile(r"^\s*(\d+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", re.I)
PAT_WALL = re.compile(r"WALL_SECONDS\s*[:=]\s*([0-9.eE+-]+)")
PAT_EXIT = re.compile(r"RUN_EXIT(?:_NZ)?\s*[:=]\s*(\S+)")

def parse(logp):
    t = logp.read_text(encoding="utf-8", errors="replace")
    lines = t.splitlines()
    steps = []
    for i, l in enumerate(lines):
        m = PAT_STEP.search(l)
        if m:
            steps.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), l.strip()[:150]))
            continue
        if i < 6 or "cycle" in l.lower():
            m2 = PAT_STEP2.match(l)
            if m2:
                try:
                    steps.append((int(m2.group(1)), float(m2.group(2)), float(m2.group(3)), l.strip()[:150]))
                except ValueError:
                    pass
    walls = [float(x) for x in PAT_WALL.findall(t)]
    exits = PAT_EXIT.findall(t)
    return steps, walls, exits, lines

print("=" * 110)
for nd in sorted(CP.iterdir()):
    if not nd.is_dir():
        continue
    logs = list(nd.glob("wsl_run_*.log"))
    if not logs:
        print(f"{nd.name}: no log")
        continue
    lp = logs[0]
    steps, walls, exits, lines = parse(lp)
    print(f"\n### {nd.name}  log={lp.name}  size={lp.stat().st_size:,}  lines={len(lines)}")
    print(f"    WALL_SECONDS={walls}  EXIT={exits}  parsed_steps={len(steps)}")
    if steps:
        print(f"    首: step={steps[0][0]} t={steps[0][1]:.6e} dt={steps[0][2]:.4e}")
        print(f"    末: step={steps[-1][0]} t={steps[-1][1]:.6e} dt={steps[-1][2]:.4e}")
        n = steps[-1][0] - steps[0][0]
        if n > 0 and walls:
            print(f"    -> {n} 步 / {walls[0]:.1f} s = {walls[0]/n:.4f} s/step")
    # 关键告警
    keys = ["Negative", "Nonconv", "CHECK LOG", "ERROR", "Abort", "not converge", "ierr",
            "dtmin", "UseFloor", "IONMIX4", "CONVERGENCE"]
    for k in keys:
        hits = [l.strip() for l in lines if k in l]
        if hits:
            print(f"    !! {k}: {len(hits)} 次 | 例: {hits[0][:120]}")

# 单独 dump n131 的末尾步骤表以核对 s/step
print("\n" + "=" * 110)
print("n131 log 尾部 30 行:")
lp = CP / "n131" / "wsl_run_131.log"
lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
for l in lines[-30:]:
    print("   ", l[:150])
