# Multi1D++ EOS/不透明度数据「格式文档」清查报告

- 清查根目录: `E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/Multi1D++Portable20241128`
- 清查范围: `doc\`（含 Conservation / FEOS / References / gnuplot_files_for_plot / multi1d7.6 / solution of unsymmetry 子目录）+ `matter++\` 根及全部子目录
- 目的: 为撰写一份 8 万字以上的中文技术文档「Multi EOS/不透明度数据格式」清点所有可用的格式说明类文档与数据文件格式特征
- 方法: 纯只读；目录枚举 + 纯文本文档全读 + Office(docx/xlsx) 用 python zipfile 解包抽取 + 旧版 .doc(OLE2) 原始 UTF-16 流扫描 + 代表性数据文件头采样
- 注意: 本机 shell 无 coreutils，全部通过 `C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe` 与 Read/Glob/Grep 完成

---

## A. 文档清单总表 (Documentation Inventory)

> 说明: 目录为空者已单独标注。Ext 列为扩展名；「格式说明价值」为对 8 万字格式文档的贡献度估计。

### A.1 `doc\` 根目录

| # | 相对路径 | 大小(B) | 扩展名 | 文档性质（一句话） | 格式价值 |
|---|----------|---------|--------|-------------------|----------|
| 1 | doc\Atomic(LEDCOP)说明.doc | 59904 | .doc(旧) | LEDCOP 原子不透明度说明（旧版 Word，需外部转换；另有 docx 版见 A.8） | 中(有 docx 副本) |
| 2 | doc\GUI,IO相关.docx | 65744 | .docx | GUI/default.ini/config.ini 配置 + 程序类型(Type=0流体/1不透明度/2状态方程) + 全部输出文件变量表 | 高 |
| 3 | doc\Hyades 数据格式说明.doc | 57344 | .doc(旧) | Hyades EOS/不透明度格式（旧版；正文已在 matter++\hyades 同名 .doc 中成功提取，见 B.5） | 高 |
| 4 | doc\MULTI使用的SESAME数据文件格式.docx | 183025 | .docx | **核心**: MULTI 使用的 SESAME 数据文件格式（material.base 规则 + EOS/不透明度/Zeff/NLTE 表格结构与单位） | **极高** |
| 5 | doc\Multi1D++ and GUI4Multi1D简介.pptx | 9215703 | .pptx | 程序与 GUI 总体介绍（二进制演示文稿，未抽文本） | 低 |
| 6 | doc\QuietStart.docx | 205813 | .docx | QuietStart 方法的原理、实现代码、正负面影响算例 | 中 |
| 7 | doc\Radiation Hydrodynamics.xmind | 456983 | .xmind | 辐射流体力学思维导图（ZIP 容器，未展开） | 低 |
| 8 | doc\Restart.doc | 61952 | .doc(旧) | 重启动功能说明（OLE2，未成功提取） | 中 |
| 9 | doc\SNOP.MANUAL | 6604 | .txt(无扩展) | **SNOP 程序完整 namelist 输入规范**（NT/NR/NG/NP/Z/RHO/T/IGROUP/EQ/IDEG/NPLA/NROSS/NEPS/NZ 等） | **高** |
| 10 | doc\Structure_of_ASCII_data_files.txt | 82 | .txt | ASCII 数据文件结构小样（序号 组 行 列 值），非说明文字 | 低 |
| 11 | doc\gnuplot.pdf | 1412263 | .pdf | gnuplot 手册 | 低(绘图) |
| 12 | doc\muParser.txt | 4073 | .txt | muParser 数学表达式解析器函数/运算符表（公式字段解析用） | 中 |
| 13 | doc\反弹冲击波的撞击壳的时刻.docx | 133017 | .docx | 冲击波反弹撞击壳时刻的提取方法（MaxPressure 判据 + Matlab 代码） | 低 |
| 14 | doc\多群辐射源(FDS).docx | 22847 | .docx | 多群辐射源(Frequency Dependent Source) 输入文件格式（能谱+辐射流时间点两文件格式） | 中 |

### A.2 `doc\` 子目录

| # | 相对路径 | 大小(B) | 扩展名 | 文档性质 | 格式价值 |
|---|----------|---------|--------|----------|----------|
| 15 | doc\Conservation | — | 目录 | **空目录** | — |
| 16 | doc\FEOS\Info.txt | 2475 | .txt | FEOS_16.7 / SHOWEOS_16.7 版本/作者/许可/文件清单 | 中 |
| 17 | doc\FEOS\License.txt | 28360 | .txt | GPLv3 许可 | 低 |
| 18 | doc\FEOS\FEOS-Package-Documentation2012.pdf | 978594 | .pdf | FEOS 包官方文档 2012 | 高(外部) |
| 19 | doc\FEOS\FEOS-Package-Documentation2016.pdf | 611826 | .pdf | FEOS 包官方文档 2016 | 高(外部) |
| 20 | doc\FEOS\MPQeos-JWGU-Documentation.pdf | 405553 | .pdf | MPQeos (JWGU) 文档 | 高(外部) |
| 21 | doc\FEOS\Multi1D++ EOS and Opacity - FEOS程序说明.pdf | 2590125 | .pdf | **FEOS 在 Multi1D++ 中的 EOS/不透明度用法说明** | **高(外部)** |
| 22 | doc\FEOS\2011(Chernogolovka)...SiO2 FOILS.pdf | 660773 | .pdf | 会议论文（SiO2 亚稳态寿命） | 低 |
| 23 | doc\gnuplot_files_for_plot\* | 多种 | .dat/.dem/.gplt | gnuplot 绘图脚本与示例数据（whale.dat、simple7.* 等） | 低 |
| 24 | doc\multi1d7.6\README | 5619 | 无扩展 | MULTI/multi1d 历史沿革（MULTI→MULTI6→7.3/7.4/7.6 物理与界面演进） | 中 |
| 25 | doc\multi1d7.6\manual | 13797 | 无扩展 | **multi1d-7.6 完整使用手册**：FT12 输入各 Section(&CONTROL/&LAYERS/&PROFILE/&RBOUND/&RSOURCE/&PULSE/&IONBEAM) + fort.10 二进制输出记录结构 | **高** |
| 26 | doc\multi1d7.6\examples | 11588 | 无扩展 | 输入算例样例 | 中 |
| 27 | doc\multi1d7.6\history | 3874 | 无扩展 | 版本历史 | 低 |
| 28 | doc\References\1988CPC49(R.Ramis)_MULTI...pdf | 2757057 | .pdf | MULTI 原始论文 (CPC 49, 1988) | 高(外部) |
| 29 | doc\References\2009CPC180.977(Ramis)_MULTI2D...pdf | 1201526 | .pdf | MULTI2D 论文 | 高(外部) |
| 30 | doc\References\2012CPC183.637(Ramis)_MULTI-fs...pdf | 1031401 | .pdf | MULTI-fs 论文 | 高(外部) |
| 31 | doc\References\2013物理学报(宋天明)_三维柱腔...pdf | 624902 | .pdf | 中文参考文献 | 中(外部) |
| 32 | doc\References\2016CPC(Ramis)_MULTI-IFE...pdf | 1749702 | .pdf | MULTI-IFE 论文 | 高(外部) |
| 33 | doc\References\2017JCP330.173(Ramis)_1D Lagrangian...pdf | 1332448 | .pdf | 1D 拉氏隐式流体算法论文 | 高(外部) |
| 34 | doc\solution of unsymmetry\关于不对称.txt | 1631 | .txt | CH-Al-CH 不对称问题的数值起源与修复分析（XC/X/V/TR 变量） | 低 |
| 35 | doc\solution of unsymmetry\2011-04-14T16-24-32_before.log | 24653 | .log | 修复前运行日志 | 低 |
| 36 | doc\solution of unsymmetry\2011-04-14T16-24-49_after.log | 26823 | .log | 修复后运行日志 | 低 |
| 37 | doc\solution of unsymmetry\unsymmetry.xls | 30720 | .xls(旧) | 不对称性数据表 | 低 |

### A.3 `matter++\` 根目录

| # | 相对路径 | 大小(B) | 扩展名 | 文档性质 | 格式价值 |
|---|----------|---------|--------|----------|----------|
| 38 | matter++\Readme.txt | 530 | .txt | **最高优先级**: material.base 修改规则 + 数据文件格式自动识别规则 | **极高** |
| 39 | matter++\Albedo.xml | 1192 | .xml | 反照率幂律表（Be/Au/Al/W/Pb/U，Type=0/1/2 公式） | 中 |
| 40 | matter++\ScalingLaws.dat | 3937 | .dat | 自由程标度律脚本（H/Au/Be 等，含 Zeldovich-Raizer、WorkOp-III 公式） | 中 |
| 41 | matter++\density.dat | 4993 | .dat | NIST 元素常数表（Z/A、平均激发能 I、密度） | 中 |
| 42 | matter++\idata.dat | 4482 | .dat | XOP/inpro 元素数据（Z、符号、A、density） | 中 |
| 43 | matter++\Reflectivity.dat | 284 | .dat | 室温反射率（求碰撞频率 ks 用） | 中 |
| 44 | matter++\material.list | 0 | — | **空文件** | — |
| 45 | matter++\AtomicWeightTable.txt | 21590 | .txt | 原子量对照表 | 中 |
| 46 | matter++\BulkModulus.xlsx | 11562 | .xlsx | 弹性模量与力学性能表（CRC Handbook 84th, Table 11） | 中 |
| 47 | matter++\DatabaseIndex.xml | 15734 | .xml | 数据库索引 | 中 |

### A.4 `matter++\` 子目录 — 格式说明类文档

| # | 相对路径 | 大小(B) | 扩展名 | 文档性质 | 格式价值 |
|---|----------|---------|--------|----------|----------|
| 48 | matter++\ATOMIC\Atomic(LEDCOP)不透明度格式说明.docx | 33218 | .docx | **核心**: LANL ATOMIC/LEDCOP(TOPS) 不透明度格式 + 单位 + u-grid + TOPS 帮助/FAQ | **极高** |
| 49 | matter++\ATOMIC\#LEDCOP | 29 | 无扩展 | LEDCOP 标记文件 | 低 |
| 50 | matter++\hyades\Hyades 数据格式说明.doc | 64000 | .doc(旧) | **核心**: Hyades 数据格式（附录 I/III/VI + EOS 编号表 + 不透明度编号表 + Inversion；正文已成功抽取） | **极高** |
| 51 | matter++\hyades\EOS.list | 4790 | .list | Hyades EOS 库编号表（EOS No./材料/Zbar/Abar/Rho0） | 高 |
| 52 | matter++\hyades\Opacity.list | 1774 | .list | Hyades 不透明度库编号表 | 高 |
| 53 | matter++\hyades\### Data from hyades%Data directory.txt | 188 | .txt | Hyades Data 目录说明（coldopac/ionpot/Opacity/qeos/sesame） | 中 |
| 54 | matter++\hyades\tmp.dat | 181 | .dat | 冷不透明度温度-自由程小样（逗号分隔） | 低 |
| 55 | matter++\PROPACEOS\Readme.txt | 120 | .txt | PROPACEOS 格式受版权保护、无公开格式说明的声明 | 中 |
| 56 | matter++\Thermos\Readme.txt | 576 | .txt | Thermos 不透明度生成工具说明 + 无 EOS 元素清单 + _Z.dat/_Zeff.dat 单位约定 | 高 |
| 57 | matter++\HeatCapacity\Readme.txt | 91 | .txt | 电子-声子耦合与热容文献指引 | 中 |
| 58 | matter++\RadiativeCoolingRates\readme.txt | 429 | .txt | 辐射冷却率数据来源（Post 1977 / Coppola 2011） | 中 |
| 59 | matter++\mat_Ti\readme.txt | 133 | .txt | Ti 的 SNOP 数据来源（Zhang Jiyan / Song Tianming） | 中 |
| 60 | matter++\mat_Ba\Readme.txt | 403 | .txt | Ba 不透明度幂律拟合说明 + 有效范围 | 中 |
| 61 | matter++\mat_Ge\Readme.txt | 939 | .txt | Ge 不透明度幂律拟合说明（2002FED）+ 有效范围 | 中 |
| 62 | matter++\mat_CELIA\Readme.txt | 92 | .txt | C/D Zeff 新旧文件（eV→keV）替换说明 | 中 |
| 63 | matter++\mat_Al-1.0\README | 617 | 无扩展 | Al 表说明（理想气体、幂律不透明度、来源） | 高 |
| 64 | matter++\mat_Al-1.0\MODINFO / FILELIST / LOCK | 138/33/29 | 无扩展 | 模块元信息（m94version/cdate/author/info） | 中 |
| 65 | matter++\Ta2O5\Ta2O5_mop.readme | 343 | .readme | Ta2O5 不透明度/材料条目说明（Li Liling 2022） | 中 |
| 66 | matter++\mat_Au\Au_Rosseland_2003POPHammerRosen.readme | 90 | .readme | Au Rosseland 幂律参数 | 中 |
| 67 | matter++\mat_Sn\Sn_Planck_1987JQSRT.readme | 94 | .readme | Sn Planck 幂律参数 | 中 |
| 68 | matter++\CH\material.user | 620 | .user | CH/CHSi 材料条目（SNOP 不透明度+SESAME EOS） | 中 |
| 69 | matter++\Ta2O5\material.user | 340 | .user | Ta2O5 材料条目 | 中 |
| 70 | matter++\mat_Vacuum\Vacuum_Opacity.dat | 186 | .dat | 真空不透明度占位表 | 中 |
| 71 | matter++\Crystal\CrystalData.dat | 588 | .dat | 晶体衍射面数据 | 低 |
| 72 | matter++\Crystal\LatticeSpacing.dat | 509 | .dat | 晶格间距/布拉格角 | 低 |
| 73 | matter++\Crystal\names.txt | 86 | .txt | 晶体名称全称 | 低 |
| 74 | matter++\mat_Others\CH10Water.info | 27 | .info | 数据作者 | 低 |
| 75 | matter++\SNOP\### Generated by SNOP | 0 | 无扩展 | **空文件**（SNOP 输出占位） | — |

### A.5 `matter++\` 空目录（无任何内容）

`matter++\ANEOS`、`matter++\Diamond`、`matter++\Isotopes`、`matter++\Reactivity`、`matter++\others`、`matter++\PeriodicTable` 均为空目录；`matter++\Thermos\___No EOS\_mat_Mn 数据有误` 亦为空。`matter++\Thermos\___No EOS` 内仅有占位文件 `No EOS data, but Opacity in OpacityThermos.txt`。

### A.6 非文档型内容概览（供格式文档引用）

以下目录不含「格式说明文档」，但含大量数据样本，可在 B/C 节作为格式实例引用：`ATOMIC`(Al/C/Fe/.../SiO2 的 NoFree / AvSqFree / GrayOpacity_PLANCK / GrayOpacity_ROSSELAND / MultiGroupOpacity_PLANCK / MultiGroupOpacity_ROSSELAND / *.txt)、`Ionmix`(.cn4/.cnr)、`hyades`(Opacity/qeos/sesame)、`CH`、`ColdOpacity`(69 个 *.coldopacity + default.ini + .case)、`FEOS`(FEOS_Material-DB.dat / FEOS_TF-Table_1197.dat)、`PowerLaws`、`Thermos`(mat_*/\*.ini + \*_Planck/Rosseland/Z/Zeff.dat)、`SNOP`、`XrayMassCoef`、各 `mat_*`（.301/.304/.305/.feos/.cst/.PAR/.data.txt/.mexport/.isobaric.dat/.critical.dat）。

---

## B. 逐文档格式规范详解（核心章节）

### B.1 `matter++\Readme.txt`（530 B，全文，最权威格式识别规则）

```
material.base的修改规则
为同一material.base的修改，简单指定规则如下：
Ramis等公布的材料，MID编号在100之前，之后用户添加的材料在10000之后。

[Thermos]中没有EOS的
Br

添加参数时请注意：
文件名命名需要有如下的规则(不同格式有不同的单位转换)：
  如果文件名和路径中有"hyades"，程序识别为hyades程序的文件
  如果文件名和路径中有".feos"，程序识别为FEOS程序文件，按照一行4个15字符的数字读入
  如果文件名和路径中有".301"或".304"或".305"，程序识别为MPQeos生成的每行4x16个字符
  其他按照默认的SESAME数据库格式，每行4x15个字符。
```

**要点（写文档必引）**：格式分派完全依赖文件名/路径关键字，优先级依上述顺序；4 种格式的每行字符宽度分别为 4×15(hyades/feos/SESAME)、4×16(.301/.304/.305)。

### B.2 `doc\MULTI使用的SESAME数据文件格式.docx`（98 05 字，核心）

**（1）material.base 材料定义规则**（以 Au 为例）
```
MATERIAL MID9                      材料名称(首行)
REM Gold modelled by tabulated physical data
REM It is not sure...              REM 注释
   A 196.97                        原子质量
   Z 79                            有效离子数
   EOS        mat_Au-1.0   AU_eos   EOS 表(实为 Inverted EOS, P(rho,e) 与 T(rho,e))
   PLANCK     mat_Au-1.0   AU_op03p 表格 Planck 不透明度
   ROSSELAND  mat_Au-1.0   AU_op03r 表格 Rosseland 不透明度
   NONLTE     mat_Au-1.0   AU_op03e 表格 Non-LTE 因子(可选)
   ZEFF       mat_Au-1.0   AU_op03z 表格有效离子数(可选)
```
物质参数数据库在模块 `[matter-2.1]`（与 matter-1.0 相同结构）：`material.base` + 若干数据表文件夹。数据库含 EOS、不透明度、Non-LTE factors、effective ion number 四类表。

**（2）两类坐标系**：EOS 用 Inverted EOS（线性/直角坐标）；不透明度、NLTE、Zeff 用 log 坐标系。程序内部单位 cgs+eV，数据库单位不同，导入后转换。

**（3）EOS 数据格式（Inverted EOS，线性坐标，4 列多行）**
```
  .20020000E+04  .0             .20000000E+01  .20000000E+01
  .0             .10000000E+01  .0             .10000000E+01
  .0             .0             .0             .0
  .0             .21680000E+00  .0             .0
  .24654354E+05  .24654354E+05
```
字段语义：
- 行1: `MID材料编号  正常密度(不使用)  nr:密度个数  ne:能量个数`
- `(rho_min 密度列表 rho_max) (de_min 能量列表 de_max)`
- `(e0[0] 冷能量 e0[nr-1]) (P[0] 压强数据 ... P[ne*nr-1]) (T[0] 温度数据 ... T[ne*nr-1])`
- 参数个数 = `4 + 2*nr + ne + 2*nr*ne`
- 单位(cgs): `r[nr]`=g/cc；`de[ne]`=Mbar·cm³/g(与冷能量之差)；`e0[nr]`=冷能量 Mbar·cm³/g；`P[ne*nr]`=Mbar，`P[(0~nr-1)+nr*i]` 对应密度 r[0..nr-1]、能量 de[i]+e0[0..nr-1]；`T[ne*nr]`=Kelvin。
- 电子表格(ieeos)由总 EOS(ieos) 与原子量 A 换算（见 eoselectron 程序）；不使用离子表格。

**（4）Inverted EOS 转换**：E(R,T)→P(R,E),T(R,E)，先由 E(R,T) 反查 T(R,E)，再 P(R,E)=P(R,T(R,E))，两次插值。

**（5）MPQeos/SESAME 单位与 .301 格式**
- SESAME 库单位: 压强 GPa、能量 MJ/kg、密度 g/cc、温度 K
- MULTI2D 内部调用 EOS 单位: 压强 Mbar、能量 Mbar·cm³/g
- 换算: `1 GPa = 1e-2 Mbar`；`1 MJ/kg = 1e-2 Mbar·cm³/g`
- SESAME 301 数据格式 = 四列多行，但 MPQeos 内容为:
  ```
  Id(1111)  Density(g/cc)  NR  NT
  R[1-NR]  T[1-NT](K)  P[1-NRxNT](GPa)  E[1-NRxNT](MJ/kg)
  Z[1-NRxNT]
  ```
- Multi1D++ 自动识别后缀 301/304/305 并做单位转换。（注: 文档提到结果中压强/能量/Z 出现负值，原因待查。）

**（6）不透明度数据格式（logloglog 全对数，4 列多行）**
```
  .24010000E+04 0.40000000E+01  .20000000E+01  .20000000E+01
  .0             .10000000E+01  .0             .10000000E+01
  .52218000E+01  .52218000E+01  .42218000E+01  .42218000E+01
```
字段语义: 行1 `MID材料编号  密度(不使用)或数据类型  nr:密度个数  ne:温度个数`；行2 `Log(Rho_min) log(Rho_max) log(T_min) log(T_max)`；行3 起为 `Z(R_min,T_min) Z(R_max,T_min) Z(R_min,T_max) Z(R_max,T_max)`。
- 单位: Z=cm²/g、温度 T=eV、密度=g/cc
- 标度公式 `L = c * T^a * rho^b` 对应 `Z = log(K) = -log(c) - a*log(T) - (b+1)*log(rho)`；示例 6.0e-06*T^1.0/rho^1.0 → Z(0)=6-log(6)=5.2218, Z(1)=5-log(6)=4.2218。
- **数据类型标识**（第一行第二列，Multifs 判读）: `PLANCK 1`=0.7e1、`ROSSELAND 1`=0.4e1、`EPS 1`=0.6e1；多群版为 `PLANCK M`/`ROSSELAND M`/`EPS M`。MULTI7.6+ 仅多群需要此标识。
- **多群数据结构** `sesame_tab`:
  ```
  27004003  ROSSELAND M  nr密度数(>=2) nt温度数(>=2)
  区间下限频率 区间上限频率
  r[nr]: log(密度 g/cc) ; t[nt]: log(温度 eV) ; z[nr*nt]: 表格数据(log, cm2/g)
  (z[(0~nr-1)+nr*i] 为温度 t[i] 时的值)
  ```
- MID9 例：频率范围 10–5000 eV，非等间距（建议用 Multi1D 程序插值）；密度 10^-6–10^2 g/cc（指数等间距）；温度 0–10^5 eV。
- `PLANCK 1` 或频率上下限为 0 → 数据适用于所有群。

**（7）Zeff 格式**：温度/密度对数坐标，Zeff 亦对数；**温度单位 keV**（与不透明度用 eV 不同），密度 g/cm³。
- 重要历史注记(20160109 况龙钰)：SNOP 等输出的 SESAME 数据温度一直是 keV，旧 Multi 输入按 eV 导致电离度偏高；程序此日起统一按 keV，Thermos 中 `X_Z.dat`(eV) 重构为 `X_Zeff.dat`(keV)，material.base 已批量替换。

**（8）NLTE 格式**：温度/密度对数坐标，NLTE 亦对数坐标，可为多群。

### B.3 `matter++\ATOMIC\Atomic(LEDCOP)不透明度格式说明.docx`（22871 字，核心）

网站导出的 LEDCOP 不透明度格式说明，分两条线：

**（1）SESAME 格式**：与 MULTI 默认格式不同，较难解析（文档略）。

**（2）LEDCOP 格式**（文件名示例 Al.txt）：
```
Number of T =  69  Number of rho =  50  Number of materials =   2
 TOPS results for  LiH             on Sep  6, 2016
 Opacities in cm**2/gm, T in keV, density in gm/cc
Normalized composition for requested elements
 No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
   5.0000E-01   8.7320E-01      3         Li        4922
   5.0000E-01   1.2680E-01      1         H         4525
Temperature grid used the following  69 points
  5.0000E-04 6.0000E-04 ... 1.0000E+01
Density grid used the following  50 points
  1.0000E-03 1.2068E-03 ... 1.0000E+01
Rosseland and Planck opacities and free electrons
 Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  5.0000E-04
  1.0000E-03  8.8707E+04  2.1555E+06  1.2280E-02  1.2280E-02
  ...
Multigroup opacities
  Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.0000E-03
  1.0000E-03  1.9954E+04  1.9957E+04
  ...
```
- 单位: 不透明度 cm²/g，T=keV，密度=g/cc。
- 三部分: 单群 gray opacity（Ross/Planck/No.Free/Av Sq Free）、多群 multigroup（Energy/Ross mg/Planck mg）、频率相关 spectrum（对有限温密点，3000 或 3900 点）。
- `No. Free`=每离子平均自由电子数；`Av Sq Free`=自由电子数平方的离子级平均。
- **温度网格**（ATOMIC 2015, 69 点；LEDCOP 2000, 50 点）与密度网格均为固定不能插值（温度）或可插值（密度）。
- 群不透明度低于等离子体截止频率者设为 1e10。
- **u-grid 定义**: `u = hν / kT`，14900 点网格: 0–12.5(步0.00125,9600点)、12.5–20(步0.005,1600)、20–30(步0.01,1000)、30–100(步0.1,700)、100–1000(步1,900)、1000–10000(步10,900)、10000–30000(步100,200)。
- TOPS 帮助/FAQ（Q1–Q13）含 SESAME 与 Web 版差异、LTE 下限 1e-6~1e-7 g/cc 等。
- 出处: LANL T-1 Opacities；参考 LA-UR-97-1038(LEDCOP)、LA-10454(TOPS)、LA-6760-M 等。
- Multi1D++ 转换: 在 Opacity 界面选文件 → Export。

### B.4 `doc\SNOP.MANUAL`（6604 B，全读）

SNOP (Eidmann, Laser and Particle Beams 12(2), 223-244, 1994) 生成多群不透明度的 Fortran namelist(`&daten`)输入规范。输入 `SNOP.INPUT`，输出 `SNOP.INHALT`(参数清单) 与 `SNOP.TAB`(MULTI 格式表)。
- 维度: `NT` 温度数, `NR` 密度数, `NG` 群数, `NP` 光子能量数（上限 NTM/NRM/NGM/NPM 在 v.risc 中）
- 范围: `Z` 核电荷, `RHO1/RHO2` 最低/最高密度(g/cm³), `T1/T2` 最低/最高温度(keV), `X1/X2` 最低/最高光子能量(keV)
- `IGROUP`: 0=用户给群边界 FG，1=线性，2=二次，3=对数（用 F0/F1，eV），4=标准 20 群(1eV–5keV)，5=灰近似 2 群
- `EQ`: 0.0=LTE, 1.0=Non-LTE；`IDEG` Thomas-Fermi 电离度开关；`LINEPRO` 线型(0 Lorentz/1 Gauss)；`DREK` 双电子复合；`XGRIEM`；`AV`；`FACT` 线增宽系数；`NSIGMA` 屏蔽常数(Mayer/More)
- **SESAME 表号**: `NPLA`(xxxx3nnn Planck群平均)、`NROSS`(xxx4nnn Rosseland)、`NEPS`(xxx5nnn 发射率群平均，LTE 时不需要)、`NZ`(xxx2nnn 平均电离度)。材料 xxxx: D=5263, Be=2020, B=7081, C=7560, Al=3712, Fe=2140, Au=2700。
- 附完整 `&daten` 示例。

### B.5 `matter++\hyades\Hyades 数据格式说明.doc`（正文成功抽取，核心）

来源 Hyades User's Manual / Physics Manual（CAS, Inc.）+ 1994JQSRT51(J.Larsen)。程序按路径/文件名含 "hyades" 识别。

**（1）Hyades 数据目录结构**（`matter++\hyades`）
| 文件/夹 | 含义 |
|---------|------|
| Ionpot.dat | 离化势（用于模拟产生与再启动 phase） |
| Coldopac.dat | 室温冷不透明度（多群在线计算低温不可靠时使用设定室温值） |
| Eoslib.lbf | EOS 数据库（二进制库） |
| Opaclib.lbf | 不透明度数据库 |
| Tfdat.lbf | QEOS 的 Thomas-Fermi 数据库（spherical-cell 热稠密等离子体 TF 理论算电子 EOS） |
| Opacity/ | 灰不透明度数据库 |
| qeos/ | LLNL-QEOS |
| sesame/ | LANL SESAME |

**（2）附录 I — HYADES EOS 库编号**
- 单流体 EOS 压/能表号 `1<num<998`；Rosseland/Planck 平均不透明度表号 `1000<num<2000`；两温 EOS `2000<num<3000`(电子)、`3000<num<4000`(离子)，两者须同时指定。
- 表列 `EOS No. / Material / Zbar / Abar / Rho0`；`*`=首选表，`#`=有双温材料。示例: 11 D+T(1.000/2.515/0.2205)、41 Al(13.00/26.982/2.7568)、341 Diamond(6.000/12.011/3.51) 等（完整表见 docx 抽取）。
- 不透明度表号表 (`Opacity No. / Material / Zbar / Abar`): 1022 Quartz(10.00/20.028)、1461 Europium(63.00/151.96)、1481 Calcium、1491 Silver；`*`=仅 Rosseland，Planck 平均位置填 0。

**（3）附录 III — EOS ASCII 材料文件格式（Hyades）**
- 第 1 行: 常用材料名 + 数据来源历史信息
- 第 2 行: HYADES EOS 号、ZBAR、ABAR、正常密度 DEN、数据数组长度；格式 `1x,i5,4x,1p3e15.8,3x,i5`
- 第 3 行起: `NR`(密度点数)、`NT`(温度点数)、密度数组(NR)、温度数组(NT)、压力矩阵(NR*NT)、能量矩阵(NR*NT)；格式 `1p5e15.8`
- **单位与 SESAME 不同**: 密度 g/cm³、温度 keV、压强 dyne/cm²、比内能 erg/g
- 实例 `eos_2051.dat` 头: `GOLD  LANL SESAME #2700-304 DATED: 81678 101582` / `2051 7.90e1 1.96967e2 1.93e1 4772`
- QEOS 文件 `qeos_115.dat`: `COPPER LLNL-QEOS Dated: 082802` / `NR, NT, RHO[], T[], P[](平均Rosseland), E[](平均Planck)`
- 附录 II（二进制库）Multi1D++ **不支持**。
- 数组长度 = `2 + NR + NT + 2*NR*NT`。

**（4）附录 VI — 外部不透明度表文件格式**（用户可提供多群表，自由格式 80 列，可续行）
| Block | 内容 |
|-------|------|
| 1 | 字符串表头 |
| 2 | 温度个数、密度个数 |
| 3 | 温度数组(keV)，最大 200 |
| 4 | 密度数组(g/cm³)，最大 200 |
| 5 | 温度#1 的光子群数 NGPS1，最大 500 |
| 6 | 温度#1 群边界数组(NGPS1+1) |
| 7 | 温度#1/密度#1 不透明度数组(cm²/g) |
| 8 | 温度#1/密度#2 ... 直至所有密度 |
| Nr+7... | 温度#2 起重复 |

**（5）Multi1D++ 对 Hyades 数据的使用**
- 需 Invert: `E(R,T)→P(R,E), T(R,E)`；先由 E(R,T) 找 T(R,E)，再 P(R,E)=P(R,T(R,E))。
- GUI4Multi1D 的 EOS/Opacity Viewer 可查看 InvertedEOS 或原始 Hyades 数据。
- 标注: Preferred tables(*)、Two-temperature(#)、Rosseland-only。

### B.6 `doc\GUI,IO相关.docx`（11174 字）

- `default.ini`: `[Config] Functioning=4, MaxNumOfGrids=1000`；`[RecentFiles] File[0]=...`
- `config.ini`: `[Programs] Program[i].Executable=` + `.Type=`（**0=辐射流体力学；1=不透明度；2=状态方程**）; Multi1D++.exe(0), multi7.6.exe(0), Snop++.exe(1), FEOS.exe(2) 等；`[Tools] GNUPlot/Notepad` 路径。
- 完整输出文件变量定义: `*.center.dat`(Time/CMC/XC/R/Te/Pe/Zi/D/DENE/Ee/Ei/Ti/Pt/Pi/TR_cell/kei/ke/ki/coulog_ei/pviscous/len_e_stop 等)、`*.interface.dat`(CMI/X/V/S+/S-/S/Tr/Vsound/Albedo/FluxLimited/FluxNonlocal)、`*.group.dat`(FREI_left/center/right, I-Left, I-Right)、`*.scalars.dat`(TIME/ISTEP/ENLAS/ENQUE/ENIE/ENII/ENKI/ENRAD/ENRL1-4/ENRG1-4/EALFA/ENAL/ENAG/EYIELD/Nproton/POWRAD/MaxRho@/rhoR/rhoRHS/rhoRN 等)。

### B.7 `doc\multi1d7.6\manual`（13797 B）

FT12 输入各 Section: `&CONTROL`(FLAG/NSPLIT/TEXIT/NEXIT/DTN/DTO/VARNOM/WALLLEFT/WALLRIGHT/FLF)、`&LAYERS`(IGEO/NC/MID/THICK/RHO/TE/TI/ZONPAR)、`&PROFILE`(tabulated initial profile, 魔数 "MSanchez")、`&RBOUND`、`&RSOURCE`、`&PULSE`、`&IONBEAM`。
输出 `fort.10` 二进制: 记录 1=字数，2=变量名(8字符)，3=double 值……；给出 record 3 与 6+ 的全部存储量(CMC/NC/CMI/NI/FREC/FREI + TIME/R/T/P/ZI/XC/TR/S+/S-/I-Left/I-Right 等)及单位。

### B.8 `doc\multi1d7.6\README`（5619 B）

MULTI→MULTI6→multi1d-7.3/7.4/7.6 演进史。关键: 1988 MULTI 用单温表 EOS(通常来自 SESAME) + 多群不透明度(通常来自 SNOP); 7.4 引入 material.base 索引文件管理表; 7.6 拆分出 matter-1.0 材料模块。

### B.9 `doc\FEOS\Info.txt`

FEOS_16.7 / SHOWEOS_16.7 (Dr. Steffen Faik, GPLv3)。MPQEOS 作者 Andreas Kemp(后由 Krenz/Ramis/Vinci 修改)。FEOS 由 MPQEOS 发展：加同质混合物计算、软球冷曲线、Maxwell 构造新数值、库化(C/C++/Fortran 接口)。文件清单: `Code/*.C/*.H/libfeos.h/Makefile`、`Documents/*.pdf`、`EOS-Data/*.par/*.dat`。文档指向 `FEOS-Package-Documentation.pdf`。

### B.10 `doc\QuietStart.docx`

QuietStart 原理(BUCKY1D/Hyades 同法: 离子温度超阈值前压力差加速度强制为 0)、Multi1D++ 实现(`fractionc`/`dvdt` 代码片段, 熔点 tm~沸点 tb 线性插值 fQS)、文献 2016PPCF58(J.Velechovsky), 及负面影响(BUCKY/CwuCC 钻石层算例)。默认 Hyades 关闭输运; tecold 默认 10eV。

### B.11 `doc\多群辐射源(FDS).docx`

三种输入方式: 能谱+辐射流时间点两文件(推荐)、能谱+光子能量+辐射流三文件(新版本废除)、直接取 `*.group.dat` 的 I-Left/I-Right。自定义格式: 时间点文件(单位秒，仅第一列有效)、能谱文件(第一列光子能量 eV，其后各列对应时间点强度 W/m²/sr/eV，列数=时间点数+1)。

### B.12 `doc\反弹冲击波的撞击壳的时刻.docx`

以 MaxPressureAt 为基准求反弹冲击波与玻璃壳撞击时刻(约 0.64 ns / 6.34e-10 s)的方法与 Matlab `calTimeReshockCollision` 代码；比较 PosInterface/PosFallLine/MaxDPressure@ 轨迹。

### B.13 `doc\muParser.txt`

muParser 支持的 26 函数(sin/cos/tan/log/ln/exp/sqrt/if/min/max/sum/avg 等)与 15 运算符(= and or xor <= >= != == > < + - * / ^)及优先级——用于 formula.ini/ScalingLaws 等公式字段解析。

### B.14 `doc\solution of unsymmetry\关于不对称.txt`

CH-Al-CH 不对称问题: 不对称变量为 XC/X/V/TR；速度误差 ~1e-7(前 5 网格最大)、密度误差 ~1e-12~1e-15；根因在 `solveImplicitly` 中 `state->x` 递推(i=0 用 dx=(v_new+v_old)/2*dt，其余用 dx=m/rho)及 `dvelocity[n]` 边界项不对称。

### B.15 `matter++\Thermos\Readme.txt`

Thermos 不透明度由 opadata.exe 生成(基于 Thermos)；多群由宋天明 OpaDataRunner 生成。无 EOS(默认理想气体)元素: Br/Dy/Gd/Sm/B/Co/F/H/K/N/Na/P/Pd/S/Sc；Mn 数据错误无法算 Opacity。**离化度文件单位**: `*_Z.dat`=eV(作废)、`*_Zeff.dat`=keV(新版使用)。

### B.16 `matter++\PROPACEOS\Readme.txt`

PROPACEOS 文件格式受版权保护，无公开格式说明；FLASH 圈 opacplot2 有相关代码但许可问题未公开。

### B.17 其余小说明文件（要点）

- `mat_Al-1.0\README`: AL_IDEAL_GAS(Z=12,A=27,GAMMA=5/3)、AL_SIMPLE_PLANCK/Rosseland 幂律(Murakami/Meyer-ter-Vehn/Ramis 1990)、AL_eos 疑为 SESAME、Al.feos 由 FEOS 算。
- `mat_Ba\Readme.txt` / `mat_Ge\Readme.txt`: 不透明度幂律 `k=a*T^s*rho^r`(cm²/g) 或 `k=e^a*T^b*rho^c`，含有效温密范围与来源(Tsakiris&Eidmann 1987JQSRT / 2002FED)。
- `mat_Au\Au_Rosseland_2003POPHammerRosen.readme`、`mat_Sn\Sn_Planck_1987JQSRT.readme`: 幂律参数 c/a/b。
- `mat_CELIA\Readme.txt`: C/D 的 Zeff 新旧替换(eV→keV)。
- `RadiativeCoolingRates\readme.txt` + `RadiativeCoolingRatesArgon1998Fournier.dat`: 冷却率来源与拟合系数。
- `HeatCapacity\Readme.txt`: 电子-声子耦合/热容文献。

---

## C. 数据文件格式特征（按格式分类，含实测头部样本）

> 以下均来自代表性文件首几行采样（.workbuddy\tmp\dataheaders.txt 及直接采样）。

### C.1 默认 SESAME 格式（4×15 字符/行，.cst / .data.txt / .mexport / _eos / _ieos / _op03p/r/e/z / SNOP 输出 / AL_SIMPLE_PLANCK 等）
特征: 每行 4×15 字符、`E` 指数; 第一行含 MID + 参数; 第二行起数据矩阵。
实测:
- `mat_Au-1.0\AL_SIMPLE_PLANCK` (183 B): `.17010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01` / `.0 .10000000E+01 ...` / `.87447000E+01 .92447000E+01 .63447000E+01 .68447000E+01`
- `mat_Ti\SNOP_LTE.PLANCK`(207420 B): `27003000      PLANCK M        0.20000000E+02 0.20000000E+02` / `0.10000000E+01 0.10000000E+02` / 对数温度数组 → **多群 Sesame_tab 结构**（与 B.2(6) 完全一致，群边界 1–100 eV）
- `mat_Vacuum\Vacuum_Opacity.dat`: `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` / `0.0 0.1e1 0.0 0.1e1` / `-1.0e1 -1.1e1 ...`

### C.2 hyades EOS ASCII（`1x,i5,4x,1p3e15.8,3x,i5` 头 + `1p5e15.8` 数据）
实测 `hyades\sesame\eos_2051.dat`(73611 B):
```
GOLD        LANL SESAME #2700-304 DATED: 81678 101582
  2051     7.90000000E+01 1.96967000E+02 1.93000000E+01    4772
 1.01000000E+02 2.30000000E+01 0.00000000E+00 1.50781250E-01 ...
```
`hyades\Opacity\opc_1022.dat`(45258 B) 与 `hyades\qeos\qeos_115.dat`(366222 B) 同样头结构（后者 P=平均Rosseland, E=平均Planck）。`FEOS_3717.hyades`(1661976 B) 亦为 hyades 格式（第2行 EOS 号 3717）。

### C.3 FEOS `.feos`（4×15）
实测 `mat_Al-1.0\Al.feos`(3628968 B) 首行:
` 1.20600000e+01 1.92000000e+02 6.90000000e+01 1.00000000e+00 1.00000000e-04 ...`（含 nden/ntemp 等元数据，后续为密度/温度网格）

### C.4 MPQeos/SESAME `.301`/`.304`/`.305`（4×16）
实测 `mat_Al-1.0\FEOS\Al.feos.301`(620139 B):
```
 37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01
 0.00000000e+00 2.70000000e-06 5.81697366e-06 1.25322899e-05
 ...
```
首行第1字段 `37170301` = 材料号 3717 + 类型 0301；随后 Rho/RhoMax/Tmax；数据为密度、温度、P、E、Z 四列多行。`.304`/`.305` 结构同（304=电子?305=离子? 同尺寸 620139）。

### C.5 Ionmix `.cn4` / `.cnr`
实测 `Ionmix\al-imx-002.cn4`(552192 B) 头 4 行:
```
        21        21                 <- NT NR
 atomic #s of gases:         13     <- 原子序数
 relative fractions:   1.00E+00     <- 相对份额
           30                        <- 群数(NGPS)
```
随后为群边界、温度网格、不透明度矩阵。`.cn4`=4 参数(Ionmix cn4 变体)，`.cnr`=`al-imx-001.cnr` 类似，第4行含密度/温度范围与群数。`h-imx-1grp.cn4`(17 21, atomic#1, 1grp)。

### C.6 ATOMIC/LEDCOP `matter++\ATOMIC\` 系列
三种文件：
- `*.txt`(13.5 MB, 如 Al.txt/CH2.txt): TOPS 输出全文（多群 + 频率相关），头部见 B.3。
- `*.NoFree` / `*.AvSqFree`(55383 B): 前两行 ` 0.1234567E+000 1.0000000e+000 5.0000000e+001 6.9000000e+001` 后接对数网格。
- `*.GrayOpacity_PLANCK` / `*.GrayOpacity_ROSSELAND`(55383 B): ` 0.1234567E+000PLANCK 1        5.0000000e+001 6.9000000e+001` —— **第一行第二列即 B.2(6) 的数据类型标识**（与 MULTI Sesame_tab 对齐）。
- `*.MultiGroupOpacity_PLANCK` / `*.MultiGroupOpacity_ROSSELAND`(5486085 B): ` 0.1234567E+000PLANCK M        5.0000000e+001 6.9000000e+001` + 群边界行 ` 9.3827458e-001 1.0657861e+000`。

### C.7 Thermos
`Thermos\mat_Al\Al.ini`(795 B):
```
ElementName=Al
Temperature=4e-2,1.0000000E+00,...
Density=1.0000000E-06,...
Frequency=0.1,1.0,10.0,50.0,100.0,...,5000.0
```
对应 `Al_Planck.dat` / `Al_Rosseland.dat` / `Al_Z.dat`(eV) / `Al_Zeff.dat`(keV)。

### C.8 SNOP 输出
- `mat_Ti\Ti_LTE.INPUT` / `Ti_NLTE.INPUT`: `&daten NT=20 NR=20 NG=30 NP=6000 RHO1=1e-6 RHO2=100 T1=0.001 T2=100 X1=0.001 X2=10 IGROUP=0 ...`（与 SNOP.MANUAL 一致）
- `SNOP\opbe.inhalt`: `EINGANGSPARAMETER` 清单(Z/AW/FACAB/EQ/IDEG/LINEPRO/DREK/XGRIEM...)
- `SNOP_LTE.PLANCK/ROSS`、`C_20GSNOP.PLANCK/ROSS`、`SNOP.ZEFF`、`SNOP.EPS` 等为 SESAME 格式。

### C.9 ColdOpacity
`ColdOpacity\*.coldopacity`(69 元素, 9.8–16.4 KB): 冷(室温)不透明度表；`default.ini`(331 B) + 若干 `.case`/`.case.log`。`AlColdOpacity.opj`(6.87 MB) 为 Origin 工程。

### C.10 其他
- `mat_B\B.PAR`(6546 B): FEOS 参数文件(`Material-Number/Maxwell_Flag/SoftSphere_Flag/...`)，`%%` 注释，实测为 aluminum 段。
- `mat_B\B.critical.dat`: 临界点(Tc/Pc/Rhoc/Hc/Sc/Zc/沸点/等温线数)。
- `mat_B\B.isobaric.dat`: 等压膨胀数据(T[Rho]P[bar]Alpha H Cp)。
- `Ta2O5\Ta2O5.Rho-*.ist/.ise/.isc/.mnt`: FEOS 输出的等温/等熵/等密度表及其 gnuplot 版。
- `PowerLaws\opacity.xlsx`: 各元素 Planck/Rosseland `k=c*T^a*rho^b` 或 `k=e^a*T^b*r^c` 拟合系数表; `PowerLaws\Ta2O5_Kr.dat`: Ta2O5 Rosseland 不透明度 T-Kappa 表。
- `mat_B\B.data.txt`(1.68 MB): FEOS 计算后转 SESAME 的四列数据；`B.mexport`(1.85 MB) 为导出中间文件。
- `RadiativeCoolingRates\RadiativeCoolingRates.dat` / `RadiativeCoolingRatesArgon1998Fournier.dat`: 冷却率多项式拟合系数(Ar 按温区分段)。
- `Crystal\CrystalData.dat` / `LatticeSpacing.dat`: 晶体衍射面/晶格间距。
- `Albedo.xml`: 反照率幂律（Type 0/1/2）。

---

## D. 无法直接读取的文档及原因

| 文档 | 类型 | 原因 | 建议 |
|------|------|------|------|
| doc\Atomic(LEDCOP)说明.doc | OLE2 旧 .doc | 二进制复合文档，原始 UTF-16 流 byte-swap/位偏移导致乱码 | 用 antiword / libreoffice / MS Word 转换；**已有 docx 版** `ATOMIC\Atomic(LEDCOP)不透明度格式说明.docx` 可替代 |
| doc\Restart.doc | OLE2 旧 .doc | 同上，未能取得可读正文 | 外部转换 |
| doc\Multi1D++ and GUI4Multi1D简介.pptx | .pptx | 未抽文本（二进制演示文稿） | 用 python-pptx 或 LibreOffice |
| doc\Radiation Hydrodynamics.xmind | .xmind | ZIP 容器，未展开 content.json | 解包后可读 |
| doc\References\*.pdf (6 个) | .pdf | 未做 PDF 文本抽取 | 可用 pdftotext（含 MULTI 系列权威论文） |
| doc\FEOS\*.pdf (4 个) | .pdf | 未做 PDF 文本抽取 | 可用 pdftotext（FEOS/MPQeos 官方文档） |
| doc\gnuplot.pdf | .pdf | 绘图手册，与数据格式无关 | 忽略 |
| doc\solution of unsymmetry\unsymmetry.xls | 旧 .xls | 未做 BIFF 解析 | 建议转 xlsx |
| matter++\hyades\list.xls / 新建 Microsoft Excel Worksheet.xls | 旧 .xls | 未做 BIFF 解析 | 建议转 xlsx |

**成功突破的重要旧 .doc**：`matter++\hyades\Hyades 数据格式说明.doc`（64000 B, OLE2）—— 通过多编码原始 UTF-16 流扫描成功获得正文（见 B.5）。

---

## E. 对 8 万字中文文档「Multi EOS/不透明度数据格式」的素材评估

### E.1 最有价值的格式规范文档（按优先级）

1. **`matter++\Readme.txt`**（最高，530 B 全文）—— 格式自动识别总纲，必作开篇。
2. **`doc\MULTI使用的SESAME数据文件格式.docx`**（极高，9805 字）—— SESAME 数据全谱: material.base 定义语言、Inverted EOS 线性格式、不透明度 logloglog 格式、`sesame_tab` 多群结构、数据类型标识(PLANCK 1/M 等)、Zeff/NLTE、单位与换算、301 格式差异、温度单位 keV/eV 陷阱。**这是构建「SESAME 格式」章节的骨架**。
3. **`matter++\ATOMIC\Atomic(LEDCOP)不透明度格式说明.docx`**（极高，22871 字）—— ATOMIC/LEDCOP/TOPS 格式、u-grid、多群/频率相关、FAQ。**构建「LANL 原子不透明度格式」章节**。
4. **`matter++\hyades\Hyades 数据格式说明.doc`（正文已抽取）**（极高）—— Hyades 附录 I/III/VI、EOS 编号库、不透明度编号库、外部不透明度表格式、EOS Inversion。**构建「Hyades 格式」章节**。
5. **`doc\SNOP.MANUAL`**（高，6604 B 全读）—— SNOP 生成流程与 SESAME 表号命名规则(`xxx3nnn` 等)。**构建「SNOP 多群不透明度生成」章节**。
6. **`doc\multi1d7.6\manual`**（高）—— FT12 输入与 fort.10 二进制输出记录结构。**构建「输入/输出数据接口」章节**。
7. **`matter++\Thermos\Readme.txt`**（高）—— Thermos 格式与 _Z/_Zeff 单位约定（呼应 keV/eV 陷阱）。
8. **`doc\GUI,IO相关.docx`**（高）—— 全部输出文件变量定义表，可直接作为「输出量字典」。
9. **`matter++\PROPACEOS\Readme.txt`**（中）—— 说明该格式无公开文档，写作时需诚实标注。
10. **`doc\FEOS\Info.txt` + FEOS/Multi1D++ 说明 PDF**（中/高外部）—— FEOS 格式与 .feos/.301/.304/.305 的来源。

### E.2 可组合成「格式分类学」的主线

| 格式家族 | 识别关键字(Readme.txt) | 行宽 | 典型扩展名 | 说明文档位置 |
|----------|------------------------|------|-----------|--------------|
| SESAME 默认 | (无) | 4×15 | .cst/.data.txt/_eos/_ieos/.PLANCK/.ZEFF | B.2 |
| hyades | "hyades" 在路径/名 | 4×15 | eos_*.dat/opc_*.dat/qeos_*.dat/*.hug | B.5 |
| FEOS | ".feos" 在名 | 4×15 | *.feos/*.feos.par | B.9 + C.3 |
| MPQeos/SESAME301 | ".301"/".304"/".305" | 4×16 | *.301/*.304/*.305 | B.2(5) |
| SNOP | 输出 | 4×15(表) | SNOP.*/*.SNOP | B.4 |
| Ionmix | 目录 | 自由 | *.cn4/*.cnr | C.5 |
| ATOMIC/LEDCOP | 目录 | 自由 | *.txt/*.NoFree/*.MultiGroupOpacity_* | B.3 |
| Thermos | 目录 | .ini 键值 + .dat | *.ini | B.15 + C.7 |
| ColdOpacity | 目录 | 表 | *.coldopacity | C.9 |

### E.3 关键「坑点」清单（8 万字文档的高价值细节）

1. **温度单位 keV vs eV**：不透明度用 eV；Zeff/SNOP/Thermos 用 keV。历史 bug(20160109)导致电离度偏高；`X_Z.dat`(eV) 已作废 → `X_Zeff.dat`(keV)。（B.2(7), B.5, B.15）
2. **SESAME(DPK) vs MULTI 单位**：GPa/MJ/kg/K ↔ Mbar/Mbar·cm³/g；`1 GPa=1e-2 Mbar`。（B.2(5)）
3. **Hyades 单位与 SESAME 不同**：keV/dyne·cm⁻²/erg·g⁻¹。（B.5(3)）
4. **.301 四列多行 ≠ MULTI 所需内容**：MPQeos 虽 4 列但字段顺序不同，需转换，且曾出现负值。（B.2(5)）
5. **多群不透明度数据类型标识**第一行第二列（PLANCK 1/M, ROSSELAND 1/M, EPS 1/M）；频率上下限为 0 表示全群。（B.2(6)）
6. **log 坐标系**：EOS 线性，不透明度/NLTE/Zeff 对数。（B.2(2)）
7. **Inverted EOS** 必要性：E(R,T)→P(R,E),T(R,E)。（B.2(4), B.5(5)）
8. **LEDCOP 温度不可插值、密度可插值**；u-grid 14900 点；群不透明度切除频率设 1e10。（B.3）
9. **格式识别依赖文件名/路径关键字**，而非文件内容嗅探。（B.1）
10. **Hyades 两温表号区段** 1–998 / 1000–2000 / 2000–3000 / 3000–4000。（B.5(2)）

---

## 附：本次清查生成的中间产物（供后续写作用）

均位于 `.workbuddy\tmp\`：
- `enum_doc_matter.txt` — doc\ 与 matter++\ 全枚举（含大小）
- `textdocs.txt`（101617 B）— 40 个纯文本文档正文
- `doc_misc.txt`（98065 B）— doc\ 下纯文本（SNOP.MANUAL/manual/Info 等）
- `docx_extract.txt`（61998 B）— 7 个 docx 抽取正文
- `xlsx_extract.txt` — 3 个 xlsx 抽取
- `legacy_doc.txt` / `legacy_doc_full.txt` / `legacy_doc_be.txt` — 旧 .doc 尝试
- `hyades_doc.txt`（18302 B）— Hyades 格式说明成功抽取正文
- `dataheaders.txt`（73230 B）— 约 48 个代表性数据文件头部
