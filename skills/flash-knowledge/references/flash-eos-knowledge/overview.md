---
title: Eos 单元总览 — 角色、6 变体、模式系统、3T、Helmholtz vs Tabulated
skill: flash-eos
category: overview
source_anchors:
  - source/physics/Eos/EosMain/Config:L13-L20
  - source/physics/Eos/EosMain/Eos.F90:L237
  - source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_helmholtz.F90:L215-L232
  - source/Simulation/constants.h:L297-L341
  - source/Grid/GridMain/Config:L155-L185
manual_ref: "FLASH 4.8 User Guide §13-15"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - eos
  - overview
  - helmholtz
  - 3t
  - mode
---

# Eos 单元总览

> **TL;DR**：Eos 是 FLASH 所有物理过程的"热力学底座"。给定 (ρ, e) 或 (ρ, T) 或 (ρ, P)，算出其他热力学量（P, T, e, c_s, γ）。**6 个互斥变体**：Gamma（理想气体，默认）/ Multigamma / Helmholtz（HEDP 默认）/ Tabulated（ionmix/sesame 表）/ multiTemp（3T 包装）/ multiFluid（VoF）。EOS 通过 `Eos_wrapped` 被 Hydro、Grid、sourceTerms、RadTrans 反复调用。

---

## 1. Eos 在 FLASH 里扮演什么角色

### 1.1 一句话定位

Eos 单元 = **热力学状态计算器**。输入 `(ρ, X)`，输出 `(P, T, e, c_s, γ, ...)` 让其他物理单元（Hydro、sourceTerms）能正确推进。

具体地说，Eos 解的是**状态方程**：

```
给定 (密度 ρ, 内能 e)     → 算 (压力 P, 温度 T)         [MODE_DENS_IE]
给定 (密度 ρ, 温度 T)     → 算 (压力 P, 内能 e)         [MODE_DENS_TEMP]
给定 (密度 ρ, 压力 P)     → 算 (内能 e, 温度 T)         [MODE_DENS_PRES]
```

加上物质成分（mass fractions → Abar, Zbar），Eos 算出所有热力学量。

### 1.2 为什么需要 EOS

Hydro 解的是**守恒律**（质量、动量、能量），但 Riemann solver 需要知道**压力**才能算通量。能量方程演化的是**总能** E = ρe + ρv²/2，需要从中得到 P 或 T 必须有 EOS。

**例子**：
- Hydro 更新 `ENER_VAR` → 通过 Eos 算 `PRES_VAR` 和 `TEMP_VAR` → 下一步 Riemann solver 用 PRES
- 激光沉积到 `EELE_VAR`（电子内能）→ 通过 Eos 算 `TELE_VAR` 和 `PELE_VAR` → 不透明度查询用 TELE

### 1.3 与其他单元的耦合

```
┌────────────────────────────────────────────────┐
│ Driver_evolveFlash                             │
│   ├── Grid_fillGuardCells(CENTER, ALLDIR)      │
│   │   └── Eos 内部调（让 guard cell 自洽）★    │
│   ├── Hydro(blockCount, blockList, dt, ...)    │
│   │   ├── Riemann state 重构（用 PRES）        │
│   │   ├── 保守更新（更新 ENER_VAR）            │
│   │   └── Eos_wrapped ★                        │  ← Hydro 后必须重算 P, T
│   ├── Eos_wrapped（让变量一致）★               │
│   ├── Driver_sourceTerms                       │
│   │   ├── Heatexchange（3T 平衡，改 EION/EELE）│
│   │   ├── Laser（沉积到 EELE）                 │
│   │   └── 每个源项后可能调 Eos_wrapped ★       │
│   ├── RadTrans（辐射传输，改 ERAD）            │
│   │   └── 调 Eos_wrapped ★                     │
│   └── Grid_updateRefinement                    │
│       └── AMR refine 后调 Eos_wrapped ★        │  ← 让新 block 自洽
└────────────────────────────────────────────────┘
```

Eos 在 **7+ 个时机**被调用（详见 §7）。

---

## 2. 6 个变体一览

源码：`source/physics/Eos/EosMain/Config:L13-L20`

```
DEFAULT Gamma                          # 不指定时默认
EXCLUSIVE Gamma Multigamma Helmholtz   # 1T 三选一
EXCLUSIVE ... multiTemp Degenerate     # 1T vs 3T 互斥
```

| 变体 | 路径 | 描述 | 何时用 |
|---|---|---|---|
| **Gamma**（默认） | `EosMain/Gamma/` | 单成分理想气体，γ=5/3 | 教学、快速测试、Sod 激波管 |
| **Multigamma** | `EosMain/Multigamma/` | 多成分混合理想气体（用 Multispecies） | 多种气体不简并、不电离 |
| **Helmholtz** | `EosMain/Helmholtz/` | Timmes 自由能表 EOS（电子简并 + 离子 + 辐射 + Coulomb） | **HEDP/ICF/激光默认** |
| **Tabulated** | `EosMain/Tabulated/` | 外部表（ionmix/sesame/OPACPLOT/HDF5） | 物质具体数据、部分电离 |
| **multiTemp** | `EosMain/multiTemp/` | 3T 包装（Gamma/Multigamma/Helmholtz/MatRad3/Multitype） | 三温算例 |
| **multiFluid** | `EosMain/multiFluid/` | VoF 双流体 | 不可混流体 |

### 2.1 Helmholtz 3 子变体

源码：`source/physics/Eos/EosMain/Helmholtz/Config:L5`

```
EXCLUSIVE SpeciesBased Ye ExternalAbarZbar
DEFAULT SpeciesBased
```

| 子变体 | 何时用 |
|---|---|
| **SpeciesBased**（默认） | 用 Multispecies 跟踪每种物质的质量分数，自动算 Abar/Zbar |
| **Ye** | 只跟踪 Ye（电子分数），不跟踪具体 species（中子星合并、核合成） |
| **ExternalAbarZbar** | Abar/Zbar 来自外部表（如预先计算的离子化状态） |

### 2.2 multiTemp 5 子变体

源码：`source/physics/Eos/EosMain/multiTemp/Config:L5`

```
CHILDORDER Gamma Multigamma Helmholtz MatRad3 Multitype
```

| 子变体 | 描述 | 何时用 |
|---|---|---|
| **Gamma**（默认） | 3T 理想气体 | 简单 3T 测试 |
| **Multigamma** | 3T 多成分理想气体 | 多物质 3T 但不简并 |
| **Helmholtz** | 3T + 电子简并（电子部分用 helm 表，离子理想气体，辐射黑体） | 完全简并 3T |
| **MatRad3** | 物质（离子+电子合并）+ 辐射 3T | 两温模型 |
| **Multitype** | **混合**：Helmholtz 电子 + Tabulated 离子 + 黑体辐射 | **生产级 3T 激光默认** |

### 2.3 默认选择

不指定时：`EosMain/Config` 默认 **Gamma**。

但**实际算例通常通过 setup shortcut 选**：
- `+eos=Helmholtz` 或 setup 配置 → Helmholtz
- `+3t` → multiTemp（具体子变体看其他 setup 变量）
- `+uhd3t` / `+usm3t` → 同时设 unsplit Hydro + 3T EOS

### 2.4 为什么有这么多变体

不同物理问题对 EOS 需求**根本不同**：

| 物理 | 必须的 EOS 特性 | 推荐 |
|---|---|---|
| 教学测试 | 简单、解析 | Gamma |
| 多物质非简并 | 多 γ | Multigamma |
| 全电离等离子体（ICF） | 电子简并 + Coulomb | Helmholtz |
| 部分电离复杂原子（Au、Fe） | 壳层结构、压力电离 | Tabulated（ionmix） |
| HEDP 三温（激光等离子体） | 简并 + 部分电离混合 | multiTemp/Multitype |

---

## 3. EOS 模式系统（核心概念）

### 3.1 模式是什么

EOS 模式（`mode` 参数）告诉 Eos：**输入是哪两个变量**，输出是哪两个。密度总是输入（`MODE_DENS_*`）。

源码：`source/Simulation/constants.h:L297-L341`

### 3.2 1T 三大主模式（最常用）

| 模式 | 常量 | 输入 | 输出 | 何时用 |
|---|---|---|---|---|
| **dens_ie** | `MODE_DENS_EI = 102` | ρ, e | P, T | **默认**。Hydro 后（能量是守恒变量） |
| **dens_pres** | `MODE_DENS_PRES = 103` | ρ, P | e, T | Riemann 后（已知压力）；导数测试 |
| **dens_temp** | `MODE_DENS_TEMP = 101` | ρ, T | e, P | 初始化（指定 ρ,T）；不透明度查询 |

**为什么有 3 种**：不同调用点手头有的变量不同。Hydro 给你能量；Riemann 给你压力；初始化你直接设温度。

### 3.3 为什么默认 dens_ie

Hydro 解的是**能量守恒方程**：

```
∂(ρE)/∂t + ∇·((ρE + P)v) = source terms
```

E = e + v²/2 是总能（包含动能）。Hydro 更新后，**已知** ρ 和总能 E，扣掉动能得到内能 e（`Eos_getData` 用 `eintSwitch` 防止大数消去）。然后 Eos 用 (ρ, e) 算 (P, T)。所以 **Hydro 后默认 dens_ie**。

### 3.4 特殊模式

| 模式 | 含义 |
|---|---|
| `MODE_EOS_NOP = 55` | No-op，跳过 EOS 计算（仅做 getData/putData） |
| `MODE_EOS_WRAPPERONLY = 67` | 只跑 getData/putData，跳过 kernel |
| `MODE_DENS_ENTR = 1207` | 熵输入（罕用） |

### 3.5 3T 扩展模式

3T 下每个 component（ion/ele/rad）可独立指定模式。常量定义在 `constants.h:L307-L341`：

| 模式族 | 含义 |
|---|---|
| `_ION` / `_ELE` / `_RAD` | 单 component 模式（如 `MODE_DENS_EI_ELE`） |
| `_COMP` | 物质 component（ion + ele，不含辐射） |
| `_ALL` | 3 个 component 独立算 |
| `_EQUI` | 假设 3 个 component 平衡（单 T） |
| `_MAT_EQUI` | 离子+电子平衡（辐射独立） |
| `_GATHER` | 把 3 个 component 能量合并算（廉价，hydro 默认） |
| `_SCATTER` | 把总能分回 3 个 component |
| `_RECAL_GATHER` | **重新算**所有，最贵但最准（`+3t` 默认） |
| `_SELE_GATHER` / `_SHOCKSELE_GATHER` | 激波 cell 特殊处理（Te ≠ Ti 时） |

### 3.6 为什么 3T 有这么多模式

每个调用点需求不同：
- Hydro 之前要"快速 gather" → `_GATHER`
- AMR 重细化后要"完全重算" → `_RECAL_GATHER`
- 激波附近要"特殊处理" → `_SELE_GATHER`
- 初始化假设平衡 → `_EQUI`

**用户层**：大多数情况下不需要直接指定，parfile 写 `eosMode = "dens_ie_recal_gather"`（`+3t` 默认）就行。

---

## 4. 为什么需要 3T（三温）

### 4.1 1T 假设的问题

1T EOS 假设 **T_ion = T_ele = T_rad**（瞬间热平衡）。HEDP 中这假设**严重错**：

| Component | 加热机制 | 时间尺度 |
|---|---|---|
| **电子** | 激光逆韧致吸收（直接） | 飞秒 (fs) |
| **离子** | 电子-离子碰撞（间接） | 皮秒 (ps) |
| **辐射** | 韧致辐射发射 | 纳秒 (ns) |

3 个时间尺度差 **3+ 数量级**。在 ps 时间尺度上：
- 电子已被激光加热到几 keV
- 离子还冷（接近初始 T）
- 辐射更冷

假设平衡会：
- **误算电子压力**（实际 Te 高于平衡值）
- **误算不透明度**（依赖 Te，指数敏感）
- **误算激波结构**（依赖离子压力）

### 4.2 3T 模型

3T 解 **3 个独立能量方程**：

```
∂(ρe_ion)/∂t + ∇·F_ion = -λ_ie(T_ion - T_ele)         # 离子
∂(ρe_ele)/∂t + ∇·F_ele = -λ_ie(T_ele - T_ion)
                       -λ_er(T_ele - T_rad)
                       + S_laser                        # 电子（含激光源）
∂(ρe_rad)/∂t + ∇·F_rad = -λ_er(T_rad - T_ele)          # 辐射
```

`λ_ie`、`λ_er` 是耦合系数（由 **Heatexchange** 单元算）。

### 4.3 3T UNK 变量

| 变量 | 含义 |
|---|---|
| `TEION_VAR` | 离子温度 |
| `TELE_VAR` | 电子温度 |
| `TERAD_VAR` | 辐射温度 |
| `EION_VAR` | 离子内能 |
| `EELE_VAR` | 电子内能 |
| `ERAD_VAR` | 辐射内能 |
| `PION_VAR` / `PELE_VAR` / `PRAD_VAR` | 各 component 压力 |

Eos 在 3T 模式下读写这 9 个变量（而不是单一 TEMP_VAR/EINT_VAR/PRES_VAR）。

### 4.4 谁做平衡（重要）

**Eos 自己不做平衡**。Eos 只算"给定 (ρ, e_ion/e_ele/e_rad)，每个 component 的 (P, T)"。

**Heatexchange** 单元做平衡（`source/physics/sourceTerms/Heatexchange/`）：基于温度差和耦合系数，在 component 间转移能量。

`MODE_DENS_TEMP_EQUI` / `MODE_DENS_EI_EQUI` 模式**假设已平衡**（不是让 Eos 帮你平衡）。

---

## 5. Helmholtz EOS（HEDP 默认）

### 5.1 物理覆盖

Helmholtz（Timmes helmeos）含：

```
P_total = P_ion + P_electron + P_radiation + P_coulomb
e_total = e_ion + e_electron + e_radiation + e_coulomb
```

| Component | 模型 |
|---|---|
| **离子** | 理想气体（默认 γ=5/3），含可选 Coulomb 修正 |
| **电子** | **完全简并、任意相对论性 Fermi 气体**（从表插值） |
| **辐射** | 黑体光子气体（γ=4/3） |
| **Coulomb 修正** | 可选，由 `eos_coulombMult` 控制（默认 1.0） |

### 5.2 为什么 HEDP 必须 Helmholtz

ICF 内爆的 DT 燃料：
- 密度从 0.001 到 1000 g/cm³（压缩后）
- 温度从 1 eV 到 100 keV
- **电子达到简并**（Fermi 能 > kT）

简单理想气体在这种情况下压力偏差几个数量级。Helmholtz 表覆盖 **14 个数量级密度**（10⁻¹⁰ 到 10¹¹ g/cm³）和 **7 个数量级温度**（10⁴ 到 10¹¹ K）。

### 5.3 表结构

源码：`source/physics/Eos/EosMain/Helmholtz/helm_table.dat`（7.7 MB ASCII）+ `eos_helmData.F90:L51` + `eos_initHelmholtz.F90:L113-L200`

```
网格：211 × 71 = 14,985 个 (ρ, T) 点
密度轴：10^-10 到 10^11 g/cm³（log 等距，211 点）
温度轴：10^4 到 10^11 K（log 等距，71 点）

4 个表块：
  1. f（Helmholtz 自由能）+ 8 阶导数
  2. dpdf 族（压力对密度偏导）
  3. ef（电子化学势）
  4. xf（数密度）
```

### 5.4 加载流程

源码：`source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_initHelmholtz.F90`

```
Eos_init
└── PE0 读 helm_table.dat（ASCII，慢）
    └── 写 helm_table.bdat（二进制缓存，下次直接读）
└── 21 次 MPI_BCAST 广播到所有 PE
└── 后续 Eos 调用直接用内存中的表
```

**第一次启动慢**（读 7.7 MB ASCII），后续启动快（读 bdat）。

### 5.5 迭代 vs 直接（重要）

源码：`source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_helmholtz.F90:L215-L232`

```
dens_temp（MODE_DENS_TEMP） → 直接（表插值）
dens_ie（MODE_DENS_EI）     → Newton-Raphson 迭代
dens_pres（MODE_DENS_PRES） → Newton-Raphson 迭代
```

**为什么 dens_ie 是迭代**：表是 (ρ, T) 索引的。如果输入是 (ρ, e)，要找 T 让 e(T) = e_input，必须迭代。

### 5.6 Helmholtz 会修改输入（重要陷阱）

源码：`eos_helmholtz.F90:L228-L232`

```
对于 MODE_DENS_EI：输入 e 可能被修改（让 (ρ, T) 自洽）
对于 MODE_DENS_PRES：输入 P 可能被修改
```

**为什么**：Newton-Raphson 找到 T 后，重算 e(T) 可能和输入 e 略有不同。Helmholtz **默认用重算值替换输入**（保持热力学一致）。

**关闭**：`eos_forceConstantInput = .true.`。

---

## 6. Tabulated EOS（ionmix/sesame）

### 6.1 vs Helmholtz 的差别

| 属性 | Helmholtz | Tabulated |
|---|---|---|
| 物理内容 | 闭式等离子体（简并 + 解析离子 + 黑体辐射） | 实验或详细原子计算的 EOS |
| 物质依赖 | 通过 Multispecies 给 Abar/Zbar | 每物质单独表 |
| 电离状态 | 假设全电离，用 Abar/Zbar | 表内含电离演化 |
| 复杂原子（Fe、Au） | 不能 | 可以（壳层、压力电离） |
| 插值 | 双三次 | log-log 线性 |
| 成本 | 便宜（单表） | 贵（per-species 表查询） |

### 6.2 表格式

源码：`source/physics/Eos/EosMain/Tabulated/`

| 格式 | 扩展名 | 读取器 |
|---|---|---|
| **IONIX v4** | `.imx` | `eos_tabIonmix4.F90`（HDF5 风味，现代） |
| **IONIX v2** | `.imx` | `eos_tabIonmix.F90`（ASCII，老） |
| **SESAME** | (变) | `eos_tabReadSesameTables.F90`（LANL 格式） |
| **OPACPLOT** | `.h5` | `eos_tabReadOpacplotTables.F90`（HDF5） |

**默认附带表**：`h-100grp-lte.imx`、`be-100grp-lte.imx`、`n-100grp-lte.imx`（氢/铍/氮，100 群不透明度，LTE）。

### 6.3 何时用 Tabulated

- **部分电离的复杂物质**（Fe、Au、CH foam）→ Helmholtz 假设全电离会错
- **需要物质具体的压力电离、壳层结构**
- **和不透明度查询共用一张表**（避免双表）

### 6.4 配合 Helmholtz 用（Multitype）

3T Multitype 默认配置：
- **电子** → Helmholtz（电子简并）+ Tabulated（电离状态 Z(ρ,T)）
- **离子** → Tabulated（离子 EOS）
- **辐射** → 黑体（γ=4/3）

这就是"混合 EOS"——每个 component 用最合适的 EOS。

---

## 7. Eos 在何处被调用

### 7.1 7+ 个调用时机

| 时机 | 谁调 | 模式 | 为什么 |
|---|---|---|---|
| **初始化** | `Simulation_initBlock` 后 | `eosModeInit`（默认 dens_ie） | 让用户设的 (ρ, e) 自洽 |
| **guard cell 填充后** | `Grid_fillGuardCells` | `eosMode`（默认 dens_ie） | 插值的 guard cell 不自洽 |
| **Hydro 后** | `Hydro` | `hy_eosModeAfter` | 更新了 ENER_VAR，要重算 P, T |
| **sourceTerms 后** | 各 sourceTerm | dens_ie(_ele) 等 | 改了能量（如激光沉积到 EELE） |
| **Heatexchange 后** | Heatexchange | dens_ie（per-component） | 改了 EION/EELE/ERAD |
| **RadTrans 后** | RadTrans | dens_ie（_rad） | 改了 ERAD |
| **AMR refine 后** | `Grid_updateRefinement` | `dens_ie_recal_gather` | 新 block 的 cell 平均不自洽 |

### 7.2 为什么这么多调用

每次有单元修改了能量 / 密度 / 成分，**所有派生量（P, T, γ）都失效**。Eos 必须重算才能让下一步物理用对压力。

### 7.3 性能影响

| 变体 | 单次 Eos_wrapped（8³ block）耗时 |
|---|---|
| Gamma | 微秒 |
| Helmholtz | 毫秒（表插值） |
| Tabulated | 10+ 毫秒（per-species 查询） |
| 3T Multitype | 30+ 毫秒（Helmholtz + Tabulated 都跑） |

所以**减少冗余 Eos 调用**是性能优化重点（hence `MODE_EOS_NOP` / `MODE_EOS_WRAPPERONLY` / `_GATHER` vs `_ALL`）。

---

## 8. 与其他单元的耦合

### 8.1 上游（谁调 Eos）

- **Driver/Grid/Hydro/sourceTerms/RadTrans**：通过 `Eos_wrapped` 调
- **Heatexchange**：通过 `Eos`（直接 kernel，per-component 模式）
- **Opacity/Conductivity** 查询：通过 `Eos_getTempData`（只读温度）

### 8.2 下游（Eos 调谁）

- **Multispecies**：算 Abar/Zbar
- **RuntimeParameters**：读 eos_* 参数
- **Grid**：通过 `Grid_getBlkPtr` 拿 unk 指针
- **MPI**：广播表（Helmholtz 启动时）

### 8.3 边界

| Eos 不做 | 谁做 |
|---|---|
| 平衡 3T | Heatexchange |
| 时间步限制 | Heatexchange（基于耦合时间尺度） |
| 物理量演化 | Hydro / RadTrans / sourceTerms |
| 不透明度查询 | Opacity 单元（用 Eos 算的 T） |

---

## 9. 延伸阅读

- **参数完整字典**：`knowledge/params.md`
- **Eos_wrapped 内部流程**：`knowledge/internals.md`
- **典型配置**：`knowledge/recipes.md`
- **常见错误**：`knowledge/pitfalls.md`
- **Hydro 单元（怎么用 EOS 算的 P,T）**：`flash-hydro` skill
- **Heatexchange（3T 平衡）**：`flash-sourceterms`（Phase 2 后）
- **手册**：FLASH 4.8 User Guide §13-15（opencode 转写中）

---

## 10. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：10 段总览 + 6 变体对比 + EOS 模式系统（3 主模式 + 3T 扩展）+ 3T 设计动机 + Helmholtz 表机制 + Tabulated vs Helmholtz + 7+ 调用时机；按 L-011 重点讲"为什么"，按 L-012 公式用 ASCII | claude |
