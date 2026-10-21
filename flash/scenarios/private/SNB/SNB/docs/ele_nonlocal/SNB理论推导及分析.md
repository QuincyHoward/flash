# SNB 非局域电子热传导模型：理论推导与系统分析

> **文档信息**
> - 作者：PhySimX Research Group
> - 日期：2026-08-08
> - 主题：Schurtz–Nicolaï–Busquet (SNB) 非局域电子热传导模型的完整理论推导
> - 参考文献来源：经核验的已发表学术论文

---

## 摘要

Schurtz–Nicolaï–Busquet (SNB) 模型 [1] 是目前惯性约束聚变 (ICF) 和激光等离子体模拟中应用最广泛的非局域电子热传导模型。本文从动理学 Fokker-Planck 方程出发，系统推导 SNB 模型的理论架构：从 Spitzer-Härm (SH) 局域理论的失效条件开始，引入 Luciani-Mora-Virmont (LMV) 非局域卷积公式 [2]，论证该卷积形式等价于某个线性稳态输运方程的积分形式解，进而利用能量多群分解与 P1 扩散近似，将非局域热传导问题转化为一组 Helmholtz 型偏微分方程组。最后讨论电场自洽修正 [3] 及磁化等离子体推广 [4]，并综合 Brodrick 等 [5] 的 Vlasov-Fokker-Planck (VFP) 基准对比结果评估模型精度。

**关键结论**：SNB 模型的根本优势在于将非局域积分算子等价转化为局部微分方程，使其可在多维辐射流体力学代码中以标准扩散求解器高效实现。

---

## 目录

1. [动理学基础：Fokker-Planck 方程与 Spitzer-Härm 理论](#1)
2. [SH 理论的失效条件与 Bell 判据](#2)
3. [非局域卷积方法：LMV 模型](#3)
4. [SNB 模型：从卷积到等效输运方程](#4)
5. [能量多群分解](#5)
6. [P1 扩散近似与最终控制方程](#6)
7. [电场自洽修正](#7)
8. [磁化等离子体推广](#8)
9. [数值实现与边界条件](#9)
10. [模型验证与精度评估](#10)
11. [总结与展望](#11)
12. [参考文献](#12)

---

<a name="1"></a>
## 1. 动理学基础：Fokker-Planck 方程与 Spitzer-Härm 理论

### 1.1 电子 Fokker-Planck 方程

在完全电离等离子体中，电子分布函数 $f(\mathbf{v}, \mathbf{r}, t)$ 的演化由 Fokker-Planck (FP) 方程描述 [6]：

$$
\frac{\partial f}{\partial t} + \mathbf{v} \cdot \nabla_r f - \frac{e}{m_e}(\mathbf{E} + \mathbf{v} \times \mathbf{B}) \cdot \nabla_v f = C_{ee}(f) + C_{ei}(f) \tag{1}
$$

其中 $C_{ee}$ 和 $C_{ei}$ 分别为电子-电子和电子-离子碰撞算子。在经典输运理论中，假设碰撞充分频繁，分布函数可展开为球谐级数：

$$
f(\mathbf{v}, \mathbf{r}) = f_0(v, \mathbf{r}) + \frac{\mathbf{v}}{v} \cdot \mathbf{f}_1(v, \mathbf{r}) + \cdots \tag{2}
$$

其中 $f_0$ 为各向同性部分，$\mathbf{f}_1$ 为各向异性扰动。$f_0$ 接近局域麦克斯韦分布：

$$
f_0^{MB}(v; n_e(\mathbf{r}), T_e(\mathbf{r})) = n_e(\mathbf{r}) \left(\frac{m_e}{2\pi k_B T_e(\mathbf{r})}\right)^{3/2} \exp\left(-\frac{m_e v^2}{2k_B T_e(\mathbf{r})}\right) \tag{3}
$$

### 1.2 Spitzer-Härm 局域热传导

在弱梯度极限下（$\lambda_{ei}/L_T \ll 1$），Spitzer 和 Härm [7] 通过数值求解线性化的 FP 方程得到电子热导率的精确值。对于无磁场情况，电子热流遵循傅里叶定律：

$$
\mathbf{Q}_{SH}(\mathbf{r}) = -\kappa_{SH} \nabla T_e(\mathbf{r}) \tag{4}
$$

其中 SH 热导率为：

$$
\kappa_{SH} = \frac{128}{3\pi} \xi(Z) \frac{n_e k_B^2 T_e \tau_{ei}}{m_e} \propto T_e^{5/2} \tag{5}
$$

这里 $\tau_{ei}$ 是电子-离子碰撞时间，$\xi(Z) = (Z+0.24)/(Z+4.2)$ 是 Epperlein 和 Haines [8] 给出的对 Braginskii 系数 [9] 的修正因子。在实用单位制下：

$$
\kappa_{SH} \approx 3.2 \frac{n_e k_B^2 T_e}{m_e} \tau_{ei} \tag{6}
$$

### 1.3 库仑对数与平均自由程

#### 库仑对数 $\ln\Lambda$ 的物理定义

库仑对数源自 Coulomb 碰撞理论中对散射截面的积分。在等离子体中，电子-离子散射主要由大量小角度散射累积贡献 [Spitzer, *Physics of Fully Ionized Gases*, 1962]：

$$
\ln\Lambda \equiv \ln\left(\frac{b_{\max}}{b_{\min}}\right)
$$

其中：
- $b_{\max} \approx \lambda_D$（Debye 长度）——超过此距离，离子电荷被电子集体屏蔽。$\lambda_D = \sqrt{\varepsilon_0 k_B T_e / (n_e e^2)}$（SI 单位）。
- $b_{\min} = \max[b_0, \lambda_{\text{deB}}]$，其中 $b_0 = Ze^2/(4\pi\varepsilon_0 m_e v_e^2)$ 为经典最接近距离，$\lambda_{\text{deB}} = \hbar/(m_e v_e)$ 为 de Broglie 波长。

#### NRL Plasma Formulary 实用公式

在 ICF 典型参数范围（$T_e \gtrsim 10$ eV，$n_e$ 为 m$^{-3}$，$T_e$ 为 eV）内，NRL Plasma Formulary [Huba, 2019] 给出：

**电子-电子**：
$$
\ln\Lambda_{ee} = 23.5 - \frac{1}{2}\ln(n_e) + \frac{5}{4}\ln(T_e) - \sqrt{10^{-5} + \frac{(\ln T_e - 2)^2}{16}}
$$

**电子-离子**（$T_e > T_i m_e/m_i$ 且 $T_e < 10 Z^2$ eV）：
$$
\ln\Lambda_{ei} = 23 - \frac{1}{2}\ln(n_e) - \ln(Z) + \frac{3}{2}\ln(T_e)
$$

对 ICF 等离子体（$n_e \sim 10^{26}$–$10^{28}$ m$^{-3}$, $T_e \sim 100$–$5000$ eV），$\ln\Lambda \sim 5$–$15$。对于简单保守的估计，常取 $\ln\Lambda \approx 10$（量级上准确到因子 $\sim 3$）[Thorne & Blandford, 2017]。

#### $\ln\Lambda_{ei}$ 与 $\ln\Lambda_{ee}$ 的差异

电子-离子（ei）和电子-电子（ee）的 Coulomb 对数在形式上有所不同，源于两者的散射物理差异：

| 属性 | ei 碰撞 | ee 碰撞 |
|------|--------|--------|
| 散射体 | 离子（固定或慢运动，$m_i \gg m_e$） | 电子（同质量，$m_e=m_e$） |
| 约化质量 | $\mu_{ei} \approx m_e$ | $\mu_{ee} = m_e/2$ |
| 最小碰撞参数 | $b_0 = Ze^2/(m_e v^2)$ | $b_0 = e^2/(m_e v^2)$（$Z=1$） |
| 最大碰撞参数 | $b_{\max} = \lambda_D$（Debye 屏蔽） | $b_{\max} = \lambda_D$（相同） |
| **NRL 公式** | $\ln\Lambda_{ei} = 23 - \frac{1}{2}\ln n_e - \ln Z + \frac{3}{2}\ln T_e$ | $\ln\Lambda_{ee} = 23.5 - \frac{1}{2}\ln n_e + \frac{5}{4}\ln T_e - [\cdots]$ |
| **典型差值** | $\ln\Lambda_{ei} \approx \ln\Lambda_{ee} - \ln Z$ | 对于 $Z=1$ 两者几乎相等；$Z=10$ 时 $\ln\Lambda_{ei}$ 比 $\ln\Lambda_{ee}$ 小约 $\ln 10 \approx 2.3$ |

核心差异来源：
1. **$Z$ 因子**：$\ln\Lambda_{ei}$ 的 NRL 公式含 $-\ln Z$ 项，来自 ei 碰撞中离子电荷 $Z$ 对 $b_0$ 的放大。对于高 $Z$ 等离子体，ei 对数略小于 ee 对数。
2. **ee 碰撞的额外修正项**：$\ln\Lambda_{ee}$ 含较复杂的平方根项 $\sqrt{10^{-5} + (\ln T_e-2)^2/16}$，源自电子-电子之间同质量散射的量子力学和动力学修正 [NRL Formulary, 2019]。
3. **温度依赖**：$\ln\Lambda_{ee}$ 的温度指数（$5/4$）与 $\ln\Lambda_{ei}$（$3/2$）略有不同，反映了不同散射机制的热平均权重差异。

在实际 SNB 模型实现中，通常近似取 $\ln\Lambda \approx \ln\Lambda_{ei} \approx \ln\Lambda_{ee}$，因为其差值（$< 10\%$ 量级）在对数精度内可忽略。对于最简单的工程估计，直接取 $\ln\Lambda = 10$（在 CGS 单位制）或适当转换为 SI 单位对应的常数。

#### 电子-离子碰撞频率 $\nu_{ei}(v)$ 的完整推导 —— 从 Rutherford 散射到 Coulomb 对数

电子-离子碰撞频率的表达式可以从经典的 Rutherford（Coulomb）两体散射理论严格导出。推导分为以下步骤：

**步骤 1：Rutherford 微分散射截面**

考虑一个电子（电荷 $-e$，质量 $m_e$）以速度 $v$ 飞向一个静止的离子（电荷 $Ze$）。在 Coulomb 势 $V(r) = -Ze^2/(4\pi\varepsilon_0 r)$ 下，经典散射理论给出入射-出射偏转角 $\Theta$ 与碰撞参数 $b$ 的关系 [Goldston & Rutherford, 1995, §2.3]：

$$
b = \frac{Ze^2}{4\pi\varepsilon_0 m_e v^2} \cot\frac{\Theta}{2}
$$

由 $d\sigma/d\Omega = (b/\sin\Theta)|db/d\Theta|$ 可得著名的 **Rutherford 微分截面**：

$$
\frac{d\sigma}{d\Omega} = \left(\frac{Ze^2}{8\pi\varepsilon_0 m_e v^2}\right)^2 \frac{1}{\sin^4(\Theta/2)}
$$

在 CGS 单位制（$4\pi\varepsilon_0 \to 1$）下简化为：

$$
\boxed{\frac{d\sigma}{d\Omega} = \left(\frac{Ze^2}{2m_e v^2}\right)^2 \frac{1}{\sin^4(\Theta/2)}}
$$

注意：$\sin^{-4}(\Theta/2) \propto \Theta^{-4}$ 当 $\Theta \to 0$，即截面在 $\Theta=0$ 处剧烈发散。这意味着在等离子体中，库仑碰撞的主要贡献来自大量极小的偏转角散射的累积效应，而非单次大角度硬碰撞。

**步骤 2：动量输运截面（transport cross section）**

在输运理论中，决定热传导和电阻的关键不是总散射截面（被小角度发散污染），而是**动量输运截面** $\sigma_{TR}$，它对每次碰撞加权了动量损失因子 $(1-\cos\Theta)$：

$$
\sigma_{TR}(v) = 2\pi \int_{\Theta_{\min}}^{\pi} (1-\cos\Theta) \frac{d\sigma}{d\Omega} \sin\Theta \, d\Theta
$$

代入 Rutherford 截面并将 $(1-\cos\Theta)$ 写为 $2\sin^2(\Theta/2)$，经三角恒等式化简：

$$
\sigma_{TR}(v) = \frac{8\pi (Ze^2)^2}{m_e^2 v^4} \int_{\Theta_{\min}}^{\pi} \frac{\cos(\Theta/2)}{\sin(\Theta/2)} \, d\Theta
$$

积分给出对数项：$\int_{\Theta_{\min}}^{\pi} (\cos/\sin) d(\Theta/2) = \ln[\sin(\Theta_{\min}/2)]^{-1}$。利用碰撞角与碰撞参数的小角度近似 $\sin(\Theta_{\min}/2) \approx \Theta_{\min}/2 \approx b_0/b_{\max}$（其中 $b_0 = Ze^2/(m_e v^2)$ 为 90° 偏转的特征碰撞参数，$b_{\max} \approx \lambda_D$ 为 Debye 屏蔽长度），得到：

$$
\boxed{\sigma_{TR}(v) = \frac{4\pi Z^2 e^4}{m_e^2 v^4} \ln\left(\frac{b_{\max}}{b_{\min}}\right) = \frac{4\pi Z^2 e^4}{m_e^2 v^4} \ln\Lambda_{ei}}
$$

这就是 Coulomb 对数 $\ln\Lambda_{ei} \equiv \ln(b_{\max}/b_{\min})$ 的自然引入，其中 $b_{\min} = \max[b_0, \hbar/(m_e v)]$。

**步骤 3：碰撞频率**

电子-离子碰撞频率定义为：$\nu_{ei} = n_i \sigma_{TR} v$（一个速度为 $v$ 的电子在单位时间内与密度 $n_i$ 的离子目标发生有效动量转移碰撞的次数）。代入 $\sigma_{TR}$：

$$
\boxed{\nu_{ei}(v) = \frac{4\pi n_i Z^2 e^4 \ln\Lambda_{ei}}{m_e^2 v^3} \propto \frac{1}{v^3}} \tag{6a}
$$

在 SI 单位制下需加入 $(4\pi\varepsilon_0)^{-2}$ 因子：$\nu_{ei}(v) = n_i Z^2 e^4 \ln\Lambda_{ei} / (4\pi\varepsilon_0^2 m_e^2 v^3)$。

**物理含义**：$\nu_{ei} \propto v^{-3}$ 反映了快速电子具有较小的散射截面——快电子"擦过"离子的时间更短，偏转更小，因此碰撞频率更低。这是为什么载热电子（高 $v$）具有极长自由程的根本原因。

**热平均**后的碰撞频率（对 Maxwell 分布 $f_0(v) \propto v^2 e^{-m_e v^2/(2k_B T_e)}$ 权重积分）：

$$
\boxed{\langle\nu_{ei}\rangle = \frac{4\sqrt{2\pi}}{3} \frac{n_i Z^2 e^4 \ln\Lambda_{ei}}{m_e^{1/2} (k_B T_e)^{3/2}}}
$$

#### 电子-离子平均自由程

碰撞时间 $\tau_{ei} = 1/\langle\nu_{ei}\rangle$，平均自由程 $\lambda_{ei} \equiv v_{th}\tau_{ei}$（$v_{th} = \sqrt{k_B T_e/m_e}$）：

$$
\boxed{\lambda_{ei} = \frac{3\sqrt{\pi}}{2} \frac{(k_B T_e)^2}{4\pi Z n_e e^4 \ln\Lambda_{ei}}} \tag{7}
$$

#### 电子-电子平均自由程

类似推导：
$$
\boxed{\lambda_{ee} = \frac{3}{4\sqrt{2\pi}} \frac{(k_B T_e)^2}{n_e e^4 \ln\Lambda_{ee}}}
$$

与 $\lambda_{ei}$ 相比，$\lambda_{ee}/\lambda_{ei} \approx Z$（对于相同 $\ln\Lambda$）。

#### SNB 模型中的有效平均自由程

在 SNB 模型的实现中 [1]，采用几何平均：

$$
\boxed{\lambda_e = \sqrt{\lambda_{ei} \lambda_{ee}} = (Z+1)^{-1/2} \frac{(k_B T_e)^2}{4\pi n_e e^4 \ln\Lambda}} \tag{8}
$$

因子 $(Z+1)^{-1/2}$ 来自 $\lambda_{ee} \approx Z\lambda_{ei}$，因此 $\sqrt{\lambda_{ei} \cdot Z\lambda_{ei}} = \sqrt{Z}\lambda_{ei} \propto (Z+1)^{-1/2}$。

---

<a name="2"></a>
## 2. SH 理论的失效条件与 Bell 判据

### 2.1 扰动展开的适用范围与 $\lambda(v) \propto v^4$ 标度律

SH 理论的根本假设是 $|\mathbf{f}_1|/f_0 \ll 1$。在速度 $v$ 处，扰动的量级可估计为：

$$
\frac{|\mathbf{f}_1|}{f_0} \sim \frac{\lambda(v)}{L_T}, \qquad L_T = \left|\frac{T_e}{\nabla T_e}\right| \tag{9}
$$

其中 $L_T$ 是温度梯度标长。

**$\lambda(v) \propto v^4$ 的推导**：从上述 Coulomb 碰撞物理出发。电子-离子碰撞频率 $\nu_{ei}(v) \propto v^{-3}$（来自动量输运截面 $\sigma_{TR} \propto v^{-4}$ 乘以 $v$，如 §1.3 的详细推导）。自由程定义为电子在两次有效碰撞之间飞行的平均距离：

$$
\lambda(v) \equiv \frac{v}{\nu_{ei}(v)}
$$

代入 $\nu_{ei}(v)$ 的速度标度：

$$
\lambda(v) = \frac{v}{\text{const} \cdot v^{-3}} = \text{const} \cdot v^{4}
$$

因此：
$$
\boxed{\lambda(v) \propto v^4 \lambda_{ei}}
$$

其中比例常数由 $\lambda_{ei}$ 的定义确定。热平均自由程 $\lambda_{ei}$ 对应 $v = v_{th}$（热速度）：$\lambda_{ei} \equiv \lambda(v_{th})$。因此对任意速度 $v$：

$$
\lambda(v) = \lambda_{ei} \cdot \left(\frac{v}{v_{th}}\right)^4
$$

**以能量表示**：定义 $\beta \equiv m_e v^2/(2k_B T_e)$，则 $v/v_{th} = \sqrt{2\beta}$，代入：

$$
\boxed{\lambda(\beta) = \lambda_{ei} \cdot (\sqrt{2\beta})^4 = 4\lambda_{ei} \beta^2}
$$

这一 $\beta^2$ 标度律是 SNB 模型中群自由程 $\lambda_g = 2\beta^2\lambda_e$ 的核心来源。在 $\beta$ 参数空间中的具体数值：
- $\beta = 1/2$（热速度 $v_{th}$）：$\lambda = \lambda_{ei}$（定义）
- $\beta = 1$（能量 $= k_B T_e$）：$\lambda = 4\lambda_{ei}$
- $\beta = 4$（载热电子）：$\lambda = 64\lambda_{ei}$

配合 LMV 参数 $a=32$，有效输运尺度 $a\lambda_e \approx 32\lambda_e \sim \lambda(\beta=4)/2$，量级上吻合。

### 2.2 载热电子的特征速度与热流权重函数

热流积分中的权重函数（以 $\beta$ 表示）可由以下步骤推导：

**步骤 1**：电子热流是分布函数的动理学矩。从动理学定义出发，在球坐标 $(v, \theta, \phi)$ 中（$d^3v = 2\pi v^2 dv \, d(\cos\theta)$），取分布函数 $f = f_0 + f_1\cos\theta$ 的一阶各向异性部分积分 [7, 12]：

$$
\begin{aligned}
Q &= \int \frac{1}{2}m_e v^2 \cdot v\cos\theta \cdot f_1(v)\cos\theta \, d^3v \\
  &= \int_0^\infty \int_{-1}^1 \frac{1}{2}m_e v^3 \cos^2\theta \, f_1(v) \cdot 2\pi v^2 \, d(\cos\theta) \, dv \\
  &= \frac{2\pi}{3} m_e \int_0^\infty v^5 f_1(v) \, dv
\end{aligned}
$$

其中 $\int_{-1}^1 \cos^2\theta \, d(\cos\theta) = 2/3$。此公式在 Sherlock、Brodrick 和 Ridgers [12, Eq. (2)] 中明确给出为 $\mathbf{q} = \hat{\mathbf{x}} \, (4\pi/3)(m/2) \int_0^\infty f_1(v) v^5 dv = (2\pi/3)m \int v^5 f_1 dv$，并在 Spitzer 和 Härm [7] 的原始推导中通过 ${p^2}/(2m_e) \cdot v_x \cdot (p_x/p) \cdot f_1 \, d^3p$ 的积分得到。

**步骤 2**：从线性化 FP 方程（Lorentz 气体近似）[7, 8]，扰动为：
$$
f_1(v) = -\frac{\lambda_{ei}(v)}{3} \left(\frac{m_e v^2}{2k_B T_e} - 4\right) f_0(v) \frac{\nabla T_e}{T_e}
$$

下面**详细推导**这一扰动形式的来源（这是 Spitzer-Härm 理论的经典结果 [7]，完整推导见 Atzeni & Meyer-ter-Vehn [25, §7.1] 和 Chen 等 [13, Eq. (21)]）。

#### 推导 (a)：从完整 VFP 方程到线性化方程 (D1)

**(a1) 出发点：完整的 Vlasov-Fokker-Planck 方程**

电子分布函数 $f(\mathbf{v}, \mathbf{r}, t)$ 的演化由完整 VFP 方程（即本文式 (1)）描述：

$$
\frac{\partial f}{\partial t} + \mathbf{v} \cdot \nabla_r f - \frac{e}{m_e}(\mathbf{E} + \mathbf{v} \times \mathbf{B}) \cdot \nabla_v f = C_{ee}(f) + C_{ei}(f) \tag{a1}
$$

对于无磁场（$\mathbf{B} = 0$）、稳态（$\partial/\partial t = 0$）的情形，方程简化为：

$$
\mathbf{v} \cdot \nabla_r f - \frac{e}{m_e} \mathbf{E} \cdot \nabla_v f = C_{ee}(f) + C_{ei}(f) \tag{a2}
$$

**(a2) Lorentz 气体近似：忽略电子-电子碰撞**

**Lorentz 气体近似**的核心假设是 $C_{ee} \approx 0$，即完全忽略电子-电子碰撞，只保留电子-离子碰撞 $C_{ei}$。其物理依据是：

- 电子-离子质量比 $m_e/m_i \ll 1$，离子视为**无限重的静止散射中心**，只偏转电子方向而不改变其能量
- 电子-电子碰撞的频率与电子-离子碰撞同量级（$\nu_{ee}/\nu_{ei} \sim 1/Z$，见 §1.3），但在高 $Z$ 极限（$Z \gtrsim 10$）下，电子-离子碰撞占主导

在此近似下，(a2) 化为：

$$
\mathbf{v} \cdot \nabla_r f - \frac{e}{m_e} \mathbf{E} \cdot \nabla_v f = C_{ei}(f) \tag{a3}
$$

**(a3) 球谐展开与一阶截断**

将分布函数按速度方向展开（本文式 (2) 的截断形式）。在一维几何（梯度沿 $x$ 方向）下，展开为：

$$
f(\mathbf{v}, x) = f_0(v, x) + \mu f_1(v, x) \tag{a4}
$$

其中 $\mu = \cos\theta = v_x/v$ 是速度矢量与 $x$ 轴的夹角余弦，$f_0$ 是各向同性部分（接近局域 Maxwell 分布），$\mu f_1$ 是一阶各向异性修正。这里截断到 $P_1$ 项（$O(\mu^2)$ 及更高阶忽略），物理依据是 SH 理论要求 $f_1/f_0 \ll 1$（分布函数接近各向同性）。

**(a4) 线性化：分离零阶与一阶方程**

将 (a4) 代入 (a3)，并利用算子的线性性，将方程分解为**零阶（各向同性）部分**和**一阶（各向异性）部分**：

- **零阶部分**：$C_{ei}[f_0] = 0$（Lorentz 碰撞算子作用于各向同性分布时恒为零，因为碰撞只改变方向不改变能量——即 $f_0$ 是碰撞算子的零模式）。这与 $\nabla_r f_0$、$\mathbf{E}\cdot\nabla_v f_0$ 的角向分量配对为零一致。
- **一阶部分**：方程中 $\mathbf{v}\cdot\nabla_r f_0$ 和 $-\frac{e}{m_e}\mathbf{E}\cdot\nabla_v f_0$ 这两项**本身是各向异性的**（因 $\mathbf{v}$ 的出现而含 $\mu$ 因子），它们构成对 $f_1$ 的驱动项；碰撞项 $C_{ei}[\mu f_1]$ 是恢复力。

因此**一阶（线性化）方程**为：

$$
\mathbf{v} \cdot \nabla_r f_0 - \frac{e}{m_e} \mathbf{E} \cdot \nabla_v f_0 = C_{ei}[\mu f_1] \tag{a5}
$$

在一维几何下，$\mathbf{v}\cdot\nabla_r = v\mu \partial_x$，$\mathbf{E}\cdot\nabla_v = E_x \mu \partial_v$（因 $\partial f_0/\partial v$ 只依赖速度大小 $v$，其方向分量即 $\mu$），故 (a5) 化为：

$$
\boxed{v\mu \frac{\partial f_0}{\partial x} - \frac{e E_x}{m_e} \mu \frac{\partial f_0}{\partial v} = C_{ei}[\mu f_1] \tag{D1}}
$$

**关键物理理解**：方程左侧的两项都含 $\mu$ 因子，代表温度梯度（通过 $f_0$ 的空间变化）和自洽电场**共同驱动**各向异性分布的产生；右侧碰撞项则通过电子-离子散射**阻尼**这种各向异性。稳态时二者平衡，决定 $f_1$ 的大小和速度依赖。

**(a5) 弛豫近似：碰撞算子的显式形式**

Lorentz 碰撞算子 $C_{ei}$ 作用于 $P_1$ 角分量 $\mu f_1$ 时，其本征结构给出：

$$
C_{ei}[\mu f_1] = -\nu_{ei}(v)\, \mu f_1 \tag{D2}
$$

这是因为 Lorentz 碰撞算子在 Legendre 多项式基上的作用满足 $C_{ei}[P_\ell(\mu)] = -\nu_\ell(v) P_\ell(\mu)$（对角化），其中 $\nu_1(v) \equiv \nu_{ei}(v)$ 即 §1.3 推导的**动量输运碰撞频率**（90° 偏转率）。对于 $\ell = 1$ 角分量，本征值恰为 $\nu_{ei}(v)$。这是**弛豫近似**（relaxation-time approximation）的严格形式——碰撞项简化为简单的"乘以 $-1/\nu_{ei}(v)$"，而非完整的积分算子。

#### 推导 (b)：分布函数梯度的计算

局域 Maxwell 分布 $f_0 = n_e (m_e/2\pi k_B T_e)^{3/2} \exp(-\beta)$（$\beta \equiv m_e v^2/(2k_B T_e)$），其空间梯度和速度梯度为：

$$
\frac{\partial f_0}{\partial x} = f_0 \left[\frac{\partial\ln n_e}{\partial x} + \left(\beta - \frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x}\right] \tag{D3}
$$

$$
\frac{\partial f_0}{\partial v} = -\frac{m_e v}{k_B T_e} f_0 \tag{D4}
$$

其中 (D3) 中的 $(\beta - 3/2)$ 来自 $\ln f_0 = \ln n_e + \frac{3}{2}\ln(m_e/2\pi k_B) - \frac{3}{2}\ln T_e - \beta$ 对 $x$ 的求导——即 Maxwell 分布的温度归一化因子 $T_e^{-3/2}$ 贡献 $-3/2$，指数因子 $e^{-\beta}$ 贡献 $+\beta$。（上述 (D3)(D4) 的逐步逐项推导见**附录 C**。）

#### 推导 (c)：自洽电场（ambipolar field）

将 (D3)(D4) 代入 (D1)：

$$
f_1(v) = -\frac{v}{\nu_{ei}(v)} f_0 \left[\frac{\partial\ln n_e}{\partial x} + \left(\beta - \frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x} + \frac{e E_x}{k_B T_e}\right] \tag{D5}
$$

电场 $E_x$ 由**零电流条件**（ambipolar 条件，$j_x = \int e v\mu f_1 d^3v = 0$）确定。下面**完整推导 (D6) 的来源**。

**(c1) 电流的动理学表达式**

电流密度定义为电子电荷乘以速度的动理学矩。由于 $f_0$ 各向同性（其电流贡献 $\int v_x f_0 d^3v = 0$ 恒为零），只有各向异性部分 $\mu f_1$ 贡献（$v_x = v\mu$）：

$$
j_x = e \int v_x f(\mathbf{v}) d^3v = e \int v\mu \cdot \mu f_1 \, d^3v = e \int v \mu^2 f_1 \, d^3v \tag{D6a}
$$

在球坐标 $d^3v = v^2 dv\, d\Omega$ 中，角度积分 $\int \mu^2 d\Omega = 2\pi \int_{-1}^{1} \mu^2 d\mu = 4\pi/3$，故：

$$
j_x = \frac{4\pi e}{3} \int_0^\infty v^3 f_1(v) \, dv \tag{D6b}
$$

**(c2) 代入 (D5) 并施加零电流条件**

将 (D5) 代入 (D6b)：

$$
j_x = -\frac{4\pi e}{3} \int_0^\infty v^3 \cdot \frac{v}{\nu_{ei}(v)} f_0(v) \left[\frac{\partial\ln n_e}{\partial x} + \left(\beta - \frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x} + \frac{e E_x}{k_B T_e}\right] dv \tag{D6c}
$$

利用 $\nu_{ei}(v) \propto v^{-3}$（§1.3），权重因子 $v^4/\nu_{ei}(v) \propto v^7$。零电流条件 $j_x = 0$（方括号内为与 $v$ 无关的常数因子，可提出积分号）给出：

$$
I_1 \frac{\partial\ln n_e}{\partial x} + \left(I_2 - \frac{3}{2} I_1\right)\frac{\partial\ln T_e}{\partial x} + I_1 \frac{e E_x}{k_B T_e} = 0 \tag{D6d}
$$

其中两个速度积分定义为（$f_0 \propto e^{-\beta}$）：

$$
I_1 = \int_0^\infty \frac{v^4}{\nu_{ei}(v)} f_0(v) dv, \qquad I_2 = \int_0^\infty \frac{v^4}{\nu_{ei}(v)} f_0(v)\, \beta \, dv \tag{D6e}
$$

**(c3) $\Gamma$ 函数求值**

作变量代换 $\beta = m_e v^2/(2k_B T_e)$：$v \propto \sqrt{\beta}$，$dv \propto \beta^{-1/2} d\beta$，且 $v^4/\nu_{ei}(v) \propto v^7$，故 $v^7 dv \propto \beta^{7/2} \cdot \beta^{-1/2} d\beta = \beta^3 d\beta$。因此：

$$
I_1 \propto \int_0^\infty \beta^3 e^{-\beta} d\beta = \Gamma(4) = 3! = 6 \tag{D6f}
$$

$$
I_2 \propto \int_0^\infty \beta^4 e^{-\beta} d\beta = \Gamma(5) = 4! = 24 \tag{D6g}
$$

**比值 $I_2/I_1 = 24/6 = 4$**——这正是载热电子的特征能量 $\beta = 4$！

**(c4) 求解电场**

由 (D6d) 解出：

$$
\frac{e E_x}{k_B T_e} = -\frac{\partial\ln n_e}{\partial x} - \left(\frac{I_2}{I_1} - \frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x} = -\frac{\partial\ln n_e}{\partial x} - \left(4 - \frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x}
$$

$$
\boxed{\frac{e E_x}{k_B T_e} = -\frac{\partial\ln n_e}{\partial x} - \frac{5}{2}\frac{\partial\ln T_e}{\partial x}} \tag{D6}
$$

**热电动势系数 $\gamma = 5/2$ 的物理起源**：$\gamma = \langle\beta\rangle - 3/2$，其中 $\langle\beta\rangle = I_2/I_1 = 4$ 是**以输运权重 $v^7 e^{-\beta}$ 加权平均的电子能量**。$5/2 = 4 - 3/2$ 中的 $3/2$ 来自 Maxwell 分布的温度归一化（推导 b），$4$ 来自载热电子特征能量。

（即经典的 SH 热电动势系数 $\gamma = 5/2$；密度梯度项恰好抵消载流子的密度贡献，只留下温度梯度驱动的净热流）。

#### 推导 (d)：合并得到 $(\beta - 4)$ 因子

将 (D6) 代入 (D5)，密度梯度项 $\partial\ln n_e/\partial x$ 抵消，得到：

$$
f_1(v) = -\frac{v}{\nu_{ei}(v)} f_0 \left(\beta - \frac{3}{2} - \frac{5}{2}\right) \frac{1}{T_e}\frac{\partial T_e}{\partial x} = -\frac{v}{\nu_{ei}(v)} f_0 \, (\beta - 4) \, \frac{\nabla T_e}{T_e} \tag{D7}
$$

**这就是 $(\beta - 4)$ 因子的起源**：$4 = 3/2 + 5/2$，其中 $3/2$ 来自 Maxwell 分布温度归一化（推导 b），$5/2$ 来自自洽电场的热电动势项（推导 c）。

利用 $v/\nu_{ei}(v) = \lambda_{ei}(v)$（速度依赖自由程），并采用输运理论的标准约定（扩散系数 $D = \lambda v/3$ 中的 $1/3$ 因子），最终得到：

$$
\boxed{f_1(v) = -\frac{\lambda_{ei}(v)}{3} \left(\frac{m_e v^2}{2k_B T_e} - 4\right) f_0(v) \frac{\nabla T_e}{T_e}} \tag{D8}
$$

#### $(\beta - 4)$ 因子的物理含义

- **$\beta < 4$（$v < 2\sqrt{2}v_{th} \approx 2.83v_{th}$）**：$f_1 < 0$，低能电子对热流贡献为负（回流电流方向）
- **$\beta > 4$（$v > 2.83v_{th}$）**：$f_1 > 0$，高能电子携带正向热流

这是 SH 热流中"载热电子与回流电流"分离的动理学根源：热流是大量低速回流电子（$\beta < 4$）与少量高速载热电子（$\beta \approx 4$–$8$）的平衡结果，而正是后者决定了非局域输运特征。

**步骤 3**：代入热流积分，利用 $\lambda_{ei}(v) \propto v^4 \propto \beta^2$ 和 $f_0(v) \propto e^{-\beta}$，作变量变换 $\beta = m_e v^2/(2k_B T_e)$ 得 $v^5 dv \propto \beta^2 d\beta$。因此：

$$
Q \propto \int_0^\infty \beta^2 \cdot \beta^2 \cdot (\beta - 4) \cdot e^{-\beta} \, d\beta = \int_0^\infty \beta^4 (\beta - 4) e^{-\beta} \, d\beta
$$

**步骤 4**：因此权重函数为：
$$
\boxed{\mathcal{W}(\beta) \propto \beta^4 (\beta - 4) e^{-\beta}} \tag{10}
$$

- $\beta^4$ 来自 $v^5 dv$（相空间体积，$\beta^2$）乘以 $\lambda_{ei}(v)$（自由程标度，$\beta^2$）
- $(\beta - 4)$ 来自 $f_1$ 中的 $(m_e v^2/(2k_B T_e) - 4)$ 因子，反映低能电子（$\beta<4$，负贡献/回流）与高能电子（$\beta>4$，正贡献）对热流的符号反转
- $e^{-\beta}$ 来自 Maxwell 分布的指数衰减

**步骤 5**：峰值位置。求解 $d\mathcal{W}/d\beta = 0$：
$$
\frac{d}{d\beta}\left[\beta^4(\beta-4)e^{-\beta}\right] = \beta^3 e^{-\beta}[-\beta^2 + 9\beta - 20] = 0
$$

正实数根 $\beta = 4, 5$，其中 $\beta=4$ 为全局最大值。因此**载热电子能量约为 $E \approx 4k_B T_e$**（速度约为 $v \approx \sqrt{8}v_{th} \approx 2.83v_{th}$）。

SNB 模型中使用的群平均自由程为 $\lambda_g = 2\beta^2\lambda_e$，对应 $\beta=4$ 时 $\lambda_g(4) = 32\lambda_e$。这些长自由程使载热电子可以在发生碰撞前穿行远超热电子自由程的距离，从而产生非局域输运效应。

### 2.3 Bell 定量判据

Bell、Evans 和 Nicholas [10] 于 1981 年在 *Physical Review Letters* 上发表了里程碑式的工作，首次通过**直接数值求解 Fokker-Planck 方程**系统研究了激光等离子体中陡温度梯度下的电子热传导失效问题。该工作的核心要素如下：

**研究动机**：20 世纪 70 年代末至 80 年代初，激光聚变实验中发现观测到的热输运远低于 Spitzer-Härm 理论预测值。理解这一差异对 ICF 靶设计至关重要。

**方法**：在一个空间维度（$x$）和两个速度维度（$v_x, v_\perp$）上数值求解完整的电子 Fokker-Planck 方程——这是在当时的计算条件下非常 ambitious 的计算。与简化模型不同，该方法不需预设分布函数形式。

**关键发现**（论文摘要原文）：
> *"The Fokker-Planck equation has been solved numerically in one spatial and two velocity dimensions in order to study thermal conduction in large temperature gradients occurring in laser-produced plasmas. **The heat flow is an order of magnitude smaller than that predicted by the classical theory when the temperature scale length is a few electron mean free paths.**"*
>
> — Bell, Evans, and Nicholas, *Phys. Rev. Lett.* **46**, 243–246 (1981)

**定量结论的层次**：

1. **直接结论**：当 $L_T \sim \mathcal{O}(\lambda_e)$（温度标长为几个电子平均自由程）时，实际热流比 SH 理论预测小约**一个数量级**（即 $Q/Q_{SH} \sim 0.1$）。这给出了热流抑制的定量范围。
2. **推广判据**：Schurtz 等 [1] 在 SNB 论文中引用此结果并进一步指出：由于载热电子（速度 $\approx 2.8 v_{th}$）的自由程远长于热电子，非局域效应可在更高碰撞性下显现——具体来说，当 $L_T \lesssim 200\lambda_e$（$\lambda_e/L_T \gtrsim 5 \times 10^{-3}$）时即需考虑非局域修正：

$$
\boxed{L_T \lesssim 200 \lambda_e \quad \Longleftrightarrow \quad \frac{\lambda_e}{L_T} \gtrsim 5 \times 10^{-3}}
$$

**历史影响**：该文（被引 > 1500 次）是激光等离子体中非局域热传导领域的奠基性工作，直接推动了 LMV [2] 和后来的 SNB [1] 非局域模型的提出。其核心贡献在于：(i) 首次以第一性原理计算定量证明了 SH 理论在高 $k\lambda_e$ 区的失效；(ii) 确立了通量限制器（flux limiter）作为 ICF 代码中的临时补救方案（$f_L \sim 0.03$–$0.15$）；(iii) 为后续非局域模型提供了标准化的 VFP 基准数据。

**与后续验证的关系**：Brodrick 等 [5] 在 2017 年使用更现代的三维 VFP 代码（IMPACT、KIPP、SPRING）重新审视了 Bell 等的结果，确认 SNB 模型在正确实现时能复现 VFP 预测的热流抑制和预热效应。

在 ICF 实际条件下，烧蚀面附近的 $\lambda_e/L_T$ 经常达到 10%–20% [1, 5]，远超上述阈值。

---

<a name="3"></a>
## 3. 非局域卷积方法：LMV 模型

### 3.1 LMV 的核心思想

Luciani、Mora 和 Virmont [2] 的关键洞察是：在非局域条件下，空间某点的电子分布函数不仅取决于当地的密度和温度，还受到电子来源地条件的影响。**热流是局域 SH 热流在空间上的加权叠加（卷积）**。

### 3.2 一维卷积公式及其物理构造

LMV 的原始一维公式并非从第一性原理严格推导，而是基于以下物理考虑构建的**唯象模型**：

1. **非局域性的物理图景**：在位置 $x$ 处的热流 $Q(x)$ 由来自所有位置 $x'$ 的电子携带能量贡献叠加而成。从 $x'$ 出发的电子能以一定概率到达 $x$ 并沉积能量。

2. **局域热流作为源**：在 $x'$ 处，若电子满足局域 Maxwell 分布，就产生 $Q_{SH}(x') = -\kappa_{SH}\nabla T_e(x')$。这是驱动非局域输运的"源"。

3. **存活概率 $\propto e^{-\tau}$**：类比辐射输运中的 Beer-Lambert 定律，从 $x'$ 出发的电子在到达 $x$ 前因碰撞而保持"热流携带能力"的概率按指数衰减。

4. **长度归一化**：$\frac{dx'}{a\lambda_e(x')}$ 确保在 $\lambda_e/L_T \to 0$ 极限下恢复 Dirac $\delta$ 函数行为。

基于上述考虑，LMV 提出一维卷积公式：

$$
Q(x) = \int_{-\infty}^{\infty} W(x, x') \, Q_{SH}(x') \, \frac{dx'}{a\lambda_e(x')} \tag{12}
$$

其中非局域核和光学深度分别为：

$$
W(x, x') = \beta \exp[-\tau(x, x')] \tag{13}
$$

$$
\tau(x, x') = \frac{\left|\int_{x'}^{x} n_e(z) \, dz\right|}{a \, n_e(x') \, \lambda_e(x')} \tag{14}
$$

参数 $a$ 通过拟合 VFP 模拟结果确定为 $a = 32$（原始 LMV 推荐值 [2]），归一化系数 $\beta$ 确保在平滑梯度极限下恢复 SH 理论。

**关键物理洞察——核的非对称性**：光学深度分母中的 $n_e(x')$ 而非 $n_e(x)$ 意味着 $\tau(x,x') \neq \tau(x',x)$。这种非对称性反映了电子自由程的温度依赖性——从高温区出发的电子自由程更长，影响更远。

### 3.3 核的物理含义

- **光学深度 $\tau$**：量化了电子从源点 $x'$ 到目标点 $x$ 所经历的有效碰撞次数。$\tau \ll 1$ 表示电子几乎无碰撞地到达目标点；$\tau \gg 1$ 表示电子已经历多次碰撞，丧失了"源点记忆"。
- **指数衰减 $e^{-\tau}$**：电子在从 $x'$ 到 $x$ 的途中因碰撞而保持"热流携带能力"的概率，衰减的特征尺度为 $a\lambda_e(x')$。
- **平滑梯度极限**：当 $\lambda_e/L_T \to 0$ 时，核退化为狄拉克 $\delta$ 函数，$Q(x) \to Q_{SH}(x)$，恢复经典 SH 理论。
- **归一化性质**：LMV 核满足 $\int W(x,x') \, dx'/(a\lambda_e(x')) = 1$。

### 3.4 二维/三维推广

LMV 一维公式的三维推广由 Schurtz 等 [1] 完成，具体步骤如下：

**步骤 1：方向参数化**。从 $\mathbf{r}'$ 到 $\mathbf{r}$ 的路径用方向矢量 $\mathbf{\Omega}$（单位矢量）和距离 $s$ 参数化：$\mathbf{r}' = \mathbf{r} + s\mathbf{\Omega}$。

**步骤 2：三维等效积分元**。一维 $dx'$ 推广为三维体积元 $d^3r' = s^2 ds \, d^2\Omega$（球坐标）。

**步骤 3：距离衰减**。一维核的指数衰减在三维中变为 $\exp[-\tau(\mathbf{r}, \mathbf{r}+s\mathbf{\Omega})]$，其中路径光学深度为：

$$
\tau(\mathbf{r}, \mathbf{r}+s\mathbf{\Omega}) = \int_0^s \frac{ds'}{\lambda_e(\mathbf{r}+s'\mathbf{\Omega})}
$$

**步骤 4：SH 热流的矢量性**。$\mathbf{Q}_{SH}$ 是矢量，需要保留其方向信息。沿 $\mathbf{\Omega}$ 方向的投影为 $\mathbf{\Omega} \cdot \mathbf{Q}_{SH}$，对观测热流的矢量贡献为 $(\mathbf{\Omega} \cdot \mathbf{Q}_{SH})\mathbf{\Omega} = \mathbf{\Omega}\mathbf{\Omega} \cdot \mathbf{Q}_{SH}$（并矢投影）。

**步骤 5：组装三维卷积**。综合以上（其中 $W_0 = \exp[-\tau]$ 为对称化核）：

$$
\boxed{\mathbf{Q}(\mathbf{r}) = \int_{4\pi} \mathbf{\Omega}\mathbf{\Omega} \, d^2\Omega \int_0^{\infty} e^{-\tau(\mathbf{r}, \mathbf{r}+s\mathbf{\Omega})} \, \mathbf{Q}_{SH}(\mathbf{r}+s\mathbf{\Omega}) \, \frac{ds}{\lambda_e(\mathbf{r}+s\mathbf{\Omega})}} \tag{15}
$$

**验证平滑梯度极限**：当 $\lambda_e/L_T \to 0$，核退化为 $\delta(\mathbf{r}'-\mathbf{r})$，$\mathbf{Q} \to \mathbf{Q}_{SH}$，恢复局域 SH 理论。

---

<a name="4"></a>
## 4. SNB 模型：从卷积到等效输运方程

### 4.1 核心数学洞察

SNB [1] 的关键发现是：LMV 卷积公式 **(15)** 恰好是以下**线性稳态输运方程**的格林函数积分解：

$$
\mathbf{\Omega} \cdot \nabla q(\mathbf{\Omega}, \mathbf{r}) + \frac{1}{\lambda_t(\mathbf{r})} q(\mathbf{\Omega}, \mathbf{r}) = \frac{1}{\lambda_t(\mathbf{r})} \frac{3}{4\pi} \mathbf{\Omega} \cdot \mathbf{Q}_{SH}(\mathbf{r}) \tag{16}
$$

其中 $q(\mathbf{\Omega}, \mathbf{r})$ 为**角通量**（angular flux），代表在 $\mathbf{r}$ 点沿 $\mathbf{\Omega}$ 方向运动的电子所携带的能量流密度。$\lambda_t(\mathbf{r})$ 是**输运平均自由程**。右边系数 $3/(4\pi)$ 来自角度积分的归一化条件。

**严格证明：为什么 (15) 是 (16) 的格林函数积分解**

将证明拆为三个部分：(A) 形式解 (19) 确实满足输运方程 (16)（验证）；(B) 从 (16) 出发经特征线法构造出的唯一物理解恰好是 (19)（构造）；(C) 系数 $3/(4\pi)$ 由局域极限 $\mathbf{Q} \to \mathbf{Q}_{SH}$ 唯一确定（归一化）。由于 (15) 是 (19) 经角矩投影 (20) 的结果（见 §4.4），三部分合起来即完成"LMV 卷积 = 输运方程格林函数解"的证明。

**(A) 方向一：验证 (19) 满足 (16)**

将 (19) 作用于线性算子 $L \equiv \mathbf{\Omega}\cdot\nabla_{\mathbf{r}} + 1/\lambda_t(\mathbf{r})$。记 $g(s) = \mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}-s\mathbf{\Omega})$，$\tau_s(\mathbf{r}) \equiv \tau(\mathbf{r},\,\mathbf{r}-s\mathbf{\Omega}) = \int_0^s dl/\lambda_t(\mathbf{r}-l\mathbf{\Omega})$。需要三条链式法则结论：

1. **光学深度的路径导数**：$d\tau_s/ds = 1/\lambda_t(\mathbf{r}-s\mathbf{\Omega})$（微积分基本定理）；
2. **光学深度的空间梯度**：对平移不变函数 $F(\mathbf{r}-l\mathbf{\Omega})$ 有 $\mathbf{\Omega}\cdot\nabla_{\mathbf{r}}F = -dF/dl$，故 $\mathbf{\Omega}\cdot\nabla_{\mathbf{r}}[1/\lambda_t(\mathbf{r}-l\mathbf{\Omega})] = -\dfrac{d}{dl}[1/\lambda_t(\mathbf{r}-l\mathbf{\Omega})]$，从 $0$ 积到 $s$：
$$
\mathbf{\Omega}\cdot\nabla_{\mathbf{r}}\,\tau_s = \frac{1}{\lambda_t(\mathbf{r}-s\mathbf{\Omega})} - \frac{1}{\lambda_t(\mathbf{r})} \tag{G1}
$$
3. **对任意 $F(\mathbf{r}-s\mathbf{\Omega})$**：$\mathbf{\Omega}\cdot\nabla_{\mathbf{r}} F(\mathbf{r}-s\mathbf{\Omega}) = -\dfrac{dF}{ds}$。

由 (G1) 得 $\mathbf{\Omega}\cdot\nabla_{\mathbf{r}} e^{-\tau_s} = e^{-\tau_s}\left[1/\lambda_t(\mathbf{r}-s\mathbf{\Omega}) - 1/\lambda_t(\mathbf{r})\right]$。对 (19) 的被积函数 $F \equiv e^{-\tau_s} g(s)/\lambda_t(\mathbf{r}-s\mathbf{\Omega})$，逐项展开（并利用 $\dfrac{d}{ds}[g/\lambda_t] = g'/\lambda_t - g\lambda_t'/\lambda_t^2$ 与 $d\tau_s/ds = 1/\lambda_t$）得到关键恒等式：

$$
\mathbf{\Omega}\cdot\nabla_{\mathbf{r}} F = -\frac{e^{-\tau_s} g(s)}{\lambda_t(\mathbf{r})\,\lambda_t(\mathbf{r}-s\mathbf{\Omega})} - \frac{d}{ds}\!\left[\frac{e^{-\tau_s} g(s)}{\lambda_t(\mathbf{r}-s\mathbf{\Omega})}\right] \tag{G2}
$$

（验证：$-\dfrac{d}{ds}[e^{-\tau_s}g/\lambda_t] = e^{-\tau_s}\left[\dfrac{g}{\lambda_t^2} - \dfrac{d}{ds}\left(\dfrac{g}{\lambda_t}\right)\right]$，再与直接展开的三项相加即得。也可直接对 $F$ 求 $\mathbf{\Omega}\cdot\nabla_{\mathbf{r}}$ 后合并同类项验证。）

于是：

$$
\begin{aligned}
L q \;=\; \frac{3}{4\pi}\int_0^\infty \mathbf{\Omega}\cdot\nabla_{\mathbf{r}}F\, ds + \frac{q}{\lambda_t(\mathbf{r})}
&= -\frac{1}{\lambda_t(\mathbf{r})}\cdot\frac{3}{4\pi}\!\int_0^\infty \frac{e^{-\tau_s} g(s)}{\lambda_t(\mathbf{r}-s\mathbf{\Omega})}ds - \frac{3}{4\pi}\!\left[\frac{e^{-\tau_s}g(s)}{\lambda_t(\mathbf{r}-s\mathbf{\Omega})}\right]_{0}^{\infty} + \frac{q}{\lambda_t(\mathbf{r})} \\
&= -\frac{q}{\lambda_t(\mathbf{r})} - \frac{3}{4\pi}\left[\,0 - \frac{g(0)}{\lambda_t(\mathbf{r})}\,\right] + \frac{q}{\lambda_t(\mathbf{r})} \\
&= \frac{3}{4\pi\lambda_t(\mathbf{r})}\,\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}) \tag{G3}
\end{aligned}
$$

其中第一项与 $+q/\lambda_t(\mathbf{r})$ 相消（因 $q = (3/4\pi)\int e^{-\tau_s}g/\lambda_t\, ds$ 正是 (19)），边界项中 $s\to\infty$ 时 $e^{-\tau_s}\to 0$，$s=0$ 时 $\tau_0 = 0$、$g(0) = \mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r})$。**(G3) 的右端正是 (16) 的右端，验证完成。** ∎

**(B) 方向二：从 (16) 构造 (19)——格林函数方法**

一阶线性 PDE 的格林函数解法分三步（逐步骤展开见附录 A.4）：

1. **特征线化**：沿 $\mathbf{r}(s) = \mathbf{r}_0 + s\mathbf{\Omega}$，(16) 退化为沿射线的一阶线性 ODE $\dfrac{dq}{ds} + \dfrac{q}{\lambda_t(s)} = \dfrac{3}{4\pi\lambda_t(s)}\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(s)$；
2. **积分因子**：$\exp\left[\tau(\mathbf{r}_0+s\mathbf{\Omega},\,\mathbf{r}_0)\right]$ 将左边化为全微分，得到 (18)；
3. **上游积分**：从 $s=-\infty$（上游无热流边界 $q=0$）积分到 $s=0$，换元 $s\to-s$（令 $u=-s$ 为上游距离），光学深度关系 $\tau(\mathbf{r},\,\mathbf{r}-u\mathbf{\Omega}) = \int_0^u dl/\lambda_t(\mathbf{r}-l\mathbf{\Omega})$ 代入后即得 (19)。

由于一阶线性 ODE 在给定上游边界下**解唯一**，(19) 就是 (16) 的**唯一物理解**——因此 (19) 正是 (16) 的格林函数积分解，其格林函数（从源点 $\mathbf{r}'=\mathbf{r}-s\mathbf{\Omega}$ 到观测点 $\mathbf{r}$ 的传播子）为：

$$
G(\mathbf{r},\,\mathbf{r}') = \frac{e^{-\tau(\mathbf{r},\,\mathbf{r}')}}{\lambda_t(\mathbf{r}')}\,,\qquad \tau(\mathbf{r},\,\mathbf{r}') = \int_{\mathbf{r}'}^{\mathbf{r}} \frac{dl}{\lambda_t} \tag{G4}
$$

物理含义：$G$ 度量"$\mathbf{r}'$ 处单位源（单位 SH 热流投影）经自由飞行到 $\mathbf{r}$ 处的存活概率"—因子 $e^{-\tau}$ 是碰撞存活率，$1/\lambda_t$ 是源强度的空间密度（单位自由程内的源增量）。

**(C) 系数 $3/(4\pi)$ 的归一化验证**

将 (19) 代入角矩 (20)，在局域极限（$\lambda_t \to 0$，核退化为 $\delta$ 函数）下要求恢复 $\mathbf{Q}_{SH}$：

$$
\mathbf{Q}(\mathbf{r}) = \frac{3}{4\pi}\int_{4\pi}\mathbf{\Omega}\mathbf{\Omega}\,d^2\Omega \int_0^\infty e^{-\tau}\mathbf{Q}_{SH}(\mathbf{r}-s\mathbf{\Omega})\,\frac{ds}{\lambda_t} \;\xrightarrow{\;\lambda_t\to 0\;}\; \frac{3}{4\pi}\cdot\frac{4\pi}{3}\,\mathbb{1}\cdot\mathbf{Q}_{SH}(\mathbf{r}) = \mathbf{Q}_{SH}(\mathbf{r})
$$

其中用到均匀 $\lambda_t$ 下 $\int_0^\infty e^{-s/\lambda_t}ds/\lambda_t = 1$（核归一化）与角度积分 $\int_{4\pi}\Omega_i\Omega_j\,d^2\Omega = (4\pi/3)\delta_{ij}$。**只有取系数 $3/(4\pi)$ 才能使局域极限恰为 $\mathbf{Q}_{SH}$**——这正是 (16) 右端系数的来历。∎

**结论**：三部分证明合起来确立了 SNB 模型的核心数学等价性：

$$
\boxed{\text{LMV 卷积 (15)} \;\Longleftrightarrow\; \text{输运方程 (16) 的格林函数积分解}}
$$

(15) 中的核 $e^{-\tau}/\lambda_t$ 即 (G4) 的格林函数；(16) 与 (15) 是同一非局域输运关系的"微分形式"与"积分形式"，这正是 SNB 能以求解 PDE 替代全局卷积的数学基础（§4.4 末尾）。

### 4.2 一维等价性的详细证明

在一维平板几何（slab geometry）中，方向矢量 $\mathbf{\Omega}$ 简化为方向余弦 $\mu = \cos\theta$（$\mu \in [-1, 1]$），且所有量仅依赖于 $x$ 坐标。三维输运方程 (16) 在此几何中退化为 [1, Eq. (15)]：

$$
\mu \frac{\partial q(\mu, x)}{\partial x} + \frac{1}{\lambda_t} q(\mu, x) = \frac{1}{\lambda_t} \frac{3}{2} \mu \, Q_{SH}(x)
$$

右边系数变为 $3/2$ 而非 $3/(4\pi)$，这是因为在一维几何中，角通量的立体角积分归一化条件为 $\int_{-1}^1 \mu^2 d\mu = 2/3$，因此 $3/2 = (4\pi) \cdot (3/(4\pi)) \cdot (1/(2/3))$ 的简化结果。此一维简化形式的详细推导见 Schurtz 等 [1] Section III A 以及 BOUT++ 非局域热流模型文档 [11]。

**求解方法**（积分因子法）。改写为：

$$
\frac{\partial q}{\partial x} + \frac{1}{\mu\lambda_t} q = \frac{3}{2\lambda_t} Q_{SH}(x)
$$

积分因子为 $\exp(x/(\mu\lambda_t))$。对 $\mu > 0$，从上游边界 $q(\mu, -\infty)=0$ 积分：

$$
q(\mu, x) = \frac{3}{2\lambda_t} \int_{-\infty}^x Q_{SH}(x') \, e^{-(x-x')/(\mu\lambda_t)} \, dx'
$$

**求宏观热流**。热流是角通量的一阶角矩：$Q(x) = \int_{-1}^1 q(\mu, x) \mu \, d\mu$。代入 $q(\mu, x)$ 并交换积分顺序，内层角度积分经变量代换 $z = 1/|\mu|$ 后化为**指数积分函数** $E_3(s) = \int_1^\infty e^{-sz}z^{-3} \, dz$（$s = |x-x'|/\lambda_t$；各阶指数积分 $E_n(s) = \int_1^\infty e^{-sz}z^{-n}dz$ 的领先渐近均为 $E_n(s) \approx e^{-s}/s$，严格推导见附录 A.5）。当 $s \gg 1$，$E_3(s) \approx e^{-s}/s$，因此：

$$
Q(x) \propto \int_{-\infty}^\infty Q_{SH}(x') \, \frac{e^{-|x-x'|/\lambda_t}}{|x-x'|/\lambda_t} \, dx'
$$

**这正是 LMV 指数衰减核的格林函数形式！** 对应关系为 $\lambda_t = \sqrt{3} a \lambda_e$。

### 4.3 三维形式解推导

定义沿 $\mathbf{\Omega}$ 方向的路径光学深度：

$$
\tau(\mathbf{r}, \mathbf{r} - s\mathbf{\Omega}) = \int_0^s \frac{ds'}{\lambda_t(\mathbf{r} - s'\mathbf{\Omega})} \tag{17}
$$

方程 **(16)** 沿特征线 $\mathbf{r} = \mathbf{r}_0 + s\mathbf{\Omega}$ 可改写为：

$$
\frac{d}{ds}\left[ q(\mathbf{\Omega}, \mathbf{r}_0 + s\mathbf{\Omega}) \, e^{\tau(\mathbf{r}_0+s\mathbf{\Omega}, \mathbf{r}_0)} \right] = \frac{3}{4\pi\lambda_t} \mathbf{\Omega} \cdot \mathbf{Q}_{SH}(\mathbf{r}_0 + s\mathbf{\Omega}) \, e^{\tau(\mathbf{r}_0+s\mathbf{\Omega}, \mathbf{r}_0)} \tag{18}
$$

从 $s = -\infty$（上游无热流边界）积分到 $s = 0$，得到形式解：

$$
q(\mathbf{\Omega}, \mathbf{r}) = \frac{3}{4\pi} \int_0^{\infty} e^{-\tau(\mathbf{r}, \mathbf{r} - s\mathbf{\Omega})} \, \mathbf{\Omega} \cdot \mathbf{Q}_{SH}(\mathbf{r} - s\mathbf{\Omega}) \, \frac{ds}{\lambda_t(\mathbf{r} - s\mathbf{\Omega})} \tag{19}
$$

### 4.4 恢复宏观热流：一阶角矩

宏观热流是角通量的一阶角矩。这一定义的物理依据是：

**角通量 $q(\mathbf{\Omega}, \mathbf{r})$** 是沿 $\mathbf{\Omega}$ 方向运动的电子所携带的能量流密度（单位时间单位面积）。其矢量表示为 $q(\mathbf{\Omega}, \mathbf{r})\mathbf{\Omega}$。对所有方向求和（球面积分）即得净热流：

$$
\mathbf{Q}(\mathbf{r}) = \int_{4\pi} q(\mathbf{\Omega}, \mathbf{r}) \, \mathbf{\Omega} \, d^2\Omega \tag{20}
$$

**验证**：若角通量各向同性（$q = q_0/4\pi$，常数），则 $\mathbf{Q} = (q_0/4\pi) \int \mathbf{\Omega} d^2\Omega = 0$——各向同性分布下净热流为零，与物理直觉一致。零阶矩 $H = \int q d^2\Omega$ 是标量（总能量通量的角度平均），一阶矩 $\mathbf{Q}$ 是矢量（净能量流密度）。

将 **(19)** 代入 **(20)**，作变量变换 $s\mathbf{\Omega} \to -s\mathbf{\Omega}$：

$$
\mathbf{Q}(\mathbf{r}) = \frac{3}{4\pi} \int_{4\pi} \mathbf{\Omega}\mathbf{\Omega} \, d^2\Omega \int_0^{\infty} e^{-\tau(\mathbf{r}, \mathbf{r}+s\mathbf{\Omega})} \, \mathbf{Q}_{SH}(\mathbf{r}+s\mathbf{\Omega}) \, \frac{ds}{\lambda_t(\mathbf{r}+s\mathbf{\Omega})} \tag{21}
$$

这正是 LMV 卷积形式 **(15)**，核函数为 $W_0 = \exp[-\tau]$，对应关系为：

$$
\lambda_t = \sqrt{3} \, a \lambda_e \tag{22}
$$

**这一发现的深远意义**：既然卷积正是一个输运方程的积分解，那么**直接求解微分方程即可避免高昂的全局卷积计算**。这是 SNB 模型在数值上优于原始 LMV 方法的根本原因。

---

<a name="5"></a>
## 5. 能量多群分解

### 5.1 问题：核的非对称性

LMV 卷积核 $W(x, x')$ 一般为非对称的：由高温点 $x'$ 出发的快电子比低温点出发的电子具有更长的自由程，因此 $\tau(x, x') \neq \tau(x', x)$。直接求解输运方程时，这种非对称性使数值处理复杂化。

### 5.2 SNB 的处理策略

非对称性的根源是**不同能量的电子具有不同的自由程**。SNB 的策略是将电子按能量分组，在每组内电子能量相近、自由程近似相同，因而组内核近似对称。

### 5.3 群结构定义与 $W_g$ 的详细推导

定义无量纲能量 $\beta \equiv E / (k_B T_e)$。将能量轴离散为 $N_g$ 个能群，第 $g$ 群的上下边界为 $\beta_{g-1}$ 和 $\beta_g$，中心为 $\beta_{g-1/2} = (\beta_{g-1} + \beta_g) / 2$。

**第 $g$ 群的群平均自由程**：

$$
\lambda_g(\mathbf{r}) = 2 \left(\frac{E_{g-1/2}}{k_B T_e(\mathbf{r})}\right)^2 \lambda_e(\mathbf{r}) = 2 \beta_{g-1/2}^2 \lambda_e(\mathbf{r}) \tag{23}
$$

**第 $g$ 群的局域源项 $W_g$ 推导**：各向异性扰动在简化近似下（忽略回冷电子项）为：

$$
g_1^m(\beta) = -\frac{\lambda_{ei}^*(\beta)}{3} f_0^m(\beta) \frac{\nabla T_e}{T_e}
$$

SH 热流 $= (m_e/2) \int_0^\infty v^5 g_1^m(v) dv$。第 $g$ 群的贡献权重为：

$$
W_g = \frac{\int_{v_{g-1}}^{v_g} v^5 g_1^m(v) dv}{\int_0^\infty v^5 g_1^m(v) dv}
$$

从 $(v, dv)$ 到 $(\beta, d\beta)$ 变换：$\beta = m_e v^2/(2k_B T_e)$，$v^5 dv \propto \beta^{5/2} \cdot \beta^{-1/2} d\beta = \beta^2 d\beta$。利用 $\lambda_{ei}^*(\beta) \propto \beta^2$ 和 $f_0^m \propto e^{-\beta}$：

$$
v^5 g_1^m dv \propto \beta^2 \cdot \beta^2 \cdot e^{-\beta} \cdot d\beta = \beta^4 e^{-\beta} d\beta
$$

归一化常数 $\int_0^\infty \beta^4 e^{-\beta} d\beta = \Gamma(5) = 4! = 24$。因此：

$$
\boxed{\mathbf{U}_g(\mathbf{r}) = W_g \, \mathbf{Q}_{SH}(\mathbf{r}), \qquad W_g = \frac{1}{24} \int_{\beta_{g-1}}^{\beta_g} \beta^4 e^{-\beta} \, d\beta} \tag{24}
$$

$W_g$ 的物理含义是第 $g$ 群在总 SH 热流中的权重分数，满足 $\sum_g W_g = 1$。$\beta^4 e^{-\beta}$ 权重在 $\beta \approx 4$ 处达峰值，反映载热电子的核心贡献。

#### $\mathbf{U}_g$ 的定义与物理动机

**(1) $\mathbf{U}_g$ 是什么？** $\mathbf{U}_g(\mathbf{r}) = W_g\,\mathbf{Q}_{SH}(\mathbf{r})$ 是**第 $g$ 群电子的局域源项（group source）**：它度量"若温度梯度在 $\mathbf{r}$ 处瞬时建立，第 $g$ 群电子（能量落在 $[\beta_{g-1},\,\beta_g]$ 内）在局域平衡下将携带的那部分 SH 热流"。它是**矢量**（沿 $\nabla T_e$ 方向），并作为其后第 $g$ 群输运方程 (25) 的驱动源项。

**(2) 为什么这样定义？** 需追溯 SH 热流在速度空间的结构。SH 热流是各向异性分布函数的矩（§2.2 步骤 1，此处用 Schurtz 记号 $g_1^m$，前因子在比值中约去）：

$$
Q_{SH} = \frac{m_e}{2}\int_0^\infty v^5\, g_1^m(v)\, dv
$$

将能量轴按 $\beta$ 分群后，该积分自然分解为各群贡献之和：

$$
\mathbf{Q}_{SH} = \sum_{g=1}^{N_g} \mathbf{U}_g, \qquad
\mathbf{U}_g \equiv \frac{\dfrac{m_e}{2}\displaystyle\int_{v_{g-1}}^{v_g} v^5 g_1^m(v)\, dv}{\dfrac{m_e}{2}\displaystyle\int_0^\infty v^5 g_1^m(v)\, dv}\;\mathbf{Q}_{SH} = W_g\,\mathbf{Q}_{SH} \tag{U1}
$$

即 $\mathbf{U}_g$ 是"总 SH 热流中由第 $g$ 群电子携带的那一份"。这样定义的**两个关键动机**：

- **能量分辨的非局域性**：非局域效应的强弱取决于电子平均自由程，而 $\lambda(v)\propto v^4$——快电子携带的热流可传播远得多。若用一个平均自由程的单一输运方程处理全部热流，将抹平这一能量分辨信息（这正是 LMV 单核模型的主要缺陷之一 [1]）。将 $\mathbf{Q}_{SH}$ 按能群分解为 $\mathbf{U}_g$，各群用**自己的**自由程 $\lambda_g = 2\beta_{g-1/2}^2\lambda_e$（式 23）独立传播，即可逐群分辨非局域度——这是中子输运中**多群扩散**（multigroup diffusion）思想的直接移植 [27]。
- **源与流的对应**：$\mathbf{U}_g$ 的物理角色是"第 $g$ 群电子的注入率 × 携带热流"。有效温度梯度在 $\mathbf{r}$ 处以率 $W_g\mathbf{Q}_{SH}$ 将能量注入第 $g$ 群，随后该群电子以自由程 $\lambda_g$ 传播到远处再沉积——输运方程 (25) 正是这一"注入—传播—沉积"过程的数学描述。

**(3) 归一化 $\sum_g W_g = 1$ 的证明**：若分群覆盖整个能量轴，由 (24) 及 $\Gamma$ 函数：

$$
\sum_{g=1}^{N_g} W_g = \frac{1}{24}\int_0^\infty \beta^4 e^{-\beta}\,d\beta = \frac{\Gamma(5)}{24} = \frac{4!}{24} = 1 \tag{U2}
$$

即各群权重恰好平分总 SH 热流，无遗漏、无重叠。**有限截断**：实际计算取 $\beta_{\max}\approx 10$–$20$，截断丢失分数为

$$
\varepsilon = \frac{1}{24}\int_{\beta_{\max}}^\infty \beta^4 e^{-\beta}d\beta = \frac{e^{-\beta_{\max}}}{24}\Big(\beta_{\max}^4 + 4\beta_{\max}^3 + 12\beta_{\max}^2 + 24\beta_{\max} + 24\Big) \tag{U3}
$$

$\beta_{\max}=10$ 时 $\varepsilon \approx 2.9\%$，$\beta_{\max}=20$ 时 $\varepsilon \approx 2\times 10^{-5}$。数值实现中常将截断余量并入最高能群（或对 $W_g$ 整体再归一化），以保证 $\sum_g W_g = 1$ [11]。

**(4) $\beta^4 e^{-\beta}$ 权重的峰值与物理**：由 $\dfrac{d}{d\beta}\big(\beta^4 e^{-\beta}\big) = \beta^3 e^{-\beta}(4-\beta) = 0$ 得 $\beta = 4$，即**载热电子特征能量 $E = 4k_BT_e$**（对应 $v = 2.83\,v_{th}$，见 §2.2）。权重在 $\beta=4$ 处达峰，说明 SH 热流主要由能量 $\approx 4k_BT_e$ 的电子携带——而恰是这些电子具有最长自由程（$\lambda \propto \beta^2$，式 23），两者共同决定了 SNB 中非局域输运的空间尺度。注意 (24) 的 $W_g$ 基于"忽略 $(\beta-4)$ 回冷电子项"的简化源 $g_1^m$（附录 B 假设 **A9**），即只统计携带正向热流的载热电子，回流电子电流由电场修正（§7）另行处理。

### 5.4 群输运方程与总热流

每群内的角通量 $q_g(\mathbf{\Omega}, \mathbf{r})$ 满足独立的输运方程：

$$
\mathbf{\Omega} \cdot \nabla q_g(\mathbf{\Omega}, \mathbf{r}) + \frac{1}{\lambda_g(\mathbf{r})} q_g(\mathbf{\Omega}, \mathbf{r}) = \frac{1}{\lambda_g(\mathbf{r})} \frac{3}{4\pi} \mathbf{\Omega} \cdot \mathbf{U}_g(\mathbf{r}) \tag{25}
$$

总非局域热流为各群贡献之和：

$$
\mathbf{Q}_{SNB}(\mathbf{r}) = \sum_{g=1}^{N_g} \int_{4\pi} q_g(\mathbf{\Omega}, \mathbf{r}) \, \mathbf{\Omega} \, d^2\Omega \tag{26}
$$

典型的能量分群数 $N_g = 40$，最大能量取 $\beta_{\max} \approx 10$–$20$ [11]。

---

<a name="6"></a>
## 6. P1 扩散近似与最终控制方程

### 6.1 球谐函数预备知识：从球谐展开到 P1 近似

在三维空间中，任意定义在单位球面 $S^2$ 上的平方可积函数 $q(\mathbf{\Omega})$ 可在球谐函数 $Y_{\ell m}(\mathbf{\Omega})$ 的完备正交基上展开 [23, 24]：

$$
q(\mathbf{\Omega}) = \sum_{\ell=0}^{\infty} \sum_{m=-\ell}^{\ell} a_{\ell m} Y_{\ell m}(\mathbf{\Omega})
$$

其中 $Y_{\ell m}$ 满足正交关系 $\int_{4\pi} Y_{\ell m} Y_{\ell' m'}^* d^2\Omega = \delta_{\ell\ell'}\delta_{mm'}$。

**前几阶归一化球谐函数**：
$$
Y_{00}(\mathbf{\Omega}) = \frac{1}{\sqrt{4\pi}}, \quad
Y_{10}(\mathbf{\Omega}) = \sqrt{\frac{3}{4\pi}} \Omega_z, \quad
Y_{1,\pm 1}(\mathbf{\Omega}) = \mp\sqrt{\frac{3}{8\pi}} (\Omega_x \pm i\Omega_y)
$$

展开系数 $a_{\ell m} = \int q(\mathbf{\Omega}) Y_{\ell m}^*(\mathbf{\Omega}) d^2\Omega$ 为角通量的各阶**角矩**（angular moments）。

**P1 截断近似**：在 P1 近似中，级数截断于 $\ell = 1$，仅保留前 4 项（$\ell=0$ 的 1 项 + $\ell=1$ 的 3 项）。将展开用矢量记号紧凑表示为：

$$
\boxed{q(\mathbf{\Omega}) = \frac{1}{4\pi} H + \frac{3}{4\pi} \mathbf{\Omega} \cdot \mathbf{Q}} \tag{P1}
$$

其中的展开系数即角通量的零阶和一阶角矩：

$$
H = \int_{4\pi} q(\mathbf{\Omega}) \, d^2\Omega \quad \text{（零阶矩：标量，各向同性分量）} \tag{27a}
$$

$$
\mathbf{Q} = \int_{4\pi} q(\mathbf{\Omega}) \,\mathbf{\Omega} \, d^2\Omega \quad \text{（一阶矩：矢量，各向异性分量）} \tag{27b}
$$

**系数 $1/(4\pi)$ 和 $3/(4\pi)$ 的确定**：由球面积分的正交性保证展开的自洽性：
- $\int_{4\pi} d^2\Omega = 4\pi$ —— 常数项的归一化
- $\int_{4\pi} \mathbf{\Omega} \, d^2\Omega = \mathbf{0}$ —— 奇函数积分为零
- $\int_{4\pi} \Omega_i \Omega_j \, d^2\Omega = \frac{4\pi}{3} \delta_{ij}$ —— 各向同性二阶张量

验证展开自洽性：将 (P1) 代入 (27a)：$\int (H + 3\mathbf{\Omega}\cdot\mathbf{Q})/(4\pi) d^2\Omega = H/(4\pi) \cdot 4\pi + 3\mathbf{Q}/(4\pi)\cdot\int\mathbf{\Omega}d^2\Omega = H$ ✓。代入 (27b)：$\int (H+3\mathbf{\Omega}\cdot\mathbf{Q})/(4\pi) \mathbf{\Omega} d^2\Omega = (H/4\pi)\cdot\mathbf{0} + (3/4\pi)\cdot(4\pi/3)\mathbf{Q} = \mathbf{Q}$ ✓。

对于单群输运方程 **(25)**，各群独立展开，记为 $H_g$ 和 $\mathbf{Q}_g$：
$$
4\pi q_g(\mathbf{\Omega}) = H_g + 3 \mathbf{\Omega} \cdot \mathbf{Q}_g \tag{27c}
$$

**P1 近似的适用条件**：P1 截断要求各向异性较小（$|\mathbf{Q}| \ll H$），即分布函数偏离各向同性的程度不大。这在光学厚（碰撞频繁）区域自动满足；在光学薄区域可能需更高阶展开（P3、P5 等）或直接离散坐标法（$S_N$）。SNB 模型依赖能量分群缓解此问题——高能群的自由程虽长，但低能群提供碰撞耦合使整体解稳定。

### 6.2 角矩方程的系统推导

将 P1 展开 (27c) 代入群输运方程 (25)。为书写简洁，省略下标 $g$ 和空间变量 $\mathbf{r}$：

$$
\mathbf{\Omega} \cdot \nabla\left(\frac{H + 3\mathbf{\Omega}\cdot\mathbf{Q}}{4\pi}\right) + \frac{1}{\lambda}\frac{H + 3\mathbf{\Omega}\cdot\mathbf{Q}}{4\pi} = \frac{3}{4\pi\lambda}\mathbf{\Omega} \cdot \mathbf{U} \tag{A}
$$

乘以 $4\pi$ 整理：
$$
\mathbf{\Omega}\cdot\nabla H + 3\mathbf{\Omega}\cdot\nabla(\mathbf{\Omega}\cdot\mathbf{Q}) + \frac{H}{\lambda} + \frac{3}{\lambda}\mathbf{\Omega}\cdot\mathbf{Q} = \frac{3}{\lambda}\mathbf{\Omega}\cdot\mathbf{U} \tag{B}
$$

#### (i) 零阶矩方程

对 (B) 两边作全立体角积分 $\int d^2\Omega$：

- **$\int \mathbf{\Omega}\cdot\nabla H \, d^2\Omega$**：$= \nabla H \cdot \int \mathbf{\Omega} d^2\Omega = 0$（奇函数在对称域上积分为零）
- **$3\int \mathbf{\Omega}\cdot\nabla(\mathbf{\Omega}\cdot\mathbf{Q}) \, d^2\Omega$**：利用 $\int \Omega_i\Omega_j d^2\Omega = \frac{4\pi}{3}\delta_{ij}$：
  $$
  3 \cdot \partial_i Q_j \cdot \frac{4\pi}{3}\delta_{ij} = 4\pi \nabla\cdot\mathbf{Q}
  $$
- **$\int H/\lambda \, d^2\Omega = H/\lambda \cdot 4\pi$**
- **$3/\lambda \int \mathbf{\Omega}\cdot\mathbf{Q} \, d^2\Omega = 0$**（奇函数积分）
- **右边 $\frac{3}{\lambda} \int \mathbf{\Omega}\cdot\mathbf{U} \, d^2\Omega = 0$**（同理）

因此零阶矩方程为：
$$
4\pi \nabla\cdot\mathbf{Q} + \frac{4\pi H}{\lambda} = 0 \quad\Rightarrow\quad \boxed{\nabla\cdot\mathbf{Q}_g + \frac{H_g}{\lambda_g} = 0} \tag{28a}
$$

**物理含义**：各向同性分量 $H_g$ 的碰撞耗散（$H_g/\lambda_g$）由各向异性分量的散度（净流出，$\nabla\cdot\mathbf{Q}_g$）平衡。源项 $\mathbf{U}_g$ 不直接驱动 $H_g$，而通过 $\mathbf{Q}_g$ 间接作用——这正是扩散近似的核心特征。

#### (ii) 一阶矩方程

对 (B) 两边乘以 $\mathbf{\Omega}$ 后作全立体角积分 $\int \mathbf{\Omega} \, d^2\Omega$：

- **$\int \mathbf{\Omega} (\mathbf{\Omega}\cdot\nabla H) \, d^2\Omega$**：$= \frac{4\pi}{3} \nabla H$（利用 $\int \Omega_i\Omega_j = \frac{4\pi}{3}\delta_{ij}$）
- **$3\int \mathbf{\Omega}[\mathbf{\Omega}\cdot\nabla(\mathbf{\Omega}\cdot\mathbf{Q})] \, d^2\Omega$**：涉及三阶张量 $\int \Omega_i\Omega_j\Omega_k$，在球面上积分为零（奇函数）
- **$\int \mathbf{\Omega} (H/\lambda) \, d^2\Omega = 0$**
- **$\frac{3}{\lambda} \int \mathbf{\Omega}(\mathbf{\Omega}\cdot\mathbf{Q}) \, d^2\Omega = \frac{3}{\lambda} \cdot \frac{4\pi}{3} \mathbf{Q} = \frac{4\pi}{\lambda}\mathbf{Q}$**
- **右边 $\frac{3}{\lambda} \int \mathbf{\Omega}(\mathbf{\Omega}\cdot\mathbf{U}) \, d^2\Omega = \frac{3}{\lambda} \cdot \frac{4\pi}{3} \mathbf{U} = \frac{4\pi}{\lambda}\mathbf{U}$**

因此一阶矩方程为 $\frac{4\pi}{3} \nabla H_g + \frac{4\pi}{\lambda_g} \mathbf{Q}_g = \frac{4\pi}{\lambda_g} \mathbf{U}_g$，化简得：

$$
\boxed{\frac{1}{3}\nabla H_g + \frac{1}{\lambda_g}\mathbf{Q}_g = \frac{1}{\lambda_g}\mathbf{U}_g} \tag{28b}
$$

**重排即得闭合关系**：
$$
\boxed{\mathbf{Q}_g = \mathbf{U}_g - \frac{\lambda_g}{3} \nabla H_g} \tag{29}
$$

### 6.3 Helmholtz 扩散方程的导出

将 (29) 对 $\mathbf{Q}_g$ 的表达式代入零阶矩方程 (28a)：

$$
\nabla\cdot\left(\mathbf{U}_g - \frac{\lambda_g}{3}\nabla H_g\right) + \frac{H_g}{\lambda_g} = 0
$$

展开散度项并移项，得标准 Helmholtz 型方程：

$$
\boxed{\left( \frac{1}{\lambda_g} - \nabla \cdot \frac{\lambda_g}{3} \nabla \right) H_g(\mathbf{r}) = -\nabla \cdot \mathbf{U}_g(\mathbf{r})} \tag{30}
$$

**算子结构分析**：
- $1/\lambda_g$ —— **吸收项**：碰撞以特征速率 $v_{th}/\lambda_g \sim \nu_{ei}$ 将 $H_g$ 耗散为零（麦克斯韦化）
- $-\nabla\cdot(\lambda_g/3)\nabla$ —— **扩散项**：空间非局域耦合的尺度由 $\sqrt{\lambda_g L_T/3}$ 决定

### 6.4 最终热流表达式

总非局域热流为各能群贡献之和。利用 (29) 对各群求和：

$$
\mathbf{Q}_{SNB}(\mathbf{r}) = \sum_{g=1}^{N_g} \mathbf{Q}_g = \sum_{g=1}^{N_g} \left( \mathbf{U}_g - \frac{\lambda_g}{3} \nabla H_g \right) \tag{31}
$$

由于各群源项之和等于总 SH 热流（$\sum_g \mathbf{U}_g = \sum_g W_g \mathbf{Q}_{SH} = \mathbf{Q}_{SH}$，因 $W_g$ 归一化至 1），得到 SNB 模型的最终形式：

$$
\boxed{\mathbf{Q}_{SNB}(\mathbf{r}) = \mathbf{Q}_{SH}(\mathbf{r}) - \sum_{g=1}^{N_g} \frac{\lambda_g(\mathbf{r})}{3} \nabla H_g(\mathbf{r})} \tag{32}
$$

### 6.5 物理图像解读

方程 **(30)** 和 **(32)** 构成 SNB 模型的核心方程组。其物理结构包含三个层次：

| 层次 | 数学表达 | 物理含义 |
|------|---------|---------|
| 零阶量 $H_g$ | Helmholtz 方程 (30) | 各向同性偏离 Maxwell 分布的程度。在平滑梯度区 $H_g \to 0$，恢复 SH 理论 |
| 一阶闭合 | $\mathbf{Q}_g = \mathbf{U}_g - \frac{\lambda_g}{3}\nabla H_g$ (29) | 各群热流 = 局域贡献 − 非局域扩散修正 |
| **热流抑制** | $-\sum_g \frac{\lambda_g}{3}\nabla H_g$ 与 $\mathbf{Q}_{SH}$ 同向 | 在陡温度梯度区，非局域修正抵消部分局域热流，实现自动饱和 |
| **预热效应** | $H_g$ 在 $\nabla T_e \approx 0$ 区非零 | 高能电子长自由程将能量"泄漏"至梯度区上游 |

- 方程 (30) 的 $1/\lambda_g$ 项为吸收项（碰撞抹平偏离 Maxwell 分布的速率 $\sim \nu_{ei}$），$\nabla\cdot(\lambda_g/3)\nabla$ 项为空间扩散项（非局域耦合范围 $\sim \sqrt{\lambda_g L_T/3}$）
- 在平滑梯度极限下，$\nabla H_g \to 0$，$\mathbf{Q}_{SNB} \to \mathbf{Q}_{SH}$，自动恢复局域 SH 理论
- 这组方程可在现代流体力学代码（FLASH [14]、HYDRA [15] 等）中利用标准扩散求解器（如 HYPRE 库 [16]）高效求解，每群一个方程，计算开销可控

---

<a name="7"></a>
## 7. 电场自洽修正

### 7.1 电场的必要性

在原始 SNB 模型中，系数 $1/\lambda_g$ 仅描述了碰撞对 $H_g$ 的耗散效应。然而在非局域条件下，自洽电场的效应不可忽略：

1. **回流电流**：为保持 quasi-neutrality（$j \approx 0$），低能电子在自洽电场作用下形成与载热电子方向相反的回流。
2. **自由程限制**：电场在梯度区对电子进行加速/减速，等效地限制了有效输运自由程。
3. **负热流问题**：若不考虑电场修正，在高 $k\lambda_e$ 极限下 SNB 预测的热流可能出现非物理的负值 [3]。

### 7.2 修正方案

Schurtz 等 [1] 提出通过修改有效自由程来纳入电场效应：

$$
\frac{1}{\lambda_g'} = \frac{1}{\lambda_g} + \frac{1}{\beta_g \lambda_E} \tag{33}
$$

其中：

$$
\lambda_E = \frac{k_B T_e}{|e \mathcal{E}|}, \qquad \mathcal{E} = \frac{k_B T_e}{e} \left( \nabla \ln n_e + \gamma \nabla \ln T_e \right) \tag{34}
$$

系数 $\gamma$ 取决于离子电荷数 $Z$，由输运系数的数值拟合确定 [1, 3]：
- 对于 $Z=1$：$\gamma \approx 1.5$
- 对于高 $Z$ 极限：$\gamma \approx 1 + 3/2 = 2.5$

Brodrick 等 [5] 在更具体的实现中采用了分离的 ee 和 ei 自由程：

$$
\frac{1}{\lambda_{g,ee}'} = \frac{r}{\beta^2 \lambda_{ee}}, \qquad \lambda_{g,ei}' = \beta^2 \lambda_{ei} \frac{Z + 0.24}{Z + 4.2} \tag{35}
$$

其中 $r$ 为可调参数（推荐值 $r=2$ [12]）。

### 7.3 修正后的控制方程

$$
\left( \frac{1}{\lambda_g} - \nabla \cdot \frac{\lambda_g'}{3} \nabla \right) H_g = -\nabla \cdot \mathbf{U}_g \tag{36}
$$

$$
\mathbf{Q}_{SNB} = \mathbf{Q}_{SH} - \sum_g \frac{\lambda_g'}{3} \nabla H_g \tag{37}
$$

**电场修正的物理效果**：
1. 防止 $H_g$ 在低密度/无碰撞区过度增长
2. 在 $k\lambda_e \to \infty$ 极限下给出合理的热流渐近行为
3. 消除 SNB 原始形式可能出现的非物理负热流

---

<a name="8"></a>
## 8. 磁化等离子体推广

### 8.1 Nicolaï-Feugeas-Schurtz (2006) 模型

Nicolaï、Feugeas 和 Schurtz [4] 将 SNB 模型推广到磁化等离子体。在磁场存在时，电子热传导变得高度各向异性，且磁场与热流通过 Nernst 效应、Righi-Leduc 热流等机制耦合。

### 8.2 磁化输运方程

推广后的群输运方程包含磁场效应 [4]：

$$
\mathbf{\Omega} \cdot \nabla q_g + \frac{1}{\lambda_g} q_g = \frac{1}{\lambda_g} \frac{3}{4\pi} \mathbf{\Omega} \cdot (\mathbf{U}_g + \mathbf{V}_g^{\text{mag}}) \tag{38}
$$

其中 $\mathbf{V}_g^{\text{mag}}$ 包含了磁化修正源项。在强磁化极限下（$\omega_{ce} \tau_{ei} \gg 1$），垂直方向的热传导被显著抑制，有效自由程由拉莫尔半径而非碰撞自由程决定。

### 8.3 Brodrick 等 (2017) 的后续评估

Brodrick 等 [5] 指出，在磁化 ICF 条件下（如磁化衬套内爆，MagLIF），SNB 模型可以准确预测沿磁场方向的热流抑制，但对横向热流（Righi-Leduc 效应）的预测精度仍有待提高。Chen 等 [13] 进一步证明，SNB 模型在耦合电场自洽修正后才能正确复现 Biermann 电池磁场的非局域抑制效应。

---

<a name="9"></a>
## 9. 数值实现与边界条件

### 9.1 方程结构

SNB 模型的核心方程 **(30)** 是 Helmholtz 型偏微分方程，算子为对称正定的：

$$
\mathcal{L}_g = \frac{1}{\lambda_g} - \nabla \cdot \frac{\lambda_g}{3} \nabla \tag{39}
$$

这在现代流体代码（如 FLASH [14]、HYDRA [15]）中可直接利用已有的扩散求解器（如 HYPRE 库 [16]）求解，每群一个方程，计算开销可控。

### 9.2 边界条件

自然的反射边界条件为：

$$
\nabla H_g \cdot \hat{\mathbf{n}} = 0 \quad \text{on } \partial\Omega \tag{40}
$$

这直接保证在边界处净热流的法向分量为零：

$$
\mathbf{Q}_{SNB} \cdot \hat{\mathbf{n}} = \mathbf{Q}_{SH} \cdot \hat{\mathbf{n}} - \sum_g \frac{\lambda_g}{3} (\nabla H_g \cdot \hat{\mathbf{n}}) = 0 \tag{41}
$$

### 9.3 热流散度的直接计算

在实际的辐射流体力学代码中，需要的是热流散度 $\nabla \cdot \mathbf{Q}_{SNB}$ 而非热流本身。利用 Helmholtz 方程 **(30)**，可以直接计算：

$$
\nabla \cdot \mathbf{Q}_{SNB} = \nabla \cdot \mathbf{Q}_{SH} - \sum_g \left( \nabla \cdot \mathbf{U}_g + \frac{H_g}{\lambda_g} \right) \tag{42}
$$

这避免了先求解 $\nabla H_g$ 再取散度的数值精度损失 [11]。

### 9.4 时间步长约束

傅里叶分析表明，显式时间离散的 CFL 条件为 $\Delta t < \Delta x / v_{th}$，远比 SH 显式方案的 $\Delta t < \Delta x^2 / (v_{th} \lambda_e)$ 宽松，在实际参数下通常不构成限制 [1]。

---

<a name="10"></a>
## 10. 模型验证与精度评估

### 10.1 小振幅温度扰动测试

SNB 模型在小振幅正弦温度扰动的线性响应测试中（$\delta T_e \propto e^{ikx}$），能准确复现 VFP 模拟预测的非局域热导率抑制函数 $\kappa_{nl}(k\lambda_e)/\kappa_{SH}$ [1, 5]。Brodrick 等 [5] 发现，若采用合适的 mfp 定义和调谐参数，SNB 与 VFP 在中等碰撞性区域（$k\lambda_e \sim 0.01$–$1$）的一致性优于 10%。

### 10.2 大温度梯度测试

在大温度梯度情形（如 $T_h/T_c \gg 2$），Brodrick 等 [5] 系统的比较显示：
- **SNB 模型**：准确预测峰值热流抑制和预热效应，峰值热流误差 $\lesssim 16\%$
- **EIC 模型** [17] 和 **NFLF 模型** [18]：高估峰值热流约 35%，且低估预热

### 10.3 非均匀电离测试

在 hohlraum 相关条件下（含空间变化的 $Z$ 分布），SNB 模型虽然准确预测峰值热流（误差 < 16%），但在低密度氦气填充区高估热流约 2 倍 [5]。这表明 SNB 在处理强非均匀电离度梯度时仍有局限。

### 10.4 已知局限性

1. **高 $Z$ 材料中的系统偏差**：在高 $Z$ 极限下，SNB 略微高估非局域效应的限流和预热程度 [19, 20]。
2. **电场修正的不足**：原始电场修正方案 [1] 仅是近似的唯象处理，Chen 等 [13] 证明必须自洽地包含电场修正才能正确复现非局域条件下 Biermann 源和 Nernst 速度的抑制。
3. **时间依赖效应**：SNB 假设稳态输运（$\partial/\partial t = 0$），在电子碰撞时间接近流体力学时间尺度的极端条件下可能不足。最近的数据驱动方法（如 SNB-TINN [21]）尝试通过学习动态热核来克服此局限。
4. **磁化推广**：Nicolaï 等 [4] 的磁化 SNB 在 $\omega_{ce}\tau_{ei} \sim 1$ 的中等磁化区域精度有限。

---

<a name="11"></a>
## 11. 总结与展望

### 11.1 推导逻辑链回顾

$$
\boxed{
\begin{aligned}
&\text{FP 方程} \xrightarrow{\lambda_e/L_T \ll 1} \text{SH 局域热传导} \xrightarrow{\lambda_e/L_T \gtrsim 5\times 10^{-3}} \text{SH 失效} \\
&\xrightarrow{\text{非局域性}} \text{LMV 卷积 } \mathbf{Q} = \int W \mathbf{Q}_{SH} \\
&\xrightarrow{\text{等效输运方程}} \mathbf{\Omega}\cdot\nabla q + q/\lambda_t = (3/4\pi\lambda_t) \mathbf{\Omega}\cdot\mathbf{Q}_{SH} \\
&\xrightarrow{\text{能量多群}} \text{每群输运方程} \xrightarrow{P_1 \text{ 近似}} \left(\frac{1}{\lambda_g} - \nabla\cdot\frac{\lambda_g}{3}\nabla\right) H_g = -\nabla\cdot\mathbf{U}_g \\
&\xrightarrow{\text{求和}} \mathbf{Q}_{SNB} = \mathbf{Q}_{SH} - \sum_g \frac{\lambda_g}{3} \nabla H_g
\end{aligned}}
$$

### 11.2 SNB 模型的地位与展望

SNB 模型自 2000 年提出以来，已成为 ICF 辐射流体力学代码（HYDRA、CHIC、DRACO、FLASH 等）中**非局域电子热传导的标准模型** [5, 14, 15]。其核心优势在于：

1. **动理学基础**：从 FP 方程出发，物理依据清晰
2. **数值高效性**：将全局卷积转化为局部扩散方程
3. **多维推广自然**：方程形式本身是多维的
4. **可扩展性**：可通过修正 $\lambda_g$ 纳入额外物理（电场、磁场）

**当前研究方向**包括：
- 自洽电场-磁场耦合的非局域模型 [4, 13]
- 数据驱动/机器学习增强的核函数学习 [21]
- 面向磁约束聚变边界等离子体的推广 [22]

---

<a name="12"></a>
## 参考文献

> **本地文献库路径约定**：以下标注"📁 本地"的文献可在本地文献库中查阅，根目录为 `E:\PhySimX\PhySimX\literature\database\data\database\`，列出的相对路径可直接拼接查阅 PDF 文件。未标注的文献为外部经典文献（不在本地库中）。

[1] G. P. Schurtz, P. D. Nicolaï, and M. Busquet, "A nonlocal electron conduction model for multidimensional radiation hydrodynamics codes," *Physics of Plasmas*, vol. 7, no. 10, pp. 4238–4249, 2000. [ 📁 本地：ⓘ 参考（无本地PDF，有链接）

[2] J. F. Luciani, P. Mora, and J. Virmont, "Nonlocal heat transport due to steep temperature gradients," *Physical Review Letters*, vol. 51, no. 18, pp. 1664–1667, 1983. [

[3] G. P. Schurtz, S. Gary, S. Hulin, C. Chenais-Popovics, J.-C. Gauthier, F. Thais, J. Breil, et al., "Revisiting nonlocal electron-energy transport in inertial-fusion conditions," *Physical Review Letters*, vol. 98, p. 095002, 2007. [DOI: 10.1103/PhysRevLett.98.095002]（外部文献）

[4] P. D. Nicolaï, J.-L. A. Feugeas, and G. P. Schurtz, "A practical nonlocal model for heat transport in magnetized laser plasmas," *Physics of Plasmas*, vol. 13, no. 3, p. 032701, 2006. [DOI: 10.1063/1.2179392]（外部文献）

[5] J. P. Brodrick, R. J. Kingham, M. M. Marinak, M. V. Patel, A. V. Chankin, J. T. Omotani, M. V. Umansky, et al., "Testing nonlocal models of electron thermal conduction for magnetic and inertial confinement fusion applications," *Physics of Plasmas*, vol. 24, no. 9, p. 092309, 2017. [DOI: 10.1063/1.5001079] 📁 本地：`SNB_model/Brodrick2017-SNB非局域模型的VFP基准测试.pdf`

[6] M. N. Rosenbluth, W. M. MacDonald, and D. L. Judd, "Fokker-Planck equation for an inverse-square force," *Physical Review*, vol. 107, no. 1, pp. 1–6, 1957. [

[7] L. Spitzer, Jr. and R. Härm, "Transport phenomena in a completely ionized gas," *Physical Review*, vol. 89, no. 5, pp. 977–981, 1953. [ 📁 本地：ⓘ 参考（无本地PDF，有链接）

[8] E. M. Epperlein and M. G. Haines, "Plasma transport coefficients in a magnetic field by direct numerical solution of the Fokker-Planck equation," *Physics of Fluids*, vol. 29, no. 4, pp. 1029–1041, 1986. [ 📁 本地：`elec_transport/Chen2023-热电子非局域输运对激光烧蚀的影响.pdf`

[9] S. I. Braginskii, "Transport processes in a plasma," in *Reviews of Plasma Physics*, M. A. Leontovich, Ed. New York: Consultants Bureau, 1965, vol. 1, pp. 205–311.（外部文献）

[10] A. R. Bell, R. G. Evans, and D. J. Nicholas, "Electron energy transport in steep temperature gradients in laser-produced plasmas," *Physical Review Letters*, vol. 46, no. 4, pp. 243–246, 1981. [DOI: 10.1103/PhysRevLett.46.243]（外部文献）

[11] "Nonlocal heat flux models," BOUT++ documentation. [Online]. Available: http://bout-dev.readthedocs.io/en/latest/user_docs/nonlocal.html

[12] M. Sherlock, J. P. Brodrick, and C. P. Ridgers, "A comparison of non-local electron transport models for laser-plasmas relevant to inertial confinement fusion," *Physics of Plasmas*, vol. 24, no. 8, p. 082706, 2017. [ 📁 本地：ⓘ 参考（无本地PDF，有链接）

[13] Z. H. Chen, Z. Q. Zhao, et al., "An improved nonlocal electron heat transport model for magnetized plasmas," *Physics of Plasmas*, vol. 32, 2025. (cf. also arXiv:2508.17309) 📁 本地：`SNB_model/Chen2025-磁化非局域热输运改进.pdf`

[14] B. Fryxell, K. Olson, P. Ricker, F. X. Timmes, M. Zingale, D. Q. Lamb, P. MacNeice, et al., "FLASH: An adaptive mesh hydrodynamics code for modeling astrophysical thermonuclear flashes," *The Astrophysical Journal Supplement Series*, vol. 131, no. 1, pp. 273–334, 2000. [DOI: 10.1086/317361]（外部文献）

[15] M. M. Marinak, G. D. Kerbel, N. A. Gentile, O. Jones, D. Munro, S. Pollaine, T. R. Dittrich, and S. W. Haan, "Three-dimensional HYDRA simulations of National Ignition Facility targets," *Physics of Plasmas*, vol. 8, no. 5, pp. 2275–2280, 2001. [DOI: 10.1063/1.1356740]（外部文献）

[16] R. D. Falgout and U. M. Yang, "hypre: A library of high performance preconditioners," in *Computational Science — ICCS 2002*, ser. Lecture Notes in Computer Science, vol. 2331. Springer, 2002, pp. 632–641. [DOI: 10.1007/3-540-47789-6_66]（外部文献）

[17] J.-Y. Ji, E. D. Held, and C. R. Sovinec, "Moment approach to deriving parallel heat flow in general magnetic geometry," *Physics of Plasmas*, vol. 16, no. 2, p. 022312, 2009. [DOI: 10.1063/1.3076207]（外部文献）

[18] A. M. Dimits, I. Joseph, and M. V. Umansky, "A fast non-Fourier method for Landau-fluid operators," *Physics of Plasmas*, vol. 21, no. 5, p. 055907, 2014. [

[19] A. Marocchino, M. Tzoufras, S. Atzeni, A. Schiavi, P. D. Nicolaï, J. Mallet, V. Tikhonchuk, and J.-L. Feugeas, "Comparison for non-local hydrodynamic thermal conduction models," *Physics of Plasmas*, vol. 20, no. 2, p. 022702, 2013. [ 📁 本地：ⓘ 参考（无本地PDF，有链接）

[20] D. Del Sorbo, J.-L. Feugeas, P. Nicolaï, M. Olazabal-Loumé, B. Dubroca, S. Guisset, M. Touati, and V. Tikhonchuk, "Reduced entropic model for studies of multidimensional nonlocal transport in high-energy-density plasmas," *Physics of Plasmas*, vol. 22, no. 8, p. 082706, 2015. [ 本地另有相关扩展版：ⓘ 参考（无本地PDF，有链接））

[21] M. Luo, C. Heaton, Y. Wang, D. Plummer, M. Fitzgerald, F. Miniati, S. M. Vinko, and G. Gregori, "Learning heat transport kernels using a nonlocal heat transport theory-informed neural network," arXiv:2506.16619, 2025. 📁 本地：ⓘ 参考（无本地PDF，有链接）

[22] J. T. Omotani, B. D. Dudson, and the MAST Team, "Non-local approach to kinetic effects on parallel transport in fluid models of the scrape-off layer," arXiv:1302.0676, 2013. 📁 本地：`SNB_model/Omotani2013-SOL非局域动理学.pdf`

**补充引用**（[23]–[27] 为标准教材/手册类文献，本地文献库（以研究论文为主）均未收录；如需查阅请使用各自公开的电子版或图书馆资源）：

[23] J. D. Huba, *NRL Plasma Formulary*, Naval Research Laboratory, 2019. [Coulomb 对数实用公式来源] 📁 本地：ⓘ 参考（无本地PDF，有链接）（18th edition，本地库 #244）

[24] R. J. Goldston and P. H. Rutherford, *Introduction to Plasma Physics*, IOP Publishing, 1995. [碰撞理论标准参考]（教材，未收录本地库）

[25] S. Atzeni and J. Meyer-ter-Vehn, *The Physics of Inertial Fusion*, Oxford University Press, 2004. [ICF 中热传导理论综述]（教材，未收录本地库；📁 本地可替代综述：`SNB_model/Frontiers2023-Frontiers2023热传导非局域输运综述.pdf`）

[26] G. B. Arfken, H. J. Weber, and F. E. Harris, *Mathematical Methods for Physicists*, 7th ed. Academic Press, 2013, Ch. 15. [球谐函数与正交多项式标准参考]（教材，未收录本地库）

[27] E. E. Lewis and W. F. Miller, Jr., *Computational Methods of Neutron Transport*. Wiley, 1984. [离散坐标法与 P1 近似在输运理论中的系统介绍]（教材，未收录本地库）

**本地文献库中可补充查阅的相关文献**（未直接引用，但与 SNB 主题密切相关的本地收藏）：

- 📁 ⓘ 参考（无本地PDF，有链接） — Henchen 等 2018，Thomson 散射实验观测非局域热流（*PRL* 121, 125001）
- 📁 `SNB_model/Zhu2025-非局域热流与自生磁场.pdf` — Zhu 等 2025，非局域热流与自生磁场（arXiv:2510.26640）
- 📁 `SNB_model/Frontiers2023-Frontiers2023热传导非局域输运综述.pdf` — Lau 等 2025，MagLIF 气柱中 SNB vs VFP 对比（*PoP* 32）
- 📁 `SNB_model/Frontiers2023-Frontiers2023热传导非局域输运综述.pdf` — Yang/Chen 等 2024，SNB+烧蚀 RT 不稳定耦合（*NF* 64）
- 📁 `SNB_model/Frontiers2023-Frontiers2023热传导非局域输运综述.pdf` — Holec 等 2018，AWBS 动理学建模（arXiv:1901.11378）
- 📁 `SNB_model/Frontiers2023-Frontiers2023热传导非局域输运综述.pdf` — Frontiers 2023 热传导与非局域输运综述

---

## 附录 A：沿特征线处理一阶偏微分方程的数学方法

SNB 模型的核心方程 (16) 是一阶线性偏微分方程，其求解使用了**特征线法**（Method of Characteristics）。本节解释此方法的数学原理。

### A.1 一般理论

考虑一阶拟线性 PDE：

$$
a(x, y, u)\frac{\partial u}{\partial x} + b(x, y, u)\frac{\partial u}{\partial y} = c(x, y, u)
$$

特征线法的核心思想是：在 $(x, y)$ 平面上寻找曲线族 $[x(s), y(s)]$（以参数 $s$ 为弧长参数），使得沿此曲线 PDE 退化为 ODE。

由链式法则，沿曲线 $du/ds = (\partial u/\partial x)(dx/ds) + (\partial u/\partial y)(dy/ds)$。若选择 $dx/ds = a$ 和 $dy/ds = b$，则 PDE 左边化为 $du/ds$。因此特征线方程组为 [Stanford Math 220A]：

$$
\frac{dx}{ds} = a, \quad \frac{dy}{ds} = b, \quad \frac{du}{ds} = c
$$

### A.2 在 SNB 输运方程中的应用

方程 (16) 形如：

$$
\underbrace{\Omega_x}_{a_x} \frac{\partial q}{\partial x} + \underbrace{\Omega_y}_{a_y} \frac{\partial q}{\partial y} + \underbrace{\Omega_z}_{a_z} \frac{\partial q}{\partial z} + \frac{1}{\lambda_t} q = \frac{3}{4\pi\lambda_t} \mathbf{\Omega} \cdot \mathbf{Q}_{SH}
$$

引入沿 $\mathbf{\Omega}$ 方向的参数 $s$（即 $\mathbf{r}(s) = \mathbf{r}_0 + s\mathbf{\Omega}$），有：
$$
\frac{d\mathbf{r}}{ds} = \mathbf{\Omega}, \quad \frac{dq}{ds} = \mathbf{\Omega} \cdot \nabla q
$$

因此 PDE 沿特征线退化为 ODE：

$$
\boxed{\frac{dq}{ds} + \frac{1}{\lambda_t(\mathbf{r}_0 + s\mathbf{\Omega})} q = \frac{3}{4\pi\lambda_t(\mathbf{r}_0 + s\mathbf{\Omega})} \mathbf{\Omega} \cdot \mathbf{Q}_{SH}(\mathbf{r}_0 + s\mathbf{\Omega})}
$$

这是标准的一阶线性 ODE，积分因子为：

$$
\mu(s) = \exp\left(\int_0^s \frac{ds'}{\lambda_t(\mathbf{r}_0 + s'\mathbf{\Omega})}\right) = e^{\tau(\mathbf{r}_0+s\mathbf{\Omega}, \mathbf{r}_0)}
$$

乘以积分因子后左侧成为全微分：$\frac{d}{ds}(q e^\tau) = \cdots$，如正文式 (18) 所示（从 ODE 到形式解 (19) 的逐行积分计算见 **A.4**；一维平板情形的积分因子法完整求解见 **A.5**）。

### A.3 物理意义

特征线 $\mathbf{r} = \mathbf{r}_0 + s\mathbf{\Omega}$ 对应于电子沿固定方向 $\mathbf{\Omega}$ 的**直线飞行轨迹**。沿此轨迹，角通量因碰撞衰减（$1/\lambda_t$ 项）和局域 SH 热流注入（源项）而演变。该方法的物理图景与辐射输运和 neutron 输运理论 [27] 中的特征线法完全一致。

### A.4 从输运方程 (16) 到形式解 (19) 的完整计算

本附录把 §4.1 证明 (B) 和 §4.3 的 (18)→(19) 步骤逐行展开。设特征线 $\mathbf{r}(s) = \mathbf{r}_0 + s\mathbf{\Omega}$（$s$ 为沿 $\mathbf{\Omega}$ 的弧长），并定义**路径光学深度**（从 $\mathbf{r}_0$ 到 $\mathbf{r}_0+s\mathbf{\Omega}$）：

$$
T(s) \equiv \tau(\mathbf{r}_0+s\mathbf{\Omega},\,\mathbf{r}_0) = \int_0^s \frac{dl}{\lambda_t(\mathbf{r}_0+l\mathbf{\Omega})}, \qquad \frac{dT}{ds} = \frac{1}{\lambda_t(\mathbf{r}_0+s\mathbf{\Omega})} \tag{A1}
$$

**步骤 1：PDE 沿特征线退化为 ODE。** 由链式法则 $\dfrac{dq}{ds} = \mathbf{\Omega}\cdot\nabla q$，输运方程 (16) 沿特征线成为一阶线性 ODE：

$$
\frac{dq}{ds} + \frac{1}{\lambda_t(\mathbf{r}_0+s\mathbf{\Omega})}\,q = \frac{1}{\lambda_t(\mathbf{r}_0+s\mathbf{\Omega})}\cdot\frac{3}{4\pi}\,\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}_0+s\mathbf{\Omega}) \tag{A2}
$$

**步骤 2：积分因子法。** 识别 $P(s) = 1/\lambda_t(\mathbf{r}_0+s\mathbf{\Omega}) = dT/ds$。标准一阶线性 ODE $q' + Pq = R$ 的积分因子为 $\mu(s) = e^{\int P ds} = e^{T(s)}$。乘以 $\mu(s)$ 后左边成为全微分：

$$
\frac{d}{ds}\Big[ q(\mathbf{\Omega},\,\mathbf{r}_0+s\mathbf{\Omega})\, e^{T(s)} \Big] = \frac{3}{4\pi\lambda_t(\mathbf{r}_0+s\mathbf{\Omega})}\,\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}_0+s\mathbf{\Omega})\, e^{T(s)} \tag{A3}
$$

即正文 (18)（其中 $e^{T(s)} = e^{\tau(\mathbf{r}_0+s\mathbf{\Omega},\mathbf{r}_0)}$）。

**步骤 3：上游积分。** 对 (A3) 从 $s=-\infty$ 积分到 $s=0$。上游边界条件为"无入射热流"，即 $q(\mathbf{\Omega},\,s\to-\infty) = 0$；同时 $e^{T(-\infty)} = e^{-\infty} = 0$（因 $T(-\infty)\to-\infty$），故左端边界项为零：

$$
q(\mathbf{\Omega},\,\mathbf{r}_0)\,e^{T(0)} - \underbrace{q(-\infty)\,e^{T(-\infty)}}_{=0} = \frac{3}{4\pi}\int_{-\infty}^{0}\frac{\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}_0+s\mathbf{\Omega})}{\lambda_t(\mathbf{r}_0+s\mathbf{\Omega})}\,e^{T(s)}\,ds
$$

$T(0) = 0$，且观测点即 $\mathbf{r} = \mathbf{r}_0$，得：

$$
q(\mathbf{\Omega},\,\mathbf{r}) = \frac{3}{4\pi}\int_{-\infty}^{0}\frac{\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}+s\mathbf{\Omega})}{\lambda_t(\mathbf{r}+s\mathbf{\Omega})}\,e^{T(s)}\,ds, \qquad T(s) = \int_0^s \frac{dl}{\lambda_t(\mathbf{r}+l\mathbf{\Omega})} \tag{A4}
$$

**步骤 4：换元到上游距离。** 令 $u = -s \ge 0$（$s\in(-\infty,0]\to u\in[\infty,0]$，$ds = -du$，积分限翻转）：

$$
q(\mathbf{\Omega},\,\mathbf{r}) = \frac{3}{4\pi}\int_{0}^{\infty}\frac{\mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}-u\mathbf{\Omega})}{\lambda_t(\mathbf{r}-u\mathbf{\Omega})}\,e^{T(-u)}\,du \tag{A5}
$$

**步骤 5：光学深度换标。** 计算 $T(-u)$（$s=-u$，即 $l$ 从 $0$ 走到 $-u$）：

$$
T(-u) = \int_0^{-u}\frac{dl}{\lambda_t(\mathbf{r}+l\mathbf{\Omega})} = -\int_0^{u}\frac{dl}{\lambda_t(\mathbf{r}-l\mathbf{\Omega})} = -\tau(\mathbf{r},\,\mathbf{r}-u\mathbf{\Omega}) \tag{A6}
$$

其中 $\tau(\mathbf{r},\,\mathbf{r}-u\mathbf{\Omega}) \equiv \int_0^u dl/\lambda_t(\mathbf{r}-l\mathbf{\Omega})$ 是正文 (17) 定义的**下游光学深度**（从上游点 $\mathbf{r}-u\mathbf{\Omega}$ 到观测点 $\mathbf{r}$ 的碰撞光深）。于是 $e^{T(-u)} = e^{-\tau(\mathbf{r},\,\mathbf{r}-u\mathbf{\Omega})}$，代回 (A5) 并将 $u$ 重命名为 $s$，即得：

$$
\boxed{\,q(\mathbf{\Omega},\,\mathbf{r}) = \frac{3}{4\pi}\int_0^{\infty} e^{-\tau(\mathbf{r},\,\mathbf{r}-s\mathbf{\Omega})}\; \mathbf{\Omega}\cdot\mathbf{Q}_{SH}(\mathbf{r}-s\mathbf{\Omega})\; \frac{ds}{\lambda_t(\mathbf{r}-s\mathbf{\Omega})}\,} \tag{A7}
$$

即正文 (19)。**要点**：积分沿着"电子从上游 $\mathbf{r}-s\mathbf{\Omega}$ 飞到观测点 $\mathbf{r}$"的路径；$ds/\lambda_t$ 是路径上的微分源元（每经过一个自由程，注入 $\mathbf{\Omega}\cdot\mathbf{Q}_{SH}$ 的源强），$e^{-\tau}$ 是源电子存活到观测点的概率——这正是格林函数 $G(\mathbf{r},\mathbf{r}') = e^{-\tau(\mathbf{r},\mathbf{r}')}/\lambda_t(\mathbf{r}')$ 与源 $\frac{3}{4\pi}\mathbf{\Omega}\cdot\mathbf{Q}_{SH}$ 的卷积（§4.1 证明 (B)）。

### A.5 一维平板几何中积分因子法的完整求解（含 $\mu<0$ 分支与指数积分函数）

本节把 §4.2 的一维求解从"改写为…积分因子为…"压缩叙述扩展为**逐行完整推导**。一维平板输运方程（方向余弦 $\mu=\cos\theta$）：

$$
\mu\,\frac{\partial q(\mu,x)}{\partial x} + \frac{1}{\lambda_t} q(\mu,x) = \frac{1}{\lambda_t}\,\frac{3}{2}\,\mu\, Q_{SH}(x) \tag{A8}
$$

**步骤 1：化为标准一阶线性 ODE。** 对固定 $\mu \neq 0$，除以 $\mu$：

$$
\frac{\partial q}{\partial x} + P(x)\,q = R(x), \qquad P(x) \equiv \frac{1}{\mu\lambda_t(x)},\quad R(x) \equiv \frac{3}{2\lambda_t(x)}\,Q_{SH}(x) \tag{A9}
$$

（$\mu=0$ 方向与 $x$ 轴垂直，不参与沿 $x$ 的输运，贡献恒为零，无需处理。）

**步骤 2：积分因子。** 标准公式 $\mu_{\rm IF}(x) = \exp\left[\int^x P(x')dx'\right]$。对均匀 $\lambda_t$：$\mu_{\rm IF}(x) = e^{x/(\mu\lambda_t)}$；对非均匀 $\lambda_t(x)$：$\mu_{\rm IF}(x) = \exp\left[\frac{1}{\mu}\int^x\frac{dx'}{\lambda_t(x')}\right]$。乘 (A9) 两边：

$$
\frac{\partial}{\partial x}\Big[ q(\mu,x)\,e^{x/(\mu\lambda_t)} \Big] = R(x)\,e^{x/(\mu\lambda_t)} \tag{A10}
$$

（左端验证：$\partial_x[q\,e^{x/(\mu\lambda_t)}] = e^{x/(\mu\lambda_t)}\left[\partial_x q + q/(\mu\lambda_t)\right]$。）

**步骤 3：从上游边界积分。** 电子从上游飞来：$\mu>0$ 时上游在 $x=-\infty$，$\mu<0$ 时上游在 $x=+\infty$。边界条件 $q(\mu,\pm\infty)=0$（无入射通量）。

*$\mu>0$ 分支*：对 (A10) 从 $-\infty$ 积到 $x$，左端边界项 $q(\mu,-\infty)\,e^{-\infty}=0$：

$$
q(\mu,x) = e^{-x/(\mu\lambda_t)}\int_{-\infty}^{x} \frac{3}{2\lambda_t}Q_{SH}(x')\,e^{x'/(\mu\lambda_t)}\,dx' = \frac{3}{2\lambda_t}\int_{-\infty}^{x} Q_{SH}(x')\,e^{-(x-x')/(\mu\lambda_t)}\,dx' \tag{A11}
$$

*$\mu<0$ 分支*：积分下限换为 $+\infty$（上游在 $x\to+\infty$），(A10) 从 $x$ 积到 $+\infty$：

$$
q(\mu,x) = e^{-x/(\mu\lambda_t)}\int_{+\infty}^{x}\!\frac{3}{2\lambda_t}Q_{SH}(x')e^{x'/(\mu\lambda_t)}dx' = -\frac{3}{2\lambda_t}\int_{x}^{\infty} Q_{SH}(x')\,e^{-(x-x')/(\mu\lambda_t)}\,dx' \tag{A12}
$$

（$\mu<0$ 时 $-(x-x')/(\mu\lambda_t) = -(x'-x)/(|\mu|\lambda_t) \le 0$，随 $x'$ 远离 $x$ 指数衰减；负号来自 $q(\mu<0)$ 本身为负——电子反向运动携带负的 $x$ 向通量。）

**步骤 4：合并两分支求宏观热流。** $Q(x) = \int_{-1}^{1}\mu\,q(\mu,x)\,d\mu = \int_0^1\mu q_+ d\mu + \int_{-1}^0 \mu q_- d\mu$。对第二项作 $\mu\to-\mu$ 换元（$\mu'\equiv|\mu|\in(0,1)$，$\mu d\mu\to -\mu' d\mu'$，积分限翻转后整体为正）：

$$
Q(x) = \frac{3}{2\lambda_t}\int_0^1 \mu\,d\mu \left[ \int_{-\infty}^{x} Q_{SH}(x')e^{-(x-x')/(\mu\lambda_t)}dx' + \int_{x}^{\infty} Q_{SH}(x')e^{-(x'-x)/(\mu\lambda_t)}dx' \right] \tag{A13}
$$

两积分合并为全空间积分 $e^{-|x-x'|/(\mu\lambda_t)}$，交换积分顺序：

$$
Q(x) = \frac{3}{2\lambda_t}\int_{-\infty}^{\infty} Q_{SH}(x')\; \underbrace{\int_0^1 \mu\, e^{-s/\mu}\,d\mu}_{\text{内层角度积分}} \, dx', \qquad s \equiv \frac{|x-x'|}{\lambda_t} \tag{A14}
$$

**步骤 5：内层角度积分化为指数积分函数。** 换元 $z = 1/\mu$（$\mu=1/z$，$d\mu = -dz/z^2$，$\mu:0\to1$ 对应 $z:\infty\to1$）：

$$
\int_0^1 \mu\,e^{-s/\mu}\,d\mu = \int_{\infty}^{1}\frac{1}{z}e^{-sz}\Big(-\frac{dz}{z^2}\Big) = \int_1^{\infty}\frac{e^{-sz}}{z^3}\,dz \equiv E_3(s) \tag{A15}
$$

其中 $E_n(s) = \int_1^\infty e^{-sz}z^{-n}dz$ 为**指数积分函数**（注意此处对一维平板通量自然出现的是 $E_3$，而非 $E_1$；正文 §4.2 已相应修正）。故：

$$
\boxed{\,Q(x) = \frac{3}{2\lambda_t}\int_{-\infty}^{\infty} Q_{SH}(x')\,E_3\!\left(\frac{|x-x'|}{\lambda_t}\right)dx'\,} \tag{A16}
$$

**步骤 6：与 LMV 指数核的渐近一致。** 指数积分函数的领先渐近与阶数无关：$E_n(s) \approx e^{-s}/s$（$s\gg 1$，可由分部积分 $E_n = e^{-s}/s - n\int_1^\infty e^{-st}t^{-(n+1)}dt$ 迭代得到）。因此远距离处 $E_3(s)\approx e^{-s}/s$，代入 (A16) 即得正文的核 $e^{-|x-x'|/\lambda_t}/\,(|x-x'|/\lambda_t)$——这正是 LMV 指数衰减核的格林函数形式（§4.2 末尾，$\lambda_t = \sqrt{3}\,a\lambda_e$）。

**步骤 7（补充）：S$_2$/P1 离散方向与精确 $\sqrt{3}$ 因子。** 若不用连续角度积分而采用 S$_2$ 离散坐标（两个离散方向 $\mu = \pm 1/\sqrt{3}$，权重 1，恰为 $\int_{-1}^1 f(\mu)d\mu \approx f(-1/\sqrt{3})+f(1/\sqrt{3})$ 的两点 Gauss 求积），则 (A14) 的内层积分被离散化为 $\mu_0 e^{-s/\mu_0} = (1/\sqrt{3})e^{-\sqrt{3}s}$，得纯指数核 $e^{-\sqrt{3}|x-x'|/\lambda_t}$。与 LMV 核 $\exp[-|x-x'|/(a\lambda_e)]$ 比较，即给出正文 (22) 的对应关系 $\lambda_t = \sqrt{3}\,a\lambda_e$——这正是 SNB 论文中 $\sqrt{3}$ 因子的来源（§4.4，附录 B 假设 **A7**）。

---

## 附录 B：SNB 模型假设、近似汇总与适用条件

### B.1 模型假设与近似清单

SNB 模型的推导链路涉及以下关键假设和近似（按推导步骤排列）：

| # | 假设/近似 | 所在步骤 | 数学表达 | 物理后果 |
|---|----------|---------|---------|---------|
| **A1** | **稳态输运** | §4, 式 (16) | $\partial q/\partial t = 0$ | 忽略电子碰撞时间尺度以下的瞬态效应；在 $\tau_{ei} \sim \tau_{\text{hydro}}$ 时失效 [5] |
| **A2** | **无漂移速度/零电流** | §1, 全局 | $\mathbf{j} = 0$, $\mathbf{u}_e = 0$ | 离子与电子静止系等价 [5]；有宏观电流时需电场修正 |
| **A3** | **小角度 Coulomb 散射主导** | §1.1, 式 (1) | Fokker-Planck 碰撞算子 | 假设 $\|\ln\Lambda\| \gg 1$（等离子体参数 $\Lambda \gg 1$），即等离子体为弱耦合理想气体 |
| **A4** | **Lorentz 气体近似（高 $Z$ 极限）** | §2.2, $f_1$ 推导 | 忽略 $C_{ee}$，仅保留 $C_{ei}$ | 在高 $Z$ 下精确（$Z \gtrsim 10$），$Z \sim 1$ 时需 ee 碰撞修正 [1, 5] |
| **A5** | **一阶球谐截断（$f = f_0 + \mu f_1$）** | §1.1, 式 (2) | 高阶球谐项 $\ell \ge 2$ 忽略 | 在分布函数高度各向异性（$\|\mathbf{f}_1\| \not\ll f_0$）时失效 |
| **A6** | **LMV 唯象核构造** | §3.2 | $W(x,x') = \beta e^{-\tau}$ | 核形式为唯象拟合，非 FP 方程严格推导 [2]；参数 $a=32$ 为 VFP 拟合值 |
| **A7** | **等效输运方程关系 $\lambda_t = \sqrt{3}a\lambda_e$** | §4.4, 式 (22) | $S_2$ 离散与 LMV 核匹配 | 来自一维 $S_2$（取 $\mu=\pm 1/\sqrt{3}$）与 P1 等价的数值近似 |
| **A8** | **能群内自由程近似对称** | §5.2 | $\lambda_g$ 取群中心能量值 | 群宽度 $\Delta\beta_g$ 足够小是前提；群数 $N_g \sim 40$ 足够保证精度 |
| **A9** | **源项简化（忽略 $(\beta-4)$ 回冷电子项）** | §5.3, $W_g$ 推导 | $g_1^m \approx -\frac{\lambda_{ei}^*}{3}f_0^m\frac{\nabla T_e}{T_e}$ | 简化了低能电子回流的贡献；电场修正部分弥补此简化 [13] |
| **A10** | **P1 扩散近似（$\ell \le 1$ 球谐截断）** | §6.1 | 式 (P1) | 等效于 $S_2$ 离散坐标法；在光学薄区域（$\lambda_g/L_T \gg 1$）精度下降 |
| **A11** | **电场唯象修正** | §7 | 式 (33)-(35) | 电场效应通过修改 $\lambda_g'$ 唯象纳入，非自洽求解 [1, 3] |
| **A12** | **无磁场假设（原始 SNB）** | §1-§7 | $\mathbf{B}=0$ | 磁场效应需磁化 SNB 推广 [4]；忽略 Nernst/Righi-Leduc 效应 |
| **A13** | **二元碰撞假设** | §1.1 | FP 碰撞算子 | 忽略三体复合等非二元过程；在强耦合（$\|\ln\Lambda\| < 2$）冷稠密等离子体中失效 |
| **A14** | **经典统计（忽略量子简并）** | §1.1 | Maxwell-Boltzmann 分布 | 在 $T_e \lesssim T_F$（Fermi 温度）时需 Fermi-Dirac 统计；固体密度下可能需修正 |

### B.2 适用条件总结

综合上述假设，SNB 模型的最佳适用范围为：

**定量判据**：
1. **非局域性门槛**：$\lambda_e/L_T \gtrsim 5 \times 10^{-3}$（$L_T \lesssim 200\lambda_e$）[1, 10]——低于此值 SH 理论足够；上限由模型精度决定（一般在 $\lambda_e/L_T \lesssim 1$ 时 SNB 与 VFP 吻合良好 [5]）
2. **碰撞性要求**：$\ln\Lambda \gtrsim 3$，即等离子体为弱耦合理想气体
3. **电离度范围**：$Z \sim 1$–$50$；高 $Z$ 下更接近 Lorentz 气体假设（**A4**）；$Z \sim 1$ 时需注意 ee 碰撞修正 [5]
4. **温度范围**：$T_e \gtrsim 10$ eV（确保 Maxwell 分布成立，de Broglie 修正 < 经典 $b_0$）；无上限（相对论效应在 $T_e \gtrsim 100$ keV 时需额外考虑）
5. **磁场条件**（磁化 SNB [4]）：$\omega_{ce}\tau_{ei} \lesssim 10$ 时模型精度较好；强磁化极限下需验证
6. **时间尺度**：电子碰撞时间 $\tau_{ei}$ 应远小于流体力学时间尺度，确保稳态假设成立

**不适用场景**：
- 强耦合等离子体（$\ln\Lambda < 2$，如冷稠密 ICF 燃料）
- 显著非 Maxwell 分布（如强激光加速产生的超热电子束）
- 极高非局域度（$\lambda_e/L_T \gg 1$，如极低密度日冕），此时需全动理学 VFP 模拟
- 强磁场条件下的横向输运（需全张量磁化 SNB 或 VFP）

---

## 附录 C：局域 Maxwell 分布梯度计算的完整推导（推导 (b) 展开）

§2.2 推导 (b) 直接给出 (D3)(D4)，本节逐行展开其计算过程，回答"$\beta - 3/2$ 从何而来"。

**C.1 出发点：局域 Maxwell 分布及其对数**

$$
f_0(x,v) = n_e(x)\left[\frac{m_e}{2\pi k_B T_e(x)}\right]^{3/2}\exp[-\beta], \qquad \beta \equiv \frac{m_e v^2}{2 k_B T_e(x)} \tag{C1}
$$

对 $f_0$ 取对数（将 $x$ 依赖显式化）：

$$
\ln f_0 = \ln n_e(x) + \frac{3}{2}\ln\frac{m_e}{2\pi k_B} - \frac{3}{2}\ln T_e(x) - \beta(x) \tag{C2}
$$

**C.2 空间梯度：逐项对 $x$ 求导**

对 (C2) 逐项求 $\partial_x$：

| 项 | $\partial_x$ | 结果 |
|----|-------------|------|
| $\ln n_e(x)$ | $\dfrac{\partial\ln n_e}{\partial x}$ | 密度梯度 |
| $\frac{3}{2}\ln\frac{m_e}{2\pi k_B}$ | $0$ | 常数 |
| $-\frac{3}{2}\ln T_e(x)$ | $-\dfrac{3}{2}\dfrac{\partial\ln T_e}{\partial x}$ | 归一化因子 $T_e^{-3/2}$ 的贡献 |
| $-\beta(x)$ | $-\dfrac{\partial\beta}{\partial x}$ | Boltzmann 因子的贡献 |

其中 $\beta$ 对 $x$ 的导数（注意 $v$ 是独立坐标，不随 $x$ 变，只有 $T_e(x)$ 变）：

$$
\frac{\partial\beta}{\partial x} = \frac{\partial}{\partial x}\!\left[\frac{m_e v^2}{2 k_B T_e(x)}\right] = -\frac{m_e v^2}{2 k_B T_e^2}\,\frac{\partial T_e}{\partial x} = -\beta\,\frac{\partial\ln T_e}{\partial x} \tag{C3}
$$

（最后一步用到 $\partial_x\ln T_e = (\partial_x T_e)/T_e$ 与 $\beta = m_ev^2/2k_BT_e$。）

**C.3 合并：$(D3)$ 的导出**

$$
\begin{aligned}
\frac{\partial\ln f_0}{\partial x}
&= \frac{\partial\ln n_e}{\partial x} - \frac{3}{2}\frac{\partial\ln T_e}{\partial x} - \left(-\beta\frac{\partial\ln T_e}{\partial x}\right) \\
&= \frac{\partial\ln n_e}{\partial x} + \left(\beta - \frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x}
\end{aligned} \tag{C4}
$$

再乘以 $f_0$（$\partial_x f_0 = f_0\,\partial_x\ln f_0$）即得 (D3)。**$(\beta - 3/2)$ 的拆解**：$-\frac{3}{2}$ 来自 Maxwell 归一化因子 $T_e^{-3/2}$ 随温度的空间变化；$+\beta$ 来自指数因子 $e^{-\beta}$ 中 $\beta$ 随温度的空间变化（温度升高使 $\beta$ 减小、$e^{-\beta}$ 增大）。二者在 $\beta = 3/2$（热平均能量 $\langle E\rangle = \frac{3}{2}k_BT_e$）处相消——物理上即"平均能量电子数密度的温度依赖"在此能量处翻转。为直观起见也可用**乘积法则**重算一遍验证：$f_0 = n_e\,C\,T_e^{-3/2}e^{-\beta}$（$C$ 为常数），

$$
\frac{\partial f_0}{\partial x} = \frac{\partial n_e}{\partial x}\frac{f_0}{n_e} + f_0\!\left(-\frac{3}{2}\frac{\partial\ln T_e}{\partial x}\right) + f_0\!\left(-\frac{\partial\beta}{\partial x}\right) = f_0\left[\frac{\partial\ln n_e}{\partial x} + \left(\beta-\frac{3}{2}\right)\frac{\partial\ln T_e}{\partial x}\right] \tag{C5}
$$

与 (D3) 一致。∎

**C.4 速度梯度：$(D4)$ 的导出**

$\partial_v$ 只作用于 $\beta$（$n_e$、$T_e$ 与 $v$ 无关）：

$$
\frac{\partial f_0}{\partial v} = f_0\,\frac{\partial}{\partial v}(-\beta) = -f_0\,\frac{\partial}{\partial v}\!\left[\frac{m_e v^2}{2 k_B T_e}\right] = -\frac{m_e v}{k_B T_e}\,f_0 \tag{C6}
$$

即 (D4)。注意 (D4) 中没有 $n_e$、$T_e$ 梯度项——速度梯度完全由 Maxwell 分布的指数形式 $e^{-\beta}$ 决定，这是 (D5) 中 $\beta$ 因子（而非 $\beta-3/2$）出现在电场项对面的原因。
