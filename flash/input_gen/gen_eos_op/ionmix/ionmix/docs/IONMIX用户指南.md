# IONMIX 用户指南

> **IONMIX** — 计算 LTE 与非 LTE 等离子体状态方程和辐射特性的 FORTRAN 代码
>
> 原作者: J.J. MacFarlane, Fusion Technology Institute, University of Wisconsin-Madison
>
> 核心文献: *Computer Physics Communications* 56 (1989) 259–278
>
> CPC 程序号: ABJT

---

## 目录

1. [概述](#1-概述)
2. [物理模型与核心公式](#2-物理模型与核心公式)
   - [2.1 电离种群计算](#21-电离种群计算)
   - [2.2 激发种群计算](#22-激发种群计算)
   - [2.3 状态方程](#23-状态方程)
   - [2.4 吸收/发射/散射系数](#24-吸收发射散射系数)
   - [2.5 平均不透明度与冷却率](#25-平均不透明度与冷却率)
3. [代码结构](#3-代码结构)
4. [输入文件 (IONMXINP)](#4-输入文件-ionmxinp)
   - [4.1 NAMELIST 参数详解](#41-namelist-参数详解)
   - [4.2 控制开关 isw 详解](#42-控制开关-isw-详解)
   - [4.3 常数 con 数组](#43-常数-con-数组)
   - [4.4 绘图控制 iplot 数组](#44-绘图控制-iplot-数组)
   - [4.5 完整输入文件示例](#45-完整输入文件示例)
5. [输出文件详解](#5-输出文件详解)
   - [5.1 IONMXOUT — 主输出文件](#51-ionmxout--主输出文件)
   - [5.2 IONMXBUG — 详细结果文件](#52-ionmxbug--详细结果文件)
   - [5.3 IMPLOT 绘图文件系列](#53-implot-绘图文件系列)
   - [5.4 EOS.CN4 — 格式化数据表](#54-eoscn4--格式化数据表)
6. [Python 输入文件生成器](#6-python-输入文件生成器)
   - [6.1 IONMIXInputGen 类](#61-ionmixinputgen-类)
   - [6.2 典型示例参数设置](#62-典型示例参数设置)
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

IONMIX 是一个 FORTRAN 77 程序，用于计算高温（$T \geq 10^4$ K ≈ 1 eV）、低至中等密度等离子体的热力学与辐射属性。它同时考虑 **二体（辐射）** 和 **三体（碰撞）** 原子过程，计算结果适用于从高密度 **LTE**（局部热动平衡）到低密度 **非 LTE**（日冕平衡）的广泛等离子体条件。

### 1.1 主要功能

| 功能 | 描述 |
|------|------|
| 电离种群 | Saha 平衡 / 日冕平衡 / 完整三体过渡模型 |
| 激发种群 | 碰撞与辐射平衡，类氢能级近似 |
| 状态方程 (EOS) | 比内能、压力、平均电荷态、热容及导数 |
| 吸收/发射系数 | 数百个光子能量点上精确计算 |
| 不透明度 | 多群 Planck 平均（吸收/发射）和 Rosseland 平均 |
| 冷却率 | 等离子体辐射能量损失速率 |
| 多种输出 | 文本 OWT 结果、CONRAD 格式 `eos.cn4`、9 种绘图数据文件 |

### 1.2 适用条件与限制

| 条件 | 要求 | 说明 |
|------|------|------|
| 密度上限 | $n_{\text{tot}} \leq 10^{20} (T/\langle Z \rangle)^3$ cm$^{-3}$ | 粒子间势能可忽略 |
| 温度下限 | $T \geq 10^4$ K (≈ 1 eV) | 无分子振动/转动 |
| 辐射场 | 能量密度小 | 电离/激发由碰撞主导 |
| 气体种类 | ≤ 10 | 数组维度限制 |
| 原子序数 | ≤ 54 | 仅 H~Xe 有默认电离势 |
| 温度点数 | ≤ 20 | 数组维度限制（可扩展） |
| 密度点数 | ≤ 20 | 数组维度限制（可扩展） |
| 不透明度群 | ≤ 50 | 数组维度限制 |

> **性能参考**: 每个 (T, n) 点约需 0.2 秒/(气体种类 × 原子序数) CPU 时间。

---

## 2. 物理模型与核心公式

### 2.1 电离种群计算

稳态条件下，第 $k$ 种气体第 $j$ 电离态的比例 $f_{jk}$ 由碰撞电离与三种复合过程的平衡决定。下标 $j$=电离态、$k$=气体种类。

#### 2.1.1 电离态比例

$$f_{jk} = \frac{ \prod_{m=0}^{j-1} R_{m,m+1} }{ \displaystyle 1 + \sum_{m=0}^{j-1} \prod_{i=0}^m R_{i,i+1} } \cdot \frac{N_k}{\text{总核子数}}, \quad R_{m,m+1} = \frac{C_{\text{coll}}^m}{\alpha_{rr}^{m+1} + \alpha_{dr}^{m+1} + \alpha_{\text{coll}}^{m+1}}$$

其中 $C_{\text{coll}}$ 为碰撞电离速率，$\alpha_{rr}$、$\alpha_{dr}$、$\alpha_{\text{coll}}$ 分别为辐射、双电子和碰撞复合速率。

#### 2.1.2 碰撞电离速率

$$C_{\text{coll}} = \left(1.09 \times 10^{-6}~\frac{\text{cm}^3}{\text{s}}\right) \frac{n_e n_{j} \, \xi \, e^{-x}}{T^{3/2} \phi^{1/2} x}$$

- $T$: 电子温度 (eV)
- $\phi$: 电离势 (eV)
- $x = \phi / T$
- $\xi$: 外层电子数
- $\bar{g}$: Gaunt 因子（采用文献 [3] 的经验公式）

#### 2.1.3 辐射复合速率（Seaton [6]）

$$\alpha_{rr} = \left(5.20 \times 10^{-14} \frac{\text{cm}^3}{\text{s}}\right) n_e n_{j+1} \sqrt{\frac{\phi}{T}} \, E_1(x)$$

其中 $E_1(x)$ 为指数积分。

#### 2.1.4 双电子复合速率（Burgess [8], Post et al. [3]）

$$\alpha_{dr} = \left(2.40 \times 10^{-9} \frac{\text{cm}^3}{\text{s}}\right) n_e n_{j+1} T^{-3/2} B(j+1) \sum_i A(y) e^{-E_\infty(i)/T}$$

- $B(z) = z^{1/2} (z+1)^{5/2} (z^2 + 13.4)^{-1/2}$
- $A(y)$: $\Delta n=0$ 或 $\Delta n \neq 0$ 的系数
- $E_\infty(i)$: 激发能量阈值

#### 2.1.5 三体碰撞复合

碰撞复合是三体碰撞电离的逆过程：

$$\alpha_{\text{coll}} = C_{\text{coll}} \times \frac{n_e \cdot L_{j+1}}{L_j} \left( \frac{h^2}{2\pi m_e k_B T} \right)^{3/2} e^{\phi/T}$$

其中 $L_j$、$L_{j+1}$ 为电子配分函数。

#### 2.1.6 电离模型选择

由 `isw(6)` 控制：

| isw(6) | 模型 | 物理图像 |
|--------|------|----------|
| 0 | Mosher 判据插值 | 自动选择 LTE 或 non-LTE |
| 1 | 纯 Saha (LTE) | 三体复合主导，高密度 |
| 2 | 纯日冕 (non-LTE) | 辐射复合主导，低密度 |
| **3** | **完整三体** (推荐) | 同时考虑二体和三体过程，通用 |

> 在完整三体模型（isw(6)=3）下，因电子密度未知，需迭代求解自洽的电子密度。

### 2.2 激发种群计算

#### 2.2.1 类氢能级

外层电子在壳层 $n$ 的能量：

$$E_n = -\Phi_j \left( \frac{n_0}{n} \right)^2 \quad (n \geq n_0)$$

其中 $n_0$ 为基态主量子数，$\Phi_j$ 为电离势。激发跃迁 $n \to m$（$m > n$）的能量为：

$$\Delta E_{nm} = \Phi_j n_0^2 \left( \frac{1}{n^2} - \frac{1}{m^2} \right)$$

#### 2.2.2 碰撞激发速率

$$C_{\text{exc}} = \left(1.58 \times 10^{-7} \frac{\text{cm}^3}{\text{s}}\right) \frac{n_e n_n \, g_m \, f_{nm} \, \bar{g}_{nm}}{T^{1/2} \Delta E_{nm}} e^{-\Delta E_{nm}/T}$$

- $n_n$: 状态 $n$ 的离子数密度
- $f_{nm}$: 振子强度
- $\bar{g}_{nm}$: Gaunt 因子（$\Delta n \neq 0$ 采用 Van Regemorter [10]，$\Delta n=0$ 采用查表）
- $g_m$: 状态 $m$ 的统计权重

#### 2.2.3 碰撞去激发

由细致平衡和 Boltzmann 统计：

$$C_{\text{deexc}}^{n \to m} = C_{\text{exc}}^{m \to n} \frac{g_m}{g_n} e^{\Delta E_{nm}/T}$$

#### 2.2.4 辐射衰变（Einstein A 系数）

$$A_{nm} = \left(4.32 \times 10^7 \frac{\text{cm}^3}{\text{s}}\right) \frac{g_m}{g_n} (\Delta E_{nm})^2 f_{nm}$$

#### 2.2.5 激发态布居比

平衡碰撞激发、去激发和辐射衰变：

$$\frac{n_n}{n_m} = \frac{(g_n/g_m) e^{-\Delta E_{nm}/T}}{1 + \displaystyle \frac{2.74 \times 10^7 f_{nm}(\Delta E_{nm})^2}{n_e \, \bar{g}_{nm} \, T^{1/2}}}$$

- 高密度极限：分母 → 1，恢复 Boltzmann 分布
- 低密度极限：辐射衰变主导，布居大幅降低

### 2.3 状态方程

#### 2.3.1 比内能

相对于中性原子基态：

$$E = \frac{n_{\text{tot}}}{\rho} \left[ \frac{3}{2} (1 + \langle Z \rangle) T + \sum_{k} f_k \sum_{j=1}^{Z_k} f_{jk} \left( \sum_{i=0}^{j-1} \Phi_{i,k} + \sum_{\text{激发态}} \epsilon_{i,k} \right) \right]$$

- $n_{\text{tot}}$: 总核子数密度 (cm$^{-3}$)
- $\rho$: 质量密度 (g/cm$^3$)
- 第一项: 电子和离子的热运动能
- 第二项: 电离能（由基态到中性原子的能量差）
- 第三项: 激发能

#### 2.3.2 平均电荷态

$$\langle Z \rangle = \sum_{k} f_k \sum_{j=1}^{Z_k} j \cdot f_{jk}$$

#### 2.3.3 压力

理想气体近似：

$$P = (1 + \langle Z \rangle) n_{\text{tot}} k_B T$$

其中 $k_B = 1.602 \times 10^{-19}$ J/eV，代码中转换为 dyne/cm$^2$（1 J/cm$^3$ = 10$^7$ dyne/cm$^2$）。

#### 2.3.4 热力学导数（数值微分）

热容：

$$C_V = \left(\frac{\partial E}{\partial T}\right)_V \approx \frac{E(T + \Delta T) - E(T)}{\Delta T \cdot T}$$

其中 $\Delta T = \text{dtheat} \times T$（默认 `dtheat=0.01`）。

平均电荷态温度导数：

$$\frac{\partial \langle Z \rangle}{\partial T} \approx \frac{\langle Z \rangle(T + \Delta T) - \langle Z \rangle(T)}{\Delta T \cdot T}$$

内能密度导数：

$$\frac{\partial E}{\partial \rho} \approx \frac{E(\rho + \Delta\rho) - E(\rho)}{\Delta\rho \cdot \rho}$$

### 2.4 吸收/发射/散射系数

IONMIX 在数百个精心布置的光子能量点上计算吸收系数 $\kappa_\nu$ 和发射系数 $\eta_\nu$。

#### 2.4.1 吸收系数

$$\begin{aligned}
\kappa_\nu = &\sum_{k} \sum_{j} \sum_{n} \sum_{m>n} \left[ n_{njk} - \frac{g_n}{g_m} n_{mjk} \right] \sigma_{nm}^{bb}(\nu) \\
&+ \sum_{k} \sum_{j} \sum_{n} \left[ n_{njk} - n_{njk}^* e^{-h\nu/k_B T} \right] \sigma_{njk}^{bf}(\nu) \\
&+ n_e \sum_{k} \sum_{j} n_{jk} \left[ 1 - e^{-h\nu/k_B T} \right] \sigma_{jk}^{ff}(\nu) + s_\nu
\end{aligned}$$

其中 $n_{njk}^*$ 为 $(j+1)$ 电离态基态的 LTE 布居。

#### 2.4.2 发射系数

$$\begin{aligned}
\eta_\nu = \frac{2h\nu^3}{c^2} \Bigg[
&\sum_{k} \sum_{j} \sum_{n} \sum_{m>n} \frac{g_n}{g_m} n_{mjk} \sigma_{nm}^{bb}(\nu) \\
&+ \sum_{k} \sum_{j} \sum_{n} n_{njk}^* e^{-h\nu/k_B T} \sigma_{njk}^{bf}(\nu) \\
&+ n_e \sum_{k} \sum_{j} n_{jk} e^{-h\nu/k_B T} \sigma_{jk}^{ff}(\nu) \Bigg]
\end{aligned}$$

> **关键**: LTE 下 $\kappa_\nu$ 和 $\eta_\nu$ 满足 Kirchhoff-Planck 关系 $\eta_\nu = \kappa_\nu B_\nu$；但 non-LTE 下两者 **分别计算**。

#### 2.4.3 自由-自由（轫致辐射）截面（类氢）

$$\sigma^{ff}(\nu) = \left(2.40 \times 10^{-37} \frac{\text{cm}^5}{\text{eV}^{1/2}}\right) \frac{j^2 \bar{g}_{ff}}{(h\nu) T^{1/2}}$$

其中 Gaunt 因子 $g_{ff}$ 采用 Karzas & Latter [12] 的拟合：

$$\bar{g}_{ff} = 1 + 0.44 \exp\left[ -\frac{1}{4}(y^2 + \eta^2) \right]$$

- $y = \log_{10}(13.6 Z_{\text{eff}}^2 / T)$
- $\eta = \langle Z^2 \rangle / \langle Z \rangle$，$\langle Z^2 \rangle = \sum_j f_{jk} j^2$

#### 2.4.4 束缚-自由（光电离）截面

$$\sigma^{bf}(\nu) = \left(1.99 \times 10^{-14} \frac{\text{cm}^2}{\text{eV}^{1.5}}\right) \frac{(j+1)^4 F_n}{n (h\nu)^3}$$

其中 $F_n$ 为壳层 $n$ 的未占据分数，$(j+1)$ 为有效核电荷数。

#### 2.4.5 束缚-束缚（线吸收）截面

$$\sigma^{bb}(\nu) = \left(2.65 \times 10^{-6} \frac{\text{cm}^2}{\text{eV}}\right) f_{nm} L(\Gamma, \Delta\nu)$$

其中 $f_{nm}$ 为振子强度，$L(\Gamma, \Delta\nu)$ 为线型函数。

##### 线轮廓

由 `isw(14)` 控制：

- **Voigt 轮廓**（默认，推荐）:
  $$L^V(\Gamma, \Delta\nu) = \frac{H(a_{\text{voigt}}, \Delta\nu/\nu_D)}{\sqrt{\pi} \nu_D}$$
  其中 $H$ 为 Voigt 函数，结合了 Doppler 和碰撞展宽。

- **Lorentzian 轮廓**（快速）:
  $$L^L(\Gamma, \Delta\nu) = \frac{\Gamma / (4\pi)}{(\Delta\nu)^2 + (\Gamma / 4\pi)^2}$$

展宽因子 $\Gamma = \Gamma_{\text{nat}} + \Gamma_{\text{Dop}} + \Gamma_{\text{coll}}$：

$$\begin{aligned}
\Gamma_{\text{nat}} &= 2.29 \times 10^{-6} (\Delta E_{nm})^2 \\
\Gamma_{\text{Dop}} &= 1.41 \times 10^{-11} \Delta E_{nm} \sqrt{T/A} \\
\Gamma_{\text{coll}} &= 4.58 \times 10^{-6} \sqrt{T/A} \, n_e
\end{aligned}$$

其中 $A$ 为原子量 (amu)。

#### 2.4.6 散射系数

- Thomson 散射: $s_T = (6.66 \times 10^{-25}~\text{cm}^2) n_e^{\text{eff}}$
- 等离子体波散射: $s_{pw} = \begin{cases} (\omega_p/\omega)^2 s_T, & h\nu < h\nu_{pw} \\ 0, & h\nu \geq h\nu_{pw} \end{cases}$

其中等离子体频率 $\omega_p = \sqrt{4\pi e^2 n_e / m_e}$。

### 2.5 平均不透明度与冷却率

#### 2.5.1 Planck 平均吸收群不透明度

$$\sigma_{P,g}^A = \frac{1}{\rho} \frac{\displaystyle \int_{x_g}^{x_{g+1}} B_\nu(T_R) \kappa_\nu \, dx}{\displaystyle \int_{x_g}^{x_{g+1}} B_\nu(T_R) \, dx}$$

其中 $x = h\nu / k_B T$，$B_\nu$ 为 Planck 函数，$T_R$ 为辐射温度。

#### 2.5.2 Planck 平均发射群不透明度

$$\sigma_{P,g}^E = \frac{1}{\rho} \frac{\displaystyle \int_{x_g}^{x_{g+1}} \eta_\nu \, dx}{\displaystyle \int_{x_g}^{x_{g+1}} B_\nu(T_R) \, dx}$$

#### 2.5.3 Rosseland 平均群不透明度

$$\frac{1}{\sigma_{R,g}} = \frac{1}{\rho} \frac{\displaystyle \int_{x_g}^{x_{g+1}} \frac{1}{\kappa_\nu + s_\nu} \frac{\partial B_\nu}{\partial T_R} \, dx}{\displaystyle \int_{x_g}^{x_{g+1}} \frac{\partial B_\nu}{\partial T_R} \, dx}$$

#### 2.5.4 全能量平均不透明度

由群不透明度积分得到：

$$\sigma_{P,\text{tot}} = \frac{\sum_g \sigma_{P,g} \cdot \int_{x_g}^{x_{g+1}} B_\nu(T_R) \, dx}{\int_0^\infty B_\nu(T_R) \, dx}$$

$$\sigma_{R,\text{tot}} = \frac{\int_0^\infty (\partial B_\nu / \partial T_R) \, dx}{\sum_g \frac{1}{\sigma_{R,g}} \cdot \int_{x_g}^{x_{g+1}} (\partial B_\nu / \partial T_R) \, dx}$$

#### 2.5.5 等离子体冷却率

$$\Lambda(T) = \frac{4 \sigma_{SB} \rho T^4}{n_e n_{\text{tot}}} \sigma_P^E$$

其中 $\sigma_{SB}$ 为 Stefan-Boltzmann 常数。输出为 $\log_{10}(\Lambda)$ 值，单位 erg·cm$^3$/s。

---

## 3. 代码结构

### 3.1 主程序流程

```
IONMIX (主程序)
  │
  ├── INPUT               读取输入参数、设置网格、打开文件
  │
  └── 主循环: 对每个 (T, n) 点
       │
       ├── ENERGY              计算电离/激发种群和比能
       │   ├── SAHA / CORONA   电离平衡 (由 isw(6) 选择)
       │   └── ATMLV           激发态布居
       │
       ├── EOS                 计算状态方程量
       │                       比能、热容、dZ/dT、dE/dρ
       │
       ├── MESHHV              生成光子能量网格
       │                        含线中心和电离边附近的细点
       │
       ├── ABSCON              计算吸收/发射/散射系数
       │   ├── LINES → ABSLIN  逐线计算 (bb 贡献)
       │   ├── fotiza / fotize 光电离 (bf 贡献)
       │   ├── brems / brmtot  轫致辐射 (ff 贡献)
       │   ├── tscatt / pscatt 散射 (Thomson + 等离子体波)
       │   └── dawson          线型中的 Dawson 积分
       │
       ├── OPACYS              积分得到群平均不透明度
       │   ├── OPACGP          对各能群积分 (Planck/Rosseland)
       │   ├── OPACBB          线贡献解析群计算 (isw(19)=2)
       │   └── rizrec          电离/复合速率比
       │
       └── OWT1                输出该点结果到 IONMXOUT 和 IMPLOT
       │
       └── (循环结束)
│
└── OWTF                   输出整体 EOS/Opacity 数据表 (eos.cn4)
```

### 3.2 全部子程序一览

| 子程序 | 功能 |
|--------|------|
| `IONMIX` | 主程序，驱动计算流程 |
| `INPUT` | 读取 NAMELIST 输入，初始化网格和文件 |
| `ENERGY` | 计算电离/激发种群和比能 |
| `SAHA` | Saha 电离平衡（LTE） |
| `CORONA` | 日冕电离平衡（非 LTE） |
| `ATMLV` | 计算离子的激发态布居 |
| `EOS` | 计算状态方程量（比能、热容、导数） |
| `MESHHV` | 生成光子能量精细网格 |
| `ABSCON` | 计算吸收/发射/散射系数 |
| `LINES` | 处理束缚-束缚跃迁（遍历所有谱线） |
| `ABSLIN` | 计算单条谱线在指定能量上的贡献 |
| `BREMS` | 计算轫致辐射系数 |
| `FOTIZA` | 计算光电离吸收系数 |
| `FOTIZE` | 计算光电离发射系数 |
| `TSCATT` | 计算 Thomson 散射系数 |
| `PSCATT` | 计算等离子体波散射系数 |
| `OPACYS` | 计算群平均不透明度 |
| `OPACGP` | 对每个能群进行积分 |
| `OPACBB` | 快速线贡献解析群计算方法 |
| `GINT` | 返回积分 $\int_{x}^{x'} B_\nu(T_R) dx$ 等（n=1~6） |
| `RIZREC` | 计算电离/复合速率比值 |
| `VOIGT` / `DAWSON` | 计算 Voigt 线型 / Dawson 积分 |
| `OWT1` | 输出单个温度-密度点的结果到 IONMXOUT |
| `OWTF` | 输出 CONRAD 格式的完整数据表 (eos.cn4) |
| `BLOCK DATA MENU` | 默认电离势和常数数据初始化 |

---

## 4. 输入文件 (IONMXINP)

IONMIX 使用 FORTRAN NAMELIST 格式读取输入参数。输入文件名为 `ionmxinp`（无扩展名），放置在与可执行文件相同的目录下。

### 4.1 NAMELIST 参数详解

#### 4.1.1 基本参数与气体成分

| 参数 | 类型 | 最大值 | 默认值 | 说明 |
|------|------|--------|--------|------|
| `ngases` | 整数 | 10 | — | 气体种类数量 |
| `izgas(i)` | 整数数组 | 54 | — | 第 $i$ 种气体的原子序数 |
| `atomwt(i)` | 浮点数组 | — | — | 第 $i$ 种气体的原子量 (amu) |
| `fracsp(i)` | 浮点数组 | — | — | 第 $i$ 种气体的原子数相对丰度 |

#### 4.1.2 温度网格参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ntemp` | 整数 | — | 温度点数 |
| `tplsma(1)` | 浮点 | — | 起始温度 (eV) |
| `dlgtmp` | 浮点 | 0.1 | 温度对数增量 |
| `isw(22)` | 整数 | 0 | `0`=对数网格；`1`=预设温度数组 |

温度点生成（`isw(22)=0`）：$T_i = T_1 \times 10^{(i-1) \times \text{dlgtmp}}$

#### 4.1.3 密度网格参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ndens` | 整数 | — | 密度点数 |
| `densnn` | 浮点 | — | 起始离子数密度 (cm$^{-3}$) |
| `dlgden` | 浮点 | 0.1 | 密度对数增量 |
| `isw(23)` | 整数 | 0 | `0`=对数网格；`1`=预设密度数组 |

密度点生成（`isw(23)=0`）：$n_i = n_1 \times 10^{(i-1) \times \text{dlgden}}$

#### 4.1.4 辐射温度参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ntrad` | 整数 | 0 | 辐射温度点数（0=不采用辐射温度变温） |
| `trad` | 浮点 | — | 辐射温度 (eV) |
| `dlgtrd` | 浮点 | 0.1 | 辐射温度对数增量 |

#### 4.1.5 光子能量网格参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `nptspg` | 整数 | 5 | **每个不透明度群内的最小网格点数** |
| `nfrqbb` | 整数 | 5 | **每条线中心附近的额外网格点数** |
| `isw(24)` | 整数 | 0 | `0`=对数间隔；`1`=线性间隔 |
| `isw(25)` | 整数 | 0 | `0`=添加线中心和电离边附近点；`≠0`=跳过 |

**`nptspg`**：
- 用于在每个能量组内生成对数均匀分布的网格点
- 平滑连续谱场景：`nptspg=5` 足够；密集线谱或尖锐边缘：建议 10~20
- 代码中每个能群生成 `nptspg` 个点（最后一组多 1 个）

**`nfrqbb`**：
- 每条谱线中心附近添加 `2 × (nfrqbb/2 + 1)` 个额外点（两侧对称分布）
- 窄线（低密度）：10~15；宽线（高密度）：可减少
- 步长采用倍程（$2^{i-1} \times \text{dhnu}$）方式向外扩展

#### 4.1.6 热力学导数参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dtheat` | 浮点 | 0.01 | 热容和 ${\rm d}Z/{\rm d}T$ 计算的温度增量分数 |

$C_V = [E(T+\Delta T) - E(T)] / (\Delta T \cdot T)$，其中 $\Delta T = \text{dtheat} \cdot T$

#### 4.1.7 能群参数

| 参数 | 类型 | 最大值 | 说明 |
|------|------|--------|------|
| `ngrups` | 整数 | 50 | 不透明度能群数量 |
| `grupbd(i)` | 浮点数组 | ngrups+1 | 能群边界值 (eV) |

`isw(13)` 控制：
- `isw(13)=0`: 使用默认 6 个能群（0.1, 1, 10, 100, 1000, 10000, 100000 eV）
- `isw(13)=1`: 用户通过 `grupbd` 数组自定义
- `isw(13)=2`: 基于温度自动生成

### 4.2 控制开关 isw 详解

`isw` 是长度为 30 的整数控制数组，**核心配置**。

#### isw(1)~isw(10)

| 索引 | 默认值 | 功能 | 选项说明 |
|------|--------|------|----------|
| 1 | 0 | 用户提供电离势 | 0=使用默认值；1=从 `ATOMnn.DAT` 读取 |
| 2 | 0 | **是否计算不透明度** | 0=计算；1=跳过 |
| 3 | 0 | 调试输出频率 | 0=无；>0=每 N 个循环输出一次 |
| 4 | 0 | **计算热容和 dZ/dT** | 0=计算；1=跳过 |
| 5 | 0 | 复制输入到输出 | 0=复制；1=不复制 |
| **6** | **3** | **电离模型（关键）** | 0=插值；1=Saha；2=日冕；**3=完整三体（推荐）** |
| 7 | 0 | 未使用 | — |
| **8** | **0** | **输出格式（关键）** | 0=无；1/12=旧 CONRAD；2/12=SESAME(未实现)；**3/13=新 CONRAD** |
| 9 | 0 | 种群计算最大主量子数 | 0=代码自动选择 (`npmaxp = isw9 + 基态主量子数`) |
| 10 | 0 | 未使用（保留） | — |

#### isw(11)~isw(20)

| 索引 | 默认值 | 功能 | 选项说明 |
|------|--------|------|----------|
| 11 | 0 | **包含 Δn=0 跃迁** | 0=包含；1=排除 |
| 12 | 0 | 限制离子到基态 | 0=否（考虑激发态）；1=是 |
| 13 | 0 | **能群边界定义方式** | 0=默认；1=用户指定；2=温度相关 |
| 14 | 0 | **线轮廓类型** | 0=Voigt（推荐）；1=Lorentzian |
| 15 | 2 | **不透明度最大主量子数** | >0=基态主量子数+isw15；<0=直接指定为-isw15 |
| 16 | 0 | 包含双电子复合 | 0=包含；1=排除 |
| 17 | 0 | 包含轫致辐射 | 0=包含；1=排除 |
| 18 | 0 | 包含光电离 | 0=包含；1=排除 |
| 19 | 0 | **包含束缚-束缚跃迁** | 0=包含；1=排除；2=核心/翼分别计算 |
| 20 | 0 | 包含散射贡献 | 0=包含；1=排除 |

#### isw(21)~isw(25)（代码扩展）

| 索引 | 默认值 | 功能 | 选项说明 | 代码引用 |
|------|--------|------|----------|----------|
| **21** | **0** | **输出 eos.cn4** | 0=不输出；≠0=输出 | `INPUT` 中打开 unit=123，`OWTF` 中写入 |
| 22 | 0 | 温度网格生成 | 0=对数增量；1=预设数组 | `INPUT` 中 `tplsma` 赋值 |
| 23 | 0 | 密度网格生成 | 0=对数增量；1=预设数组 | `INPUT` 中 `densnn` 赋值 |
| 24 | 0 | 光子能量网格类型 | 0=对数间隔；1=线性间隔 | `MESHHV` 中 `dloghv` 计算 |
| 25 | 0 | 添加线中心和电离边附近点 | 0=添加；≠0=跳过 | `MESHHV` 中额外点插入 |

> isw(26)~isw(30) 未使用。

#### 常见 isw 推荐配置

| 场景 | isw 设置 | 说明 |
|------|----------|------|
| **标准 ICF 计算** | `isw(6)=3, isw(8)=3, isw(14)=0, isw(15)=5, isw(21)=1` | 完整三体、新 CONRAD、Voigt 线型 |
| **快速 EOS 预览** | `isw(2)=1, isw(4)=1, isw(19)=1` | 跳过不透明度、跳过导数、跳过谱线 |
| **低密度日冕** | `isw(6)=2, isw(16)=0, isw(19)=0` | 日冕模型、双电子复合、谱线全开 |

### 4.3 常数 con 数组

`con` 是长度为 10 的浮点数组，控制数值计算的阈值和范围。

| 索引 | 默认值 | 说明 |
|------|--------|------|
| 1 | 0.0 | 保留 |
| 2 | 1.0E-10 | 最小物种浓度阈值（低于此忽略 bb 和 bf 跃迁） |
| 3 | 1.0E-10 | 最小电离浓度阈值 |
| 4 | 1.0E-10 | 最小原子态浓度阈值 |
| 5 | 1.0E+10 | 谱线贡献计算范围，以 FWHM 为单位 |
| 6 | 1.0E+01 | 线核心宽度，以 FWHM 为单位 |
| 7 | 1.0E+01 | 吸收系数的 Planck 加权范围：$1/\text{con}7 < h\nu/kT < \text{con}7$ |
| 8 | 0.0 | 保留 |
| 9 | 1.0 | 线附近网格点间距乘数 |
| 10 | 0.0 | 保留 |

### 4.4 绘图控制 iplot 数组

`iplot` 是长度为 30 的整数数组，控制绘图数据文件的输出。

| 索引 | 文件 | 输出的物理量 | 格式 |
|------|------|-------------|------|
| **1** | `implot01` | **吸收系数 vs. 光子能量**: `photen, abscfs, brmtot, piztot, abslns, sctcfs, 总消光系数` | `1p7e14.5` |
| **2** | `implot02` | **平均不透明度 vs. 温度**: `tp, culrat (log10), oppma, oppme, oprm` | `1p5e14.4` |
| **3** | `implot03` | **发射系数 vs. 光子能量**: `photen, emscfs, brmtot, piztot, emslns` | `1p5e14.5` |
| **4** | `implot04` | **不透明度 vs. 密度**: `densnn, zbar, enrgy, pres` | `1p4e14.4` |
| **5** | `implot05` | **电荷态和冷却率 vs. 温度**: `tp, culrat (log10), zbar, enrgy, pres` | `1p5e14.4` |
| **6** | `implot06` | **热力学导数**: `tp, heatcp, dzdt, dpdt, ratio(dpdt/heatcp)` | `1p5e14.4` |
| **7** | `implot07` | **不透明度比值 vs. 密度**: `densnn, opme/opma, opma, opme, orm` | `1p5e14.4` |
| **8** | `implot08` | **光子通量加权不透明度**: `engrup(ig), oppet*dum1, g5odhv` (每组两行) | `1p5e14.4` |
| **9** | `implot09` | **电离种群 vs. 温度**: `tp, log10(fraciz)` (每个电离态一行) | `1p5e14.4` |
| 10~30 | — | 未定义（可自定义扩展） | — |

> **注**: 包含 `opme/opma` 的文件（如 implot07），若比值 ≠ 1 表示 non-LTE。

### 4.5 完整输入文件示例

#### 示例 1: 低密度氮等离子体

```fortran
! IONMIX Input File
! 示例：低密度氮等离子体（论文图 6-8 验证案例）
! Generated by Python IONMIXInputGen
! Based on Computer Physics Communications 56(1989) 259-278

$data
    ngases = 1,              ! 气体种类数量
    izgas(1) = 7,            ! 氮的原子序数
    atomwt(1) = 14.006700,   ! 氮的原子量 (amu)
    fracsp(1) = 1.000000,    ! 相对丰度（纯氮）
    ntemp = 20,              ! 温度点数
    dlgtmp = 0.200000,       ! 温度对数增量
    tplsma(1) = 1.000000,    ! 起始温度 (eV)
    ndens = 1,               ! 密度点数
    densnn = 1.000000e+14,   ! 初始数密度 (cm⁻³)
    ntrad = 0,               ! 无辐射温度变化
    nptspg = 50,             ! 每个能群网格点数
    nfrqbb = 5,              ! 线中心附近的网格点数
    dtheat = 0.010000,       ! 导数计算温度增量
    iplot(1) = 1,            ! 吸收系数 vs 光子能量
    iplot(2) = 1,            ! 平均不透明度 vs 温度
    iplot(3) = 1,            ! 发射系数 vs 光子能量
    iplot(4) = 0,
    iplot(5) = 1,            ! 电荷态和冷却率 vs 温度
    iplot(6) = 0,
    isw(1) = 0,              ! 默认电离势
    isw(6) = 3,              ! 完整三体过程
    isw(8) = 0,              ! 不输出 CONRAD 格式
    isw(13) = 0,             ! 默认能群边界
    isw(14) = 0,             ! Voigt 线型
    isw(15) = 3,             ! 激发态：基态+3
    isw(19) = 0,             ! 包含束缚-束缚跃迁
    isw(21) = 1,             ! 输出 eos.cn4
    isw(24) = 1,
    isw(25) = 1,
    ngrups = 6,              ! 6 个能群
    grupbd(1) = 0.100000,    ! 能群边界 (eV)
    grupbd(2) = 1.000000,
    grupbd(3) = 10.000000,
    grupbd(4) = 100.000000,
    grupbd(5) = 1000.000000,
    grupbd(6) = 1.000000e+04,
    grupbd(7) = 1.000000e+05
$end
```

#### 示例 2: 金等离子体（高 Z）

```fortran
$data
    ngases = 1,
    izgas(1) = 79,           ! 金的原子序数
    atomwt(1) = 196.97,      ! 金的原子量
    fracsp(1) = 1.000,
    ntemp = 21,              ! 21 个温度点
    dlgtmp = 0.1,
    tplsma(1) = 500.0,       ! 起始 500 eV
    ndens = 21,              ! 21 个密度点
    dlgden = 0.1,
    densnn = 1.0e+23,        ! 起始数密度
    ntrad = 0,
    trad = 100.0,
    nptspg = 5,
    nfrqbb = 5,
    dtheat = 0.01,
    iplot(1) = 1,  iplot(2) = 1,
    iplot(3) = 1,  iplot(4) = 1,
    iplot(5) = 1,  iplot(6) = 1,
    isw(5) = 1,              ! 不复制输入到输出
    isw(6) = 3,              ! 完整三体
    isw(8) = 3,              ! 新 CONRAD 格式
    isw(13) = 1,             ! 用户指定能群
    isw(15) = 5,             ! 激发态：基态+5
    isw(21) = 1,             ! 输出 eos.cn4
    isw(24) = 1,
    isw(25) = 1,
    ngrups = 6,
    grupbd(1) = 1.0e-1,  grupbd(2) = 1.0e+0,
    grupbd(3) = 1.0e+1,  grupbd(4) = 1.0e+2,
    grupbd(5) = 1.0e+3,  grupbd(6) = 1.0e+4,
    grupbd(7) = 1.0e+5
$end
```

---

## 5. 输出文件详解

### 5.1 IONMXOUT — 主输出文件

程序运行后生成的主输出文件，包含输入摘要和所有计算结果。

#### 文件结构

```
  number of gases  =  1

    gas #               atomic #            number fraction     atomic weight
      1                    7                    1.00000000          14.007

   For gas #  1, with atomic #   7,
      the ionization potentials are:
      ionization state =  0         ionization potential =    13.400
      ionization state =  1         ionization potential =    32.000
      ...

                             Switches used for current calculation
   isw( 1) =   0  User supplies ionization potentials (0=>no)
   isw( 2) =   0  Compute opacities ?  (0=>yes)
   ...

                             Constants used for current calculation
   con( 2) =   1.00E-10  min. species concentration to compute bb and bf transitions
   ...

                             Plot files opened for current calculation
   iplot( 1) =   1  Absorption coefs. vs. photon energy
   ...

   Contents of input file -- IONMXINP
   ! IONMIX Input File
   ...

  Results for next temperature, density point
  *******************************************

  Temperature             =  x.xxxE+xx eV
  Number density          =  x.xxxE+xx cm**-3
  Mass density            =  x.xxxE+xx grams/cm**3
  Electron density        =  x.xxxE+xx cm**-3
  Average charge state    =  x.xxxE+xx
  Specific energy         =  x.xxxE+xx J/gram
  Pressure                =  x.xxxE+xx dyne/cm**2

  Max. prin. quantum # used to compute populations    =   20
  Max. prin. quantum # used to compute absorp. coefs. =    5

  Planck mean opacity (abs.) =  x.xxxE+xx cm**2/gram
  Planck mean opacity (ems.) =  x.xxxE+xx cm**2/gram
  Rosseland mean opacity     =  x.xxxE+xx cm**2/gram
  Plasma cooling rate        =  x.xxxE+xx erg*cm**3/sec   (Log10 value)

  Group opacities:
  group   lower         upper         Planck (abs)  Planck (ems)  Rosseland
  number  boundary      boundary      opacity       opacity       opacity
          (eV)          (eV)          (cm**2/g)     (cm**2/g)     (cm**2/g)
    1      x.xxE+xx     x.xxE+xx     x.xxE+xx     x.xxE+xx     x.xxE+xx
    ...
```

#### 输出量物理意义汇总

| 输出量 | 单位 | 物理意义 |
|--------|------|----------|
| Temperature | eV | 等离子体温度 |
| Number density | cm$^{-3}$ | 核子数密度 |
| Mass density | g/cm$^3$ | $\rho = n_{\text{tot}} \sum f_k A_k / N_A$ |
| Electron density | cm$^{-3}$ | $n_e = \langle Z \rangle n_{\text{tot}}$ |
| Average charge state | — | $\langle Z \rangle$ |
| Specific energy | J/g | $E$ (热运动能 + 电离能 + 激发能) |
| Pressure | dyne/cm$^2$ | $P = (1+\langle Z \rangle) n_{\text{tot}} k_B T$ |
| Planck mean opacity (abs.) | cm$^2$/g | $\sigma_P^A$ |
| Planck mean opacity (ems.) | cm$^2$/g | $\sigma_P^E$ |
| Rosseland mean opacity | cm$^2$/g | $\sigma_R$ |
| Plasma cooling rate | erg·cm$^3$/s | $\log_{10}(\Lambda)$ |

#### IONMXOUT 中的 EOS 尾段

在每个 (T, n) 点计算结果后，文件末尾附加 EOS 导数数据。格式如下：

```
 en
 en
 en
   2.79948975E-09
 Heat capacity           =  1.425E+05 J/gram/eV
 d(Charge st.)/d(Temp.)  =  1.277E+00 ev**-1
 d(Spec. En.)/d(Dens.)   = -1.172E-14 J*cm**3/g
 en
 en
 en
   1.40856699E-07
 ...
```

- **第一行数值**: 比能 `enrgy` (J/g)
- **Heat capacity**: 定容比热 $C_V = (\partial E/\partial T)_V$ (J/g/eV)
- **d(Charge st.)/d(Temp.)**: 平均电荷态温度导数 $\partial\langle Z \rangle/\partial T$ (eV$^{-1}$)
- **d(Spec. En.)/d(Dens.)**: 比能密度导数 $\partial E/\partial \rho$ (J·cm$^3$/g)

> **关键物理**: 比能值随温度升高而增大（热电离增强）；热容在电离阈值附近出现峰值（电离潜热）；${\rm d}Z/{\rm d}T$ 反映电离度对温度的敏感性。

### 5.2 IONMXBUG — 详细结果文件

`ionmxbug` 包含与 `IONMXOUT` 中 **计算结果部分相同格式** 的内容，即每个 (温度, 密度) 点的详细结果。常用于批量提取数据以进行后处理分析。

**文件内容格式**（与 IONMXOUT 中的计算结果段一致）：

```
  Temperature             =  x.xxxE+xx eV
  Number density          =  x.xxxE+xx cm**-3
  ...
  Electron density        =  x.xxxE+xx cm**-3
  Average charge state    =  x.xxxE+xx
  ...
  Planck mean opacity (abs.) =  x.xxxE+xx cm**2/gram
  ...
  Group opacities: ...
```

### 5.3 IMPLOT 绘图文件系列

由 `iplot` 数组控制生成的格式化数据文件，每行格式为科学计数法。

#### IMPLOT01 — 吸收系数谱

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | photen | eV | 光子能量
2 | abscfs | cm$^{-1}$ | **总吸收系数**
3 | brmtot | cm$^{-1}$ | 轫致辐射 (ff) 贡献
4 | piztot | cm$^{-1}$ | 光电离 (bf) 贡献
5 | abslns | cm$^{-1}$ | 线吸收 (bb) 贡献
6 | sctcfs | cm$^{-1}$ | 散射系数
7 | abscfs+sctcfs | cm$^{-1}$ | 总消光系数

**绘图建议**: 以 `photen` 为 x 轴（对数坐标），`abscfs` 为 y 轴，展示吸收谱线结构。

#### IMPLOT02 — 平均不透明度 vs. 温度

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | tp | eV | 等离子体温度
2 | culrat | erg·cm$^3$/s | 冷却率 (Log10)
3 | oppma | cm$^2$/g | Planck 吸收平均不透明度
4 | oppme | cm$^2$/g | Planck 发射平均不透明度
5 | oprm | cm$^2$/g | Rosseland 平均不透明度

#### IMPLOT03 — 发射系数谱

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | photen | eV | 光子能量
2 | emscfs | cm$^{-1}$ | **总发射系数**
3 | brmtot | cm$^{-1}$ | 轫致辐射贡献
4 | piztot | cm$^{-1}$ | 光电离贡献
5 | emslns | cm$^{-1}$ | 线发射贡献

#### IMPLOT04 — 不透明度 vs. 密度

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | densnn | cm$^{-3}$ | 核子数密度
2 | zbar | — | 平均电荷态
3 | enrgy | J/g | 比内能
4 | pres | dyne/cm$^2$ | 压力

#### IMPLOT05 — 电荷态和冷却率 vs. 温度

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | tp | eV | 温度
2 | culrat | erg·cm$^3$/s | 冷却率 (Log10)
3 | zbar | — | 平均电荷态
4 | enrgy | J/g | 比内能
5 | pres | dyne/cm$^2$ | 压力

**绘图建议**: 双 Y 轴图，左轴（对数）冷却率、右轴（线性）平均电荷态。

#### IMPLOT06 — 热力学导数

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | tp | eV | 温度
2 | heatcp | J/(g·eV) | 比热容 $C_V$
3 | dzdt | eV$^{-1}$ | ${\rm d}\langle Z\rangle/{\rm d}T$
4 | dpdt | dyne/(cm$^2$·eV) | ${\rm d}P/{\rm d}T$
5 | ratio | — | ${\rm d}P/{\rm d}T \big/ C_V$

其中 ${\rm d}P/{\rm d}T = n_{\text{tot}} \cdot 11605 \cdot 1.381\times10^{-16} (1+\langle Z \rangle + T \cdot {\rm d}Z/{\rm d}T)$（单位: dyne/cm$^2$/eV）

#### IMPLOT07 — 不透明度比值 vs. 密度

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | densnn | cm$^{-3}$ | 核子数密度
2 | opme/opma | — | **发射/吸收不透明度比**（≠1 = non-LTE）
3 | opma | cm$^2$/g | Planck 吸收不透明度
4 | opme | cm$^2$/g | Planck 发射不透明度
5 | orm | cm$^2$/g | Rosseland 不透明度

#### IMPLOT08 — 光子通量加权不透明度

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | engrup(ig) | eV | 能群边界
2 | oppet(ig) × dum1 | cm$^2$/g | 通量加权发射不透明度
3 | g5odhv | — | Planck 函数积分权重因子

> 每个能群输出两行（上边界和下边界各一行），`dum1 = G_5(x) \cdot T^4 / h\nu_{\text{avg}} \cdot h\nu_{\text{avg}}^{\text{isw(10)}}$，其中 $G_5$ 为 Planck 函数的积分。

#### IMPLOT09 — 电离种群 vs. 温度

**列** | **变量** | **单位** | **说明**
:----:|:---------|:---------|:---------
1 | tp | eV | 温度
2 | log10(fraciz) | — | 电离态占比 (Log10)

每个电离态占一行，多个温度点连续输出。

### 5.4 EOS.CN4 — 格式化数据表

由 `isw(21) ≠ 0` 触发输出，文件名为 `eos.cn4`。这是供辐射流体力学代码（如 CONRAD/MF-FIRE/ZPINCH）使用的结构化数据表。

#### 文件结构示例（纯金，ntemp=21, ndens=21, ngrups=6）

```fortran
        21        21
 atomic #s of gases:         79
 relative fractions:   1.00E+00
           6
0.500000E+03 0.629463E+03 0.792446E+03 0.997631E+03    ← 温度数组 (eV)
...
0.100000E+24 0.125893E+24 0.158490E+24 0.199527E+24    ← 密度数组 (cm⁻³)
...
0.313510E+02 0.342890E+02 0.382216E+02 0.420961E+02    ← 平均电荷态 zbar (ntemp×ndens 个值)
...
0.257130E-01 0.230566E-01 0.230047E-01 0.150169E-01    ← Rosseland 群不透明度
...
```

#### 完整数据排列顺序

| 序号 | 数据 | 维度 | 单位 | 说明 |
|:----:|:-----|:----:|:----:|:-----|
| — | 头部 | 3 行 | — | 第 1 行 `ntemp ndens`；第 2 行原子序数；第 3 行丰度 |
| 1 | ngrups | 1 | — | 能群数 |
| 2 | 温度数组 | ntemp | eV | 升序排列 |
| 3 | 密度数组 | ndens | cm$^{-3}$ | 升序排列 |
| 4 | **平均电荷态 zbar** | ntemp×ndens | — | $n_e / n_{\text{tot}}$ |
| 5 | **dzbar/dT** | ntemp×ndens | eV$^{-1}$ | 平均电荷态温度导数 |
| 6 | **离子压力** | ntemp×ndens | J/cm$^3$ | $n_{\text{tot}} \cdot T \cdot 1.602\times10^{-19}$ |
| 7 | **电子压力** | ntemp×ndens | J/cm$^3$ | $n_e \cdot T \cdot 1.602\times10^{-19}$ |
| 8 | **d(离子压力)/dT** | ntemp×ndens | J/(cm$^3$·eV) | $n_{\text{tot}} \cdot 1.602\times10^{-19}$ |
| 9 | **d(电子压力)/dT** | ntemp×ndens | J/(cm$^3$·eV) | $[n_{\text{tot}} \cdot T \cdot {\rm d}Z/{\rm d}T + n_e] \cdot 1.602\times10^{-19}$ |
| 10 | **离子比内能** | ntemp×ndens | J/g | `enrgyion` |
| 11 | **电子比内能** | ntemp×ndens | J/g | `enrgy - enrgyion` |
| 12 | **离子比热** | ntemp×ndens | J/(g·eV) | `heatcpion` |
| 13 | **电子比热** | ntemp×ndens | J/(g·eV) | `heatcp - heatcpion` |
| 14 | **d(离子能量)/d(密度)** | ntemp×ndens | J·cm$^3$/g | `dedden_ion` 经单位转换 |
| 15 | **d(电子能量)/d(密度)** | ntemp×ndens | J·cm$^3$/g | `dedden - dedden_ion` |
| 16 | **能群边界** | ngrups+1 | eV | 定义不透明度群的端点 |
| 17 | **Rosseland 群不透明度** | ntemp×ndens×ngrups | cm$^2$/g | 辐射扩散用 |
| 18 | **Planck 吸收群不透明度** | ntemp×ndens×ngrups | cm$^2$/g | 辐射吸收用 |
| 19 | **Planck 发射群不透明度** | ntemp×ndens×ngrups | cm$^2$/g | 辐射发射用（non-LTE 下 ≠ 吸收） |

> **存储顺序**:
> - 二维数组: **先温度（内循环）、再密度（外循环）**
> - 三维数组: **先能群、再温度、最后密度**
> - 数据格式: `4e12.6`（每行 4 个科学计数法值）

---

## 6. Python 输入文件生成器

### 6.1 IONMIXInputGen 类

位置: `src/Ionmix_run/ionmix_core.py`（flash-sim 包内路径: `flash/input_gen/gen_eos_op/ionmix/ionmix/src/Ionmix_run/ionmix_core.py`）

#### 核心 API

```python
from Ionmix_run.ionmix_core import IONMIXInputGen

gen = IONMIXInputGen()
```

| 方法 | 说明 |
|------|------|
| `set_parameter(name, value, index=None)` | 设置参数。`index` 用于数组参数（1-based） |
| `set_array_parameter(name, values)` | 设置数组参数 |
| `set_grupbd(boundaries)` | 设置能群边界，自动计算 `ngrups` |
| `clear_parameters()` | 清除所有已设参数 |
| `generate_input(output_dir)` | **生成输入文件** `ionmxinp` 到指定目录（仅生成，不运行） |
| `run_single(params_dict, output_base_dir)` | 单次运行：设置参数 → 生成输入 → 编译/拷贝二进制 → 执行 `abjt_03` → 输出 `.cn4` |
| `batch_run(params_list, output_base_dir)` | 批量运行多组参数 |

#### 生成流程（run_single）

```
IONMIXInputGen.run_single(params_dict, output_base_dir)
  │
  ├── 依据参数设置 (set_parameter / set_grupbd)
  │
  ├── 生成 ionmxinp 到工作目录
  │
  ├── 拷贝/编译 abjt_03 可执行文件（缺失时经 WSL gfortran 自动编译 abjt_03.f）
  │
  ├── 执行 ./abjt_03（WSL 或本地）
  │
  └── 将 eos.cn4 重命名为 Z{izgas}_{fracsp}.cn4 规范文件名
```

> **说明**: `generate_input(output_dir)` 仅生成输入文件；完整的"生成 → 运行 → 命名输出"流程请使用 `run_single()` / `batch_run()`。

#### 基本使用示例

```python
from Ionmix_run.ionmix_core import IONMIXInputGen

gen = IONMIXInputGen()

# 设置气体
gen.set_parameter('ngases', 1)
gen.set_parameter('izgas', 7, 1)       # 氮
gen.set_parameter('atomwt', 14.0067, 1)
gen.set_parameter('fracsp', 1.0, 1)

# 温度网格
gen.set_parameter('ntemp', 20)
gen.set_parameter('dlgtmp', 0.2)
gen.set_parameter('tplsma', 1.0, 1)

# 密度网格
gen.set_parameter('ndens', 1)
gen.set_parameter('densnn', 1.0e14)

# isw 开关
gen.set_parameter('isw', 3, 6)     # 完整三体
gen.set_parameter('isw', 0, 8)     # 不输出 CONRAD
gen.set_parameter('isw', 1, 21)    # 输出 eos.cn4

# 能群边界
gen.set_grupbd([0.1, 1.0, 10.0, 100.0, 1000.0, 1e4, 1e5])

# 方式一: 仅生成输入文件到指定目录
gen.generate_input('work_dir')

# 方式二: 单次完整运行（生成 → 编译/拷贝二进制 → 执行 → 输出 .cn4）
out_path = gen.run_single(
    params_dict={
        'ngases': 1, 'izgas': [7], 'atomwt': [14.0067], 'fracsp': [1.0],
        'ntemp': 20, 'dlgtmp': 0.2, 'tplsma': [1.0],
        'ndens': 1, 'densnn': 1.0e14,
        'isw': {6: 3, 8: 0, 21: 1},
    },
    output_base_dir='./outputs',
)
print(f"输出 .cn4: {out_path}")
```

### 6.2 典型示例参数设置

#### N 等离子体（论文标准测试用例）

```python
ngases   = 1
izgas    = [7]            # 氮
atomwt   = [14.0067]
fracsp   = [1.0]
ntemp    = 20,  dlgtmp = 0.2,  tplsma(1) = 1.0
ndens    = 1,   densnn = 1.0e14
nptspg   = 50,  nfrqbb = 5
dtheat   = 0.01
iplot    = [1,1,1,0,1,0]
isw(6)   = 3     # 完整三体
isw(13)  = 0     # 默认能群
isw(15)  = 3
```

#### Au 等离子体（高 Z、多网格点）

```python
ngases   = 1
izgas    = [79]           # 金
atomwt   = [196.97]
fracsp   = [1.0]
ntemp    = 21,  dlgtmp = 0.1,  tplsma(1) = 500.0
ndens    = 21,  dlgden = 0.1,  densnn(1) = 1.0e23
isw(6)   = 3,   isw(8) = 3    # 新 CONRAD
isw(15)  = 5,   isw(21) = 1
# 能群: 0.1, 1, 10, 100, 1000, 10000, 100000 eV
```

#### CH 混合物（ICF 常见）

```python
ngases   = 2
izgas    = [6, 1]         # C + H
atomwt   = [12.011, 1.008]
fracsp   = [0.5, 0.5]
ntemp    = 61,  dlgtmp = 0.1,  tplsma(1) = 2.0
ndens    = 71,  dlgden = 0.14, densnn(1) = 1.0e16
nptspg   = 200, nfrqbb = 15
isw(6)   = 3,   isw(21) = 1
# 能群: np.logspace(-1, 5, 11)
```

---

## 7. 运行流程

### 7.1 目录结构

```
ionmix/
├── src/Ionmix/            ← IONMIX 工作目录（abjt_03 可执行文件 + abjt_03.f 源码）
│   ├── abjt_03            ←   IONMIX 可执行文件（用户自行获取或编译）
│   ├── abjt_03.f          ←   FORTRAN 源代码
│   ├── ionmxinp           ←   输入文件（由生成器创建）
│   ├── eos.cn4            ←   CONRAD 格式输出
│   ├── #.cn4              ←   用户命名的输出文件
│   ├── ionmxout           ←   主输出（文本结果）
│   ├── ionmxbug           ←   详细结果（调试用）
│   ├── implot01 ~ implot09←   绘图数据文件
│   └── ATOMnn.DAT         ←   自定义电离势文件（可选）
├── src/Ionmix_run/        ← Python 生成器与运行脚本
│   ├── ionmix_core.py     ←   核心类 IONMIXInputGen（生成/编译/运行/批量）
│   ├── gen_examples.py    ← 典型示例调用脚本
│   ├── gen_mywork.py      ← 自定义用例脚本
│   ├── gen_paper.py       ← 论文示例
│   └── gen_Si.py          ← Si 靶示例
└── docs/                  ← 文档（本指南 + macfarlane1989.md）
```

> **重要（FLASH License 合规）**: IONMIX 可执行文件 `abjt_03` 与 Fortran 源码 `abjt_03.f` **不随 flash-sim 发布包分发**（受 FLASH License Agreement §3 约束）。用户需自行从 [Elsevier Digital Commons Data](https://elsevier.digitalcommonsdata.com/datasets/8n4r3rh8kr/1)（DOI `10.17632/8n4r3rh8kr.1`）下载 `abjt_v1_0.gz` 并解压到 `src/Ionmix/`。`run_single()` 在可执行文件缺失时会尝试用 WSL gfortran 从 `abjt_03.f` 自动编译。

### 7.2 Python 自动运行

```bash
cd src/Ionmix_run/
python gen_mywork.py
```

自动流程（`run_single()`）：
1. 创建 `IONMIXInputGen` 实例
2. 设置参数（调用 `set_parameter` / `set_grupbd` 或示例方法）
3. 生成 `ionmxinp` 到工作目录
4. 拷贝/编译 `abjt_03`（缺失时经 WSL gfortran 自动编译）
5. 执行 `./abjt_03`
6. 将 `eos.cn4` 重命名为 `Z{izgas}_{fracsp}.cn4` 规范文件名

### 7.3 手动运行

```bash
# 1. 编辑输入文件
vim ../Ionmix/ionmxinp

# 2. 进入目录并运行
cd ../Ionmix
./abjt_03

# 3. 查看结果
cat ionmxout
cat ionmxbug
cat eos.cn4
```

### 7.4 编译说明

如需从源代码重新编译：

```bash
cd ../Ionmix
gfortran -o abjt_03 abjt_03.f -O2 -ffixed-line-length-132
chmod +x abjt_03
```

> **注意**: 原代码包含 VAX/VMS 系统调用（`CALL TIME`、`CALL IDATE`），已被注释移除。NAMELIST 语法在不同 FORTRAN 编译器下可能需调整。

---

## 8. 限制与注意事项

### 8.1 物理限制

1. **理想等离子体**: 忽略粒子间势能，要求 $n_{\text{tot}} \leq 10^{20} (T/\langle Z \rangle)^3$ cm$^{-3}$
2. **碰撞主导**: 假设辐射场弱
3. **统一温度**: 电子和离子温度相同。**不支持双温等离子体**（$T_e \neq T_i$）
4. **温度下限**: $T \geq 10^4$ K，无分子效应
5. **类氢近似**: 激发能级、振子强度等使用类氢离子近似

### 8.2 代码限制

- **默认电离势**仅覆盖 H, He, Li, Be, B, C, N, O, F, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, Sc, Ti, V, Cr, Mn, Fe, Ni, Cu, Kr, Xe（共 30 种元素）
- 其他元素需通过 `ATOMnn.DAT` 文件由用户提供电离势（设置 `isw(1)=1`），格式为**每行一个电离势值**（中性原子、一次电离、二次电离...）
- **SESAME 格式输出**（`isw(8)=2`）**未实现**（代码中有 `STOP` 提示）

### 8.3 常见警告

```
*** warning ***  the temperature is not within the photon energy boundaries --
   this means the mean opacities are suspect
```

- 可能原因：能群边界未覆盖等离子体温度范围，导致 Planck 函数积分不完整
- 解决方案：调整 `grupbd` 使其覆盖 $0.1 T$ 到 $10 T$ 范围

### 8.4 NaN 输出

常见原因：
- 温度超出能群边界 → 检查温度范围和 `grupbd`
- 密度过低导致电子密度为零 → 检查密度网格
- 高 Z 元素在特定离子阶段的数值发散 → 调整 `isw(15)` 或 `nptspg`

---

## 9. 常见问题

### Q1: 如何选择能群边界？

A: 覆盖感兴趣的光子能量范围，确保 $h\nu_{\min} \ll k_B T \ll h\nu_{\max}$。一般建议从 0.1 eV 扩展到 100 keV，在电离边附近加密（参考 `grupbd = [0.1, 1, 10, 100, 1000, 1e4, 1e5]` eV）。

### Q2: Planck 和 Rosseland 平均区别？

| 类型 | 权重 | 应用场景 |
|------|------|----------|
| Planck 吸收 | $B_\nu(T_R)$ | 光学薄吸收/发射率 |
| Planck 发射 | $\eta_\nu$ (参与 Planck 函数) | 光学薄发射率 |
| Rosseland | $\partial B_\nu/\partial T_R$ | 光学厚辐射扩散 |

### Q3: 如何修改数组维度上限？

A: 修改 Fortran 源代码中的 `COMMON` 块数组声明。例如将 `ntemp=20` 改为 50：
- 修改所有 `DIMENSION` 声明中的 `20` 为 `50`
- 注意 `OWTF` 和 `MESHHV` 中的格式语句可能需要调整

### Q4: 如何添加新原子？

A: 对于 Z > 54 的元素：
1. 创建电离势文件命名为 `ATOMnn.DAT`（nn=原子序数，两位数）
2. 文件格式：每行一个电离势值（eV），从中性原子开始
3. 在输入文件中设置 `isw(1)=1`

### Q5: 运行中出现数值错误怎么办？

A: 排除步骤：
1. 设置 `isw(3)=1` 查看调试输出
2. 检查 `ionmxbug` 中的中间变量
3. 使用更简单的模型减弱计算量（如设置 `isw(19)=1` 跳过谱线）
4. 增加 `nptspg` 和 `nfrqbb`（但会增加计算时间）

### Q6: 如何加快计算速度？

A: 可尝试：
- 减少网格点数（ntemp, ndens）
- `isw(2)=1` 跳过不透明度
- `isw(19)=1` 跳过线计算
- `isw(17)=1` 跳过轫致辐射
- 减小 `isw(15)` 限制主量子数
- 减少 `nptspg` 和 `nfrqbb`
- 使用 Lorentzian 代替 Voigt（`isw(14)=1`）

### Q7: 如何输出 eos.cn4？

A: 必须同时满足：
1. 输入文件中设置 `isw(21)=1`
2. 执行程序后会在工作目录生成 `eos.cn4`

### Q8: 如何判断 LTE / non-LTE？

A: 检查 `implot07` 中的第 2 列（`opme/opma`）：
- 比值 ≈ 1: LTE（吸收=发射）
- 比值 ≠ 1: non-LTE（需分别考虑吸收和发射）

---

## 10. 参考文献

1. J.J. MacFarlane, "IONMIX - A code for computing the equation of state and radiative properties of LTE and non-LTE plasmas", *Computer Physics Communications* 56 (1989) 259–278. — **核心文献**
2. M. Uesaka, R.R. Peterson and G.A. Moses, *Nucl. Fusion* 24 (1984) 1137.
3. R.V. Jensen, D.E. Post, W.H. Grasberger, C.B. Tarter, and W.A. Lokke, *Nucl. Fusion* 17 (1977) 1187.
4. D. Mihalas, *Stellar Atmospheres* (Freeman, San Francisco, 1978).
5. T.A. Carlson, C.W. Nestor Jr., N. Wasserman and J.D. McDowell, *At. Data Nucl. Data Tables* 2 (1970) 63.
6. M.J. Seaton, *Mon. Not. R. Astron. Soc.* 119 (1959) 81.
7. W.J. Karzas and R. Latter, *Astrophys. J. Suppl.* 6 (1961) 167.
8. H. Van Regemorter, *Astrophys. J.* 136 (1962) 906.
9. A. Burgess, *Astrophys. J.* 141 (1965) 1588.

---

> **文档版本**: v2.1（适配 flash-sim 0.1.0 PyPI 发布版目录结构）
>
> **更新日期**: 2026-08-12
>
> **信息来源**:
> - MacFarlane (1989) 原始论文（`macfarlane1989.md`）
> - IONMIX Fortran 源代码（`abjt_03.f`）
> - Python 生成器（`src/Ionmix_run/ionmix_core.py` 及变体）
> - 中文技术说明（`输出文件参数说明/` 中 17 份文档）
> - 各类示例文件和运行结果
