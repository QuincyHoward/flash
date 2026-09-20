# -*- coding: utf-8 -*-
"""更新项目长期备忘 MEMORY.md: 写入本轮 3 条铁律 (并压缩空间)。"""
import io
import os
import re

P = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\.workbuddy\memory\MEMORY.md"
t = io.open(P, encoding="utf-8").read()
print("before:", len(t), "chars")

# 1) 在 "工程坑" 段落后追加新条目
NEW = """
8. ★★★ **判 HPC 作业"是否真在算"必须看三处, 只看 `run_%j_out.txt` 会误判**:
   ① `squeue`/`sacct` 状态; ② **作业目录内 chk/plt 的 mtime 是否在增长**;
   ③ ★ **objdir 内 FLASH 日志的步进轨迹**。本仓库 `run.sh` 把 stdout
   `> wsl_run_snbonech.log` 重定向进 objdir, 所以 SLURM 的 `--output` 文件
   **永远是 0 字节**。2026-09-12 曾据此误判"空转", 实际作业已正常跑完
   (9073 步 / 58.1 min / RUN_EXIT=0 / 23 chk + 5 plt)。
   同理 `hydra_bstrap_proxy FAILED` 常是**作业被 kill 后的伴随现象**, 非根因。
9. ★★★ **`+ug` 网格必须按 nproc 反推 nxb, 否则 0.1 µm 薄层物种从不被写入**:
   `Simulation_initBlock.F90` 按单元中心判据选物种, 若 `dx > 薄层厚度` 则
   **没有任何单元中心落进薄层** → 该物种质量分数恒为 `sim_smallX=1e-99` →
   相邻层直接接触 (ρ 差 6 量级) → 一步即爆。
   铁律: `nxb = 2**ceil(log2(max(8, dom/(3e-6 * nproc))))` (3e-6 cm = 0.03 µm),
   且 `dx > 0.03 µm` 时**硬中止**。验收判据 = **chk_0000 里 8 个物种全部 nonzero**,
   每个薄层 6-7 格 (门槛 3 格)。见 `SNBOneCH_ml.py:build_setup_flags_ug()`。
10. ★ **`pres` 跨 6-9 个量级不一定是故障**: `P = rho*kT/(mu*m_p)`, 冷区 ρ=1e-6
   与密区 ρ=1.0 的 6 量级 ρ 差会**原样传递**到 pres。判据 = **dens 跳变处数**
   (`|d log10 rho| > 0.5`), 本场景**只有 2 处** (cham|shld 与 samp|cham),
   层间无跳变 (层间 ρ 全 = 1.0, 靠 spec_* 质量分数区分)。
11. ★ **WSL `bash -lc` 会吞 shell 变量与反引号**: 内联 `$OBJ` 展开为**空**
   (导致 `ls /` 而非目标目录), 反引号内容被命令替换吞掉。
   ★ 唯一可靠: **Windows 侧 Write `.sh` → `cp -f` 进 WSL → `sed -i 's/\\r$//'` → `bash`**。
   远端同理: **base64 编码后 `printf | base64 -d > f.sh && bash f.sh`** (规避引号/换行)。
   ★ 另: h5py **无法从 `\\\\wsl$\\` UNC 路径读** (Win32 文件锁 errno 1)
   → 必须先 `cp` 到 `/mnt/e/...` 再读。
"""

# 插到 "## ⚠ 待用户决策的历史遗留" 之前
marker = "## ⚠ 待用户决策的历史遗留"
if marker in t:
    t = t.replace(marker, NEW.strip() + "\n\n---\n\n" + marker, 1)
else:
    t += "\n" + NEW

# 更新日期与轮次
t = re.sub(r"最近更新: [^\n]*", "最近更新: 2026-09-12（第六轮 + 第二轮归档/超算核实）", t)

io.open(P, "w", encoding="utf-8").write(t)
print("after:", len(t), "chars")
assert len(t) < 20000, "MEMORY.md 过长"
print("OK")
