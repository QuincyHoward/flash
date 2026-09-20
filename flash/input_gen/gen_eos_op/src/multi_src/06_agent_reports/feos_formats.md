# FEOS / MPQeos 格式族 —— 源码级逆向分析报告

分析对象：FEOS 官方软件包 16.7（`Code/` 下 18 个 `.C` + 18 个 `.H`，`Documents/FEOS-Package-Documentation.pdf` 之文本版，`EOS-Data/` 样例）
交叉验证对象：`src/Multi1D++Portable20241128/matter++/` 下 29 个 `.feos`、28 个 `.301`、27 个 `.304`、27 个 `.305`、24 个 `.cst`、14 个 `.critical.dat`、19 个 `.isobaric.dat`、23 个 `.mexport`、5 个 `.hug`、10 个 `.ist*` 实测样本

> 说明：本报告中所有「源码位置」均标注为 `文件名:行号`，行号取自本机解压的 FEOS 16.7 源码。
> 凡源码中无依据者，一律写明「**源码中未找到**」，不做推测。

---

## 1. 摘要表

| 问题 | 结论（一句话） | 置信度 | 主要源码位置 |
|---|---|---|---|
| **Q1** `.feos` 行宽冲突 | **`SF_TRENN` 被定义为空串 `""`**，所以写入器实际输出的是**无分隔符**的 `%15.8le` 紧接串联；`.feos` = **每行 10 字段 × 15 字符 = 150 字符**。`Readme.txt` 的「一行 4 个 15 字符」是**错误的**（那是给 `.301/.304/.305` 用的）。参数行与数据行均为 10 字段/行，无差别；数据体共 **8 个组块**（P/E/S/F、Pe/Ee/Se/Fe、Pi/Ei/Si/Fi、PTF/ETF/STF/FTF、Qtot、Q）。 | **极高** | `FE-00_DEFINITS.H:28`、`FE-01_TABTOOLS.C:196-366`、`SE-01_READTABLE.C:11-123` |
| **Q2** `.301/.304/.305` 真实类型 | **纯 ASCII，每行 4 × 15 字符 = 60 字符**（FEOS 16.7 原生输出，`%15.8le` 无分隔符）。`Readme.txt` 的「4×16」在**本机确有实物**（`mat_Au-1.0/Au.301` 实测 64 字符 = 4×16），那是**旧版 MPQeos v2.0 写入器**的产物，不是 FEOS 16.7。两者都是纯文本。 | **极高** | `FE-01_TABTOOLS.C:594-668`（301）、`:672-744`（304）、`:748-820`（305） |
| **Q3** SHOWEOS 6 个输出后缀 | `.ist`/`.isc`/`.ise`/`.mnt`/`.hug` 五个后缀在 `SE-00_DEFINITS.H:29-33` 定义；单点（选项 6）**只打印到 stdout，不落盘**。首行注释确切文字见 §4。**`*4gnuplot` 在 FEOS 源码中未找到** —— 它是**外部后处理工具**生成的（实测证实：`.ist4gnuplot` = `.ist` 的转置重排，T 提到第 1 列、块间用空行替代 `&`）。`.hug` 6 列语义与单位已从源码逐列确认。 | 高（.hug/.ist 等）；低（4gnuplot 生产者身份） | `SE-00_DEFINITS.H:29-33`、`SE-03_SERVICES.C:306-378`（Isotherms）、`:382-454`（Isochores）、`:458-560`（Isentropes）、`:564-645`（Mountain）、`:649-749`（Hugoniot）、`:753-796`（SinglePoint）、`SE-04_MAIN.C:98-106` |
| **Q4** `.mexport` | **SESAME「mexport」ASCII 数据库格式**，**单材料**（仅含被算材料），含记录 `101/102/201/301/304/305`，**每行严格 80 字符**（5×15 数据 + 5 字符控制列 = 5×16 视觉宽度）。表号来自 `.par` 的 `Material-Number` ↔ 材料库 `SESAME-Number`。 | **极高** | `FE-01_TABTOOLS.C:370-590` |
| **Q5** `.cst` | **Rostock format**，纯文本（UTF-8，含德文表头）。逐列 = `Moleküldichte[1/cm^3]`, `Massendichte[g/cm^3]`, `Druck[MBar]`, `Ladungszustand`。它是 **T–ρ 网格**上每一条等温线里的 `(n, ρ, P, Qtot)` 四元组。 | **极高** | `COMMON-00_DEFINITS.H:26`、`FE-01_TABTOOLS.C:883-907` |
| **Q6** `.critical.dat` / `.isobaric.dat` | 两者均为纯文本、`#` 注释、`%e` 数据。`.critical.dat` 有 **14 个分段**（临界点/沸点/双结点/旋节线/直径线/蒸发焓/Arrhenius/压缩因子…），逐列语义见 §6。`.isobaric.dat` 首段 6 列 `T[K] / ρ[g/cm³] / P[bar] / α[1/K] / H[J/g] / Cp[J/gK]`，另附一段 T–ρ 平面数据。 | **极高** | `FE-01_TABTOOLS.C:58-192`（critical）、`FE-02_CALCULATIONS.C:181-218`（isobaric）、`FE-00_DEFINITS.H:26-27` |
| **Q7** `.feos` 参数行语义 | **20 个字段全部逐字段与源码变量对齐**（对照表见 §7），team-lead 给出的前 10 字段命名**部分不准确**（第 4 个是 `Nelements+1` 不是 `Nelements`；第 9 个准确名为 `BulkModulusRef`）。表尺寸为 `NR+1`/`NT+1` 的原因是 **`write_FEOS_format` 里的 `NR = NRho-1` 是「最后下标」**，写出的 `NR+1` 就是**数组元素个数 `NRho`**；文档明确说明**自动补 `T=0.0 eV` 与 `ρ=0.0 g/cm³`**。 | **极高** | `FE-01_TABTOOLS.C:206-227`、`SE-01_READTABLE.C:34-36`、`FE-03_MAIN.C:55-56,82-90`、文档 §15（"automatically adds T = 0.0 eV and ρ = 0.0 g/cm3"） |
| **Q8** `.par` 与 `Path =` 机制 | `.par` 为 **NAMELIST 风格 ASCII**（非严格 namelist，是自定义 `key = value` + `%`/`#` 注释），分区 `Computation-Settings` / `Q-table` / `General` / `Units` / `Rho-T-Mesh` / `Isocurves` / `Mountain` / `Hugoniot`。**`Path =` 在 FEOS 16.7 源码中未找到** —— 它属于**旧版 MPQEOS v2.0 参数模式**（本机仅 `mat_He/Untitled.PAR` 一处遗留样本）。TF 表路径在 FEOS 中是**编译期硬编码**的 `TF_TABLE_PATH`。`FEOS_TF-Table_1197.dat` 内部格式已完整还原：**93×44**，列序 `T[eV], Pe, Ee, Fe, Q, dPdT`，单位 cgs。 | **极高**（.par/TF 表）；**高**（Path 归属） | `COMMON-02_READFILE.C:129-169`、`LIB-00_DEFINITS.H:23-24`、`LIB-01_TF_SERVICES.C:74-162`、`LIB-02_TF_TABLE_2.C:331-409` |

---

## 2. Q1 —— `.feos` 文件的行宽冲突（最重要）

### 2.1 关键定义：`SF_TRENN` 是空串

```c
// FE-00_DEFINITS.H:26-28
#define CRITICAL_SUFFIX "critical.dat"
#define ISOBARIC_SUFFIX "isobaric.dat"
#define SF_TRENN        ""
```

**这是整个冲突的根因。** `SF_TRENN` 这个名字（"Trennzeichen" = 德文「分隔符」）本意是字段分隔符，但被赋值为空串。因此所有 `fprintf(h,"%15.8le",x); if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");` 实际等价于「每 10 个字段换行、字段间零分隔」。

### 2.2 写入代码（`FE-01_TABTOOLS.C:196-366`）

```c
// FE-01_TABTOOLS.C:196-227
void write_FEOS_format( char* name_in, Qtable* table)
{
  // FEOS EOS format
  // indices start at 0
  //
  // with Pressure, Energy, Free Energy, Entropy, Charge states, 
  //      EOS paramters
  //
  // FEOS units are cgs (+ eV for temperature)
  
  double FileVersion = 12.06;
  int i,j,k,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1,
    Nelements = (*table).Nelements-1;
  FILE* h;
  char name[STRSIZE];  

  sprintf( name,"%s.%s",name_in,"feos" );
  printf( "\nWrite FEOS table format (%s):\n", name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_FEOS_format ---> Error occured while opening file !!!\n");
    exit(0);
  }

  // Print EOS parameters:
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",FileVersion,SF_TRENN,double(NR+1),SF_TRENN,double(NT+1),SF_TRENN,double(Nelements+1),SF_TRENN,(*table).Tcalclimit);
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).Rhocalclimit,SF_TRENN,(*table).RhoRef,SF_TRENN,(*table).TRef,SF_TRENN,(*table).BulkModulusRef,SF_TRENN,double((*table).SESAMEnumber));
  fprintf(h,"\n");
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).ElectronOffset,SF_TRENN,(*table).IonOffset,SF_TRENN,(*table).Ecoh,SF_TRENN,(*table).softsphere_n,SF_TRENN,(*table).softsphere_m);
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).softsphere_A,SF_TRENN,(*table).softsphere_B,SF_TRENN,(*table).Atot,SF_TRENN,(*table).Ztot,SF_TRENN,(*table).Xtot);
  fprintf(h,"\n");
  //
  count = 0;
  //
  for(k=0;k<=Nelements;k++ ) {
    fprintf(h,"%15.8le", (*table).A[k] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }
  for(k=0;k<=Nelements;k++ ) {
    fprintf(h,"%15.8le", (*table).Z[k] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }   
  for(k=0;k<=Nelements;k++ ) {
    fprintf(h,"%15.8le", (*table).X[k] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }
  
  // Print densities and temperatures:      
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8le", (*table).Rho[i] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j] );
    if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }        
```

**读代码：**

```c
// SE-01_READTABLE.C:11-40
void read_FEOS_format( char* name_in, Qtable* qtab, Units* units )
{
  FILE* h;
  int i,j,k,NR,NT,Nelements;
  int fscanfresult __attribute__ ((unused));
  double d;
  char name[STRSIZE];
  
  sprintf(name,"%s.%s",name_in, "feos");
  printf("\nCheck file version and read table size from source %s...", name );
  if ((h=fopen(name,"r"))==NULL) {
    printf("\nSE-ERROR in read_FEOS_format ---> File %s not found !!!\n",name);
    exit(0);
  }

  // Check file version:
  fscanfresult = fscanf(h,"%le",&d );
  if(d>12.06) {
    printf("\nSE-ERROR in read_FEOS_format ---> %s (file version %4.2f) cannot be read by this (old) version of SHOWEOS !!!\n",name,d);
    exit(0);  
  }

  // Read table parameters:
  fscanfresult = fscanf(h,"%le",&d); (*qtab).NRho = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).NT = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Nelements = int(d);
```

**注意：读取方用 `fscanf(h,"%le",&d)` —— 纯空白（含换行）分隔，完全无视「每行几个」。** 这说明 `.feos` 的「每行 10 个」只是**排版约定**，语义上是一个 **token 流**。这一点对写解析器非常重要。

### 2.3 实测验证

`src/Multi1D++Portable20241128/matter++/mat_Al-1.0/Al.feos`（3,628,968 B，CRLF 行尾）：

```
line 0  len=150  ' 1.20600000e+01 1.92000000e+02 6.90000000e+01 1.00000000e+00 1.00000000e-04 1.00000000e-50 2.70000000e+00 2.58525700e-02 7.50000000e+11 3.71700000e+03'
line 1  len=150  '-2.94875001e+14 3.00821482e+09 1.21230000e+11 2.00000000e+00 5.00000000e-01 5.27428129e+09 9.90197297e+10 2.69815000e+01 1.30000000e+01 1.00000000e+00'
line 2  len=150  ' 2.69815000e+01 1.30000000e+01 1.00000000e+00 0.00000000e+00 2.70000000e-06 ...'
```

按 15 字符切分，**每行恰好 10 个字段**：

```
line0 -> [' 1.20600000e+01',' 1.92000000e+02',' 6.90000000e+01',' 1.00000000e+00',' 1.00000000e-04',
          ' 1.00000000e-50',' 2.70000000e+00',' 2.58525700e-02',' 7.50000000e+11',' 3.71700000e+03']
```

**行宽直方图（全部 23875 行）：`{10 字段: 23874 行, 8 字段: 1 行}`** —— 即**每行都是 10 字段**，只有最后一行（文件自然结束）是 8 字段。

### 2.4 字段总数核算（证实 writer 完全自洽）

以 `Al.feos` 为例，头 20 个字段给出 `NRho=192, NT=69, Nelements=1`：

| 段 | 公式 | 字段数 |
|---|---|---|
| 参数行第 1 行 | 10 | 10 |
| 参数行第 2 行 | 10 | 10 |
| `A[]`, `Z[]`, `X[]` | `3 × Nelements` | 3 |
| `Rho[]` | `NR+1 = NRho` | 192 |
| `T[]` | `NT+1 = NT` | 69 |
| 总 EOS：`P, E, S, F` | `4 × NRho × NT` | 52,992 |
| 电子：`Pe, Ee, Se, Fe` | `4 × NRho × NT` | 52,992 |
| 离子：`Pi, Ei, Si, Fi` | `4 × NRho × NT` | 52,992 |
| 纯 TF：`PTF, ETF, STF, FTF` | `4 × NRho × NT` | 52,992 |
| `Qtot` | `NRho × NT` | 13,248 |
| `Q[k]`（k=0..Nelements = 1 个） | `Nelements × NRho × NT` | 13,248 |
| **合计** | | **238,748** |

**实测字段总数 = 238,748 → 完全吻合。** 结论：`.feos` 是**无分隔符的 15 字符定宽 token 流**，每 10 个换行。

### 2.5 数据体的组块划分（共 **8 个组块**）

按 `FE-01_TABTOOLS.C:254-353` 的写出顺序：

| # | 组块内容 | 变量 | 排列顺序 |
|---|---|---|---|
| 0 | EOS 参数（2 行 × 10） | — | 见 §7 |
| 0' | 元素 A / Z / X | `A[k], Z[k], X[k]` | k 递增 |
| 0'' | 网格 | `Rho[i]` (i=0..NR)，`T[j]` (j=0..NT) | i 递增；再 j 递增 |
| 1 | 总 EOS 压力 | `P[i][j]` | **j 外层、i 内层**（等温线为主序） |
| 2 | 总 EOS 能量 | `E[i][j]` | 同上 |
| 3 | 总 EOS 熵 | `S[i][j]` | 同上 |
| 4 | 总 EOS 自由能 | `F[i][j]` | 同上 |
| 5 | 电子 EOS：P/E/S/F | `Pe, Ee, Se, Fe` | 同上 |
| 6 | 离子 EOS：P/E/S/F | `Pi, Ei, Si, Fi` | 同上 |
| 7 | 纯 TF EOS：P/E/S/F | `PTF, ETF, STF, FTF` | 同上 |
| 8 | 电荷态 | `Qtot[i][j]`；再 `Q[k][i][j]` | 同上 |

> **注意主序**：源码是 `for(j=0;j<=NT;j++) for(i=0;i<=NR;i++)`，即**温度外层、密度内层**。而 `Q[k][i][j]` 在读取方是 `for(j) for(i) for(k)`（`SE-01_READTABLE.C:108-110`），写读一致。

### 2.6 参数行 vs 数据行：**无差别**

参数行（第 1、2 行）由**两条** `fprintf` 各写 5 字段（见 `:222-226`），合起来**恰好 10 字段/行**，与数据行完全相同。**不存在「参数行字段数不同」的情况。**

### 2.7 与 `Readme.txt` 的对照裁决

```
src/Multi1D++Portable20241128/matter++/Readme.txt:12-14（GBK 编码）
如果文件名和路径中有“.feos”，程序识别为FEOS程序文件，按照一行4个15字符的数字读入
如果文件名和路径中有“.301”或“.304”或“.305”，程序识别为MPQeos生成的每行4x16个字符
其他按照默认的SESAME数据库格式，每行4x15个字符。
```

**裁决：`Readme.txt` 关于 `.feos` 的第 12 行描述是错误的。**
- 真实 `.feos` 是 **10×15**，不是 4×15；
- 真实 `.301/.304/.305`（FEOS 16.7 产出）是 **4×15**，不是 4×16；
- `Readme.txt` 的「4×16」在**旧 MPQeos 产物上确实成立**（见 Q2）。

可能的误导来源：`Readme.txt` 把 `.feos` 与 `.301/.304/.305` 的**行宽规则写反/串位了**。

---

## 3. Q2 —— `.301` / `.304` / `.305` 的真实类型

### 3.1 写入代码

```c
// FE-01_TABTOOLS.C:594-637（write_301_format，节选）
void write_301_format( char* name_in, Qtable* table)
{
  // SESAME 301 standard format
  // indices start at 0
  //
  // with Pressure, Energy, Charge State
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin

  double rhosolid = (*table).RhoRef;
  int matnumber = (*table).SESAMEnumber;

  int i,j,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];
  //
  sprintf( name,"%s.%s",name_in,SES_301_SUFFIX );
  printf( "\nWrite SESAME table format (%s):\n",name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_301_format ---> Error occured while opening file !!!\n");
    exit(0);
  }
  
  fprintf(h," %04d0301      %15.8le%15.8le%15.8le\n",
	  matnumber,rhosolid,double(NR+1),double(NT+1) );
  //
  // Rho and T vectors:
  //  
  count = 0;
  for(i=0;i<=NR;i++ ) {
    fprintf(h,"%15.8le", (*table).Rho[i]*cgs2ses_rho );
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  }  
  for(j=0;j<=NT;j++ ) {
    fprintf(h,"%15.8le", (*table).T[j]*cgs2ses_t ); 
    if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
  } 

  for(j=0;j<=NT;j++)      // pressure
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).P[i][j]*cgs2ses_p );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)   // energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).E[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }  
  
  for(j=0;j<=NT;j++)  // free energy
    for(i=0;i<=NR;i++) {
      fprintf(h,"%15.8le", (*table).F[i][j]*cgs2ses_e );
      if(++count%4) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
    }

  fclose(h);
```

`.304` 见 `FE-01_TABTOOLS.C:672-744`（用 `Pe, Ee, Fe`，头部 `" %04d0304      "`）；
`.305` 见 `FE-01_TABTOOLS.C:748-820`（用 `Pi, Ei, Fi`，头部 `" %04d0305      "`）。

### 3.2 实测两种实物

**（A）FEOS 16.7 原生输出 —— 4 × 15 = 60 字符：**

```
mat_Al-1.0/FEOS/Al.feos.301
  line 0 len=60 : ' 37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01'
  line 1 len=60 : ' 0.00000000e+00 2.70000000e-06 5.81697366e-06 1.25322899e-05'
按 15 切分 line1 -> [' 0.00000000e+00',' 2.70000000e-06',' 5.81697366e-06',' 1.25322899e-05']   ← 4 个
行宽直方图: {60 字符: 10002 行, 15 字符: 1 行}
```

**（B）旧 MPQeos v2.0 遗留输出 —— 4 × 16 = 64 字符：**

```
mat_Au-1.0/Au.301
  line 0 len=64 : '  1111           1.92800000e+001 1.23000000e+002 1.01000000e+002'
  line 1 len=64 : ' 0.00000000e+000 1.92800000e-004 3.42852270e-004 6.09687133e-004'
按 16 切分 line1 -> [' 0.00000000e+000',' 1.92800000e-004',' 3.42852270e-004',' 6.09687133e-004']  ← 4 个
行宽直方图: {64 字符: 9374 行, 16 字符: 1 行}
```

注意 (B) 的指数是 **3 位**（`e+001`），需要 16 字符才能容纳；FEOS 16.7 的 `%15.8le` 产生 **2 位指数**（`e+00`），15 字符足够。**这正是 15 vs 16 差异的物理原因。**

### 3.3 ASCII / 二进制判定（全库统计）

| 扩展名 | 文件数 | 含 >127 字节者 | 判定 |
|---|---|---|---|
| `.301` | 28 | **0** | 纯 ASCII 文本 |
| `.304` | 27 | **0** | 纯 ASCII 文本 |
| `.305` | 27 | **0** | 纯 ASCII 文本 |
| `.mexport` | 23 | **0** | 纯 ASCII 文本 |
| `.cst` | 24 | 23（仅德文 `Moleküldichte` 的 `ü`） | 文本（UTF-8） |

**结论：`.301/.304/.305` 全部为纯 ASCII 文本，绝无二进制/16 字节记录。**
- **每行字段数 = 4**（首行是 `%04d0301` + 8 空格 + 3 个 15 字符字段，视觉上凑成「4 个字块」）。
- **字段宽度 = 15 字符**（FEOS 16.7）；旧 MPQeos 为 **16 字符**。

### 3.4 单位换算常量（回答「单位」）

```c
// COMMON-00_DEFINITS.H:62-67
// SESAME:
const double
  cgs2ses_t   = 1.0/t_kelvin,
  cgs2ses_rho = 1.0,
  cgs2ses_p   = 1.0e-10,               // cgs units used in QEOS --- > SESAME units
  cgs2ses_e   = 1.0e-10;
```

配合 `COMMON-00_DEFINITS.H:56` 的 `t_kelvin = 8.617383848e-5`（eV/K）：
- `cgs2ses_t = 1/8.617383848e-5 = 11604.5` → **eV → K**
- `cgs2ses_p = 1e-10` → **dyne/cm² → GPa**（1 dyne/cm² = 1e-10 GPa）
- `cgs2ses_e = 1e-10` → **erg/g → MJ/kg**（1 erg/g = 1e-10 MJ/kg = 1e-4 J/g）
- `cgs2ses_rho = 1.0` → g/cm³ 数值不变（SESAME 语义为 Mg/m³，数值等同）

---

## 4. Q3 —— SHOWEOS 的 6 个输出后缀

### 4.1 后缀常量定义

```c
// SE-00_DEFINITS.H:23-45
#define KEY_ISOUNITS       "IsoUnits"
#define KEY_OFFSET         "OffsetFlag"
#define KEY_ORIGINAL       "OriginalFlag"
#define KEY_VOLUME         "VolumeFlag"
#define KEY_NUMBER         "Number"
#define KEY_MOUNTAIN       "Mountain"
#define ISOTHERM_SUFFIX    "ist"
#define ISOCHORE_SUFFIX    "isc"
#define MOUNTAIN_SUFFIX    "mnt"
#define ISENTROPE_SUFFIX   "ise"
#define HUG_SUFFIX         "hug"
#define DENSITY_SUFFIX     "Rho"
#define VOLUME_SUFFIX      "V"
#define TEMPERATURE_SUFFIX "T"
#define CHARGE_SUFFIX      "Q"
#define PRESSURE_SUFFIX    "P"
#define ENERGY_SUFFIX      "E"
#define ENTROPY_SUFFIX     "S"
#define FREE_ENERGY_SUFFIX "F"
#define VELOCITY_SUFFIX    "U"
#define ELECTRON_SUFFIX    "e"
#define ION_SUFFIX         "i"
#define TF_SUFFIX          "TF"
```

### 4.2 选项 → 后缀 → 文件名 → 首行注释

```c
// SE-04_MAIN.C:98-106
  switch( type_in ) {
    case 1 : Isotherms( &qtable, name_in, &units, fileformat, eostype ); break;
    case 2 : Isochores( &qtable, name_in, &units, fileformat, eostype ); break;
    case 3 : Isentropes( &qtable, name_in, &units, fileformat, eostype ); break;
    case 4 : Mountain( &qtable, name_in, &units, fileformat, eostype ); break;
    case 5 : Hugoniot( &qtable, name_in, &units, fileformat, eostype ); break;
    case 6 : SinglePoint( &qtable, argv[3], argv[4], &units, fileformat, eostype ); break;
    default : printf( "\nSE-ERROR in main ---> Unexpected error !!!\n" ); exit(0); 
  }
```

| 选项 | 功能 | 后缀常量 | 后缀字符串 | 文件名模板 | 首行注释确切文字 |
|---|---|---|---|---|---|
| 1 | Isotherms（等温线） | `ISOTHERM_SUFFIX` | `"ist"` | `%s.%s.%s` = `<file>.<Xname>-<Yname>.ist` | `# T = %e [%e eV]:` |
| 2 | Isochores（等密度线） | `ISOCHORE_SUFFIX` | **`"isc"`** | `<file>.<Xname>-<Yname>.isc` | `# Rho = %e [%e g/cm^3]:` |
| 3 | Isentropes（等熵线） | `ISENTROPE_SUFFIX` | `"ise"` | `<file>.<Xname>-<Yname>.ise` | `# S = %e [%e erg/(g*eV)]:` |
| 4 | Mountain | `MOUNTAIN_SUFFIX` | `"mnt"` | `<file>.<Xname>-<T>-<Zname>.mnt` | `# N<X>  NT  N<Z>` |
| 5 | Hugoniot | `HUG_SUFFIX` | `"hug"` | `<file>.hug` | `# <X> <Xunit>  T <Tunit>  P <Punit>  E <Eunit>  Us <Uunit>  Up <Uunit>` |
| 6 | SinglePoint | — | **无** | **不落盘**（仅 stdout） | — |

**逐条源码原文：**

**（1）Isotherms —— `SE-03_SERVICES.C:347-357`**
```c
  // Calculate and write isotherms:
  sprintf(suffix,"%s-%s", Xname, Yname);
  sprintf(name,"%s.%s.%s", file, suffix, ISOTHERM_SUFFIX);
  h = fopen(name,"w");
  printf(" Processing temperature [%e eV]:\n ", Tunit);
  for( l = 0; l<= Tnumber-1; l++ )
  {
    T = temperatures[l];
    printf(" %e", T/Tunit);
    fflush( stdout );   
    fprintf( h, "# T = %e [%e eV]:\n", T/Tunit, Tunit );
    fprintf( h, "# %s %s  %s %s\n", Xname, Xunitname, Yname, Yunitname );
```
块间分隔符：`if(l<(Tnumber-1)) fprintf(h, "&\n" );`（`:364`），文件末 `fprintf( h, "# eof." );`（`:369`）

**（2）Isochores —— `SE-03_SERVICES.C:422-433`**
```c
  // Calculate and write isochores:
  sprintf(suffix,"%s-%s", Xname, Yname);
  sprintf(name,"%s.%s.%s", file, suffix, ISOCHORE_SUFFIX);
  h = fopen(name,"w");
  printf(" Processing density [%e g/cm^3]:\n ", Runit);
  for( l = 0; l<= Rnumber-1; l++ )
  {
    R = densities[l];
    printf(" %e", R/Runit);
    fflush( stdout );   
    fprintf( h, "# Rho = %e [%e g/cm^3]:\n", R/Runit, Runit );
    fprintf( h, "# %s %s  %s %s\n", Xname, Xunitname, Yname, Yunitname );
```

**（3）Isentropes —— `SE-03_SERVICES.C:500-513`**
```c
  // Calculate and write isentropes:
  sprintf(suffix,"%s-%s", Xname, Yname);
  sprintf(name,"%s.%s.%s", file, suffix, ISENTROPE_SUFFIX);
  h = fopen(name,"w");  
  printf(" Processing entropy [%e erg/(g*eV)]:\n ", Sunit);
  fulldens = true;
  for( l = 0; l<= Tnumber-1; l++ )
  {
    T = temperatures[l];
    R = densities[0];
    S = GetQuantity( 7, qtab, R, T, 0, eostype, units );
    printf(" %e", S/Sunit);
    fflush( stdout );   
    fprintf( h, "# S = %e [%e erg/(g*eV)]:\n", S/Sunit, Sunit );
    fprintf( h, "# %s %s  %s %s\n", Xname, Xunitname, Yname, Yunitname );
```

**（4）Mountain —— `SE-03_SERVICES.C:609-624`**
```c
  // Calculate and write mountain data:
  sprintf(suffix,"%s-%s-%s", Xname, Tname, Zname);
  sprintf(name,"%s.%s.%s", file, suffix, MOUNTAIN_SUFFIX);
  h = fopen(name,"w");  
  printf(" Table size (densities x temperatures): %d x %d\n", Rnumber, Tnumber );
  printf(" Processing table...");
  fflush( stdout );   
  fprintf( h, "# N%s  NT  N%s\n", Xname, Zname );  
  fprintf( h, "%d  %d  %d\n", Rnumber, Tnumber, Rnumber*Tnumber );
  fprintf(h, "&\n" );    
  fprintf( h, "# %s %s\n", Xname, Xunitname );
  for( l = 0; l<= Rnumber-1; l++ ) fprintf( h, "%e\n", (GetQuantity( Xquantity, qtab, densities[l], 0.0, 0, eostype, units )) / Xunit );
  fprintf(h, "&\n" );
  fprintf( h, "# %s %s\n", Tname, Tunitname );
  for( i = 0; i<= Tnumber-1; i++ ) fprintf( h, "%e\n", temperatures[i] / Tunit );
  fprintf(h, "&\n" );
  fprintf( h, "# %s %s\n", Zname, Zunitname );
```
`.mnt` 是**三块 `&` 分隔**（X 轴、T 轴、Z 值体按 i 外层/j 内层的长列）。

**（5）Hugoniot —— `SE-03_SERVICES.C:702-712`**
```c
  // Calculate and write Hugoniot curve:
  sprintf(name,"%s.%s", file, HUG_SUFFIX );
  h = fopen(name,"w");
  printf(" Processing Hugoniot...");
  fflush( stdout );  
  fprintf( h, "# %s %s  %s %s  %s %s  %s %s  %s %s  %s %s\n", 
           Xname, Xunitname, Tname, Tunitname, Pname, Punitname, 
           Ename, Eunitname, Uname1, Uunitname1, Uname2, Uunitname2 );         
  fprintf( h, "%e  %e  %e  %e  %e  %e\n", 
           (GetQuantity( Xquantity, qtab, R0, 0.0, 0, eostype, units ) / Xunit),
           T0/(*units).T, P0/(*units).P, E0/(*units).E, 0.0, 0.0 );
```

**（6）SinglePoint —— `SE-03_SERVICES.C:753-796`：只有 `printf`，无 `fopen`/`fprintf`。确认不产出文件。**

### 4.3 `*4gnuplot` 后缀如何拼上去？

**`4gnuplot` 在 FEOS 16.7 源码中未找到**（在 18 个 `.C` + 18 个 `.H` 中检索 `4gnuplot`/`gnuplot` 均为 0 命中；官方 96KB 文档 `FEOS-Package-Documentation.txt` 中亦为 0 命中）。官方文档只列出 `.ist/.isc/.ise/.mnt/.hug`。

**实测证实它是后处理产物：**

```
Al.feos.Rho-P.ist  (1802 B, 56 行)          Al.feos.Rho-P.ist4gnuplot  (2133 B, 49 行)
line 0: '# T = 0.000000e+000 [1.000000e+000 eV]:'   line 0: '# T[1.000000e+000 eV]\tRho[1.000000e+000 g/cm^3]\tP.ist4gnuplot[1.000000e+000e+012 dyne/cm^2]'  ← 制表符分隔
line 1: '# Rho [1.000000e+000 g/cm^3]  P.ist [..]'   line 1: '0.000000e+000\t1.000000e-003\t3.550148e-056'
line 2: '1.000000e-003  3.550148e-056'               line 2: '0.000000e+000\t2.500750e+000\t3.550148e-056'
块分隔 ('&'): 6 处                                    块分隔（空行）: 7 处
```

**转换规则（由数据比对推出）：**
1. 把 `.ist` 每块的 2 列 `(X, Y)` 中，把该块的**自变量 T 作为第 1 列重复铺满**（因 `.ist4gnuplot` 第 1 列恒为常数 `0.000000e+000`）；
2. 列头改为 `# T[<Tunit>]\t<X>[<Xunit>]\t<Y>.<suffix>4gnuplot[<Yunit>]`（用 TAB 分隔）；
3. 块间 `&` 换成**空行**；
4. Y 列头被错误地拼接成 `P.ist4gnuplot` —— 这暴露了生成器是**按 `"<Yname>.<suffix>4gnuplot"` 拼字符串**的。

> **结论：`4gnuplot` 文件由 Multi1D++ 侧（或某个外部小工具）对 FEOS 输出的 `.ist/.isc/.ise/.mnt` 做「T 提升为第 1 列 + TAB 分隔」重排得到，不经 FEOS 16.7。** 其 Y 列头 `P.ist4gnuplot` 是拼接 bug 的表现（本应是 `P`）。
> **置信度：数据关系「高」；生产者身份「源码中未找到」→ 推断。**

### 4.4 `.hug` 各列语义与单位

**列头由 `GetQuantityName`/`GetUnitsName` 动态生成**（`SE-03_SERVICES.C:677-687`）：

```c
  // Get quantity names:
  GetUnitsName( Tunitname, 3, 0, units );
  GetQuantityName( Tname, 3, 0, eostype );
  GetUnitsName( Punitname, 4, 0, units );
  GetQuantityName( Pname, 4, 0, eostype );
  GetUnitsName( Eunitname, 5, 0, units );
  GetQuantityName( Ename, 5, 0, eostype );
  GetUnitsName( Uunitname1, 9, 0, units );
  GetQuantityName( Uname1, 9, 0, eostype );
  GetUnitsName( Uunitname2, 10, 0, units );
  GetQuantityName( Uname2, 10, 0, eostype );
```

而 `GetQuantityName` 对 9/10 号量的定义（`SE-03_SERVICES.C:120-121`）：
```c
  case 9 : sprintf(name,"%s%s", VELOCITY_SUFFIX, "s"); break;
  case 10 : sprintf(name,"%s%s", VELOCITY_SUFFIX, "p"); break;
```
`VELOCITY_SUFFIX = "U"` → 量名 `"Us"` 与 `"Up"`。单位名（`SE-03_SERVICES.C:206-207`）：
```c
  case 9 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "cm/s"); break;
  case 10 : sprintf(name,"[%e %s]", GetUnits( qn, units ), "cm/s"); break;
```

**实测首行（`mat_Al-1.0/Al.feos.hug`，155 字符）：**
```
# Rho [1.000000e+000 g/cm^3]  T [1.000000e+000 eV]  P [1.000000e+012 dyne/cm^2]  E [1.000000e+000 erg/g]  Us [1.000000e+005 cm/s]  Up [1.000000e+005 cm/s]
```

**逐列语义表（6 列，源码顺序即文件列序）：**

| 列 | 名称 | 语义 | 内部单位 | 样例单位乘子 | 样例单位 | 有效数字 |
|---|---|---|---|---|---|---|
| 1 | **Rho** | 冲击后**密度**（或比容，取决于 `Xquantity`=1/2） | cgs `g/cm³` | `Rho_unit` = 1.0 | g/cm³ | `%e` |
| 2 | **T** | 冲击后**温度** | cgs `eV` | `T_unit` = 1.0 | eV | `%e` |
| 3 | **P** | 冲击后**压力** | cgs `dyne/cm²` | `P_unit` = 1e12 | dyne/cm² | `%e` |
| 4 | **E** | 冲击后**比内能** | cgs `erg/g` | `E_unit` = 1.0 | erg/g | `%e` |
| 5 | **Us** | **冲击波速度** | cgs `cm/s` | `U_unit` = 1e5 | km/s | `%e` |
| 6 | **Up** | **粒子速度** | cgs `cm/s` | `U_unit` = 1e5 | km/s | `%e` |

**Us/Up 的物理公式（源码原文 `SE-03_SERVICES.C:728-729`）：**
```c
    Us = (1.0/R0)*sqrt( (P-P0)/(1.0/R0 - 1.0/R));
    Up = fabs(1.0- R0/R)*Us; 
```
即质量守恒 + 雨贡纽关系的标准形式：`Us = sqrt((P-P0)/(ρ0^{-1} - ρ^{-1})/ρ0)`，`Up = |1-ρ0/ρ|·Us`。

首行数据为**起始点**（`SE-03_SERVICES.C:710-712`），Us/Up 置 0：
```
2.700000e+000  2.585257e-002  2.578641e-004  1.041546e+005  0.000000e+000  0.000000e+000
```

**`.hug` 输出的是「筛选后的步点」而非全部积分步**（`:730-736`）：
```c
    if (P>0.0 && fabs(P/P_alt) > P_MULT_HUG)     // don't save all steps
    {
      fprintf(h,"%e  %e  %e  %e  %e  %e\n", 
      	      (GetQuantity( Xquantity, qtab, R, 0.0, 0, eostype, units ) / Xunit),
              T/(*units).T,P/((*units).P),E/(*units).E,Us/(*units).U,Up/(*units).U ); 
      P_alt = P;
    }
```

---

## 5. Q4 —— `.mexport`

### 5.1 写入代码（`FE-01_TABTOOLS.C:370-428, 577`）

```c
// FE-01_TABTOOLS.C:370-428（节选）
void write_mexport_format( char* name_in, Qtable* table)
{
  // SESAME mexport format
  // indices start at 0
  //
  // with Pressure, Energy, Free Energy
  //
  // SESAME units are
  //
  // Pressure in GPa
  // energy in MJ/kg
  // density Mg/m3
  // temperature in Kelvin
  //

  double rhosolid = (*table).RhoRef;
  double Amat = (*table).Atot/(*table).Xtot;
  double Zmat = (*table).Ztot/(*table).Xtot;
  double Bulkmat = (*table).BulkModulusRef;
  int matnumber = (*table).SESAMEnumber;
  
  time_t current;
  struct tm *timeptr;
  
   current = time(NULL);
   timeptr = localtime(&current);

  int i,j,count,
    NR = (*table).NRho-1,
    NT = (*table).NT-1;
  FILE* h;
  char name[STRSIZE];
  char linea[81];
  char control[6]="00000";
  //
  sprintf( name,"%s.%s",name_in,"mexport" );
  printf( "\nWrite SESAME mexport table format (%s):\n", name );
  if ((h = fopen(name,"w")) == NULL) {
    printf("\nFE-ERROR in write_mexport_format ---> Error occured while opening file !!!\n");
    exit(0);
  }

  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",0,matnumber,101,160,0,0,1,1);
  sprintf(linea,"material. %s (Zmean=%.1f, Amean=%.2f) /source. feos /date %04d%02d%02d%02d%02d",name_in,Zmat,Amat,timeptr->tm_year + 1900, timeptr->tm_mon+1, timeptr->tm_mday,timeptr->tm_hour,timeptr->tm_min);
  fprintf(h,"%s",linea);
  for (int i=strlen(linea);i<80;i++) fprintf(h," ");
  fprintf(h,"\n");
  sprintf(linea,"/refs. none /comp. LULI /codes. FEOS /");
  fprintf(h,"%s",linea);
  for (int i=strlen(linea);i<80;i++) fprintf(h," ");
  fprintf(h,"\n");
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,102,80,0,0,1,1);
  sprintf(linea,"contact: tommaso.vinci@polytechnique.edu");
  fprintf(h,"%s",linea);
  for (int i=strlen(linea);i<80;i++) fprintf(h," ");
  fprintf(h,"\n");
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,201,5,0,0,1,1);
  fprintf(h,"%15.8le%15.8le%15.8le%15.8le%15.8le11100\n",Zmat,Amat,rhosolid,Bulkmat/1.e10,0.);


  //  
  //  Writing Total EOS 301 
  //  
  fprintf(h,"%2d%6d%6d%6d   r%9d%9d%4d%34d\n",1,matnumber,301,2+(NR+1)+(NT+1)+3*(NR+1)*(NT+1),0,0,1,1);
  fprintf(h,"%15.8le%15.8le",double(NR+1),double(NT+1));
```

尾行（`FE-01_TABTOOLS.C:577`）：
```c
  fprintf(h," 2                                                                             2\n");
```

### 5.2 格式判定与结构还原

- **类型：SESAME「mexport」ASCII 数据库格式**（官方文档 §16.3 明确："the routine `write mexport format(...)` writes the SESAME mexport format (extension `.mexport`). The mexport format is a database file which usually contains all the EOS tables (301,...) of all materials from the SESAME database. In the case of the FEOS table generation tool the mexport file of course contains only the 301, 304, and 305 tables of the calculated material."）。
- **多材料？否 —— 单材料。** 文件头只有材料 `SESAMEnumber`，不含材料库循环。`FE-03_MAIN.C:321` 只调用一次 `write_mexport_format( name_in, &qtable );`。
- **表号来源：`(*table).SESAMEnumber` 直接来自材料参数库的 `[NNNN]_SESAME-Number`**，经 `FEOS_Get_Mat_Par`（`FE-03_MAIN.C:160-161`）填充。
- **`matnumber` 是 `.par` 的 `Material-Number`，`SESAMEnumber` 是材料库的 SESAME 号**，二者在样例中相同（如 B: 104005 / Al: 3717）。

**实测记录结构（`mat_B/B.mexport`，22,508 行，每行严格 80 字符）：**

| 行号 | 记录 | 内容 |
|---|---|---|
| 0 | `0104005   101   160   r        0        0   1                                 1` | 文件级头，表 101，160 条记录 |
| 1 | `material. B (Zmean=5.0, Amean=10.81) /source. feos /date 202106191914`（补空格至 80） | 材料描述 |
| 2 | `/refs. none /comp. LULI /codes. FEOS /`（补空格至 80） | 引用/代码 |
| 3 | `1104005   102    80   r ...` | 表 102（注释表） |
| 4 | `contact: tommaso.vinci@polytechnique.edu` | 联系人 |
| 5 | `1104005   201     5   r ...` | 表 201（材料参数，5 条） |
| 6 | ` 5.00000000e+00 1.08110000e+01 2.34000000e+00 1.85000000e+02 0.00000000e+00` + `11100` | `Zmat, Amat, ρ_solid, B/1e10, 0` + 5 字符控制列 |
| 7 | `1104005   301 37495   r ...` | 表 301（总 EOS），37,495 条 |
| 7507 | `1104005   304 37495   r ...` | 表 304（电子 EOS） |
| 15007 | `1104005   305 37495   r ...` | 表 305（离子 EOS） |
| 22507 | ` 2` … 补空格 … `2` | 文件尾 |

**301/304/305 的记录条数验证：** `2 + (NR+1) + (NT+1) + 3*(NR+1)*(NT+1)` = `2 + 123 + 101 + 3*12423` = 37,495 ✓（与 B 的 `NRho=123, NT=101` 吻合）

**每行 = 5 个 15 字符数值 + 5 字符控制列 = 80 字符（视觉 5×16）。**
控制列语义（源码 `:439-449`）：前 2 位表示 `ρ`/`T` 向量非零性，之后每 5 个数值更新一次 —— `1`=非零，`0`=零。样例 `11100`、`11011`、`11111` 与源码 `if (v==0.) control[count%5]='0'; else control[count%5]='1';` 一致。

> **⚠ 注意一个潜在 bug（源码级）**：`.304`/`.305` 段的**自由能位置写的是总 EOS 的 `F`**，而非对应的 `Fe`/`Fi`：
> ```c
> // FE-01_TABTOOLS.C:516 (304 段) 与 :564 (305 段)，两处均为：
>       fprintf(h,"%15.8le", (*table).F[i][j]*cgs2ses_e );
> ```
> 而独立的 `.304`/`.305` 写入器正确使用了 `Fe`/`Fi`（`:730`、`:806`）。这是 `.mexport` 内的一个不一致点。**置信度：高（源码原文）**。

---

## 6. Q5 & Q6 —— `.cst` / `.critical.dat` / `.isobaric.dat`

### 6.1 `.cst`（Rostock format）

**常量：**
```c
// COMMON-00_DEFINITS.H:26
#define ROSTOCK_SUFFIX "cst"
```

**写入代码（`FE-01_TABTOOLS.C:883-907`）—— 全文：**
```c
void write_Rostock_format(  char* name_in, Qtable* table)
{ 
  // write isotherms : charge state and pressure vs density
  
  FILE* h;
  int NR = (*table).NRho-1,
    NT = (*table).NT-1,
    i,j;
  char name[STRSIZE];
  sprintf( name, "%s.%s", name_in, ROSTOCK_SUFFIX );
  printf( "\nWrite charge state table / Rostock format (%s)...",name );
  h = fopen( name, "w" );
  for(j=0;j<=NT;j++) {
    fprintf( h, "Isotherme T = %.0f Kelvin \n", (*table).T[j]*eV2Kelvin );
    fprintf( h, "Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand\n" );
    for(i=0;i<=NR;i++) {
      fprintf( h,"%e          %e          %e    %e\n", 
	       (*table).Rho[i]/((*table).Atot*M_proton), (*table).Rho[i],
	       (*table).P[i][j]*cgs2MBar, (*table).Qtot[i][j] );
    }
  }
  fclose( h);
  printf(" done.\n" );
  return;
}
```

**格式判定：纯 ASCII/文本（严格说是 UTF-8，因德文 `Moleküldichte` 的 `ü` 为 2 字节）。100% 不是二进制。**
（全库 24 个 `.cst` 中 23 个含 >127 字节，全部来自该德语表头。）

**逐列语义与单位表（4 列，每一条等温线重复一次表头）：**

| 列 | 表头（德文原文） | 中文 | 公式（源码） | 单位 | 换算常量 |
|---|---|---|---|---|---|
| 1 | `Moleküldichte[1/cm^3]` | **分子数密度** | `ρ / (A_tot · m_p)` | `1/cm³` | `M_proton = 1.6726231e-24 g`（`COMMON-00_DEFINITS.H:57`） |
| 2 | `Massendichte[g/cm^3]` | **质量密度** | `ρ` 原值 | `g/cm³` | — |
| 3 | `Druck[MBar]` | **压力** | `P · cgs2MBar` | `MBar`（兆巴） | `cgs2MBar = 1.0e-12`（`:60`） |
| 4 | `Ladungszustand` | **电荷态**（平均电离度） | `Qtot[i][j]` | 电子电荷倍数 | — |

**分区结构：** 外层 `for j`（每条等温线），每块首行 `Isotherme T = %.0f Kelvin`（**T 已换算为开尔文**，`eV2Kelvin = 1/t_kelvin ≈ 11604.5`），次行德文表头，随后 `NR+1` 行数据（密度递增）。

**实测（`mat_B/B.cst`，12,626 行，101 个 `Isotherme` 块 + 101 个表头）：**
```
line 0: 'Isotherme T = 0 Kelvin '
line 1: 'Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand'
line 2: '0.000000e+00          0.000000e+00          3.537120e-55    2.992190e+00'
line 3: '1.294053e+18          2.340000e-05          3.537120e-55    1.780794e+00'
```
（`101 块 × (2 头 + 123 数据) + 1 = 12626` ✓）

**它是哪个物理量组合：** 它是 **T–ρ 网格上的等温线族**，每条等温线给出 `(n, ρ, P, Z̄)` 四元组。即 **T–ρ 平面**上的「分子数密度 + 质量密度 + 压力 + 平均电荷态」组合；`n` 与 `ρ` 是一一对应的冗余表达（因为 `n = ρ/(A·m_p)`）。

### 6.2 `.critical.dat`

**常量与写入代码头：**
```c
// FE-00_DEFINITS.H:26
#define CRITICAL_SUFFIX "critical.dat"

// FE-01_TABTOOLS.C:58-91（节选）
void write_criticaldata( char* name_in, CriticalDataTable* ctable, int MaxwellFlag, double Atot, double Xtot )
{ 
  // write binodal, spinodal, boiling- and cp-data to .critical.dat file
  
  FILE* h;
  int j,i;
  double Amean = Atot/Xtot;
  char name[STRSIZE];
  sprintf( name, "%s.%s", name_in, CRITICAL_SUFFIX );
  printf( "\nWrite critical data table (%s)...",name );
  h = fopen( name, "w" );
  fprintf( h, "# Critical point: Tc = %.2f K, Pc = %.2f bar, Rhoc = %.4f g/cm³,\n", 
	   (*ctable).Tc*eV2Kelvin, (*ctable).Pc*cgs2Bar, (*ctable).Rhoc );
  fprintf( h, "#                 Hc = %.2f kJ/g, Sc/R = %.4f, Zc = %.2f\n\n", 
	   (*ctable).Hc*cgs2Joule*1.0e-3, (*ctable).Sc*Amean/GAS_CONSTANT, (*ctable).Zc );
  if(MaxwellFlag==2) 
    fprintf( h, "# Two-phase-boundary (binodal) calculated by finding equal areas under/over pressure-loops! \n\n" ); 
  else 
    fprintf( h, "# Two-phase-boundary (binodal) calculated by finding densities with equal pressure and Gibbs free energy! \n\n" );
  if((*ctable).Tb) fprintf( h, "# Boiling temperature: Tb = %.2f K \n\n", (*ctable).Tb*eV2Kelvin );
  else fprintf( h, "# Boiling temperature could not be calculated! \n\n" );

  fprintf( h, "# Number of calculated isotherms below cp: Niso = %d \n\n", (*ctable).Niso );
```

**14 个分段，逐段给出「表头原文 + 列语义 + 单位」（源码 `FE-01_TABTOOLS.C:58-192`）：**

| # | 段标题（原文） | 列头原文 | 列语义与单位 | 源码行 |
|---|---|---|---|---|
| 0 | （文件头） | `# Critical point: Tc = ... K, Pc = ... bar, Rhoc = ... g/cm³,`<br>`#   Hc = ... kJ/g, Sc/R = ..., Zc = ...` | `Tc`[K], `Pc`[bar], `Rhoc`[g/cm³], `Hc`[kJ/g], `Sc/R`[无量纲], `Zc`[无量纲] | `:69-72` |
| 1 | （说明 2 行） | `# Two-phase-boundary (binodal) calculated by ...` / `# Boiling temperature: Tb = ... K` | 方法说明 + `Tb`[K] | `:73-78` |
| 2 | （Niso + T 列表） | `# Number of calculated isotherms below cp: Niso = %d` / `# Temperatures in Kelvin:` | 低于临界点的等温线数 + 温度清单（每行 6 个） | `:80-88` |
| 3 | `# Check P_sat = P_vap = P_liq and G_vap = G_liq for good accuracy of binodal:` | `# T [Kelvin]  Rho_vap [g/cm³]  Rho_liq [g/cm³]  P_sat [bar]  P_vap [bar]  P_liq [bar]  G_vap [kJ/g]  G_liq [kJ/g]` | 8 列：T, ρ_vap, ρ_liq, P_sat, P_vap, P_liq, G_vap, G_liq | `:90-95` |
| 4 | `# Binodal in Rho-P-plane` | `# Rho [g/cm³]  P_sat [bar]` | 双结点 ρ–P：先气相支、临界点、再液相支（逆序） | `:97-105` |
| 5 | `# Spinodal in Rho-P-plane` | `# Rho [g/cm³]  P_sat [bar]` | 旋节线 ρ–P（用 `Rhomax/Pmax` 与 `Rhomin/Pmin`） | `:107-115` |
| 6 | `# Binodal in T-Rho-plane` | `# T [Kelvin]  Rho [g/cm³]` | 双结点 T–ρ | `:117-125` |
| 7 | `# Spinodal in T-Rho-plane` | `# T [Kelvin]  Rho [g/cm³]` | 旋节线 T–ρ | `:127-135` |
| 8 | `# Diamener curve in T-Rho-plane` | `# T [Kelvin]  1/2*Rho_liq+1/2*Rho_vap [g/cm³]` | **直径线**（源码拼写为 "Diamener"，实为 "diameter" 的笔误） | `:137-142` |
| 9 | `# Binodal in T-H-plane` | `# T [Kelvin]  H [kJ/g]` | 双结点 T–H（比焓） | `:144-152` |
| 10 | `# Evaporation heat in T-DeltaH-plane` | `# T [Kelvin]  DeltaH [kJ/g]` | **蒸发潜热** ΔH = Hv−Hl | `:154-159` |
| 11 | `# Saturation curve in Arrhenius coordinates` | `# 1/T [T in Kelvin]  log10(P_sat) [P_sat in bar]` | Arrhenius 坐标（横轴 1/T，纵轴 log10 P_sat） | `:161-166` |
| 12 | `# Compressibility factor in T-Z-plane` | `# T [Kelvin]  Z` | 压缩因子 Z(T) | `:168-176` |
| 13 | `# Compressibility factor in P-Z-plane` | `# P_sat [bar]  Z` | 压缩因子 Z(P_sat) | `:178-186` |

文件末：`fprintf( h, "# eof.\n" );`（`:188`）

**实测分段位置（`mat_B/B.critical.dat`，1616 行）与上表完全一致：**
```
行 0/1   临界点；行 3 binodal 方法；行 5 沸点；行 7 Niso=86
行 26    Check P_sat...
行 115   Binodal in Rho-P-plane          行 291   Spinodal in Rho-P-plane
行 467   Binodal in T-Rho-plane          行 643   Spinodal in T-Rho-plane
行 819   Diamener curve in T-Rho-plane   行 909   Binodal in T-H-plane
行 1085  Evaporation heat in T-DeltaH    行 1175  Saturation curve (Arrhenius)
行 1264  Compressibility T-Z             行 1440  Compressibility P-Z
行 1615  # eof.
```

**触发条件（`FE-03_MAIN.C:319`）：** 仅当 `ctable.Niso > 0`（即材料初始化时启用了 Maxwell 构造）时才写出 —— `if(ctable.Niso > 0) write_criticaldata(name_in, &ctable, MaxwellFlag, qtable.Atot, qtable.Xtot);`

### 6.3 `.isobaric.dat`

**常量：**
```c
// FE-00_DEFINITS.H:27
#define ISOBARIC_SUFFIX "isobaric.dat"
```

**写入代码（`FE-02_CALCULATIONS.C:181-218`）—— 全文：**
```c
void write_isobaricdata( char* name_in, IsobaricExpansionTable* data )
{ 
  // write isobaric expansion data to .isobaric.dat file
  
  FILE* h;
  int j;
  char name[STRSIZE];
  sprintf( name, "%s.%s", name_in, ISOBARIC_SUFFIX );
  printf( "\nWrite isobaric expansion data (%s)...",name );
  h = fopen( name, "w" );
  fprintf( h, "# Calculated isobaric expansion data (P ~= 0) from %.2f to %.2f Kelvin:\n", 
	   (*data).MinT*eV2Kelvin, (*data).MaxT*eV2Kelvin );
  fprintf( h, "# T [K]       Rho [g/cm^3]  P [bar]        Alpha [1/K]    H [J/g]        Cp [J/gK]\n" );
  for(j=0;j<(*data).Niso;j++) {
    if(j==(*data).Niso-1 && (*data).alpha[j]==0.0 && (*data).Cp[j]==0.0 && (*data).H[j]==0.0)
	    fprintf( h, "%e  %e  %+e       ---            ---            ---\n",
	    (*data).Tiso[j]*eV2Kelvin,(*data).Rho0[j],(*data).P[j]*cgs2Bar );
    else fprintf( h, "%e  %e  %+e  %+e  %+e  %+e\n",
	    (*data).Tiso[j]*eV2Kelvin,(*data).Rho0[j],(*data).P[j]*cgs2Bar,
	    (*data).alpha[j]/eV2Kelvin,(*data).H[j]*cgs2Joule,(*data).Cp[j]*cgs2Joule/eV2Kelvin );
  }
  fprintf( h, "\n# Data in T-Rho-plane" );
  fprintf( h, "\n# T [Kelvin]  Rho [g/cm³]\n" );
  for(j=0;j<(*data).Niso;j++) {
    fprintf( h, "%e  %e\n", (*data).Tiso[j]*eV2Kelvin, (*data).Rho0[j] );
  }
  fprintf( h, "# eof.\n" );
  fclose( h);
  printf(" done.\n" );
  
  free_dvector( (*data).Tiso,0,(*data).NT-1 ); 
  free_dvector( (*data).Rho0,0,(*data).NT-1 );
  free_dvector( (*data).P,0,(*data).NT-1 );
  free_dvector( (*data).alpha,0,(*data).NT-1 );
  free_dvector( (*data).H,0,(*data).NT-1 );
  free_dvector( (*data).Cp,0,(*data).NT-1 );
  return;
}
```

**逐列语义与单位表（第 1 段，6 列）：**

| 列 | 表头原文 | 中文 | 源码表达式 | 单位 |
|---|---|---|---|---|
| 1 | `T [K]` | 温度 | `Tiso[j]·eV2Kelvin` | **K** |
| 2 | `Rho [g/cm^3]` | 密度（沿 P≈0） | `Rho0[j]` | **g/cm³** |
| 3 | `P [bar]` | 压力（用于校验精度） | `P[j]·cgs2Bar` | **bar** |
| 4 | `Alpha [1/K]` | 热膨胀系数 | `alpha[j]/eV2Kelvin` | **1/K** |
| 5 | `H [J/g]` | 比焓 | `H[j]·cgs2Joule` | **J/g** |
| 6 | `Cp [J/gK]` | 定压比热容 | `Cp[j]·cgs2Joule/eV2Kelvin` | **J/(g·K)** |

**第 2 段（缺列时用 `---` 占位）**：末点若 `α=Cp=H=0`，只写前 3 列，后 3 列打印字面量 `---`（`:195-197`）。
**第 3 段：** `# Data in T-Rho-plane` / `# T [Kelvin]  Rho [g/cm³]`，2 列。

**实测（`mat_B/B.isobaric.dat`，2664 B）：**
```
line 0: '# Calculated isobaric expansion data (P ~= 0) from 1.16 to 6000.00 Kelvin:'
line 1: '# T [K]       Rho [g/cm^3]  P [bar]        Alpha [1/K]    H [J/g]        Cp [J/gK]'
line 2: '1.160445e+00  2.346663e+00  -3.364498e-02  -0.000000e+00  -1.906063e+02  +4.648964e-05'
```

**触发条件（`FE-03_MAIN.C:329-333`）：** 仅当 `.par` 里 `UserCalculations_Flag = 1`：
```c
    // If UserCalculations_Flag is set on, perform used-defined calculations:
    if(UserCalculationsFlag) {
      printf("\n====================== Start user-defined calculations ======================\n");
      UserCalculations( entity, name_in, &qtable, &ctable );
```
而 `UserCalculations` 无条件调用 `write_isobaricdata`（`FE-02_CALCULATIONS.C:13-21`）。

**采样网格硬编码（`FE-02_CALCULATIONS.C:96-98`）：**
```c
  (*data).MaxT = 5.1704304e-1;      // eV  ≈ 6000 K
  (*data).MinT = (*qtable).Tcalclimit;
  (*data).NT = 21;                  // 21 个线性等距温度点
```

---

## 7. Q7 —— `.feos` 参数行逐字段语义

### 7.1 第 1 行（`FE-01_TABTOOLS.C:222-224`）

```c
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",FileVersion,SF_TRENN,double(NR+1),SF_TRENN,double(NT+1),SF_TRENN,double(Nelements+1),SF_TRENN,(*table).Tcalclimit);
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).Rhocalclimit,SF_TRENN,(*table).RhoRef,SF_TRENN,(*table).TRef,SF_TRENN,(*table).BulkModulusRef,SF_TRENN,double((*table).SESAMEnumber));
  fprintf(h,"\n");
```

| # | 源码表达式 | 类型 | 语义 | 单位 | Al 实测值 |
|---|---|---|---|---|---|
| 1 | `FileVersion`（硬编码 `12.06`） | double | **文件版本号** | — | `1.20600000e+01` |
| 2 | `double(NR+1)` | double | **密度点数 `NRho`**（表尺寸） | 无量纲 | `1.92000000e+02` = 192 |
| 3 | `double(NT+1)` | double | **温度点数 `NT`**（表尺寸） | 无量纲 | `6.90000000e+01` = 69 |
| 4 | `double(Nelements+1)` | double | **元素数 `Nelements`** | 无量纲 | `1.00000000e+00` = 1 |
| 5 | `Tcalclimit` | double | **库温度下限** | eV | `1.00000000e-04` |
| 6 | `Rhocalclimit` | double | **库密度下限** | g/cm³ | `1.00000000e-50` |
| 7 | `RhoRef` | double | **参考（固态）密度** | g/cm³ | `2.70000000e+00` |
| 8 | `TRef` | double | **参考温度** | eV | `2.58525700e-02`（= 300 K） |
| 9 | `BulkModulusRef` | double | **参考体积模量** | dyne/cm² | `7.50000000e+11` |
| 10 | `double(SESAMEnumber)` | int→double | **SESAME 材料号** | — | `3.71700000e+03` = 3717 |

> **对 team-lead 命名表的修正：**
> - 第 4 字段源码是 `Nelements+1`，但写出的值**就是 `Nelements`**（因为读者回填 `(*qtab).Nelements = int(d)`，见 `SE-01_READTABLE.C:36`）。**语义 = 元素个数**，不是「Nelements+1」。
> - 第 9 字段准确名 = `BulkModulusRef`（team-lead 写作 `BulkModulusRef`，正确）。
> - 第 5/6 字段 `Tcalclimit`/`Rhocalclimit` 取自 `FEOS_Get_Calc_Limits`（`FE-03_MAIN.C:101`）。

### 7.2 第 2 行（`FE-01_TABTOOLS.C:225-227`）

```c
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).ElectronOffset,SF_TRENN,(*table).IonOffset,SF_TRENN,(*table).Ecoh,SF_TRENN,(*table).softsphere_n,SF_TRENN,(*table).softsphere_m);
  fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",(*table).softsphere_A,SF_TRENN,(*table).softsphere_B,SF_TRENN,(*table).Atot,SF_TRENN,(*table).Ztot,SF_TRENN,(*table).Xtot);
  fprintf(h,"\n");
```

| # | 源码表达式 | 语义 | 单位 | Al 实测值 | 含义 |
|---|---|---|---|---|---|
| 11 | `ElectronOffset` | **电子能量零点偏移** | erg/g | `-2.94875001e+14` | 使 `Ee − Fe` 对齐的常数 |
| 12 | `IonOffset` | **离子能量零点偏移** | erg/g | `3.00821482e+09` | 同上 |
| 13 | `Ecoh` | **内聚能/升华焓** | erg/g | `1.21230000e+11` | 软球函数用 |
| 14 | `softsphere_n` | **软球函数指数 n** | — | `2.00000000e+00` | 源码用 `%15.8le`（**注意：声明为 double**） |
| 15 | `softsphere_m` | **软球函数指数 m** | — | `5.00000000e-01` | 同上 |
| 16 | `softsphere_A` | **软球函数参数 A** | erg/g | `5.27428129e+09` | |
| 17 | `softsphere_B` | **软球函数参数 B** | erg/g | `9.90197297e+10` | |
| 18 | `Atot` | **总原子量** `Σ X[k]·A[k]` | g/mol | `2.69815000e+01` | |
| 19 | `Ztot` | **总原子序数** `Σ X[k]·Z[k]` | — | `1.30000000e+01` | |
| 20 | `Xtot` | **总分子原子数** `Σ X[k]` | — | `1.00000000e+00` | |

> **重要提示**：`softsphere_n`/`softsphere_m` 在头文件里是 `double`（`COMMON-00_DEFINITS.H:101`），但在材料库中以整数形式给出（`Al.par` 写 `Soft-Sphere-m = 0.5`，`Soft-Sphere-n = 2.0`）。
> 另注：材料库注释里写「软球函数需指定 `Ecohesive`, `Soft-Sphere-m`, `Soft-Sphere-n`」（`FEOS_Material-DB.dat:22-24`），但 **`.feos` 参数行包含 4 个软球参数 `A/B/n/m`**，其中 `A/B` 由库侧 `FEOS_Get_SoftSphere_Par` 返回（`FE-03_MAIN.C:163-164`）。

### 7.3 为什么表尺寸是 `NR+1` / `NT+1`？—— **并非「强制补点」，而是「下标 vs 计数」的换算**

**源码证据链：**

1. `FE-03_MAIN.C:82,89` 读取密度/温度点数时，`getPointDensity` 直接写入 `qtable.NRho` / `qtable.NT`，且注释明说是**包含 `/ρ0`、`T0` 的总点数**：
```c
  getPointDensity(&rf, Rdensity, &(qtable.NRho), (char*)key_RR);
  printf(" Total number of density points (includes Rho0 = %.2e g/cm^3): %d\n", Rhostart, qtable.NRho);
  ...
  getPointDensity(&rf,Tdensity, &(qtable.NT), (char*)key_TR);
  printf(" Total number of temperature points (includes T0 = %.2e eV): %d\n", Tstart, qtable.NT);
```
而 `getPointDensity` 的 `*total` 从 **1** 起算（`FE-01_TABTOOLS.C:17`）：
```c
  *total = 1;
  for( c = -MAXRATIO; c <=MAXRATIO; c++ ) {
    sprintf( str, "%s%d",type_name,c);
    density[c+MAXRATIO] = atoi( (*rf).setget( (char*)"Q-table", str ) );
    *total += (density[c+MAXRATIO]);   // don't count overlapping points
```
→ **`NRho`/`NT` 已经是「计数」**（含第 0 点）。

2. `makeRTPointArray` 显式把 `array[0] = Qstart`（= 0.0）作为第 0 点（`FE-01_TABTOOLS.C:38`，`FE-03_MAIN.C:56` 设 `Rhostart = Tstart = 0.0`）：
```c
  array[0] = Qstart;
  q = pow(10.0, -MAXRATIO-1 ) * Qnorm;
```

3. `write_FEOS_format` 内部把 `NR = NRho-1` 当作**末下标**（`FE-01_TABTOOLS.C:208-210`），循环 `for(i=0;i<=NR;i++)` 共 `NRho` 次；**写成文件头时又 `double(NR+1)` 还原回计数**。

4. 读取方 `SE-01_READTABLE.C:34-39` 把该值直接存为 `NRho` 并算 `NR = NRho-1`：
```c
  fscanfresult = fscanf(h,"%le",&d); (*qtab).NRho = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).NT = int(d);
  fscanfresult = fscanf(h,"%le",&d); (*qtab).Nelements = int(d);
  NR = (*qtab).NRho-1;
  NT = (*qtab).NT-1;
  Nelements = (*qtab).Nelements-1;
```

5. **官方文档 §15 明确说明补点**：
> "Nevertheless, the FEOS table generation tool automatically adds **T = 0.0 eV** and **ρ = 0.0 g/cm³** to the density-temperature mesh."

**结论：**
- 文件头第 2/3 字段 = **`NRho` / `NT`，即「点数」**（不是「末下标+1」的巧合，而是字面上的点数）；
- 表**确实强制包含 `T=0` 与 `ρ=0` 两个点**（`getPointDensity` 的 `*total = 1` 起算 + `makeRTPointArray` 的 `array[0] = Qstart = 0`）；
- 因此「表尺寸为 `NR+1`/`NT+1`」的说法只要把 `NR`/`NT` 理解为**末下标**就成立，但**更准确的表述是：文件头存的是点数 `NRho`/`NT`，且该点数中已强制包含 T=0 与 ρ=0 两点**。
- Al 实测：`Rho[0] = 0.0`（`Al.feos` 网格段第 1 个值即 `0.00000000e+00`），`T[0] = 0.0` ✓

> **⚠ 一处值得注意的源码瑕疵（供文档记录）**：`FE-01_TABTOOLS.C:208-210` 把 `NR = (*table).NRho-1`，但 `Al.feos` 头写 `192`，而网格段实际有 **192** 个 ρ 值。若按「末下标」逻辑应该是 191 个值。实测表明 writer 循环 `for(i=0;i<=NR;i++)` 跑了 192 次（因为 `NR = 192-1 = 191`），**所以头值 192 = 点数，自洽**。但 `Q[k]` 循环 `for(k=0;k<=Nelements;k++)` 中 `Nelements = (*table).Nelements-1 = 1-1 = 0`，只写 1 个值；而**读取方** `for(k=0;k<=Nelements;k++)` 中 `Nelements = (*qtab).Nelements-1 = 0`，也读 1 个 → **一致**。（先前一度误判为读写不匹配，经字段总数 238,748 精确核算后确认一致。）

---

## 8. Q8 —— `.par` 文件与 `Path =` 机制

### 8.1 `.par` 文件结构

**格式判定：不是标准 Fortran NAMELIST，而是自定义的「分区 + `key = value`」ASCII 文本。**
源码只提供 `setget(key, var)` 两级检索（`COMMON-02_READFILE.C:129-169`）：

```c
char* readfile::setget(char *key, char *a) 
{
  // set file pointer beyond the key word 'key',
  // scan following lines for variable 'a',
  // and return string following 'a='.
  // break, if next key word (beginning with '&') is reached before 'a'

  int m,i,n,j=0;

  n = strlen(a);
                                                   // reset file pointer to the key word
  if (!setinput(key)) {
    printf( "\nCOMMON-ERROR in readfile::setget ---> Key word '%s' missing !!!\n", key );
    exit(-1);
  }   
```

- **分区头**：一行纯文本（如 `Computation-Settings`、`Q-table`），由 `setinput` 精确整行匹配（`COMMON-02_READFILE.C:104-125`，注意 `if(m==n){...}` 要求**行内容长度完全等于关键字长度**，且 `read_one_line` 已剥除所有空格）。
- **变量行**：`Name = value  % 注释`，值截到 `,` 或行尾（`COMMON-02_READFILE.C:153-157`）。
- **注释**：`%` ← 由 `read_one_line` 剥除（`:252-256` 处理 `#`）；**实际上 `read_one_line` 只剥 `#`**，`%` 注释被当作值的一部分由 `atof`/`atoi` 自然忽略 —— 所以 `%` 注释能工作靠的是 `atoi/atof` 的宽容。
- **分区终止**：遇 `&`（`strchr(buffer,38)`，`:147`）。样例 `.par` 未用 `&`，靠下一个分区头的「长度不等」自然失配后 `exit`... 实际是 `setget` 一路扫到 EOF 才报错，因此**每个变量名必须唯一**。

**官方文档 §4 描述：**
> "A parameter file `Materialname.par` and the material parameter database file `FEOS Material-DB.dat` are ASCII files devided into several sections by headlines (`Q-table`, `Material-7386:`, etc.). Each section contains one or several lines with a key-word (like `Rhonorm`, `[7386] A[1]`), a `=` sign, and some value. Lines can be commented out by a `%` or `#` at the beginning."

### 8.2 `Al.par` / `SiO2.par` 字段清单与语义

两个文件结构**完全同构**（仅 `Material-Number`、`Rhonorm`、`Rho0` 不同）。分区如下：

**（A）`Computation-Settings`** —— FEOS 表生成工具（`FE-03_MAIN.C:63-76`）

| 字段 | 语义 | 单位/取值 | Al | SiO2 |
|---|---|---|---|---|
| `Material-Number` | FEOS 材料库编号 | 1000–9999 | 3717 | 7386 |
| `Maxwell_Flag` | 是否做 Maxwell 构造 | 0/1 | 1 | 1 |
| `SoftSphere_Flag` | ρ<ρ_solid 时用软球替代 TF 冷曲线 | 0/1 | 1 | 1 |
| `UserCalculations_Flag` | 是否执行用户自定义计算 | 0/1 | 1 | 1 |

**（B）`Q-table`** —— 密度/温度网格生成（`FE-03_MAIN.C:78-90`）

| 字段 | 语义 | 单位 | Al | SiO2 |
|---|---|---|---|---|
| `Rhonorm` | 密度归一化基准 | g/cm³ | 2.7 | 2.2 |
| `Rhoratio-6 ... Rhoratio6` | 每个数量级区间内的**对数等距**密度点数（区间 `Rnorm·10^{x-1}` ~ `Rnorm·10^x`，x=-6..6） | 无量纲 | 见下 | 同 Al |
| `Tnorm` | 温度归一化基准 | eV | 1.0e3 | 1.0e3 |
| `Tratio-6 ... Tratio6` | 同上，温度 | 无量纲 | 见下 | 同 Al |

`Al.par` 的 `Rhoratio`：`-6..-4 = 0,0,3`? 实际为 `[-6]=0, [-5]=3, [-4]=3, [-3]=3, [-2]=10, [-1]=50, [0]=50, [1]=50, [2]=10, [3]=3, [4]=3, [5]=3, [6]=3`。
`Tratio`：`[-6]=1, [-5]=2, [-4]=10, [-3]=20, [-2]=20, [-1]=10, [0]=2, [1]=1, [2]=1, [3]=1, [4..6]=0`。

> **源码关键：`getPointDensity` 与 `key_RR`/`key_TR`**（`FE-01_TABTOOLS.C:11-28`；`FE-00_DEFINITS.H:23-24`）
> ```c
> #define key_RR "Rhoratio"
> #define key_TR "Tratio"
> ```

**（C）`General`** —— SHOWEOS 用（`SE-04_MAIN.C:57-60`）

| 字段 | 语义 | 取值 |
|---|---|---|
| `File-Format` | 表格式 | `1`=FEOS(`.feos`), `2`=SESAME(`.301/.304/.305`) |
| `EOS-Type` | 分项 | `1`=total, `2`=electronic, `3`=ionic, `4`=Thomas-Fermi |

**（D）`Units`** —— 输出单位乘子（`SE-04_MAIN.C:61-68`）

| 字段 | 乘子 | 1.0 表示 | 备选 | Al/SiO2 值 |
|---|---|---|---|---|
| `Rho_unit` | `units.R` | g/cm³ | — | 1.0 |
| `T_unit` | `units.T` | eV | `8.617525902e-5` → K | 1.0 |
| `P_unit` | `units.P` | dyne/cm² | `1.0e12` → MBar | 1.0e12 |
| `E_unit` | `units.E` | erg/g | `1.0e10` → MJ/kg | 1.0 |
| `U_unit` | `units.U` | cm/s | `1.0e5` → km/s | 1.0e5 |

自动派生（`SE-04_MAIN.C:70-73`）：`S_unit = E_unit/T_unit`，`F_unit = E_unit`，`V_unit = 1/Rho_unit`，`Q_unit = 1.0`。

**（E）`Rho-T-Mesh`** —— 等温/等密/等熵的采样网格（`SE-03_SERVICES.C:237-278`）

| 字段 | 语义 | 源码键 | Al/SiO2 |
|---|---|---|---|
| `Rhomin`/`Rhomax` | 密度范围（按 `Rho_unit`） | `Check_Density` | 1.0e-3 / 10 |
| `Rhooriginal` | 是否只用表内原始密度点 | `Rhooriginal` | 0 |
| `Rhonumber` | 密度点数（`Rhooriginal=0` 时） | `Rhonumber` | 5 |
| `Rholog` | 0=线性,1=对数 | `Rholog` | 0 |
| `Tmin`/`Tmax` | 温度范围（按 `T_unit`） | `Check_Temperature` | 1.0e-4 / 1.0e3 |
| `Toriginal`/`Tnumber`/`Tlog` | 同上（温度） | — | 0 / 7 / 1 |
| `Rhofirst`/`Tfirst` | 是否打印最低点 | — | 0 / 1 |

**（F）`Isocurves`** —— 等温/等密/等熵的 X/Y 轴量（`SE-03_SERVICES.C:282-302`）

| 字段 | 语义 | 取值范围（`Al.par:129-132`） |
|---|---|---|
| `Xquantity`/`Yquantity` | 轴量编号 | 1=密度, 2=比容, 3=温度, 4=压力, 5=比内能, 6=比 Helmholtz 自由能, 7=比熵, 8=电荷态 |
| `Xelement`/`Yelement` | 元素号（仅电荷态；0=总和） | 0 |

**（G）`Mountain`**（`SE-03_SERVICES.C:596-605`）：`Xquantity` (1/2)、`Quantity` (4–8)、`Element`。

**（H）`Hugoniot`**（`SE-03_SERVICES.C:665-669`）：`Rho0`、`T0`、`Pmax`、`Xquantity` (1/2)。

### 8.3 `Path = ./tabelle/tabelle1197` 这类路径重定向如何工作？

**结论：在 FEOS 16.7 源码中未找到任何 `Path` 关键字处理。**

证据：
1. 在 `Code/` 全部 36 个源文件中检索 `Path`（含大小写变体）→ **唯一命中是两条宏定义**：
```c
// LIB-00_DEFINITS.H:23-24
#define MATERIAL_DATABASE_PATH "./FEOS_Material-DB.dat"
#define TF_TABLE_PATH          "./FEOS_TF-Table_1197.dat"
```
2. 这两条是**编译期硬编码**的**相对路径**；读取处：
```c
// LIB-07_C_INTERFACE.C:192（注释）
    // Initialize QIPscheme for every element (TF-Table read from TF_TABLE_PATH)
```
3. `readfile::setget` 只做 `key`/`var` 两级检索，**没有任何路径拼接 / 重定向逻辑**。
4. 官方 96KB 文档中检索 `Path` → **0 命中**。
5. 本机 `matter++` 下所有 `*.par`/`*.PAR` 中检索 `Path` → **仅 2 处命中，且都是同一个文件** `mat_He/Untitled.PAR`（重复计数），其内容是**完全不同的旧版参数模式**：
```
     TF-Table
Path = ./tabelle/tabelle1197
     Maxwell-Construction
Maxwell_Flag = 0
Charge_Flag = 1
     Material-Data
A = 4.00256163944925
Z = 2
Rsolid = 0.0001663
Bulk-Modulus = 2.61e+12
T_standard = 0.0235
     Q-table
Rratio-6 = 0
...
     Isotherms
Quantity = Pressure
Tmin = 100
...
```

**判定：`Path = ...` 属于旧版 MPQEOS v2.0 参数模式**：
- 分区名是 `TF-Table` / `Maxwell-Construction` / `Material-Data`，而 FEOS 16.7 是 `Computation-Settings` / `Q-table`；
- 直接给出 `A`/`Z`/`Rsolid`/`Bulk-Modulus`/`T_standard` 而非 FEOS 的 `Material-Number`（查库）；
- 网格键是 `Rratio-X`（单 R），FEOS 是 `Rhoratio-X`；
- 有 `Charge_Flag`（FEOS 无）。

因此 `Path = ./tabelle/tabelle1197` **只能被 MPQEOS v2.0 或 Multi1D++ 的旧式读取器解释**（该读取器不在本 FEOS 包内），语义是「把 TF 表目录从默认位置重定向到 `./tabelle/`，基名 `tabelle1197`」。

> **置信度：Path 归属 MPQEOS 旧模式「高」；FEOS 16.7 无此机制「极高」。** 若需确认 Multi1D++ 侧读取器，需检索 Multi1D++ 的非 FEOS 源码（本次任务范围外，未在 `matter++` 下找到处理该键的 `.C/.cpp`）。

### 8.4 `FEOS_TF-Table_1197.dat` 内部格式

**读取代码（`LIB-01_TF_SERVICES.C:74-162`）—— 全文见 §2 引用，要点：**

```c
  // format of the TF table (units: cgs, T[eV], mass density)
  // scaling CAN be done already here.
  //
  // indices from (1,1) .. ( NR,  NT)
  // R(i)
  // T(j)  Pe(i,j)  Ee(i,j)  Fe(i,j)  Q(i,j)  dP/dT(i,j)
  // T(j+1) ....  
  // R(i+1)
  // T(j)...
```
```c
  // skip comment lines:
  do { rf.read_line( &argc, argv ); }
  while( strcmp( argv[0],"#") == 0 );

  // read Table:  
  for(i=1;i<=NR;i++) {  
     if( i>1 ) rf.read_line( &argc, argv );
     if(argc!=1) {
       printf("\nLIB-ERROR in read_TF_TABLE ---> %d !!!\n",argc); 
       exit(0); 
     } 
     (*table).rho[i] = atof( argv[0] );
     for(j=1;j<= NT;j++) { 
       rf.read_line( &argc, argv );
       if( argc != WORDS_IN_TF_LINE ) { 
	 printf("\nLIB-ERROR in read_TF_TABLE ---> Wrong number of words in TF-table line !!!\n");
	 exit(0); 
       }
       (*table).Te[j]     = atof( argv[0] );
       
       (*table).Pe[i][j]  = atof( argv[1] );
       (*table).Ee[i][j]  = atof( argv[2] );
       (*table).Fe[i][j]  = atof( argv[3] );

       (*table).Se[i][j]  = ( (*table).Te[j] > ZERO ) ? 
       	 ( (*table).Ee[i][j] - (*table).Fe[i][j]) / 
	 ( eV2cgs*(*table).Te[j] ) : 0.0;
       
       (*table).Q[i][j]   = atof( argv[4] );
       (*table).dPdT[i][j]    = atof( argv[5] );
     }
   }
```

**常量：**
```c
// LIB-00_DEFINITS.H:38
  WORDS_IN_TF_LINE = 6;                // No of words in line of TF-table 
```

**表尺寸判定（`COMMON-02_READFILE.C:47-69`）：**
```c
int readfile::getTableSize( int* NR, int* NT )
{ 
  // corresponds to structure of TF-table

  char** arg;
  int narg,nr,nt;
  arg = cmatrix( MAX_LINE_NO , MAX_LINE_LENGTH );
  nr = nt = 0;
  while( read_line( &narg, arg ) != 0 ) { 
    if(arg[0][0]!='#'){ 
      if( narg==1 ) nr++; 
      else nt++;
    } 
  }
  if(nr==0) { printf("\nCOMMON-ERROR in readfile::getTableSize ---> No table entries found !!!\n"); exit(0); }
  nt = int( nt/nr );
  
  *NR = nr;
  *NT = nt;
```
→ **「单字段行」计数 = `NR`；「多字段行」总数 / NR = `NT`。**

**实测验证（`EOS-Data/FEOS_TF-Table_1197.dat`，567,342 B）：**

```
NUL 字节数 = 0                       ← 纯 ASCII 文本
非空非注释行 = 4,185
单字段行 = 93                         ← NR = 93
6 字段行 = 4,092
NT = 4092 / 93 = 44                   ← NT = 44
ρ 范围: 1.000000000000000e-06 .. 1.584893192461114e+03
每 ρ 块的 T 范围: 0.000000000000000e+00 .. 1.000000000000003e+06
```

**✅ 93 × 44 证实。**

**内部格式（逐层）：**

| 层级 | 行数 | 内容 |
|---|---|---|
| 全局 | 若干 `#` 开头 | 注释（`read_TF_TABLE` 跳过；本样例无） |
| 每个 ρ 块 | 1 行 | **单字段**：该块的密度 `ρ[i]` [g/cm³] |
| 每个 ρ 块 | NT=44 行 | **6 字段**：`T, Pe, Ee, Fe, Q, dPdT` |

**列序与单位（源码 `LIB-01_TF_SERVICES.C:136-147` + 表头注释 `:90`）：**

| 列 | 变量 | 语义 | 文件单位 | 内部存储单位 | 换算 |
|---|---|---|---|---|---|
| 1 | `Te[j]` | 电子温度 | **eV** | eV | 直接用 |
| 2 | `Pe[i][j]` | 电子压力 | **cgs (dyne/cm²)** | cgs | 直接用 |
| 3 | `Ee[i][j]` | 电子比内能 | **cgs (erg/g)** | cgs | 直接用 |
| 4 | `Fe[i][j]` | 电子比 Helmholtz 自由能 | **cgs (erg/g)** | cgs | 直接用 |
| 5 | `Q[i][j]` | 电荷态（电离度） | 电子电荷倍数 | 同 | 直接用 |
| 6 | `dPdT[i][j]` | ∂P/∂T | **cgs / eV** | cgs/eV | 直接用 |
| — | `Se[i][j]` | 电子比熵 | — | cgs `erg/(g·eV)` | **由 `(Ee−Fe)/(eV2cgs·Te)` 现场算出，文件不含** |
| （行首） | `rho[i]` | 质量密度 | **g/cm³** | cgs | 直接用 |

**实测首块（ρ[1] = 1e-6）：**
```
1.000000000000000e-06                                    ← ρ[1]
0.000000000000000e+00  1.254660623088583e-03  -2.003759859646893e+13  ...   ← T, Pe, Ee, Fe, Q, dPdT
3.981071705534973e-03  5.545522588506331e+01  -2.003725909054711e+13  ...
```
（与 `LIB-02_TF_TABLE_2.C:368` 的 `Einfinity = -2.003755854614347e+13` 量级吻合，印证单位为 erg/g 的 cgs 电子能量。）

**H 表生成（二次加工，`LIB-02_TF_TABLE_2.C:331-378`）：** TF 表在库内被转成插值用的「H 表」，索引 `u = ρ^{-2/3}`（`ufield[i] = pow(tft1.rho[NU+1-i], -ZWEI_DRITTEL)`，`:360`），并**剥掉第 1 个温度点**（`int CUT = 1; NT = tft1.NT-CUT;`，`:342,348`），即丢弃 `T=0` 冷点，`Tfield[j] = eV2cgs*tft1.Te[j+CUT]`。
**注意：这意味着 `.feos` 里 `T[0]=0` 是 FEOS 工具层补的，而库内 TF 插值表本身不用该点。**

**插值矩阵一致性检查（`LIB-02_TF_TABLE_1.C:23-27`）：**
```c
  if( fabs( ht.TabMult_rho - QIPmult_rho ) > 1e-10 || 
      fabs( ht.TabMult_T - QIPmult_T ) > 1e-10 ) {
    printf("\nLIB-ERROR in QIPscheme::QIPscheme ---> Table does not match with interpolation matrix !!!\n");
    exit(0);
  }
```
而 `QIPmult_rho = pow(10.0, 0.1)`、`QIPmult_T = pow(10.0, 0.2)`（`LIB-00_DEFINITS.H:45-46`）。
实测 TF 表 ρ 比值 = `3.981071705534973e-03 / 1.0e-06 = 3.9810717 = 10^0.6`（**每 5 步一个数量级**），T 比值 = `3.981071705534973e-03/...` 同理 → 与 `TabMult_rho`/`TabMult_T` 的检验自洽。

---

## 9. 附：`FEOS_Material-DB.dat` 与 `.par` 的对应

```c
// LIB-00_DEFINITS.H:23
#define MATERIAL_DATABASE_PATH "./FEOS_Material-DB.dat"
```

**库文件字段（`FEOS_Material-DB.dat:1-30` 的自述头）：**
```c
% This file contains the FEOS material properties database.            %
% To add a new material, introduce a new section with an unused FEOS   %
% material number. Allowed numbers are: 1000-9999                      %
% The material number comes before each parameter in squared brackets. %
...
% - SESAME-Number: SESAME table number (if not known, set to 1000)     %
% - Treference: Reference temperature in eV                            %
% - Rhoreference: Density at Treference and zero pressure in g/cm^3    %
% - Buld-Modulus: Bulkmodulus at Treference, Rreference in dyne/cm^2   %
% - Number-of-Elements: Number of elements included in the material    %
% - A[1...Element-Number]: Atomic weights of all included elements     %
% - Z[1...Element-Number]: Atomic numbers of all included elements     %
% - X[1...Element-Number]: Number of atoms per molecule                %
%                          of all included elements                   %
% If you want to use the soft-sphere function, please specify also:    %
% - Ecohesive: Cohesive energy / enthalphy of sublimation in erg/g     %
% - Soft-Sphere-m: Parameter m in soft-sphere function                 %
% - Soft-Sphere-n: Parameter n in soft-sphere function                 %
```

**样例（Tin）：**
```
Material-2160:

[2160]_SESAME-Number = 2160
[2160]_Treference = 2.585257e-2         % 2.585257771e-2 ---> 300 K
[2160]_Rhoreference = 7.7
[2160]_Bulk-Modulus = 5.8e11            % GPa value multiplied by 1.0e10 
[2160]_Number-of-Elements = 1

[2160]_A[1] = 118.69                    % Element 1: Tin (Sn)
[2160]_Z[1] = 50.0
[2160]_X[1] = 1.0

[2160]_Ecohesive = 2.552e10
[2160]_Soft-Sphere-m = 0.5
[2160]_Soft-Sphere-n = 2.0
```

**`Material-DB` → `.feos` 参数行的映射链（`FE-03_MAIN.C:155-164`）：**
```c
  FEOS_Init_Mat(entity, matnumber, MaxwellFlag, SoftSphereFlag, TMaxwell, qtable.NT, 
                      &(qtable.Nelements), &(ctable.Niso), &(ctable.Trel));  

  // Get material parameters:
  GetQTABmemory2(&qtable, 0);
  FEOS_Get_Mat_Par(entity, qtable.A, qtable.Z, qtable.X, &(qtable.Atot), &(qtable.Ztot), &(qtable.Xtot), 
                         &(qtable.TRef), &(qtable.RhoRef), &(qtable.BulkModulusRef), &(qtable.SESAMEnumber));
  FEOS_Get_Energy_Offsets( entity, &(qtable.ElectronOffset), &(qtable.IonOffset) );
  if(SoftSphereFlag) FEOS_Get_SoftSphere_Par(entity, &(qtable.Ecoh), &(qtable.softsphere_n), &(qtable.softsphere_m),
                                                   &(qtable.softsphere_A), &(qtable.softsphere_B));                       
```

---

## 10. 「源码中未找到」清单（诚实声明）

| 项 | 状态 |
|---|---|
| `4gnuplot` 后缀的**生成代码** | **FEOS 16.7 源码与官方文档中均未找到**（0 命中）。实测判定为外部后处理产物。 |
| `Path =` 键的**解析代码** | **FEOS 16.7 源码中未找到**。判定归属旧 MPQEOS v2.0 参数模式。 |
| `.ist4gnuplot` 的**列头拼接函数** | 未找到（只有产物）。推断拼接模板为 `"<Yname>.<suffix>4gnuplot"`（因产物中 Y 列头为 `P.ist4gnuplot`）。 |
| `SE-03_SERVICES.C` 中 `Mountain` 用到的 `KEY_*` 宏（`IsoUnits`/`OffsetFlag`/`VolumeFlag`/`OriginalFlag`/`Number`） | 宏在 `SE-00_DEFINITS.H:23-28` 有定义，但**在当前 `SE-03_SERVICES.C` 中未被引用**（改用 `rf.setget("Mountain", ...)`）。属遗留定义。 |
| `write_txt_format` 的 `.data.txt` | **本次未被要求，但源码存在**：`FE-01_TABTOOLS.C:824-879`，后缀 `"%s.data.txt"`，每行 10 列（i, j, ρ, T, P, Pi, Pe, E, Ei, Ee），SESAME 单位。 |
| `KEY_OFFSET` 等宏对应的**旧 `.PAR` 模式读取器** | 不在 FEOS 包内。 |

---

## 11. 快速参考卡（供规格书直接引用）

### 11.1 扩展名 → 生成器 → 行宽 → 编码

| 扩展名 | 生成函数 | 源码位置 | 每行字段 × 宽度 | 编码 | 单位制 |
|---|---|---|---|---|---|
| `.feos` | `write_FEOS_format` | `FE-01_TABTOOLS.C:196` | **10 × 15** = 150 字符 | ASCII | cgs + eV |
| `.301` | `write_301_format` | `FE-01_TABTOOLS.C:594` | **4 × 15** = 60 字符 | ASCII | GPa / MJ·kg⁻¹ / g·cm⁻³ / K |
| `.304` | `write_304_format` | `FE-01_TABTOOLS.C:672` | **4 × 15** = 60 | ASCII | 同上 |
| `.305` | `write_305_format` | `FE-01_TABTOOLS.C:748` | **4 × 15** = 60 | ASCII | 同上 |
| `.mexport` | `write_mexport_format` | `FE-01_TABTOOLS.C:370` | **5 × 15 + 5 控制列** = 80 | ASCII | GPa / MJ·kg⁻¹ / Mg·m⁻³ / K |
| `.data.txt` | `write_txt_format` | `FE-01_TABTOOLS.C:824` | 10 列 TAB 分隔 | ASCII | SESAME |
| `.cst` | `write_Rostock_format` | `FE-01_TABTOOLS.C:883` | 4 列空格分隔 | UTF-8 | 1/cm³, g/cm³, MBar, — |
| `.critical.dat` | `write_criticaldata` | `FE-01_TABTOOLS.C:58` | 1–8 列 `%e` 空格分隔 | UTF-8（g/cm³） | K/bar/g·cm⁻³/kJ·g⁻¹ |
| `.isobaric.dat` | `write_isobaricdata` | `FE-02_CALCULATIONS.C:181` | 6 列 / 3 列 / 2 列 | ASCII | K, g/cm³, bar, 1/K, J/g, J/gK |
| `.ist` | `Isotherms` | `SE-03_SERVICES.C:306` | 2 列 `%e` 空格分隔 | ASCII | 依 `.par` 的 `*_unit` |
| `.isc` | `Isochores` | `SE-03_SERVICES.C:382` | 2 列 | ASCII | 同上 |
| `.ise` | `Isentropes` | `SE-03_SERVICES.C:458` | 2 列 | ASCII | 同上 |
| `.mnt` | `Mountain` | `SE-03_SERVICES.C:564` | 分块长列 | ASCII | 同上 |
| `.hug` | `Hugoniot` | `SE-03_SERVICES.C:649` | 6 列 | ASCII | 同上（默认 1e12 dyne/cm²、1e5 cm/s） |
| `.ist4gnuplot` 等 | **未找到** | — | 3 列 TAB 分隔 | ASCII | 同上 |

### 11.2 三条最容易踩的坑

1. **`.feos` 是 10×15 不是 4×15** —— `Readme.txt:12` 有误。`SF_TRENN=""` 是根因。
2. **`.301/.304/.305` 有 4×15（FEOS）与 4×16（旧 MPQeos）两种实物** —— 解析时**不能假设固定宽度**，应通用地按空白分割再回退到定宽；或至少用「行长度 60 / 64」区分。
3. **`.mexport` 是 80 字符定宽 5×16**，最后 5 字符是**控制位**而非数值 —— 数值解析必须切掉 `line[75:80]`。

---

*报告结束。所有结论均基于本机 FEOS 16.7 源码原文与本机 `matter++` 实测文件，未联网、未修改任何受保护文件。*
