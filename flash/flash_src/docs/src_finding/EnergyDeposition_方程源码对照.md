# 激光能量沉积（EnergyDeposition）源码与方程对照

> 本文档追踪 FLASH 中激光能量沉积从物理方程到 Fortran 代码的实现路径。
>
> 参考文件：
> - 主驱动: `source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition.F90`
> - 光束功率: `.../Laser/LaserBeams/ed_computeBeamPower.F90`
> - 光线追迹: `.../Laser/LaserRayTrace/CellAverage/ed_traceRays*.F90`
> - 光线创建: `.../Laser/LaserRays/ed_createRays.F90`
> - 等离子体更新: `.../Laser/Laser_3T/ed_updatePlasma3T.F90`
> - 文档: `docs/flash4_ug_4p8.md` 第14章

---

## 目录

1. [物理方程](#1-物理方程)
2. [模块架构](#2-模块架构)
3. [Step 1：时间脉冲 → 光束功率（ed_computeBeamPower）](#3-step-1时间脉冲--光束功率ed_computebeampower)
4. [Step 2：光线创建（ed_createRays）](#4-step-2光线创建ed_createrays)
5. [Step 3：光线追迹与能量沉积（ed_traceRays）](#5-step-3光线追迹与能量沉积ed_tracerays)
6. [逆轢射吸收公式的详细实现](#6-逆轢射吸收公式的详细实现)
7. [Step 4：等离子体能量更新（ed_updatePlasma）](#7-step-4等离子体能量更新ed_updateplasma)
8. [完整数据流与代码行号对应](#8-完整数据流与代码行号对应)

---

## 1. 物理方程

### 文档中的方程（第14章，式14.7b）

FLASH 文档第14章描述的 3T 电子能量方程中的沉积项：

$$\left.\frac{\partial (\rho e_{\text{ele}})}{\partial t}\right|_{\text{laser}} = Q_{\text{las}}$$

其中 $Q_{\text{las}}$ 是激光沉积在电子上的能量源项（单位：erg/cm³/s）。

### 几何光学近似

FLASH 使用**几何光学**（射线追踪）方法计算激光能量沉积。假设激光沿直线（或折射路径）传播，每个光束由大量"光线"（ray）表示，每条光线携带一定功率。当光线穿过等离子体时，通过逆轢射吸收（inverse bremsstrahlung）将能量交给电子：

$$Q_{\text{las}}(\mathbf{x}) = \sum_{\text{rays}} \frac{dP_{\text{ray}}}{dV} \cdot f_{\text{deposition}}(\mathbf{x})$$

其中 $f_{\text{deposition}}$ 取决于当地的密度、温度和激光频率。

---

## 2. 模块架构

```
EnergyDepositionMain/Laser/
│
├── EnergyDeposition.F90     ← 主驱动 ─── 整体流程控制
│
├── LaserBeams/
│   └── ed_computeBeamPower.F90  ← 脉冲→功率
│
├── LaserRays/
│   ├── ed_createRays.F90        ← 光线初始化
│   ├── ed_initRays.F90          ← 光线参数设置
│   └── ed_depositRays.F90       ← 能量沉积计算
│
├── LaserRayTrace/               ← 光线追迹（多种实现）
│   ├── CellAverage/
│   │   ├── ed_traceRays1DRec.F90
│   │   ├── ed_traceRays2DRec.F90
│   │   ├── ed_traceRays2DCyl3D.F90
│   │   ├── ed_traceRays3DRec.F90
│   │   └── ed_traceRays3DCyl.F90
│   └── CubicInterpolation/
│       └── ...
│
├── Laser_3T/
│   └── ed_updatePlasma3T.F90    ← 3T 等离子体更新
│
└── Laser_1T/
    └── ed_updatePlasma1T.F90    ← 1T 等离子体更新
```

---

## 3. Step 1：时间脉冲 → 光束功率（ed_computeBeamPower）

### 文件
`LaserBeams/ed_computeBeamPower.F90`

### 功能

根据用户定义的[时间, 功率]脉冲分段线性数据，计算当前时间步内的**平均光束功率**。

### 核心算法

```fortran
!! ed_computeBeamPower.F90 行34-156

subroutine ed_computeBeamPower(timeStep, timeSimulation, pulseNumber, beamPower)
  ! 输入: timeStep = 当前时间步 Δt
  !        timeSimulation = 当前模拟时间 t^n
  !        pulseNumber = 脉冲编号
  ! 输出: beamPower = 平均光束功率 P̄

  timeMin = timeSimulation                                    ! 行73
  timeMax = timeSimulation + timeStep                         ! 行74
  ! ↑ 时间窗 = [t^n, t^n+Δt]

  ! 对脉冲的每个分段（t1→t2, 功率p1→p2）:
  ! 计算在时间窗内的重叠部分:
  do n = 1, numberOfSections
     !! 梯形面积: ∫p(t)dt                             (行139-144)
     slope = (p2 - p1) / (t2 - t1)                    ! 行139: 分段斜率
     pa = p1 + slope * (ta - t1)                      ! 行141: 左端点功率
     pb = p2 - slope * (t2 - tb)                      ! 行142: 右端点功率
     area = 0.5 * (pa + pb) * (tb - ta)               ! 行144: 梯形面积 = 此分段传递的能量
     energy = energy + area                            ! 行146: 累积能量
  end do

  beamPower = energy / timeStep                        ! 行156: 平均功率 = 总能量/Δt
```

### 与方程的关系

$Q_{\text{las}}$ 的宏观输入就是光束功率 $P(t)$。该子程序将用户定义的脉冲波形 $P(t)$ 在时间步上平均：

$$\bar{P} = \frac{1}{\Delta t} \int_{t^n}^{t^n+\Delta t} P(t) \, dt$$

---

## 4. Step 2：光线创建（ed_createRays）

### 文件
`LaserRays/ed_createRays.F90`

### 功能

根据光束几何参数（焦点位置、光斑形状、发散角、功率分布）创建一组光线（rays），每条光线携带 $\bar{P}/N_{\text{rays}}$ 的功率。

### 调用位置

```fortran
!! EnergyDeposition.F90 行234-236

call ed_createRays(blockCount, blockList, timeStep, timeSimulation)
```

### 光线数据结构

```fortran
!! EnergyDeposition_data.F90 中定义
type ray
   real :: pos(1:MDIM)      ! 位置
   real :: dir(1:MDIM)      ! 方向 (单位矢量)
   real :: power             ! 当前功率 (开始 = 总功率/Nrays)
   real :: deltaPower        ! 已沉积功率
   ...
end type
```

---

## 5. Step 3：光线追迹与能量沉积（ed_traceRays）

### 文件
`LaserRayTrace/CellAverage/ed_traceRays*Rec.F90`（具体实现取决于维度）

### 主循环（EnergyDeposition.F90）

```fortran
!! EnergyDeposition.F90 行303-319

call ed_commInitComm()           ! 初始化光线通信

activeRays = .true.
do while (activeRays)
   call ed_traceRays(timeStep)    ! 行305: 追迹+沉积能量
   call ed_saveRays()             ! 行306: 保存状态
   call IO_writeRays(...)         ! 行309: IO输出（可选）
   call ed_updateRays(moveRays)   ! 行316: 更新位置
   call ed_commIsTransportDone(isTransportDone)
   activeRays = .not. isTransportDone
end do
```

### 核心物理

光线追迹在每个网格单元内计算**逆轢射吸收**：

$$P_{\text{dep}} = P_{\text{ray}} \cdot \left(1 - e^{-\kappa_{\text{ib}} \cdot \Delta s}\right)$$

其中：
- $\kappa_{\text{ib}}$ — 逆轢射吸收系数（依赖 $\rho$, $T_e$, 激光频率 $\omega$）
- $\Delta s$ — 光线在单元内的路径长度

沉积能量存入 `ed_depoVar` 变量。

---

## 6. 逆轢射吸收公式的详细实现

> 这是激光能量沉积中**最核心的物理计算**——决定光线穿过等离子体时到底沉积多少能量。
>
> 参考文件：
> - `LaserUtilities/ed_inverseBremsstrahlungRate.F90` — 逆轢射碰撞频率
> - `LaserUtilities/ed_CoulombFactor.F90` — 库仑对数
> - `LaserRayTrace/CellAverage/ed_traceBlockRays1DRec.F90` — 1D 光线追迹实现

### 6.1 完整的计算链

光线在每个网格单元内的能量沉积经过以下计算链：

```
  等离子体状态            单条光线
  Z̄, ρ, Tₑ, ω, ω_pe           P_ray
       │                         │
       ▼                         ▼
  ┌─────────────────────────────────────┐
  │ ① 库仑对数 Λ (ed_CoulombFactor)    │
  │   Λ = (1.5 / Z̄·e³) · √((kTₑ)³/πNe) │
  │   lnΛ = max(ln(Λ), 1.0)            │
  └──────────────┬──────────────────────┘
                 │ lnΛ
                 ▼
  ┌─────────────────────────────────────┐
  │ ② 逆轢射频率 ν (ed_inverseBrems-   │
  │   strahlungRate)                    │
  │   ν = (4/3)·√(2π/mₑ)·(Z̄·e⁴/Nc)·   │
  │       (Ne²/(kTₑ)^(3/2))·lnΛ        │
  └──────────────┬──────────────────────┘
                 │ ν [Hz]
                 ▼
  ┌─────────────────────────────────────┐
  │ ③ 光学路径积分 I = ∫ν·dt           │
  │   简单版本: I = ν·Δt (行408)        │
  │   高斯版本: 2点Gauss-Legendre求积   │
  │   (行427-445)                       │
  └──────────────┬──────────────────────┘
                 │ I
                 ▼
  ┌─────────────────────────────────────┐
  │ ④ 功率衰减因子 e^{-I} (行449)      │
  │   P_loss = P_ray·(1 - e^{-I})      │
  └──────────────┬──────────────────────┘
                 │ P_loss [erg/s]
                 ▼
  ┌─────────────────────────────────────┐
  │ ⑤ 写入 ed_depoVar (行453-457)      │
  │   Q_las += P_loss·Δt / (ρ·V)       │
  │   (比能形式) 或 P_loss·Δt/V (体密度)│
  └─────────────────────────────────────┘
```

### 6.2 库仑对数 —— `ed_CoulombFactor.F90`

```fortran
!! ed_CoulombFactor.F90 行33-64

real function ed_CoulombFactor(Z, e, k, T, Ne)
  ! 输入: Z=平均电离度, e=电子电荷, k=Boltzmann常数
  !       T=电子温度, Ne=电子数密度

  kT = k * T                                                             ! 行53

  !! ★★★ 库仑参数 Λ (行54): ★★★
  Lambda = (1.5 / (Z * e * e * e)) * sqrt(kT * kT * kT / (PI * Ne))
  !                3/2 · (kT)^(3/2)
  !       = ──────────────────────────
  !           Z̄ · e³ · √(π · Nₑ)

  lnLambda = log(Lambda)                                                  ! 行55
  ed_CoulombFactor = max(lnLambda, 1.0)                                   ! 行57
  ! ↑ 取最大值避免负数或极小值
end function
```

### 6.3 逆轢射碰撞频率 —— `ed_inverseBremsstrahlungRate.F90`

这是**核心公式**。函数返回电子-离子碰撞频率 $\nu$（单位：1/s）。

```fortran
!! ed_inverseBremsstrahlungRate.F90 行41-77

real function ed_inverseBremsstrahlungRate(Z, e, Me, k, T, Ne, Nc, lnLambda)
  ! 输入: Z=电离度, e=电子电荷, Me=电子质量, k=Boltzmann常数
  !       T=电子温度, Ne=电子数密度, Nc=临界密度, lnLambda=库仑对数

  kT   = k * T                                                            ! 行64
  e2Ne = e * e * Ne                                                       ! 行65
  twoe2Ne = e2Ne + e2Ne                                                   ! 行66

  !! ★★★ 逆轢射碰撞频率 ν (行68-70): ★★★
  ed_inverseBremsstrahlungRate = (Z * twoe2Ne * twoe2Ne / (Nc + Nc + Nc)) &
                               * sqrt((PI + PI) / (Me * kT * kT * kT))    &
                               * lnLambda
  !                         4    Z̄ · e⁴ · Nₑ²             √(2π)
  !          =    ν    =   ─ · ─────────────── · √(──────────────) · lnΛ
  !                         3         Nc              mₑ · (kTₑ)³
  !
  ! 等价于经典公式:
  !           ν_ib = (4/3)·√(2π/mₑ) · (Z̄e⁴/N_c) · (Nₑ²/(kTₑ)^(3/2)) · lnΛ
  !
  ! 其中 Nc = ε₀·mₑ·ω²/e² 是激光频率 ω 对应的临界密度

end function
```

### 公式推导

逆轢射碰撞频率的连续形式为：

$$\nu_{\text{ib}} = \frac{4}{3} \sqrt{\frac{2\pi}{m_e}} \frac{\bar{Z} e^4}{N_c} \frac{N_e^2}{(k_B T_e)^{3/2}} \ln \Lambda$$

其中：
- $N_c = \epsilon_0 m_e \omega^2 / e^2$ — 激光频率 $\omega$ 对应的**临界密度**
- $\ln \Lambda$ — 库仑对数（$ed\_CoulombFactor$ 计算）

在网格单元内，光线穿过距离 $\Delta s$ 对应的路径积分为：

$$I = \int_{\text{cell}} \nu_{\text{ib}} \, dt = \nu_{\text{ib}} \cdot \Delta t_{\text{cross}}$$

（$\Delta t_{\text{cross}} = \Delta s / c$ 是跨越时间）

### 6.4 沉积功率计算 —— `ed_traceBlockRays1DRec.F90` 行391-465

```fortran
!! ★★★ 计算光学深度积分 ★★★

!! 步骤1: 计算逆轢射频率 (行399-406):
call ed_inverseBremsstrahlungRate(cellZbar, e, Me, k, centerTele, &
                                   centerNele, rayCritDens, lnLambda)

!! 步骤2: 路径积分 (行408):
integral = nu * crossTime          ! I = ν·Δt_cross (简单版本)

!! 或使用2点 Gauss-Legendre 求积 (行427-445):
U = velX * gradNeleX / Nele
W = velX * gradTeleX / Tele
R = -gradNeleX²/Nₑ · c²/(4·N_c)
S = -gradNeleX·gradTeleX/Nₑ · c²/(4·N_c)

a = G_root1 · Δt/2, b = a²
integral = [(1+U·a+R·b)² / (1+W·a+S·b)^(3/2)  +  (G_root2对应项)]
integral ×= ν · Δt/2

!! 步骤3: ★★★ 能量沉积公式 (行449-457): ★★★
powerLossFactor = exp(-integral)                        !! e^{-I}
cellPower = rayPower * (1.0 - powerLossFactor)           !! P_dep = P·(1-e^{-I})
cellEnergy = cellPower * timeStep                        !! ΔE_dep = P_dep·Δt

if (ed_depoVarIsPerMass) then
   !! 比能形式 (erg/g): Q_las += ΔE / (ρ·V)
   cellEnergyDepot(i) += cellEnergy / cellMass
else
   !! 体密度形式 (erg/cm³): Q_las += ΔE / V
   cellEnergyDepot(i) += cellEnergy / cellVolume
endif

!! 步骤4: 更新光线剩余功率 (行459):
rayPower = rayPower * powerLossFactor                    !! P_ray' = P_ray · e^{-I}

!! 如果功率耗尽则标记光线为"死亡" (行461-464):
if (rayPower <= ed_rayZeroPower) then
    ed_rays(RAY_BLCK, ray) = real(NONEXISTENT)
    exit
endif
```

### 6.5 高斯求积的物理意义

简单版本 $I = \nu \cdot \Delta t$ 假设光线在穿越网格时等离子体参数不变。

高斯版本采用 **2 点 Gauss-Legendre 求积**，在光线路径上取两个采样点，考虑了路径中：
- 电子密度梯度 $\nabla N_e$ 引起的折射率变化（U, R 项）
- 电子温度梯度 $\nabla T_e$ 引起的碰撞频率变化（W, S 项）

这使得高斯版本在密度/温度梯度大的区域（如烧蚀面附近）比简单版本精确得多。

### 6.6 与连续方程的关系

逆轢射吸收在连续层次上是光束辐射输运方程的解：

$$\frac{dP_{\text{ray}}}{ds} = -\kappa_{\text{ib}} P_{\text{ray}}$$

其中 $\kappa_{\text{ib}} = \nu_{\text{ib}} / c$ 是逆轢射吸收系数。

方程的解为：

$$P_{\text{ray}}(s) = P_{\text{ray}}(0) \cdot \exp\left(-\int_0^s \kappa_{\text{ib}} \, ds'\right)$$

这正是代码中 `powerLossFactor = exp(-integral)` 的来源，其中 `integral = ∫ν·dt = ∫κ·ds`。

---

## 7. Step 4：等离子体能量更新（ed_updatePlasma）

### 文件
`Laser_3T/ed_updatePlasma3T.F90`（3T模式）

### 功能

将沉积能量 $Q_{\text{las}} = \frac{P_{\text{dep}}}{\text{cellVolume}}$ 写入电子能量变量 `ed_depoVar`，供下游算子分裂使用：

```fortran
!! EnergyDeposition.F90 行199-204

!! 初始化沉积变量为0:
solnData(ed_depoVar, :, :, :) = 0.0

!! 追迹与沉积: 过程由 ed_traceRays 和 ed_depositRays 完成
!! 结果写入 ed_depoVar
```

### 在 3T 算子分裂中的位置

```
       Hydro 单元 (守恒律)
           │
           ▼
   Heatexchange 单元 (离子-电子交换)
           │
           ▼
   Diffuse 单元 (电子热传导)  ← 见下份文档
           │
           ▼
●→ RadTrans 单元 (辐射扩散)  ← 见下下份文档
           │
           ▼
   EnergyDeposition 单元 (激光沉积) ← 本文档
           │
           ▼
       下一时间步
```

---

## 8. 完整数据流与代码行号对应

### 代码行号速查表

| 功能 | 文件 | 关键行 |
|------|------|--------|
| 主驱动入口 | `EnergyDeposition.F90` | 行45: `subroutine EnergyDeposition` |
| 初始化沉积变量 | `EnergyDeposition.F90` | 行202: `solnData(ed_depoVar) = 0.0` |
| 创建光线 | `LaserRays/ed_createRays.F90` | 主体 |
| 光束功率积分 | `LaserBeams/ed_computeBeamPower.F90` | 行139-156 |
| 光线循环追迹 | `EnergyDeposition.F90` | 行303-319 |
| 能量沉积到`ed_depoVar` | `LaserRayTrace/.../ed_traceRays*.F90` | 主体 |
| **库仑对数计算** | `LaserUtilities/ed_CoulombFactor.F90` | 行54: `Λ = (1.5/(Ze³))·√((kT)³/(πNe))` |
| **逆轢射碰撞频率** | `LaserUtilities/ed_inverseBremsstrahlungRate.F90` | 行68-70: `ν = (4/3)·√(2π/mₑ)·(Z̄e⁴/Nc)·(Ne²/(kT)³/²)·lnΛ` |
| **功率衰减公式** | `LaserRayTrace/CellAverage/ed_traceBlockRays1DRec.F90` | 行449: `powerLossFactor = exp(-integral)` |
| **沉积功率** | `LaserRayTrace/CellAverage/ed_traceBlockRays1DRec.F90` | 行450: `cellPower = rayPower·(1 - e^{-I})` |
| 光线功率更新 | `LaserRayTrace/CellAverage/ed_traceBlockRays1DRec.F90` | 行459: `rayPower = rayPower·e^{-I}` |
| 光线耗尽判断 | `LaserRayTrace/CellAverage/ed_traceBlockRays1DRec.F90` | 行461-464 |
| 写入`ed_depoVar` | `LaserRayTrace/CellAverage/ed_traceBlockRays1DRec.F90` | 行453-457 |
| 等离子体更新(3T) | `Laser_3T/ed_updatePlasma3T.F90` | 主体 |
| 激光是否开启 | `EnergyDeposition.F90` | 行162-163 |

### 数据流总图

```
        用户输入                 时间循环
     脉冲波形 P(t)       t^n              t^n+Δt
           │                │                │
           ▼                ▼                ▼
    ┌──────────────┐
    │ed_computeBeam│   P̄ = (1/Δt)∫P(t)dt     ← 梯形数值积分
    │Power         │
    └──────┬───────┘
           │ beamPower = P̄
           ▼
    ┌──────────────┐
    │ ed_createRays│   创建 N 条光线, 每条功率 P̄/N
    └──────┬───────┘
           │ 每条光线: pos(3), dir(3), power
           ▼
    ┌──────────────┐
    │ ed_traceRays │
    │ (do while)   │ ← 循环直至所有光线离开计算域或耗尽
    │              │
    │ 在每个网格:  │
    │ ① 计算 Λ     │  Λ = (1.5/Ze³)·√((kTₑ)³/(πNe))    (CoulombFactor)
    │ ② 计算 ν_ib  │  ν = (4/3)·√(2π/mₑ)·(Z̄e⁴/Nc)·    (invBremsRate)
    │               │      (Ne²/(kTₑ)³/²)·lnΛ
    │ ③ 计算 I=∫νdt│  I = ν·Δt         或 Gauss-Legendre 求积
    │ ④ P_dep=     │  P_ray·(1 − e^{-I})
    │ ⑤ ed_depoVar │  += P_dep·Δt / (ρ·V)  或  P_dep·Δt/V
    │ ⑥ 更新光线:  │  rayPower *= e^{-I},  pos += dir·Δs
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ ed_update-   │  将 Q_las 加入电子能量方程
    │ Plasma(3T)   │  ∂(ρe_ele)/∂t = ... + Q_las
    └──────────────┘
           │
           ▼
     进入下一算子分裂步骤
```

### 关键点总结

1. **几何光学近似**：激光按直线（或 Snell 折射）传播，不考虑衍射效应
2. **时间步平均**：光束功率用梯形法在时间步上平均，而非取瞬时值
3. **逆轢射沉积的完整计算链**：
   - 库仑对数：$\Lambda = \frac{3}{2\bar{Z}e^3} \sqrt{\frac{(k_B T_e)^3}{\pi N_e}}$
   - 碰撞频率：$\nu_{\text{ib}} = \frac{4}{3} \sqrt{\frac{2\pi}{m_e}} \frac{\bar{Z} e^4}{N_c} \frac{N_e^2}{(k_B T_e)^{3/2}} \ln \Lambda$
   - 光学深度：$I = \int \nu_{\text{ib}} dt$（高斯求积考虑梯度效应）
   - 功率衰减：$P_{\text{dep}} = P_{\text{ray}} (1 - e^{-I})$
4. **密度梯度修正**：高斯版本在路径积分中通过 U/W/R/S 项计入了电子密度和温度的梯度对折射率和碰撞频率的影响，在烧蚀面附近精度更高
5. **临界密度截断**：$N_c = \epsilon_0 m_e \omega^2 / e^2$，当 $N_e > N_c$ 时光线被反射，能量全部沉积在转折点附近
6. **算子分裂**：$Q_{\text{las}}$ 在 Hydro/Diffuse/RadTrans 之后、作为最后一个算子加入电子能量方程
