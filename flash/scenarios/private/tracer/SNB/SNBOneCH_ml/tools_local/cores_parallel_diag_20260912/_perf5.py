# -*- coding: utf-8 -*-
"""_perf5.py — 稳健解析 FLASH 步表（按 token 拆分，不用大正则）"""
import re, json
from pathlib import Path
import numpy as np

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")

SUBMIT = 20 * 3600 + 44 * 60 + 34      # 2026-09-12T20:44:34
CANCEL = 20 * 3600 + 54 * 60 + 25      # n131/n192 CANCELLED AT 20:54:25
WALL131 = CANCEL - SUBMIT              # 581 s
JOB = {"131": ("4864482", "ia1814"), "192": ("4864483", "ia1009"), "256": ("4864484", "?")}
TAIL = re.compile(r"^(.*?)\s*\|\s*(.*)$")

def parse_steps(path):
    rows = []
    for l in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "|" not in l:
            continue
        m = TAIL.match(l)
        if not m:
            continue
        left, right = m.group(1).strip(), m.group(2).strip()
        if left.startswith("n "):
            continue
        toks = left.split()
        if len(toks) < 3:
            continue
        try:
            step = int(toks[0]); t = float(toks[1]); dt = float(toks[2])
        except ValueError:
            continue
        if "(" not in left:
            continue
        vx = None
        mo = re.search(r"\(\s*([-0-9.Ee+]+),", left)
        if mo:
            vx = float(mo.group(1))
        rt = right.split()
        if len(rt) < 4:
            continue
        try:
            rows.append(dict(step=step, t=t, dt=dt, vx=vx,
                             dt_hydro=float(rt[0]), dtDiff=float(rt[1]),
                             dtHeatXc=float(rt[2]), cfl=float(rt[3])))
        except ValueError:
            continue
    return rows

res = {}
for nd in sorted(CP.iterdir()):
    if not nd.is_dir():
        continue
    logs = list(nd.glob("wsl_run_*.log"))
    if not logs:
        continue
    r = parse_steps(logs[0])
    if r:
        res[nd.name] = r
        print(f"{nd.name}: parsed {len(r)} step rows, step {r[0]['step']}..{r[-1]['step']}")

tgt = 2.0e-10
print("\n" + "=" * 130)
print(f"{'cores':>5} {'rows':>5} {'stepN':>6} {'t_final[s]':>13} {'dt_final':>11} {'dt_med':>11} "
      f"{'s/step':>8} {'完成度':>7} {'剩余步':>9} {'预计小时':>9} {'cells':>7}")
print("-" * 130)
summ = {}
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    N = rows[-1]["step"] - 1
    tf, dtf = rows[-1]["t"], rows[-1]["dt"]
    dtm = float(np.median([r["dt"] for r in rows]))
    sps = WALL131 / N if n == "131" else float("nan")
    left = (tgt - tf) / dtf
    hrs = left * (WALL131 / N) / 3600 if n == "131" else float("nan")
    print(f"{n:>5} {len(rows):>5} {rows[-1]['step']:>6} {tf:>13.5e} {dtf:>11.4e} {dtm:>11.4e} "
          f"{sps:>8.4f} {tf/tgt*100:>6.2f}% {left:>9.0f} {hrs:>9.2f}")
    summ[n] = dict(jobid=JOB[n][0], node=JOB[n][1], rows=len(rows), last_step=rows[-1]["step"],
                   t_final=tf, dt_final=dtf, dt_median=dtm, s_per_step=sps,
                   steps_remaining=float(left), hours_remaining=float(hrs))
print("-" * 130)

print("\n--- dt 演化 ---")
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    d = np.array([r["dt"] for r in rows]); ts = np.array([r["t"] for r in rows])
    print(f"n{n}: dt[0]={d[0]:.4e} dt[5]={d[5]:.4e} dt[20]={d[20]:.4e} dt_max={d.max():.4e}"
          f"@{rows[int(d.argmax())]['step']} dt[-1]={d[-1]:.4e}")
print("\n--- dt_hydro 是否 == dt (CFL 主导判据) ---")
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    d = np.array([r["dt"] for r in rows]); dh = np.array([r["dt_hydro"] for r in rows])
    rat = d / dh
    print(f"n{n}: dt/dt_hydro min={np.nanmin(rat):.6f} max={np.nanmax(rat):.6f} "
          f"median={np.nanmedian(rat):.6f}  ==1 的比例={np.isclose(rat,1,rtol=1e-3).mean()*100:.1f}%")
print("\n--- cfl / dtDiff / dtHeatXc ---")
for k, rows in sorted(res.items()):
    n = k.lstrip("n")
    cfl = np.unique([r["cfl"] for r in rows])
    dd = np.array([r["dtDiff"] for r in rows]); dx = np.array([r["dtHeatXc"] for r in rows])
    print(f"n{n}: cfl={cfl}  dtDiff[{dd.min():.3e},{dd.max():.3e}]  dtHeatXc[{dx.min():.3e},{dx.max():.3e}]")
json.dump(summ, open(r"C:\Users\Administrator\_perf_summary.json", "w"), indent=1)
print("\n-> C:\\Users\\Administrator\\_perf_summary.json")
