# SNBOneCH_ml — OneCH_ml 几何/材料 + SNB 非局域热传导模型

> 创建：2026-09-08
> 定位：**local vs nonlocal 热输运直接对照场景** — 几何结构、8 物种 12 区分层、
> 材料表、激光脉冲与 `tracer/OneCH_ml` **严格同源**（经 `import build_species_defs`
> 复用，零手抄差异），唯一物理差异是电子热传导由 local (Spitzer + flux limiter)
> 换为 **SNB（Schurtz–Nicolaï–Busquet）非局域模型**。两场景输出可直接对比。

## 1. 快速使用

```
cd <flash 包根目录>
# 首跑验证（场景快速验证规范: tmax=1e-11 冒烟）
python -m flash.scenarios.private.tracer.SNB.SNBOneCH_ml.SNBOneCH_ml --tmax 1.0e-11
# 正式物理运行（规范 tmax 1.6e-9）
python -m flash.scenarios.private.tracer.SNB.SNBOneCH_ml.SNBOneCH_ml
# 只生成 FLASHSNB 输入文件
python -m flash.scenarios.private.tracer.SNB.SNBOneCH_ml.SNBOneCH_ml --generate-only
# 复用已编译 flash4（改 par 后快速重跑）
python -m flash.scenarios.private.tracer.SNB.SNBOneCH_ml.SNBOneCH_ml \
    --tmax 1.0e-11 --skip-setup --skip-make
```

流水线：生成输入 → 部署单元到 FLASHSNB → setup → make（首编 10~30 min）→
`mpiexec -n 4 ./flash4` → 收集输出到 `flash_output/`（WSL 侧用后即清）→ 快速分析
（密度剖面 + SNB 变量非零检查）。

## 2. 生成的 FLASHSNB 输入文件（flash_input/）

| 文件 | 说明 |
|---|---|
| `snbonech_ml.par` | 运行参数：CH_FLASH_PAR 规范基线（82 点激光脉冲/MGD 10 群/材料）+ SNB 覆写 |
| `Config` | 8 物种注册 + 几何/材料 PARAMETER + **18 个 SNB VARIABLE**（QESH/QENL/GRQX/CORQ/MFPE...） |
| `Makefile` | `Simulation += Simulation_data.o mgd_qesh.o` |
| `Simulation_data.F90` / `Simulation_init.F90` | 生成器产出（同 OneCH_ml） |
| `Simulation_initBlock.F90` | 8 物种 12 区分层（参数表达式控制几何，只改 .par 即可改几何） |
| `CH-QC-1-001.cn4` / `He-BADGER-TOPS-Final.cn4` | EOS/不透明度表（多级查找复制） |
| `run_flash.sh` | 手动一键流水线（与 py 驱动同逻辑；环境变量 `SKIP_SETUP/SKIP_MAKE/SKIP_DEPLOY/TMAX/NPROC`） |
| `pre_diag_laser_pulse.png` / `pre_diag_initial_density.png` | 预诊断图 |

**SNB 物理覆盖文件（9 个 .F90，部署时从 FLASHSNB 的 `SNB_1D_laser` 单元原样复制，
不入库 — License §3）**：`diff_advanceTherm.F90`（SNB 群分辨热流）、`mgd_qesh.F90`
（多群 SH 热流权重）、`Conductivity.F90`（增强泛型）、`Driver_evolveFlash.F90`、
`Grid_advanceDiffusion.F90`、`hy_uhd_DataReconstructNormalDir_PPM.F90`、
`hy_uhd_dataReconstOneStep.F90`、`hy_uhd_getRiemannState.F90`、`hy_uhd_ragelike.F90`。
机制：FLASH setup 的 Simulation 单元**后置覆盖**同名单 physics 文件；
`mgd_qesh.o` 无同名 physics 文件，经单元 Makefile 显式加入。
已核查 9 个文件均无 `sim_`/`Simulation_data` 引用（与场景层解耦，物种无关）。

## 3. 关键设计决策（实测依据）

### 3.1 必须用 AMR，禁用 +ug
t001（`SNB_1D_laser`）的 chk 输出实测：`+ug` 模式下 FLASH 只建 **iProcs 块
level-1 均匀网格**（par 的 `nblockx=5`/`lrefine_max=6` 被无视，4 块 × 8 格，
dx = 域宽/(iProcs·nxb) ≈ 9.4 µm）。该分辨率无法解析 OneCH_ml 的 0.1 µm
示踪薄层。故本场景走 **AMR 模式**（与 OneCH_ml 完全一致）：
`nblockx=8, nxb=16, lrefine_max=9, lrefine_min_init=9` → 初始均匀 2048 块，
`dx = 0.05/(16·8·2^8) ≈ 1.53e-6 cm ≈ 0.0153 µm`，允许 deref 至 `lrefine_min=1`。

### 3.2 SNB 运行参数（t001 SNB 基线）

| 参数 | 值 | 说明 |
|---|---|---|
| `useDIffuseTherm` | `.true.` | Diffuse 单元热传导开关（SNB 必需；注意 FLASH 参数名大写 I） |
| `diff_eleFlMode` / `diff_eleFlCoef` | `fl_harmonic` / `0.06` | t001 SNB 基线（OneCH_ml 用 fl_minmax/0.08，勿混淆） |
| `cfl` | `0.2` | t001 SNB 基线（OneCH_ml 为 0.4） |
| `use_3dFullCTU` / `eos_maxNewton` | `.true.` / `5000` | t001 SNB 基线 |
| `iProcs` | 4 | = `mpiexec -n`；须 ≤ nblockx=8（default_nprocs 可能给 11，已显式固定 4） |
| plot_var 17–24 | QESH/QESX/QESY/GRQX/GRAQ/CORQ/MFPE/QENL | SNB 诊断输出（QENL=非局域热流，QESH=SH 热流，对比核心量） |

### 3.3 部署/编译防御（承 t001 经验）
1. 树级 physics 补丁（`Diffuse_computeDt.F90`、`hy_uhd_getFaceFlux.F90`）缺失时
   从 `SNB/SNBtest/Test/t001/source_patches/` 自动补齐（幂等）。
2. 编译竞态防御：先单独 `make hy_slopeLimiters.o Conductivity_interface.o
   Conductivity_fullState.o` 再 `-j4` 全量编译。
3. objdir 内 `mgd_qesh.F90` 符号链接兜底（单元完整时 setup 通常自动处理）。

## 4. 验证记录

### 4.1 首跑验证（tmax=1e-11，2026-09-08）

| 项目 | 结果 |
|---|---|
| 输入生成 | ✅ 9 项产物（见 §2） |
| 单元部署 | ✅ `source/Simulation/SimulationMain/SNBOneCH_ml/`（5 件套 + 2 表 + 9 覆盖文件） |
| setup（AMR 模式） | ✅ objdir 生成 |
| 编译 | ✅ flash4 15.7MB（预编关键模块 + `-j4`，约 6 min） |
| 运行 | ✅ `RUN_EXIT=0` + "reached max SimTime"（tmax=1e-11） |
| SNB 变量 | ✅ QENL 8.99e17 / CORQ 5.80e17 / MFPE 8.54e7 非零（QESH/GRQX 全零符合预期 — 82 段脉冲 t=1e-11 时功率≈0，无温度梯度） |
| 物理量 | ✅ dens 1e-6~1.003 分层正确、tele 98~3357 K（启动瞬态残余，无爆炸） |

### 4.2 调试记录（Root Cause → Fix）

**现象**：首次运行 step 66（t≈4.9e-12）`DRIVER_ABORT: Negative 3T internal energy`，
dt 崩至 1e-16 下限；日志显示 hypre 扩散求解自 step 33 起 500 次迭代不收敛，
He 腔（species 1, rho≈1e-6）温度飞至 3.8e13 K **超出 EOS 表 Tmax**。

**根因**：He|CH 界面 6 个数量级密度跳变 + 0.1µm 薄层的细网格（dx=0.0153µm，
初始全域 lrefine 9）下，启动瞬态（初始 290 K 等温、激光功率≈0）期间 dt 按
×1.1/步增长过快 → 扩散/传导矩阵病态发散 → 温度爆表 → 负内能。
（OneCH_ml 同几何用 local SH 可承受该 dt 增长；SNB 版不能。）

**修正**（相对 OneCH_ml 基线的偏离，已固化到生成器 config_constants）：

| 参数 | OneCH_ml | SNBOneCH_ml | 理由 |
|---|---|---|---|
| `tstep_change_factor` | 1.1 | **1.05** | 慢化启动瞬态 |
| `dtmax` | 1.65e-9 | **2.0e-14** | 封顶 dt，瞬态期限制能量注入率 |

修正后一次通过。正式物理运行（tmax=1.6e-9）时 dtmax=2e-14 意味着 ≥8 万步，
若时长不可接受可试验放宽 dtmax（如 1e-13）+ 保持 tstep 1.05，但需重验瞬态稳定性。

### 4.3 过程工程坑（已修，供复用）

1. **wsl 双层 bash 展开**：`wsl -d X bash -lc "<cmd>"` 的命令会被外层 bash 先展开
   `$var`/`$?`/`$(...)` → shell 循环变量为空、`RUN_EXIT=$?` 恒为 0。
   对策：内联命令一律 Python 端展开（显式逐文件 cp 链 + if/else 落盘标记）。
2. **make 成败判定**：make 输出含 "error" 字样的源文件名会让 `grep -i error` 误报
   （flash4 实际已生成）。对策：`if make ...; then echo MAKE_OK; fi` + flash4 存在性。
3. `_T001_DIR` 相对路径恰好 3 层 parent 到 `private/`（多一层到 scenarios/ 导致
   补丁归档查不到）。


### 4.4 三机并行速度对比 + 一致性检验（2026-09-08）

核数探测（`--probe-cores 4,8,16,32 --probe-tmax 2e-12`）→ 各机最优核数 → 正式跑。
⚠️ **tmax=1e-10 不可达**：三机均在 t≈2.6~8.9e-11 触发负 3T 内能中止
（dt 先钉在 dtmax=2e-14，随后单步崩至 1e-16；触发时刻随 MPI 分解变化，
cfl=0.1 试跑无效 → 时间确定性物理失稳，SNB+细网格临界稳定问题，待专项处理）。
速度对比改用已验证稳定的 **tmax=1e-11**（三机全部 RUN_EXIT=0）：

| 机器 | 核数（探测推荐） | 墙钟 | 相对速度 |
|------|------|------|------|
| WSL (Ubuntu-22.04) | 4（4.0s） | **39.8 s** | 1.00x |
| NC-E (scfa2696, v5_192) | 8（9.1s） | 59.9 s | 0.66x |
| BSCC-T6 (sch0348, v6_384) | 16（7.1s） | 84.3 s | 0.47x |

一致性（forced plt @ t=1.0012e-11，dens/tele/tion/qenl 逐点插值 rel diff）：
主体解 median ≤ 1e-6 完全一致；max 偏差集中于界面/临界面尖峰格点
（dens ≤2.8%、tion ≤5%、tele ≤19%、qenl 尖峰区 O(1)），源自 AMR 分块
模式随机器不同 + WSL(oneAPI) vs HPC(gcc9.3) 编译器数学差异。
叠加剖面图 `flash_output/cross_machine_consistency.png`；
对比脚本 `compare_machines.py`（`python compare_machines.py --plot`）。


### 4.5 tele +50µm 凹陷诊断 + 初始温度实验（2026-09-08）

- 凹陷非初始条件错误：初始全场均匀 290.11375K；系 t∈(0,1e-11] 内 CH|He 界面
  （x=56.2µm，第一个 He 格点）单格点 tele 下陷（290→181K，tion 微升）——
  6 量级密度跳变界面电子导热通量发散伪影。
- `--t-init 3500` 均匀初温实验：t=1.86e-12 即中止（比 290K 基线 8.9e-11 更早）——
  均匀升温放大界面初始压强跳变 ×12 → 启动瞬态更强。基线保持 290.11375K。

### 4.6 t001 长时间对照 + cn4 换表实验（2026-09-08）

- **t001（SNB_1D_laser）@ tmax=1e-10 与 2e-10 均正常完成**（无负内能；11 次 hypre
  非收敛均恢复）→ 失稳为 SNBOneCH_ml 配置特有，非 SNB 模型通病。
- **★ cn4 表头发现**：CH-QC-1-001 温度网格下限 2.0 eV (~23,200 K)，室温初值
  0.025 eV 在表外（EOS 钳位）；CH/He-BADGER 下限 0.01 eV 覆盖室温；两族均 10 群。
- **1e-10 实验矩阵**（均负内能中止，时刻随配置漂移）：
  QC+lrefine9 → 8.90e-11（最稳基线）；QC+cfl0.1 → 8.91e-11（同一时刻）；
  QC+Tinit3500K → 1.86e-12；BADGER+l9 → 4.39e-12；BADGER+l7 → 2.30e-11；
  BADGER+l7+dtmax2e-12 → 1.51e-11（启动发散，证明 dtmax=2e-14 启动必需）；
  BADGER+l8 → 7.9e-13。
- **结论**：BADGER 物理上必要（室温覆盖）但当前几何启动更脆（QC 钳位客观起阻尼）。
  工作基线保留 QC+lrefine9；`ch_cn4` 已做成 cfg 键一行可切；启用 BADGER 前需先修
  He|CH 界面启动瞬态（密度/压强过渡区或初压平衡）。
## 5. 目录结构

```
SNBOneCH_ml/
├── SNBOneCH_ml.py        # 主脚本（生成 + 部署/编译/运行/收集/分析）
├── README.md             # 本文件
├── flash_input/          # 生成的 FLASHSNB 输入（gitignore 覆盖）
├── flash_output/         # 运行输出（WSL 收集）
└── pipeline_t1e11.log    # 首跑流水线日志
```

### 4.7 +ug 对照实验：SNBOneCH_ml 均匀网格模式 (2026-09-08 晚)

`SNBOneCH_ml.py --ug --nproc N --tmax 1.0e-10`：运行期切换 +ug 均匀网格
（独立 objdir `SNBOneCH_ml_ug_obj` / basenm `snbonechug_`，不动 AMR 构建；
自动换 t001 基线 tstep=1.10 / dtmax=2e-12）。

| 模式 | 网格 | dx | tmax=1e-10 | 备注 |
|------|------|----|-----------|------|
| +ug iProcs=4 | 4 块×16 | 7.81 µm | ✓ reached max SimTime (1.2 s) | — |
| +ug iProcs=16 | 16 块×16 | 1.95 µm | ✓ reached max SimTime (2.0 s) | QENL 1.3e23 非零, 固体平台 [1.4, 56.0] µm 完整, max_dens 1.004 |
| AMR lrefine9 | 2048 块 | 0.0153 µm | ✗ 死于 ≤8.9e-11 | §4.6 实验矩阵 |

**结论：直接证实"SNB 必须 +ug"——同一 ml 几何, +ug 全档稳定而 AMR 必炸。**
注意 +ug 下 0.1 µm 薄层不可分辨 (dx ≥ 1.95 µm), 属场景设计接受的妥协。

附带的坑（已修）：`--nproc` 此前不写入 par iProcs（恒 4），+ug 块数 iProcs
≠ mpiexec -n 时启动即 `Logfile_open io_status=29` + MPI_Abort；现已加
`cfg["nprocs"]=nproc` + `_par_iprocs_ok` 一致性检查。

### 4.8 默认配置改版: +ug 默认 / 0.03µm 一键 (2026-09-08 晚, 用户指令)

SNB 模型默认使用 +ug 均匀网格 (铁律); AMR 降级为 `--amr` 历史基线选项
(独立 objdir `SNBOneCH_ml_obj` / basenm `snbonech_`, tstep1.05/dtmax2e-14)。

**默认一键** (`python SNBOneCH_ml.py`, 全参数有默认值):
- +ug, nxb=128, iProcs=131 → dx = 500µm/(131×128) = **0.0298 µm ≤ 0.03 µm**
  (薄层 0.1µm ≈ 3 格点; 1042 进程 @nxb=16 的等分辨率配置超出 NC-E 192 核,
  大块少进程是唯一同时适配两超算的方案)
- tmax=2.0e-10, tstep_change_factor=1.10, dtmax=2e-12, cfl=0.2, T_init 室温
- objdir `SNBOneCH_ml_ug_obj`, basenm `snbonechug_`

**核数=分辨率耦合 (重要)**: +ug 下 nproc 必须严格等于 iProcs (块数) —
"固定分辨率扫核数"不存在; 核数探测 (`--probe-cores`) 的每个点自洽地对应
各自 dx。HPC 的 -N 节点数现按分区每节点核数自动计算 (`sinfo %c`;
NC-E 48 核/节点 → 131 任务 = -N 3; 硬编码 -N 1 会报
"Requested node configuration is not available")。

**WSL 探测实测** (nxb=128, tmax=2e-10): 4 核 9.8s / 8 核 17.8s /
16 核 59.7s / 24 核 121.7s — **小规模 +ug 问题核越多越慢** (MPI 延迟主导 +
超订), WSL 最优 4 核 (dx≈0.98µm)。注意: 探测前须确认 objdir 是 nxb=128
二进制 (probe 分支见 flash4 存在即跳过重建)。

**三平台 0.03µm 正式探测** (tmax=2e-10, iProcs=131, dx=0.0298µm):

| 平台 | 状态 | WALL_SECONDS | 备注 |
|------|------|--------------|------|
| WSL | ✅ 4 核最优 | 9.8 s (dx0.98µm 档) | 本地无 131 核, 0.03µm 只能上超算 |
| NC-E scfa2696 | ✅ COMPLETED (JobID 4858339, -N 3) | **3501.9 s (58.4 min)** | 首跑 IB 瞬时故障 (rc_verbs retry exceeded, 0 步即死), 原样重试成功; ~5.6 s/步 |
| BSCC sch0348 | ❌ 未完成 (JobID 36201968, -N 2) | 被杀 @3h09m (164 步) | ~42-66 s/步 (慢 ~10 倍); 23:50 被外部 CANCELLED (Timelimit=UNLIMITED); 见 hypre 不收敛警告 + dt 下滑 (oneAPI 编译版失稳前兆) — **0.03µm 生产不可用 BSCC** |

NC-E 数据已收集至 `flash_output/hpc_flash_ssh/` (57 文件, 远端已清理);
BSCC 残留输出已清理 (partial log 留远端 ~/SNB1CH_out_bscc_partial.log)。

### 脚本索引 (2026-09-10 整理: scripts/ 按功能分类, 根目录仅主脚本)

| 位置 | 脚本 | 功能 |
|------|------|------|
| 根 | `SNBOneCH_ml.py` | 场景主脚本: 输入生成 + WSL/HPC 一键运行 + 探测 (`--mode/--tmax/--nproc/--poll-timeout/--probe-cores/--amr`) |
| 根 | `run_full_nce_16ns.py` | NC-E 1.6ns 全流程编排: 冒烟 1e-11 → 正式 1.6e-9 → 调分析脚本 |
| `scripts/collect/` | `fetch_16ns_batch.py` | 全量输出分批收集 (tar 分卷+md5 校验+断点续传; `--batch-size/--start-file`) |
| `scripts/collect/` | `fetch_16ns_all.py` | 整包 tar 收集 (历史方案, 配额受限时用 batch 版) |
| `scripts/monitor/` | `monitor_job.py` | 通用 SLURM 作业低频监控 (`--account/--job/--interval`) |
| `scripts/monitor/` | `monitor_bscc.py` | BSCC 36201968 一次性监控 (历史, 被 monitor_job 取代) |
| `scripts/analysis/` | `plot_snb_profile.py` | 终态密度/Te 剖面 + dt 演化图 → `flash_output/hpc_flash_ssh/analysis/` |
| `scripts/analysis/` | `preview_16ns.py` | 收集等待期抓终态 plt + log 采样预览 |
| `scripts/analysis/` | `compare_machines.py` | 三机 (WSL/NC-E/BSCC) 终态一致性对比 |
| `logs/` | `run_*.log` 等 | 历史运行日志归档 |

注意: `scripts/` 下脚本相对路径均按新位置修正 (上溯 7 级 = 内层 flash,
8 级 = 外层根; `flash_output` = 脚本位置上两级)。

### 关键数据资产 (1.6ns 正式跑, 2026-09-09)

- `flash_output/hpc_flash_ssh/`: **1309 文件 / 11.3GB** (chk 1088 + plt 219 +
  dat + log), md5 逐批校验齐全; `analysis/` 内终态剖面与 dt 演化图。
- `flash_input/`: FLASHSNB 输入全套 21 文件 (Config + 覆盖 F90 ×14 + par +
  cn4 表 ×3 + run 脚本 + 预诊断图 ×2)。
- 仿真参数: 131 核 +ug dx=0.0298µm, tmax=1.6e-9, 433,972 步,
  WALL_SECONDS=64871.1 (18.0h), RUN_EXIT=0。
