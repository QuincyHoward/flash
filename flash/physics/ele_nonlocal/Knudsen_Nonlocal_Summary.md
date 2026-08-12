# 激光聚变等离子体非局域电子热传导判定 — 物理总结与实施计划

> 基于 `equation_cal.tex` 的修正 Spitzer-Härm 通量限制模型 | CGS 单位制 | Ti 掺杂光谱诊断

---

## 目录

1. [物理模型](#1-物理模型)
2. [核心公式汇总](#2-核心公式汇总)
   - [2.5 电子平均自由程（标准粒子 MFP）](#25-电子平均自由程-lambda_ei标准粒子碰撞-mfp)
   - [2.5.1 两种 MFP 的本质区别](#251-两种电子平均自由程mfp的本质区别)
3. [准稳态近似：理论、判据与严格检验](#3-准稳态近似理论判据与严格检验)
4. [$DT/Dt$ vs $\partial T/\partial t$：诊断数据的物理意义](#4-dtdt-vs-部分t部分t诊断数据的物理意义)
5. [实验数据实施计划](#5-实验数据实施计划)
6. [模拟数据实施计划](#6-模拟数据实施计划)
7. [实施路线图](#7-实施路线图)

---

## 1. 物理模型

### 1.1 问题定义

**目标**：判定激光烧蚀等离子体中某一空间区域是否需要使用非局域电子热传导模型。

**判据**：克努森数（Knudsen Number）

$$ \mathrm{Kn} = \frac{\lambda_{\mathrm{eff}}}{L_T} $$

其中 $\lambda_{\mathrm{eff}}$ 为电子热传导有效平均自由程，$L_T = T_e / |\nabla T_e|$ 为温度梯度标长。

### 1.2 判据阈值

| Kn 范围 | 热传导状态 | 行动 |
|---------|----------|------|
| $\mathrm{Kn} < 10^{-3}$ | 局域（纯扩散） | Spitzer-Härm 完全适用 |
| $10^{-3} \le \mathrm{Kn} < 10^{-2}$ | 局域（通量限制建议） | SH + 通量限制器 |
| $10^{-2} \le \mathrm{Kn} < 0.1$ | 过渡区 | 非局域效应开始显现，建议使用非局域模型 |
| $\mathrm{Kn} \ge 0.1$ | 非局域必需 | SH 失效，必须使用非局域电子热传导 |

### 1.3 关键关系：Kn 与通量限制因子的等价性

在本模型中，Knudsen 数等于热流通量限制因子 $f$：

$$ \mathrm{Kn} = \frac{\lambda_{\mathrm{eff}}}{L_T} = f = \frac{q_{\mathrm{SH}}}{q_{\mathrm{fs}}} $$

当 $f > \alpha_{ele}$（通量限制因子，CH 取 0.06）时，热流被主动限幅至 $q_{\max}$。

---

## 2. 核心公式汇总

### 2.1 有效电子热流（通量限制 SH 模型）

$$ q_{\mathrm{eff}} = \min\!\left\{D,\ \frac{q_{\max}}{|\nabla T_e|}\right\} \cdot \nabla T_e $$

### 2.2 最大热流 $q_{\max}$

$$ q_{\max} = \alpha_{ele}\, n_e k_B T_e \cdot \sqrt{\frac{k_B T_e}{m_e}} = \mathbf{A} \cdot n_e T_e^{3/2} $$

$$ \mathbf{A} = \alpha_{ele}\, k_B^{3/2} m_e^{-1/2} $$

### 2.3 修正 Spitzer-Härm 热导率 $D = K_{ele}$

$$ D = K_{ele} = \left(\frac{8}{\pi}\right)^{3/2} \frac{k_B^{7/2}}{e^4 \sqrt{m_e}} \cdot \frac{1}{\bar{z} + 3.3} \cdot \frac{T_e^{5/2}}{\ln\Lambda_{ei}} $$

化简：
$$ D = \mathbf{B} \cdot T_e^{5/2} \cdot \frac{1}{\ln\Lambda_{ei}},\quad \mathbf{B} = \mathbf{B}_0 \cdot \mathbf{G}_1 $$

$$ \mathbf{B}_0 = \left(\frac{8}{\pi}\right)^{3/2} \frac{k_B^{7/2}}{e^4 \sqrt{m_e}},\qquad \mathbf{G}_1 = \frac{1}{\bar{z} + 3.3} $$

**与标准 Spitzer 的区别**：
- 系数：$(8/\pi)^{3/2}$ 替代 $20(2/\pi)^{3/2}$
- Z 依赖：$1/(Z+3.3)$ 替代 $1/Z$（电子-电子碰撞修正内置）

### 2.4 库仑对数 $\ln\Lambda_{ei}$（量子修正版）

$$ \ln\Lambda_{ei} = \ln\!\left(1 + \frac{b_{\max}}{b_{\min}}\right) $$

$$ b_{\max} = \sqrt{\frac{k_B T_e}{4\pi e^2 n_e}} = \mathbf{C} \cdot T_e^{1/2} n_e^{-1/2} $$

$$ b_{\min} = \max\!\left\{\frac{\bar{z} e^2}{3 k_B T_e},\ \frac{\hbar}{2\sqrt{3 k_B T_e m_e}}\right\} $$

**创新点**：$\ln(1+\Lambda)$ 替代 $\ln(\Lambda)$（高密度低温下数值稳定）；$b_{\min}$ 包含量子修正（高密度下电子简并效应）。

### 2.5 电子平均自由程 $\lambda_{ei}$（标准粒子碰撞 MFP）

**标准定义**（文献中 Knudsen 判据的分子）：

$$ \nu_{ei} = \frac{4\sqrt{2\pi}}{3} \cdot \frac{n_e Z e^4 \ln\Lambda_{ei}}{\sqrt{m_e}\,(k_B T_e)^{3/2}} \quad [\mathrm{s}^{-1}] $$

$$ v_{\mathrm{th}} = \sqrt{\frac{3k_B T_e}{m_e}},\qquad \lambda_{ei} = \frac{v_{\mathrm{th}}}{\nu_{ei}} \quad [\mathrm{cm}] $$

其中 $\ln\Lambda_{ei}$ 使用本模型 §2.4 的量子修正定义。

$$ \boxed{\mathrm{Kn} = \frac{\lambda_{ei}}{L_T}} \quad \text{(standard Knudsen number)} $$

**通量限制因子 $f$ 独立定义**（不与 Kn 等同）：

$$ f = \frac{q_{\mathrm{SH}}}{q_{\mathrm{fs}}} = \frac{D \cdot |\nabla T_e|}{n_e k_B T_e v_{\mathrm{th}}^{\text{(user)}}},\quad v_{\mathrm{th}}^{\text{(user)}} = \sqrt{\frac{k_B T_e}{m_e}} $$

Kn 与 $f$ 是两个独立判据：Kn 判定非局域程度，$f$ 判定热流是否饱和。两者数值不相等。

#### 2.5.1 两种电子平均自由程（MFP）的本质区别

在电子热传导的语境中，**"平均自由程"（MFP, Mean Free Path）有两种完全不同的含义**，混淆二者会导致 Knudsen 判定系统性偏差。

**MFP = Mean Free Path = 平均自由程**
指粒子（或能量载体）在两次碰撞之间自由运动的平均距离。在电子输运中有两种不同的定义：

##### (a) 粒子碰撞平均自由程 $\lambda_{ei}$（粒子 MFP）

**物理图像**：单个电子与离子发生 Coulomb 碰撞前的平均自由飞行距离。

$$ \lambda_{ei} = \frac{v_{th}}{\nu_{ei}} $$

其中 $v_{th}$ 为热速度，$\nu_{ei}$ 为电子-离子碰撞频率。

**主导电子**：Maxwell 分布峰值附近的热电子（速度 $\sim v_{th}$），占粒子数主体。

**典型数值**（$T_e = 1000$ eV，$n_e = 10^{21}$ cm⁻³，$Z = 3.5$）：

$$ \lambda_{ei} \approx 2 \times 10^{-6}\ \mathrm{cm} \ (\sim 0.02\ \mu\mathrm{m}) $$

**用途**：判定等离子体是否为流体（$\lambda_{ei} \ll L$）、计算电阻率、能量弛豫等**局域输运**问题。

##### (b) 热传导有效平均自由程 $\lambda_{\mathrm{eff}}$（热传导 MFP，参考概念）

**物理图像**：携带热流的超热尾电子从热端到冷端传递热能的**等效特征距离**。

$$ \lambda_{\mathrm{eff}} = \frac{D}{n_e k_B v_{th}} $$

**主导电子**：Maxwell 分布尾部的超热电子（速度 $\sim 3$–$4\ v_{th}$），虽数量少但因其高速度在热流积分中权重极大。

**典型数值**（$T_e = 1000$ eV，$n_e = 10^{21}$ cm⁻³，$Z = 3.5$）：

$$ \lambda_{\mathrm{eff}} \approx 3 \times 10^{-5}\ \mathrm{cm} \ (\sim 0.3\ \mu\mathrm{m}) $$

**用途**：理解热传导尾电子物理图像；解释为何通量限制因子 $f$ 可能远大于粒子 Kn。

##### (c) 为什么 $\lambda_{\mathrm{eff}} \gg \lambda_{ei}$：超热尾电子的物理

热流由速度分布的**第三阶矩**主导：

$$ \mathbf{q} = \frac{1}{2} m_e \int v^2 \mathbf{v} f(\mathbf{v})\ d^3v $$

被积函数中 $v^3$ 的权重极大地放大了 Maxwell 分布尾部（$v \sim 3$–$4\ v_{th}$）的贡献。而 Coulomb 碰撞频率随速度急剧下降：

$$ \nu_{ei}(v) \propto v^{-3} $$

一个 $v = 3v_{th}$ 的尾电子：
- 碰撞频率仅为热电子的 $1/27$
- 平均自由程为热电子的 **$3^4 = 81$ 倍**

因此热传导的有效平均自由程天然比粒子碰撞平均自由程大**一个数量级以上**。

##### (d) 对比汇总表

| | 粒子 MFP $\lambda_{ei}$ | 热传导 MFP $\lambda_{\mathrm{eff}}$ |
|---|---|---|
| **定义** | $\lambda_{ei} = v_{th}/\nu_{ei}$ | $\lambda_{\mathrm{eff}} = D/(n_e k_B v_{th})$ |
| **物理含义** | 电子每碰一次走多远 | 电子从热端传热传多远 |
| **载体电子群** | 热速度附近电子（~$v_{th}$，占主体） | 超热尾电子（~$3$–$4v_{th}$，占少数但主导热流） |
| **量级（1000 eV, $10^{21}$ cm⁻³）** | ~$0.02$ μm | ~$0.3$ μm（约 **15 倍**） |
| **若误用于 Kn 判据** | Kn 被低估 3–7× → 系统性误判为局域 | ✅ 正确的 Kn（= 通量限制因子 $f$） |

##### (e) 公式形式的逐项对比

若统一化为 $\propto (k_B T_e)^2 / (n_e \cdot F(Z) \cdot e^4 \ln\Lambda)$ 的形式：

| 项目 | 粒子 MFP（标准 Spitzer） | 热传导 MFP（equation_cal.tex） |
|------|------------------------|---------------------------|
| **前置系数** | $\frac{3\sqrt{3}}{4\sqrt{2\pi}} \approx 0.518$ | $\left(\frac{8}{\pi}\right)^{3/2} \approx 4.062$ |
| **$Z$ 依赖因子 $F(Z)$** | $Z \cdot (1 + \frac{1}{\sqrt{2}Z}) = Z + 0.707$ | $Z + 3.3$ |
| **$F(Z=1)$** | $1.707$ | $4.3$ |
| **$F(Z=3.5)$** | $4.207$ | $6.8$ |
| **$\ln\Lambda$ 定义** | $\ln(\Lambda)$，$b_{\min}=e^2/(k_B T)$，无量子修正 | $\ln(1+\Lambda)$，$b_{\min}=\max\{Z e^2/(3k_B T),\ \hbar/(2\sqrt{3k_B T m_e})\}$（含量子修正） |
| **$v_{th}$ 约定** | $\sqrt{3k_B T/m_e}$ | $\sqrt{k_B T/m_e}$（用户约定） |

**注意**：Kn 与通量限制因子 $f$ 是两个独立量。Kn = $\lambda_{ei}/L_T$ 基于粒子碰撞 MFP，用于判定是否偏离局域 Spitzer-Härm 传导；$f = q_{\mathrm{SH}}/q_{\mathrm{fs}}$ 基于热导率与自由流热流之比，用于判定热流是否饱和。二者均在程序中间接关联——物理上，Kn 越大 → 热传导越偏离扩散极限 → $f$ 也趋于增大 — 但它们**不相等**，也不应被等同。

### 2.6 预计算常数（CGS 单位制）

| 符号 | 表达式 | 数值 |
|------|--------|------|
| $\mathbf{C}$ | $\sqrt{k_B/(4\pi e^2)}$ | $6.90 \times 10^3$ |
| $\mathbf{E}$ | $\bar{z} e^2/(3 k_B)$ | $\bar{z} \cdot 5.57 \times 10^{-6}$ |
| $\mathbf{F}$ | $\hbar/(2\sqrt{3 k_B m_e})$ | $2.45 \times 10^{-9}$ |
| $\mathbf{A}$ | $\alpha_{ele} k_B^{3/2} m_e^{-1/2}$ | $\alpha_{ele} \cdot 5.37 \times 10^{15}$ |
| $\mathbf{B}_0$ | $(8/\pi)^{3/2} k_B^{7/2}/(e^4\sqrt{m_e})$ | $2.15 \times 10^{-67}$ |

### 2.7 CGS 基本常数

| 常数 | 符号 | CGS 值 |
|------|------|--------|
| 玻尔兹曼常数 | $k_B$ | $1.380649 \times 10^{-16}$ erg/K |
| 元电荷 | $e$ | $4.8032047 \times 10^{-10}$ esu |
| 电子质量 | $m_e$ | $9.1093837 \times 10^{-28}$ g |
| 约化普朗克常数 | $\hbar$ | $1.0545718 \times 10^{-27}$ erg·s |
| 电子伏特 | $1$ eV | $1.602176634 \times 10^{-12}$ erg |
| 单位转换 | — | $1$ K = $8.617 \times 10^{-5}$ eV；$1$ μm = $10^{-4}$ cm；$1$ ns = $10^{-9}$ s |

---

## 3. 准稳态近似：理论、判据与严格检验

### 3.1 准稳态的定义与公式

物质导数分解：

$$ \frac{DT_e}{Dt} = \frac{\partial T_e}{\partial t} + \mathbf{v} \cdot \nabla T_e $$

$$\begin{array}{ll}
DT_e/Dt & \text{— 物质导数（跟随流体微元观测）} \\
\partial T_e/\partial t & \text{— Eulerian 当地导数（固定空间点观测）} \\
\mathbf{v} \cdot \nabla T_e & \text{— 对流导数（微元在温度梯度上运动）}
\end{array}$$

**准稳态条件**：$\partial T_e/\partial t \approx 0$，此时 $DT_e/Dt \approx \mathbf{v} \cdot \nabla T_e$。

### 3.2 为什么准稳态假设是"信息不完备"问题而非物理假设

在只有 Lagrangian 追踪数据（$T(t), v(t)$）时：

- **已知**：$DT/Dt$（差分 $T(t)$ 直接得到）
- **未知**：$\partial T/\partial t$（需要同一空间点不同时刻数据）
- **需要**：$\nabla T_e$（需要同一时刻不同空间点数据）

我们有一个方程（$DT/Dt = \partial T/\partial t + v\cdot\nabla T$），但有两个未知数（$\partial T/\partial t$ 和 $\nabla T$）。这是**信息论层面的硬约束**——无法从纯追踪数据内部解决。

准稳态假设 $\partial T/\partial t \approx 0$ 消去了一个未知数，使得 $\nabla T \approx (DT/Dt)/v$ 可解。

### 3.3 严格实验判据：$R(T)$ 函数检验

**数学原理**：在准稳态流中，$T(x)$ 仅是 $x$ 的函数，$dT/dx = F(T)$ 仅依赖 $T$。因此：

$$ R(T) = \frac{1}{v}\frac{dT}{dt} = \frac{dT}{dx} = F(T) $$

$R$ 作为 $T$ 的函数必须是**单值**的。

**操作步骤**：

1. 取激光功率平顶段的时间窗口 $[t_1, t_2]$
2. 对每个时间点 $t_i$，计算：
   $$ R_i = \frac{T_{i+1} - T_{i-1}}{2\Delta t} \cdot \frac{1}{v_i} $$
3. 以 $T_i$ 为横轴、$R_i$ 为纵轴作图
4. 检验 $R(T)$ 是否为单值曲线

**判定标准**：

| $R(T)$ 形态 | 散度 $\sigma_R / \bar{R}$ | 判定 | 行动 |
|------------|-------------------------|------|------|
| 清晰单值曲线 | $< 15\%$ | ✅ 严格准稳态 | 放心使用 Derived 模式 |
| 窄带 | $15\%$–$25\%$ | ✅ 近似准稳态 | Derived 模式，附加置信度标注 |
| 宽带 | $25\%$–$40\%$ | ⚠️ 临界 | 输出 $[\mathrm{Kn}_{\min}, \mathrm{Kn}_{\max}]$ 区间 |
| 散点/环状 | $> 40\%$ | ❌ 非准稳态 | 必须用 Direct 模式（$L_T$ 直接从模拟取） |

**��格性的来源**：此判据直接检验"$T$ 与 $dT/dx$ 的一一对应关系"，这正是稳态的数学定义。不需要任何外部假设或模拟数据。

### 3.4 辅助实验判据

| 判据 | 条件 | 物理含义 |
|------|------|---------|
| $T/v \approx$ 常数 | $T_i/v_i$ 变化 < 20% | 准等压烧蚀，质量通量守恒 |
| $T(t)$ 单调递减 | $dT/dt < 0$ 持续 | 对流主导（非瞬态加热） |
| $\tau_{conv} \gg \tau_{laser}$ | $T/|dT/dt| \gg$ 激光波动周期 | 温度响应对激光波动不敏感 |

### 3.5 严格模拟判据

**方法 1 — Eulerian 残差检验**：

$$ S(x,t) = \frac{|\partial T/\partial t|}{|v\cdot\nabla T|} $$

- $S < 0.05$：严格准稳态
- $0.05 < S < 0.2$：近似准稳态
- $S > 0.2$：非准稳态

**方法 2 — Tracer 对比法**：

对比 Lagrangian tracer 推算的 $L_T^{\mathrm{trace}}$ 与 Eulerian 空间梯度直接得到的 $L_T^{\mathrm{true}}$：

$$ \eta(t) = \frac{|L_T^{\mathrm{trace}} - L_T^{\mathrm{true}}|}{L_T^{\mathrm{true}}} $$

- $\eta < 0.1$：准稳态成立
- $\eta > 0.3$：准稳态不成立

**方法 3 — 能量方程完整核算**：

从模拟输出计算所有能量方程项，定义稳态指数：

$$ \mathcal{S} = \frac{|\partial T/\partial t|}{\max(|v\cdot\nabla T|, |\nabla\cdot q/(\rho c_v)|, |Q_{las}/(\rho c_v)|)} $$

$\mathcal{S} < 0.05$ 为绝对严格稳态。

---

## 4. $DT/Dt$ vs $\partial T/\partial t$：诊断数据的物理意义

### 4.1 各观测量的对应关系

| 实验诊断 | 给出量 | 对应导数 | 获取方式 |
|---------|--------|---------|---------|
| Ti Doppler 频移 | $v(t)$ | — | 直接测量 |
| Ti 线强/线宽比 | $T(t)$ | — | 直接测量 |
| $T(t)$ 差分 | $dT/dt$ | $DT/Dt$ (物质导数) | 检验 $T(t)$ 后直接算出 |
| — | $\partial T/\partial t$ | Eulerian 当地导数 | **不可直接测量** |
| — | $\nabla T$ | 空间温度梯度 | **不可直接测量** |

**核心事实**：追踪同一 Ti 微元 → 数据沿 Lagrangian 轨迹 → 得到的是 **$DT/Dt$（物质导数）**，不是 $\partial T/\partial t$。

### 4.2 两种导数的物理图像

```
∂T/∂t（Eulerian）：
  固定点观测
  ┌─────────────┐
  │ x = const   │  不同时刻，不同流体微元流过
  │ t₁: T=1000  │  → 看到的温差来自微元来源不同
  │ t₂: T=950   │
  └─────────────┘

DT/Dt（Lagrangian）：
  跟随微元
  ┌─────────────┐
  │ 同一团流体  │  微元自身在运动中冷却/加热
  │ x(t₁) → x(t₂)│  → 真实的能量得失
  │ T(t₁)=1000  │
  │ T(t₂)=950   │
  └─────────────┘
```

### 4.3 $\partial T/\partial t$ 的三种评估方法

**方法 A — 激光功率波动上界估计**：

$$ \left|\frac{\partial T}{\partial t}\right|_{\max} \approx \frac{T}{\tau_{\mathrm{response}}} \cdot \frac{\Delta P}{P} $$

- $\tau_{\mathrm{response}} \sim 0.3$ ns（电子-离子能量弛豫+对流混合时标）
- $\Delta P/P \sim 3\%$–$5\%$（调 Q 激光平顶）
- 典型值：$|\partial T/\partial t|_{\max} \sim 100$–$200$ eV/ns

**方法 B — 双 Ti 掺杂层**：

靶设计中在 $x_1$ 和 $x_2$ 两深度掺杂 Ti。若两层信号有交叠窗口：

1. 同窗口得到 $(T_1, v_1)$ 和 $(T_2, v_2)$
2. 推算 $\nabla T \approx (T_2 - T_1)/(x_2 - x_1)$
3. 从 $DT/Dt$ 和 $\nabla T$ 反算 $\partial T/\partial t$

**方法 C — FLASH 模拟一次标定**：

用标称实验参数跑模拟，计算校正因子：

$$ C(t) = L_T^{\mathrm{true}}(\nabla T) / L_T^{\mathrm{trace}}(DT/Dt, v) $$

将 $C(t)$ 施加到后续实验数据的 $L_T^{\mathrm{trace}}$ 上。

---

## 5. 实验数据实施计划

### 5.1 输入数据规格

| 参数 | 来源 | 符号 | 单位 | 时间分辨率要求 |
|------|------|------|------|--------------|
| Ti 示踪温度 | Ti 光谱线宽/线强比 | $T(t)$ | eV | $\le 0.1$ ns |
| Ti 示踪速度 | Ti 光谱 Doppler 频移 | $v(t)$ | μm/ns | $\le 0.1$ ns |
| 电子密度 | Stark 展宽 / 模拟参考值 | $n_e$ | cm⁻³ | 每数据点插值 |
| 平均电离度 | 模拟 / 碰撞辐射模型 | $\bar{z}$ | — | 常数或缓变 |
| 激光功率波形 | 实验记录 | $P(t)$ | W/cm² | $\le 0.1$ ns |
| 通量限制因子 | 材料参数 (CH: 0.06) | $\alpha_{ele}$ | — | 常数 |

### 5.2 执行步骤

#### Phase 1 — 数据筛选

1. **时间窗口筛选**：只取 $P(t)$ 平顶段（$|\Delta P/P| < 5\%$）
2. **速度阈值筛选**：剔除 $v < 5$ μm/ns 的滞止区数据
3. **单调性检查**：筛选 $T(t)$ 单调下降段（排除瞬态加热段）
4. **异常值剔除**：剔除 $|dv/dt|$ 异常大的激波段

#### Phase 2 — 准稳态 $R(T)$ 检验

对筛选后的每个时间点：

1. 计算 $R_i = \frac{T_{i+1} - T_{i-1}}{2\Delta t} \cdot \frac{1}{v_i}$
2. 绘制 $R_i$ vs $T_i$ 散点图
3. 计算散度 $\sigma_R / \bar{R}$
4. 判定准稳态置信度

#### Phase 3 — $L_T$ 计算（根据 $R(T)$ 检验结果选择模式）

**若 $R(T)$ 通过检验**（$\sigma_R/\bar{R} < 25\%$）：

使用 Derived 模式：
$$ L_T = \frac{T \cdot v}{|dT/dt|} \quad [\mathrm{cm}] $$

注意：结果为保守上限（假设 $\partial T/\partial t = 0$，若实际 $\partial T/\partial t < 0$，则真实 $L_T$ 更大、Kn 更小）。

**若 $R(T)$ 未通过检验**（$\sigma_R/\bar{R} > 40\%$）：

不可用准稳态公式。需借助模拟数据切换到 Direct 模式，输入 $\nabla T_e$ 的直接值。

**若临界**（$25\% < \sigma_R/\bar{R} < 40\%$）：

输出 $[\mathrm{Kn}_{\min}, \mathrm{Kn}_{\max}]$ 区间（用 $\partial T/\partial t$ 上界约束）。

#### Phase 4 — Kn 计算与判定

1. 使用 [`knudsen_judge.html`](knudsen_judge.html) 工具（打开选择 `equation_cal.tex` 版）
2. 输入 $(T, v, dT/dt, n_e, \bar{z}, \alpha_{ele})$ 或直接输入 $L_T$
3. 读取 Kn 值及判定结果

#### Phase 5 — 时间序列输出

对每个时间点生成：

| 时间 | $T$ | $v$ | $dT/dt$ | $L_T$ | $\lambda_{\mathrm{eff}}$ | Kn | 判定 | 准稳态置信度 |
|------|-----|-----|---------|-------|------------------------|-----|------|------------|
| $t_1$ | ... | ... | ... | ... | ... | ... | 局域/过渡/非局域 | 高/中/低 |
| $t_2$ | ... | ... | ... | ... | ... | ... | ... | ... |

### 5.3 输出与可视化

- $R(T)$ 散点图（准稳态诊断用）
- Kn($t$) 时间序列曲线
- $T$–$n_e$ 相图（标注 Kn 等值线区域）
- 各时刻的区域/非局域状态时间线

---

## 6. 模拟数据实施计划

### 6.1 输入数据规格

| 参数 | FLASH 输出变量 | 符号 | 需求 |
|------|---------------|------|------|
| 全场电子温度 | `tele` | $T_e(x,t)$ | all blocks, all timesteps |
| 全场电子密度 | `dens` × $Z/A m_u$ | $n_e(x,t)$ | all blocks |
| 全场电子热流 | `qele` | $\mathbf{q}_{ele}(x,t)$ | all blocks |
| 全场速度 | `velx`/`vely`/`velz` | $\mathbf{v}(x,t)$ | all blocks |
| Lagrangian tracer 数据 | $T_{\mathrm{tr}}(t), v_{\mathrm{tr}}(t), x_{\mathrm{tr}}(t)$ | — | 追踪微元时间序列 |
| 激光功率 | `laser_power` | $P(t)$ | 全场背景时间积分量 |

### 6.2 执行步骤

#### Phase 1 — 准稳态全场判定（Eulerian $S$ 检验）

对每个 grid cell 和 timestep：

1. 计算 $\partial T/\partial t$（finite difference in time）
2. 计算 $v\cdot\nabla T$（finite difference in space）
3. 计算 $S = |\partial T/\partial t| / |v\cdot\nabla T|$
4. 生成 $S(x,t)$ 2D colormap，识别非准稳态区域

#### Phase 2 — Tracer 对比法

对每个 tracer：

1. $L_T^{\mathrm{trace}} = T_{\mathrm{tr}}\cdot v_{\mathrm{tr}} / |dT_{\mathrm{tr}}/dt|$
2. 全场插值得 $T_{\mathrm{tr}}$ 所在位置的 $\nabla T$
3. $L_T^{\mathrm{true}} = T_{\mathrm{tr}} / |\nabla T|$
4. 计算 $\eta(t) = |L_T^{\mathrm{trace}} - L_T^{\mathrm{true}}| / L_T^{\mathrm{true}}$
5. 生成校正因子 $C(t) = L_T^{\mathrm{true}} / L_T^{\mathrm{trace}}$

#### Phase 3 — 能量方程完整核算

对关键区域（临界密度面 $n_c$、消融前沿）：

1. 从 FLASH dump 读取 $\partial(\rho e_{ele})/\partial t$
2. 计算对流项、热传导散度、激光加热项
3. 计算稳态指数 $\mathcal{S}$
4. 判定该区域是否为定常流

#### Phase 4 — Kn 空间分布计算

1. 对每个 cell：计算 $D = \mathbf{B}_0/(\bar{z}+3.3) \cdot T^{5/2}/\ln\Lambda$
2. 计算 $\lambda_{\mathrm{eff}} = D / (n_e k_B v_{th})$
3. $L_T = T/|\nabla T|$（直接空间差分）
4. $\mathrm{Kn} = \lambda_{\mathrm{eff}} / L_T$
5. 输出 $\mathrm{Kn}(x)$ 空间分布

#### Phase 5 — 非局域区域识别

标记 $\mathrm{Kn} > 0.1$ 的区域为**必须使用非局域模型**的区域。

---

## 7. 实施路线���

### 阶段 1：基础工具搭建 ✅

- [x] 编写 `knudsen_judge.html` 交互式判定工具
- [x] 集成 `equation_cal.tex` 的全部物理公式（修正 SH + 量子修正 lnΛ）
- [x] 实现 Derived / Direct L_T 双模式
- [x] 添加通量限制因子 $\alpha_{ele}$ 滑块
- [x] KaTeX 渲染完整公式面板

### 阶段 2：实验数据处理脚本

- [ ] **`data_screening.py`** — 数据筛选器
  - 输入：$(t, T, v, P)$ CSV 文件
  - 输出：筛选后的合格数据段 + 筛选报告（剔除比例、原因分类）
  - 实现：激光平顶检测、$v$ 阈值、单调性检查、异常值过滤

- [ ] **`quasi_steady_test.py`** — $R(T)$ 准稳态检验脚本
  - 输入：筛选后的 $(t, T, v)$
  - 输出：$R(T)$ 散点图 (PPT 级)、散度 $\sigma_R/\bar{R}$、准稳态置信度
  - 实现：中心差分法、最小二乘拟合、带状区间估计

- [ ] **`kn_batch.py`** — 批量 Kn 计算脚本
  - 输入：筛选后的 $(t, T, v, n_e, \bar{z}, \alpha_{ele})$
  - 输出：每时间点 Kn 值 + 判定表 (CSV)
  - 根据 $R(T)$ 检验结果自动选择 Derived/Direct 模式
  - 临界模式自动输出 $[\mathrm{Kn}_{\min}, \mathrm{Kn}_{\max}]$

- [ ] **`plot_kn_timeline.py`** — Kn 时间序列可视化
  - 输出：PPT 级 $\mathrm{Kn}(t)$ 曲线 + 区域状态彩带

### 阶段 3：FLASH 模拟分析脚本

- [ ] **`sim_steady_test.py`** — 准稳态全场判定
  - 输入：FLASH plot/checkpoint HDF5
  - 输出：$S(x,t)$ colormap、非准稳态区域标注
  - 工具：`physimx-h5py-yt-extract` skill

- [ ] **`sim_tracer_compare.py`** — Tracer 对比校正
  - 输入：FLASH tracer 数据 + 全场 $T(x,t)$
  - 输出：$\eta(t)$ 曲线、校正因子 $C(t)$

- [ ] **`sim_kn_spatial.py`** — Kn 空间分布计算
  - 输入：FLASH plot/checkpoint HDF5
  - 输出：$\mathrm{Kn}(x)$ 曲线 + 非局域区域标注

### 阶段 4：在线互动工具增强

- [ ] 工具中添加 **$R(T)$ 在线检验**功能（输入 $(t, T, v)$ 数据表，实时绘制 $R(T)$ 散点图）
- [ ] 工具中添加 **$\partial T/\partial t$ 上界估计**面板（输入激光参数，自动评估）
- [ ] 工具中添加 **批量模式**（上传 CSV，批量计算多时间点 Kn）

### 阶段 5：文档与论文支撑

- [ ] 编写 Knudsen 判据方法论文档
- [ ] 编写准稳态 $R(T)$ 检验方法的理论推导附录
- [ ] 生成典型激光烧蚀 CH 场景的 Kn 参数扫描表（$T$–$n_e$ 相图）

---

## 附录 A：典型预设参数（`knudsen_judge.html` 工具）

| 场景 | $T_e$ [eV] | $n_e$ [cm⁻³] | $\bar{z}$ | $\alpha_{ele}$ | $dT/dt$ [eV/ns] | $v$ [μm/ns] |
|------|-----------|-------------|----------|---------------|-----------------|------------|
| 日冕 (Corona) | 2000 | $1\times10^{20}$ | 3.5 | 0.06 | 60 | 300 |
| 临界密度面 (Critical) | 1000 | $1\times10^{21}$ | 3.5 | 0.06 | 50 | 150 |
| 消融前沿 (Ablation) | 100 | $5\times10^{22}$ | 3.5 | 0.06 | 30 | 50 |
| 固体密度 (Solid) | 10 | $1\times10^{23}$ | 3.5 | 0.06 | 5 | 10 |
| 黑腔壁 (Hohlraum) | 300 | $1\times10^{20}$ | 40 | 0.06 | 10 | 50 |
| 激波前沿 (Shock) | 500 | $1\times10^{22}$ | 3.5 | 0.06 | 200 | 200 |

---

## 附录 B：文件清单

| 文件 | 用途 | 位置 |
|------|------|------|
| `knudsen_judge.html` | 交互式 Kn 判定工具（浏览器） | 本目录 |
| `Knudsen_Nonlocal_Summary.md` | 本文档 | 本目录 |
| `equation_cal.tex` | 输入物理学公式源文件 | VM 共享路径 |
| `data_screening.py` (待开发) | 实验数据筛选 | — |
| `quasi_steady_test.py` (待开发) | $R(T)$ 准稳态检验 | — |
| `kn_batch.py` (待开发) | 批量 Kn 计算 | — |

---

*文档版本：v1.0 | 日期：2026-07-26 | 作者：PhySimX WorkBuddy Agent*
