# gen_eos_op / eosop_pro —— 支持数据类型与单位溯源清单

> **文档定位**: 回答两个问题 ——
> (1) `eosop_pro` 当前能处理**哪些类型**的数据文件；
> (2) 这些文件的数据**各对应什么单位**，且每个单位**必须给出可核对的文档/源码出处**。
>
> **编制日期**: 2026-09-14
> **编制依据**: 全部为**本地可核对的**文件 —— 源码、用户指南、解析器实现三者交叉。
> **纪律**: 凡无法从本地文档/源码唯一确定的，一律标 **`unknown`**，不猜。
>
> **验证状态**: 全套测试 `30 files / all passed`（`test/run_all.py`）。

---

## 0. 阅读须知 —— 本文档的单位判断规则

单位来源分五个等级，**等级越高越权威**，解析器实现中的 `unit_source` 字段即记录此等级：

| 等级 | 记号 | 含义 | 可信度 |
|---|---|---|---|
| L1 | `format:` | 由**写出该格式的源码/程序手册**确定 | 最高 |
| L2 | `declared:` | 数据文件**自身内嵌**的单位声明（表头/注释行） | 高 |
| L3 | `default:` | 程序约定默认值，文件未声明时采用 | 中（须注明） |
| L4 | `inferred` | 由物理量量纲/赋值表达式反推 | 中（须注明推导） |
| L5 | `none` / `unknown` | **无任何依据 → 标 unknown，不使用** | — |

⚠️ **关键原则**: 同一物理量在不同族里单位可能不同（如 T 在 F1 是 eV、
在 F5 LEDCOP 是 keV），**跨族比较前必须换算**。

---

## 1. 支持的格式族总览（共 6 族 / 17 个声明族）

分派逻辑见 `eosop_pro/registry/dispatch.py` 的 `FAMILY_PARSERS`，
扩展名映射见 `eosop_pro/registry/declared_types.py`。

| 族 | 声明族名 | 解析器模块 | 主要触发扩展名 | 典型内容 |
|---|---|---|---|---|
| **F1** | `multi_inverted_eos` | `parsers/multi_inverted_eos.py` | `.dat` / `.sesame` / `.301/.304/.305` | MULTI 反演 EOS 表 |
| **F2** | `multi_opacity` | `parsers/multi_opacity.py` | `.dat` / `.opac` / `.zeff` | MULTI 不透明度 / Zeff / NLTE |
| **F3** | `hyades_eos` | `parsers/hyades_eos.py` | 路径含 `hyades`；`.sesame` | Hyades 5×15 布局 |
| **F3** | `hyades_opacity` | `parsers/hyades_eos.py` | 同上 | Hyades 不透明度 |
| **F3** | `sesame_dat` | `parsers/hyades_eos.py` | `.sesame` / 默认回退 | SESAME 库格式 |
| **F4** | `mpqeos` | `parsers/mpqeos.py` | `.tabular` / MPQ 标记 | MPQeos 表（GPa / MJ/kg） |
| **F4** | `feos_native` | `parsers/feos_native.py` | `.feos`（原生 10 数表头） | FEOS 工具原生输出 |
| **F4** | `feos_tabdata` | `parsers/feos_tabdata.py` | `*.data.txt` | FEOS tab 数据 |
| **F4** | `feos_aux` | `parsers/feos_aux.py` | `.par` / `.cst` / `.mexport` / `.critical.dat` / `.isobaric.dat` | FEOS 辅助参数 |
| **F5** | `ledcop_atomic` | `parsers/ledcop_atomic.py` | `ATOMIC/*.txt` | LEDCOP 原子表 |
| **F5** | `ledcop_zeff` | `parsers/ledcop_zeff.py` | `*.ZEFF` / `*.Z` / `*_MG` | LEDCOP 平均电离度 |
| **F6** | `ionmix` | `parsers/ionmix.py` | **`.cn4` / `.cnr`** | IONMIX EOS+不透明度 |
| **F6** | `coldopacity` | `parsers/coldopacity.py` | `.coldopacity` / `GRAYOPACITY` | 冷/灰不透明度 |
| **F6** | `hugoniot` | `parsers/hugoniot.py` | `.hug` / 注释列头 | 雨贡纽曲线 |
| **F6** | `snop_input` | `parsers/snop_input.py` | `.snop` | SNOP 输入表 |
| **F6** | `generic_curve` | `parsers/generic_curve.py` | 兜底（无声明命中时） | 通用曲线（**单位 unknown**） |

**特殊回退规则**: `.feos` 的候选顺序是 `[feos_native, multi_inverted_eos]`。
实测 `mat_Al-1.0/AL_eos.feos` 与 `AL_eos` **字节相同**（名为 FEOS、实为 SESAME），
故会回退到 F1。这是**按声明候选顺序尝试**，不是猜测，且完整记录在
`ParseSnapshot.dispatch_rule`。

---

## 2. 逐族单位溯源表

### F1 —— `multi_inverted_eos`（MULTI 反演 EOS）

| 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 `format:` | `parsers/multi_inverted_eos.py:235`，`unit_source = "format:F1"` |
| `de`（比内能轴） | `Mbar*cm3/g` | L1 | 同上 `:239` |
| `P`（压力） | `Mbar` | L1 | 同上 `:244` |
| `e0_cold`（冷能） | `Mbar*cm3/g` | L1 | 同上 `:252` |
| `E`（比内能） | `Mbar*cm3/g` | L1 | 同上 `:258` |
| `T`（温度） | `eV` | L1 | 同上 `:263`。**原始文件为 Kelvin，解析器转 eV** |
| `de_energy` | `Mbar*cm3/g` | L1 | 同上 `:268` |

**注意**: `T` 的**文件内原始单位是 Kelvin**，`eV` 是解析器换算后的结果。
换算依据见 `unit_source` 字段（`T Kelvin->eV`）。

### F2 —— `multi_opacity`（不透明度 / Zeff / NLTE）

| 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 | `parsers/multi_opacity.py:342` |
| `Te`（温度轴） | `eV` | L1/L3 | 同上 `:345`；`unit_source` 为 `declared:<hint>` 或 `default:eV` |
| `kappa_*`（不透明度） | `cm2/g` | L1 | 同上 `:361` |
| 非 `kappa` 类字段（Zeff 等） | `1`（无量纲） | L1 | 同上 `:361` |

⚠️ **重要告警**（`multi_opacity.py:380`）: ZEFF 表存在 **eV / keV 两套**，
必须由文件注释声明。未声明时回退 `default:eV` 并**在 `unit_source` 中显式标注**。

### F3 —— `hyades_eos` / `hyades_opacity` / `sesame_dat`

| 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 | `parsers/hyades_eos.py:173` |
| `Te`（温度轴） | `eV`（文件为 keV，转 eV） | L1 | 同上 `:175,177`（`{"kev":1e3,"ev":1.0}`） |
| `kappa` / 不透明度类 | `cm2/g` | L1 | 同上 `:189` |
| `P`（压力） | `dyne/cm2` | L1 | 同上 `:195` |
| `E`（比内能） | `erg/g` | L1 | 同上 `:199` |
| `raw_tail`（尾部残余） | **`unknown`** | L5 | 同上 `:216` —— 无文档，**不猜** |

**注意**: 本族是 **CGS 原生**（`dyne/cm2` / `erg/g`），与 F1/F4 的 `Mbar` 体系不同。

### F4 —— `mpqeos`

| 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 | `parsers/mpqeos.py:108` |
| `Te`（温度轴） | `eV`（文件为 Kelvin，转 eV） | L1 | 同上 `:111` |
| `P`（压力） | `Mbar`（文件为 GPa，转 Mbar） | L1 | 同上 `:117`，`unit_source` 明写 `GPa->Mbar` |
| `E`（比内能） | `Mbar*cm3/g`（文件为 MJ/kg） | L1 | 同上 `:122`，明写 `MJ/kg->Mbar*cm3/g` |
| `Z`（平均电离度） | `1`（无量纲） | L1 | 同上 `:127` |

### F4 —— `feos_native` / `feos_tabdata` / `feos_aux`

| 族 | 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|---|
| `feos_native` | `rho` | `g/cm3` | L1 | `parsers/feos_native.py:106` |
| `feos_native` | `Te` | `eV` | L1 | 同上 `:109` |
| `feos_native` | `raw_values` | **`unknown`** | L5 | 同上 `:118` |
| `feos_tabdata` | 全部列 | **`unknown`** | L5 | `parsers/feos_tabdata.py:76,80` —— 明写"列语义无本地文档" |
| `feos_aux` | `raw_values` | **`unknown`** | L5 | `parsers/feos_aux.py:78,80` —— 辅助参数文件 |

`feos_native` 整体 `unit_source = "format:FEOS (cgs + eV)"`（`feos_native.py:140`）。

### F5 —— `ledcop_atomic` / `ledcop_zeff`

| 族 | 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|---|
| `ledcop_atomic` | `rho` | `g/cm3` | L1 | `parsers/ledcop_atomic.py:201` |
| `ledcop_atomic` | `Te` | `eV`（文件默认 keV，转 eV） | **L2** | 同上 `:174,204`；`unit_source = "declared:<unit> (文件内嵌单位行)"` |
| `ledcop_atomic` | `Ross` / `Planck` | `cm2/g` | L2 | 同上 `:212` |
| `ledcop_atomic` | 其他场 | `1`（无量纲） | L2 | 同上 `:212` |
| `ledcop_zeff` | `rho` | `g/cm3` | L1 | `parsers/ledcop_zeff.py:90` |
| `ledcop_zeff` | `Te` | `eV`（默认 keV） | L3 | 同上 `:92,95,103`：`format:T in keV` |
| `ledcop_zeff` | Zeff 场 | `1`（无量纲） | L1 | 同上 `:100` |

⚠️ **LEDCOP 的 T 单位是 keV 而非 eV**（`ledcop_zeff.py:103`），
且 `test_zeff_registry.py::test_ledcop_split_tables_are_keV` 与
`test_thermos_zeff_is_keV_and_z_is_eV_by_declaration` 专门守护这一区别
（另有 `.Z` 文件声明为 **eV**）。**跨族比较前必须统一**。

### F6 —— `ionmix`（`.cn4` / `.cnr`）—— 本族是本次合并的重点

本族有**两种互斥的 CONRAD 家族格式**，同出 `abjt_03.f` 的 `SUBROUTINE OWTF`
（line 4510），但走**不同分支、不同 fortran unit、不同扩展名**：

| 格式 | 源码分支 | 源码行 | unit | 块数 | 含 EOS 场 |
|---|---|---|---|---|---|
| `.cn4` | `isw(21) != 0` | 4662–4743 | 123 | 18 | ✅ 完整 |
| `.cnr` | `isw(8) = 1/12/13`（late-1986 CONRAD） | 4598–4621 | 8 | 7 | ❌ 无 |

#### F6 / `.cn4` —— 逐块单位（**全部 L1，源码逐行可核**）

权威出处: `src/Ionmix/abjt_03.f` `SUBROUTINE OWTF` `isw(21)!=0` 分支，
以及 `ionmix/ionmix/docs/IONMIX用户指南.md` §5.4。

| # | 量 | 形状 | 单位 | 源码行 | 单位依据 |
|---|---|---|---|---|---|
| 1 | `tplsma`（温度轴） | `ntemp` | **eV** | — | 源码注释 `write the temperature points (in ev)` |
| 2 | `densnn`（密度轴） | `ndens` | **cm^-3** | — | 源码注释 `write the number density points (in cm^-3)`（**核子数密度，非质量密度**） |
| 3 | `zbar` = ne/nion | `ntemp*ndens` | `-`（无量纲） | 4687 | 量定义 |
| 4 | `dzdt` | `ntemp*ndens` | `1/eV` | 4691 | `owtf` 入参说明块 line 4519 |
| 5 | `p_ion`（离子压） | `ntemp*ndens` | **J/cm3** | 4693 | 赋值式 `densnn*tplsma*1.602E-19`：`cm^-3 · eV · J/eV`（**L4 推导，依据明确**） |
| 6 | `p_ele`（电子压） | `ntemp*ndens` | **J/cm3** | 4696 | 同上，`densne*tplsma*1.602E-19` |
| 7 | `dpion_dt` | `ntemp*ndens` | **J/cm3/eV** | 4699 | 源码注释 `write the d(pion)/dT (in Joules/cm^3/eV)` |
| 8 | `dpele_dt` | `ntemp*ndens` | **J/cm3/eV** | 4702 | 同构注释 |
| 9 | `e_ion` | `ntemp*ndens` | **J/g** | 4706 | `owtf` 入参说明: `enrgyion - specific energies (J/g)` |
| 10 | `e_ele` | `ntemp*ndens` | **J/g** | 4708 | 同上 |
| 11 | `cv_ion` | `ntemp*ndens` | **J/g/eV** | 4711 | 入参说明 `heatcpion (J/g/eV)` |
| 12 | `cv_ele` | `ntemp*ndens` | **J/g/eV** | 4713 | 同上 |
| 13 | `deion_dn` | `ntemp*ndens` | **`unknown`** | 4718 | ⚠️ **源码自身注释 `(not sure)`** → 标 unknown |
| 14 | `deele_dn` | `ntemp*ndens` | **`unknown`** | 4723 | ⚠️ 同上，源码注 `(not sure)` |
| 15 | `engrup`（能群边界） | `ngrups+1` | **eV** | — | `opacs` common 注释: `engrup` 为光子能量边界 |
| 16 | `opac_rosseland` | `ngrups*ntemp*ndens` | **cm2/g** | 4733 | 入参说明 `orm - Rosseland mean opacities (cm^2/g)` |
| 17 | `opac_planck_abs` | `ngrups*ntemp*ndens` | **cm2/g** | 4736 | 入参说明 `opm - Planck mean opacities (cm^2/g)` |
| 18 | `opac_planck_ems` | `ngrups*ntemp*ndens` | **cm2/g** | 4739 | 同上 |

> ⚠️ **第 13/14 块是唯一的两处 `unknown`**，原因：源码 line 4715/4720 自身
> 注释为 `(not sure)`，且写出量经过 `condd = -6.242e18*avgatw/avgdro` 换算，
> 量纲**无法从源码独立确认**。已在代码中以
> `eosop_pro.cn4.units.UNCERTAIN_UNITS` 显式登记，并由
> `test_ionmix.py::test_cn4_unknown_units_declared` 守护。

> ⚠️ **`densnn` 是核子（离子）数密度 cm^-3，不是质量密度 g/cm³**。
> 转 `rho` 需乘平均原子量 `<A>`: `rho = n_ion · <A> / N_A`，
> 依据 `IONMIX用户指南.md` §5.1 `Mass density` 行。
> `<A>` 的权威来源是同目录 `ionmxinp`；原子量缺失时解析器**不给 rho**（不猜）。

#### F6 / `.cnr` —— 逐块单位（legacy，**指南未文档化**）

⚠️ **`IONMIX用户指南.md` 全文检索 "cnr" 零命中** —— 该格式**只有源码一个依据**。

| # | 量 | 形状 | 单位 | 源码行 | 依据 |
|---|---|---|---|---|---|
| 1 | `zbar` = ne/nion | `ntemp*ndens` | `-` | 4602 | 量定义（同 `.cn4`） |
| 2 | `enrgy` | `ntemp*ndens` | **J/g** | 4604 | `owtf` 入参说明 `enrgy (J/g)` |
| 3 | `op2tr`（2-T Rosseland） | `ntrad*ntemp*ndens` | **cm2/g** | 4605 | 入参说明 `op2tr` 为 cm^2/g |
| 4 | `op2tp`（2-T Planck） | `ntrad*ntemp*ndens` | **cm2/g** | 4607 | 同上 |
| 5 | `engrup`（能群边界） | `ngrups+1` | **eV** | 4609 | `opacs` common |
| 6 | `orgp`（群 Rosseland） | `ngrups*ntemp*ndens` | **cm2/g** | 4611 | 入参说明 `orgp (cm^2/g)` |
| 7 | `opgpe`（群 Planck 发射） | `ngrups*ntemp*ndens` | **cm2/g** | 4613 | 入参说明 `opgpe (cm^2/g)` |
| H | 头部 4 个网格参数 | `4` | **`inferred`** | 4609 附近 | `(dlgden, log10(rho0), dlgtmp, log10(T0))` —— **指南未文档化 → 标 inferred** |

**`.cnr` 的头部与 `.cn4` 根本不同**（这是本次排查的关键发现）:

| | `.cn4` | `.cnr` |
|---|---|---|
| 第 4 行格式 | `982 format (i12)` | `981 format (4e12.6,i12)` |
| `ngrups` 位置 | **独占一行** | 与 4 个网格参数**同行**，在末尾 12 列 |
| 实测 | `          10` | `0.250000E+000.190000E+020.250000E+000.000000E+00          30` |

**`.cnr` 的 `ntrad` 不在头部存储**，必须由**计数守恒反解**:

```
rem   = N - [ 2*ntemp*ndens + (ngrups+1) + 2*ngrups*ntemp*ndens ]
ntrad = rem / (2*ntemp*ndens)
```

本仓库 8 个 `.cnr` 的实测结果（`parse_cnr` 全部 8/8 通过）:

| 文件 | ntemp | ndens | ngrups | ntrad 反解 | 状态 |
|---|---|---|---|---|---|
| `n-100grp-lte.cnr` | 1 | 1 | 100 | **51** | OK |
| `o-100grp-lte.cnr` | 20 | 20 | 100 | **51** | OK |
| `h-100grp-lte.cnr` | 30 | 5 | 100 | **51** | OK |
| `be-100grp-lte.cnr` | 20 | 10 | 100 | **51** | OK |
| `xe-100grp-lte.cnr` | 20 | 10 | 100 | **51** | OK |
| `al-imx-001.cnr` | 21 | 21 | 30 | **16** | OK |
| `helium-imx-002.cnr` | 21 | 17 | 30 | **16** | OK |
| `xe-005grp-lte.cnr` | 17 | 13 | 5 | **无法整除 → None** | `op2tr`/`op2tp` 标 **unknown** |

> ✅ **诚实边界**: `xe-005grp-lte.cnr` 的余数不被 `2*ntemp*ndens` 整除，
> 切分点**无法唯一确定** → `op2tr`/`op2tp` 标 `unknown`，**不伪造偏移**；
> 但 `engrup`/`orgp`/`opgpe` 仍从文件尾部**反向定位**成功。

> ✅ **`.cnr` 的固有限制**: 它**不含** `.cn4` 的 12 个 EOS 二维场
> （压力/比热/离子电子分量）。因此 `.cnr` **不能**用于 EOS 路径分析
> （等温/等压/等熵/雨贡纽/声速），也**不能**直接转 `.cn4`。
> 解析器在 `notes` 中显式声明这一局限，并由
> `test_ionmix.py::test_cnr_legacy_variant_parsed` 守护。

#### F6 / ionmix —— 头部格式语句对照（源码 line 4749–4755）

```fortran
  921 format (' atomic #s of gases: ',5i10)     ! 组分元素原子序数
  922 format (' relative fractions: ',1p5e10.2) ! 数分数（注意是 1p5e10.2，非 e12.6）
  923 format (2i10)                             ! ntemp, ndens
  980 format (a80)                              ! 80 字符串
  981 format (4e12.6,i12)                       ! .cnr 头部（4 网格参数 + ngrups）
  982 format (i12)                              ! .cn4 头部（ngrups 独占行）
  991 format (4e12.6)                           ! 所有数据区
```

#### ⚠️ F6 ionmix —— Fortran `E12.6` 字段溢出缺陷（**实测，非猜测**）

`E12.6` 只能容纳 `0.ddddddE±ee` = **12 列**。当指数为 **3 位数**且尾数无
前导空格时（值 `0.ddddddE-140`）需 **13 列**，Fortran 运行时**静默丢掉 `E`**，
写出 `0.638380-140`。

**实证**（`Ionmix/h-imx-1grp.cn4`，`ntemp=17, ndens=21, ngrups=1`）:

| 检查项 | 结果 |
|---|---|
| 期望数值数 | **5395** |
| 严格 12 列切分 token 数 | **5395** ✅ 计数本就闭合 |
| 匹配打包指数模式的 token | **89** 个（`0.638380-140` … `0.201874-144`） |
| 修复后数值数 | **5395** ✅ 不变 |
| 修复后量级 | `1e-140`，正是该表压力/不透明度区的物理合理量级 |

**修复规则**（已在 `cn4_io.py::_PACKED_EXP_RE` 实现并注释）:

```
(\d\.\d{6})([-+]\d{3})   →   \1E\2
```

---

### F6 —— `coldopacity` / `hugoniot` / `snop_input` / `generic_curve`

| 族 | 量 | 单位 | 等级 | 权威出处 |
|---|---|---|---|---|
| `coldopacity` | 全部列 | **由文件 2 行头内嵌声明** | L2 | `parsers/coldopacity.py:84,89,91`：`unit_source = "declared:inline (2-line header)"` |
| `hugoniot` | 全部列 | **由注释列头内嵌声明** | L2 | `parsers/hugoniot.py:103,107,110`：`unit_source = "declared:inline (comment column header)"` |
| `snop_input` | `T1`,`T2`,`X1`,`X2` | **keV** | L1 | `parsers/snop_input.py:35-36` |
| `snop_input` | `FG` | **eV** | L1 | 同上 `:37` |
| `snop_input` | 整体 | — | L1 | `unit_source = "declared:doc/SNOP.MANUAL"`（`snop_input.py:106`） |
| `generic_curve` | `x` 轴 / 全部场 | **`unknown`** | L5 | `parsers/generic_curve.py:80,86,89`：`"none（列语义无文档 → 不猜测）"` |

⚠️ `coldopacity` / `hugoniot` 的单位**不在代码里硬编码**，而是从文件自身
头部/注释**读出**——这是设计使然（不同实例可能用不同单位），
但若文件未声明，解析器不给单位（`unit_source` 会显示实际来源）。

---

## 3. 跨族单位差异速查（**做跨族比较前必读**）

| 物理量 | F1 MULTI | F2 MULTI-opac | F3 Hyades | F4 MPQeos | F5 LEDCOP | F6 IONMIX |
|---|---|---|---|---|---|---|
| 温度 T | eV（原 K） | eV（或 eV/keV 双套⚠️） | eV（原 keV） | eV（原 K） | **keV**⚠️ | **eV** |
| 密度 | `g/cm3` | `g/cm3` | `g/cm3` | `g/cm3` | `g/cm3` | **`cm^-3`（数密度）**⚠️ |
| 压力 P | `Mbar` | — | **`dyne/cm2`** | `Mbar`（原 GPa） | — | **`J/cm3`** |
| 比内能 E | `Mbar*cm3/g` | — | **`erg/g`** | `Mbar*cm3/g`（原 MJ/kg） | — | **`J/g`** |
| 不透明度 | — | `cm2/g` | `cm2/g` | — | `cm2/g` | `cm2/g` |

**三处最容易踩的坑**:

1. **F6 ionmix 的密度轴是 `cm^-3` 数密度**，其余族都是 `g/cm3` ——
   混用会得到量级完全错误的结果。
2. **F5 LEDCOP 的温度是 keV**，其余族（换算后）是 eV ——
   差 1000 倍。
3. **F6 ionmix 的 P/E 是 SI 派生的 `J/cm3` / `J/g`**，
   与 F1/F4 的 `Mbar` / `Mbar*cm3/g` 及 F3 的 CGS `dyne/cm2` / `erg/g` 都不同。

统一换算因子（含完整推导链）集中在
`eosop_pro/cn4/units.py`，并在 `DISPLAY_UNITS` / `RAW_UNITS` /
`RAW_UNIT_EVIDENCE` 三个字典中区分"文件原始单位"与"显示单位"。

---

## 4. 其他类型 eosop 数据 → `.cn4` 的转换桥梁

用户后续需求: **把其他类型的 eosop 数据转为 `.cn4` 格式**。

**唯一入口**: `eosop_pro.cn4.cn4_io.parsed_tables_to_cn4`

```
其他格式文件 → [各族 parser] → ParsedTable → parsed_tables_to_cn4() → .cn4 文件
```

* 反方向: `cn4_to_parsed_tables()` 把 1 张 cn4 总表拆成 4 张 `ParsedTable`
  （1 张 EOS + 3 张不透明度），便于**按族**喂给 `parsed_tables_to_cn4`。
* 已验证: `cn4 → ParsedTable → cn4` **byte-identical**（无损往返）。
* `write_cn4` 与 `Ti-BADGER-TOPS.cn4`（2230155 字节）**逐字节相同**。
* 单位纪律: `parsed_tables_to_cn4` 要求输入表带 `field_units`；
  单位不匹配时会**拒绝或显式警告**，不会静默按错误单位写。

⚠️ **`.cnr` 不能作为来源**: 它缺 12 个 EOS 场，无法补齐 cn4 的必需块。

---

## 5. `unknown` 清单（**诚实汇总，共 5 处**）

| 位置 | 量 | 为何 unknown |
|---|---|---|
| F6 `.cn4` block 13 | `deion_dn` | 源码自身注 `(not sure)`（`abjt_03.f:4715`），量纲无法独立确认 |
| F6 `.cn4` block 14 | `deele_dn` | 同上（`abjt_03.f:4720`） |
| F4 `feos_tabdata` | 全部列 | 列语义无本地文档（`feos_tabdata.py:80`） |
| F4 `feos_aux` | `raw_values` | 辅助参数文件，语义无文档（`feos_aux.py:80`） |
| F3 `hyades_eos` | `raw_tail` | 尾部残余无文档（`hyades_eos.py:216`） |
| F6 `generic_curve` | 全部列 | 无声明命中时的兜底，列语义无文档（`generic_curve.py:89`） |
| F6 `.cnr`（`xe-005grp-lte`） | `op2tr` / `op2tp` | `ntrad` 反解不整除，切分点不唯一 |

另有一处 **`inferred`**（非 unknown，但须注明）:
F6 `.cnr` 头部 4 个网格参数 —— 物理含义由源码 `write` 语句位置推断，
IONMIX 用户指南未文档化该格式。

---

## 6. 结论

1. **支持 6 大格式族 / 17 个声明族**，覆盖 MULTI、Hyades/SESAME、MPQeos、
   FEOS、LEDCOP、IONMIX 及若干辅助格式，分派逻辑全在
   `registry/dispatch.py` + `registry/declared_types.py`。
2. **每一个非 unknown 的单位都有可核对出处**（源码行号 或 用户指南章节 或
   文件内嵌声明），代码中以 `unit_source` 字段与
   `cn4/units.py::RAW_UNIT_EVIDENCE` 逐项登记。
3. **IONMIX 是本项目单位最"特殊"的一族** —— 密度用数密度、压力/能量用 SI 派生，
   且 `.cn4` 与 `.cnr` 是两种不同格式，必须按扩展名分派。
4. **`unknown` 共 7 处，全部显式标注**（含 `.cnr` 的 2 处不可唯一切分的块），
   无一处靠猜测填充。
5. **`.cn4` 是后续"其他格式 → cn4"转换的目标格式**，入口为
   `parsed_tables_to_cn4`，且已验证往返无损。
