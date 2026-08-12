# FLASH 4.8 内置运行时参数参考手册

> **来源**: [FLASH 4.8 Runtime Parameters Documentation](https://flash.rochester.edu/site/flashcode/user_support/rpDoc_4p8.py?submit=rpDoc.txt)  
> **版本**: 2026-06-30 | **目录**: `input_gen/gen_newpara/`  
> **核心要点**: ⭐ 以下参数均为 FLASH 4.8 内置参数，已在其对应模块中通过 `PARAMETER` 注册声明。  
> **使用时仅需在 `.par` 文件中赋值即可，不需要在仿真 `Config` 文件中重复声明，也不需要手动调用 `RuntimeParameters_get`。**

---

## 1. 使用规则

### 1.1 什么参数可直接在 .par 中使用？

FLASH 内置参数由各个物理模块的 `Config` 文件注册，由模块自己的初始化代码读取。只要在 `.par` 文件中赋值，FLASH 启动时会自动捕获。

**只需在 `.par` 中写:**
```ini
lrefine_max = 4
xl_boundary_type = "outflow"
cfl = 0.4
```

**不需要在仿真 `Config` 中:**
```fortran
PARAMETER lrefine_max INTEGER 1   ← ❌ 重复声明 (FLASH 已有的!)
```

**不需要在 `Simulation_init.F90` 中:**
```fortran
call RuntimeParameters_get("lrefine_max", lrefine_max)   ← ❌ (这些由模块自己读取)
```

### 1.2 边界: 自定义参数 vs 内置参数

| 特性 | 自定义参数 (`sim_*`) | 内置参数 |
|------|---------------------|---------|
| 注册位置 | 仿真 `Config` (`PARAMETER ...`) | FLASH 源码自带 `Config` |
| 读取方式 | `Simulation_init.F90` 中手动 `RuntimeParameters_get` | 各模块初始化代码自动读取 |
| 文件位置 | 仿真目录 (`QC/MySim/Config`) | FLASH 源码各模块目录 |
| 命名惯例 | `sim_*` 前缀 | 无统一前缀 (按功能命名) |
| 修改需要 | 全部 5 步流程 | 仅改 `.par` 文件 |

### 1.3 参数组织方式

本文档按 FLASH 源码单元 (Unit) 组织，每个参数给出:
- **名称** — 在 `.par` 中使用的参数名
- **类型** — BOOLEAN / INTEGER / REAL / STRING
- **默认值** — 不设置时的默认行为
- **描述** — 功能说明
- **常用场景** — 在 LaserSlab 仿真中是否需要修改

---

## 2. Driver/DriverMain — 时间步进与并行控制

### 2.1 时间步进参数

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `tinitial` | REAL | 0.0 | 初始仿真时间 | ⭐ 一般不改 |
| `tmax` | REAL | 0.2 | 最大仿真时间 (秒) | ⭐ **必须设置** (如 1e-9) |
| `dtinit` | REAL | 1.0e-10 | 初始时间步长 | ⭐ 建议设 1.0e-15 |
| `dtmax` | REAL | 1.0e5 | 最大时间步长 | ⭐ 建议设 1.0e-12 |
| `dtmin` | REAL | 1.0e-10 | 最小时间步长 | ⭐ 一般不改 |
| `nbegin` | INTEGER | 1 | 第一时间步编号 | 一般不改 |
| `nend` | INTEGER | 100 | 最大时间步数 | ⭐ **必须设置** (如 100000) |
| `tstep_change_factor` | REAL | 2.0 | dt 增长因子 (每步乘以此值直到 CFL 限制) | 一般不改 |
| `dr_tstepSlowStartFactor` | REAL | 0.1 | 初始 dt = CFL_dt × 此因子 | 一般不改 |
| `dr_shortenLastStepBeforeTMax` | BOOLEAN | FALSE | TRUE = 缩短最后一步避免超过 tmax | ⭐ 建议设为 TRUE |
| `dr_dtMinContinue` | REAL | 0.0 | 允许继续的最小 dt | 一般不改 |
| `dr_dtMinBelowAction` | INTEGER | 1 | dt 过小时的行动: 0=立即中止, 1=写检查点后中止 | 一般不改 |
| `dr_printTStepLoc` | BOOLEAN | TRUE | 打印时间步信息 | 一般不改 |
| `dr_abortPause` | INTEGER | 2 | 异常中止前休眠秒数 | 一般不改 |

### 2.2 STS (超时间步进) 参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `useSTS` | BOOLEAN | FALSE | 使用超时间步进算法 |
| `useSTSforDiffusion` | BOOLEAN | FALSE | 用 STS 加速扩散时间推进 |
| `nstepTotalSTS` | INTEGER | 5 | STS 总步数 |
| `nuSTS` | REAL | 0.1 | STS 稳定性参数 nu |
| `allowDtSTSDominate` | BOOLEAN | FALSE | 允许 dt_STS > dt_Hydro |

### 2.3 正定时间步长限制器

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `dr_usePosdefComputeDt` | BOOLEAN | FALSE | 开启正定时间步长限制器 |
| `dr_numPosdefVars` | INTEGER | 4 | 正定变量数量 (0-4) |
| `dr_posdefDtFactor` | REAL | 1.0 | 缩放因子 (-1 = 使用 CFL 因子) |
| `dr_posdefVar_1` ~ `_4` | STRING | "none" | 正定变量名 |

### 2.4 MPI 并行参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `iProcs` | INTEGER | 1 | i 方向进程数 |
| `jProcs` | INTEGER | 1 | j 方向进程数 |
| `kProcs` | INTEGER | 1 | k 方向进程数 |
| `meshCopyCount` | INTEGER | 1 | 完整计算网格副本数 |
| `eachProcWritesOwnAbortLog` | BOOLEAN | FALSE | 每进程是否写自己的中止日志 |
| `wall_clock_time_limit` | REAL | 604800 | 挂钟时间限制 (秒, -1=无限制) |

### 2.5 重启参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `restart` | BOOLEAN | FALSE | 是否为重启运行 |
| `initializeParticleAtRestart` | BOOLEAN | false | 重启时重新初始化粒子 |

### 2.6 其他

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sweepOrder` | INTEGER | 123 | 方向扫描顺序 (如 123,132,213,...) |
| `zInitial` | REAL | -1.0 | 初始红移 (<0 表示未使用) |
| `zFinal` | REAL | 0.0 | 最终红移 |

---

## 3. Grid/GridMain — 网格与几何

### 3.1 几何参数

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `geometry` | STRING | "cartesian" | 网格几何: cartesian/polar/cylindrical/spherical | ⭐ 设为 "cartesian" |
| `geometryOverride` | BOOLEAN | FALSE | 绕过几何一致性检查 | 调试用 |
| `unbiased_geometry` | BOOLEAN | FALSE | 移除浮点偏差 (未在 FLASH3 实现) | 不用 |

### 3.2 边界条件

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `xl_boundary_type` | STRING | "periodic" | x 方向左边界 | ⭐ 设为 "outflow" |
| `xr_boundary_type` | STRING | "periodic" | x 方向右边界 | ⭐ 设为 "outflow" |
| `yl_boundary_type` | STRING | "periodic" | y 方向下边界 | 1D 忽略 |
| `yr_boundary_type` | STRING | "periodic" | y 方向上边界 | 1D 忽略 |
| `zl_boundary_type` | STRING | "periodic" | z 方向下边界 | 1D 忽略 |
| `zr_boundary_type` | STRING | "periodic" | z 方向上边界 | 1D 忽略 |
| `bndPriorityOne` | INTEGER | 1 | 角点边界最高优先级方向 | 一般不改 |
| `bndPriorityTwo` | INTEGER | 2 | 第二优先级 | 一般不改 |
| `bndPriorityThree` | INTEGER | 3 | 最低优先级 | 一般不改 |
| `gr_bcEnableApplyMixedGds` | BOOLEAN | TRUE | 启用混合 GDS 边界接口 | 一般不改 |

### 3.3 物理域

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `xmin` | REAL | 0.0 | x 方向下界 | ⭐ **必须设置** |
| `xmax` | REAL | 1.0 | x 方向上界 | ⭐ **必须设置** |
| `ymin` | REAL | 0.0 | y 方向下界 | 2D/3D 需要 |
| `ymax` | REAL | 1.0 | y 方向上界 | 2D/3D 需要 |
| `zmin` | REAL | 0.0 | z 方向下界 | 3D 需要 |
| `zmax` | REAL | 1.0 | z 方向上界 | 3D 需要 |

### 3.4 EOS 模式

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `eosMode` | STRING | "dens_ie_recal_gather" | EOS 操作模式 | ⭐ 3T 用此默认值 |
| `eosModeInit` | STRING | "dens_ie" | 初始化 EOS 模式 | ⭐ 用 "dens_ie" |

> **EOS 模式可选值**: "dens_ie", "dens_pres", "dens_temp", "dens_ie_all", "dens_ie_scatter", "dens_ie_gather", "dens_ie_sele_gather", "dens_temp_equi", "dens_temp_all", "dens_temp_gather", "dens_ie_recal_gather", "dens_ie_mat_gather_pradscale", "eos_nop"

### 3.5 小量截止值

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `smalle` | REAL | 1.0e-10 | 能量截止值 |
| `smallx` | REAL | 1.0e-10 | 丰度截止值 |
| `small` | REAL | 1.0e-10 | 通用截止值 |
| `smlrho` | REAL | 1.0e-10 | 密度截止值 |
| `smallp` | REAL | 1.0e-10 | 压力截止值 |
| `smallt` | REAL | 1.0e-10 | 温度截止值 |
| `smallu` | REAL | 1.0e-10 | 速度截止值 |

### 3.6 Paramesh AMR 参数 — 细化控制

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `nblockx` | INTEGER | 1 | x 方向初始 block 数 | ⭐ 设 4-8 |
| `nblocky` | INTEGER | 1 | y 方向初始 block 数 | 2D/3D 需要 |
| `nblockz` | INTEGER | 1 | z 方向初始 block 数 | 3D 需要 |
| `lrefine_min` | INTEGER | 1 | 最小 AMR 细化级别 | ⭐ 设 1 |
| `lrefine_min_init` | INTEGER | 1 | 初始化最小细化级别 | 一般不改 |
| `lrefine_max` | INTEGER | 1 | 最大 AMR 细化级别 | ⭐ **必须设置** (3-6) |
| `lrefine_del` | INTEGER | 0 | 重启时减少细化级别数 | 一般不改 |
| `nrefs` | INTEGER | 2 | 每 nrefs 步细化/粗化一次 | ⭐ 一般不改 |
| `refine_var_1` ~ `_4` | STRING | "none" | 细化判据变量名 | ⭐ 设 "dens" 或 "tele" |
| `refine_cutoff_1` ~ `_4` | REAL | 0.8 | 细化阈值 | 一般不改 |
| `derefine_cutoff_1` ~ `_4` | REAL | 0.2 | 粗化阈值 | 一般不改 |
| `refine_filter_1` ~ `_4` | REAL | 0.01 | 防发散 filter | 一般不改 |
| `refine_var_count` | INTEGER | 4 | 最大细化变量数 | 一般不改 |
| `refine_on_particle_count` | BOOLEAN | FALSE | 粒子数作为细化标准 | 一般不改 |
| `max_particles_per_blk` | INTEGER | 100 | 块最大粒子数 (超出则细化) | 粒子仿真用 |
| `min_particles_per_blk` | INTEGER | 1 | 块最小粒子数 (低于则粗化) | 粒子仿真用 |
| `x_refine_center` | REAL | 0.0 | 基于距离细化的中心 x | 一般不改 |
| `y_refine_center` | REAL | 0.0 | 基于距离细化的中心 y | 一般不改 |
| `z_refine_center` | REAL | 0.0 | 基于距离细化的中心 z | 一般不改 |
| `gr_lrefineMaxRedDoByTime` | BOOLEAN | FALSE | 随时间降低有效 lrefine_max | 一般不改 |
| `gr_lrefineMaxRedDoByLogR` | BOOLEAN | FALSE | 随距离降低有效 lrefine_max | 一般不改 |
| `gr_lrefineMaxRedRadiusFact` | REAL | 0.0 | 距离降低因子 | 一般不改 |
| `gr_lrefineMaxRedTRef` | REAL | 0.0 | 基于时间的降低参考时间 | 一般不改 |
| `gr_lrefineMaxRedTimeScale` | REAL | 1.0 | 降低时间尺度 | 一般不改 |
| `gr_lrefineMaxRedLogBase` | REAL | 10.0 | 对数底数 | 一般不改 |
| `flux_correct` | BOOLEAN | true | 通量校正开关 | 一般不改 |
| `interpol_order` | INTEGER | 2 | 插值阶数 (0, 1, 2) | 一般不改 |
| `convertToConsvdInMeshInterp` | BOOLEAN | TRUE | 插值时转换为守恒形式 | 一般不改 |
| `earlyBlockDistAdjustment` | BOOLEAN | TRUE | 重启后提前重新分配 block | 一般不改 |
| `gr_restrictAllMethod` | INTEGER | 3 | 全局限制方法 (0-3) | 一般不改 |

### 3.7 Paramesh4 专用参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enableMaskedGCFill` | BOOLEAN | TRUE | 启用掩码保护单元填充 |
| `gr_sanitizeDataMode` | INTEGER | 1 | 插值后数据清洗模式 (0=无动作, 1=检查并报告, 3=检查并修复, 4=检查并中止) |
| `gr_sanitizeVerbosity` | INTEGER | 5 | 数据清洗详细程度 (0,1,4,5) |

### 3.8 Paramesh4dev 参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `gr_pmrpAdvanceAllLevels` | BOOLEAN | FALSE | PARAMESH advance_all_levels |
| `gr_pmrpConserve` | BOOLEAN | FALSE | PARAMESH conserve |
| `gr_pmrpConsvFluxDensities` | BOOLEAN | TRUE | consv_flux_densities (FLASH 自动调整) |
| `gr_pmrpConsvFluxes` | BOOLEAN | FALSE | consv_fluxes (FLASH 自动调整) |
| `gr_pmrpDiagonals` | BOOLEAN | TRUE | diagonals |
| `gr_pmrpDivergenceFree` | INTEGER | 1 | -1=FLASH决定, 0=FALSE, 1=TRUE |
| `gr_pmrpForceConsistency` | BOOLEAN | TRUE | force_consistency |
| `gr_pmrpNoPermanentGuardcells` | BOOLEAN | TRUE | no_permanent_guardcells |
| `gr_pmrpNxb` | INTEGER | -1 | nxb (-1=FLASH自动) |
| `gr_pmrpNyb` | INTEGER | 1 | nyb (-1=FLASH自动) |
| `gr_pmrpNzb` | INTEGER | -1 | nzb (-1=FLASH自动) |
| `gr_pmrpMaxblocks` | INTEGER | -1 | maxblocks (-1=FLASH自动) |
| `gr_pmrpNguard` | INTEGER | -1 | nguard (-1=FLASH自动) |
| `gr_pmrpNvar` | INTEGER | -1 | nvar (-1=FLASH自动) |
| `gr_pmrpOutputDir` | STRING | "./" | 输出目录 |
| `gr_pmrpLsingularLine` | BOOLEAN | FALSE | lsingular_line |
| `gr_pmrpCurvilinear` | BOOLEAN | FALSE | curvilinear |

---

## 4. IO/IOMain — 文件输出控制

### 4.1 检查点输出

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `basenm` | STRING | "flash_" | 检查点文件基本名 | ⭐ 可改为自定义名 |
| `output_directory` | STRING | "" | 输出目录 (绝对或相对路径) | ⭐ 建议设置 |
| `checkpointFileNumber` | INTEGER | 0 | 初始检查点编号 | 一般不改 |
| `checkpointFileIntervalStep` | INTEGER | 0 | 每 N 步写一个检查点 | ⭐ 设 50-200 |
| `checkpointFileIntervalTime` | REAL | 1.0 | 每 T 秒写一个检查点 | ⭐ 常用 |
| `rolling_checkpoint` | INTEGER | 10000 | 保留最近 N 个检查点 | ⭐ 保护磁盘 |
| `wall_clock_checkpoint` | REAL | 43200 | 每 N 秒挂钟时间写检查点 | 超算用 |

### 4.2 绘图文件输出

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `plotFileNumber` | INTEGER | 0 | 初始绘图编号 | 一般不改 |
| `plotFileIntervalStep` | INTEGER | 0 | 每 N 步写一个绘图 | ⭐ 设 10-50 |
| `plotFileIntervalTime` | REAL | 1.0 | 每 T 秒写一个绘图 | ⭐ 常用 |

### 4.3 绘图变量选择

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `plot_var_1` ~ `_12` | STRING | "none" | 输出到绘图文件的 UNK 变量名 |
| `plot_grid_var_1` ~ `_12` | STRING | "none" | 输出到绘图文件的 GRID 变量名 |

> **常用 plot_var**: `"dens"`, `"pres"`, `"tele"`, `"tion"`, `"trad"`, `"velx"`, `"eint"`, `"ener"`

### 4.4 其他 IO 参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `stats_file` | STRING | "flash.dat" | 积分量输出文件名 |
| `prof_file` | STRING | "profile.dat" | profile 输出文件名 |
| `fileFormatVersion` | INTEGER | 9 | 文件格式版本 |
| `outputSplitNum` | INTEGER | 1 | 拆分输出文件数 |
| `useLegacyLabels` | BOOLEAN | true | 使用 4 字符网格标签 |
| `useCollectiveHDF5` | BOOLEAN | true | 使用 HDF5 集体输出模式 |
| `typeMatchedXfer` | BOOLEAN | true | 浮点类型匹配传输 |
| `alwaysComputeUserVars` | BOOLEAN | true | 始终为检查点计算用户变量 |
| `alwaysRestrictCheckpoint` | BOOLEAN | true | 检查点数据始终 restrict |
| `summaryOutputOnly` | BOOLEAN | false | 仅写摘要数据 |
| `forcedPlotFileNumber` | INTEGER | 0 | 强制绘图文件编号 |
| `ignoreForcedPlot` | BOOLEAN | false | 忽略强制绘图 |
| `plotfileGridQuantityDP` | BOOLEAN | false | 绘图文件网格变量双精度 |
| `plotfileMetadataDP` | BOOLEAN | false | 绘图文件元数据双精度 |
| `rss_limit` | REAL | -1.0 | RSS 限制 (MB, 超限则检查点退出) |
| `memory_stat_freq` | INTEGER | 100000 | 内存统计转储频率 |
| `wr_integrals_freq` | INTEGER | 1 | 写入 flash.dat 的频率 |
| `io_writeMscalarIntegrals` | BOOLEAN | FALSE | 质量标量密度积分写入 stats_file |
| `appendParRestart` | BOOLEAN | FALSE | 重启时追加参数到 flash.par |

---

## 5. 物理模块参数

以下是各物理模块的内置参数，按模块组织。

### 5.1 Hydro — 流体力学

> Hydro 模块的参数由 `physics/Hydro` 及其子单元 Config 注册。

#### CFL 条件

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `cfl` | REAL | 0.5 | CFL 数 | ⭐ 设 0.4 |

#### 斜率限制器

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `slopeLimiter` | STRING | "mc" | 斜率限制器类型 |
| `useAuxSlopeLimiter` | BOOLEAN | FALSE | 使用辅助斜率限制器 |

#### 其他 Hydro 参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `updateHydroFluxes` | BOOLEAN | TRUE | 更新流体通量 |
| `computeHydroFluxes` | BOOLEAN | TRUE | 计算流体通量 |
| `useUpwindTVD` | BOOLEAN | FALSE | 使用迎风 TVD 格式 |
| `useConstALocal` | BOOLEAN | FALSE | 使用局部常声速 |

### 5.2 Eos — 状态方程

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `gamma` | REAL | 1.6667 | 绝热指数 (单原子理想气体) | ⭐ IONEOS 用 |
| `mu` | REAL | 1.0 | 平均分子量 | IONEOS 用 |
| `eos_targTableFile` | STRING | "" | 靶材 EOS 表文件名 | ⭐ **必须设置** (.cn4) |
| `eos_chamTableFile` | STRING | "" | 腔室 EOS 表文件名 | ⭐ **必须设置** (.cn4) |

### 5.3 Opacity — 不透明度

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `op_targFileName` | STRING | "" | 靶材不透明度表文件 |
| `op_chamFileName` | STRING | "" | 腔室不透明度表文件 |

### 5.4 Conductivity — 电导率/热导率

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `cond_useEleCond` | BOOLEAN | FALSE | 使用电子电导率 |
| `cond_useIonCond` | BOOLEAN | FALSE | 使用离子电导率 |
| `cond_radFluxLimiter` | REAL | 3.0 | 辐射通量限制器 |

### 5.5 Multigrid — 多重网格求解器

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `mg_maxCorrections` | INTEGER | 100 | 最大校正 V-cycle 数 |
| `mg_maxResidualNorm` | REAL | 1.0e-6 | 最大残差范数 |
| `mg_printNorm` | BOOLEAN | TRUE | 打印残差范数 |

### 5.6 HYPRE — 高性能预处理求解器

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `gr_hypreSolverType` | STRING | "HYPRE_PCG" | 求解器类型 (PCG/AMG/GMRES/BiCGSTAB) |
| `gr_hyprePCType` | STRING | "HYPRE_AMG" | 预条件器类型 |
| `gr_hypreMaxIter` | INTEGER | 500 | 最大迭代次数 |
| `gr_hypreRelTol` | REAL | 1.0e-8 | 相对容差 |
| `gr_hypreAbsTol` | REAL | 0.0 | 绝对容差 |
| `gr_hypreInfoLevel` | INTEGER | 1 | 输出详细程度 |
| `gr_hyprePrintSolveInfo` | BOOLEAN | FALSE | 打印求解器信息 |
| `gr_hypreUseFloor` | BOOLEAN | TRUE | 对结果应用下限 |
| `gr_hypreFloor` | REAL | 1.0e-12 | 扩散下限值 |
| `gr_hypreMinIter` | INTEGER | 0 | 最小迭代次数 (仅 GMRES) |
| `gr_hypreRelChange` | BOOLEAN | FALSE | 使用相对变化收敛判据 |
| `gr_hypreUse2Norm` | BOOLEAN | FALSE | 使用 L2 范数 |
| `gr_hypreRecomputeResidual` | BOOLEAN | FALSE | 重新计算残差 |
| `gr_hypreSlopeLimType` | STRING | "HYPRESL_MC" | 斜率限制器类型 |

### 5.7 MHD — 磁流体力学

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `killdivb` | BOOLEAN | FALSE | 清除 div B 误差 |
| `useBfield` | BOOLEAN | FALSE | 使用磁场 |
| `useHallTerm` | BOOLEAN | FALSE | 使用霍尔项 |
| `useBiermannBattery` | BOOLEAN | FALSE | 使用 Biermann 电池效应 |

### 5.8 RadTrans — 辐射输运

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `rt_mgdXlBoundaryType` | STRING | "vacuum" | 辐射 x 方向左边界 |
| `rt_mgdXrBoundaryType` | STRING | "vacuum" | 辐射 x 方向右边界 |
| `rt_mgdNumGroups` | INTEGER | 10 | MGD 辐射群组数 |
| `rt_mgdLmax` | INTEGER | 0 | MGD 最大 Legendre 阶数 |

### 5.9 Laser — 激光能量沉积

| 参数名 | 类型 | 默认值 | 说明 | 常用场景 |
|--------|------|--------|------|---------|
| `ed_numberOfBeams` | INTEGER | 1 | 光束数量 | ⭐ **必须设置** |
| `ed_numberOfPulses` | INTEGER | 1 | 脉冲数量 | ⭐ **必须设置** |
| `ed_lensX_N` | REAL | 0.0 | 第 N 束激光透镜 X 位置 | ⭐ **必须设置** |
| `ed_targetX_N` | REAL | 0.0 | 第 N 束激光目标 X 位置 | ⭐ **必须设置** |
| `ed_wavelength_N` | REAL | 1.053 | 第 N 束激光波长 (μm) | ⭐ 0.351 (3ω) |
| `ed_crossSectionFunctionType_N` | STRING | "uniform" | 光束截面函数 | ⭐ "uniform" |
| `ed_numberOfRays_N` | INTEGER | 1 | 光线数 (1D 用 1) | ⭐ 设 1 |
| `ed_gridType_N` | STRING | "regular1D" | 网格类型 | ⭐ "regular1D" |
| `ed_gridnRadialTics_N` | INTEGER | 512 | 径向网格点数 | 一般不改 |
| `ed_pulseNumber_N` | INTEGER | 1 | 光束使用的脉冲编号 | ⭐ **必须设置** |
| `laser_powMult` | REAL | 1.0 | 激光功率倍增因子 | ⭐ 批量扫描用 |

**脉冲形状**:

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ed_numberOfSections_P` | INTEGER | 1 | 脉冲 P 的分段数 |
| `ed_time_P_S` | REAL | 0.0 | 脉冲 P 段 S 的时间点 (秒) |
| `ed_power_P_S` | REAL | 0.0 | 脉冲 P 段 S 的功率 (W) |

### 5.10 HeatExchange — 热交换

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `hx_useHeatExchange` | BOOLEAN | TRUE | 使用热交换 |
| `hx_eleTempCoupleFactor` | REAL | 1.0 | 电子温度耦合因子 |
| `hx_ionTempCoupleFactor` | REAL | 1.0 | 离子温度耦合因子 |
| `hx_radTempCoupleFactor` | REAL | 1.0 | 辐射温度耦合因子 |

### 5.11 Diffusion — 扩散

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `diff_useDiffusion` | BOOLEAN | FALSE | 使用扩散 |
| `diff_useEleDiff` | BOOLEAN | FALSE | 使用电子扩散 |
| `diff_useIonDiff` | BOOLEAN | FALSE | 使用离子扩散 |
| `diff_useRadDiff` | BOOLEAN | FALSE | 使用辐射扩散 |
| `diff_useImplicit` | BOOLEAN | FALSE | 使用隐式扩散 |

### 5.12 Burn — 核燃烧

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `useBurn` | BOOLEAN | FALSE | 使用核燃烧 |
| `burn_tmin` | REAL | 1.0e7 | 燃烧最低温度 |
| `burn_densityMin` | REAL | 1.0e-10 | 燃烧最低密度 |

### 5.13 Gravity — 引力

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `useGravity` | BOOLEAN | FALSE | 使用引力 |
| `grav_const` | REAL | 6.67e-8 | 引力常数 |

### 5.14 SourceTerms — 源项

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `useSourceTerms` | BOOLEAN | FALSE | 使用源项 |

---

## 6. 粒子模块 (Particles)

### 6.1 粒子基本控制

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `useParticles` | BOOLEAN | FALSE | 是否推进粒子 |

### 6.2 粒子主控

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `pt_maxPerProc` | INTEGER | 1000 | 每处理器最大粒子数 |
| `pt_dtFactor` | REAL | 0.5 | 粒子时间步长因子 |
| `pt_small` | REAL | 1.0e-10 | 速度截止值 |
| `pt_logLevel` | INTEGER | 700 | 日志级别 |
| `pt_numAtOnce` | INTEGER | 1 | 一次读取粒子数 |
| `pt_dtChangeTolerance` | REAL | 0.4 | 时间步变化容差 |

### 6.3 IO/IOParticles

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `particleFileNumber` | INTEGER | 0 | 初始粒子文件编号 |
| `particleFileIntervalStep` | INTEGER | 0 | 每 N 步写粒子文件 |
| `particleFileIntervalTime` | REAL | 1.0 | 每 T 秒写粒子文件 |
| `writeParticleAll` | BOOLEAN | true | 写入完整粒子数组 |
| `writeParticleSubset` | BOOLEAN | false | 写入子集 |

---

## 7. 实用场景速查表

### 7.1 LaserSlab 1D 典型参数组合

```ini
# ===== TIME CONTROL =====
tmax = 1.0e-9
dtinit = 1.0e-15
dtmax = 1.0e-12
nend = 100000
dr_shortenLastStepBeforeTMax = .TRUE.

# ===== DOMAIN =====
geometry = "cartesian"
xmin = 0.0
xmax = 0.016
xl_boundary_type = "outflow"
xr_boundary_type = "outflow"
zmin = 0.0
zmax = 1.0

# ===== AMR =====
nblockx = 4
lrefine_max = 4
lrefine_min = 1
refine_var_1 = "dens"
refine_var_2 = "tele"
refine_var_3 = "none"
refine_var_4 = "none"

# ===== IO =====
basenm = "laserslab_"
output_directory = "./"
plotFileNumber = 0
plotFileIntervalStep = 10
checkpointFileIntervalStep = 50
plot_var_1 = "dens"
plot_var_2 = "pres"
plot_var_3 = "tele"
plot_var_4 = "tion"
plot_var_5 = "trad"
plot_var_6 = "velx"

# ===== HYDRO =====
cfl = 0.4

# ===== MATERIAL PARAMS (由仿真 Config 注册) =====
sim_rhoTarg = 2.7
sim_teleTarg = 290.11375
sim_tionTarg = 290.11375
sim_tradTarg = 290.11375
sim_rhoCham = 1.0e-6
sim_teleCham = 290.11375
sim_tionCham = 290.11375
sim_tradCham = 290.11375
eos_targTableFile = "al-imx-003.cn4"
eos_chamTableFile = "he-imx-005.cn4"
op_targFileName = "al-imx-003.cn4"
op_chamFileName = "he-imx-005.cn4"

ms_targA = 26.9815
ms_targZ = 13.0
ms_chamA = 4.0026
ms_chamZ = 2.0
```

> **注意**: `sim_*` 前缀的参数、`ms_*`、`eos_*`、`op_*` 等是**自定义参数**，需要在仿真 Config 中注册，它们**不属于** FLASH 内置参数。

### 7.2 内置参数修改频率分类

| 频率 | 参数 | 说明 |
|------|------|------|
| **几乎每次必改** | `tmax`, `nend`, `xmin`, `xmax`, `lrefine_max`, `nblockx` | 仿真基本参数 |
| **经常改** | `dtinit`, `dtmax`, `cfl`, `xl_boundary_type`, `xr_boundary_type`, `plotFileIntervalStep`, `checkpointFileIntervalStep`, `refine_var_1`, `basenm` | 精度/输出控制 |
| **偶尔改** | `dr_shortenLastStepBeforeTMax`, `restart`, `refine_cutoff_1`, `geometry` | 特定需求 |
| **几乎不改** | `small*` 系列, `bndPriority*`, `eosMode`, `interpol_order`, `flux_correct` 等 | FLASH 默认最优 |

---

## 8. 参数验证与故障排除

### 8.1 如何验证参数是否生效？

1. **检查 `.par` 文件** — 参数名必须与 FLASH Config 中的 `PARAMETER` 名完全一致
2. **检查日志** — FLASH 启动日志会显示所有读取的参数:
   ```
   RuntimeParameters_read: lrefine_max = 4
   ```
3. **检查 `flash.par` 转储** — 启动时 FLASH 会转储当前参数快照

### 8.2 常见错误

| 错误现象 | 原因 | 解决 |
|---------|------|------|
| "Unknown parameter" 错误 | 参数名拼写错误或模块未包含 | 检查参数名和 setup 命令是否包括该模块 |
| 参数值未被使用 | 模块未包含在 setup 中 | 添加对应 `+module` 到 setup |
| plot_var 不生效 | 变量名与 FLASH 内部名不匹配 | 用 `test/newpara/` 中的 gen_checker 验证变量名 |
| AMR 不细化 | refine_var 设置错误或 lrefine_max 太低 | 检查 refine_var_1 和 lrefine_max |

### 8.3 快速验证脚本

```python
from flash.input_gen.gen_checker import DependencyChecker
c = DependencyChecker("./my_simulation/flash_input")
c.check_all()
print(c.summary())
```

---

## 附录 A: 按模块分类一览

| 模块路径 | 关键参数 | 是否常用 |
|---------|---------|---------|
| Driver/DriverMain | `tmax`, `nend`, `dtinit`, `restart`, `wall_clock_time_limit` | ⭐ 常用 |
| Grid/GridMain | `geometry`, `xmin/xmax`, `xl_boundary_type`, `nblockx`, `lrefine_max`, `refine_var_1` | ⭐ 常用 |
| physics/Hydro | `cfl`, `slopeLimiter` | ⭐ 常用 |
| physics/Eos | `gamma`, `mu`, `eos_targTableFile` | ⭐ 常用 |
| physics/materialProperties/Opacity | `op_targFileName` | ⭐ 常用 |
| physics/sourceTerms/Laser | `ed_numberOfBeams`, `ed_lensX_*`, `ed_targetX_*`, `ed_pulse*` | ⭐ 常用 |
| IO/IOMain | `basenm`, `plotFileIntervalStep`, `checkpointFileIntervalStep`, `plot_var_*` | ⭐ 常用 |
| IO/IOParticles | `particleFileIntervalStep` | 不常用 |
| Particles/ParticlesMain | `useParticles`, `pt_maxPerProc` | 不常用 |
| Grid/GridSolvers/HYPRE | `gr_hypreSolverType`, `gr_hypreRelTol` | 不常用 |
| Grid/GridSolvers/Multigrid | `mg_maxCorrections`, `mg_maxResidualNorm` | 不常用 |

## 附录 B: 参数命名约定

FLASH 内置参数使用以下命名约定:
- **功能前缀**: `dr_*` (Driver), `gr_*` (Grid), `pt_*` (Particle), `ed_*` (EnergyDeposition), `mg_*` (Multigrid), `mpole_*` (Multipole)
- **无前缀**: 基本参数如 `tmax`, `cfl`, `nblockx`, `geometry` 等直接命名
- **仿真自定义**: `sim_*` — 这些**不属于**内置参数，需在仿真 Config 中注册
- **材料**: `ms_*` (质量), `eos_*` (EOS 表), `op_*` (不透明度) — 需仿真 Config 注册

---

> **参考链接**
> - [FLASH 4.8 官方运行时参数文档](https://flash.rochester.edu/site/flashcode/user_support/rpDoc_4p8.py?submit=rpDoc.txt)
> - [FLASH 4.8 用户指南](https://flash.rochester.edu/site/flashcode/user_support/flash4_ug_4p8.pdf)
> - [本包新参数流程指南](./README.md)
> - [本包 API: NewParaGenerator](./generator.py)
