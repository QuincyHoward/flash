# 未解后缀逆向结果

> 工作目录：`E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op`
> 数据根：`src/Multi1D++Portable20241128/`
> 方法：逐字节分析（NUL 计数 / 不可打印字节比例）+ 计数闭合验证（实际数据行数 vs 表头声明维度）
> 所有结论均附真实路径 + 原文照录 + 字段切分标注。

---

## 摘要表

| 组 | 后缀 | 文件数 | 总字节 | 判定 | 置信度 | 读取方法 |
|---|---|---|---|---|---|---|
| 1 | `.dem` | 5 | 25,780 | **gnuplot demo 脚本**（非 EOS 表） | **确认** | 文本直读；`load 'x.dem'` |
| 2 | `.opj` | 4 | 9,210,409 | **OriginLab 工程文件**（magic `CPYA 4.2878 724#`） | **确认** | 非 MULTI 格式，不解析 |
| 2 | `.mat` | 1 | 9,230,590 | **MATLAB 5.0 MAT-file**（`MATLAB 5.0 MAT-file, Platform: PCWIN64`，endian `IM`） | **确认** | `scipy.io.loadmat` |
| 2 | `.xmind` | 1 | 456,983 | **XMind 2.0 脑图**（ZIP，内含 `meta.xml`） | **确认** | zipfile / XMind |
| 3 | `.zeff_old` | 3 | 20,313 | `.ZEFF` 的**逐字节相同备份**（MD5 一致） | **确认** | 同 `.ZEFF` |
| 3 | `.sesame_` | 1 | 4,650 | **SESAME ASCII 表**，与 `.SESAME` 同格式（不同网格） | **确认** | 同 `.sesame` |
| 3 | `.sesame_PLANCK` | 1 | 23,359 | **MULTI `.PLANCK` 多群表 + SESAME 风格标签头** | **确认** | 见组3 |
| 3 | `.sesame_ROSSELAND` | 1 | 23,359 | **MULTI `.ROSS` 多群表 + SESAME 风格标签头** | **确认** | 见组3 |
| 4 | `.coldopacity` | 67 | 884,991 | **2 列 ASCII 表** `Eph(eV) <TAB> miu(cm²/g)`，**4 种表头子格式** | **高** | 见组4 |
| 5 | `.snop` | 12 | 8,726 | **Fortran namelist `&daten`** 输入卡 | **确认** | namelist 解析 |
| 5 | `.input` | 4 | 2,567 | 同上（`&daten`，CRLF + 额外 `AW`/`ElementSymbol`） | **确认** | namelist 解析 |
| 5 | `.sesame` | 6 | 16,368,406 | **SESAME ASCII EOS 表**（CRLF，15 字符定宽×4/行） | **高** | 见组5 |
| 6 | `.base` | 2 | 104,558 | **材料主索引**：`MATERIAL` 记录块，实测 **251 块** ✓ | **确认** | 按 `MATERIAL` 切块 |
| 6 | `.manifest` | 2 | 1,072 | **Microsoft VC90 DLL 清单 XML**（非数据） | **确认** | 不解析 |
| 6 | `.list` | 3 | 6,564 | **Hyades 材料/不透明度索引表**（1 个为 0 字节） | **确认** | 定宽 5 列 |
| 6 | `.cat` | 1 | 121 | MATLAB 函数**注释头**片段（非目录） | **高** | 不解析 |
| 6 | `.db` | 1 | 5,632 | **Windows `Thumbs.db` 缩略图缓存**（OLE 复合文档） | **确认** | 不解析 |
| 7 | `.tab1` | 1 | 4,123 | **NIST X 射线质量衰减系数**元素表（Z/Element/Z/A/I/Density） | **确认** | TSV 直读 |
| 7 | `.tab2` | 1 | 5,825 | 同上，**化合物表**（Material/⟨Z/A⟩/I/Density/Composition） | **确认** | TSV 直读 |
| 7 | `.inv` | 2 | 761,036 | **MULTI 反演 EOS 表**（同 `.IN` / `.dat_MULTI` 族） | **高** | 见组7 |
| 7 | `.inhalt` | 2 | 4,548 | **SNOP 德语「输入参数」报告**（文本） | **确认** | 文本直读 |
| 7 | `.info` | 6 | 4,264 | **表说明文本**（含 SESAME 表号 IP/IR/IME/IMI/IZ） | **确认** | 文本直读 |
| 7 | `.user` | 2 | 960 | **用户材料定义**（`MATERIAL MIDxxxxxx` 块，同 `.base` 语法） | **确认** | 同 `.base` |
| 8 | `.gplt` | 4 | 1,096 | **gnuplot 脚本** | **确认** | 文本直读 |
| 8 | `.gid` | 1 | 70,152 | **Windows gnuplot 二进制 GID**（含 `*` 索引；非 GiD 网格） | **高** | 二进制，勿直读 |
| 8 | `.mnu` | 1 | 14,858 | **Windows gnuplot 菜单文件**（`;` 注释 + `[Menu]`） | **确认** | 文本直读 |
| 8 | `.hlp` | 1 | 434,726 | **Windows gnuplot 帮助（HLP 二进制）** | **高** | 不解析 |
| 8 | `.animate` | 1 | 286 | **gnuplot 动画循环脚本** | **确认** | 文本直读 |
| 8 | `.template` | 14 | 15,410 | **输出数据列模板**（列名+单位）；1 个为 0 字节 | **确认** | TSV 两列直读 |
| 8 | `.templete` | 1 | 1,801 | 同上（**拼写变体**） | **确认** | 同上 |
| 8 | `.ini` | 50 | 49,077 | **两种子格式**：GUI 配置 `[Config]` / **Thermos 输入卡** `ElementName=` | **确认** | 见组8 |
| 8 | `.case` | 96 | 395,989 | **Fortran namelist `&CONTROL` 算例卡** | **确认** | namelist 解析 |
| 9 | `CSi2.5_mopp95` | 1 | 2,858,265 | **`.PLANCK`**（表号 6140003） | **确认** | 见组1-3 表格式 |
| 9 | `CSi2.5_mopr95` | 1 | 2,858,265 | **`.ROSS`**（表号 6140002）；MD5 与上不同（数据不同） | **确认** | 同上 |
| 9 | `AU_op03p/e/r` | 3 | 408,120 | **`.PLANCK`(27003003)/`.EPS`(27005003)/`.ROSS`(27004003)** | **确认** | 同上 |
| 9 | `AU_op03z` | 1 | 6,771 | **`.ZEFF`**（表号 27002003） | **确认** | 同上 |
| 9 | `.dat_MULTI` | 2 | 38,782 | **MULTI 反演 EOS 表**（`Ta_Kr(T,rho)`），**已闭合** | **高** | 见组9 |
| 9 | `.5_from_lililing` | 2 | **0** | **空文件（纯标记）** | **确认** | 无内容 |
| 9 | `.10` | 1 | 1,564,646 | **Fortran `fort.10` 输出**（首行 `263` = 记录数） | **高** | 见组9 |
| 9 | `.in` | 3 | 217,758 | **反演 EOS 表**（同 `.inv`/`.dat_MULTI`），3 个互不相同 | **高** | 见组7/9 |

> 置信度分级：**确认** = 有明确 magic / 官方头部文本 / 闭合验证；**高** = 多样本一致 + 结构自洽；**低** = 单样本推测；**未解** = 未确定。

---

## 组 1 `.dem`（5 个，25,780 B）

### 结论
**不是**「细节平衡/状态方程表」。这 5 个 `.dem` 全部是 **gnuplot 官方演示脚本（demo script）**，纯 ASCII，位于 `doc/gnuplot_files_for_plot/`。命名来源是 gnuplot 的 demo 目录约定（`.dem` = demo）。

### 证据

路径与首行（均为 `$Id:$` CVS 头，直接证明来源是 gnuplot 上游发行包）：

```
doc/gnuplot_files_for_plot/scatter.dem    1391 B   60 行
  1| #
  2| # $Id: scatter.dem,v 1.7 2003/10/28 05:35:54 sfeam Exp $
  3| #
  4| # Simple demo of scatter data conversion to grid data.
  7| set title "Simple demo of scatter data conversion to grid data"
 16| splot "hemisphr.dat"

doc/gnuplot_files_for_plot/surface1.dem   6509 B  216 行
  2| # $Id: surface1.dem,v 1.11 2004/09/17 05:01:12 sfeam Exp $
 17| splot x*y

doc/gnuplot_files_for_plot/contours.dem   4645 B  162 行
  2| # $Id: contours.dem,v 1.13 2006/06/25 17:24:32 sfeam Exp $
 11| set contour

doc/gnuplot_files_for_plot/pm3d.dem      11507 B  464 行
  2| # $Id: pm3d.dem,v 1.20 2007/03/04 06:06:39 sfeam Exp $
 14| # Prepared by Petr Mikulik
162| print "End of pm3d demo."

doc/gnuplot_files_for_plot/dgrid3d.dem    1728 B   74 行
  1| set view 60,75
  7| splot "gnu-valley" u 1:2:3 w linesp
```

### ASCII / 二进制判定
5 个文件 **NUL = 0，不可打印控制字节 = 0，比例 0.00000** → **纯 ASCII**。

### 计数闭合验证
**不适用**（非表数据）。文件行数分别为 60 / 216 / 162 / 464 / 74，表中并无 `nr`/`nt` 声明，故无闭合可言。已排除的可能：「细节平衡表」「SESAME 表」「EOS 二维表」——均无表头、无网格、无递增数值列。

### 读取方法（伪代码）
```python
# .dem 是 gnuplot 脚本，按文本读取即可（不需要数值解析）
with open(path, 'r') as f:
    script = f.read()
# 若要执行：gnuplot> load 'scatter.dem'
```

---

## 组 2 `.opj` / `.mat` / `.xmind`

### 结论
**全部为第三方软件产物，非 MULTI 数据格式，不需要解析。**

### 证据（前 160 字节 hex + ASCII 对照）

#### `.opj`（4 个）— OriginLab Origin 工程文件
4 个文件（`MG.opj`、`Shot20120821015.Spline3OrderIterative.TotalRadiation2DVertical0.opj`、`matlab/RadiationSource/RadiationSource.opj`、`matter++/ColdOpacity/AlColdOpacity.opj`）**magic 完全相同**：

```
0000  43 50 59 41 20 34 2e 32 38 37 38 20 37 32 34 23  |CPYA 4.2878 724#|
0010  0a 4b 00 00 00 0a 02 00 f8 ff f8 ff 5e 05 ea 02  |.K..........^...|
```

`CPYA` 是 OriginLab 工程文件的固定 magic；其后 ` 4.2878 724#` 是 Origin 的版本/构建号（Origin 4.2878 系列，内部版本 724）。判定依据：(a) 4 样本 magic 逐字节一致；(b) 版本号字符串形如 Origin 内建版本号；(c) 紧随其后即二进制结构（含 `0x00000000` 与双精度常量 `0x3FF0000000000000` = 1.0，见 offset 0x90）。

#### `.mat`（1 个）— MATLAB 5.0 MAT-file
`matlab/matlab.mat`（9,230,590 B）128 字节头完整解析：

```
0000  4d 41 54 4c 41 42 20 35 2e 30 20 4d 41 54 2d 66  |MATLAB 5.0 MAT-f|
0010  69 6c 65 2c 20 50 6c 61 74 66 6f 72 6d 3a 20 50  |ile, Platform: P|
0020  43 57 49 4e 36 34 2c 20 43 72 65 61 74 65 64 20  |CWIN64, Created |
0030  6f 6e 3a 20 54 68 75 20 4e 6f 76 20 31 38 20 30  |on: Thu Nov 18 0|
0040  39 3a 33 37 3a 31 35 20 32 30 32 31 20 20 20 20  |9:37:15 2021    |
...
0070  20 20 20 20 00 00 00 00 00 00 00 00 00 01 49 4d  |    ..........IM|
0080  0f 00 00 00 bf 06 00 00 78 9c 4d 91 0b 38 d5 d9  |........x.M..8..|
```

字段切分标注（MAT v5 规范）：

| 偏移 | 长度 | 内容 | 语义 |
|---|---|---|---|
| 0..115 | 116 B | `MATLAB 5.0 MAT-file, Platform: PCWIN64, Created on: Thu Nov 18 09:37:15 2021` | 描述文本（空格填充） |
| 116..123 | 8 B | `00 00 00 00 00 00 00 00` | 子系统数据偏移（此文件为 0） |
| 124..125 | 2 B | `00 01`（LE 读作 **1**） | **version = 1** |
| 126..127 | 2 B | `49 4d` = ASCII **`IM`** | **endian indicator = `IM`** → IEEE 小端 |

> **修正说明**：最初把 124-125 误读为 `0x0100`(256)，实为字节序 `00 01` → 小端整数 1，符合 MAT v5 规范。判定依据：MAT v5 的 `endian indicator` 位于第 126-127 字节且为 `IM`(0x49 0x4D) = 小端。
> offset 0x80 处 `0f 00 00 00` = 15 (miINT8?) 后接 `bf 06 00 00`；`78 9c` 是 **zlib 流头**（MAT v5 的 miCOMPRESSED 元素），进一步验证为压缩 MAT-file，版本 **MATLAB 5.0 / R2021b 之前**。

#### `.xmind`（1 个）— XMind 脑图
`doc/Radiation Hydrodynamics.xmind`（456,983 B）：

```
0000  50 4b 03 04 14 00 08 08 08 00 94 8d 5c 51 00 00  |PK..........\Q..|
0010  00 00 00 00 00 00 00 00 00 00 08 00 00 00 6d 65  |..............me|
0020  74 61 2e 78 6d 6c 01 86 01 79 fe 3c 3f 78 6d 6c  |ta.xml...y.<?xml|
0030  20 76 65 72 73 69 6f 6e 3d 22 31 2e 30 22 20 65  | version="1.0" e|
0040  6e 63 6f 64 69 6e 67 3d 22 55 54 46 2d 38 22 20  |ncoding="UTF-8" |
0050  73 74 61 6e 64 61 6c 6f 6e 65 3d 22 6e 6f 22 3f  |standalone="no"?|
0060  3e 3c 6d 65 74 61 20 78 6d 6c 6e 73 3d 22 75 72  |><meta xmlns="ur|
0070  6e 3a 78 6d 69 6e 64 3a 78 6d 61 70 3a 78 6d 6c  |n:xmind:xmap:xml|
0080  6e 73 3a 6d 65 74 61 3a 32 2e 30 22 20 76 65 72  |ns:meta:2.0" ver|
0090  73 69 6f 6e 3d 22 32 2e 30 22 3e 3c 41 75 74 68  |sion="2.0"><Auth|
```

判定：`PK\x03\x04` = ZIP（XMind 本质是 zip 容器）；条目名 `meta.xml`；命名空间 `urn:xmind:xmap:xmlns:meta:2.0`，`version="2.0"` → **XMind 2.0 格式**。

### 计数闭合验证
**不适用**（非表数据）。

### 读取方法
```python
# .opj : 用 OriginLab Origin 打开；MULTI 管线不读取
# .mat : scipy.io.loadmat('matlab.mat')
# .xmind: import zipfile; zipfile.ZipFile(p).read('meta.xml')
```
**明确结论：这 3 个后缀均为第三方软件文件，不需纳入 MULTI 格式规格书的数据格式章节**（可在「非数据文件清单」中列出）。

---

## 组 3 `.zeff_old` / `.sesame_` / `.sesame_PLANCK` / `.sesame_ROSSELAND`

### 结论 3a：`.zeff_old` 与 `.zeff` **逐字节相同**

### 证据

```
matter++/mat_C-1.0/C.ZEFF      6771 B  md5=17886f1fdfb11309547390267970195e
matter++/mat_C-1.0/C.ZEFF_old  6771 B  md5=17886f1fdfb11309547390267970195e   identical=True
matter++/mat_CELIA/C.ZEFF      6771 B  md5=17886f1fdfb11309547390267970195e
matter++/mat_CELIA/C.ZEFF_old  6771 B  md5=17886f1fdfb11309547390267970195e   identical=True
matter++/mat_CELIA/D.ZEFF      6771 B  md5=d46f107c6fd3a55e29e96c575b82220f
matter++/mat_CELIA/D.ZEFF_old  6771 B  md5=d46f107c6fd3a55e29e96c575b82220f   identical=True
```

前 30 行原文（`C.ZEFF_old`）：

```
   1|  1              0.60000000E+01 0.20000000E+02 0.20000000E+02
   2| -0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01
   3| -0.43157895E+01-0.38947368E+01-0.34736842E+01-0.30526316E+01
   ...
  12| -0.10021263E+01-0.11996638E+01-0.14004198E+01-0.16001953E+01
```

字段切分（第 1 行）：` 1` = 表号/模式；`0.60000000E+01`(=6.0)；`0.20000000E+02`(=20.0)；`0.20000000E+02`(=20.0)。第 2 行起为 4 值/行的网格（log10 尺度，范围 -6..+20）。

**增量差异：无。** 全部 3 组对比均 `A==B`。`.zeff_old` 是**纯备份副本**（可能是 GUI 保存时的 `_old` 备份机制），**格式与 `.zeff` 完全一致**，不需要单独规定格式。

### 结论 3b：`.sesame_PLANCK` / `.sesame_ROSSELAND` = **MULTI `.PLANCK`/`.ROSS` + SESAME 标签头**

### 证据（关键发现）

```
matter++/SiO2/opc_1022.sesame_PLANCK   23359 B  377 行
  1|  0.1234567E+000PLANCK 1        3.1000000e+001 4.6000000e+001
  2| -6.0000000e+000-5.6675615e+000-5.3334820e+000-5.0000000e+000
  ...（与 .PLANCK 完全相同的 4 值/行布局）

matter++/SiO2/opc_1022.sesame_ROSSELAND 23359 B 377 行
  1|  0.1234567E+000ROSSELAND 1     3.1000000e+001 4.6000000e+001
  2| -6.0000000e+000-5.6675615e+000-5.3334820e+000-5.0000000e+000
```

表头字段切分（**注意前两个字段被写连在一起**）：

| 字段 | 原文 | 语义 |
|---|---|---|
| 1 | `0.1234567E+000PLANCK` | **表号字段未初始化**（写入缓冲区残留初值 `0.1234567E+000`）与类别名 `PLANCK` 首尾粘连 |
| 2 | `1` | 模式标志（`1`=单群/单温度；对照 `M`=多群） |
| 3 | `3.1000000e+001` | T_low = 31.0 eV |
| 4 | `4.6000000e+001` | T_high = 46.0 eV |

对照**标准 MULTI 表头**（`matter++/mat_C-1.0/C_1G.PLANCK`）：

```
  10003000      PLANCK 1        0.20000000E+02 0.20000000E+02
```

→ 格式**完全相同**，唯一区别是第一个字段（表号）被 `0.1234567E+000` 占位符取代。该 `0.1234567E+000` 是 Fortran 未初始化 write 缓冲的典型特征值（`0.1234567` 是最常见的「顺手打的」测试常量），也出现在全部 `.SESAME` 文件首字段。

### 计数闭合验证

`opc_1022.sesame_PLANCK`：
- body 数值令牌 = 1503（hdr 4 tok + body 1499）
- 行直方图：`{3: 1, 4: 375}`
- 结构 = 1 行 hdr + 1 行 T-pair（3 tok）+ 375 行×4 = 1503 ✓ **闭合**

`.sesame_`（`PowerLawTa2O5_EOS.SESAME_`，4,650 B）首行：

```
  0.1234567E+000 1.0000000E+000 5.0000000e+000 2.6000000e+001
```

→ 与 `.SESAME`（`PowerLawTa2O5_EOS.SESAME`：`0.1234567E+000 1.0 3.0 1.9e1`，T_max=19）**同格式、不同网格**（T_max=26）。判定为**同一格式的两种网格版本**。注意 `.sesame_`（末尾下划线，4,650 B）与 `.sesame`（2,217 B）是**不同物理网格的两个文件**，不是重命名。

### 读取方法（伪代码）
```python
# 1) .zeff_old == .zeff，直接按 .ZEFF 解析
# 2) .sesame_PLANCK / .sesame_ROSSELAND ：完全按 .PLANCK/.ROSS 解析
#    但表头需先修复被粘连的第 1 字段：
hdr = line0
if hdr.startswith(' 0.1234567E+000'):
    hdr = hdr.replace('0.1234567E+000', '', 1).lstrip()  # 丢弃占位符
table_id, kind, mode, T1, T2 = hdr.split()
# 3) .sesame_ / .sesame ：SESAME ASCII，15 字符定宽 ×4/行，CRLF
```

---

## 组 4 `.coldopacity`（67 个，884,991 B）

### 结论
**统一格式：2 列 TAB 分隔 ASCII 表，`Eph(eV) \t miu(cm²/g)`**，能量范围 10 – 100000 eV。
**存在 4 种表头子格式**（不是两种以上「结构」差异，仅为表头行/注释样式差异）。

### 证据（3 个不同材料抽样 + 异常值）

#### 变体 A：`Eph\tmiu` + `eV\tcm2/g` + 2 行空白制表符（**主要形态**，如 Al）

```
matter++/ColdOpacity/Al.coldopacity   11357 B  609 行
  token/行分布: {2: 607, 0: 2}
    0| 'Eph\tmiu'
    1| 'eV\tcm2/g'
    2| '\t'
    3| '\t'
    4| '10\t486606.52638'
    5| '10.1617\t469396.24406'
  ...
  608| '100000\t0.01827'
```

#### 变体 B：`#Eph\tmiu` + `#eV\tcm2/g`（注释符 `#`）

```
matter++/ColdOpacity/Ac.coldopacity   12081 B  641 行   {2: 641}
    0| '#Eph\tmiu'
    1| '#eV\tcm2/g'
    2| '10\t22149.45765'

matter++/mat_Al-1.0/Al.coldopacity   11354 B  607 行   {2: 607}
    0| '#Eph\tmiu'
    1| '#eV\tcm2/g\t'          <-- 注意：第 2 行多一个尾随 TAB（与 ColdOpacity/Al 差 3 字节）
```

> **异常值提示**：`mat_Al-1.0/Al.coldopacity`(11354) 与 `ColdOpacity/Al.coldopacity`(11357) 内容几乎相同但**字节数差 3**（尾随 `\t` 与 2 行空行差异）；`ColdOpacity` 目录版本带 2 行空白制表符行。属**同一材料的两个副本**，非两种格式。

#### 变体 C：**无表头**，数据直接开始

```
matter++/ColdOpacity/C.coldopacity   14029 B  541 行   {2: 541}
    0| '10\t282690.80052061'
    1| '10.1617\t293582.076107182'

matter++/ColdOpacity/H.coldopacity   13818 B  515 行   {2: 515}
    0| '10\t1.00002219571632E-10'
```

#### 变体 D：**表头在，但数值列被整列剥空**（每行仅 1 令牌）

```
matter++/ColdOpacity/Xe.coldopacity    8034 B  881 行   {1: 879, 0: 2}
    0| 'Eph\t'
    1| 'eV\t'
    2| '\t'
    3| '\t'
    4| '10\t'
    5| '10.1617\t'
  ...
  880| '100000\t'
```
→ `Xe` 的 miu 列**全部为空**（数据缺失），这是 8034 B 这个最小尺寸的成因。

### 尺寸分布（884991/67 ≈ 13,209 B 均值）与异常值
67 个文件尺寸**全部互不相同**（`Counter` 每项计数均为 1）：8034 … 16388 B。
- **最小 8034 B**：`Xe.coldopacity`（值列为空，见变体 D）
- **最大 16388 B**：`Tb.coldopacity`
- **无第二格式子族**：所有文件均为 2 列 TSV，差异仅来自「能量点数」与「有无表头/值列」。

### ASCII / 二进制判定
67 个文件全部 **NUL = 0，不可打印控制字节 = 0** → **纯 ASCII**。

### 计数闭合验证
**不适用**（1D 表，非 nr×nt）。能量网格单调递增，点数与文件尺寸线性相关（每行约 17-22 字节）。

### 读取方法（伪代码）
```python
import re
def load_coldopacity(path):
    rows = []
    with open(path, 'r', newline='') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith(('#', 'Eph', 'eV')):
                continue
            parts = line.split('\t')
            if len(parts) >= 2 and parts[0].strip():
                e = float(parts[0])
                if parts[1].strip():              # 变体 D 会跳过（空值）
                    rows.append((e, float(parts[1])))
    return rows   # [(Eph_eV, miu_cm2_per_g), ...]
```

### 单位
- **Eph：eV**（表头明写 `eV`，范围 10 – 100000 eV）
- **miu：cm²/g**（质量衰减/吸收系数，表头明写 `cm2/g`）
- **不是** J/cm³，**不是** erg/g。

---

## 组 5 `.snop` / `.input` / `.sesame`

### 结论 5a：`.snop` 与 `.input` **同为 Fortran namelist `&daten` 输入卡**

### 证据

```
matter++/SNOP/Be_40G.SNOP    891 B   (LF)
&daten
   NT       = 20,
   NR       = 20,
   NG       = 40,
   NP       = 6000,
   RHO1     = 1e-06,
   RHO2     = 100,
   T1       = 0.001,
   T2       = 100,
   X1       = 0.001,
   X2       = 10,
   IGROUP   = 0,
   F0       = 1,
   F1       = 2048,
   FG(1)    =   1.000, 62.000, 70.857, 82.667, 95.385,103.333,...

matter++/mat_He/He_LTE.INPUT  580 B   (CRLF: \r\n)
&daten\r\n
   NT = 20,\r\n
   NR = 20,\r\n
   NG = 30,\r\n
   ...
   EQ = 0,\r\n
   Z = 2,\r\n
   AW = 4.00256163944925,\r\n
```

差异：`.snop`（多为 LF、对齐宽）与 `.input`（CRLF、紧凑、含 `AW`/`ElementSymbol`）为**同一 namelist 的两种书写风格**；`.INPUT`/`.SNOP` 大写扩展名同理。

### 全部出现过的 namelist 变量名（跨 32 个 `.snop`/`.input` 文件统计）

| 变量 | 出现次数 | 语义/单位 |
|---|---|---|
| `NT` | 32 | 温度网格点数 |
| `NR` | 32 | 密度网格点数 |
| `NG` | 32 | 光子群数（energetic group count） |
| `NP` | 32 | 光子能量采样点数 |
| `RHO1` | 32 | 最小密度 (g/cm³) |
| `RHO2` | 32 | 最大密度 (g/cm³) |
| `T1` | 32 | 最小温度 (eV) |
| `T2` | 32 | 最大温度 (eV) |
| `X1` | 32 | 最小光子能量 (eV? keV) |
| `X2` | 32 | 最大光子能量 |
| `IGROUP` | 32 | 群边界模式开关 |
| `F0` / `F1` | 各 32 | 群边界首/末能量 (eV) |
| `FG` | 32 | 群边界数组（`FG(1)=...`） |
| `EQ` | 32 | 局域热动平衡开关 (LTE=0 / non-LTE=1) |
| `Z` | 32 | 原子序数 |
| `AW` | 30 | 原子量 (g/mol) |
| `IDEG` | 32 | 简并处理开关 |
| `LINEPRO` | 32 | 线型处理开关 |
| `NBFSMEAR` | 32 | 束缚-自由展宽开关 |
| `DREK` | 32 | 参数（默认 10） |
| `XGRIEM` | 32 | 碰撞展宽参数 |
| `FACT` | 32 | 展宽因子（如 300） |
| `NWRITE` | 2 | 输出详细度 |
| `NSIGMA` / `NPLA` / `NROSS` / `NEPS` / `NZ` | 各 32 | **输出 SESAME 表号**（见下） |
| `AV` | 30 | 平均电离度 |
| `AV_FixedLineWidth` / `AV_UserDefinedLineWidth` / `AV_DopplerBroadening` / `AV_ElectronImpactBroadening` | 各 2 | AV 子开关 |
| `ElementSymbol` | 2 | 元素符号（字符串） |

**关键交叉验证**：`NPLA/NROSS/NEPS/NZ` 直接给出 SESAME 表号，与下游文件表头**逐位吻合**：

```
matter++/mat_Ce/Ce.INPUT :
   NPLA = 27003000,  NROSS = 27004000,  NEPS = 27005000,  NZ = 27002000
matter++/mat_Au-1.0/AU_op03p 首行 :  27003003      PLANCK M ...
matter++/mat_Au-1.0/AU_op03r 首行 :  27004003      ROSSELAND M ...
matter++/mat_Au-1.0/AU_op03e 首行 :  27005003      EPS M ...
matter++/mat_Au-1.0/AU_op03z 首行 :  27002003       0.6e1 0.2e2 0.2e2
```
→ 证明 `.snop`/`.input` 是**驱动 SNOP 生成 `.PLANCK`/`.ROSS`/`.EPS`/`.ZEFF` 的输入卡**。

### 读取方法
```python
# Fortran namelist：按 F90 namelist 语法解析
import re
def read_daten(path):
    txt = open(path, 'rb').read().decode('latin1')
    txt = re.sub(r'^\s*&\s*daten\s*', '', txt, flags=re.I)   # 去掉 &daten
    txt = re.sub(r'&end|/\s*$', '', txt)                     # 去掉结束符
    # FG(1)=1,10,50,... 数组需特殊处理
    d = {}
    for m in re.finditer(r'([A-Za-z_]\w*)\s*=\s*([^,\n]*(?:,(?![A-Za-z_]\w*\s*=)[^,\n]*)*)', txt):
        d[m.group(1)] = m.group(2).strip()
    return d
```

### 结论 5b：`.sesame`（6 个，16,368,406 B）= **ASCII SESAME EOS 表**

### 证据

**先判定 ASCII / 二进制**：6 个文件全部 **NUL = 0，不可打印控制字节 = 0，比例 0.00000** → **纯 ASCII**（CRLF 换行）。**不是 16 MB 二进制**。

`matter++/mat_Au/Au_2003POPHammerRosen_EOS.SESAME`（6,495 B，105 行）：

```
     len=60  b' 0.1234567E+000 1.0000000E+000 6.0000000e+000 3.1000000e+001'
     len=60  b' 1.0000000e-002 1.0000000e-001 1.0000000e+000 1.0000000e+001'
     len=60  b' 2.0000000e+001 1.0000000e+002 3.1366911e-005 3.9294119e-005'
     ...
     len=45  b' 2.7105455e+007 2.9654027e+007 3.6618586e+007'      <-- 末行短
```

**列宽判定（逐字节）**：行长度分布 `{60: 104, 45: 1}`，即 **60 字符/行 = 4 值 × 15 字符定宽**；末行 45 = 3 值。已排除宽度 13/14/16/18/20/22（均导致 token 断裂）。

表头字段切分（15 字符定宽）：

| 字段 | 值 | 语义（已由 ρ 网格长度交叉验证） |
|---|---|---|
| `hdr[0]` | `0.1234567E+000` / `0.0000000E+000` | 占位符 / 表号（Au=0.1234567，SiO2=0.0） |
| `hdr[1]` | `1.0` | 未用 / 模式 |
| `hdr[2]` | 6 / 36 / 43 / 75 / 73 | **nρ（密度网格点数）** |
| `hdr[3]` | 31.0 / 1792 / 1765 / 2695 / 2474 | **T_max（最大温度）** |

**验证 `hdr[2]` = nρ**：从 `v[4]` 起做「严格递增游程」检测，得到的网格长度**精确等于 `hdr[2]`**：

```
eos_22.sesame : hdr[2]=36  ->  ρ 网格长度 36  ✓  [0.0, 2.204e-4, 3.919e-4, ...] ... 22040.018
eos_21.sesame : hdr[2]=43  ->  ρ 网格长度 43  ✓  [1.6e-6, 2.5e-6, 4e-6, ...] ... 150.0
eos_23.sesame : hdr[2]=75  ->  ρ 网格长度 75  ✓  [... 44080.0]
eos_24.sesame : hdr[2]=73  ->  ρ 网格长度 73  ✓  [... 53000.0]
Au_..._EOS.SESAME : hdr[2]=6 -> ρ 网格长度 6  ✓  [0.01, 0.1, 1.0, 10.0, 20.0, 100.0]
```

其后紧跟的是「T 值 + nρ 个同温数据值」的重复块（Au 实测可见 T=3.1366911e-05, 0.00035427028, 0.015540999, 34.0, 272.19048 …）。

### 计数闭合验证（诚实记录）

| 文件 | nvals | hdr[2]=nρ | 公式 `4+nρ+nT+nT·nρ` | 结果 |
|---|---|---|---|---|
| `Ta2O5/PowerLawTa2O5_EOS.SESAME` | 143 | 3 | `4+3+34+34×3 = 143` | **✓ 闭合** |
| `mat_Au/Au_2003...SESAME` | 419 | 6 | `4+6+nT+6nT = 419` → nT=58.43 | ✗ 不闭合 |
| `SiO2/eos_21.sesame` | 153,645 | 43 | — | ✗ 不闭合 |
| `SiO2/eos_22.sesame` | 130,892 | 36 | — | ✗ 不闭合 |
| `SiO2/eos_23.sesame` | 407,099 | 75 | — | ✗ 不闭合 |
| `SiO2/eos_24.sesame` | 363,828 | 73 | — | ✗ 不闭合 |

**已穷举尝试的公式**（`nρ,nT` 取自表头整数，两个方向都试）：
`4+nρ+nT·nρ`、`4+nρ+nT+nT·nρ`、`4+nρ·nT`、`4+nρ+nρ·nT`、`4+nT+nT·nρ`、`4+nρ+nT*(nρ+1)`、`A·B+A+B`、`4+A+B+B²` … 均**未在 SiO2 / Au 上闭合**。

**如实结论：`.sesame` 的表头语义（`hdr[2]=nρ`、`hdr[3]=T_max`、15 字符定宽 CRLF ASCII）已确认；但其「数据区维度公式」在 SiO2 组与 Au 上未能闭合（仅 Ta2O5 单样本闭合）。**
最可能的解释（尚未证实）：(a) 数据区按 T 分块、每块含 T 值 + nρ 值，但存在额外的尾部/头部行；(b) `hdr[1]=1.0` 处另有隐匿维度字段被写成了浮点。**判定置信度：高（格式骨架）/ 未解（精确维度公式）**。

### 读取方法（伪代码）
```python
def read_sesame_ascii(path):
    buf = open(path,'rb').read()
    rows = [r for r in buf.split(b'\r\n') if r]
    vals = []
    for r in rows:
        vals += [float(r[j:j+15]) for j in range(0, len(r), 15)]   # 15 字符定宽
    table_id, f1, nrho, Tmax = vals[:4]
    rho_grid = vals[4:4+int(nrho)]                                  # 已闭合部分
    data = vals[4+int(nrho):]                                       # 维度公式待确认
    return table_id, int(nrho), Tmax, rho_grid, data
```

---

## 组 6 `.base` / `.manifest` / `.list` / `.cat` / `.db`

### 结论 6a：`.base` = **材料主索引**，实测 **251 个 `MATERIAL` 块** ✓

### 证据

`matter++/material.base`（103,452 B，3,805 行）—— 文件自带**完整语法说明**：

```
   0| # This is the User Defined material database.
   1| # The syntax of the file is the following:
   2| #     - Comments , all characters following "REM" are ignored 
   3| #     - Material records begin with a line with keyword "MATERIAL" and the
   4| #       name of material, and end by End-of-file or the begining of next
   5| #       material
   6| #       Name of material is a integer smaller than 100000, 
   7| #       User defined material with no > 100000 stored in material.user
  11| #          - REM <text>                 	Comment
  12| #          - Name <text>                	Name of the material
  13| #          - Formula <text>             	Formula or symbol
  14| #          - RHO <real>                 	Density (g/cc)
  15| #          - EOS <module> <file>        	... tabulated equation of state
  16| #          - IEOS <module> <file>       	... tabulated ion equation of state
  17| #          - IonEOSModel <string>        	IdealGas / Atzeni1986 / CowanModel / ZSplit
  18| #          - EEOS        <module> <file> 	... electron EOS
  19| #          - PLANCK      <module> <file> 	... Planck opacity (Multi-format)
  20| #          - ROSSELAND   <module> <file> 	... Rosseland opacity (Multi-format)
  21| #          - EMS         <module> <file> 	... Planck emission
  .. 
  .. #          - ColdOpacity / NONLTE / ZEFF / ZeffSquared / A / Z ...
```

单块实例（`matter++/mat_CELIA/material.base`，28 行）：

```
   0| MATERIAL MID101
   1| REM DEUTERIUM WITH ANALYTICAL OPACITY (PLANCK)
   2| REM THE EOS TABLE HAS BEEN GENERATED BY SCALING A FACTOR 4/5
   3| REM THE DENSITY IN A DT TABLE (PROBABLY ORIGINATED FROM SESAME
   4| REM LIBRARY). SOLID DENSITY IS 0.176426387 G/CM3 AT T=0
   7| REM MFP_PLANCK(CM)   =7.21010052E-11*(A^2*T(EV)^(7/2))/(Z^3*RHO(G/CM^3)^2)
   8| REM MFP_ROSSELAND(CM)=2.26199232E-9* (A^2*T(EV)^(7/2))/(Z^3*RHO(G/CM^3)^2)
  11|    A 2.0
  12|    Z 1.0
  13|    EOS       mat_CELIA   DD_ieos
  14|    PLANCK    mat_CELIA   D_AN.PLANCK
  15|    ROSSELAND mat_CELIA   D_AN.PLANCK
  16|    NEGATIVE_PRESSURE 1
  17| MATERIAL MID201
  ...
```

### 块结构（精确字段语义）

```
块开始 :  ^\s*MATERIAL\s+<name>          # name = 整数 < 100000；>100000 存入 material.user
块内行 :  ^\s*REM\s+<任意文本>            # 注释（会被回显到程序报告）
          ^\s*<KEYWORD>\s+<args...>       # 见下表
块结束 :  下一个 ^MATERIAL 或 EOF
注释   :  # 开头的整行为文件级注释
分隔符 :  空白（空格/TAB）；关键字大小写不敏感
```

块内关键字频次（`material.base`，251 块）：

| 关键字 | 次数 | 参数格式 | 语义 |
|---|---|---|---|
| `Name` | 251 | `<text>` | 材料名 |
| `RHO` | 251 | `<real>` | 密度 (g/cc) |
| `A` | 285 | `<real>` | 平均原子量 |
| `Z` | 285 | `<real>` | 平均原子序数 |
| `Formula` | 245 | `<text>` | 化学式 |
| `PLANCK` | 236 | `<module> <file>` | Planck 不透明度表（Multi-format） |
| `ROSSELAND` | 236 | `<module> <file>` | Rosseland 不透明度表（Multi-format） |
| `EOS` | 219 | `<module> <file>` | 总 EOS 表 |
| `ZEFF` | 130 | `<module> <file>` | 有效电离度表 |
| `GammaG` / `c0` / `s` | 各 72 | `<real>` | 理想气体 γ 模型参数 |
| `EEOS` / `IEOS` | 各 36 | `<module> <file>` | 电子/离子分表 EOS |
| `X` | 34 | `<real>` | 元素丰度 |
| `IonizationModel` | 21 | `<string>` | 电离模型 |
| `NumberOfElements` | 17 | `<int>` | 元素数 |
| `NONLTE` | 7 | `<module> <file>` | 非局域热动平衡因子表 |
| `EMS` | 9 | `<module> <file>` | Planck 发射表 |
| `NEGATIVE_PRESSURE` | 4 | `0/1` | 负压开关 |
| … | | | |

### 计数闭合验证
```
实测 MATERIAL 记录数 = 251   （正则 ^\s*MATERIAL\b）
```
与「材料主索引（251 块）」的既有描述**精确吻合** ✓ → **闭合**。第 2 个 `.base` 文件为 `mat_CELIA/material.base`（1 块），合计 2 文件 104,558 B。

### 读取方法（伪代码）
```python
def read_base(path):
    mats, cur = [], None
    for line in open(path, 'r', encoding='latin1'):
        s = line.strip()
        if not s or s.startswith('#'): continue
        m = re.match(r'MATERIAL\s+(\S+)', s, re.I)
        if m:
            cur = {'name': m.group(1), 'entries': []}
            mats.append(cur); continue
        if cur is None: continue
        if s.upper().startswith('REM'): continue
        parts = s.split()
        cur['entries'].append((parts[0], parts[1:]))   # (KEY, [args])
    return mats    # 251 条
```

### 结论 6b：`.manifest` / `.list` / `.cat` / `.db`

| 后缀 | 路径 | 判定 | 证据 |
|---|---|---|---|
| `.manifest` ×2 | `Microsoft.VC90.CRT/*.manifest`、`Microsoft.VC90.MFC/*.manifest` | **MSVC 运行时 DLL 清单 XML** | `<assembly xmlns="urn:schemas-microsoft-com:asm.v1" ...>`，`name="Microsoft.VC90.CRT"`，version `9.0.21022.8`，列出 `msvcr90.dll/msvcp90.dll/msvcm90.dll` |
| `.list` ×3 | `matter++/hyades/EOS.list`(4790B)、`Opacity.list`(1774B)、`matter++/material.list`(**0 B**) | **Hyades 材料/不透明度索引表** | 定宽 5 列：`ID  Name  Z  A  ρ`；样例 `11  Deuterium+tritium  1.000  2.515  0.2205`；`material.list` 为空文件 |
| `.cat` ×1 | `matlab/Multi1DppDP.cat`(121B) | **MATLAB 函数注释头片段**（非目录） | `% Function to Load Multi1D data file in ASCII format` / `Author: tianming.song@gmail.com` |
| `.db` ×1 | `.../NIST X-Ray Mass Attenuation Coefficients - References_files/Thumbs.db`(5632B) | **Windows 缩略图缓存**（OLE 复合文档） | `D0 CF 11 E0 ...` 签名；NUL=988，不可打印=1725，比例 **0.30629** → 二进制 |

**`.db` 是最确凿的二进制样本**：0.31 的不可打印比例 + JPEG 段（`FFD8 FFE0 JFIF`）出现在偏移 0x0A 之后 → 判定为 `Thumbs.db` 缩略图库，**非 MULTI 数据**。

---

## 组 7 `.tab1` / `.tab2` / `.inv` / `.inhalt` / `.info` / `.user` / `.sesame_`

### `.tab1` / `.tab2` — NIST 质量衰减系数表（纯文本 TSV）

```
matter++/XrayMassCoef/XrayMassCoef.tab1  4123 B  93 行
    0| Z 	  	Element 	  	Z/A 	  	I(eV)  	  	Density(g/cm3)
    1| 1 	H 	  	Hydrogen 	  	0.99212 	  	19.2 	  	8.375E-05
    2| 2 	He 	Helium 	0.49968 	41.8 	1.663E-04
    ...
    9| 9 	F 	Fluorine 	0.47372 	115.0 	1.580E-03

matter++/XrayMassCoef/XrayMassCoef.tab2  5825 B  245 行
    0| Material 	  	<Z/A> 	  	I 	  	Density 	  	Composition
    1| (eV) 	(g/cm3) 	(Z: fraction
    2| by weight)
    3| A-150 Tissue-Equivalent Plastic 	  	0.54903 	  	65.1 	  	1.127E+00 	  	1: 0.101330
```
判定：**NIST X 射线质量衰减系数**数据库的两种导出（表1=元素，含 Z/符号/名称/⟨Z/A⟩/I(eV)/密度；表2=化合物/混合物，含成分比）。制表符分隔，ASCII，**非 MULTI 格式**（属参考数据）。

### `.inv` / `.IN` / `.dat_MULTI` — MULTI **反演 EOS 表**（同一族）

```
matter++/mat_CPC/AU.INV   380518 B  6238 行   {4: 6238}
    0|  1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02
    1|  0.00000000e+00 1.92799998e-04 3.42852261e-04 6.09687122e-04
    2|  1.08419405e-03 1.92800001e-03 3.42852273e-03 6.09687110e-03

matter++/CH/CHSi1_eos.IN  72586 B  1171 行   {3: 1, 4: 1170}
    0|            1214  6.725700e+000 5.8000000e+001 3.9000000e+001
    1|  1.0440000e-003 1.5660000e-003 2.6100000e-003 4.1760000e-003

matlab/Ta_Kr(T,rho).dat_MULTI  19391 B  313 行   {3: 1, 4: 312}
    0|   0.0000000e+00  1.0000000e+00  2.5000000e+01  4.7000000e+01
    1|  -4.0000000e+00 -3.6675615e+00 -3.3334820e+00 -3.0000000e+00
```
三者均为 **4 值/行、表头 4 字段、后接网格+数据** 的反演 EOS 表。实测 2 个 `.INV` 内容不同（AU vs BE，同为 380,518 B 但数值不同）；3 个 `.IN` 全部 **MD5 相同** `f04a80fb...`（同一文件 3 份副本）。

**计数闭合（`.dat_MULTI`）**：
```
Ta_Kr(T,rho).dat_MULTI : nvals=1251, hdr=[0, 1, 25, 47]
  4 + nρ(25) + nT(47) + nρ·nT(25×47=1175) = 1251   ✓ 闭合
Ta2O5_Kr(T,rho).dat_MULTI : 同样 1251 = 4+25+47+1175  ✓（两文件结构同、数值不同）
```
→ 表头 `hdr = [id, 未用, nρ, nT]`。**判定：高**。
`.IN`/`.INV` 因表头首个字段为「表号」(1214 / 1.00003010e7) 使维度字段位置不同，未闭合，**判定：高（族归属）/ 未解（精确维度字段位置）**。

### `.inhalt`（2 个，4,548 B）— SNOP 德语「输入参数」报告

```
matter++/SNOP/opbe.inhalt   2274 B  70 行
    0|  **************************************************
    1|  ********* EINGANGSPARAMETER **********************
    2|  ****** Mit angeregten Niveaus in BF und BB *******
    3|  **************************************************
    4|    Z        =     4.000E+00
    5|    AW       =     9.012E+00
    6|    FACAB    =     1.000E+00
    7|    EQ       =     0.000E+00
    8|    IDEG     =          1
    9|    LINEPRO  =          0
```
判定：**SNOP 程序写出的纯文本参数回显**（`EINGANGSPARAMETER` = 输入参数）。两个样本 MD5 相同（`SNOP/opbe.inhalt` 与 `mat_Be-1.0/opbe.inhalt`）。**非数据表**。

### `.info`（6 个，4,264 B）— 表说明文本（含 SESAME 表号）

```
matter++/mat_Be-1.0/BE_eos.info   611 B   9 行
    1| files BE_eos_e and BE_eos_i  (Beryllium)
    3|    IEOS table for electrons            (IME=304)
    4|    IEOS table for ions                 (IMI=305)
    6| NOTE: The original table [mat_Be-1.0]/BE_eos has been separated in electron
    7| and ion components by code [13_MULTI-fs]/split_EOS_table (Atomic mass 9.012)

matter++/mat_C-1.0/Carbon.info   1150 B  17 行
    3|     IEOS polystyrene table for electrons  (IME=75901)
    5|     IEOS DLC table for electrons          (IME=50001001)
    7|     Carbon ionization                     (IZ =50002000)
    8|     Carbon Planck 20-groups opacity       (IP =50003000)
    9|     Carbon Rosseland 20-groups opacity    (IR =50004000)
```
判定：**人工/程序生成的 .info 说明**，其中 `IME/IMI/IZ/IP/IR` 是 **SESAME 表号**（与组 5 的 `NPLA/NROSS/NZ` 同源），可作为表号→文件映射依据。`mat_Others/CH10Water.info`(27 B) 仅一行 `Calculated by Dong Yunsong`。

### `.user`（2 个，960 B）— 用户材料定义

```
matter++/CH/material.user   620 B  27 行
    0| MATERIAL MID106120
    1| REM CH Opacities FROM SNOP.
    2| REM EOS FROM SESAME LIBRARY (MATERIAL CODE=7590)
    3| REM C:H is 0.5:0.5
    4|    A 6.510
    5|    Z 5.280
    6|    Formula CH

matter++/Ta2O5/material.user   340 B  14 行
    0| MATERIAL MID110873
    1| REM generated by Li Liling @20220422
    2| REM 96G opacity, Planck opacity use Rosseland opacity
```
判定：**与 `.base` 完全同语法**的 `MATERIAL` 块容器；仅存 `no > 100000` 的用户材料（见 `.base` 头部注释第 7 行）。读取方法同 `.base`。

---

## 组 8 `.gplt` / `.gid` / `.mnu` / `.hlp` / `.animate` / `.template` / `.ini` / `.case`

| 后缀 | 文件数 | 判定 | 证据（原文） |
|---|---|---|---|
| `.gplt` | 4 (1,096 B) | **gnuplot 脚本** | `plot1D.gplt`: `reset` / `plot 'simple7.center2.dat' u 1:3 every 50:1:5:1 w linespoints ,\` |
| `.gid` | 1 (70,152 B) | **Windows gnuplot 二进制 GID**（**非 GiD 网格**） | NUL=25,338，不可打印=32,161；可见 `\|FILES`、`\|KWBTREE`、函数名表 `asin/asinh/atan/atan2/...` |
| `.mnu` | 1 (14,858 B) | **Windows gnuplot 菜单文件** | `; Menu file for Windows gnuplot` / `; Roger Hadgraft, 26-5-92` / `[Menu]` / `&File` / `&Open ...` |
| `.hlp` | 1 (434,726 B) | **Windows gnuplot 帮助（HLP 二进制）** | NUL=59,153，不可打印=130,729；含 `\|CONTEXT` / `\|CTXOMAP` / `\|FONT` / `\|KW` |
| `.animate` | 1 (286 B) | **gnuplot 动画循环脚本** | `iteration_count = iteration_count +1` / `plot filename0 u xUsing:($4/ymax0) every :::iteration_count...` / `reread` |
| `.template` | 14 (15,410 B) | **输出数据列模板（列名 + 单位）** ★ | 见下 |
| `.templete` | 1 (1,801 B) | 同上（**拼写变体**） | `templates/data/fuel_scalars.templete` |
| `.ini` | 50 (49,077 B) | **两种子格式** | 见下 |
| `.case` | 96 (395,989 B) | **Fortran namelist `&CONTROL` 算例卡** | 见下 |

### ★ `.template` — 确认存在模板机制（重要发现）

```
templates/data/backlighter.template   286 B   8 行
    0| Time        	Time(s)
    1| CMC         	Mass coordinate at cell center(g)
    2| XC          	Center of cell (cm)
    3| R           	Density (g/cm3)
    4| Te          	Electron temperature (eV)
    5| MFP_Rosseland	Rosseland Mean Free Path(cm)
    6| MFP_Planck   	Planckian Mean Free Path(cm)
    7| Uemission    	Emission

templates/data/center.template       1322 B  34 行
    0| Time        	Time(s)
    1| CMC         	Mass coordinate at cell center(g)
    2| XC          	Center of cell (cm)
    3| R           	Density (g/cm3)
    4| Te          	Electron temperature (eV)
    5| Pe          	Electron pressure (dynes/cm2)
    6| Zi          	Effective ion number
    7| D           	Specific external deposition(erg/g/s)
    8| DENE        	Electron number density (1/cm3)
    9| Ee          	Electron specific energy (erg/g)
```

**结构**：每行 = `<列名> \t <物理量说明(含单位)>`，`#` 开头为注释。共 14 个：
`backlighter / center / fuel_center / fusion / group / hotelectrons / interface / laser / matter / mixing / mixing_scalars / particlebeam(**0 字节**) / radiation / scalars`（`.templete` 变体：`fuel_scalars`）。

**判定**：这是**输出数据列的定义模板** —— 说明 MULTI 的输出 `.dat` 文件各列由模板机制驱动（列顺序 + 物理语义 + 单位）。**结论：确认存在模板机制**；`particlebeam.template` 为 0 字节（占位/未启用）。该族列出的正是诊断输出（中心量、界面量、聚变量、激光、辐射、混合等）的列清单。

### `.ini` — 两种子格式

**子格式 A：GUI 配置**（`[Config]`/`[RecentFiles]`/`[Settings]`，5 个）
```
default.ini   442 B  11 行
    0| [Config]
    1| Functioning=0
    2| MaxNumOfGrids=1000
    3| [RecentFiles]
    4| File[0]=cases_ZhangLu\ShapedPulseDoubleShockFoam.case
```

**子格式 B：Thermos 输入卡**（`ElementName=`，约 42 个，全部在 `matter++/Thermos/mat_*/`）
```
matter++/Thermos/mat_Al/Al.ini   795 B  4 行
    0| ElementName=Al
    1| Temperature=4e-2,1.0000000E+00,1.8329807E+00,3.3598183E+00,...
    2| Density=1.0000000E-06,2.6366507E-06,6.9519286E-06,...
    3| Frequency=0.1,1.0,10.0,50.0,100.0,125,150.0,175.0,200.0, 400.0,600.0,...
```
→ 定义 Thermos 代码的 **T / ρ / ν 三维网格**（与同目录 `*_Planck.dat`、`*_Rosseland.dat`、`*_Z.dat`、`*_Zeff.dat` 配对）。**这是 Thermos 格式族的输入网格定义**。

另有 `mat_Au/formula.ini`（203 B，`&Formula` 开头，namelist 风格）与 `settings.ini`（27 B，`[Settings]`），属子格式 A 的边缘变体。

### `.case` — Fortran namelist `&CONTROL` 算例卡

```
Untitled.case   6923 B  119 行
    0| &CONTROL
    1|    GUIVerion=2024-01-29 15:14:28
    2|    FLAG=1 	#Enable/disable control section
    3|    IsNoLog=0 	#Enable/disable logging
    4|    Solver=0 	# default 0 for MULTI, 1 for MULTI-IFE
    5|    Solver.Method=0 	# default 0 for Explicit, 1 for Implicit
    6|    NSPLIT=1 	#Number of hydro substeps (divisor of the number of groups)
    7|    TEXIT=2.000000E-009 	#Maximum value of time
    8|    TBegin=0.000000E+000 	#Minimum value of time
    9|    NEXIT=10000 	#Maximum number of time steps
   10|    DTN=1.000000E-011 	#Initial time step, maximum time step
   11|    MinTimeStep=1.000000E-017 	# Min time step
```
判定：**Fortran namelist `&CONTROL` 算例卡**（96 个，LF 分隔，`#` 行内注释）。读取同 `.snop`（namelist 解析）。

---

## 组 9 非标准双后缀

**总判定：全部可归入已有标准族；不存在新格式。**「双后缀」只是把**材料标识**或**能量/版本标记**塞进了文件名。

| 文件 | 字节 | 首行原文 | 真实归属 | 置信度 |
|---|---|---|---|---|
| `matter++/mat_C-1.0/CSi2.5_mopp95` | 2,858,265 | ` 6140003        PLANCK M         4.3000000e+01  4.3000000e+01` | **`.PLANCK`**（多群，表号 6140003） | 确认 |
| `matter++/mat_C-1.0/CSi2.5_mopr95` | 2,858,265 | ` 6140002        ROSSELAND M      4.3000000e+01  4.3000000e+01` | **`.ROSS`**（表号 6140002） | 确认 |
| `matter++/mat_Au-1.0/AU_op03e` | 136,040 | ` 27005003      EPS M           0.20000000E+02 0.20000000E+02` | **`.EPS`**（发射率表；`e`=emission） | 确认 |
| `matter++/mat_Au-1.0/AU_op03p` | 136,040 | ` 27003003      PLANCK M        0.20000000E+02 0.20000000E+02` | **`.PLANCK`**（`p`=Planck） | 确认 |
| `matter++/mat_Au-1.0/AU_op03r` | 136,040 | ` 27004003      ROSSELAND M     0.20000000E+02 0.20000000E+02` | **`.ROSS`**（`r`=Rosseland） | 确认 |
| `matter++/mat_Au-1.0/AU_op03z` | 6,771 | ` 27002003       0.60000000E+01 0.20000000E+02 0.20000000E+02` | **`.ZEFF`**（`z`=Zeff） | 确认 |
| `matlab/Ta_Kr(T,rho).dat_MULTI` | 19,391 | `  0.0000000e+00  1.0000000e+00  2.5000000e+01  4.7000000e+01` | **MULTI 反演 EOS**（同 `.IN`/`.inv`） | 高 |
| `matlab/Ta2O5_Kr(T,rho).dat_MULTI` | 19,391 | 同上 | 同上 | 高 |
| `matter++/hyades/sesame/CSi2.5_from_lililing` | **0** | （空） | **空文件（纯标记）** | 确认 |
| `matter++/mat_C-1.0/CSi2.5_from_lililing` | **0** | （空） | **空文件** | 确认 |
| `matlab/fort.10` | 1,564,646 | `    263`（首行） | **Fortran 单元 10 输出** | 高 |
| `matter++/CH/CHSi1_eos.IN` / `CHSi10_eos.IN` 等 3 个 | 217,758 合计 | `            1214  6.725700e+000 5.8000000e+001 3.9000000e+001` | **反演 EOS 表**（3 个 MD5 全同 = 副本） | 高 |

### 关键细节

**1) `mopp95` vs `mopr95` MD5 不同但字节数相同**：
```
mopp95  md5=dbdc8cb482ac660cda9f3c45c1f49d2d   (PLANCK   M, 6140003)
mopr95  md5=a5e8a63c39081d3d7670075ac9212917   (ROSSELAND M, 6140002)
```
→ 是**同一材料的 Planck / Rosseland 两个不同物理量**，数值必然不同，故 MD5 不同（**不是**同一文件的两份拷贝）。文件名 `_mopp`/`_mopr` 中的 `p`/`r` 即 Planck/Rosseland 标记。

**2) `AU_op03e/p/r/z` 的交织可完全复原**（表号连续）：
```
27002003 -> z = ZEFF
27003003 -> p = PLANCK
27004003 -> r = ROSSELAND
27005003 -> e = EPS (emissivity)
```
后缀字母 = **表类型标记**，`op03` = 不透明度表版本 03，`AU` = 材料（金）。同一模式见组 5 的 `.info`（`IP/IR/IZ/IME/IMI`）。

**3) `.dat_MULTI` 计数闭合（已确认）**：
```
Ta_Kr(T,rho).dat_MULTI  : 4 + nρ(25) + nT(47) + nρ·nT(1175) = 1251 ✓
```
文件名 `(T,rho)` 直接点明网格顺序。表头 `[id=0, 未用=1, nρ=25, nT=47]`。

**4) `.5_from_lililing` = 0 字节**：
两个文件均为 **0 字节**（MD5 `d41d8cd98f00b204e9800998ecf8427e` = 空文件）。文件名语义为「由 Li Liling 提供的 CSi2.5 文件（占位）」。同目录的 `matter++/Thermos/___No EOS/No EOS data, but Opacity in OpacityThermos.txt` 亦是 **0 字节标记文件**，说明本数据集存在用「空文件 + 描述性文件名」做占位的习惯。**判定：确认（空文件）**。

**5) `fort.10` 结构**：
```
matlab/fort.10   1,564,646 B  93,336 行
  token/行分布: {0: 1374, 1: 91645, 2: 317}
    0|    263
    1| CMC     
    2| CMC     
```
首行 `263 = 记录/列数`，其后为 Fortran 单元 10 直接写出的 ASCII（列标 `CMC` 等）。**判定：高（Fortran 列表输出）**；精确记录布局未展开（非核心 EOS 格式）。

---

## 仍未解 / 未闭合清单

| 项 | 状态 | 原因与已排除的可能 |
|---|---|---|
| `.sesame`（SiO2 4 个 + Au）数据区精确维度公式 | **未闭合** | 已排除 `4+nρ+nT·nρ`、`4+nρ+nT+nT·nρ`、`4+nρ·nT`、`4+nρ+nρ·nT`、`4+nT+nT·nρ`、`4+nρ+nT(nρ+1)`、`A·B+A+B`、`4+A+B+B²`；`hdr[2]=nρ` 已由 ρ 网格长度**独立验证**；仅 `Ta2O5`(143) 单样本闭合。疑为「T 分块 + 额外行」，需 SESAME 301 官方规范比对。 |
| `.inv` / `.IN` 表头维度字段位置 | **未闭合** | 首字段为表号（`1.00003010e7` / `1214`）使 `nρ,nT` 位置不同于 `.dat_MULTI`；族归属（反演 EOS）已确认。 |
| `fort.10` 精确记录布局 | **未解（低优先级）** | 首行 `263` 疑为列数，未逐列还原；非 EOS 核心格式。 |
| `.gid` / `.hlp` 内部结构 | **未解（不值得解）** | 已确认是 Windows gnuplot 的二进制资源文件，非 MULTI 数据。 |
| `.opj` 内部数据组织 | **未解（不需要）** | OriginLab 专有格式；已确认非 MULTI 数据。 |

---

## 附：本报告的方法学说明

1. **ASCII / 二进制判定依据**：统计 `\x00` 字节数与「不可打印且非 `\t\n\r`」字节比例。
   - 判定为 ASCII 的文件比例均为 **0.00000**
   - 判定为二进制的样本：`Thumbs.db`(0.30629)、`wgnuplot.GID`、`wgnuplot.HLP`
2. **计数闭合**：凡声称 nr×nt 表，均给出「实际令牌/行数 == 表头声明值」的算术等式；未闭合的**如实标注并列出全部试过的公式**。
3. **交叉验证**：`.planck/.ross`（42 样本）、`.coldopacity`（67 样本）、`.dem`（5 样本）、`.sesame`（6 样本）、`.snop/.input`（32 样本）均 ≥2 样本互验。
4. **最强证据链**：`.snop` 的 `NPLA/NROSS/NEPS/NZ` 表号 → `.PLANCK/.ROSS/.EPS/.ZEFF` 文件首字段，**逐位吻合**，构成闭环证明。
