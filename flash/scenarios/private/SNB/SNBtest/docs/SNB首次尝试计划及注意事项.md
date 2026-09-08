# SNB 首次尝试计划及注意事项

> SNB (Schurtz–Nicolai–Busquet) 非局域电子热传导特殊场景 — 第一次尝试的计划指导书
>
> 位置: `flash/scenarios/private/SNB/SNBtest/docs/`
> 创建: 2026-08-29 | 状态: 计划稿 (未执行)
> 关联: 热传导模型对比研究 (local Spitzer vs nonlocal SNB)

---

## 1. 目标

在专用修改版 FLASH (FLASHSNB) 中首次运行 SNB 非局域热传导仿真：

1. **基线复现**：原样运行 SNB 自带的 `SNB_1D_laser` 算例，打通
   "专用 FLASH 树 → setup → make → 运行 → SNB 诊断变量输出" 全链路；
2. **结构替换**：把算例初始结构替换为本项目多薄层示踪靶几何
   （与 `layer_tracer_CH_ml` 一致的 cham/shld/samp/tar1/tar2/tar3 分层）；
3. **模型对比**：同一初始结构分别用 常用 FLASH（Spitzer local）与
   FLASHSNB（SNB nonlocal）运行，对比电子温度剖面 —— 热传导模型
   对比研究的直接产出。

## 2. 资源清单（已核实的现状）

| 资源 | 位置 / 内容 | 状态 |
|------|------------|------|
| **专用 FLASH 树** | WSL `~/QC/FLASH/FLASHSNB/FLASH4.8`（完整源码树, 已确认存在） | ★ 仅 SNB 场景可用 |
| **常用 FLASH 树** | WSL `~/QC/FLASH/FLASH4.8`（所有常规场景使用） | ★ 严禁与 SNB 混用 |
| 应用目录 | `src/SNB/SNB_1D_laser/SNB_1D_laser/`（Config + flash.par + 修改的 F90 + 2 张 EOS 表） | 就绪 |
| 修改单元文件 | `src/SNB/f90/{Conductivity.F90, diff_advanceTherm.F90}`（与应用目录内为同一套修改） | 就绪 |
| 运行指令 | `src/SNB/运行指令.txt`（setup/make/mpiexec 三步） | 就绪 |
| 打包备份 | `src/SNB/{SNB_1D_laser.tar, physics.tar, source.tar}` | 原始存档, 勿改动 |

### 2.1 SNB_1D_laser 算例要点（读自 Config / flash.par）

| 项 | 值 | 备注 |
|----|-----|------|
| setup 指令 | `./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=SNB_1D_laser` | `+ug` 含义待核实（原样沿用） |
| 物种 | **cham, tar1, tar2, tar3**（4 个, 无 shld/samp） | 与 layer_tracer_CH_ml 的 6 物种命名部分重叠但**不是同一套配置** |
| 域 | x ∈ [-500, +250] µm（`xmin=-50e-4, xmax=250e-4` cm） | 比本项目常规域大 |
| 网格 | `nblockx=5, lrefine_max=lrefine_min=6`（均匀 6 级） | 理论 res = 750µm/(8×5×2⁵) ≈ **0.586 µm** |
| tmax | 0.8e-9 s | 首次尝试建议先截短（见 §4 P1） |
| 激光 | 单束, `ed_lensX_1=500e-4` cm（域外透镜）, `ed_targetX_1=0` | |
| 腔室 | He, ρ=2.655e-7 g/cm³（1.6 mbar）, **eos_gam**（理想气体!） | 注意: 与本项目 ml 场景的 eos_tab 不同 |
| 靶参数 | `sim_rhoTar1/2/3 = 2.7`（Al 默认值, 未改 CH） | 替换几何时必须改 |
| EOS 表 | CH-BADGER-TOPS-Final / He-BADGER-TOPS-Final（另有 V/Ti 表在 DATAFILES 中备用） | |
| 通量限制 | `diff_eleFlMode="fl_harmonic"`, `diff_eleFlCoef=0.06`, `diff_thetaImplct=1`, 电子导通 `diff_useEleCond=.true.`, 两端 neumann | SNB 对比基线 |
| 边界 | 电子热传导两端 neumann | |

### 2.2 SNB 专属诊断变量（Config 声明, 共 19 个）

`QESH, QEFL, QENL, NELE, MFPE, MFPR, QESX, QESY, GRQX, GRQY, GRAQ, CORQ,
QEXG, QEYG, GRGX, GRGY, GRQG, COGQ`（另 `lase`）

- `QESH/QEFL/QENL`: Shack 实 heat flow / flux-limited / nonlocal 分量对比 —
  **模型对比研究的核心输出**；
- 这些变量**只有加入 `.par` 的 `plot_var_N` 白名单才会出现在 plotfile**
  （参考 flash.par: plot_var_5/6/7 已含 QESH/QESX/QESY; 扩展白名单时防
  "plot_var 陷阱"）；
- SNB 通量计算主要位于修改的 `diff_advanceTherm.F90`（QESH/QENL 标记约 9 处）;
  `Conductivity.F90` 文件头仍是 SpitzerHighZ 原始文档 —— **修改藏在函数体内,
  阅读时勿被文件头注释误导**。

### 2.3 修改文件清单（相对标准 FLASH4.8, 均在应用目录内覆盖）

```
Conductivity.F90               ← 传导单元 (SpitzerHighZ 修改版)
diff_advanceTherm.F90          ← ★ SNB 非局域通量核心计算
Grid_advanceDiffusion.F90      ← 扩散驱动修改
hy_uhd_dataReconstOneStep.F90  ← UHD 重构修改 (4 个)
hy_uhd_DataReconstructNormalDir_PPM.F90
hy_uhd_getRiemannState.F90
hy_uhd_ragelike.F90
Driver_evolveFlash.F90         ← 驱动器修改
Simulation_data/init/initBlock ← 算例自身
```

## 3. ★ 与常用 FLASH 的严格区分（红线, 执行前逐条核对）

| # | 红线 | 核对方法 |
|---|------|---------|
| 1 | SNB 一律使用 `~/QC/FLASH/FLASHSNB/FLASH4.8`；常用场景一律 `~/QC/FLASH/FLASH4.8` | 运行前 `echo $FLASH_HOME` / 脚本内 flash_home 字段 |
| 2 | objdir 命名区分：SNB 一律 `SNB_*` 前缀（如 `SNB_1D_laser`、`SNB_tracer_ml`），且位于 FLASHSNB 树内 | `ls ~/QC/FLASH/FLASHSNB/FLASH4.8/<objdir>` |
| 3 | **禁止**把 SNB 修改的 F90 拷入常用 FLASH 树，也禁止把常用场景文件拷入 FLASHSNB 树（双向污染都会破坏可复现性） | 拷贝前 `pwd` 双确认 |
| 4 | 场景脚本中 `flash_home` **显式写死为 FLASHSNB 路径**（本场景属于"配置即文档"的例外——路径本身是场景定义的一部分, 不算敏感凭据） | 代码 review |
| 5 | 两套树的 setup 产物（objdir）不共用；切换后先 `rm -rf` 对应 objdir 再全新 setup | 编译日志 "Running setup..." |
| 6 | 常用 FLASH 没有 SNB 单元——若误在常用树 setup SNB 算例, 覆盖文件会污染常用树源码（SimulationMain 下残留） | 误操作后立刻恢复: 删除 SimulationMain/SNB_* + git status 检查常用树 |
| 7 | WSL 内备份 FLASHSNB 树的原始状态（`tar -czf ~/QC/FLASHSNB_backup_$(date).tar.gz ~/QC/FLASH/FLASHSNB`）在首次改动前完成 | 备份文件存在 |

## 4. 首次尝试计划（P0–P4 分阶段, 每阶段有明确通过判据）

### P0 — 环境核查（不编译, ~10 min）

1. 确认 FLASHSNB 树完整：`ls ~/QC/FLASH/FLASHSNB/FLASH4.8/{setup,bin,source,...}`；
2. 按红线 #7 做原始状态备份；
3. 记录 FLASHSNB 版本信息（有无 git / README / 版本文件, `bin/setup_version`）；
4. 确认与常用树无路径交叉（`readlink -f` 两套树的物理路径）。

**通过判据**: 备份存在 + 树完整 + 路径记录入本文档附录。

### P1 — 基线复现（原样运行, 零修改）

1. 在 WSL: `cd ~/QC/FLASH/FLASHSNB/FLASH4.8 && cp -r <SNB_1D_laser 应用目录> ./`（或按运行指令直接在树内 setup）；
2. 原样执行运行指令的三步（setup → make -j4 → mpiexec -n 4），
   **唯一修改: 先临时把 flash.par 的 `tmax` 截短为 `1.0e-11`（极短验证）**，
   `plotFileIntervalTime` 相应调小保证至少 2 帧；
3. 通过判据:
   - exit 0, 日志含 "exiting: reached max SimTime"；
   - plotfile 含 SNB 诊断变量（QESH/QESX/QESY/MFPE…, 用 h5py 键列表核对）；
   - tar1/tar2/tar3 物种变量存在（防 plot_var 陷阱）。
4. 产物按 run_id 规范归档（见 §5）。

**风险预案**: 编译失败 → 逐条记录 gfortran 错误（可能与常用树编译器版本差异有关，
FLASHSNB 原始开发环境未必是当前 gfortran）；先试 `make` 单线程定位。

### P2 — 结构替换（本项目多薄层几何移植）

1. 以 `layer_tracer_CH_ml` 的 6 物种分层为蓝本, 重写 SNB_1D_laser 的
   `Simulation_initBlock.F90`（保持 SNB 修改文件**一个字节都不动**）；
2. 物种集二选一（**首次建议 A**）:
   - A. 沿用 SNB 自带 4 物种（cham,tar1,tar2,tar3）, 把 ml 场景的
     shld/samp 物质映射进 tar 通道 —— 最小改动, 与基线可比性最强;
   - B. 扩成 6 物种（cham,shld,samp,tar1,tar2,tar3）—— 需同步改 setup
     species= 列表、Config、flash.par 的 plot_var 白名单（陷阱高发）;
3. 域/网格参数迁移: ml 场景域 [-400,+100] µm 换算入 SNB par
   （xmin/xmax/nblockx/lrefine 按分辨率需求重算, 用 gen_par 的分辨率注释公式核对）;
4. 材料参数替换: `sim_rhoTar*` 2.7→1.0 (CH), cham `eos_gam`→`eos_tab`
   （或保留 gam 并记录差异）; V 层是否引入取决于物种方案（A 方案下 V 层
   暂以 CH 或 tar 通道近似, 明确记录为已知差异）;
5. 重新极短验证, 判据同 P1 + 初始密度/物种分布图与 layer_tracer_CH_ml
   对齐（物种分布图逐边核对）。

### P3 — local vs SNB 对比运行（研究产出）

1. 同一初始结构（P2 产物）:
   - run A: 常用 FLASH + layer_tracer_CH_ml 生成器（Spitzer local, fl_harmonic 0.06）;
   - run B: FLASHSNB + SNB（diff_eleFlMode 等 SNB 配置）;
2. 统一 tmax 与输出频率, run_id 归档;
3. 对比分析: `tele(x,t)` 剖面差、热流前排位置、QESH vs QEFL vs QENL;
4. 产出对比报告（图 + 结论）至 `SNBtest/docs/`。

### P4 — 归档与文档

- run_id 归档 + par 快照（`*.par.used`）+ 本计划文档回填"实际结果"栏;
- 提炼 SNB 场景生成器化方案（SNB 专用 input_gen 变体或模板参数化）——仅作
  后续计划, 不在本轮实现。

## 5. run_id 与产物归档规范（全场景统一）

- run_id 采用 **6 位零填充**（`run_000001`），预留大规模仿真扩展;
- 新 run_id = 扫描输出目录现有 `run_NNNNNN*` 的最大 id + 1（工具函数
  `flash.scenarios.runner.allocate_run_id`，自动读取、无需手工记数）;
- 每次运行的**输入文件快照**存 `flash_input/run_NNNNNN/`（不同 id 的
  par/Config 可能不同，与 flash_output 的分 id 布局对称）;
- 输出存 `flash_output/outputfiles/run_NNNNNN_<标签>/`，分析图存
  `flash_output/plots/run_NNNNNN_<标签>/`，par 快照 `*.par.used` 与输出同目录。

## 6. 已知风险与开放问题

| # | 风险/问题 | 缓解 |
|---|----------|------|
| 1 | `+ug` setup 标志含义未核实 | P1 原样沿用; 若 setup 报未知参数, 从 FLASHSNB 的 bin/setup_shortcuts.txt 查定义 |
| 2 | FLASHSNB 的编译环境与当前 WSL gfortran 版本兼容性 | P1 单线程 make 定位; 必要时在 Makefile.h 锁旧标准 |
| 3 | `Conductivity.F90` 文件头文档为 SpitzerHighZ 原文, 实际函数体已改 | 阅读以代码为准; 对比标准 FLASH4.8 同名文件 diff |
| 4 | SNB 算例 cham 用 eos_gam（理想气体）, 密度 2.655e-7 与本项目 1e-6 不同 | 结构替换时显式决策并记录; 两种都先跑通再统一 |
| 5 | SNB 诊断变量 19 个 + 物种变量可能超出 plot_var 白名单容量/顺序 | 白名单按 §2.2 重排; plot_var 陷阱复检 |
| 6 | 大域 (750 µm) + 均匀 6 级网格分辨率 0.586 µm, 解析 0.1 µm 薄层不足 | P2 结构替换时重算 lrefine（需要 res ≤ 0.03 µm → lrefine ≥ 9, 或加大薄层厚度） |
| 7 | SNB 计算量显著大于局部传导（多调和分量迭代） | tmax 分段推进, 先 1e-11 → 1e-10 → 1e-9 |

## 7. 执行记录（回填区）

| 日期 | 阶段 | 结果 | 备注 |
|------|------|------|------|
| （待填） | | | |
