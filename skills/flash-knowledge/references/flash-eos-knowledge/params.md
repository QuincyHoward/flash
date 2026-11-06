---
title: Eos 参数字典 — 主控 / 模式 / 截断 / Newton / Coulomb / 表 / 3T
skill: flash-eos
category: params
source_anchors:
  - source/Grid/GridMain/Config:L155-L185
  - source/physics/Eos/Config:L40-L91
  - source/physics/Eos/EosMain/Helmholtz/Config:L8-L34
  - source/physics/Eos/EosMain/Tabulated/Config:L4-L11
  - source/physics/Eos/EosMain/multiTemp/Config:L21-L53
manual_ref: "FLASH 4.8 User Guide §13-15"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - eos
  - parameter
  - helmholtz
  - 3t
  - mode
---

# Eos 参数字典

> **TL;DR**：~40 个 runtime parameter，按 8 类组织。**重要**：`eosMode` / `smalle` / `smallt` / `smlrho` 等不在 `physics/Eos/` Config，而在 **`source/Grid/GridMain/Config:L155-L185`**（Grid 单元也用它们填 guard cell）。每个参数给出**默认值依据**（按 L-011）。

---

## 0. 命名约定（重要）

**`eosMode` / `smalle` 等不归 Eos 单元管**，归 Grid。Eos 单元自己管的参数才有 `eos_` 前缀：

| parfile 参数 | 在哪声明 |
|---|---|
| `eosMode` / `eosModeInit` / `smalle` / `smallt` / `smlrho` / `smallx` | `source/Grid/GridMain/Config` |
| `eintSwitch` / `gamma` / `eos_singleSpeciesA/Z` / `eos_logLevel` | `source/physics/Eos/Config` |
| `eos_tolerance` / `eos_maxNewton` / `eos_coulombMult` / `eos_forceConstantInput` | `source/physics/Eos/EosMain/Helmholtz/Config` |
| `eos_useLogTables` / `eos_tabUseGeoSpace` | `source/physics/Eos/EosMain/Tabulated/Config` |
| `eos_smallEion` / `eos_smallEele` / `eos_smallErad` / `eos_combinedTempRule` | `source/physics/Eos/EosMain/multiTemp/Config` |

Hydro 单元也涉及 EOS 模式（`hy_eosModeGc` / `hy_eosModeAfter`）—— Hydro 调 Eos 时用哪个模式。

---

## 1. 主控参数（在 Grid!）

源码：`source/Grid/GridMain/Config:L155-L185`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eosMode` | STRING | `"dens_ie"`（`+3t` 时 `"dens_ie_recal_gather"`） | Hydro 后能量是守恒变量，从 e 算 P,T 最自然 |
| `eosModeInit` | STRING | `"dens_ie"` | 初始化后让 (ρ,e) 自洽。某些算例用 `"dens_temp"`（用户直接设 T） |
| `smalle` | REAL | 1.E-10 | 内能下限。实验室尺度默认；天体降到 1.E-30 |
| `smallt` | REAL | 1.E-10 | 温度下限 |
| `smlrho` | REAL | 1.E-10 | 密度下限（防 NaN） |
| `smallx` | REAL | 1.E-10 | 物种丰度下限 |

**为什么在 Grid**：Grid 填 guard cell 时也要调 Eos（让插值的 guard cell 自洽），所以 Grid 需要直接访问 eosMode。

---

## 2. Eos 单元顶层

源码：`source/physics/Eos/Config:L40-L91`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eintSwitch` | REAL | 0.0 | 0=关；>0 时如果 E_int < eintSwitch × E_kin，直接用 E_int = E_total - E_kin（防大数消去）。典型 0.1-1.0 |
| `gamma` | REAL | 1.6667 | 理想气体 γ（仅 Gamma 变体）。5/3 = 单原子，7/5 = 双原子 |
| `gammaA` / `gammaB` | REAL | 1.6667 | VoF 双流体 A/B 各自 γ |
| `eos_singleSpeciesA` | REAL | 1.0 | 单物质质量数 A（无 Multispecies 时） |
| `eos_singleSpeciesZ` | REAL | 1.0 | 单物质电荷数 Z |
| `eos_mfASpeciesA/Z` | REAL | 1.0 | VoF 流体 A 的 (A, Z) |
| `eos_mfBSpeciesA/Z` | REAL | 1.0 | VoF 流体 B 的 (A, Z) |
| `eos_logLevel` | INTEGER | 700 | 日志阈值（`EOS_LOGLEVEL_*` 见 Eos.h） |
| `eos_entrEleScaleChoice` | INTEGER | 6 | 电子熵公式变体（3 = Sackur-Tetrode） |
| `threadEosWithinBlock` | BOOLEAN | FALSE（+threadWithinBlock 时 TRUE） | block 内 OpenMP 并行 Eos 调用 |

---

## 3. Helmholtz 专属

源码：`source/physics/Eos/EosMain/Helmholtz/Config:L8-L34`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eos_coulombMult` | REAL | 1.0 | Coulomb 修正系数。0=关；1=正常修正。某些算例降到 0.5 避免负压 |
| `eos_tolerance` | REAL | 1.E-8 | Newton-Raphson 收敛容差（dens_ie / dens_pres 模式） |
| `eos_maxNewton` | INTEGER | 50 | 最大 Newton 迭代次数 |
| `eos_forceConstantInput` | BOOLEAN | FALSE | TRUE=不修改输入 e/P（关闭"自洽"反馈） |
| `eos_coulombAbort` | BOOLEAN | TRUE | TRUE=Coulomb 负压时 abort；FALSE=只警告 |
| `larget` | REAL | 1.E20 | 温度上限 bracket（仅 ExternalAbarZbar） |
| `eos_fluffDens` | REAL | 0.0 | 低密度阈值（仅 ExternalAbarZbar） |

### 3.1 Helmholtz 子变体专属

源码：`source/physics/Eos/EosMain/Helmholtz/SpeciesBased/Config`

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `eos_singleSpeciesA/Z` | REAL | 1.0 | 同顶层（仅 SpeciesBase 无 Multispecies 时） |

### 3.2 表文件

| 文件 | 路径 | 大小 |
|---|---|---|
| `helm_table.dat` | `source/physics/Eos/EosMain/Helmholtz/helm_table.dat` | 7.7 MB ASCII |
| `helm_table.bdat` | （运行时生成） | 二进制缓存 |

第一次启动 PE0 读 .dat → 写 .bdat → 后续直接读 .bdat → MPI_BCAST 广播。

**注意**：`.bdat` 是 architecture-specific，**不能跨机器拷贝**（endian、float size 可能不同）。

---

## 4. Tabulated 专属

源码：`source/physics/Eos/EosMain/Tabulated/Config:L4-L11`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eos_useLogTables` | BOOLEAN | TRUE | 表存 log 值（数值范围大时必须） |
| `eos_tabUseGeoSpace` | BOOLEAN | TRUE | (ρ,T) 网格用 log 等距（geometric）；FALSE=线性 |

### 4.1 表文件（DATAFILES）

源码：`source/physics/Eos/EosMain/Tabulated/Config:L11`

默认附带的 ionmix 表：
- `h-100grp-lte.imx`（氢，100 群 LTE）
- `be-100grp-lte.imx`（铍）
- `n-100grp-lte.imx`（氮）

**加自己的表**：在算例 Config 文件加 `DATAFILES mytable.imx`，setup 自动拷贝到 objdir。

---

## 5. multiTemp 专属

源码：`source/physics/Eos/EosMain/multiTemp/Config:L21-L53`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eint1Switch` / `eint2Switch` / `eint3Switch` | REAL | -1.0 | **OBSOLETE**。-1=继承 `eintSwitch` |
| `eos_combinedTempRule` | INTEGER | -10 | 3T 输出时 `EOS_TEMP` 放什么：-10=未定义；0=平衡 T（贵）；1=ion；2=ele；3=rad |
| `eos_smallEion` | REAL | 0.0 | 离子内能下限 |
| `eos_smallEele` | REAL | 0.0 | 电子内能下限 |
| `eos_smallErad` | REAL | 0.0 | 辐射内能下限 |

### 5.1 诊断变量（UNK VARIABLE，不是 PARAMETER）

| 变量 | 含义 |
|---|---|
| `TITE` | T_ion / T_ele 比值（`Config:L52`） |
| `PIPE` | P_ion / P_ele 比值（`Config:L53`） |
| `TRTE` | T_rad / T_ele 比值（`multiTemp/Gamma/Config:L7`） |
| `PRPE` | P_rad / P_ele 比值（`multiTemp/Gamma/Config:L8`） |

这些是 Eos 写入 unk 的诊断变量，可在 plotfile 中查看（debug 3T 平衡）。

---

## 6. Multitype（3T 混合）专属

源码：`source/physics/Eos/EosMain/multiTemp/Multitype/Config:L13-L30`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eos_tolerance` | REAL | 1.E-8 | 同 Helmholtz |
| `eos_maxNewton` | INTEGER | 50 | 同 Helmholtz |
| `eos_forceConstantInput` | BOOLEAN | FALSE | 同 Helmholtz |
| `eos_largeT` | REAL | 1.E14 | 温度上限 bracket（K） |
| `eos_maxFactorUp` | REAL | 1.5848932 | 单步 T 增加上限（约 1.6×） |
| `eos_maxFactorDown` | REAL | 0.6309573 | 单步 T 减少下限（约 0.63×） |

**为什么限制单步 T 变化**：避免 Newton 迭代跨表外推或数值震荡。

---

## 7. Per-component gamma（3T）

源码：`source/physics/Eos/EosMain/multiTemp/Gamma/Config`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `gammaIon` | REAL | 1.6667 | 离子 γ（单原子理想气体 5/3） |
| `gammaEle` | REAL | 1.6667 | 电子 γ（电子气体近似 5/3） |
| `gammaRad` | REAL | 1.3333 | 辐射 γ（黑体光子气体 4/3） |

**为什么辐射 γ=4/3**：黑体辐射压 P = aT⁴/3，内能密度 u = aT⁴，所以 γ = P/(uρ) + 1 = ... 实际推导得 γ_rad = 4/3。

---

## 8. EosNuclear（核 EOS，核坍缩超新星）

源码：`source/physics/Eos/EosNuclear/Config:L17-L23`

| 参数 | 类型 | 默认 | 默认值依据 |
|---|---|---|---|
| `eos_file` | STRING | `"myshen_test_220r_180t_50y_extT_analmu_20100322_SVNr28.h5"` | stellarcollapse.org 的 Shen 表（HDF5） |
| `postBounce` | BOOLEAN | FALSE | 是否进入反弹后阶段 |
| `bounceTime` | REAL | 0.0 | 反弹时刻（s） |

**只用于核坍缩超新星**。普通算例不要用。

---

## 9. Hydro 单元的 EOS 相关参数

源码：`source/physics/Hydro/HydroMain/unsplit/Config:L199-L201`

| 参数 | 类型 | 默认 | 含义 |
|---|---|---|---|
| `hy_eosModeGc` | STRING | `"see eosMode"` | Hydro guard cell 填充时用的 EOS 模式（默认跟 eosMode） |
| `hy_eosModeAfter` | STRING | `"dens_ie"` | Hydro sweep 结束后 EOS 模式 |

**为什么 Hydro 单独有这俩**：某些算例需要 Hydro 用和全局不同的 EOS 模式（如 guard cell 用 dens_temp 避免 Newton 迭代）。

---

## 10. 参数前缀速查

| 前缀 | 含义 | 出处 |
|---|---|---|
| `eosMode` / `eosModeInit` / `smalle` / `smallt` / `smlrho` | 主控（**无 eos_ 前缀**，在 Grid） | `GridMain/Config` |
| `eintSwitch` / `gamma` | Eos 顶层（**无 eos_ 前缀**） | `physics/Eos/Config` |
| `eos_` | Eos 单元模块变量 / 子模块参数 | 各 Config |
| `hy_eosMode*` | Hydro 单元的 EOS 模式覆盖 | `HydroMain/unsplit/Config` |

---

## 11. 延伸阅读

- **Eos 总览**：`knowledge/overview.md`
- **Eos_wrapped 流程**：`knowledge/internals.md`
- **典型配置**：`knowledge/recipes.md`
- **常见错误**：`knowledge/pitfalls.md`
- **跨单元查参数**：`flash-param-query` skill + `skills/flash-param-query/knowledge/param-index.md`

---

## 12. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：10 类参数 + 默认值依据（按 L-011）+ 命名约定（eosMode 在 Grid！）+ 前缀速查 | claude |
