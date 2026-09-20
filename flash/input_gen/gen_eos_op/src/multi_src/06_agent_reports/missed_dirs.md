# 遗漏目录与材料族补查

> 补查对象：《MultiEOSOP格式说明.md》主文档**完全未提及**的两批内容
> （A）数据根 `src/Multi1D++Portable20241128/` 的一级目录；
> （B）`matter++/` 下含真实数据但文档未提及的材料族。
> 数据根：`src/Multi1D++Portable20241128/`。所有字节数为 `os.path.getsize` 实测值。
> 本文件 UTF-8 + LF。生成脚本：`.workbuddy/tmp/{_probe,_probe2,_dump,_tft,_cases,_mats,_mhead,_x,_tree}.py`

---

## 摘要表

| 目录 | 文件数 | 字节 | 性质 | 格式归属 | 文档应补章节 |
|---|---|---|---|---|---|
| `templates/` | 183 | 2,092,091 | 输出变量名→说明 对照表 + 配色表 + 空白输入卡骨架 | **无占位符**；非模板展开器 | 新增「§输出变量字典与配色表」 |
| `templates/data/` | 16 | 12,266 | 输出列名/单位字典（15 个 `.template` + 1 个错拼 `.templete`） | 纯文本「名 TAB 说明」 | 同上 |
| `templates/color/` | 166 | 1,947,000 | gnuplot 配色表（`.dat` 3328B 定长 + `.gif` 预览） | gnuplot `set palette` 体系 | 新增「§配色表格式」 |
| `tabelle/` | 3 | 567,699 | Thomas-Fermi / QEOS 预计算表 | **TFT 纯文本数值表**（NR=93 × NT=44） | 新增「§Thomas-Fermi 预计算表」 |
| `cases_1988CPC` | 7 | 20,435 | 算例（输入卡） | MULTI namelist `.case` | 新增「§算例组织」 |
| `cases_Experiments` | 2 | 9,054 | 算例 | `.case` | 同上 |
| `cases_HotElectrons` | 2 | 14,500 | 算例 | `.case` | 同上 |
| `cases_M1_78` | 4 | 10,187 | 算例 | `.case` | 同上 |
| `cases_RadiativeShock` | 3 | 26,216 | 算例 | `.case` + `.data` + 无后缀网格表 | 同上 |
| `cases_ZhangLu` | 36 | 431,061,444 | 算例 + 30 个大输出 `.dat` | `.case`/`.dat`/`.log` | 同上 |
| `cases_multi-ife` | 11 | 70,416 | MULTI-IFE 算例 | `.case` | 同上（对应 2016CPC Ramis） |
| `cases_multifs` | 15 | 53,455 | MULTI-fs 算例 | `.case` | 同上（对应 2012CPC Ramis） |
| `cases_simple` | 48 | 143,965 | 教学算例 | `.case` + `.data` | 同上 |
| `matlab/` | 197 | 14,622,042 | MATLAB 后处理脚本（含少量 `.dat`/`.10`/`.dat_multi`） | **非数据格式**（后处理代码） | 新增「§MATLAB 后处理接口」 |
| `Microsoft.VC90.CRT` | 4 | 1,449,996 | VC++ 运行时 DLL | **非数据格式** | 「§分发包说明」一句话 |
| `Microsoft.VC90.MFC` | 5 | 2,439,700 | MFC 运行时 DLL | **非数据格式** | 同上 |
| `matter++/mat_Bi`（等 19 族） | 见 §B | — | FEOS/EOS/不透明度材料库 | SESAME/FEOS/Rostock/IO 多族 | 各材料族小节 |
| `matter++/` 全树 | 1213 | 729,653,444 | 129 个子目录，含 60+ 空目录 | — | 新增「§材料库目录树」 |

---

## A. 数据根一级目录

### A1. `templates/`（183 文件，2,092,091 B）

#### 文件清单（分类统计）

| 子目录 | 文件数 | 扩展名分布 |
|---|---|---|
| `templates/`（根） | 2 | `definitions.txt`(7338), `template.case`(5870) |
| `templates/data/` | 16 | `.template` × 14, `.templete` × 1（**错拼**）, `readme.txt` × 1 |
| `templates/color/` | 165 | `.dat` × 130, `.gif` × 32, `.txt` × 2, `readme.txt` |

**结论：183 个文件中，只有 14 个真正以 `.template` 结尾，且它们不是「模板」字面意义上的占位符文件。**

`templates/data/` 完整清单（全部为 100% 可打印 ASCII 文本）：

```
  backlighter.template      286
  center.template          1322
  fuel_center.template     1512
  fuel_scalars.templete    1801   <- 后缀拼写错误（应为 .template）
  fusion.template          2077
  group.template            381
  hotelectrons.template     824
  interface.template        617
  laser.template           1336
  matter.template           555
  mixing.template          1090
  mixing_scalars.template  2155
  particlebeam.template       0   <- 空文件
  radiation.template        646
  scalars.template         2609
  readme.txt                180
```

#### 关键文件原文

**`templates/data/readme.txt`（180 B，全文）**
```
Templates for output data files
Name and Explanation separated with Tab¡£
Stored in fusion.template are those fusion related variables that will be hidden if fusion is disabled. 
```
（注：`¡£` 是 `。` 的 GBK 双字节被按 Latin-1 显示的结果，原文为中文句号。）

**`templates/data/matter.template`（555 B，全文照录）**
```
ebf		emission_bf(1/cm)
abf		absorption_bf(1/cm)
eff		emission_ff
aff		absorption_ff(1/cm)
ebb		emission_bb
abb		absorption_bb(1/cm)
em		emission_total
ab		absorption_total(1/cm)
xkirch	non-lte factor
sctcfs	scattering coefficients (1/cm)
abscfs	absorption coefficients
emscfs	emission coefficients
brmtota	bremsstrahlung total
piztota	photon ionization total
brmtote	bremsstrahlung total
piztote	photon ionization total
abslns	absorption lines
emslns  emission lines
emscfs	emission coefficients
photen	photon energy(eV)
```

**`templates/data/scalars.template`（2609 B，头部 12/40 行）**
```
TIME        	Time (s)
ISTEP       	Number of time step
ENLAS       	Incident laser energy(erg)
ENQUE       	Absorbed laser energy(erg)
ENIE        	Electron internal energy(erg)
ENII        	Ion internal energy(erg)
ENKI        	Kinetic energy(erg)
ENRAD       	ENRL*-ENRG*
ENRL1       	Rad. energy (left b.)
ENRL2       	Rad. energy (internal b. left)
ENRL3       	Rad. energy (internal b. right)
ENRL4       	Rad. energy (right b.)
...（共 40 行，ENRG1..4 / EALFA / ENAG / EYIELD / POWRAD(t) /
   MaxDrho@ / MaxTr@ / rhoR / Centroid / V_imp / Ti_burn_avg / PosInterface ...）
```

**`templates/data/fuel_scalars.templete`（1801 B，头部 8/38 行）** —— 注意后缀是 `.templete`
```
Time        	Time(s)
EALFA       	Energy in alpha particles(erg)
ENAL        	Energy lost in alpha particles(erg)
ENAG        	Fusion energy / 5(erg)
EYIELD      	Number of neutrons
Nproton     	Number of protons
Ti_burn_avg 	DT Burn-averaged ion temperature (eV)
Ti_mass_avg 	Mass-averaged ion temperature (eV)
...（共 38 行，Fusion.dndt / dndt(DT) / dadt(pB11) / dBe7dt ...）
```

**`templates/definitions.txt`（7338 B，头部 12 行）** —— 这是 **gnuplot 配色定义**，不是数据字典
```
Accent; defined ( 0 '#7FC97F', 1 '#BEAED4', 2 '#FDC086', 3 '#FFFF99', 4 '#386CB0', 5 '#F0027F', 6 '#BF5B17', 7 '#666666' ) 
Belgium; rgbformulae -4, 4, 9 model HSV
BioHazard; rgbformulae 3, 11, 6 model RGB
Blue_Sky; rgbformulae 23, 9, 2 model RGB
Blues; defined ( 0 '#F7FBFF', 1 '#DEEBF7', 2 '#C6DBEF', 3 '#9ECAE1', 4 '#6BAED6', 5 '#4292C6', 6 '#2171B5', 7 '#084594' )
BrBG; defined ( 0 '#8C510A', 1 '#BF812D', ... )
...
```
语法：`<名称>; defined ( idx '<#RRGGBB>', ... )` 或 `<名称>; rgbformulae r,g,b model RGB|HSV`。

**`templates/color/readme.txt`（305 B，全文）**
```
To add a new user defined color-tables, use the following format
#first line MUST be commented with #, only digits are allowed.
#R	G	B 
0	0	0
...
255	255	255

* save to file with extension *.dat
* current data from
   ct**.dat from IDL
   other from https://github.com/NeutrinoToolkit/Neutrino
```
`.dat` 配色表 = **定长 3328 B**（256 行 × RGB 三元组）；`ct00.gif`~`ct40.gif` 为对应预览图。

**`templates/template.case`（5870 B，头部 40 行）** —— 一个**空白 MULTI 输入卡骨架**（`&CONTROL` 段）
```
&CONTROL
   FLAG=1 	#Enable/disable control section
   Solver=0 	# default 0 for MULTI, 1 for MULTI-IFE
   NSPLIT=1 	#Number of hydro substeps (divisor of the number of groups)
   TEXIT=2.000000E-009 	#Maximum value of time
   TBegin=0.000000E+000 	#Minimum value of time
   NEXIT=10000 	#Maximum number of time steps
   DTN=1.000000E-011 	#Initial time step, maximum time step
   ...
```

#### 模板机制判定（**核心结论**）

1. **不存在变量占位符。** 对 `templates/**` 全量搜索 `$VAR` / `%VAR%` / `{VAR}` / `@VAR@` / `${...}` 均**无任何命中**。
2. **不存在模板展开器。** 目录内无宏处理器、无 `subst`/`expand` 类工具；`Multi1D++.exe` 为二进制，未发现引用 `templates/`。
3. **`templates/data/*.template` 的真实语义是「输出列名字典」**：
   - 每行格式恒为 `<变量名>\t<说明含单位>`，即 `readme.txt` 所述 *"Name and Explanation separated with Tab"*；
   - 用途是声明 MULTI 的 **ASCII 输出文件列头（colheaders）**——这正好解释了 `matlab/FAQ.txt` 中 *"Reference to non-existent field 'colheaders'"* 的报错；
   - **`fusion.template` 中的列在关闭聚变时会被隐藏**（`readme.txt` 明说）。
4. **`templates/color/` 是 gnuplot 配色表**（MULTI 自带 `gnuplot.exe`/`wgnuplot.exe`，见数据根），与 EOS 数据格式无关。
5. **`templates/template.case` 是「新建算例」的空白骨架**——GUI（`GUI4Multi1D.exe`）用它初始化 `Untitled.case`。

#### 如何生成输入文件

> **不是**「模板 → 展开 → 输入文件」，而是：
> **`templates/template.case`（骨架）+ GUI 用户填写 → 保存为 `*.case`（namelist 输入卡）**
> `templates/data/*.template` 只决定**输出文件的列名与单位**，不参与输入生成。

**文档应补：** 新增一节「输出变量字典（colheader）与配色表」，说明两套 `.template` 的实际语义，以纠正「模板=占位符替换」的直觉误解。

---

### A2. `tabelle/`（3 文件，567,699 B）**最高价值发现**

#### 文件清单

| 文件 | 字节 | 说明 |
|---|---|---|
| `tabelle/readme.txt` | 357 | **实为 C 源码片段**（见下） |
| `tabelle/tabelle1197.TFT` | 567,342 | Thomas-Fermi 预计算表数据 |
| `tabelle/### precomputed results of the Thomas-Fermi model` | 0 | **空文件，起目录标题作用**（Windows 下 `###` 前缀用于排序置顶） |

#### `readme.txt` 全文照录 —— 它不是说明，而是**生成代码**
```c
  for( i = 1; i<=NR; i++ ) {
    fprintf( h, "%.15e\n", (*table).rho[i] );
    for( j = 1; j<=NT; j++ ) 
      fprintf(h,"%.15e  %.15e  %.15e  %.15e  %.15e  %.15e\n",
	      (*table).Te[j],
	      (*table).Pe[i][j] ,
	      (*table).Ee[i][j], 
	      (*table).Fe[i][j],
	      (*table).Q[i][j], 
	      (*table).dPdT[i][j] );
	      }

rho
Te	Pe	Ee	Fe	Q	dPdT
```
> 这是**唯一权威的格式定义**：内层 6 列顺序为 `Te Pe Ee Fe Q dPdT`，密度逐块外层循环。

#### `tabelle1197.TFT` 实测结构
```
FILE: tabelle/tabelle1197.TFT  bytes=567342  [TEXT] nul=0 printable=1.000
L01| 1.000000000000000e-06                                        <- 块头：单个 rho 值
L02| 0.000000000000000e+00  1.254660623088583e-03  -2.003759859646893e+13  -2.003760052791487e+13  2.893944495541917e-04  1.392940783937051e+04
L03| 3.981071705534973e-03  5.545522588506331e+01  -2.003725909054711e+13  -2.003806034911374e+13  1.452750452487350e-02  2.449151112440131e+04
L04| 6.309573444801934e-03  1.246570912152580e+02  -2.003684986668875e+13  -2.003862411614766e+13  2.061068042156928e-02  3.475271211438451e+04
```
**结构统计（程序化验证）：**
- 非空行总数 = **4185**
- 字段数为 1 的行（rho 块头）= **93**
- 字段数为 6 的行（数据行）= **4092** = 93 × 44
- 每块行数恒定 = **44**（`distinct NT per block = [44]`）
- 无任何异常行

**⇒ 表维度：NR = 93（密度），NT = 44（温度）**
- rho 首值 `1.000000000000000e-06`，末值 `1.584893192461114e+03` g/cm³（对数等距）
- Te 首值 `0.0`，末值 `1.000000000000003e+06` eV

#### 与数据根同名文件的**逐字节等价性（关键）**

| 文件 | 字节 | sha256 |
|---|---|---|
| `tabelle/tabelle1197.TFT` | 567,342 | `3d0c638c2af54ff5af88d83938807d9f8e9b151ca6460d9dc7ad768ad65279df` |
| `FEOS_TF-Table_1197.dat`（数据根） | 567,342 | `3d0c638c2af54ff5af88d83938807d9f8e9b151ca6460d9dc7ad768ad65279df` |

**⇒ 两者内容完全一致**，仅文件名/位置不同。`.TFT` = `.dat` 的同一数据。

#### Thomas-Fermi 表在 EOS 计算中的角色（**由日志原文证实**）

`matter++/mat_Bi/Bi.PAR.log` L063–L074 原文：
```
 Initialize QIPscheme for element 1 (A = 208.980380, Z = 83.000000):
  Read Thomas-Fermi table:
   Source: ./FEOS_TF-Table_1197.dat
   Allocate memory for Thomas-Fermi table... done.
   Table size (densities x temperatures): 93 x 44          <-- 与实测 NR=93 NT=44 完全吻合
   Table boundaries (density, temperature):
    (1.000000e-06 g/cm^3, 0.000000e+00 eV) ...
    ... (1.584893e+03 g/cm^3, 1.000000e+06 eV)             <-- 与实测首末值完全吻合
  Generate H table... done.
  Initialize QEOS interpolation scheme... done.
 QIPscheme for element 1 successfully initialized.
```

**角色判定（证据链闭合）：**
- 该表是 **QEOS / QIP（Quotidian Equation of State）模型的「冷/简并电子」基座**；
- FEOS 的 `QIPscheme` 逐元素读取它，据此构造 **H 表**并建立 QEOS 插值；
- 它给出**单元素的 Thomas-Fermi 统计模型电子压强/能量/自由能/电荷态/∂P/∂T** 作为温度-密度全平面的先验，再叠加 `Bulk-Modulus`、`Rsolid`、结合能项（`E0`/`b`/`Ei_Offset`/`Ee_Offset`，见 log L081–L089）得到真实材料 EOS；
- 参数文件（`mat_He/Untitled.PAR` L01–L02）以 **`Path = ./tabelle/tabelle1197`** 引用它（无扩展名书写，实际打开 `.TFT`）。

> **注意**：`tabelle/` 是**基准元素（tabelle 1197）**的 Thomas-Fermi 表；每材料目录下无独立副本，FEOS 统一读数据根的 `FEOS_TF-Table_1197.dat`。

---

### A3. `cases_*`（9 个目录，121 文件，431,461,627 B）

#### 扩展名统计

| 目录 | 文件数 | 字节 | 扩展名分布 |
|---|---|---|---|
| `cases_1988CPC` | 7 | 20,435 | `.case`×7 |
| `cases_Experiments` | 2 | 9,054 | `.case`×2 |
| `cases_HotElectrons` | 2 | 14,500 | `.case`×2 |
| `cases_M1_78` | 4 | 10,187 | `.case`×4 |
| `cases_RadiativeShock` | 3 | 26,216 | `.case`×1, `.data`×1, **无后缀**×1 |
| `cases_ZhangLu` | 36 | 431,061,444 | `.dat`×30, `.case`×3, `.log`×3 |
| `cases_multi-ife` | 11 | 70,416 | `.case`×11 |
| `cases_multifs` | 15 | 53,455 | `.case`×15 |
| `cases_simple` | 48 | 143,965 | `.case`×46, `.data`×2 |

#### 典型算例的组织方式

**一个算例 = 1 个 `.case`（输入卡） + 0~1 个 `.data`（分区/网格表）[+ 运行产生 `.log`/`.dat`]**

**`cases_simple/simple1.case`（7629 B，头部 40 行）** —— FORTRAN namelist 风格的**输入卡**
```
&CONTROL
   GUIVerion=2024-09-12 15:14:25
   FLAG=1 	#Enable/disable control section
   IsNoLog=0 	#Enable/disable logging
   Solver=0 	# default 0 for MULTI, 1 for MULTI-IFE
   Solver.Method=0 	# default 0 for Explicit, 1 for Implicit
   NSPLIT=1 	#Number of hydro substeps (divisor of the number of groups)
   TEXIT=2.000000E-009 	#Maximum value of time
   ...
   WALLLEFT=1 	# left boundary
   WALLRIGHT=0 	# right boundary
   FLF=0.03 	#Flux limit factor
   ElectronHeatTransportModel=0 	#0 local(harmonic mean), 1 local(sharp cutoff), 2 LMV, ...
```
（`GUIVerion` 为 GUI 自动写入的时间戳；与 `templates/template.case` 段名完全同构 ⇒ **`template.case` 就是新建 `.case` 的骨架**。）

**`cases_simple/simple19.data`（497 B，全文头部）** —— **分区/网格表**（第 1 行为标识串，后续为 6 列数值）
```
MSanchez
0.00 0 5 0.05 5000 5000
0.01 0 5 0.15 5000 5000
0.02 0 5 0.25 5000 5000
...
0.20 0 
```

**`cases_RadiativeShock/RadiationCH150umAu2umCH50umFoamCH`（9,696 B，**无后缀**，头部 22 行）** —— 同族网格表
```
MSanchez
0	0	18	1	0.0253	0.0253
0.00075	0	18	1	0.0253	0.0253
...
0.015	0	9	19.32	0.0253	0.0253      <- 层界面：材料码 18->9，密度 1->19.32
0.0150066666666667	0	9	19.32	0.0253	0.0253
```
⇒ 第 1 列 = 位置（cm），第 4 列 = 密度（g/cm³），材料随位置切换（CH→Au）。**首个标识串 `MSanchez` 命名作者**。

**`.case` 段名全量统计（91 个 `.case` 文件）** —— 这是 MULTI 输入卡的完整段清单：

| 段名 | 出现次数 | 段名 | 出现次数 |
|---|---|---|---|
| `&CONTROL` | 91 | `&RTHCON` | 17 |
| `&RBOUND` | 91 | `&RELION` | 17 |
| `&LAYERS` | 87 | `&RSpectrum` | 17 |
| `&HYDRAND` | 70 | `&RSpectrumRight` | 13 |
| `&PULSE` | 46 | `&RSpectrumLeft` | 13 |
| `&PLASMA` | 41 | `&MixingControl` | 9 |
| `&RSOURCE` | 35 | `&PROFILE` | 5 |
| `&FSPULSE` | 28 | `&PULSE_3D` | 5 |
| `&MixModel` | 23 | `&MagneticField` | 4 |
| `&Fusion` | 18 | `&ResistivityModel` | 4 |
| `&RESIS` | 17 | `&IONBEAM` | 4 |
| `&LeakingTube` | 3 | `&ParticleBeam` | 2 |
| `&ParticleBeamParticleEnergy` | 2 | `&RSOURCETrHistoryFile` | 1 |
| `&PULSE1` | 1 | `&FSPULSE1` | 1 |

#### `cases_multi-ife` / `cases_multifs` 的论文对应关系

`doc/References/` 实测存在：
- `2016CPC(Ramis)_MULTI-IFE=A 1D computer code for IFE target simulations.pdf`（1,749,702 B）
- `2012CPC183.637(Ramis)_MULTI-fs – A computer code for laser–plasma interaction in the fs regime.pdf`（1,031,401 B）

`cases_multi-ife/` 文件名（`2015CPC.case`、`2015DIR.case`、`2015IND.case`、`2015DIR3DRayTest.case`、`2015DIRMaxwellTest.case`、`2015DIRWKBTest.case` …）与 MULTI-IFE 论文中的算例命名（DIR/IND = 直接/间接驱动，3DRay/WKB/Maxwell = 光线追踪模型）一致。
`cases_multifs/` 15 个 `.case` 与 MULTI-fs（飞秒激光等离子体相互作用）论文对应。

**⇒ 判定：`cases_multi-ife` ↔ 2016CPC (Ramis) MULTI-IFE；`cases_multifs` ↔ 2012CPC (Ramis) MULTI-fs。两者均属「算例输入卡集」，非数据格式。**

---

### A4. `matlab/`（197 文件，14,622,042 B）—— **非数据格式，概述即可**

**扩展名分布：** `.m`×150, `.dat`×26, `.docx`×7, `.txt`×4, `.dat_multi`×2, `无后缀`×2, 其他各 1（`.mat`/`.cat`/`.md`/`.case`/`.opj`）

**目录结构：**
```
matlab/
  *.m（主目录 175 项）       <- 导出/绘图/优化脚本
  Backlighter/     (3)
  Optimization/    (2)
  PostProcess/     (6)
    PostProcess/CrystalSpectrometer/ (1)
  RadiationSource/ (10)
```

**功能概览（据文件名与 FAQ）：**
- **数据导出**：`m1dppR1.m`（巫顺超版本原版 MULTI **二进制**输出导出码）、`Multi1DppDP.m`（Multi1D++ **ASCII** 输出导出码）、`Multi1DppDPFromFile.m`
- **物理后处理**：`CriticalDensity.m`、`FermiEnergy.m`、`FermiPressure.m`、`AtwoodNumber.m`、`AbsorptionSpectra.m`、`CalSpericalSurfaceRadiationFlux.m`
- **峰位/定位**：`PositionFromLeftToPeak.m` / `PositionOfHalfMax.m` / `RunGetShockWave.m`
- **运动模糊/优化**：`MotionBlur*.m`、`Optimization.m`、`RunOptimizationShock.m`
- 外部依赖 `processManager`（Brian Lau 的 MATLAB 异步进程管理类）

**`matlab/FAQ.txt`（GBK 编码，594 B，解码后全文）**
```
文件说明：
m1dppR1.m		巫顺超版本的原版MULTI二进制输出文件的导出代码
Multi1DppDP.m		Multi1D++的ASCII输出文件的导出代码
小写字母开头的文件为内部函数，请不要修改。

1. Data dimensions must agree.	
>>  surf(Time2D_interface,X, TI); 
上面的命令出错，因为离子温度TI是定义在网格中心，而不是网格边界上的量(如TR)，因此其空间维数要比TR等少一个，因此时间和空间坐标也应该使用定义在网格中心的量，如下：
>>  surf(Time2D_center,XC, TI); 

2.??? Reference to non-existent field 'colheaders'.
当前Matlab代码版本和Multi1D生成的数据文件版本不兼容，请使用最新的Multi1D版本运行后再用Matlab处理。
```

**⇒ 判定：`matlab/` 是 MATLAB 后处理工具集，属「软件」而非「数据格式」。唯一与格式相关的价值在于它揭示了输出数据的两个版本（原版 MULTI 二进制 vs Multi1D++ ASCII）及「colheaders」列头机制（呼应 §A1 的 `*.template`）。**

---

### A5. `Microsoft.VC90.CRT` / `Microsoft.VC90.MFC`（9 文件，3,889,696 B）—— **仅记录**

```
Microsoft.VC90.CRT/Microsoft.VC90.CRT.manifest        524
Microsoft.VC90.CRT/msvcm90.dll                     224,768
Microsoft.VC90.CRT/msvcp90.dll                     568,832
Microsoft.VC90.CRT/msvcr90.dll                     655,872
Microsoft.VC90.MFC/Microsoft.VC90.MFC.manifest        548
Microsoft.VC90.MFC/mfc90.dll                     1,156,600
Microsoft.VC90.MFC/mfc90u.dll                    1,162,744
Microsoft.VC90.MFC/mfcm90.dll                       59,904
Microsoft.VC90.MFC/mfcm90u.dll                      59,904
```

**一句话判定：Visual C++ 2008 (VC90) 运行时与 MFC 可再发行组件的私有分发（manifest 声明 + `msvc*m90.dll`/`mfc*90.dll`），使 Multi1D++ 免安装运行，与数据格式完全无关。**

---

## B. 遗漏的材料族

> 以下 19 个目录（+ 补查中发现的 3 个同族目录）含真实数据，主文档**完全未提及**。

### B-0. **格式族的权威自描述：`*.PAR.log`**

**`mat_Bi/Bi.PAR.log`（8,821 B）L001–L008 是 FEOS 自动生成的「输出文件清单」，这是全部 FEOS 族的权威格式定义：**
```
ï»¿FEOS.exe Bi
FEOS output file for Bi.PAR:
	Bi.301/.304/.305	SESAME EOS/Electron EOS/Ion EOS
	Bi.feos        	FEOS file
	Bi.cst         	Rostock format
	Bi.mexport     	SESAME mexport format
	Bi.data.txt    	SESAME 301 standard format
	Bi.critical.dat	binodal, spinodal, boiling- and cp-data
```
同日志后续（L011–L215）完整记录了 FEOS 12.9-beta 的建表流程：
```
FEOS table generation tool 12.9-beta
Read parameters from source Bi.par:
 Material number: 4083
 Rhonorm: 9.780000e+00 g/cm^3   Total number of density points: 123
 Tnorm: 1.000000e+02 eV         Total number of temperature points: 101
 Table size (densities x temperatures): 123 x 101
 Read Thomas-Fermi table: Source: ./FEOS_TF-Table_1197.dat  (93 x 44)
 Calculate energy offsets: Ei_Offset = +3.578674e+08 erg/g / Ee_Offset = -2.881273e+15 erg/g
 Write SESAME table format (Bi.301/304/305) / FEOS (Bi.feos) / mexport / data.txt / Rostock (Bi.cst)
 Calculate isobaric expansion data along P ~ 0 bar  ->  Bi.isobaric.dat
```

**⇒ 每个材料的标准产物为 7 件套：** `.301` `.304` `.305` `.feos` `.mexport` `.data.txt` `.cst` `+ .critical.dat + .isobaric.dat + .PAR（输入） + .PAR.log（日志）`

---

### B1. `mat_Bi`（9 文件，9,610,620 B）—— `mat_Cl/Co/Cr/Dy/F/K/N/Na/Ne/P/Pd/Sc/Sm` 同族

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `Bi.301` | 581,203 | **SESAME 301 ASCII** | ` 40830301       9.78000000e+00 1.23000000e+02 1.01000000e+02` |
| `Bi.304` | 581,203 | **SESAME 304 ASCII**（电子） | 同结构，表号 304 |
| `Bi.305` | 581,203 | **SESAME 305 ASCII**（离子） | 同结构，表号 305 |
| `Bi.data.txt` | 1,677,513 | **SESAME 301 标准制表文本** | `0	0	 0.00000000e+00	 0.00000000e+00	 9.64458415e-52	 4.58360282e-55	 9.64000055e-52	-1.08531956e+01 ...` |
| `Bi.feos` | 3,402,687 | **FEOS 原生表** | ` 1.20600000e+01 1.23000000e+02 1.01000000e+02 1.00000000e+00 1.00000000e-04 1.00000000e-50 9.78000000e+00 2.58525700e-02 3.10000000e+11 4.08300000e+03` |
| `Bi.mexport` | 1,845,656 | **SESAME mexport** | ` 0  4083   101   160   r        0        0   1                                 1` |
| `Bi.cst` | 930,030 | **Rostock（`.cst`）** | `Isotherme T = 0 Kelvin` / `MolekÃ¼ldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand` |
| `Bi.isobaric.dat` | 2,304 | **等压膨胀曲线** | `# Calculated isobaric expansion data (P ~= 0) from 1.16 to 6000.00 Kelvin:` / `# T [K]       Rho [g/cm^3]  P [bar]        Alpha [1/K]    H [J/g]        Cp [J/gK]` |
| `Bi.PAR.log` | 8,821 | FEOS 运行日志 + **格式自描述** | 见 §B-0 |

**关键校正：`Bi.301/.304/.305` 经二进制诊断（`nul=0, printable=1.000`）确认为 `%e` 科学计数法的 ASCII 文本，不是 SESAME 二进制格式。** 头部第一字段 `40830301` 即「材料号 4083 + 表号 301」拼接。

**材料语义：** Bi = 铋（Z=83, A=208.98, ρ₀=9.78 g/cm³，SESAME 号 4083）。**这是高 Z 材料，用于辐射屏蔽/不透明度实验。**

**新增未解后缀：** 无（全部为已知族）。`.PAR.log` 为 `.log` 族的 FEOS 特化，建议单独收录。

**同族差异（实测）：**
- `mat_Cl/F/N/Ne`：仅 9 文件 —— **缺** `.critical.dat` 与 `.isobaric.dat`
- `mat_Co/Cr/Dy/K/Na/Pd/Sm`：11 文件，含 `.critical.dat`(≈54 KB) 与 `.isobaric.dat`(2657 B)
- `mat_Na/K`：`critical.dat` 较小（53,449 / 3,955 B），`isobaric.dat` 2188 / 1608 B
- `mat_Sc`（22 文件）：**同目录双材料** —— `Sc.*`（钪）+ `Sc2.*`（另一物相/化学计量比）
- `mat_P`（14 文件）：**`P-red.*`（红磷，11 文件全套）+ `RedP.301/.304/.305`（仅 SESAME 三件）** —— 说明同一材料可只保留 SESAME 表
- `mat_Bi` 无 `.PAR`（仅有 `.PAR.log`），其余多数族有 `.PAR`（FEOS **输入**参数卡）

---

### B2. `mat_CH2`（3 文件，2,060,874 B）—— 多群不透明度（**非 FEOS 族**）

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `planckmg.out` | 1,020,250 | **多群 Planck 不透明度（`.out`）** | ` 20071004      PLANCK M         3.0000000E+01  4.2000000E+01` |
| `rossmg.out` | 1,020,250 | **多群 Rosseland 不透明度** | ` 20071004      ROSSELAND M      3.0000000E+01  4.2000000E+01` |
| `zeff.out` | 20,374 | **有效电荷 Zeff** | ` 20071004       0.60000000E+01  3.0000000E+01  4.2000000E+01` |

第 2 行 `  1.0000000E+00  1.1775000E+00` = 密度边界（归一化）；后续为对数能量网格（`-3.0` 起，间隔 0.1379）。`planckmg/rossmg` 与 `zeff` **列数不同**（前者 4 列/行，后者 4 列但少一列表头维度）。

**材料语义：** `mat_CH2` = **聚乙烯 CH₂**（ρ₀ = 1.1775 g/cm³ 与试验值 0.95 有差异，此处 1.1775 疑为归一化密度）；多群表 30 群 × 42？→ 首行 `3.0E+01`(NG) `4.2E+01`(NT)。

**新增未解后缀：** `.out`（多群不透明度，**未在已知清单**）。

---

### B3. `mat_CHBr`（4 文件，2,352,400 B）+ `CHBr3at%`（2 文件，1,176,200 B）

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `mat_CHBr/C50H38Br12_mopp` | 588,100 | **多群 Planck（`_mopp`）** | ` 1400003        PLANCK M         4.3000000e+01  4.2000000e+01` |
| `mat_CHBr/C50H38Br12_mopr` | 588,100 | **多群 Rosseland（`_mopr`）** | ` 1400002        ROSSELAND M      4.3000000e+01  4.2000000e+01` |
| `mat_CHBr/CHBr3at%/C50H47Br3_mopp` | 588,100 | 多群 Planck | ` 0700003        PLANCK M        4.3000000e+001 4.2000000e+001` |
| `mat_CHBr/CHBr3at%/C50H47Br3_mopr` | 588,100 | 多群 Rosseland | 同族 |
| `CHBr3at%/C50H47Br3_mopp` | 588,100 | 多群 Planck（**顶层重复**） | ` 0700003        PLANCK M        4.3000000e+001 4.2000000e+001` |
| `CHBr3at%/C50H47Br3_mopr` | 588,100 | 多群 Rosseland（**顶层重复**） | — |

**材料语义：**
- `C50H38Br12` = 溴化碳氢（**12 个 Br**，即高溴含量的 CHBr 类等离子体配方）
- `C50H47Br3` = **3 个 Br** 的配方
- `CHBr3at%` 目录名 = **「溴仿 CHBr₃ 的原子百分比（at%）配方」**；`C50H47Br3` 形式即「C:H:Br 计数比 ≈ 50:47:3」，与 CHBr₃ 的化学计量（1:1:3）经 H/C 富集后一致
- **顶层 `CHBr3at%/` 与 `mat_CHBr/CHBr3at%/` 内容同名同大小（588,100 B × 2），为重复副本**——可能是目录搬迁残留，**建议在文档中标注为冗余**

**新增未解后缀：** `_mopp` / `_mopr`（无点号，实为「多群 Planck/Rosseland」命名后缀，**未在已知清单**）。与 `mat_C-1.0` 的 `_mopp20` / `_mopr20` / `_mopp95` / `_mopr95` 同族（数字表示群数或版本）。

---

### B4. `mat_Gd`（12 文件，15,687,797 B）—— **新后缀族：`PLANCK/ROSS/EPS/ZEFF`（无点号）**

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `Gd100PLANCK` | 2,458,402 | **多群 Planck（无点后缀）** | ` 27003000      PLANCK M        3.00000000e+01 5.00000000e+01` |
| `Gd100ROSS` | 2,458,402 | **多群 Rosseland** | ` 27004000      ROSSELAND M     3.00000000e+01 5.00000000e+01` |
| `Gd100EPS` | 2,458,402 | **归一化发射率（EPS）** | ` 27005000      EPS M           3.00000000e+01 5.00000000e+01` |
| `Gd100ZEFF` | 24,553 | **有效电荷 Zeff** | ` 27002000      0.60000000E+01 3.00000000e+01 5.00000000e+01` |
| `Gd20PLANCK` / `Gd20ROSS` / `Gd20EPS` | 138,282 各 | 同上（**20 群**） | 首行 NG=2.0E+01 |
| `Gd20ZEFF` | 6,883 | Zeff（20 群） | — |
| `Gd_op100PLANCK` / `_ROSS` / `_EPS` | 2,613,402 各 | 同上（`op` 前缀） | ` 27003000      PLANCK M        4.00000000e+01 4.00000000e+01` |
| `Gd_op100ZEFF` | 26,103 | Zeff | — |

**结构解读：** 第 1 行 ` <SESAME号>  <PLANCK|ROSSELAND|EPS> M  <NG>  <NT>`；`M` 疑为 "Multi-group"。SESAME 号编成对：`27002000`(Zeff) / `27003000`(Planck) / `27004000`(Rosseland) / `27005000`(EPS) —— **末三位固定表示表类型**（2000=Zeff, 3000=Planck, 4000=Rosseland, 5000=Emissivity）。`mat_Au-1.0/AU_info` 原文佐证：
```
 ***       NLTE TABELLE FUER GOLD         ************
 *** 20 GRUPPEN ZWISCHEN 0 UND 5 KEV      ************
 **   Z:27002003; P:27003003; R:27004003  ************
 **   E:27005003                          ************
```
⇒ **Z/Zeff、P/Planck、R/Rosseland、E/Emissivity 四类表的后三位编号规则完全确认。**

**材料语义：** Gd = 钆（Z=64，极高中子吸收截面 + 高 Z 稀土），用于间接驱动黑腔掺杂与不透明度实验。`100`/`20` = 光子群数；`_op` 前缀 = opacity 变体（另一分辨率/网格）。

**新增未解后缀：** `PLANCK` / `ROSS` / `EPS` / `ZEFF`（**全部无点号，大写**；与有点号的 `.planck`/`.ross`/`.eps`/`.zeff` 并存，**未在已知清单**）。同族见 `mat_Au-1.0/Au100{EPS,PLANCK,ROSS}`+`Au100ZEFF`、`mat_Others/Mix20keV.{PLANCK,ROSS,EPS}`（**有点号**）——⇒ **两种书写风格混用**。

---

### B5. `mat_He`（9 文件，3,266,503 B）—— **混合族：FEOS 命名 + SNOP 命名**

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `Untitled.PAR` | 1,269 | **FEOS 输入参数卡** | `     TF-Table`<br>`Path = ./tabelle/tabelle1197`<br>`     Maxwell-Construction`<br>` Maxwell_Flag = 0`<br>` Charge_Flag = 1`<br>`     Material-Data`<br>` A = 4.00256163944925`<br>` Z = 2`<br>` Rsolid = 0.0001663`<br>` Bulk-Modulus = 2.61e+12` |
| `Untitled.301` | 618,700 | SESAME 301 | `  1111           1.66300000e-004 1.23000000e+002 1.01000000e+002` |
| `Untitled.304` / `.305` | 618,700 各 | SESAME 304 / 305 | 同结构 |
| `Untitled.CST` | 986,832 | **Rostock（大写扩展名 `.CST`）** | `Isotherm T = 0 Kelvin`<br>`Particle density[1/cc]  Mass density[g/cc]  Pressure[MBar]load state` |
| `SNOP.PLANCK` | 207,420 | 多群 Planck | ` 27003000      PLANCK M        0.20000000E+02 0.20000000E+02` |
| `SNOP.ROSS` | 207,420 | 多群 Rosseland | — |
| `SNOP.ZEFF` | 6,882 | Zeff | ` 27002000       0.60000000E+01 0.20000000E+02 0.20000000E+02` |
| `He_LTE.INPUT` | 580 | **SNOP 输入卡（namelist）** | `&daten`<br>`   NT = 20,`<br>`   NR = 20,`<br>`   NG = 30,`<br>`   NP = 3000,`<br>`   RHO1 = 0.000001,`<br>`   RHO2 = 100,`<br>`   T1 = 0.001,`<br>`   T2 = 100,`<br>`   X1 = 0.001,` |

**关键跨越：** 本目录**同时含 FEOS 产物（`Untitled.*`）与 SNOP 产物（`SNOP.*` + `He_LTE.INPUT`）**，且 `Untitled.PAR` 的 `Path = ./tabelle/tabelle1197` **直接证明 §A2 的 `tabelle/` 被 FEOS 引用**。

**材料语义：** He = 氦（Z=2, A=4.00256, ρ_solid=0.1663 g/cm³, B=2.61e12 dyne/cm²? 疑 MPa）。氦为 ICF 中的诊断气体/填充气体。

**新增未解后缀：** `.INPUT`（**大写，未在已知清单**，SNOP 输入卡）；`.CST`（大写 `.cst`）。

---

### B6. `mat_Sc`（22 文件，19,346,202 B）—— 双材料

| 材料 | 文件 | 格式族 |
|---|---|---|
| `Sc` | `Sc.301/.304/.305/.PAR/.PAR.log/.critical.dat/.cst/.data.txt/.feos/.isobaric.dat/.mexport`（11） | FEOS 全套（见 §B1） |
| `Sc2` | `Sc2.301/.304/.305/.PAR/.PAR.log/.critical.dat/.cst/.data.txt/.feos/.isobaric.dat/.mexport`（11） | 同上 |

**材料语义：** Sc = 钪（Z=21）。`Sc2` 为第二物相/第二化学计量（`.cst` 大小 929,594 vs 929,954，`.critical.dat` 54,073 vs 7,052 ⇒ 物相不同）。`Sc2.PAR.log` 仅 13,909 B（vs `Sc.PAR.log` 54,289 B）⇒ 未计算 `critical.dat` 全部等温线。

---

### B7. `mat_Pd`（11）、`mat_Sm`（11）、`mat_Dy`（11）、`mat_Cr`（11）、`mat_Co`（11）、`mat_K`（11）、`mat_Na`（11）、`mat_Cl`（9）、`mat_F`（8）、`mat_N`（9）、`mat_Ne`（9）、`mat_P`（14）

全部为 §B1 的 FEOS 7-11 件套，材料语义：

| 目录 | 元素 | Z | 说明 |
|---|---|---|---|
| `mat_Cl` | 氯 | 17 | 9 文件（无 critical/isobaric） |
| `mat_Co` | 钴 | 27 | 11 文件 |
| `mat_Cr` | 铬 | 24 | 11 文件 |
| `mat_Dy` | 镝 | 66 | 11 文件（稀土，高 Z） |
| `mat_F` | 氟 | 9 | 8 文件（无 `.PAR`） |
| `mat_K` | 钾 | 19 | 11 文件 |
| `mat_N` | 氮 | 7 | 9 文件；**其 `N.PAR` 仍写 "Material: aluminum (Al)"** ⇒ FEOS 参数卡模板未改，材料由文件名决定 |
| `mat_Na` | 钠 | 11 | 11 文件 |
| `mat_Ne` | 氖 | 10 | 9 文件；`Ne.feos` = 3,402,688 B（**比其它族多 1 字节**） |
| `mat_P` | 磷 | 15 | 14 文件（`P-red.*` 红磷全套 + `RedP.301/.304/.305`） |
| `mat_Pd` | 钯 | 46 | 11 文件 |
| `mat_Sm` | 钐 | 62 | 11 文件（稀土） |

> **注意 `mat_N/N.PAR` 头部仍为 `%% Material: aluminum (Al)`** —— 这是 FEOS 参数卡模板的**大量复制粘贴残留**，`mat_Cl/Cl.PAR` 亦然。**不能据 `.PAR` 内注释判断材料身份**，须以文件名/`SESAME 号`/`A`/`Z` 字段为准。文档应显式提示此陷阱。

**新增未解后缀：** 无。`.PAR.log`、`.critical.dat`、`.isobaric.dat`、`.data.txt` 建议正式收录。

---

### B8. `CHBr3at%`（顶层，2 文件，1,176,200 B）

`C50H47Br3_mopp`(588,100) + `C50H47Br3_mopr`(588,100) —— **与 `mat_CHBr/CHBr3at%/` 同名同大小，判为重复副本**（见 §B3）。

---

### B9. **补查中额外发现**：未提及但含真实数据的材料族

任务下达时未列出，但在 `os.walk` 全树中发现，**同样未被主文档提及**：

#### `mat_Others`（14 文件递归，含 2 子目录）—— 混合材料

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `Mix20keV.PLANCK` / `.ROSS` / `.EPS` | 204,060 各 | 多群不透明度（**点号 + 大写**） | 见 info |
| `Mix20keV.info` | 965 | 说明 | `files Mix20keV.PLANCK, Mix20keV.ROSS, and Mix20keV.EPS  (Doped Beryllium)`<br>`Planck-multigroup opacity table     (IP=20143000)`<br>`Rosseland-multigroup opacity table  (IR=20144000)`<br>`Normalized emissivity table         (IR=20145000)`<br>`Mass composition: 75.00 % Beryllium, 15.00 % Bromide, 10.00 % Sodium` |
| `CH10Water.info` | 27 | 说明 | — |
| `SiO2.feos` | 3,878,423 | FEOS 原生表 | — |
| `CH10Water1/CH10Water1_ieos` | 41,944 | **IONMIX ASCII EOS（`_ieos`）** | `           61310       0.958837 2.6000000E+001 5.0000000E+001` |
| `CH10Water1/CH2_H2O_1m1Z` | 30,087 | **Zeff（`_Z`）** | ` 3.1315100E+007 0.60000000E+01 3.7000000E+001 5.0000000E+001` |
| `CH10Water1/CH2_H2O_1m1opp` | 1,325,236 | **多群 Planck（`_opp`）** | 同 `_mopp` 族 |
| `CH10Water1/CH2_H2O_1m1opr` | 1,325,236 | 多群 Rosseland（`_opr`） | — |
| `CH10Water2/*`（4） | 同 | 同（`2m1` 变体） | — |

**`mat_Others` 是重要的复合/掺杂材料示例（掺 Br/Na 的 Be、CH 掺水、SiO₂）。**

#### `mat_S`（32 文件，28,947,941 B）—— 硫的三个同素异形体

`S-alpha.*`(11) / `S-beta.*`(11) / `S-gamma.*`(10) —— 全部 FEOS 7-11 件套；**`S-gamma` 缺 `critical.dat`**。

#### `mat_Au-1.0`（27 文件，9,083,292 B）—— **MULTI 1.0 模块分发格式（关键新族）**

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `README` | 1,221 | 说明 | `Gold properties` / `===============` / `AU_IDEAL_GAS` / `   EOS as ideal gas with Z=19.998,A=197 and GAMMA=1.2168` / `AU_eos` |
| `MODINFO` | 133 | **模块描述** | `m94version=2.0`<br>`cdate=Mon Oct 20 15:23:39 MET 1997`<br>`name=mat_Au-1.0`<br>`author=N/A`<br>`info=Tables for Gold`<br>`ldate=Mon Oct 20 15:42:58 MET 1997` |
| `FILELIST` | 34 | **文件清单** | `FILELIST`/`MODINFO`/`README`/`AU_*`/`LOCK` |
| `LOCK` | 29 | 锁标记 | — |
| `AU_info` | 853 | **NLTE 表说明（德文）** | ` ***       NLTE TABELLE FUER GOLD         ************`<br>` *** 20 GRUPPEN ZWISCHEN 0 UND 5 KEV      ************`<br>` **   Z:27002003; P:27003003; R:27004003  ************`<br>` **   E:27005003                          ************` |
| `AU_IDEAL_GAS` | 305 | **理想气体 EOS 参数卡（无后缀）** | `  .20020000E+04  .0             .20000000E+01  .20000000E+01` |
| `AU_NLTE.SNOP` | 518 | **SNOP 输入卡** | `&daten`<br>`   NT = 20,`<br>`   NR = 20,`<br>`   NG = 20,`<br>`   NP = 3000,`<br>`   RHO1 = 1e-06,` |
| `AU_eos` / `AU_eosd` | 74,003 / 145,608 | **MULTI 1.0 二进制 EOS 表** | — |
| `AU_eos.hug` | 81 | **Hugoniot 表（仅表头）** | `# Rho[g/cm^3]  T [eV]         P [Mbar]  E [erg/g]      Us [km/s]      Up [km/s]` |
| `AU_op03e/p/r` | 136,040 各 | **MULTI 1.0 多群不透明度**（e=发射率, p=Planck, r=Rosseland） | — |
| `AU_op03z` | 6,771 | Zeff | — |
| `AU_SIMPLE_PLANCK` / `_ROSSELAND` | 183 各 | 幂律不透明度占位 | — |
| `AU_SIMPLE_PLANCK_MG` | 4,893 | 幂律多群 | — |
| `AU_WorkOp_Ross` | 183 | 幂律 Rosseland | — |
| `Au.301` | 618,700 | SESAME 301 | — |
| `Au100EPS/PLANCK/ROSS` | 2,458,400 各 | 多群（无点后缀） | — |
| `Au100ZEFF` | 24,552 | Zeff | — |
| `SNOP.EPS/.PLANCK/.ROSS/.ZEFF` | 138,280×3 + 6,882 | SNOP 产物 | — |

**⇒ `FILELIST` + `MODINFO` + `README` + `LOCK` 构成「MULTI 1.0 模块（module）分发契约」**，`m94version=2.0` 为格式版本号。**这是主文档完全遗漏的一整套元数据格式。**

#### `mat_C-1.0`（43 文件，19,177,615 B）—— 同类，含更多新后缀

| 文件 | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `README` / `MODINFO` / `FILELIST` / `LOCK` | 654/134/33/29 | MULTI 1.0 模块 | 同 §mat_Au-1.0 |
| `C_IDEAL_GAS` | 305 | 理想气体卡 | — |
| `C_EOS` | 73,893 | MULTI 1.0 二进制 EOS | — |
| `C_Z.dat` | 30,055 | **Zeff（`.dat` 后缀但内容为 Zeff）** | `00000000        0.60000000E+01 4.3000000e+001 4.3000000e+001` |
| `C.ZEFF` / `C.ZEFF_old` | 6,771 各 | Zeff | — |
| `C_1G.PLANCK` | 6,771 | 单群 Planck | — |
| `C_Planck.dat` / `C_Rosseland.dat` | 2,858,265 各 | **多群不透明度（`.dat` 后缀）** | — |
| `C_20G.SNOP` / `C_20GSNOP.PLANCK/ROSS/ZEFF` | 651/138,280/138,280/6,882 | SNOP 族 | — |
| `Carbon.Planck/.Rosseland/.Zeff` | 138,280/138,280/6,882 | 多群（命名式） | — |
| `Carbon.info` | 1,150 | 说明 | — |
| `Carbon_DLC_ieos_e` / `_i` | 386,757 / 386,756 | **IONMIX ASCII（`_ieos_e`/`_ieos_i` = 电子/离子）** | — |
| `Carbon_Polystyrene_ieos_e` / `_i` | 317,845 各 | IONMIX ASCII | — |
| `CH_ieos` / `511_ieos` | 312,747 / 81,857 | IONMIX ASCII | — |
| `FEOS_Diamond.301/.304/.305` | 498,433 各 | SESAME | — |
| `Diamond_9216.dat` / `_e_` / `_i_` | 331,499 各 | 表 9216 三变体 | — |
| `FEOS_Diamond_9216.dat` | 331,499 | — | — |
| `CHSi1_mopp/mopr` | 588,100 各 | 多群 | — |
| `CH_mopp20/mopr20` | 588,100 各 | 多群（20 群） | — |
| **`CSi2.5_mopp95` / `CSi2.5_mopr95`** | 2,858,265 各 | 多群（95 群） | ` 6140003        PLANCK M         4.3000000e+01  4.3000000e+01` |
| **`CSi2.5_from_lililing`** | **0** | 空文件（占位） | — |
| `CHSi1_eos.IN` | 72,586 | **IONMIX ASCII（`.IN`）** | `            1214  6.725700e+000 5.8000000e+001 3.9000000e+001` |
| `C_SIMPLE_PLANCK` / `_ROSSELAND` | 183 各 | 幂律占位 | — |

#### `mat_Be-1.0`、`mat_Al-1.0`、`mat_Ti`、`mat_Ce`、`mat_CELIA`、`mat_CPC`、`mat_Ba`、`mat_B`、`mat_Eu`、`mat_Ge`、`mat_Sn`、`mat_Vacuum`

| 文件（代表） | 字节 | 格式族 | 头部原文 |
|---|---|---|---|
| `mat_Be-1.0/opbe.Rosseland` | 276,560 | **多群 Rosseland（命名式，大写 R）** | ` 20204000      ROSSELAND M     0.20000000E+02 0.20000000E+02` |
| `mat_Be-1.0/opbe.inhalt` | 2,274 | **SNOP 输入（德文 `EINGANGSPARAMETER`）** | ` ********* EINGANGSPARAMETER **********************`<br>` ****** Mit angeregten Niveaus in BF und BB *******`<br>`    Z        =     4.000E+00`<br>`    AW       =     9.012E+00` |
| `mat_Al-1.0/FEOS/FEOS_3717.hyades` | 1,661,976 | **Hyades 格式（`.hyades`）** | `   Al    DUAN-FEOS Dated: 202006`<br>`   3717     1.30000000E+01 2.698150000E+01 2.7000000E+00   107914` |
| `mat_Al-1.0/Al.feos.Rho-P.ist4gnuplot` | 2,133 | **gnuplot 绘图数据块（`4gnuplot` 族）** | `# T[1.000000e+000 eV]	Rho[1.000000e+000 g/cm^3]	P.ist4gnuplot[1.000000e+000e+012 dyne/cm^2]` |
| `mat_Eu/Eu_Planck_1987JQSRT` | 186 | **幂律不透明度表（`.readme` 附带系数）** | ` 0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001`<br>` 0.0000000E+000 0.1000000E+001 0.0000000E+000 0.1000000E+001` |
| `mat_Eu/Eu_Planck_1987JQSRT.readme` | 94 | 说明 | `Opacity generated by power law l = c * T^a*rho^b, with`<br>`c: 5.95806e-008`<br>`a: 1.536`<br>`b: -1.238` |
| `mat_Ge/Readme.txt` | 939 | 说明 | `Ge_2002FED_Planck & Ge_2002FED_Rosseland`<br>`REM from Analytical opacity formulas for ICF elements,Fusion Engineering and Design 60(2002) 17-25`<br>`REM equation k=e^a*T^b*rho^c` |
| `mat_Vacuum/Vacuum_Opacity.dat` | 186 | **真空占位不透明度** | `-1.0000000e+001-1.1000000e+001-1.0000000e+001-1.1000000e+001` |
| `mat_Sn/*`（4） | 186/94/186/92 | 幂律 + readme | — |
| `mat_CPC/AU.INV` | — | `.inv` 族 | — |
| `mat_Ce/Ce.INPUT` | — | `.INPUT` 族 | — |
| `SNOP/Be_40G.*` / `C_20G*.*` | 272,080×2+891+6,771 / 651+138,280×2+6,882 | SNOP 产物族 | — |
| `PROPACEOS/Readme.txt` | 120 | **明确「格式不公开」** | （GBK）`此文件格式为版权保护，没有找到相关格式说明文件。FLASH圈的格式转化软件opacplot2有相关代码，但是由于许可证问题没有公开。` |

**⇒ `PROPACEOS/Readme.txt` 是**关于 PROPACEOS 格式的一条重要的「负面证据」**：其格式受版权保护、转换工具 `opacplot2` 源码因许可问题未公开。主文档若声称覆盖 PROPACEOS，必须引用此限制。**

---

## C. `matter++/` 三级目录树

`matter++/` 根：11 文件 / 167,756 B；**129 个子目录**；递归 1,213 文件 / 729,653,444 B。
`files(here)` = 该目录直属文件数；`rec` = 递归文件数（含子目录）。**大量空目录（`rec=0`）已列出。**

```
<matter++>| files=11 bytes=167756 subdirs=129 rec=1213
  ANEOS|                              files=0  rec=0    <- 空目录
  ATOMIC|                             files=69 bytes=276117373
  CH|                                 files=19 bytes=13453140
  CHBr3at%|                           files=2  bytes=1176200
  ColdOpacity|                        files=71 bytes=7762868
  Crystal|                            files=3  bytes=1183
  Diamond|                            files=0  rec=0    <- 空目录
  FEOS|                               files=2  bytes=599833
  HeatCapacity|                       files=3  bytes=13134  subdirs=1 rec=5
    HeatCapacity/EP Coupling and Electron Heat Capacity in Metals at High Te_files| files=2 bytes=12771
  hyades|                             files=10 bytes=247649 subdirs=3 rec=157
    hyades/Opacity|                   files=36 bytes=1411801
    hyades/qeos|                      files=14 bytes=1934561
    hyades/sesame|                    files=97 bytes=7256502
  Ionmix|                             files=17 bytes=7124596
  Isotopes|                           files=0  rec=0    <- 空目录
  mat_Ac|                             files=0  rec=0    <- 空目录
  mat_Ag-Thermos|                     files=0  rec=0    <- 空目录
  mat_Al-1.0|                         files=35 bytes=9837986 subdirs=1 rec=39
    mat_Al-1.0/FEOS|                  files=4  bytes=3522393
  mat_Ar|                             files=0  rec=0    <- 空目录
  mat_Ar-Thermos|                     files=0  rec=0    <- 空目录
  mat_Au|                             files=4  bytes=6974
  mat_Au-1.0|                         files=27 bytes=9083292
  mat_B|                              files=11 bytes=9718166
  mat_Ba|                             files=17 bytes=9619158
  mat_Be-1.0|                         files=23 bytes=2392469
  mat_Bi|                             files=9  bytes=9610620
  mat_Br-Thermos|                     files=0  rec=0    <- 空目录
  mat_C-1.0|                          files=43 bytes=19177615
  mat_Ca-Thermos|                     files=0  rec=0    <- 空目录
  mat_Cd|                             files=0  rec=0    <- 空目录
  mat_Ce|                             files=16 bytes=9660233
  mat_CELIA|                          files=39 bytes=3760381
  mat_CH2|                            files=3  bytes=2060874
  mat_CHBr|                           files=2  bytes=1176200 subdirs=1 rec=4
    mat_CHBr/CHBr3at%|                files=2  bytes=1176200
  mat_Cl|                             files=9  bytes=9618162
  mat_Co|                             files=11 bytes=9707847
  mat_CPC|                            files=8  bytes=761803
  mat_Cr|                             files=11 bytes=9714136
  mat_Cu|                             files=0  rec=0    <- 空目录
  mat_Cu-Thermos|                     files=0  rec=0    <- 空目录
  mat_DT-1.0|                         files=13 bytes=532125
  mat_Dy|                             files=11 bytes=9707845
  mat_Er|                             files=0  rec=0    <- 空目录
  mat_Eu|                             files=4  bytes=559
  mat_F|                              files=8  bytes=9612202
  mat_Fe|                             files=0  rec=0    <- 空目录
  mat_Fe-|                            files=0  rec=0    <- 空目录
  mat_Fr|                             files=0  rec=0    <- 空目录
  mat_Ga|                             files=0  rec=0    <- 空目录
  mat_Gd|                             files=12 bytes=15687797
  mat_Ge|                             files=8  bytes=2041
  mat_H|                              files=0  rec=0    <- 空目录
  mat_H-Thermos|                      files=0  rec=0    <- 空目录
  mat_He|                             files=9  bytes=3266503
  mat_Hf|                             files=0  rec=0    <- 空目录
  mat_Hg|                             files=0  rec=0    <- 空目录
  mat_I|                              files=0  rec=0    <- 空目录
  mat_In|                             files=0  rec=0    <- 空目录
  mat_Ir|                             files=0  rec=0    <- 空目录
  mat_K|                              files=11 bytes=9622645
  mat_Kr-Thermos|                     files=0  rec=0    <- 空目录
  mat_La|                             files=0  rec=0    <- 空目录
  mat_Li-Thermos|                     files=0  rec=0    <- 空目录
  mat_Lu|                             files=0  rec=0    <- 空目录
  mat_Mg-Thermos|                     files=0  rec=0    <- 空目录
  mat_Mn|                             files=0  rec=0    <- 空目录
  mat_Mo|                             files=0  rec=0    <- 空目录
  mat_Mo-Thermos|                     files=0  rec=0    <- 空目录
  mat_N|                              files=9  bytes=9612815
  mat_Na|                             files=11 bytes=9712841
  mat_Nb|                             files=0  rec=0    <- 空目录
  mat_Nd|                             files=0  rec=0    <- 空目录
  mat_Ne|                             files=9  bytes=9621249
  mat_Ni-Thermos|                     files=0  rec=0    <- 空目录
  mat_Np|                             files=0  rec=0    <- 空目录
  mat_O|                              files=9  bytes=9607043
  mat_Os|                             files=0  rec=0    <- 空目录
  mat_Others|                         files=6  bytes=4491595 subdirs=2 rec=14
    mat_Others/CH10Water1|            files=4  bytes=2722503
    mat_Others/CH10Water2|            files=4  bytes=2722503
  mat_P|                              files=14 bytes=11447040
  mat_Pb|                             files=0  rec=0    <- 空目录
  mat_Pb-Thermos|                     files=0  rec=0    <- 空目录
  mat_Pd|                             files=11 bytes=9708878
  mat_Pm|                             files=0  rec=0    <- 空目录
  mat_Po|                             files=0  rec=0    <- 空目录
  mat_Pr|                             files=0  rec=0    <- 空目录
  mat_Pt|                             files=0  rec=0    <- 空目录
  mat_Pu|                             files=0  rec=0    <- 空目录
  mat_Ra|                             files=0  rec=0    <- 空目录
  mat_Rb|                             files=0  rec=0    <- 空目录
  mat_Re|                             files=0  rec=0    <- 空目录
  mat_Rh|                             files=0  rec=0    <- 空目录
  mat_Rn|                             files=0  rec=0    <- 空目录
  mat_Ru|                             files=0  rec=0    <- 空目录
  mat_S|                              files=32 bytes=28947941 subdirs=1 rec=32
    mat_S/mat_P|                      files=0  rec=0    <- 空目录
  mat_Sb|                             files=0  rec=0    <- 空目录
  mat_Sc|                             files=22 bytes=19346202
  mat_Se|                             files=0  rec=0    <- 空目录
  mat_Si-Thermos|                     files=0  rec=0    <- 空目录
  mat_Sm|                             files=11 bytes=9707848
  mat_Sn|                             files=4  bytes=558
  mat_Sr|                             files=0  rec=0    <- 空目录
  mat_Ta-Thermos|                     files=0  rec=0    <- 空目录
  mat_Tb|                             files=0  rec=0    <- 空目录
  mat_Tc|                             files=0  rec=0    <- 空目录
  mat_Te|                             files=0  rec=0    <- 空目录
  mat_Th|                             files=0  rec=0    <- 空目录
  mat_Ti|                             files=16 bytes=1640716
  mat_Tl|                             files=0  rec=0    <- 空目录
  mat_Tm|                             files=0  rec=0    <- 空目录
  mat_U|                              files=0  rec=0    <- 空目录
  mat_U-Thermos|                      files=0  rec=0    <- 空目录
  mat_V-Thermos|                      files=0  rec=0    <- 空目录
  mat_Vacuum|                         files=1  bytes=186
  mat_W|                              files=0  rec=0    <- 空目录
  mat_W-Thermos|                      files=0  rec=0    <- 空目录
  mat_Xe|                             files=0  rec=0    <- 空目录
  mat_Xe-Thermos|                     files=0  rec=0    <- 空目录
  mat_Y|                              files=0  rec=0    <- 空目录
  mat_Yb|                             files=0  rec=0    <- 空目录
  mat_Zn-Thermos|                     files=0  rec=0    <- 空目录
  mat_Zr|                             files=0  rec=0    <- 空目录
  others|                             files=0  rec=0    <- 空目录
  PeriodicTable|                      files=0  rec=0    <- 空目录
  PowerLaws|                          files=5  bytes=45079
  PROPACEOS|                          files=1  bytes=120
  RadiativeCoolingRates|              files=5  bytes=154986
  Reactivity|                         files=0  rec=0    <- 空目录
  SiO2|                               files=9  bytes=27378950
  SNOP|                               files=10 bytes=838189
  Ta2O5|                              files=45 bytes=16573847
  Thermos|                            files=1  bytes=576 subdirs=45 rec=228
    Thermos/mat_Ag|                   files=5  bytes=650484
    Thermos/mat_Al|                   files=5  bytes=412727
    Thermos/mat_Ar|                   files=5  bytes=1934335
    Thermos/mat_Au|                   files=9  bytes=2492195
    Thermos/mat_B|                    files=5  bytes=1997634
    Thermos/mat_Be|                   files=5  bytes=1854998
    Thermos/mat_Br|                   files=5  bytes=2092872
    Thermos/mat_C|                    files=5  bytes=1553902
    Thermos/mat_Ca|                   files=5  bytes=1680660
    Thermos/mat_Cl|                   files=5  bytes=526223
    Thermos/mat_Co|                   files=5  bytes=2108645
    Thermos/mat_Cr|                   files=5  bytes=682168
    Thermos/mat_Cu|                   files=5  bytes=2061154
    Thermos/mat_Dy|                   files=5  bytes=1997760
    Thermos/mat_F|                    files=5  bytes=2061059
    Thermos/mat_Fe|                   files=5  bytes=571212
    Thermos/mat_Gd|                   files=5  bytes=1981932
    Thermos/mat_H|                    files=5  bytes=1316114
    Thermos/mat_He|                   files=5  bytes=1728189
    Thermos/mat_K|                    files=5  bytes=2710938
    Thermos/mat_Kr|                   files=5  bytes=2520886
    Thermos/mat_Li|                   files=5  bytes=1189328
    Thermos/mat_Mg|                   files=5  bytes=1680668
    Thermos/mat_Mo|                   files=5  bytes=359744
    Thermos/mat_N|                    files=5  bytes=1981805
    Thermos/mat_Na|                   files=5  bytes=2425640
    Thermos/mat_Nd|                   files=5  bytes=1791732
    Thermos/mat_Ne|                   files=4  bytes=1251770
    Thermos/mat_Ni|                   files=5  bytes=1744057
    Thermos/mat_O|                    files=5  bytes=443205
    Thermos/mat_P|                    files=5  bytes=2156206
    Thermos/mat_Pb|                   files=5  bytes=571217
    Thermos/mat_Pd|                   files=5  bytes=2457376
    Thermos/mat_S|                    files=5  bytes=2536594
    Thermos/mat_Sc|                   files=5  bytes=1744086
    Thermos/mat_Si|                   files=5  bytes=1759981
    Thermos/mat_Sm|                   files=5  bytes=2140355
    Thermos/mat_Ta|                   files=6  bytes=2004120
    Thermos/mat_Ti|                   files=4  bytes=400948
    Thermos/mat_U|                    files=5  bytes=290604
    Thermos/mat_V|                    files=5  bytes=1696589
    Thermos/mat_W|                    files=8  bytes=1300816
    Thermos/mat_Xe|                   files=5  bytes=967500
    Thermos/mat_Zn|                   files=5  bytes=919928
    Thermos/___No EOS|                files=1  bytes=0 subdirs=1 rec=1
      Thermos/___No EOS/_mat_Mn 数据有误| files=0 rec=0   <- 空目录（且目录名标注「数据有误」）
  XrayMassCoef|                       files=2  bytes=9948 subdirs=5 rec=41
    XrayMassCoef/NIST  X-Ray Mass Attenuation Coefficients - Introduction_files| files=4 bytes=53316
    XrayMassCoef/NIST  X-Ray Mass Attenuation Coefficients - References_files|   files=5 bytes=58948
    XrayMassCoef/NIST  X-Ray Mass Attenuation Coefficients - Section 2_files|    files=10 bytes=58493
    XrayMassCoef/NIST  X-Ray Mass Attenuation Coefficients - Section 3_files|    files=16 bytes=71809
    XrayMassCoef/NIST  X-Ray Mass Attenuation Coefficients - Summary_files|      files=4 bytes=53316
```

**空目录统计：60 个 `rec=0` 的目录**（多为 `mat_XX` 元素占位、`mat_XX-Thermos` 占位、`ANEOS`/`Diamond`/`Isotopes`/`others`/`PeriodicTable`/`Reactivity` 等）。
**特殊：**
- `mat_S/mat_P` —— **嵌套了一个空目录 `mat_P`（目录名与顶层 `mat_P` 相同），判为误建**
- `Thermos/___No EOS/_mat_Mn 数据有误` —— 中文目录名，**标注锰数据有误**
- `mat_CHBr/CHBr3at%` 与顶层 `CHBr3at%` —— **同名重复**

---

## D. 新增未解后缀汇总

> 「已知」= 在任务下达的已知后缀清单中；本表仅列**新增**（不在清单内）或**需修正**的项。

| 后缀 | 出现位置 | 文件数 | 是否已知 | 初步判定 |
|---|---|---|---|---|
| `.PAR.log` | `mat_Bi` 等 13 个 FEOS 族 | 26 | **N** | FEOS 运行日志 + **输出文件格式自描述**（权威） |
| `.critical.dat` | `mat_Co/Cr/Dy/K/Na/P/Pd/S/P-red/Sc/Sm` 等 | ~12 | **N**（`.dat` 已知，此复合名未列） | 临界点 / binodal / spinodal / 沸点 / Cp 数据 |
| `.isobaric.dat` | 同上 | ~10 | **N**（同上） | P≈0 等压膨胀线（T, ρ, P, α, H, Cp） |
| `.data.txt` | 全部 FEOS 族 | 14 | **N**（`.txt` 已知，复合名未列） | SESAME 301 标准制表文本（10 列） |
| `.out` | `mat_CH2` | 3 | **N** | 多群 Planck/Rosseland 不透明度 + Zeff |
| `_mopp` / `_mopr` | `mat_CHBr`、`mat_CHBr/CHBr3at%`、`CHBr3at%` | 6 | **N** | 无点后缀；多群 Planck(pp)/Rosseland(pr) |
| `_mopp20` / `_mopr20` / `_mopp95` / `_mopr95` | `mat_C-1.0` | 4 | **N** | 同上 + 群数（20 / 95） |
| `_opp` / `_opr` | `mat_Others/CH10Water1、CH10Water2` | 4 | **N** | 同 `_mopp`/`_mopr` 变体拼写 |
| `_Z` | `mat_Others/CH10Water1、CH10Water2` | 2 | **N** | Zeff 表的简写后缀 |
| `PLANCK` / `ROSS` / `EPS` / `ZEFF`（**无点号全大写**） | `mat_Gd`(12)、`mat_Au-1.0`(4)、`mat_C-1.0` | 18 | **N** | 多群 Planck / Rosseland / 归一化发射率 / Zeff；**与有点号写法并存** |
| `.INPUT` / `.input`（**全大写**） | `mat_He/He_LTE.INPUT`、`mat_Ce/Ce.INPUT`、`mat_Au-1.0/AU_NLTE.SNOP` 同族 | 4 | **N**（`.input` 小写已知） | SNOP 输入卡（`&daten` namelist） |
| `.inhalt` / `.INHALT` | `mat_Be-1.0/opbe.inhalt`、`SNOP/opbe.inhalt` | 2+ | 部分 | **实为 SNOP 输入参数表（德文 `EINGANGSPARAMETER`）**，非「内容索引」 |
| `.CST`（全大写） | `mat_He/Untitled.CST` | 1 | **N** | Rostock 格式（`.cst` 大写变体） |
| `_ieos` / `_ieos_e` / `_ieos_i` | `mat_Others/CH10Water1、CH10Water2`、`mat_C-1.0` | 7 | **N** | **IONMIX ASCII EOS**（`_e`/`_i` = 电子/离子）；头 `61400/61310/1214` + 材料参量 |
| `.IN`（全大写） | `mat_C-1.0/CHSi1_eos.IN`、`CH/CHSi10_eos.IN` | 2+ | 部分 | IONMIX ASCII EOS（与 `_ieos` 同族） |
| `.hyades` | `mat_Al-1.0/FEOS/FEOS_3717.hyades`、`mat_Ce` 同族 | 2 | **N** | Hyades 格式；头 `   Al  DUAN-FEOS Dated: 202006` + 表号 3717 |
| `4gnuplot`（复合） | `mat_Al-1.0/Al.feos.Rho-P.ist4gnuplot` 等 | 5+3+1+1 | **N** | gnuplot 二维/三维绘图数据块（`# 列名[单位]` + TAB 数据） |
| `_from_lililing` / `.5_from_lililing` | `hyades/sesame/CSi2.5_from_lililing`（**0 B**）、`mat_C-1.0/CSi2.5_from_lililing`（**0 B**） | 2 | **N** | 空占位；`lililing` 疑为贡献者 ID；`CSi2.5` 为材料名 |
| `FILELIST` / `MODINFO` / `LOCK` / `README`（无后缀） | `mat_Au-1.0`、`mat_C-1.0`、`mat_Be-1.0` 等 MULTI 1.0 模块 | 4+/族 | **N** | **MULTI 1.0 模块分发元数据契约**；`m94version=2.0` |
| `AU_IDEAL_GAS` / `C_IDEAL_GAS`（无后缀） | `mat_Au-1.0`、`mat_C-1.0` | 2 | **N** | 理想气体 EOS 参数卡（无后缀） |
| `.readme`（小写） | `mat_Eu`、`mat_Ge`、`mat_Sn`、`mat_Au` 等 | 11 | **N** | 幂律不透明度系数说明（`c`,`a`,`b`） |
| `.Rosseland` / `.Planck` / `.Zeff`（**首字母大写**） | `mat_Be-1.0/opbe.Rosseland`、`mat_C-1.0/Carbon.*` | 6+ | **N** | 多群不透明度，命名式大写变体 |
| `.ist4gnuplot` | 同 `4gnuplot` | 5 | **N** | 同上 |
| `### ...`（目录标题文件，0 B） | `tabelle/### precomputed results of the Thomas-Fermi model`、`matter++/SNOP/### Generated by SNOP` | 2 | **N** | 0 字节占位文件，用 `###` 前缀在资源管理器中置顶作目录标题 |
| `Settings` / `Default` / `data` / `default`（`.ini` 家族） | `ColdOpacity/default.ini` 等 | 43 | 部分 | 各工具配置 |
| `.xlsx` / `.xls` / `.xml` / `.js` / `.html` / `.doc` / `.bak` / `.db` | `mat_Al-1.0/BulkModulus.xlsx`、`XrayMassCoef/*`、`hyades/*` | ~25 | **N**（非数据格式） | 办公/网页/备份杂项，**建议明确排除** |
| `.10` / `.dat_multi` / `.cat` / `.m` | `matlab/` | 1/2/1/150 | 部分 | MATLAB 后处理相关（`.m` 为源码） |
| `_mexport`(已已知) 头字段 | `Bi.mexport` | — | 已知 | 第 1 行 `0 4083 101 160 r ...` = 表类型/材料号/NT/NR/网格类型 |

**⚠ 建议修正主文档的 3 处：**
1. `.301/.304/.305` **为 ASCII 文本**（`%e` 格式），**不是 SESAME 二进制**——文档若按二进制描述须更正。
2. `.cst` 有两处拼写变体：`.cst`（小写，24 个）与 `.CST`（大写，`mat_He/Untitled.CST`）。
3. `.PAR` 内的 `%% Material: ...` 注释**不可信**（`mat_N/N.PAR`、`mat_Cl/Cl.PAR` 均残留 "aluminum (Al)"）。

---

## 未能读取 / 存疑项

| 项 | 状态 | 说明 |
|---|---|---|
| `tabelle/### precomputed results of the Thomas-Fermi model` | **0 字节** | 确定为目录标题占位文件，非数据 |
| `matter++/SNOP/### Generated by SNOP` | **0 字节** | 同上 |
| `matter++/hyades/sesame/CSi2.5_from_lililing` | **0 字节** | 空占位 |
| `matter++/mat_C-1.0/CSi2.5_from_lililing` | **0 字节** | 空占位 |
| `templates/data/particlebeam.template` | **0 字节** | 空模板 |
| `matter++/mat_Au-1.0/AU_eos`、`AU_eosd`、`AU_op03e/p/r` | **判定为二进制** | 未做完整解析（MULTI 1.0 未公开二进制格式）；如需，建议单独任务 |
| `matter++/hyades/*`（Opacity/qeos/sesame，157 文件） | **未展开** | 不在本任务 19 族清单；建议另派 |
| `matter++/Thermos/*`（228 文件） | **未展开** | 同上 |
| `matter++/ATOMIC/`（276 MB）、`ColdOpacity/`、`Ionmix/`、`SiO2/`、`Ta2O5/`、`CH/`、`mat_CELIA/`、`mat_CPC/`、`mat_Ba/`、`mat_B/`、`mat_Ce/`、`mat_CELIA/` | **未展开** | 主文档若已覆盖则为已知族；本任务仅补查「未提及」者，故未逐一读头 |
| `matter++/XrayMassCoef/*`（41 文件） | **未展开** | NIST 网页存档（`.js`/`.html`/`.gif`），非数值格式 |
| `FEOS_Material-DB.dat`（114,029 B，数据根） | **未读** | 数据根 FEOS 材料数据库，建议纳入另一次任务 |
| `matter++/PROPACEOS/` | **格式不公开** | 见 §B9 引用的 `Readme.txt`（版权保护，`opacplot2` 源码未公开） |

---

*报告结束。所有判定均附「真实相对路径 + 头部原文照录」；二进制/文本判定基于 `nul` 字节数与可打印字符比例（阈值：`nul=0 且 printable>0.90` 判为 TEXT）。*
