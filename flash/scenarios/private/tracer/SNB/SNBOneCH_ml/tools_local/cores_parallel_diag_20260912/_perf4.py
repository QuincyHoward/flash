# -*- coding: utf-8 -*-
"""_perf4.py — 完整解析 FLASH 步表 + 性能统计"""
import re, json
from pathlib import Path
import numpy as np

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")

ROW = re.compile(r"^\s*(\d+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+\(\s*([-0-9.Ee+]+),\s*([-0-9.Ee+]+),\s*([-0-9.Ee+]+)\s*\)\s*\|\s+"
                 r"([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)")

# 墙钟（由 slurm CANCELLED 时间 - 提交时间）
SUBMIT = 20 * 3600 + 44 * 60 + 34
CANCEL = 20 * 3600 + 54 * 60 + 25
WALL = CANCEL - SUBMIT          # 581 s
JOB = {"131": "4864482", "192": "4864483", "256": "4864484"}
NODE = {"131": "ia1814", "192": "ia1009", "256": "?"}

res = {}
for nd in sorted(CP.iterdir()):
    if not nd.is_dir():
        continue
    logs = list(nd.glob("wsl_run_*.log"))
    if not logs:
        continue
    rows = []
    for l in logs[0].read_text(encoding="utf-8", errors="replace").splitlines():
        m = ROW.match(l)
        if m:
            rows.append(dict(step=int(m.group(1)), t=float(m.group(2)), dt=float(m.group(3)),
                             vx=float(m.group(4)), dt_hydro=float(m.group(7)),
                             dtDiff=float(m.group(8)), dtHeatXc=float(m.group(9)), cfl=float(m.group(10))))
    if rows:
        res[nd.name] = rows

print("=" * 128)
print(f"{'cores':>5} {'rows':>5} {'step0':>6} {'stepN':>6} {'t_final[s]':>13} {'tmax目标':>10} {'完成度':>8} "
      f"{'dt_final':>11} {'s/step':>8} {'预计到2e-10':>11}")
print("-" * 128)
tgt = 2.0e-10
summary = {}
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    N = rows[-1]["step"] - 1
    tf = rows[-1]["t"]
    dtf = rows[-1]["dt"]
    sps = WALL / N if N else float("nan")
    n_left = (tgt - tf) / dtf if dtf > 0 else float("inf")
    hrs = n_left * sps / 3600
    print(f"{n:>5} {len(rows):>5} {rows[0]['step']:>6} {rows[-1]['step']:>6} {tf:>13.5e} {tgt:>10.1e} "
          f"{tf/tgt*100:>7.2f}% {dtf:>11.4e} {sps:>8.4f} {hrs:>9.2f} h")
    summary[n] = dict(jobid=JOB[n], node=NODE.get(n, "?"), rows=len(rows), steps=N,
                      t_final=tf, dt_final=dtf, s_per_step=sps,
                      n_steps_to_tmax=float(n_left), hours_to_tmax=float(hrs))
print("-" * 128)

# ---- dt 演化: 启动瞬态 vs CFL 稳定段 ----
print("\n--- dt 演化分段（每腿）---")
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    dts = np.array([r["dt"] for r in rows])
    ts = np.array([r["t"] for r in rows])
    i10 = min(10, len(dts) - 1)
    print(f"n{n}: dt[0]={dts[0]:.4e}  dt[10]={dts[i10]:.4e}  dt_max={dts.max():.4e} @step "
          f"{rows[int(dts.argmax())]['step']}  dt[-1]={dts[-1]:.4e}")
    # 进入 CFL 平稳段的步号（dt 变化 < 1%）
    stable = None
    for i in range(20, len(dts)):
        if abs(dts[i] / dts[i-1] - 1) < 0.01 and ts[i] > 1e-11:
            stable = i
            break
    print(f"      进入平稳段 step≈{rows[stable]['step'] if stable else 'N/A'}  "
          f"(t≈{ts[stable]:.3e})" if stable else "      未进入平稳段")

# ---- 数值健康: dt_Diff / dt_HeatXc / cfl ----
print("\n--- 数值健康 ---")
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    cfl = np.array([r["cfl"] for r in rows])
    dh = np.array([r["dt_hydro"] for r in rows])
    dd = np.array([r["dtDiff"] for r in rows])
    dx = np.array([r["dtHeatXc"] for r in rows])
    print(f"n{n}: cfl={np.unique(cfl)}  dt_hydro[{dh.min():.3e},{dh.max():.3e}]  "
          f"dt_Diff[{dd.min():.3e},{dd.max():.3e}]  dt_HeatXc[{dx.min():.3e},{dx.max():.3e}]")
    print(f"      dt==dt_hydro 的比例 = {(np.isclose(dts:=np.array([r['dt'] for r in rows]), dh, rtol=1e-3)).mean()*100:.1f}%  "
          f"(=> CFL/hydro 限速主导)")

json.dump(summary, open(r"C:\Users\Administrator\_perf_summary.json", "w"), indent=1)
print("\n-> C:\\Users\\Administrator\\_perf_summary.json")
