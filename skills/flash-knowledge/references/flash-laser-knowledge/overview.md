---
title: 激光（EnergyDeposition）单元总览
skill: flash-laser
category: overview
source_anchors:
  - source/Driver/DriverMain/Driver_sourceTerms.F90:44-69
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition.F90:160-351
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:118-132
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:375-384
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserPulses/ed_setupPulses.F90:96-125
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_computeBeamPower.F90:34-160
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_beam3DGridWeightRadial.F90:110-200
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserRaysCreate/ed_createRays3DRec.F90:419-476
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserRaysCreate/ed_createRays3DRec.F90:979-994
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserUtilities/ed_inverseBremsstrahlungRate.F90:41-77
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserUtilities/ed_updatePlasma.F90:50-115
manual_ref: "FLASH 4.8 User Guide, EnergyDeposition unit (待 Phase 1 Week 2 转换后补章节号)"
created: 2026-06-17
last_verified: 2026-06-17
verifier: claude
status: beta
tags:
  - laser
  - EnergyDeposition
  - ray-tracing
  - 几何光学
  - 逆韧致吸收
  - ICF
  - sourceTerm
  - 3T
---

# 激光（EnergyDeposition）单元总览

> **TL;DR**：FLASH 把一束激光表示成 N 根几何光线（ray），从 lens 椭圆面射向 target 椭圆面，沿途被等离子体按逆韧致吸收沉积到 cell 的电子内能（`EELE_VAR`）上。空间分布由 cross-section 函数控制，时间波形由 pulse 表控制，两者解耦。

---

## 1. 物理原理

### 1.1 模型本质：几何光线追踪 + 逆韧致吸收

FLASH 激光模块**不解波动方程**，而采用几何光学近似：

- 一束激光被离散成 N 根独立光线（ray）
- 每根 ray 携带一份功率 $P_{\text{ray}}$，沿直线以光速 c 传播
- 在每个 cell 内，功率按逆韧致吸收率 ν 衰减：$dP = -\nu P \, ds$
- 衰减的能量加到该 cell 的电子内能 `EELE_VAR`

**适用条件**：
- 等离子体尺度 ≫ 波长（几何光学有效）
- 等离子体不过密（$N_e < N_c$，否则 ray 被反射）
- 弱相对论（强度不是极高，无相对论自生磁场等相对论效应）

**主循环源码**：`source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition.F90:160-351`

```fortran
! EnergyDeposition.F90:160-351 主循环（节选）
call ed_laserIOCheckWrite (passSplitDriver)              ! :160
call ed_checkReuseDepo (reuseDepo,laserIsOn)             ! :165  激光是否开
! ...
call ed_createRays (blockCount, blockList, timeStep, timeSimulation)  ! :235 创建 ray
! ...
call ed_traceRays  (timeStep)                            ! :305  追踪 + 吸收
! ...
call ed_updatePlasma (blockCount, blockList, scaleFact)  ! :348  沉积到 EELE_VAR + Eos
```

### 1.2 临界密度与反射

临界密度 $N_c$ 由波长 λ 决定：

$$N_c = \frac{\pi m_e c^2}{e^2 \lambda^2}$$

**源码实现**：`LaserRaysCreate/ed_createRays3DRec.F90:419, 476`

```fortran
! ed_createRays3DRec.F90:419
criticalDensityFactor = ed_electronMass * PI / (ed_electronCharge * ed_electronCharge)
! ed_createRays3DRec.F90:476
beamCriticalDensity = criticalDensityFactor * frequency * frequency
```

其中 `frequency = c / wavelength`（`LaserBeams/ed_setupBeams.F90:384`），wavelength 在 `:375` 已从 μm 转换为 cm。

**反射机制**：ray 进入 domain 时如果初始 cell 的 $N_e > N_c$，ray 不进入，标记为 `RAY_OUTDOMAIN`（详见 `LaserRayTrace/CellAverage/ed_traceBlockRays2DCyl3D.F90` 中 `vnewFactor = 1.0 - Nele * rayCritDensInv` 的处理）。

### 1.3 折射

ray 经过电子密度梯度 $\nabla N_e$ 时方向被偏转，由 `ed_gradOrder` 控制：

| `ed_gradOrder` | 行为 |
|---|---|
| 1 | 不计算折射（直线传播） |
| 2 | 一阶差分计算 $\nabla N_e$，更新 ray 方向 |

源码：`LaserRayTrace/CellAverage/ed_traceBlockRays*.F90`（按几何分支不同文件）。

### 1.4 逆韧致吸收率

每单位长度的功率衰减率 ν（`LaserUtilities/ed_inverseBremsstrahlungRate.F90:60-67`）：

$$\nu = \frac{Z (2 e^2 N_e)^2}{3 N_c} \sqrt{\frac{2\pi}{m_e (k_B T_e)^3}} \ln \Lambda$$

其中：
- $Z$ — 电离度（来自 `ZBAR_VAR`）
- $N_e$ — 电子数密度（来自 `NELE_VAR` 或从 `DENS_VAR` + EOS 计算）
- $T_e$ — 电子温度（来自 `TELE_VAR`）
- $\ln \Lambda$ — 库仑对数

**调用位置**：`LaserRayTrace/CellAverage/ed_traceBlockRays{1DRec,2DRec,3DRec,2DCyl3D,3DCyl}.F90`，每根 ray 在每个 cell 内调用一次。

**沉积到 cell 的功率** = ray 在 cell 内走过的有效长度 × ν × ray 当前功率。

### 1.5 能量沉积到等离子体

沉积完成后，`ed_updatePlasma`（`LaserUtilities/ed_updatePlasma.F90:85-100`）把累积的 depo 加到电子内能：

```fortran
! LaserUtilities/ed_updatePlasma.F90:85-100
if (ed_depoVarIsPerMass) then
   solnData (EELE_VAR,ib:ie,jb:je,kb:ke) = &
       solnData (EELE_VAR,ib:ie,jb:je,kb:ke) &
     + solnData (ed_depoVar,ib:ie,jb:je,kb:ke)         ! per-mass 模式
else
   ! per-volume 模式：除以 DENS_VAR
   solnData (EELE_VAR,...) = solnData (EELE_VAR,...) &
       + solnData (ed_depoVar,...) / solnData (DENS_VAR,...)
end if
! ...
call Eos_wrapped (MODE_DENS_EI_GATHER, blkLimits, blockID)   ! 重算 T_e, T_i, P
```

→ **必须用 multi-temp EOS**（`+mtmmmt`），否则没有独立的 `EELE_VAR`。

---

## 2. 设计动机

### 2.1 为什么是 ray tracing 而不是波动方程

| 方面 | ray tracing | 波动方程 / FDTD |
|---|---|---|
| 计算成本 | N 根 ray（典型 10³-10⁴）| 6D 相空间网格（极贵）|
| 物理范围 | 几何光学（波长 ≪ 尺度） | 全波动光学 |
| 临界密度反射 | 自然处理 | 自然处理 |
| 折射 | 自然处理 | 自然处理 |
| 衍射/干涉 | **不能** | 能 |
| 适用场景 | ICF / OIC / 实验室等离子体 | 短脉冲 / 强场 / 高次谐波 |

FLASH 的目标场景（ICF、激光烧蚀、等离子体加热）都在几何光学范围内，所以选了 ray tracing。

### 2.2 为什么分 lens/target 两个椭圆

**几何概念**：每束激光由两个椭圆截面定义——
- **lens 椭圆**：光源/透镜面（如 ICF 靶场最外层透镜组的位置）
- **target 椭圆**：靶面（如 ICF 胶囊表面、平面靶表面）

每根 ray 从 lens 面上一个采样点出发，指向 target 面上对应采样点。

**为什么这样设计**：
- 自然支持聚焦（lens 大、target 小 → 锥形入射）
- 自然支持发散（反之）
- 椭圆而非圆形 → 支持非对称打靶（SSD 相位板、椭圆光斑、线聚焦）
- lens 和 target 椭圆参数独立 → 几何灵活性最大

### 2.3 为什么 grid 和 cross-section 解耦

这是最容易让新用户误解的地方：

| 概念 | 控制什么 | 不控制什么 |
|---|---|---|
| **cross-section 函数** | 每根 ray 携带的功率 → **分布形状** | ray 物理位置 |
| **grid type** | ray 物理位置 → **采样精度** | 分布形状 |

**自动归一化保证**（`LaserBeams/ed_beam3DGridWeightRadial.F90:158-184` + `LaserRaysCreate/ed_createRays3DRec.F90:979-994`）：

```
gridWeight       = Σ_i  w(x_i, y_i)            # setup 时一次性算好
powerFraction_i  = w(x_i, y_i) / gridWeight    # 每根 ray 占的功率份额
P_ray_i          = P_beam(t) × powerFraction_i # 每根 ray 实际携带的功率
```

→ **不论 grid 怎么撒点、不论 cross-section 函数选什么，Σ P_ray 永远严格等于 P_beam**。

**实际意义**：
- 想改分布形状 → 改 cross-section 参数（`ed_crossSectionFunctionType_<i>` + `ed_gaussian*_<i>`）
- 看到分布图有噪点 → 增大 `ed_numberOfRays_<i>`，**不要**改 cross-section
- 选 grid 类型 → 看光斑形状（圆形用 `radial2D`，矩形用 `rectangular2D`）

---

## 3. 在 FLASH 中的位置

### 3.1 调用链

```
Driver/Driver_evolveFlash.F90                          (主循环)
   ↓
Driver/DriverMain/Driver_sourceTerms.F90:44-69         (sourceTerms 调度)
   ↓
call EnergyDeposition(blockCount, blockList, dt, dr_simTime, pass)
   ↓
EnergyDepositionMain/Laser/EnergyDeposition.F90:160-351  (激光主入口)
   ├─ ed_checkReuseDepo       :165   laser 是否开 / 是否复用上次沉积
   ├─ ed_createRays           :235   按 grid 生成 ray 位置 + 分配功率
   ├─ ed_traceRays            :305   追踪 + 逆韧致吸收
   └─ ed_updatePlasma         :348   沉积到 EELE_VAR + Eos_wrapped
```

**调用顺序**（在 `Driver_sourceTerms.F90:46-69`）：

```fortran
#ifdef DRIVER_EDEARLY
  call EnergyDeposition(...)        ! 排在 sourceTerms 序列前
#endif
  call Polytrope(...)
  call Stir(...)
  call Turb_calc(...)
  call Flame_step(...)
  call Burn(...)
  call Heat(...)
  call Heatexchange(...)
  call Cool(...)
  call Ionize(...)
#ifndef DRIVER_EDEARLY
  call EnergyDeposition(...)        ! 默认：排在 Heatexchange/Cool 之后
#endif
  call Deleptonize(...)
```

→ 默认激光排在所有热/燃/冷源之后，对 3T 模型更稳。需要改顺序可在 setup 时定义 `DRIVER_EDEARLY`。

### 3.2 setup 期机制

`+laser` 等价于 `+unit physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser`。setup.py 会：

1. 解析 `Laser/Config` 的 `genLines` Python 代码（位置：`Laser/Config` 第 140-260 行附近）
2. 根据 setup 变量动态生成所有 `ed_*` runtime parameter 槽位
3. 把 `PPDEFINE ED_MAXBEAMS` / `ED_MAXPULSES` / `ED_MAXPULSESECTIONS` 写入 `Flash.h`

**关键 setup 变量**（在 setup 命令行设置，编译期生效）：

| setup 变量 | 默认 | 作用 |
|---|---|---|
| `ed_maxBeams` | 6 | 决定生成多少个 `ed_<prop>_<i>` 参数槽 |
| `ed_maxPulses` | 5 | 决定生成多少条 pulse 的 (time, power) 段 |
| `ed_maxPulseSections` | 20 | 每条 pulse 最多多少段 |
| `threadRayTrace` | false | 是否 OpenMP 并行 ray tracing |

→ 想用 > 6 束激光必须在 setup 命令加 `ed_maxBeams=N`，否则 `ed_setupBeams` abort。

### 3.3 单元内部结构

```
source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/
├── Config                              # genLines Python，生成所有 ed_* 参数
├── EnergyDeposition.F90                # 主入口（每步调用）
├── EnergyDeposition_init.F90           # 初始化（读所有参数 + 调 setupPulses/Beams/Rays）
├── EnergyDeposition.h                  # RAY_POSX 等常量定义
├── LaserComm/                          # 跨 processor 传 ray
├── LaserIO/                            # ray 轨迹输出
├── LaserBeams/                         # beam 几何 + cross-section
│   ├── ed_setupBeams.F90              #    读 beam 参数 + 白名单验证
│   ├── ed_computeBeamPower.F90        #    由 P(t) 计算当前步平均功率
│   ├── ed_beamCrossSectionFunctions.F90  # ★ 6 种截面函数（自定义改这里）
│   ├── ed_beam3DGridWeight{Radial,Square,RecBeam,Statistical}.F90  # gridWeight 归一化
│   └── ed_beamsInfo3DRec.F90          #    按 gridType 分发 setup/weight
├── LaserPulses/ed_setupPulses.F90      # 读 pulse 时间/功率表
├── LaserRaysCreate/                    # 按 grid 生成 ray
│   ├── ed_createRays{1DRec,2DRec,3DRec,3DCyl,2DCyl3D}.F90
│   └── ed_initializeRays.F90
├── LaserRayTrace/                      # ray 追踪 + 吸收
│   ├── CellAverage/                   #    cell-average 插值（默认）
│   │   └── ed_traceBlockRays{1D,2D,3D,2DCyl3D,3DCyl}*.F90
│   └── CubicInterpolation/            #    三次插值（更精确，更贵）
└── LaserUtilities/                     # 辅助
    ├── ed_inverseBremsstrahlungRate.F90  # ★ 逆韧致率公式
    ├── ed_updatePlasma.F90              # ★ 沉积到 EELE_VAR + Eos
    ├── ed_printBeamsData.F90            # 调试日志
    └── ed_extractBeamsData.F90          # 运行时改 beam 参数
```

带 ★ 的文件是**自定义/扩展点**——改截面函数改 `ed_beamCrossSectionFunctions.F90`，改吸收公式改 `ed_inverseBremsstrahlungRate.F90`。

---

## 4. 关键概念图

```
        lens 椭圆面                       target 椭圆面（你关心的截面）
       (光源 / 透镜)                         (功率密度分布的"画板")
       ┌────────────┐                      ┌────────────┐
       │  • • • • • │  ─── N 根 ray ───→  │  • • • • • │
       │  • • • • • │      沿直线 c        │  • • • • • │
       │  • • • • • │                      │  • • • • • │
       └────────────┘                      └────────────┘
        ed_lens{X,Y,Z}                      ed_target{X,Y,Z}
        ed_lensSemiAxisMajor                ed_targetSemiAxis{Major,Minor}
                   │
                   ↓
       沿途每根 ray 被等离子体按逆韧致吸收 ν
                   │
                   ↓
       每根 ray 沉积能量到经过的 cell
                   │
                   ↓
       累积到 depo 变量（per-mass 或 per-volume）
                   │
                   ↓
       ed_updatePlasma: depo → EELE_VAR
                   │
                   ↓
       Eos_wrapped 重算 T_e, T_i, P 等
```

---

## 5. 与其他单元的耦合

| 方向 | 关联单元 | 关系 | 源码位置 |
|---|---|---|---|
| **上游** | `Driver/Driver_sourceTerms` | 每个时间步调用一次 | `DriverMain/Driver_sourceTerms.F90:56,68` |
| **上游** | `Grid/*` | 取 blockList、cell 数据、guard cells | `EnergyDeposition.F90` 调用 `Grid_*` |
| **上游** | `Eos/EosMain/multiTemp` | **必须**用 3T EOS（`+mtmmmt`），因为沉积目标是 `EELE_VAR` | `EosMain/multiTemp/Multitype/Config` |
| **下游** | `Eos_wrapped` | 沉积后调用，重算 T_e/T_i/P | `LaserUtilities/ed_updatePlasma.F90:104` |
| **平行** | `physics/materialProperties/Opacity` | **不耦合**——激光用逆韧致公式，**不读 opacity 表** | — |
| **平行** | `physics/RadTrans/MGD` | **独立**——多群扩散是另一套机制，与激光不共享 ray | — |
| **平行** | `Multispecies/` | 通过 species 名绑定（如 `cham`, `targ1`），影响 Z 和 N_e | `Multispecies_*` |

**重要误解警告**：
- 改 opacity 表**不会**改激光吸收率（激光用逆韧致公式，与 opacity 表无关）
- 激光与 MGD **没有共享能量**（两套独立的辐射机制）
- 激光能量只加到 `EELE_VAR`，不加到 `ERAD_VAR` 或 `EION_VAR`

---

## 6. 已知陷阱 / 与手册的差异

### 6.1 pulse 功率单位是 W（瓦特），不是 erg/s

- **手册可能写**：CGS 单位 erg/s
- **源码实际**：parfile 写 **W（焦耳/秒）**，在 `ed_setupPulses.F90:104, 125` 内自动乘 `ed_Joule2erg` 转 erg/s

```fortran
! LaserPulses/ed_setupPulses.F90:104
ed_pulses (1,pulse) % pulsePower = pulsePower * ed_Joule2erg   ! Watt (J/s) -> erg/s
```

→ **用户在 parfile 里写 W**（如 `ed_power_1_2 = 3.0e11` 表示 300 GW）。

### 6.2 wavelength 单位是 μm（微米），不是 cm 或 nm

- **手册可能写**：cm 或 nm
- **源码实际**：parfile 写 **μm**，在 `ed_setupBeams.F90:375` 自动乘 `ed_microns2cm` 转 cm

```fortran
! LaserBeams/ed_setupBeams.F90:375
wavelength = wavelength * ed_microns2cm   ! convert to cm
```

→ **用户在 parfile 里写 μm**（如 `ed_wavelength_1 = 1.053` 表示钕玻璃激光 1.053 μm）。

### 6.3 lens/target 坐标和 gaussian 参数都是 cm

- 所有空间坐标（`ed_lens{X,Y,Z}`, `ed_target{X,Y,Z}`, `ed_lensSemiAxisMajor`, `ed_targetSemiAxis{Major,Minor}`, `ed_gaussianRadius*`, `ed_gaussianCenter*`）单位都是 **cm**
- 常见陷阱：写成 μm 导致光斑极小、所有 ray 落在域外、depo 为 0

### 6.4 grid vs cross-section 解耦（最常见的概念错误）

- 直觉：grid 决定分布形状
- 实际：**cross-section 决定形状，grid 只决定采样精度**
- 自动归一化（§2.3）保证换 grid 不改形状

详见 [[knowledge/internals]] §3。

### 6.5 2D RZ 必须开 `ed_laser3Din2D`

不开的话 ray 只在 (r,z) 平面内运动，模拟不出真实锥形入射，导致吸收率严重偏低。

```fortran
! ed_setupBeams.F90:118-132（节选）
beams3D = ...
   .or. (ed_gridGeometry == GRID_2DCYLINDRICAL .and. ed_laser3Din2D)
```

→ 2D RZ 算例**必须**设 `ed_laser3Din2D = .true.` + `ed_laser3Din2DwedgeAngle = <小角度>`。

### 6.6 radial2D grid 中心没有 ray

`ed_beam3DGridSetupRadial.F90` 注释明说："there is no grid point at the center"。如果用 super-Gaussian（α 很大）+ `radial2D`，中心功率密度会被低估。

→ 解法：换 `square2D`，或加大 ray 数，或用 `gaussianInverse2D` 故意做环形。

---

## 7. 延伸阅读

### 7.1 本 skill 内的关联条目

- [[knowledge/params]] — 全部 `ed_*` 参数完整字典
- [[knowledge/internals]] — EnergyDeposition 内部调用图（含 mermaid 图）
- [[knowledge/recipes]] — 4 个典型 parfile 配置（圆光斑/椭圆/环形/多束）
- [[knowledge/pitfalls]] — 常见错误与排查（ed_maxBeams、单位陷阱、abort 字符串）

### 7.2 跨 skill 关联

- `flash-driver` skill — `Driver_sourceTerms` 调用顺序的完整解释
- `flash-eos` skill — multiTemp EOS 和 `EELE_VAR` 的机制
- `flash-source-reader` skill — 想看具体函数实现时调用
- `flash-pitfall-finder` skill — 调试 abort 时调用

### 7.3 外部资料

- Birdsall & Langdon, *Plasma Physics via Computer Simulation*（几何光学 + PIC 背景）
- Lindl, *Phys. Plasmas 2, 3933 (1995)* — ICF 物理背景
- Atzeni & Meyer-ter-Vehn, *The Physics of Inertial Fusion* — 激光等离子体相互作用章节

### 7.4 手册章节

FLASH 4.8 User Guide, EnergyDeposition unit（待 Phase 1 Week 2 按工作流转换后补精确页码和章节号）。

---

## 8. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-06-17 | 初始创建（从 `LASER_SETUP_GUIDE.md` 抽取"物理原理 + 设计动机"部分，按 `knowledge-entry` 模板重写，补 12 个源码锚点） | claude |
