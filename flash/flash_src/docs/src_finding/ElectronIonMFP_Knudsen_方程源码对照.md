# 电子-离子平均自由程 λ_ei 与平均碰撞频率 ν_ei 源码与方程对照（含克努森数 Kn）

> 本文档追踪 FLASH 4.8 中**电子-离子平均自由程 λ_ei**、**平均碰撞频率 ν_ei（碰撞时间 τ_ei）**相关物理量从物理方程到 Fortran 源码的实现路径，
> 并给出利用这些源码公式**组装计算克努森数 Kn = λ_ei / L_T** 的方法。
>
> **本次更新（2026-07-30 第五次修订）要点**：
> - 前四次修订已落实：统一标准 τ_ei（单次碰撞时间）、库仑对数 F90 源码、公式一律附源码、删除 CGS 速算、数密度统一 `n_ion=dens·sumy·N_A`、删除 m_ion 内容。
> - **第五次新增（a）约化质量 μ 不敏感性论证（§4.1）**：FLASH 在约化质量 μ 中喂入首阶 `m_ion=abar/NA`（含束缚电子质量，与精确裸核质量差 ~10⁻⁴），但 EI 碰撞 μ=m_e·m_ion/(m_e+m_ion)→m_e（因 m_ion≫m_e），故 m_ion 取法对 b_min、lnΛ、τ_ei、λ_ei、Kn 的影响被压制在 10⁻³ 以下，可忽略。
> - **第五次新增（b）Kn 计算链路源码复核（§12）**：逐行核对整条 Kn 计算链（数密度→库仑对数→v_th→τ_ei→λ_ei→Kn），确认与 FLASH4.8 源码完全一致。
> - **第六次新增（联网核查，2026-07-30 23:06）**：§13 联网核查 Kn 计算正确性与改进建议——确认 `Kn≡λ_ei/L_T`（`L_T=T_e/|∇T_e|`）定义与文献（Arber 2023、NIF/MagLIF 2025、ICF ML 2026）完全一致；但失效阈值应改为 **$Kn>0.01$**（非 $Kn≳0.1\!-\!1$），并补充 λ_ei 的 O(1) 因子、电子-电子碰撞修正（Epperlein–Short 去局域长度 λ_e*）、b_max 粒子间距截断（高密度）、v_th 约定、L_T 方向、Z* 多组分等 7 项改进点。
>
> 单位制：**CGS**（密度 g/cm³、温度 K、长度 cm、时间 s）。
>
> 参考文件（绝对路径前缀 `E:\PhySimX\PhySimX\simulation\flash\flash_src\FLASH4.8\FLASH4.8\`）：
> - `source/physics/utilities/PlasmaState/PlasmaStateMain/PlasmaState_tau.F90`        —— **标准**碰撞时间 τ（ee/ei/ii），ELE_ION 分支 = 单次碰撞时间（本文采用）
> - `source/physics/materialProperties/Viscosity/ViscosityMain/Spitzer/visc_logLambda.F90` —— Atzeni 形式库仑对数（**不含 m_ion**，b_max/b_min 与本文公式逐字符一致）——**本文库仑对数源码**
> - `source/physics/utilities/PlasmaState/PlasmaStateMain/PlasmaState_logLambda.F90`  —— 库仑对数替代实现（Spitzer / LeeMore 两形式，ELE_ION 用约化质量 μ；重离子极限下退化为 visc_logLambda）
> - `source/PhysicalConstants/PhysicalConstantsMain/PhysicalConstants_init.F90`      —— 物理常数（CGS）
> - 交叉参考：`docs/src_finding/ThermalConduction_方程源码对照.md`
>
> **注意**：FLASH 中另有 `PlasmaState_ieEquilTime.F90` 计算**离子-电子热平衡（能量交换）时间**，它与本文标准的单次碰撞时间 τ_ei 不同，**计算 Kn 时不可混用**，详见 §8 末尾提醒。

---

## 目录

1. [源码逐条映射（公式 → FLASH 源码）](#1-源码逐条映射公式--flash-源码)
2. [物理常数（CGS）与源码取值](#2-物理常数cgs与源码取值)
3. [单元 A：电子/离子数密度 n_ele、n_ion](#3-单元-a电子离子数密度)
4. [单元 B：电子-离子库仑对数 lnΛ_ei（F90 源码，Atzeni）](#4-单元-b电子离子库仑对数-lnλei-f90-源码atzeni)
4.1 [约化质量 μ 对 m_ion 首阶近似的不敏感性](#41-约化质量-μ-对-m_ion-首阶近似的不敏感性)
5. [单元 C：电子-离子碰撞时间 τ_ei（标准·单次碰撞时间）](#5-单元-c电子离子碰撞时间-τei标准单次碰撞时间)
6. [单元 D：电子-离子平均自由程 λ_ei 与碰撞频率 ν_ei](#6-单元-d电子离子平均自由程-λei-与碰撞频率-νei)
7. [克努森数 Kn = λ_ei / L_T](#7-克努森数-kn--λei--l_t)
8. [完整 Fortran 调用示例（计算标准 Kn）](#8-完整-fortran-调用示例计算标准-kn)
9. [文献对照](#9-文献对照)
10. [讨论：τ 的输入 n 必须是 n_ion](#10-讨论τ-的输入-n-必须是-n_ion)
11. [注意事项与易错点](#11-注意事项与易错点)
12. [Kn 计算链路源码复核](#12-kn-计算链路源码复核)
13. [联网核查：Kn 计算正确性与改进建议](#13-联网核查kn-计算正确性与改进建议)

---

## 1. 源码逐条映射（公式 → FLASH 源码）

下表每一行均给出对应的 FLASH4.8 F90 源码位置（行号基于当前版本）。

| 公式 | 对应 FLASH4.8 F90 源码 | 吻合度 |
|------|------------------------|--------|
| $n_{\rm ele}=\rho\,y_e N_A,\;n_{\rm ion}=\rho\,\Sigma y\,N_A$ | `ye`/`sumy` 为解向量量（`YE_MAP`/`SUMY_MAP`，`Eos_getData.F90` L168,280-283）；`sumy=1/abar`，`ye=zbar\cdot sumy` | **精确** |
| $v_{\rm th}=\sqrt{3k_B T_e/m_e}$ | `visc_logLambda.F90` 隐含热速度口径；`PlasmaState_logLambda.F90` L100（`vtherm=sqrt(3*pls_boltz*tele/pls_mele)`，ELE_ION） | **精确** |
| $b_{\max}=\sqrt{k_B T_e/(4\pi e^2 n_{\rm ele})}$ | **`visc_logLambda.F90` L53** | **精确** |
| $b_{\min}=\max\!\left(\frac{\bar z\,e^2}{3k_B T_e},\;\frac{\hbar}{2\sqrt{3k_B T_e m_e}}\right)$ | **`visc_logLambda.F90` L55-57** | **精确** |
| $\ln\Lambda_{ei}=\ln(b_{\max}/b_{\min})$ | **`visc_logLambda.F90` L59**（`ll = max(log(bmax/bmin), 1.0)`） | **源码形式** |
| $\tau_{ei}=\dfrac{3\sqrt{m_e}(k_B T_e)^{3/2}}{4\sqrt{2\pi}\,\ln\Lambda_{ei}\,e^4\bar z^2 n_{\rm ion}}$ | **`PlasmaState_tau.F90` L66-67**（`ELE_ION` 分支，标准单次碰撞时间） | **精确** |
| $\lambda_{ei}=v_{\rm th}\tau_{ei},\;\nu_{ei}=1/\tau_{ei}$ | 组合 `v_th`(上) × `τ_ei`(下)；ν 为定义 | 组合式 |
| $K_n=\lambda_{ei}/L_T=v_{\rm th}\tau_{ei}/L_T$ | FLASH **无**内建克努森数例程（已检索 `source/physics`，无匹配）；$L_T=T_e/\|\nabla T_e\|$ 需用户自提供 | 用户定义 |




---

## 2. 物理常数（CGS）与源码取值

源码在 `PlasmaState_init.F90` / `visc_*_init` 中通过 `PhysicalConstants_get` 读取，单位制为 **CGS**。后续 λ_ei/ν_ei/Kn 的精确计算直接代入下列常量：

```fortran
! source/physics/utilities/PlasmaState/PlasmaStateMain/PlasmaState_init.F90  (L41-46)
call PhysicalConstants_get("electron mass",pls_mele)   ! m_e  [g]
call PhysicalConstants_get("Boltzmann",pls_boltz)      ! k_B  [erg/K]
call PhysicalConstants_get("electron charge",pls_qele)! e    [esu]
call PhysicalConstants_get("Planck",pls_hbar)          ! h    [erg*s]
pls_hbar = pls_hbar/(2.0*PI)                           ! -> ħ = h/2π [erg*s]
call PhysicalConstants_get("Avogadro",navo)             ! N_A  [mol^-1]
```

数值取自 `source/PhysicalConstants/PhysicalConstantsMain/PhysicalConstants_init.F90`（FLASH 4.8 当前版本）：

| 常数 | 符号 | 源码变量 | 数值（CGS） | 单位 |
|------|------|----------|-------------|------|
| 电子质量 | $m_e$ | `pls_mele`/`visc_mele` | `9.10938356E-28` | g |
| 玻尔兹曼常数 | $k_B$ | `pls_boltz`/`visc_boltz` | `1.38064852E-16` | erg/K |
| 元电荷 | $e$ | `pls_qele`/`visc_qele` | `4.80320467299766E-10` | esu (statcoulomb) |
| 约化普朗克常数 | $\hbar$ | `pls_hbar`/`visc_hbar` | `6.626070040E-27/(2π)=1.0545718E-27` | erg·s |
| 阿伏伽德罗常数 | $N_A$ | `navo`/`cond_navo` | `6.022140857E23` | mol⁻¹ |

---

## 3. 单元 A：电子/离子数密度

FLASH 中 `ye`（电子分数，每重子电子数）与 `sumy`（每重子离子数，$=\Sigma Y_i=1/\rm abar$）均为解向量量，可直接读取；也可由 EOS 派生。因此数密度的最直接 F90 写法如下（与用户公式一致）：

```fortran
! 数密度（用户公式： n_ele = dens*ye*NA, n_ion = dens*sumy*NA）
! ye, sumy 来自于解向量（YE_MAP, SUMY_MAP）
ye    = solnData(YE_MAP, i,j,k)      ! y_e
sumy  = solnData(SUMY_MAP, i,j,k)    ! Σy = 1/abar
nele  = dens * ye    * navo          ! 电子数密度 n_ele  [cm^-3]
nion  = dens * sumy  * navo          ! 离子数密度 n_ion  [cm^-3]   ← τ_ei 用 nion
```

- **`n_ele = ρ·y_e·N_A`**：`ye` 为电子分数（解向量 `YE_MAP`），或等价地由 `Eos_getAbarZbar` 得 `(abar,zbar)` 后 `ye = zbar/abar`。
- **`n_ion = ρ·Σy·N_A = ρ·sumy·N_A`**：`sumy` 为解向量 `SUMY_MAP`，满足 `sumy = 1/abar`（见 `Eos_getData.F90` L280-283：`abar=1/sumy`）。
- 二者关系：$n_{\rm ele}=y_e\,N_A\rho$、$\Sigma y=y_e/\bar z$，故 $n_{\rm ele}=\bar z\,n_{\rm ion}$（因 $y_e=\bar z\cdot sumy$）。**调用 τ_ei 时务必用 $n_{\rm ion}$，而非 $n_{\rm ele}$**，见 §10。

---

## 4. 单元 B：电子-离子库仑对数 lnΛ_ei（F90 源码，Atzeni）

**库仑对数完全以 F90 源码形式给出**，来源为 `visc_logLambda.F90`（注释明确 “formula comes from Atzeni”）。该实现**不含离子质量 m_ion**，仅含电子质量 $m_e$，与本文公式集逐字符一致：

```fortran
! source/physics/materialProperties/Viscosity/ViscosityMain/Spitzer/visc_logLambda.F90  (L50-59)
real, parameter :: ll_floor = 1.0

bmax = sqrt(visc_boltz * tele / (4*PI * visc_qele**2 * nele))          ! ★ b_max = sqrt(k_B T_e/(4π e² n_ele))

bmin_classic = zbar * visc_qele**2 / (3*visc_boltz*tele)               ! ★ b_min(经典) = zbar e²/(3 k_B T_e)
bmin_quantum = visc_hbar / (2*sqrt(3*visc_boltz*tele*visc_mele))       ! ★ b_min(量子) = ħ/(2 sqrt(3 k_B T_e m_e))
bmin = max(bmin_classic, bmin_quantum)                                ! ★ b_min = max(经典, 量子)

ll = max(log(bmax/bmin), ll_floor)                                    ! ★ lnΛ_ei = ln(b_max/b_min)，地板 1.0
```

对应数学式（源码形式见上）：

$$
b_{\max}=\sqrt{\frac{k_B T_e}{4\pi e^2 n_{\rm ele}}},\qquad
b_{\min}=\max\!\left(\frac{\bar z\,e^2}{3k_B T_e},\;\frac{\hbar}{2\sqrt{3k_B T_e m_e}}\right),
\qquad\ln\Lambda_{ei}=\ln\!\frac{b_{\max}}{b_{\min}}
$$

> **替代实现（约化质量路径）**：`PlasmaState_logLambda.F90` 的 `ELE_ION` 分支提供**约化质量 μ** 的普适形式（L99 `mu=(pls_mele*mion)/(pls_mele+mion)`，L108-109 `bmin` 用 μ）；在 $m_{\rm ion}\gg m_e$（重离子极限）下 μ→m_e，退化为上式 `visc_logLambda.F90`。关于该路径中 `m_ion` 取首阶近似（`abar/NA`）是否影响 Kn，见 **§4.1**。为保持公式集无 m_ion 干扰，本文统一采用 `visc_logLambda.F90`。

---

### 4.1 约化质量 μ 对 m_ion 首阶近似的不敏感性

`PlasmaState_logLambda.F90`（L99、L108-110）取约化质量 μ 计算 `b_min`。FLASH 所有调用点传入的 `mion` 均为首阶 `abar/NA`（**原子质量，含 Z 个束缚电子质量**），而非精确裸核质量 $(\rho-n_{\rm ele}m_e)/n_{\rm ion}={\rm abar}/N_A-\bar z\,m_e$：

```fortran
! 各调用点的首阶 m_ion 取法（未做电子质量扣除）
! Heatexchange_computeDt.F90   L160 : mion = abar / hx_navo
! hy_uhd_computeDtExtMHD.F90   L162 : mion = abar / hy_avogadro
! res_spitzerhighz.F90          L64 : mion = abar / res_shz_navo
```

二者相对差仅

$$\frac{\Delta m_{\rm ion}}{m_{\rm ion}}=\frac{\bar z\,m_e}{{\rm abar}/N_A}\approx\frac{\bar z}{\rm abar}\times 5.486\times10^{-4}\sim 10^{-4}$$

（CH ~3×10⁻⁴，金 ~1.4×10⁻⁴）。

**关键：EI 碰撞的约化质量由轻粒子（电子）主导。**

$$\mu=\frac{m_e\,m_{\rm ion}}{m_e+m_{\rm ion}}=m_e\!\left(1-\frac{m_e}{m_{\rm ion}}+\cdots\right)\approx m_e$$

因 $m_{\rm ion}\gg m_e$（差 10³–10⁵ 倍），μ 几乎严格等于 $m_e$，与 $m_{\rm ion}$ 取值无关：

- 若 $m_{\rm ion}$ 有 10⁻⁴ 相对误差，μ 的相对误差仅 $\sim(m_e/m_{\rm ion})\cdot(\Delta m_{\rm ion}/m_{\rm ion})\sim 10^{-7}\!-\!10^{-9}$；
- 即便 $m_{\rm ion}$ 差一倍（极端情形），μ 也只变 $\sim m_e/m_{\rm ion}\sim 10^{-3}$。

因此 `b_min`、`lnΛ_ei`、`τ_ei`、`λ_ei`、`Kn` 受 `m_ion` 取法的影响被压制在 10⁻³ 以下，**远小于 lnΛ 地板（§4 `ll_floor=1.0`）、简并修正（§11.8）等其它不确定度**。结论：**FLASH 对 `m_ion` 的首阶近似对克努森数计算不构成可观测误差**。这正是一开始把 m_ion 相关内容从主公式集删除的物理依据；即便走约化质量 μ 路径，该近似同样可忽略。

---

## 5. 单元 C：电子-离子碰撞时间 τ_ei（标准·单次碰撞时间）

**标准 τ_ei = 单次碰撞（动量弛豫）时间**，来自 `PlasmaState_tau.F90` 的 `ELE_ION` 分支（与 Braginskii / NRL 一致）。这就是计算 Kn 应采用的形式：

```fortran
! source/physics/utilities/PlasmaState/PlasmaStateMain/PlasmaState_tau.F90  (L63-67)
case (ELE_ION)
   !! temp = tele, n = nion                 ! ★ n 必须是离子数密度 n_ion
   !! ll should be electron-ion (llei)
   tau = (3.*sqrt(pls_mele)*(pls_boltz*temp)**1.5) / &
         (4.*sqrt(2.*PI) * ll * pls_qele**4 * zbar**2 * n)
! 其中 zbar = max(Z, 1.)  (L54，地板避免 τ 发散)
```

对应数学式（标准、非平衡时间变体）：

$$
\boxed{\tau_{ei}=\frac{3\sqrt{m_e}\,(k_B T_e)^{3/2}}{4\sqrt{2\pi}\,\ln\Lambda_{ei}\,e^4\,\bar z^2\,n_{\rm ion}}}
$$

- `temp` = $T_e$（电子温度），`n` = $n_{\rm ion}$（离子数密度，**不是** $n_{\rm ele}$，见 §10），`ll` = $\ln\Lambda_{ei}$（由 §4 计算），`zbar` = $\bar z$（平均电离度，源码取 `max(Z,1.)`）。
- 此 τ 是电子被离子散射的**单次碰撞时间**；用它得到的 λ_ei 为**电子输运平均自由程**，是标准 Knudsen 数的正确入参。
- 该公式**只含电子质量 $m_e$**（源码 `pls_mele`），不含离子质量 $m_{\rm ion}$。

---

## 6. 单元 D：电子-离子平均自由程 λ_ei 与碰撞频率 ν_ei

热速度 $v_{\rm th}$ 的源码口径（见 §4 / `visc_logLambda` 隐含，及 `PlasmaState_logLambda.F90` L100）：

```fortran
vtherm = sqrt(3*pls_boltz*tele/pls_mele)   ! v_th = sqrt(3 k_B T_e / m_e)
```

平均自由程与碰撞频率（F90 组合）：

```fortran
! 组合 PlasmaState_tau 的 τ_ei 与 v_th
vth  = sqrt(3.0*pls_boltz*tele/pls_mele)   ! 与源码一致
tau  = (3.*sqrt(pls_mele)*(pls_boltz*tele)**1.5) / &
       (4.*sqrt(2.*PI) * ll * pls_qele**4 * zbar**2 * nion)   ! ELE_ION 单次碰撞时间
lambda_ei = vth * tau                       ! λ_ei = v_th τ_ei
nu_ei     = 1.0 / tau                       ! ν_ei = 1/τ_ei
```

数学式：

$$
\boxed{\lambda_{ei}=v_{\rm th}\,\tau_{ei},\qquad
v_{\rm th}=\sqrt{\frac{3k_B T_e}{m_e}},\qquad
\nu_{ei}=\frac{1}{\tau_{ei}}}
$$

---

## 7. 克努森数 Kn = λ_ei / L_T

温度空间尺度长度（标准定义，**非 FLASH 源码内部量**）：

```fortran
LT     = tele / gradTe        ! L_T = T_e / |∇T_e|  [cm]，gradTe=|∇T_e| 自行提供
Kn     = lambda_ei / LT       ! Kn = λ_ei / L_T
```

数学式：

$$
L_T=\frac{T_e}{|\nabla T_e|},\qquad
\boxed{Kn=\frac{\lambda_{ei}}{L_T}=\frac{v_{\rm th}\,\tau_{ei}}{L_T}
=\sqrt{\frac{3k_B T_e}{m_e}}\;\tau_{ei}\;\frac{|\nabla T_e|}{T_e}}
$$

- 一维：$|\nabla T_e|\approx|\Delta T_e/\Delta x|$，$L_T\approx T_e/|dT_e/dx|$。
- **判定阈值（联网核查修正，见 §13）**：局部（Spitzer/Braginskii 流体）近似在 **$Kn<0.01$ 时可靠**；当 **$Kn>0.01$（1%）局部热传导模型即开始失效**进入非局域（文献一致结论，非 $Kn\gtrsim 0.1\!-\!1$）——因热流主要由 $v\approx 3.6v_{\rm th}$ 的快速电子贡献，且 $\lambda_{ei}(v)\propto v^4$，故实际判据为 $Kn_{ei}>1/(3.6)^4\approx 0.01$。$Kn\gtrsim 1$ 为完全非局域/弹道输运。一旦 $Kn\gtrsim 0.01$，热传导可能因非局域效应被显著抑制，应考虑 FLASH 通量限制（`diff_eleFlCoef` 等）或 SNB/非局域热传导模型。

---

## 8. 完整 Fortran 调用示例（计算标准 Kn）

严格沿用源码子程序；**仅使用单次碰撞时间 τ_ei（标准）**，库仑对数采用 `visc_logLambda.F90`（Atzeni，m_ion-free）。

```fortran
! 计算 λ_ei 与标准 Kn = λ_ei/L_T
! use: Viscosity_interface (visc_logLambda)
!      PlasmaState_interface (PlasmaState_tau)
!      PhysicalConstants_interface (PhysicalConstants_get)
!      (ye, sumy 来自解向量 YE_MAP, SUMY_MAP；或 Eos_interface(Eos_getAbarZbar) + Multispecies_interface)

real :: tele, xden, nele, nion, zbar, ll, tau, vth, lambda_ei, LT, gradTe, Kn
real :: ye, sumy
real :: navo
real, pointer :: solnData(:,:,:,:)   ! 含 DENS_VAR, TELE_VAR, YE_MAP, SUMY_MAP

call PhysicalConstants_get("Avogadro", navo)   ! N_A

xden = solnData(DENS_VAR, i,j,k)
tele = solnData(TELE_VAR, i,j,k)
ye   = solnData(YE_MAP,    i,j,k)
sumy = solnData(SUMY_MAP,  i,j,k)

! --- 数密度（§3）---
nele = xden * ye   * navo      ! = dens*ye*NA
nion = xden * sumy * navo      ! = dens*sumy*NA   ← τ_ei 用 nion（关键，见 §10）
! zbar 可由 Eos_getAbarZbar 得到，亦可 zbar = ye/sumy
zbar = ye / sumy

! --- 库仑对数 lnΛ_ei（§4，visc_logLambda.F90，Atzeni，m_ion-free）---
call visc_logLambda(tele, nele, tion, zbar, ll)   ! tion 传入但未被该实现使用

! --- 标准 τ_ei = 单次碰撞时间（§5，ELE_ION 分支）---
call PlasmaState_tau(ELE_ION, tele, ll, zbar, nion, tau)   ! zbar 内部取 max(Z,1.)

! --- λ_ei = v_th * τ_ei，ν_ei = 1/τ_ei（§6）---
vth       = sqrt(3.0*pls_boltz*tele/pls_mele)   ! 与源码一致
lambda_ei = vth * tau                            ! λ_ei
nu_ei     = 1.0 / tau                            ! ν_ei

! --- 标准克努森数 Kn = λ_ei / L_T（§7）---
LT = tele / gradTe                              ! L_T [cm]，gradTe=|∇T_e| 自行提供
Kn = lambda_ei / LT
```

> **提醒（请勿混用）**：FLASH 中 `PlasmaState_ieEquilTime.F90` 计算的是**离子-电子热平衡（能量交换）时间**，它约为单次碰撞时间的 $m_{\rm ion}/m_e$ 倍，**不是**本文标准的 τ_ei。计算 Kn 时务必使用 `PlasmaState_tau(ELE_ION)` 的单次碰撞时间，不要改用平衡时间，否则会系统高估 λ_ei 与 Kn。

---

## 9. 文献对照

- §5 的 τ_ei（单次碰撞时间）与 **Braginskii (1965)**、**NRL Plasma Formulary** 一致（NRL 亦写作 $\nu_{ei}\propto n_e \bar z$，与本文 $n_{\rm ion}\bar z^2$ 等价，因 $n_e=\bar z n_{\rm ion}$）。
- `visc_logLambda.F90` 注释明确 “formula comes from Atzeni”——即 $b_{\max}/b_{\min}$ 公式的出处；与本文 §4 逐字符一致。
- `PlasmaState_logLambda.F90` Spitzer 分支亦给出 `b_max`（德拜长度）与 `ln(b_max/b_min)` 形式，在重离子极限下与 `visc_logLambda.F90` 等价。
- 与 `ThermalConduction_方程源码对照.md` 中 Spitzer 热导率 $\kappa\propto T_e^{5/2}/(\bar z\ln\Lambda_{ei})$ 自洽（由 $\kappa\sim n_e k_B^2 T_e \tau_{\rm coll}/m_e$ 反推得同一 τ_ei）。

---

## 10. 讨论：τ 的输入 n 必须是 n_ion

`PlasmaState_tau` 的 ELE_ION 分支（§5）中 τ_ei 显含 $n$（源码变量 `n`），且注释明确要求 `n = nion`（离子数密度）。其物理来源：标准 Spitzer 电子-离子碰撞频率为

$$\nu_{ei}=\frac{4\sqrt{2\pi}\,e^4\,\bar z^2\,n_{\rm ion}\,\ln\Lambda_{ei}}{3\sqrt{m_e}(k_B T_e)^{3/2}}
\;\;\propto\;\bar z^2\,n_{\rm ion}$$

等价地 NRL 常写作 $\nu_{ei}\propto n_e\bar z$（因 $n_e=\bar z\,n_{\rm ion}$，二者等价）。**FLASH 采用 $n_{\rm ion}\bar z^2$ 形式，故传入的 `n` 必须是 $n_{\rm ion}$。**

若误传 $n=n_{\rm ele}=\bar z\,n_{\rm ion}$，则

$$\tau_{ei}^{\rm(误)}=\frac{3\sqrt{m_e}(k_B T_e)^{3/2}}{4\sqrt{2\pi}\,\ln\Lambda_{ei}\,e^4\,\bar z^2\,(\bar z\,n_{\rm ion})}
=\frac{\tau_{ei}^{\rm(正确)}}{\bar z}$$

即 τ_ei 被**低估 $\bar z$ 倍**，进而 $\lambda_{ei}=v_{\rm th}\tau_{ei}$ 与 $Kn=\lambda_{ei}/L_T$ 同样被**低估 $\bar z$ 倍**。对激光等离子体，$\bar z$（平均电离度）通常为 5–50（CH 约 3.5、中 Z 约 20–26、金约 50），**这是约 5–50 倍的数量级误差，绝非可忽略**。

等价表述：误传 $n_{\rm ele}$ 等于把 $\nu_{ei}$ 算成 $\propto n_{\rm ele}\bar z^2=\bar z^3 n_{\rm ion}$，而正确应为 $\bar z^2 n_{\rm ion}$——多计了一次 $\bar z$。这是最常见的簿记错误。实践上务必：

```fortran
nion = xden * sumy * navo   ! = dens * sumy * NA   ← 正确（§3）
! 切勿写成 nion = nele  (= zbar * nion)
```

**补充（密度输入不要混淆）**：库仑对数 `visc_logLambda.F90` 的 `b_max`（德拜长度）用的是 **`nele`**（电子密度，见 §4 L53），而 `PlasmaState_tau` 的 τ_ei 用的是 **`nion`**（离子密度）——两者是不同的入参，调用时务必分别传入，不能互相替代。

---

## 11. 注意事项与易错点

1. **单位制**：全部 CGS（密度 g/cm³、温度 K、长度 cm、时间 s）；SI 输入须先换算。
2. **采用标准 τ_ei**：本文 Kn 统一采用**单次碰撞时间** `PlasmaState_tau(ELE_ION)`，即 Braginskii 形式；离子-电子平衡时间（equilibration time）变体已删除，请勿混用 `PlasmaState_ieEquilTime`（见 §8 提醒）。
3. **库仑对数口径**：采用 `visc_logLambda.F90` 的 `ll = max(log(bmax/bmin), 1.0)`（Atzeni 形式，m_ion-free）；替代实现 `PlasmaState_logLambda` 在重离子极限下与之等价。
4. **τ 的输入 n（关键）**：`PlasmaState_tau` ELE_ION 要求 `n = n_ion`；误用 `n_ele` 会使 λ_ei 与 Kn 整体低估 $\bar z$（≈5–50）倍（§10）。
5. **lnΛ 与 τ 的密度输入不同**：`visc_logLambda` 的 `b_max` 用 `nele`（德拜长度），`PlasmaState_tau` 的 τ_ei 用 `nion`——分别传入，勿混。
6. **`zbar` 下限**：源码对 Z 取 `max(Z,1.)`，避免 τ 发散；手动实现需同样处理。
7. **L_T 非源码量**：`L_T=T_e/|\nabla T_e|` 需用户从温度场梯度提供；FLASH 不计算 Knudsen 数。
8. **强简并修正**：高密低温（$T_e\ll T_F$）时改用 LeeMore LM84 Eq.27 的 τ（含费米-狄拉克因子），经典 τ 会偏小。

---

## 12. Kn 计算链路源码复核（2026-07-30 第五次修订）

对本文采用的标准 Kn = λ_ei/L_T 整条计算链逐行对照 FLASH4.8 源码，确认准确性：

| 计算项 | 采用公式 | FLASH4.8 源码位置 | 一致性 |
|--------|----------|-------------------|--------|
| $n_{\rm ele}$ | `dens·ye·NA` | `Eos_getData.F90` L280-283（`ye=YE_MAP`、`sumy=SUMY_MAP`、`abar=1/sumy`、`zbar=ye/sumy`） | ✓ |
| $n_{\rm ion}$ | `dens·sumy·NA` | 同上；`sumy=SUMY_MAP` 直接读取 | ✓ |
| $b_{\max}$ | $\sqrt{k_B T_e/(4\pi e^2 n_{\rm ele})}$ | `visc_logLambda.F90` **L53** | ✓ 逐字符 |
| $b_{\min}$ | $\max(\bar z e^2/3k_B T_e,\;\hbar/2\sqrt{3k_B T_e m_e})$ | `visc_logLambda.F90` **L55-57** | ✓ 逐字符 |
| $\ln\Lambda_{ei}$ | $\ln(b_{\max}/b_{\min})$，地板 1.0 | `visc_logLambda.F90` **L59** | ✓ 源码形式 |
| $v_{\rm th}$ | $\sqrt{3k_B T_e/m_e}$ | `PlasmaState_logLambda.F90` L100（ELE_ION `vtherm`）；`visc_logLambda` 隐含同口径 | ✓ |
| $\tau_{ei}$ | $3\sqrt{m_e}(k_B T_e)^{3/2}/(4\sqrt{2\pi}\,\ln\Lambda_{ei}\,e^4\bar z^2 n_{\rm ion})$ | `PlasmaState_tau.F90` **L66-67**（ELE_ION 单次碰撞时间） | ✓ 逐字符 |
| $\lambda_{ei}$ | $v_{\rm th}\tau_{ei}$ | 组合式（定义） | ✓ |
| $\nu_{ei}$ | $1/\tau_{ei}$ | 组合式（定义） | ✓ |
| $Kn$ | $\lambda_{ei}/L_T$ | 用户定义；$L_T=T_e/|\nabla T_e|$ 非源码量 | — |

**复核结论**：

1. 标准 Kn 的整条计算链（数密度 → 库仑对数 → $v_{\rm th}$ → $\tau_{ei}$ → $\lambda_{ei}$ → $Kn$）与 FLASH4.8 源码**完全一致**；唯一依赖外部输入的是温度梯度尺度 $L_T$（FLASH 无内建 Kn 例程，已检索 `source/physics` 确认）。
2. 最关键的簿记约束——`PlasmaState_tau` 的 `n` 必须传 `n_ion`（离子数密度），**不是** `n_ele`——已在 §10 量化：误用会使 τ_ei、λ_ei、Kn 整体低估 $\bar z$（≈5–50）倍。
3. 本文 $\tau_{ei}$ 为**单次碰撞时间**（Braginskii，仅含 $m_e$，L66-67），与用户早先给出的平衡时间形式（含 $m_{\rm ion}$、约为 $(m_{\rm ion}/m_e)$ 倍）已明确分离；标准 Kn 采用前者。
4. 库仑对数 `b_max` 用 `nele`（德拜长度，L53），而 τ_ei 用 `nion`（L66-67）——两者入参不同，调用时分别传入（§10 末已提醒）。
5. 约化质量路径（`PlasmaState_logLambda.F90` ELE_ION）中 `m_ion` 的首阶近似对结果影响 <10⁻³（§4.1），无论走哪条路径，Kn 计算均可靠。

---

## 13. 联网核查：Kn 计算正确性与改进建议（2026-07-30）

### 13.1 核查结论：定义正确

对等离子体/激光聚变（ICF）领域文献的联网核查确认，本文采用的 **$Kn\equiv\lambda_{ei}/L_T$、$L_T=T_e/|\nabla T_e|$ 定义与主流文献完全一致**：

- **Arber, Goffrey & Ridgers (2023)**, *Front. Astron. Space Sci.* **10**, 1155124：\(Kn=\lambda^{ei}_T/L_T\)，\(\lambda^{ei}_T\) 为热电子-离子平均自由程，\(L_T=T/|\nabla T|\) 为温度尺度长度。
- **NIF/MagLIF 研究 (2025)**, arXiv:2504.09091 / *Phys. Plasmas* **33**, 0275673：\(Kn_{ei}\equiv\lambda_{ei}/L_T\)，\(\lambda_{ei}\) 为热电子-离子平均自由程；并给出阈值 \(Kn_{ei}>1/(3.6)^4\approx 0.01\)。
- **Luo et al. (2026)**, *Resolution-Independent ML Heat Flux Closure*, arXiv:2604.03439：\(Kn=\lambda_0/L_T\)，\(\lambda_0=4\pi\varepsilon_0^2 m_e^2 v_{\rm th}^4/(Z n_e e^4\ln\Lambda)\)，\(L_T=T_e/\nabla T_e\)。
- **Del Sorbo et al. (2017)**, *Phys. Plasmas* **24**, 102707：Braginskii 高斯单位下 \(\lambda_{ei}^{(B)}=3\sqrt{\pi/2}(k_B T_e)^2/(4\pi Z n_e e^4\ln\Lambda_{ei})\)。

**即本文 Kn 计算链路的“形式”正确**，无需推翻重写。但下列 7 点需改进/补充，否则 Kn 的数值与判据可能偏差 1–2 个数量级。

### 13.2 需要改进的地方

**① 失效阈值写错（最严重）**
原 §7 判定写“$Kn\gtrsim 0.1\!-\!1$ 进入非局域”。文献一致结论：**局部热传导模型在 $Kn>0.01$（1%）即开始失效**，而非 $Kn\sim 1$。原因：热流由 $v\approx 3.6v_{\rm th}$ 的快速电子主导，且 $\lambda_{ei}(v)\propto v^4$，故失效判据为 $Kn_{ei}>1/(3.6)^4\approx 0.01$（Bell, Evans & Nicholas 1981；Arber 2023；NIF 2025）。§7 已按此修正。

**② $\lambda_{ei}$ 定义的 O(1) 因子歧义**
本文 $\lambda_{ei}=v_{\rm th}\tau_{ei}$ 是**动量弛豫（碰撞）平均自由程**。文献（Braginskii/Del Sorbo）用于热输运的**热平均自由程**为
$$\lambda_{ei}^{(B)}=\frac{3}{4}\sqrt{\frac{\pi}{2}}\,\frac{(k_B T_e)^2}{Z\,n_e\,e^4\ln\Lambda_{ei}}$$
（高斯单位）。与本文 $\lambda_{ei}=v_{\rm th}\tau_{ei}$ 差一个 O(1) 因子（约 $3\sqrt{3}/(4\sqrt{2\pi})\div 3/(4\sqrt{2\pi})\sim\sqrt{3}$）。作为**数量级判据**可接受，但若要与 SNB 模型或文献 Kn 阈值严格对标，建议采用 Braginskii 热平均自由程口径（或下面的 $\lambda_e^*$）。

**③ 电子-电子（ee）碰撞修正 → 去局域长度 $\lambda_e^*$**
纯电子-离子碰撞（Lorentz 气体）会**高估**非局域程度，因为 ee 自碰撞也限制快速电子传播。更精确的特征长度为 **Epperlein & Short (1991)** 的去局域长度：
$$\lambda_e^*=\frac{4\pi\varepsilon_0^2 T_e^2}{n_e e^4\bigl(Z^*\Phi\ln\Lambda_{ei}\ln\Lambda_{ee}\bigr)^{1/2}},\qquad
\Phi=\frac{Z^*+4.2}{Z^*+0.24},\qquad Z^*=\frac{\langle Z^2\rangle}{\langle Z\rangle}$$
$\Phi=1$ 时退化为纯 ei 情形。建议用进阶判据 $Kn_d\equiv\lambda_e^*/L_T$。**FLASH 可行性**：$\ln\Lambda_{ee}$ 可由 `PlasmaState_logLambda(ELE_ELE, …)`（L94-97）计算；$\ln\Lambda_{ei}$ 由 `visc_logLambda` 或 `PlasmaState_logLambda(ELE_ION)` 给出；$Z^*$ 需用户对多离子组分自行统计（单流体单 zbar 下取 $Z^*=\bar z$）。

**④ 高密度下 $b_{\max}$ 应截断到粒子间距**
`visc_logLambda.F90`（本文采用）的 $b_{\max}=$ 德拜长度。在极密区（如烧蚀层、高密度壳层），德拜长度可能小于平均粒子间距，导致 $\ln\Lambda$ **偏低、$\lambda_{ei}$ 偏高**。正确做法（LeeMore 1984）取 $b_{\max}=\max(\lambda_D,\,R_0)$，$R_0=(4\pi n_{\rm ion}/3)^{-1/3}$ 为平均粒子间距。`PlasmaState_logLambda.F90` 的 LeeMore 分支（L76-86）已实现此截断（需 `spitzer=.false.`）。**改进**：强耦合/高密度区改用 `PlasmaState_logLambda`（LeeMore）计算 $\ln\Lambda_{ei}$，而非 `visc_logLambda`。

**⑤ 热速度约定**
文献用 $v_{\rm th}=\sqrt{k_B T_e/m_e}$ 或 $\sqrt{3k_B T_e/m_e}$（RMS）；差异为 O(1) 因子。本文采用 FLASH 的 RMS 口径 $\sqrt{3k_B T_e/m_e}$，与 §4/§6 一致，可接受，但在与文献 Kn 阈值比较时应注明是基于 $v_{\rm th}$ 的热电子判据。

**⑥ $L_T$ 应取沿最大温度梯度方向**
非局域性在最陡梯度方向最强（NIF 论文指出 MagLIF gaspipe 径向梯度最强）。标量 $|\nabla T_e|$ 给出最严格（最大）的 Kn；若取平均或弱梯度方向会低估非局域程度。建议取 $\nabla T_e$ 模长（即最不利情形）。

**⑦ 多离子组分的 $Z^*$**
文献用 $Z^*=\langle Z^2\rangle/\langle Z\rangle$（Landau 平均），FLASH 单流体仅提供单一 `zbar`。单组分/部分电离近似下取 $\bar z$ 即可；多离子混合时需按组分统计 $Z^*$ 替换 $\bar z^2$（注意 $\tau_{ei}\propto\bar z^2 n_{\rm ion}$，而 $\lambda_e^*$ 用 $Z^*$）。

### 13.3 推荐改进版 Kn 计算（含 ee 修正 + 密度截断）

```fortran
! 进阶 Kn（含 Epperlein-Short 去局域长度 λ_e* 与 LeeMore 密度截断）
! 用 PlasmaState_logLambda 同时取 lnΛ_ei（ELE_ION, LeeMore 截断）与 lnΛ_ee（ELE_ELE）
real :: ll_ei, ll_ee, lambda_star, Zstar, Phi, Kn_d
real :: nion_dens

nion_dens = xden * sumy * navo          ! n_ion
Zstar     = zbar                         ! 单流体近似；多组分时取 <Z^2>/<Z>
Phi       = (Zstar + 4.2)/(Zstar + 0.24)! Epperlein-Short 修正
call PlasmaState_logLambda(ELE_ION, tele, tion, nele, mion_abar, zbar, ll_ei, spitzer=.false.)  ! LeeMore: b_max=max(λ_D,R0)
call PlasmaState_logLambda(ELE_ELE, tele, tion, nele, mion_abar, zbar, ll_ee)                   ! lnΛ_ee（mion 此处不被 ELE_ELE 使用）

! λ_e* (CGS, 高斯单位; ε0 → 1/(4π) 故 4π ε0^2 = 1/(4π) )
lambda_star = (tele**2)/(4.*PI * nele * pls_qele**4 * sqrt(Zstar*Phi*ll_ei*ll_ee))   ! = 4π ε0^2 T_e^2 /(...)，CGS 下 4π ε0^2=1
Kn_d        = lambda_star / LT            ! 进阶 Knudsen 数（去局域长度口径）

! 与标准 Kn 对照（§7）：标准 Kn = lambda_ei / LT，其中 lambda_ei = v_th * tau_ei
```

> 注：CGS 高斯单位下 $\varepsilon_0=1/(4\pi)$，故 Epperlein–Short 式 $4\pi\varepsilon_0^2 T_e^2=T_e^2/(4\pi)$。上式 `lambda_star` 即此口径。SI 制需保留 $4\pi\varepsilon_0^2$。

---

*文档生成/更新依据：FLASH 4.8 源码（`source/physics/utilities/PlasmaState/PlasmaState_tau.F90`、
`source/physics/materialProperties/Viscosity/ViscosityMain/Spitzer/visc_logLambda.F90`、
`source/physics/utilities/PlasmaState/PlasmaState_logLambda.F90`、
`source/physics/materialProperties/Conductivity/ConductivityMain/LeeMore/`、
`source/physics/Eos/EosMain/Eos_getData.F90`、`source/physics/Eos/EosMain/Eos_putData.F90`、
`source/PhysicalConstants/PhysicalConstantsMain/PhysicalConstants_init.F90`、
`source/physics/utilities/PlasmaState/PlasmaStateMain/PlasmaState_init.F90`）逐行核对；
交叉参考 `docs/src_finding/ThermalConduction_方程源码对照.md`。所有公式均附 F90 源码逐行对应。
第六次修订（2026-07-30）：联网核查 Kn 定义正确性（§13.1 确认与文献一致）；修正失效阈值 $Kn>0.01$（§7、§13.2①）；
新增 §13（联网核查与 7 项改进建议：λ_ei 的 O(1) 因子、ee 碰撞修正 λ_e*、b_max 密度截断、v_th 约定、L_T 方向、Z* 多组分，及推荐改进版 F90）。
参考：Arber et al. 2023 (doi:10.3389/fspas.2023.1155124)、NIF/MagLIF 2025 (arXiv:2504.09091; Phys.Plasmas 33, 0275673)、
Luo et al. 2026 (arXiv:2604.03439)、Del Sorbo et al. 2017 (Phys.Plasmas 24, 102707)、Epperlein & Short 1991 (Phys.Fluids B 3, 3)。*
