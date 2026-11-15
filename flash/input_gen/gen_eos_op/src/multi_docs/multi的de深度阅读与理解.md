# MULTI 反演 EOS 中 de 的口径：深度阅读与理解

**主题**：Multi1D++ 反演 EOS（Inverted EOS）中能量增量 `de` 与冷能 `e0` 的物理定义、参考基准、单位体系、数据布局及其跨格式转换
**日期**：2026-11-14（初稿）· 2026-11-14（修订：SESAME 302 同构对应、LaTeX 推导、术语规范化）
**溯源标记**：沿用《MultiEOSOP格式说明.md》纪律——`[S-L1]` 上游明文 / `[S-L2]` 数据文件内嵌 / `[S-L3]` 程序默认 / `[S-L4]` 推导 / `[S-WEB]` 网络核验 / `[S-UNK]` 本地无依据

---

## 0. 结论摘要

| 编号 | 结论 | 依据 |
|:---:|---|---|
| C1 | MULTI 反演 EOS 中，`de[ne]` 为能量增量列表，`e0[nr]` 为各密度点的冷能量列表；压强与温度矩阵挂载的物理自变量为 $E_{\mathrm{total}}(\rho, T) = e_0(\rho) + de$。注意 $e_0$ 随密度下标变化，不是全局常数 | `[S-L1]` docx §EOS数据 |
| C2 | MULTI 反演 EOS 的字段结构与 **SESAME 302 表（Inverted EOS）严格同构**：$de \leftrightarrow ET$（thermal energy mesh，$ET = E - E_C$），$e_0 \leftrightarrow E_C$（internal energy at 0 K）。该结构在 SESAME 官方文献中有明文定义 | `[S-WEB]` LANL LA-UR-92-3407 |
| C3 | 文件层面仅保证 $E_{\mathrm{total}} = e_0 + de$ 的**自洽分解**；$e_0$ 是否为严格 0 K 冷曲线由生成端约定决定。冷曲线的零点能归属（是否含零点振动能）在不同生成器间并不统一 | `[S-L4]` 文件内不可验证 + `[S-WEB]` LA-UR-92-3407、arXiv:0707.0056 |
| C4 | `de` 与 `e0` 的原生单位均为 `Mbar·cm³/g`（比能量量纲）；与 SI 的换算为 $1\ \mathrm{Mbar\cdot cm^3/g} = 10^5\ \mathrm{J/g}$，完整推导见 §5 | `[S-L1]` docx + `[S-L4]` §5 |
| C5 | 实测存在两种 payload 布局：`with_e0`（计数式 $4+2n_r+n_e+2n_r n_e$，样本 `AL_eos`、`CH_ieos`）与 `no_e0`（计数式 $4+n_r+n_e+2n_r n_e$，样本 `AU_eosd`），判定依据为计数守恒 | `[S-L4]` §6 实测 |
| C6 | IONMIX/cn4 的能量零点**构造性定义于中性原子基态**（$T=0$ 时 $E\equiv 0$），故 cn4 → MULTI 转换采用 `no_e0` 布局（$de \equiv E_{\mathrm{total}}$），严格等价于 SESAME 口径 $E - E_C$（此时 $E_C \equiv 0$） | `[S-L1]` abjt_03.f + 既有裁定 §4.1 |
| C7 | cn4 离子/电子拆分的真实口径：`enrgyion` 仅含离子热运动项，全部激发能与电离能计入电子分量（`enrgy − enrgyion`） | `[S-L1]` abjt_03.f L2135–2178 |
| C8 | 工程约束：解析器不得假设 $P/E/Z$ 非负——上游作者自述表中存在负值，实测 `AL_eos` 的 $e_0$ 段亦出现轻微负值 | `[S-L1]` docx + `[S-L2]` 实测 |

---

## 1. 一手证据：上游手册原文摘录

证据源：`src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx`。以下按解包 `word/document.xml` 后的抽取段号（P***）逐字引用。

### 1.1 三分量模型与反演表定位

> P072/P074：EOS数据采用"三因素模型(Three component model)"……第一项为冷分布，其他两项分别是电子和例子的参数。

（注："例子"为"离子"之笔误；"三因素模型"即 SESAME 三分量分解，见 §3。）

> P075/P126：EOS表格数据为Inverted EOS数据，即自变量为[ρ]和[E]，因变量为[P]和[T]……为了在计算时直接使用EOS数据，省去转化，需要将EOS数据表格中的P(R, T)，E(R, T)转化为P(R,E), T(R,E)。

### 1.2 de 与 e0 的定义句（核心证据）

> P109：**de[ne] 能量(能量列表，与冷能量的差距, 单位Mbar*cm3/g)**
> P110：**e0[nr]   冷能量(密度对应的冷能量列表，单位Mbar*cm3/g)**
> P111：P[ne*nr]  压力 P[(0~nr-1)+nr*i]为密度为r[0~nr-1]，能量**de[i]+e0[0~nr-1]**时的压力，单位为Mbar
> P112：T[ne*nr] 密度为r[0~nr-1]，能量**de[i]+e0[0~nr-1]**时的温度（Kelvin）
> P113：即参数个数为4+2*nr+ne+2*nr*ne
> P114–P115：P[0] to P[nr-1] are the pressures at energy de[0]+e0[0 to nr-1]；P[nr] to P[nr*2-1] at de[1]+e0[0 to nr-1], etc

### 1.3 坐标系与反演方法

> P084：因变量和自变量都没有使用对数坐标系，而是使用线性坐标系
> P129–P130：对某个密度R，首先根据E(R, T)找到对应的温度T(R, E)，这个过程需要差值[插值]。P(R, E) = P(R, T(R, E))，这里同样需要差值。

### 1.4 SESAME/MPQeos 单位链（手册原文）

> P134：SESAME数据库的单位：压强（GPa），能量（MJ/kg），密度（g/cc），温度(Kelvin)
> P135：MULTI2D程序中使用cgs单位，而其调用的EOS数据中的单位为压强Mbar，能量Mbar*cm3/g
> P137：压力：1GPa = 1e9Pa = 1e10 dyne/cm2 = 1e10 erg/cm3 = 1e-2 Mbar
> P138：能量密度：1MJ/kg = 1e3J/g = 1e10 erg/g = 1e-2 Mbar*cm3/g

---

## 2. 与 SESAME 302 表的同构对应（口径定位的关键）

SESAME 官方数据库文献（LA-UR-92-3407, *SESAME: The Los Alamos National Laboratory Equation of State Database*）对 **Table 302（Inverted EOS）** 的字段定义 `[S-WEB]`（访问 2026-11-14）：

> **No. 302. Inverted EOS tables**: pressure and temperature as functions of density and internal energy.
> `NR, NE, (R(I), I=1,NR), (ET(J), J=1,NE), (EC(I), I=1,NR), ((P(I,J)), ((T(I,J)))`
> **R** — density mesh; **ET** — thermal energy mesh (**ET = E − EC**); **EC** — internal energy at 0 K; **P** — pressure; **T** — temperature.

该文献同时给出 SESAME 库官方单位制 `[S-WEB]`：

> Units used in the Sesame library are: pressure — GPa, energy — MJ/kg, density — Mg/m³ (= g/cm³), temperature — K.

**对应关系**（结论 C2 的展开）：

| MULTI 反演 EOS 字段 | SESAME 302 字段 | 语义 | 单位（各自体系） |
|---|---|---|---|
| `de[ne]` | `ET(NE)` | thermal energy mesh，$E_T = E - E_C$ | `Mbar·cm³/g` |
| `e0[nr]` | `EC(NR)` | internal energy at 0 K（冷曲线） | `Mbar·cm³/g` |
| `r[nr]` | `R(NR)` | density mesh | `g/cc` |
| `P[ne·nr]` | `P(NR×NE)` | pressure | `Mbar` |
| `T[ne·nr]` | `T(NR×NE)` | temperature | `K` |

二者在物理语义上完全一致：**de 即"热能网格"（相对冷曲线的能量增量），e0 即"0 K 内能"（冷曲线）**。差异仅在单位制（MULTI 用 Mbar 系，SESAME 官方用 GPa/MJ/kg）与载体形式（4×15 定宽文本 vs SESAME 数据卡片）。

`[S-L4]` 佐证：LA-UR-92-3407 同时说明 302 表"are easy to generate from the 301 form when they are needed"——与 docx P126 的反演动机（将 $P(\rho,T),E(\rho,T)$ 转化为 $P(\rho,E),T(\rho,E)$）一致。

---

## 3. 冷曲线的物理语义与零点约定

### 3.1 SESAME 三分量分解

SESAME 生成理论（LA-UR-92-3407 §Baseline EOS Theory；LA-7130 `[S-WEB]` OSTI 5150206）将 EOS 写为三项之和：

$$
P(\rho, T) = P_C(\rho) + P_N(\rho, T) + P_e(\rho, T)
$$

其中 $P_C(\rho)$ 为冷曲线（0 K 等温线）贡献，$P_N$ 为离子热运动项，$P_e$ 为电子热项；内能等热力学函数有同构分解：

$$
E(\rho, T) = E_C(\rho) + E_{\mathrm{ion}}(\rho, T) + E_e(\rho, T)
$$

docx 的"三因素模型（Three component model）……第一项为冷分布"即此结构 `[S-L1]`+`[S-WEB]`。

### 3.2 零点能归属是生成端约定

不同文献对冷曲线零点能的处理存在明确分歧：

- **LA-UR-92-3407**（SESAME 主流实践）："By convention we put the zero point motion of the ions in with the thermal ionic contribution."——冷曲线**不含**离子零点振动能，零点能归入离子热项 `[S-WEB]`；
- **NiAl 第一性原理 EOS 构造**（arXiv:0707.0056）："the zero-point energy of the lattice modes was subsumed in the lattice-thermal contribution rather than the cold curve; thus the cold curve strictly assumed frozen ions… **the cold curve is not physically real as defined**" `[S-WEB]`；
- 三分量综述口径："the cold curve, really the 0 K isotherm with zero-point energy (zpe) removed" `[S-WEB]`（ScienceDirect, Thermodynamic Potential 词条）。

**结论**（C3 的依据）：冷曲线的绝对零点因生成器而异，且即使同一生成器内部也存在"冷曲线非物理真实"的构造性近似。因此**文件层面能且只能保证 $E_{\mathrm{total}} = e_0 + de$ 的加法自洽**；任何跨表混用（如将某表的 $e_0$ 与另一表的 $de$ 组合）在物理上不成立。MULTI 文件内的 $e_0$ 沿用其生成端（SESAME/Murat 转换链）的零点约定，本文不对其绝对性做断言 `[S-L4]`。

### 3.3 Mie–Grüneisen 视角下冷曲线与 de 的关系

冷曲线可由冲击 Hugoniot 数据反演（Rice–McQueen–Walsh 方法），其 Mie–Grüneisen 形式 `[S-WEB]` OSTI 5150206 式 (4)：

$$
P_C(\rho) - \rho\,\gamma(\rho)\,E_C(\rho) = P_H(\rho) - \rho\,\gamma(\rho)\,E_H(\rho)
$$

其中 $\gamma(\rho)$ 为 Grüneisen 参数，$P_H$、$E_H$ 为 Hugoniot 上的实测压强与内能。该式说明 $E_C$ 与 $P_C$ 通过物态方程耦合：**$e_0 = E_C$ 并非独立自由参数，而是与该密度的压强零点绑定**——这为实测中 $e_0$ 出现负值的现象（束缚能/负压参考点，§6 注 2）提供物理解释。

---

## 4. abjt_03.f：cn4（IONMIX）侧的源码级定义

文件：`ionmix/Ionmix_run/outputfiles/cn4/gen_hohlraum10/Z06_0.50-Z01_0.50-20261108_2013/abjt_03.f`（各材料目录含同版副本）。

### 4.1 内能构造与零点（`subroutine energy`，L1910–2188）

每核热能（eV）：

$$
e_{\mathrm{th}} = \tfrac{3}{2}\,(1+\langle Z\rangle)\,T, \qquad
e_{\mathrm{th,ion}} = \tfrac{3}{2}\,T, \qquad
e_{\mathrm{th,e}} = \tfrac{3}{2}\,\langle Z\rangle\,T
$$

（源码 `etherm`/`ethermion`/`ethermele`；`avizst` = 平均电离度 $\langle Z\rangle$；`tp` = 温度，单位 eV。）

激发能（相对基态）与电离能（逐级电离势累加）：

$$
E_{\mathrm{exc}} = \sum_g f_g \sum_{q} f_q \sum_{n \ge n_0} f_n\,
\underbrace{n_0^{2}\,\chi_{q}\left(\frac{1}{n_0^{2}}-\frac{1}{n^{2}}\right)}_{\texttt{ennp}\text{（eV）}}, \qquad
E_{\mathrm{iz}} = \sum_g f_g \sum_{q\ge 1} f_q \sum_{q'=1}^{q} \chi_{q'}
$$

（$f_g$ 为元素丰度 `fracsp`，$f_q$ 为电荷态布居 `fraciz`，$f_n$ 为能级布居 `fraclv`，$\chi_{q}$ 为电离势 `pot`。源码 L2160–2169。）

总比内能（写表值，J/g）：

$$
E = \frac{\bigl(e_{\mathrm{th}} + E_{\mathrm{exc}} + E_{\mathrm{iz}}\bigr)\,n_i}{\rho \cdot 6.242\times 10^{18}},
\qquad
\rho = \frac{n_i\,\overline{A}}{N_A}
$$

（源码：`enrgy = (etherm + tsumex + tsumiz)*densnn`，`rho = densnn*avgatw/avgdro`，`enrgy = enrgy/(rho*6.242e18)`，L2172–2178。换算常数的量纲核验见 §5.5。）

**零点结论**：$T=0$ 时 $e_{\mathrm{th}}$、$E_{\mathrm{exc}}$、$E_{\mathrm{iz}}$ 均为零 → **cn4 的 $E$ 构造性定义于中性原子基态**（结论 C6）`[S-L1]`。

**拆分口径**（结论 C7）：

$$
E_{\mathrm{ion}}^{\mathrm{cn4}} = \frac{\tfrac{3}{2}\,T\, n_i}{\rho \cdot 6.242\times10^{18}}\ \text{（仅热项）}, \qquad
E_e^{\mathrm{cn4}} = E - E_{\mathrm{ion}}^{\mathrm{cn4}} = \frac{\bigl(\tfrac{3}{2}\langle Z\rangle\, T + E_{\mathrm{exc}} + E_{\mathrm{iz}}\bigr)\,n_i}{\rho \cdot 6.242\times10^{18}}
$$

即**全部激发能与电离能计入电子分量**（源码 L2173–2174 定义与 L4710 写出式的代数关系）`[S-L1]+[S-L4]`。

### 4.2 cn4 逐块写出公式（`subroutine owtf`，isw(21) 块，L4642–4756）

记 $q_e = 1.602\times10^{-19}\ \mathrm{J/eV}$（eV→J 换算因子）：

| 块 | 物理量 | 写出公式（源码语义） | 单位 | 行号 |
|:---:|---|---|---|:---:|
| 4 | $\bar Z$ | $n_e/n_i$ | — | L4666 |
| 5 | $\mathrm{d}\bar Z/\mathrm{d}T$ | `dzdt(it,id)` | eV⁻¹ | L4670 |
| 6 | $P_{\mathrm{ion}}$ | $n_i\,T\,q_e$ | J/cm³ | L4673 |
| 7 | $P_e$ | $n_e\,T\,q_e$ | J/cm³ | L4677 |
| 8 | $\mathrm{d}P_{\mathrm{ion}}/\mathrm{d}T$ | $n_i\,q_e$ | J/(cm³·eV) | L4681 |
| 9 | $\mathrm{d}P_e/\mathrm{d}T$ | $\bigl(n_i\,T\,\tfrac{\mathrm{d}\bar Z}{\mathrm{d}T} + n_e\bigr)q_e$ | J/(cm³·eV) | L4701 |
| 10 | $E_{\mathrm{ion}}$ | `enrgyion(it,id)` | J/g | L4706 |
| 11 | $E_e$ | $E - E_{\mathrm{ion}}$ | J/g | L4710 |
| 12 | $c_{V,\mathrm{ion}}$ | `heatcpion(it,id)` | J/(g·eV) | L4714 |
| 13 | $c_{V,e}$ | $c_V - c_{V,\mathrm{ion}}$ | J/(g·eV) | L4718 |
| 14/15 | $\mathrm{d}E/\mathrm{d}\rho$ 类 | `dedden_ion · condd · n_i/T²`，`condd = −6.242\times10^{18}·\overline{A}/\overline{\rho}`（源码注释自标 *not sure*） | — | L4721–4735 |
| 16 | 能群边界 | `engrup(ig), ig = 1, …, ngrups+1` | eV | L4739 |
| 17–19 | 群不透明度 | `orgp / opgpa / opgpe × opacity_lim`（`opacity_lim = 1.0`） | cm²/g | L4741–4756 |
| 20 | 电子比熵 | 注释占位全零 | — | L4743–4744 |

物理合理性核验 `[S-L4]`：块 6/7 为理想气体形式 $P_{\mathrm{ion}} = n_i k_B T$、$P_e = n_e k_B T$（$T$ 以 eV 计时 $k_B \to q_e$；$n$ 以 cm⁻³ 计则得 J/cm³）；块 9 由 $P_e = n_e\,T\,q_e$ 与 $\mathrm{d}n_e/\mathrm{d}T = n_i\,\mathrm{d}\bar Z/\mathrm{d}T$ 经乘积法则展开：

$$
\frac{\partial P_e}{\partial T} = q_e\left(T\,\frac{\partial n_e}{\partial T} + n_e\right) = q_e\left(n_i\,T\,\frac{\mathrm{d}\bar Z}{\mathrm{d}T} + n_e\right)
$$

与源码逐项一致。

---

## 5. 单位换算：完整推导链

### 5.1 原生单位及其量纲依据

`de`、`e0` 的原生单位为 `Mbar·cm³/g` `[S-L1]` docx P109/P110，量纲为比能量：

$$
\bigl[\mathrm{Mbar\cdot cm^3/g}\bigr] = \frac{[\text{压强}]\times[\text{体积}]}{[\text{质量}]} = \mathrm{L^2\,T^{-2}}
$$

该单位选择并非任意：由热力学关系 $E = P\,v$（比内能 = 压强 × 比容，$v = 1/\rho$），$P\,[\mathrm{Mbar}] \times v\,[\mathrm{cm^3/g}]$ 在 MULTI 单位制下数值直读为比内能——**这正是反演 EOS 采用 Mbar（压强）与 Mbar·cm³/g（能量）配套的原因** `[S-L4]`。

### 5.2 Mbar·cm³/g → erg/g → J/g

$$
1\ \mathrm{Mbar} = 10^{6}\ \mathrm{bar}, \qquad 1\ \mathrm{bar} = 10^{6}\ \mathrm{dyne/cm^2}
\;\Longrightarrow\;
1\ \mathrm{Mbar} = 10^{12}\ \mathrm{dyne/cm^2}
$$

$$
1\ \mathrm{Mbar\cdot cm^3/g} = 10^{12}\,\frac{\mathrm{dyne}}{\mathrm{cm^{2}}}\cdot\frac{\mathrm{cm^{3}}}{\mathrm{g}} = 10^{12}\,\frac{\mathrm{dyne\cdot cm}}{\mathrm{g}} = 10^{12}\,\frac{\mathrm{erg}}{\mathrm{g}}
$$

（最后一步利用 $1\ \mathrm{erg} \equiv 1\ \mathrm{dyne\cdot cm}$。）再由 $1\ \mathrm{erg} = 10^{-7}\ \mathrm{J}$：

$$
\boxed{\;1\ \mathrm{Mbar\cdot cm^3/g} = 10^{12}\ \mathrm{erg/g} = 10^{5}\ \mathrm{J/g}\;}
$$

### 5.3 与 MJ/kg（SESAME 官方能量单位）的换算

$$
1\ \mathrm{MJ/kg} = \frac{10^{6}\ \mathrm{J}}{10^{3}\ \mathrm{g}} = 10^{3}\ \mathrm{J/g}
\;\Longrightarrow\;
\boxed{\;1\ \mathrm{MJ/kg} = 10^{-2}\ \mathrm{Mbar\cdot cm^3/g}\;}
$$

与 docx P138 原文一致。注：P138 中"1e10 erg/g = 1e12 erg*cm/g"一步为笔误式速记（正确量纲为 dyne·cm/g），严格展开即本节推导，结论不受影响（辨析亦见《MultiEOSOP格式说明.md》§5.2.1）。

### 5.4 J/cm³（cn4 压强单位）→ Mbar（MULTI 压强单位）

压强与能量密度同量纲（$[\text{压强}] = [\text{能量}]/[\text{体积}]$），IONMIX 以 `J/cm³` 表出压强即能量密度形式：

$$
1\ \mathrm{J/cm^3} = 10^{7}\ \mathrm{erg/cm^3} = 10^{7}\ \mathrm{dyne/cm^2} = 10^{-5}\ \mathrm{Mbar}
\;\Longrightarrow\;
\boxed{\;P\,[\mathrm{Mbar}] = \bigl(P_{\mathrm{ion}} + P_e\bigr)[\mathrm{J/cm^3}] \times 10^{-5}\;}
$$

### 5.5 abjt_03.f 换算常数的量纲核验

**$q_e = 1.602\times10^{-19}$**：即 $1\ \mathrm{eV} = 1.602\times10^{-19}\ \mathrm{J}$（CODATA 精确值 $1.602176634\times10^{-19}\ \mathrm{J}$）。块 6/7 中 $n\,[\mathrm{cm^{-3}}] \times T\,[\mathrm{eV}] \times q_e \Rightarrow \mathrm{J/cm^3}$ ✓

**$6.242\times10^{18}$**：其倒数 $1.602\times10^{-19}$ 即 J↔eV 桥接。源码 `enrgy = ε[eV/cm³] / (ρ·6.242e18)` 的严格等价式为

$$
E\,[\mathrm{J/g}] = \frac{\varepsilon\,[\mathrm{eV/cm^3}]}{\rho\,[\mathrm{g/cm^3}]} \times \underbrace{1.602\times10^{-19}}_{\mathrm{eV}\to\mathrm{J}} = \frac{\varepsilon}{\rho} \cdot \frac{1}{6.242\times10^{18}}
$$

即源码将 eV→J 换算写成除以其倒数常数，两步合并后与直接计算一致 `[S-L4]`。

### 5.6 温度换算

$$
T\,[\mathrm{K}] = T\,[\mathrm{eV}]\times\frac{1\ \mathrm{eV}}{k_B}
= T\,[\mathrm{eV}]\times\frac{1.602176634\times10^{-19}\ \mathrm{J}}{1.380649\times10^{-23}\ \mathrm{J/K}}
= T\,[\mathrm{eV}]\times 1.16045\times10^{4}
$$

（即 $1\ \mathrm{eV} \leftrightarrow 11604.5\ \mathrm{K}$；实现取 `EV_PER_K` 常数。）

### 5.7 密度轴换算

$$
\rho\,[\mathrm{g/cm^3}] = n_i\,[\mathrm{cm^{-3}}]\times\frac{\overline{A}}{N_A}
= n_i\,[\mathrm{cm^{-3}}]\times\overline{A}\times 1.66054\times10^{-24}
$$

（$N_A = 6.02214\times10^{23}\ \mathrm{mol^{-1}}$；$1/N_A\ \mathrm{g}$ 即原子质量单位对应的质量。实现见 `convert/invert_eos.py` 的 `cn4_eos_to_rho_base`，并逐列校验 $\rho$ 的常值性。）

---

## 6. 两种 payload 布局的实测验证

用 `eosop_pro.parsers.multi_inverted_eos.parse_all` 载入三个代表文件（2026-11-14 实测，WSL python3）：

| 文件 | 布局 | $n_\rho$ | $n_{de}$ | 验证式 | 结果 |
|---|---|:---:|:---:|---|---|
| `mat_CELIA/CH_ieos` | with_e0 | 101 | 100 | $E\big|_{de=0} \equiv e_0$（逐点） | 最大绝对偏差 = 0 |
| | | | | $\max_i E_{ij} \equiv de_{\max} + e_{0,j}$ | 最大相对误差 = 0 |
| `mat_Al-1.0/AL_eos` | with_e0 | 66 | 74 | 同上闭合式 | 最大相对误差 = 0 |
| `mat_Au-1.0/AU_eosd` | no_e0 | 101 | 23 | $\max_i E_{ij} \equiv de_{\max}$ | 逐点相等；$de$ 单调且 $\ge 0$ |

**计数守恒判据**：

$$
L_{\mathrm{with\_e0}} = 4 + 2n_r + n_e + 2n_r n_e, \qquad
L_{\mathrm{no\_e0}} = 4 + n_r + n_e + 2n_r n_e
$$

（`AL_eos`：$4 + 2\times66 + 74 + 2\times66\times74 = 9978$，与实测 token 数精确相等。）

实测附注：

1. **CH_ieos**：$e_0$ 段 $\min = 0$（低密度端冷能为零）、$\max = 3701.45\ \mathrm{Mbar\cdot cm^3/g}$；$de$ 轴为等差数列（步长 $0.00150899$）→ 反演表能量轴与密度轴均为线性，与 docx P084 一致 `[S-L2]`。
2. **AL_eos**：$e_0$ 段出现轻微负值（$\min = -0.00156\ \mathrm{Mbar\cdot cm^3/g}$），对应低密度端的束缚能参考点/压强零点漂移（§3.3 的 Grüneisen 耦合给出物理解释）。与 docx P153 上游自述"压强、能量甚至 Z 等有负值，原因正在查找"相互印证 → **解析器不得假设非负**（结论 C8）。
3. **AU_eosd（no_e0）**：$de \in [0,\ 3.71\times10^{8}]$，能量场与 $de$ 轴闭合 → no_e0 布局下 $de \equiv E_{\mathrm{total}}$（绝对比内能）`[S-L2]+[S-L4]`。
4. 与《MultiEOSOP格式说明.md》§5.1.4 的版本差异说明：该节（2026-09-17 版）曾将 `AU_eosd` 登记为 `[S-UNK]`（两计数式均不闭合）；解析器后续（2026-11-05）确认该文件含 2 个同表头块，单块按 $L_{\mathrm{no\_e0}}$ 计数闭合。本文以解析器实测为准 `[S-L2]`。

---

## 7. 跨格式族能量零点对比

| 格式族 | 能量存储结构 | 零点约定 | 依据 |
|---|---|---|---|
| MULTI 反演 EOS | 双层：$de$（增量）+ $e_0$（冷能） | "与冷能量的差距"；$e_0$ 绝对性由生成端定 | `[S-L1]` docx P109–P110 |
| SESAME 302 | 双层：$ET = E - E_C$ + $E_C$ | $E_C$ = internal energy at 0 K；零点能归属为库级约定 | `[S-WEB]` LA-UR-92-3407 |
| SESAME 301 | 单列累计 $E(\rho,T)$ | 文献口径 $E - E_C$ 需用户结合 306 冷曲线表（$T=0$ 单温表）或自行估计 | `[S-WEB]` LA-UR-92-3407 + NJP aa83d8 |
| Hyades | 单列绝对比内能（erg/g），与 $P$ 并列 | $T=0$ 行即冷曲线；转 MULTI 需自行拆分 $de/e_0$ | `[S-L1]` Hyades 格式说明 + 规格书 §4.2.4 |
| FEOS | 单列，列头自带 `E_unit` 归一化声明 | 单位由文件内参数声明，不写死 | `[S-L1]` FEOS 说明（规格书 §4.1.2） |
| IONMIX（cn4） | 单列总量 + ion/ele 拆分（块 10/11） | 零点=中性基态（源码级构造） | `[S-L1]` abjt_03.f L2129–2178 |

**核心结论**：除 cn4/IONMIX 外，各族的能量绝对零点均无法从文件内部唯一确定（结论 C3）。双层结构与单列结构相互转换时，必须保持 $E_{\mathrm{total}}$ 的加法自洽并显式声明零点约定 `[S-L4]`。

---

## 8. 与 cn4 / FLASH 的双向转换公式

> 既有裁定与实现：`eosop_pro/parsers/formats/multi_inverted_eos.md` §4.1（no_e0 布局裁定，commit 13f8504）；转换 API `eosop_pro/convert/invert_eos.py`（`to_de_grid`、`cn4_eos_to_rho_base`）与 `convert/writers_multi.py`（`write_multi_inverted_eos_from_cn4`）。本节为公式汇总。

### 8.1 cn4 → MULTI F1

设 cn4 给出 $E_{\mathrm{ion}}$（块10）、$E_e$（块11）、$P_{\mathrm{ion}}$（块6）、$P_e$（块7）、温度轴 $T\,[\mathrm{eV}]$、离子数密度轴 $n_i\,[\mathrm{cm^{-3}}]$，则：

$$
\mathrm{de}\,[\mathrm{Mbar\cdot cm^3/g}] = \frac{E_{\mathrm{ion}} + E_e\,[\mathrm{J/g}]}{10^{5}},
\qquad
P\,[\mathrm{Mbar}] = \frac{P_{\mathrm{ion}} + P_e\,[\mathrm{J/cm^3}]}{10^{5}}
$$

$$
T\,[\mathrm{K}] = T\,[\mathrm{eV}]\times 1.16045\times10^{4},
\qquad
\rho\,[\mathrm{g/cm^3}] = \frac{n_i\,\overline{A}}{N_A}
$$

布局采用 **no_e0**（不写 $e_0$ 段）：由结论 C6，cn4 零点构造性在中性基态，故

$$
de \equiv E_{\mathrm{total}} \equiv E - E_C \quad (E_C \equiv 0)
$$

与 SESAME 302 的 $E_T$ 口径严格一致（结论 C2）。

矩阵排布：线性指标 $\mathrm{idx} = i_\rho + n_r\, i_{de}$（能量慢变、密度快变）`[S-L1]` docx P111。

### 8.2 反演算法（$E(\rho,T)$ 网格与 $T(\rho,de)$ 网格的互转）

反演的可行性依赖固定 $\rho$ 下 $E(\rho,T)$ 关于 $T$ 严格单调递增（除相变潜热平台外物理上成立）`[S-L4]`。

**正演（$(\rho,T)$ → $(\rho,de)$，`to_de_grid`）**：对每条密度列、目标能量 $E^* = de^* + e_0$（with_e0）或 $E^* = de^*$（no_e0），在温度序列上定位 $E_k \le E^* \le E_{k+1}$，取 log–log 插值权重

$$
s = \frac{\ln E^* - \ln E_k}{\ln E_{k+1} - \ln E_k} \in [0,1]
$$

同一权重同时插出两场（保证 $P$、$T$ 自洽）：

$$
T(\rho, de^*) = \exp\!\bigl[\ln T_k + s\,(\ln T_{k+1} - \ln T_k)\bigr], \qquad
P(\rho, de^*) = \exp\!\bigl[\ln P_k + s\,(\ln P_{k+1} - \ln P_k)\bigr]
$$

**反向（$(\rho,de)$ → $(\rho,T)$，`to_Te_grid`）**：以 $T^*$ 为目标，权重换为

$$
s = \frac{\ln T^* - \ln T_k}{\ln T_{k+1} - \ln T_k}
$$

再以同一 $s$ 插 $P$ 与 $E$。越界点按端点延拓处理并记入 notes `[S-L4]`。

插值坐标说明：docx P084 明文反演表为线性坐标系（线性插值亦可）；实现默认 log–log 以兼顾跨数量级精度，两种模式均已提供 `[S-L1]+[S-L4]`。

### 8.3 MULTI F1 → FLASH IONMIX 表（反向路径）

| FLASH 量（= IONMIX 约定） | MULTI F1 来源 | 公式 |
|---|---|---|
| 块 10/11（$E_{\mathrm{ion}}$/$E_e$） | — | **结构性缺失**：F1 仅含总量，离子/电子拆分需外部电离模型 |
| 块 6/7（$P_{\mathrm{ion}}$/$P_e$） | — | **结构性缺失**（同上） |
| 块 4/5（$\bar Z$、$\mathrm{d}\bar Z/\mathrm{d}T$） | — | 需 `*.ZEFF` 表或电离模型 |
| 总内能（块 10+11 之和） | $e_0 + de$（with_e0）或 $de$（no_e0） | $E\,[\mathrm{J/g}] = \bigl(e_0[\rho] + de\bigr)\times10^{5}$ |
| 总压（块 6+7 之和） | $P$ 段 | $P\,[\mathrm{J/cm^3}] = P\,[\mathrm{Mbar}]\times10^{5}$ |
| 温度（eV） | $T$ 段（K） | $T\,[\mathrm{eV}] = T\,[\mathrm{K}]\,\big/1.16045\times10^{4}$ |

**结论**：F1 → cn4 方向存在不可逆信息损失（离子/电子拆分与电离态无法重建）；cn4 是 FLASH 表的原始形态，MULTI 文件适合交叉验证而非替代。

---

## 9. 残留不确定项

| 编号 | 项 | 状态 |
|:---:|---|---|
| U1 | $e_0$ 是否严格等于 0 K 冷曲线 | `[S-UNK]` 文件内不可验证；docx 称"冷能量"（L1 口径），§3.2 文献表明零点能归属为生成器约定。工程上按"生成端参考能量"处理，转换时保持加法自洽 |
| U2 | `AU_eosd` 表号 2700 的族语义（规格书 §3.1 记录表号位数差异） | `[S-UNK]` 不影响 de 口径（payload 计数与数值闭合已定） |
| U3 | abjt_03.f 中 `avgdro` 常数的精确定义 | `[S-UNK]` 仅影响块 14/15（dedden 类），不影响 de/E 口径 |
| U4 | docx 文字笔误三处（"电子和例子"→离子、"差值"→插值、"erg*cm/g"→dyne·cm/g） | 已按上下文校正，原文照录于 §1 `[S-L4]` |

---

## 10. 参考文献

1. R. Ramis, R. Schmalz, J. Meyer-ter-Vehn, *MULTI — A one-dimensional laser plasma hydrocode*, Comput. Phys. Commun. **49**, 475 (1988).
2. R. Ramis, K. Eidmann, J. Meyer-ter-Vehn, S. Hüller, *MULTI-fs — A computer code for laser–plasma interaction in the femtosecond regime*, Comput. Phys. Commun. **183**, 637 (2012), DOI 10.1016/j.cpc.2011.10.016.
3. LANL, *SESAME: The Los Alamos National Laboratory Equation of State Database*, LA-UR-92-3407（302 表字段定义、库官方单位制、三分量分解约定）. https://cdn.lanl.gov/files/laur-92-3407_a0e99.pdf （访问 2026-11-14）`[S-WEB]`
4. B. I. Bennett et al., *Recent Developments in the SESAME Equation-of-State Library*, LA-7130（301/302 记录结构、冷曲线经验模型、Mie–Grüneisen 反演）. OSTI 5150206 （访问 2026-11-14）`[S-WEB]`
5. *The equation of state of solid nickel aluminide*, arXiv:0707.0056（冷曲线零点能归属的生成端约定）`[S-WEB]`
6. *Laser-plasma induced shock waves in micro shock tubes*, New J. Phys. **19**, 103017 (2017), DOI 10.1088/1367-2630/aa83d8（MULTI-fs 反演表使用与 SESAME 304 口径引述）`[S-WEB]`

---

## 附：证据文件路径速查

| 证据 | 路径（相对 `gen_eos_op/`） |
|---|---|
| 上游手册 | `src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx` |
| IONMIX 源码 | `ionmix/Ionmix_run/outputfiles/cn4/gen_hohlraum10/Z06_0.50-Z01_0.50-20261108_2013/abjt_03.f`（energy：L1910–2188；owtf cn4 块：L4642–4756） |
| 项目规格书 | `src/multi_docs/MultiEOSOP格式说明.md`（§3.2.2、§4.1.3–4.2.4、§5.1–5.2） |
| 实测文件 | `src/Multi1D++Portable20241128/matter++/{mat_CELIA/CH_ieos, mat_Al-1.0/AL_eos, mat_Au-1.0/AU_eosd}` |
| 解析器实现 | `eosop_pro/parsers/multi_inverted_eos.py`、`eosop_pro/convert/invert_eos.py`、`eosop_pro/convert/writers_multi.py` |
| 既有裁定 | `eosop_pro/parsers/formats/multi_inverted_eos.md` §4.1 |
