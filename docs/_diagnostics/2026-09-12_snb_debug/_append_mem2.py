# -*- coding: utf-8 -*-
"""追加 NC-E 4864358 完整事后分析到 2026-09-12.md。"""
import io

P = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\.workbuddy\memory\2026-09-12.md"

ADD = """
## 74. ★★★ NC-E 4864358 完整事后分析: **已完成, 但物理退化**

**结论: 该作业在调查期间已正常运行至结束, 不是空转。**

权威证据 (objdir 内 `wsl_run_snbonech.log`, 15352 行):
```
 exiting: reached max SimTime
 *** Wrote checkpoint file to snbonechug_hdf5_chk_0023 ****
 *** Wrote plotfile to snbonechug_forced_hdf5_plt_cnt_0000 ****
RUN_EXIT=0
WALL_SECONDS=3484.333439160        # 58.1 min
```
- 推进 **9073 步**, 到 `t = 2.0000E-10` = 恰好 tmax ✓
- 产出 **23 个 chk** (chk_0000..0023, 各 10.1 MB) + **5 个 plt** (各 2.03 MB)
- 效率 **0.384 s/step**

**为什么 SLURM 的 `run_*_out.txt` 是 0 字节**: `run.sh` 里是
`mpiexec -n 131 ./flash4 > wsl_run_snbonech.log 2>&1` —— stdout **被重定向进
objdir 内的日志**, SLURM 的 `--output` 文件自然空。
★ 教训: **查 HPC 作业是否在算, 必须读 objdir 内的 FLASH 日志, 不能只看
`run_%j_out.txt`**。

## 75. ★★ 但该结果**物理退化**: HYPRE component=2 全程非收敛

| 指标 | 实测 | 判定 |
|---|---|---|
| `Nonconv` 总次数 | **5962** | 每 1-2 步就有一次 |
| component 分布 | 5962 全是 **component=2** | MGD 第 2 能群 |
| ierr 分布 | ierr=0 : 5512 / **ierr=256 : 450** | 后者是真失败 |
| `eos_nr WARN` | 4 次 (T~1.1万 K) | 少量 |
| ERROR/ABORT | **0** | 没崩 |

**dt 演化 (每 800 步采样)** —— dt **没有被钉死**, 而是从 2.5e-14 缓慢单调下滑:
| step | t | dt |
|---|---|---|
| 1 | 1.00e-15 | 1.100e-15 |
| 801 | 1.03e-10 | 2.526e-14 |
| 2401 | 1.28e-10 | 1.308e-14 |
| 4801 | 1.57e-10 | 1.115e-14 |
| 7201 | 1.82e-10 | 9.865e-15 |
| 8801 | 1.98e-10 | 9.132e-15 |
| 9073 | 2.00e-10 | 8.995e-15 |

★ 首 10 步 dt **按 1.1 倍增长** (`tstep_change_factor=1.1`), 从 1e-15 爬到 2.6e-14
(约 800 步内), 说明 **dt 增长机制正常**, 不是被 dtmin 钉死。
`dt_minloc` 的 x 从 `-2.684e-06` 漂到 `-3.906e-03` (即从域右端附近移到左端附近),
**是移动的限制点, 不是冻结**。

⇒ 与本地 WSL 的"dt 钉在 dtmin + x 冻结在 -3.995e-02"**现象不同**
(本地更严重)。NC-E 上 131 核 = 3.35 格/层勉强达标, 结果**可用但需要审查**。

## 76. ★ 1.6 ns 全长外推 (供用户决策)

沿用实测 `0.384 s/step` 与末段 `dt ≈ 9.0e-15`:
```
1.6e-9 / 9.0e-15 = 177,778 步  =>  68,267 s  =>  19.0 h
```
★ 注意 dt 若继续下滑, 步数还会增加。**19 h 是乐观下限**。

若提到 192 核 (dx = 500/(192*128) = 0.02035 um, 4.92 格/层):
- 每步更贵 (格数 × 1.5), 但 dt 更小 (CFL) → 步数 × 1.47
- 净效果约 **1.5× 更慢** => ~28 h, 但**薄层分辨更好**。

**建议**: 先下载 4864358 的 23 个 chk 做物理审查 (是否已到准稳态 / 前沿位置是否合理),
再决定 1.6 ns 是否值得 19-28 h。用户明确"由我决定是否需要完整 1.6 ns 测试"。

## 77. 两份被取消作业 (4864352 / 4864357) 的解读

- 两者 `hydra_bstrap_proxy` = **FAILED**, `run_*_out.txt` = **0 字节**
- `run_*_err.txt` 只有 `slurmstepd: error: JOB ... CANCELLED` —— **无自身报错**
- 时间线: 4864352 启动 17:04 -> 17:18 取消 (14 min); 4864357 启动 17:19 -> 17:23 取消 (3 min)
- 4864358 于 17:24 启动并成功

⇒ 这两次是**被上层主动取消** (很可能是前一轮调试时我或用户手动 scancel,
或投递脚本重投时先取消旧作业), **不是程序崩溃**。
`hydra_bstrap_proxy FAILED` 是 MPI 启动代理在作业被 kill 后的**伴随现象**, 非根因。

★ 教训: 判"作业是否真的在跑"要三看 —— ① `squeue`/`sacct` 状态;
② **作业目录内是否有 chk/plt 且 mtime 在增长**; ③ **objdir 内 FLASH 日志的步进轨迹**。
只看 `run_%j_out.txt` 会得出"空转"的**错误结论**。
"""

with io.open(P, "a", encoding="utf-8") as fh:
    fh.write(ADD)
print(f"appended {len(ADD)} chars")
