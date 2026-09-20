# -*- coding: utf-8 -*-
"""_perf2.py — 解析 FLASH 逐步日志 (nstep t dt (x y z) | dtnew dtDiff dtHeatXc cfl)"""
import re, json
from pathlib import Path
import numpy as np

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")

ROW = re.compile(
    r"^\s*(\d+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+\(\s*([-0-9.Ee+]+),\s*([-0-9.Ee+]+),\s*([-0-9.Ee+]+)\)\s*\|\s*"
    r"([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)\s+([0-9.Ee+-]+)")

res = {}
for nd in sorted(CP.iterdir()):
    if not nd.is_dir():
        continue
    logs = list(nd.glob("wsl_run_*.log"))
    if not logs:
        continue
    lines = logs[0].read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for l in lines:
        m = ROW.match(l)
        if m:
            rows.append(dict(step=int(m.group(1)), t=float(m.group(2)), dt=float(m.group(3)),
                             vx=float(m.group(4)), dtnew=float(m.group(7)),
                             dtDiff=float(m.group(8)), dtHeatXc=float(m.group(9)),
                             cfl=float(m.group(10))))
    if not rows:
        print(f"{nd.name}: no step rows")
        continue
    res[nd.name] = rows
    s = rows[0]["step"]; e = rows[-1]["step"]
    print(f"\n### {nd.name}   rows={len(rows)}  step {s} -> {e}  (Δ={e-s})")
    print(f"    t: {rows[0]['t']:.6e} -> {rows[-1]['t']:.6e}   dt: {rows[0]['dt']:.4e} -> {rows[-1]['dt']:.4e}")
    print(f"    dtnew: {rows[0]['dtnew']:.4e} -> {rows[-1]['dtnew']:.4e}")
    print(f"    cfl(尾部5): {[r['cfl'] for r in rows[-5:]]}")
    hh = ["%.3e" % r["dtHeatXc"] for r in rows[-3:]]
    dd = ["%.3e" % r["dtDiff"] for r in rows[-3:]]
    print("    dtHeatXc(尾部3): " + str(hh))
    print("    dtDiff(尾部3): " + str(dd))
    # dtnew 钳位统计
    dtn = np.array([r["dtnew"] for r in rows])
    print(f"    dtnew min={dtn.min():.4e} max={dtn.max():.4e} median={np.median(dtn):.4e}")
    print(f"    dtnew 被钳在 1e-16 的步数 = {(dtn <= 1.05e-16).sum()}")

# s/step: 用墙钟/步数（n131: CANCELLED AT 20:54:25, submitted 20:44:34 -> 581 s）
print("\n" + "=" * 100)
print("s/step 估算 (墙钟 = cancel - submit):")
wall = {"131": (20*3600+44*60+34, 20*3600+54*60+25, 4864482)}
for k, rows in res.items():
    ws, we, jid = wall.get(k.lstrip("n"), (0, 0, 0))
    n = rows[-1]["step"] - 1
    if ws:
        W = we - ws
        print(f"  n{k}: {n} 步 / {W} s = {W/n:.4f} s/step   (JobID {jid})")
    else:
        print(f"  n{k}: {n} 步 (墙钟未记录)")
json.dump({k: v[-50:] for k, v in res.items()}, open(Path(r"C:\Users\Administrator\_perf_tail.json"), "w"), indent=1)
print("-> C:\\Users\\Administrator\\_perf_tail.json")
