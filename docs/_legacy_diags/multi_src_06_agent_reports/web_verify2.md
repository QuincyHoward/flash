# 网络核验记录（第二轮）

> 访问日期：**2026-09-18**（GMT+8）
> 纪律：本地是唯一权威骨架；联网只用于核对与补缺。凡联网与本地冲突，**以本地为准并显式记录冲突**。查不到即标 `[S-UNK]`，不杜撰。
> 本文件为 `web_verify.md`（W1–W6）之续，**不覆盖**前者。

---

## 摘要表

| # | 目标 | 结论 | 置信度 | 来源数 |
|---|---|---|---|---|
| W7 | P1 IONMIX / MacFarlane CPC 56 | **书目完全核实**；DOI `10.1016/0010-4655(89)90023-4`；CPC 程序号 `ABJT_v1_0`；并**意外获得 IONMIX/IONMIX4 完整 24 段格式规范**（FLASH UG §23.5.6） | **确认** | 6+ |
| W8 | P2-A Kemp & Meyer-ter-Vehn NIM A 415 | **完全核实**；DOI `10.1016/S0168-9002(98)00446-X`；415(3):674–676；1998-10；MPQ Garching | **确认** | 4 |
| W9 | P2-B FEOS 正式论文 | **完全核实**；DOI `10.1016/j.cpc.2018.01.008`；*CPC* **227**:117–125；2018-06；GPLv3；Mendeley Data `10.17632/6vjsv6v48p.1` | **确认** | 5 |
| W10 | P3 SHOWEOS 与派生后缀 | SHOWEOS **官方定位确认**（FEOS 三组件之一，绘制 isotherm/isochore/isentrope/Hugoniot）；`.ist/.isc/.ise/.mnt/.hug` 与 `*4gnuplot` **无果** | **高**（定位）/ **无果**（后缀） | 1+ |
| W11 | P4 PROPACEOS | **`.prp` 为 ASCII 单一文件**，Prism 官方公开了**按 format 版本递增的字段清单**；`*4gnuplot` 无关；PROPACEOS reader **明确不分发** | **确认**（结构清单）/ **确认**（未公开字节级） | 4 |
| W12 | P4 附：opacplot2 关于 PROPACEOS/MULTI 的佐证 | opacplot2 明确：Propaceos *"not distributed … contact jtlaune at uchicago dot edu"*；MULTI 支持 `.opp/.opr/.opz/.eps` | **确认** | 3 |
| W13 | P5 SNOP 群结构惯例 | Eidmann 1994 摘要+正文书目核实；**第三方独立复现 3000 点 / 1 eV–5 keV / 20 群**（arXiv:2207.14026）；`d`/`DREK` 仍非同一定义 | **高** | 3 |
| W14 | P6 Hyades / CAS Inc. | **Larsen & Lane 1994 *JQSRT* 51(1-2):179–186** 完全核实，DOI `10.1016/0022-4073(94)90078-7`（**W5 遗留项已解决**）；"Cascade Applied Sciences" 与双温表号分段**无果** | **确认**（文献）/ **无果**（CAS / 表号） | 3 |
| W15 | P9 MULTI 自身格式 | Ramis 1988 CPC 49(3):475 核实（DOI `10.1016/0010-4655(88)90008-2`）；MULTI 官方页存在但 `.base/.template/.case` **无果**；opacplot2 给出 MULTI 数据后缀 `.opp/.opr/.opz/.eps` | **高**（血统）/ **无果**（自身格式） | 4 |
| W16 | P7 cold opacity | 找到 ICF 语境下「cold opacity 被补丁进 AOT 用于流体仿真」的明确文献表述；SESAME 官方 opacity 下限 `~1 eV`，**无 T=0 cold opacity 表型**；`.coldopacity` 后缀无果 | **高**（概念）/ **无果**（后缀） | 3 |
| W17 | P8 `.dem` | **完全无果** | **无果** | 0 |

**统计**：确认 7 项、高 5 项、低 0 项、无果 5 项（`.ist/.isc/.ise/.mnt/.hug`、`*4gnuplot`、`.dem`、CAS Inc.、双温表号分段）。

---

## W7 — IONMIX / MacFarlane, *Comput. Phys. Commun.* **56** (1989) 259–278

### 结论

**书目完全核实，逐项与本地任务书一致：**

| 字段 | 核实值 |
|---|---|
| 作者 | J. J. MacFarlane（署名亦见 `Macfarlane J.J.` 变体） |
| 题名 | *IONMIX — a code for computing the equation of state and radiative properties of LTE and non-LTE plasmas* |
| 期刊 | Computer Physics Communications |
| 卷 / 期 | **56**（Issue **2**） |
| 页码 | **259–278** |
| 年 / 月 | **1989**，**1 December 1989** |
| DOI | **`10.1016/0010-4655(89)90023-4`** |
| 机构 | University of Wisconsin–Madison，**Fusion Technology Institute** |
| CPC 程序号 | **`ABJT_v1_0`**（即本地源码 `abjt_03.f` 之所属程序） |

**CPC 程序库归档（Mendeley Data）**：
- DOI `10.17632/8n4r3rh8kr.1`（Version 1，Published 1 December 1989）
- 附带文件：`abjt_v1_0.gz`（58.2 KB）、打包 `IONMIX-…zip`（57.7 KB）
- SHA-256（zip）：`e09e7fa78b6111f37cd124f96895d574c004edea16f7c6d34fdad48245e6b27e`
- 说明：*"This program has been imported from the CPC Program Library held at Queen's University Belfast (1969–2019)"*
- **⇒ 本地 `abjt_03.f` 与 CPC 官方归档 `abjt_v1_0.gz` 同源**，本地源码的一手权威性得到官方归档佐证。

**摘要原文（多源一致）**：
> *A detailed description of a code developed to compute the energetics and radiative properties of high temperature, low-to-moderate density plasmas is presented. Steady-state ionization and excitation populations are determined by detailed balancing arguments and rate coefficients based on the hydrogenic ion approximation. We consider contributions from bound-bound, bound-free, free-free and electron scattering processes in evaluating extinction and emission coefficients at several hundred well-placed photon energies, which are then used to compute multi-group Planck and Rosseland mean opacities.*

### **重大补白A：`.cn4` / `.cnr` / `.imx` 的真正含义（本地缺失，联网获得）**

**（a）`.cn4` = IONMIX4 输出文件的标准后缀。** FLASH 中心官方邮件（Klaus Weide，2017-06-21）明确：

> *There are actually some more IONMIX files in the FLASH release than the ones with the suffix ".cn4" that you found. You can also find several files with ".imx" which have been generated with IONMIX and may be usable for you. Also possibly some files ending in ".cnr".*

同时，FLASH 用户（Roman Yurchak，2015-11-01）进一步澄清：
> *FLASH uses only the `*.cn4` files, the other `.imx` files are just provided for convenience (human readable output of the IONMIX code).*

**（b）`.imx` 是 IONMIX 的「人类可读」输出，但不是单一格式**——存在 IONMIX **1** 与 IONMIX **4** 两代，需按前四行判据区分。**官方判据（FLASH 中心 Klaus Weide 原始文本）**：

> **判据1 — IONMIX 4 输出文件**，若前四行为：
> ```
> ======================================================================
> 21 17
> atomic #s of gases: 2
> relative fractions: 1.00E+00
> 30
> ======================================================================
> ```
> **判据2 — IONMIX 1 输出文件**，若前四行为：
> ```
> ======================================================================
> 30 5
> atomic #s of gases: 1
> relative fractions: 1.00E+00
> 0.100000E+010.140000E+020.333333E+00-.100000E+01 100
> ======================================================================
> ```
> **关键区分点**：**第四行含 5 个数（4 实数 + 1 整数）⇒ IONMIX 4；仅含 1 个整数 ⇒ IONMIX 1。**（该整数恒为文件所含不透明度的**辐射能群数**。）

**（c）格式规范位置**：`FLASH Users Guide, §"The IONMIX EOS/Opacity Format"`（旧版 `flash4_ug_4p4` 为 §22.4.6；新版 `flash4_ug_4p8` 为 §23.5.6）。

### **重大补白B：IONMIX4 文件格式完整规范（24 段，官方 Fortran 原样）**

来源：FLASH 4.8 User's Guide §23.5.6（`https://flash.rochester.edu/site/flashcode/user_support/flash4_ug_4p8/node149.html`）

**总述（官方原文）**：
> *FLASH reads tabulated opacity and Equation Of State (EOS) files in the **IONMIX, IONMIX4, and IONMIX6** formats. … Each file contains information for a **single material**. All EOS/opacity information is defined on a temperature/density grid. **The densities are actually ion number densities.***
> *…the latter [IONMIX6] is identical to the former [IONMIX4] but also includes **electron specific entropy** information.*

**段落清单（逐段，1-based）**：

| # | 内容 | 单位 | FLASH 是否使用 |
|---|---|---|---|
| 01 | 温度点数 `ntemp` | — | 是 |
| 02 | 离子数密度点数 `ndens` | — | 是 |
| 03 | 各元素原子序数行（`izgas(l)`） | — | **忽略** |
| 04 | 各元素相对分数行（`fracsp(l)`） | — | **忽略** |
| 05 | 辐射能群数 `ngrups` | — | 是 |
| 06 | 温度列表 `tplsma(it)` | **eV** | 是 |
| 07 | 离子数密度列表 `densnn(id)` | **cm⁻³** | 是 |
| 08 | 平均电离度 `zbar`（= `nele/nion`） | — | **仅 EOS 用** |
| 09 | `d(zbar)/dT` | **1/eV** | **忽略** |
| 10 | 离子压强 = `densnn·tplsma·1.602E-19` | **J/cm³** | **仅 EOS 用** |
| 11 | 电子压强 = `tplsma·densne·1.602E-19` | **J/cm³** | **仅 EOS 用** |
| 12 | `d(pion)/dT` | **J/cm³/eV** | **忽略** |
| 13 | `d(pele)/dT` | **J/cm³/eV** | **忽略** |
| 14 | 离子比内能 `enrgyion` | **J/g** | **仅 EOS 用** |
| 15 | 电子比内能 `enrgy − enrgyion` | **J/g** | **仅 EOS 用** |
| 16 | 离子比热 `heatcpion` | **J/g/eV** | **忽略** |
| 17 | 电子比热 `heatcp − heatcpion` | **J/g/eV** | **忽略** |
| 18 | `d(eion)/d(nion)` | **J/g/cm³** | **忽略** |
| 19 | `d(eele)/d(nele)` | **J/g/cm³** | **忽略** |
| **20** | **【仅 IONMIX6】** 电子比熵 `entrele` | **J/g/eV** | （IONMIX4 无此段） |
| 21 | 能群边界 `engrup(ig)`，共 `ngrups+1` 个 | **eV** | 是 |
| 22 | Rosseland 群不透明度 `orgp` | **cm²/g** | **仅 opacity 用** |
| 23 | Planck **吸收**群不透明度 `opgpa` | **cm²/g** | **仅 opacity 用** |
| 24 | Planck **发射**群不透明度 `opgpe` | **cm²/g** | **仅 opacity 用** |

**格式语句（官方原样，可作字节级复现依据）**：
```fortran
921 format (' atomic #s of gases: ',5i10)
922 format (' relative fractions: ',1p5e10.2)
923 format (2i10)
980 format (a80)
981 format (4e12.6,i12)
982 format (i12)
991 format (4e12.6)
```
**⇒ 所有数据段均为 `4e12.6`：每行 4 个值，每值 12 字符宽、6 位小数、无分隔符。** 三个字符串头（03/04 行）用 `a80` 整行写出。

**数据排布次序（官方 Fortran 循环索引，极重要）**：
```fortran
! 标量场（08–19 段）：每段均为
(( val(it,id), it=1,ntemp), id=1,ndens )
⇒ 外层 id（密度）、内层 it（温度）——即【温度变化最快】。

! 不透明度（22–24 段）：
((( val(it,id,ig), it=1,ntemp), id=1,ndens), ig=1,ngrups)
⇒ 外层 ig（能群）、次层 id（密度）、内层 it（温度）
⇒ 即【同一能群内，温度最快、密度次之；能群最慢】。
```

**第 10 段压强公式中的物理量（官方代码原文，可反推）**：
- `pion = densnn(id) * tplsma(it) * 1.602E-19` ⇒ 离子按**理想气体**处理（`p = n_i kT`，`1.602E-19` 为 eV→J）
- `pele = tplsma(it) * densne(it,id) * 1.602E-19` ⇒ 电子同样理想气体
- `d(pele)/dT = (tplsma·densnn·dzdt + densne) * 1.602E-19`

### **重大补白C：IONMIX1 的读写限制（解释本地 `--log` 类问题）**

opacplot2 官方文档（`readthedocs` 版）指出 IONMIX **1** 格式的固有限制：

> *`ValueError: invalid literal for int() with base 10` — This error arises when **the exponent for the data is more than 2 digits long, which IONMIX does not support**. What that usually means is that the data was originally stored logarithmically and must be written back to IONMIX as **logarithmic data**.*

**⇒ IONMIX1 的实数字段宽度不容许 3 位指数（如 `1.234E-105`）**，必须改为存储对数值。这是本地解析器判断字段宽度时必须考虑的陷阱。

### 来源（URL + 日期 2026-09-18）

1. ScienceDirect 作者页 / 文章页 — https://www.sciencedirect.com/author/7201418151/joseph-j-macfarlane
2. Scilit 书目 — https://www.scilit.com/publications/af36341c8fba31a804238ca44ca3125c
3. SciSpace 书目（含 "Vol. 56, Iss: 2, pp 259-278" 与 University of Wisconsin-Madison 机构信息） — https://scispace.com/papers/ionmix-a-code-for-computing-the-equation-of-state-and-18snb6vvw7
4. Mindat 书目 — https://www.mindat.org/reference.php?id=6594151
5. **CPC 程序库官方归档（Mendeley Data）** — https://data.mendeley.com/datasets/8n4r3rh8kr/1 ；解析页 https://dx.doi.org/10.17632/8n4r3rh8kr.1
6. **FLASH 4.8 User's Guide §23.5.6 The IONMIX EOS/Opacity Format** — https://flash.rochester.edu/site/flashcode/user_support/flash4_ug_4p8/node149.html
7. FLASH-USERS 邮件列表（IONMIX1/4 判据，Klaus Weide 2017-06-21） — https://flash.rochester.edu/pipermail/flash-users/2017-June/006705.html
8. FLASH-USERS 邮件列表（`*.cn4` 为 FLASH 唯一使用格式，Roman Yurchak 2015-11-01） — https://flash.rochester.edu/pipermail/flash-users/2015-November/001818.html
9. FLASH EOS/Opacity 教学 PDF（*"IONMIX4 is a table format documented in the FLASH Users Guide"*） — https://flash.rochester.edu/site/flashcode/user_support/tutorial_talks/RAL_May2012/EOS_Opac.pdf
10. opacplot2 官方文档（IONMIX1 指数宽度限制） — https://readthedocs.org/projects/opacplot2/downloads/pdf/latest/

### 与本地文件的对照（是否冲突？）

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| MacFarlane CPC 56 (1989) 259–278 | 已知书目 | **完全一致** | ✅ 无冲突，书目升格为 `[S-WEB]` |
| CPC 程序号 | `abjt_03.f`（本地源码） | `ABJT_v1_0`（官方归档） | ✅ 一致，`abjt_` 前缀确为 CPC 程序号 |
| IONMIX4 是 `.cn4` | 本地按后缀识别 | 官方确认 `.cn4` = IONMIX4 | ✅ 无冲突，可加注 `[S-WEB]` |
| 群边界数 = `ngrups+1` 个值 | — | 官方 §21 段明确 `ngrups+1` | ➕ 补白（本地若无此点须补） |
| **第 3/4 行被 FLASH「忽略」** | — | 官方标 `(ignored by FLASH)` | ⚠️ **注意**：这是 **FLASH 的实现选择**，不代表 IONMIX 本身无意义。本地若把这些字段当语义字段解析，**不算错**，但须说明 FLASH 不读它们 |
| 密度是**离子数密度**（cm⁻³）而非质量密度 | 待与本地核对 | 官方明确 *"The densities are actually **ion number densities**"* | ⚠️ **须重点核对**。若本地文档按质量密度解读 IONMIX4，则**以本地为准**但必须记录此冲突 |

### 未解决

- MacFarlane 1989 **正文**（Elsevier 付费墙）未获取 ⇒ **仅书目核验 + 官方程序库归档核验，正文未获取**。§22.4.6 / §23.5.6 的格式规范来自 **FLASH 用户指南转述的 IONMIX 代码写法**，非 MacFarlane 原文。
- IONMIX 的 `.cn4` 写入端（`abjt_03.f` 内部 WRITE 语句）未与 FLASH 指南逐句对照 ⇒ 建议由 `rev-source-code` 在本地源码中定位 `921/922/923/980/981/982/991` 的 `FORMAT` 语句做**双向校验**（若本地源码中 FORMAT 语句号相同，则等同官方规范）。
- University of Wisconsin 的 IONMIX 分发页：本轮未找到独立分发页；MacFarlane 现于 **Prism Computational Sciences**（HELIOS/SPECT3D 作者），但未找到 IONMIX 的 UW 托管页 ⇒ `[S-UNK]`。

---

## W8 — P2-A MPQeos：Kemp & Meyer-ter-Vehn, *NIM A* **415** (1998) 674

### 结论

**书目完全核实：**

| 字段 | 核实值 |
|---|---|
| 作者 | A. J. Kemp；J. Meyer-ter-Vehn |
| 题名 | *An equation of state code for hot dense matter, based on the QEOS description* |
| 期刊 | Nuclear Instruments and Methods in Physics Research **Section A** |
| 卷 / 期 | **415**（Issue **3**） |
| 页码 | **674–676**（**本地任务书写「674」为起始页，正确；完整页码为 674–676**） |
| 年 / 月 | **1998**，**October 1998** |
| DOI | **`10.1016/S0168-9002(98)00446-X`** |
| Bibcode | `1998NIMPA.415..674K` |
| 机构 | **Max-Planck-Institut für Quantenoptik, Hans-Kopfermann-Str. 1, D-85748 Garching, Germany** |
| 参考文献数 | 4 refs（OSTI 记录） |

**摘要（OSTI 原文）**：
> *An equation of state code for hot dense matter, based on the QEOS description [More et al. (1988)] is presented. Results of Hugoniot calculations and hydrodynamic simulations, based on this EOS, are shown. The purpose of this work is to make QEOS available in the form of a computer program.*

**⇒ MPQ229 报告号本轮仍未证实为公开报告** ⇒ `[S-UNK]`。
（本地 `web_verify.md` W6 亦未获；本轮同样无果。**注意**：FEOS 官网参考文献 [1] 给出的是另一个报告号 **`GSI Darmstadt; Report 2012-1, PNI-PP-12`**，与 MPQ229 不同，**不可混用**。）

### 来源

1. NASA ADS — https://ui.adsabs.harvard.edu/abs/1998NIMPA.415..674K/abstract
2. OSTI/ETDEWEB（含卷期年月与 4 refs） — https://www.osti.gov/etdeweb/biblio/304840
3. CNKI Scholar（含 MPQ Garching 机构地址） — https://scholar.cnki.net/Detail/index/GARJ8099_1/SJESE27A83431FEA6DAF50696180C4D8D1F8
4. Mindat 书目（含 pp. 674-676） — https://www.mindat.org/reference.php?id=5470514
5. Semantic Scholar（被引 81，含引文脉络） — https://www.semanticscholar.org/paper/2ea9f2cd04346dbf8bb3ab857f9068ab95fa49a9

### 与本地文件的对照

- 本地 `matter++/mat_B/B.mexport` 内嵌 `/comp. LULI /codes. FEOS /` —— FEOS 血统即 MPQeos，**与本条书目链条闭合**：`QEOS(More 1988) → MPQeos(Kemp 1998) → FEOS(Faik 2018)`。✅ 无冲突，可将该血缘链条升格为 `[S-WEB]`。
- 本地任务书称「MPQ229」—— **联网未获任何 MPQ229 公开记录**，且 FEOS 官网给出的是 `GSI Report 2012-1, PNI-PP-12`。**建议正文中 MPQ229 标 `[S-UNK]`，或改引 Kemp 1998 NIM A 415 这一**已核实**出处。**

### 未解决

- 正文（Elsevier 付费墙）未获取 ⇒ **仅书目核验，正文未获取**。
- MPQ229 报告是否存在/是否公开 ⇒ **无果**。

---

## W9 — P2-B FEOS 正式发表论文

### 结论

**完全核实，且发现本地文档未记录的关键事实：**

| 字段 | 核实值 |
|---|---|
| 作者 | **Steffen Faik**；**Anna Tauschwitz**；**Igor Iosilevskiy** |
| 题名 | *The equation of state package FEOS for high energy density matter* |
| 期刊 | **Computer Physics Communications** |
| 卷 / 页码 | **227**: **117–125** |
| 年 / 月 | **2018**，**June 2018** |
| DOI | **`10.1016/j.cpc.2018.01.008`** |
| 程序归档 DOI | **`10.17632/6vjsv6v48p.1`**（Mendeley Data，**Published 15 March 2018**，附件 `FEOS.tar.gz` **759 KB**） |
| 许可 | **GNU General Public License version 3** |
| 编程语言 | **C++** |
| 机构 | Goethe Univ. Frankfurt am Main / GSI Darmstadt；RAS Joint Inst. High Temp. Moscow；Moscow Inst. Phys. & Technol. |
| 资助 | **EMMI (Helmholtz Alliance)**；BMBF；JIHTS RAS "Physics of extreme states of matter" |

**⇒ 注意：FAQ/任务书中「High Energy Density Physics 2018?」的猜测不正确——FEOS 正式论文发表在 `Computer Physics Communications` 227:117–125，不是 HEDP。** 但 Faik 等人确有一篇 HEDP 论文（见下）。

**程序概要（Program Summary，官方原文）**：
> **Program Title**: FEOS — Frankfurt equation of state
> **Program Files doi**: http://dx.doi.org/10.17632/6vjsv6v48p.1
> **Licensing provisions**: GNU General Public License version 3
> **Programming language**: C++
> **Supplementary material**: **Documentation/manual, exemplary input files for aluminum (Al) and fused silica (SiO2)**

**⇒ 官方声明补充材料含「Documentation/manual」** —— 即 `.feos` 格式文档应在 `FEOS.tar.gz` 内。本地 `doc/FEOS/*.pdf` 很可能正是此手册的副本。

**求解方法（官方原文，可作第 10 章物理背景）**：
> *f = f_e + f_i + f_b* —— 电子项（Thomas–Fermi 统计模型数值解）、离子项（**Cowan 模型**，在 Debye 固体/正常固体/液态间解析插值）、**键合修正** `f_b`（半经验，补偿 TF 忽略成键力的缺陷）。
> *Although the total EOS is calculated for a single temperature **T = Te = Ti**, the user is free to calculate the ionic and the corrected electronic contributions **independently with different temperatures**.*
> *For homogeneous mixtures … partial volumes of all element species k are iteratively adjusted in order to equilibrate the Thomas–Fermi pressures p_{e,k} and to fulfill an **additive volume rule** for the electronic contribution.*
> *…the model provides the (metastable) EOS with its characteristic features like **van-der-Waals loops**. The fully equilibrium EOS inside the two-phase region can be calculated by an iterative **Maxwell construction** scheme.*
> *…despite the existence of the bonding correction, pressures near the critical point are often overestimated. Therefore, an improved cold curve can be applied to fit the location of the critical point to theoretical or experimental data.*

**适用范围（Mendeley 记录原文）**：
> `1e-7 ≤ ρ/ρ₀ ≤ 1e+6`；`1e-4 eV ≤ T ≤ 1e+6 eV`
> *Homogeneous mixtures with more than three elements may implicate numerical difficulties and/or uneconomical computing times.*

**TF 混合与摩尔分数公式（用于第 10 章）**：`x_k` 为数分数，`A_k` 为原子量；元素 k 的电子贡献按 `x_k·A_k/A` 加权求和。

### 来源

1. ScienceDirect 文章页（含 Program Summary 全文） — https://www.sciencedirect.com/science/article/pii/S0010465518300122
2. Mendeley Data 程序归档 — https://data.mendeley.com/datasets/6vjsv6v48p ；解析页 https://dx.doi.org/10.17632/6vjsv6v48p.1
3. Mindat 书目 — https://www.mindat.org/reference.php?id=6602097
4. **作者官网（Dr. Steffen Faik）FEOS Code Package 专页** — https://physik.faik.de/feos.php?lang=eng
5. Mendeley 论文页（含完整参考文献与适用范围） — https://www.mendeley.com/catalogue/40e5334e-538f-3b60-bf58-5eed6c4a9579

### 与本地文件的对照

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| FEOS 是 MPQeos 后续 | 本地 `doc/FEOS/Info.txt` 有血统声明 | 论文摘要**明确**：*"a further development of the MPQeos code … from MPQ in Garching"* | ✅ 一致，升格 `[S-WEB]` |
| FEOS 版本号 `FEOS_16.7`？ | `web_verify.md` W6 提及 | **本轮未在任何官方源见到 `16.7` 版本号** | ⚠️ `[S-UNK]` —— **不得写入正文为版本号** |
| GPLv3 | W6 提及 | **官方 Program Summary 确认 GPLv3** | ✅ 一致，升格 `[S-WEB]` |
| 代码语言 C++ | — | 官方确认 **C++** | ➕ 补白 |
| 补充材料含 manual | — | 官方确认含 **Documentation/manual** | ➕ 补白（可指引读者到 `FEOS.tar.gz` 找 `.feos` 格式） |

### 未解决

- **S. Faik 博士论文**："Equations of state in dense plasmas"（TU Darmstadt / 或 UPMC）—— **本轮未找到**。检索返回的均为 SESAME/ADS 聚合页噪声。⇒ `[S-UNK]`。
- **`.feos` 文件格式附录**是否存在 ⇒ **无果**（须下载 `FEOS.tar.gz` 759 KB 后核对，本轮未做）。**建议**：由具备下载权限的成员抓取该归档以确认（这是 `.feos` 格式的**唯一权威来源**）。
- Faik 等人的 HEDP 论文（**Faik, Basko, Tauschwitz, Iosilevskiy, Maruhn, *HEDP* 8(4) (2012) 349–359, DOI `10.1016/j.hedp.2012.08.003`**）已核实，**但这是 2012 年的「液体–蒸汽亚稳态」论文，不是 FEOS 发布论文**，勿与 CPC 227 混淆。

---

## W10 — P3 SHOWEOS 派生后缀（`.ist` / `.isc` / `.ise` / `.mnt` / `.hug`）

### 结论

**（a）SHOWEOS 的官方定位——「确认」**

FEOS 官网（作者 Steffen Faik 本人）原文：
> *The FEOS (Frankfurt equation-of-state) package (formerly known under the name **MPQeos-JWGU**) … consists of **three parts**:
> 1. the **FEOS library** … (C/C++ 及 Fortran 接口)
> 2. the **FEOS table generation tool** … to generate EOS table files **(e.g. in the SESAME database format)**
> 3. and the **SHOWEOS table visualization tool** which was developed to plot **isotherms, isochores, isentropes, and Hugoniot curves**.*

Mendeley/CPC 论文描述亦一致：
> *…(3) the **SHOWEOS table visualization tool** which was developed to provide **isotherms, isochores, isentropes, and Hugoniot curves** from the FEOS or SESAME tables.*

**⇒ 关键推断（有依据的对应关系，但**官方未明写后缀**）**：

| 后缀 | 推断含义 | SHOWEOS 功能对应 | 置信度 |
|---|---|---|---|
| `.ist` | **isotherm**（等温线） | ✓ isotherms | **低**（推断） |
| `.isc` | **isochore**（等容线） | ✓ isochores | **低**（推断） |
| `.ise` | **isentrope**（等熵线） | ✓ isentropes | **低**（推断） |
| `.hug` | **Hugoniot** | ✓ Hugoniot curves | **低**（推断） |
| `.mnt` | **?** | 无对应功能名 | **无果** |

> ⚠️ **纪律声明**：上表 `.ist/.isc/.ise/.hug` 的对应关系是**基于 SHOWEOS 四项官方功能名的合理推断**，**不是官方明文**。正文若采用，**必须标为推断**（建议 `[S-INF]`），**不得写成「官方定义」**。`.mnt` 完全无对应，**标 `[S-UNK]`**。

**（b）`*4gnuplot` 变体命名规则——「无果」**

已尝试关键词（全部无结果）：
- `SHOWEOS FEOS tool ".ist" ".isc" ".ise" ".mnt" file format suffix`
- `"4gnuplot" SESAME table export suffix multi1d "mexport" "base" material database`
- `IONMIX ".isc" ".ise" OR ".cst" SESAME ASCII "table 301" suffix naming convention`

检索仅返回与 InstallShield（`.ise`）、数字高程模型（`.dem`）、gnuplot 绘图教程等**完全无关**的结果。
**⇒ `*4gnuplot` 命名规则标 `[S-UNK]`。这是 FEOS 包内部约定，须从 `FEOS.tar.gz` 源码/makefile 中反推，公开网络无记载。**

### 来源

1. **FEOS 官网（作者本人，SHOWEOS 三组件定位）** — https://physik.faik.de/feos.php?lang=eng（2026-09-18）
2. Mendeley FEOS 论文页（SHOWEOS 功能复述） — https://www.mendeley.com/catalogue/40e5334e-538f-3b60-bf58-5eed6c4a9579（2026-09-18）

### 与本地文件的对照

- 本地既有 `.ist/.isc/.ise/.mnt/.hug` 后缀，联网**未获任何官方定义**。
- **以本地为准**：本地若已从 `FEOS.tar.gz` 或实测数据确定了这些后缀的含义，**本地结论优先**，本文件仅提供 SHOWEOS 的**功能名清单**作为语义参照。
- **冲突记录**：无直接冲突（联网无明文可冲突）。

### 未解决

- 五个后缀的**官方定义** ⇒ **无果**（未尝试：下载 `FEOS.tar.gz` 后 grep 后缀字符串 —— **建议作为后续动作**）。
- `*4gnuplot` 命名规则 ⇒ **无果**。

---

## W11 — P4 PROPACEOS

### 结论

**本次取得重大进展：官方虽未公布字节级布局，但已公开 `.prp` 的完整字段清单与版本演进史。**

**（a）文件格式基础事实（Prism 官方文档原文）**

- 主 EOS/不透明度数据写入**单一文件**：`{Run_Name}.prp`（`Run_Name` 为仿真开始时指定的运行名）
- **文件性质**：`opacplot2` 文档标题明确称其为 **"PROPACEOS ASCII (.prp)"** ⇒ **`.prp` 是 ASCII 文本格式**，**不是二进制**。这一条推翻了「版权保护⇒二进制加密」的猜测。
- 文件包含（官方原文逐项）：
  1. **plasma composition data**
  2. **grid specifications for temperature, density, and photon energy grids**
  3. **ion, electron, and total internal specific energies**
  4. **ion, electron, and total pressures**
  5. **Rosseland, Planck absorption, and Planck emission multigroup opacities**

**（b）按 format 版本的字段演进（官方原文，极有价值）**

| format | 新增内容 |
|---|---|
| > 2 | Rosseland / Planck absorption / Planck emission **频率积分不透明度** |
| > 3 | **各级电离态的电离分数**（依 atomic model 文件所含离子级） |
| > 4 | **QEOS 参数** |
| > 5 | **标志位**：指示是否写出 EOS 数据、是否写出 opacity 数据 |
| > 6 | **各原子的同位素索引**（`-1` 表示天然形态） |
| > 7 | **各元素原子量** |
| > 8 | 文件**头部结构重大变更**。此前版本自变量仅限 **等离子体温度** 与 **离子数密度**；**format ≥ 9 起，EOS 与 opacity 表可在最多 6 个自变量的网格上生成**。EOS 与 opacity 数据可各自使用不同的自变量集合。**每个自变量，其 ID 与网格均写入文件。** |

**⇒ format ≥ 9 的「最多 6 个自变量 + 每自变量 ID + 网格」是本地文档极可能缺失的重要结构信息。**

**（c）配套文件与工具链（官方 `files_overview` 页）**

- 工作区文件：`*.prw`
- 原子模型文件：`*.atm`
- **ATBASE 原子数据库文件：`*.atb`**
- 输出：`{Run_Name}.prp`（数据）、`{Run_Name}.prc`（工作区副本）、`{Run_Name}.log`
- 输出目录：`{Run_Directory}/{Run_Name}`

**（d）PROPACEOS reader / converter 的分发限制——「确认不分发」**

`opacplot2` 官方 README 与文档**反复明确**：
> *Supported input file formats: **Propaceos (not distributed, contact jtlaune at uchicago dot edu)** — SESAME (.ses) — QEOS SESAME (.mexport) — MULTI (.opp, .opr, .opz, .eps)*

以及文档正文：
> **2.4 PROPACEOS ASCII (.prp)** — *Warning: **Handling for Propaceos EoS tables is not publicly distributed with opacplot2** and so its documentation will not be presented here.*

FLASH 邮件列表亦佐证（2023-05-03，UNIST 研究生回复）：
> *Supported input file formats: **Propaceos (not distributed)*** …

⇒ **`.prp` 的 reader 需向 `jtlaune@uchicago.edu` 索取**，属**有条件分发**（很可能要求 PROPACEOS 商业许可）。本地 `Readme.txt` 称「版权保护，格式未公开」——**联网结论与本地基本一致，但精度更高**：格式**字段清单已公开**，**字节级布局未公开**，**reader 有条件分发**。

**（e）第三方实现佐证（Tech-X USim）**

Tech-X 的 `propaceosVariables` 文档表明：**USim 可读 PROPACEOS 表**，并给出 operation 枚举，可用于交叉验证字段语义：
`Zbar`、`Eint`、`Eion`、`Eele`、`Pion`、`Pele`、`Ptot`、`IntRosseland`、`IntAbsPlanck`、`IntEmisPlank`、`Zeffective`、`Rosseland`、`AbsPlanck`、`EmisPlanck`、`IonizationFraction`。

单位约定（USim 原文）：
> *Units in USim are all MKS units. However, the **PROPACEOS tables use CGS units and eV for temperature**. These units are converted to MKS by USim.*

**⇒ 单位口径：CGS + eV（与 IONMIX4 的 J/cm³、J/g、eV 体系不同，勿混）。**

**（f）结论：本地 `Readme.txt` 与联网是否冲突？**

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| 「版权保护，格式未公开」 | 是 | **部分成立**：字节级布局未公开 ✅；但**字段清单、版本演进、单位口径、文件名规则均已公开** ⇒ 本地表述**过于绝对** | ⚠️ **建议在正文细化**，而非直接推翻 |
| 是否有公开逆向成果 | — | **opacplot2 有 reader 但「not distributed」**；**USim 有 reader 但未开源** | 记录 |

### 来源

1. **Prism 官方：EOS/Multigroup Opacity Files（`.prp` 字段清单与版本演进）** — https://prism-cs.com/Manuals/PrOpacEOS/files/eos_opacity_data_files.html
2. **Prism 官方：Files overview（`.prw/.atm/.atb/.prp/.prc/.log`）** — https://prism-cs.com/Manuals/PrOpacEOS/files/files_overview.html
3. Prism 官方：PrOpacEOS Major Features — https://www.prism-cs.com/Software/Propaceos/major_features.html
4. **opacplot2 官方文档（"PROPACEOS ASCII (.prp)"、"not distributed"）** — https://readthedocs.org/projects/opacplot2/downloads/pdf/latest/
5. opacplot2 README（GitHub） — http://github.org/jtlaune/opacplot2 ；Flash Center 版 https://de.github.com/flash-center/opacplot2
6. FLASH-USERS 邮件（PROPACEOS reader "not distributed"，2023-05） — https://flash.rochester.edu/pipermail/flash-users/2023-May/008334.html
7. **Tech-X USim `propaceosVariables`（字段语义与 CGS+eV 单位口径）** — https://www.txcorp.com/images/docs/usim/latest/reference_manual/source_propaceosVariables.html

### 与本地文件的对照

- ⚠️ **本地 `matter++/PROPACEOS/Readme.txt` 的「格式未公开」表述应收窄为**：「**字节级布局未公开；reader 有条件分发；但字段清单/版本演进/单位口径已由 Prism 官方文档公开**」。**以本地为准**（本地声明是供给方的正式声明），但**建议补注联网获得的公开信息**，避免读者误以为完全无据可查。
- ✅ 无实质冲突。

### 未解决

- `.prp` 的**字节级布局**（字段宽度、分隔符、行结构）⇒ **无果**。官方只给字段**清单**，不给**格式串**。
- `opg_propaceos.py`（reader 源码）⇒ **未获取**（需联系 `jtlaune@uchicago.edu`）。**建议**：若能取得，是唯一可得的逆向素材。

---

## W12 — P4 附：opacplot2 对 MULTI / PROPACEOS / TOPS 的格式支持清单（**高价值交叉线索**）

### 结论

`opacplot2`（FLASH Center 维护）官方 `opac-convert` 工具支持清单：

| 输入格式 | 后缀 | 备注 |
|---|---|---|
| **Propaceos** | `.prp` | **not distributed**，联系 jtlaune |
| **SESAME** | `.ses` | 公开 |
| **QEOS SESAME** | `.mexport` | —— **⚠️ 与本地 `mexport` 完全对应！** |
| **MULTI** | **`.opp`, `.opr`, `.opz`, `.eps`** | —— **本地 MULTI 数据后缀线索** |
| **TOPS** | `.html`, `.tops` | 另一分支 |

**输出格式**：**仅 IONMIX（`.cn4`）**。

**`opac-convert` 关键选项**：
```
--Znum   Comma separated list of atomic numbers.
--Xfracs Comma separated list of element fractions.
--outname
--log    Comma separated list of logarithmic data.
--tabnum SESAME table number (defaults to last).
```

**`--log` 可用数据键**（可作 IONMIX 字段语义的官方对照表）：
`idens`（离子数密度）、`temps`（温度）、`Zf_DT`（平均电离度）、`Pi_DT`（离子压强）、`Pec_DT`（电子压强）、`Ui_DT`（离子内能）、`Uec_DT`（电子内能）、`groups`（不透明度边界）、`opr_mg`（Rosseland 平均）、`opp_mg`（吸收 Planck 平均）、`emp_mg`（发射 Planck 平均）。

**HDF5 中间层命名约定**（opacplot2 官方）：`Znum`、`Xnum`、`idens`、`temp`、`Ng`（属性）、`groups`、`opp_mg`、`opr_mg`、`emp_mg`。

**SESAME 表型前缀约定（opacplot2 官方）**：
- 顶层数据点：`abar`(Mean Atomic Mass)、`bulkmod`、`excoef`、`rho0`、`zmax`(Mean Atomic number)
- 每表前缀：`dens`、`eint`、`ndens`、`ntemp`、`pres`、`stemp`
- 表型：`301 total`、`303 ioncc`、`304 ele`、`305 ion`、`306 cc`

### 来源

1. opacplot2 官方文档 — https://readthedocs.org/projects/opacplot2/downloads/pdf/latest/
2. opacplot2 README（Flash Center 版，含完整转换清单） — https://de.github.com/flash-center/opacplot2
3. FLASH-USERS 邮件（TOPS 补充条目） — https://flash.rochester.edu/pipermail/flash-users/2023-May/008334.html

### 与本地文件的对照

- ⚠️ **`mexport` 得到独立第三方（FLASH Center）确认**：`web_verify.md` W1 已从 SESAME ASCII 格式同构性推断 `.mexport` 是 SESAME 整库导出；本轮 opacplot2 将其**明确列为输入格式 `QEOS SESAME (.mexport)`** ⇒ **双重佐证，可升格为 `[S-WEB]`**。
- **重要冲突警告（沿用 W1 结论）**：opacplot2 把 `zmax` 命名为 "Mean Atomic number"，与本地 `AL_eos` 第 2 字段 `<Z>=2.7`（Al 应约 13）不符 ⇒ **仍以本地为准**，勿采信 opacplot2 的字段命名。
- ➕ **MULTI 数据后缀 `.opp/.opr/.opz/.eps` 是本地文档可能缺失的关键线索**，建议交由 `rev-unknown-ext` 与本地实测对照。

### 未解决

- `.opp/.opr/.opz/.eps` 四者的**语义分工**（哪个是 opacity、哪个是 EOS、哪个是 zbar）⇒ **无果**（opacplot2 未展开）。

---

## W13 — P5 SNOP 的群结构惯例

### 结论

**（a）Eidmann 1994 书目核实（与 `web_verify.md` W2 一致，本轮补充 INIS/OSTI 记录）**

| 字段 | 核实值 |
|---|---|
| 作者 | K. Eidmann |
| 题名 | *Radiation transport and atomic physics modeling in high-energy-density laser-produced plasmas* |
| 期刊 | Laser and Particle Beams |
| 卷 / 期 / 页 | **12**(2): **223–244** |
| 年 / 月 | **1994**，**June 1994** |
| DOI | `10.1017/S0263034600007709` |
| ISSN / CODEN | 0263-0346 / LPBEDA |
| 机构 | Max-Planck-Institut für Quantenoptik, 85740 Garching |
| INIS RN | 25063052 |

**摘要原文**：
> *The radiation hydrodynamics in laser-produced high-energy-density plasmas has been successfully simulated by means of the **MULTI hydrocode**. It is used in combination with the **SNOP atomic physics code**, which uses a **steady-state screened hydrogenic explicit ion model** and which generates **non-LTE opacity tables for MULTI**. … Examples of simulations … include a laser-irradiated gold foil and a radiatively heated carbon foil.*

**（b）SNOP 群结构惯例——第三方独立复现（与 W2 完全吻合）**

来源：arXiv:2207.14026（*Detailed investigation on x-ray emission from laser driven high-Z foils in a wide intensity range: role of conversion layer and reemission zone*，2022）原文：

> *NLTE opacity tables for all materials are generated from **SNOP radiative opacity code (Eidmann 1994)**. SNOP model is an **explicit ion model based on screened hydrogenic approximation** where population densities of different ionic species are determined by solving **steady state rate equation**. In ionization balance equation, atomic processes like electronic ionization, collision and radiative recombination are accounted for by use of explicit coefficients whereas **dielectronic recombination is treated via a parameter denoted by "d"**. **A total number of 3000 photon frequency points, with lower and upper boundaries at 1 eV and 5 keV, are used to calculate the opacities for all materials. Further, total 20 photon energy groups are employed to determine the Rosseland and Planck mean opacities.** Material density ranges from 10⁻⁶ g/cc to 100 g/cc while temperature varies from 1 eV to 100 keV.*

**⇒ 与 `web_verify.md` W2 的「3000 点 / 1 eV–5 keV / 20 群」完全一致，且本次获得第二独立来源（印度 ICTS/arXiv 团队）。可升格为「**高**」置信度。**

**（c）d 参数（系综再平衡参数）**

上文献原文：
> *the use of NLTE opacity reduces Z̄ compared to LTE opacity. To show the sensitivity of dielectronic recombination on NLTE results, **we have varied the value of d from 0 to 1000. We find that the mean ionization is significantly reduced from d = 0 to d = 1000.** … Therefore, we have used **d = 10** for all simulation results presented in this study.*

**⇒ 文献惯例：`d = 10`（常用）；`d ∈ [0, 1000]`（敏感性扫描区间）。**

**⚠️ 纪律**：本地 SNOP 参数名为 `DREK`。**文献中的 `d` 与本地 `DREK` 是否为同一量，联网无法证实** ⇒ **仍标 `[S-UNK]`**，勿强行等同（沿用 W2 结论）。

### 来源

1. Cambridge Core 文章页（卷期页 + 摘要 + 参考文献目录） — http://resolve.cambridge.org/core/product/B2CBA95E13FFBE2C67D4DF41FFD7E01E
2. INIS 记录（INIS RN 25063052） — https://inis.iaea.org/records/tdw9z-c9093
3. OSTI/ETDEWEB — https://www.osti.gov/etdeweb/biblio/7202570
4. **arXiv:2207.14026（3000 点 / 1 eV–5 keV / 20 群 / d 参数）** — https://arxiv-vanity.com/papers/2207.14026
5. CNKI Scholar — https://scholar.cnki.net/en/Detail/index/GARJ8099_1/SCUD15080300005433

### 与本地文件的对照

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| 群边界 `1.0 – 100 eV`（本地 `SNOP_LTE.PLANCK` 第 2 行） | 实测 | 文献惯例 **1 eV – 5 keV** | ⚠️ **冲突**。**以本地为准**；记录为「文献惯例 vs 本地实测」之差异 —— 说明群边界**依 namelist `X1/X2` 与 `IGROUP` 而变，非固定值**（沿用 W2 判定） |
| 3000 频率点 | — | 文献明确 3000 点 | ➕ 补白，**高**置信度 |
| 20 群 | — | 文献明确 20 群 | ➕ 补白，**高**置信度 |
| `DREK` vs `d` | 本地参数名 | 文献参数名 `d` | ⚠️ **不可等同**，标 `[S-UNK]` |

### 未解决

- SNOP 是否有**独立的 SNOP 手册**（含 namelist 全部参数定义）⇒ **本轮无果**。本地 `SNOP.MANUAL` 仍是最强一手依据。
- 3000 点频率网格的**具体分段规律**（是否也分段、如何分段）⇒ **无果**。

---

## W14 — P6 Hyades

### 结论

**（a）HYADES 正式文献出处——完全核实（**解决了 `web_verify.md` W5 的遗留项**）**

| 字段 | 核实值 |
|---|---|
| 作者 | **Jon T. Larsen**；**Stephen M. Lane** |
| 题名 | *HYADES — a plasma hydrodynamics code for dense plasma studies* |
| 期刊 | Journal of Quantitative Spectroscopy & Radiative Transfer |
| 卷 / 期 / 页 | **51**(1–2): **179–186** |
| 年 / 月 | **1994**，**February 1994** |
| DOI | **`10.1016/0022-4073(94)90078-7`** |
| Bibcode | `1994JQSRT..51..179L` |
| ISSN | 0022-4073 |

**⇒ `web_verify.md` W5 中「1994 *JQSRT* 51（Larsen）未核到具体条目 → 标 `[S-UNK]`」** 现已解决：**是 Larsen & Lane, JQSRT 51(1-2):179–186**（注意 W5 记为「51」卷正确，但**未指出期号 1-2 与合著者 Lane**）。

**摘要原文（ADS）**：
> *The one-dimensional radiation hydrodynamics code HYADES was originally developed to simulate laboratory experiments on dense plasmas driven by intense sources of energy. Examples of simulations of two recent laboratory experiments demonstrates the utility of the code.*

**关键词（ADS 原文）**：Computer Programs; Computerized Simulation; Dense Plasmas; High Power Lasers; Hydrodynamics; Atomic Physics; Conductive Heat Transfer; Mathematical Models; **Opacity**; Plasma Physics …

**（b）HYADES 始创年份与作者（W5 已核，本轮维持）**

W5 已确认：**HYADES 诞生于 1988 年，作者 Jon Larsen**；其经历：UC Lawrence Radiation Laboratory（即 LLNL）→ 1980 年代初 KMS Fusion, Inc.（Ann Arbor, Michigan）→ 独立创业开发 HYADES。

**（c）「Cascade Applied Sciences Inc.（CAS Inc.）」——「无果」**

本轮以 `Jon Larsen "Cascade Applied Sciences" HYADES equation of state opacity manual` 检索，**未返回任何 CAS Inc. 相关命中**（返回了 HYADES JQSRT 论文、系外行星大气、OPAL 不透明度等无关内容）。
**⇒ 沿用 W5 结论：供应商名称标 `[S-UNK]`。凡需引用供应商时，只引本地数据文件内嵌的血统串（`GOLD LANL SESAME #2700-304 DATED: 81678 101582`、`COPPER LLNL-QEOS Dated: 082802`）。**

**（d）「双温表号分段 2000–3000（电子）/ 3000–4000（离子）」——「无果」**

已尝试关键词：
- `Hyades SESAME table numbers 2000-3000 electron 3000-4000 ion two-temperature EOS format`
- `SESAME table numbers 2000-3000 electron 3000-4000 ion two-temperature`

返回结果均为**无关内容**（SWIFT 行星 EoS 文档、Altair Radioss `/EOS/SESAME` 块、锡的多相 SESAME 2162、约旦 SESAME 同步辐射光源——后者与 LANL SESAME **同名但完全无关**，是重要干扰源）。
**⇒ 该分段规则标 `[S-UNK]`。**
**重要提示**：`web_verify.md` W1 已由 LANL 官方确认 SESAME 的段位约定为 **EOS `0–9999`**（含 `50000`、`90000` 为 beta/experimental）、**Opacity `10000`/`60000`**、**Conductivity `20000`/`70000`**、**Melt & Shear `30000`/`80000`**。**该段位体系与「2000–3000 电子 / 3000–4000 离子」的**表号**分段是不同层级的编码**（前者是材料 ID 万位段，后者若是表号则属 `nnn` 表型编码，而 SESAME 官方表型 300 系列含义为 `301/303/304/305/306`）。**⇒ 本地若持「2000–3000 电子 / 3000–4000 离子」之说，与 LANL 官方 300 系列表型编码**不兼容**，须重点核对并**以本地为准**记录冲突。**

### 来源

1. **NASA ADS（Larsen & Lane 1994 JQSRT 51(1-2):179–186，DOI）** — https://adsabs.harvard.edu/abs/1994JQSRT..51..179L
2. W5 已引：Larsen, *Foundations of High-Energy-Density Physics*（Cambridge UP）作者自述 Preface — https://vdoc.pub/documents/foundations-of-high-energy-density-physics-physical-processes-of-matter-at-extreme-conditions-50dk6ibasuv0
3. W1 已引：LANL SESAME 官方页（材料 ID 段位） — https://www.lanl.gov/engage/organizations/aldsct/theoretical/pcm/sesame

### 与本地文件的对照

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| HYADES 1994 JQSRT 51 | W5 标 `[S-UNK]` | **已核实：51(1-2):179–186，DOI `10.1016/0022-4073(94)90078-7`** | ✅ **升级**，W5 遗留项解决 |
| CAS Inc. 供应商名 | 本地疑似 | **无果** | ⚠️ 标 `[S-UNK]` |
| 双温表号 2000–3000 / 3000–4000 | 本地疑似 | **无果**，且与 LANL 官方 300 系列表型编码**不兼容** | ⚠️ **重点冲突项**：以本地为准，**显式记录与 SESAME 官方表型体系的矛盾** |

### 未解决

- **HYADES 手册/技术报告的公开版本**及其 EOS/opacity 格式章节 ⇒ **无果**。HYADES 为商业闭源代码（Cascade Applied Sciences / 或 Larsen 个人），手册未公开。
- CAS Inc. 的**公司实体、成立年份、官方网址** ⇒ **无果**。
- 双温表号分段规则的**公开依据** ⇒ **无果**。

---

## W15 — P9 Multi1D++ 自身格式（`.base` / `.manifest` / `.template` / `.case`）

### 结论

**（a）MULTI 血统的书目核实**

| 字段 | 核实值 |
|---|---|
| 作者 | **R. Ramis**；**R. Schmalz**；**J. Meyer-Ter-Vehn** |
| 题名 | *MULTI — A computer code for one-dimensional multigroup radiation hydrodynamics* |
| 期刊 | Computer Physics Communications |
| 卷 / 期 / 页 | **49**(3): **475–**（起始页 475） |
| 年 / 月 | **1988**，**June 1988** |
| DOI | **`10.1016/0010-4655(88)90008-2`** |
| Bibcode | `1988CoPhC..49..475R` |
| CPC 程序号 | **`ABBV_v1_0`** |
| 程序归档 | Mendeley Data，DOI `10.17632/zdcrnjph48.1`（Published 1 January 1988） |
| 早期报告 | **MPQ-110**（Max-Planck-Institut für Quantenoptik, Garching，1986-02，63 页，INIS RN 18077870，**Restricted**） |

**摘要原文**：
> *The basic physical equations as well as a computer code for the simulation of one-dimensional radiation hydrodynamics are described. The hydrodynamic equations are combined with a multigroup method for the radiation transport. The code, written in standard FORTRAN-77, is characterized by **one-dimensional planar geometry with multilayer structure**. A **time-splitting schema** has been adopted with **implicit finite-differencing** formulation (including the hydrodynamics), and **Lagrangian coordinates**. **Tabulated equations of state and opacities are used.***

**（b）MULTI 官方项目页（R94 语言）**

检索获得 MULTI 官方网站文本（`…/multi/index.html` 的镜像，doc88 转载）原文：
> *MULTI is a computer program that simulates the behavior of matter at the high densities of energy typically found in Inertial Fusion Energy (IFE) … It is a multidimensional hydrodynamic code with coupled thermal radiation transport, heat conduction, and several energy deposition mechanisms: laser beams, ion beams, and fusion produced alpha-particles. Although the code has been designed as a unique entity, there are several versions (**1D, 2D, 3D, and fs**) … The code has been developed since **1985** in a collaborative work between the **Universidad Politécnica de Madrid** and the **Max-Planck-Institut für Quantenoptik** in Munich. The source code is available as free software …*
> *The current version has been written using a specially developed computer language called **r94**. The **r94 programming system** was created in **1994** by **Rafael Ramis** with the main purpose of to be used as a front-end of the radiation hydrodynamics code MULTI. The r94 computer language belongs to the class of the so called **non-typed languages** …*

**（c）`.base` / `.manifest` / `.template` / `.case` ——「无果」**

已尝试关键词：
- `"Multi1D++" OR "MULTI 1D++" Ramis laser plasma code download documentation`
- `Ramis MULTI 1D++ "MULTI-IFE" matter database material library input file format`

返回结果均**未提及上述四个后缀**（返回了 Ramis & Ramirez 2004 的 2D 论文上下文、MULTI2D-Z 改写、doc88 的 MULTI 介绍等）。
**⇒ 四个后缀标 `[S-UNK]`。凡涉及这些后缀的说明，一律以本地 `Multi1D++Portable20241128/` 源码与文档为唯一权威。**

**（d）MULTI 数据文件后缀（由 opacplot2 获得，见 W12）**

**MULTI 输出格式：`.opp`、`.opr`、`.opz`、`.eps`**（opacplot2 官方支持清单）。**这是本轮对 MULTI 数据格式最有价值的联网收获。** 具体语义分工未展开 ⇒ 标 `[S-UNK]`，但四个后缀本身**已获独立第三方确认**，可作为本地实测的对照锚点。

**（e）MULTI 的物理设定（可作正文旁证，高价值）**

来自 core.ac.uk 论文（*Implosion symmetry of laser-irradiated cylindrical targets*）原文：
> *The code MULTI (Ramis et al., 1988; Ramis & Ramirez, 2004) was developed in a collaboration between the Universidad Politécnica de Madrid and the Max-Planck-Institut für Quantenoptik in Munich. It integrates the plasma hydrodynamic motion, together with several energy transport mechanisms: **electronic heat conduction, thermal radiation, and laser beam deposition**. We use here **tabulated equations of state from the SESAME library** and **opacity tables generated by the SNOP code** (Eidmann, 1994).*
> *The code is available for either **1D geometry (using separate temperatures for electron and ion species, multigroup radiation transport, and radial laser irradiation)** or **2D axial symmetric geometry (one temperature, radiation transport in the gray approximation, and 3D ray tracing without refraction/reflection)**.*
> *…we consider three values for the **flux limiter factor f: 10⁶ (no limitation), 0.1 (standard value is this work), and 0.03 (strong inhibition)**. The results are qualitatively similar in all the cases; by decreasing the value of f from 0.1 to 0.03, temperatures in the corona increases a 20% and the ablated mass decreases a 5%.*

**⇒ 关键事实：MULTI 的 1D 版本使用「电子/离子分离温度」+ 多群辐射输运；2D 版本退化为单温 + 灰近似。这直接支撑本地对「双温」相关格式的判断。**

### 来源

1. NASA ADS（Ramis, Schmalz, Meyer-Ter-Vehn 1988 CPC 49:475） — https://adsabs.harvard.edu/abs/1988cophc..49..475r
2. INIS（MPQ-110 报告，Restricted，63 p） — https://inis.iaea.org/records/e7ypf-t0x42
3. CPC 程序归档 Mendeley Data — https://dx.doi.org/10.17632/ZDCRNJPH48
4. MULTI 官方项目页镜像（R94 语言、1985 起源、1D/2D/3D/fs 版本） — https://m.doc88.com/p-0157256302956.html
5. core.ac.uk 论文（MULTI 物理设定与 SESAME+SNOP 数据链） — https://core.ac.uk/download/148653263.pdf
6. opacplot2 官方文档（MULTI 后缀清单） — https://readthedocs.org/projects/opacplot2/downloads/pdf/latest/
7. Space Frontiers 书目 — https://spacefrontiers.org/r/10.1016/0010-4655(88)90008-2

### 与本地文件的对照

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| `.base` / `.manifest` / `.template` / `.case` | 本地有这些后缀 | **无果** | ⚠️ 标 `[S-UNK]`，**以本地源码为唯一权威** |
| MULTI 数据后缀 | — | **`.opp` / `.opr` / `.opz` / `.eps`**（opacplot2 确认） | ➕ 补白线索 |
| MULTI 数据链：SESAME EOS + SNOP opacity | 本地设计意图 | 文献**明确复现**：*"tabulated EOS from the SESAME library and opacity tables generated by the SNOP code"* | ✅ **强佐证**，支撑本地 SNOP+SESAME 双源设计 |
| MULTI 1D 双温（Te/Ti） | 本地涉及双温 | 文献明确 *"1D geometry (using separate temperatures for electron and ion species)"* | ✅ 一致 |
| 通量限制因子惯例 | — | `f = 0.1`（标准）、`0.03`（强抑制） | ➕ 补白 |

### 未解决

- `.base` / `.manifest` / `.template` / `.case` 的**官方定义** ⇒ **无果**（Ramis 1988 论文正文付费墙；MULTI 项目的输入文件文档未公开检索到）。
- Ramis 1988 CPC 49 论文**是否有附录描述输入/输出文件** ⇒ **正文未获取**，`仅书目核验`。**建议**：尝试通过 Mendeley Data 的 CPC 程序归档（`10.17632/zdcrnjph48.1`）下载源码包，其中的 README/输入样例或可直接确认。
- MULTI 2016 CPC（**MULTI-IFE**，Ramis & Meyer-ter-Vehn）与 2012 CPC（**MULTI-fs**）已见引用（Semantic Scholar 提示），**但本轮未单独核实其卷期页** ⇒ 若正文需引用，须另行核实。

---

## W16 — P7 `.coldopacity` 与冷不透明度

### 结论

**（a）「冷不透明度」的概念与 ICF 用途——「高」**

来自 Berkeley 论文 *Impact of First-Principles Properties of Deuterium-Tritium on Inertial Confinement Fusion Target Designs*（FPEOS_2015）原文：

> *One more example is the opacity of warm dense plasmas. The traditional **astrophysics opacity table (AOT)** as well as the **OPAL** project, which were built for astrophysics applications, **do not provide data in the WDM regime**. **Historically, the cold opacity of materials was patched for the WDM plasma condition in hydro-simulations.** … Most recently, the opacity of warm dense deuterium has been systematically investigated by QMD calculations for the full range of ρ/T conditions covering the ICF implosion path. Again, **orders-of-magnitude differences were identified when compared to the cold opacity that was patched to the AOT for ICF simulations**.*

**⇒ 关键结论（可写入正文）**：
1. 「cold opacity」**不是** SESAME 数据库的一个表型，而是 ICF 流体仿真中的一种**工程补丁手段**：在 WDM 区（NIF/ICF 内爆路径上的低温高密区）**用材料在 T→0 附近的不透明度替代/外插**，以填充 AOT/OPAL 覆盖不到的区域。
2. 该做法被明确批评为**可能产生数量级误差**（*"orders-of-magnitude differences"*）。
3. **⇒ `.coldopacity` 更可能是某个流体代码（或 Multi1D++）自建的「冷不透明度输入文件」约定，而非 SESAME 的子集。** 这个判断与「本地声明」须以本地实测为准。

**（b）SESAME 官方的温度下限——「确认」**

LANL SESAME 官方页原文：
> *There also exist SESAME Libraries for **opacity** and **conductivity** data. **The lower limit on the opacity data is about 1 eV.** The opacity library includes **Rosseland and Planck mean opacities**, **electron conductive opacity** and **mean ion charge** for elements with atomic number **Z ≤ 30**.*

以及 SESAME '83 报告（LALP-83-4）摘要：
> *The **lower temperature limit on the opacity data is about 1 eV**. … The Library includes **Rosseland mean opacities**, thermal and electrical conductivities, and **mean ion charges** for elements **Z ≤ 30**.*

**⇒ SESAME opacity 库的**官方温度下限约 1 eV**，**不提供 T = 0 的 cold opacity 表**。**这从官方侧证明：`.coldopacity` 不可能是 SESAME 的表型子集，而必然是另一路数据。**

**（c）`.coldopacity` 后缀本身——「无果」**

已尝试关键词：
- `"cold opacity" ICF table format SESAME zero temperature opacity coldopacity`
- `cold opacity table format ICF cold opacity opacity at T=0`

检索返回 LANL SESAME 官方页、SESAME '83 报告、Grokipedia 的 SESAME 条目、FPEOS_2015 论文——**均未出现 `.coldopacity` 这一后缀名**。
**⇒ 后缀本身标 `[S-UNK]`，但**其概念定位已由 (a)(b) 明确**。**

### 来源

1. **FPEOS 论文（cold opacity 补丁进 AOT 的明确表述）** — https://greif.geo.berkeley.edu/papers/FPEOS_2015.pdf
2. **LANL SESAME 官方页（opacity 下限 ~1 eV、Z ≤ 30、Rosseland/Planck/electron conductive opacity）** — https://www.lanl.gov/engage/organizations/aldsct/theoretical/pcm/sesame
3. OSTI SESAME '83 报告（LALP-83-4，下限 ~1 eV） — https://osti.gov/biblio/6349782
4. OSTI《The SESAME database》（Johnson 1994，LA-UR-94-1451） — https://osti.gov/biblio/10150216

### 与本地文件的对照

| 项 | 本地 | 联网 | 判定 |
|---|---|---|---|
| `.coldopacity` 是 SESAME 子集？ | 待定 | **不是**。SESAME opacity 下限 ~1 eV，无 T=0 表型 | ✓ **可据此判定「独立格式」** |
| 「cold opacity」概念 | 本地有 `.coldopacity` | ICF 语境有明确的「cold opacity 补丁」传统 | ✅ 概念吻合，可作正文依据 |
| 后缀的字节级格式 | 本地有 | **无果** | ⚠️ 以本地为准，标 `[S-UNK]` |

### 未解决

- `.coldopacity` 的**字节级格式**与其**生成工具** ⇒ **无果**。
- 是否有独立发表的「cold opacity」标准格式 ⇒ **无果**（判定：**很可能没有标准格式**，是各代码自建）。

---

## W17 — P8 `.dem` 后缀

### 结论

**完全无果。**

已尝试关键词：
- `"multi1d" "dem" file format`
- `radiation hydrodynamics .dem file`
- `"MULTI" Ramis radiation hydrodynamics lid "opacity" ".dem" file extension format`

检索返回的唯一与 `.dem` 相关的权威条目是 **USGS Digital Elevation Model**（数字高程模型，地理信息栅格数据）与若干国产文件后缀词典页——**与等离子体辐射流体力学完全无关**。

**⇒ `.dem` 标 `[S-UNK]`，无条件。**
**建议**：只有本地实测（十六进制 dump + 与已知格式比对）才能确定其含义。**禁止基于「detail / demonstration / demand」等词源猜测写入正文。**

### 来源

无（无果）。

### 未解决

- `.dem` 的**任何官方或第三方定义** ⇒ **无果**。

---

## 全部无果项汇总

| # | 目标 | 尝试过的关键词 | 结论 |
|---|---|---|---|
| 1 | IONMIX `abjt` 的 UW 分发页 | `IONMIX Prism Computational Sciences MacFarlane "cn4" OR "cnr" file format opacity`；`IONMIX "abjt" input file format "atomic #s of gases"` | **无果**（只有 CSDN 的 AI 生成中文页，非权威） |
| 2 | MPQ229 报告 | `Kemp Meyer-ter-Vehn MPQ229 LULI`（W6）＋本轮 NIM A 检索 | **无果**（无公开记录；FEOS 官网给的是 `GSI Report 2012-1, PNI-PP-12`，非 MPQ229） |
| 3 | S. Faik 博士论文（".feos" 格式附录） | `Faik thesis "Equations of state in dense plasmas" TU Darmstadt FEOS appendix file format` | **无果**（返回 science.gov/ADS/PubMed 聚合噪声） |
| 4 | SHOWEOS `.ist / .isc / .ise / .mnt / .hug` 官方定义 | `SHOWEOS FEOS tool ".ist" ".isc" ".ise" ".mnt" file format suffix` | **无果**（仅得 SHOWEOS 功能名，后缀未明写） |
| 5 | `*4gnuplot` 变体命名规则 | `"4gnuplot" SESAME table export suffix multi1d "mexport" "base" material database` | **无果**（仅得 OpenSesame/gsas 噪声） |
| 6 | `.prp` 字节级布局 | `PROPACEOS Prism Computational Sciences opacity equation of state file format documentation` | **部分**：字段清单已获，**字节级布局无果** |
| 7 | MULTI `.opp/.opr/.opz/.eps` 语义分工 | 同 W12 系列检索 | **无果**（后缀已确认，分工未明） |
| 8 | CAS Inc.（Cascade Applied Sciences） | `Jon Larsen "Cascade Applied Sciences" HYADES equation of state opacity manual` | **无果** |
| 9 | HYADES 手册公开版 / EOS-opacity 格式章节 | 同上 | **无果** |
| 10 | 双温表号分段 2000–3000 / 3000–4000 | `Hyades SESAME table numbers 2000-3000 electron 3000-4000 ion two-temperature EOS format` | **无果**，且与 LANL 官方 300 系列表型编码**不兼容** |
| 11 | `.base / .manifest / .template / .case` | `"Multi1D++" OR "MULTI 1D++" Ramis laser plasma code download documentation`；`"MULTI-IFE" matter database material library input file format` | **无果** |
| 12 | `.coldopacity` 后缀 | `"cold opacity" ICF table format SESAME zero temperature opacity coldopacity` | **无果**（概念已明确，后缀未明） |
| 13 | `.dem` | `"multi1d" "dem" file format`；`radiation hydrodynamics .dem file`；见 W17 | **完全无果** |
| 14 | MULTI-IFE (2016 CPC) / MULTI-fs (2012 CPC) 卷期页 | — | **未核实**（仅见 Semantic Scholar 引用提示，未单独核） |

---

## 附：本轮对既有结论的升降格建议

| 原标记 | 项 | 建议 |
|---|---|---|
| W1「`mexport` 是 SESAME ASCII 整库导出」为 `[S-L1]` | FEOS `.mexport` | **升格为 `[S-L1]` + `[S-WEB]`**（opacplot2 官方列为 `QEOS SESAME (.mexport)` 输入格式） |
| W5「1994 JQSRT 51（Larsen）`[S-UNK]`」 | Hyades 文献 | **升级为已核实**：`Larsen & Lane, JQSRT 51(1-2):179–186, DOI 10.1016/0022-4073(94)90078-7` |
| W2「SNOP 3000 点 / 1–5 keV / 20 群」为「高」 | SNOP 群结构 | **维持「高」**，新增第二独立来源（arXiv:2207.14026） |
| W2「`DREK` vs 文献 `d`」为 `[S-UNK]` | SNOP d 参数 | **维持 `[S-UNK]`**，文献惯例 `d = 10` 可作旁证但**不可等同** |
| W6「MPQeos/FEOS `[S-UNK]`」 | FEOS | **大幅升级**：FEOS 论文 `CPC 227:117–125, DOI 10.1016/j.cpc.2018.01.008`，GPLv3，C++，含 manual 补充材料 ⇒ **`[S-WEB]` 确认** |
| W4「IONMIX `[S-UNK]`」 | IONMIX 书目 | **升级为确认**：`CPC 56(2):259–278, DOI 10.1016/0010-4655(89)90023-4`，CPC 程序号 `ABJT_v1_0` ⇒ **`[S-WEB]`** |
| W6「PROPACEOS 可能二进制」 | `.prp` | **修正**：`.prp` 是 **ASCII**（opacplot2 官方标题 "PROPACEOS ASCII (.prp)"） |

---

## 附：给下游成员的三条行动建议

1. **`rev-source-code`**：在本地 `ionmix/abjt_03.f` 中检索 FORMAT 语句号 `921 / 922 / 923 / 980 / 981 / 982 / 991`，与 W7 的官方格式串做**双向校验**。若一致，则本地格式规范可标 `[S-L1]` + `[S-WEB]` 双重权威。
2. **`rev-unknown-ext`**：将 `.opp / .opr / .opz / .eps`（MULTI，W12/W15）与本地实测量对照——这是本轮**唯一新获的 MULTI 数据后缀线索**。
3. **有下载权限者**：抓取 `https://data.mendeley.com/datasets/6vjsv6v48p`（`FEOS.tar.gz`，759 KB）→ 这是 `.feos` / `.ist / .isc / .ise / .mnt / .hug` / `*4gnuplot` **全部格式的唯一权威来源**，可一举解决 W10 的 4 项无果。
