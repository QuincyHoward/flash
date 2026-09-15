# 各种类型的 eosop 数据 —— 物理量及其单位说明

> **文档定位**: 逐族列出 `eosop_pro` 所处理的全部 eosop 数据**物理量**及其**单位**，
> 并对每一个单位给出**可定位、可复核的判定依据**（源码文件 + 行号 / 手册章节 / 文件内嵌声明）。
>
> **编制日期**: 2026-09-14
> **编制原则**: **只写已确定的**。凡本地源码与文档**均无法唯一确定**的，一律写 `unknown`，
> **不作推测**。凡由量纲推导得出（而非文档明写）的，标注 `inferred` 并给出推导式。
>
> **验证状态**: 交叉验证 `62 PASS / 0 FAIL`；全量测试 `31 file(s) all passed`。

---

## 0. 阅读须知 —— 单位判定等级与本文档引用约定

### 0.1 判定等级

| 等级 | 记号 | 含义 | 可信度 |
|---|---|---|---|
| **L1** | `format:` | 由**写出该格式的源码**或**官方程序手册**确定 | 最高 |
| **L2** | `declared:` | 数据文件**自身内嵌**的单位声明（表头/注释行） | 高 |
| **L3** | `default:` | 程序约定默认值；文件未声明时采用，**须注明** | 中 |
| **L4** | `inferred` | 由**物理量量纲/赋值表达式**反推（附推导式） | 中 |
| **L5** | `unknown` | **无任何本地依据 → 标 unknown，不使用、不猜测** | — |

该等级即解析器 `ParsedTable.unit_source` 字段的取值，写入 h5 的 `/meta/units`，可程序化复核。

### 0.2 本文档引用的本地文件（**均为可核对的本地路径**）

| 引用简称 | 本地绝对/相对路径 | 说明 |
|---|---|---|
| `abjt_03.f` | `ionmix/ionmix/src/Ionmix/abjt_03.f` | IONMIX 主控 FORTRAN 源码（写出 cn4/cnr 者） |
| `IONMIX用户指南.md` | `ionmix/ionmix/docs/IONMIX用户指南.md` | IONMIX 用户指南（中文整理版，含逐块单位表） |
| `cn4/units.py` | `eosop_pro/eosop_pro/cn4/units.py` | cn4 换算因子（**每因子附推导链**） |
| `config.py` | `eosop_pro/eosop_pro/config.py` | **唯一常量来源**（`N_A`、`EV_PER_K` 等） |
| `SUPPORTED_TYPES_AND_UNITS.md` | `eosop_pro/docs/SUPPORTED_TYPES_AND_UNITS.md` | 支持类型与单位溯源清单（**姊妹文档**） |
| `extracted/` | `eosop_pro/docs/extracted/` | 各格式官方手册的**纯文本抽取**（可全文检索） |

> **核查方法**: 本文档每条依据都写成 `<文件>:<行号>` 或 `<文件> §<章节>`，
> 可直接用编辑器跳转或 `grep -n` 定位。

### 0.3 ⚠️ 三条铁律（跨族使用前必读）

1. **同一物理量在不同族单位可能不同** —— 例如温度 `T`：F1/F3/F4/F6 为 `eV`，
   **F5 LEDCOP 为 `keV`**（差 1000 倍）。
2. **F6 IONMIX 的密度轴是数密度 `cm^-3`**，其余族均为质量密度 `g/cm3`。
3. **F6 IONMIX 的 P/E 是 SI 派生的 `J/cm3` / `J/g`**（**不是** `Mbar` / `erg/g`）。

---

## 1. 格式族总览

分派逻辑: `eosop_pro/registry/dispatch.py::FAMILY_PARSERS`；
扩展名映射: `eosop_pro/registry/declared_types.py::EXT_MAP` / `EXT_SPECIFIC`。

| 族 | 声明族名 | 解析器 | 主要扩展名 | 内容 |
|---|---|---|---|---|
| **F1** | `multi_inverted_eos` | `parsers/multi_inverted_eos.py` | `.dat` / `.inv` / `.sesame` | MULTI 反演 EOS |
| **F2** | `multi_opacity` | `parsers/multi_opacity.py` | `.planck` / `.ross` / `.zeff` / `.eps` | 不透明度 / Zeff / NLTE |
| **F3** | `hyades_eos` / `hyades_opacity` / `sesame_dat` | `parsers/hyades_eos.py` | `hyades` 路径；`.sesame` | Hyades 5×15 布局 |
| **F4** | `mpqeos` | `parsers/mpqeos.py` | `.301` / `.304` / `.305` | MPQeos 表 |
| **F4** | `feos_native` | `parsers/feos_native.py` | `.feos`（原生 10 数表头） | FEOS 原生输出 |
| **F4** | `feos_tabdata` | `parsers/feos_tabdata.py` | `*.data.txt` | FEOS ShowEOS 导出 TSV |
| **F4** | `feos_aux` | `parsers/feos_aux.py` | `.par` / `.cst` / `.mexport` | FEOS 辅助参数 |
| **F5** | `ledcop_atomic` | `parsers/ledcop_atomic.py` | `ATOMIC/*.txt` | LEDCOP 原子表 |
| **F5** | `ledcop_zeff` | `parsers/ledcop_zeff.py` | `*.NoFree` / `*.AvSqFree` | LEDCOP 平均电离度 |
| **F6** | `ionmix` | `parsers/ionmix.py` | **`.cn4` / `.cnr`** | IONMIX EOS + 不透明度 |
| **F6** | `coldopacity` | `parsers/coldopacity.py` | `.coldopacity` / `GRAYOPACITY` | 冷/灰不透明度 |
| **F6** | `hugoniot` | `parsers/hugoniot.py` | `.hug` | 雨贡纽曲线 |
| **F6** | `snop_input` | `parsers/snop_input.py` | `.snop` | SNOP 输入表 |
| **F6** | `generic_curve` | `parsers/generic_curve.py` | 兜底 | 通用曲线（**单位 unknown**） |

---

## 2. F1 —— `multi_inverted_eos`（MULTI 反演 EOS）

`unit_source = "format:F1 (rho g/cm3, P Mbar, T Kelvin->eV)"`
（`parsers/multi_inverted_eos.py:270`）

| 量 | 文件内单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 | `parsers/multi_inverted_eos.py:235`，`unit_source` 明写 |
| `de`（比内能轴） | `Mbar*cm3/g` | L1 | 同上 `:239` |
| `P`（压力） | `Mbar` | L1 | 同上 `:244` |
| `e0_cold`（冷能） | `Mbar*cm3/g` | L1 | 同上 `:252` |
| `E`（比内能） | `Mbar*cm3/g` | L1 | 同上 `:258` |
| `T`（温度） | **`eV`（原文件为 Kelvin，解析器换算）** | L1 | 同上 `:263`，名称 `T Kelvin->eV` |
| `de_energy` | `Mbar*cm3/g` | L1 | 同上 `:268` |

> ⚠️ `T` 的**文件内原始单位是 Kelvin**；`eV` 是解析器换算后的结果，
> 换算系数取自 `config.EV_PER_K`（`config.py`），非本地硬编码。

---

## 3. F2 —— `multi_opacity`（不透明度 / Zeff / NLTE）

| 量 | 单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 | `parsers/multi_opacity.py:342` |
| `Te`（温度轴） | `eV` | L2/L3 | 同上 `:345`；`unit_source` = `declared:<hint>` 或 `default:eV` |
| `kappa_*`（不透明度） | `cm2/g` | L1 | 同上 `:361` |
| 非 `kappa` 字段（Zeff 等） | `-`（无量纲） | L1 | 同上 `:361` |

**⚠️ 重要告警**: ZEFF 表存在 **eV / keV 两套**，必须由文件注释声明。
未声明时回退 `default:eV` 并在 `unit_source` 中**显式标注**
（`parsers/multi_opacity.py:378,380`）。

实测反例（`registry/units_registry.py` 模块 docstring）:

```
Thermos/mat_Al/Al_Zeff.dat    → keV
Thermos/mat_Al/Al_Z.dat       → eV
```

两者**表头与行数完全相同**（均 128 行），`logT` 区间只差 `log10(1000)=3.000` ——
**纯数字无法区分**。可靠区分只能来自**声明**。裁决优先级见
`registry/units_registry.py` docstring：`companion > inline > envelope > config_default`。
其中 `companion` 依据 `Thermos/Readme.txt` 的文件名模式声明。

---

## 4. F3 —— `hyades_eos` / `hyades_opacity` / `sesame_dat`

`unit_source = "format:F3 (rho g/cm3, T keV->eV, P dyne/cm2, E erg/g)"`
（`parsers/hyades_eos.py:202`）

| 量 | 单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|
| `rho`（密度轴） | `g/cm3` | L1 | `parsers/hyades_eos.py:173` |
| `Te`（温度轴） | **`eV`（文件为 keV，转 eV）** | L1 | 同上 `:175,177`：换算表 `{"kev":1e3,"ev":1.0}` |
| `kappa` / 不透明度类 | `cm2/g` | L1 | 同上 `:189` |
| `P`（压力） | `dyne/cm2` | L1 | 同上 `:195` |
| `E`（比内能） | `erg/g` | L1 | 同上 `:199` |
| `raw_tail`（尾部残余） | **`unknown`** | L5 | 同上 `:216` —— 无文档，**不猜** |

> **本族是 CGS 原生**（`dyne/cm2` / `erg/g`），与 F1/F4 的 `Mbar` 体系**不同**。
> 官方说明见 `docs/extracted/Hyades_数据格式说明__*.txt`（两版）与
> `docs/extracted/MULTI使用的SESAME数据文件格式__*.txt`。

---

## 5. F4 —— `mpqeos`

`unit_source = "format:F4 (GPa->Mbar, MJ/kg->Mbar*cm3/g, T Kelvin->eV)"`
（`parsers/mpqeos.py:130`）

| 量 | 文件内单位 | 单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|---|
| `rho`（密度轴） | — | `g/cm3` | L1 | `parsers/mpqeos.py:108` |
| `Te`（温度轴） | Kelvin | `eV` | L1 | 同上 `:111` |
| `P`（压力） | GPa | `Mbar` | L1 | 同上 `:117`，`unit_source` 明写 `GPa->Mbar` |
| `E`（比内能） | MJ/kg | `Mbar*cm3/g` | L1 | 同上 `:122`，明写 `MJ/kg->Mbar*cm3/g` |
| `Z`（平均电离度） | — | `-`（无量纲） | L1 | 同上 `:127` |

官方说明: `docs/extracted/MPQeos-JWGU-Documentation__pdf__6ff27aa7.txt`。

---

## 6. F4 —— `feos_native` / `feos_tabdata` / `feos_aux`

| 族 | 量 | 单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|---|
| `feos_native` | `rho` | `g/cm3` | L1 | `parsers/feos_native.py:106` |
| `feos_native` | `Te` | `eV` | L1 | 同上 `:109` |
| `feos_native` | `raw_values` | **`unknown`** | L5 | 同上 `:118` |
| `feos_native`（整体） | — | `cgs + eV` | L1 | 同上 `:140`：`unit_source = "format:FEOS (cgs + eV)"` |
| `feos_tabdata` | **全部列** | **`unknown`** | L5 | `parsers/feos_tabdata.py:76,80` —— 明写"列语义无本地文档" |
| `feos_aux` | `raw_values` | **`unknown`** | L5 | `parsers/feos_aux.py:78,80` —— 辅助参数文件 |

官方说明: `docs/extracted/FEOS-Package-Documentation2012__pdf__f5675065.txt`、
`...2016__pdf__c14ce581.txt`、`Multi1D_EOS_and_Opacity_-_FEOS程序说明__pdf__54722ef1.txt`。

---

## 7. F5 —— `ledcop_atomic` / `ledcop_zeff`

| 族 | 量 | 单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|---|
| `ledcop_atomic` | `rho` | `g/cm3` | L1 | `parsers/ledcop_atomic.py:201` |
| `ledcop_atomic` | `Te` | `eV`（文件默认 keV，转 eV） | **L2** | 同上 `:174,204`；`unit_source = "declared:<unit> (文件内嵌单位行)"`（`:230`） |
| `ledcop_atomic` | `Ross` / `Planck` | `cm2/g` | L2 | 同上 `:212` |
| `ledcop_atomic` | 其他场 | `-`（无量纲） | L2 | 同上 `:212` |
| `ledcop_zeff` | `rho` | `g/cm3` | L1 | `parsers/ledcop_zeff.py:90` |
| `ledcop_zeff` | `Te` | **`keV`（默认）** | L3 | 同上 `:92,95,103`：`unit_source = "format:T in keV"` |
| `ledcop_zeff` | Zeff 场 | `-`（无量纲） | L1 | 同上 `:100` |

### ⚠️ LEDCOP 的温度单位陷阱（**本项目第二易错处**）

1. **`ledcop_zeff` 的 T 默认是 `keV`**（`parsers/ledcop_zeff.py:103`），
   而 `ledcop_atomic` 是**由文件内嵌单位行声明**（默认 keV，可被覆盖）。
2. 同一材料目录下可能并存两套：
   * `*_Zeff.dat` → **keV**
   * `*_Z.dat` → **eV**（依据 `Thermos/Readme.txt` 声明）
3. 守护测试:
   * `test_zeff_registry.py::test_ledcop_split_tables_are_keV`
   * `test_zeff_registry.py::test_thermos_zeff_is_keV_and_z_is_eV_by_declaration`

官方说明: `docs/extracted/Atomic_LEDCOP_不透明度格式说明__*.txt`、
`Atomic_LEDCOP_说明__*.txt`。

---

## 8. F6 —— `ionmix`（`.cn4` / `.cnr`）★ 本族是重点

### 8.1 两种互斥格式（同出 `abjt_03.f` 的 `SUBROUTINE OWTF`，line 4510）

| | `.cn4` | `.cnr` |
|---|---|---|
| 源码分支 | `isw(21) != 0`（`abjt_03.f:4662–4743`） | `isw(8) = 1/12/13`（late-1986 CONRAD，`:4598–4621`） |
| fortran unit | `123` | `8` |
| 块数 | **18**（含完整 EOS 场） | **7**（**无** EOS 场） |
| 头部第 4 行 | `982 format (i12)`（`ngrups` **独占行**） | `981 format (4e12.6,i12)`（与 4 个网格参数**同行**） |
| 用户指南 | **§5.4 有全表**（`IONMIX用户指南.md:889–938`） | **零命中**（全文检索 "cnr" = 0 次，仅源码可依） |

**判据**（程序化）: 头部第 4 行能否被 `int()` 解析 —— 能 = `.cn4`，不能 = `.cnr`。

### 8.2 `.cn4` 逐块物理量与单位（**18 块 / 全部 L1，源码逐行可核**）

**双重权威出处**:
1. `abjt_03.f` `SUBROUTINE OWTF` `isw(21)!=0` 分支（line 4662–4743）—— **一手源码**
2. `ionmix/ionmix/docs/IONMIX用户指南.md` §5.4 完整数据排列表（line 910–934）—— **手册**

| # | 字段名 | 物理量 | 形状 | **单位** | 源码行 | 依据（原文） |
|---|---|---|---|---|---|---|
| 1 | `tplsma` | 温度轴 | `ntemp` | **`eV`** | 4684 | 注释 `write the temperature points (in ev)`（L4683） |
| 2 | `densnn` | 密度轴（**核子数密度**） | `ndens` | **`cm^-3`** | 4686 | 注释 `write the number density points (in cm^-3)`（L4685） |
| 3 | `zbar` | 平均电荷态 `ne/nion` | `ntemp×ndens` | **`-`（无量纲）** | 4688 | 注释 `(nele/nion)`（L4687）→ 比值 |
| 4 | `dzdt` | `d(zbar)/dT` | `ntemp×ndens` | **`1/eV`** | 4691 | `T` 以 eV 计 → 量纲 `1/eV`（**L4 推导**，见注 ①） |
| 5 | `p_ion` | 离子压力 | `ntemp×ndens` | **`J/cm3`** | 4693 | 赋值 `densnn*tplsma*1.602E-19`（**L4 推导**，见注 ②） |
| 6 | `p_ele` | 电子压力 | `ntemp×ndens` | **`J/cm3`** | 4696 | 赋值 `densne*tplsma*1.602E-19` |
| 7 | `dpion_dt` | `d(p_ion)/dT` | `ntemp×ndens` | **`J/cm3/eV`** | 4699 | 注释 `(in Joules/cm^3/eV)`（L4698） |
| 8 | `dpele_dt` | `d(p_ele)/dT` | `ntemp×ndens` | **`J/cm3/eV`** | 4702 | 注释 `(in Joules/cm^3/eV)`（L4701） |
| 9 | `e_ion` | 离子比内能 | `ntemp×ndens` | **`J/g`** | 4706 | 注释 `(in Joules/gram)`（L4705） |
| 10 | `e_ele` | 电子比内能 | `ntemp×ndens` | **`J/g`** | 4708 | 注释 `(in Joules/gram)`（L4707） |
| 11 | `cv_ion` | 离子比热 | `ntemp×ndens` | **`J/g/eV`** | 4711 | 注释 `(in Joules/gram/eV)`（L4710） |
| 12 | `cv_ele` | 电子比热 | `ntemp×ndens` | **`J/g/eV`** | 4713 | 注释 `(in Joules/gram/eV)`（L4712） |
| 13 | `deion_dn` | `d(e_ion)/d(n_ion)` | `ntemp×ndens` | **`unknown`** ⚠️ | 4717–4719 | 源码 L4715 注 **`(not sure)`** → 见 §8.4 |
| 14 | `deele_dn` | `d(e_ele)/d(n_ele)` | `ntemp×ndens` | **`unknown`** ⚠️ | 4722–4725 | 源码 L4720 注 **`(not sure)`** → 见 §8.4 |
| 15 | `engrup` | 能群边界 | `ngrups+1` | **`eV`** | 4729 | 注释 `(in ev)`（L4728） |
| 16 | `opac_rosseland` | Rosseland 群不透明度 | `ngrups×ntemp×ndens` | **`cm2/g`** | 4733 | 参数说明 `orm - Rosseland mean opacities (cm^2/g)`（L4525） |
| 17 | `opac_planck_abs` | Planck 吸收群不透明度 | `ngrups×ntemp×ndens` | **`cm2/g`** | 4736 | 参数说明 `opgp - Planck group opacities (cm^2/g)`（L4526） |
| 18 | `opac_planck_ems` | Planck 发射群不透明度 | `ngrups×ntemp×ndens` | **`cm2/g`** | 4739 | 同上（`opgpe`，`cm^2/g`） |

**计数值（必须闭合）**:

```
N = ntemp + ndens + 12·ntemp·ndens + (ngrups+1) + 3·ngrups·ntemp·ndens
```

实测锚点: `Z06_0.50-Z01_0.50-20260708_0850.cn4`
（`ntemp=51, ndens=31, ngrups=6`）→ `n_numbers = 47519 / 47519` **精确闭合**。

#### 注 ① `dzdt` 的 `1/eV`

源码无单位注释，但 L4691 紧接 L4690 注释 `write d(zbar)/dT`，
而 `T` 已是 `eV`（L4683/4684）→ `d(zbar)/dT` 量纲为 `1/eV`。属 **L4 推导**（有明确依据）。

#### 注 ② `p_ion` / `p_ele` 的 `J/cm3`（**推导链完整，非猜测**）

源码 L4693 赋值表达式:

```fortran
densnn(id) * tplsma(it) * 1.602E-19
```

量纲逐步展开:

```
[cm^-3]  ·  [eV]  ·  [J/eV]  =  J/cm^3
   ↑         ↑         ↑
 densnn    tplsma   1.602E-19
```

其中 `1.602E-19` 即元电荷 `1.602176634e-19 J/eV` 的 Fortran 简写
（理想气体律 `P = n k_B T` 在 eV–J 单位制下的 `k_B`）。
`IONMIX用户指南.md:920–921` 亦**独立给出同一结论**（单位列写 `J/cm^3`），
故该判定有**源码 + 手册双重佐证**。

#### 注 ③ `densnn` 是**数密度**，不是质量密度

`IONMIX用户指南.md:735`（§5.1 输出量表）明写:

| 输出量 | 单位 | 物理意义 |
|---|---|---|
| Number density | `cm^-3` | **核子数密度** |
| Mass density | `g/cm^3` | $\rho = n_{\text{tot}} \sum f_k A_k / N_A$ |

故 `.cn4` 内的密度轴 `densnn` 是 **`cm^-3`**。
转质量密度需乘平均原子量 `<A>`:

```
rho [g/cm3] = n_ion [cm^-3] · <A> [amu] / N_A
```

* `<A>` 的权威来源 = **同目录 `ionmxinp`** 文件（`atomwt(i)` 行）。
  依据 `IONMIX用户指南.md:412`（`atomwt(i)` 第 i 种气体的原子量 (amu)）
  与 §4.1 NAMELIST 参数详解。
* `N_A` 的**唯一来源** = `config.N_A = 6.02214076e23`（`config.py`），
  由 `cn4/units.py:111` 复用（`from ..config import N_A as NA`），
  **不在别处硬编码**（守护: `test_config_single_source.py::test_no_conversion_constant_hardcoded_outside_config`）。
* 原子量**缺失**时解析器**不给 `rho`**（`parsers/ionmix.py` notes 明写"未提供 atomwt 时不给 rho（不猜）"）。

### 8.3 `.cnr` 逐块物理量与单位（legacy，**只有源码一个依据**）

> ⚠️ **`IONMIX用户指南.md` 全文检索 "cnr" 命中 `0` 次** —— 该格式
> **未被用户指南文档化**，单位**只能**取自 `abjt_03.f` 的注释与参数说明块。

| # | 字段名 | 物理量 | 形状 | **单位** | 源码行 | 依据 |
|---|---|---|---|---|---|---|
| 1 | `zbar` | 平均电荷态 `ne/nion` | `ntemp×ndens` | `-`（无量纲） | 4606 | 赋值 `densne(it,id)/densnn(id)` → 比值 |
| 2 | `enrgy` | 比内能 | `ntemp×ndens` | **`J/g`** | 4608 | 参数说明 `enrgy - specific energies (J/g)`（L4519） |
| 3 | `op2tr` | 2-T Rosseland 不透明度 | `ntrad×ntemp×ndens` | **`cm2/g`** | 4609 | 参数说明 `op2tr - Rosseland 2-temperature opacities (cm^2/g)`（L4529） |
| 4 | `op2tp` | 2-T Planck 不透明度 | `ntrad×ntemp×ndens` | **`cm2/g`** | 4611 | 参数说明 `op2tp - Planck 2-temperature opacities (cm^2/g)`（L4528） |
| 5 | `engrup` | 能群边界 | `ngrups+1` | **`eV`** | 4613 | 同 `.cn4`（`(in ev)`） |
| 6 | `orgp` | 群 Rosseland 不透明度 | `ngrups×ntemp×ndens` | **`cm2/g`** | 4614 | 参数说明 `orgp - Rosseland group opacities (cm^2/g)`（L4527） |
| 7 | `opgpe` | 群 Planck 发射不透明度 | `ngrups×ntemp×ndens` | **`cm2/g`** | 4616 | 参数说明 `opgp`/`opgpe`（`cm^2/g`）（L4526） |
| H | 头部 4 网格参数 | `dlgden, log10(rho0), dlgtmp, log10(T0)` | 4 | **`inferred`** ⚠️ | 4604 | **指南未文档化** → 由 `write` 语句位置推断，**标 inferred** |

**`.cnr` 的 `ntrad` 不在头部存储**，必须由**计数守恒反解**:

```
rem   = N - [ 2·ntemp·ndens + (ngrups+1) + 2·ngrups·ntemp·ndens ]
ntrad = rem / (2·ntemp·ndens)
```

本仓库 8 个 `.cnr` 实测（`parse` 全部 8/8 通过）:

| 文件 | ntemp | ndens | ngrups | ntrad 反解 | 状态 |
|---|---|---|---|---|---|
| `n-100grp-lte.cnr` | 1 | 1 | 100 | **51** | OK |
| `o-100grp-lte.cnr` | 20 | 20 | 100 | **51** | OK |
| `h-100grp-lte.cnr` | 30 | 5 | 100 | **51** | OK |
| `be-100grp-lte.cnr` | 20 | 10 | 100 | **51** | OK |
| `xe-100grp-lte.cnr` | 20 | 10 | 100 | **51** | OK |
| `al-imx-001.cnr` | 21 | 21 | 30 | **16** | OK |
| `helium-imx-002.cnr` | 21 | 17 | 30 | **16** | OK |
| `xe-005grp-lte.cnr` | 17 | 13 | 5 | **不整除 → `None`** | `op2tr`/`op2tp` 标 **`unknown`** |

> ✅ **诚实边界**: `xe-005grp-lte.cnr` 的余数不被 `2·ntemp·ndens` 整除，
> 切分点**无法唯一确定** → `op2tr`/`op2tp` 单位标 `unknown`，**不伪造偏移**；
> 但 `engrup`/`orgp`/`opgpe` 仍从**文件尾部反向定位**成功。

> ⚠️ **`.cnr` 的固有限制**: 它**不含** `.cn4` 的 12 个 EOS 二维场
> （压力 / 比热 / 离子电子分量）。因此 `.cnr`:
> * **不能**用于 EOS 路径分析（等温/等压/等熵/雨贡纽/声速）
> * **不能**直接转 `.cn4`（缺 12 个必需块，无法补齐）

### 8.4 `.cn4` 中唯一的两处 `unknown`（**源码自身存疑**）

| # | 字段 | 源码注释 | 写出表达式 | 为何 unknown |
|---|---|---|---|---|
| 13 | `deion_dn` | `abjt_03.f:4715` → **`(not sure)`** | `dedden_ion·condd·densnn/tplsma²`，其中 `condd = -6.242e18·avgatw/avgdro`（L4716） | 该组合的物理量纲**无法从源码独立确认** |
| 14 | `deele_dn` | `abjt_03.f:4720` → **`(not sure)`** | `(dedden - dedden_ion)·condd·densnn/tplsma²`（L4721–4725） | 同上 |

**处置方式**（**不代为断言**）:
* 代码中以 `eosop_pro.cn4.units.UNCERTAIN_UNITS` **显式登记**（`cn4/units.py:221–232`）
* `parsers/ionmix.py` notes 中同步告警
* 守护测试: `test_ionmix.py::test_cn4_unknown_units_declared`

> 注: `cn4/units.py::RAW_UNITS` 中为这两项暂填了 `J*cm3/g`（与
> `IONMIX用户指南.md:928–929` 的表格取值一致），但该值**属于手册对
> `dedden` 原始量的标注**，而文件实际写出的是经 `condd·densnn/tplsma²`
> 变换后的量 —— **二者不等价**，故**单位最终判定为 `unknown`**。

### 8.5 F6 / ionmix —— 头部格式语句对照（`abjt_03.f:4749–4755`）

```fortran
 921 format (' atomic #s of gases: ',5i10)     ! 组分元素原子序数
 922 format (' relative fractions: ',1p5e10.2) ! 数分数（1p5e10.2，非 e12.6）
 923 format (2i10)                             ! ntemp, ndens
 980 format (a80)                             ! 80 字符串（头部 3 行）
 981 format (4e12.6,i12)                       ! .cnr 头部（4 网格参数 + ngrups 同行）
 982 format (i12)                              ! .cn4 头部（ngrups 独占行）
 991 format (4e12.6)                           ! 所有数据区（每行 4 个数）
```

### 8.6 ⚠️ F6 ionmix —— Fortran `E12.6` 字段溢出缺陷（**实测，非猜测**）

`E12.6` 仅能容纳 `0.ddddddE±ee` = **12 列**。当指数为 **3 位数**时
（`0.ddddddE-140`）需 **13 列**，Fortran 运行时**静默丢掉 `E`**，
写出 `0.638380-140`。

**实证**（`src/.../matter++/Ionmix/h-imx-1grp.cn4`，`ntemp=17, ndens=21, ngrups=1`）:

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

### 8.7 ionmix → 显示单位换算（**因子与推导链**）

全部集中在 `eosop_pro/cn4/units.py`（每因子附推导链与出处）。
**显示层约定**（`cn4/units.py:160–174` `DISPLAY_UNITS`）:
压力 `Mbar`、比内能 `erg/g`、比热 `erg/g/eV`、速度 `um/ns`、时间 `ns`、长度 `um`。

| 换算 | 因子 | 推导链 | 依据（`cn4/units.py` 行） |
|---|---|---|---|
| `J/cm3` → `Mbar` | `1e-5` | `1 J/cm3 = 1e7 erg/cm3 = 1e7 dyne/cm2 = 1e7·1e-6 bar = 10 bar = 1e-5 Mbar` | `:53–66`，依据 `abjt_03.f:4693` + `docs/15_单位换算.md` |
| `J/cm3/eV` → `Mbar/eV` | `1e-5` | 同上（分母 eV 不变） | `:68–70`，依据 `abjt_03.f:4698` |
| `J/g` → `erg/g` | `1e7` | `1 J = 1e7 erg` | `:72–80`，依据 `abjt_03.f:4705,4707` |
| `J/g/eV` → `erg/g/eV` | `1e7` | 同上（分母 eV 不变） | `:82–84`，依据 `abjt_03.f:4710,4712` |
| `cm/s` → `um/ns` | `1e-5` | `1 cm = 1e4 um`；`1 s = 1e9 ns` → `1e4/1e9` | `:86–94` |
| `s` → `ns` | `1e9` | `1 s = 1e9 ns` | `:96–98` |
| `cm` → `um` | `1e4` | `1 cm = 1e4 um` | `:100–102` |

**不发生换算的量**（保持原单位）:
`n_ion` = `cm^-3`、`rho` = `g/cm3`、`T` = `eV`、不透明度 = `cm2/g`、
`zbar` = 无量纲。

### 8.8 F6 —— `.cn4` 的已注册字段（程序化复核结果）

对 `Z06_0.50-Z01_0.50-20260708_0850.cn4` 实际解析得到的 `field_units`:

| 字段 | 单位 | 形状 |
|---|---|---|
| `zbar` | `-` | `(51, 31)` |
| `dzdt` | `1/eV` | `(51, 31)` |
| `p_ion` | `J/cm3` | `(51, 31)` |
| `p_ele` | `J/cm3` | `(51, 31)` |
| `dpion_dt` | `J/cm3/eV` | `(51, 31)` |
| `dpele_dt` | `J/cm3/eV` | `(51, 31)` |
| `e_ion` | `J/g` | `(51, 31)` |
| `e_ele` | `J/g` | `(51, 31)` |
| `cv_ion` | `J/g/eV` | `(51, 31)` |
| `cv_ele` | `J/g/eV` | `(51, 31)` |
| `deion_dn` | `J*cm3/g`（**判定 `unknown`**，见 §8.4） | `(51, 31)` |
| `deele_dn` | `J*cm3/g`（**判定 `unknown`**，见 §8.4） | `(51, 31)` |
| `kappa_rosseland` | `cm2/g` | `(6, 51, 31)` |
| `kappa_planck_abs` | `cm2/g` | `(6, 51, 31)` |
| `kappa_planck_ems` | `cm2/g` | `(6, 51, 31)` |

`unit_source = "abjt_03.f SUBROUTINE OWTF (isw(21)!=0 分支, line 4662-4743) + docs/IONMIX用户指南.md §5.4"`

---

## 9. F6 —— `coldopacity` / `hugoniot` / `snop_input` / `generic_curve`

| 族 | 量 | 单位 | 等级 | 判定依据（可定位） |
|---|---|---|---|---|
| `coldopacity` | 全部列 | **由文件 2 行头内嵌声明** | L2 | `parsers/coldopacity.py:84,89,91`：`unit_source = "declared:inline (2-line header)"` |
| `hugoniot` | 全部列 | **由注释列头内嵌声明** | L2 | `parsers/hugoniot.py:103,107,110`：`unit_source = "declared:inline (comment column header)"` |
| `snop_input` | `T1`,`T2`,`X1`,`X2` | **`keV`** | L1 | `parsers/snop_input.py:35–36` |
| `snop_input` | `FG` | **`eV`** | L1 | 同上 `:37` |
| `snop_input`（整体） | — | — | L1 | 同上 `:106`：`unit_source = "declared:doc/SNOP.MANUAL"` |
| `generic_curve` | `x` 轴 / 全部场 | **`unknown`** | L5 | `parsers/generic_curve.py:80,86,89`：`"none（列语义无文档 → 不猜测）"` |

> ⚠️ `coldopacity` / `hugoniot` 的单位**不在代码里硬编码**，
> 而是从文件自身头部/注释**读出** —— 这是设计使然（不同实例可用不同单位），
> 但若文件未声明，解析器**不给单位**（`unit_source` 会显示实际来源）。

官方说明: `docs/extracted/SNOP__text__79a5123d.txt`。

---

## 10. 跨族单位差异速查表（**做跨族比较前必读**）

| 物理量 | F1 MULTI | F2 MULTI-opac | F3 Hyades | F4 MPQeos | F5 LEDCOP | **F6 IONMIX** |
|---|---|---|---|---|---|---|
| 温度 `T` | `eV`（原 K） | `eV`（或 eV/keV 双套 ⚠️） | `eV`（原 keV） | `eV`（原 K） | **`keV`** ⚠️ | **`eV`** |
| 密度 | `g/cm3` | `g/cm3` | `g/cm3` | `g/cm3` | `g/cm3` | **`cm^-3`（数密度）** ⚠️ |
| 压力 `P` | `Mbar` | — | **`dyne/cm2`** | `Mbar`（原 GPa） | — | **`J/cm3`** |
| 比内能 `E` | `Mbar*cm3/g` | — | **`erg/g`** | `Mbar*cm3/g`（原 MJ/kg） | — | **`J/g`** |
| 不透明度 | — | `cm2/g` | `cm2/g` | — | `cm2/g` | `cm2/g` |
| 能群边界 | — | — | — | — | — | `eV` |

**三处最容易踩的坑**:

1. **F6 ionmix 的密度轴是 `cm^-3` 数密度**，其余族都是 `g/cm3` ——
   混用会得到量级完全错误的结果。
2. **F5 LEDCOP 的温度是 `keV`**，其余族（换算后）是 `eV` —— 差 **1000 倍**。
3. **F6 ionmix 的 P/E 是 SI 派生的 `J/cm3` / `J/g`**，
   与 F1/F4 的 `Mbar` / `Mbar*cm3/g` 及 F3 的 CGS `dyne/cm2` / `erg/g` **都不同**。

---

## 11. ★ `unknown` 清单（**诚实汇总，共 7 处 + 1 处 inferred**）

> **纪律**: 以下各处**本地源码与文档均无法唯一确定**，故标 `unknown`，
> **无一处靠猜测填充**。

| # | 族 / 位置 | 量 | 为何 `unknown` | 依据 |
|---|---|---|---|---|
| 1 | F6 `.cn4` block 13 | `deion_dn` | 源码自身注 `(not sure)`，量纲无法独立确认 | `abjt_03.f:4715` |
| 2 | F6 `.cn4` block 14 | `deele_dn` | 同上 | `abjt_03.f:4720` |
| 3 | F4 `feos_tabdata` | 全部列 | 列语义无本地文档 | `parsers/feos_tabdata.py:80` |
| 4 | F4 `feos_aux` | `raw_values` | 辅助参数文件，语义无文档 | `parsers/feos_aux.py:80` |
| 5 | F3 `hyades_eos` | `raw_tail` | 尾部残余无文档 | `parsers/hyades_eos.py:216` |
| 6 | F6 `generic_curve` | 全部列 | 兜底族，列语义无文档 | `parsers/generic_curve.py:89` |
| 7 | F6 `.cnr`（`xe-005grp-lte.cnr`） | `op2tr` / `op2tp` | `ntrad` 反解不整除，切分点**不唯一** | `abjt_03.f:4609,4611` + 计数反解 |

**另有 1 处为 `inferred`**（非 unknown，但**必须注明**）:

| 位置 | 量 | 说明 | 依据 |
|---|---|---|---|
| F6 `.cnr` 头部 4 个网格参数 | `dlgden, log10(rho0), dlgtmp, log10(T0)` | 物理含义由 `write (8,981)` 语句位置**推断**；IONMIX 用户指南**未文档化该格式** | `abjt_03.f:4604` |

---

## 12. 其他类型 eosop 数据 → `.cn4` 的转换（**单位纪律**）

### 12.1 唯一入口

```
其他格式文件 → [各族 parser] → ParsedTable → parsed_tables_to_cn4() → .cn4 文件
```

* 入口函数: `eosop_pro.cn4.cn4_io.parsed_tables_to_cn4`
* 反方向: `cn4_to_parsed_tables()` 把 1 张 cn4 总表拆成 4 张 `ParsedTable`
  （1 张 EOS + 3 张不透明度），便于**按族**喂给 `parsed_tables_to_cn4`。
* 已验证: `cn4 → ParsedTable → cn4` **byte-identical**（无损往返）。

### 12.2 ⚠️ 单位纪律（转换时的硬约束）

1. `parsed_tables_to_cn4` **要求输入表带 `field_units`**。
2. 单位不匹配时**拒绝或显式警告**，**不会静默按错误单位写**。
3. `.cnr` **不能**作为来源 —— 它缺 12 个 EOS 场，无法补齐 cn4 的必需块。
4. 目标 `.cn4` 的 18 块单位**必须**是 §8.2 所列表格中的值
   （如压力必须为 `J/cm3`，**不是** `Mbar`）——
   由其他族（`Mbar` / `dyne/cm2`）转换时**必须显式换算**。

---

## 13. 结论

1. **支持 6 大格式族 / 17 个声明族**（分派见 `registry/dispatch.py` +
   `registry/declared_types.py`）。
2. **每一个非 `unknown` 的单位都有可定位的出处** —— 或为源码**行号**
   （`abjt_03.f`），或为用户指南**章节**（`IONMIX用户指南.md §5.4` / §5.1），
   或为**文件内嵌声明**。代码中以 `ParsedTable.unit_source` 与
   `cn4/units.py::RAW_UNIT_EVIDENCE` 逐项登记。
3. **F6 IONMIX 是本项目单位最"特殊"的一族** —— 密度用**数密度 `cm^-3`**、
   压力/能量用 **SI 派生 `J/cm3` / `J/g`**，且 `.cn4` 与 `.cnr` 是**两种不同格式**，
   必须按**扩展名分派**。`.cnr` **未被用户指南文档化（检索命中 0）**，
   单位**仅有源码一个依据**。
4. **`unknown` 共 7 处，全部显式标注**，无一处靠猜测填充；
   另有 **1 处 `inferred`** 已注明推断依据。
5. **`.cn4` 是后续"其他格式 → cn4"转换的目标格式**，
   入口 `parsed_tables_to_cn4`，已验证往返无损，且带单位校验。

---

## 附录 A —— 复现与核查命令

```bash
# 1) 复核 cn4 解析（18 块计数闭合 + 逐场单位）
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
cd <repo>/eosop_pro
$PY -c "
import sys; sys.path.insert(0,'.')
from eosop_pro.parsers import ionmix
t = ionmix.parse('../eos_op_data/Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/Z06_0.50-Z01_0.50-20260708_0850.cn4')
print(t.unit_source)
print(t.n_numbers_seen, '/', t.n_numbers_expected)
[print(k, v) for k, v in t.field_units.items()]
"

# 2) 复核 Fortran 源码单位注释（逐行）
awk 'NR>=4510 && NR<=4755' ../ionmix/ionmix/src/Ionmix/abjt_03.f | grep -n -i "in ev\|Joules\|cm\^2/g\|not sure"

# 3) 复核用户指南 §5.4 逐块单位表
grep -n "EOS.CN4" -A 50 ../ionmix/ionmix/docs/IONMIX用户指南.md

# 4) 复核 .cnr 在用户指南中的覆盖情况（应为 0）
grep -ic "cnr" ../ionmix/ionmix/docs/IONMIX用户指南.md

# 5) 交叉验证两套实现（62 项）
$PY eosop_pro/test/cross_validate_cn4.py

# 6) 全量测试（31 个测试文件）
$PY test/run_all.py
```

## 附录 B —— 权威来源速查

| 内容 | 文件 | 定位 |
|---|---|---|
| `.cn4` 逐块单位 | `ionmix/ionmix/docs/IONMIX用户指南.md` | §5.4（line 889–938），表在 910–934 |
| 质量密度公式 | `ionmix/ionmix/docs/IONMIX用户指南.md` | §5.1（line 735） |
| 温度 / 数密度注释 | `ionmix/ionmix/src/Ionmix/abjt_03.f` | L4683–4685 |
| 压力赋值表达式 | 同上 | L4693 / L4696 |
| `(not sure)` 两处 | 同上 | L4715 / L4720 |
| 格式语句 | 同上 | L4749–4755 |
| 换算因子与推导链 | `eosop_pro/eosop_pro/cn4/units.py` | line 51–156 |
| 单位证据链字典 | 同上 | `RAW_UNIT_EVIDENCE` line 199–218 |
| 存疑量登记 | 同上 | `UNCERTAIN_UNITS` line 221–232 |
| 单一来源常量 | `eosop_pro/eosop_pro/config.py` | `N_A` = 6.02214076e23 |
| T 轴单位裁决 | `eosop_pro/eosop_pro/registry/units_registry.py` | 模块 docstring + `UnitDecision` |
| 各族官方手册 | `eosop_pro/docs/extracted/*.txt` | 见 §0.2 |
