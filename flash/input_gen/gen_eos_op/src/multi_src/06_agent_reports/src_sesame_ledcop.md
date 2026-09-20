# MultiEOSOP 规格书 · 原始素材（第 4/7/8/11 章）
采集人：general-purpose-2　采集日期：2026-09-18
工作目录：`e:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op`
所有源文件**只读**，未做任何修改。逐条标注来源（文件路径 + 行号/段落号）。
凡源中未找到者明确标注「源中未找到」。

---

## A 节　文件清单（实测字节数 + 性质 + 抽取状态）

| # | 相对路径（前缀 `src/Multi1D++Portable20241128/`） | 字节数 | 性质 | 抽取 |
|---|---|---|---|---|
| 1 | `doc/MULTI使用的SESAME数据文件格式.docx` | 183,025 | ★★ SESAME 格式主规格（135 段 + 1 表） | OK，全文 + 表格 |
| 2 | `doc/Atomic(LEDCOP)说明.doc` | 59,904 | TOPS 网页帮助/FAQ/u 网格（英文，0 汉字） | OK（复用 `.workbuddy/tmp/docext/Atomic(LEDCOP)说明.txt`，20,640 字符，无乱码，完整） |
| 3 | `matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx` | 33,218 | ★★ LEDCOP 文件头/三段结构（179 段 + 1 表） | OK |
| 4 | `doc/GUI,IO相关.docx` | 65,744 | ★ 输出量字典（54 段 + 6 表，34+15+6+65+8 列表） | OK |
| 5 | `doc/multi1d7.6/manual` | 13,797 | 上游 7.6 手册（FT12/&CONTROL/&LAYERS/输出记录） | OK，UTF-8 |
| 6 | `doc/multi1d7.6/README` | 5,619 | MULTI 版本史 | OK，UTF-8 |
| 7 | `doc/多群辐射源(FDS).docx` | 22,847 | 多群辐射源输入（24 段 + 2 表） | OK |
| 8 | `doc/QuietStart.docx` | 205,813 | QuietStart 算法（40 段，无表） | OK |
| 9 | `doc/Restart.doc` | 61,952 | Restart 功能（1,230 汉字） | OK（复用 `docext/Restart.txt`） |
| 10 | `doc/Structure_of_ASCII_data_files.txt` | 82 | 极简 ASCII 结构示意（纯数字） | OK，全文 |
| 11 | `doc/solution of unsymmetry/关于不对称.txt` | 1,631 | 不对称问题排查笔记 | OK（**GBK**，1,289 字符） |
| 12 | `doc/muParser.txt` | 4,073 | muParser 数学解析器功能表 | OK，全文 |
| 13 | `matter++/material.base` | 103,452 | ★ 材料库（格式注释 98 行 + 大量 MATERIAL 记录） | OK（补充采到，见 I 节坑点） |
| 14 | `matter++/mat_Al-1.0/AL_SIMPLE_PLANCK` | 183 | 单群 Planck（PLANCK 1，3 行） | OK |
| 15 | `matter++/mat_Ti/SNOP_LTE.PLANCK` | 207,420 | Ti 多群 Planck（PLANCK M） | OK |
| 16 | `matter++/mat_Vacuum/Vacuum_Opacity.dat` | 186 | 真空不透明度（3 行） | OK |
| 17 | `matter++/mat_Al-1.0/AL_eos` | 152,165 | 反演 EOS（301 族） | OK，计数公式精确验证 |
| 18 | `matter++/mat_Au-1.0/AU_eosd` | 145,608 | 反演 EOS（另一变体，`eosd`） | OK，结构部分解出 |
| 19 | `matter++/ATOMIC/Al.txt` | 13,487,715 | ★ LEDCOP 大文件（348,636 行） | OK，头 47 行 + 三段边界定位 |
| 20 | `matter++/ATOMIC/Al.NoFree` | 55,383 | ATOMIC 去自由电子变体 | OK，头 30 行 |
| 21 | `matter++/ATOMIC/Al.GrayOpacity_PLANCK` | 55,383 | ATOMIC 灰度 Planck | OK，头 30 行 |
| 22 | `matter++/mat_C-1.0/Carbon.info` | 1,150 | 材料索引说明（16 行） | OK |

补充枚举：`matter++` 下共找到 **63 个** `.PLANCK/.ROSS/.EPS/.ZEFF` 族文件（见 C 节实测表）。

---

## B 节　`MULTI使用的SESAME数据文件格式.docx` 章节结构树与逐节提炼

原文参考声明（P1）：
> 参考：MULTI2002_MANUAL_V0 Richard Hrutkai, Diploma Thesis, 3.3.4 Material Module

开篇（P2）：
> MULTI的数据库中提供了EOS，不透明度、Non-LTE factors和effective ion number表格数据。

### 结构树（依 Heading 样式还原）

```
数据文件格式 (H1, P0)
├─ Multi的物质参数数据库 (H2, P3)
├─ 材料的定义 (H2, P8)
├─ EOS数据 (H2, P23)
│   ├─ 表格的转化（电子、离子表格） (H3, P54)
│   ├─ Inverted EOS (H3, P59)
│   └─ MPQeos计算结果SESAME的数据格式和单位制 (H3, P66)
├─ 不透明度数据 (H2, P83)
│   └─ 多群的情况 (H3, P101)
├─ Zeff (H2, P126)
└─ NLTE (H2, P132)
```

### B1　Multi 的物质参数数据库（P3–P7）

- P4：「MULTI中使用的不透明度和状态方程参数在模块 `[matter-2.1]` 数据库中，主要包括 `material.base` 材料定义文件和若干个包含有数据表格文件的文件夹。`$MULTI/r94/matter-2.1/material.base` 中包含了相关路径（material.base:matter-1.0与matter-2.1相同）。」
- P5（关键）：**「数据库中的格式有两种：一种为 Inverted EOS，采用直角坐标系，一种为不透明度，NLTE 因子，Zeff 等，采用 log 坐标系。」**
- P7（单位制总纲）：**「Multi1D程序代码中采用的单位制为 cgs+eV，但是其数据库 matter-2.1 中的 EOS 数据的单位制却并不是按照此单位制，因此程序在导入后进行了单位转化。」**

### B2　材料的定义（P8–P22）

- P9：以 Au 为例。
- P11–P18 表中标识（原文逐条）：

| 标识 | 原文含义 |
|---|---|
| `A` | 原子质量 |
| `Z` | 有效离子数 |
| `EOS` | 状态方程表（实际上是 Inverted EOS, P(rho,e) 与 T(rho,e)） |
| `PLANCK` | 表格 Planck 不透明度 |
| `ROSSELAND` | 表格 Rosseland 不透明度 |
| `NONLTE` | 表格 Non-LTE 因子 |
| `ZEFF` | 表格有效离子数 |

- P20：「material.base 中各个变量对应 mentry 中的前半部分内容」
- P22：**「数据文件都为 4 列多行，通过相关函数逐行读入然后解析。」**（← 注意：此"4 列多行"仅在列宽固定时成立，见 I 节坑点 1）

### B3　EOS 数据（P23–P53）

- P24：「EOS数据采用『三因素模型(Three component model)』」
- P26：「第一项为冷分布，其他两项分别是电子和例子的参数。」（原文"例子"疑为"离子"笔误）
- P27：「如 `mat_Au-1.0/AU_IDEAL_GA`，使用理想气体的状态方程。Multi1D 中为方便计算中直接使用，EOS 表格数据为 Inverted EOS 数据，即自变量为和，因变量为和：」（原文公式对象丢失，留空）
- P29/P31：「根据公式」「电子和离子对应的公式分别为」
- P35：**「表 `mat_Au-1.0/AU_IDEAL_GA` 中的相关常数为：Z=19.998, A=197, GAMMA=1.2168。」**
- P36：**「因变量和自变量都没有使用对数坐标系，而是使用线性坐标系」**
- P41–P46（★ 单位与字段语义，逐字照录）：

| 符号 | 原文定义 |
|---|---|
| `r[nr]` | 密度 (g/cc) |
| `de[ne]` | 能量(能量列表，与冷能量的差距, 单位 Mbar*cm3/g) |
| `e0[nr]` | 冷能量(密度对应的冷能量列表，单位 Mbar*cm3/g) |
| `P[ne*nr]` | 压力 P[(0~nr-1)+nr*i] 为密度为 r[0~nr-1]，能量 de[i]+e0[0~nr-1] 时的压力，单位为 Mbar |
| `T[ne*nr]` | 密度为 r[0~nr-1]，能量 de[i]+e0[0~nr-1] 时的温度（Kelvin） |

- P47（★ 计数公式）：**「即参数个数为 `4+2*nr+ne+2*nr*ne`」**
- P48–P49（P 数组排布）：
  > P[0] to P[nr-1] are the pressures at energy de[0]+e0[0 to nr-1]
  > P[nr] to P[nr*2-1] at de[1]+e0[0 to nr-1], etc
- P51–P52：「补充」「Mass-specific heat capacity」

### B4　表格的转化（电子、离子表格）（H3, P54–P57）

- P55：**「计算中使用的 Electron Table（ieeos）根据总的 EOS(ieos) 和原子质量 A 换算出来。详情请参考 eoselectron 程序代码。」**
- P56：**「没有使用离子表格。」**
- P57：「MPQeos 计算结果中包括了总的 EOS 和电子、离子表格，可以参考。」

### B5　Inverted EOS（H3, P59–P64）

- P60：**「为了在计算时直接使用 EOS 数据，省去转化，需要将 EOS 数据表格中的 P(R, T)，E(R, T) 转化为 P(R,E), T(R,E)」**
- P61–P64 算法（原文）：
  - 「对于 P(R, E)」→「对某个密度 R,」
  - 「首先根据 E(R, T) 找到对应的温度 T(R, E)，这个过程需要差值」
  - 「P(R, E) = P(R, T(R, E))，这里同样需要差值。」
  - 即：以 ρ 为外层循环，先在等密度线上由 E 反插出 T，再由 T 插出 P。原来自变量 (ρ,T) → 目标自变量 (ρ,E)。

### B6　MPQeos 计算结果 SESAME 的数据格式和单位制（H3, P66–P82）

- P68（**SESAME 数据库单位**）：**「压强（GPa），能量（MJ/kg），密度（g/cc），温度（Kelvin）」**
- P69（MULTI2D 使用单位）：**「MULTI2D 程序中使用 cgs 单位，而其调用的 EOS 数据中的单位为压强 Mbar，能量 Mbar*cm3/g，密度和温度单位与 SESAME 数据库相同。」**
- P71（压力换算，原文照录）：
  > 压力：1GPa = 1e9Pa = 1e10 dyne/cm2 = 1e10 erg/cm3 = 1e12 erg/cm2 = 1e-2 Mbar
- P72（能量密度换算，原文照录）：
  > 能量密度：1MJ/kg = 1e3 J/g = 1e10 erg/g = 1e12 erg*cm/g = 1e-2 Mbar*cm3/g
- P74：**「同时，SESAME 数据库使用 301 数据格式，四列多行数据。虽然 MPQeos 采用了四列多行的结构，但是其内容与 Multi1D 的要求并不一致」**
- P80：「因此 MPQeos 的计算结果并不能直接用于 Multi1D 的计算。」
- P81（★ 自动识别）：**「Multi1D++ 程序将自动识别文件后缀 301/304/305 并对单位制进行转化。」**
- P82（已知缺陷）：**「但是，从计算的结果来看，压强、能量甚至 Z 等有负值，原因正在查找。」**

### B7　不透明度数据（H2, P83–P125）

- P84：**「不透明度为 logloglog 全部采用对数存储数据」**（即 loglog(K), 温度、密度、不透明度三量全取对数）
- P85/P87：例 `Mat_Au-1.0/AU_SIMPLE_PLANCK`、`Mat_Au-1.0/AU_SIMPLE_ROSSELAND`
- P89：**「第一行第二列数据类型为 Multifs 中读取并判断数据类型用：」**
- P91 表 1「数据类型及其意义」→ 见 C 节完整转录。
- P93：**「在 MULTI7.6+ 代码中只有多群的需要此标识」**
- P95（单位）：**「其中 Z 的单位为 cm2/g，温度 T 单位为 eV，密度单位为 g/cc」**（注意：此处"Z"即不透明度 κ）
- P96–P100（定标公式推演，原文照录）：
  > 对定标公式 L = c * T^a*rho^b
  > Z = log(K)=log(1/(L*rho) ) = - log(c*T^a*rho^(b+1)) = -log(c) – a*log(T) –(b+1)*log(rho)
  > 本算例中 Rosseland opacity (cm): 6.0e-06 * T^1.0 / rho^1.0
  > Z(log(T)) = 6-log(6)-log(T)
  > Z(0)= 6-log(6)= 5.2218; Z(1) = 5-log(6)=4.2218
  （即：表中存的 Z = log10(κ) 中 κ 已含 1/ρ 因子，故与 (b+1)*log ρ 对应）

### B8　多群的情况（H3, P101–P125）

- P103：**「其中数据类型包括 PLANCE 1, PLANCK M, ROSSELAND 1, ROSSELAND M, EPS 1, EPS M. 等情况，分别表示 Planck 平均不透明度(cm2/gr)，Rosseland 平均不透明度(cm2/gr)，NLTE因子(non-lte factor)」**
- P104（★ 灰度约定）：**「如果为 PLANCK 1 或者频率上下限都为 0，则数据应用于所有的群。」**
- P105：「数据结构为 `sesame_tab`」
- P108–P110（频率网格，原文照录）：
  > 以 MID9 为例，频率范围为 10eV-5000eV
  > 1  10 50 100 150 250 400 550 700 900 1200 1600 2000 2200 2400 2600 2800 3100 3500 4000 5000
  > 并不是等间距（因此，最好使用 Multi1D 的程序进行插值，否则自编会带来较大的工作量）：
- P112–P124（网格范围与间距）：
  - 「密度和温度为指数坐标，指数等间距：」
  - **「密度：10-6-102 g/cc」**（实测 20 点，log10 从 −6.0 步长 +0.42105263 至 +2.0，见 G 节）
  - **「温度：0-105 eV」**（实测 20 点，log10 从 ~0 步长 +0.26315789 至 +5.0，见 G 节）
- P125：「如要得到某一温度密度下的参数随光子能量（频率）的向量数据，则需要处理。自编程序，提取出响应频率区间的值。」

### B9　Zeff（H2, P126–P131）

- P127（★ 单位）：**「温度和密度采用对数坐标系，Zeff 也采用了对数坐标系。温度单位是 keV, 密度单位是 g/cm3.（与不透明度不同，不透明度温度单位为 eV）」**
- P128（★ 历史坑点，原文照录）：
  > 注：之前的 Multi 计算中一直发现电离度偏高，况龙钰(20160109)发现是温度的单位弄错了，SNOP 等输出的 SESAME 数据，温度的单位一直是 keV。但是在 Multi 的输入是按照 eV 输入的，因此导致电离度明显偏高。
- P129：「因为之前(20160109)的计算中按照 eV 输入，因此在创建 Thermos 的数据文件时电离度也是按照 eV 创建的，不存在偏大的情况。但程序自 20160109 之后，统一将输入按照 keV 执行；相应的 Thermos 文件夹中所有的电离度文件(名字为 X_Z.dat)温度按照 keV 重新生成，以使其格式与 SNOP 等 SESAME 格式一致。名字为 X_Zeff.dat(温度单位为 keV)，以与之前的 X_Z.dat(温度单位为 eV)相区分。」
- P130：**「Material.base 中替换所有 X_Z.dat 为 X_Zeff.dat.」**
- P131：「Thermos 的数据生成软件也将输出的温度单位改为 keV。」

### B10　NLTE（H2, P132–P133）

- P133：**「温度和密度采用对数坐标系，NLTE 也采用了对角坐标系。格式可以为多群。」**（原文"对角"疑为"对数"笔误）

---

## C 节　SESAME 表型编号体系与多群不透明度格式

### C1　数据类型编码（docx 表 1「数据类型及其意义」逐格照录）

| 参数类型（第一行第二列） | 意义 |
|---|---|
| 默认为 1 | INVERTED EOS |
| `0.60000000E+01` | Z-MEAN |
| `PLANCK 1` | P.OPAZ. (1G) |
| `0.70000000E+01` | R.OPAZ. (1G) |
| `ROSSELAND 1` | R.OPAZ. (1G) |
| `0.40000000E+01` | EPS. (1G) |
| `PLANCK M` | P.OPAZ. (MG) |
| `ROSSELAND M` | R.OPAZ. (MG) |
| `EPS M` | EPS. (MG) |

（1G = 单群 gray；MG = 多群 multigroup。表中"默认为 1"即灰度 EOS 的标识。）

### C2　实测确认的表型编号位置（★ 一手证据）

**文件第一行第二个字段**即表型编号。实测（`matter++` 下 63 个族的抽样，第 1 行原文）：

| 文件 | 第 1 行（原文，前 60 字符） | 表型码 | 类型串 |
|---|---|---|---|
| `mat_Au-1.0/SNOP.PLANCK` | ` 27003000      PLANCK M        0.20000000E+02 0.20000000E+02` | 27003000 | PLANCK M |
| `mat_Au-1.0/SNOP.ROSS` | ` 27004000      ROSSELAND M     0.20000000E+02 0.20000000E+02` | 27004000 | ROSSELAND M |
| `mat_Au-1.0/SNOP.EPS` | ` 27005000      EPS M           0.20000000E+02 0.20000000E+02` | 27005000 | EPS M |
| `mat_Au-1.0/SNOP.ZEFF` | ` 27002000       0.60000000E+01 0.20000000E+02 0.20000000E+02` | 27002000 | （Z-MEAN 型，无类型串） |
| `mat_C-1.0/C_1G.PLANCK` | ` 10003000      PLANCK 1        0.20000000E+02 0.20000000E+02` | 10003000 | PLANCK 1 |
| `mat_C-1.0/C_20GSNOP.PLANCK` | ` 10003000      PLANCK M        0.20000000E+02 0.20000000E+02` | 10003000 | PLANCK M |
| `mat_C-1.0/C_20GSNOP.ROSS` | ` 10004000      ROSSELAND M     0.20000000E+02 0.20000000E+02` | 10004000 | ROSSELAND M |
| `mat_C-1.0/C_20GSNOP.ZEFF` | ` 10002000       0.60000000E+01 0.20000000E+02 0.20000000E+02` | 10002000 | Z-MEAN |
| `mat_Be-1.0/Be20keV.PLANCK` | ` 20143000      PLANCK M        2.00000000e+01 2.00000000e+01` | 20143000 | PLANCK M |
| `mat_Be-1.0/Be_40G.PLANCK` | ` 20203000      PLANCK M        0.20000000E+02 0.20000000E+02` | 20203000 | PLANCK M |
| `mat_Ce/Ce.PLANCK` | ` 27003000      PLANCK M        2.00000000e+01 2.00000000e+01` | 27003000 | PLANCK M |
| `mat_C-1.0/Carbon.Planck` | ` 50003000      PLANCK M        0.20000000E+02 0.20000000E+02` | 50003000 | PLANCK M |
| `mat_C-1.0/C.ZEFF` | ` 1              0.60000000E+01 0.20000000E+02 0.20000000E+02` | 1 | Z-MEAN |
| `mat_Al-1.0/AL_eos` | `      37181000    .27000000E+01  .66000000E+02  .74000000E+02` | 37181000 | （EOS，默认 1） |

**编号体系规律（实测归纳）**：
- 末两位（十位+个位）决定量类：`02` = Zeff/Z-MEAN，`03` = Planck，`04` = Rosseland，`05` = EPS(NLTE factor)；`10`/`12`… 段为 EOS 系（末两位 `10` 之类，如 37181000、27003000 的前缀 3718/2700 为材料 ID）。
- 高 4~6 位为**材料/来源 ID**（如 2700=Au/SNOP、1000=C、2020=Be 40 群、2014=Be 20keV、5000=CELIA-C、3718=Al、9173=ATOMIC-Al）。
- 灰度与多群由**类型串**（`PLANCK 1` vs `PLANCK M`）区分，编号中不可辨。
- 抽样中还出现 `1`（如 `C.ZEFF`）这类极简编号，属占位。

### C3　多群不透明度的频率上下限约定

实测（第 1 行第 3、4 字段，15 字符定宽）：

| 文件 | 第 3 字段 | 第 4 字段 | 解读 |
|---|---|---|---|
| `SNOP.PLANCK` / `SNOP.ROSS` / `SNOP.EPS` / `SNOP.ZEFF` | `0.20000000E+02` (20) | `0.20000000E+02` (20) | 频率下限 20 eV、上限 20 eV |
| `Be20keV.PLANCK` / `Ce.PLANCK` | `2.00000000e+01` (20) | `2.00000000e+01` (20) | 同上 |
| `C_1G.PLANCK` | `20` | `20` | 灰度文件同样填 20/20 |

结合 B8-P104「如果为 PLANCK 1 或者频率上下限都为 0，则数据应用于所有的群」，可判定：**这两个字段是频率下/上限（eV）；两值相等或为 0 时视为灰度/全群适用**。实测文件普遍填 20/20 而非 0/0，说明来源（SNOP）以 20/20 作为"全群"占位。

---

## D 节　反演 EOS（Inverted EOS）完整说明与参数计数

### D1　语义（来自 B5）

- 原始表格：P(R,T)、E(R,T)；目标表格：P(R,E)、T(R,E)。
- 转换：对每个密度 R，先由 E(R,T) 反插得 T(R,E)，再 P(R,E)=P(R,T(R,E))。
- 坐标系：**线性**（P36），不使用对数。

### D2　字段顺序（来自 B3，4 列多行固定流）

```
[ header 4 字段 ]  ← 第 1 行为 4 个整数
r[0..nr-1]         ← nr 个密度值 (g/cc)
de[0..ne-1]        ← ne 个能量差值 (Mbar*cm3/g)，相对冷能
e0[0..nr-1]        ← nr 个冷能量 (Mbar*cm3/g)
P[0..ne*nr-1]      ← ne*nr 个压力 (Mbar)，ρ 快变、i(能量) 慢变
T[0..ne*nr-1]      ← ne*nr 个温度 (K)，排布同上
```

- P 排布（P48–P49）：`P[(0~nr-1)+nr*i]` 对应密度 r[0~nr-1]、能量 de[i]+e0[0~nr-1]。
- 总参数个数（P47）：**`4 + 2*nr + ne + 2*nr*ne`**。

### D3　计数公式实测验证（★ 独立复算）

对 `mat_Al-1.0/AL_eos` 用严格 15 字符定宽分词得总字段数 **9978**；文件头 4 整数为 `[37181000, 2, 66, 74]`。代入公式穷举 6 种整数指派组合：

| 试验 (nr,ne) | 4+2nr+ne+2nr·ne | 与实测 9978 比较 |
|---|---|---|
| (66,74) | **9978** | ✅ 精确相等 |
| (74,66) | 9986 | ✗ |
| (2,66) | 338 | ✗ |

→ **判定：AL_eos 的 nr=66、ne=74；头部第 2 值=2（材料/版本占位），第 3 值=nr=66，第 4 值=ne=74。计数公式 P47 得到精确验证。**

实测密度网格（AL_eos 前 12 个非头部值）：
`0.0, 2.7e-06, 5.4e-06, 1.35e-05, 2.7e-05, 5.4e-05, 1.35e-04, 2.7e-04, 5.4e-04, 1.35e-03, 2.7e-03, 4.05e-03 …`
（从 0 起、非均匀递增的 ρ 网格，与 P42「r[nr] 密度(g/cc)」一致。）

### D4　`AU_eosd` 变体（`eosd` 后缀）

- 头部 4 值：`0.27000000E+04, 0.19300003E+02, 0.10100000E+03, 0.23000000E+02` → `[2700, 19.3, 101, 23]`。
- 第 1 值 2700 = 材料/来源 ID（与 material.base 中 `MATERIAL MID300` 附近记录相符）。
- **第 3 值 101 恰为密度网格点数**：实测第一段单调递增序列在索引 105 处以 `…, 193000, 386000, 0.0, 290.12, …` 首次出现下降，密度网格长度 = 105−4 = **101**，终点 386000 g/cc。
- 因此该变体符合「4 头 + nr 网格 + …」的同族骨架，但**其总字段数与 P47 公式不吻合**（实测 9430/9548 视分词方式而定），且第 2 值 19.3 为实数而非整数。**结论：`*_eosd` 是 301 族的一个变体/另一版本，字段计数公式与 P47 不通用；源文档未描述 `eosd` 后缀，源中未找到其规格。**

---

## E 节　单位体系

### E1　三套单位制对照（来源：B6-P68/P69、B3-P41~P46、B7-P95、B9-P127、GUI/P）

| 物理量 | SESAME 库单位 | MULTI EOS 表内单位 | Multi1D 内部 | 不透明度表 | Zeff 表 |
|---|---|---|---|---|---|
| 压力 | GPa | **Mbar** | cgs (dyne/cm2) | — | — |
| 能量（比） | MJ/kg | **Mbar·cm3/g** | erg/g | — | — |
| 密度 | g/cc | g/cc | g/cc | g/cc（对数） | g/cm3（对数） |
| 温度 | Kelvin | Kelvin | eV | **eV（对数）** | **keV（对数）** |
| 不透明度 κ | — | — | cm2/g | cm2/g（Z=log10 κ） | — |
| 有效电离度 | — | — | 无量纲 | — | 对数 |

### E2　换算关系（原文照录，B6-P71/P72）

```
压力   ： 1 GPa = 1e9 Pa = 1e10 dyne/cm2 = 1e10 erg/cm3 = 1e12 erg/cm2 = 1e-2 Mbar
能量密度： 1 MJ/kg = 1e3 J/g = 1e10 erg/g = 1e12 erg*cm/g = 1e-2 Mbar*cm3/g
```

即：**1 GPa = 1e-2 Mbar（10 MPa = 1e-2 Mbar）；1 MJ/kg = 1e-2 Mbar·cm3/g**。SESAME→MULTI 表内均为「×1e-2」。

### E3　程序端自动换算（B6-P81）

> Multi1D++ 程序将自动识别文件后缀 301/304/305 并对单位制进行转化。

### E4　不透明度定标公式（B7-P96~P100）

```
L = c · T^a · ρ^b
Z = log10(K) = log10(1/(L·ρ)) = −log10(c) − a·log10(T) − (b+1)·log10(ρ)
Au Rosseland 例：L = 6.0e-06 · T^1.0 / ρ^1.0（cm）
   ⇒ Z(log T) = 6 − log10(6) − log10(T)；Z(0)=5.2218, Z(1)=4.2218
```

---

## F 节　LEDCOP / ATOMIC 格式完整说明

### F1　文件名与三段式数据体（`Atomic(LEDCOP)不透明度格式说明.docx` 表 0）

文件名例：`Al.txt`。全文（第 2 列注释为文档作者所加）：

```
Number of T =  69  Number of rho =  50  Number of materials =   2
TOPS results for  LiH             on Sep  6, 2016
Opacities in cm**2/gm, T in keV, density in gm/cc        | 维度等
Normalized composition for requested elements
No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
  5.0000E-01   8.7320E-01      3         Li        4922      | 成分介绍
  5.0000E-01   1.2680E-01      1         H         4525
Temperature grid used the following  69 points            | 温度网格点
  5.0000E-04  6.0000E-04  8.0000E-04 …  1.0000E+01
Density grid used the following  50 points                | 密度网格点
  1.0000E-03  1.2068E-03  1.4563E-03 …  1.0000E+01
Rosseland and Planck opacities and free electrons          | 单群 gray opacity
 Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  5.0000E-04
  1.0000E-03  8.8707E+04  2.1555E+06  1.2280E-02  1.2280E-02
  …
Multigroup opacities                                        | 多群
  Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.0000E-03
  1.0000E-03  1.9954E+04  1.9957E+04
  …
  2.6412E+02  7.7877E-02  1.8976E-06
```

### F2　头部块逐行（三段定位 + `Al.txt` 实测原文）

`matter++/ATOMIC/Al.txt`（13,487,715 B，348,636 行）实测：

```
L1:  Number of T =  69  Number of rho =  50  Number of materials =   1
L2:  TOPS results for  Li              on Jul  2, 2017
L3:  Opacities in cm**2/gm, T in keV, density in gm/cc
L4: Normalized composition for requested elements
L5: No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
L6:   1.0000E+00   1.0000E+00     13         Al        9173
L7: Temperature grid used the following  69 points
L8–L19: 69 个温度点（keV），6 个/行
       5.0000E-04  6.0000E-04  8.0000E-04  1.0000E-03  1.2500E-03  1.5000E-03
       …  6.0000E+00  8.0000E+00  1.0000E+01
L20: Density grid used the following  50 points
L21–L29: 50 个密度点（g/cc），6 个/行
       1.0000E-03  1.2068E-03  1.4563E-03 …  8.2864E+00  1.0000E+01
L30: Photon grid used the following  99 points          ← ★ 见 F4 偏离
L31–L47: 99 个光子能量点（keV？见下），6 个/行
       1.0000E-03  1.1359E-03 …  2.6412E+02
L48: Rosseland and Planck opacities and free electrons   ← 第 1 个 gray 块头
L49:  Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  5.0000E-04
L50:   1.0000E-03  7.4869E+02  9.8625E+04  1.2330E-02  1.2330E-02
L51–L99: 继续 50 行密度点 → L48 起共 52 行/块（1 头 + 1 子头 + 50 行）
L100: Rosseland and Planck opacities and free electrons   ← 第 2 个 gray 块（T=6.0e-4）
L3636: Multigroup opacities                                ← 多群段起
L3637:   Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.0000E-03
L3638:   1.0000E-03  1.1162E+03  1.5340E+03
L3639:   1.1359E-03  8.0003E+02  8.2258E+02
…
L348624:   2.3253E+02  8.2766E-02  1.6706E-06
L348636:   2.6412E+02  7.7893E-02  1.1052E-06
```

### F3　三段结构的量化验证（实测计数）

| 项 | 实测 | 期望 | 结论 |
|---|---|---|---|
| gray 块头 `Rosseland and Planck …` 出现次数 | **69** | = Number of T = 69 | ✅ |
| 多群子块 `for T, density =` 出现次数 | **3450** | = 69×50 = 3450 | ✅ |
| 光子网格点数 | **99** | 文档表 0 示例未给，L30 自述 99 | ✅ 自洽 |
| gray 块行数 | 每块 1+1+50 = 52 行，69 块占 L48–L3635 | 69×52 = 3588 行 | ✅ |

### F4　u 网格七段定义（来自 `Atomic(LEDCOP)说明.doc`「Photon Energy Grid」）

定义：**u = hν / kT**（hν 为光子能量 eV，kT 为温度 eV）。选用 u 网格而非能量网格的理由（原文）：

> The u grid is selected instead of the photon energy grid because the same u grid can be used for all temperatures and cover the important photon energy ranges needed to integrate the Rosseland and Planck "gray" opacities. These photon energy ranges would be 0.–20. eV for a temperature of 1. eV and 0.–2000. eV for a 100. eV temperature. For the u grid, the range would be 0.–20. for both temperatures.

网页端 **14,900 点** u 网格（逐段照录）：

```
u Values      14,900 Point Grid
_________  ___________________________
    0.0
     |    9600 points, steps of .00125
   12.5
     |    1600 points, steps of .005
   20.0
     |    1000 points, steps of .01
   30.0
     |     700 points, steps of .1
  100.0
     |     900 points, steps of 1.0
 1000.0
     |     900 points, steps of 10.0
10000.0
     |     200 points, steps of 100.0
30000.0
         _____
         14900 points
```

分段合计校验：9600+1600+1000+700+900+900+200 = **14,900** ✅（七段）。

### F5　温度/密度网格可插值性（关键约定）

- **温度不可插值**（Q2 原文）：
  > The TOPS code can only use tabulated temperature points for cross section data. It will not interpolate on temperature. … reject it if it does not agree with one of the table values to within 1 percent.
  > NOTE: The TOPS code will interpolate in density.
- 温度表可直接照录（ATOMIC 2015 发布，69 点，keV）：
  `5.000E-04 6.000E-04 8.000E-04 1.000E-03 1.250E-03 1.500E-03 2.000E-03 2.500E-03 3.000E-03 3.500E-03 4.000E-03 5.000E-03 6.000E-03 7.000E-03 8.000E-03 9.000E-03 1.000E-02 1.250E-02 1.500E-02 2.000E-02 2.500E-02 3.000E-02 4.000E-02 5.000E-02 6.000E-02 7.000E-02 8.000E-02 9.000E-02 1.000E-01 1.250E-01 1.500E-01 1.750E-01 2.000E-01 2.250E-01 2.500E-01 2.750E-01 3.000E-01 3.500E-01 4.000E-01 4.500E-01 5.000E-01 5.500E-01 6.000E-01 6.500E-01 7.000E-01 8.000E-01 9.000E-01 1.000E+00 1.125E+00 1.250E+00 1.375E+00 1.500E+00 1.625E+00 1.750E+00 1.875E+00 2.000E+00 2.125E+00 2.250E+00 2.375E+00 2.500E+00 2.625E+00 2.750E+00 3.000E+00 3.500E+00 4.000E+00 5.000E+00 6.000E+00 8.000E+00 1.000E+01 1.500E+01 2.500E+01 4.000E+01 6.000E+01 1.000E+02`
  （逐段：P15–P25。**注意：此表为 76 值**，而 ATOMIC 网页自述默认网格前 69 点被 `Al.txt` 采用；`Al.txt` 实测 L8–L19 与上表前 69 点一致，止于 `1.0000E+01`。原文档顶部标题即写 "Number of T = 69"，与 `Al.txt` 一致。）

### F6　截止频率约定（Q1/Q5/Q10，原文照录）

- Q1：
  > The TOPS code calculates the plasma cutoff frequency for each temperature-density point. Any group that lies either partly or fully below that frequency has the opacity set to 1010 to indicate that photons at those frequencies cannot propagate in the plasma.
  （"1010" 指 1e10；即低于等离子体截止频率的能群，不透明度填 **1e10** 作为哨兵值。）
- Q10：低温高密度点无截面数据时，TOPS 取该温度下最高已算密度的值外延 → Rosseland 高密度曲线重合。
- Q4：低温下高密度无数据时「uses the gray opacity from those cross sections for all the multigroup and frequency dependent opacities」→ 多群各群值相同（退化）。

### F7　单位声明（`Al.txt` L3 原文）

> Opacities in cm**2/gm, T in keV, density in gm/cc

即 **ATOMIC/LEDCOP 的 T 单位为 keV**，与 SESAME 的 Zeff（keV）一致、与 SESAME 不透明度（eV）**不一致**——这是 E 节的关键分歧点。

### F8　`Al.NoFree` 与 `Al.GrayOpacity_PLANCK` 实测头部

两者字节数同为 55,383。第 1 行对照：

```
Al.NoFree            :  0.1234567E+000 1.0000000e+000 5.0000000e+001 6.9000000E+001
Al.GrayOpacity_PLANCK:  0.1234567E+000PLANCK 1        5.0000000e+001 6.9000000E+001
```

- 共同点：首字段 `0.1234567E+000`（魔数/占位，与 `Vacuum_Opacity.dat` 的第 1 字段相同）；第 3 字段 50（rho 数）、第 4 字段 69（T 数）。
- 差异：`.GrayOpacity_PLANCK` 在第 1 字段后直接写表型串 `PLANCK 1`（灰度单群），而 `.NoFree` 第 2 字段为 `1.0000000e+000`（无量值），**证明 ATOMIC 派生文件同样以"第 2 字段=类型标识"的方式标注族类**，与 SESAME docx 表 1 的编码规则同源。

---

## G 节　SESAME 样本文件实测头部（原文引用）

### G1　`mat_Al-1.0/AL_SIMPLE_PLANCK`（183 B，3 行，全文照录）

```
L1:   .17010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01
L2:   .0             .10000000E+01  .0             .10000000E+01
L3:   .87447000E+01  .92447000E+01  .63447000E+01  .68447000E+01
```

- 第 1 行第 2 字段 `0.70000000E+01` = **7.0** → 对应 docx 表 1「`0.70000000E+01` = R.OPAZ.(1G)」？——**矛盾**：文件名为 `PLANCK` 但类型码 7 在表中记为 R.OPAZ。结合 B7-P100「Z(0)=6−log(6)=5.2218;Z(1)=4.2218」，第 1 字段 0.1701e4 = 1701 更可能是材料/版本 ID。**判定：此处类型码与表 1 的对应关系在灰度文件上不成立，是本规格书需标注的一处矛盾（见 I 节坑点 3）。**
- L2 为频率下限/上限对（`.0` / `1.0` 与 `.0` / `1.0`）；L3 为该灰度不透明度的若干 log 值。

### G2　`mat_Vacuum/Vacuum_Opacity.dat`（186 B，3 行，全文照录）

```
L1:  0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001
L2:  0.0000000E+000 0.1000000E+001 0.0000000E+000 0.1000000E+001
L3: -1.0000000e+001-1.1000000e+001-1.0000000e+001-1.1000000e+001
```

- 同族骨架（3 行小文件），第 1 字段磨数 `0.1234567E+000` 与 ATOMIC 派生文件一致。
- L3 值为 −10、−11（log10 κ），即真空近乎透明。

### G3　`mat_Ti/SNOP_LTE.PLANCK`（207,420 B，3,360 行，头部照录）

```
L1:  27003000      PLANCK M        0.20000000E+02 0.20000000E+02
L2:  0.10000000E+01 0.10000000E+02
L3: -0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01
L4: -0.43157895E+01-0.38947368E+01-0.34736842E+01-0.30526316E+01
L5: -0.26315789E+01-0.22105263E+01-0.17894737E+01-0.13684211E+01
L6: -0.94736842E+00-0.52631579E+00-0.10526316E+00 0.31578947E+00
L7:  0.73684211E+00 0.11578947E+01 0.15789474E+01 0.20000000E+01
L8: -0.41821037E-34 0.26315789E+00 0.52631579E+00 0.78947368E+00
L9:  0.10526316E+01 0.13157895E+01 0.15789474E+01 0.18421053E+01
L10: 0.21052632E+01 0.23684211E+01 0.26315789E+01 0.28947368E+01
L11: 0.31578947E+01 0.34210526E+01 0.36842105E+01 0.39473684E+01
L12: 0.42105263E+01 0.44736842E+01 0.47368421E+01 0.50000000E+01
L13: 0.77094687E+01 0.78044479E+01 0.78642049E+01 0.79024432E+01
```

**逐字段解读（与 docx B8 完全吻合）**：
- 字段 0：`27003000` 表型码；字段 1：`PLANCK M`（多群）；字段 2、3：`20.0 20.0` 频率下/上限。
- **字段 4–25（L2+L3–L7，共 20 值）= 密度网格**，log10 ρ，从 −6.0 步长 +0.42105263 至 +2.0 → 对应 docx「密度：10^-6–10^2 g/cc」✅（步长 8/19 = 0.421052…，等间距）。
- **字段 26–45（L8–L12，共 20 值）= 温度网格**，log10 T(eV)，首值 `-0.41821037E-34`（浮点误差下等价 0）步长 +0.26315789 至 +5.0 → 对应 docx「温度：0–10^5 eV」✅（步长 5/19 = 0.263157…）。
- 字段 46 起（L13…）为不透明度数据体（log10 κ）。

### G4　计数公式验证汇总

| 文件 | 实测总字段 | 公式/结构 | 结论 |
|---|---|---|---|
| `AL_eos` | 9978 | 4+2·66+74+2·66·74 = **9978** | ✅ 精确匹配 P47 |
| `mat_Au-1.0/SNOP.ZEFF` | **444** | 4 + 20(ρ) + 20(T) + 20×20(数据) = 444 | ✅ 精确 |
| `mat_C-1.0/C_1G.PLANCK` | **444** | 同上（PLANCK 1 灰度） | ✅ 精确 |
| `mat_Au-1.0/SNOP.PLANCK` | 8920 | 4 + 2(频率界) + 40(网格) + 8874 | 8874 因数 2·3²·17·29，**不能整除 20²，计数公式未解出** |

→ **EOS（P47 公式）与 Zeff/灰度（20×20=400）两类均已精确验证；多群 `PLANCK M`/`ROSS M`/`EPS M` 的数据体计数在源文档中未给出公式，本次也未反解成功。**

---

## H 节　其余文档要点

### H1　`多群辐射源(FDS).docx`

- 标题：多群辐射源（Frequency Dependent Source）；「输入有能谱分布的辐射源。」
- 输入方式三种（P4）：两种用 SpectroSim 多道谱仪解谱结果（一种用「能谱 + 辐射流时间点」两个定义文件，另一种用「能谱 + 光子能量 + 辐射流时间点」三个文件；**推荐前者，后者新版本废除**）；第三种用 MULTI1D 的 `*.group.dat` 结果，选左右边界（`I-Left`/`I-Right`）出射能谱作源。
- 示例数据（P6–P13）：M 带较强 `Shot20120821015.Spline3OrderIterative.{Flux0,Flux3ns,TotalRadiation2DVertical0}.dat`；M 带较弱 `Flux0.dat`、`Flux3ns.dat`（"从 Flux0 文件将第一列乘以 3 得到"）、`TotalRadiation2D0Vertical.dat`。
- 格式约定（P17–P22，★）：
  - 「辐射流时间点数据只需要数据文件的第一列数据有效，**以秒为单位**。」
  - 「能谱文件为多行多列。其中**第一列为光子能量点（eV），第二列开始的各个列为对应光子能量点的能谱强度（W/m2/sr/eV）**，能谱列的列数应该与辐射流时间点的数目相同。如时间点数据文件有 n 行数据，那么，能谱文件就有 n+1 列数据。」
  - 表 0（时间点）：`0 / 1e-10 / 2e-10 / … / 3e-9`
  - 表 1（能谱）：`80  1e-10 1e-10 … 1e-10 / 100  2e-10 2e-10 … 2e-10 / 1200  2e-10 … / …`

### H2　`GUI,IO相关.docx` 输出量字典（★ 第 4 章用）

`*.center.dat`（34 项，表 1）：
`Time`(s)、`CMC`(网格中心质量坐标 g)、`XC`(网格中心位置 cm)、`R`(密度 g/cm3)、`Te`(电子温度 eV)、`Pe`(电子压力 dynes/cm2)、`Zi`(电离度)、`D`(能量沉积 erg/g)、`DENE`(电子数密度 1/cm3)、`Ee`(电子比能 erg/g)、`Ei`(离子比能 erg/g)、`Ti`(离子温度 eV)、`Pt`(总压力 dynes/cm2)、`dln(Pt)/dx`(dynes/cm3)、`Pi`(离子压力 dynes/cm2)、`Te(Emission)`(发射谱用电子温度 eV)、`dln(R)/dx`、`MID`(物质 ID)、`Ea`(Alpha 比能 erg)、`fT`、`fD`、`fHe3`、`fZ`(非反应燃料份额)、`dndt`(中子产率 1/cm3/s)、`dpdt`(质子产率 1/cm3/s)、`Index`、`TR_cell`(辐射温度 eV)、`kei`(电子离子耦合系数)、`ke`(电子热导系数)、`ki`(离子热导系数)、`coulog_ei`(库伦对数)、`pviscous`(黏性压力 dynes/cm2)、`len_e_stop`(电子阻止长度 cm)。

`*.interface.dat`（13 项，表 2）：
`Time`(s)、`CMI`(界面质量坐标 g)、`X`(界面位置 cm)、`V`(界面速度 cm/s)、`S+`(正向辐射流 erg/s/cm2)、`S-`(负向)、`S`(=S+ − S−)、`Tr`(辐射温度 eV)、`Vsound`(声速 cm/s)、`Albedo(Wall)`、`Albedo(Part)`、`RelativeFlux`(=flux/flux_free_streaming)、`FluxLimited`(erg/s/cm2)、`FluxNonlocal`(erg/s/cm2)。

`*.group.dat`（5 项，表 3）：
`Time`(s)、`FREI_left`(能群左边界 eV)、`FREI_center`(能群中点)、`FREI_right`(能群右边界 eV)、`I-Left`(左向光谱强度 erg/sec/eV)、`I-Right`(右向)。

`*.scalars.dat`（65 项，表 4，节选关键）：
`TIME`、`ISTEP`、`ENLAS`/`ENQUE`(入射/吸收激光能量 erg)、`ENIE`/`ENII`/`ENKI`、`ENRAD`、`ENRL1..4`/`ENRG1..4`、`EALFA`/`ENAL`/`ENAG`、`EYIELD`(中子产额)、`Nproton`、`POWRAD(t)`、`MaxDrho@`…、`TOTALMASS`/`TOTALENERGY`、`TR_Left`/`TR_Right`、`rhoR`/`rhoRHS`/`rhoRTotal`/`rhoRN`/`rhoRHM`/`rhoRAM`、`Centroid`、`V_imp`、`Ti_burn_avg`/`Ti_mass_avg`、`PosInterface`/`PosFallLine`/`PosBubble`/`PosMix`、`AlbedoLeft`/`AlbedoRight`、`Ti(DDburn_avg)`/`Ti(DHe3burn_avg)`、`AbsoluteError`/`RelativeError`、`FusionDeposEnergy`/`FusionTotalEnergy`/`FusionEAGain`/`FusionEALoss`、`Fusion.dndt`/`Fusion.dpdt`/`Fusion.FuelBound`、`AblatedMass`/`AblatedPressure`。

`*.final.dat`（P49）：「保存最后时刻的等离子体状态。」列对应 `x, v, MID, rho, te, ti, cmc`（见 H4 Restart）。

`*.backlighter.dat`（7 项，表 5）：`Time`、`CMC`、`XC`、`R`、`Te`、`MFP_Rosseland`(cm)、`MFP_Planck`(cm)、`Uemission`。

配置文件：`default.ini`（`[Config]/Functioning=4/MaxNumOfGrids=1000`；`[RecentFiles]`）；`config.ini`（`[Programs]` 中 `Type`：0=辐射流体力学、1=不透明度、2=状态方程；`[Tools]` GNUPlot/Notepad 路径）。

### H3　`muParser.txt`（数学表达式解析器，供 case 文件公式用）

- 内建函数（26 个）：`sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh log2 log10 log ln exp sqrt sign rint abs if(3) min max sum avg`（后 4 个变参）。
- 内建二元算符（15 个）及优先级：`=`(-1, 仅作用于变量)、`and/or/xor`(1)、`<= >= != == > <`(2)、`+ -`(3)、`* /`(4)、`^`(5)。
- 单字符后缀可作单位乘子（`3m -> 0.003`）；支持数值微分、自定义函数（≤5 定参 / 变参 / 字符串参）、自定义常量与变量。

### H4　`Restart.doc`（1,230 汉字）要点

- MULTI7.6 原生只读 profile 的位置/速度/密度/MID/Te/Ti，**缺辐射温度、聚变量**，restart 能力有限。
- Multi1D++ 输出 `*.final.dat`（列 = `x, v, MID, rho, te, ti, cmc`；记录结束时刻），Restart 基于此文件。
- 命令行：`Multi1D++.exe --Input Untitled.case --ASCII --Restart --TimeExit 3E-09 --AppendOutput [--RestartFrom Untitled.final.dat]`；`--Restart` 激活；`--TimeExit` 须比 case 更晚；`--AppendOutput` 决定续写/覆盖；`--RestartFrom` 文件名与 case 同名时可省。
- 与 IRAD3D 联动的 6 步方案（读 `*.final.dat` → 设默认等离子体状态 → 起始时刻取自 final.dat 第一行 → 指定新终止时刻 → 输出新 final.dat）。
- 燃料组分：当前支持 H/D/T/He3/Z，结束存 `*.fusion.final.dat`。

### H5　`关于不对称.txt`（GBK，1,289 字符）要点

- 针对 CH-Al-CH 算例，不对称量主要为 `XC, X, V, TR`；其余量对称条件下基本重合。
- `solveImplicitly` 的 dvec 中速度不对称作主要来源：**「速度的误差在 1e-7 左右。其中靠近边缘的网格的误差最大，靠近中间的逐渐缩小到 1e-20。」**
- 实测残差（原文照录）：
  ```
  state->v[0]+state->v[99] = 8.4239582065492868e-007
  state->v[5]+state->v[94] = -3.4582059438292845e-013
  rho_final[0]-rho_final[98]  6.0396132539608516e-013
  rho_final[1]-rho_final[97]  7.2386541205560206e-014
  rho_final[48]-rho_final[50] 1.7763568394002505e-015
  rho_final[49]               2.7000097312953821
  ```
- 根因：计算 `state->x` 时从 i=0 起递推 —— `i=0 时 dx=(v_new+v_old)/2*dt`，其余 `dx = m/rho`。「如果统一使用 dx=(v_new+v_old)/2*dt，则结果完全对称。但是否会有其他不守恒的问题？(质量守恒？)」
- 另一来源：`dvelocity[n]=area_per_mass[n]*pressure_total[n-1];   // Unsymmetry`。
- 缓解方案：「先查找是否有静止不动的界面，如果有则从这个界面开始向两侧计算。对于 Simple19.case 计算通过，但是其他算例涉及到其他的不对称来源，结果仍然不对称。」

### H6　`multi1d7.6/manual` + `README`

- README：MULTI 由 R.Ramis 于 1985 年 10–12 月在 MPQ Garching 编写；CPC 49 (1988) 475–505；MULTI6（柱/球几何、双温、DT 聚变、边界 Planck 浴+数据文件）；1996 译成 C 得 multi1d-7.4（引入 `material.base` 索引文件管理表格）；1997 拆分为 multi1d-7.6 + matter-1.0 模块。
- manual 关键格式：
  - 辐射输运用 **multigroup**，不透明度/发射率来自 **SNOP 代码**（G.D.Tsakiris & K.Eidmann, JQSRT 38, 353 (1987)）；数据「ussually generated from SESAME library」。
  - FT12 为 case 文件，`&CONTROL / &LAYERS / &PROFILE / &RBOUND / &RSOURCE / &PULSE / &IONBEAM` 分节，每项 `<name> = <value>`，可跟 `#` 注释。
  - `&LAYERS`：`IGEO`(1 平面/2 柱/3 球)、`NFUEL`、每层 `NC/MID/THICK/RHO/TE/TI/ZONPAR`。
  - `&PROFILE`：ASCII 表首行魔数 `"MSanchez"`，随后每行 `x v mid rho te ti`，末行 `x v`。
  - 输出 `fort.10` 二进制：记录 1/4 为字节计数，记录 2/5 为 8 字符变量名，记录 3/6 为 double 值；记录 3 含 `CMC/NC/CMI/NI/FREC(NG)/FREI(NG+1)`，后续记录含 `TIME…I-Left(NG)/I-Right(NG)`。

### H7　`QuietStart.docx`

- 问题：初始压强差导致网格自发运动；QuietStart 借鉴 BUCKY1D/Hyades，设初始开关温度，离子温度低于该值时强制压力加速度为 0（代码见 P：`if(dvdt[0]<0.0) dvdt[0]*=fractionc[0]; …`）。
- 影响：可能致初始几步密度无变化被判 `No Variation`，需把 `Max Allowed No Variation Steps` 设大；纯冲击波算例中「有无 QuietStart 会导致冲击波速度变慢！」；钻石层 `CwuCC.case`（1341 号材料）使用 QuietStart 致冲击波未穿透。
- 参考：2016PPCF58(J.Velechovsky)_[PALE]。

### H8　`Structure_of_ASCII_data_files.txt`（82 B，全文照录）

```
1	0	2	1	12
2	0	1
3	0	4

1	1	3	2	2
2	1	2
3	1	5

1	2	1	4	22
2	2	2
3	2	10
```
（三组记录，每组 3 行；列似为 [记录号, 组号, 字段1, 字段2, 字段3]。**源中未找到该文件的任何说明文字，语义无法确定。**）

---

## I 节　坑点与矛盾（本规格书须显式标注）

1. **「4 列多行」是理想化的说法，实际是定宽字段流。** docx P22 称「数据文件都为 4 列多行，通过相关函数逐行读入然后解析」，但实测每行字段数因文件而异（EOS=4/行；PLANCK=4/行；ZEFF=4/行；ATOMIC=3~5/行；灰度小文件 L1 为 4 值 L2 为 4 值 L3 为 4 值）。**按空白切分会把相邻的负数字段粘连（如 `-0.60000000E+01-0.55789474E+01` 被当成一个 token）**，必须用 **15 字符定宽**逐字符切分。这是解析 SESAME ASCII 表的头号陷阱。

2. **`AL_SIMPLE_PLANCK` 的类型码与 docx 表 1 不一致。** docx 表 1 记 `0.70000000E+01 = R.OPAZ.(1G)`，而该文件名为 PLANCK 且首行第 2 字段正是 `0.70000000E+01`。**灰度单群文件的类型码语义在实测中不可靠**（另 `C.ZEFF` 的类型码为裸 `1`、`SNOP.ZEFF` 为 27002000 且第 2 字段为空）。→ **建议：灰度文件不要依赖类型码，应依赖文件名/`material.base` 的 PLANCK/ROSSELAND 关键字。**

3. **温度单位三套并存，是最大事故源。** SESAME 不透明度表温度=**eV**（P95）；SESAME Zeff 表温度=**keV**（P127）；ATOMIC/LEDCOP 文件温度=**keV**（L3）。P128 明确记录了因把 keV 误当 eV 导致「电离度明显偏高」的历史事故，且修复方案是改名 `X_Z.dat`(eV) → `X_Zeff.dat`(keV) 并在 material.base 中全局替换。

4. **反演 EOS 的计数公式只对 301 族自动识别、且仅对 `AL_eos` 类文件验证成功；`AU_eosd` 不适用。** P81 说「自动识别文件后缀 301/304/305」，但实测目录中的文件名为 `AL_eos`、`AU_eosd`、`Au.301`（见 material.base L823），**后缀形态混杂**；`_eosd` 的字段计数与 P47 不符（实测 9430，公式候选均不匹配），docx 亦未描述 `eosd`。

5. **多群不透明度（PLANCK M/ROSS M/EPS M）的数据体计数公式，源文档中未找到。** docx 只给了 EOS 的 `4+2nr+ne+2nr*ne`，未给多群表的总字段公式。本次实测 `SNOP.PLANCK` 数据体 8874、`SNOP_LTE.PLANCK` 数据体 13334、`Be_40G.PLANCK` 数据体 17794 —— 三者因数分解均**不含 20×20**，无法用「nr·nt·ng」自洽闭合。**这是规格书必须标注为"未解"的空白。**

6. **灰度表（PLANCK 1 / Zeff / EPS 1）已精确验证为 4+20+20+400=444 字段**，多群表与灰度表的骨架不一致（多群表 L2 只有 2 个"频率界"字段，而灰度表 L2 直接是密度网格）。**切勿用同一套解析器读两类文件。**

7. **频率上下限普遍写成 20/20 而非 0/0。** docx P104 称「频率上下限都为 0 则应用于所有群」，但实测所有 SNOP 族文件都填 20/20，**"全群"的判据在真实数据中是 20/20 而非 0/0**，仅按 P104 编码会误判。

8. **`Al.txt` 文件名的 Li/Al 错位。** `Al.txt` 的 L2 写 `TOPS results for  Li`，但 L4–L6 成分块写 `Chem. Sym. Al / At.No. 13 / Mat ID 9173`。**文件名为 Al，L2 的 "Li" 是 TOPS 模板遗留字符串**，不可作为元素判据；应以成分块（L5–L6 的 Mat ID/符号）为准。

9. **`Al.txt` 多出 "Photon grid" 段（L30，99 点）不在 docx 表 0 的三段描述中。** docx 表 0 只描述 温度网格 / 密度网格 / 单群 gray / 多群 四块，实测 `Al.txt` 在密度网格后、gray 块前额外有 99 点光子网格。**解析时须允许"可选光子网格段"存在**（文档 `Atomic(LEDCOP)说明.doc` 的 u 网格 14,900 点与此 99 点不是同一物）。

10. **`AU_eosd` 的头部第 2 值为实数（19.300003），而 `AL_eos` 为整数 2。** 头部字段类型不稳定，解析器不能假设 4 个整数。

11. **docx 公式对象全部丢失。** 原 docx 中 P27/P29/P31/P35/P96 等多处出现"和"、"公式"等空指代（公式为嵌入 OLE 对象未导出为文本），**三因素模型的具体解析式、定标公式的完整形式在纯文本抽取中不可得**，需从 MULTI2002 手册原书补。

12. **`QuietStart.docx` 的代码片段与"影响"部分存在因果未证实。** 原文多次用"可能""还需要结合具体算例分析"，**不可当作确定性结论引用**。

---

## J 节　源中未找到 / 无法确定（诚实清单）

1. **多群不透明度表（`PLANCK M`/`ROSSELAND M`/`EPS M`）的完整字段计数公式与数据体排布（频率优先还是密度优先）** —— docx 未给公式；本次实测 3 个文件的字段数均无法自洽分解，**未解**。
2. **EOS 301 / 304 / 305 三者的具体差异** —— docx 仅提到「自动识别文件后缀 301/304/305 并对单位制进行转化」，**未列出 301/304/305 各自的表型定义、字段顺序差异**；`matter++` 目录下也未找到以 `304`/`305` 命名的样本文件（只在 material.base 中出现 `Au.301`）。
3. **三因素模型（Three component model）的解析表达式** —— docx 中公式均为嵌入对象，文本抽取后只剩"根据公式""分别为"等空壳，**未找到**。
4. **"Mass-specific heat capacity"（P52）的定义** —— 仅一行标题，**正文未找到**。
5. **`*_eosd` / `Au.301` / `AL_IDEAL_GAS` / `AU_IDEAL_GA` 文件本身** —— material.base 引用了这些名字，但目录中**未找到对应文件**（仅有 `AL_eos`、`AU_eosd` 等），无法实测。
6. **`Structure_of_ASCII_data_files.txt` 的语义** —— 82 字节纯数字，**源中无任何说明**（见 H8）。
7. **ATOMIC `Al.txt` 的 L2 时间是 `Jul 2, 2017`，与 doc 中"ATOMIC 2015 发布"的温度表时间不一致** —— 温度表内容与 2015 表前 69 点一致，但生成日期为 2017，**具体版本归属无法确定**。
8. **`Al.txt` 光子网格（99 点）的单位** —— L3 只声明「T in keV」，未声明光子网格单位；L31–L47 数值跨度 1e-3 → 2.64e2，**是 keV 还是 eV 无法从文件本身确定**（结合 u=hu/kT 与 T 网格 5e-4~1e1 keV，若为 keV 则 u 上限 ≈ 2.64e2/5e-4 = 5.3e5，偏大；若为 eV 则 u 上限 ≈ 2.64e2/(0.5) = 5.3e2，较合理，但**文件未明示**）。
9. **SESAME 表型编号（301/304/305/37181000/27003000 等）的官方编号体系文档** —— 本目录内**未找到** SESAME 官方《SESAME Report》类文件；所有编号规律均为本次**实测归纳**，非权威定义。
10. **EOS 表"4 个头字段"各值的官方语义** —— docx P47 只给出总数公式，**未逐字说明 header 4 值的含义**；本次实测推断为 `[材料/来源ID, 版本占位, nr, ne]`，属**推断而非源文**。
11. **`AL_SIMPLE_PLANCK` 第 3 行 4 个 log 值与频率网格的对应关系** —— 文件仅 3 行、无频率网格段，**无法确定**其覆盖的频率范围（只能从 P100 的 Z(0)/Z(1) 间接推测为 2 点或 log T 扫描）。
12. **`doc/Atomic(LEDCOP)说明.doc` 中 Q3 提到的 "lithium to magnesium only go down to .001 keV" 与本目录 Al 数据（5e-4 keV 起始）是否矛盾** —— doc 说 Li~Mg 最低只到 1e-3 keV，但 `Al.txt` 实测温度网格从 **5.000E-04 keV** 起。**二者矛盾，原因不明（Al 可能不属该受限组，或 2017 版已补齐）。**

---

### 附：本素材涉及的采样命令与产物

- 抽取产物（本目录 `.workbuddy/tmp/`）：`sesame_dump.txt`、`atomic_dump.txt`、`fds_gui.txt`、`src_sesame_ledcop.md`（本文件）；复用 `docext/Atomic(LEDCOP)说明.txt`、`docext/Restart.txt`。
- 解释器：`C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（docx/正则/定宽解析）。
- **所有源文件均未修改。**
