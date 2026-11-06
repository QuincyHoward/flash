---
title: 激光（EnergyDeposition）参数完整字典
skill: flash-laser
category: params
source_anchors:
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config:1-146
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config:148-210
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config:212-328
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserPulses/ed_setupPulses.F90:74-145
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:160-300
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:336-355
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition_init.F90:80-200
manual_ref: "FLASH 4.8 User Guide, EnergyDeposition runtime parameters (待 Phase 1 Week 2 转换)"
created: 2026-06-17
last_verified: 2026-06-17
verifier: claude
status: beta
tags:
  - laser
  - parameters
  - runtime-parameters
  - ed_
  - parfile
  - Config
---

# 激光参数完整字典

> **TL;DR**：FLASH 激光单元通过 `Laser/Config` 的 Python `genLines` 动态生成约 38 个全局参数 + 每条 pulse 的 (time, power) 段 + 每束 beam 的 30 个属性参数。所有参数都是 runtime parameter（写在 `flash.par` 里），少数关键的（`ed_maxBeams/Pulses/PulseSections`）是 setup 变量（写在 `./setup` 命令行）。

---

## 1. 参数生成机制

> 详细原理见 [[knowledge/overview]] §3.2，这里只讲参数层面的影响。

**源码**：`source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config:1-328`

`Config` 文件分三段：

| 段 | 位置 | 生成内容 |
|---|---|---|
| **静态全局参数** | `:1-146` | 38 个固定名字的 runtime parameter（如 `useEnergyDeposition`, `ed_gradOrder`） |
| **Pulse 参数生成** | `:148-210`（Python 循环） | 对每条 pulse 生成 `ed_numberOfSections_<p>` + 每个 section 的 `ed_time_<p>_<s>` / `ed_power_<p>_<s>` |
| **Beam 参数生成** | `:212-328`（Python 循环） | 对每束 beam 生成 30 个属性参数（如 `ed_wavelength_<i>`, `ed_lensX_<i>`） |

**关键设计**：beam 和 pulse 的参数槽位数量由 setup 变量决定：

| setup 变量 | 默认 | 作用 |
|---|---|---|
| `ed_maxBeams` | 6 | 生成多少套 beam 参数槽 |
| `ed_maxPulses` | 5 | 生成多少套 pulse 参数槽 |
| `ed_maxPulseSections` | 20 | 每条 pulse 最多生成多少 (time, power) 段 |

源码：`Config:182-191` 和 `Config:228-232`。

→ **想用 > 6 束激光或 > 5 条 pulse 必须在 setup 命令加相应变量**，重新 setup + make。运行时改 parfile 无效（参数槽不存在）。

---

## 2. 全局参数（38 个）

### 2.1 总开关与几何

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `useEnergyDeposition` | BOOLEAN | **true** | 激光总开关。**注意**：Config 默认是 `true`（`Config:108`），但必须在 parfile 显式设为 `.true.` 才会真的生效；如果 setup 时没引入 Laser unit，这个参数根本不存在 |
| `ed_laser3Din2D` | BOOLEAN | false | 2D RZ 几何下用 3D ray（**2D RZ 算例必须设 .true.**） |
| `ed_laser3Din2DwedgeAngle` | REAL | 0.0 | 3D-in-2D 模式的楔形对称角（度，< 180，常用 0.1） |
| `threadRayTrace` | BOOLEAN | false | ray tracing 是否 OpenMP 并行（setup 变量 `threadRayTrace` 控制，见 `Config:140-145`） |

### 2.2 物理精度控制

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_gradOrder` | INTEGER | 2 [1,2] | 折射梯度阶：1=直线传播（不折射），2=一阶差分折射 |
| `ed_cellWallThicknessFactor` | REAL | 1.0e-06 | ray 离 cell 壁的最小距离（防数值误差，单位是 cell 边长的分数） |
| `ed_cellStepTolerance` | REAL | 1.0e-06 | ray 一段路径允许的 cell 误差（cell 边长的分数） |
| `ed_powerStepTolerance` | REAL | 1.0e-06 | ray 一段路径允许的功率误差（当前功率的分数） |
| `ed_velocityStepTolerance` | REAL | 1.0e-06 | ray 一段路径允许的速度误差 |
| `ed_rayZeroPower` | REAL | 1.0e-06 | 功率低于此值（erg/s）的 ray 被视为 0 功率，停止追踪 |
| `ed_cellTimeEnergyDeposition` | BOOLEAN | false | true 时按 ray 在 cell 内停留时间算沉积（而非按路径长度） |
| `ed_RungeKuttaMethod` | STRING | "CashKarp45" | ray tracing 的 RK 方法（一般不改） |
| `ed_cubicInterpolationZeroDerv` | BOOLEAN | false | 立方插值时是否强制顶点导数为 0（单调性） |
| `ed_enforcePositiveTele` | BOOLEAN | true | 强制 T_e 梯度 ≥ 0（避免非物理负梯度） |
| `ed_enforcePositiveNele` | BOOLEAN | true | 强制 N_e 梯度 ≥ 0 |

### 2.3 梯度分量开关（一般不改）

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_computeGradNeleR` | BOOLEAN | true | 计算 N_e 的 r 分量梯度（cylindrical） |
| `ed_computeGradNeleP` | BOOLEAN | true | 计算 N_e 的 φ 分量梯度 |
| `ed_computeGradNeleT` | BOOLEAN | true | 计算 N_e 的 θ 分量梯度（spherical） |
| `ed_computeGradNeleX` | BOOLEAN | true | 计算 N_e 的 x 分量梯度（cartesian） |
| `ed_computeGradNeleY` | BOOLEAN | true | y 分量 |
| `ed_computeGradNeleZ` | BOOLEAN | true | z 分量 |

### 2.4 域扩展与对称性

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_adjustBeamsTargetIntensity` | BOOLEAN | false | 调整 1D/2D beams 的 target 强度以模拟圆形 3D beam |
| `ed_adjustBySymmetryX` | BOOLEAN | false | X 方向对称性补偿（多 counting 修正） |
| `ed_adjustBySymmetryY` | BOOLEAN | false | Y 方向 |
| `ed_adjustBySymmetryZ` | BOOLEAN | false | Z 方向 |
| `ed_beamsCheckExpandX` | BOOLEAN | false | `ed_beamsCheck` 中是否对 X 边界 reflect/periodic 扩展域 |
| `ed_beamsCheckExpandY` | BOOLEAN | false | Y 方向同上 |
| `ed_beamsCheckExpandZ` | BOOLEAN | false | Z 方向同上 |
| `ed_createRaysExpandX` | BOOLEAN | false | `ed_createRays` 中是否对 X 边界扩展 |
| `ed_createRaysExpandY` | BOOLEAN | false | Y 方向同上 |
| `ed_createRaysExpandZ` | BOOLEAN | false | Z 方向同上 |

### 2.5 沉积变量与复用

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_depoVarName` | STRING | "depo" | 沉积率存储的变量名（对应 `DEPO_VAR`） |
| `ed_depoReuseMaxSteps` | INTEGER | -1 | 复用上次沉积的最大步数（-1=禁用，0=仅同一步内复用，N=跨 N 步复用） |
| `ed_irradVarName` | STRING | "lase" | 激光辐射场能量密度变量名（对应 `LASE_VAR`，per-volume） |

### 2.6 容量与诊断

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_maxRayCount` | INTEGER | 100 | **每 processor** 最多能容纳的 ray 数。实际 ray 数远超此值时会 abort。setup 时可用 `ed_maxRayCount=N` 改 |
| `ed_numberOfBeams` | INTEGER | -1 | **运行时**告诉代码"实际用几束"（≤ `ed_maxBeams`）。在 parfile 设 |
| `ed_numberOfPulses` | INTEGER | -1 | 同上，pulse 数（≤ `ed_maxPulses`） |
| `ed_printMain` | BOOLEAN | false | 调试：打印 main laser info 到日志 |
| `ed_printBeams` | BOOLEAN | false | 调试：打印每束 beam 详情 |
| `ed_printPulses` | BOOLEAN | false | 调试：打印每条 pulse 详情 |
| `ed_printRays` | BOOLEAN | false | 调试：打印每根 ray 详情（**慎用**，输出量极大） |
| `ed_saveOutOfDomainRays` | BOOLEAN | false | 出域 ray 是否保留（诊断用） |
| `ed_useRayCoords2GetBlockID` | BOOLEAN | false | true 时 Grid 用 ray 坐标决定 blockID（更精确但更慢） |

---

## 3. Pulse 参数（每条 pulse 一套）

**命名规则**：`ed_<property>_<p>`，其中 `<p>` 是 pulse 编号（1 到 `ed_maxPulses`）。

| 参数 | 类型 | 默认 | 单位 | 含义 |
|---|---|---|---|---|
| `ed_numberOfSections_<p>` | INTEGER | -1 | — | 第 p 条 pulse 的 (time, power) 段数（≥2） |
| `ed_time_<p>_<s>` | REAL | -1.0 | **s** | 第 p 条 pulse 第 s 段的时间（s 从 1 到 `ed_numberOfSections_<p>`） |
| `ed_power_<p>_<s>` | REAL | -1.0 | **W**（瓦特） | 第 p 条 pulse 第 s 段的功率。**注意：不是 erg/s**，源码 `ed_setupPulses.F90:104, 125` 内自动乘 `ed_Joule2erg` 转 erg/s |

**约束**（`LaserPulses/ed_setupPulses.F90:74-145`）：
- `numberOfSections_<p>` ≥ 2（至少一对起止时刻）
- `ed_time_<p>_<s>` 必须严格递增（违反 → `Driver_abortFlash: Wrong time order`）
- `ed_power_<p>_<s>` 不能为负（违反 → `Negative pulse power specified`）

**P(t) 解释**：FLASH 把连续的 (time, power) 段**线性插值**成 P(t) 函数，在每步内梯形积分求平均功率（源码：`LaserBeams/ed_computeBeamPower.F90:122-156`）。

**典型 pulse 形状**（梯形，ICF 常用）：

```fortran
ed_numberOfPulses     = 1
ed_numberOfSections_1 = 4
ed_time_1_1 = 0.0       ; ed_power_1_1 = 0.0          # 起始 0
ed_time_1_2 = 0.1e-9    ; ed_power_1_2 = 3.0e11       # 100 ps 上升沿 → 300 GW
ed_time_1_3 = 6.0e-9    ; ed_power_1_3 = 3.0e11       # 5.9 ns 平顶
ed_time_1_4 = 6.1e-9    ; ed_power_1_4 = 0.0          # 100 ps 下降沿
```

---

## 4. Beam 参数（每束 30 个属性）

**命名规则**：`ed_<property>_<i>`，其中 `<i>` 是 beam 编号（1 到 `ed_maxBeams`）。

> 下面分组列出 30 个属性，每组按用途聚合。

### 4.1 Beam 标识与绑定

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_pulseNumber_<i>` | INTEGER | -HUGE(1) | 第 i 束绑哪条 pulse（1 到 `ed_numberOfPulses`） |
| `ed_wavelength_<i>` | REAL | -HUGE(1.0) | 波长 λ，**单位 μm**（不是 cm 或 nm！）。源码 `ed_setupBeams.F90:375` 自动转 cm |

### 4.2 Lens 面（光源）几何

| 参数 | 类型 | 默认 | 单位 | 含义 |
|---|---|---|---|---|
| `ed_lensX_<i>` | REAL | -HUGE(1.0) | cm | lens 椭圆中心 X 坐标 |
| `ed_lensY_<i>` | REAL | -HUGE(1.0) | cm | Y 坐标 |
| `ed_lensZ_<i>` | REAL | -HUGE(1.0) | cm | Z 坐标 |
| `ed_lensSemiAxisMajor_<i>` | REAL | -HUGE(1.0) | cm | lens 椭圆半长轴 |

注意：lens 椭圆只有"半长轴"参数，**没有半短轴**——lens 默认是圆形。如果需要椭圆 lens，要靠 target 椭圆 + 几何变换实现。

### 4.3 Target 面（光斑）几何

| 参数 | 类型 | 默认 | 单位 | 含义 |
|---|---|---|---|---|
| `ed_targetX_<i>` | REAL | -HUGE(1.0) | cm | target 椭圆中心 X 坐标（**光斑中心**） |
| `ed_targetY_<i>` | REAL | -HUGE(1.0) | cm | Y 坐标 |
| `ed_targetZ_<i>` | REAL | -HUGE(1.0) | cm | Z 坐标 |
| `ed_targetSemiAxisMajor_<i>` | REAL | -HUGE(1.0) | cm | target 半长轴 a（必须 > 0） |
| `ed_targetSemiAxisMinor_<i>` | REAL | -HUGE(1.0) | cm | target 半短轴 b（**a ≥ b**，违反 abort） |

### 4.4 椭圆定向

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_semiAxisMajorTorsionAxis_<i>` | STRING | " " | target 主轴绕哪个坐标轴扭转：`x` / `y` / `z`（其他值 abort） |
| `ed_semiAxisMajorTorsionAngle_<i>` | REAL | -HUGE(1.0) | 度 | 扭转角（0-360，源码 `ed_setupBeams.F90:373` 自动转弧度） |

→ 用于非对称打靶：椭圆光斑在 target 面上的方向。

### 4.5 Ray 数量与布点（grid）

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_numberOfRays_<i>` | INTEGER | -HUGE(1) | 这束的总 ray 数（采样精度，**不改变分布形状**） |
| `ed_gridType_<i>` | STRING | " " | ray 布点方式，**白名单**（`Config:311`）：`rectangular2D` / `square2D` / `delta2D` / `radial2D` / `statistical2D` / `regular1D` / `statistical1D` / ` ` |
| `ed_gridnRadialTics_<i>` | INTEGER | -HUGE(1) | (radial2D) 径向环数 |
| `ed_gridnAngularTics_<i>` | INTEGER | -HUGE(1) | (radial2D) 角向切片数（≤0 表示自动算） |
| `ed_gridnSemiAxisMajorTics_<i>` | INTEGER | -HUGE(1) | (rectangular2D) 主轴 tic 数 |
| `ed_gridnSemiAxisMinorTics_<i>` | INTEGER | -HUGE(1) | (rectangular2D) 副轴 tic 数 |
| `ed_gridDeltaSemiAxisMajor_<i>` | REAL | -HUGE(1.0) | (delta2D) 主轴位置 |
| `ed_gridDeltaSemiAxisMinor_<i>` | REAL | -HUGE(1.0) | (delta2D) 副轴位置 |

**gridType 白名单源码**：`LaserBeams/ed_setupBeams.F90:345-355`（3D 分支）。其他字符串会 abort。

### 4.6 截面权重函数（控制空间分布）

| 参数 | 类型 | 默认 | 单位 | 含义 |
|---|---|---|---|---|
| `ed_crossSectionFunctionType_<i>` | STRING | " " | — | 截面权重函数类型，**白名单**（`ed_setupBeams.F90:336-343`）：`uniform` / `radialweighted` / `gaussian2D` / `gaussianInverse2D`（3D 分支）；2D 分支允许 `uniform` / `gaussian1D` / `gaussianInverse1D` |
| `ed_gaussianExponent_<i>` | REAL | -HUGE(1.0) | — | 高斯指数 α（公式 `exp(-r^(2α))`，α=1 标准高斯，α=4 平顶 super-Gaussian） |
| `ed_gaussianRadiusMajor_<i>` | REAL | -HUGE(1.0) | cm | 主轴方向 1/e 半径 R_x |
| `ed_gaussianRadiusMinor_<i>` | REAL | -HUGE(1.0) | cm | 副轴方向 1/e 半径 R_y |
| `ed_gaussianCenterMajor_<i>` | REAL | 0.0 | cm | 主轴方向中心偏移 C_x（target 局部坐标） |
| `ed_gaussianCenterMinor_<i>` | REAL | 0.0 | cm | 副轴方向中心偏移 C_y |

**gaussian2D 公式**（源码 `LaserBeams/ed_beamCrossSectionFunctions.F90:255-261`）：

$$w(x, y) = \exp\left( -\left[\left(\frac{x - C_x}{R_x}\right)^2 + \left(\frac{y - C_y}{R_y}\right)^2\right]^\alpha \right)$$

(x, y) 是 ray 在 **target 椭圆局部坐标系**下的位置（原点在椭圆中心，x 沿主轴）。

### 4.7 数值与边界

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `ed_adjustInitialRaySpeed_<i>` | BOOLEAN | true | 是否按初始 cell 的 N_e 调整 ray 初速（折射修正） |
| `ed_ignoreBoundaryCondition_<i>` | BOOLEAN | false | ray 是否忽略域边界条件 |
| `ed_radial3Dcontraction_<i>` | BOOLEAN | false | 3D beam 是否做径向收缩分布 |

---

## 5. 参数默认值的"哨兵"约定

Config 里很多参数默认值是 `-HUGE(1.0)` 或 `-HUGE(1)` 或 `-1`，这是**"未设置"哨兵**：

| 哨兵值 | 出现在 | 含义 |
|---|---|---|
| `-HUGE(1.0)` | 所有必须用户指定的 REAL 参数（如 `ed_wavelength`, `ed_lensX`, `ed_gaussianExponent`） | "用户没设" → `ed_setupBeams` 在 `:160-300` 不会主动检查，但后续计算会用这个无效值，导致结果错乱。**用户必须在 parfile 显式设这些** |
| `-HUGE(1)` | 所有必须用户指定的 INTEGER 参数（如 `ed_numberOfRays`, `ed_pulseNumber`） | 同上 |
| `-1` | `ed_numberOfBeams`, `ed_numberOfPulses`, `ed_numberOfSections_<p>`, `ed_time_*`, `ed_power_*` | 同上，但 `ed_setupBeams/Pulses` 会显式检查（`< 1` 时 abort） |

→ **parfile 必须显式设置所有非默认的 beam/pulse 参数**。漏设一个典型表现是 abort 或数值错乱。

---

## 6. setup 变量 vs runtime parameter 对比

| 类型 | 在哪写 | 何时生效 | 改了要不要重新 setup+make |
|---|---|---|---|
| **setup 变量** | `./setup` 命令行 | 编译期 | **要** |
| **runtime parameter** | `flash.par` | 运行时 | 不要（只改 parfile） |

**易混淆点**：

| 名字相似 | setup 变量（编译期） | runtime parameter（运行时） |
|---|---|---|
| 最大 beam 数 | `ed_maxBeams=6`（在 `./setup` 命令行） | `ed_numberOfBeams=2`（在 parfile，≤ `ed_maxBeams`） |
| 最大 pulse 数 | `ed_maxPulses=5` | `ed_numberOfPulses=1`（≤ `ed_maxPulses`） |
| 最大 ray 数/proc | `ed_maxRayCount=200`（setup 命令行） | — |
| 线程 ray tracing | `threadRayTrace=true`（setup 命令行） | — |

→ **"max" 开头的都是 setup 变量**，"numberOf" 开头的都是 runtime parameter。

---

## 7. 常见错误（参数相关）

| 错误信息 | 原因 | 修复 |
|---|---|---|
| `ed_setupBeams: Not enough beam runtime parameters` | beam 数 > `ed_maxBeams` 默认 6 | setup 时加 `ed_maxBeams=N` |
| `ed_setupBeams: No beam defined!` | `ed_numberOfBeams` 未设或 < 1 | 在 parfile 设 `ed_numberOfBeams = N` |
| `ed_setupBeams: invalid 3D beam cross section function type!` | `ed_crossSectionFunctionType_<i>` 拼错 | 对照 §4.6 白名单 |
| `ed_setupBeams: invalid 3D beam grid type!` | `ed_gridType_<i>` 拼错 | 对照 §4.5 白名单 |
| `ed_setupBeams: target semiaxes lengths out of order (major < minor)!` | `targetSemiAxisMajor < Minor` | 交换二者 |
| `ed_setupPulses: No pulse defined!` | `ed_numberOfPulses` 未设或 < 1 | 在 parfile 设 |
| `ed_setupPulses: Wrong time order for pulse sections!` | `ed_time_<p>_<s>` 没严格递增 | 检查时间序列 |
| `ed_setupPulses: Negative pulse power specified!` | `ed_power_<p>_<s>` < 0 | 功率不能负 |
| `ed_setupPulses: No timeframe for current pulse!` | `ed_numberOfSections_<p>` < 2 | pulse 至少 2 段 |
| `ed_createRays*: Too many rays! No storage` | 实际 ray 数 > `ed_maxRayCount` | setup 时加 `ed_maxRayCount=N`，或减小 `numberOfRays` |

更多踩坑见 [[knowledge/pitfalls]]。

---

## 8. 已知陷阱 / 与手册的差异

### 8.1 `useEnergyDeposition` 默认值矛盾

- `Config:108` 默认 `true`
- 但**实际跑算例时必须在 parfile 显式设 `.true.`**
- 原因：如果 setup 时没引入 Laser unit，这个参数根本不存在；引入后即使默认 true，也建议显式写以便配置可读

### 8.2 pulse 功率单位是 W，不是 erg/s

- 见 [[knowledge/overview]] §6.1
- parfile 写 W，源码自动转

### 8.3 wavelength 单位是 μm

- 见 [[knowledge/overview]] §6.2
- parfile 写 μm（如 `1.053`），不要写 `1.053e-4` cm

### 8.4 lens 半轴只有 Major，没有 Minor

- `ed_lensSemiAxisMinor_<i>` **不存在**
- lens 默认是圆形（Major = 半径）
- 想做椭圆 lens 要靠 target 椭圆 + 几何变换

### 8.5 gridType 字符串大小写敏感

- 必须全小写：`radial2D` ✅，`Radial2D` ❌
- 末尾必须 `2D` 或 `1D`，不是 `2d` / `1d`

### 8.6 crossSectionFunctionType 白名单依赖几何

- 3D 模拟（含 2DCylindrical + `ed_laser3Din2D=.true.`）允许：`uniform`, `radialweighted`, `gaussian2D`, `gaussianInverse2D`
- 纯 2D 模拟允许：`uniform`, `gaussian1D`, `gaussianInverse1D`
- 跨用会 abort（源码 `ed_setupBeams.F90:285-292, 336-343`）

### 8.7 `ed_numberOfRays` 是 beam 局部，不是全局总 ray 数

- 总 ray 数 ≈ Σ_i `ed_numberOfRays_<i>` × 对称倍数
- 受 `ed_maxRayCount`（每 processor）限制
- 不是"整个模拟的 ray 总数"

---

## 9. 延伸阅读

- [[knowledge/overview]] — 物理原理与设计动机
- [[knowledge/internals]] — Config 的 genLines 机制如何被 setup.py 解析
- [[knowledge/recipes]] — 完整 parfile 片段（含所有必要参数）
- [[knowledge/pitfalls]] — 参数相关踩坑

外部：
- `Laser/Config` 源码（328 行）— 真正权威的参数定义
- `bin/setup.py` — genLines Python 代码如何被解析
- `bin/Readme.SetupVars` — setup 变量机制文档

---

## 10. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-06-17 | 初始创建（从 `Laser/Config` 完整提取 38 全局参数 + pulse/beam 参数生成机制；标注单位陷阱和白名单） | claude |
