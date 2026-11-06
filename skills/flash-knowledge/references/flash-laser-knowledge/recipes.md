---
title: 激光（EnergyDeposition）典型 parfile 配置集
skill: flash-laser
category: recipes
source_anchors:
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/Config:182-232
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:160-300
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_setupBeams.F90:336-355
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserPulses/ed_setupPulses.F90:74-145
  - source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/LaserBeams/ed_beamCrossSectionFunctions.F90:124-170
  - cases/LaserSlab/flash.par
  - cases/Sunliang_laser_CH/flash.par
manual_ref: "FLASH 4.8 User Guide, EnergyDeposition examples (待 Phase 1 Week 2 转换)"
created: 2026-06-17
last_verified: 2026-06-17
verifier: claude
status: beta
tags:
  - laser
  - recipes
  - parfile
  - 配置
  - ICF
  - super-Gaussian
  - 多束
---

# 激光典型 parfile 配置集

> **TL;DR**：4 个由易到难的完整 parfile 配置 + 1 个补充。从"最小可运行"到"6 束对称打靶"，每个都可直接抄改。所有配置都基于 2D RZ + 3T + MGD + Laser 的 `laser_CH` 类 setup。

---

## 1. 物理原理

> 详见 [[knowledge/overview]] 和 [[knowledge/params]]。本条目只讲"怎么配"。

---

## 2. 通用 setup 命令（所有 recipes 共享）

所有 recipes 假设你的 problem 是 `laser_CH`（参考 `source/Simulation/SimulationMain/Sunliang_laser_CH/`，可按需重命名）。基础 setup 命令：

```bash
./setup laser_CH -2d -auto +pm4dev -geometry=cylindrical \
    -nxb=16 -nyb=16 +mtmmmt +laser +mgd +uhd3t \
    species=cham,targ1,targ2,targ3 mgd_meshgroups=6 \
    [-parfile=<your_parfile>] [-objdir=cases/<your_objdir>]
```

**变体**：
- **Recipe 4**（6 束）需要加 `ed_maxBeams=6`
- 想用 thread：加 `threadRayTrace=true`
- 想调试：加 `-debug`

---

## 3. Recipe 1：最小可运行配置

> **目标**：用最少的参数让激光算例**跑通**，让用户理解每行参数干啥。**不开 LaserIO，不优化 ray 数**。

### 3.1 适用场景

- 第一次配置 FLASH 激光的人
- 想快速验证 setup/make/run 流程是否正常
- 调试 EOS/Opacity 表是否能加载（激光本身要算 N_e、T_e）

### 3.2 parfile（激光段）

把下面这段加到 `<your_case>/flash.par` 的 `##### LASER PARAMETERS #####` 处：

```fortran
# ===== 总开关 =====
useEnergyDeposition       = .true.
ed_laser3Din2D            = .true.            # 2D RZ 必须
ed_laser3Din2DwedgeAngle  = 0.1               # 楔角（度）
ed_gradOrder              = 2                 # 一阶折射

# ===== Pulse 1: 简单 4 段梯形（1 ns, 100 GW 峰值）=====
ed_numberOfPulses     = 1
ed_numberOfSections_1 = 4
ed_time_1_1 = 0.0       ; ed_power_1_1 = 0.0
ed_time_1_2 = 0.1e-9    ; ed_power_1_2 = 1.0e11
ed_time_1_3 = 0.9e-9    ; ed_power_1_3 = 1.0e11
ed_time_1_4 = 1.0e-9    ; ed_power_1_4 = 0.0

# ===== Beam 1: 单束圆光斑标准高斯 =====
ed_numberOfBeams = 1
ed_pulseNumber_1              = 1
ed_wavelength_1               = 1.053         # μm（钕玻璃）

# 几何（lens 在 z=12 cm 处，target 在原点）
ed_lensX_1 = 0.0  ; ed_lensY_1 = 0.0  ; ed_lensZ_1 = 12.0    # cm
ed_lensSemiAxisMajor_1        = 0.5           # cm（lens 口径 1 cm）
ed_targetX_1 = 0.0 ; ed_targetY_1 = 0.0 ; ed_targetZ_1 = 0.0  # cm
ed_targetSemiAxisMajor_1      = 0.01          # cm（光斑半径 100 μm）
ed_targetSemiAxisMinor_1      = 0.01          # cm（a=b 圆形）
ed_semiAxisMajorTorsionAxis_1 = "x"
ed_semiAxisMajorTorsionAngle_1= 0.0

# 标准高斯（α=1），ray 数少（512 够跑通）
ed_numberOfRays_1             = 512
ed_gridType_1                 = "radial2D"
ed_gridnRadialTics_1          = 16
ed_crossSectionFunctionType_1 = "gaussian2D"
ed_gaussianExponent_1         = 1.0
ed_gaussianRadiusMajor_1      = 0.01          # cm（=target 半径）
ed_gaussianRadiusMinor_1      = 0.01
ed_gaussianCenterMajor_1      = 0.0
ed_gaussianCenterMinor_1      = 0.0
```

### 3.3 关键参数解释

| 参数 | 为什么这么设 |
|---|---|
| `ed_laser3Din2D = .true.` | 2D RZ 几何必须；不开则 ray 只在 (r,z) 平面，吸收率严重偏低 |
| `ed_wavelength_1 = 1.053` | μm 单位（不是 cm/nm）。钕玻璃激光基频 |
| `ed_lensSemiAxisMajor_1 = 0.5` | lens 在域外（z=12 cm vs 域 ~3 cm），口径大小不影响光斑 |
| `ed_targetSemiAxisMajor_1 = 0.01` | cm 单位（100 μm）。决定光斑最大半径 |
| `ed_gaussianExponent_1 = 1.0` | α=1 是标准高斯；α=4 是 super-Gaussian（见 Recipe 2） |
| `ed_gaussianRadius*_1 = 0.01` | 1/e 半径 = target 半径，分布填满光斑 |
| `ed_numberOfRays_1 = 512` | 最小可运行数量；正式跑要 ≥ 2048 |
| `ed_gridnRadialTics_1 = 16` | radial2D 的环数；16 × 自动角向 ≈ 512 ray |

### 3.4 预期结果

跑完应该看到：
- `depo` 变量在 target 附近（z ≈ 0, r < 100 μm）非零
- 中心功率密度最高，向外高斯衰减
- `TELE_VAR` 在 target 附近升高（电子被加热）
- 总沉积能量 ≈ 入射能量 × 50-80%（取决于密度/温度）

### 3.5 检查清单

- [ ] setup 成功（无 abort）
- [ ] make 成功（无 link error）
- [ ] flash4 启动后日志含 `[EnergyDeposition_init]` 输出
- [ ] 第一个 plotfile 的 `depo` 非零
- [ ] `TELE_VAR` 在 target 区域升高

---

## 4. Recipe 2：ICF 直接驱动 super-Gaussian

> **目标**：实际科研主力配置。**平顶光斑 + 大 ray 数 + 开 LaserIO 可视化**。

### 4.1 适用场景

- ICF 直接驱动模拟（如 OMEGA、NIF 直接驱动实验复现）
- 需要平顶强度分布（中心平台 + 陡边）
- 需要分析 ray 轨迹和吸收率

### 4.2 parfile（激光段）

```fortran
# ===== 总开关 =====
useEnergyDeposition       = .true.
ed_laser3Din2D            = .true.
ed_laser3Din2DwedgeAngle  = 0.1
ed_gradOrder              = 2
ed_enforcePositiveTele   = .true.           # 防非物理负梯度
ed_enforcePositiveNele   = .true.

# 调试（推荐打开）
ed_printMain   = .true.
ed_printPulses = .true.
ed_printBeams  = .true.

# ===== Pulse 1: ICF 梯形脉冲（100 ps 上升 + 6 ns 平顶 + 100 ps 下降，300 GW）=====
ed_numberOfPulses     = 1
ed_numberOfSections_1 = 4
ed_time_1_1 = 0.0       ; ed_power_1_1 = 0.0
ed_time_1_2 = 0.1e-9    ; ed_power_1_2 = 3.0e11
ed_time_1_3 = 6.0e-9    ; ed_power_1_3 = 3.0e11
ed_time_1_4 = 6.1e-9    ; ed_power_1_4 = 0.0

# ===== Beam 1: 圆光斑平顶 super-Gaussian =====
ed_numberOfBeams = 1
ed_pulseNumber_1              = 1
ed_wavelength_1               = 1.053

ed_lensX_1 = 0.0  ; ed_lensY_1 = 0.0  ; ed_lensZ_1 = 12.0
ed_lensSemiAxisMajor_1        = 0.5
ed_targetX_1 = 0.0 ; ed_targetY_1 = 0.0 ; ed_targetZ_1 = 0.0
ed_targetSemiAxisMajor_1      = 0.01
ed_targetSemiAxisMinor_1      = 0.01
ed_semiAxisMajorTorsionAxis_1 = "x"
ed_semiAxisMajorTorsionAngle_1= 0.0

# 平顶 super-Gaussian（α=4）+ 大 ray 数
ed_numberOfRays_1             = 4096
ed_gridType_1                 = "radial2D"
ed_gridnRadialTics_1          = 64
ed_crossSectionFunctionType_1 = "gaussian2D"
ed_gaussianExponent_1         = 4.0           # ★ α=4 平顶
ed_gaussianRadiusMajor_1      = 0.01          # 1/e 半径 = target 半径
ed_gaussianRadiusMinor_1      = 0.01
ed_gaussianCenterMajor_1      = 0.0
ed_gaussianCenterMinor_1      = 0.0

# ===== LaserIO（可视化 ray 轨迹）=====
ed_useLaserIO                  = .true.
ed_laserIOMaxNumberOfPositions = 10000        # 每根 ray 最多 N 个轨迹点
ed_laserIOMaxNumberOfRays      = 128          # 最多可视化多少根 ray
ed_laserIORayFrequency         = 1            # 每步都写
```

### 4.3 关键参数解释

| 参数 | 为什么这么设 |
|---|---|
| `ed_gaussianExponent_1 = 4.0` | α=4 是 ICF 标准平顶 super-Gaussian；α=6 更方；α=8 几乎 top-hat |
| `ed_gaussianRadius*_1 = 0.01` | 与 target 半径相同，让分布在椭圆内填满 |
| `ed_numberOfRays_1 = 4096` | ICF 算例推荐 ≥ 4096；少了沉积图有颗粒感 |
| `ed_gridnRadialTics_1 = 64` | 64 环 × 自动角向（约 64）≈ 4096 ray |
| `ed_useLaserIO = .true.` | 必须！否则没法验证 ray 路径是否合理 |
| `ed_laserIOMaxNumberOfRays = 128` | 全部 ray 写出来文件太大；128 根足够可视化光路 |

### 4.4 预期结果

- `depo` 在 target 面呈**平顶**分布（中心一段近似恒定，边缘陡降）
- 总吸收率约 60-80%（取决于靶密度和厚度）
- LaserIO 数据可在 yt 中画出 ray 路径

### 4.5 检查清单（在 Recipe 1 基础上额外）

- [ ] `depo` 在光斑内**平顶**（不是高斯尖峰）→ 验证 α=4 生效
- [ ] plotfile 含 LaserIO 数据集
- [ ] 总沉积能量 = 入射能量 × 吸收率（容差 ±5%）
- [ ] `TELE_VAR` 峰值在合理范围（< 5 keV，否则可能数值问题）

---

## 5. Recipe 3：椭圆光斑 + 偏心 + 扭转

> **目标**：展示非对称打靶配置。`target a ≠ b` + 偏心 + 主轴扭转。

### 5.1 适用场景

- 实验复现（实测近场图是椭圆）
- SSD（smoothing by spectral dispersion）相位板模拟
- 故意非对称加热（如线聚焦、条带烧蚀）

### 5.2 parfile（激光段，差异部分）

完整 pulse + 总开关同 Recipe 2，**只列差异**：

```fortran
# ===== Beam 1: 椭圆光斑 + 偏心 + 扭转 =====
ed_numberOfBeams = 1
ed_pulseNumber_1              = 1
ed_wavelength_1               = 1.053

ed_lensX_1 = 0.0  ; ed_lensY_1 = 0.0  ; ed_lensZ_1 = 12.0
ed_lensSemiAxisMajor_1        = 0.5

# 椭圆 target: a=150 μm, b=80 μm
ed_targetX_1 = 0.0 ; ed_targetY_1 = 0.0 ; ed_targetZ_1 = 0.0
ed_targetSemiAxisMajor_1      = 0.0150         # cm（150 μm）
ed_targetSemiAxisMinor_1      = 0.0080         # cm（80 μm）

# 主轴绕 z 轴扭转 45°（让长轴沿 x=y 对角线）
ed_semiAxisMajorTorsionAxis_1 = "z"
ed_semiAxisMajorTorsionAngle_1= 45.0           # 度

# 椭圆高斯：主副轴 1/e 半径不同
ed_numberOfRays_1             = 4096
ed_gridType_1                 = "radial2D"
ed_gridnRadialTics_1          = 64
ed_crossSectionFunctionType_1 = "gaussian2D"
ed_gaussianExponent_1         = 2.0            # α=2 介于高斯和平顶之间
ed_gaussianRadiusMajor_1      = 0.0150         # 主轴 1/e 半径 = target 主半轴
ed_gaussianRadiusMinor_1      = 0.0080         # 副轴 1/e 半径 = target 副半轴

# 偏心：高斯中心在 (30 μm, 0)，相对 target 椭圆中心
ed_gaussianCenterMajor_1      = 0.0030         # cm（30 μm）
ed_gaussianCenterMinor_1      = 0.0

ed_useLaserIO                  = .true.
ed_laserIOMaxNumberOfPositions = 10000
ed_laserIOMaxNumberOfRays      = 128
```

### 5.3 关键参数解释

| 参数 | 为什么这么设 |
|---|---|
| `ed_targetSemiAxisMajor_1 = 0.0150` | a=150 μm，椭圆长半轴 |
| `ed_targetSemiAxisMinor_1 = 0.0080` | b=80 μm，**必须 a ≥ b**（违反 abort） |
| `ed_semiAxisMajorTorsionAxis_1 = "z"` | 主轴绕 z 旋转（2D RZ 中 z 是对称轴） |
| `ed_semiAxisMajorTorsionAngle_1 = 45.0` | 度（不是弧度）；源码 `ed_setupBeams.F90:374` 自动转 |
| `ed_gaussianRadiusMajor_1 = 0.0150` | **必须和 target 主半轴同比**，否则分布被椭圆边界截断 |
| `ed_gaussianCenterMajor_1 = 0.0030` | 偏心 30 μm；局部坐标，0 = 椭圆中心 |

### 5.4 注意事项

- **a ≥ b 是硬约束**：源码 `ed_setupBeams.F90:318` 检查，违反 abort
- **扭转角单位是度**：写 `45.0` 不是 `0.785`；源码内转弧度
- **偏心量限制**：`|gaussianCenter| + gaussianRadius < targetSemiAxis`，否则能量会"溢出"椭圆外被丢弃

### 5.5 检查清单

- [ ] `depo` 分布是**椭圆**而非圆
- [ ] 椭圆长轴方向符合扭转角设定（沿 x=y 对角线）
- [ ] 强度中心偏离 target 中心 30 μm

---

## 6. Recipe 4：6 束对称打靶

> **目标**：多束配置。需要 setup 期 `ed_maxBeams=6`，6 束沿周向均匀排布指向中心。

### 6.1 适用场景

- ICF 直接驱动（如 OMEGA 60 束、NIF 192 束的简化模型）
- Hohlraum 间接驱动（激光打入黑腔内壁）
- 任何需要球对称/柱对称加热的场景

### 6.2 setup 命令（关键改动）

```bash
./setup laser_CH -2d -auto +pm4dev -geometry=cylindrical \
    -nxb=16 -nyb=16 +mtmmmt +laser +mgd +uhd3t \
    species=cham,targ1,targ2,targ3 mgd_meshgroups=6 \
    ed_maxBeams=6 \
    -parfile=example_6beams.par -objdir=cases/laser_6beams
```

**关键**：`ed_maxBeams=6` 是 setup 变量，决定生成多少个 `ed_<prop>_<i>` 参数槽。不加这个，parfile 里写 `ed_wavelength_7` 会报"unknown parameter"。

### 6.3 parfile（激光段，pulse 同 Recipe 2）

```fortran
# ===== 6 束配置 =====
ed_numberOfBeams = 6

# 6 束的 lens 沿 z=12 cm 圆周均匀排布（半径 0.3 cm）
# 方位角: 0°, 60°, 120°, 180°, 240°, 300°
# 全部 target 都指向 (0,0,0)
# 用 ed_X_{1..6} 模板批量设置

# --- 所有 beam 共享的参数（逐束复制）---
# ed_pulseNumber_<i>              = 1
# ed_wavelength_<i>               = 1.053
# ed_lensZ_<i>                    = 12.0
# ed_lensSemiAxisMajor_<i>        = 0.1
# ed_targetX_<i>                  = 0.0 ; ed_targetY_<i> = 0.0 ; ed_targetZ_<i> = 0.0
# ed_targetSemiAxisMajor_<i>      = 0.01 ; ed_targetSemiAxisMinor_<i> = 0.01
# ed_numberOfRays_<i>             = 2048
# ed_gridType_<i>                 = "radial2D"
# ed_gridnRadialTics_<i>          = 64
# ed_crossSectionFunctionType_<i> = "gaussian2D"
# ed_gaussianExponent_<i>         = 4.0
# ed_gaussianRadiusMajor_<i>      = 0.01 ; ed_gaussianRadiusMinor_<i> = 0.01
# ed_semiAxisMajorTorsionAxis_<i> = "x"
# ed_semiAxisMajorTorsionAngle_<i>= 0.0

# --- 每束的 lens 横向位置（差异部分）---
ed_pulseNumber_1 = 1
ed_lensX_1 = 0.300  ; ed_lensY_1 = 0.000   # 0°

ed_pulseNumber_2 = 1
ed_lensX_2 = 0.150  ; ed_lensY_2 = 0.260   # 60°

ed_pulseNumber_3 = 1
ed_lensX_3 = -0.150 ; ed_lensY_3 = 0.260   # 120°

ed_pulseNumber_4 = 1
ed_lensX_4 = -0.300 ; ed_lensY_4 = 0.000   # 180°

ed_pulseNumber_5 = 1
ed_lensX_5 = -0.150 ; ed_lensY_5 = -0.260  # 240°

ed_pulseNumber_6 = 1
ed_lensX_6 = 0.150  ; ed_lensY_6 = -0.260  # 300°

# --- 每束的其他参数（重复 6 次）---
# 完整 parfile 应该把每个 ed_<prop>_<i> 都写出。这里展示 1 个完整 + 5 个差异
# 实际写法见 examples/multi-beam-6.par（在 Phase 1 Week 2 补）

ed_useLaserIO                  = .true.
ed_laserIOMaxNumberOfPositions = 10000
ed_laserIOMaxNumberOfRays      = 256         # 6 束 × ~42 ray/束
```

### 6.4 关键参数解释

| 参数 | 为什么这么设 |
|---|---|
| `ed_maxBeams=6`（setup） | **必须**在 setup 命令设置；运行时改无效 |
| `ed_numberOfBeams = 6`（parfile） | 告诉代码实际用 6 束；必须 ≤ ed_maxBeams |
| 6 束 lens 沿圆周等分 | 实现"对称打靶"；每束方位差 60° |
| 所有 target 指向 (0,0,0) | 收敛到靶心；可改为环面（Hohlraum） |
| 每束 2048 ray | 6 × 2048 = 12288 总 ray；注意 `ed_maxRayCount` 限制 |

### 6.5 注意事项（容易踩的坑）

1. **`ed_maxRayCount`**：默认 100/proc，6 束 × 2048 ray 远超。**setup 时要加 `ed_maxRayCount=N`**（按 `6 × 2048 / num_procs × 2` 估）
2. **`ed_lensZ_<i>` 必须相同**：让 6 束在同一平面，否则失去对称性
3. **2D RZ + 3D-in-2D 的限制**：多束在 wedge 内会被对称采样。要真正多方位打靶，考虑真 3D 模拟
4. **每束参数都要复制**：`ed_wavelength_1` 到 `ed_wavelength_6` 都要写（除非默认值合理）。FLASH 不会从 beam 1 推断到 beam 6

### 6.6 检查清单

- [ ] setup 命令含 `ed_maxBeams=6`
- [ ] make 后 `cases/laser_6beams/flash.par` 含 6 套 `ed_*_<i>` 参数
- [ ] 日志（开 `ed_printBeams=.true.`）打印 6 个 beam 的详情
- [ ] `depo` 在 target 中心叠加（六束汇聚）
- [ ] 总沉积能量 ≈ 6 × 单束沉积（验证每束都在工作）

---

## 7. 补充：环形分布（`gaussianInverse2D`）

> 不单独成 recipe，因为实现简单。**仅在需要中心暗、亮环分布时使用**。

### 7.1 parfile 片段

在 Recipe 2 基础上替换 cross-section 段：

```fortran
ed_crossSectionFunctionType_1 = "gaussianInverse2D"   # ★ 环形
ed_gaussianExponent_1         = 2.0
ed_gaussianRadiusMajor_1      = 0.005                  # cm（亮峰在 ~50 μm）
ed_gaussianRadiusMinor_1      = 0.005
ed_targetSemiAxisMajor_1      = 0.010                  # cm（必须 > gaussianRadius）
ed_targetSemiAxisMinor_1      = 0.010
```

### 7.2 公式

`gaussianInverse2D`（源码 `ed_beamCrossSectionFunctions.F90:263-281`）：

$$w(x, y) = \exp\left( +\left[\left(\frac{x - C_x}{R_x}\right)^2 + \left(\frac{y - C_y}{R_y}\right)^2\right]^\alpha \right)$$

注意是**正号**（不是负号），所以中心是凹陷（w=1）、边缘指数发散。

### 7.3 关键约束

- **`targetSemiAxis > gaussianRadius`**：否则分布会被椭圆边界截断到极大值，能量集中在椭圆边缘
- 适合做"中心减压"的 ICF 对称化研究
- 大多数场景不需要，默认用 `gaussian2D`

---

## 8. 通用检查清单（每个 recipe 跑完都该检查）

### 8.1 启动期检查

```
□ flash4 启动无 abort
□ 日志含 [EnergyDeposition_init] 输出
□ ed_printBeams=.true. 时日志列出每束的 wavelength/lens/target/cross-section
□ ed_printPulses=.true. 时日志列出每条 pulse 的 (time, power) 段
```

### 8.2 运行期检查

```
□ plotfile 正常输出（plotFileIntervalStep 合理）
□ depo 变量在 target 附近非零
□ TELE_VAR 在 target 区域升高
□ 总能量近似守恒（容差 < 5%）
□ 日志无 ffpe-trap 或 NaN 警告
```

### 8.3 物理合理性检查

| 指标 | 期望范围 | 异常处理 |
|---|---|---|
| 激光吸收率 | 30-90%（取决于密度/波长） | < 30% 检查 N_e 是否过低；> 95% 检查是否数值饱和 |
| TELE_VAR 峰值 | < 10 keV（典型 ICF） | > 10 keV 可能是 grid 太粗或 N_e 算错 |
| depo 总和 | ≈ pulse 总能量 × 吸收率（±10%） | 不等则检查 ray 是否落域外 |
| 光斑形状 | 与 `crossSectionFunctionType` 一致 | 不一致则检查 `gridWeight` 是否算对 |

---

## 9. 已知陷阱（recipe 层面）

### 9.1 单位混淆（最常见）

| 参数 | 正确单位 | 容易写错 |
|---|---|---|
| `ed_wavelength_<i>` | **μm** | cm（1.053e-4）或 nm（1053） |
| `ed_lens{X,Y,Z}_<i>` | **cm** | mm（10.0）或 μm（10000） |
| `ed_target{X,Y,Z}_<i>` | **cm** | 同上 |
| `ed_targetSemiAxis*_<i>` | **cm** | μm（100） |
| `ed_gaussianRadius*_<i>` | **cm** | μm |
| `ed_gaussianCenter*_<i>` | **cm** | μm |
| `ed_time_<p>_<s>` | **s** | ns（0.1e-9 写成 0.1） |
| `ed_power_<p>_<s>` | **W** | erg/s（自动转，但用户容易混淆） |
| `ed_semiAxisMajorTorsionAngle_<i>` | **度** | 弧度（0.785） |

### 9.2 setup 变量 vs runtime parameter 混淆

| 想改的 | 在哪改 | 改完要不要重新 setup+make |
|---|---|---|
| beam 总数 | `./setup ... ed_maxBeams=N` | **要** |
| pulse 总数 | `./setup ... ed_maxPulses=N` | **要** |
| pulse 段数上限 | `./setup ... ed_maxPulseSections=N` | **要** |
| ray 数/proc 上限 | `./setup ... ed_maxRayCount=N` | **要** |
| 实际用几束 | parfile `ed_numberOfBeams=N` | 不要 |
| 实际用几条 pulse | parfile `ed_numberOfPulses=N` | 不要 |
| 某束的 wavelength | parfile `ed_wavelength_<i>=X` | 不要 |

### 9.3 2D RZ 几何的特殊性

- 必须开 `ed_laser3Din2D=.true.`
- `ed_lensZ` 是对称轴方向，`ed_lensX/Y` 是垂直对称轴的横向
- wedge 角决定对称采样范围；多束在 wedge 内会被镜像
- 想做真正的多方位打靶，建议用 3D Cartesian 几何

### 9.4 多束配置的 ray 数预算

总 ray 数 = Σ_i `ed_numberOfRays_<i>` × 对称倍数

受 `ed_maxRayCount`（每 processor）限制：

```
ed_maxRayCount ≥ Σ numberOfRays / num_procs × 2
```

→ 6 束 × 2048 ray / 4 proc × 2 = 6144，至少要 `ed_maxRayCount=6144`（实际留余量取 8192）

---

## 10. 延伸阅读

### 10.1 本 skill 内
- [[knowledge/overview]] — 为什么这么配的物理动机
- [[knowledge/params]] — 每个参数的精确含义和单位
- [[knowledge/internals]] — 配置如何在源码内被处理
- [[knowledge/pitfalls]] — 配置错误的诊断与修复

### 10.2 跨 skill
- `flash-setup-builder` skill — 自动生成 setup 命令
- `flash-case-runner` skill — 跑这些配置
- `flash-result-analyzer` skill — 跑完检查物理合理性

### 10.3 真实参考 case
- `cases/LaserSlab/flash.par` — 单束 laser slab 算例
- `cases/Sunliang_laser_CH/flash.par` — 多物种 CH laser 算例
- `source/Simulation/SimulationMain/LaserSlab/Config` — LaserSlab 的 setup 选项

---

## 11. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-06-17 | 初始创建（4 个核心 recipes + 1 个补充：最小可运行 / ICF super-Gaussian / 椭圆偏心 / 6 束对称 + 环形补充） | claude |
