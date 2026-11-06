---
title: Hydro 内部实现 — 公共 API + hy_uhd_* 调用图 + CTU 流程 + flux correction
skill: flash-hydro
category: internals
source_anchors:
  - source/physics/Hydro/Hydro_interface.F90:L1-L161
  - source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90:L64-L1059
  - source/physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90:L412-L462
  - source/physics/Hydro/HydroMain/unsplit/hy_uhd_TVDslope.F90:L89
  - source/physics/Hydro/HydroMain/hy_slopeLimiters.F90:L39-L84
manual_ref: "FLASH 4.8 User Guide §9-12"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - hydro
  - internals
  - api
  - ctu
  - flux-correction
---

# Hydro 内部实现

> **TL;DR**：Hydro 公共 API 只 12 个函数（外部表面小），内部 `hy_uhd_*` 约 50 个（复杂度高）。本文件讲：① 公共 API 分类；② unsplit CTU 流程（10 步）；③ Riemann solver 调度机制；④ AMR flux correction 双循环；⑤ MHD CT 实现；⑥ guard cell 填充策略。

---

## 1. 公共 API 总览

源码：`source/physics/Hydro/Hydro_interface.F90`（161 行，含 12 个 interface 块）

### 1.1 API 分类

| 类别 | 函数 | 数量 |
|---|---|---|
| **生命周期** | `Hydro_init`、`Hydro_finalize`、`Hydro`（主入口） | 3 |
| **时间步** | `Hydro_computeDt`、`Hydro_consolidateCFL` | 2 |
| **激波** | `Hydro_detectShock`、`Hydro_shockStrength` | 2 |
| **辅助** | `Hydro_recalibrateEints`、`Hydro_recalibrateEintsForCell` | 2 |
| **其他** | `Hydro_mapBcType`、`Hydro_gravPotIsAlreadyUpdated`、`Hydro_sendOutputData` | 3 |

### 1.2 关键 API 详解

#### `Hydro`（主入口）

```fortran
subroutine Hydro(blockCount, blockList, timeEndAdv, dt, dtOld, sweepOrder)
```

- stub: `source/physics/Hydro/Hydro.F90:L49-L60`
- unsplit 实现: `source/physics/Hydro/HydroMain/unsplit/Hydro.F90:L44-L72`
- split 实现: `source/physics/Hydro/HydroMain/split/PPM/Hydro.F90`

Driver 每步调一次。`sweepOrder` 在 split 是 `SWEEP_XYZ` 或 `SWEEP_ZYX`，在 unsplit 是 dummy。

#### `Hydro_init`

```fortran
subroutine Hydro_init()
```

- stub: `source/physics/Hydro/Hydro_init.F90:L81-L85`（空）
- unsplit 实现: `source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L24-L927`（**927 行**，最重要）

读所有 runtime parameter（`RuntimeParameters_get`），分配 scratch 数组，把字符串参数（RiemannSolver / slopeLimiter / eosModeGc）映射到整数常量（`hy_RiemannSolver` / `hy_limiter`）。

#### `Hydro_computeDt`

```fortran
subroutine Hydro_computeDt(blockID, x,dx,uxgrid, y,dy,uygrid, z,dz,uzgrid, &
                            blkLimits, blkLimitsGC, solnData, &
                            dtCheck, dtMinLoc, extraInfo)
```

每 block 算一个 CFL 限制 `dtCheck`，并记录最小位置 `dtMinLoc(5)=(i,j,k,blockID,meshMe)`。Driver 把所有 block 的 dtCheck 取最小，得全局 dt。

源码：`source/physics/Hydro/HydroMain/unsplit/Hydro_computeDt.F90`

---

## 2. 内部 hy_uhd_* 函数

源码：`source/physics/Hydro/HydroMain/unsplit/hy_uhd_interface.F90`（~50 个 interface）

`hy_uhd` = "Hydro Unsplit HydroDynamics"。

### 2.1 主流程类

| 函数 | 文件 | 用途 |
|---|---|---|
| `hy_uhd_unsplit` | `Hydro_Unsplit/hy_uhd_unsplit.F90:L64`（pure hydro）/ `MHD_StaggeredMesh/hy_uhd_unsplit.F90`（MHD） | **主工作流**。10 步：fillGuardCells → shockDetect → dataReconst → getFaceFlux → CTU update → fluxCorrect → conservativeUpdate → energyFix → MHD CT → EOS |
| `hy_uhd_getRiemannState` | `hy_uhd_getRiemannState.F90` | 计算每个面的 left/right Riemann state |
| `hy_uhd_getFaceFlux` | `hy_uhd_getFaceFlux.F90` | **Riemann solver 调度**——按 hy_RiemannSolver 调具体 solver |
| `hy_uhd_unsplitUpdate` | `hy_uhd_unsplitUpdate.F90` | 保守更新 U^{n+1} = U^n - dt/dV * Σ(F*A) |
| `hy_uhd_energyFix` | `hy_uhd_energyFix.F90` | 能量修正（避免 KE ≫ IE 时消去误差） |

### 2.2 状态转换

| 函数 | 用途 |
|---|---|
| `hy_uhd_prim2con` | primitive → conservative |
| `hy_uhd_con2prim` | conservative → primitive |
| `hy_uhd_prim2flx` | 从 primitive state 算物理通量 |
| `hy_uhd_unitConvert` | code units ↔ physical units |

### 2.3 重构 / limiter

| 函数 | 用途 |
|---|---|
| `hy_uhd_TVDslope` | TVD slope 调度（按 hy_limiter 选 minmod/vanLeer/MC/...） |
| `hy_uhd_TVDslopeUpwind` | PPM upwind TVD slopes |
| `hy_uhd_dataReconstOneStep` | 一步数据重构（含 order、limiter、返回 sig/lambda/eigenvectors） |
| `hy_uhd_DataReconstructNormalDir_MH/PCM/PPM/WENO/GP` | 按 order 选不同重构方法（MH=MUSCL-Hancock order=2，PCM=order=1，PPM=order=3，WENO=order=5，GP=order=6） |

### 2.4 Riemann solver（8 种 + Zero）

| 函数 | 文件 |
|---|---|
| `hy_uhd_HLL` | `hy_uhd_HLL.F90` |
| `hy_uhd_HLLC` | `hy_uhd_HLLC.F90` |
| `hy_uhd_HLLD` | `MHD_StaggeredMesh/hy_uhd_HLLD.F90`（MHD only） |
| `hy_uhd_Roe` | `hy_uhd_Roe.F90` |
| `hy_uhd_LLF` | `hy_uhd_LLF.F90` |
| `hy_uhd_Marquina` / `hy_uhd_MarquinaModified` | 同名文件 |
| `hy_uhd_ZERO` | `hy_uhd_ZERO.F90` |

**全部共享签名**：`(dir, Vm, Vp, Fstar, speed, ierr)`

### 2.5 特征结构（Roe/Marquina 用）

| 函数 | 用途 |
|---|---|
| `hy_uhd_eigenParameters` | 算 C_fast、C_alfn、C_slow、A_f、A_s、B_beta |
| `hy_uhd_eigenValue` | 特征值 |
| `hy_uhd_eigenVector` | 左/右特征向量 |
| `hy_uhd_entropyFix` | Harten/HartenHyman entropy fix（Roe 用） |
| `hy_uhd_checkRHJumpCond` | Rankine-Hugoniot 跳跃检查（hybridOrder 用） |

### 2.6 MHD 专属

| 函数 | 用途 |
|---|---|
| `hy_uhd_staggeredDivb` | CT 清理 ∇·B（curl 形式更新 face B） |
| `hy_uhd_getElectricFields` | 从通量算 edge 电场 E = -(v × B) |
| `hy_uhd_getFaceCurrents` | J = curl(B) at faces |
| `hy_uhd_addHallFluxes` | Hall 项 |
| `hy_uhd_addBiermannFluxes` | Biermann battery |
| `hy_uhd_addNernstFluxes` | Nernst 项 |
| `hy_uhd_addCrossFieldFluxes` | 跨场热扩散 |
| `hy_uhd_addResistiveFluxes` | 电阻率 |

---

## 3. unsplit CTU 完整流程（10 步）

源码：`source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90`（~1059 行）

### 3.1 流程图（文字 + 缩进）

```
Hydro(blockCount, blockList, dt, ...)
│
├── 对每个 blockID in blockList:
│   └── hy_uhd_unsplit(blockID, dt, ...)
│       │
│       ├── Step 1: 填 guard cell（行 227, 294）
│       │   ├── Grid_fillGuardCells(CENTER, ALLDIR, doEos=.false., mask=gcMask)  # 激波探测前
│       │   └── Grid_fillGuardCells(CENTER, ALLDIR, doEos=.true., eosMode=hy_eosModeGc,
│       │                            mask=hy_gcMask)                                # 主前
│       │   └── MHD: Grid_fillGuardCells(CENTER_FACES, ALLDIR, ...) (行 323, 630)
│       │
│       ├── Step 2: 激波探测（可选，行 ~340）
│       │   └── hy_uhd_shockDetect(solnData, shock, blkLimits, blkLimitsGC, ...)
│       │       └── 算 divV, |∇P|；flag SHOK_VAR if (minP * divV < -0.5 .and. |gradP|/(minP*c_s) > 0.1)
│       │
│       ├── Step 3: 数据重构（计算 left/right state）
│       │   ├── hy_uhd_dataReconstOneStep 或 hy_uhd_DataReconstructNormalDir_{MH/PCM/PPM/WENO/GP}
│       │   │   └── 按 order 选方法
│       │   ├── hy_uhd_TVDslope → 按 hy_limiter 选限幅器
│       │   │   ├── MINMOD / MC / VANLEER / VANLEER15 / HYBRID / LIMITED
│       │   │   └── charLimiting=TRUE 时投影到特征空间限制
│       │   └── 返回 Wp, Wn, sig, lambda, leftEig, rghtEig
│       │
│       ├── Step 4: Riemann solver（每面算通量，行 412-462 X，853-906 Y，1251-... Z）
│       │   └── hy_uhd_getFaceFlux
│       │       ├── if hy_RiemannSolver == HLLC → call hy_uhd_HLLC(DIR_X, VL, VR, xflux, speed, ierr)
│       │       ├── if hy_RiemannSolver == HLL  → call hy_uhd_HLL(...)
│       │       ├── if hy_RiemannSolver == HLLD → call hy_uhd_HLLD(...) ★ MHD only
│       │       ├── if hy_RiemannSolver == Roe  → call hy_uhd_Roe(...)
│       │       ├── if hy_RiemannSolver == LLF  → call hy_uhd_LLF(...)
│       │       ├── if hy_RiemannSolver == Marquina → call hy_uhd_Marquina(...)
│       │       ├── if hy_RiemannSolver == Hybrid →
│       │       │   if SHOK_VAR(cell) == 1 → call hy_uhd_HLL(...)
│       │       │   else → call hy_uhd_HLLC(...) (or HLLD for MHD)
│       │       └── ...
│       │
│       ├── Step 5: Transverse flux（3D CTU）
│       │   └── 按 transOrder 跨方向修正
│       │
│       ├── Step 6: AMR flux correction（行 534-599）
│       │   ├── Grid_putFluxData(blockID, IAXIS, flx, datasize, hy_fluxCorVars, faceAreas)
│       │   │   # 把通量存到 Grid 内部 gr_xflx/yflx/zflx
│       │   ├── Grid_conserveFluxes(ALLDIR, level)
│       │   │   # 跨 block 边界做守恒修正
│       │   └── Grid_getFluxData(blockID, IAXIS, flx, ...)
│       │       # 读回修正后的通量
│       │
│       ├── Step 7: 保守更新
│       │   └── hy_uhd_unsplitUpdate
│       │       └── U^{n+1} = U^n - (dt/dV) * Σ_faces (F * A) + source terms
│       │
│       ├── Step 8: 能量修正
│       │   └── hy_uhd_energyFix
│       │       └── 如果总能量 ≈ 动能（内能 << 动能），用辅助内能方程的结果替换
│       │
│       ├── Step 9: MHD 专属（如果是 USM-MHD）
│       │   ├── hy_uhd_getElectricFields（行 ~700）
│       │   │   └── E_edge = -(v × B) at cell edges
│       │   ├── hy_uhd_staggeredDivb（行 610, 769, 1059）
│       │   │   └── B_face^{n+1} = B_face^n + dt * curl(E_edge)
│       │   │       └── div(B) = div(curl(E)) ≡ 0 数学恒等
│       │   └── 非理想 MHD（如启用）：add{Hall,Biermann,Nernst,Resistive,CrossField}Fluxes
│       │
│       └── Step 10: EOS 调和
│           └── Eos_wrapped(CENTER, MODE_DENS_IE)
│               └── 让 dens/ener/temp/eint 物理自洽
│
└── 所有 block 处理完后:
    └── Hydro_consolidateCFL (CFL 统计)
```

### 3.2 为什么是这个顺序

按 L-011 讲为什么：

- **填 guard cell 最前**：Riemann solver 必须看邻居 cell 才能算界面通量；guard cell 脏 = 通量算错
- **激波探测在重构前**：让 Hybrid solver / shockLowerCFL 知道哪里降阶
- **数据重构在 Riemann 前**：Riemann solver 输入是 left/right state，必须先重构
- **AMR flux correction 在保守更新前**：保证 block 边界通量守恒，否则不同 block 的能量不守恒
- **能量修正最后**：检查更新结果，避免数值消去误差
- **EOS 最后**：让变量物理自洽（Hydro 写了 dens/ener，EOS 算 tele/eint）
- **MHD CT 在 B 更新后**：CT 公式直接给 B^{n+1}，不需要"修正"

---

## 4. Riemann solver 调度机制

源码：`source/physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90:L412-L462`（X 方向）

### 4.1 调度代码（伪）

```fortran
! source/physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90:412-462
do k = blkLimits(LOW,KAXIS), blkLimits(HIGH,KAXIS)
   do j = blkLimits(LOW,JAXIS), blkLimits(HIGH,JAXIS)
      do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)+1

         ! 取 left/right state（来自 Step 3 重构）
         VL = hy_VL(:, i, j, k)
         VR = hy_VR(:, i, j, k)

         ! 按 hy_RiemannSolver 调具体 solver
         if (hy_RiemannSolver == HLLC) then
            call hy_uhd_HLLC(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)

         elseif (hy_RiemannSolver == HLL) then
            call hy_uhd_HLL(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)

         elseif (hy_RiemannSolver == HLLD) then
            call hy_uhd_HLLD(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)

         elseif (hy_RiemannSolver == ROE) then
            call hy_uhd_Roe(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)

         elseif (hy_RiemannSolver == LLF) then
            call hy_uhd_LLF(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)

         elseif (hy_RiemannSolver == HYBRID) then
            if (SHOK_VAR(i,j,k) == 1) then
               call hy_uhd_HLL(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)
            else
               call hy_uhd_HLLC(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)
            end if
         end if

         ! 错误处理
         if (ierr /= 0) then
            ! 退到 HLL（最鲁棒）
            call hy_uhd_HLL(DIR_X, VL, VR, xflux(:,i,j,k), speed, ierr)
         end if
      end do
   end do
end do
```

### 4.2 为什么 if-elseif 不是 select-case

历史原因 + 可读性。每个分支重复 3 次（X/Y/Z 方向），共 ~150 行代码。Modern Fortran 可以重构为 select case + 函数指针，但 FLASH 团队保留这种风格。

### 4.3 错误回退

如果某个 Riemann solver 返回 `ierr != 0`（如 HLLC 在极端 state 崩），自动退到 HLL（最鲁棒）。这是**数值稳定性兜底**。

---

## 5. AMR flux correction 双循环

### 5.1 为什么需要

AMR 网格里，粗 block 和细 block 的边界通量必须**精确守恒**——否则不同 block 的能量/动量不守恒，长时间漂移。

### 5.2 双循环机制

源码：`hy_uhd_unsplit.F90:L534-L599`（put）和后续（get）

```
第一遍循环（每 block）:
   算通量 flx
   └── Grid_putFluxData(blockID, IAXIS, flx, ...)
       # 存到 Grid 内部 gr_xflx/yflx/zflx 数组

跨 block 守恒修正:
   └── Grid_conserveFluxes(ALLDIR, level)
       # 对每个粗-细边界：
       #   细 block 通量平均 = 粗 block 通量
       #   修正粗 block 通量使两边一致

第二遍循环（每 block）:
   └── Grid_getFluxData(blockID, IAXIS, flx, ...)
       # 读回修正后的通量
   └── hy_uhd_unsplitUpdate 用修正后的通量做保守更新
```

### 5.3 UG 模式自动关

源码：`hy_uhd_unsplit.F90:L197-L199`

```fortran
if (GRID_UNKNOWN == GRID_UG) then
   hy_fluxCorrect = .FALSE.
end if
```

UG 无 AMR，没有粗-细边界，flux correction 无意义。

---

## 6. Guard cell 填充策略

源码：`hy_uhd_unsplit.F90:L227-L323`

### 6.1 三次 fillGuardCells

| 时机 | 行号 | 用途 |
|---|---|---|
| **激波探测前**（行 227） | `Grid_fillGuardCells(CENTER, ALLDIR, doEos=.false., mask=gcMask)` | 激波探测需要邻居数据，但不需要 EOS 调和 |
| **主前**（行 294） | `Grid_fillGuardCells(CENTER, ALLDIR, doEos=.true., eosMode=hy_eosModeGc, mask=hy_gcMask)` | Riemann state 重构需要 EOS 自洽的邻居 |
| **MHD 面心**（行 323, 630） | `Grid_fillGuardCells(CENTER_FACES, ALLDIR, ...)` | 面心磁场 guard cell |

### 6.2 hy_gcMask（哪些变量填）

源码：`Hydro_init.F90:L577-L682`

`hy_gcMask` 是 `NUNK_VARS + NDIM*NFACE_VARS` 大小的布尔数组。每个变量对应一个开关：

- `DENS_VAR` / `PRES_VAR` / `ENER_VAR` / `VELX/Y/Z_VAR` / `EINT_VAR` / `TELE_VAR` / ... → TRUE（Hydro 用）
- `DEPO_VAR`（激光沉积） → FALSE（激光自己更新）
- `COND_VAR`（电导率） → FALSE（materialProperties 更新）
- `PWIN_VAR`（等离子体频率） → FALSE

**为什么**：只填 Hydro 需要的变量，省时间和避免覆盖其他单元的更新。

---

## 7. MHD CT 详解

### 7.1 Constrained Transport 数学

CT 的核心：**B 在 face 中心**（staggered），用 edge 电场的 curl 更新：

$$B^{n+1}_{face} = B^n_{face} + dt \cdot \nabla \times E_{edge}$$

由于离散 curl 的数学恒等性 $\nabla \cdot (\nabla \times E) \equiv 0$，**初始 ∇·B = 0 时永远保持**。

### 7.2 电场计算

源码：`source/physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh/hy_uhd_getElectricFields.F90`

理想 MHD：$\vec{E} = -\vec{v} \times \vec{B}$

每个 cell edge 算一个 E（共 12 个 edge/cell，3D）。然后 CT 公式更新 face B。

### 7.3 divB 检查

源码：`source/physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh/hy_uhd_staggeredDivb.F90`

调用时机（行 610, 769, 1059）：每次 B 场更新后。

```
divB(i,j,k) = (Bx(i+1,j,k) - Bx(i,j,k))/Δx + ...（face 中心差分）
```

如果 divB 接近机器精度（~1E-15），CT 正常；如果发散，说明 bug。

---

## 8. 能量修正机制

源码：`source/physics/Hydro/HydroMain/unsplit/hy_uhd_energyFix.F90`

### 8.1 为什么需要

总能量 $E = \rho e + \frac{1}{2}\rho v^2$。当动能远大于内能（$v^2 \gg e$），用总能量减动能算内能会有**灾难性消去**（catastrophic cancellation）——有效位数丢失。

### 8.2 解决方案

`use_auxEintEqn=TRUE`（默认）**同时解两个能量方程**：
- 总能量方程（动量通量里含压力）
- 辅助内能方程（独立演化）

更新后：
- 如果总能量减动能的结果和辅助内能方程差别大（消去误差） → 用辅助内能
- 否则用总能量（更精确）

`hy_uhd_energyFix` 就是这个检查和替换。

---

## 9. 完整调用关系（文字 + 缩进）

```
Driver_evolveFlash (Driver)
├── (初始化) Driver_initFlash
│   └── Hydro_init ★
│       ├── RuntimeParameters_get 读所有 hy_* 参数
│       ├── 字符串→整数映射（RiemannSolver, slopeLimiter, eosModeGc）
│       ├── 分配 scratch 数组
│       └── 设置 hy_gcMask（哪些变量 fillGuardCells）
│
├── (主循环每步)
│   ├── Grid_fillGuardCells (Grid)
│   ├── Hydro_computeDt ★
│   │   └── 每 block 算 dt_CFL = CFL * Δx/(|v| + c_s)
│   │       └── Driver_computeDt 汇总取最小
│   │
│   ├── Hydro(blockCount, blockList, dt, ...) ★
│   │   ├── 对每 blockID:
│   │   │   └── hy_uhd_unsplit (unsplit 主流程)
│   │   │       ├── Step 1: Grid_fillGuardCells
│   │   │       ├── Step 2: hy_uhd_shockDetect
│   │   │       ├── Step 3: hy_uhd_dataReconst + hy_uhd_TVDslope
│   │   │       ├── Step 4: hy_uhd_getFaceFlux → hy_uhd_HLLC/HLL/HLLD/Roe/...
│   │   │       ├── Step 5: transverse flux
│   │   │       ├── Step 6: Grid_putFluxData → Grid_conserveFluxes → Grid_getFluxData
│   │   │       ├── Step 7: hy_uhd_unsplitUpdate
│   │   │       ├── Step 8: hy_uhd_energyFix
│   │   │       ├── Step 9: hy_uhd_staggeredDivb (MHD)
│   │   │       │          hy_uhd_getElectricFields (MHD)
│   │   │       │          hy_uhd_add{Hall,Biermann,Nernst,...}Fluxes (非理想 MHD)
│   │   │       └── Step 10: Eos_wrapped
│   │   └── Hydro_consolidateCFL (CFL 统计)
│   │
│   ├── Eos_wrapped (Eos 单元)
│   ├── Driver_sourceTerms (Burn/Cool/Laser/...)
│   └── Grid_updateRefinement
│
└── (收尾) Driver_finalizeFlash
    └── Hydro_finalize ★ (空)
```

---

## 10. 延伸阅读

- **Hydro 总览**：`knowledge/overview.md`
- **参数字典**：`knowledge/params.md`
- **典型配置**：`knowledge/recipes.md`
- **常见错误**：`knowledge/pitfalls.md`
- **Grid 单元（unk 数组、AMR flux）**：`flash-grid` skill
- **Driver 主循环**：`flash-driver` skill
- **EOS 三温耦合**：`flash-eos` skill（Phase 2）

---

## 11. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：11 段 internals；12 公共 API 分类；CTU 完整 10 步流程（含行号）；Riemann solver 调度源码；AMR flux correction 双循环；MHD CT 数学；hy_gcMask 机制；完整文字调用图（按 L-002 不用 mermaid） | claude |
