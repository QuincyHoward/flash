# SandwichTxN 双端执行统计报告（WSL vs 超算）

- 日期: 2026-10-31 21:07–21:40 (CST)
- 场景: `sandwich_txn` — CH(2×100 µm)/Si(1 µm)/He 三明治靶, 超高斯脉冲 3.14e14 W/cm² @1.0 ns, tmax = 1.8 ns, lrefine_max = 10
- 执行载体: ① 本地 WSL2（引擎 `--mode wsl`）; ② 国家超算 v5_192 分区（SSH 提交, 作业 **4935059**）
- 关联历史作业: 4932538（2026-10-30, 同场景首次超算运行, 11m48s）

---

## 1. 执行环境对比

| 项目 | 本地 WSL2 | 超算 v5_192 |
|---|---|---|
| 宿主 | Windows + WSL2 (24 逻辑核) | 计算节点 48 核 / 2 路 / 187 GB RAM |
| 可用内存 | 11.9 GiB（WSL 上限） | 187 GB（整节点独占） |
| MPI | OpenMPI (`/usr/bin/mpirun`), 4 rank | Intel 2018 MPI + `srun`, 4 rank |
| 编译 | make -j4（指纹缓存命中, 秒级增量） | make -j4（作业内全新编译, 91 s 含 setup） |
| 工作盘 | /mnt/e（9P 跨文件系统, 慢） | 节点本地 /tmp（tmpfs）+ 共享并行盘归档 |
| 提交方式 | `sandwich_txn.py run --mode wsl --nproc 4 --timeout 7200` | `python -m flash.scenarios.core.entry.cli submit sandwich_txn --run-id 000002` |

## 2. WSL 运行统计（runs/000001）

- 引擎总耗时 **5 m 55 s**（含输入复制/编译检查/FLASH 运行/H5 插值后处理）
- FLASH 运行段: 21:14:25 → 21:19:58 ≈ **5 m 35 s**，22002 步推进至 1.8 ns
- 速度: **≈ 65.7 步/s**（4 rank 合计）
- CPU: 4× flash4 全程稳定 ~400%（即每 rank 单核打满，无超线程增益）
- 内存: 4 rank 总 RSS ≈ **245–247 MiB**（约 61 MiB/rank）；WSL 系统内存峰值仅 ~700 MiB / 11.9 GiB
- 磁盘: 运行目录合计 **190 MB**（sim_output 222 个 chk + plt；每 chk ≈ 0.86 MB）
- 资源采样: `runs/000001/wsl_stats.csv`（10 s 间隔，37 样本，`scripts/collect_wsl_stats.sh` 生成）
- 结果: success=True, n_chk=222, result.h5 生成正常

## 3. 超算运行统计（作业 4935059）

### 3.1 作业时间线（sacct）

| 阶段 | 时刻/时长 | 说明 |
|---|---|---|
| Submit → Start | 21:22:06 → 21:22:06 | **排队 0 s**（274 idle 节点，即提即跑） |
| stage+setup+make | 91 s | make -j4 全新编译（1550 .o） |
| flash4 (srun .0 步) | 21:23:37 → 21:33:45 = **10 m 08 s** | 21910 步至 1.8 ns |
| 归档 | ~1 s | 221 个 chk → 共享盘 flash_output/sandwich_txn/000002 |
| 总 Elapsed | **11 m 40 s**（Timelimit 02:00:00，占用 9.7%） | COMPLETED |

### 3.2 节点资源消耗（sacct 记账）

| 指标 | 数值 | 备注 |
|---|---|---|
| NNodes / AllocCPUS | 1 / **48** | **整节点分配**（分区 SelectTypeParameters=NONE，4 task 亦占满 48 核） |
| flash4 步 TotalCPU | 40:29.194 | ÷ Elapsed 608 s ⇒ 实际平均 **4.0 核忙**（每 rank 单核） |
| **节点 CPU 利用率** | **40:29 / (48×10:08) ≈ 8.3%** | 44 核全程空转 —— 核心浪费点 |
| batch 步 TotalCPU | 4:12.279 | 编译段（make -j4） |
| MaxRSS (flash4) | **65,252 KB/rank ≈ 63.7 MiB** | ×4 rank ≈ 255 MiB，内存极小 |
| MaxRSS (batch/make) | 475,884 KB ≈ 465 MiB | make -j4 峰值，远低于 187 GB |
| MaxDiskRead | 2.91 GB（batch，编译读源）/ 25.5 MB（flash4） | 编译期为主 |
| MaxDiskWrite | ~150 MB（batch）/ 122 MB/rank（flash4） | chk 写 tmpfs 后归档 |
| 归档产物 | 221 文件 / **196 MB** | 共享并行盘 |

### 3.3 双端对比要点

| 指标 | WSL (4 rank) | 超算 (4 rank) | 比值 |
|---|---|---|---|
| FLASH 段墙钟 | 5 m 35 s | 10 m 08 s | WSL 快 **1.82×** |
| 步速 | 65.7 步/s | 36.0 步/s | — |
| 每 rank 内存 | ~61 MiB | 63.7 MiB | 一致 |
| 4 rank 扩展效率 | ~100%（400%/4） | ~100%（40:29 CPU/608 s = 4.0） | 均为理想线性 |
| 物理终态 | 1.8 ns @ 22002 步, chk 0221 | 1.8 ns @ 21910 步, chk 0220 | 一致（步数差异源于输出间隔取整） |

结论:
1. **单 rank 计算性能**: 本地桌面 CPU 明显快于超算节点（1.8×），超算优势在并发吞吐而非单点速度。
2. **该 1D 场景是"小内存、单核级"负载**: 每 rank ~64 MiB、1 核，节点级 48 核/187 GB 严重过剩。
3. **当前提交模式的浪费**: 每作业独占 48 核仅用 4 核（利用率 8.3%）；若并行提交多个此类任务，必须打包复用同一节点。
4. 编译阶段（91 s）占作业总时长 13%，批量场景可复用同一二进制进一步压缩。

## 4. 产物与数据索引

- WSL 运行: `runs/000001/`（sim_output 222 chk、database、wsl_stats.csv）
- 超算产物: `$HOME/PhySimX/.../flash_sim/flash_output/sandwich_txn/000002`（221 chk, 196 MB，未下载）
- 作业日志: `flash_logs/sandwich_txn/000002/flash_sandwich_txn_4935059.out`
- 采样脚本: `../scripts/collect_wsl_stats.sh`
- 提速方案: 见同目录《超算并行提速方案计划.md》
