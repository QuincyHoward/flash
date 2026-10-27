# FEOS 源码级裁定（第四问集）—— 主理人亲自完成

**定稿时间**：2026-09-19
**执行者**：team-lead（**接管失败代理 `rev-feos-src2` 的任务**）
**失败说明**：原代理 `rev-feos-src2` 因**网络故障**中断（`502 getaddrinfo ENOTFOUND copilot.tencent.com`），
落盘了 `feos_src_q1.py/.out.txt`、`feos_src_q1b.*`、`feos_src_q2.*`、`feos_src_q4.*` 等探针，
但**未产出本文件**。经核查，该任务**全部输入均为本地文件**（`vendor/FEOS_src/`），
**不需要联网**，故由主理人直接完成，不重新派发。

**源码基准**（两份内容相同，均为 FEOS 官方发行包 GPLv3）：
`src/multi_src/09_source_verify/vendor/FEOS_src/FEOS/Code/`（18 `.C` + 18 `.H`）

---

## Q1. `.feos` 头部两行的**字段顺序与单位**（**全部定案**）

### 1.1 写出端明文（决定性证据）

`FE-01_TABTOOLS.C:196` `void write_FEOS_format( char* name_in, Qtable* table)`，
第 204 行注释与第 222–227 行 `fprintf`：

```c
196: void write_FEOS_format( char* name_in, Qtable* table)
204:   // FEOS units are cgs (+ eV for temperature)      ← 单位总声明
206:   double FileVersion = 12.06;                       ← 硬编码的版本号
208:     NR = (*table).NRho-1,                          ← 注意 -1
221:   // Print EOS parameters:
222:   fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",
             FileVersion, SF_TRENN, double(NR+1), SF_TRENN, double(NT+1), SF_TRENN,
             double(Nelements+1), SF_TRENN, (*table).Tcalclimit);
223:   fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",
             (*table).Rhocalclimit, SF_TRENN, (*table).RhoRef, SF_TRENN, (*table).TRef,
             SF_TRENN, (*table).BulkModulusRef, SF_TRENN, double((*table).SESAMEnumber));
224:   fprintf(h,"\n");
225:   fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",
             (*table).ElectronOffset, SF_TRENN, (*table).IonOffset, SF_TRENN, (*table).Ecoh,
             SF_TRENN, (*table).softsphere_n, SF_TRENN, (*table).softsphere_m);
226:   fprintf(h,"%15.8le%s%15.8le%s%15.8le%s%15.8le%s%15.8le",
             (*table).softsphere_A, SF_TRENN, (*table).softsphere_B, SF_TRENN,
             (*table).Atot, SF_TRENN, (*table).Ztot, SF_TRENN, (*table).Xtot);
227:   fprintf(h,"\n");
```

### 1.2 由此得出的**行 0 / 行 1 完整字段表**

| 行 | # | 变量 | 本地实测（`mat_Al-1.0/Al.feos`） | 单位 / 语义 |
|---|---|---|---|---|
| **0** | 1 | `FileVersion` | `12.06` | 硬编码常量（源码 206 行） |
| 0 | 2 | `NR+1` | `192` | ρ 点数（源码里 `NR=NRho-1`，故写出 +1） |
| 0 | 3 | `NT+1` | `69` | T 点数 |
| 0 | 4 | `Nelements+1` | `1` | 元素数（纯 Al ⇒ 0+1） |
| 0 | 5 | `Tcalclimit` | `1e-4` | **eV** |
| **1** | 1 | `Rhocalclimit` | `1e-50` | **g/cm³** |
| 1 | 2 | `RhoRef` | `2.7` | **g/cm³**（参考密度 = Al 固态密度 ✓） |
| 1 | 3 | `TRef` | `2.585257e-02` | **eV**（见 1.3） |
| 1 | 4 | `BulkModulusRef` | `7.5e11` | **dyne/cm²**（cgs） |
| 1 | 5 | `SESAMEnumber` | `3.717e03` | 整数（`Al.feos.301` 的 Id `37170301` 前 4 位 ✓） |

**行 1 的十字段顺序与本地推断（第二版）完全一致** —— 无需更正。

### 1.3 三个单位悬案的裁定

| 字段 | 裁定 | 依据（`文件:行号`） |
|---|---|---|
| `Tcalclimit` | **eV** | `FE-03_MAIN.C:136` `printf(" ... below library calculation limit %.2e eV!", qtable.Tcalclimit);` |
| `Rhocalclimit` | **g/cm³** | `FE-03_MAIN.C:141` `printf(" ... below library calculation limit %.2e g/cm^3!", qtable.Rhocalclimit);` |
| `RhoRef` | **g/cm³** | `FE-03_MAIN.C:257-258` `printf(" ... (Rho < %e g/cm^3)!", qtable.RhoRef);` |
| **`TRef`** | **eV（不是 Hartree）** | `FE-01_TABTOOLS.C:204` 注释 `FEOS units are cgs (+ eV for temperature)`；旁证：全包一致地把内部 T（eV）乘 `eV2Kelvin` 才输出 Kelvin（如 `FE-01_TABTOOLS.C:896`、`FE-02_CALCULATIONS.C:192`） |

> **✅ 关闭第二版遗留悬案「`.feos` 头 `TRef` 单位（eV vs Hartree）」**：
> 两者差 27.2114 倍，**源码明文定为 eV**。旧代理的"Hartree"推测**错误**，作废。
> `Tcalclimit = 1e-4 eV` 与 `TRef = 2.585e-2 eV` 量级自洽（均为 eV 级），也否证 Hartree
> （若为 Hartree，`1e-4 Ha = 2.7e-3 eV`、`2.6e-2 Ha = 0.7 eV`，与 `Al.feos` 中 T 网格
> 下限 `0.5 eV`、`T0 = 2.585257e-2` 的实际物理量不符）。

### 1.4 **顺带关闭第二版最老的悬案：`.feos` 行宽**

`FE-00_DEFINITS.H:28`：`#define SF_TRENN  ""` —— **分隔符为空串**。
再结合 `FE-01_TABTOOLS.C:233/237/241/247/251/258` 的统一写法：

```c
if(++count%10) fprintf(h,"%s",SF_TRENN); else fprintf(h,"\n");
```

⇒ **每 10 个 `%15.8le` 字段换一次行**，字段间**无任何分隔** ⇒ **每行恰好 10×15 = 150 字符**。

**结论**：`.feos` 的按行布局是 **10×15 = 150**，**由写出端明文定义**。
`matter++/Readme.txt:12` 所写"一行 4 个 15 字符"**是错的**（或仅描述读入端的粗粒度提示），
文档应以**源码为准** `[S-SRC]`。§10.6.2 的更正由此获得最硬的依据。

---

## Q2. `.cst`（Rostock 格式）四列单位 + 英文变体存在性

### 2.1 写出端明文

`FE-01_TABTOOLS.C:883-907` `void write_Rostock_format( char* name_in, Qtable* table)`：

```c
892:   sprintf( name, "%s.%s", name_in, ROSTOCK_SUFFIX );        ← 后缀宏（.cst）
895:   for(j=0;j<=NT;j++) {
896:     fprintf( h, "Isotherme T = %.0f Kelvin \n", (*table).T[j]*eV2Kelvin );
897:     fprintf( h, "Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand\n" );
898:     for(i=0;i<=NR;i++) {
899:       fprintf( h,"%e          %e          %e    %e\n",
900: 	       (*table).Rho[i]/((*table).Atot*M_proton),   ← col0 数密度 1/cm³
901: 	       (*table).Rho[i],                            ← col1 质量密度 g/cm³
902: 	       (*table).P[i][j]*cgs2MBar,                  ← col2 压强 MBar
903: 	       (*table).Qtot[i][j] );                      ← col3 电荷态总和
904:     }
905:   }
```

### 2.2 四列裁定（**与本地实测完全一致**）

| 列 | 表达式 | 单位 | 说明 |
|---|---|---|---|
| 0 | `ρ/(Atot·M_proton)` | **1/cm³** | 数密度；`M_proton` 为质子质量常量 |
| 1 | `ρ` | **g/cm³** | 质量密度 |
| 2 | `P·cgs2MBar` | **MBar** | `cgs2MBar = 1e-12` |
| 3 | `Qtot[i][j]` | **无量纲** | 电荷态总和（非平均 Z̄） |

**格式串** `"%e          %e          %e    %e\n"` —— **10 + 10 + 4 个空格**，
这正是本地实测"第 3 token 起始列在 60/61 抖动"的根源：
`%e` 的宽度随有效数字位数变化（`-1.#INF00e+000` 为 15 字符、常规约 13 字符），
**故不可定宽切片，必须空白 split + 断言 4 个字段** `[S-SRC]` 确证。

### 2.3 表头 `T` 的语义（**证实代理的更正，并否证第二版**）

`FE-01_TABTOOLS.C:896` `(*table).T[j]*eV2Kelvin` ⇒

- `T` 在**块间变化**（`j` 循环，每个等温线一块）；
- 输出单位为 **Kelvin**（乘 `eV2Kelvin`）；
- 格式 `%.0f` **取整** ⇒ 低温区出现相邻块相同整数（**精度截断，不是数据重复**）。

⇒ 第二版曾写"首行 `Isotherme T = 0 Kelvin` 是常量 0"**错误**，代理 `probe-cst-naming`
的更正**正确**，本裁定予以**确认**。

### 2.4 **英文变体 `mat_He/Untitled.CST` 的裁定：源码中不存在**

在整个 `vendor/`（`FEOS_src` + `FEOS_extract` 两份完整包，共 74 个源码/文档文件）中检索：

```
pattern: Particle density | load state | Pressure[MBar] | Isotherm T
result : No matches found        ← 零命中
```

同时德文模板 `Moleküldichte ... Ladungszustand` **在 `FE-01_TABTOOLS.C:897` 命中**
（首轮检索因源码为 Latin-1 编码、`ü` 未按 UTF-8 匹配而漏检，本轮已用 ASCII 子串复核）。

**裁定**：

| 项目 | 结论 | 溯源级 |
|---|---|---|
| 德文 `.cst` 模板 | **FEOS 16.7 官方写出器产出**（`FE-01_TABTOOLS.C:897`） | `[S-SRC]` |
| **英文 `.cst` 模板**（`Particle density` / `load state`） | **FEOS 16.7 源码包中不存在** ⇒ 由**外部工具或手工编辑**产生 | `[S-UNK]`（已排除"本包源码"这一可能） |

⇒ 第二版登记的"英文 `.cst` 生成工具未解"**保持未解**，但**排除范围收窄**：
可以确定**不是 FEOS 16.7 的 `write_Rostock_format`**。建议后续在 FEOS 旧版本
（≤2012，见 `Documents/FEOS-Package-Documentation2012.txt`）或第三方转换脚本中查找。

---

## Q3. `.feos` 行 1 的十个字段（**与本地推断一致**）

见 Q1.1 的 `FE-01_TABTOOLS.C:225-226`。确认顺序为：

```
ElectronOffset, IonOffset, Ecoh, softsphere_n, softsphere_m,
softsphere_A, softsphere_B, Atot, Ztot, Xtot
```

**`Atot` 是"分子总量"而非平均值** —— 这一点由写出端与读入端共同确认：

- 写出端：`Qtable` 成员 `Atot / Ztot / Xtot`（`COMMON-00_DEFINITS.H`）;
- 数值验证（第二版实测，本轮沿用）：`Ta2O5.feos` 行 1 第 8 字段 = `4.41893536e+02` = Ta₂O₅ 分子量
  441.893，而 `Xtot = 7.0`（2 Ta + 5 O）⇒ **`Atot/Xtot` 才是平均原子量** ✓
- 另证：`Al.feos` 行 1 第 8–10 字段 = `26.9815, 13.0, 1.0` ⇒ `Atot/Xtot = 26.9815` = Al ✓

⇒ 第二版结论**正确，无需更正**。

---

## Q4. 不透明度表 T 轴缩放 —— **FEOS 源码不适用（职责在 SNOP）**

对 FEOS 全部写出函数做了穷举（`Grep '^void write_'`），**共 10 个写出器**：

```
FE-01_TABTOOLS.C : write_criticaldata(:58)   write_FEOS_format(:196)   write_mexport_format(:370)
                   write_301_format(:594)    write_304_format(:672)    write_305_format(:748)
                   write_txt_format(:824)    write_Rostock_format(:883)
FE-02_CALCULATIONS.C: write_isobaricdata(:181)
LIB-01_TF_SERVICES.C: write_TF_TABLE(:40)
```

**其中没有任何函数写出 SESAME/MULTI 风格的 Planck/Rosseland 多群不透明度表**。
即 **FEOS 不产出该类文件** —— 它是 **SNOP / MULTI-94** 的职责。

**因此 Q4 的权威来源不是 FEOS 源码，而是 `doc/SNOP.MANUAL`**，而该问题在本轮
**已由手册明文定案**（见 `§14.5.5` 与 `§15.12.6`）：

```
SNOP.MANUAL:34-37   RHO1/RHO2  Lowest/Highest density (in g/cm**3)
SNOP.MANUAL:38-41   T1/T2      Lowest/Highest temperature (in keV)     ← 关键
SNOP.MANUAL:42-44   X1/X2      ... (in keV)
SNOP.MANUAL:55-58   F0/F1      ... (in eV)
SNOP.MANUAL:62      FG(NG+1)   Group boundaries (in eV)
```

⇒ `T1/T2` 单位为 **keV**，表内 `log10(T[eV])`，换算 **×1000**；
`RHO1/RHO2` 单位为 **g/cm³**，表内 `log10(ρ[g/cm³])`，**无因子**。
端点逐位验证：`Ce`（`1e-5, 5` keV → `0.01…5000 eV`）、`Be`（`1e-3, 100` keV → `1…1e5 eV`）。
**不存在 10× 因子**；第二版的"10× 悬案"是切片错误造成的假象。

---

## 确定性汇总表

| # | 问题 | 裁定 | 依据 | 溯源级 | 置信 |
|---|---|---|---|---|---|
| 1a | `.feos` 行 0 字段顺序 | `FileVersion, NR+1, NT+1, Nel+1, Tcalclimit, Rhocalclimit, RhoRef, TRef, BulkModulusRef, SESAMEnumber` | `FE-01_TABTOOLS.C:206,222-223` | `[S-SRC]` | **高** |
| 1b | `Tcalclimit` 单位 | **eV** | `FE-03_MAIN.C:136` | `[S-SRC]` | **高** |
| 1c | `Rhocalclimit` 单位 | **g/cm³** | `FE-03_MAIN.C:141` | `[S-SRC]` | **高** |
| 1d | **`TRef` 单位** | **eV（非 Hartree）** | `FE-01_TABTOOLS.C:204` 注释 + `eV2Kelvin` 旁证 | `[S-SRC]` | **高** |
| 1e | **`.feos` 行宽** | **10×15 = 150**（`SF_TRENN=""`） | `FE-00_DEFINITS.H:28` + `FE-01_TABTOOLS.C:233…258` | `[S-SRC]` | **高** |
| 2a | `.cst` 四列语义 | 数密度(1/cm³) / 质量密度(g/cm³) / 压强(MBar) / 电荷态总和 | `FE-01_TABTOOLS.C:899-903` | `[S-SRC]` | **高** |
| 2b | `.cst` 不可定宽切片 | 格式串 `"%e          %e          %e    %e\n"`（10/10/4 空格） | 同上 | `[S-SRC]` | **高** |
| 2c | `.cst` 块首 `T` 非常量 | `(*table).T[j]*eV2Kelvin`，`%.0f` 取整 | `FE-01_TABTOOLS.C:896` | `[S-SRC]` | **高** |
| 2d | **英文 `.cst` 模板** | **FEOS 16.7 源码中不存在**（外部工具/手工） | 全 vendor 零命中 | `[S-UNK]` | 中（已排除本包） |
| 3 | `.feos` 行 1 十字段 | `ElectronOffset, IonOffset, Ecoh, ssm_n, ssm_m, ssm_A, ssm_B, Atot, Ztot, Xtot`；`Atot/Xtot` = 平均原子量 | `FE-01_TABTOOLS.C:225-226` | `[S-SRC]` | **高** |
| 4 | 不透明度 T 轴缩放 | **FEOS 不产出该表**（10 个写出器穷举无此函数）；权威在 `SNOP.MANUAL:38-41` ⇒ **keV 输入 / eV 表内 / ×1000，无 10×** | 穷举 `^void write_` + 手册 | `[S-SRC]`+`[S-L1]` | **高** |

## 仍未解 / 需后续

| # | 项 | 状态 | 下一步 |
|---|---|---|---|
| 1 | 英文 `.cst` 表头的生成工具 | **未解**（已排除 FEOS 16.7） | 查 FEOS ≤2012 版本或第三方转换脚本；或向数据集提供者询问 |
| 2 | `ROSTOCK_SUFFIX` 宏的定义位置 | 未定位（不在 `FE-00_DEFINITS.H`） | grep 其余 `.H` |
| 3 | `M_proton` / `cgs2MBar` / `eV2Kelvin` 的数值常量定义 | 未取到定义行 | grep `COMMON-00_DEFINITS.H`（第二版曾引 `M_proton=1.6726231e-24`、`cgs2MBar=1e-12`，待复核） |
| 4 | `write_txt_format` / `write_mexport_format` 的完整列定义 | 未逐字核对 | 后续按族补 |

---

## 与原代理的关系（诚实说明）

原代理 `rev-feos-src2` **因网络故障未能交付本文件**。其落盘的探针与输出保留在
`src/multi_src/04_probe/04_feos/`（`feos_src_q1.py/.out.txt`、`feos_src_q1b.*`、
`feos_src_q2.*`、`feos_src_q4.*`），本文件的结论**由主理人独立读取源码得出**，
未引用其未经验证的结论；凡与本文件冲突者，以本文件的 `文件:行号` 明文为准。
