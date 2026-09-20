# hy_uhd_unsplitUpdate.F90 与守恒方程(14.1)的源码对照

> 本文档逐个方程、逐行解释 FLASH 非分裂（unsplit）流体求解器中**守恒变量更新**模块与
> 第14章式(14.1a-c)三个守恒律之间的精确对应关系。
>
> 参考文件：
> - 源文件: `FLASH4.8/source/physics/Hydro/HydroMain/unsplit/hy_uhd_unsplitUpdate.F90`
> - 通量计算: `FLASH4.8/source/physics/Hydro/HydroMain/unsplit/hy_uhd_prim2flx.F90`
> - 主驱动: `FLASH4.8/source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90`
> - 索引定义: `FLASH4.8/source/physics/Hydro/HydroMain/unsplit/UHD.h`
> - 文档: `docs/flash4_ug_4p8.md` 第14-15章

---

## 目录

1. [核心方程回顾](#1-核心方程回顾)
2. [数值方法：有限体积法](#2-数值方法有限体积法)
3. [Step 0：主驱动 hy_uhd_unsplit（宏观数据流）](#3-step-0主驱动-hy_uhd_unsplit宏观数据流)
4. [Step A：Riemann求解器——动量/能量通量的选值核心](#4-step-a-Riemann求解器)
5. [变量索引体系（UHD.h）](#5-变量索引体系uhdh)
6. [Step 1：原始变量 → 守恒变量（调用前准备）](#6-step-1原始变量--守恒变量调用前准备)
7. [Step 2：通量向量（hy_uhd_prim2flx）](#7-step-2通量向量hy_uhd_prim2flx)
8. [Step 3：守恒更新核心（updateConservedVariable）](#8-step-3守恒更新核心updateconservedvariable)
9. [Step 4：几何源项（非笛卡尔坐标系）](#9-step-4几何源项非笛卡尔坐标系)
10. [Step 5：物理源项（压力做功、重力、欧姆加热等）](#10-step-5物理源项压力做功重力欧姆加热等)
11. [完整数据流总图](#11-完整数据流总图)

---

## 1. 核心方程回顾

FLASH 文档第14章式(14.1a-c) —— 无磁场等离子体的质量、动量、能量守恒：

| 编号 | 方程 | 物理含义 |
|------|------|----------|
| (14.1a) | $\partial_t \rho + \nabla\cdot(\rho\mathbf{v}) = 0$ | **质量守恒** |
| (14.1b) | $\partial_t (\rho\mathbf{v}) + \nabla\cdot(\rho\mathbf{v}\mathbf{v} + P_\text{tot}\mathbf{I}) = 0$ | **动量守恒** |
| (14.1c) | $\partial_t E_\text{tot} + \nabla\cdot[(E_\text{tot} + P_\text{tot})\mathbf{v}] = Q_\text{las} - \nabla\cdot\mathbf{q}$ | **总能量守恒**（含源项） |

其中总压力 $P_\text{tot} = P_\text{ion} + P_\text{ele} + P_\text{rad}$，
总比能 $E_\text{tot} = e_\text{ion} + e_\text{ele} + e_\text{rad} + \frac{1}{2}\rho|\mathbf{v}|^2$。

在本轮 **Hydro 单元**的算子分裂中，只求解**无源项的绝热部分**（第14章式14.6）：

```text
∂ρ/∂t + ∇·(ρv) = 0
∂(ρv)/∂t + ∇·(ρvv + P_tot·I) = 0
∂(ρE_tot)/∂t + ∇·[(ρE_tot + P_tot)v] = 0
```

其它源项（激光加热、热传导、辐射吸收/发射）在后面的热传导、辐射、能量沉积单元中单独处理。

---

## 2. 数值方法：有限体积法

FLASH unsplit 求解器采用**有限体积法**。核心思想：

对网格单元 $(i,j,k)$，守恒律的离散形式为：

```text
U^{n+1} = U^{n} - Δt · [ (F_{i+1/2} - F_{i-1/2})/Δx 
                        + (G_{j+1/2} - G_{j-1/2})/Δy 
                        + (H_{k+1/2} - H_{k-1/2})/Δz ]
                       + Δt · (S_geo + S_phys)
```

其中：
- **U** = $[\rho, \rho v_x, \rho v_y, \rho v_z, \rho E]^T$ — 守恒变量向量
- **F, G, H** — x, y, z 方向的面通量向量
- **S_geo** — 非笛卡尔坐标系的几何源项（如柱坐标/球坐标的额外项）
- **S_phys** — 物理源项（如压力做功修正项）

整个过程分为三步：

```
hy_uhd_unsplit.F90 (主驱动)
  │
  ├── 1. 数据重构 (PPM/WENO) → 单元边界左右状态
  ├── 2. 黎曼求解器 → 面通量 F(i±½), G(j±½), H(k±½)
  │     └── hy_uhd_getFaceFlux → hy_uhd_RiemannSolver → hy_uhd_prim2flx
  │
  └── 3. hy_uhd_unsplitUpdate (更新守恒变量)
        └── updateConservedVariable (有限体积离散)
```

---

## 3. Step 0：主驱动 hy_uhd_unsplit（宏观数据流）

### 文件位置
`source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90`

### 主驱动职责

`hy_uhd_unsplit` 是整个 Hydro 单元的**顶层入口**。它接收一个 block 列表，对每个 block 依次执行：

```
hy_uhd_unsplit (行64)
  │
  │  对每个 block（行446-）:
  │
  ├── [A] 重力预备:  hy_uhd_prepareNewGravityAccel   (行455)
  │
  ├── [B] 面通量计算: hy_uhd_getFaceFlux              (行465-471)
  │     └── 内部流程:
  │           1. 调用 hy_uhd_getRiemannState → 数据重构 (PPM/WENO)
  │              → 获得单元面左右状态 VL, VR
  │           2. 调用 Riemann 求解器 (如 hy_uhd_HLLC)
  │              → 内部调用 hy_uhd_prim2flx 计算左/右通量
  │              → 应用 HLLC 公式得到最终界面通量 F*
  │           3. 可选: 添加粘性/热通量修正
  │
  ├── [C] 守恒量更新: hy_uhd_unsplitUpdate            (行485-491)
  │     └── 调用 updateConservedVariable (行966-974)
  │          应用: U^{n+1} = U^n - Σ dt/dx·(F_{i+½} - F_{i-½})
  │
  └── [D] EOS:  Eos_wrapped → 更新状态方程          (行500-507)
```

### 代码位置

```fortran
!! hy_uhd_unsplit.F90 行465-500

!! 对每个block:
call Timers_start("getFaceFlux")
call hy_uhd_getFaceFlux(blockID, blkLimits, blkLimitsGC, datasize, del,      &
                        xflux, yflux, zflux,                                &
                        scrchFaceXPtr, scrchFaceYPtr, scrchFaceZPtr,         &
                        scrch_Ptr, hy_SpcR, hy_SpcL, hy_SpcSig, lastCall)    ! 行467
call Timers_stop("getFaceFlux")
! ↑ 此时 xflux/yflux/zflux 已经包含各方向完全计算好的面通量
!   这些通量是求解黎曼问题得到的 Godunov 通量

!! 应用通量 → 更新守恒变量:
call hy_uhd_unsplitUpdate(blockID, updateMode, dt, del, datasize, blkLimits,&
                           blkLimitsGC, xflux, yflux, zflux,                &
                           gravX, gravY, gravZ, scrch_Ptr)                   ! 行485

!! 守恒量更新后:
call Eos_wrapped(MODE_DENS_EI, blklst(lb), blkLimitsGC)                     ! 行500
! ↑ 从更新后的 ρ 和 ρE 反解出 P, T
```

**关键点**：动量守恒和能量守恒的实现**横跨三个子程序**：
1. **`hy_uhd_prim2flx`**（通量函数）——定义通量 F = [ρv, ρvv+P, (E+P)v]^T 的数学表达式
2. **黎曼求解器**（如 `hy_uhd_HLLC`）——根据左右状态 VL, VR 选出正确的 Godunov 通量 F*
3. **`updateConservedVariable`**（更新函数）——对每个单元做 U^{n+1} = U^n - Σ(F_{i+½} - F_{i-½})·Δt/Δx

其中 **第 2 步** 是动量/能量守恒的**最重要**环节——它决定了界面处的动量通量和能量通量到底取多大，这是确保数值稳定性和激波捕捉能力的关键。

---

## 4. Step A：Riemann求解器——动量/能量通量的选值核心

### 文件位置
`source/physics/Hydro/HydroMain/unsplit/hy_uhd_HLLC.F90`（或 `hy_uhd_Roe.F90` 等）

FLASH 提供多个 Riemann 求解器选项：
| 求解器 | 文件 | 特点 |
|--------|------|------|
| **HLLC** | `hy_uhd_HLLC.F90` | **默认**，接触间断恢复好，纯流体首选 |
| Roe | `hy_uhd_Roe.F90` | 线性化近似，可能产生奇异模式 |
| HLL | `hy_uhd_HLL.F90` | 更耗散，无接触间断 |
| LLF (Local Lax-Friedrichs) | `hy_uhd_LLF.F90` | 最耗散，最鲁棒 |
| Marquina | `hy_uhd_Marquina.F90` | 特征分解型 |

下面以 **HLLC** 为例，详细解释它如何实现动量守恒和能量守恒。

### HLLC Riemann 扇区

```text
        SL      SM=qStar    SR
         \        |        /
          \       |       /
           \  UL* | UR*  /
            \     |     /
             \    |    /
              \   |   /
       UL      \  |  /       UR
                \ | /
                 \|/
  --------------------------------------
```

HLLC 求解器假设三个波：左波 SL、接触波 SM（=qStar）、右波 SR。它将黎曼问题的解分为四个区域：
- **UL**（原始左侧，SL 左侧）
- **UL\***（左星区，SL 与接触波之间）
- **UR\***（右星区，接触波与 SR 之间）
- **UR**（原始右侧，SR 右侧）

### HLLC 动量/能量通量源码解析

```fortran
!! hy_uhd_HLLC.F90 行53-325

Subroutine hy_uhd_HLLC(dir, Vm, Vp, Fstar, speed, ierr)
  ! Vm = 左侧原始变量 [ρ, vx, vy, vz, P, γ_c, γ_e, e]
  ! Vp = 右侧原始变量
  ! Fstar = 输出的 Godunov 通量

  !! ▓▓▓ 第1步: 计算左右波速 SL, SR ▓▓▓
  !! (依据 Davis 估算, JCP 1988)
  aL2 = γ_c*P_L/ρ_L                              ! 左声速² (行102)
  aR2 = γ_c*P_R/ρ_R                              ! 右声速² (行103)
  cfL = sqrt(aL2)                                 ! 纯流体: cf = 声速 (行131)
  cfR = sqrt(aR2)                                 ! (行132)
  SL = min(vnL - cfL, vnR - cfR)                 ! 左波速 (行142)
  SR = max(vnL + cfL, vnR + cfR)                 ! 右波速 (行143)
  speed = max(|SL|, |SR|)                         ! CFL 时间步约束 (行146)

  !! ▓▓▓ 第2步: 计算左右通量 ▓▓▓
  call hy_uhd_prim2con(Vm, UL)                   ! UL = [ρ, ρv, ρE] (行158)
  call hy_uhd_prim2con(Vp, UR)                   ! UR = [ρ, ρv, ρE] (行159)
  call hy_uhd_prim2flx(dir, Vm, FL)              ! FL = 左通量 (行160)
  call hy_uhd_prim2flx(dir, Vp, FR)              ! FR = 右通量 (行161)

  !! ▓▓▓ 第3步: 接触波速度 qStar ▓▓▓
  !! 这是HLLC的核心——找到中间接触波的速度
  qStar = ( ρ_R·vnR·(SR-vnR) - ρ_L·vnL·(SL-vnL)  &
            + P_total_L - P_total_R )             &  ! 行190-194
         / ( ρ_R·(SR-vnR) - ρ_L·(SL-vnL) )
  ! ↑ 这正是根据动量守恒推导出的接触波速度
  !   公式来源: Toro, Riemann Solvers, 1997

  !! ▓▓▓ 第4步: 星区总压力 pStar ▓▓▓
  pStar = ρ_L·(SL - vnL)·(qStar - vnL) + P_total_L   ! 行204
  ! ↑ 利用Rankine-Hugoniot条件通过左波SL计算星区压力

  !! ▓▓▓ 第5步: 计算星区密度和能量 ▓▓▓
  !! 左星区密度:
  dStarL = ρ_L·(SL - vnL) / (SL - qStar)               ! 行210
  !! 左星区总能量 (保守形式):
  UCstarL(HY_ENER) = (ρE)_L·(SL - vnL)/(SL - qStar)    &  ! 行215-216
                   + (pStar·qStar - P_total_L·vnL)/(SL - qStar)
  ! ↑ 这对应动量守恒方程 (14.1b) 和能量守恒方程 (14.1c) 
  !   在接触间断处的Rankine-Hugoniot跳跃条件

  !! ▓▓▓ 第6步: 计算星区各方向动量 ▓▓▓
  select case (dir)
  case (DIR_X)                                             ! 行236-251
     UCstarL(HY_XMOM) = dStarL · qStar                    ! 法线方向动量 (行237)
     UCstarL(HY_YMOM) = (ρvy)_L·(SL - vnL)/(SL - qStar)   ! 切向动量I (行238)
     UCstarL(HY_ZMOM) = (ρvz)_L·(SL - vnL)/(SL - qStar)   ! 切向动量II (行239)
     ! ↑ 法线动量传播间断，切线动量只做简单输运

     ! 右星区同理:
     UCstarR(HY_XMOM) = dStarR·qStar                      ! 行241
     UCstarR(HY_YMOM) = (ρvy)_R·(SR - vnR)/(SR - qStar)   ! 行242
     UCstarR(HY_ZMOM) = (ρvz)_R·(SR - vnR)/(SR - qStar)   ! 行243
  end select

  !! ▓▓▓ 第7步: 根据波速方向选择最终Godunov通量 ▓▓▓
  !! 这是动量/能量守恒的"判决"步骤
  if (SL >= 0.) then
     !! 左波向右运动 → 取左侧通量
     Fstar = FL                                              ! 行297

  elseif (SL < 0. .and. qStar >= 0.) then
     !! 取左星区通量 (左波向左, 接触波向右)
     Fstar(HY_DENS_FLUX:HY_ENER_FLUX) =                      &  ! 行300-301
          FL(HY_DENS_FLUX:HY_ENER_FLUX)                      &
          + SL·(UCstarL - UL)

  elseif (qStar < 0. .and. SR >= 0.) then
     !! 取右星区通量 (接触波向左, 右波向右)
     Fstar(HY_DENS_FLUX:HY_ENER_FLUX) =                      &  ! 行304-305
          FR(HY_DENS_FLUX:HY_ENER_FLUX)                      &
          + SR·(UCstarR - UR)

  else
     !! 右波向左运动 → 取右侧通量
     Fstar = FR                                              ! 行310
  endif

End Subroutine hy_uhd_HLLC
```

### 与动量方程(14.1b)的对应

| 方程(14.1b)项 | HLLC中的实现位置 | 说明 |
|---------------|-----------------|------|
| 左/右通量 ρvv+P | `FL(HY_XMOM_FLUX)` = ρ_L·vx_L²+P_L | 由 `prim2flx` 在行160-161计算 |
| 界面法向动量通量 F*_{x} | 行237: `UCstarL(HY_XMOM) = dStarL·qStar` | 法线动量通过接触波传播 |
| 界面切向动量通量 F*_{y} | 行238: 切线动量简单输运 | 切向速度无间断 |
| **最终选通量** | 行296-312: SL/qStar/SR 方向判断 | 决定界面处究竟是左、右还是星区通量 |

### 与能量方程(14.1c)的对应

| 方程(14.1c)项 | HLLC中的实现位置 | 说明 |
|---------------|-----------------|------|
| 左/右能通量 (E+P)v | `FL(HY_ENER_FLUX)` = (E_L+P_L)·vx_L | 由 `prim2flx` 计算 |
| 星区总能量 | 行215-220: `UCstarL(HY_ENER) = ...` | 包含 Rankine-Hugoniot 跳跃 |
| HLLC总压力 | 行204: `pStar = ρ·(SL-vn)·(qStar-vn)+P` | 由动量跳跃条件反推 |

### 动量/能量守恒的关键保障机制

```text
         Cell_i             界面             Cell_{i+1}
    ┌──────────────┬──────────┼──────────┬──────────────┐
    │  ρ_i^(n)     │  F_{i+½}  │          │  ρ_{i+1}^(n) │
    │ (ρv)_i^(n)   │  = F*     │          │ (ρv)_{i+1}^(n)│
    │ (ρE)_i^(n)   │           │          │ (ρE)_{i+1}^(n)│
    └──────────────┴──────────┴──────────┴──────────────┘
                       ↑
                 通量 F_{i+½} 来自 HLLC 求解器
                 它对 Cell_i 是 FR, 对 Cell_{i+1} 是 FL
                 同一值 → 通量配平 → 全局守恒保障
```

HLLC 求解器保证：
1. **同一界面只有一个通量**：F_{i+½} 对 Cell_i 是"右通量"、对 Cell_{i+1} 是"左通量"——完全相同
2. **三种波速覆盖所有信息传播情况**：亚音速/超音速/激波/稀疏波
3. **星区状态满足 Rankine-Hugoniot**：保证了激波处的守恒律

---

## 5. 变量索引体系（UHD.h）

纯流体模式（`FLASH_UHD_HYDRO`）下的关键索引定义：

### 原始变量（Primitive Variables）
```fortran
#define HY_DENS 1    ! 密度 ρ
#define HY_VELX 2    ! x方向速度 vx
#define HY_VELY 3    ! y方向速度 vy
#define HY_VELZ 4    ! z方向速度 vz
#define HY_PRES 5    ! 压力 P
#define HY_GAMC 6    ! 绝热指数 γ_c
#define HY_GAME 7    ! 绝热指数 γ_e
#define HY_EINT 8    ! 比内能 e
```

### 通量变量（Flux Variables）
```fortran
#define HY_DENS_FLUX 1   ! 质量通量 F01
#define HY_XMOM_FLUX 2   ! x动量通量 F02
#define HY_YMOM_FLUX 3   ! y动量通量 F03
#define HY_ZMOM_FLUX 4   ! z动量通量 F04
#define HY_ENER_FLUX 5   ! 总能通量 F05
#define HY_P_FLUX    6   ! 压力通量 (P, 用于几何源项)
#define HY_EINT_FLUX 7   ! 内能通量 (辅助方程)
#define HY_VOLU_FLUX 8   ! 体积通量 (用于3T)
```

### 守恒变量内部索引（Local buffer `U0`）
```fortran
#define HY_DENS 1
#define HY_XMOM 2   ! HY_VELX → 实际连续存放: 守恒数组起始位置
#define HY_YMOM 3
#define HY_ZMOM 4
#define HY_ENER 5
```

### 通量数组索引映射到U0守恒变量
```
U0(HY_DENS) = ρ                         → 通量编号 HY_DENS_FLUX = 1
U0(HY_XMOM) = ρ·vx                      → 通量编号 HY_XMOM_FLUX = 2
U0(HY_YMOM) = ρ·vy                      → 通量编号 HY_YMOM_FLUX = 3
U0(HY_ZMOM) = ρ·vz                      → 通量编号 HY_ZMOM_FLUX = 4
U0(HY_ENER) = ρ·E = ρ·e + ½ρ·|v|²     → 通量编号 HY_ENER_FLUX = 5
```

---

## 6. Step 1：原始变量 → 守恒变量（调用前准备）

在调用 `updateConservedVariable` 之前，主程序将 UNK 中的**原始变量**打包成**守恒形式**存入局部数组 `U0`：

```fortran
!! hy_uhd_unsplitUpdate.F90 行882-884

!! Prepare to update conserved quantities
U0(HY_XMOM:HY_ZMOM) = U(VELX_VAR:VELZ_VAR,i,j,k) * U(DENS_VAR,i,j,k)   ! 动量: ρ·v
U0(HY_ENER) = U(DENS_VAR,i,j,k) * U(ENER_VAR,i,j,k)                    ! 总能: ρ·E
```

**对应方程 (14.1) 的守恒变量展开：**

| 索引 | 表达式 | 对应方程变量 |
|------|--------|-------------|
| `U0(HY_DENS)` | ρ | (14.1a) 中的 ρ |
| `U0(HY_XMOM)` | ρ·v_x | (14.1b) 中的 ρv_x |
| `U0(HY_YMOM)` | ρ·v_y | (14.1b) 中的 ρv_y |
| `U0(HY_ZMOM)` | ρ·v_z | (14.1b) 中的 ρv_z |
| `U0(HY_ENER)` | ρ·E = ρ·e + ½ρ·(v_x²+v_y²+v_z²) | (14.1c) 中的 ρE |

注意 `U0(HY_DENS)` 并未在行882-884显式赋值，因为密度已直接从UNK读取——局部数组的 `HY_DENS` 分量实际在行679就已经保存了。

---

## 7. Step 2：通量向量（hy_uhd_prim2flx）

`hy_uhd_prim2flx` 将**原始变量**转换为**面通量向量**。这是方程(14.1)中**散度项**的离散基础。

### X方向通量（dir==DIR_X）

```fortran
!! hy_uhd_prim2flx.F90 行66-83

!! 总能量 E_total（行53-54）:
E = 0.5*ρ·(vx²+vy²+vz²) + P/(γ-1)

!! 无磁场分支 #ifdef FLASH_UHD_HYDRO（行68-72）:
F(HY_DENS_FLUX) = ρ·vx                          ! → ∂(ρ)/∂t + ∂(ρvx)/∂x = 0
F(HY_XMOM_FLUX) = (ρ·vx)·vx + P                 ! → ∂(ρvx)/∂t + ∂(ρvx²+P)/∂x = 0
F(HY_YMOM_FLUX) = (ρ·vx)·vy                     ! → ∂(ρvy)/∂t + ∂(ρvx·vy)/∂x = 0
F(HY_ZMOM_FLUX) = (ρ·vx)·vz                     ! → ∂(ρvz)/∂t + ∂(ρvx·vz)/∂x = 0
F(HY_ENER_FLUX) = (E + P)·vx                    ! → ∂(ρE)/∂t + ∂((ρE+P)vx)/∂x = 0
```

### Y方向通量（dir==DIR_Y）

```fortran
!! hy_uhd_prim2flx.F90 行86-102
F(HY_DENS_FLUX) = ρ·vy                          ! 质量通量 (Y)
F(HY_XMOM_FLUX) = (ρ·vy)·vx                     ! x动量通量 (Y)
F(HY_YMOM_FLUX) = (ρ·vy)·vy + P                 ! y动量通量 (Y): ∂(ρvy)/∂t + ∂(ρvy²+P)/∂y = 0
F(HY_ZMOM_FLUX) = (ρ·vy)·vz                     ! z动量通量 (Y)
F(HY_ENER_FLUX) = (E + P)·vy                    ! 能量通量 (Y)
```

### Z方向通量（dir==DIR_Z）

```fortran
!! hy_uhd_prim2flx.F90 行104-121
F(HY_DENS_FLUX) = ρ·vz                          ! 质量通量 (Z)
F(HY_XMOM_FLUX) = (ρ·vz)·vx                     ! x动量通量 (Z)
F(HY_YMOM_FLUX) = (ρ·vz)·vy                     ! y动量通量 (Z)
F(HY_ZMOM_FLUX) = (ρ·vz)·vz + P                 ! z动量通量 (Z): ∂(ρvz)/∂t + ∂(ρvz²+P)/∂z = 0
F(HY_ENER_FLUX) = (E + P)·vz                    ! 能量通量 (Z)
```

### 与方程 (14.1) 的对应关系

通量向量 F、G、H 分别对应散度项中的三个方向：

```text
∇·[F] = ∂F_x/∂x + ∂G_y/∂y + ∂H_z/∂z

对于质量守恒 (14.1a):
  F_x = ρvx,  G_y = ρvy,  H_z = ρvz
  → ∇·(ρv) = ∂(ρvx)/∂x + ∂(ρvy)/∂y + ∂(ρvz)/∂z

对于 x-动量守恒 (14.1b):
  F_x = ρvx²+P,  G_y = ρvx·vy,  H_z = ρvx·vz
  → ∇·(ρvv + P·I) 的第一行分量
  
对于总能量守恒 (14.1c):
  F_x = (E+P)vx,  G_y = (E+P)vy,  H_z = (E+P)vz
  → ∇·[(E+P)v]
```

---

## 8. Step 3：守恒更新核心（updateConservedVariable）

这是**最核心的代码**——直接实现有限体积离散方程：

```fortran
!! hy_uhd_unsplitUpdate.F90 行1364-1419

Subroutine updateConservedVariable(Ul,FL,FR,GL,GR,HL,HR,  &
                                     gravX, gravY, gravZ,&
                                     dx,dy,dz,dt,Sgeo,Sphys)

  !! 保存 n 时刻的状态
  densOld = Ul(HY_DENS)                    ! 行1378: ρ^n
  momentaOld(1:3) = Ul(HY_XMOM:HY_ZMOM)    ! 行1379: (ρv)^n

  !! ▓▓▓ X方向更新 ▓▓▓
  !! Ul^{n+1} = Ul^n - dt/dx * (FR - FL)
  !! 对应: ∂U/∂t + ∂F/∂x = 0 的离散形式
  Ul(HY_DENS:HY_DENS+HY_VARINUM-1) = &
       Ul(HY_DENS:HY_DENS+HY_VARINUM-1) &
       - dt/dx * ( FR(HY_DENS_FLUX:HY_DENS_FLUX+HY_VARINUM-1) &        ! 行1382-1384
                  -FL(HY_DENS_FLUX:HY_DENS_FLUX+HY_VARINUM-1))

  !! ▓▓▓ Y方向更新 (仅 NDIM>1) ▓▓▓
  if (NDIM > 1) then
     Ul = Ul - dt/dy * (GR - GL)                                       ! 行1387-1389
  endif

  !! ▓▓▓ Z方向更新 (仅 NDIM>2) ▓▓▓
  if (NDIM > 2) then
     Ul = Ul - dt/dz * (HR - HL)                                       ! 行1392-1394
  endif

  !! ▓▓▓ 源项加入 ▓▓▓
  Ul = Ul + dt * (Sgeo + Sphys)                                        ! 行1401

  !! ▓▓▓ 重力源项 ▓▓▓
  if (hy_useGravity) then
     !! 动量源: (ρv)^{n+1} += 0.5·dt·ρ^n·g
     Ul(HY_XMOM:HY_ZMOM) = Ul(HY_XMOM:HY_ZMOM) &
          + 0.5*dt*densOld*(/gravX,gravY,gravZ/)                      ! 行1410-1411
     
     !! 能量源: (ρE)^{n+1} += 0.5·dt·(ρv)^n·g
     Ul(HY_ENER) = Ul(HY_ENER) &
          + 0.5*dt*dot_product(momentaOld(1:3),(/gravX,gravY,gravZ/)) ! 行1413-1414
  endif

End Subroutine updateConservedVariable
```

### 逐项对照 (14.1a-c)

以一维情况为例展开：

**质量守恒 (14.1a)** — 仅 `Ul(HY_DENS)` 分量参与：

```text
ρ^{n+1} = ρ^n - Δt/Δx · [ (ρvx)_{i+½} - (ρvx)_{i-½} ]
```

这正是离散化的:
$$\rho^{n+1}_i = \rho^n_i - \frac{\Delta t}{\Delta x}\left(F^{\rho}_{i+1/2} - F^{\rho}_{i-1/2}\right)$$

对应 (14.1a): $\partial_t\rho + \partial_x(\rho v_x) = 0$

**x-动量守恒 (14.1b)** — `Ul(HY_XMOM)` 分量:

```text
(ρvx)^{n+1} = (ρvx)^n 
              - Δt/Δx · [ (ρvx²+P)_{i+½} - (ρvx²+P)_{i-½} ]
```

对应 (14.1b): $\partial_t(\rho v_x) + \partial_x(\rho v_x^2 + P) = 0$

**总能量守恒 (14.1c)** — `Ul(HY_ENER)` 分量:

```text
(ρE)^{n+1} = (ρE)^n 
             - Δt/Δx · [ ((ρE+P)vx)_{i+½} - ((ρE+P)vx)_{i-½} ]
```

对应 (14.1c): $\partial_t(\rho E) + \partial_x[(\rho E + P)v_x] = 0$

---

## 9. Step 4：几何源项（非笛卡尔坐标系）

在柱坐标/极坐标/球坐标系下，动量方程出现额外的几何源项 $S_\text{geo}$。计算位置在 `hy_uhd_unsplitUpdate.F90` 行894-963：

```fortran
!! 柱坐标 (CYLINDRICAL):
Sgeo(HY_XMOM) = (ρ·vφ² + fP·α·P̄) / r          ! r方向离心力 (行910)
Sgeo(MOM_PHI) = -(ρ·vφ·vr) / r                 ! φ方向科里奥利力 (行911)

!! 球坐标 (SPHERICAL):
Sgeo(HY_XMOM) += (ρ·vθ²) / r                   ! θ方向分量 (行955)
Sgeo(MOM_THT) = (ρ·vφ²·cotθ - ρ·vr·vθ) / r    ! θ方向力矩 (行958-959)
```

这些几何源项是**动量守恒方程 (14.1b)** 在非笛卡尔坐标系下的曲率修正项。

---

## 10. Step 5：物理源项（压力做功、重力、欧姆加热等）

除了重力（在 `updateConservedVariable` 内部处理），还有多个物理源项通过 `Sphys` 传入：

### 8.1 压力做功修正项 `Sphys`

```fortran
!! hy_uhd_unsplitUpdate.F90 行565-667

!! X方向压力梯度源项 (fP 控制是纯流体还是MHD):
Sphys(HY_XMOM) = (FL(HY_P_FLUX) - FR(HY_P_FLUX)) * (1.0-fP) / dx
  ! ↑ 这是对通量中压力处理的修正 (fP≈0 时表示压力项完全通过通量处理)

!! Y方向 (行666):
Sphys(HY_YMOM) = (GL(HY_P_FLUX) - GR(HY_P_FLUX)) * (1.0-fP) / dy

!! Z方向 (行667):
Sphys(HY_ZMOM) = (HL(HY_P_FLUX) - HR(HY_P_FLUX)) * (1.0-fP) / dz
```

### 8.2 欧姆加热 `Qohm`

```fortran
!! hy_uhd_unsplitUpdate.F90 行703-712
!! MHD电阻耗散产生的热量 (激活磁阻率时):
Qohm = scrch_Ptr(HY_XN02_SCRATCHCTR_VAR,i,j,k)   ! 1T情况
Qohm = scrch_Ptr(HY_XN07_SCRATCHCTR_VAR,i,j,k)   ! 3T情况
```

### 8.3 粘性加热 `Qvisc`

```fortran
!! hy_uhd_unsplitUpdate.F90 行716-729
if (hy_useViscosity) then
   call calcQvisc(dt, del, U, xflux, yflux, zflux, Qvisc)
endif
```

### 8.4 总加热源项

```fortran
!! 行737
Qtot = Qohm + Qvisc   ! 总加热量, 传入内能辅助方程更新
```

这些源项对应方程 (14.1c) 右侧的 `Q_las - ∇·q` 中的额外加热贡献——注意激光加热 (Q_las) 和热传导 (-∇·q) 在之后的算子分裂步骤中处理，不在 Hydro 单元处理。

---

## 11. 完整数据流总图

### 从物理方程到 Fortran 代码的全链路

```
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ 连续方程 (14.1a-c)                                                       │
    │ ∂ρ/∂t + ∇·(ρv) = 0                                                      │
    │ ∂(ρv)/∂t + ∇·(ρvv+P) = 0                                                │
    │ ∂(ρE)/∂t + ∇·[(ρE+P)v] = 0                                              │
    └─────────────────────┬───────────────────────────────────────────────────┘
                          │ 有限体积离散
                          ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ 离散守恒律: U^{n+1} = U^n - Σ dt/dx·(F_{i+½} - F_{i-½})                 │
    └─────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ hy_uhd_unsplit.F90 (主驱动, 行64-500+)
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ [A] hy_uhd_getFaceFlux (行467)                                    │    │
│ │      │                                                              │    │
│ │      ├── hy_uhd_getRiemannState (PPM/WENO 重构)                     │    │
│ │      │   → 获得每个面的左/右原始变量: VL, VR                        │    │
│ │      │                                                              │    │
│ │      ├── hy_uhd_HLLC(dir, VL, VR, Fstar, speed, ierr)  (行425)     │    │
│ │      │   │                                                           │    │
│ │      │   ├── hy_uhd_prim2con(VL) → UL   (行158)                     │    │
│ │      │   ├── hy_uhd_prim2con(VR) → UR   (行159)                     │    │
│ │      │   ├── hy_uhd_prim2flx(dir, VL) → FL (行160):                 │    │
│ │      │   │     FL(HY_DENS_FLUX) = ρ_L·v_L                           │    │
│ │      │   │     FL(HY_XMOM_FLUX) = ρ_L·v_L² + P_L  (动量通量)       │    │
│ │      │   │     FL(HY_ENER_FLUX) = (E_L+P_L)·v_L   (能量通量)        │    │
│ │      │   ├── hy_uhd_prim2flx(dir, VR) → FR (行161):                 │    │
│ │      │   │     FR(HY_DENS_FLUX) = ρ_R·v_R                           │    │
│ │      │   │     FR(HY_XMOM_FLUX) = ρ_R·v_R² + P_R                   │    │
│ │      │   │     FR(HY_ENER_FLUX) = (E_R+P_R)·v_R                    │    │
│ │      │   │                                                           │    │
│ │      │   ├── 计算波速 SL, SR (行142-143)                             │    │
│ │      │   ├── 计算接触波速度 qStar (行190-194) ——— 动量守恒约束      │    │
│ │      │   ├── 计算星区压力 pStar (行204) ——— Rankine-Hugoniot         │    │
│ │      │   ├── 计算星区状态 UCstarL, UCstarR (行210-287):             │    │
│ │      │   │     • 密度   dStarL = ρ_L·(SL-vnL)/(SL-qStar)            │    │
│ │      │   │     • 动量   pStar, 法线: dStar·qStar, 切线:输运         │    │
│ │      │   │     • 能量   (ρE)_L·(SL-vnL)/(SL-qStar) + ...            │    │
│ │      │   │                                                           │    │
│ │      │   └── 选择最终 Godunov 通量 Fstar (行296-312):                │    │
│ │      │        SL≥0  → Fstar=FL (完全超音速)                          │    │
│ │      │        SL<0≤qStar → Fstar = FL+SL·(UCstarL-UL)               │    │
│ │      │        qStar<0≤SR → Fstar = FR+SR·(UCstarR-UR)               │    │
│ │      │        SR<0 → Fstar=FR                                        │    │
│ │      │                                                               │    │
│ │      └── 输出: xflux, yflux, zflux (各方向面通量)                     │    │
│ │                                                                       │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                           │                                                 │
│                           ▼                                                 │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ [B] hy_uhd_unsplitUpdate (行485)                                  │    │
│ │      │                                                              │    │
│ │      ├── 加载面通量 (行546-551):                                     │    │
│ │      │     FL = xflux(i  ,j,k),  FR = xflux(i+1,j,k)               │    │
│ │      │     GL = yflux(i,j  ,k),  GR = yflux(i,j+1,k)                │    │
│ │      │     HL = zflux(i,j,k  ),  HR = zflux(i,j,k+1)                │    │
│ │      │                                                               │    │
│ │      ├── 准备守恒变量 (行882-884):                                   │    │
│ │      │     U0(HY_DENS) = ρ                                          │    │
│ │      │     U0(HY_XMOM:HY_ZMOM) = (ρv)^n                             │    │
│ │      │     U0(HY_ENER) = (ρE)^n                                     │    │
│ │      │                                                               │    │
│ │      └── call updateConservedVariable (行966-974):                    │    │
│ │             │                                                         │    │
│ │             ├── X方向: U0 -= dt/dx·(FR-FL)  (行1382-1384)            │    │
│ │             │   ↑ 质量守恒: ρ^{n+1}=ρ^n - dt/dx·((ρv)flux diff)     │    │
│ │             │   ↑ 动量守恒: (ρv)^{n+1} = (ρv)^n                      │    │
│ │             │                - dt/dx·((ρvv+P)flux diff)              │    │
│ │             │   ↑ 能量守恒: (ρE)^{n+1} = (ρE)^n                      │    │
│ │             │                - dt/dx·(((ρE+P)v)flux diff)            │    │
│ │             │                                                         │    │
│ │             ├── Y方向: U0 -= dt/dy·(GR-GL)  (行1387-1389)            │    │
│ │             ├── Z方向: U0 -= dt/dz·(HR-HL)  (行1392-1394)            │    │
│ │             │                                                         │    │
│ │             ├── 源项: U0 += dt·(Sgeo+Sphys)  (行1401)                │    │
│ │             │                                                         │    │
│ │             └── 重力: 动量 += ½·dt·ρ^n·g  (行1410-1411)               │    │
│ │                       能量 += ½·dt·(ρv)^n·g  (行1413-1414)           │    │
│ │                                                                       │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                           │                                                 │
│                           ▼                                                 │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ [C] 后处理 (行984-997):                                             │    │
│ │   U(DENS_VAR) = max(U0(HY_DENS), smalldens)    ↓ 密度               │    │
│ │   U(ENER_VAR) = U0(HY_ENER)                     ↓ 总能              │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                           │                                                 │
│                           ▼                                                 │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ [D] Eos_wrapped (行500): 从 ρ, ρE → P, T                            │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 方程与代码行号对应表

| 物理方程 | 守恒变量 | 通量数组 | 通量公式 | 源码位置 |
|----------|---------|---------|----------|---------|
| (14.1a): ∂ρ/∂t + ∇·(ρv)=0 | `U0(HY_DENS)` | `HY_DENS_FLUX` | ρ·v | `prim2flx.F90:67,86,105` |
| (14.1b): ∂(ρv_x)/∂t + ∇·(ρv_x v+P)=0 | `U0(HY_XMOM)` | `HY_XMOM_FLUX` | ρ·v_x·v + P | `prim2flx.F90:69,88,107` |
| (14.1b): ∂(ρv_y)/∂t + ... | `U0(HY_YMOM)` | `HY_YMOM_FLUX` | ρ·v_y·v + P | `prim2flx.F90:70,89,108` |
| (14.1b): ∂(ρv_z)/∂t + ... | `U0(HY_ZMOM)` | `HY_ZMOM_FLUX` | ρ·v_z·v + P | `prim2flx.F90:71,90,109` |
| (14.1c): ∂(ρE)/∂t + ∇·[(ρE+P)v]=0 | `U0(HY_ENER)` | `HY_ENER_FLUX` | (ρE+P)·v | `prim2flx.F90:72,91,110` |
| **Godunov通量选值（Riemann求解）** | 全部 | 全部 | HLLC公式: 见下文 | `hy_uhd_HLLC.F90:296-312` |
| 接触波速度（动量守恒约束） | qStar | — | (ρ_R·vn_R·(SR-vn_R)-...)/(...) | `hy_uhd_HLLC.F90:190-194` |
| 星区总压力（Rankine-Hugoniot） | pStar | — | ρ_L·(SL-vn_L)·(qStar-vn_L)+P_L | `hy_uhd_HLLC.F90:204` |
| 星区动量（法线方向） | UCstar(HY_XMOM) | — | dStar·qStar | `hy_uhd_HLLC.F90:237` |
| 星区总能量 | UCstar(HY_ENER) | — | UL(ENER)·(SL-vn_L)/(SL-qStar)+... | `hy_uhd_HLLC.F90:215-216` |
| 有限体积更新 | 全部 | 全部 | -dt/dx·(FR-FL), -dt/dy·(GR-GL), -dt/dz·(HR-HL) | `unsplitUpdate.F90:1382-1394` |
| 几何源项 | 动量 | — | 曲率修正 | `unsplitUpdate.F90:894-963` |
| 重力源项 | 动量+能量 | — | 0.5·dt·ρ^n·g | `unsplitUpdate.F90:1410-1414` |

### 关键点总结

1. **通量是方程的离散化桥梁**：`hy_uhd_prim2flx` 将连续方程(14.1)中的散度项 `∇·(F)` 在三个空间方向上离散为面通量 `(FR-FL)/dx, (GR-GL)/dy, (HR-HL)/dz`

2. **动量守恒的核心在 Riemann 求解器**：界面处的动量通量不是简单的左右平均或算术平均，而是通过求解黎曼问题得到的 Godunov 通量。HLLC 通过 SL/SR/qStar 三个波速覆盖了从亚音速到超音速、从稀疏波到激波的所有流动状态，确保动量在不同波系中的正确传播。

3. **能量守恒的 Rankine-Hugoniot 保障**：HLLC 星区能量公式（行215-216）来源于 Rankine-Hugoniot 跳跃条件，保证激波前后能量守恒律精确满足。总压力 pStar 由动量跳跃条件（行204）约束，与能量跳跃自洽。

4. **保守性保证**：通量 `FL`, `FR` 来自相邻单元共享的同一界面——Cell_i 的 FR 就是 Cell_{i+1} 的 FL，因此 $\sum \rho_i$（以及 $\sum \rho v_i$、$\sum \rho E_i$）严格守恒。

5. **算子分裂**：Hydro 单元只处理守恒律的绝热输运部分（无源项的 14.1）。Q_las（激光沉积）、-∇·q（电子热传导）、辐射吸收/发射在后续的 EnergyDeposition/Diffuse/RadTrans 单元中分别处理

6. **3T 扩展**：在 3T 模式下（`FLASH_UHD_3T`），除了 1T 的 5 个守恒变量外，还额外输运 `e_ele, e_ion, e_rad` 3个内能分量，以及 Volu 通量，用于多温度耦合
