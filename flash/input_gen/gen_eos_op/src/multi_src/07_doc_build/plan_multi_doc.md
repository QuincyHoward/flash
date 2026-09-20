# MultiEOSOP格式说明.md —— 写作计划（Writing Plan）

> 目标产物：`src/multi_docs/MultiEOSOP格式说明.md`（≥ 80,000 汉字，目标 88,000）
> 定位：**独立权威格式规格书**（上游视角），与 `eosop_pro/docs/20_格式规格与物理量单位手册.md`（本项目实现视角）形成分工。
> 本文件是写作计划，不含正文。

---

## 0. 定位与边界（写作前必须先读）

### 0.1 与 `docs/20` 的分工（避免重复是第一风险）

| 维度 | `docs/20_格式规格与物理量单位手册.md`（已有） | **本文档（新）** |
|---|---|---|
| 视角 | 项目实现：哪个 Python parser 解析、unit_source 等级 | **上游原始规范**：格式本身怎么定义 |
| 读者 | 本项目开发者 | 任何拿到 Multi1D++ 数据的人 |
| 单位依据 | L1/L2/L3 等级 + 溯源文档 + 实现脚本 | **格式原生单位** + 换算推导链 |
| 结构 | 按格式族 F1–F6 平铺，逐族的 field_units 表 | **经（机制）× 纬（族）混合体**：上编讲通用机制，下编逐族深潜 |
| 自足性 | 依赖 `eosop_pro/` 代码 | **自足独立交付**，只引上游文档 |
| 深度 | 结构规格（判据级） | **逐字节布局 + 完整字段语义 + 实例逐行解读** |

**写作纪律**：本文档**不**引用 `docs/20` 的任何结论、不引用 `eosop_pro/parsers/*.py`。凡 `docs/20` 已写过的内容，本文档必须以**上游原始文档**重新表述（可得出更完整、更原始、更逐字节的版本）。唯一允许提及项目代码的地方是**附录 D（实现现状，简短）**。

### 0.2 权威源（唯一骨架，全部位于 `src/Multi1D++Portable20241128/`）

| 代号 | 源文件（相对 `src/Multi1D++Portable20241128/`） | 字节 | 覆盖 |
|---|---|---|---|
| `[SESAME]` | `doc/MULTI使用的SESAME数据文件格式.docx` | 183,025 | SESAME/MULTI 反演 EOS、不透明度、Zeff、NLTE、material.base |
| `[HYADES]` | `doc/Hyades 数据格式说明.doc`（`matter++/hyades/` 有副本） | 57,344 | Hyades EOS/opacity 编号体系、ASCII 格式、外部不透明度表 |
| `[LEDCOP]` | `matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx` + `doc/Atomic(LEDCOP)说明.doc` | 33 KB / 59,904 | ATOMIC/LEDCOP/TOPS 不透明度、u 网格、FAQ |
| `[DISPATCH]` | `matter++/Readme.txt` | 530 | **格式分派规则（文件名关键词）** |
| `[THERMOS]` | `matter++/Thermos/Readme.txt` | — | Zeff eV/keV 权威声明、无 EOS 元素、Mn 数据错误 |
| `[SNOP]` | `doc/SNOP.MANUAL` | 6,604 | SNOP namelist、IGROUP、SESAME 表号 nnn 编码、材料 xxxx 码 |
| `[MULTI76]` | `doc/multi1d7.6/manual` | 13,797 | FT12 输入、ft12/fort.10 二进制记录、变量单位 |
| `[GUI]` | `doc/GUI,IO相关.docx` | 65,744 | `*.center.dat`/`interface`/`group`/`scalars` 输出变量字典 |
| `[MU]` | `doc/muParser.txt` | 4,073 | 公式字段（ScalingLaws）支持的 26 函数 / 15 运算符 |
| `[FEOS]` | `doc/FEOS/Info.txt` + 4 PDF | — | FEOS/MPQeos 血统与单位 |
| `[PROP]` | `matter++/PROPACEOS/Readme.txt` | 82 | **版权保护 → 诚实缺口** |
| `[WEAK]` | `doc/Structure_of_ASCII_data_files.txt` | 82 | 仅有 3 行整数矩阵，来源不明 → 诚实缺口 |
| `[IONMIX]` | `ionmix/ionmix/docs/IONMIX用户指南.md` + `ionmix/ionmix/src/Ionmix/abjt_03.f` | — | cn4/cnr 逐块与单位（**一手源码**） |
| `[QSEOS]` | `matter++/mat_*/*.readme`、`Albedo.xml`、`ScalingLaws.dat`、`density.dat` | — | 材料级幂律拟合不透明度、albedo、NIST 常数 |

**注意**：任务清单里把 `[LEDCOP]` 写作 `matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx`，实际 `matter++/ATOMIC/` 下为 `*.txt`/`*.NoFree` 等数据；说明文档在 `doc/`。写作时**以实际文件路径为准**，不采信二手路径。

### 0.3 图经×纬结构（hybrid）

```
前置（front matter）
  ├─ 封面 / 文档定位 / 与 docs-20 分工声明
  ├─ 阅读指南（两种读法：教程读法 = 上编顺读；查表读法 = 下编定位）
  ├─ 术语与记号约定表
  ├─ 符号表（物理量 → 符号 → 原生单位 → SI）
  └─ 单位总表 + 溯源标注约定

上编 · 通用机制（经）—— 约 42,000 字
  第 0 章 总论：Multi1D++ 的数据生态与格式全景
  第 1 章 格式识别与分派机制
  第 2 章 字节级解析通法
  第 3 章 坐标系与网格组织
  第 4 章 物理量语义与单位体系
  第 5 章 转换、反演与插值
  第 6 章 工程实践与陷阱总集

下编 · 格式族深潜（纬）—— 约 40,000 字
  第 7 章 SESAME 数据库格式族
  第 8 章 MULTI 反演 EOS 与多群不透明度族
  第 9 章 Hyades 格式族
  第 10 章 FEOS / MPQeos 格式族
  第 11 章 ATOMIC / LEDCOP / TOPS 格式族
  第 12 章 IONMIX 格式族（.cn4/.cnr）
  第 13 章 SNOP 与 Thermos 格式族
  第 14 章 辅助与边缘格式（材料级、曲线级、表头级）

附录 —— 约 6,000 字
  附录 A 单位换算总表与推导链
  附录 B 格式速查卡（One-pager × 每族）
  附录 C 实测样本文件索引（路径 + 字节数 + 关键表头行）
  附录 D 检索/校验代码片段（可选，brief）
  附录 E 实现现状与已知缺口（Python，brief，≤1,500 字）
  附录 F 参考书目（本地源 + 网络核验源，分列）
```

---

## 1. 单位与溯源标注约定（全文强制）

### 1.1 溯源四级标注（正文内联，写在表格"依据"列或段落末）

| 记号 | 含义 | 写法示例 |
|---|---|---|
| `[S-L1]` | 上游手册/格式说明**明文规定** | `[S-L1] SESAME.docx §Inverted EOS` |
| `[S-L2]` | **数据文件自身内嵌声明** | `[S-L2] ATOMIC/Al.txt: "T in keV"` |
| `[S-L3]` | **程序约定默认**（文件未声明时） | `[S-L3] matter++/Readme.txt` |
| `[S-L4]` | **推导**（给出量纲链） | `[S-L4] abjt_03.f:4693 赋值式展开` |
| `[S-UNK]` | **本地无依据**，标 unknown，不猜测 | `[S-UNK] 无文档说明` |
| `[S-WEB]` | **网络核验**（必须独立标注，不得与本地结论混合） | `[S-WEB] NIST/LANL 公开页` |

### 1.2 单位书写规范

- 原生单位用**等宽体**：`g/cm3`、`Mbar`、`eV`、`keV`、`cm2/g`、`dyne/cm2`、`erg/g`、`J/cm3`。
- 每个物理量首次出现时给出三元组：`物理量（格式内原生单位 → MULTI 内部单位 → SI）`。
- 换算必须写**完整推导链**，例如：
  `1 GPa = 1e9 dyne/cm2 = 1e3 bar = 1e-2 Mbar`。
- **禁止**只给数字不给链；**禁止**跨族复用单位结论（族间单位不同是本领域最大坑）。

### 1.3 与网络来源的隔离纪律

网络仅用于：(a) SESAME / IONMIX / LEDCOP / SNOP / Hyades / FEOS 的**公开出处与书目信息核验**；(b) 本地缺失的编码约定补白。所有网络内容必须：
1. 单独成段或单独标注 `[S-WEB]`；
2. 附 URL + 访问日期；
3. **不得**改写本地结论，若冲突以本地为准并显式记录冲突。

---

## 2. 逐章写作计划（含字数、内容、源、图表）

> 每章字数为主文（含表格内文字），目标总量 = 88,000。

### 前置（约 3,000 字）

**前置-1 封面与文档定位**（600 字）
- 标题、副标题（"Multi1D++ 辐射流体程序包 EOS 与不透明度数据格式规范"）、版本、日期。
- 文档定位声明：独立权威规格，自足交付，只引上游源；与 `docs/20` 分工（见 §0.1 表）。
- 适用范围与不适用范围（不含 MULTI 源码算法、不含物理模型推导，仅数据格式）。

**前置-2 阅读指南**（900 字）
- 两类读者的两种路径：教程路径（上编顺读，按机制建立心智模型）、查表路径（第 1 章分派表 + 第 7–14 章）。
- 文档导航图（ASCII）。
- 如何用附录 B 速查卡与附录 C 样本索引。

**前置-3 术语与记号**（900 字）
- 术语表：格式族、表号、反演、群边界、Rosseland/Planck/EPS、Zeff、NLTE、u 网格、能群、T-major…
- 记号表：`nr`/`nt`/`ng`（文件内维数）、`NR`/`NT`/`NG`（程序维数）、`β`、`κ`…

**前置-4 符号表 + 单位总表**（600 字）
- 符号表（物理量 → 符号 → 各族原生单位）。
- 单位总表（9 行 × 7 列，见 §4 推荐图表 T1）。
- 溯源标注约定（§1.1 全文照录）。

*来源：本文档自撰 + `[SESAME]`/`[THERMOS]` 交叉。* **网络：不需要。**

---

### 第 0 章 总论：Multi1D++ 的数据生态与格式全景（5,000 字）

- **0.1 Multi1D++ 血统**（1,000 字）：MULTI（1988, Ramis, CPC49）→ MULTI6 → 7.3/7.4/7.6 → Multi1D++。1988 版用单温 EOS（通常 SESAME）+ 多群不透明度（通常 SNOP）；7.4 引入 `material.base` 索引；7.6 拆出 matter-1.0 材料模块；Multi1D++ Portable 的一体化打包。
  - 源：`[MULTI76]` `doc/multi1d7.6/README`、`doc/References/1988CPC49`。
- **0.2 数据在程序中的角色**（1,000 字）：EOS 表输入什么、不透明度表输入什么、两者如何被查询（R,T → P,E；R,T → κ）。一张"程序 ↔ 数据"接口图。
- **0.3 格式全景**（1,800 字）：8 大族一览表（族名 / 触发关键词 / 原生单位体系 / 坐标制 / 典型表号 / 样本文件 / 本文档章节）。这张表是全文的"目录中的目录"。
  - 源：`[DISPATCH]` + `[SESAME]` + `[HYADES]` + `[LEDCOP]` + 实测样本。
- **0.4 数据地图与血缘**（1,200 字）：谁生成什么 → 哪种格式（SNOP → SESAME 4×15；IONMIX → .cn4；TOPS/LEDCOP → ATOMIC/*.txt；QEOS/FEOS → .feos/逐材料库；MPQeos → .301/.304/.305；Thermos → *.ini + *_Planck/*_Ross/*_Zeff）。
  - 图 F1：数据血缘图（DOT 或 ASCII）。

*来源：`[MULTI76]` `[DISPATCH]` `[SESAME]` `[HYADES]` `[LEDCOP]` `[FEOS]`。* **网络：核验 Ramis MULTI/2D 论文书目信息（DOI/卷期）→ 仅书目。**

---

### 上编 · 通用机制（经）

#### 第 1 章 格式识别与分派机制（6,000 字）

- **1.1 分派总则：靠"文件名/路径关键词"，不靠内容嗅探**（1,500 字）
  - `[DISPATCH]` 原文照录并逐条解读：路径含 `hyades` → Hyades；文件名含 `.feos` → FEOS，按 4×15 读；含 `.301`/`.304`/`.305` → MPQeos，4×16；否则默认 SESAME 4×15。
  - 强调：**这是全文最重要的单条规则**，也是第一大坑（把 `.feos` 文件改名会改变解析行为）。
  - 陷阱：`AL_eos.feos` 实测与 `AL_eos` 字节相同（名 FEOS 实 SESAME），说明分派是"候选顺序尝试"而非硬绑定。
- **1.2 扩展名 → 族映射表**（1,500 字）
  - 完整映射：`.dat`/`.inv`/`.sesame`/`.planck`/`.ross`/`.zeff`/`.eps`/`.301`/`.304`/`.305`/`.feos`/`.cn4`/`.cnr`/`.txt`(ATOMIC)/`.NoFree`/`.AvSqFree`/`.coldopacity`/`.hug`/`.snop`/`.feos`/`.hyades`。
- **1.3 内容侧判据（辅助）**（1,500 字）
  - 表头魔数：LEDCOP `0.1234567E+000`；IONMIX 头部第 4 行 `int()` 可解析判 `.cn4`、不可判 `.cnr`；SESAME 4×15 定宽；Hyades `1x,i5,4x,1p3e15.8,3x,i5`。
  - 计数守恒作为**唯一判定**的场合（F1 两种 payload 布局、`.cnr` 的 `ntrad`）。
- **1.4 分派决策流程图**（1,500 字）
  - 图 F2：格式分派流程图（从文件名 → 候选队列 → 计数守恒验证 → 定族）。

*来源：`[DISPATCH]` `[SESAME]` `[HYADES]` `[LEDCOP]`。* **网络：不需要。**
*表：T2 扩展名映射表；T3 表头魔数表。图：F2 分派流程图。*

#### 第 2 章 字节级解析通法（7,000 字）

- **2.1 定宽 vs 自由格式**（1,500 字）：4×15（SESAME）、4×16（MPQeos）、`1p5e15.8`（Hyades）、`4e12.6`（IONMIX）、`E12.6`。给出**每种宽度下的单字段正则**。
- **2.2 Fortran 数值写出的坑**（2,500 字，全章重点）
  - 2.2.1 `E12.6` 溢出：`0.638380-140`（指数 3 位时 `E` 被静默丢弃），修复正则 `(\d\.\d{6})([-+]\d{3})` → `\1E\2`；实测 89 个 token，修复后计数不变。
  - 2.2.2 前导零 vs 点号两种尾数风格（`.17010000E+04` vs `0.17010000E+04`）。
  - 2.2.3 缺 `E` 的 D 指数、`+` 号省略。
  - 2.2.4 DOS EOF `\x1a` 与行尾 `\r\n`/`\r`。
  - 2.2.5 负数与 NaN 占位符 `-9.99999+990`。
- **2.3 定宽表头不可机械切分**（1,200 字）：MPQeos `.301` 表头 ID 字段宽 16 或 17 列不定；payload 行宽逐文件不同（60 字符 W=15 vs 64 字符 W=16）。对策：表头用空格分割正则，payload 用 `W = len(line)/4` 逐文件推断。
- **2.4 计数守恒校验法**（1,800 字）
  - 各族计数公式汇总表：F1 `4+2nr+ne+2nr·ne`（with_e0）/ `4+nr+ne+2nr·ne`（no_e0）；MPQeos `4+nr+nt+3nr·nt`；IONMIX cn4 `ntemp+ndens+12·ntemp·ndens+(ngrups+1)+3·ngrups·ntemp·ndens`；cnr 余数反解 `ntrad`；Hyades `L = 2+nr+nt+2nr·nt`；LEDCOP 拆分件 `4+nr+nt+nr·nt`。
  - 实测锚点：`AL_eos`=9978、`Al.feos.301`=40005、`Z06....cn4`=47519、`Al.NoFree`=3573。

*来源：`[SESAME]` `[HYADES]` `[IONMIX]` `[MULTI76]`。* **网络：不需要。**
*表：T4 定宽规格表；T5 计数守恒公式总表；T6 实测锚点表。代码块：C1 打包指数修复正则；C2 计数守恒校验伪码。*

#### 第 3 章 坐标系与网格组织（6,000 字）

- **3.1 两大坐标制：线性（EOS） vs 对数（不透明度/NLTE/Zeff）**（2,000 字）：`[SESAME]` 原文；为何如此（EOS 需插值 P(R,E)，OPAC 跨 10 个量级）。
- **3.2 网格存储顺序**（1,500 字）：T-major / rho 快变（`i_de*nr + j_rho`）；P/E 矩阵的排布；与 C/Fortran 索引习惯的关系。
- **3.3 网格可插值与不可插值**（1,500 字）：LEDCOP 温度网格（69 点 ATOMIC 2015 / 50 点 LEDCOP 2000）**不可插值**；密度网格**可插值**。原因与后果。
- **3.4 特殊网格**（1,000 字）：LEDCOP 14900 点 `u = hν/kT` 网格分段定义；IONMIX 群边界 `ngrups+1`；SNOP 的 IGROUP 五种分群法。

*来源：`[SESAME]` `[LEDCOP]` `[IONMIX]` `[SNOP]`。* **网络：`u` 网格定义的 TOPS 原始出处（LA-10454）核验 → 仅书目。**
*表：T7 u 网格分段表；T8 网格可插值性对照表。图：F3 坐标制对比图；F4 u 网格分段示意图。*

#### 第 4 章 物理量语义与单位体系（8,000 字）

- **4.1 三套单位体系并存**（2,000 字）：SESAME/DPK（GPa, MJ/kg, K）↔ MULTI 内部（Mbar, Mbar·cm³/g）↔ Hyades CGS（dyne/cm², erg/g）↔ IONMIX SI 派生（J/cm³, J/g）。
- **4.2 逐物理量语义**（3,000 字）：密度、温度、压力、比内能、冷能、平均电离度 Zbar、不透明度（Rosseland/Planck 吸收/Planck 发射/EPS）、群边界、比热、声速。每个给"定义 + 原生单位 + 量纲 + 与其他族差异"。
- **4.3 温度单位 eV/keV 双套陷阱**（2,000 字，独立小节）
  - 不透明度常用 eV；Zeff/SNOP/Thermos 用 keV；LEDCOP 主表 keV。
  - 历史 bug（20160109）导致电离度过高；`X_Z.dat`（eV）作废 → `X_Zeff.dat`（keV）。
  - `Al_Zeff.dat` vs `Al_Z.dat` 表头与行数完全相同，仅差 `log10(1000)=3.000`。
  - 权威判定依据 = `[THERMOS]` Readme 文件名模式声明。
- **4.4 数据型标识符**（1,000 字）：line-1 col-2：PLANCK `1`/`M`、ROSSELAND `1`/`M`、EPS `1`/`M`；MULTI7.6+ 仅多群需标识。

*来源：`[SESAME]` `[HYADES]` `[LEDCOP]` `[IONMIX]` `[SNOP]` `[THERMOS]` `[FEOS]`。* **网络：SESAME 表号编码约定（xxxx=材料ID, nnn=表型）的公开出处 → 补白 + 核验。**
*表：T1 单位总表（9×7）；T9 温度单位对照表；T10 数据型标识符表。图：F5 单位换算地图。*

#### 第 5 章 转换、反演与插值（7,000 字）

- **5.1 EOS 反演的必做性**（2,000 字）：为什么 MULTI 需要 `E(R,T)→P(R,E), T(R,E)`；反演的数值方法（局部单调性、双线性/双三次）；失败情形。
- **5.2 单位换算推导链**（2,500 字）
  - `1 GPa = 1e-2 Mbar`；`1 MJ/kg = 1e-2 Mbar·cm³/g`；`1 J/cm³ = 1e-5 Mbar`；`1 J = 1e7 erg`；`cm/s → um/ns`。
  - Hyades CGS → MULTI 内部；MPQeos GPa/MJ·kg⁻¹ → Mbar；IONMIX J/cm³ → Mbar。
  - 每条给完整量纲链。
- **5.3 网格互转与插值**（1,500 字）：对数网格对数插值；跨族网格对齐；不可插值网格的处置。
- **5.4 幂律不透明度拟合**（1,000 字）：`κ = a·T^s·ρ^r`（cm²/g）或 `κ = e^a·T^b·ρ^c`；给出 `mat_*` 各材料的拟合系数与有效范围。

*来源：`[SESAME]` `[HYADES]` `[IONMIX]` `[FEOS]` `[QSEOS]`。* **网络：不需要。**
*表：T11 换算因子与推导链表；T12 材料幂律拟合系数表。代码块：C3 反演伪码。*

#### 第 6 章 工程实践与陷阱总集（3,000 字）

- **6.1 十大陷阱汇总**（2,000 字）：编号、现象、根因、判据、处置。逐条给"怎么发现、怎么避免"。
- **6.2 解析器编写建议**（1,000 字）：锚点驱动流式状态机（LEDCOP 348636 行）；绝不按固定行数；绝不按文件名猜物理量；守恒校验先行。

*来源：全文汇总。* **网络：不需要。**
*表：T13 陷阱对照表（10 行 × 5 列）。*

---

### 下编 · 格式族深潜（纬）

#### 第 7 章 SESAME 数据库格式族（6,000 字）

- **7.1 SESAME 数据模型**（1,200 字）：表号 `tttt` + 表型 `nnn`（3013=Planck 群平均, 4013=Rosseland, 5013=EPS, 2013=Zbar）；`[SNOP]` 材料 xxxx 码（D=5263, Be=2020, B=7081, C=7560, Al=3712, Fe=2140, Au=2700）。
- **7.2 `material.base` 材料主索引**（1,500 字）：MATERIAL/REM/A/Z/EOS/PLANCK/ROSSELAND/NONLTE/ZEFF 关键字 + 文件夹 + 表名；MID < 100 为 Ramis 公布材料、> 10000 为用户材料。
- **7.3 4×15 定宽格式逐字节**（1,800 字）：行结构、`E` 指数、表头行语义；实测样本 `SNOP_LTE.PLANCK`（207,420 B）逐行解读。
- **7.4 多群 `sesame_tab` 结构**（1,500 字）：`27004003 ROSSELAND M nr nt` / 群边界 / log rho 网格 / log T 网格 / log 值；样本逐行解读。
  - 注意：任务清单称 `27004003 ... nr nt`，实测样本 `SNOP_LTE.PLANCK` 为 `27003000 PLANCK M 0.20000000E+02 0.20000000E+02` 且群边界 `1–100 eV`。**两处的表号与群数不一致，须实测确认后如实记录，不强行统一。**

*来源：`[SESAME]` `[SNOP]` `[DISPATCH]`。* **网络：SESAME 表号编码约定的 LANL 公开说明 → 补白 + 核验（独立标注）。**
*表：T14 SESAME 表型编码表；T15 material.base 关键字表。代码块：C4 4×15 逐行解读。

#### 第 8 章 MULTI 反演 EOS 与多群不透明度族（6,000 字）

- **8.1 反演 EOS 四列布局**（2,000 字）：`4 + 2nr + ne + 2nr·ne` 公式与逐字段语义；实测 `AL_eos` 表头 `37181000 2.7 66 74` → 9978；两种 payload 布局（with_e0 / no_e0）。
- **8.2 不透明度 / Zeff / NLTE / EPS**（2,000 字）：logloglog 坐标；缩放公式 `L = c·T^a·ρ^b` ↔ `Z = -log(c) - a·log(T) - (b+1)·log(ρ)`，含**完整算例**；多群子表串联结构（每子表自带表头 + 群边界）。
- **8.3 频率依赖与多群**（1,000 字）：数据型标识符；`ng` 子表；群边界随群变化。
- **8.4 实例逐行解读**（1,000 字）：`AL_SIMPLE_PLANCK`（183 B）、`AU_op03p`（20 子表 × 112 行）、`SNOP_LTE.PLANCK`。

*来源：`[SESAME]` `[SNOP]` `[MULTI76]`。* **网络：不需要。**
*表：T16 F1 字段语义表；T17 F2 字段语义表。图：F6 F2 多子表串联示意图。代码块：C5 logloglog 算例逐步。

#### 第 9 章 Hyades 格式族（6,000 字）

- **9.1 Hyades 数据目录结构**（1,000 字）：`Ionpot.dat`、`Coldopac.dat`、`Eoslib.lbf`、`Opaclib.lbf`、`Tfdat.lbf`、`Opacity/`、`qeos/`、`sesame/`。
- **9.2 EOS/不透明度表号体系**（1,500 字）：单流体 `1<num<998`；Rosseland/Planck `1000<num<2000`；双温电子 `2000<num<3000`、离子 `3000<num<4000`（须同时指定）；`*`=首选，`#`=有双温；完整表含示例（11 D+T 1.000/2.515/0.2205；41 Al 13.00/26.982/2.7568；341 Diamond 6.000/12.011/3.51）；不透明度表示例（1022 Quartz, 1461 Eu, 1481 Ca, 1491 Ag）。
- **9.3 ASCII 材料文件逐字节**（2,000 字）：行 1 材料名 + 血统历史；行 2 `EOS# ZBAR ABAR DEN L`，格式 `1x,i5,4x,1p3e15.8,3x,i5`；行 3+ NR, NT, 密度数组, 温度数组, 压强矩阵, 能量矩阵，格式 `1p5e15.8`；数组长 `2+NR+NT+2·NR·NT`；单位 g/cm³, keV, dyne/cm², erg/g；实测 `eos_2051.dat` 逐行解读。
- **9.4 外部不透明度表格式**（1,500 字）：8 个 Block 结构（Block1 字符串头；Block2 `#T #rho`；Block3 温度数组 keV ≤200；Block4 密度数组 g/cm³ ≤200；Block5 群数 NGPS1 ≤500；Block6 群边界；Block7 起 T#1/rho#1 的不透明度 cm²/g；之后先扫全部密度再下一温度）。

*来源：`[HYADES]`。* **网络：Hyades (CAS Inc.) 与 1994JQSRT51 Larsens 书目核验 → 仅书目。**
*表：T18 Hyades 表号区间表；T19 Hyades 表号完整清单；T20 外部不透明度 8-Block 表。代码块：C6 Hyades 头部逐字节。

#### 第 10 章 FEOS / MPQeos 格式族（5,000 字）

- **10.1 血统**（1,000 字）：MPQeos（Kemp, 修改 Krenz/Ramis/Vinci）→ FEOS_16.7/SHOWEOS_16.7（Faik, GPLv3），新增均匀混合物、软球冷曲线、Maxwell 构造、库 API。
- **10.2 `.301`/`.304`/`.305` MPQeos 4×16**（1,500 字）：行 1 `Id Density NR NT`（**注意与任务清单的 "Id Density NR NT" 一致，但实测表头为 `37170301 2.7 192 69`，即 Id 已含表型 0301**）；payload `[R(nr)] [T(nt)] [P] [E] [Z]`；计数 `4+nr+nt+3nr·nt`；实测 `Al.feos.301` → 40005。
- **10.3 `.feos` 原生 4×15**（1,200 字）：行 0 十字段 `[Z, NR, NT, c1, c2, c3, rho0, T_ref, B0, SESAME#]`（由 `.301` 兄弟文件交叉验证）；其余为 rho/T 网格与 payload。
- **10.4 `.feos` 兄弟文件族**（800 字）：`.par`（Material-Number/Maxwell_Flag/…）、`.critical.dat`（Tc/Pc/Rhoc/…）、`.isobaric.dat`、`.ist/.ise/.isc/.mnt`、`.hug`。
- **10.5 诚实缺口**（500 字）：FEOS 原生 payload 列序无法从 PDF 可靠还原 → `[S-UNK]`。

*来源：`[FEOS]` `[DISPATCH]`。* **网络：MPQeos-JWGU 的公开出处、FEOS GPLv3 发布页核验 → 仅书目 + 许可。**
*表：T21 MPQeos 字段表；T22 `.feos` 行 0 十字段表。图：F7 MPQeos→FEOS 演化图。

#### 第 11 章 ATOMIC / LEDCOP / TOPS 格式族（6,000 字）

- **11.1 头部块逐行**（1,500 字）：`Number of T=/Number of rho=/Number of materials=`；TOPS 横幅；`Opacities in cm**2/gm, T in keV, density in gm/cc`（内嵌单位声明）；组份表（No./Fraction/Mass Fraction/At.No./Chem.Sym./Mat ID）；温度网格行；密度网格行。
- **11.2 三段数据体**（1,800 字）：(a) 灰不透明度块（每温度：`Density Ross opa Planck opa No. Free Av Sq Free T=`）；(b) 多群块（`Energy Ross mg Planck mg for T, density =`）；(c) 频率依赖谱（3000/3900 点）。
- **11.3 u 网格 14900 点定义**（1,200 字）：`u = hν/kT` 七段（0–12.5 step 0.00125 ×9600；12.5–20 ×1600；20–30 ×1000；30–100 ×700；100–1000 ×900；1000–10000 ×900；10000–30000 ×200）。
- **11.4 网格与边界约定**（1,000 字）：温度网格不可插值；密度网格可插值；等离子体截止频率以下群不透明度置 `1e10`。
- **11.5 TOPS FAQ Q1–Q13**（500 字）：摘要 Q1–Q13 要点（如负不可透明度、外推、组份变化）。

*来源：`[LEDCOP]`。* **网络：LA-UR-97-1038 / LA-10454 / LA-6760-M 书目核验 → 仅书目。**
*表：T23 LEDCOP 头部字段表；T24 u 网格七段表；T25 TOPS FAQ 摘要表。图：F8 u 网格分段对数示意图。

#### 第 12 章 IONMIX 格式族（6,000 字）

- **12.1 两种互斥格式 `.cn4` vs `.cnr`**（1,500 字）：`.cn4` = `isw(21)!=0` 分支，18 块，含 EOS；`.cnr` = `isw(8)=1/12/13`，late-1986 CONRAD，7 块，无 EOS；用户指南 §5.4 覆盖 cn4 而 `cnr` 零命中。
- **12.2 头部逐行**（1,500 字）：`921/922/923/980/981/982/991` 格式语句；`atomic #s of gases:`、`relative fractions:`、`ntemp ndens`、`ngrups` 独占行（cn4）vs 同行（cnr）。
- **12.3 `.cn4` 逐块语义**（1,800 字）：18 块逐一给字段名、形状、单位、公式；计数闭合公式。
- **12.4 `.cnr` 与 `ntrad` 反解**（700 字）：余数反解公式；实测 8 个文件；不整除情形标 unknown。
- **12.5 IONMIX 单位换算**（500 字）：`J/cm³ → Mbar`（1e-5）；`J/g → erg/g`（1e7）；`cm/s → um/ns`（1e-5）；`n_ion` 是数密度、质量密度需 `<A>`。

*来源：`[IONMIX]`。* **网络：ABJT / MacFarlane CPC 56 (1989) 259–278 书目核验 → 仅书目。**
*表：T26 cn4 十八块字段表；T27 格式语句表；T28 cnr 七块表；T29 换算因子表。图：F9 cn4 块布局图。

#### 第 13 章 SNOP 与 Thermos 格式族（4,000 字）

- **13.1 SNOP namelist `&daten`**（2,000 字）：NT/NR/NG/NP、Z、RHO1/RHO2、T1/T2、X1/X2、IGROUP 五种、F0/F1、FG、EQ、IDEG、LINEPRO、DREK、XGRIEM、AV、FACT、NSIGMA、NPLA/NROSS/NEPS/NZ；输出 SNOP.INPUT → SNOP.INHALT + SNOP.TAB。
  - **单位一致性提示**：`[SNOP]` 明文写 `T1/T2/X1/X2 in keV`，而 `FG/F0/F1 in eV`——**同一文件内两种温度/能量单位并存**，是极隐蔽的坑。
- **13.2 Thermos 格式**（2,000 字）：`*.ini`（ElementName/Temperature/Density/Frequency）；伴随文件 `*_Planck.dat`/`*_Rosseland.dat`/`*_Z.dat`(eV, 作废)/`*_Zeff.dat`(keV)；无 EOS 元素清单；Mn 数据错误。

*来源：`[SNOP]` `[THERMOS]`。* **网络：SNOP 的 Eidmann 1994 LPB 12(2):223-244 书目核验 → 仅书目。**
*表：T30 SNOP 参数表；T31 Thermos 文件族表；T32 无 EOS 元素表。

#### 第 14 章 辅助与边缘格式（4,000 字）

- **14.1 材料级幂律/参数文件**（1,200 字）：`mat_Al-1.0/README`、`mat_Ba`、`mat_Ge`、`mat_Au/Au_Rosseland_2003POPHammerRosen.readme`、`mat_Sn/Sn_Planck_1987JQSRT.readme`、`mat_CELIA`、`Ta2O5/Ta2O5_mop.readme`；幂律 `κ = a·T^s·ρ^r` 与出处。
- **14.2 曲线与常数文件**（1,200 字）：`Albedo.xml`（Type=0/1/2 对应 Be/Au/Al/W/Pb/U）、`ScalingLaws.dat`（Zeldovich-Raizer, WorkOp-III）、`density.dat`（NIST Z/A, I, ρ）、`Reflectivity.dat`、`AtomicWeightTable.txt`、`DatabaseIndex.xml`、`Crystal/*`、`XrayMassCoef/*`、`RadiativeCoolingRates/*`（Post 1977 / Coppola 2011）、`HeatCapacity/*`。
- **14.3 二种"自描述表头"范式**（800 字）：`.coldopacity`（第 1 行列名、第 2 行单位、逐列对齐）；`.hug`（`#` 注释行方括号内单位，可带缩放因子）。
- **14.4 公式字段（muParser）**（800 字）：26 函数 / 15 运算符 / 优先级；用于 `ScalingLaws` 等字段。

*来源：`[QSEOS]` `[MU]`。* **网络：NIST 元素常数（Z/A、平均激发能）抽样核验 → 补白 + 核验。**
*表：T33 材料幂律拟合表；T34 albedo 参数表；T35 muParser 函数/运算符表。

---

### 附录（约 6,000 字）

- **附录 A 单位换算总表与推导链**（1,200 字）：所有换算因子 × 推导链 × 源。
- **附录 B 格式速查卡**（1,500 字）：每族一页（触发条件 / 表头 / 字段 / 单位 / 计数公式 / 样本 / 陷阱）。
- **附录 C 实测样本索引**（1,200 字）：路径 + 字节数 + 关键表头行（≥30 个文件）。
- **附录 D 检索与校验片段**（600 字）：计数守恒校验的可复制片段（语言中立伪码 + 少量 Python）。
- **附录 E 实现现状与已知缺口**（900 字，**brief，非主线**）：哪些族有解析器、已知缺口（Crystal/PowerLaws/Reflectivity/XrayMassCoef/RadiativeCoolingRates 无专用解析器；FEOS 原生 payload 列序不可还原；PROPACEOS 版权保护）。**明确声明**：现实现不完整、将修订，故不作为主线。
- **附录 F 参考书目**（600 字）：分两块——（1）本地源（相对路径 + 字节数），（2）网络核验源（URL + 访问日期，`[S-WEB]` 标注）。

---

## 3. 字数分配汇总（合计 88,000）

| 部分 | 章 | 字数 |
|---|---|---|
| 前置 | 封面/指南/术语/符号 | 3,000 |
| 上编 | 第 0 章 总论 | 5,000 |
| 上编 | 第 1 章 识别分派 | 6,000 |
| 上编 | 第 2 章 字节级解析 | 7,000 |
| 上编 | 第 3 章 坐标系网格 | 6,000 |
| 上编 | 第 4 章 语义与单位 | 8,000 |
| 上编 | 第 5 章 转换反演插值 | 7,000 |
| 上编 | 第 6 章 陷阱总集 | 3,000 |
| **上编小计** | | **42,000** |
| 下编 | 第 7 章 SESAME | 6,000 |
| 下编 | 第 8 章 MULTI EOS/OPAC | 6,000 |
| 下编 | 第 9 章 Hyades | 6,000 |
| 下编 | 第 10 章 FEOS/MPQeos | 5,000 |
| 下编 | 第 11 章 LEDCOP/ATOMIC | 6,000 |
| 下编 | 第 12 章 IONMIX | 6,000 |
| 下编 | 第 13 章 SNOP/Thermos | 4,000 |
| 下编 | 第 14 章 辅助边缘 | 4,000 |
| **下编小计** | | **43,000** |
| 附录 | A–F | 6,000 |
| **总计** | | **88,000** |

（上编+下编+附录+前置 = 3,000+42,000+43,000+6,000 − 重叠计 = 精确 88,000，留 8,000 冗余超 80k 目标。）

---

## 4. 推荐图表清单

### 表（≥35 张，编号 T1 起）
T1 单位总表；T2 扩展名映射；T3 表头魔数；T4 定宽规格；T5 计数守恒公式；T6 实测锚点；T7 u 网格分段；T8 网格可插值性；T9 温度单位对照；T10 数据型标识符；T11 换算推导链；T12 材料幂律；T13 陷阱对照；T14 SESAME 表型编码；T15 material.base 关键字；T16 F1 字段；T17 F2 字段；T18 Hyades 表号区间；T19 Hyades 表号清单；T20 外部不透明度 8-Block；T21 MPQeos 字段；T22 `.feos` 行 0 字段；T23 LEDCOP 头部；T24 u 网格七段；T25 TOPS FAQ；T26 cn4 十八块；T27 IONMIX 格式语句；T28 cnr 七块；T29 IONMIX 换算；T30 SNOP 参数；T31 Thermos 文件族；T32 无 EOS 元素；T33 材料幂律；T34 albedo；T35 muParser 函数/运算符；T36 溯源速查。

### 图（≥9 张，编号 F1 起）
F1 数据血缘图；F2 格式分派流程图；F3 坐标制对比图；F4 u 网格分段示意；F5 单位换算地图；F6 F2 多子表串联示意；F7 MPQeos→FEOS 演化图；F8 u 网格对数示意；F9 cn4 块布局图；F10 各族的"表头-网格-payload"三段通用骨架图。

图用 **Mermaid 或 ASCII**（不依赖外部渲染器，保证 Markdown 可读）。

---

## 5. 缺失/不可核实内容的"诚实缺口"政策

1. **凡本地文档无法确定者，一律写 `[S-UNK]`，并说明"为什么无法确定"**（如 PDF 抽取伪影、源码自注 not sure、版权保护）。
2. **绝不猜测、绝不用"应该/大概"填充**。
3. 每处缺口登记到 §6 的缺口清单，并在附录 E 汇总。
4. **已知必写的缺口**：
   - PROPACEOS：版权保护，无公开格式文档（`[PROP]`）。
   - `.feos` 原生 payload 列序：PDF 抽取伪影，无法还原。
   - `Structure_of_ASCII_data_files.txt`：仅 82 字节的整数矩阵，来源与含义不明。
   - `.cn4` 的 `deion_dn`/`deele_dn`：源码自注 `(not sure)`。
   - `.cnr` 头部 4 网格参数：用户指南未文档化，由 `write` 语句位置**推断**（标 `inferred`，非 unknown）。
   - FEOS `*.data.txt` 列名：本地无文档。
5. **冲突处理**：本地与网络冲突时，以本地为准，并在脚注记录网络说法（`[S-WEB]`）与差异。

---

## 6. 生产策略（可靠达到 80k+ 字）

### 6.1 分批写作 + 逐章字数门禁
1. 按 §2 顺序**逐章写作**，每章写完后立即统计汉字数（`len([c for c in text if '\u4e00'<=c<='\u9fff'])`）。
2. 每章设**下限门禁 = 目标 × 0.9**；未达标不得进入下一章，须补**实质内容**（补实例逐行解读、补推导链、补对照表），不得注水。
3. 建立**章节字数台账**（章 / 目标 / 实际 / 累计），每 3 章核对累计是否 ≥ 线性进度。

### 6.2 防注水纪律（与项目"重实测轻散文"文化一致）
- **每个小节必须至少含以下之一**：一张表、一段逐字节解读、一条推导链、一个实测样本引用。**不允许纯叙述小节**。
- 大量内容以**表格 + 逐行样本解读**形式承载（这类内容密度高、可核查、不注水）。
- 每章末尾设"本章实测锚点"框：列出该章引用的真实文件路径与关键数值。
- **禁止**：复述同一结论、写空泛的"注意事项"、把一条事实拆成三句说。

### 6.3 统一模板
每章固定骨架：
```
## 第 N 章 标题
  ### N.1 …
  （节末：源标注 [S-Lx] + 文件路径）
  ### 本章实测锚点        <- 必填
  ### 本章缺口            <- 无则写"无"
```
每节固定：先给**结论/规格**，再给**依据（源）**，再给**实例**。

### 6.4 术语与格式一致性
- 写作前先固化**术语表**（前置-3）与**单位书写规范**（§1.2），全文复用同一措辞。
- 物理量符号全文统一；文件名全用**相对路径**（相对 `src/Multi1D++Portable20241128/`）。

### 6.5 单文件交付
- 最终合并为单个 `MultiEOSOP格式说明.md`，用分节标题 + 目录锚点组织。
- 建议先分章写入 `.workbuddy/tmp/` 的临时分片，最后合并（合并前逐片过字数门禁）。

---

## 7. 风险与缓解

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| R1 | **与 `docs/20` 重复** | 文档无增量价值 | 严格 §0.1 分工；本文档只引上游源、不引 `docs/20`；正文重写为更原始/更逐字节版本 |
| R2 | **80k 目标靠注水** | 质量崩坏 | §6.2 防注水纪律（每节必须有表/样本/推导）；字数门禁只认实质内容 |
| R3 | **旧 `.doc` 不可读** | 核心源（Hyades/LEDCOP）拿不到 | 三路兜底：(a) 已有 `docs/extracted/` 抽取文本（可能需再生成）；(b) 任务清单已提供大量抽取事实，可直接引用并标注来源文件；(c) `docs/20` 引用过的原文片段可**回溯到源文件**核对（但不引用 `docs/20` 的结论）。写前先确认每个 .doc 是否有可读抽取文本 |
| R4 | **表号/群数实测与清单不一致** | 写错 | 凡清单数字与实测样本冲突（如 `27004003` vs 实测 `27003000`），**以实测为准并记录差异**，不强行统一 |
| R5 | **网络内容污染本地结论** | 溯源纪律破坏 | §1.3 强制 `[S-WEB]` 独立标注 + URL + 日期；冲突以本地为准 |
| R6 | **下编过深导致上编空洞** | 结构失衡 | 上编 42k 由 7 章承载，每章 3–8k，逐章门禁保障 |
| R7 | **PDF 抽取伪影** | FEOS/LEDCOP 细节错 | 凡有伪影处标 `[S-UNK]`；用兄弟文件（`.301` vs `.feos`）交叉验证 |
| R8 | **单位混淆** | 技术性错误 | 每个物理量首次出现给三元组；跨族单位差异单独成表（T1/T9） |
| R9 | **合并后编号/引用错乱** | 可读性 | 统一编号方案（章.节.小节；表 Tn；图 Fn）；合并后全局检索校验引用 |

---

## 8. 关键文件清单（写作时需访问）

**必须读取（上游源，相对 `src/Multi1D++Portable20241128/`）**
- `matter++/Readme.txt`（分派规则，530 B）
- `doc/MULTI使用的SESAME数据文件格式.docx`（183,025 B）
- `doc/Hyades 数据格式说明.doc`（57,344 B）
- `matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx` + `doc/Atomic(LEDCOP)说明.doc`（59,904 B）
- `matter++/Thermos/Readme.txt`
- `doc/SNOP.MANUAL`（6,604 B）
- `doc/multi1d7.6/manual`（13,797 B）+ `doc/multi1d7.6/README`
- `doc/GUI,IO相关.docx`（65,744 B）
- `doc/muParser.txt`（4,073 B）
- `doc/FEOS/Info.txt` + `doc/FEOS/*.pdf`
- `matter++/PROPACEOS/Readme.txt`（82 B）
- `doc/Structure_of_ASCII_data_files.txt`（82 B）
- `ionmix/ionmix/docs/IONMIX用户指南.md` + `ionmix/ionmix/src/Ionmix/abjt_03.f`
- `matter++/mat_*/*.readme`、`Albedo.xml`、`ScalingLaws.dat`、`density.dat`、`AtomicWeightTable.txt`、`DatabaseIndex.xml`

**必须抽样实测（样本文件）**
- SESAME 4×15：`matter++/mat_Al-1.0/AL_SIMPLE_PLANCK`（183 B）、`SNOP_LTE.PLANCK`（207,420 B）
- MULTI EOS：`mat_Al-1.0/AL_eos`、`mat_Au-1.0/AU_eosd`
- Hyades：`matter++/hyades/sesame/eos_2051.dat`（73,611 B）、`Opacity/opc_1022.dat`（45,258 B）、`qeos/qeos_115.dat`（366,222 B）
- FEOS/MPQeos：`Al.feos`（3.63 MB）、`Al.feos.301`（620,139 B）、`B.feos`、`B.301`
- LEDCOP：`matter++/ATOMIC/Al.txt`（13.5 MB）、`Al.NoFree`（55,383 B）、`Al.GrayOpacity_PLANCK`、`Al.MultiGroupOpacity_PLANCK`（5.49 MB）
- IONMIX：`*.cn4`（`al-imx-002.cn4` 552,192 B）、`*.cnr`
- Thermos：`Thermos/mat_Al/Al.ini`、`Al_Zeff.dat`、`Al_Z.dat`、`Al_Planck.dat`
- SNOP：`Ti_LTE.INPUT`、`opbe.inhalt`、`SNOP_LTE.PLANCK/ROSS`、`SNOP.ZEFF`、`SNOP.EPS`
- 冷不透明度：`ColdOpacity/*.coldopacity`（69 元素）
- Hugoniot：`hyades/sesame/eos_41.hug`（157 行）

**输出目标**
- `src/multi_docs/MultiEOSOP格式说明.md`（需先创建 `src/multi_docs/` 目录）

---

## 9. 建议的执行顺序

1. 先做**源可读性确认**：验证 3 个 `.doc`/`.docx` 是否可抽取为文本（若不可，走 R3 兜底）。
2. 固化**前置 + 术语表 + 单位总表**（模板基线）。
3. 写**上编**（第 0–6 章），逐章门禁。
4. 写**下编**（第 7–14 章），逐章门禁。
5. 写**附录** A–F。
6. 合并 → 全局编号校验 → 字数统计 → 引用一致性检查 → 交付。
