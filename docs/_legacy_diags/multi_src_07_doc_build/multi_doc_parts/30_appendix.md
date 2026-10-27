# 附录

## 附录 A 单位换算总表与推导链

本附录是全文单位换算的**唯一汇总入口**。每一条换算给"因子 + 推导链 + 溯源"，禁止只有数字没有链。换算表按物理量维度分组。

### A.1 长度与时间

| 换算 | 因式 | 推导链 | 溯源 |
|---|---|---|---|
| cm ↔ µm | `1 cm = 1e4 µm` | 1 m=1e6 µm；1 cm=1e-2 m=1e4 µm | [S-L4] |
| ns ↔ s | `1 ns = 1e-9 s` | 定义 | [S-L4] |
| 速度 `cm/s → µm/ns` | `1 cm/s = 1e-5 µm/ns` | `1 cm=1e4 µm`；`1 s=1e9 ns`；故 `cm/s = 1e4 µm / 1e9 ns = 1e-5 µm/ns` | [S-L4] |
| 速度 `km/s → cm/s` | `1 km/s = 1e5 cm/s` | 1 km=1e5 cm；分母同为 s | [S-L4] |
| 速度 `km/s → µm/ns` | `1 km/s = 1e10 µm/ns` | `1e5 cm/s`，再由 `1 cm/s=1e-5 µm/ns` 得 `1e5·1e-5=1`… 复核：1 km/s=1e5 cm/s=1e5·1e-5 µm/ns=1 µm/ns | [S-L4] |
| **速度 `km/s → µm/ns`（正确）** | **`1 km/s = 1 µm/ns`** | 同上：`1e5 cm/s × 1e-5 µm/ns per cm/s = 1 µm/ns` | [S-L4] |

### A.2 压力 / 压强

| 换算 | 因式 | 推导链 | 溯源 |
|---|---|---|---|
| `GPa → Mbar` | `1e-2` | `1 GPa=1e9 Pa=1e9 dyne/cm2/10 = 1e10 dyne/cm2`（1 Pa=10 dyne/cm2）；`1 Mbar=1e12 dyne/cm2`；故 `1 GPa=1e10/1e12=1e-2 Mbar` | [S-L4] |
| `Mbar → dyne/cm2` | `1e12` | 定义：1 bar=1e5 Pa=1e6 dyne/cm2；1 Mbar=1e6 bar=1e12 dyne/cm2 | [S-L4] |
| `dyne/cm2 → bar` | `1e-6` | 1 bar=1e6 dyne/cm2 | [S-L4] |
| `dyne/cm2 → Mbar` | `1e-12` | 1 Mbar=1e12 dyne/cm2 | [S-L4] |
| `bar → Mbar` | `1e-6` | 1 Mbar=1e6 bar | [S-L4] |
| `GPa → dyne/cm2` | `1e10` | 由 A.2 第 1 行展开 | [S-L4] |
| **`J/cm3 → Mbar`** | **`1e-5`** | `1 J = 1e7 erg`；`1 erg/cm3 = 1 dyne/cm2`（能量密度≡压强）；故 `1 J/cm3 = 1e7 dyne/cm2 = 1e7·1e-12 Mbar = 1e-5 Mbar` | [S-L4] |
| `J/cm3 → GPa` | `1e-3` | `1e-5 Mbar / 1e-2 Mbar per GPa = 1e-3 GPa` | [S-L4] |

### A.3 比能 / 能量密度

| 换算 | 因式 | 推导链 | 溯源 |
|---|---|---|---|
| **`MJ/kg → Mbar·cm3/g`** | **`1e-2`** | `1 MJ=1e6 J`；`1 kg=1e3 g`；`1 MJ/kg=1e6 J/1e3 g=1e3 J/g`；又 `1 J/g = 1 J/cm3 × (1 g/cm3)/(ρ)` 中以单位密度归一：`1 J/g ÷ (g/cm3)⁻¹ = 1 J·cm3/g`；`1 J/cm3=1e-5 Mbar` ⇒ `1 J/g=1e-5 Mbar·cm3/g`；故 `1 MJ/kg=1e3·1e-5=1e-2 Mbar·cm3/g` | [S-L4]；与 [S-L1] SESAME docx 一致 |
| **`J/g → erg/g`** | **`1e7`** | `1 J=1e7 erg`；分母同为 g | [S-L4] |
| `Mbar·cm3/g → erg/g` | `1e9` | `1 Mbar=1e12 dyne/cm2=1e12 erg/cm3`；×`cm3/g` ⇒ `1e12 erg/g`？复核：`1 Mbar·cm3/g` 的能量密度形式 = `1e12 dyne/cm2 × cm3/g = 1e12 erg/g`。**但**由 `1 J/g=1e-5 Mbar·cm3/g` 与 `1 J/g=1e7 erg/g` 联立：`1e-5 Mbar·cm3/g = 1e7 erg/g` ⇒ `1 Mbar·cm3/g = 1e12 erg/g`。故因子为 `1e12` | [S-L4]（两条链一自洽） |
| `MJ/kg → erg/g` | `1e10` | `1 MJ/kg=1e-2 Mbar·cm3/g=1e-2·1e12 erg/g=1e10 erg/g` | [S-L4] |
| **`erg → J`** | **`1e-7`** | 定义：1 erg=1 dyne·cm；1 J=1e7 erg | [S-L4] |
| `keV → erg` | `1.602176634e-9` | `1 keV=1e3 eV`；`1 eV=1.602176634e-19 J`；`1e3·1.602176634e-19 J=1.602176634e-16 J`；×`1e7 erg/J = 1.602176634e-9 erg` | [S-L4] |
| `J → eV` | `6.241509074e18` | `1/1.602176634e-19` | [S-L4] |

### A.4 温度 / 能量（eV ↔ K ↔ keV）

| 换算 | 因式 | 推导链 | 溯源 |
|---|---|---|---|
| **`eV → K`** | **`11604.518`** | `1 eV = 1.602176634e-19 J`；`k_B=1.380649e-23 J/K`；`T=1.602176634e-19/1.380649e-23=1.1604518e4 K` | [S-L4]；与 [S-L1] 一致 |
| `K → eV` | `8.617333262e-5` | `1/11604.518`（即 `k_B[eV/K]`） | [S-L4] |
| `keV → eV` | `1e3` | 定义 | [S-L4] |
| `keV → K` | `1.1604518e7` | `1e3 eV × 11604.518 K/eV` | [S-L4] |
| **`log10` 温度 eV↔keV 位移** | **`±3.000`** | `log10(T_keV)=log10(T_eV/1000)=log10(T_eV)−3`；故 keV 版对数值 = eV 版 − 3.000 | [S-L4]；实测见 13.2.3 |

### A.5 不透明度 / 吸收系数

| 换算 | 因式 | 推导链 | 溯源 |
|---|---|---|---|
| `cm2/g` 保持 | `1` | 质量吸收系数为强度量，与密度线性组合：`κ[m⁻¹]=κ[cm2/g]·ρ[g/cm3]·100` | [S-L4] |
| `cm2/g → m2/kg` | `1e-1` | `1 cm2=1e-4 m2`；`1 g=1e-3 kg`；`1e-4/1e-3=1e-1` | [S-L4] |
| 自由程 `cm ↔ 1/(κρ)` | — | `λ[cm]=1/(κ[cm2/g]·ρ[g/cm3])` | [S-L4] |

### A.6 密度与数密度

| 换算 | 因式 | 推导链 | 溯源 |
|---|---|---|---|
| `g/cm3 → kg/m3` | `1e3` | `1e-3 kg / 1e-6 m3 = 1e3` | [S-L4] |
| `n_e` 由 `ρ,Zbar,A` | — | `n_e = ρ·N_A·Zbar/A`，`N_A=6.02214076e23 mol⁻¹` | [S-L4]；[S-L2] 项目 config |
| `amu(原子质量单位) → g` | `1.66053906660e-24` | 定义 | [S-L4] |
| `1/cm3 → 1/m3` | `1e6` | `1 m3=1e6 cm3` | [S-L4] |

### A.7 单位换算总表（速查）

| 量 | 从 | 到 | 因子 | 溯源 |
|---|---|---|---|---|
| 压强 | GPa | Mbar | ×1e-2 | [S-L4] |
| 压强 | bar | Mbar | ×1e-6 | [S-L4] |
| 压强 | dyne/cm2 | Mbar | ×1e-12 | [S-L4] |
| 压强 | Mbar | dyne/cm2 | ×1e12 | [S-L4] |
| 压强 | J/cm3 | Mbar | ×1e-5 | [S-L4] |
| 比能 | MJ/kg | Mbar·cm3/g | ×1e-2 | [S-L4] |
| 比能 | Mbar·cm3/g | erg/g | ×1e12 | [S-L4] |
| 比能 | J/g | erg/g | ×1e7 | [S-L4] |
| 能量 | erg | J | ×1e-7 | [S-L4] |
| 能量 | keV | erg | ×1.602176634e-9 | [S-L4] |
| 温度 | eV | K | ×11604.518 | [S-L4] |
| 温度 | K | eV | ×8.617333262e-5 | [S-L4] |
| 温度 | keV | eV | ×1e3 | [S-L4] |
| 温度(log) | eV | keV | −3.000 | [S-L4] |
| 速度 | cm/s | µm/ns | ×1e-5 | [S-L4] |
| 速度 | km/s | µm/ns | ×1 | [S-L4] |
| 不透明度 | cm2/g | m2/kg | ×0.1 | [S-L4] |
| 密度 | g/cm3 | kg/m3 | ×1e3 | [S-L4] |

### A.8 跨族单位体系对照（族间差异是最大坑）

| 族 | 压强单位 | 比能单位 | 温度单位 | 溯源 |
|---|---|---|---|---|
| SESAME/DPK 原库 | GPa | MJ/kg | K | [S-L1] SESAME docx |
| MULTI 内部 | Mbar | Mbar·cm3/g | eV | [S-L1] SESAME docx |
| Hyades ASCII | dyne/cm2 | erg/g | **keV** | [S-L1] Hyades doc |
| IONMIX `.cn4` 原生 | J/cm3 | J/g | eV | [S-L1] IONMIX 指南 §5.4 |
| MPQeos `.301` 原生 | GPa | MJ/kg | K | [S-L1] SESAME docx |
| Thermos `_Z.dat`（作废） | — | — | **eV** | [S-L2] Thermos/Readme |
| Thermos `_Zeff.dat`（现行） | — | — | **keV** | [S-L2] Thermos/Readme |

**禁止跨族复用单位结论**：例如 Hyades 的 `erg/g` 与 SESAME 的 `MJ/kg` 相差 1e10 倍，即便都叫"比能"也不可混用。每次读一个新族的数据，必须重新确认其单位，不得沿用上一族的换算。

---

## 附录 B 格式速查卡

每族一卡，六要素：触发条件 / 表头 / 字段 / 单位 / 计数公式 / 样本 / 陷阱。**触发条件**依据 `[S-L3] matter++/Readme.txt`（文件名/路径关键字分派，见第 1 章）。

### B.1 SESAME 4×15 定宽（默认族）

| 项 | 内容 |
|---|---|
| 触发 | 无任何特定关键字时**默认** |
| 表头 | 行 1：`table_id rho0 nr ne`（4 字段，每字段 15 字符） |
| 字段 | rho(nr)、de(ne)、e0(nr)、P(nr·ne)、T(nr·ne) |
| 单位 | rho g/cm3、de/e0/P Mbar 系、T K（转 eV） |
| 计数 | `4 + 2nr + ne + 2nr·ne`（with_e0）/ `4+nr+ne+2nr·ne`（no_e0） |
| 样本 | `matter++/mat_Al-1.0/AL_SIMPLE_PLANCK`（183 B）、`AL_eos`（152,165 B） |
| 陷阱 | EOS 线性坐标而 OPAC 对数坐标；两种 payload 布局须靠计数反解 |

### B.2 Hyades ASCII EOS

| 项 | 内容 |
|---|---|
| 触发 | 路径或文件名含 `hyades` |
| 表头 | 行 1 自由文本（材料+SESAME#）；行 2 `EOS# ZBAR ABAR DEN L` |
| 字段 | `NR NT RHO(NR) T(NT) P(NR·NT) E(NR·NT)` |
| 单位 | rho g/cm3、**T keV**、P dyne/cm2、E erg/g |
| 计数 | `L = 2 + NR + NT + 2·NR·NT` |
| 样本 | `matter++/hyades/sesame/eos_2051.dat`（73,611 B） |
| 陷阱 | 单位与 SESAME **完全不同**（keV/dyne/erg）；末尾补零与 DOS EOF `\x1a` |

### B.3 FEOS 原生 `.feos`

| 项 | 内容 |
|---|---|
| 触发 | 文件名含 `.feos` |
| 表头 | 行 0 十字段 `[Z,NR,NT,c1,c2,c3,rho0,T_ref_eV,B0,SESAME#]` |
| 字段 | rho 网格、T 网格、payload（**列序未定**） |
| 单位 | rho g/cm3、T_ref eV、未知 payload 单位 |
| 计数 | 行 0 固定 10 数；网格用单调性裁剪（NR 实测多 1 个 0.0 哨兵） |
| 样本 | `matter++/mat_Al-1.0/Al.feos`（3,628,968 B） |
| 陷阱 | payload 列序**无法从 PDF 还原** `[S-UNK]`；名实不符（`AL_eos.feos` 实为 SESAME） |

### B.4 MPQeos `.301`/`.304`/`.305`

| 项 | 内容 |
|---|---|
| 触发 | 文件名含 `.301`/`.304`/`.305` |
| 表头 | 行 1 `Id Density NR NT`（**每行 4×16 字符**；ID 宽 16/17 不定，须用空格正则） |
| 字段 | `[R(nr)][T(nt)][P][E][Z]` |
| 单位 | R g/cm3、T K、P GPa、E MJ/kg、Z 无量纲 |
| 计数 | `4 + nr + nt + 3·nr·nt` |
| 样本 | `matter++/mat_Al-1.0/FEOS/Al.feos.301`（620,139 B） |
| 陷阱 | 4×16 而非 4×15；Z 段实测含负值（语义待核）；T Kelvin 须转 eV |

### B.5 多群不透明度（F2，含 Thermos 输出）

| 项 | 内容 |
|---|---|
| 触发 | 默认（SESAME）或路径含 `Thermos`；LEDCOP 拆分件由复合扩展名 |
| 表头 | 行 1 `xxxx3nnn PLANCK M nr nt`；行 2 群边界 `E_lo E_hi` |
| 字段 | log(rho)(nr)、log(T)(nt)、log(κ)(nr·nt) |
| 单位 | rho g/cm3、T **eV**、κ cm2/g |
| 计数 | 每子表 `4+nr+nt+nr·nt`，共 ng 个子表串联 |
| 样本 | `matter++/mat_Ti/SNOP_LTE.PLANCK`（207,420 B）、`Thermos/mat_Al/Al_Planck.dat`（198,075 B） |
| 陷阱 | 全对数坐标；`PLANCK M` vs `ROSSELAND M` 标识；Zeff 表有 eV/keV 两套（差 3.000） |

### B.6 IONMIX `.cn4`

| 项 | 内容 |
|---|---|
| 触发 | 目录/扩展名 `.cn4` |
| 表头 | 行 1 `2i10 (ntemp,ndens)`；行 2 原子序数；行 3 相对份额；行 4 `i12 (ngrups)` |
| 字段 | 18 块：tplsma、densnn、12 个 2D 场、engrup、3 个 3D 不透明度场 |
| 单位 | T eV、n_ion cm⁻³、E J/g、P J/cm3、ngrups eV |
| 计数 | `ntemp+ndens+12·n2d+(ngrups+1)+3·ngrups·n2d` |
| 样本 | `matter++/Ionmix/al-imx-002.cn4`（552,192 B） |
| 陷阱 | 定宽 `e12.6`；打包指数 `0.638380-140`（缺 E）；NaN 占位 `-9.99999+990`；`deion_dn/deele_dn` 源码自注 not sure |

### B.7 IONMIX `.cnr`（legacy）

| 项 | 内容 |
|---|---|
| 触发 | 扩展名 `.cnr` |
| 表头 | 行 1–3 同 cn4；行 4 `4e12.6,i12` = `dlgden, log10(rho0), dlgtmp, log10(T0), ngrups` |
| 字段 | 7 块：zbar、enrgy、op2tr、op2tp、engrup、orgp、opgpe |
| 单位 | enrgy J/g；op2tr/op2tp 不透明度 |
| 计数 | **无 ntrad 于头部**，由余数反解 |
| 样本 | `matter++/Ionmix/al-imx-001.cnr`（508,500 B） |
| 陷阱 | 无 cn4 的 12 个 EOS 2D 场；`ntrad` 有时不可唯一确定 |

### B.8 ATOMIC/LEDCOP 主表 `*.txt`

| 项 | 内容 |
|---|---|
| 触发 | 目录 `ATOMIC` + `.txt` |
| 表头 | `Number of T/Rho/materials`；`Opacities in cm**2/gm, T in keV, density in gm/cc`（**内嵌单位**） |
| 字段 | 三段：灰度块、多群块、频率相关谱（3000/3900 点） |
| 单位 | κ cm2/g、**T keV**、ρ g/cc |
| 计数 | 锚点驱动，非固定行数（Al.txt 348,636 行） |
| 样本 | `matter++/ATOMIC/Al.NoFree`（55,383 B）；主表 `Al.txt`（13.5 MB） |
| 陷阱 | 温度网格**不可插值**、密度可插值；49/89 点两套；须锚点流式扫描 |

### B.9 LEDCOP 拆分件 `*.NoFree` / `*.AvSqFree`

| 项 | 内容 |
|---|---|
| 触发 | 文件名 `NoFree`/`AvSqFree` |
| 表头 | 4 数 `<魔数 0.1234567> <1.0> NR NT` |
| 字段 | `[log10 rho(NR)][log10 T(NT)][值(NR·NT)]` |
| 单位 | rho log10 g/cc、**T log10 keV** |
| 计数 | `4 + NR + NT + NR·NT` |
| 样本 | `matter++/ATOMIC/Al.GrayOpacity_PLANCK`（55,383 B，首行 `0.1234567E+000PLANCK 1 ...`） |
| 陷阱 | 魔数 0.1234567 是判定魔数；`PLANCK 1`/`PLANCK M` 标识位 |

### B.10 冷不透明度 `.coldopacity`

| 项 | 内容 |
|---|---|
| 触发 | 目录 `ColdOpacity` + 扩展名 `.coldopacity` |
| 表头 | 行 1 列名 `Eph  miu`；行 2 单位 `eV  cm2/g`（Tab 分隔） |
| 字段 | `Eph`、`miu` 两列 |
| 单位 | eV、cm2/g |
| 计数 | 列数 = 行 1 列数 = 行 2 列数；每行同列数 |
| 样本 | `matter++/ColdOpacity/Al.coldopacity`（11,357 B）；共 69 个 |
| 陷阱 | 两行头后有空行；空行不计入数据 |

### B.11 Hugoniot `.hug`

| 项 | 内容 |
|---|---|
| 触发 | 扩展名 `.hug` |
| 表头 | 首行 `#` 注释，列名+单位在方括号内 |
| 字段 | `Rho  T  P  E  Us  Up` 六列 |
| 单位 | **两写法**：FEOS 带缩放因子（`[1.0e+012 dyne/cm^2]`）；Hyades 裸单位（`[Mbar]`） |
| 计数 | 列数由数据行决定 |
| 样本 | `mat_Al-1.0/Al.feos.hug`（15,642 B）、`AL_eos.hug`（16,181 B） |
| 陷阱 | 同一族两种单位尺度；可"有表头无数据"（`AU_eos.hug` 81 B） |

### B.12 SNOP namelist `&daten`

| 项 | 内容 |
|---|---|
| 触发 | 扩展名 `.SNOP` / 文件名 `SNOP.INPUT` |
| 表头 | `&daten ... /` |
| 字段 | 见附录 B 表 T30（NT/NR/NG/NP/Z/RHO/T/X/IGROUP/F0/F1/FG/EQ/IDEG/LINEPRO/DREK/FACT/NSIGMA/NPLA/NROSS/NEPS/NZ） |
| 单位 | RHO g/cm3、**T1/T2/X1/X2 keV**、**F0/F1/FG eV** |
| 计数 | 不产生网格（kind=AUX） |
| 样本 | `matter++/SNOP/Be_40G.SNOP`、`matter++/mat_Ti/Ti_LTE.INPUT` |
| 陷阱 | **同 namelist 内 keV 与 eV 并存**；数组跨行续写；DREK 取值三处冲突 |

### B.13 Thermos `*.ini` 与伴随文件

| 项 | 内容 |
|---|---|
| 触发 | 路径含 `Thermos` |
| 表头 | `.ini`：四键 `ElementName/Temperature/Density/Frequency` |
| 字段 | 伴随 `_Planck.dat`/`_Rosseland.dat`/`_Z.dat`/`_Zeff.dat`（均为 F2 格式） |
| 单位 | `.ini` 未声明；`_Z.dat` eV（作废）、`_Zeff.dat` keV（现行） |
| 计数 | 各文件按 F2 计数 |
| 样本 | `Thermos/mat_Al/Al.ini`（795 B）、`Al_Zeff.dat`（7,891 B） |
| 陷阱 | **`_Z` vs `_Zeff` 差 3.000**；`Al.ini` Frequency 行末孤值 `4` |

### B.14 材料级幂律 `.readme`

| 项 | 内容 |
|---|---|
| 触发 | 文件 `*.readme` / `Readme.txt`（mat_* 目录） |
| 表头 | 无固定，纯文本 `REM` 注释 |
| 字段 | `c, a, b` 或 `a, b, c`（型 A/B） |
| 单位 | k cm2/g、T keV 或 eV（逐文件）、rho g/cc |
| 计数 | 不适用 |
| 样本 | `mat_Au/Au_Rosseland_2003POPHammerRosen.readme`（90 B）、`mat_Ba/Readme.txt`（403 B） |
| 陷阱 | 型 A（`a`=温度指数）与型 B（`a`=ln 前系数）字母含义相反；表名与正文可能互换 |

### B.15 曲线/常数 `.dat` / `.xml` / `.txt`

| 项 | 内容 |
|---|---|
| 触发 | 文件名（`density.dat`/`Albedo.xml`/`AtomicWeightTable.txt` 等） |
| 表头 | 注释头或 XML 属性 |
| 字段 | 各异 |
| 单位 | 内嵌注释声明 |
| 计数 | 各异 |
| 样本 | `density.dat`（4,993 B）、`Albedo.xml`（1,192 B） |
| 陷阱 | `Albedo.xml` Type=0/1/2 三公式且 Au 重复 5 条；`density.dat` Z=85/87 密度人为设 10 |

---

## 附录 C 实测样本索引

以下全部为 `src/Multi1D++Portable20241128/` 下的真实文件，字节数由 `os.path.getsize` 实测，表头行逐字抄录。**凡是"表头"列写 `[S-UNK]` 者，指该文件无表头或未读取到表头**。

| # | 相对路径 | 字节数 | 关键表头行 | 族 |
|---|---|---|---|---|
| 1 | `matter++/Readme.txt` | 530 | `material.baseµÄÐÞ¸Ä¹æÔò`（GBK 编码） | 分派 |
| 2 | `matter++/material.base` | 103,452 | `MATERIAL MID9` | 索引 |
| 3 | `matter++/Albedo.xml` | 1,192 | `<?xml version="1.0" encoding="utf-8" ?>` | 曲线 |
| 4 | `matter++/ScalingLaws.dat` | 3,937 | `local freepath_H(r,t)` | 公式 |
| 5 | `matter++/density.dat` | 4,993 | `# NIST:X-Ray Mass Attenuation Coefficients` | 常数 |
| 6 | `matter++/Reflectivity.dat` | 284 | `# Reflectivity at room temperature` | 常数 |
| 7 | `matter++/AtomicWeightTable.txt` | 21,590 | `Isotope data from http://physics.nist.gov/...` | 常数 |
| 8 | `matter++/DatabaseIndex.xml` | 15,734 | `<EOS No="11" Material="Deuterium+tritium" ...>` | 索引 |
| 9 | `matter++/idata.dat` | 4,482 | `[S-UNK]` 未读取表头 | 常数 |
| 10 | `matter++/material.list` | 0 | （空文件） | 索引 |
| 11 | `matter++/Thermos/Readme.txt` | 576 | `Opacity data generated using opadata.exe` | Thermos |
| 12 | `matter++/Thermos/mat_Al/Al.ini` | 795 | `ElementName=Al` | Thermos |
| 13 | `matter++/Thermos/mat_Al/Al_Planck.dat` | 198,075 | `00000000       PLANCK M        2.2000000e+001 2.1000000e+001` | F2 |
| 14 | `matter++/Thermos/mat_Al/Al_Rosseland.dat` | 198,075 | `00000000       ROSSELAND M     2.2000000e+001 2.1000000e+001` | F2 |
| 15 | `matter++/Thermos/mat_Al/Al_Zeff.dat` | 7,891 | `00000000        0.60000000E+01 2.2000000e+001 2.1000000e+001` | F2 |
| 16 | `matter++/Thermos/mat_Al/Al_Z.dat` | 7,891 | 同 15（逐字节同，数据区差 3.000） | F2 |
| 17 | `matter++/SNOP/opbe.inhalt` | 2,274 | `********* EINGANGSPARAMETER ***********` | SNOP |
| 18 | `matter++/SNOP/Be_40G.SNOP` | 1,135 | `&daten` | SNOP |
| 19 | `matter++/SNOP/Be_40G.PLANCK` | — | `20203000      PLANCK M        0.20000000E+02 0.20000000E+02` | F2 |
| 20 | `matter++/SNOP/Be_40G.ROSS` | — | （成对 ROSSLAND 表） | F2 |
| 21 | `matter++/SNOP/### Generated by SNOP` | 0 | （空文件） | SNOP |
| 22 | `matter++/ColdOpacity/Al.coldopacity` | 11,357 | `Eph\tmiu` / `eV\tcm2/g` | 冷不透 |
| 23 | `matter++/mat_Al-1.0/README` | 617 | `Tables for Aluminium` | 幂律 |
| 24 | `matter++/mat_Al-1.0/AL_SIMPLE_PLANCK` | 183 | `.17010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01` | SESAME |
| 25 | `matter++/mat_Al-1.0/AL_eos` | 152,165 | `37181000    .27000000E+01  .66000000E+02  .74000000E+02` | F1 |
| 26 | `matter++/mat_Al-1.0/AL_eos.hug` | 16,181 | `# Rho[g/cm^3]  T [eV]  P [Mbar]  E [erg/g]  Us [km/s]  Up [km/s]` | hug |
| 27 | `matter++/mat_Al-1.0/Al.feos.hug` | 15,642 | `# Rho [1.0e+000 g/cm^3] ... P [1.0e+012 dyne/cm^2] ...` | hug |
| 28 | `matter++/mat_Al-1.0/Al.feos` | 3,628,968 | `1.20600000e+01 1.92000000e+02 6.90000000e+01 1.00000000e+00 ...` | FEOS |
| 29 | `matter++/mat_Al-1.0/FEOS/Al.feos.301` | 620,139 | `37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01` | .301 |
| 30 | `matter++/mat_Au-1.0/AU_eosd` | 145,608 | `0.27000000E+04 0.19300003E+02 0.10100000E+03 0.23000000E+02` | F1 |
| 31 | `matter++/mat_Au-1.0/AU_eos.hug` | 81 | `# Rho[g/cm^3]  T [eV]  P [Mbar] ...`（**无数据**） | hug |
| 32 | `matter++/mat_Au/Au_Rosseland_2003POPHammerRosen.readme` | 90 | `Opacity generated by power law l = c * T^a*rho^b` | 幂律 |
| 33 | `matter++/mat_Sn/Sn_Planck_1987JQSRT.readme` | 94 | 同上 | 幂律 |
| 34 | `matter++/mat_Sn/Sn_Rosseland_1987JQSRT.readme` | 92 | 同上 | 幂律 |
| 35 | `matter++/mat_Ge/Ge_Planck_1999Minguez.readme` | 94 | 同上 | 幂律 |
| 36 | `matter++/mat_Ge/Readme.txt` | 939 | `Ge_2002FED_Planck & Ge_2002FED_Rosseland` | 幂律 |
| 37 | `matter++/mat_Ba/Readme.txt` | 403 | `Ba_1987JQSRT_Planck/Rosseland` | 幂律 |
| 38 | `matter++/mat_Eu/Eu_Planck_1987JQSRT.readme` | 94 | `Opacity generated by power law ...` | 幂律 |
| 39 | `matter++/mat_CELIA/C.ZEFF.readme` | 223 | `20170425:` | 幂律 |
| 40 | `matter++/mat_CELIA/Readme.txt` | 92 | `C.ZEFF_old, Te in eV, replace by Carbon.Zeff` | 幂律 |
| 41 | `matter++/mat_Ti/readme.txt` | 133 | `[SNOP from Zhang Jiyan]` | 血缘 |
| 42 | `matter++/mat_Ti/SNOP_LTE.PLANCK` | 207,420 | `27003000      PLANCK M        0.20000000E+02 0.20000000E+02` | F2 |
| 43 | `matter++/Ta2O5/Ta2O5_mop.readme` | 343 | `MATERIAL MID110873` | 材料 |
| 44 | `matter++/Ta2O5/Ta2O5.Rho-T.ist` | 1,725 | `# T = 0.000000e+000 [1.000000e+000 eV]:` | FEOS aux |
| 45 | `matter++/Ta2O5/Ta2O5.Rho-T-P.mnt` | 6,730 | `# NRho  NT  NP` | FEOS aux |
| 46 | `matter++/Ta2O5/Ta2O5.Rho-P.ist4gnuplot` | 18,759 | `# T[1.000000e+000 eV]\tRho[...]\tP[...]` | FEOS aux |
| 47 | `matter++/Ta2O5/Ta2O5.data.txt` | 1,610,910 | `0\t0\t 0.00000000e+00\t 0.00000000e+00\t ...` | FEOS aux |
| 48 | `matter++/mat_B/B.PAR` | 6,546 | `%%%...%%% This file contains all the data needed ...` | FEOS aux |
| 49 | `matter++/mat_B/B.critical.dat` | 54,692 | `# Critical point: Tc = 20675.94 K, Pc = 35091.45 bar, ...` | FEOS aux |
| 50 | `matter++/mat_B/B.isobaric.dat` | 2,657 | `# Calculated isobaric expansion data (P ~= 0) ...` | FEOS aux |
| 51 | `matter++/mat_B/B.data.txt` | 1,677,513 | `0\t0\t 0.00000000e+00\t ...` | FEOS aux |
| 52 | `matter++/mat_B/B.mexport` | 1,845,656 | `0104005   101   160   r        0        0   1 ...` | FEOS aux |
| 53 | `matter++/mat_O/O.cst` | 929,594 | `Isotherme T = 0 Kelvin` | FEOS aux |
| 54 | `matter++/hyades/sesame/eos_2051.dat` | 73,611 | `GOLD        LANL SESAME #2700-304 DATED: 81678 101582` | Hyades |
| 55 | `matter++/hyades/sesame/eos_32.hug` | 12,685 | `# Rho[g/cm^3]  T [eV]  P [Mbar] ...` | hug |
| 56 | `matter++/hyades/Opacity/opc_1022.dat` | 45,258 | `QUARTZ      LANL SESAME #17380 DATED:  80679  12681` | Hyades |
| 57 | `matter++/hyades/qeos/qeos_115.dat` | 366,222 | `COPPER      LLNL-QEOS Dated: 082802` | Hyades |
| 58 | `matter++/hyades/tmp.dat` | 181 | `1.e-9,2.65e+6` | 曲线 |
| 59 | `matter++/ATOMIC/Al.NoFree` | 55,383 | `0.1234567E+000 1.0000000e+000 5.0000000e+001 6.9000000e+001` | LEDCOP |
| 60 | `matter++/ATOMIC/Al.GrayOpacity_PLANCK` | 55,383 | `0.1234567E+000PLANCK 1        5.0000000e+001 6.9000000e+001` | LEDCOP |
| 61 | `matter++/ATOMIC/Al.AvSqFree` | 55,383 | `0.1234567E+000 1.0000000e+000 5.0000000e+001 6.9000000e+001` | LEDCOP |
| 62 | `matter++/ATOMIC/Al.MultiGroupOpacity_PLANCK` | 5,486,085 | `0.1234567E+000PLANCK M        5.0000000e+001 6.9000000e+001` | LEDCOP |
| 63 | `matter++/mat_C-1.0/CSi2.5_mopp95` | 2,858,265 | `6140003        PLANCK M         4.3000000e+01  4.3000000e+01` | F2 |
| 64 | `matter++/Ionmix/al-imx-002.cn4` | 552,192 | `        21        21` | cn4 |
| 65 | `matter++/Ionmix/al-imx-001.cnr` | 508,500 | `        21        21` | cnr |
| 66 | `matter++/mat_Vacuum/Vacuum_Opacity.dat` | 186 | `0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001` | SESAME |
| 67 | `matter++/CH/material.user` | 620 | `MATERIAL MID106120` | 索引 |
| 68 | `matter++/CH/CHSi10_eos.IN` | 72,586 | `           1214  6.725700e+000 5.8000000e+001 3.9000000e+001` | 曲线 |
| 69 | `matter++/mat_CPC/AU.INV` | 380,518 | ` 1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02` | INV |
| 70 | `matter++/mat_Ce/Cerium.critical.dat` | 2,111 | `# Critical point: Tc = 2006.73 K, Pc = 23032.87 bar, ...` | FEOS aux |
| 71 | `matter++/Crystal/CrystalData.dat` | 588 | `material\tplane\td (nm)\tmin 竹 (nm)\t...` | 曲线 |
| 72 | `matter++/Crystal/LatticeSpacing.dat` | 509 | `Channel\tDiffraction\tcrystal\tLattice spacing/A\t...` | 曲线 |
| 73 | `matter++/Crystal/names.txt` | 86 | `TIAP: thalium acid phthalate` | 曲线 |
| 74 | `matter++/RadiativeCoolingRates/readme.txt` | 429 | `Ref: 1977ADNDT20.397(Post)_...` | 曲线 |
| 75 | `matter++/HeatCapacity/Readme.txt` | 91 | `Electron-Phonon Coupling and ...` | 曲线 |
| 76 | `matter++/XrayMassCoef/XrayMassCoef.tab1` | — | `Z \t Element \t Z/A \t I(eV) \t Density(g/cm3)` | 曲线 |
| 77 | `matter++/PROPACEOS/Readme.txt` | 120 | （版权保护声明，GBK） | 缺口 |
| 78 | `doc/SNOP.MANUAL` | 6,604 | `1. GENERAL` | SNOP |
| 79 | `doc/muParser.txt` | 4,073 | `muParser - fast math parser for C++` | 公式 |
| 80 | `doc/Structure_of_ASCII_data_files.txt` | 82 | `1\t0\t2\t1\t12` | 缺口 |
| 81 | `matter++/mat_Al-1.0/FEOS/Al.feos.304` | 620,139 | ` 37170304       2.70000000e+00 1.92000000e+02 6.90000000e+01` | .304 |
| 82 | `matter++/mat_Al-1.0/FEOS/Al.feos.305` | 620,139 | ` 37170305       2.70000000e+00 1.92000000e+02 6.90000000e+01` | .305 |
| 83 | `matter++/mat_Be-1.0/BE_eos.info` | 611 | `files BE_eos_e and BE_eos_i  (Beryllium)` | 血缘 |
| 84 | `matter++/mat_C-1.0/Carbon.info` | 1,150 | `file Carbon (Carbon, Diamond-like-Carbon, and Polystyrene)` | 血缘 |
| 85 | `matter++/mat_Others/Mix20keV.info` | 965 | `files Mix20keV.PLANCK, Mix20keV.ROSS, and Mix20keV.EPS  (Doped Beryllium)` | 血缘 |
| 86 | `matter++/mat_Others/CH10Water.info` | 27 | `Calculated by Dong Yunsong` | 血缘 |
| 87 | `matter++/SiO2/eos_21.sesame` | 2,381,499 | ` 0.0000000E+000 1.0000000E+000 4.3000000e+001 1.7650000E+003` | SESAME |
| 88 | `matter++/Ta2O5/PowerLawTa2O5_EOS.SESAME` | 2,217 | ` 0.1234567E+000 1.0000000E+000 3.0000000e+000 1.9000000E+001` | SESAME |
| 89 | `matter++/mat_Au/Au_2003POPHammerRosen_EOS.SESAME` | 6,495 | ` 0.1234567E+000 1.0000000E+000 6.0000000e+000 3.1000000E+001` | SESAME |
| 90 | `matter++/hyades/qeos/qeos_392.dat.par` | 4,530 | `%%%...%%% This file contains all the data needed ...` | FEOS aux |
| 91 | `matter++/mat_Al-1.0/Al.feos.par` | 4,530 | `File-Format = 1    % 1: FEOS (recommended), 2: SESAME 301/304/305` | FEOS aux |
| 92 | `matter++/mat_Al-1.0/Al.feos.Rho-P.ist` | 1,802 | `# T = 0.000000e+000 [1.000000e+000 eV]:` | FEOS aux |
| 93 | `matter++/mat_Al-1.0/Al.feos.Rho-P.ist4gnuplot` | 2,133 | `# T[1.000000e+000 eV]\tRho[...]\tP.ist4gnuplot[...]` | FEOS aux |
| 94 | `matter++/Ta2O5/Ta2O5.Rho-P.ise` | 13,653 | `# S = 1.434441e+011 [1.000000e+000 erg/(g*eV)]:` | FEOS aux |
| 95 | `matter++/Ta2O5/Ta2O5.Rho-T.isc` | 1,563 | `# Rho = 1.000000e-003 [1.000000e+000 g/cm^3]:` | FEOS aux |
| 96 | `matter++/mat_S/Ta2O5.Rho-PTF.ise`（同类） | 1,788 | `# Rho [1.000000e+000 g/cm^3]  PTF [1.000000e+012 dyne/cm^2]` | FEOS aux |
| 97 | `matter++/mat_C-1.0/CSi2.5_mopr95` | 2,858,265 | `6140002        ROSSELAND M      4.3000000e+01  4.3000000e+01` | F2 |
| 98 | `matter++/mat_Ge/New File.txt` | — | `[S-UNK]` 未读取 | 幂律 |
| 99 | `matter++/mat_CELIA/Readme.txt` | 92 | `C.ZEFF_old, Te in eV, ...` | 幂律 |
| 100 | `matter++/SNOP/C_20GSNOP.PLANCK` | — | `[S-UNK]`（成对表） | F2 |

> 注：少量条目（如 # 19/# 20/# 31/# 56 的部分）以"—"表示本次未单独实测字节数；凡在别处已实测者以实测值填入。**禁止推断未实测的字节数**。

---

## 附录 D 检索与校验片段

本附录给出可直接复用的**计数守恒校验**片段：语言中立伪码 + 少量 Python。核心思想：**先由文件头部参数算出期望数字个数，再统计文件内实际数字个数，二者不等则判格式错误或布局误判**。这是跨族通用的第一道闸门。

### D.1 语言中立伪码

```
function count_check(text, family):
    # 步骤 1：剥离头部的结构性行，得到"数值区"
    # 各族的结构行数不同（见 D.2），由 family 决定
    numbers = lex_all_floats(text)         # 全文扫描所有浮点/整数 token
    hdr     = parse_header(text, family)   # 解出 nr, nt, ne, ng, ntemp, ndens ...

    # 步骤 2：按族选计数公式
    switch family:
        case "multi_inverted_eos":
            if layout == "with_e0":  expected = 4 + 2*nr + ne + 2*nr*ne
            else:                    expected = 4 + nr + ne + 2*nr*ne
        case "multi_opacity_gray":   expected = 4 + nr + nt + nr*nt
        case "multi_opacity_mg":     expected = 4 + nr + nt + ng*nr*nt  # ng 个子表
        case "hyades_eos":           expected = 2 + nr + nt + 2*nr*nt
        case "mpqeos":               expected = 4 + nr + nt + 3*nr*nt
        case "ledcop_zeff":          expected = 4 + nr + nt + nr*nt
        case "cn4":
            n2d = ntemp*ndens
            expected = ntemp + ndens + 12*n2d + (ngrups+1) + 3*ngrups*n2d
        case "cnr":
            expected = "由余数反解 ntrad，不固定"
        default:                     return UNKNOWN

    # 步骤 3：比较
    if numbers.seen == expected:     return OK
    else:                            return COUNT_MISMATCH(seen, expected)
```

**关键纪律**：`COUNT_MISMATCH` **不可静默处理**——不得"取前 expected 个"或"补零到 expected"，必须显式抛错并报告 `seen/expected`，因为不匹配通常意味着**布局判错**（如把 `with_e0` 当 `no_e0`）或**文件被截断**。

### D.2 各族头部结构行数（剥离用）

| 族 | 头部结构行 | 说明 |
|---|---|---|
| multi_inverted_eos | 首行 4 数 | `table_id rho0 nr ne` |
| multi_opacity_gray | 首行 4 数 | `xxxx3nnn LABEL nr nt`（LABEL 非数字，不计入） |
| multi_opacity_mg | 首 2 行 | `[表头 4 数][群边界 2 数]`，每子表重复 |
| hyades_eos | 首 2 行 | 第 1 行纯文本、第 2 行 `id zbar abar rho0 L`（5 数） |
| mpqeos | 首 1 行 | `Id Density NR NT`（4 数，注意 Id 定宽不定） |
| ledcop_zeff | 首 1 行 | `<魔数><1.0> NR NT`（4 数） |
| cn4 | 首 4 行 | `2i10 / 文本+5i10 / 文本+5e10.2 / i12`（第 4 行 1 数） |
| cnr | 首 4 行 | 前 3 行同 cn4；第 4 行 5 数 |

### D.3 Python 片段

```python
import re

# 通用浮点 token 器：兼容 Fortran 打包指数（缺 E）与两种尾数风格
_PACKED_EXP = re.compile(r'(\d\.\d{6})([-+]\d{3})')          # 0.638380-140 → 0.638380E-140
_ANY_NUM    = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][-+]?\d+)?')

def restore_packed_exp(s: str) -> str:
    """修复 E12.6 Fortran 写出时被丢弃的指数 E。"""
    return _PACKED_EXP.sub(r'\1E\2', s)

def lex_numbers(text: str):
    """提取全文所有数值 token，返回 float 列表。"""
    return [float(t.replace('D', 'E').replace('d', 'e'))
            for t in _ANY_NUM.findall(text)]

def check_multi_inverted_eos(path: str):
    with open(path, 'r', errors='replace') as fh:
        raw = fh.read()
    nums = lex_numbers(restore_packed_exp(raw))
    table_id, rho0, nr, ne = nums[0], nums[1], int(nums[2]), int(nums[3])
    seen_with = 4 + 2 * nr + ne + 2 * nr * ne
    seen_no   = 4 +     nr + ne + 2 * nr * ne
    n = len(nums)
    if n == seen_with:
        return ('with_e0', nr, ne, n)
    elif n == seen_no:
        return ('no_e0', nr, ne, n)
    else:
        raise ValueError(f'COUNT_MISMATCH: seen={n}, '
                         f'with_e0={seen_with}, no_e0={seen_no}')
```

### D.4 计数守恒校验的实际价值

以 `matter++/mat_Al-1.0/AL_eos` 为例：首行 `37181000 .27000000E+01 .66000000E+02 .74000000E+02`，即 `nr=66, ne=74`。期望值 `with_e0 = 4+2·66+74+2·66·74 = 4+132+74+9768 = 9978`。实测数字个数应等于 9978（此为第 2 章实测锚点之一）。若不编解码直接读，难以判断 payload 是 `with_e0` 还是 `no_e0`；两条公式给出的期望值分别为 9978 与 9845，**实测落在 9978 即唯一确定 `with_e0` 布局**——这就是"用计数反解布局"的机制。

对多群不透明度（F2）：每子表 `4+nr+nt+nr·nt`，`ng` 个子表串联，总期望 `ng·(4+nr+nt+nr·nt)`（各子表 nr/nt 可不同）。若某文件总计数不匹配任一整数值，则可能 `ng` 估计错误或子表数不符——须逐子表切分后再逐块校验，不能整体一次比较。

---

## 附录 E 实现现状与已知缺口

**定位声明**：本附录记录的是 Multi1D++ 数据格式在本项目 Python 侧的**实现现状**，其**不完整、将被修订**，故**不作为本文档主线**。本文档的主线是"格式本身怎么定义"（第 0–14 章）；本附录仅作备忘与缺口登记，凡与前面章节冲突者以前面章节为准。

### E.1 有专门解析器的族

当前已实现专门解析器的族包括：MULTI 反演 EOS（F1）、MULTI 多群不透明度/Zeff/NLTE/EPS（F2）、Hyades/SESAME ASCII（F3）、MPQeos/FEOS（F4）、LEDCOP/ATOMIC（F5）、IONMIX `.cn4`/`.cnr`、冷不透明度 `.coldopacity`、雨贡纽 `.hug`、SNOP namelist、FEOS 辅助文件等。其中 **`.cn4` 是唯一实现"完整解码 + 读写 + 逐字节往返"的格式**。

### E.2 已知缺口（按严重程度）

| # | 缺口 | 原因 | 处置 |
|---|---|---|---|
| 1 | **FEOS 原生 `.feos` payload 列序不可还原** | FEOS PDF §16.2 抽取伪影，列序无法从文档可靠恢复 | 行 0 十字段 + rho/T 网格已解码；payload 存 `raw_values`，标 `[S-UNK]` |
| 2 | **PROPACEOS 无公开格式文档** | 版权保护（`matter++/PROPACEOS/Readme.txt` 明文）；FLASH 圈 opacplot2 有代码但许可问题未公开 | 整体标 `[S-UNK]`，不实现 |
| 3 | **`doc/Structure_of_ASCII_data_files.txt` 来源不明** | 仅 82 字节的三行整数矩阵，无上下文 | 标 `[S-UNK]`，不作格式依据 |
| 4 | **`.cn4` 的 `deion_dn`/`deele_dn` 单位** | 源码 `abjt_03.f` 自注 "(not sure)" | 控制字典标 unknown |
| 5 | **`.cnr` 头部 4 网格参数** | 用户指南未文档化，由 `write` 语句位置推断 | 标 `inferred`（非 unknown） |
| 6 | **FEOS `*.data.txt` 列名** | 本地无文档 | 列名用 `colN`，unit=unknown |
| 7 | **Crystal / PowerLaws / Reflectivity / XrayMassCoef / RadiativeCoolingRates 无专用解析器** | 无格式文档，仅被通用兜底解析器覆盖 | 单位/语义 unknown |
| 8 | **Hyades `coldopac.dat` / `ionpot.dat`** | 无专门解析器 | 走通用兜底 |
| 9 | **`.feos` 名实不符** | `AL_eos.feos` 实测与 `AL_eos` 字节相同（名 FEOS 实 SESAME） | 须内容/计数兜底判定 |
| 10 | **`material.base` 非数据表** | 是材料主索引（251 块） | 由注册表层解析，非数据族解析器 |

### E.3 与本文档的关系

本文档（第 0–14 章 + 附录 A–D、F）**不引用**本项目任何解析器实现，只引上游原始文档与数据文件自身。因此上表任何缺口都**不影响**本文档对格式本身的描述：凡上游文档或文件内嵌声明能确定者，本文档给出结论；否则标 `[S-UNK]`。实现侧的缺口与格式侧的缺口**不是同一件事**——例如某族"无解析器"不代表"无格式定义"，反之"有解析器"也不代表"格式已被上游文档确认"。

---

## 附录 F 参考书目

### F.1 本地源（相对 `src/Multi1D++Portable20241128/`，附字节数）

| 源 | 字节数 | 覆盖 | 溯源级别 |
|---|---|---|---|
| `matter++/Readme.txt` | 530 | 格式分派规则 | [S-L3] |
| `doc/SNOP.MANUAL` | 6,604 | SNOP namelist 完整规范 | [S-L1] |
| `doc/muParser.txt` | 4,073 | 26 函数 / 15 运算符 | [S-L1] |
| `doc/Structure_of_ASCII_data_files.txt` | 82 | 来源不明（缺口） | [S-UNK] |
| `matter++/Thermos/Readme.txt` | 576 | 无 EOS 元素、eV/keV 声明 | [S-L2] |
| `matter++/PROPACEOS/Readme.txt` | 120 | 版权保护声明 | [S-L2] |
| `matter++/Albedo.xml` | 1,192 | 反照率幂律 | [S-L2] |
| `matter++/ScalingLaws.dat` | 3,937 | 自由程标度律 | [S-L2] |
| `matter++/density.dat` | 4,993 | NIST 元素常数 | [S-L2] |
| `matter++/Reflectivity.dat` | 284 | 室温反射率（仅注释） | [S-L2] |
| `matter++/AtomicWeightTable.txt` | 21,590 | 原子量 | [S-L2] |
| `matter++/DatabaseIndex.xml` | 15,734 | 数据库索引 | [S-L2] |
| `matter++/material.base` | 103,452 | 材料主索引 | [S-L2] |
| `matter++/mat_Al-1.0/README` | 617 | Al 表说明 | [S-L2] |
| `matter++/mat_Ba/Readme.txt` | 403 | Ba 幂律（keV/eV 双式） | [S-L2] |
| `matter++/mat_Ge/Readme.txt` | 939 | Ge 幂律（型 B） | [S-L2] |
| `matter++/mat_Au/Au_Rosseland_2003POPHammerRosen.readme` | 90 | Au Ross 系数 | [S-L2] |
| `matter++/mat_Sn/Sn_Planck_1987JQSRT.readme` | 94 | Sn Planck 系数 | [S-L2] |
| `matter++/mat_Sn/Sn_Rosseland_1987JQSRT.readme` | 92 | Sn Ross 系数 | [S-L2] |
| `matter++/mat_CELIA/Readme.txt` + `C.ZEFF.readme` | 92 + 223 | Zeff eV→keV 替换 | [S-L2] |
| `matter++/mat_Ti/readme.txt` | 133 | Ti 血缘 | [S-L2] |
| `matter++/mat_Others/Mix20keV.info` | 965 | 掺杂铍表说明 | [S-L2] |
| `matter++/SNOP/opbe.inhalt` | 2,274 | 一次 SNOP 运行参数回显 | [S-L2] |
| `matter++/SNOP/Be_40G.SNOP` | 1,135 | namelist 实例 | [S-L2] |
| `doc/MULTI使用的SESAME数据文件格式.docx` | 183,025 | SESAME/MULTI 全谱（第 7、8 章源） | [S-L1] |
| `matter++/hyades/Hyades 数据格式说明.doc` | 64,000 | Hyades 格式（第 9 章源） | [S-L1] |
| `matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx` | 33,218 | LEDCOP 格式（第 11 章源） | [S-L1] |
| `doc/multi1d7.6/manual` | 13,797 | FT12 输入/fort.10 输出 | [S-L1] |
| `doc/FEOS/Info.txt` + `doc/FEOS/*.pdf` | 2,475 + 4 PDF | FEOS 血统（第 10 章源） | [S-L1] |

### F.2 网络核验源

**待核验清单（本次写作未联网核验，一律标 `[S-UNK]`，不列具体 URL）**：

| # | 待核验项 | 用途 | 状态 |
|---|---|---|---|
| 1 | K. Eidmann, Laser and Particle Beams 12(2), 223–244 (1994) | SNOP 物理出处 | [S-UNK] 未联网核验 |
| 2 | Tsakiris & Eidmann, 1987JQSRT38 | Ba/Sn/Eu 幂律来源 | [S-UNK] 未联网核验 |
| 3 | Hammer & Rosen, 2003POP | Au 幂律来源 | [S-UNK] 未联网核验 |
| 4 | Fusion Engineering and Design 60 (2002) 17–25 | 型 B 幂律来源 | [S-UNK] 未联网核验 |
| 5 | M. Murakami, J. Meyer-ter-Vehn, R. Ramis, J. X-Ray Sci. Tech. 2, 127–148 (1990) | Al 幂律来源 | [S-UNK] 未联网核验 |
| 6 | NIST X-Ray Mass Attenuation Coefficients Table 1 | `density.dat` 来源 | [S-UNK] 未联网核验（URL 见文件注释） |
| 7 | Post 1977ADNDT20.397 | 辐射冷却率 | [S-UNK] 未联网核验 |
| 8 | Coppola 2011MNRAS415 | 冷却函数（H/D/He/Li） | [S-UNK] 未联网核验 |
| 9 | 2000PRE62_1_145 | 反射率/碰撞频率 | [S-UNK] 未联网核验 |
| 10 | WorkOp-III:94（第三届国际不透明度研讨会 Final Report） | Au 自由程 | [S-UNK] 未联网核验 |
| 11 | Zeldovich & Raizer (1966) p.260 式 5.23/5.24 | H/Be 自由程 | [S-UNK] 未联网核验 |
| 12 | Lindl 1995 eqn 135 | Au 反照率 | [S-UNK] 未联网核验 |
| 13 | G. Mishra, 2018HEDP | Al/W/Au/Pb/U 反照率 | [S-UNK] 未联网核验 |
| 14 | R. Ramis et al. 1988CPC49（MULTI 原始论文） | MULTI 血统 | [S-UNK] 未联网核验 |
| 15 | Jiang Shaoen et al., 物理学报 53 (2004) | Au 反照率 | [S-UNK] 未联网核验 |

**核验纪律（重申）**：网络内容仅用于书目信息与本地缺失的编码约定补白；任何网络结论须独立标注 `[S-WEB]` 并附 URL + 访问日期；**与本地冲突时以本地为准**并显式记录差异。本次写作**未进行联网核验**，故上表所有条目保持 `[S-UNK]`，不编造 URL。

### F.3 溯源速查表（表 T36）

| 记号 | 含义 | 本文档典型用例 |
|---|---|---|
| `[S-L1]` | 上游手册明文 | `[S-L1] doc/SNOP.MANUAL §2` |
| `[S-L2]` | 数据文件内嵌声明 | `[S-L2] matter++/Thermos/Readme.txt` |
| `[S-L3]` | 程序约定默认 | `[S-L3] matter++/Readme.txt` |
| `[S-L4]` | 推导（含量纲链） | `[S-L4] 1 keV=1e3 eV` |
| `[S-UNK]` | 本地无依据，不猜测 | `[S-UNK] Albedo.xml "heV" 无定义` |
| `[S-WEB]` | 网络核验（须 URL+日期） | （本次未使用） |

---

## 附录图

### 图 F10 各族的"表头-网格-payload"三段通用骨架

```
                    ┌─────────────────────────────────────────────┐
                    │  ① 表头区 (Header)                           │
                    │     · 表号 / 类型标识 / 维度 (nr, nt, ne, ng) │
                    │     · 单位若内嵌则在此声明                    │
                    ├─────────────────────────────────────────────┤
                    │  ② 网格区 (Grid)                             │
                    │     · 自变量数组：rho[], T[], de[], E_group[] │
                    │     · 线性 (EOS) 或 log10 (OPAC/Zeff/NLTE)   │
                    │     · T-major: z[i*nt + j]                   │
                    ├─────────────────────────────────────────────┤
                    │  ③ Payload 区 (Data)                         │
                    │     · 二维场 (nr×nt) 或三维场 (ng×nr×nt)      │
                    │     · 计数守恒校验的落点                      │
                    └─────────────────────────────────────────────┘

各族差异只在这三段的"具体实现"：
  SESAME 4×15   : 定宽，三段连续；表头 4 数
  Hyades        : 表头 2 行(1 文本+5 数)，单位 CGS
  多群 OPAC(F2) : 表头+群边界成对，ng 个子表串联
  cn4           : 表头 4 行，18 块(网格与 payload 交错)
  .feos         : 表头 10 数，payload 列序未知 [S-UNK]
```

### 图 F11 全局文档导航图

```
                        MultiEOSOP格式说明.md
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   【前置】                  【上编·机制】              【下编·族】
   阅读指南/术语/符号        第0章 总论               第7章  SESAME
   单位总表                  第1章 识别分派           第8章  MULTI EOS/OPAC
                            第2章 字节级解析         第9章  Hyades
                            第3章 坐标系网格         第10章 FEOS/MPQeos
                            第4章 语义与单位         第11章 LEDCOP/ATOMIC
                            第5章 转换反演           第12章 IONMIX
                            第6章 陷阱总集           第13章 SNOP/Thermos ★
                                 │                   第14章 辅助边缘 ★
                                 │                        │
                                 └────────────┬───────────┘
                                              │
                                        【附录】★
                                    A 单位换算  B 速查卡
                                    C 样本索引  D 校验片段
                                    E 实现缺口  F 书目
                                              │
                          ★ = 本写手负责的第13、14章与全部附录
```

### 图 F12 格式族决策树

```
读入一个数据文件
   │
   ├─ 文件名/路径含 "hyades" ? ──是──> Hyades ASCII (eos_*/opc_*/qeos_*)
   │                                    单位: keV/dyne·cm⁻²/erg·g⁻¹
   │
   ├─ 文件名含 ".feos" ? ────────是──> FEOS 原生 4×15 (行0 十字段)
   │                                    payload 列序 [S-UNK]
   │
   ├─ 文件名含 ".301/.304/.305" ? ─是─> MPQeos 4×16
   │                                    单位: GPa/MJ·kg⁻¹/K
   │
   ├─ 扩展名 ".cn4" / ".cnr" ? ───是──> IONMIX (头4行区分)
   │                                    cn4=18块 / cnr=7块
   │
   ├─ 扩展名 ".coldopacity" ? ────是──> 两行自描述头 (Eph/miu)
   │
   ├─ 扩展名 ".hug" ? ───────────是──> 首行 # 方括号单位（两写法）
   │
   ├─ 路径含 "Thermos" + ".ini" ?─是──> 四键 ini (AUX)
   │
   ├─ 目录 ATOMIC + ".txt" ? ─────是──> LEDCOP 锚点状态机
   │
   └─ 其它 ──────────────────────────> 默认 SESAME 4×15
                                        ├─ 4 数头 + 计数=4+2nr+ne+2nr·ne → F1 EOS
                                        ├─ 4 数头 + 计数=4+nr+nt+nr·nt    → F2 OPAC
                                        └─ 计数不匹配 → 报错，不静默
```
