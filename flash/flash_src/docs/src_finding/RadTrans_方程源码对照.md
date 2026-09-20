# 多群辐射扩散（RadTrans/MGD）源码与方程对照

> 本文档追踪 FLASH 中多群辐射扩散（Multigroup Diffusion, MGD）从物理方程到 Fortran 代码的实现路径。
> 这是 FLASH 中**最复杂的物理模块**之一，涉及 RadTrans + Opacity + Diffuse 三个单元的协作。

> 参考文件：
> - MGD 主驱动: `source/physics/RadTrans/RadTransMain/MGD/RadTrans.F90`
> - 限流器: `.../MGD/RadTrans_computeFluxLimiter.F90`
> - Planck 积分: `source/physics/RadTrans/RadTransMain/RadTrans_planckInt.F90`
> - 能量汇总: `.../RadTransMain/RadTrans_sumEnergy.F90`
> - 边界条件: `.../MGD/RadTrans_mgdSetBc.F90`
> - 不透明度: `source/physics/materialProperties/Opacity/OpacityMain/.../Opacity.F90`
> - 扩散求解: `source/physics/Diffuse/DiffuseMain/Diffuse_solveScalar.F90`
> - 文档: `docs/flash4_ug_4p8.md` 第14、25章

---

## 目录

1. [物理方程](#1-物理方程)
2. [模块架构](#2-模块架构)
3. [物理常量与数据结构](#3-物理常量与数据结构)
4. [Step 1：预处理——总能归一化](#4-step-1预处理总能归一化)
5. [Step 2：逐群主循环——群扩散方程求解](#5-step-2逐群主循环群扩散方程求解)
6. [Step 3：通量限流（Diffuse_fluxLimiter）](#6-step-3通量限流diffuse_fluxlimiter)
7. [Step 4：隐式扩散求解（Diffuse_solveScalar）](#7-step-4隐式扩散求解diffuse_solvescalar)
8. [Step 5：吸收后处理](#8-step-5吸收后处理)
9. [不透明度（Opacity 单元）](#9-不透明度opacity-单元)
10. [Planck 积分函数（RadTrans_planckInt）](#10-planck-积分函数radtrans_planckint)
11. [完整数据流与代码行号对应](#11-完整数据流与代码行号对应)

---

## 1. 物理方程

### 全辐射输运方程（第14章，式14.11-14.15）

FLASH 使用**多群扩散**（Multigroup Diffusion, MGD）近似处理辐射输运。对于第 $g$ 群（$1 \le g \le N_g$）：

$$\frac{\partial u_g}{\partial t} + \nabla \cdot (u_g \mathbf{v}) + \frac{u_g}{\varepsilon_{\text{rad}}} (P_{\text{rad}} : \nabla \mathbf{v}) = -\nabla \cdot \mathbf{q}_g + Q_{\text{emis},g} - Q_{\text{abs},g}$$

### 扩散近似

群通量采用 Fick 定律形式：

$$\mathbf{q}_g = -D_g \nabla u_g, \quad D_g = \frac{c}{3\kappa_{\text{tr},g}}$$

其中 $D_g$ 是群扩散系数，$\kappa_{\text{tr},g}$ 是群输运不透明度。

### 吸收项

$$Q_{\text{abs},g} = c \cdot \kappa_{\text{a},g} \cdot u_g$$

### 发射项（Planck）

$$Q_{\text{emis},g} = \kappa_{\text{e},g} \cdot c \cdot a T_{\text{ele}}^4 \cdot \frac{15}{\pi^4} [\mathcal{P}(x_g) - \mathcal{P}(x_{g+1})]$$

其中：
- $x_g = h\nu_g / (k_B T_{\text{ele}})$ — 归一化群边界能量
- $\mathcal{P}(x) = \int_0^x \frac{t^3}{e^t - 1} dt$ — 归一化 Planck 积分（不完全）
- $a = 4\sigma/c$ — 辐射常数

### 算子分裂的绝热部分

在 Hydro 单元处理完 $(u_g\mathbf{v})$ 绝热项后，RadTrans 单元求解剩余部分：

$$\frac{\partial u_g}{\partial t} = \nabla \cdot (D_g \nabla u_g) + Q_{\text{emis},g} - Q_{\text{abs},g}$$

---

## 2. 模块架构

```
RadTrans/
│
├── RadTransMain/
│   ├── MGD/                    ← 多群扩散 (本文档重点)
│   │   ├── RadTrans.F90        ← 主驱动: 逐群循环 + 吸收/发射
│   │   ├── RadTrans_computeDt.F90
│   │   ├── RadTrans_computeFluxLimiter.F90  ← 辐射通量限流
│   │   ├── RadTrans_mgdEFromT.F90 / ..._UFromT.F90  ← 温度↔能量转换
│   │   ├── RadTrans_mgdSetBc.F90 / ..._SetBound.F90  ← 边界条件
│   │   ├── rt_data.F90         ← MGD运行时参数
│   │   ├── rt_init.F90         ← 初始化
│   │   ├── ExpRelax/           ← ExpRelax 变体
│   │   └── Unified/            ← Unified MGD 变体
│   ├── RadTrans_data.F90       ← 全局数据（物理常量）
│   ├── RadTrans_init.F90       ← 初始化
│   ├── RadTrans_planckInt.F90  ← Planck 积分函数
│   ├── RadTrans_sumEnergy.F90  ← 群能量汇总
│   └── ...
│
├── localAPI/                   ← 本地接口
├── RadTrans_interface.F90      ← 接口定义
└── RadTrans.F90                ← 顶层包装

materialProperties/
└── Opacity/                    ← 不透明度
    └── OpacityMain/
        └── .../Opacity.F90     ← 提供 κ_a, κ_e, κ_tr
```

---

## 3. 物理常量与数据结构

### 物理常量（RadTrans_data.F90）

```fortran
!! RadTrans_data.F90
real :: rt_boltz    = 1.3806503e-16   ! 玻尔兹曼常数 k_B [erg/K]
real :: rt_speedlt  = 2.99792458e10   ! 光速 c [cm/s]
real :: rt_speedlt3 = rt_speedlt / 3  ! c/3
real :: rt_radconst = 7.5657e-15      ! 辐射常数 a [erg·cm⁻³·K⁻⁴]
```

### MGD 运行时参数（rt_data.F90）

```fortran
!! rt_data.F90
integer :: rt_mgdNumGroups          ! 群数 N_g
real    :: rt_mgdBounds(N_g+1)      ! 群边界能量 [hν_1, hν_2, ..., hν_{Ng+1}]
real    :: rt_mgdFlCoef             ! 通量限流系数 f_lim
integer :: rt_mgdFlMode             ! 限流模式
real    :: rt_mgdthetaImplct        ! 隐式参数 θ (0=显式, 1=全隐)
```

### 群能量变量索引

每组辐射能量存储在独立的 UNK 变量中，索引通过 `MGDR_NONREP_LOC2UNK(gloc)` 从局部群编号映射到全局变量编号。

```fortran
!! 主临时变量:
MGDC_VAR   — 辐射能量变化量 (Δu_g 的汇总)
ERAD_VAR   — 总辐射能量 (∑u_g)
COND_VAR   — 扩散系数 D_g
ABSR_VAR   — 吸收系数 c·κ_a
EMIS_VAR   — 发射系数 κ_e·c·aT⁴·ΔP
FLLM_VAR   — 通量限流因子 3λ
DFCF_VAR   — 前导系数 (恒为 1.0)
```

---

## 4. Step 1：预处理——总能归一化

### 代码位置：`MGD/RadTrans.F90` 行119-203

```fortran
!! 第0步: 计算总辐射能并归一化群能量 (行137-186)

!! 累计各群能量 → MGDC_VAR (行138-155):
do gloc = 1, NGROUPS
   gvar = MGDR_NONREP_LOC2UNK(gloc)
   do k = ...
      do j = ...
         do i = ...
            blkPtr(MGDC_VAR,i,j,k) = blkPtr(MGDC_VAR,i,j,k) + blkPtr(gvar,i,j,k)
         enddo
      enddo
   enddo
enddo

!! 用 ERAD_VAR 归一化各群能量 (行159-186):
!!  如果总辐射能量变化，按比例调整各群
!!  f = ERAD_VAR / MGDC_VAR
!!  u_g_new = u_g_old * f
```

这个步骤确保：$\sum_g u_g = e_{\text{rad}}$（辐射总比能守恒）。

---

## 5. Step 2：逐群主循环——群扩散方程求解

### 代码位置：`MGD/RadTrans.F90` 行250-509

这是 MGD 的核心。对每个群 $g$ 依次执行：

```fortran
!! ★★★ 逐群循环 ★★★ (行250)
do gloc = 1, NONREP_NLOCS(rt_acrossMe, rt_meshCopyCount, rt_mgdNumGroups)
   gvar = MGDR_NONREP_LOC2UNK(gloc)    !! 群能量变量索引
   g    = NONREP_LOC2GLOB(gloc, ...)   !! 全局群编号

   !! ▓▓▓ A: 能量密度转换 (行291) ▓▓▓
   !!    u_g(erg/cm³) = e_g(erg/g) × ρ(g/cm³)
   blkPtr(gvar,i,j,k) = blkPtr(gvar,i,j,k) * blkPtr(DENS_VAR,i,j,k)

   !! ▓▓▓ B: 不透明度查询 + 扩散系数 (行296-344) ▓▓▓
   do k = ...
      do j = ...
         do i = ...

            !! B1: 获取不透明度 (行301):
            call Opacity(blkPtr(:,i,j,k), g, absorb_opac, emit_opac, trans_opac)

            !! B2: ★★★ 扩散系数 D_g = c/(3κ_tr) ★★★ (行312):
            blkPtr(COND_VAR,i,j,k) = rt_speedlt3 / max(TINY, trans_opac)

            !! B3: 前导系数 (行316):
            blkPtr(DFCF_VAR,i,j,k) = 1.0

            !! B4: ★★★ 吸收项 Q_abs = c·κ_a ★★★ (行319):
            blkPtr(ABSR_VAR,i,j,k) = C * absorb_opac

            !! B5: ★★★ 发射项 Q_emis (Planck) ★★★ (行322-333):
            tele = blkPtr(TELE_VAR,i,j,k)
            if (kB*tele > 0.0) then
               xg    = rt_mgdBounds(g)   / (kB*tele)      ! x_g = hν_g/kT
               xgp1  = rt_mgdBounds(g+1) / (kB*tele)      ! x_{g+1}
               call RadTrans_planckInt(xg, pxg)            ! 不完全Planck积分
               call RadTrans_planckInt(xgp1, pxgp1)
               emiss = emit_opac * C * a*tele**4           &
                     * 15/pi**4 * (pxgp1 - pxg)            !! (行329)
            else
               emiss = 0.0
            end if
            blkPtr(EMIS_VAR,i,j,k) = emiss

            !! B6: 限流值 (行340):
            blkPtr(FLLM_VAR,i,j,k) = rt_mgdFlCoef * C * blkPtr(gvar,i,j,k)
         enddo
      enddo
   enddo

   !! ▓▓▓ C: 通量限流 (行356) ▓▓▓
   call Diffuse_fluxLimiter(COND_VAR, gvar, FLLM_VAR, rt_mgdFlMode, nblk, blklst)

   !! ▓▓▓ D: ★★★ 隐式扩散求解 ★★★ (行415-419) ▓▓▓
   call Diffuse_solveScalar(gvar, COND_VAR, DFCF_VAR, &
                            bcTypes, bcValues, dt, 1.0, 1.0, mgdTheta, &
                            pass, nblk, blklst, ABSR_VAR, EMIS_VAR)
   ! ↑ 求解: u_g^{n+1} = u_g^n + Δt·[∇·(D∇u_g) + Q_emis - Q_abs]

   !! ▓▓▓ E: 吸收后处理 (行473-506) ▓▓▓
   do k = ...
      do j = ...
         do i = ...
            urad = blkPtr(gvar,i,j,k)                        !! 更新后的 u_g
            call Opacity(blkPtr(:,i,j,k), g, absorb_opac, ...)  !! 重新查询吸收系数

            !! ★★★ 吸收能量: ΔE += urad·c·κ_a ★★★ (行490):
            change = change + urad * C * absorb_opac

            !! 能量密度→比能 (行494-496):
            rho = blkPtr(DENS_VAR,i,j,k)
            blkPtr(gvar,i,j,k) = urad / rho

            !! 累计总辐射能 ERAD_VAR (行499-501):
            ERAD_VAR = ERAD_VAR + eradg
         enddo
      enddo
   enddo

end do  !! 下一个群
```

---

## 6. Step 3：通量限流（Diffuse_fluxLimiter）

### 文件
`source/physics/Diffuse/DiffuseMain/Diffuse_fluxLimiter.F90`

### 物理

辐射扩散在光学薄区（$\kappa \Delta x \ll 1$）会高估通量。限流器的功能是让扩散系数从 $D = c/(3\kappa)$ 在光学薄区平滑过渡到 $D = \lambda c u_g / |\nabla u_g|$：

$$\lambda_g = \frac{1}{3} \cdot \frac{2}{2 + |\nabla u_g|/(\kappa_{\text{tr},g} u_g)} \quad \text{(Levermore-Pomraning)}$$

### 调用方式（MGD/RadTrans.F90 行356）

```fortran
call Diffuse_fluxLimiter(COND_VAR, gvar, FLLM_VAR, rt_mgdFlMode, nblk, blklst)
```

输入：`COND_VAR`（限流前扩散系数），`gvar`（群辐射能）
输出：`FLLM_VAR`（$3\lambda$），`COND_VAR`（限流后扩散系数）

---

## 7. Step 4：隐式扩散求解（Diffuse_solveScalar）

### 文件
`source/physics/Diffuse/DiffuseMain/Diffuse_solveScalar.F90`

### 物理

求解离散化的扩散方程：

$$\frac{u_g^{n+1} - u_g^n}{\Delta t} = \theta \cdot \nabla \cdot (D_g \nabla u_g^{n+1}) + (1-\theta) \cdot \nabla \cdot (D_g \nabla u_g^n) + Q_{\text{emis},g} - c\kappa_{\text{a},g} u_g^{n+1}$$

其中 $\theta$ 是隐式参数（`rt_mgdthetaImplct`），$Q_{\text{abs}} = c\kappa_a u_g^{n+1}$ 用隐式处理以保证正定性。

### 调用方式（MGD/RadTrans.F90 行415-419）

```fortran
call Diffuse_solveScalar( &
     gvar,                          & ! 待求解变量: 第g群辐射能 u_g
     COND_VAR,                      & ! 扩散系数 D_g (已限流)
     DFCF_VAR,                      & ! 前导系数 = 1.0
     bcTypes, bcValues,             & ! 边界条件
     dt,                            & ! 时间步
     1.0, 1.0, mgdTheta,            & ! θ 方法参数
     pass, nblk, blklst,            & ! block信息
     ABSR_VAR, EMIS_VAR)              ! 吸收/发射系数
```

### 线性系统求解

`Diffuse_solveScalar` 内部构建一个线性系统 $Ax = b$，其中 x = $u_g^{n+1}$，用 HYPRE（默认）或 Pardiso 等外部线性求解器求解。

---

## 8. Step 5：吸收后处理

### 代码位置：`MGD/RadTrans.F90` 行473-506

```fortran
!! 吸收能量累计到 MGDC_VAR (行489-491):
!!   对于每个网格单元:
change = blkPtr(MGDC_VAR,i,j,k)
change = change + urad * C * absorb_opac   !! ΔE_abs = u_g·c·κ_a·Δt
blkPtr(MGDC_VAR,i,j,k) = change

!! 将 u_g(erg/cm³) 转回比能 e_g = u_g/ρ (行493-496):
blkPtr(gvar,i,j,k) = urad / rho
```

### 与电子能量方程的耦合

`MGDC_VAR` 中累计的净能量变化 $\Delta E = \sum_g (u_g \cdot c \cdot \kappa_{a,g} - \text{emiss}_g)$ 最终传输到电子能量方程：

$$\rho \frac{\partial e_{\text{ele}}}{\partial t} = \sum_g (Q_{\text{abs},g} - Q_{\text{emis},g})$$

---

## 9. 不透明度（Opacity 单元）

### 文件
`source/physics/materialProperties/Opacity/OpacityMain/.../Opacity.F90`

### 接口

```fortran
call Opacity(solnVec, g, absorb_opac, emit_opac, trans_opac)
```

### 返回值

| 变量 | 含义 | 单位 |
|------|------|------|
| `absorb_opac` | 吸收不透明度 $\kappa_{a,g}$ | 1/cm |
| `emit_opac` | 发射不透明度 $\kappa_{e,g}$ | 1/cm |
| `trans_opac` | 输运不透明度 $\kappa_{tr,g}$ | 1/cm |

### 不透明度模型

FLASH 提供多种不透明度模型（在 `OpacityMain/` 下）：
- **Local**：局域热动平衡（LTE），查表或解析公式
- **Multigroup**：多群平均不透明度
- **Constant**：常数（测试用）

---

## 10. Planck 积分函数（RadTrans_planckInt）

### 文件
`source/physics/RadTrans/RadTransMain/RadTrans_planckInt.F90`

### 物理

计算归一化不完全 Planck 积分：

$$\mathcal{P}(x) = \int_0^x \frac{t^3}{e^t - 1} \, dt$$

与完整 Planck 积分 $\int_0^\infty \frac{t^3}{e^t-1} dt = \pi^4/15$ 的比值即为：

$$\frac{\mathcal{P}(x)}{\mathcal{P}(\infty)} = \frac{15}{\pi^4} \int_0^x \frac{t^3}{e^t - 1} dt$$

因此第 $g$ 群的发射项为：

$$Q_{\text{emis},g} = \kappa_{e,g} \cdot c \cdot a T^4 \cdot \frac{15}{\pi^4} [\mathcal{P}(x_{g+1}) - \mathcal{P}(x_g)]$$

### 调用

```fortran
!! MGD/RadTrans.F90 行327-328:
call RadTrans_planckInt(xg,   pxg)
call RadTrans_planckInt(xgp1, pxgp1)
```

---

## 11. 完整数据流与代码行号对应

### 代码行号速查表

| 功能 | 文件 | 关键行 |
|------|------|--------|
| **MGD主入口** | `MGD/RadTrans.F90` | 行31: `subroutine RadTrans` |
| **群循环开始** | `MGD/RadTrans.F90` | 行250: `do gloc = 1, NGROUPS` |
| 不透明度查询 | `MGD/RadTrans.F90` | 行301: `call Opacity(...)` |
| **扩散系数 D_g** | `MGD/RadTrans.F90` | 行312: `COND_VAR = c/3κ_tr` |
| 前导系数 | `MGD/RadTrans.F90` | 行316: `DFCF_VAR = 1.0` |
| **吸收项 cκ_a** | `MGD/RadTrans.F90` | 行319: `ABSR_VAR = C * absorb_opac` |
| **发射项 (Planck)** | `MGD/RadTrans.F90` | 行322-333 |
| Planck 积分 | `MGD/RadTrans.F90` | 行327-328: 调用 `RadTrans_planckInt` |
| 通量限流值 | `MGD/RadTrans.F90` | 行340: `FLLM_VAR = f_lim · c · u_g` |
| Planck 积分函数 | `RadTransMain/RadTrans_planckInt.F90` | 主体 |
| 通量限流 | `MGD/RadTrans.F90` | 行356: `call Diffuse_fluxLimiter` |
| **扩散隐式求解** | `MGD/RadTrans.F90` | 行415-419: `call Diffuse_solveScalar` |
| **吸收累计** | `MGD/RadTrans.F90` | 行490: `change += urad·c·κ_a` |
| 能量密度→比能 | `MGD/RadTrans.F90` | 行496: `u_g/ρ` |
| 总辐射能累计 | `MGD/RadTrans.F90` | 行500: `ERAD_VAR += e_g` |
| 辐射常量 | `RadTrans_data.F90` | rt_speedlt, rt_boltz, rt_radconst |
| MGD 参数 | `rt_data.F90` | rt_mgdNumGroups, rt_mgdBounds, etc. |
| 不透明度接口 | `Opacity/.../Opacity.F90` | 主体 |

### 数据流总图（逐群流程）

```
                    第g群
                      │
                      ▼
    ┌──────────────────────────────────┐
    │ 能量密度转换 (行291)              │
    │ u_g(erg/cm³) = e_g(erg/g)·ρ     │
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │ 不透明度查询 (行301)              │
    │ Opacity() → κ_a, κ_e, κ_tr     │
    └──┬───────────────┬───────────────┘
       │               │
       ▼               ▼
    ┌──────────┐  ┌──────────────────────┐
    │ 扩散系数  │  │ 发射项 (行322-333)   │
    │ D_g=c/(3κ)│  │ Q_emis=κ_e·c·aT⁴·ΔP│
    │ (行312)   │  │ △P=PlanckInt差分    │
    └─────┬────┘  └──────────┬───────────┘
          │                  │
          ▼                  ▼
    ┌──────────────────────────────────┐
    │ 通量限流 (行356)                  │
    │ Diffuse_fluxLimiter(COND_VAR,...) │
    │ D_limited = D/(1+3λ·D·|∇u|/(c·u))│
    └──────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │ ★★★ 核心: 扩散求解 (行415-419) ★★★│
    │ Diffuse_solveScalar(u_g, D_g,    │
    │   A=1.0, bc, dt, θ=theta,        │
    │   src_abs=ABSR, src_emis=EMIS)   │
    │                                   │
    │ 求解: u_g^{n+1} = u_g^n          │
    │   +Δt·[∇·D_g∇u_g + Q_emis        │
    │        - cκ_a·u_g^{n+1}]         │
    └──────────────┬───────────────────┘
                   │ u_g^{n+1}
                   ▼
    ┌──────────────────────────────────┐
    │ 吸收后处理 (行473-506)            │
    │ ΔE_rad += u_g·c·κ_a              │
    │ u_g(erg/cm³) → e_g = u_g/ρ      │
    │ ERAD_VAR += e_g                  │
    └──────────────┬───────────────────┘
                   │
                   ▼
           进入下一群 g+1
```

### 与 3T 电子/离子方程的耦合

```
    RadTrans 完成所有群后:

    MGDC_VAR = Σ(u_g^n - u_g^{n+1})
             = Σ(净吸收 - 净发射)

    电子能量方程接收:
    ∂(ρe_ele)/∂t = ... + ρ·MGDC_VAR/dt
                   (吸收能量 - 发射能量)

    这个耦合在 Heatexchange 或下一个算子分裂步骤中处理
```

### 关键点总结

1. **扩散系数**：$D_g = c/(3\kappa_{\text{tr},g})$，由不透明度单元提供输运不透明度
2. **发射项**：基于 Planck 黑体谱积分，通过 `RadTrans_planckInt` 计算每个群的能量窗口内黑体辐射功率
3. **隐式求解**：吸收项 $c\kappa_a u_g$ 做隐式处理（在 `Diffuse_solveScalar` 的源项矩阵中），避免显式格式对 $1/(c\kappa_a)$ 的严格时间步约束
4. **限流器**：辐射通量限流与电子热传导限流共享同一个 `Diffuse_fluxLimiter` 框架，但输入参数不同
5. **多群并发**：群与群之间按顺序求解（串行），但群内扩散方程通过 HYPRE 并行求解
