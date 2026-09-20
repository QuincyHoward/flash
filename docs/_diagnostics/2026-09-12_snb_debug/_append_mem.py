# -*- coding: utf-8 -*-
"""追加本轮结论到 2026-09-12.md (用文件方式写, 规避 shell 反引号吞噬)。"""
import io

P = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\.workbuddy\memory\2026-09-12.md"

HEAD = "=" * 78
ADD = f"""
{HEAD}
# 第二轮 (18:20 更新): 根目录收纳 + 超算作业核实 + nxb 自适应修复验收
{HEAD}

## 69. ★★★ 决定性修复验收通过: 8 物种全部写入

上轮根因: `Simulation_initBlock.F90` 按 `xcent(i) >= bnd_k .and. <= bnd_k+1`
判据选物种, 而 `-nxb=128` 配 `-n 4` 得 dx = 0.977 um >> 0.1 um 薄层
=> 6 个物种**一个格点都落不进**, 质量分数恒为 `sim_smallX = 1e-99`。

修复: `build_setup_flags_ug()` 按 nproc 反推
`nxb = 2**ceil(log2(max(8, dom/(3e-6 * nproc))))`, 并加 `dx>0.03um` 硬中止门。

**实测验收** (WSL `--nproc 4` => `-nxb=8192`, 总格 **32768**, dx = 0.015259 um):

| 物种 | 非零格数 | 覆盖区间 (质量分数 > 0.5) | 设计位置 | 判定 |
|---|---|---|---|---|
| cham | 29091 | -400 ... +100 um (填充) | He fill | OK |
| shld | 7 | 0.0015 ... 0.0931 um | 0 - 0.1 um | OK |
| samp | 3638 | 0.108 ... 56.09 um | CH 主层 | OK |
| tar1 | 6 | 1.0086 ... 1.0849 um | 1.0 um | OK |
| tar2 | 7 | 2.0004 ... 2.0920 um | 2.0 um | OK |
| tar3 | 7 | 3.0075 ... 3.0991 um | 3.0 um | OK |
| tar4 | 6 | 4.0146 ... 4.0909 um | 4.0 um | OK |
| tar6 | 6 | 6.0135 ... 6.0898 um | 6.0 um | OK |

**对比修复前**: shld / tar1 / tar2 / tar3 / tar4 / tar6 全部 nonzero = 0。
=> 根因判定正确, 修复有效。每薄层 6-7 格 >= 门槛 3 格。

## 70. 撤销上轮告警: pres 跨 9 个量级 **不是** 故障

实测 chk_0000 剖面: x<0 与 x>56 um 处 rho=1e-6 / P=6.07e3;
0<x<56 um 处 rho=1.0 / P=2.245e10。
**dens 跳变仅 2 处** (delta log10 正好 6.00), 即 cham|shld 与 samp|cham 界面;
**中间 12 层之间无任何密度跳变** —— 层间 rho 全部 = 1.0, 靠 spec_* 质量分数区分。
=> pres 的 9 量级跨度 = P = rho*kT/(mu*m_p) 中 rho 跨 6 量级的**正常后果**,
不是热力学不一致。tele 全域 290.11 K 均匀、velx 恒为 0。

★ 几何修正: 层堆在 x 属于 [0, 56 um], **不是** 上轮 summary 写的 [0, 6e-4]。

## 71. ★★★ 超算"三个作业"真相: 只有 1 个在跑, 且它 **可能没在算**

NC-E (scfa2696) 今日 sacct 全量:

| JobID | Name | State | Elapsed | 诊断 |
|---|---|---|---|---|
| 4864350 | SNB1CH_b_nce | COMPLETED | 00:01:08 | 仅 build, 正常 |
| 4864352 | SNB1CH_r_nce | CANCELLED | 00:14:31 | hydra_bstrap_proxy **FAILED** |
| 4864357 | SNB1CH_r_nce | CANCELLED | 00:03:18 | hydra_bstrap_proxy **FAILED** |
| 4864358 | SNB1CH_r_nce | **RUNNING** | 00:55:39 | 唯一存活 |

**关键证据 1 — 失败的共性**: 4864352 / 4864357 的 `hydra_bstrap_proxy` 均为 FAILED,
`run_*_err.txt` 只有 `slurmstepd: error: JOB ... CANCELLED` (被上层取消, 非自身崩溃)。
两者的 `run_*_out.txt` = **0 字节** => 从未开始计算。

**★★ 关键证据 2 — RUNNING 的 4864358 输出也是 0 字节**:
- `run_4864358_out.txt` = 0 B (T0) -> 0 B (T1, 6 秒后), 完全没增长
- 作业目录下**没有任何 `*_chk_*` / `*_hdf5_plt_*`** => 未产生任何输出
- `run.sh` 是 `cd ~/QC/.../SNBOneCH_ml_ug_obj && mpiexec -n 131 ./flash4 > wsl_run_snbonech.log`
  => 真正的 stdout **被重定向进了 `wsl_run_snbonech.log`**, 所以 SLURM 的
  `run_*_out.txt` 必然是空的。**必须去看 objdir 里的 `wsl_run_snbonech.log`**。

**★ 关键证据 3 — run.sh 里的 build 参数是旧的**:
`build.sh` 中 `./setup ... -nxb=128 ...`, 而本机修复后应为按 nproc 自适应。
131 核时 `-nxb=128` 恰好 dx = 500/(131*128) = 0.02982 um, 勉强达标 (3.35 格/层),
所以超算上这个值**碰巧可用**, 但**不是**由新逻辑算出的。

## 72. 超算作业待办 (未完成)

1. 读 `~/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/wsl_run_snbonech.log`
   判断 4864358 是否真在推进 (这是唯一权威证据)。
2. 若该 log 不存在 => `cd` 失败或 flash4 未启动, 作业是"空转"。
3. 重新提交时应:
   - `build.sh` 的 `-nxb=128` 改成由 `build_setup_flags_ug()` 计算 (或显式用 256);
   - 131 核仅 3.35 格/层, **建议 >= 192 核** (dx = 500/(192*128) = 0.02035 um, 4.92 格/层);
   - 两份失败作业说明**连续取消**: 需要在 run.sh 里加错误即时报错 (已有 `set -e`)。
4. BSCC (sch0348): `squeue` 空, 今日无作业 => 未使用。

## 73. 根目录收纳完成

- 归档 **203 个**散落临时诊断文件 (199 个 `_*` + `quick_test_1d.h5` + `]` + 4 个后到者)
  -> `docs/_diagnostics/2026-09-12_snb_debug/` (含 `_INDEX.txt`, 只移动不删除)
- 根目录现仅剩 **17 个**合法文件 (.gitattributes/.gitignore/.pre-commit-config.yaml/
  INSTALL_TEST_REPORT.txt/LICENSE/Makefile/NOTICE/README.md/pyproject.toml/
  start_flash.py + 3 个 pytest 日志) + 3 个运行中任务的 .txt 副本
- 未动 `%SystemDrive%/` (内含 Windows Caches .db, 属误建垃圾目录, 已列清单待用户裁决)
- 收纳脚本: `_archive_root.py` / `_sweep_root.py` (均已随归档移入 `_diagnostics/`)
"""

with io.open(P, "a", encoding="utf-8") as fh:
    fh.write(ADD)
print(f"appended {len(ADD)} chars -> {P}")
