# -*- coding: utf-8 -*-
"""
_timing_final.py — 核数伸缩性能的**权威**推导
=================================================
已知锚点（全部来自 sacct / 日志硬数据）:
  * JobID 4864482 (131核): Start 20:44:13, End 20:54:25, Elapsed 00:10:12 = 612 s
  * JobID 4864483 (192核): Start 20:44:24, End 20:54:25, Elapsed 00:10:01 = 601 s
  * JobID 4864484 (256核): Start 20:44:34, End 20:50:55, Elapsed 00:06:21 = 381 s
       └ 其中 WALL_SECONDS=343.8136 s 是**纯 mpiexec ./flash4 时长**（脚本内 date 夹逼）
         => 编译+setup 阶段 = 381 - 344 = 37.2 s

  ★ 关键推论: n256 的 setup+make 只用 37 s（因为 unit.tar.gz 已解压、make -j8）。
    三腿的 setup+make 阶段近似同量级。
    因此:
       n131 纯积分 ≈ 612 - T_build
       n192 纯积分 ≈ 601 - T_build

  但 131 与 192 是被**同一时刻** (20:54:25) CANCELLED 的 → 说明两者都在运行中被打断。
  ★ 更强约束: 三腿**串行提交**、131 与 192 同时结束 => 192 的运行起点晚 11 s。
"""
import json

JOB = {
    "131": dict(jobid="4864482", start="20:44:13", end="20:54:25", elapsed=612, nodes=3,
                node="ia[1814-1816]", steps=1997, t_end=1.23550e-10, dt_end=1.3313e-14, nxb=128),
    "192": dict(jobid="4864483", start="20:44:24", end="20:54:25", elapsed=601, nodes=4,
                node="ia[1009,1712-1713,1810]", steps=1200, t_end=1.04640e-10, dt_end=1.7459e-14, nxb=128),
    "256": dict(jobid="4864484", start="20:44:34", end="20:50:55", elapsed=381, nodes=6,
                node="ib[0514-0516,0601-0603]", steps=980, t_end=9.46600e-11, dt_end=1.0000e-16, nxb=128),
}

# n256 提供了"编译+setup"阶段的实测标定
BUILD_256 = 381 - 343.813593598
print(f"【标定】n256: elapsed={381} s, 纯积分={343.81} s → setup+make 阶段 = {BUILD_256:.1f} s\n")

# 假设三腿 setup+make 阶段相仿（同一 unit.tar.gz、同一台机器的同规格编译）
# 但 N 不同 → setup 的 par 生成/符号链接量相同，故近似相同
BUILD = {"131": BUILD_256, "192": BUILD_256, "256": BUILD_256}

print("=" * 118)
print(f"{'cores':>5} {'JobID':>8} {'N':>3} {'Elapsed':>8} {'build':>7} {'积分墙钟':>9} "
      f"{'nsteps':>6} {'s/step':>8} {'t_end[s]':>12} {'dt_end':>10} {'cells':>7} {'状态':>10}")
print("-" * 118)
rows = []
for n, d in JOB.items():
    run_wall = d["elapsed"] - BUILD[n]
    sps = run_wall / d["steps"]
    print(f"{n:>5} {d['jobid']:>8} {d['nodes']:>3} {d['elapsed']:>8} {BUILD[n]:>7.1f} {run_wall:>9.1f} "
          f"{d['steps']:>6} {sps:>8.4f} {d['t_end']:>12.5e} {d['dt_end']:>10.4e} "
          f"{d['steps'] and d['nxb']*int(n):>7} "
          f"{'CANCELLED' if n!='256' else 'ABORT 3T':>10}")
    rows.append(dict(cores=int(n), **{k: v for k, v in d.items()}, build=BUILD[n],
                     run_wall=run_wall, s_per_step=sps, cells=d["nxb"]*int(n)))
print("-" * 118)

print("\n【相对效率】以 131 核为基准")
base = rows[0]["s_per_step"]
for r in rows:
    print(f"  n{r['cores']:>3}: s/step={r['s_per_step']:.4f}  "
          f"相对 131 = {r['s_per_step']/base:.3f}×  "
          f"({'>' if r['s_per_step']>base else '<'}131)  "
          f"单核效率比 = {(base/r['s_per_step'])*(r['cores']/131):.3f}")

print("\n【到 tmax=2e-10 的剩余成本】(按各自 dt_end，纯积分)")
TGT = 2.0e-10
for r in rows:
    left = (TGT - r["t_end"]) / r["dt_end"]
    hrs = left * r["s_per_step"] / 3600
    print(f"  n{r['cores']:>3}: 完成 {r['t_end']/TGT*100:5.2f}%  剩余 {left:>8.0f} 步  "
          f"预计 {hrs:>7.2f} h  ({hrs*60:>6.0f} min)")

print("\n【到 1.6 ns 生产的剩余成本】(生产目标)")
TGT2 = 1.6e-9
for r in rows:
    left = (TGT2 - r["t_end"]) / r["dt_end"]
    hrs = left * r["s_per_step"] / 3600
    print(f"  n{r['cores']:>3}: 剩余 {left:>10.0f} 步  预计 {hrs:>8.1f} h  ({hrs/24:.1f} 天)")

json.dump(rows, open(r"C:\Users\Administrator\_scaling_verdict.json", "w"), indent=1)
print("\n-> C:\\Users\\Administrator\\_scaling_verdict.json")
