# FEOS 用户指南

> **FEOS (Frankfurt equation of state)** — 计算任意化学元素及均匀混合物 EOS 表的 C++ 代码
>
> 原作者: Dr. Steffen Faik, Goethe-Universität Frankfurt am Main
>
> 核心文献: *Computer Physics Communications* **227** (2018) 117–125, doi:10.1016/j.cpc.2018.01.008
>
> 许可: GPL v3 · 版本: FEOS_16.7 (2016-07-29) · vendored: `../src/FEOS/` · 文献 PDF: `../Documents/`

---

## 目录

1. [概述](#1-概述)
   - [1.1 主要功能](#11-主要功能)
   - [1.2 适用条件与限制](#12-适用条件与限制)
2. [物理模型与核心公式](#2-物理模型与核心公式)
   - [2.1 QEOS 谱系与自由能分解](#21-qeos-谱系与自由能分解)
   - [2.2 电子部分：Thomas–Fermi 模型](#22-电子部分thomasfermi-模型)
   - [2.3 离子部分：Cowan 模型](#23-离子部分cowan-模型)
   - [2.4 冷曲线修正](#24-冷曲线修正)
   - [2.5 混合物](#25-混合物)
   - [2.6 液-汽两相区与 Maxwell 构建](#26-液-汽两相区与-maxwell-构建)
   - [2.7 与 SESAME 的关系](#27-与-sesame-的关系)
3. [代码结构](#3-代码结构)
   - [3.1 包组成](#31-包组成)
   - [3.2 源码文件一览](#32-源码文件一览)
4. [输入文件 (.par)](#4-输入文件-par)
   - [4.1 参数详解](#41-参数详解)
   - [4.2 控制开关](#42-控制开关)
   - [4.3 完整输入文件示例](#43-完整输入文件示例)
5. [输出文件详解](#5-输出文件详解)
   - [5.1 .feos — 原生 EOS 表（逐块对照）](#51-feos--原生-eos-表逐块对照)
   - [5.2 副产物文件系列](#52-副产物文件系列)
   - [5.3 单点模式](#53-单点模式)
6. [Python 输入文件生成器](#6-python-输入文件生成器)
   - [6.1 FEOSInputGen 类](#61-feosinputgen-类)
   - [6.2 feos_to_cn4 转换器](#62-feos_to_cn4-转换器)
   - [6.3 典型示例参数设置](#63-典型示例参数设置)
7. [运行流程](#7-运行流程)
   - [7.1 目录结构](#71-目录结构)
   - [7.2 Python 自动运行](#72-python-自动运行)
   - [7.3 手动运行](#73-手动运行)
   - [7.4 编译说明](#74-编译说明)
8. [限制与注意事项](#8-限制与注意事项)
9. [常见问题](#9-常见问题)
10. [参考文献](#10-参考文献)

---

## 1. 概述

### 1.1 主要功能

FEOS 是 QEOS 谱系的最新实现（More 1988 → Young & Corey 1995 → MPQeos (Kemp 1998) → FEOS (Faik 2018)），
以少量实验标定参数换取**任意材料即取即用、全相图平滑自洽**的 EOS，专供流体力学程序作表或在线调用。
计算量为比 Helmholtz 自由能分解出的全部热力学量：

| 输出量 | 说明 | 单位 |
|---|---|---|
| 压力 $p$ | 总量及电子/离子/TF 分项 | dyn/cm² |
| 比内能 $\epsilon$ | 总量及分项；参考点归零 | erg/g |
| 比熵 $s$ | 总量及分项 | erg/(g·eV) 类 |
| 比自由能 $f$、$F$ | Helmholtz（总量/分项） | erg/g |
| 电荷态 $\bar{Z}$ | 总量 Qtot + 分元素 Q[k] | 无量纲 |
| 临界点/binodal/spinodal | 仅 Maxwell_Flag=1（`.critical.dat`） | — |

三件套组成：

| 部件 | 可执行/库 | 用途 |
|---|---|---|
| FEOS library | `libfeos.a` | EOS 计算内核，C/C++/Fortran 三接口 |
| 表生成工具 | `feos` | 读 `.par` → 产 `.feos`/SESAME 格式表（本子包封装对象） |
| 可视化工具 | `showeos` | 等温线/等熵线/Hugoniot/等容线 |

**与 ionmix 的分工**：需要不透明度（辐射算例）→ ionmix（`.cn4` 含 EOS+多群不透明度）；
只要 EOS（纯流体/关辐射算例、或 EOS 质量敏感的算例）→ feos（`.feos` → 转 cn4 零填充）。

### 1.2 适用条件与限制

- **适用域**（CPC 明示）：$10^{-7} \le \rho/\rho_0 \le 10^{6}$，$10^{-4}\ \mathrm{eV} \le T \le 10^{6}\ \mathrm{eV}$；
- 混合物 **>3 元素**可能数值困难/耗时不可接受；
- 临界点附近压力仍常偏高；$T \lesssim T_c$ 区域建议核对更高级 EOS（SESAME/DFT-MD）；
- 化合物按**强制同余**处理（无解离化学，见 §2.6.3）；
- 无熔化相变（无潜热/体积突变）；
- **只产 EOS，无不透明度**；
- 数值下限 `RHO_ZERO = 1e-50 g/cm³`、`T_ZERO = 1e-4 eV`（低于此取 $T \to 0$ 极限律）。

---

## 2. 物理模型与核心公式

> 依据：vendored 源码一手对照（LIB-01..06、FE-02/03，标注文件与行号区域）×
> Faik, Tauschwitz & Iosilevskiy, CPC 227, 117 (2018) 全文（`../Documents/`）。两者已交叉核对一致。

### 2.1 QEOS 谱系与自由能分解

#### 2.1.1 谱系

```
Thomas–Fermi (1927/28, Thomas; Fermi)
  └─ QEOS (More, Warren, Young & Zimmerman, Phys. Fluids 31, 3059, 1988)
       ├─ Young & Corey, J. Appl. Phys. 78, 3748 (1995)   ← soft-sphere 冷曲线
       └─ MPQeos (Kemp & Meyer-ter-Vehn, NIM A 415, 674, 1998 + MPQ Report 229)
            └─ FEOS (Faik, Tauschwitz & Iosilevskiy, CPC 227, 117, 2018)
                 首次应用: Faik et al., HEDP 8, 349 (2012) 液-汽亚稳态
```

#### 2.1.2 自由能分解与热力学关系

全部热力学量由**比 Helmholtz 自由能**导出（比量 = 单位质量；cgs + eV）：

$$f(\rho, T) = f_e(\rho, T) + f_i(\rho, T) + f_b(\rho, T)$$

- $f_e$: 电子部分（TF 统计模型，含冷曲线 + 热部分，§2.2/§2.4）
- $f_i$: 离子部分（Cowan 半经验模型，§2.3）
- $f_b$: 半经验键合修正（补偿 TF 缺失的中性原子间键合力，§2.4）

三大热力学关系：

$$p = \rho^2 \left(\frac{\partial f}{\partial \rho}\right)_T, \qquad
s = -\left(\frac{\partial f}{\partial T}\right)_\rho, \qquad
\epsilon = f + Ts$$

源码对应（`LIB-05_EOS_SERVICES.C` `GetAllEOSQuantities`）：分项分别计算、直接相加

$$p = p_i + p_e, \qquad \epsilon = \epsilon_i + \epsilon_e, \qquad f = f_i + f_e, \qquad s = s_i + s_e$$

⚠️ `.feos` 中"电子分量" $p_e,\epsilon_e,s_e,f_e$ = **TF + 冷曲线修正后的结果**（soft-sphere 或
bonding 已并入）；TF 对照块中 $p_{TF},s_{TF}$ 为原始 TF，$\epsilon_{TF},f_{TF}$ 已减电子能量偏移
（压力/熵不受能量偏移影响）。总 EOS 用单一温度 $T = T_e = T_i$ 计算，但库接口允许
离子/电子分量各自独立取不同温度调用（辐射流体双温耦合需求）。

### 2.2 电子部分：Thomas–Fermi 模型

#### 2.2.1 物理图像与缩放律

电子为处于电子+离子自洽静电场中的简并 Fermi 气体；物质分割成球形 Wigner–Seitz 胞，
胞内解 TF 方程得平衡电子分布。TF 模型仅以 Fermi 统计和量子化相空间计入量子效应，
**不含**壳层结构、交换关联、相对论与原子间键合力。

TF 热力学量随原子序数 $Z$ 按幂律缩放——TF 方程只需对**氢解一次并制表**
（`FEOS_TF-Table_1197.dat`，u–t 网格主函数及其导数），运行时插值。缩放因子
（`LIB-02_TF_TABLE_1.C` QIPscheme 构造器 64–69 行）：

| 量 | 变量 → 氢表变量 | 缩放因子 |
|---|---|---|
| 密度 | $\rho \to \rho/(A Z)$ | 同位素线性缩放（同 $Z$ 异 $A$ 只差密度轴） |
| 温度 | $T \to T/Z^{4/3}$ | $t_{\mathrm{scal}} = Z^{-4/3}$ |
| 压力 | $p \to p/Z^{10/3}$ | $p_{\mathrm{scal}} = Z^{10/3}$ |
| 比能 | $\epsilon \to \epsilon \cdot A/Z^{7/3}$ | $e_{\mathrm{scal}} = Z^{7/3}/A$ |
| 比熵 | $s \to s \cdot A/Z$ | $s_{\mathrm{scal}} = Z/A$ |
| 电荷 | $q \to q/Z$ | $q_{\mathrm{scal}} = Z$ |

#### 2.2.2 氢表插值

变量代换 $u = \rho^{-2/3}$（原子半径 $r \propto \rho^{-1/3}$ 的平方）后，氢表主函数
$h(u, t)$ 经 **bicubic Hermite 插值**（`Qbcuint`，$4\times4$ 系数矩阵 `Qbcucof`）给出各量：

$$p = p_{\mathrm{scal}} \cdot \frac{2}{3} u^{-5/2} \left( h - u \frac{\partial h}{\partial u} \right)$$

$$\epsilon = e_{\mathrm{scal}} \cdot \frac{h - t \, \partial h/\partial t}{u}$$

$$s = -s_{\mathrm{scal}} \cdot \frac{\partial h/\partial t}{u} \qquad (\times\ eV2cgs)$$

$$f = e_{\mathrm{scal}} \cdot \frac{h}{u}$$

- $h_1 \equiv \partial h/\partial u$、$h_2 \equiv \partial h/\partial t$：氢表同时存储的一阶导数
- $t$: 归一化温度（$t = T/Z^{4/3}$，cgs 单位内含 eV2cgs）

网格四边与四角（$T\to 0$、$T\to\infty$、$u\to 0$、$u\to\infty$ 及组合）均有专用外推分支
（`Qextrapolate_*`）：$T\to\infty$ 分支先把对数发散项 $\tfrac{3}{2} u T \ln T$ 移出、
对"位移函数"插值后再减回（`LIB-02_TF_TABLE_1.C` 179–215 行），保证渐近行为正确。

#### 2.2.3 电荷态（无 Saha 方程）

FEOS 不解 Saha 平衡，而用更简化的判据——**自洽势中总能量为正的电子视为自由**
（CPC 脚注 1）。数值实现（`getQ`，`LIB-02_TF_TABLE_1.C` 476–500 行）由 TF 压力反演：

$$a_r = \frac{p}{2 C_1 T^{5/2}/3}, \qquad C_1 = \frac{\sqrt{2}}{\pi^2} = 0.143289792$$

$$z_1 = F_{3/2}^{-1}(a_r) \quad (\text{Fermi 积分逆，快速近似}), \qquad
\bar{Z} = \frac{m_p}{\rho} C_1 T^{3/2} \tilde{F}(z_1)$$

- $F_{3/2}^{-1}$: Fermi 积分 $F_{3/2}$ 的逆函数（源码 `fermi_1`/`quickfermi_oh` 快速近似）
- $\tilde{F}$: 精化函数（`quickfermi_oh`）

反压极限（$a_r > 10^{12}$，冷/极高压）切换到冷曲线幂律反演：

$$\bar{Z} \propto \frac{p^{3/5}}{\rho}$$

这就是 `.feos` 中 Qtot/Q 块的来源；feos_to_cn4 的 zbar/dzdt 亦源于此
（dzdt = $\partial \bar{Z}/\partial T|_\rho$，由 Qtot 数值微分；FLASH EOS 的 $Q^0$ 判据必须真值）。

### 2.3 离子部分：Cowan 模型

离子贡献在 $T < 10\ \mathrm{eV}$ 且 $\rho \lesssim 2\rho_s$ 时主导总 EOS；高 $T$/高 $\rho$ 下电子部分主导。
Cowan 模型 = **经验部分（密度依赖标度）+ 结构部分（固/液分支自由能公式）**，
在已知极限（理想气体、Debye 固体、Dulong–Petit、液体标度律）间平滑插值。

#### 2.3.1 经验部分（`getEmpiricalModel`，135–160 行）

定义 $\xi = \rho/\rho_{\mathrm{ref}}$，其中参考密度与 Cowan 常数

$$\rho_{\mathrm{ref}} = \frac{\bar{A}}{9 \bar{Z}^{0.3}}, \qquad b = 0.6\, \bar{Z}^{1/9}$$

$$\text{Debye 温度: } kT_d = \frac{1.68}{\bar{Z}+22} \cdot \frac{\xi^{b+2}}{(1+\xi)^2} \quad [\mathrm{eV}]$$

$$\text{熔化温度: } kT_m = 0.32 \cdot \frac{\xi^{2b + 10/3}}{(1+\xi)^4} \quad [\mathrm{eV}] \quad (\text{Lindemann 型})$$

$$\gamma_s = b + \frac{2}{1+\xi} \ (\text{固态}), \qquad
\gamma_F = \frac{(3b-1)\rho + (3b+5)\rho_{\mathrm{ref}}}{\rho + \rho_{\mathrm{ref}}}$$

- $\bar{A}, \bar{Z}$: 原子分数加权的平均原子量/核电荷数
- $\gamma_s/\gamma_F$: 固态/液态 Grüneisen 参数

#### 2.3.2 结构部分（`getIonicQuantities`，164–212 行）

无量纲变量 $u = kT_d/T$、$w = kT_m/T$。固/液由 $w > 1$ 判据切换：

| 相 | 判据 | 自由能 $f$（源码函数） |
|---|---|---|
| 固（冷支） | $w>1$, $u\ge 3$ | `get_f_cold_solid`: $f = 3\left(1 + \dfrac{6}{u^3} + \dfrac{6}{u^2} + \dfrac{3}{u}\right) e^{-u} - \dfrac{\pi^4}{5u^3} + \dfrac{9u}{8} + 3\ln\left(1 - e^{-u}\right)$；$u>50$ 渐近 $f = 9u/8$ |
| 固（热支） | $w>1$, $u<3$ | `get_f_hot_solid`: $f = -1 + \dfrac{3u^2}{40} - \dfrac{u^4}{2240} + 3\ln u$（6 次幂项按源码注释被有意舍弃） |
| 液 | $w\le 1$ | `get_f_liquid`: $f = -5.5 + 4.5\, w^{1/3} + 1.5 \ln\left(\dfrac{u^2}{w}\right)$ |

热力学量由 $f$ 合成（cgs 换算内含 eV2cgs，$\bar{m}_p = \bar{A} m_p$；$f_u \equiv \partial f/\partial u$）：

$$F_i = \frac{f \cdot T}{\bar{m}_p}, \qquad S_i = \frac{\epsilon_i - F_i}{T} \qquad (\text{两相通用})$$

**液相**（$w \le 1$）：

$$\epsilon_i = \frac{3}{2} \frac{T}{\bar{m}_p}\left(1 + w^{1/3}\right), \qquad
p_i = \frac{\rho T}{\bar{m}_p}\left(1 + \gamma_F w^{1/3}\right)$$

**固相**（$w > 1$）：

$$\epsilon_i = \frac{kT_d \, f_u}{\bar{m}_p}, \qquad
p_i = \frac{\rho^2 f_u \, (\partial kT_d / \partial \rho)}{\bar{m}_p}$$

**性质与局限**：离子 EOS 为**纯热性质**——Coulomb 与键合能量分别落在电子分量与键合修正中；
模型不含熔化体积变化（"熔融无潜热"近似），固/液由 $w = kT_m/T$ 平滑衔接。

### 2.4 冷曲线修正

TF 冷曲线在参考点 $(\rho_0, T_0)$（通常取常压固态点）不满足 $p = \epsilon = 0$。
FEOS 提供两档修正（`.par` 的 `SoftSphere_Flag` 切换）：

#### 2.4.1 Bonding correction（QEOS 原方案，`get_bonding_contrib` 325–335 行）

指数型吸引项：

$$\epsilon_b(\rho) = \epsilon_0 \left[1 - e^{\,b\left(1 - (\rho_0/\rho)^{1/3}\right)}\right]$$

$$p_b(\rho) = -\frac{\epsilon_0 \, b \, \rho_0}{3} \; e^{\,b\left(1 - (\rho_0/\rho)^{1/3}\right)} \left(\frac{\rho}{\rho_0}\right)^{2/3}$$

两个参数在参考点自洽解出（`getBondingParameters` 216–243 行，$p_{\mathrm{solid}} = p_e + p_i$ 于参考点）：

$$b = -2 + 3\,\frac{\rho_0 \left(\frac{\partial p}{\partial \rho}\right)_{\mathrm{solid}} - K_0}{p_{\mathrm{solid}}}, \qquad
\epsilon_0 = \frac{3\, p_{\mathrm{solid}}}{b\, \rho_0}$$

- $K_0 = \rho (\partial p/\partial \rho)_s$: 用户给定体模量（等温/等熵差异通常忽略）
- $(\partial p/\partial \rho)_{\mathrm{solid}}$: 参考点附近数值微分（源码用 ±0.1% 密度）

#### 2.4.2 Soft-sphere 改进（FEOS 增量，Young & Corey 1995）

即使有键合修正，QEOS 仍高估临界点（Al：MPQeos2.0 给 $T_c = 13487$ K / $p_c = 23487$ bar，
实验 ~5700 K / 1820 bar——CPC Table 1）。`SoftSphere_Flag = 1` 时，$\rho < \rho_0$ 区段
**整体替换** TF 冷曲线与键合修正（`GetElectronEOSQuantities` 31–37 行：TF 冷贡献被减去、
软球量被加入）：

$$\epsilon_{\mathrm{cold}}(\rho, T=0) = A_s \rho^{n_s} - B_s \rho^{m_s} + \epsilon_{\mathrm{coh}}$$

$$p_{\mathrm{ss}} = n_s A_s \rho^{n_s + 1} - m_s B_s \rho^{m_s + 1}$$

- $\epsilon_{\mathrm{coh}}$: 比内聚能（升华焓，Material-DB 提供）
- $A_s, B_s$: 由参考点条件 $p(\rho_0, T_0) = 0$、$\epsilon(\rho_0, T_0) = 0$ 解析解出
  （`getBondingParameters` 250–258 行）：

$$A_s = \frac{\epsilon_0^{ss} - \epsilon_{\mathrm{coh}} - p_0/(m_s \rho_0)}{\rho_0^{n_s}\left(1 - n_s/m_s\right)}$$

- $\epsilon_0^{ss}, p_0$: 参考点处扣除电子/离子分量后的目标余量（源码 `pe_zero`/`Ee_zero` 路径）

自由参数 $m_s, n_s$ 用来拟合临界点。效果（CPC Table 1，Al，$m_s = 0.5,\ n_s = 2.0$，
$\epsilon_{\mathrm{coh}} = 12.123\ \mathrm{kJ/g}$）：

| 模型 | $T_c$ [K] | $p_c$ [bar] |
|---|---|---|
| 实验（Young & Corey 1995 参考值） | 5700 | 1820 |
| MPQeos 2.0（无软球） | 13487 | 23487 |
| **FEOS 16.7（软球）** | **5558** | **1722** |

⚠️ 在 $\rho = \rho_0$ 处声速允许不连续（软球只作用于低密度侧）。

#### 2.4.3 能量零点约定

电子/离子能量偏移取参考点值（`getBondingParameters` 246–248 行）：

$$E_{e,\mathrm{Offset}} = \epsilon_e(\rho_0, T_0), \qquad E_{i,\mathrm{Offset}} = \epsilon_i(\rho_0, T_0)$$

使 $\epsilon(\rho_0, T_0) = 0$——feos_to_cn4 转出的 cn4 能量零点继承此约定。

### 2.5 混合物

NE 元素均匀混合物（组成由 Material-DB 的 $A[i], Z[i], X[i]$ 描述，$X$ = 每分子原子数，
原子分数 $x_{E,i} = X_i/\sum_j X_j$；$\bar{Z} = \sum_i x_{E,i} Z_i$，$\bar{A} = \sum_i x_{E,i} A_i$）：

- **离子分量 + 键合修正**：视作单一种"平均元素"（$\bar{Z}, \bar{A}$），直接套用 §2.3/§2.4 公式。
- **电子分量**：逐元素处理，两条件迭代求解（`mixture_getallquantities`，38–105 行；
  $m \le MAXIT$ 迭代 + Ridder 求根 `getrho_Ridder`）：

$$\text{(1) TF 压力平衡:} \quad p_{e,i}(\rho_i, T) = \bar{p}_e \quad \forall i$$

$$\text{(2) 加体积规则:} \quad \frac{\bar{A}}{\rho} = \sum_i \frac{x_{E,i} A_i}{\rho_i}$$

  电子能量/熵/自由能/电荷按质量分数加权求和：

$$\epsilon_e = \sum_i \frac{x_{E,i} A_i}{\bar{A}} \epsilon_{e,i}(\rho_i, T)$$

- 该流程对每个 $(\rho, T)$ 点都要嵌套两层数值求根 → **混合物比单元素慢约两个数量级**
  （Al $\langle t_{\mathrm{point}}\rangle = 6.2\times10^{-6}$ s vs SiO2 $3.7\times10^{-4}$ s，见 §8.2）。
- 循环不收敛防护：源码检测 $\rho_{\mathrm{tot}}$ 振荡（endlloop），对迭代解做两点平均。

### 2.6 液-汽两相区与 Maxwell 构建

#### 2.6.1 MS-EOS 与 EQ-EOS

不做 Maxwell 构建时，模型输出含 van der Waals 环的**亚稳态 EOS**（MS-EOS），其中
$(\partial p/\partial v)_T > 0$ 段机械不稳定；spinodal（等温线极值点轨迹）围出绝对失稳区，
binodal（双节线）围出两相共存区。Maxwell 构建（`Maxwell_Flag = 1`）把环替换为水平平衡线，
得**完全平衡 EOS**（EQ-EOS）。

#### 2.6.2 热力学判据与数值流程

$$\text{相平衡:} \quad \mu_l(T, p_{EQ}) = \mu_v(T, p_{EQ}) \;\Longleftrightarrow\; g_l = g_v,
\qquad g = f + pv$$

（$g$–$p$ 平面等温线上液体支与蒸汽支曲线的交点给出 $p_{EQ}$。）

$$\text{临界点:} \quad \left(\frac{\partial p}{\partial v}\right)_T = 0, \quad
\left(\frac{\partial^2 p}{\partial v^2}\right)_T = 0
\quad \left(\text{兼} \left(\frac{\partial T}{\partial s}\right)_p = \left(\frac{\partial^2 T}{\partial s^2}\right)_p = 0\right)$$

两相区内热力学量按杠杆规则线性插值：

$$\epsilon(v, T) = \epsilon_l + (\epsilon_v - \epsilon_l)\,\frac{v - v_l}{v_v - v_l}, \qquad v = 1/\rho$$

数值流程（`CriticalData` 类，`LIB-06_MAXWELL.C` 构造器 19–73 行）：

1. `CritPoint()`：$T$ 递增扫描等温线，用 `contains_loop`（`LIB-05` 158–183 行，含数值噪声
   裕度 `CONTAINS_LOOP_NUM_NOISE`）找**第一条无 van der Waals 环等温线** → 临界点估计；
2. `vaporisation_curve()`：$T < T_c$ 的等温线网格上 `getPmax_Pmin` 找每条等温线的环极值
   $(p_{max}, \rho_{max})$、$(p_{min}, \rho_{min})$；
3. $g$–$p$ 平面迭代二分求 $(g_{EQ}, p_{EQ})$ 交点（`derivP1` 用 ±1% 密度中心差分）；
4. 两相区内热力学量按杠杆规则线性插值。

`Maxwell_Flag = 1` 时额外输出 `.critical.dat`（临界点 + binodal + spinodal 全数据）。

⚠️ Maxwell 温度网格质量直接决定临界数据质量——临界区附近须布足够多点；室温附近蒸汽支
密度极低，双精度下限约束使构建在 ~100 K 以下可能失败（feos 打印警告）。

#### 2.6.3 非同余相平衡（未实现）

化合物（SiO2、UO2、NaCl…）的真实蒸发是**非同余**的（如 SiO₂ ⇌ SiO + ½O₂，两相化学组成
不同），严格处理需对每个基本组分分别写化学势方程（CPC Eq. 15–16，Gibbs 非同余条件）：

$$\mu_{Si,1}(T, p, x_1) = \mu_{Si,2}(T, p, x_2), \qquad \mu_{O,1}(T, p, x_1) = \mu_{O,2}(T, p, x_2)$$

**FEOS 现版按强制同余（forced congruent）处理化合物**——单一总化学势方程；理论框架可
扩展但未实现。这解释了 SiO2 临界点各模型间巨大分歧（CPC Table 3：$T_c$ 5000–13000 K）。

### 2.7 与 SESAME 的关系

SESAME（LANL, LA-UR-92-3407）约 150 种材料的权威多模型拼接表；FEOS 走相反路线：
**单一自洽模型 + 少量标定参数** → 任意材料即取即用、表与表完全平滑。FEOS 表生成工具亦
支持输出 SESAME 格式（`.301/.304/.305` 序列，feos 运行副产物，feos_core 默认清理）。
临界点以下温度，若可用，优先 SESAME/DFT-MD 级数据（CPC 明示建议）。

---

## 3. 代码结构

### 3.1 包组成

```
feos (表生成工具) ──┬── FEOS library (libfeos.a)   ← EOS 内核（TF 插值/Cowan/Maxwell）
                    ├── .par 输入卡                 ← §4
                    └── 输出: .feos / .critical.dat / SESAME 格式（§5）
showeos (可视化) ── 独立工具，读 .feos/SESAME 表 → 等温线/等熵线/Hugoniot
```

### 3.2 源码文件一览（`src/FEOS/Code/`）

| 文件 | 职责 |
|---|---|
| `LIB-00_DEFINITS.H` | 常量（`C1`=√2/π²、`T_ZERO`、`RHO_ZERO`、`TSCALE`）与数据文件路径（CWD 相对） |
| `LIB-01_TF_SERVICES.C` | TF 表读取 + Fermi–Dirac 快速函数（$F_{1/2}$、$F_{3/2}$ 及逆） |
| `LIB-02_TF_TABLE_1/2.C` | 单元素 TF EOS 插值方案（`QIPscheme` 类：缩放律/bicubic 插值/8 种外推）+ 电荷反演 `getQ` |
| `LIB-03_TF_MIXTURE.C` | 混合物电子分量（压力平衡 + 加体积规则迭代） |
| `LIB-04_IONMOD.C` | Material-DB 读取 + Cowan 离子 EOS + bonding + soft-sphere（`Ionpart` 类） |
| `LIB-05_EOS_SERVICES.C` | 组装分项（无 Maxwell）、能量偏移、van der Waals 环检测 |
| `LIB-06_MAXWELL.C` | Maxwell 构建（`CriticalData` 类：临界点/汽化线/沸点） |
| `LIB-07/08_*_INTERFACE.C` | C / Fortran 调用接口 |
| `FE-01_TABTOOLS.C` | 表写出（**`.feos` 格式权威定义** `write_FEOS_format` 196–355 行） |
| `FE-02_CALCULATIONS.C` | 用户自定义计算（等压线等） |
| `FE-03_MAIN.C` | 表生成工具主程序（CLI/模式分派/7 种输出） |
| `SE-01..04_*.C` | SHOWEOS 可视化工具 |
| `COMMON-01/02_*.C` | 工具函数 + `.par` 输入卡解析（`readfile`） |

---

## 4. 输入文件 (.par)

feos CLI: `./feos <basename>`（**不带 .par 后缀**，`FE-03_MAIN.C` 自动拼接 `.par`；
可再跟 `<rho> <T>` 进入单点模式）。表生成模式只读 `Computation-Settings` 与 `Q-table` 两节。

### 4.1 参数详解

| 参数 | 含义 | 单位/取值 |
|---|---|---|
| `Material-Number` | Material-DB 条目号（如 Al=3717, SiO2=7386） | 1000–9999 |
| `Rhonorm` | 密度网格归一化基准 $\rho_{\mathrm{norm}}$ | g/cm³ |
| `Rhoratio-x` | 区间 $[\rho_{\mathrm{norm}} 10^{x-1},\ \rho_{\mathrm{norm}} 10^{x}]$ 内对数分布点数 | x = −6..6 |
| `Tnorm` | 温度网格归一化基准 $T_{\mathrm{norm}}$ | eV |
| `Tratio-x` | 区间 $[T_{\mathrm{norm}} 10^{x-1},\ T_{\mathrm{norm}} 10^{x}]$ 内点数 | x = −6..6 |

要点：
- 区间号 x = −6..6（`getPointDensity` 以 `%s%d` 拼 key，如 `Rhoratio-2`/`Rhoratio0`）；
- **网格总点数 = 1 + Σ ratio**（首点是 Qstart = 0.0，含 Rho0/T0 哨兵语义）；
- ratio 负数会被 `ME-ERROR` 拒绝；区间为 0 时该十进制 decade 跨越（q×10）无采样；
- showeos 各节（General/Units/Rho-T-Mesh/Isocurves/Mountain/Hugoniot）表生成模式不读，
  `FEOSInputGen.generate_par()` 不生成（保持最小输入卡）。

### 4.2 控制开关

| 开关 | 含义 | 物理效果（详见） |
|---|---|---|
| `Maxwell_Flag = 1` | 执行 Maxwell 构建 | 两相区替换为 EQ-EOS + `.critical.dat`（§2.6）；**耗时大增**（SiO2 5.4 s → 167 s） |
| `SoftSphere_Flag = 1` | 启用软球冷曲线 | ρ < ρ₀ 区段替换 TF 冷曲线+键合（§2.4.2）；拟合临界点 |
| `UserCalculations_Flag = 1` | 执行用户自定义计算 | 附加等压数据文件输出（FE-02）；不需要可关（提速） |

### 4.3 完整输入文件示例

**示例 1: 铝（Al, Material-Number 3717，= vendored `EOS-Data/Al.par` 对照）**

```
                   Computation-Settings

Material-Number = 3717       % Material number in FEOS parameter database
Maxwell_Flag = 1             % "Maxwell construction" desired? (0: no, 1: yes)
SoftSphere_Flag = 1          % Replace TF cold curve for densities < Rsolid with
                             %   soft sphere function? (0: no, 1: yes)
UserCalculations_Flag = 1    % Perform user-defined calculations? (0: no, 1: yes)

                   Q-table

% Distribution of densities:
Rhonorm = 2.7     % Norm in g/cm^3
Rhoratio-6 = 0
Rhoratio-5 = 3
...
Rhoratio0 = 50
...
Rhoratio6 = 3

% Distribution of temperatures:
Tnorm = 1.0e3     % Norm in eV
Tratio-6 = 1
...
Tratio6 = 1
```

**示例 2: 融熔石英 SiO2（Material-Number 7386，混合物）**

同结构，`Material-Number = 7386`、`Rhonorm = 2.2`；组成（A/Z/X）不在 .par 中，
而在 Material-DB 条目 `Material-7386:` 内（`Number-of-Elements = 2`，Si: A=28.09, Z=14, X=1；
O: A=16.00, Z=8, X=2）。软球参数 $\epsilon_{\mathrm{coh}} = 9.74\ \mathrm{kJ/g}$、
$m_s = 0.8$、$n_s = 2.8$（拟合临界点 $T_c = 6300$ K, $p_c = 3500$ bar——Iosilevskiy & Gryaznov）。

**新增材料的 Material-DB 条目字段**（§9 Q1）：

```
[<num>]_SESAME-Number, [num]_Treference [eV], [num]_Rhoreference [g/cm^3],
[num]_Bulk-Modulus [dyne/cm^2], [num]_Number-of-Elements,
[num]_A[i]/Z[i]/X[i] (i=1..N), [num]_Ecohesive [erg/g],
[num]_Soft-Sphere-m, [num]_Soft-Sphere-n
```

---

## 5. 输出文件详解

### 5.1 .feos — 原生 EOS 表（逐块对照）

一手依据：`FE-01_TABTOOLS.C` `write_FEOS_format`（196–355 行）。全文件为连续数值流
（每值 `%15.8le`，分隔符为空串）：

| 段 | 数量 | 内容 |
|---|---|---|
| 行 0 | 10 | FileVersion(12.06), NRho, NT, Nelements, Tcalclimit, Rhocalclimit, RhoRef, TRef(eV), B0, SESAME# |
| 行 1 | 10 | ElectronOffset, IonOffset, Ecoh, ss_n, ss_m, ss_A, ss_B, **Atot, Ztot, Xtot** |
| A/Z/X | 各 Nelements | 元素原子量/原子序数/每分子原子数 |
| rho 网格 | NRho | g/cm³，**首点 0.0 哨兵** |
| T 网格 | NT | eV，**首点 0.0 哨兵** |
| 16 个二维块 | 各 NRho×NT | P,E,S,F（总）→ Pe,Ee,Se,Fe（电子）→ Pi,Ei,Si,Fi（离子）→ PTF,ETF,STF,FTF（TF） |
| Qtot | NRho×NT | 总电荷态 |
| Q[k] | Nelements × NRho×NT | 分元素电荷态 |

二维块循环序：**T 外循环、rho 内循环**（T-major）；单位 cgs+eV（P: dyn/cm²，E/S/F: erg/g 类）。
行 1 的 ElectronOffset/IonOffset 即能量零点偏移（§2.4.3），ss_* 为软球参数 $A_s/B_s/m_s/n_s$。

> ⚠️ eosop_pro `feos_native.py` 的"数据块列序未定（R3）"已由本表（源码）定案；
> 其头部/网格解码（含 NR/NT 单调性裁剪）与源码一致，可交叉校验。

### 5.2 副产物文件系列

| 文件 | 条件 | 内容 |
|---|---|---|
| `.feos` | 总是 | 原生 EOS 表（§5.1） |
| `.critical.dat` | Maxwell_Flag=1 | 临界点 + binodal + spinodal 全数据（§2.6.2） |
| `.301/.304/.305` | 总是 | SESAME 301/304/305 格式表（总 EOS/电子/离子分量） |
| `.mexport` | 总是 | Maxwell/临界数据导出 |
| `.txt` | UserCalculations_Flag=1 | 等压扩展数据（FE-02 `write_isobaricdata`） |

`FEOSInputGen._clean_output_folder()` 默认只保留 `feos`、两个 dat、`.par`、`.feos`/`.cn4`
（副产物丢弃；需要时改清理列表）。

### 5.3 单点模式

`./feos <basename> <rho> <T>`：对单点 $(\rho, T)$ 直接向 stdout 打印全部热力学量，
不写表文件——调试验证模型行为时常用。

---

## 6. Python 输入文件生成器

### 6.1 FEOSInputGen 类

```python
from feos_core import FEOSInputGen

gen = FEOSInputGen()
gen.set_parameter('material_number', 3717)
gen.set_ratio_distribution('rhoratio', {-6: 0, -5: 3, ..., 0: 50, ..., 6: 3})
gen.set_elements([(13.0, 1.0)])            # 用于输出命名（可省略，自动查 Material-DB）
par = gen.generate_par(output_dir, basename)   # 仅写 .par 不运行
feos_path = gen.run_single(params_dict, output_base_dir)   # 完整流程
paths = gen.batch_run(params_list, output_base_dir)        # 批量
```

`run_single(params_dict, output_base_dir)` 流程：

1. `_dict_to_parameters`：还原参数（`'_elements'` 组成列表、`'_name'` 示例名、
   `rhoratio`/`tratio` 区间字典）；
2. **Material-Number 预检**：`_check_material_number()` 扫描 Material-DB，
   缺失即抛错并列出全部可用条目；组成未显式给出时从 DB 反查 A/Z/X；
3. 建工作目录 `{basename}-{timestamp}`（basename = `Z13_1.00` 或
   `Z14_0.33-Z08_0.67`，**无群数后缀**）；
4. `_copy_feos_binaries`：feos 二进制 + 2 个 dat 拷入（二进制缺失时先 `make all`）；
5. `generate_par` 写 `<basename>.par`；
6. `_wsl_run`：`wsl --cd <wsl路径> ./feos <basename>`（先 chmod +x，timeout 600 s），
   stdout/stderr 落 `_stdout.log`/`_stderr.log`；
7. `<basename>.feos` → 重命名 `{basename}-{timestamp}.feos`，0 字节/缺失时从
   运行日志提取 `FE-ERROR`/`LIB-ERROR`/`ME-ERROR` 提示；
8. `_clean_output_folder`：只保留 `feos`、两个 dat、`.par`、`.feos`/`.cn4`。

### 6.2 feos_to_cn4 转换器

```python
from feos_to_cn4 import feos_to_cn4, read_feos
tbl = read_feos("Z13_1.00-20261114_2316.feos")       # 完全解码（16 块 + Qtot + Q）
cn4 = feos_to_cn4("Z13_1.00-20261114_2316.feos",
                  "al.cn4", ngrups=None, grupbd=None)  # 默认 DEFAULT_GRUPBD（7 边界=6 群）
```

**块映射与单位换算**（`parsed_tables_to_cn4` 跨族路径，字段用 cn4 原生标签直通）：

| cn4 块 | 来源 | 换算 | 说明 |
|---|---|---|---|
| zbar | Qtot / Xtot | ÷Xtot（每核归一） | **Qtot = Σₖ Qₖ·Xₖ 是每化学式总量**（LIB-03_TF_MIXTURE.C:123 + FE-03:267 "for molecule"）；cn4 zbar = 每核平均；ne=1 时 Xtot=1 无差别，混合物（SiO2）必须除（实测 zbar 上限 10 = 30/3） |
| dzdt | Qtot 对 T 中心差分，再 ÷Xtot | 1/eV | 端点单侧；**FLASH USED，必须真值** |
| p_ion | Pi | dyn/cm²→J/cm³ ×1e-7 | |
| p_ele | Pe | ×1e-7 | FEOS 内 p = p_i + p_e，守恒 |
| e_ion | Ei | erg/g→J/g ×1e-4 | |
| e_ele | Ee | ×1e-4 | |
| dpion_dt / dpele_dt / cv_ion / cv_ele / deion_dn / deele_dn | — | NaN 占位 | FLASH ignored（eosop_pro 既有约定） |

**Q 块排布（2026-11 定案）**：k 最内层交错（`for j, for i, for k`，FE-01_TABTOOLS.C
348–353）；混合物用 zbar = Σₖ (Xₖ/ΣX)·Qₖ 守恒检验判定（连续块解释被否证）。

**网格**：默认保留 .feos 原生对数网格（cn4 轴显式，FLASH 从文件读取）；修剪
Qstart=0.0 哨兵点（cn4 轴须严格正）。密度轴换算 $n_{\mathrm{ion}} = \rho N_A / \langle A \rangle$
（$\langle A \rangle = A_{\mathrm{tot}}/X_{\mathrm{tot}}$；SiO2 → 20.02）。
cn4 头部组成：`izgas←Z[]`、`atomwt←A[]`、`fracsp←X[]` 归一化原子分数。

**不透明度决策**：FEOS 不产生不透明度 → 默认 `ngrups=6`（DEFAULT_GRUPBD 7 边界，
与现役 ionmix 表同构）+ **零填充**；备选 `ngrups=0`。
⚠️ 转换出的 cn4 **不透明度块为 0 占位，禁止消费**（EOS-only 用途）。

**验证环**（已在 Al/SiO2 上执行通过）：`parse_cn4` 18 块计数守恒（389906=389906）→
轴单调 → zbar ∈ [0, Ztot] → 全表逐点保真度 < 1.2e-5（E12.6 量化极限）→
generator 自动发现注册表新表。

### 6.3 典型示例参数设置

**Al（单元，Material-Number 3717，= vendored Al.par 对照）**

```python
{'_name': 'Al', '_elements': [(13.0, 1.0)], 'material_number': 3717,
 'maxwell_flag': 1, 'softsphere_flag': 1, 'user_calculations_flag': 1,
 'rhonorm': 2.7,
 'rhoratio': {-6: 0, -5: 3, -4: 3, -3: 3, -2: 10, -1: 50,
              0: 50, 1: 50, 2: 10, 3: 3, 4: 3, 5: 3, 6: 3},
 'tnorm': 1.0e3,
 'tratio': {-6: 1, -5: 2, -4: 10, -3: 20, -2: 20, -1: 10,
            0: 2, 1: 1, 2: 1, 3: 1, 4: 0, 5: 0, 6: 0}}
```

**SiO2（混合物，Material-Number 7386；注意 `_elements` 给的是 X 值而非分数）**

```python
{'_name': 'SiO2', '_elements': [(14.0, 1.0), (8.0, 2.0)], 'material_number': 7386,
 'maxwell_flag': 1, 'softsphere_flag': 1, 'user_calculations_flag': 1,
 'rhonorm': 2.2,
 'rhoratio': {…同 Al…}, 'tnorm': 1.0e3, 'tratio': {…同 Al…}}
```

**Au（高 Z 模板，Material-Number 2700，= gen_mywork）**

```python
{'_name': 'Au', '_elements': [(79.0, 1.0)], 'material_number': 2700,
 'rhonorm': 19.3, ...}   # 其余同 Al 模板
```

gen 脚本入口：

```bash
python gen_examples.py               # Al + SiO2（vendored 全部示例）
python gen_examples.py Al --cn4      # 名称过滤 + 联动 cn4 转换
python gen_examples.py --no-copy     # 不复制到 eos_op_data/
python gen_mywork.py                 # 用户模板（Au 示例，复制改名后修改）
```

---

## 7. 运行流程

### 7.1 目录结构

```
feos/src/FEOS/
├── Code/                # C++ 源码 + Makefile（编译产物 feos 亦在此）
├── EOS-Data/
│   ├── Al.par, SiO2.par          # vendored 示例输入卡（= gen_examples 的对照）
│   ├── FEOS_Material-DB.dat      # 材料参数数据库（7.7 KB，Material-Number 1000-9999）
│   └── FEOS_TF-Table_1197.dat    # 氢 TF 插值表（567 KB，u-t 网格主函数 h 及其导数）
└── Documents/           # PDF 文档 + Info.txt + License.txt

feos/outputfiles/feos/<脚本名>/<basename>-<timestamp>/   # 每次 run 的工作目录
```

### 7.2 Python 自动运行（推荐）

```bash
python gen_examples.py Al --cn4    # 生成 → 运行 → 转换 → 校验一条龙
```

### 7.3 手动运行

```bash
# 1. 准备工作目录（feos 二进制 + 2 个 dat 必须在场——CWD 相对路径）
cp feos/src/FEOS/Code/feos feos/src/FEOS/EOS-Data/FEOS_*.dat  <workdir>/
# 2. 写输入卡（不带后缀运行）
cd <workdir> && ./feos Al
# 3. 查看结果
ls Al.feos && tail _stdout.log
```

### 7.4 编译说明

一次性编译（产物跨 run 复用）：`_ensure_feos_binary()` 在 `Code/` 内 `wsl ... make all`；
WSL 需 `g++` 与 `make`（`sudo apt install g++ make`）。产物 `libfeos.a` + `feos`（+
Makefile 自动拷贝到 `../EOS-Data/` 的副本）。

---

## 8. 限制与注意事项

### 8.1 物理限制

- 简单 TF 无壳层/交换/相对论效应 → 电离态在壳层过渡区粗糙（zbar 仅热力学自洽用途，
  **勿用于光谱诊断级电离分布**——那是 flychk/IONMIX 的领域，§9 Q5）；
- 临界点附近压力（即使有软球）往往仍偏高；$T \lesssim T_c$ 区域建议核对更高级 EOS；
- 化合物按强制同余处理，无解离化学（§2.6.3）；
- 无熔化相变（无熔融潜热/体积突变）；固-液由 Cowan 模型平滑衔接；
- 混合物 >3 元素数值困难。

### 8.2 数值限制

- 适用域 $10^{-7} \le \rho/\rho_0 \le 10^6$、$10^{-4}\ \mathrm{eV} \le T \le 10^6\ \mathrm{eV}$；
- 数值下限 `RHO_ZERO = 1e-50 g/cm³`、`T_ZERO = 1e-4 eV`，低于此取极限律（§2.2.2 外推分支）；
- Maxwell 构建在室温以下（~100 K）蒸汽支密度过低可能失败（feos 打印警告）；
- 性能基准（CPC Table 2，i7-7920HQ 单线程，表网格 191×68）：

| EOS | 全表耗时 | ⟨单点⟩ |
|---|---|---|
| Al（无 Maxwell） | 0.46 s | 6.2e-6 s |
| Al（含 Maxwell） | 4.98 s | 1.9e-5 s |
| SiO2（无 Maxwell） | 5.43 s | 3.7e-4 s |
| SiO2（含 Maxwell） | 167.2 s | 6.6e-4 s |

本项目实测（WSL，gen_examples）：Al 191×69 ≈ 数秒；SiO2 ≈ 38 s——同一量级。

### 8.3 常见警告与陷阱

1. **`feos <name>` 不带 `.par` 后缀**（自动拼接）；
2. **dat 文件 CWD 相对路径** —— 必须拷入运行目录（封装已处理）；
3. **Qstart=0.0 前导哨兵** —— 网格首点为 0，下游对数插值需修剪；
4. **间歇性 buffer overflow**（glibc `sprintf_chk` 检测，编译警告所示 char[70] 缓冲区）
   —— 上游代码问题，崩溃后重跑即可；产物以 `.feos` 存在为准；
5. **cgs 单位** —— p: dyn/cm²、ε: erg/g，转 cn4 时 ×1e-7/×1e-4；
6. **低密度角点伪影** —— 最低 (rho, T) 角点总 p 可能 ≠ p_i + p_e（数值退化），
   cn4 侧取分项故自洽；比对原始总 p 时注意；
7. **E12.6 量化** —— cn4 全部数值仅 6 位有效数字，保真度上限 ~1e-5 相对；
8. **混合物 X[] 语义** —— 每分子原子数（原子分数由此归一化），勿当摩尔分数；
9. **Git Bash 下 `wsl --cd`** 会被 MSYS 路径转换破坏（ERROR_PATH_NOT_FOUND），
   改用 `wsl bash -c "cd ..."`；Python subprocess 不受影响。

---

## 9. 常见问题

### Q1: 如何添加新材料？

Material-DB（`EOS-Data/FEOS_Material-DB.dat`）新增条目（Material-Number 1000–9999），
必填：SESAME-Number（可自编）、Treference/Rhoreference（参考点，通常取常压固态）、
Bulk-Modulus $K_0$、Number-of-Elements + A[i]/Z[i]/X[i]；SoftSphere_Flag=1 时还需
Ecohesive、Soft-Sphere-m/n。参考点选择准则：$p = 0$ 处材料为固态（即 $T_0 \ll T_c$）。

### Q2: Maxwell_Flag 开还是关？

- 辐射流体算例只关心单相区（$\rho > \rho_c$ 或 $T > T_c$）→ 关（提速 10–30×）；
- 涉及蒸发/膨胀进入两相区（薄箔爆轰、泡沫膨胀）→ 开，且临界区附近温度网格要密。

### Q3: 软球参数 m_s/n_s 怎么定？

自由参数，用于把临界点拟合到理论/实验值。已标定：Al（$m=0.5, n=2.0$，
$\epsilon_{\mathrm{coh}} = 12.123\ \mathrm{kJ/g}$ → $T_c = 5558$ K）、
SiO2（$m=0.8, n=2.8$，$\epsilon_{\mathrm{coh}} = 9.74\ \mathrm{kJ/g}$，$T_c = 6300$ K 目标）。
新材料的可行做法：先取 Al/SiO2 量级，跑 Maxwell 后对照文献临界点微调。

### Q4: 如何把 .feos 用于 FLASH？

`python feos_to_cn4.py <in.feos> [out.cn4]`（或 gen 脚本 `--cn4`）→ cn4 拷入
`eos_op_data/Gen_eos_op_data/<stem>/` → generator 自动发现。**不透明度块为零占位，
禁止消费**（EOS-only 场景使用，勿配辐射算例）。

### Q5: 电荷态 zbar 可靠吗？

热力学自洽用途（FLASH EOS $Q^0$ 判据）可靠；但它是 TF 压力反演的正能电子判据，
**无壳层结构**，不可用于光谱诊断级电离分布（谱线强度比等）——用 flychk/IONMIX。

### Q6: 如何加快混合物计算？

按性价比排序：① `Maxwell_Flag = 0`（30×）；② `UserCalculations_Flag = 0`；
③ 缩减网格点数（Q-table 的 ratio 总和）；④ 混合物尽量 ≤ 3 元素。

### Q7: 运行崩溃/无输出怎么办？

看 `_stderr.log`/`_stdout.log` 的 `FE-ERROR`/`LIB-ERROR`/`ME-ERROR` 三类标记：
`ME-ERROR` = .par 网格参数非法（如负 ratio）；`LIB-ERROR` = 表/DB 不匹配或数值超限；
无标记的 `buffer overflow detected` = 上游间歇性崩溃，重跑即可（§8.3 条 4）。

### Q8: FEOS 表和 ionmix cn4 的 EOS 部分可互换吗？

同一材料两者都可用时：单位/轴格式经 feos_to_cn4 归一后一致，但**能量零点不同**
（FEOS 参考点归零 vs IONMIX 电离能基准）且物理模型不同（TF+Cowan vs IONMIX 的
Saha/日冕类模型）——**不可混用于同一场景的不同 run 之间做定量对比**；
场景内选定一种 EOS 后保持一致。

---

## 10. 参考文献

已下载至 `../Documents/`：

1. **S. Faik, A. Tauschwitz, I. Iosilevskiy**, "The equation of state package FEOS for high
   energy density matter", *Comput. Phys. Commun.* **227**, 117–125 (2018),
   doi:10.1016/j.cpc.2018.01.008 —— 权威论文（`Faik_2018_FEOS_CPC_227_117.pdf`）
2. S. Faik, M. M. Basko, A. Tauschwitz, I. Iosilevskiy, J. A. Maruhn, "Dynamics of
   volumetrically heated matter passing through the liquid–vapor metastable states",
   *High Energy Density Phys.* **8**, 349 (2012) —— 首次应用（`Faik_2012_HEDP_metastable_arXiv.pdf`）
3. S. Faik, "Radiation-Hydrodynamic Simulations of Matter at High Energy Density",
   PhD defense slides, Goethe-Universität Frankfurt (2016)（`Faik_2016_PhD_defense_slides.pdf`）

核心引文链（按需获取原文）：

4. R. M. More, K. H. Warren, D. A. Young, G. B. Zimmerman, "A new quotidian equation of state
   (QEOS) for hot dense matter", *Phys. Fluids* **31**, 3059 (1988), doi:10.1063/1.866963
   —— QEOS 原始模型（Cowan 模型细节见其引用的 LA-7313-MS, Cranfill & More 1978）
5. D. A. Young, E. M. Corey, "A new global equation of state model for hot, dense matter",
   *J. Appl. Phys.* **78**, 3748 (1995), doi:10.1063/1.359955 —— soft-sphere 冷曲线
6. A. J. Kemp, J. Meyer-ter-Vehn, "An equation of state code for hot dense matter, based on
   the QEOS description", *NIM A* **415**, 674 (1998), doi:10.1016/S0168-9002(98)00446-X
   + MPQ Report 229 —— MPQeos（FEOS 前身）
7. S. P. Lyon, J. D. Johnson, "SESAME: The Los Alamos National Laboratory equation of state
   database", LA-UR-92-3407 (1992) —— 对照相体系
8. L. H. Thomas (1927); E. Fermi (1928); R. P. Feynman, N. Metropolis, E. Teller,
   *Phys. Rev.* **75**, 1561 (1949) —— TF 模型起源与球胞解经典文献

---
**文档版本**: 3.0 · **创建**: 2026-11-14 · **更新**: 2026-11-15（按 IONMIX用户指南 目录体系重构 + LaTeX 公式化）
**依据**: FE-01/02/03 + LIB-01..06 一手源码 · Faik CPC 227, 117 (2018) 全文
**维护**: PhySimX Team
