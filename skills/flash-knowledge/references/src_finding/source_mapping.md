> **迁移注记**（2026-11-06 · commit 54a9f69）：本文档迁自 `flash/flash_src/docs/src_finding/`（源目录已移至 `flash/temp_delete/`），内容零改动。
> - FLASH4.8 源码树：`E://PhySimX//PhySimX//simulation//flash//flash_src//FLASH4.8//FLASH4.8//source//`（仓外只读）；文中 `FLASH4.8/source/...` 均为相对该树的路径，已抽验存在
> - FLASH4.8 用户指南：`E://PhySimX//PhySimX//simulation//flash//docs//flash4_ug_4p8.md`（仓外）
> - 归属：flash-knowledge 技能参考文档（skills/flash-knowledge/references/src_finding/）

> - 行号抽验：✅ `hy_uhd_prim2flx.F90` 行67-72 通量赋值区段与文档一致（2026-11-06）；来源为用户级 flash-source-lookup 技能，作为方程↔源码映射附录

# FLASH4.8 物理方程 ↔ 源码映射参考

> 本文档为 FLASH4.8 源码中关键物理方程的定位参考。
> 所有路径相对于 `FLASH4.8/source/`。

## 1. Euler守恒方程（无磁场）

### 文档位置
`docs/flash4_ug_4p8.md` 第15章，式15.1-15.3

```text
∂ρ/∂t + ∇·(ρv) = 0
∂(ρv)/∂t + ∇·(ρvv + P·I) = 0
∂(ρE)/∂t + ∇·[(ρE + P)v] = 0
```

### 源码映射

| 功能 | 文件 | 实现位置 |
|------|------|----------|
| **原始变量→通量** | `physics/Hydro/HydroMain/unsplit/hy_uhd_prim2flx.F90` | 行53-121 |
| **守恒变量更新** | `physics/Hydro/HydroMain/unsplit/hy_uhd_unsplitUpdate.F90` | 行1364-1419 (`updateConservedVariable`) |
| **主驱动** | `physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90` | 整体流程 |
| **黎曼求解器(HLLC)** | `physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_HLLC.F90` | / |
| **原始→守恒转换** | `physics/Hydro/HydroMain/unsplit/hy_uhd_prim2con.F90` | / |
| **守恒→原始转换** | `physics/Hydro/HydroMain/unsplit/hy_uhd_con2prim.F90` | / |

### 核心方程源码（通量）

```fortran
! hy_uhd_prim2flx.F90, 无磁场分支 (#ifdef FLASH_UHD_HYDRO)
! X方向 (行67-72):
F(F01DENS_FLUX) = dens*velx                 ! 质量通量
F(F02XMOM_FLUX) = (dens*velx)*velx + pres   ! x动量通量 = ρ·u²+P
F(F03YMOM_FLUX) = (dens*velx)*vely          ! y动量通量 = ρ·u·v
F(F04ZMOM_FLUX) = (dens*velx)*velz          ! z动量通量 = ρ·u·w
F(F05ENER_FLUX) = (ener + pres)*velx        ! 能量通量 = (E+P)·u

! Y方向 (行86-91):
F(F01DENS_FLUX) = dens*vely
F(F02XMOM_FLUX) = (dens*vely)*velx
F(F03YMOM_FLUX) = (dens*vely)*vely + pres
F(F04ZMOM_FLUX) = (dens*vely)*velz
F(F05ENER_FLUX) = (ener + pres)*vely

! Z方向 (行104-110):
F(F01DENS_FLUX) = dens*velz
F(F02XMOM_FLUX) = (dens*velz)*velx
F(F03YMOM_FLUX) = (dens*velz)*vely
F(F04ZMOM_FLUX) = (dens*velz)*velz + pres
F(F05ENER_FLUX) = (ener + pres)*velz
```

### 有限体积更新

```fortran
! hy_uhd_unsplitUpdate.F90 (updateConservedVariable)
! 一维: U = U - dt/dx * (FR - FL)
! 二维: U = U - dt/dy * (GR - GL)
! 三维: U = U - dt/dz * (HR - HL)
! 物理源项: U = U + dt * Sphys
```

---

## 2. 激光能量沉积

### 文档位置
第14章，式14.7b — `Q_las` 项

### 源码映射

| 功能 | 文件 | 实现位置 |
|------|------|----------|
| **主驱动（几何光学追迹）** | `physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition.F90` | 整体流程 |
| **光束功率（脉冲插值）** | `.../LaserBeams/ed_computeBeamPower.F90` | 主体 |
| **光线创建** | `.../LaserRays/ed_createRays.F90` | / |
| **光线追迹** | `.../ed_traceRays/ed_traceRays.F90` | / |
| **等离子体能量更新** | `.../Laser_3T/ed_updatePlasma3T.F90` | 3T版本 |

### 流程
```
ed_createRays → ed_traceRays → ed_updatePlasma(3T)
                                ↕
ed_computeBeamPower(当前时间步平均功率)
```

### 能量沉积变量
- 默认写入 `ed_depoVar`（对应 Q_las）
- 在 3T 运行模式下，写入电子能量方程 `e_ele`

---

## 3. 电子热传导（限流 Spitzer 模型）

### 文档位置
第14章，式14.9-14.10；第19章（扩散求解器）；第23章（热导率）

```text
q_ele = -κ_ele · ∇T_ele
∂(ρ·e_ele)/∂t |_cond = ∇·(κ_ele · ∇T_ele)
```

### 源码映射（两单元协作）

#### 单元A：热导率

| 功能 | 文件 | 实现 |
|------|------|------|
| **Spitzer热导率** | `physics/materialProperties/Conductivity/ConductivityMain/Spitzer/Conductivity.F90` | 行87: `condLoc = 9.2e-7 * T^2.5` |
| **比热c_v** | `physics/materialProperties/Conductivity/ConductivityMain/Spitzer/cond_getCv.F90` | / |
| **常量热导率** | `.../ConductivityMain/Constant/Conductivity.F90` | / |
| **Lee-More热导率** | `.../ConductivityMain/LeeMore/Conductivity.F90` | / |
| **Epperlein-Haines** | `.../ConductivityMain/EppHain/Conductivity.F90` | / |

#### 单元B：扩散求解 + 限流器

| 功能 | 文件 | 实现 |
|------|------|------|
| **热扩散通量计算** | `physics/Diffuse/DiffuseFluxBased/Diffuse_therm.F90` | 行41-49 |
| **限流因子计算** | `physics/Diffuse/DiffuseMain/Diffuse_fluxLimiter.F90` | λ∈(0,1/3], 输出3λ∈[0,1] |
| **通用限流器** | `physics/Diffuse/DiffuseMain/Diffuse_applyGenericFluxLimiter.F90` | / |
| **扩散标量求解** | `physics/Diffuse/DiffuseMain/Diffuse_solveScalar.F90` | 隐式求解 |

### Spitzer热导率源码

```fortran
! Conductivity.F90 行55-89
real, parameter :: ck = 9.2e-7     ! Spitzer常数
real, parameter :: cexp = 2.5       ! 温度指数
condLoc = ck * xtemp**cexp          ! κ = 9.2e-7·T^2.5
diff_coeffLoc = condLoc / (xden * cv)  ! 扩散系数 = κ/(ρ·c_v)
```

### 限流器源码

```fortran
! Diffuse_fluxLimiter.F90 行42-45
! 限流因子 λ ∈ (0, 1/3]
! 输出到 FLLM_VAR 的是 3λ ∈ [0, 1]
! 修改后的扩散系数: κ_limited = κ / (1 + 3λ·κ·|∇T|/(ρ·c_v·T_max))
```

### 热扩散通量

```fortran
! Diffuse_therm.F90 行40-49
! 面通量: F_i = -(κ_i + κ_{i-1})/2 · (T_i - T_{i-1})/dx
! 能量更新: dE_i = -(F_{i+1} - F_i)/dx
```

---

## 4. 多群辐射扩散

### 文档位置
第14章式14.11-14.20；第25章节25.1

```text
第g群:
∂u_g/∂t + ∇·(u_g·v) + ... = -∇·q_g + Q_emis,g - Q_abs,g
  其中 q_g = -D_g·∇u_g,  D_g = c/(3κ_tr,g)
  Q_abs,g = c·κ_a,g·u_g
  Q_emis,g = κ_e,g·c·aT^4·[P(x_g) - P(x_{g+1})]   (Planck积分)
```

### 源码映射

| 功能 | 文件 | 子程序/位置 |
|------|------|-------------|
| **MGD主驱动** | `physics/RadTrans/RadTransMain/MGD/RadTrans.F90` | `RadTrans` 整体流程 |
| **逐群扩散求解** | 同上 | 行250-509循环 |
| **扩散系数** | 同上 | 行312 |
| **吸收项** | 同上 | 行319 |
| **发射项(Planck)** | 同上 | 行322-333 |
| **通量限流** | `.../MGD/RadTrans_computeFluxLimiter.F90` | 委托 Diffuse |
| **辐射边界条件** | `.../MGD/RadTrans_mgdSetBc.F90` | / |
| **组能量汇总** | `physics/RadTrans/RadTransMain/RadTrans_sumEnergy.F90` | / |
| **Planck积分** | `physics/RadTrans/RadTransMain/RadTrans_planckInt.F90` | / |
| **不透明度查询** | `physics/materialProperties/Opacity/OpacityMain/.../Opacity.F90` | 返回 κ_a, κ_e, κ_tr |
| **扩散求解器** | `physics/Diffuse/DiffuseMain/Diffuse_solveScalar.F90` | 隐式求解 |

### 核心源码（MGD/RadTrans.F90）

```fortran
! 行250: 逐群循环
do gloc = 1, NGROUPS
  ! 行312: 扩散系数 D_g = c/(3·κ_tr)
  COND_VAR = rt_speedlt3 / max(TINY, trans_opac)

  ! 行316: 前导系数 = 1.0
  DFCF_VAR = 1.0

  ! 行319: 吸收项 Q_abs = c·κ_a
  ABSR_VAR = C * absorb_opac

  ! 行322-333: 发射项 (Planck积分)
  tele = TELE_VAR
  xg   = rt_mgdBounds(g)   / (KB*tele)
  xgp1 = rt_mgdBounds(g+1) / (KB*tele)
  call RadTrans_planckInt(xg, pxg)
  call RadTrans_planckInt(xgp1, pxgp1)
  emiss = emit_opac * C * A*tele**4 * 15/pi**4 * (pxgp1 - pxg)
  EMIS_VAR = emiss

  ! 行340: 通量限流值
  FLLM_VAR = rt_mgdFlCoef * C * u_g

  ! 行409-419: 调用隐式扩散求解器
  call Diffuse_solveScalar(gvar, COND_VAR, DFCF_VAR, bcTypes, bcValues, dt, ...)

  ! 行490: 吸收后处理
  change = change + urad * C * absorb_opac
end do
```

---

## 5. 完整3T算子分裂流程

多物理耦合的完整流程图：

```
┌──────────────────────────────────────────────┐
│  3T算子分裂 (第14章)                          │
│                                                │
│  1. Hydro 单元 (守恒律+功)   → Eqs.14.6       │
│     - hy_uhd_unsplit.F90                      │
│                                                │
│  2. Heatexchange 单元 (ion-ele平衡) → Eq.14.8 │
│     - physics/sourceTerms/Heatexchange/        │
│                                                │
│  3. Diffuse 单元 (电子热传导)    → Eq.14.10    │
│     - Diffuse_therm.F90 + Conductivity.F90     │
│                                                │
│  4. RadTrans 单元 (辐射扩散)     → Eq.14.11    │
│     - MGD/RadTrans.F90 + Opacity.F90           │
│                                                │
│  5. EnergyDeposition (激光加热)  → Eq.14.7b    │
│     - Laser/EnergyDeposition.F90               │
└──────────────────────────────────────────────┘
```

## 6. 搜索技巧汇总

### grep关键词速查

| 要查找的内容 | 关键词 |
|-------------|--------|
| Spitzer热导率公式 | `ck*xtemp**cexp` 或 `9.2e-7` |
| 辐射扩散系数 | `rt_speedlt3 / max` |
| 辐射吸收 | `urad * C * absorb_opac` |
| 辐射发射(Planck) | `RadTrans_planckInt` |
| 通量限制 | `FLLM_VAR` |
| 能量沉积(Q_las) | `ed_depoVar` 或 `Qlas` |
| 质量通量 | `F01DENS_FLUX` |
| 动量通量 | `F02XMOM_FLUX` |
| 光速常量 | `rt_speedlt` |
| 限流器模式 | `rt_mgdFlMode` |
