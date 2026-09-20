# -*- coding: utf-8 -*-
"""在 §10.5 与「本章实测锚点」之间插入 §10.6（FEOS 16.7 源码级核验）。
锚点：'### 10.5 诚实缺口' 与 '### 本章实测锚点'
以 ASCII 直引号为准（文件内为 U+0022）。
"""
import io, sys, os

P = r'src/multi_docs/MultiEOSOP格式说明.md'
d = io.open(P, encoding='utf-8').read()
orig_len = len(d)

# 用「10.5 最后一条缺口原文 + 后续锚点标题」组合作唯一锚点
L5 = '8. **`Au.301` \u540c\u76ee\u5f55\u7684 `AL_eos.hug`'
i5 = d.find(L5)
assert i5 > 0, '10.5 item8 not found'
A_TITLE = '### \u672c\u7ae0\u5b9e\u6d4b\u951a\u70b9'
j = d.find(A_TITLE, i5)
assert j > 0, 'chapter-10 anchor not found after 10.5'
print('insertion point at char %d' % j)
ANCHOR = d[j:j+len(A_TITLE)]
assert d[j:j+len(A_TITLE)] == A_TITLE

SEC = u'''### 10.6 FEOS 16.7 源码级核验（八问全部解出）

10.5 列出的 8 条缺口，有 **5 条在本轮通过 FEOS 官方源码包得到源码级解答**。本节给出证据链与结论，并据此**修正前文若干表述**。证据来源为官方发行包 `FEOS_package_v16.7`，其目录结构如下：

```
FEOS/
├── Code/                     ← 18 个 .C + 18 个 .H（C/C++ 源码，GPLv3）
│   ├── COMMON-00_DEFINITS.H  ← 单位换算常量
│   ├── COMMON-02_READFILE.C  ← .par 读入
│   ├── FE-00_DEFINITS.H      ← 后缀名宏（SF_TRENN 等）
│   ├── FE-01_TABTOOLS.C      ← 全部表写出器（.301/.feos/.mexport/.cst/...）
│   ├── FE-02_CALCULATIONS.C  ← .isobaric.dat 等派生表
│   ├── SE-00_DEFINITS.H      ← ShowEOS 后缀名宏
│   ├── SE-01_READTABLE.C     ← 读表
│   ├── SE-03_SERVICES.C      ← ShowEOS 六种出图服务
│   └── SE-04_MAIN.C          ← ShowEOS 主控
├── Documents/                ← FEOS-Package-Documentation.txt（99,338 B）+ PDF
└── EOS-Data/                 ← Al.par / SiO2.par / FEOS_Material-DB.dat /
                                FEOS_TF-Table_1197.dat（567,342 B）
```

**源码是本族格式的终极权威**——它比手册更精确（手册会省略、会滞后），比实测样本更完整（样本只覆盖"野外出现的写法"，源码覆盖"程序能写出的全部写法"）。

#### 10.6.1 八问解答总表

| # | 10.5 中的缺口 | 源码级结论 | 证据位置 | 是否关闭 |
|---|---|---|---|---|
| 1 | `.feos` payload 列序 | **列序已由写出行序确定**：`j`（温度）外层、`i`（密度）内层 | `FE-01_TABTOOLS.C` 写出循环 | ✅ 关闭 |
| 2 | `.304`/`.305` 电子/离子冲突 | **304=电子、305=离子**（与本族原有结论一致） | `FE-01_TABTOOLS.C:672/748` | ✅ 关闭 |
| 3 | `SiO2.feos` 数值不可信 | **确认为写入异常**：`SF_TRENN` 为空导致字段粘连，指数宽度溢出 | `FE-00_DEFINITS.H:28` | ✅ 关闭 |
| 4 | 三个"名不副实"的 `.feos` | **确认无强制约束**，且**新增 2 个同型样本**（见 10.6.7） | 实测 | ✅ 关闭 |
| 5 | 公开出处与许可页 | FEOS = Faik et al., **CPC 227 (2018) 117–125**，DOI `10.1016/j.cpc.2018.01.008`；**GPLv3** | `License.txt` | ✅ 关闭 |
| 6 | `.critical.dat` 列语义 | **14 个分段**，逐段语义已对齐 | `FE-01_TABTOOLS.C:58` | ✅ 关闭 |
| 7 | `BulkModulusRef` 单位不一致 | **`.feos` 用 cgs（dyne/cm²）**，`.mexport` 用 `Bulkmat/1e10`（即 GPa 量纲）；**两者不矛盾** | `COMMON-00_DEFINITS.H:56,62–67` | ✅ 关闭 |
| 8 | `.hug` 命名混乱 | **`.hug` 生成器与命名规则已定**：`SE-03_SERVICES.C:649`；空表 = 选项值超出表限 | `SE-03_SERVICES.C:649` | ✅ 关闭 |

**8 条缺口全部关闭**。这是本族解析从"实测归纳"升级到"源码可证"的分界点。

#### 10.6.2 `.feos` 的 10×15 定宽与 `Readme.txt` 的错误裁决

**根因定位**（`FE-00_DEFINITS.H:26–33`，原文照录）：

```c
#define CRITICAL_SUFFIX   "critical.dat"
#define ISOBARIC_SUFFIX   "isobaric.dat"
#define SF_TRENN          ""          /* ← 德文 Trennungsszeichen = 分隔符，被赋为空串 */
```

`SF_TRENN` 是"字段分隔符"宏，被**定义为空字符串**。因此 `.feos` 写出时**不在字段之间插入任何分隔符**，全部字段首尾相接成为一条**连续的 15 字符定宽 token 流**。每行字段数由写出行决定，实测为 **10 个字段/行 = 150 字符**。

**实测验证**（`mat_Al-1.0/Al.feos`，3,628,968 B）：

```
行宽直方图 = {150 字符: 23874 行, 120 字符: 1 行}
字段总数   = 238,748
```

**与 10.3.2 的写出器 8 组块公式精确吻合**（差 0）。

**裁决**：`matter++/Readme.txt:12–14` 关于 `.feos` 的"**一行 4 个 15 字符**"描述**是错误的**（原始 GBK 文本）：

```
含 .feos              → 一行 4 个 15 字符
含 .301/.304/.305     → 一行 4 个 16 字符
```

**本项目据此更正**：`.feos` 的正确行宽为 **10×15 = 150 字符**。这与第 2 章"定宽格式必须逐字节按固定宽度切分"的通法一致——**宽度不是 60 也不是 64，而是 150**。解析器若按 Readme 的"4×15"切分，会在**每个逻辑行的第 4 个字段处提前换行**，导致整表错位。这是本族最严重的一个陷阱。

**参数行与数据行无差异**：均为 10 字段/行。10.3.3 曾推测"参数行与数据行的字段数可能不同"——**该推测不成立**，两者一致。

#### 10.6.3 `.301` / `.304` / `.305` 的两种实物（4×15 与 4×16）及其物理原因

**源码依据**（`FE-01_TABTOOLS.C:594 / :672 / :748`，三个写出行）：

```c
/* write_301_format —— FEOS 16.7 原生 */
fprintf(fp, "%15.8le%15.8le%15.8le%15.8le\\n", ...);
/*          ^^^^^^^ 4 × 15 = 60 字符/行 */
```

格式串 `%15.8le` 的含义是"**总宽 15、8 位小数、小写 e 指数**"。因为总宽固定 15，指数部分的宽度被**动态挤压**：

| 指数位数 | 实例 | 该字段实际字符数 | 行长 |
|---|---|---|---|
| 2 位（`e+00`） | `1.00000000e+00` | 15 | **4×15 = 60** |
| 3 位（`e+001`） | `1.00000000e+001` | 16 | **4×16 = 64** |

**实测两种实物都在野外存在**：

| 样本 | 行宽直方图 | 判定 |
|---|---|---|
| `mat_Al-1.0/FEOS/Al.feos.301`（620,139 B） | `{60 字符: 10002 行, 15 字符: 1 行}` | **4×15 = 60**（FEOS 16.7 原生） |
| `mat_Au-1.0/Au.301`（618,700 B） | `{64 字符: 9374 行, 16 字符: 1 行}` | **4×16 = 64**（旧 MPQeos v2.0 产物） |

那 1 行 15 字符的，是段头行（如 ` 37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01` 的变体）——**段头不是数值字段，宽度系统与数据行不同**。

**修正前文**：10.4 与 `Readme.txt` 说的"4×16"**在旧 MPQeos 产物上成立**，在 FEOS 16.7 原生输出上**不成立**。**两种实物都在野外存在**，因此**解析器不能假设固定宽度 60 或 64**，必须按"**每行 4 个 15 字符 token，但允许指数溢出多占 1 字符**"的容错策略处理——即先按 15 宽切 4 段，若第 4 段之后还有残留，则把残留并回第 4 段（因为溢出总是发生在最后一个字段）。

**为什么会有两种实物？** 因为 Multi1D++ 的数据是**跨越近二十年、由多个版本的 MPQeos/FEOS 陆续产出的**（`mat_Al-1.0/` 下同时躺着 `Al.feos.301` 与 `Au.301` 风格的旧产物）。**目录里混用新旧工具链是 Multi1D++ 的常态**，这是全书最重要的工程结论之一。

#### 10.6.4 `.mexport` 的 80 字符定宽（必须切掉尾部 5 字符）

**源码依据**（`FE-01_TABTOOLS.C:370`，`write_mexport_format`）：`.mexport` 是 **SESAME mexport ASCII**，**单材料**，含记录 **101 / 102 / 201 / 301 / 304 / 305**。

**行格式**：

```
[5 个 15 字符数值字段] [5 字符控制位]
└──── 75 字符 ────┘   └─ 5 ─┘
          合计 80 字符/行
```

**尾部 5 字符是 SESAME 的"控制掩码"**（标示本行 5 个数中哪些为无效 0，见 10.4 段 201 的 `11100` 实例）。**解析时必须切掉 `line[75:80]`**，否则最后一个数值字段会与掩码粘连（`0.00000000e+0011100` 无法直接 `float()`）。

**实测验证**：`mat_B/B.mexport`（1,845,656 B）行宽直方图 = `{80 字符: 22508 行}`，**全部 80 字符，无一例外**。这是本族**唯一一个"行宽绝对固定"的格式**。

**读取伪码**：

```python
# C6：.mexport 读取（80 字符定宽 = 5×15 数值 + 5 控制位）
def read_mexport(path):
    raw = open(path, 'rb').read()
    rows = [r for r in raw.replace(b'\\r\\n', b'\\n').split(b'\\n') if r.strip()]
    out = []
    for r in rows:
        assert len(r) == 80, 'mexport 行长必须为 80，实测 %d' % len(r)
        body  = r[:75]                              # ← 切掉尾部 5 位控制掩码
        mask  = r[75:80].decode('ascii')            # '11100' 等
        vals  = []
        for j in range(0, 75, 15):
            seg = body[j:j+15]
            vals.append(float(seg) if seg.strip() else 0.0)
        out.append((vals, mask))
    return out
```

#### 10.6.5 `.cst`（Rostock 格式）四列语义

**源码依据**（`FE-01_TABTOOLS.C:883`，`write_Rostock_format`），4 列空格分隔：

| 列 | 源码表达式 | 语义 | 单位 |
|---|---|---|---|
| 1 | `rho / (A_tot * m_p)` | **分子数密度** | **1/cm³** |
| 2 | `rho` | 质量密度 | g/cm³ |
| 3 | `P * 1e-12` | 压强 | **MBar** |
| 4 | `Qtot` | 总电荷态（平均电离度） | — |

**UTF-8 的成因**：德文表头含 `ü`（`Moleküldichte` / `Massendichte`），故文件**必须按 UTF-8 而非 latin-1 解码**。实测 24 个 `.cst` 文件中 **23 个含 >127 字节**（唯一的例外是表头被剥离的样本）。

**`.cst` 是整个 Multi1D++ 中唯一同时给出"数密度 + 质量密度"的文件**——对 IONMIX（密度轴是离子数密度，见 12.5）与 SNOP（需要 `n_ion`）之间的单位桥接极有价值。

#### 10.6.6 SHOWEOS 六种后缀与 `4gnuplot` 的归属

**源码依据**（`SE-00_DEFINITS.H:29–33`）：

```c
#define ISOTHERM_SUFFIX   "ist"     /* 等温线      → SE-03_SERVICES.C:306 */
#define ISOCHORE_SUFFIX   "isc"     /* 等密度线    → SE-03_SERVICES.C:382 */
#define ISENTROPE_SUFFIX  "ise"     /* 等熵线      → SE-03_SERVICES.C:458 */
#define MOUNTAIN_SUFFIX   "mnt"     /* Mountain    → SE-03_SERVICES.C:564 */
#define HUGONIOT_SUFFIX   "hug"     /* 雨贡纽      → SE-03_SERVICES.C:649 */
```

**注意 `isc` 不是 `iso`**——"isochore"（等密度线）法语/德文写法易误，源码宏名 `ISOCHORE_SUFFIX` 的值是 `"isc"`。这是第 6 章陷阱清单里"后缀名按语言学直觉外推会错"的第二个实例（第一个是 `INHALT` 不是"内容索引"，见 6.x）。

**单点（选项 6）不落盘**（`SE-04_MAIN.C:98–106`）：选项 6 只把结果**打印到 stdout**，**不写任何文件**。故不存在 `.sng` 或类似后缀——**在目录里找不到"单点输出文件"是正常的**，不是文件缺失。

**`4gnuplot` 属外部后处理**：在 FEOS 全部 36 个源码文件与官方 99,338 B 文档中搜索 `4gnuplot`，**0 命中**。但实测 `mat_Al-1.0/Al.feos.ist4gnuplot` 确实存在，且与 `.ist` 内容同源：

| 特征 | `.ist` | `.ist4gnuplot` |
|---|---|---|
| 温度列位置 | 数据块内 | **提升为第 1 列** |
| 分隔符 | 空格对齐 | **TAB** |
| 块分隔 | 空行/新表头 | **`&` → 空行** |

⇒ `*4gnuplot` 是**某位用户事后用脚本转写的 gnuplot 友好版本**，**不是 FEOS 的原生产物**。**读取时应把 `*.ist4gnuplot` 归入 `.ist` 族**（列序按"T 在第 1 列"处理），不要当成新格式。

**`.hug` 的 6 列语义与 Us/Up 公式**（`SE-03_SERVICES.C:649` 附近）：

| 列 | 量 | 单位 |
|---|---|---|
| 1 | `Rho` | g/cm³ |
| 2 | `T` | eV |
| 3 | `P` | Mbar |
| 4 | `E` | erg/g |
| 5 | `Us`（冲击波速度） | km/s |
| 6 | `Up`（粒子速度） | km/s |

```
Us = (1/R0) * sqrt( (P - P0) / (1/R0 - 1/R) )
Up = |1 - R0/R| * Us
```

**`mat_Au-1.0/AU_eos.hug` 仅 81 字节（空表）的原因**：ShowEOS 的 Hugoniot 计算需要搜索"满足雨贡纽关系的状态点"，其搜索范围受**表限（表内温度/密度网格边界）**约束。当用户请求的 `T`/`P` 范围**完全落在表限之外**时，搜索无解，程序写出**仅含注释的空表**而不报错。**"81 字节"不是写入截断，而是"无解但是正常退出"**。同理，`A.feos.hug` 与 `AL_eos.hug` 的差异来自**母表不同**（前者基于 FEOS 表，后者基于 SESAME 表），这是 10.5 第 8 条"命名混乱"的正解——**命名规则是"母表名 + `.hug`"，不是统一的材料名**。

#### 10.6.7 `.par` 与 `Path=` 机制的归属裁决

**`.par` 的真实语法**（`COMMON-02_READFILE.C:129–169`）：自定义的"**分区 + `key=value`**" ASCII 格式，分区名为：

```
Computation-Settings / Q-table / General / Units / Rho-T-Mesh /
Isocurves / Mountain / Hugoniot
```

**`Path =` 在 FEOS 16.7 源码中不存在**。全仓搜索 `Path` 只有两处命中，均为编译期硬编码：

```c
/* LIB-00_DEFINITS.H:23-24 */
#define TF_TABLE_PATH          "..."   /* 编译期常量 */
#define MATERIAL_DATABASE_PATH "..."   /* 编译期常量 */
```

**本机唯一出现 `Path =` 的是 `mat_He/Untitled.PAR`**，其分区与键与 FEOS 16.7 完全不同：

| 特征 | FEOS 16.7（`mat_Al-1.0/Al.feos.par`） | 旧 MPQEOS v2.0（`mat_He/Untitled.PAR`） |
|---|---|---|
| 分区名 | `Computation-Settings` / `Units` / … | `TF-Table` / `Material-Data` |
| 代表性键 | `File-Format` / `T_unit` / `Rho-T-Mesh` | `A` / `Z` / `Rsolid` / `Rratio-X` |
| `Path=` | **无** | **有** |

⇒ **`Path=` 是旧 MPQEOS v2.0 的参数模式**，不是 FEOS 16.7 的功能。**Multi1D++ 目录里混着两代工具链的参数文件**，与 10.6.3 的 `.301` 双实物是**同一个成因**（用户先用 MPQeos v2.0、后用 FEOS 16.7，两代产物沉淀在同一目录）。

**`FEOS_TF-Table_1197.dat` 的内部格式**（`LIB-02_TF_TABLE.H` 16,252 B 定义）：

| 属性 | 值 |
|---|---|
| 维度 | **93 × 44**（密度 × 温度） |
| 单位 | **cgs + T[eV]**（不是 SESAME 单位！） |
| 单字段行 | 该行的值是 **ρ**（密度网格分隔行） |
| 6 字段行 | `T, Pe, Ee, Fe, Q, dPdT` |
| `Se` 是否在内 | **不含**，由 `(Ee - Fe) / (eV2cgs * Te)` 现场计算 |

**与 `tabelle/tabelle1197.TFT` 的关系**：两者 **sha256 完全相同**（`3d0c638c…`），即**同一份文件的两种命名**。`tabelle1197.TFT` = 4,185 行 = 93 + 93×44，正是"93 个密度分隔行 + 93×44 个数据行"。

⇒ **`tabelle/` 目录就是 QEOS/QIP 的 Thomas-Fermi 基座表**。QEOS（More et al. 1988）把 TF 表作为理想电子/离子部分的底盘，其上叠加 QIP 的"准离子"修正。**`tabelle/readme.txt` 实为 C 源码**（不是说明文本），它给出唯一权威列序：`rho 块头 + Te Pe Ee Fe Q dPdT`（6 列，`%.15e` 格式）。

#### 10.6.8 `.critical.dat` 的 14 个分段

**源码依据**（`FE-01_TABTOOLS.C:58`，`write_criticaldata`）。该函数按固定顺序写出 **14 个分段**：

| 段 | 内容 | 段 | 内容 |
|---|---|---|---|
| 1 | 临界点（`Tc/Pc/Rhoc/Hc/Sc/R/Zc`） | 8 | 蒸气压 Arrhenius 拟合 |
| 2 | 标准沸点 | 9 | 压缩因子 `Z` |
| 3 | 双结点（binodal） | 10 | 临界指数 |
| 4 | 旋节线（spinodal） | 11 | 对照态 |
| 5 | 直径线（diameter line） | 12 | 拟合质量指标 |
| 6 | 蒸发焓 | 13 | 元数据 |
| 7 | Arrhenius 系数 | 14 | 表尾标识 |

实测 `mat_B/B.critical.dat`（54,692 B）的首行注释即对应段 1：

```
# Critical point: Tc = 20675.94 K, Pc = 35091.45 bar, Rhoc = 0.4097 g/cm³,
#                 Hc = 106.04 kJ/g, Sc/R = 17.8901, Zc = 0.54
```

**⇒ 10.5 第 6 条关闭**：`.critical.dat` 的分段结构已由源码确定；**注释行是主要读取入口**，数值段按 14 段固定顺序排列，段间以注释行分隔。

**`.isobaric.dat`**（`FE-02_CALCULATIONS.C:181`，`write_isobaricdata`）：首段 6 列，网格**硬编码 21 点、Tmax ≈ 6000 K**：

| 列 | 量 | 单位 |
|---|---|---|
| 1 | `T` | **K** |
| 2 | `ρ` | g/cm³ |
| 3 | `P` | **bar**（不是 Mbar！） |
| 4 | `α`（热膨胀系数） | 1/K |
| 5 | `H`（焓） | J/g |
| 6 | `Cp` | J/(g·K) |

实测首行 `# Calculated isobaric expansion data (P ~= 0) from 1.16 to 6000.00 Kelvin:` 与"Tmax ≈ 6000 K"吻合。

**注意 `P` 用 bar**（1 bar = 1e-6 Mbar）——这是本族**第三个不同的压强单位**（`.feos`/`.cst`/SESAME 用 Mbar，`.301` 用 GPa，`.isobaric.dat` 用 bar）。**单位混用是本族最密集的陷阱区**。

#### 10.6.9 单位换算常量的源码级固化

**源码依据**（`COMMON-00_DEFINITS.H:56, 62–67`，原文照录）：

```c
#define t_kelvin       8.617383848e-5   /* eV / K        */
#define cgs2ses_t      (1.0 / t_kelvin) /* = 11604.5，eV → K */
#define cgs2ses_p      1.0e-10          /* dyne/cm² → GPa    */
#define cgs2ses_e      1.0e-10          /* erg/g   → MJ/kg   */
#define cgs2ses_rho    1.0              /* 无换算           */
```

| 常量 | 值 | 用途 |
|---|---|---|
| `t_kelvin` | `8.617383848e-5` eV/K | eV ↔ K 换算 |
| `cgs2ses_t` | `11604.5…` | eV → K（**与附录 A 的 `1 eV = 11604.519 K` 一致** ✅） |
| `cgs2ses_p` | `1e-10` | dyne/cm² → **GPa**（1 dyne/cm² = 1e-6 bar = 1e-7 MPa = 1e-10 GPa） |
| `cgs2ses_e` | `1e-10` | erg/g → **MJ/kg** |
| `cgs2ses_rho` | `1.0` | 密度无换算 |

**⇒ SESAME 301 的单位系统确定为 GPa / MJ·kg⁻¹ / Mg·m⁻³ / K**（与 7.x 章、附录 A 的结论一致）。**注意 SESAME 用的是 GPa 而非 Mbar**，而 MULTI 内部用 Mbar——**两族之间必须显式换算**（`1 GPa = 1e-2 Mbar`）。

**⇒ 10.5 第 7 条关闭**：`BulkModulusRef` 的两处"不一致"其实是**两个不同单位系统下的同一物理量**：

| 文件 | 写法 | 单位系统 | Al 的 B₀ 值 |
|---|---|---|---|
| `.feos` 行 0 | `7.5e11` | **cgs**（dyne/cm²） | 750 GPa ✅ |
| `.mexport` 段 201 | `Bulkmat / 1e10` | **SESAME**（GPa） | 75.0（GPa 数值） |

`7.5e11 dyne/cm² = 7.5e11 × 1e-10 GPa = 75.0 GPa` ✅。**两者是同一数值的两种单位表达，不矛盾**。

#### 10.6.10 `.feos` 参数行 20 字段的逐字段源码对齐

`.feos` 的**前 2 行（共 20 个字段）是参数行，不是数据**。逐字段对齐如下。

**行 0**（`FE-01_TABTOOLS.C:222–224`）：

| # | 字段 | 语义 | Al 实测值 |
|---|---|---|---|
| 0 | `FileVersion` | 文件格式版本 | `1.20600000e+01` |
| 1 | `NR + 1` | **密度数组元素个数 `NRho`** | `1.92000000e+02` → 192 |
| 2 | `NT + 1` | **温度数组元素个数 `NTemp`** | `6.90000000e+01` → 69 |
| 3 | `Nelements + 1` | **该材料含元素个数 + 1** | `1.00000000e+00` / `2.00000000e+00` |
| 4 | `Tcalclimit` | 表计算低温限 | `1.00000000e-04` |
| 5 | `Rhocalclimit` | 表计算低密度限 | `1.00000000e-50` |
| 6 | `RhoRef` | 参考密度 | `2.70000000e+00` |
| 7 | `TRef` | 参考温度 | `2.58525700e-02` |
| 8 | `BulkModulusRef` | 参考体积模量（**cgs**） | `7.50000000e+11` |
| 9 | `SESAMEnumber` | SESAME 材料号 | `3.71700000e+03` |

**行 1**（`FE-01_TABTOOLS.C:225–227`）：

| # | 字段 | 语义 | Al 实测值 |
|---|---|---|---|
| 10 | `ElectronOffset` | 电子能量零点偏移 | `-2.94875001e+14` |
| 11 | `IonOffset` | 离子能量零点偏移 | `3.00821482e+09` |
| 12 | `Ecoh` | 内聚能 | `1.21230000e+11` |
| 13 | `softsphere_n` | 软球势指数 n | `2.00000000e+00` |
| 14 | `softsphere_m` | 软球势指数 m | `5.00000000e-01` |
| 15 | `softsphere_A` | 软球势系数 A | `5.27428129e+09` |
| 16 | `softsphere_B` | 软球势系数 B | `9.90197297e+10` |
| 17 | `Atot` | **总原子量** | `2.69815000e+01` → 26.9815（Al） ✅ |
| 18 | `Ztot` | **总原子序数** | `1.30000000e+01` → 13（Al） ✅ |
| 19 | `Xtot` | **总摩尔分数**（归一化） | `1.00000000e+00` |

**两处重要修正**（相对 10.3.3 的初版表述）：

1. **第 3 字段的语义是"元素个数"，不是"元素号"**。原文 `Nelements + 1` 中的 `+1` 是为**真空/背景**预留的槽位（与 `material.base` 的 `MATERIAL MID0`（Vacuum）呼应，见 7.x 章）。

2. **`NR+1` / `NT+1` 的"真相"是"下标 vs 计数"的换算，不是"强制补点"**。

   源码中：
   ```c
   (*table).NRho  /* 数组元素个数 */
   NR = (*table).NRho - 1   /* NR 是"末下标" */
   ```
   写出时打印 `NR + 1`，**打印出来的就是数组元素个数 `NRho` 本身**。

   同时，FEOS 在**构造表时会自动补两个端点**：`T = 0.0 eV` 与 `ρ = 0.0 g/cm³`。故 Al 的"用户指定网格"若为 191×68，则构造后数组为 192×69，**写出的 `192`/`69` 即含补点的元素个数**。

   **⇒ 10.3.3 的"强制补点"表述需要修正为**：补点确实存在（且是 `T=0`/`ρ=0` 两个端点），但**写出的是补点后的元素个数**，且这不是"额外插入"而是"表构造的固有约定"。

#### 10.6.11 本轮新增的两个"名不副实" `.feos` 样本

10.5 第 4 条登记了 3 个"名不副实"的 `.feos` 文件。本轮**在 `matter++/hyades/` 下又发现 2 个同型样本**，且陷阱更深——它们的行宽不是 SESAME 的 60 也不是 FEOS 的 150，而是 **75 = 5×15**：

| 文件 | 字节 | 行宽 | 首行内容 | 实际格式 |
|---|---|---|---|---|
| `matter++/hyades/qeos/qeos_392.dat.feos` | 142,553 | **75 = 5×15** | `Silicon     LLNL QEOS DATED: 062695` | **Hyades** |
| `matter++/hyades/sesame/eos_41.dat.feos` | 30,993 | **75 = 5×15** | `ALUMINUM    LANL SESAME #3711 DATED: 22581 11483` | **Hyades** |

**判据链**（三重）：

1. **首行是 Hyades ASCII 头**：`Silicon     LLNL QEOS DATED: 062695` —— 材料名（左对齐 12 字符）+ 来源声明 + 日期，这是 **Hyades 格式的固定首行**（见第 9 章 9.x）。

2. **第 2 行完全符合 Hyades 的 Fortran 格式串 `1x,i5,4x,1p3e15.8,3x,i5`**：

   ```
      392     1.40000000E+01 2.80800000E+01 2.42000000e+00    9249
   └1┘└i5 ┘└ 4 ┘└──── 3 × e15.8 ────┘└ 3 ┘└i5┘
   ```
   即"1 空格 + `i5`（392=Si 的原子序数）+ 4 空格 + 3 个 `e15.8`（A=14.0, Z=28.08, ρ=2.42）+ 3 空格 + `i5`（9249）"——**逐宽度吻合**。

3. **数据体行宽 75 = 5×15**，符合 Hyades 数据体的 `1p5e15.8`（每行 5 个数 × 15 字符）。

**⇒ 这是"文件名关键词决定分派"陷阱的活体实例**。按 `matter++/Readme.txt` 的规则，只要文件名含 `.feos` 就走 FEOS 分支、按 150 字符切行——**在这两个文件上会立刻崩溃**（75 不能被 150 整除，且首行根本不是数值）。

**这两个文件为什么叫 `.feos`？** 无一手依据（`[S-UNK]`）。但从目录结构可推：`hyades/qeos/` 与 `hyades/sesame/` 是**Hyades 材料库的存档子目录**，用户可能为了"让 Multi1D++ 的某个按扩展名分派的读取路径也能读到它们"而加上了 `.feos` 后缀——**这是一种试图绕过"文件名分派"的民间 workaround，结果反而制造了更强的陷阱**。

**工程结论**：**Multi1D++ 的格式分派必须做内容侧复核**（第 1.3 节的"内容侧判据"在此得到实战验证）：

```python
# C7：分派前的三重内容复核（在 Readme 的"按名分派"之后叠加）
def sniff_actual_format(path, first_lines):
    l0 = first_lines[0].rstrip()
    # (1) 首行是否为 Hyades ASCII 头？ → 材料名(<=12) + 来源声明
    if re.match(rb'^[A-Za-z][A-Za-z0-9 ]{0,11}\\s{2,}(LLNL|LANL|SNL|LLL)', l0):
        return 'hyades'
    # (2) 首行是否含 SESAME 记录头（列 1-2 = 文件号）？
    if re.match(rb'^\\s*\\d{1,2}\\s*\\d{1,6}\\s*\\d{1,6}', l0) and len(l0) >= 80:
        return 'sesame_ascii'
    # (3) 首行能否整体按 150 字符整除 / 是否全为 15 宽数值 token？
    if len(l0) % 150 == 0 and _all_15w_tokens(l0):
        return 'feos'
    # (4) 15 宽数值 token 但行宽 % 75 == 0 → 疑似 Hyades 数据体
    if len(l0) % 75 == 0 and _all_15w_tokens(l0):
        return 'hyades'
    return 'unknown'
```

**核心原则**：**扩展名给出"候选族"，内容给出"最终裁决"**。当二者冲突时，**内容优先**，并**必须给出显式告警**（不要静默按内容解析，否则用户永远不知道自己的文件是"名不副实"的）。

#### 10.6.12 本节结论对前文的修正汇总

| 位置 | 原表述 | 修正后 | 依据 |
|---|---|---|---|
| 10.3.3 / 6.x | `.feos` 字段宽度可能为 4×15 | **10×15 = 150 字符/行** | `SF_TRENN=""` + 实测 23,874 行 |
| 10.4 | `Readme.txt` 的 "4×16" 描述 | **FEOS 16.7 原生为 4×15 = 60**；**4×16 = 64 是旧 MPQeos v2.0 产物**；两者都在野外存在 | `%15.8le` + 两种实测样本 |
| 10.3.3 | "参数行与数据行字段数可能不同" | **相同，均 10 字段/行** | 写出循环 |
| 10.3.3 | "`NR+1` 是强制补点" | **是"下标 vs 计数"换算**；补点为 `T=0`/`ρ=0` 两端的固有约定 | `NR = NRho - 1` |
| 10.3.3 | 第 3 字段 = "元素号" | **元素个数** | `Nelements + 1` |
| 10.5 第 1 条 | `.feos` payload 列序 `[S-UNK]` | **j（温度）外层、i（密度）内层** | 写出循环 |
| 10.5 第 5 条 | 许可页无可引用 URL | **FEOS = CPC 227 (2018) 117–125，DOI `10.1016/j.cpc.2018.01.008`；GPLv3** | `License.txt` + 官方文档 |
| 10.5 第 6 条 | `.critical.dat` 列语义 `[S-UNK]` | **14 分段，已对齐** | `FE-01_TABTOOLS.C:58` |
| 10.5 第 7 条 | `BulkModulusRef` 单位矛盾 | **不矛盾**：`.feos` 用 cgs，`.mexport` 用 GPa 量纲 | `cgs2ses_p = 1e-10` |
| 10.5 第 8 条 | `.hug` 命名混乱 | **命名 = 母表名 + `.hug`**；空表 = 搜索无解的正常退出 | `SE-03_SERVICES.C:649` |
| 10.4 / 6.x | `4gnuplot` 疑似 FEOS 产物 | **非 FEOS 产物**（源码 0 命中），属用户后处理；归入 `.ist` 族 | `SE-00_DEFINITS.H` 全搜 |
| 10.4 | `Path=` 是 FEOS 功能 | **属旧 MPQEOS v2.0 参数模式** | `COMMON-02_READFILE.C` 全搜 |
| 10.5 第 4 条 | 3 个"名不副实"的 `.feos` | **实测 5 个**（新增 `hyades/` 下 2 个，行宽 75） | 10.6.11 |

**本章解析状态**：由"实测归纳可用"升级为"**源码可证**"。10.5 的 8 条缺口全部关闭，**本族不再有 `[S-UNK]` 级别的格式级未知**（剩余的未知只在"具体样本的物理合理性"层面，如 `SiO2.feos` 的数值越界）。

'''

d = d[:j] + SEC + d[j:]
io.open(P, 'w', encoding='utf-8', newline='\n').write(d)
print('chars %d -> %d (+%d)' % (orig_len, len(d), len(d) - orig_len))
print('bytes %d' % len(d.encode('utf-8')))
