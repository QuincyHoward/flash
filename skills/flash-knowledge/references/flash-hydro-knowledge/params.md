---
title: Hydro 参数字典 — 主控 / 重构 / Riemann / 限幅器 / MHD / 截断
skill: flash-hydro
category: params
source_anchors:
  - source/physics/Hydro/HydroMain/Config:L15-L33
  - source/physics/Hydro/HydroMain/unsplit/Config:L80-L226
  - source/physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh/Config:L88-L152
  - source/physics/Hydro/HydroMain/split/PPM/Config:L80-L116
manual_ref: "FLASH 4.8 User Guide §9-12"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - hydro
  - parameter
  - cfl
  - riemann
  - limiter
  - mhd
---

# Hydro 参数字典

> **TL;DR**：~70 个 runtime parameter，按 9 类组织。**重要**：参数名是 `RiemannSolver`（不是 `hy_riemannSolver`）、`cfl`（不是 `hy_cfl`，虽然内部存到 `hy_cfl`）、`slopeLimiter`（不是 `hy_limiter`）。每个参数给出**默认值依据**（按 L-011）。

---

## 0. 命名约定（重要）

**Hydro 参数在 parfile 里没有 `hy_` 前缀**！前缀只用于 Hydro_data 模块内部全局变量（如 `hy_cfl`、`hy_RiemannSolver`）。parfile 写：

```fortran
# parfile 里
cfl = 0.5                  # ✓
RiemannSolver = "HLLD"     # ✓
slopeLimiter = "mc"        # ✓

# 不是
hy_cfl = 0.5               # ✗ parfile 不识别
hy_RiemannSolver = "HLLD"  # ✗
```

`Hydro_init` 在启动时把这些参数读到模块变量（加 `hy_` 前缀）：

```fortran
call RuntimeParameters_get("cfl", hy_cfl)
call RuntimeParameters_get("RiemannSolver", str_RiemannSolver)
! 然后把字符串映射到 int: hy_RiemannSolver = HLLC
```

源码：`source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L68-L69, L432-L477`

---

## 1. 主控参数

源码：`source/physics/Hydro/HydroMain/Config:L9-L33`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `useHydro` | BOOLEAN | FALSE（Hydro/Config）→ TRUE（HydroMain/Config） | Hydro/Config 是顶层 stub，不调 Hydro；HydroMain 是实际启用 |
| `updateHydroFluxes` | BOOLEAN | TRUE | FALSE 时只算通量不更新 unk（调试用） |
| `cfl` | REAL | **0.8** | CTU 理论稳定限 CFL≤1，0.8 留 20% 余量给非线性。强激波降到 0.4-0.5 |
| `UnitSystem` | STRING | "none" | "none" / "SI" / "CGS"。影响 `hy_bref`（磁场参考单位） |
| `irenorm` | INTEGER | 0 | 0=不归一化物种丰度（保持质量守恒）；1=每步归一化到 1 |

---

## 2. 重构 / 插值（unsplit）

源码：`source/physics/Hydro/HydroMain/unsplit/Config:L80-L150`

### 2.1 空间重构阶

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `order` | INTEGER [1,2,3,5,6] | **2** | 2=MUSCL-Hancock，2 阶 TVD 基线。3=PPM（更锐但耗内存，NGUARD≥6）；5=WENO（更锐但慢 3-5x）；6=GP（实验） |
| `wenoMethod` | STRING | "WENO5" | order=5 时选 WENO5（标准）或 WENOZ（更锐但更耗散在某些情况） |
| `hy_3Torder` | INTEGER [-1,1,2,3,5] | -1 | -1=同 order（推荐）；3T 变量重构阶。某些算例需要单独调（如 3T 离子温度用 1 阶更稳） |
| `transOrder` | INTEGER [0,1,2,3,4] | 1 | 3D CTU transverse flux 阶数。1=默认；3 实验性 |
| `use_3dFullCTU` | BOOLEAN | TRUE | TRUE=CFL≤1（推荐）；FALSE=CFL≤1/2（简化）。**非 cartesian abort**（未推导） |

### 2.2 限幅器

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `slopeLimiter` | STRING | **"vanLeer"** | vanLeer 平衡耗散和锋利度。minmod 太耗散；MC 在强激波易崩；hybrid 实验性 |
| `LimitedSlopeBeta` | REAL | 1.0 | slopeLimiter="limited" 时用（1=minmod，2=superbee） |
| `charLimiting` | BOOLEAN | TRUE | TRUE=限制特征变量（按波族独立限制，物理合理）；FALSE=限制原始变量（耦合，激波失真） |
| `use_steepening` | BOOLEAN | FALSE | PPM 接触陡峭（让密度界面更锐）；通常不需要 |
| `use_flattening` | BOOLEAN | FALSE | PPM flattening（强激波附近 zerout slopes）；现代用 shockDetect 替代 |

### 2.3 杂交重构（自适应降阶）

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `use_hybridOrder` | BOOLEAN | FALSE | TRUE=激波附近自动降到 1 阶（保 positivity） |
| `hybridOrderKappa` | REAL | 0.0 | 激波检测阈值（基于 Rankine-Hugoniot 跳跃） |
| `PosKappa1` | REAL | 0.4 | positivity 保留下限 |
| `PosKappa2` | REAL | 0.4 | positivity 保留范围 |

### 2.4 人工粘性 / upwind

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `use_avisc` | BOOLEAN | FALSE | 人工粘性（老办法）；现代用 Riemann solver + limiter |
| `cvisc` | REAL | 0.1 | 人工粘性系数（0=关；典型 0.1-0.3） |
| `use_upwindTVD` | BOOLEAN | FALSE | PPM upwind TVD。**NGUARD≤4 时强制关**（需要 6 层 guard cell） |

### 2.5 其他重构

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `hy_fPresInMomFlux` | REAL [0..1] | 1.0 (unsplit) / 0.0 (unsplit_rad) | 动量通量里压力梯度处理比例 |
| `conserveAngMom` | BOOLEAN | FALSE | 柱坐标下守恒角动量（用环向动量替代直角速度） |
| `use_auxEintEqn` | BOOLEAN | TRUE | 同时解辅助内能方程（避免总能量大数消去内能的误差） |
| `EOSforRiemann` | BOOLEAN | FALSE | TRUE=重构后对 left/right state 调 EOS（更准但慢） |

---

## 3. Riemann solver

源码：`source/physics/Hydro/HydroMain/unsplit/Config:L156-L172`、调度在 `Hydro_init:L432-L477`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `RiemannSolver` | STRING | **"HLLC"** | HLLC 恢复接触间断、保守、不需 entropy fix、稳定。MHD 推荐 HLLD |

**取值**（8 种 + Zero）：
- `"HLL"` — 简单鲁棒但耗散
- `"HLLC"` — **默认**，平衡
- `"HLLD"` — MHD 推荐（5 中间态）
- `"Roe"` — 精确但需 entropy fix
- `"LLF"` / `"LocalLaxFriedrichs"` — 最鲁棒但最耗散
- `"Marquina"` / `"MarquinaModified"` — 强激波鲁棒，昂贵
- `"Hybrid"` — 激波区 HLL + 其他 HLLC（自动启用 shockDetect）
- `"Zero"` — 调试用

### 3.1 Entropy fix（Roe 用）

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `entropy` | BOOLEAN | FALSE | Roe 的 entropy fix 开关（推荐用 Roe 时打开） |
| `entropyFixMethod` | STRING | "HARTENHYMAN" | "Harten"（简单）/ "HartenHyman"（更精确） |

### 3.2 激波探测 + 自适应 CFL

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `shockDetect` | BOOLEAN | FALSE | Balsara-Spicer 1999 激波探测 |
| `shockLowerCFL` | BOOLEAN | FALSE | 激波 cell 自动降 CFL（强激波鲁棒，建议开） |
| `hy_fallbackLowerCFL` | BOOLEAN | FALSE | 重构 fallback 到 1 阶时降 CFL |
| `hy_cflFallbackFactor` | REAL | 0.9 | fallback 时 CFL 乘以 0.9 |

---

## 4. 截断（floor values）

源码：`source/physics/Hydro/HydroMain/Config` 各 Config 重复

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `small` | REAL | 1.E-10 | 通用小阈值 |
| `smlrho` | REAL | 1.E-10 | 密度下限（防止 NaN/log(0)）。天体算例可能需要降到 1.E-30 |
| `smallp` | REAL | 1.E-10 | 压力下限 |
| `smalle` | REAL | 1.E-10 | 能量下限 |
| `smallt` | REAL | 1.E-10 | 温度下限 |
| `smallu` | REAL | 1.E-10 | 速度截断 |
| `smallx` | REAL | 1.E-10 | 物种丰度下限 |
| `tiny` | REAL | 1.E-16 | 防 div-by-zero |

**注意**：默认 1.E-10 适合实验室尺度（密度 ~1 g/cm³）。**天体算例（密度 ~1E-20 g/cm³）需要降到 1.E-30**，否则 floor 会"压制"真实物理。

---

## 5. MHD 参数（USM-MHD）

源码：`source/physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh/Config:L88-L152`

### 5.1 DivB 控制

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `killdivb` | BOOLEAN | TRUE | CT（constrained transport）清理 ∇·B，保持机器精度。1D/order=1/ForceHydroLimit 时自动关 |
| `killdivb8w` | BOOLEAN | FALSE | TRUE=用 Powell 8-wave 替代 CT（更耗散但简单） |
| `E_modification` | BOOLEAN | TRUE | 改进的电场计算 |
| `E_upwind` | BOOLEAN | FALSE | upwind 更新电场（更准但慢） |
| `energyFix` | BOOLEAN | FALSE | CT scheme 的能量修正 |

### 5.2 重构 / prolongation

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `ForceHydroLimit` | BOOLEAN | FALSE | TRUE=USM 代码路径但不更新 B（当纯流体用） |
| `prolMethod` | STRING | "INJECTION_PROL" | face-var prolongation。**cylindrical 强制 Balsara**（正确性需要） |
| `conserveAngField` | BOOLEAN | FALSE | 柱坐标下角向场守恒形式 |

### 5.3 非理想 MHD

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `use_Biermann` | BOOLEAN | FALSE | Biermann battery（磁场种子机制） |
| `use_Biermann1T` / `use_Biermann3T` | BOOLEAN | FALSE | 1T/3T battery 变体 |
| `hy_biermannSource` | BOOLEAN | FALSE | 作为源项而非通量实现 |
| `hy_biermannCoef` | REAL | 1.0 | battery 系数（调试用，正常=1） |
| `use_Hall` | BOOLEAN | FALSE | Hall 效应（电子-离子尺度分离） |
| `use_Nernst` | BOOLEAN | FALSE | Nernst 项（电子热扩散带磁） |
| `use_CrossField` | BOOLEAN | FALSE | 跨场热扩散 |
| `use_Seebeck` | BOOLEAN | FALSE | Seebeck 效应 |
| `useResistive_limMode` | BOOLEAN | FALSE | 电阻率 limiter |
| `VresistMax` | REAL | — | 最大电阻率（限制数值不稳定） |
| `hallVelocity` | BOOLEAN | FALSE | 用 u_ele = u - J/(ne qe) 做能量更新 |

### 5.4 电流 limiter

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `currFlMode` | STRING | "fl_none" | 电流 limiter（"fl_none"/"fl_harmonic"/"fl_minmax"/"fl_larsen"） |
| `currFlCoef` | REAL | 1.0 | limiter 系数 |

---

## 6. Split PPM 专属

源码：`source/physics/Hydro/HydroMain/split/PPM/Config:L80-L116`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `epsiln` | REAL | 0.33 | PPM 激波检测参数 |
| `omg1` / `omg2` | REAL | 0.75 / 10. | PPM 耗散参数 |
| `igodu` | INTEGER | 0 | 1=用 1 阶 Godunov（不用 PPM） |
| `iplm` | INTEGER | 0 | 1=用 piecewise linear（不用 PPM） |
| `nriem` | INTEGER | 10 | 迭代 Riemann solver 次数 |
| `rieman_tol` | REAL | 1.E-5 | Riemann 收敛容差 |
| `dp_sh` / `dp_sh_md` | REAL | 0.33 | 1D/多维激波检测压力跳变阈值 |
| `cvisc` | REAL | 0.1 | 人工粘性系数（同 unsplit） |
| `hybrid_riemann` | BOOLEAN | FALSE | Woodward-Colella trick：激波处用 HLLE 避免奇偶耦合 |
| `leveque` | BOOLEAN | FALSE | LeVeque 风格重力源项处理 |

---

## 7. 8-wave MHD 专属

源码：`source/physics/Hydro/HydroMain/split/MHD_8Wave/Config:L50-L75`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `killdivb` | BOOLEAN | TRUE | Powell 8-wave DivB 清理（这个变体里只能用 Powell） |
| `RoeAvg` | BOOLEAN | TRUE | TRUE=用 Roe 平均；FALSE=用算术平均 |
| `hall_parameter` | REAL | 0.0 | Hall 参数 |
| `hyperResistivity` | REAL | 0.0 | Hyper-resistivity 系数（数值稳定） |

---

## 8. Flux correction / AMR

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `hy_fullSpecMsFluxHandling` | BOOLEAN | TRUE | 物种 & mass scalar 全 flux correction 处理（一致性） |
| `addThermalFlux` | BOOLEAN | TRUE（FALSE if 3T） | 加热传导通量。**3T 模式自动关**（unsplit 热 conduction 与 3T 不兼容） |
| `hy_useFluxEqn` | BOOLEAN | FALSE | 用 FLUX-type 方程（高级，一般不开） |
| `flux_correct` | BOOLEAN | TRUE（UG 自动 FALSE） | AMR 细-粗边界 flux correction（Driver 拥有） |

---

## 9. EOS / 边界 / 时间步

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `hy_eosModeGc` | STRING | "see eosMode" | guard cell 填充时 EOS 模式（默认跟全局 eosMode） |
| `hy_eosModeAfter` | STRING | "dens_ie" | Hydro sweep 结束后 EOS 模式（split PPM 专属） |
| `use_gravHalfUpdate` | BOOLEAN | TRUE | n+1/2 时刻重力源项（2 阶时间中心） |
| `hydroComputeDtOption` | INTEGER [-1,0,1] | -1 | -1=完整 Hydro_computeDt.F90（推荐）；0/1=轻量版（优化） |

---

## 10. 守护单元（NGUARD）

源码：`source/physics/Hydro/HydroMain/unsplit/Config:L215-L221`

| 变体 | NGUARD 默认 |
|---|---|
| unsplit（Hydro_Unsplit / MHD_StaggeredMesh） | **4** |
| unsplit + SupportPpmUpwind | **6**（PPM upwind 需要更宽模板） |
| split/PPM | 4（默认） |
| split/MHD_8Wave | **2**（分裂法模板窄） |
| split/RHD | 4 |

**改 NGUARD**：通过 unit Config 文件 `GUARDCELLS N` 声明，重新 setup+make。

---

## 11. 参数前缀速查

| parfile 参数名（无前缀） | 内部模块变量（hy_ 前缀） |
|---|---|
| `cfl` | `hy_cfl` |
| `RiemannSolver` | `hy_RiemannSolver`（int） |
| `slopeLimiter` | `hy_limiter`（int） |
| `order` | `hy_order` |
| `cvisc` | `hy_cvisc` |
| `smlrho` / `smallp` / ... | `hy_small` / `hy_smlrho` / ... |

**记住**：parfile 里**没有** `hy_` 前缀。

---

## 12. 延伸阅读

- **Hydro 总览 / 6 变体**：`knowledge/overview.md`
- **CTU 流程详解**：`knowledge/internals.md`
- **典型 setup + parfile**：`knowledge/recipes.md`
- **常见错误**：`knowledge/pitfalls.md`
- **跨单元查参数**：`flash-param-query` skill + `skills/flash-param-query/knowledge/param-index.md`

---

## 13. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：11 类参数 + 默认值依据（按 L-011）+ 命名约定（parfile 无 hy_ 前缀）+ 前缀速查 | claude |
