# 电子热传导（限流 Spitzer 模型）源码与方程对照

> 本文档追踪 FLASH 中电子热传导从物理方程到 Fortran 代码的实现路径。
> 电子热传导是一个**两单元协作**的跨模块物理过程。
>
> 参考文件：
> - 热导率: `source/physics/materialProperties/Conductivity/ConductivityMain/Spitzer/Conductivity.F90`
> - 比热: `.../Spitzer/cond_getCv.F90`
> - 扩散通量: `source/physics/Diffuse/DiffuseFluxBased/Diffuse_therm.F90`
> - 限流因子: `source/physics/Diffuse/DiffuseMain/Diffuse_fluxLimiter.F90`
> - 通用限流器: `.../DiffuseMain/Diffuse_applyGenericFluxLimiter.F90`
> - 隐式求解: `.../DiffuseMain/Diffuse_solveScalar.F90`
> - 文档: `docs/flash4_ug_4p8.md` 第14、19、23章

---

## 目录

1. [物理方程](#1-物理方程)
2. [模块协作架构](#2-模块协作架构)
3. [单元 A：Spitzer 热导率计算（Conductivity）](#3-单元-aspitzer-热导率计算conductivity)
4. [单元 B：扩散通量（Diffuse_therm）](#4-单元-b扩散通量diffuse_therm)
5. [单元 C：限流因子（Diffuse_fluxLimiter）](#5-单元-c限流因子diffuse_fluxlimiter)
6. [单元 D：隐式扩散求解（Diffuse_solveScalar）](#6-单元-d隐式扩散求解diffuse_solvescalar)
7. [完整数据流与代码行号对应](#7-完整数据流与代码行号对应)

---

## 1. 物理方程

### 文档中的方程（第14章，式14.9-14.10）

电子热通量（Fourier 定律 + Spitzer 热导率）：

$$\mathbf{q}_{\text{ele}} = -\kappa_{\text{ele}} \nabla T_{\text{ele}}$$

代入电子能量方程后的算子分裂形式：

$$\left.\frac{\partial (\rho e_{\text{ele}})}{\partial t}\right|_{\text{cond}} = \nabla \cdot (\kappa_{\text{ele}} \nabla T_{\text{ele}})$$

### 限流通量公式

> 对应图片中的公式(1)

FLASH 中限流热通量的具体实现采用**有效扩散系数**策略。不是直接对通量做 min 截断，而是通过限流因子 $\lambda$ 修改扩散系数 $D$：

$$\mathbf{q}_{\text{eff}} = \min\left\{D,\; \frac{q_{\max,\text{ele}}}{|\nabla T_{\text{ele}}|}\right\} \cdot \nabla T_{\text{ele}}$$

其中 $D = \kappa_{\text{ele}}$ 是原始扩散系数（热导率），$q_{\max,\text{ele}} / |\nabla T_{\text{ele}}|$ 是限流后的等效扩散系数。

### 最大热流

> 对应图片中的公式(2)

最大电子热通量取为自由流极限（free-streaming limit），即电子以热速度 $v_{\text{th}}$ 输运其热能的通量：

$$q_{\max,\text{ele}} = \alpha_{\text{ele}} \cdot n_{\text{ele}} \cdot k_B T_{\text{ele}} \cdot \sqrt{\frac{k_B T_{\text{ele}}}{m_{\text{ele}}}} = A \cdot n_{\text{ele}} \cdot T_{\text{ele}}^{3/2}$$

其中前因子 $A$ 聚合了所有物理常数（$\alpha_{\text{ele}}$ 是用户可调的限流系数，对应运行时参数 `diff_eleFlCoef`）：

$$A = \alpha_{\text{ele}} \cdot \frac{k_B^{3/2}}{\sqrt{m_{\text{ele}}}}$$

### Spitzer 热导率完整公式

> 对应图片中的公式(3)

FLASH 中更完整的 Spitzer 热导率实现（`SpitzerHighZ/Conductivity.F90`）采用 Braginskii 形式的完整表达式：

$$D = \kappa_{\text{ele}} = \left(\frac{8}{\pi}\right)^{3/2} \frac{k_B^{7/2}}{e^4 \sqrt{m_{\text{ele}}}} \cdot \frac{1}{1 + 3.3/\bar{z}} \cdot \frac{T_{\text{ele}}^{5/2}}{\bar{z} \cdot \ln \Lambda_{\text{ei}}}$$

其中：
- $\bar{z}$ — 平均电离度（`zbar`）
- $\ln \Lambda_{\text{ei}}$ — 电子-离子库仑对数（`lnLambda`）
- $1/(1+3.3/\bar{z})$ — Spitzer 修正因子（`g(Z)`，当 $\bar{z} \to \infty$ 时趋近于 1）

而简单的 `Spitzer/Conductivity.F90` 采用聚合常数的形式：

$$\kappa_{\text{ele}} = 9.2 \times 10^{-7} \cdot T_{\text{ele}}^{5/2}$$

后者对 $\bar{z} = 1$ 的氢等离子体在典型 HEDP 参数范围内近似成立。前者（`SpitzerHighZ`）适用更广的 $\bar{z}$ 范围。

### 通量限流（flux limiting）与限流模式

在温度梯度极大的区域，经典 Spitzer 热导率会高估热通量（超过自由流极限）。FLASH 的限流器通过求解通量比 $R$ 并应用限流函数 $\lambda_3 = 3\lambda$ 来降低扩散系数：

$$\kappa_{\text{limited}} = \kappa_{\text{ele}} \cdot \lambda_3, \quad \lambda_3 = f(R), \quad R = \frac{3 \kappa_{\text{ele}} |\nabla T|}{q_{\max,\text{ele}}}$$

四种限流模式：

| 模式 | 公式 $\lambda_3 = f(R)$ | 常数宏名 | 物理含义 |
|------|------------------------|---------|---------|
| **谐和平均** (HARMONIC) | $1/(1+R)$ | `FL_HARMONIC` | 最简单，扩散+极限的调和 |
| **Min-Max** (MINMAX) | $\min(1, 1/R)$ | `FL_MINMAX` | 直接截断到自由流极限 |
| **Larsen** (LARSEN) | $1/\sqrt{1+R^2}$ | `FL_LARSEN` | 平滑过渡 |
| **Levermore-Pomraning** (LEVPOM) | $3(2+R)/(6+3R+R^2)$ | `FL_LEVPOM` | 辐射输运理论推导（默认） |

其中 `R = 3 * κ |∇T| / q_max` 表示当前扩散通量与自由流极限的比值。

---

## 2. 模块协作架构

电子热传导涉及两个物理单元的协作：

```
                 物理过程                    FLASH 模块
                                       
          ┌────────────────────┐         materialProperties/
          │  热导率计算         │         Conductivity/
          │  κ = 9.2e-7·T^2.5 │         Spitzer/Conductivity.F90
          └─────────┬──────────┘
                    │ κ(T, ρ)
                    ▼
          ┌────────────────────┐         Diffuse/
          │  限流因子           │         DiffuseMain/
          │  λ ∈ (0, 1/3]     │         Diffuse_fluxLimiter.F90
          └─────────┬──────────┘
                    │ κ_limited
                    ▼
          ┌────────────────────┐         Diffuse/
          │  扩散通量           │         DiffuseFluxBased/
          │  F = -κ·∇T        │         Diffuse_therm.F90
          └─────────┬──────────┘
                    │ dE = -∇·F dt
                    ▼
          ┌────────────────────┐         Diffuse/
          │  隐式时间积分       │         DiffuseMain/
          │  E^{n+1}=E^n+Δt·∇·κ∇T│        Diffuse_solveScalar.F90
          └────────────────────┘
```

---

## 3. 单元 A：Spitzer 热导率计算（Conductivity）

### 文件
`source/physics/materialProperties/Conductivity/ConductivityMain/Spitzer/Conductivity.F90`

### 核心实现

```fortran
!! Conductivity.F90 行41-101

subroutine Conductivity(solnVec, cond, diff_coeff, component)
  ! solnVec = 当前网格单元的状态变量向量
  ! cond    = 输出的热导率 [κ_∥, κ_⊥, κ_×] (各向同性, 三个相等)
  ! diff_coeff = 扩散系数 (= κ/(ρ·c_v))
  ! component  = 组件选择: 1=离子, 2=电子, 3=辐射

  real, parameter :: ck   = 9.2e-7     !! Spitzer 常数 (行55)
  real, parameter :: cexp = 2.5         !! 温度指数 (行56)

  !! 选择温度变量: (行68-81)
  select case(componentLoc)
  case(1)   tempToUse = TION_VAR   !! 离子温度
  case(2)   tempToUse = TELE_VAR   !! 电子温度
  case(3)   call Driver_abortFlash(...)  !! Spitzer 不适用于辐射
  end select

  xden = solnVec(DENS_VAR)                !! 密度 ρ   (行84)
  xtemp = solnVec(tempToUse)              !! 温度 T   (行85)

  !! ★★★ Spitzer 热导率公式 (行87): ★★★
  condLoc = ck * xtemp**cexp
  !!        = 9.2e-7 × T^2.5
  !! 单位: erg/(cm·s·K)

  !! 扩散系数 (行89):
  diff_coeffLoc = condLoc / (xden * cond_getCv(...))
  !! D = κ / (ρ·c_v)

  !! 各向同性输出 (行99-100):
  if(present(cond)) cond(:) = condLoc
  if(present(diff_coeff)) diff_coeff(:) = diff_coeffLoc
end subroutine
```

### 其他可选模型（同一目录下）

| 模型 | 目录 | 适用场景 |
|------|------|---------|
| **Spitzer** | `Spitzer/` | 完全电离等离子体，默认 |
| Lee-More | `LeeMore/` | 部分电离/稠密等离子体 |
| Constant | `Constant/` | 常数热导率，测试用 |
| Epperlein-Haines | `EppHain/` | 磁化等离子体 |

---

## 4. 单元 B：扩散通量（Diffuse_therm）

### 文件
`source/physics/Diffuse/DiffuseFluxBased/Diffuse_therm.F90`

### 物理

该子程序计算热扩散通量：$\mathbf{F} = -\kappa \nabla T$，并将其加入总能通量。

### 文档中的离散公式（行38-62）

```text
!! 面通量 (界面 i+½):
              κ_i + κ_{i-1}     T_i - T_{i-1}
      F_i = - ───────────── × ───────────────     (行40-42)
                   2                 Δx

!! 能量更新:
              F_{i+1} - F_i
      dE_i = ─────────────                          (行47-49)
                  Δx
```

### 核心源码

```fortran
!! Diffuse_therm.F90 行240-307

!! Step 1: 从 Conductivity 单元获取热导率 κ
do i = blkLimits(LOW,IAXIS)-1, blkLimits(HIGH,IAXIS)+1
   call Conductivity(solnData(:,i,j,k), cond_zone, diff_coeff, 2)   !! 行251, component=2 表示电子
   cond(i) = cond_zone(2)                                            !! 行253
end do

!! Step 2: 界面热导率 (算术平均或几何平均)
do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)+1
   if (diff_geometricMeanDiff) then
      condi(i) = 2.*(cond(i)*cond(i-1))/(cond(i)+cond(i-1))          !! 几何平均 (行258)
   else
      condi(i) = 0.5*(cond(i)+cond(i-1))                              !! 算术平均 (行260)
   endif
end do

!! Step 3: ★★★ 计算热通量 ★★★ (行265-278)
do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)+1
   if (thermal_diff_method == 1) then
      !! 方法1: F = -κ·∇T (线性梯度) (行267-270)
      thermflux(i) = -condi(i) * dxinv(i) * &
           (solnData(tempVar,i  ,j,k) - solnData(tempVar,i-1,j,k))
   else
      !! 方法2: F = -(κ/4T³)·∇T⁴ (行274-277)
      thermflux(i) = -0.5*(0.25*cond(i)/solnData(tempVar,i,j,k)**3 &
                         + 0.25*cond(i-1)/solnData(tempVar,i-1,j,k)**3) &
                     * dxinv(i)*(solnData(tempVar,i,j,k)**4 &
                               - solnData(tempVar,i-1,j,k)**4)
   endif
end do

!! Step 4: 将热通量加入总能通量 / 内能通量 (行302-305)
temp_flx(E_FLUX,i,j,k) = temp_flx(E_FLUX,i,j,k) + areaLeft(i,j,k)*thermflux(i)
temp_flx(EINT_FLUX,i,j,k) = temp_flx(EINT_FLUX,i,j,k) + areaLeft(i,j,k)*thermflux(i)
```

### 与方程的关系

方法1直接对应：$F = -\kappa \nabla T$

方法2利用：$\nabla T^4 = 4T^3 \nabla T$，变换后：
$$F = -\frac{\kappa}{4T^3} \nabla T^4$$

两种方法在 $\nabla T$ 平滑时等价，但方法2在强间断处数值稳定性更好。

---

## 5. 限流通量的完整实现（图片公式的源码映射）

### 5.1 最大热流 $q_{\max,\text{ele}}$ 的计算

> 对应图片公式(1)(2): $q_{\max,\text{ele}} = \alpha_{\text{ele}} \cdot n_{\text{ele}} k_B T_{\text{ele}} \cdot \sqrt{\frac{k_B T_{\text{ele}}}{m_{\text{ele}}}}$

#### 文件
`source/physics/Diffuse/DiffuseMain/CG/diff_advanceTherm.F90`

#### 源码

```fortran
!! diff_advanceTherm.F90 行221-225

!! ★★★ 计算电子最大热流 q_max,ele ★★★
!! FLLM_VAR = q_max,ele = diff_eleFlCoef · nele · kB · Tele · √(kB·Tele/mele)

solnVec(FLLM_VAR,i,j,k) = diff_eleFlCoef *                                      &  !! α_ele
     sqrt(diff_boltz * xtemp / diff_mele) *                                      &  !! √(kB·Tele/mele)
     diff_boltz * xtemp *                                                        &  !! kB·Tele
     (Ye * diff_avo * xdens)                                                       !! nele = Ye·NA·ρ
```

#### 公式对应

逐项对照：

```text
FLLM_VAR (q_max,ele)  
  = diff_eleFlCoef                          ← α_ele  (运行时参数, 默认~0.1)
  × √(diff_boltz·xtemp/diff_mele)           ← √(kB·Tele/mele)   [电子热速度]
  × diff_boltz·xtemp                        ← kB·Tele           [热能]
  × (Ye·diff_avo·xdens)                     ← nele = Ye·NA·ρ   [电子数密度]

合并即: q_max,ele = α_ele · nele · kB · Tele · √(kB·Tele/mele)  [图片公式(2)]
                    = A · nele · Tele^(3/2)
其中 A = α_ele · kB^(3/2) · mele^(-1/2)     [聚合常数的前因子A]
```

### 5.2 限流扩散系数 $\min\{D,\; q_{\max,\text{ele}}/|\nabla T|\}$ 的实现

> 对应图片公式(1): $\mathbf{q}_{\text{eff}} = \min\left\{D,\; \frac{q_{\max,\text{ele}}}{|\nabla T|}\right\} \cdot \nabla T$

#### 文件
`source/physics/Diffuse/DiffuseMain/Diffuse_computeFluxLimiter.F90`

#### 通量比 $R$ 的计算

```fortran
!! Diffuse_computeFluxLimiter.F90 行182-192

!! R = dcoefOld * |∇T| / q_max * 3
!!   = 3 · κ · |∇T| / q_max,ele

if (maggrad == 0.0) then
   R = 0.0                                                  !! 行184: 无梯度→不限流
else
   R = dcoefOld * maggrad / max(TINY(fl)*dcoefOld*maggrad, fl) * 3.0   !! 行187
end if
```

其中:
- `dcoefOld` = `COND_VAR` = 原始扩散系数 $\kappa_{\text{ele}}$
- `maggrad` = $|\nabla T_{\text{ele}}|$ (温度梯度幅值, 行169)
- `fl` = `FLLM_VAR` = $q_{\max,\text{ele}}$ (最大热流, 由上一步计算)

#### 四种限流模式的 $\lambda_3$ 计算

```fortran
!! Diffuse_computeFluxLimiter.F90 行195-220

select case(mode)
case(FL_HARMONIC)
   !! 谐和平均: λ₃ = 1/(1+R)                           (行197)
   dcoef = 1.0 / (1.0/dcoefOld + maggrad/(fl + 1.0e-100))
   lambda3 = dcoef / dcoefOld

case(FL_MINMAX)
   !! Min-Max:  λ₃ = min(1, 1/R)                       (行200-201)
   dcoef = min(dcoefOld, fl/(maggrad + 1.0e-100))
   lambda3 = dcoef / dcoefOld

case(FL_LARSEN)
   !! Larsen:   λ₃ = 1/√(1+R²)                         (行204-205)
   dcoef = 1.0 / sqrt((1.0/dcoefOld)**2 + (maggrad/(fl + 1.0e-100))**2)
   lambda3 = dcoef / dcoefOld

case(FL_LEVPOM)
   !! ★★★ Levermore-Pomraning (1981) [默认] ★★★        (行208-216)
   !! λ₃ = 3(2+R)/(6+3R+R²)
   if (R > sqrtHuge) then
      lambda3 = 3.0/R
   else
      lambda3 = 3.0*(2.0 + R)/(6.0 + 3.0*R + R**2)
   endif

case DEFAULT
   call Driver_abortFlash("Invalid Flux limiter type")
end select

!! 存储限流因子到 FLLM_VAR (行232):
solnData(iflOut, i, j, k) = lambda3    !! iflOut 通常 = FLLM_VAR, 存储 3λ
```

#### 各模式在 $R$ 不同区间的行为

```
         R → 0 (弱梯度)         │    R → ∞ (强梯度)
                                │
  HARMONIC:  λ₃ → 1             │    λ₃ → 0 (1/R)
  MINMAX:    λ₃ → 1             │    λ₃ → 0 (1/R)
  LARSEN:    λ₃ → 1             │    λ₃ → 0 (1/R)
  LEVPOM:    λ₃ → 1             │    λ₃ → 0 (3/R)
                                │
  所有模式在弱梯度时 λ₃→1 (不限流)
  在强梯度时 λ₃→0 (完全限流)
```

### 5.3 限流后的扩散系数更新

限流因子 $\lambda_3$ 通过 `Diffuse_fluxLimiter` 应用回扩散系数：

```fortran
!! Diffuse_fluxLimiter.F90 行57-82

!! COND_VAR (κ) 被原位修改为限流后的值:
!!   κ_limited = κ * λ₃

!! 其中 λ₃ = f(R) 由 f(R) = min(1, κ·|∇T|/q_max) 
!! 或 Levermore-Pomraning 公式给出

!! 输出 FLLM_VAR = 3λ = λ₃ 供诊断使用
```

### 5.4 完整 Spitzer 热导率（含 $\bar{z}$ 和 $\ln\Lambda$）

> 对应图片公式(3): $D = \left(\frac{8}{\pi}\right)^{3/2} \frac{k_B^{7/2}}{e^4 \sqrt{m_e}} \cdot \frac{1}{1+3.3/\bar{z}} \cdot \frac{T_e^{5/2}}{\bar{z} \cdot \ln\Lambda_{ei}}$

#### 文件
`source/physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/Conductivity.F90`

#### 源码

```fortran
!! SpitzerHighZ/Conductivity.F90 行119-123

!! ★★★ 完整 Spitzer 热导率公式 ★★★

call PlasmaState_logLambda(ELE_ION, solnVec(teleVar), solnVec(tionVar), &
                           nele, mion, zbar, ll, .true.)                   !! 行120: 获取库仑对数 lnΛ

isochoricCondLoc = (8.0/PI)**1.5 * cond_boltz**3.5 / &
                   (sqrt(cond_mele) * cond_qele**4) * &
                   solnVec(teleVar)**cexp / (ll * (zbar + 3.3))            !! 行122-123
```

#### 公式逐项对照

```text
isochoricCondLoc = (8.0/PI)**1.5           ← (8/π)^(3/2)
                 × cond_boltz**3.5           ← kB^(7/2)   [cond_boltz = kB]
                 / (sqrt(cond_mele)          ← 1/√(me)    [cond_mele = mele]
                 × cond_qele**4)             ← 1/e⁴       [cond_qele = e]
                 × xtemp**cexp               ← Te^(5/2)   [cexp = 2.5 = 5/2]
                 / (ll * (zbar + 3.3))       ← 1/(lnΛ·(z̄+3.3))

其中 lnΛ·(z̄+3.3) = lnΛ · z̄ · (1 + 3.3/z̄)
                   = z̄ · lnΛ · (1 + 3.3/z̄)^{-1}
因此完整展开等价于图片公式(3):

  κ = (8/π)^(3/2) · kB^(7/2) / (e⁴ · √(me))
    · 1/(1 + 3.3/z̄) · Te^(5/2) / (z̄ · lnΛ)
```

#### 参数说明

| 代码变量 | 物理量 | 常数值（`SpitzerHighZ/`中） |
|---------|--------|---------------------------|
| `cond_boltz` | 玻尔兹曼常数 $k_B$ | `1.3806503e-16 erg/K` |
| `cond_mele` | 电子质量 $m_e$ | `9.10938188e-28 g` |
| `cond_qele` | 电子电荷 $e$ | `4.803204e-10 esu` |
| `cexp` | 温度指数 | `2.5 = 5/2` |
| `cond_navo` | 阿伏伽德罗常数 $N_A$ | `6.02214199e23` |

#### 两种 Spitzer 实现的比较

| 实现 | 文件 | 公式 | 优点 | 局限 |
|------|------|------|------|------|
| `Spitzer/` | `Conductivity/Spitzer/Conductivity.F90` | $\kappa = 9.2\times10^{-7} \cdot T^{2.5}$ | 简单快速 | 假定 $\bar{z}=1$, 固定 $\ln\Lambda$ |
| `SpitzerHighZ/` | `Conductivity/SpitzerHighZ/Conductivity.F90` | 完整 Braginskii 形式（含 $z̄,\ln\Lambda$） | 适用范围广 | 需要调用 `PlasmaState_logLambda` 和 EOS |
| `LeeMore/` | `Conductivity/LeeMore/Conductivity.F90` | LM84 模型（含简并修正） | 稠密等离子体 | 计算量大 |

## 6. 单元 D：隐式扩散求解（Diffuse_solveScalar）

### 文件
`source/physics/Diffuse/DiffuseMain/Diffuse_solveScalar.F90`

### 功能

如果使用隐式时间积分（默认），`Diffuse_solveScalar` 求解：

$$\frac{e^{n+1} - e^n}{\Delta t} = \nabla \cdot (\kappa_{\text{limited}} \nabla T^{n+1})$$

这等价于求解一个线性系统：

$$(\mathbf{I} - \Delta t \cdot \nabla \cdot \kappa \nabla) e^{n+1} = e^n$$

该方程用 HYPRE 或 Pardiso 等线性求解器求解。

### 调用方式

```fortran
call Diffuse_solveScalar( &
     gvar,                &  ! 待求解变量索引 (如 TEMP_VAR / TELE_VAR)
     COND_VAR,            &  ! 热导率 κ
     DFCF_VAR,            &  ! 前导系数 (一般为 1.0)
     bcTypes, bcValues,   &  ! 边界条件
     dt,                  &  ! 时间步
     1.0, 1.0, theta,     &  ! 隐式参数
     pass,                &  ! 求解方向
     nblk, blklst)          ! block 列表
```

---

## 7. 完整数据流与代码行号对应

### 代码行号速查表

| 功能 | 文件 | 关键行 |
|------|------|--------|
| **Spitzer 常数（简化）** | `ConductivityMain/Spitzer/Conductivity.F90` | 行55-56: `ck=9.2e-7, cexp=2.5` |
| **热导率公式（简化）** | `ConductivityMain/Spitzer/Conductivity.F90` | 行87: `condLoc = ck*xtemp**cexp` |
| **完整 Spitzer 公式** | `ConductivityMain/SpitzerHighZ/Conductivity.F90` | 行122-123: `(8/π)^(1.5)·kB^3.5/(√(me)·e⁴)·Te^2.5/(lnΛ·(z̄+3.3))` |
| 库仑对数 lnΛ | `ConductivityMain/SpitzerHighZ/Conductivity.F90` | 行120: `call PlasmaState_logLambda(...)` |
| **最大热流 q_max** | `DiffuseMain/CG/diff_advanceTherm.F90` | 行222-225: `α·√(kB·T/me)·kB·T·n` |
| **通量比 R 计算** | `DiffuseMain/Diffuse_computeFluxLimiter.F90` | 行187: `R = dcoefOld·|∇T|/q_max·3` |
| **Levermore-Pomraning 限流** | `DiffuseMain/Diffuse_computeFluxLimiter.F90` | 行215: `λ₃ = 3(2+R)/(6+3R+R²)` |
| **Min-Max 限流** | `DiffuseMain/Diffuse_computeFluxLimiter.F90` | 行201: `λ₃ = min(1, 1/R)` |
| **Larsen 限流** | `DiffuseMain/Diffuse_computeFluxLimiter.F90` | 行205: `λ₃ = 1/√(1+R²)` |
| **谐和平均限流** | `DiffuseMain/Diffuse_computeFluxLimiter.F90` | 行197: `λ₃ = 1/(1+R)` |
| 限流因子输出 | `DiffuseMain/Diffuse_computeFluxLimiter.F90` | 行232: `solnData(iflOut) = lambda3` |
| 限流器应用 | `DiffuseMain/Diffuse_fluxLimiter.F90` | 主体: 修改 COND_VAR = κ·λ₃ |
| 扩散系数 | `ConductivityMain/Spitzer/Conductivity.F90` | 行89: `diff_coeffLoc = condLoc/(ρ·c_v)` |
| 热导率调用 | `DiffuseFluxBased/Diffuse_therm.F90` | 行251: `call Conductivity(..., component=2)` |
| 界面平均κ | `DiffuseFluxBased/Diffuse_therm.F90` | 行258/260: 几何/算术平均 |
| **热通量公式** | `DiffuseFluxBased/Diffuse_therm.F90` | 行267-270: `F = -κ·∇T` |
| 通量→能量 | `DiffuseFluxBased/Diffuse_therm.F90` | 行302-305: `E_FLUX += area·F` |
| 隐式扩散求解 | `DiffuseMain/Diffuse_solveScalar.F90` | 主体 |
| 隐式扩散求解 | `DiffuseMain/Diffuse_solveScalar.F90` | 主体 |

### 数据流总图

```
   每个时间步 / 每个网格块:

   ρ, T_ele, 成分
      │
      ▼
    ┌────────────────┐
    │ Conductivity   │   κ = 9.2e-7 · T^2.5  (行87)
    │ (Spitzer)      │   单位: erg/(cm·s·K)
    └───────┬────────┘
            │ κ
            ▼
    ┌────────────────┐
    │ Diffuse_       │   计算限流因子 λ ∈ (0,1/3]
    │ fluxLimiter    │   修改 κ_limited = κ / (1+3λ·κ·|∇T|/(ρ·c_v·T))
    └───────┬────────┘   FLLM_VAR = 3λ
            │ κ_limited
            ▼
    ┌────────────────┐
    │ Diffuse_therm  │   面通量: F_i = -κ_{i-½} · (T_i - T_{i-1})/Δx
    │ (X/Y/Z扫描)    │   能量更新: dE_i = -(F_{i+1} - F_i)/Δx
    └───────┬────────┘
            │ 热通量 F
            ▼
    ┌────────────────┐
    │ Diffuse_       │   隐式: (I-Δt·∇·κ∇)e^{n+1}=e^n
    │ solveScalar    │   或显式: e^{n+1}=e^n+Δt·∇·(κ∇T^n)
    └───────┬────────┘
            │ e_ele^{n+1}
            ▼
    进入下一算子分裂步骤
```

### 关键点总结

1. **两单元协作**：Conductivity（物性）+ Diffuse（求解器），物理上解耦、代码上分开
2. **Spitzer 热导率**：提供两种实现——`Spitzer/`（简化常数 $9.2\times10^{-7}T^{2.5}$）和 `SpitzerHighZ/`（完整 Braginskii 形式，含 $\bar{z}$ 和 $\ln\Lambda$ 的精确依赖）
3. **最大热流**：$q_{\max,\text{ele}} = \alpha_{\text{ele}} \cdot n_{\text{ele}} \cdot k_B T_{\text{ele}} \cdot \sqrt{k_B T_{\text{ele}}/m_{\text{ele}}}$，其中 $\alpha_{\text{ele}}$ 是运行时参数 `diff_eleFlCoef`
4. **四种限流模式**：谐和平均（HARMONIC）、Min-Max（MINMAX）、Larsen（LARSEN）、Levermore-Pomraning（LEVPOM，默认），通过 $R = 3\kappa|\nabla T|/q_{\max}$ 计算 $\lambda_3 = f(R)$
5. **隐式求解**：$\nabla \cdot \kappa \nabla T$ 通过 `Diffuse_solveScalar` 隐式求解，避免扩散 CFL 条件限制时间步（$dt < 0.5 \cdot \Delta x^2 / D$）

### 与辐射扩散的区别

电子热传导和辐射扩散共用同一个 `Diffuse` 框架（`Diffuse_solveScalar`、`Diffuse_fluxLimiter`），区别在于：
- **热导率来源**：热传导用 `Conductivity`（Spitzer），辐射用 `c/(3κ_tr)`（不透明度）
- **发射项**：辐射有 Planck 发射项，热传导无
- **温度变量**：热传导用 `TELE_VAR`，辐射用 `TRAD_VAR`
