---
name: flash-knowledge
description: FLASH 源码级知识导航（11 单元：laser/driver/grid/hydro/eos/radtrans/sourceterms/material/io/diffuse/multispecies 的物理原理、关键参数语义、典型坑）。FLASH 物理/setup 标志/参数语义问答时使用。触发词：laser 块、+ug 语义、mgd_meshgroups、EOS 表、MGD、radtrans、multispecies、diffuse 求解器、FLASH 参数是什么意思。
---

> 最后核对：2026-11-06 · commit 72f6428
> 上游：FLASH-Expert @ 25013c5（github.com/boxu-pku/FLASH-Expert，temp/ 浅克隆只读）
> 本 skill 是导航索引；每节为 20 行级精华转写，全文见 references/ 或 temp/ 原文。

# FLASH 源码级知识导航（11 单元）

## 分工声明

- 本 skill 只答 **FLASH 物理机制 / setup 标志 / par 参数语义** 类问题（源码级）。
- flash-sim 工程操作（场景生成、运行部署、输出分析、表处理）走本仓其他操作型 skill（flash-scenario-setup / flash-scenario-family / flash-run-deploy 等）。
- 报错/症状诊断 → `flash-pitfalls` skill。

## 逐单元精华（11 节）

### 1. laser — 激光能量沉积（EnergyDeposition）

- **物理**：几何光学 ray tracing；光线在临界密度 N_c∝1/λ² 处折射/反射，沿程逆韧致吸收沉积到 EELE_VAR（沉积机制，温度计算归 EOS）。激光**不读 opacity 表**（用逆韧致公式）。
- **关键参数**：

| 参数 | 语义 | 坑 |
|---|---|---|
| `ed_wavelength_<i>` | 波长，单位 **μm**（不是 cm） | 决定 N_c；三倍频后 N_c ×9 |
| `ed_numberOfBeams/Pulses` | 实际束/pulse 数（runtime） | 超过 max 槽位即 abort |
| `ed_maxBeams/Pulses/RayCount` | **setup 变量**（默认 6/5/100） | parfile 改无效，须 setup+make |
| `ed_crossSectionFunctionType_<i>` | 截面：gaussian2D / gaussianInverse2D(环形) / super-Gaussian 等 | gaussianInverse2D 需 targetSemiAxis > gaussianRadius |
| `ed_gaussianExponent_<i>` | α：1=标准高斯，4=平顶 | 单位系 μm/cm/s/W/度混用是头号坑 |
| `ed_laser3Din2D` | 2D RZ 用 3D ray，**必须 .true.** | wedge 角配 `ed_laser3Din2DwedgeAngle` |
| `ed_pulseNumber_<i>` | 束绑哪条 pulse | time/power 段须时间升序，否则 Wrong time order |

- **典型坑**：`Not enough beam runtime parameters`（束数超 maxBeams）；沉积能量偏少 5 因素（pulse 时段不覆盖 simTime / target 椭圆小 / grid 边界丢 ray / 临界反射 / 单位错）。
- **锚点**：源码入口 `source/physics/sourceTerms/EnergyDeposition/.../Laser/`（ed_setupBeams / ed_traceRays / ed_updatePlasma）· last_verified 2026-07-12

### 2. driver — 主循环（Driver）

- **物理/机制**：Driver_evolveFlash 每步 = 取块 → Hydro → 扩散 → sourceTerms → 粒子 → 收尾（重力/AMR/IO/dt）。4 变体：Unsplit（默认）/Split（Strang，燃烧）/multithreaded（OpenMP）/INSfracstep。
- **关键参数**：`dtinit/dtmin/dtmax/tmax/nend`（时间步与终止）；`tstep_change_factor`（dt 增长限幅）；`wall_clock_time_limit`（默认 604800 s=7 天，-1 禁用）；`restart`+`checkpointFileNumber`（续跑）；`useSTS/nuSTS`（超时间步，加速扩散类）；`DRIVER_EDEARLY`/`DRIVER_DIFFULAST` 宏调整 sourceTerms 中激光/扩散位置（激光默认第 10 位，等温度场算完再加，保稳定）。
- **典型坑**：dt 持续下降 → 查激波增强/CFL 过大/EOS 表外推；Split vs Unsplit 选错（大多数算例用 Unsplit）。
- **锚点**：`source/Driver/DriverMain/Driver_sourceTerms.F90:44-69`（调度顺序）· last_verified 2026-07-18

### 3. grid — 网格/AMR/几何（Grid）

- **物理/机制**：block-AMR 数据底座（unk/facevarx,y,z/scratch）。4 backend：paramesh4dev（默认，`+pm4dev`）/ UG（`+ug`，无 AMR）/ Chombo（半成熟）/ Samrai（未实现）。
- **关键参数**：`xmin..zmax`（域边界，cm）；`geometry`（cartesian/cylindrical/spherical/polar）；`lrefine_min/max`（细化层界）；`refine_var_N`+`refine_cutoff/derefine_cutoff`（按变量细化）；`xl/xr_boundary_type` 等（reflect/outflow/axisymmetric/vacuum）；`nblockx/y/z`、`NXB/NYB/NZB`（编译期块尺寸）。
- **几何要点**：cylindrical + 2D = **R-Z 平面**（φ 丢弃）；要 R-φ 用 polar。leaf 遍历范式：`Grid_getListOfBlocks(LEAF)` → `Grid_getBlkPtr` → 计算 → **必须** `Grid_releaseBlkPtr` 配对。
- **典型坑**：geometry 与维度不匹配 abort；refine 不触发（cutoff/filter 未配）；getBlkPtr 不释放在 NO_PERMANENT_GUARDCELLS 下数据不一致。
- **锚点**：`source/Grid/GridMain/`（Config 选 backend，gr_initGeometry 轴向映射）· last_verified 2026-07-19

### 4. hydro — 流体求解器（Hydro）

- **物理**：6 互斥变体（split PPM/MHD_8Wave/RHD；unsplit Hydro_Unsplit 默认/MHD_StaggeredMesh；unsplit_rad RadFLAH）。unsplit = CTU 多维 Godunov，无分裂误差、支持 3T/MHD。
- **关键参数**：

| 参数 | 默认 | 语义 |
|---|---|---|
| `cfl`（hy_cfl） | 0.8 | CTU 稳定限近 1，留 20% 余量；强激波 0.4-0.5，保守起步 0.3 |
| `slopeLimiter` | vanLeer | minmod/MC/vanLeer/limited |
| Riemann solver | HLLC | 恢复接触间断免 entropy fix；MHD 用 HLLD；强激波鲁棒用 Hybrid/Marquina |
| `+usm` vs `+8wave` | usm | USM-CT 保 ∇·B 机器精度；8-wave 更耗散 |
| `small/smlrho/smallp/smalle` | 1e-10 量级 | 截断 floor，过低致 NaN |
| `hy_3Torder` | — | 3T 耦合阶（+uhd3t） |

- **典型坑**：NaN/负密度 5 类原因（CFL 大 / Riemann 选错 / 截断低 / charLimiting 关 / AMR flux 不守恒）；诊断先看 NaN 位置是否激波附近。
- **锚点**：`source/physics/Hydro/HydroMain/unsplit/hy_uhd_*.F90`（getFaceFlux 调度各 solver）· last_verified 2026-07-19

### 5. eos — 状态方程（Eos）

- **物理**：6 变体：Gamma（默认理想气体）/Multigamma/Helmholtz（HEDP 首选，含电子简并）/Tabulated（ionmix/sesame 表）/multiTemp（3T，5 子变体 Multitype 最全）/multiFluid。3T = TEION/TELE/TERAD 分演（时间尺度差 3+ 数量级，强行平衡会误算电子压力/不透明度）。
- **关键参数**：`eosMode`（dens_ie 默认：Hydro 后能量为守恒变量；dens_temp：初始化指定 ρ,T 直接求；dens_pres：Riemann 后；3T 还有 _EQUI/_GATHER/_RECAL_GATHER）；`eos_maxNewton=50`/`eos_tolerance`（迭代参数）；`eintSwitch`（防能量灾难消去）；`eos_coulombMult/eos_coulombAbort`；`gamma/gammaIon/Ele/Rad`；截断 `smalle/smallt`。Helmholtz 表 helm_table.dat 7.7MB（211×71，ρ∈[1e-10,1e11]、T∈[1e4,1e11]）= 电子自由能表 + 离子理想气体 + 辐射 + Coulomb 修正。
- **典型坑**：Newton 不收敛（低密度+高能+混合物质，见 pitfalls）；dens_ie 初始猜测差；表外推；Coulomb 修正负压。
- **锚点**：`source/physics/Eos/EosMain/Eos.F90:L237`（按 eos_type 分发）；eosMode 常量在 `source/Simulation/constants.h:L297-L341` · last_verified 2026-07-19

### 6. radtrans — 辐射传输（RadTrans/MGD）

- **物理**：HEDP 主流 = MGD 多群扩散：光子分 N 群，每群解扩散方程，经 `Diffuse_solveScalar` 走 HYPRE 隐式求解（θ-加权，`rt_mgdthetaImplct=1.0` 全隐式无条件稳定）。
- **关键参数**：

| 参数 | 语义 | 坑 |
|---|---|---|
| `rt_useMGD` | MGD 总开关 | 关辐射走 par 三开关（见 pitfalls） |
| `rt_mgdNumGroups` | 群数 | **必须 == setup 的 `mgd_meshgroups`**（setup 变量！） |
| `rt_mgdBounds_*` | 群边界，单位 **eV** | 须 N+1 个；默认 -1 启动 abort；**须手动与 IONMIX 表群结构对齐**，不自动同步 |
| `rt_mgdFlMode` | flux limiter | **Config 默认 fl_none 危险**（光学薄超光速）；LaserSlab 用 fl_harmonic |
| `rt_mgdXlBoundaryType` 等 | 边界：vacuum/reflecting/marshak | vacuum 误用 reflecting 会物理失真 |
| `rt_dtFactor` | 辐射 dt 因子（Morel-McClarren） | 常设 1e100 禁用 |

- **典型坑**：群边界没设/群数不一致 abort；IONMIX 表与 meshgroups 不匹配；fl_none 辐射能量爆炸。
- **锚点**：`source/physics/RadTrans/RadTransMain/MGD/RadTrans.F90:L31`、`rt_init.F90:L15` · last_verified 2026-08-07

### 7. sourceterms — 非流体源项（Heatexchange 主讲）

- **物理**：Heatexchange = 电子-离子(-辐射)能量平衡源项（3T 必备，否则 TELE/TEION 持续漂移）。5 变体：Constant（默认）/ConstCoulomb/**Spitzer**（HEDP 标准）/LeeMore（高 Z）/Immediate（强制平衡）。Spitzer-Härm：eqtime ~ T_ele^1.5/(Z²·n·lnΛ)，解析 ODE 解严格守恒（cvion·ΔTion+cvele·ΔTele=0）。
- **关键参数**：`useHeatexchange`（**默认 .false.**）；`hx_dtFactor`（默认 0.5=每步最多交换一半内能；LaserSlab 设 1e100 禁用，因 eqtime≪dt_hydro）；`hx_ieTimeCoef/hx_relTol`；lnΛ 由 PlasmaState_logLambda 共享计算。
- **其他源项**（简要）：Burn（核燃烧，改 Multispecies）/Cool（辐射冷却）/Heat/Stir（湍流）/Ionize/Flame/Polytrope。
- **典型坑**：TELE 不变 → useHeatexchange 没开 / 没用 3T EOS（REQUIRES multiTemp）/ DRIVER_EDEARLY 顺序错。
- **锚点**：`source/physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer/Heatexchange.F90:L124-L307` · last_verified 2026-07-30

### 8. material — 物质属性（Conductivity + Opacity 主讲）

- **物理**：Conductivity = 热传导系数（HEDP 电子主导）；SpitzerHighZ 变体（LaserSlab 用）：cond ~ k_B^3.5·T_e^2.5/(√m_e·e^4·lnΛ·(Z+3.3))（Atzeni 修正），diffCoeff = cond/(ρ·cv)。Opacity = 不透明度，MGD **每群每物种查一次**；三种表：PA(Planck 吸收)/PE(Planck 发射)/RO(Rosseland 扩散通量)，MGD 需三者齐备。
- **关键参数**：`useConductivity/useOpacity`；`op_<spec>Absorb/Emiss/Trans`（= op_tabpa/op_tabpe/op_tabro）；`op_<spec>FileType/FileName`（ionmix4=.cn4 主流）；`cond_constantIsochoric` 等（Constant 变体）；`opacity_ignoreLowTemp/opacity_ceiling`。lnΛ 由 PlasmaState_logLambda 与 Heatexchange/Resistivity 共享。
- **典型坑**：cond=0（diffusion_cutoff_density 触发）；SpitzerHighZ 只支持 3T；.cn4 群数须全体物种一致且与 MGD 对齐。
- **锚点**：`source/physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/Conductivity.F90:L122-L131` · last_verified 2026-07-31

### 9. io — 输入输出（HDF5 plotfile/checkpoint）

- **机制**：plotfile = 单精度可视化（yt/Visit）；checkpoint = 双精度 restart（写全部 unk+facevar+参数）。backend：`+hdf5typeio`（type-based parallel HDF5，PM_argonne，HEDP 主流）> 标准 PM > pnetcdf/direct。4 类输出触发：step/simTime/wallclock/触发文件（.dump_plotfile/.dump_checkpoint/.kill）。
- **关键参数**：`plotFileIntervalStep/Time`、`checkpointFileIntervalStep/Time`（**IntervalStep 与 Time 是 OR 双触发**）；`plot_var_1..N`（白名单）；`basenm`（前缀）；`rolling_checkpoint`（滚动保留）；`useCollectiveHDF5`（默认 true，快 5-10×；NoFbs 强制 false）；`wr_integrals_freq`+`stats_file`（flash.dat 积分量）；`restart`+`checkpointFileNumber`+`plotFileNumber`（续跑三件套）。
- **典型坑**：plotfile 不出（IntervalTime<dt 或全默认）；restart 后 plotFileNumber 不设 → 从 0 覆盖旧文件；NXB 改了 checkpoint 不兼容（io_checkBlockShape abort）。
- **锚点**：`source/IO/IOMain/IO_output.F90:L114-L600`；`io_checkBlockShape.F90:L23-L43` · last_verified 2026-07-31

### 10. diffuse — 隐式扩散求解（Diffuse + HYPRE）

- **物理/机制**：解 ρcv·∂T/∂t = ∇·(κ∇T) 类抛物方程，θ-加权隐式离散 → 稀疏线性系统 → HYPRE（LLNL 库，非 FLASH 组件）。Diffuse_solveScalar 是 thin wrapper，真正实现在 `Grid/GridSolvers/HYPRE/`。
- **关键参数**：

| 参数 | 语义 | 坑 |
|---|---|---|
| `diff_thetaImplct` | θ：0 显式 / 0.5 CN / 1.0 全隐式 | 默认 0.5；LaserSlab 用 1.0（极陡梯度下 CN 震荡） |
| `gr_hypreSolverType` | 默认 HYPRE_PCG + AMG 预条件 | 大网格直接 HYPRE_AMG 更稳 |
| `gr_hypreRelTol/MaxIter` | 收敛容差/迭代上限 | 1e-8/500 常不够；物理精度 1e-6、1000+ 迭代 |
| `gr_hypreUseFloor` | 解的 floor | **本仓 SNB 铁律：必须 .false.**（见 flash-pitfalls） |
| `diff_useEleCond/IonCond` | 电子/离子热传导开关 | 电子默认开 |
| `diff_eleFlMode/Coef` | 电子通量限制器 | fl_none 危险；LaserSlab fl_larsen coef=0.06 |
| `dt_diff_factor` | 扩散 dt 因子 | 常设 1e100 禁用 |
| `diff_anisoCondForEle` | 各向异性传导（需 MHD） | CND1/2/3 = 平行/垂直/交叉 |

- **典型坑**：HYPRE 不收敛 6 因素（MaxIter 小/RelTol 严/θ<1 震荡/limiter 系数跳变/COND_VAR=0 矩阵奇异/全 Neumann 解不唯一）。
- **锚点**：`source/physics/Diffuse/DiffuseMain/Unsplit/diff_advanceTherm.F90:L64-L488`；`Grid/GridSolvers/HYPRE/gr_hypreSolve.F90:L27-L420` · last_verified 2026-07-31

### 11. multispecies — 多物质追踪（Multispecies）

- **物理/机制**：追踪每种物质质量分数 X_i（SPECIES_VAR 中心变量，ΣX=1 自动归一）。`species=cham,targ` setup 变量触发 Config Python 自动生成：Flash.h 索引宏（CHAM_SPEC...）、参数族 `ms_<spec>A/Z/...`、`eos_<spec>EosType/TableFile`、`op_<spec>*`。Helmholtz 用质量分数加权自动算 Abar/Zbar：`Abar = 1/Σ(X_i/A_i)`，`Zbar = Abar·Σ(X_i·Z_i/A_i)`。
- **关键参数**：`ms_<spec>A/Z`（必填，默认 -999 会除零 abort）；`ms_<spec>ZMin`；多元素物质用 `ms_<spec>NumElems + ZElems_k/AElems_k/Fractions_k` 三件套（如 CH：C 0.857/H 0.143）；8 个 API（getSum/getSumInv/getSumFrac/getAvg/getProperty/setProperty/list 等）。
- **典型坑**：Abar=0 → ms_<spec>A 没填或 species= 没传；**species 名 4 处必须完全一致**（setup/Flash.h/parfile 前缀/initBlock），>4 字符长名触发 HDF5 dataset 冲突（见 pitfalls）。
- **锚点**：`source/Multispecies/MultispeciesMain/Config:L1-L42`（自动生成核心）；`Multispecies_getSumInv.F90:L87-L159` · last_verified 2026-08-02

## 上游原文获取

- 三大高频单元（laser/eos/hydro）knowledge 五件套已精选拷贝至本 skill `references/flash-{laser,eos,hydro}-knowledge/`。
- 其余单元原文在 `temp/FLASH-Expert/skills/flash-<unit>/`（git pull 更新通道），需要时按单元读取 overview/params/internals/recipes/pitfalls 五件套。
- 上游 commit 变更后重跑核对：`git -C temp/FLASH-Expert log -1 --format=%h`。
