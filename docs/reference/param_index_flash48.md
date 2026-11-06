# FLASH 4.8 参数索引（核心 ~150 条）

> 最后核对：2026-11-06 · commit 72f6428
> 上游：FLASH-Expert @ 25013c5（flash-param-query 收纳）
>
> 使用规则：
> - 本索引是高频参数快速参考（含 Config 没写的单位、典型值、含义、setup 相关性）
> - 本索引没有的参数 → 动态搜 Config：`find source -name Config | xargs grep "^PARAMETER <名>"`
> - 物理背景与陷阱 → 上游对应 flash-\<unit\> skill 的 knowledge/params.md
> - **setup 变量 vs runtime parameter**：setup 变量在 `./setup` 命令行改，改完须重新 setup+make；runtime parameter 写 flash.par 即可。名字以 `max` 开头通常是 setup 变量，`numberOf` 开头通常是 runtime parameter。

## 目录

1. [Driver（时间步/模拟控制）](#1-driver)
2. [Grid（AMR/几何/refinement）](#2-grid)
3. [Hydro（流体求解器）](#3-hydro)
4. [Eos（状态方程）](#4-eos)
5. [RadTrans / MGD（辐射传输）](#5-radtrans--mgd)
6. [EnergyDeposition / Laser（激光）](#6-energydeposition--laser)
7. [Diffuse（扩散）](#7-diffuse)
8. [materialProperties（物质属性）](#8-materialproperties)
9. [sourceTerms（Burn/Cool/Heat/Heatexchange）](#9-sourceterms)
10. [IO（输入输出）](#10-io)
11. [Multispecies（多物种）](#11-multispecies)
12. [Simulation（用户参数）](#12-simulation)
13. [按前缀速查](#13-按前缀速查)

---

## 1. Driver

> 声明：`source/Driver/DriverMain/Config`

### 时间步控制

| 参数 | 类型 | 默认 | 单位 | 含义 | setup 相关 |
|---|---|---|---|---|---|
| `dtinit` | REAL | 1e-10 | s | 初始时间步 | runtime |
| `dtmin` | REAL | 1e-10 | s | 最小允许 dt（小于则 abort） | runtime |
| `dtmax` | REAL | 1e5 | s | 最大允许 dt（本仓 SNB 铁律 2.0e-14） | runtime |
| `tstep_change_factor` | REAL | 2.0 | — | dt 单步最大变化倍数 | runtime |
| `dr_tstepSlowStartFactor` | REAL | 0.1 | — | 慢启动因子 | runtime |
| `useSTS` / `useSTSforDiffusion` | BOOLEAN | false | — | Super-time-stepping（加速扩散类） | runtime |
| `allowDtSTSDominate` | BOOLEAN | false | — | 允许 STS 主导 dt | runtime |

### 模拟范围与终止

| 参数 | 类型 | 默认 | 单位 | 含义 | setup 相关 |
|---|---|---|---|---|---|
| `nbegin` / `nend` | INTEGER | 1 / 100 | — | 起始/终止步 | runtime |
| `tinitial` / `tmax` | REAL | 0.0 / 0.2 | s | 起始/终止时间 | runtime |
| `wall_clock_time_limit` | REAL | 604800 | s | 墙钟超时（7 天；-1 禁用） | runtime |

### Restart 与诊断

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `restart` | BOOLEAN | false | 从 checkpoint 重启 | runtime |
| `checkpointFileNumber` | INTEGER | 0 | 读哪个 chk（restart 用） | runtime |
| `dr_printTStepLoc` | BOOLEAN | true | 打印 dt 计算位置 | runtime |
| `dr_usePosdefComputeDt` | BOOLEAN | false | 强制正定 dt | runtime |
| `eachProcWritesOwnAbortLog` | BOOLEAN | false | 每 processor 独立 abort 日志 | runtime |

## 2. Grid

> 声明：`source/Grid/GridMain/Config`、`source/Grid/Config`

### 域边界与几何

| 参数 | 类型 | 默认 | 单位 | 含义 | setup 相关 |
|---|---|---|---|---|---|
| `xmin`/`xmax`（y/z 同） | REAL | 0 / 1 | cm | 域边界 | runtime |
| `geometry` | STRING | "cartesian" | — | cartesian/cylindrical/spherical/polar（cylindrical+2D=R-Z 平面） | runtime |

### AMR refinement

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `lrefine_min` / `lrefine_max` | INTEGER | 1 | 最小/最大细化层（+ug 下被忽略） | runtime |
| `nrefs` | INTEGER | 2 | 触发细化的误差次数 | runtime |
| `refine_var_1..4` | INTEGER | -1 | 触发细化的变量索引 | runtime |
| `deref_var_1..4` | INTEGER | -1 | 触发粗化的变量索引 | runtime |
| `iProcs` | INTEGER | — | 每方向 processor 数（+ug 必须等于 `mpiexec -n`） | runtime |
| `iGridSize` | INTEGER | — | 非固定块模式全域网格数（须显式 `-nofbs`） | runtime |

### 边界条件

| 参数 | 类型 | 含义 | setup 相关 |
|---|---|---|---|
| `xl_boundary_type` 等 6 个 | STRING | reflect/outflow/diode/axisymmetric/vacuum/user | runtime |

## 3. Hydro

> 声明：`source/physics/Hydro/HydroMain/Config`、`.../unsplit/Config`

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `useHydro` | BOOLEAN | true | Hydro 总开关 | runtime |
| `cfl`（hy_cfl） | REAL | 0.8 | Courant 数；强激波 0.4-0.5，保守起步 0.3 | runtime |
| `small` / `smallp` / `smallu` | REAL | 1e-10 | 密度/压强/速度 floor | runtime |
| `smallx` | REAL | 1e-99 | 质量分数 floor（薄层判据相关） | runtime |
| `slopeLimiter` | STRING | vanLeer | minmod/MC/vanLeer/limited | runtime |
| `use_steepening` | BOOLEAN | true | 接触不连续陡化 | runtime |
| `epsilon_1` / `epsilon_2` | REAL | — | 激波检测阈值 | runtime |

（Riemann solver 由 setup 变体决定：+usm / +8wave / +splitHydro 等，见 flash-knowledge §4。）

## 4. Eos

> 声明：`source/physics/Eos/EosMain/<variant>/Config`

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `eos_gammas` | REAL | 5/3 | 单原子理想气体 γ | runtime |
| `eos_singleSpecies` | BOOLEAN | true | 单物种模式 | runtime |
| `eos_tolerance` | REAL | 1e-12 | EOS 迭代容差（不收敛时放宽到 1e-6） | runtime |
| `eos_maxNewton` | INTEGER | 50 | Newton 迭代上限（不收敛时提到 100） | runtime |
| `eos_lowTemp` / `eos_highTemp` | REAL | — | 表格适用温度范围（multiTemp） | runtime |
| `eos_<spec>EosType` | STRING | — | 每物种 EOS 类型（species= 自动生成） | runtime |
| `eos_<spec>TableFile` | STRING | — | 每物种 EOS 表文件（.cn4/.ses） | runtime |

（eosMode dens_ie/dens_temp/dens_pres 是代码内常量，不经 parfile，见 flash-knowledge §5。）

## 5. RadTrans / MGD

> 声明：`source/physics/RadTrans/RadTransMain/MGD/Config`

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `useRadTrans` | BOOLEAN | false | RadTrans 总开关（本仓关辐射三开关之一） | runtime |
| `rt_useMGD` | BOOLEAN | false | MGD 启用（三开关之一） | runtime |
| `rt_mgdNumGroups` | INTEGER | 4 | 群数；**必须 == setup 的 mgd_meshgroups** | runtime |
| `rt_mgdBounds_1..N+1` | REAL | — | 群边界（**eV**），须 N+1 个，手动与 IONMIX 表对齐 | runtime |
| `rt_mgdFlMode` | STRING | — | flux limiter：fl_harmonic/fl_geometric/fl_none（默认危险） | runtime |
| `rt_mgdFlCoef` | REAL | 1.0 | flux limiter 系数 | runtime |
| `rt_mgdXlBoundaryType` 等 6 个 | STRING | — | vacuum/reflecting/marshak | runtime |
| `rt_mgdDtFactor`（rt_dtFactor） | REAL | 1e100 | 辐射 dt 因子 | runtime |
| `mgd_meshgroups` | INTEGER | 4 | **setup 变量**：分配能群数组的编译期上限 | **setup** |
| `rt_mgdthetaImplct` | REAL | 1.0 | θ-加权隐式度（全隐式无条件稳定） | runtime |

## 6. EnergyDeposition / Laser

> 声明：`source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config`

### 总控与几何

| 参数 | 类型 | 默认 | 单位 | 含义 | setup 相关 |
|---|---|---|---|---|---|
| `useEnergyDeposition` | BOOLEAN | true | — | 激光总开关 | runtime |
| `ed_laser3Din2D` | BOOLEAN | false | — | 2D RZ 用 3D ray（**必须 .true.**） | runtime |
| `ed_laser3Din2DwedgeAngle` | REAL | 0.0 | 度 | 楔形角 | runtime |
| `ed_gradOrder` | INTEGER | 2 | — | 折射阶：1=无折射，2=一阶 | runtime |
| `ed_numberOfBeams` / `ed_numberOfPulses` | INTEGER | -1 | — | 实际束/pulse 数 | runtime |
| `ed_maxBeams` / `ed_maxPulses` / `ed_maxRayCount` | INTEGER | 6 / 5 / 100 | — | 参数槽位上限 | **setup** |

### Pulse 时间波形

| 参数 | 类型 | 默认 | 单位 | 含义 | setup 相关 |
|---|---|---|---|---|---|
| `ed_numberOfSections_<p>` | INTEGER | -1 | — | 第 p 条 pulse 的段数 | runtime |
| `ed_time_<p>_<s>` | REAL | -1.0 | **s** | 段时间（须升序） | runtime |
| `ed_power_<p>_<s>` | REAL | -1.0 | **W** | 段功率 | runtime |

### Beam 几何与截面（每束，列核心）

| 参数 | 类型 | 默认 | 单位 | 含义 | setup 相关 |
|---|---|---|---|---|---|
| `ed_wavelength_<i>` | REAL | -HUGE | **μm** | 波长（决定临界密度） | runtime |
| `ed_lensX/Y/Z_<i>` | REAL | -HUGE | cm | lens 椭圆中心 | runtime |
| `ed_targetX/Y/Z_<i>` | REAL | -HUGE | cm | target 椭圆中心（光斑中心） | runtime |
| `ed_targetSemiAxisMajor/Minor_<i>` | REAL | -HUGE | cm | 光斑半长/短轴 | runtime |
| `ed_pulseNumber_<i>` | INTEGER | -HUGE | — | 绑哪条 pulse | runtime |
| `ed_crossSectionFunctionType_<i>` | STRING | " " | — | uniform/gaussian2D/gaussianInverse2D 等 | runtime |
| `ed_gaussianExponent_<i>` | REAL | -HUGE | — | α：1=高斯，4=平顶 | runtime |
| `ed_gaussianRadius{Major,Minor}_<i>` | REAL | -HUGE | cm | 1/e 半径 | runtime |
| `ed_numberOfRays_<i>` | INTEGER | -HUGE | — | 该束 ray 数 | runtime |
| `ed_gridType_<i>` | STRING | " " | — | radial2D/square2D/statistical2D 等 | runtime |

## 7. Diffuse

> 声明：`source/physics/Diffuse/DiffuseMain/Unsplit/Config`

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `useDiffuse` | BOOLEAN | false | 扩散总开关 | runtime |
| `diff_useEleCond`（diff_useThermDiff） | BOOLEAN | true | 电子热传导 | runtime |
| `diff_useIonCond` | BOOLEAN | false | 离子热传导 | runtime |
| `diff_doMagDiff` | BOOLEAN | false | 磁扩散 | runtime |
| `diff_thetaImplct`（diff_theta / diff_3Ttheta） | REAL | 0.5-1.0 | θ-加权：0 显式/0.5 CN/1.0 全隐式 | runtime |
| `diff_eleFlMode` / `diff_eleFlCoef` | STRING/REAL | — | 电子通量限制器（LaserSlab: fl_larsen 0.06） | runtime |
| `diff_anisoCondForEle` | BOOLEAN | false | 各向异性传导（需 MHD；CND1/2/3） | runtime |
| `dt_diff_factor` | REAL | 0.8 | 扩散 dt 因子（常设 1e100 禁用） | runtime |
| `diffusion_cutoff_density` | REAL | — | 低于此密度电导置 0（真空区） | runtime |
| `gr_hypreSolverType` | STRING | "HYPRE_PCG" | PCG/AMG/BiCGSTAB/GMRES/HYBRID | runtime |
| `gr_hyprePcType` | STRING | "HYPRE_AMG" | 预条件子 | runtime |
| `gr_hypreRelTol` / `gr_hypreMaxIter` | REAL/INTEGER | 1e-8 / 500 | 收敛容差/迭代上限（大网格放宽/加大） | runtime |
| `gr_hypreUseFloor` / `gr_hypreFloor` | BOOLEAN/REAL | true / — | 解的 floor（**本仓 SNB 必须关**） | runtime |

## 8. materialProperties

> 声明：`source/physics/materialProperties/*/Config`

### Conductivity

| 参数 | 类型 | 含义 | setup 相关 |
|---|---|---|---|
| `useConductivity` | BOOLEAN | 启用热传导 | runtime |
| `cond_constantIsochoric` 等 | REAL | Constant 变体系数 | runtime |
| （变体） | — | SpitzerHighZ/LeeMore 等由 setup 选 | **setup** |

### Opacity

| 参数 | 类型 | 含义 | setup 相关 |
|---|---|---|---|
| `useOpacity` | BOOLEAN | 启用不透明度（三开关之一） | runtime |
| `op_<spec>Absorb/Emiss/Trans` | STRING | PA/PE/RO 三表模式：op_tabpa/op_tabpe/op_tabro | runtime |
| `op_<spec>FileType` | STRING | ionmix4/ionmix7/sesame/opacplot | runtime |
| `op_<spec>FileName` | STRING | 表文件名（须在 Config DATAFILES 声明） | runtime |
| `opacity_ignoreLowTemp` | BOOLEAN | 低温区跳过表 | runtime |

## 9. sourceTerms

> 声明：`source/physics/sourceTerms/*/Config`

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `useBurn` / `burn_dtFactor` / `burn_eosMode` | — | false / 1e100 / dens_e | Burn 核燃烧 | runtime |
| `useCool` / `cool_dtFactor` | — | false / 1e100 | Cool 辐射冷却 | runtime |
| `useHeat` | BOOLEAN | false | Heat 外热源 | runtime |
| `useHeatexchange` | BOOLEAN | **false** | 电子-离子能量交换（3T 必开） | runtime |
| `hx_dtFactor` | REAL | 0.5 | HX dt 因子（LaserSlab 设 1e100 禁用） | runtime |
| `hx_ieTimeCoef` / `hx_relTol` | REAL | — | 平衡时间系数/相对容差 | runtime |

## 10. IO

> 声明：`source/IO/IOMain/Config`

| 参数 | 类型 | 默认 | 含义 | setup 相关 |
|---|---|---|---|---|
| `basenm` | STRING | — | 输出前缀（含目录，如 "01-data/lasslab_"） | runtime |
| `plot_var_1..12` | INTEGER/STRING | 0 | 输出变量白名单（**≤12 项从 1 连续**，超限静默忽略） | runtime |
| `plotFileIntervalStep` | INTEGER | 1000 | 每 N 步出 plotfile | runtime |
| `plotFileIntervalTime` | REAL | 0 | 每 N（模拟）秒出（≥5×dt） | runtime |
| `plotFileNumber` | INTEGER | 0 | 当前 plotfile 编号（restart 续号用） | runtime |
| `checkpointFileIntervalStep` / `...Time` | — | 1000 / 1.0 | checkpoint 触发（与 Step 是 OR 双触发） | runtime |
| `checkpointFileNumber` | INTEGER | 0 | 当前 chk 编号 | runtime |
| `rolling_checkpoint` | INTEGER | — | 只保留最近 N 个 chk | runtime |
| `wall_clock_checkpoint` | REAL | — | 墙钟周期写 chk | runtime |
| `useCollectiveHDF5` | BOOLEAN | true | 集体 HDF5 写（NoFbs 强制 false） | runtime |
| `log_file` / `run_comment` | STRING | — | 日志名/算例注释 | runtime |
| `wr_integrals_freq` / `stats_file` | — | — | flash.dat 积分量频率/文件名 | runtime |
| `restart` | BOOLEAN | false | restart 开关（+checkpointFileNumber+plotFileNumber 三件套） | runtime |

## 11. Multispecies

| 参数 | 类型 | 含义 | setup 相关 |
|---|---|---|---|
| `species` | (setup 变量) | species=cham,tar1,...（**名 ≤4 字符且四处一致**） | **setup** |
| `ms_<spec>A` / `ms_<spec>Z` | REAL | 质量数/电荷数（必填，默认 -999 会除零 abort） | runtime |
| `ms_<spec>ZMin` | REAL | 最低电离态 | runtime |
| `ms_<spec>NumElems` + ZElems/AElems/Fractions | — | 多元素物质三件套 | runtime |
| `ms_maxelems`（MS_MAXELEMS） | — | 每物种最大元素数上限 | **setup** |

## 12. Simulation

每个 `SimulationMain/<problem>/Config` 声明该算例特有 `sim_*` 参数：

| 参数 | 类型 | 含义 |
|---|---|---|
| `sim_xmin`/`sim_xmax` 等 | REAL | 算例域边界（独立于 Grid xmin/xmax） |
| `sim_pAmbient` / `sim_rhoAmbient` | REAL | 环境压强/密度 |
| `sim_teleAmbient` / `sim_tionAmbient` / `sim_tradAmbient` | REAL | 3T 环境温度 |
| `sim_smallX` | REAL | 物种格心判据下限（薄层分辨率约束来源） |
| `sim_targetRadius` 等 | REAL | 算例特定几何 |

查具体算例：`cat source/Simulation/SimulationMain/<problem>/Config`

## 13. 按前缀速查

| 前缀 | 单元 |
|---|---|
| `ed_` | EnergyDeposition（激光） |
| `rt_` | RadTrans |
| `mgd_` | MGD（RadTrans 子集，含 setup 变量） |
| `hy_` | Hydro |
| `eos_` | Eos（含每物种 eos_\<spec\>*） |
| `gr_` | Grid（含 gr_hypre* 求解器参数） |
| `sim_` | Simulation（用户算例参数） |
| `dr_` | Driver |
| `io_` / `plot*` / `checkpoint*` | IO |
| `diff_` | Diffuse |
| `op_<spec>` | Opacity（每物种一套） |
| `cond_` | Conductivity |
| `visc_` | Viscosity |
| `res_` | MagneticResistivity |
| `hx_` | Heatexchange |
| `burn_` / `cool_` / `heat_` / `stir_` / `fl_` | Burn/Cool/Heat/Stir/Flame |
| `ms_<spec>` | Multispecies（每物种一套） |
| `xray_` | XrayImaging（X 光诊断） |
