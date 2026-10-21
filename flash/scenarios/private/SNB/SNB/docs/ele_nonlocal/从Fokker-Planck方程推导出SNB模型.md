# 从 Fokker-Planck 方程推导出 SNB 非局域电子热传导模型

> **文档信息**
> - 主题：Schurtz–Nicolaï–Busquet (SNB) 非局域电子热传导模型的完整数学推导
> - 推导起点：电子 Fokker-Planck 动理学方程
> - 推导终点：SNB 多群扩散控制方程组
> - 日期：2026-08-08
> - 核心参考文献：Schurtz, Nicolaï & Busquet, *Phys. Plasmas* **7**, 4238 (2000)
> - 说明：本文档旨在提供可逐行人工核查的详细推导步骤

---

## 摘要

本文从电子 Fokker-Planck 动理学方程出发，系统推导 Schurtz–Nicolaï–Busquet (SNB) 非局域电子热传导模型 [1]。推导路径为：

1. 对 FP 方程作 P1 球谐展开，得到 $f_0$ 和 $\mathbf{f}_1$ 的矩方程；
2. 以局域 Maxwell 分布为零阶近似，得到 Spitzer-Härm (SH) 局域热传导理论；
3. 在陡温度梯度条件下 SH 理论失效，引入 LMV 非局域卷积公式 [2]；
4. 证明该卷积等价于某线性稳态输运方程的积分解；
5. **（核心步骤）** 利用 FP 方程的 Jacobian 线性化与迭代求解，在第一次迭代中直接导出 SNB 多群扩散方程组；
6. 结合 P1 扩散近似获得最终 Helmholtz 型控制方程。

本文特别详细展开第 5 步——从 FP 方程经 Jacobian 迭代直接得到 SNB 方程的数学过程 [1, §III.F]。

---

## 目录

1. [电子 Fokker-Planck 方程与 P1 球谐展开](#sec1)
2. [零阶解：Spitzer-Härm 局域热传导理论](#sec2)
3. [SH 理论失效与非局域卷积方法（LMV 模型）](#sec3)
4. [卷积的输运方程等价性（SNB 的核心洞察）](#sec4)
5. [从 FP 方程到 SNB 多群扩散方程——迭代推导](#sec5)
   - 5.1 问题的建立（三个残差函数）
   - 5.2 Jacobian 线性化与 Newton 迭代
   - 5.3 构造近似 Jacobian
   - 5.4 初始条件与第 $n=0$ 步残差
   - 5.5 第 $n=0$ 次迭代方程
   - 5.6 消去 $\Delta\mathbf{f}_1$ 得扩散方程
   - 5.7 源项物理含义（Joule 加热）
   - 5.8 归一化源函数 $g(v)$
   - 5.9 一阶修正热流
   - 5.10 与多群 SNB 方程的对应
6. [能量多群分解](#sec6)
7. [P1 扩散近似与最终控制方程](#sec7)
8. [电场自洽修正](#sec8)
9. [完整推导链路总结](#sec9)
10. [参考文献（含本地文献对应）](#sec10)

**附录**
- [附录 A：P1 球谐展开下矩方程的完整推导](#appA)
- [附录 B：(5.1c) 零电流条件的详细证明](#appB)
- [附录 C：Jacobian 矩阵的详细构造](#appC)
- [附录 D：$\partial C_0/\partial f_0 \approx -\nu_{ee}(v)$ 的详细由来](#appD)
- [附录 E：第 $n=0$ 次迭代方程的详细推导](#appE)
- [附录 F：近似 Jacobian (5.4) 的逐元素构造与 "$\times$" 记号](#appF)

---

<a name="sec1"></a>
## 1. 电子 Fokker-Planck 方程与 P1 球谐展开

### 1.1 Fokker-Planck 方程的一般形式

在完全电离的等离子体中，电子分布函数 $f(\mathbf{v}, \mathbf{r}, t)$ 满足 Fokker-Planck 方程 [6,7]：

$$
\frac{\partial f}{\partial t} + \mathbf{v} \cdot \nabla_r f - \frac{e}{m_e} (\mathbf{E} + \mathbf{v} \times \mathbf{B}) \cdot \nabla_v f = C_{ee}(f) + C_{ei}(f) \tag{1.1}
$$

其中：
- $\mathbf{v}$ 为电子速度矢量
- $e > 0$ 为元电荷，$m_e$ 为电子质量
- $\mathbf{E}$ 为低频自洽电场，由零电流条件 $j = 0$ 确定
- $\mathbf{B}$ 为磁场（原始 SNB 推导中假设 $\mathbf{B}=0$）
- $C_{ee}$ 和 $C_{ei}$ 分别为电子-电子和电子-离子 Fokker-Planck 碰撞算子

Schurtz 等 [1] 考虑的是**稳态情况**（$\partial f/\partial t = 0$，因电子碰撞时间远小于流体力学时间尺度），并假设电子分布函数绝热地、瞬时地调整到当地流体密度和温度条件。因此：

$$
\mathbf{v} \cdot \nabla f - \frac{e\mathbf{E}}{m_e} \cdot \nabla_v f = C(f) \tag{1.2}
$$

其中 $C(f) = C_{ee}(f) + C_{ei}(f)$。

### 1.2 P1 球谐展开

对激光等离子体中的电子，P1 球谐展开通常具有足够精度 [1,8]。设 $\mathbf{v} = v \mathbf{\Omega}$（$\mathbf{\Omega}$ 为单位方向矢量），展开为：

$$
f(\mathbf{v}, \mathbf{r}) = \frac{1}{4\pi} f_0(v, \mathbf{r}) + \frac{3}{4\pi} \mathbf{\Omega} \cdot \mathbf{f}_1(v, \mathbf{r}) \tag{1.3}
$$

其中：
- $f_0(v, \mathbf{r})$ 为各向同性部分（零阶 Legendre 分量）
- $\mathbf{f}_1(v, \mathbf{r})$ 为各向异性矢量扰动（一阶 Legendre 分量）

零阶和一阶角矩定义为：

$$
f_0(v, \mathbf{r}) \equiv \int_{4\pi} f(\mathbf{v}, \mathbf{r}) \, d^2\Omega, \qquad
\mathbf{f}_1(v, \mathbf{r}) \equiv \int_{4\pi} f(\mathbf{v}, \mathbf{r}) \, \mathbf{\Omega} \, d^2\Omega \tag{1.4}
$$

**展开的自洽性验证**：将 (1.3) 代入 (1.4)，利用球面积分恒等式：
- $\int d^2\Omega = 4\pi$
- $\int \mathbf{\Omega} \, d^2\Omega = \mathbf{0}$
- $\int \Omega_i \Omega_j \, d^2\Omega = \frac{4\pi}{3} \delta_{ij}$

可得 $\int f_0/4\pi \, d^2\Omega = f_0$ ✓ 且 $\int (3\mathbf{\Omega}\cdot\mathbf{f}_1/4\pi) \mathbf{\Omega} \, d^2\Omega = \mathbf{f}_1$ ✓。

### 1.3 角矩方程

将展开式 (1.3) 代入稳态 FP 方程 (1.2)，对立体角分别取零阶矩和一阶矩。

#### 零阶矩方程

对 (1.2) 作 $\int d^2\Omega$：

- 对流项：$\int \mathbf{v}\cdot\nabla f \, d^2\Omega = v \nabla \cdot \int \mathbf{\Omega} f \, d^2\Omega = v \nabla \cdot \mathbf{f}_1$
- 电场项：$-\frac{e}{m_e} \int \mathbf{E} \cdot \nabla_v f \, d^2\Omega$。利用 $\nabla_v = \mathbf{\Omega}\frac{\partial}{\partial v} + \frac{1}{v}\nabla_\Omega$，电场仅作用于各向异性部分，零阶矩积分为 $-\frac{e\mathbf{E}}{m_e v^2} \frac{\partial(v^2 \mathbf{f}_1)}{\partial v}$

得到：

$$
\boxed{v \, \nabla \cdot \mathbf{f}_1 - \frac{e\mathbf{E}}{m_e v^2} \frac{\partial(v^2 \mathbf{f}_1)}{\partial v} = C_0(f_0)} \tag{1.5}
$$

其中 $C_0(f_0)$ 为碰撞算子的零阶矩。这里假设 $C_0$ 仅依赖于各向同性部分 $f_0$（通过 Rosenbluth 势 [6]）。

#### 一阶矩方程

对 (1.2) 乘以 $\mathbf{\Omega}$ 后作 $\int \mathbf{\Omega} \, d^2\Omega$：

- 对流项：$\int \mathbf{\Omega}(\mathbf{v}\cdot\nabla f) d^2\Omega = \frac{v}{3} \nabla f_0$（利用 $\int \Omega_i \Omega_j d^2\Omega = \frac{4\pi}{3}\delta_{ij}$）
- 电场项：$-\frac{e\mathbf{E}}{3m_e} \frac{\partial f_0}{\partial v}$

得到：

$$
\boxed{\frac{v}{3} \nabla f_0 - \frac{e\mathbf{E}}{3m_e} \frac{\partial f_0}{\partial v} = \mathbf{C}_1(\mathbf{f}_1)} \tag{1.6}
$$

对于碰撞算子的一阶矩 $\mathbf{C}_1$，采用 Lorentz 气体近似（包括 e-e 扩散的有效 e-i 碰撞频率）：

$$
\mathbf{C}_1(\mathbf{f}_1) = -\nu_{ei}^*(v) \, \mathbf{f}_1 \tag{1.7}
$$

其中 $\nu_{ei}^*(v)$ 为有效电子-离子碰撞频率：

$$
\nu_{ei}^*(v) = (Z+1) \, \frac{4\pi n_e e^4 \ln\Lambda}{m_e^2 v^3} = \nu_{ei}(v) + \nu_{ee}^{\text{eff}}(v) \tag{1.8}
$$

#### 符号约定：$\nu_{ee}$ 与 $\nu_{ei}^*$ 的使用原则

> 本文档中 $\nu_{ee}$ 与 $\nu_{ei}^*$ 两个碰撞频率符号**分别对应分布函数的不同部分**，选择哪一个取决于被弛豫的对象。这一约定贯穿全文，特此集中说明（对应关系见附录 D.2 的物理推导）：

| 符号 | 定义 | 物理作用 | 使用场合 |
|------|------|---------|---------|
| $\nu_{ee}(v)$ | **e-e 碰撞频率**，$\nu_{ee}(v) = \frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3}$ | 电子间**能量交换** → $f_0$ 的**麦克斯韦化**（能量分布弛豫） | $f_0$（各向同性部分）的碰撞弛豫算子 $C_0$，以及 Jacobian 元 (1,1) 的 BGK 近似（附录 D） |
| $\nu_{ei}(v)$ | 纯 **e-i 碰撞频率** | 电子-离子**角度散射** → $\mathbf{f}_1$ 的动量弛豫 | 通常并入 $\nu_{ei}^*$ 使用（见 (1.8)） |
| $\nu_{ei}^*(v)$ | **有效 e-i 碰撞频率**，$\nu_{ei}^*(v) = (Z+1)\nu_{ee}(v)$ | $\mathbf{f}_1$（各向异性部分）的**动量/角度弛豫**（含 e-e 散射对角度弛豫的有效贡献） | $\mathbf{f}_1$ 的碰撞弛豫算子 $\mathbf{C}_1$（(1.7)）、一阶矩方程 (1.9b)、Jacobian 元 (2,2) |

**一句话原则**：**$f_0$（能量分布）的弛豫用 $\nu_{ee}$；$\mathbf{f}_1$（动量输运）的弛豫用 $\nu_{ei}^*$。**

**物理原因**（详细推导见附录 D）：
1. **e-e 碰撞主导 $f_0$ 的麦克斯韦化**：同质量粒子碰撞，每次碰撞能量交换比例 $\Delta E/E \sim O(1)$；而 e-i 碰撞每次能量交换仅 $\Delta E/E \sim m_e/m_i \sim 5\times10^{-4}$。因此 $f_0$（决定能量分布形状）的弛豫只能由 e-e 碰撞完成 → 用 $\nu_{ee}$。
2. **e-i 碰撞主导 $\mathbf{f}_1$ 的动量弛豫**：$\mathbf{f}_1$ 对应分布函数的角度各向异性（热流/电流的载体），其弛豫由角度散射决定。e-i 碰撞（离子电荷 $Z$ 散射强）与 e-e 碰撞（角度散射系数相同）共同贡献，有效频率为两者之和，归一化后给出 $(Z+1)$ 因子 → 用 $\nu_{ei}^* = \nu_{ei} + \nu_{ee}^{\text{eff}} = (Z+1)\nu_{ee}$ [1, §III.B]。
3. **Lorentz 气体极限**（$Z\to\infty$）：$\nu_{ei}^* \to Z\nu_{ee} \gg \nu_{ee}$——各向异性（$\mathbf{f}_1$）被快速抹平，而能量分布（$f_0$）缓慢弛豫，这正是高 $Z$ 等离子体的标准物理图像。

**读者速查**：遇到"$\Delta f_0$ 的弛豫 / $C_0$ / Jacobian (1,1) / $H_g$ 的耗散"→ $\nu_{ee}$；遇到"$\mathbf{f}_1$ 或 $\Delta\mathbf{f}_1$ 的弛豫 / $\mathbf{C}_1$ / 一阶矩方程 / Jacobian (2,2)"→ $\nu_{ei}^*$。

#### 矩方程汇总

总结 P1 展开下的零阶和一阶矩方程：


$$
\begin{align}
v \, \nabla \cdot \mathbf{f}_1 - \frac{e\mathbf{E}}{m_e v^2} \frac{\partial(v^2 \mathbf{f}_1)}{\partial v} &= C_0(f_0) \tag{1.9a} \\[6pt]
\frac{v}{3} \nabla f_0 - \frac{e\mathbf{E}}{3m_e} \frac{\partial f_0}{\partial v} &= -\nu_{ei}^*(v) \, \mathbf{f}_1 \tag{1.9b}
\end{align}
$$

物理量由分布函数的矩给出：
- 电流密度：$\mathbf{J} = -e \int \mathbf{v} f \, d^3v = -e \int \mathbf{f}_1 v^3 dv$
- 热流：$\mathbf{Q} = \frac{m_e}{2} \int v^2 \mathbf{v} f \, d^3v = \frac{m_e}{2} \int \mathbf{f}_1 v^5 dv$

---

<a name="sec2"></a>
## 2. 零阶解：Spitzer-Härm 局域热传导理论

### 2.1 Maxwell-Boltzmann 零阶分布

在 SH 理论中，假设 $f_0$ 为局域 Maxwell-Boltzmann 分布：

$$
f_0^{\text{MB}}(v; n_e(\mathbf{r}), T_e(\mathbf{r})) = n_e(\mathbf{r}) \left( \frac{m_e}{2\pi k_B T_e(\mathbf{r})} \right)^{3/2} \exp\left[ -\frac{m_e v^2}{2k_B T_e(\mathbf{r})} \right] \tag{2.1}
$$

在此假设下 $C_0(f_0^{\text{MB}}) = 0$（Maxwell 分布是碰撞算子的稳态解）。

### 2.2 零电流条件确定自洽电场

零电流条件 $\mathbf{J}=0$ 给出电场的约束方程。由电流定义：

$$
\mathbf{J} \propto \int \mathbf{f}_1 v^3 dv = 0
$$

利用 (1.9b) 解出 $\mathbf{f}_1$：

$$
\mathbf{f}_1 = -\frac{v}{3\nu_{ei}^*(v)} \nabla f_0^{\text{MB}} + \frac{e\mathbf{E}}{3m_e \nu_{ei}^*(v)} \frac{\partial f_0^{\text{MB}}}{\partial v} \tag{2.2}
$$

代入 $\partial f_0^{\text{MB}}/\partial v = -(m_e v/k_B T_e) f_0^{\text{MB}}$，乘以 $v^3$ 并对 $v$ 积分。零电流条件要求第二项（电场相关）精确抵消第一项中与密度梯度相关的部分，得到：

$$
\mathbf{E}^{\text{MB}} = \frac{k_B T_e}{e} \left( \frac{\nabla n_e}{n_e} + \frac{5}{2} \frac{\nabla T_e}{T_e} \right) \tag{2.3}
$$

更一般地，有 [1, Eq. (49)]：

$$
e\mathbf{E}^{\text{MB}} = k_B T_e \left( \frac{\nabla n_e}{n_e} + \frac{5}{2} \frac{\nabla T_e}{T_e} \right)
$$

**注意**：当考虑更精确的输运系数时，温度梯度前的系数改用与 $Z$ 相关的 $\gamma(Z)$ 函数 [9]。高 $Z$ 极限下 $\gamma \to 1 + 3/2 = 5/2$。

### 2.3 一阶扰动 $\mathbf{f}_1^{\text{MB}}$ 与 SH 热流

将 $f_0^{\text{MB}}$ 和 $\mathbf{E}^{\text{MB}}$ 代入 (2.2)：

$$
\mathbf{f}_1^{\text{MB}} = -\frac{v}{3\nu_{ei}^*(v)} \left( \frac{m_e v^2}{2k_B T_e} - 4 \right) f_0^{\text{MB}} \frac{\nabla T_e}{T_e} \tag{2.4}
$$

**推导**：

Step 1: $\nabla f_0^{\text{MB}} = f_0^{\text{MB}} \left[ \frac{\nabla n_e}{n_e} + \left(\frac{m_e v^2}{2k_B T_e} - \frac{3}{2}\right) \frac{\nabla T_e}{T_e} \right]$

Step 2: 计算 $\frac{v}{3} \nabla f_0^{\text{MB}} - \frac{e\mathbf{E}^{\text{MB}}}{3m_e} \frac{\partial f_0^{\text{MB}}}{\partial v}$：
- $\frac{e\mathbf{E}^{\text{MB}}}{3m_e} \frac{\partial f_0^{\text{MB}}}{\partial v} = -\frac{e\mathbf{E}^{\text{MB}}}{3m_e} \frac{m_e v}{k_B T_e} f_0^{\text{MB}}$
- 代入 (2.3) 并简化，密度梯度项精确抵消，得 $-\frac{v}{3} \left(\frac{m_e v^2}{2k_B T_e} - 4\right) f_0^{\text{MB}} \frac{\nabla T_e}{T_e}$

Step 3: 除以 $-\nu_{ei}^*(v)$ 得 (2.4)。

热流由 $\mathbf{f}_1$ 的五阶速度矩给出：

$$
\mathbf{Q}_{SH} = \frac{m_e}{2} \int_0^\infty \mathbf{f}_1^{\text{MB}}(v) \, v^5 dv = -\kappa_{SH} \nabla T_e \tag{2.5}
$$

SH 热导率：

$$
\kappa_{SH} = \frac{128}{3\pi} \xi(Z) \, n_e k_B v_T \lambda_{ei} \tag{2.6}
$$

其中 $\xi(Z) = (Z + 0.24)/(Z + 4.2)$ [10]，$v_T = \sqrt{k_B T_e/m_e}$。

Schurtz 等使用的实用形式 [1, Eq. (2)]：

$$
\boxed{\kappa_{SH} = 0.4 \frac{Z^*}{Z^* + 0.2 \ln(Z^* + 3.44)} \frac{20(2/\pi)^{3/2} k_B^{7/2} T_e^{5/2}}{m_e^{1/2} e^4 Z^* \ln\Lambda}} \tag{2.7}
$$

其中 $Z^* = \langle Z^2 \rangle / \langle Z \rangle$ 为有效离子电荷。

### 2.4 有效平均自由程

电子-离子和电子-电子的平均自由程 [1, Eq. (3)]：

$$
\lambda_{ei} = \frac{(k_B T_e)^2}{4\pi n_e e^4 \ln\Lambda}, \qquad \lambda_{ee} \approx Z \lambda_{ei} \tag{2.8}
$$

SNB 模型中采用的**有效平均自由程**为两者几何平均 [1, Eq. (3)]：

$$
\boxed{\lambda_e = \sqrt{\lambda_{ei} \lambda_{ee}} = (Z+1)^{-1/2} \frac{(k_B T_e)^2}{4\pi n_e e^4 \ln\Lambda}} \tag{2.9}
$$

---

<a name="sec3"></a>
## 3. SH 理论失效与非局域卷积方法（LMV 模型）

### 3.1 载热电子的自由程

热流积分中的权重函数比例于 $\beta^4(\beta-4)e^{-\beta}$（其中 $\beta = m_e v^2/(2k_B T_e)$），在 $\beta \approx 4$ 处达峰值 [1, §II.A]。因此载热电子的特征速度为 $v \approx 2.83 v_T$。

速度 $v$ 处电子的自由程 $\lambda(v) \propto v^4 \propto \beta^2$ [11]。以 $\beta=4$ 代入：

$$
\lambda(\beta=4) = 4\lambda_e \cdot 4^2 = 64 \lambda_e \tag{3.1}
$$

载热电子的自由程是热电子自由程的数十倍。当 $\lambda_e/L_T > 5 \times 10^{-3}$（即 $L_T < 200\lambda_e$）时，SH 理论显著偏离实际热流 [1,12]——此时超热电子（suprathermal electrons）可以穿越梯度区而不发生碰撞。

### 3.2 LMV 非局域卷积核

Luciani、Mora 和 Virmont [2] 提出的非局域热流卷积公式：

$$
\mathbf{Q}(\mathbf{r}) = \int_{4\pi} \mathbf{\Omega}\mathbf{\Omega} \, d^2\Omega \int_0^\infty W_0(\mathbf{r}, \mathbf{r}+s\mathbf{\Omega}) \, \mathbf{Q}_{SH}(\mathbf{r}+s\mathbf{\Omega}) \, \frac{ds}{\lambda_e(\mathbf{r}+s\mathbf{\Omega})} \tag{3.2}
$$

其中一维LMV核 [2]：

$$
W_0(x, x') = \beta \exp[-\tau(x, x')], \qquad \tau(x, x') = \frac{\left|\int_x^{x'} n_e(z)dz\right|}{a \, n_e(x') \, \lambda_e(x')} \tag{3.3}
$$

参数 $a = 32$ 通过 VFP 模拟拟合确定 [2]。$\tau$ 为光学深度，量化电子的碰撞衰减。

---

<a name="sec4"></a>
## 4. 卷积的输运方程等价性（SNB 的核心洞察）

Schurtz 等 [1] 的核心发现是：LMV 卷积 (3.2) 恰好是以下**线性稳态输运方程**的 Green 函数积分解：

$$
\boxed{\mathbf{\Omega} \cdot \nabla q(\mathbf{\Omega}, \mathbf{r}) + \frac{1}{\lambda_t(\mathbf{r})} q(\mathbf{\Omega}, \mathbf{r}) = \frac{1}{\lambda_t(\mathbf{r})} \frac{3}{4\pi} \mathbf{\Omega} \cdot \mathbf{Q}_{SH}(\mathbf{r})} \tag{4.1}
$$

其中 $q(\mathbf{\Omega}, \mathbf{r})$ 为**角通量**（angular flux），$\lambda_t(\mathbf{r})$ 为**输运平均自由程**。

### 4.1 形式解的推导（特征线法）

沿 $\mathbf{\Omega}$ 方向参数化路径：$\mathbf{r}(s) = \mathbf{r}_0 + s\mathbf{\Omega}$。引入光学深度：

$$
\tau(\mathbf{r}, \mathbf{r} - s\mathbf{\Omega}) \equiv \int_0^s \frac{ds'}{\lambda_t(\mathbf{r} - s'\mathbf{\Omega})} \tag{4.2}
$$

方程 (4.1) 沿特征线化为标准一阶线性 ODE：

$$
\frac{dq}{ds} + \frac{1}{\lambda_t} q = \frac{3}{4\pi\lambda_t} \mathbf{\Omega} \cdot \mathbf{Q}_{SH}
$$

积分因子 $\mu(s) = \exp[\tau(\mathbf{r}_0 + s\mathbf{\Omega}, \mathbf{r}_0)]$。乘以积分因子后左侧为全微分：

$$
\frac{d}{ds}\left[ q \, e^{\tau} \right] = \frac{3}{4\pi\lambda_t} \mathbf{\Omega} \cdot \mathbf{Q}_{SH} \, e^{\tau}
$$

从 $s = -\infty$（上游无源）积分到 $s = 0$ 得形式解：

$$
\boxed{q(\mathbf{\Omega}, \mathbf{r}) = \frac{3}{4\pi} \int_0^\infty e^{-\tau(\mathbf{r}, \mathbf{r}-s\mathbf{\Omega})} \, \mathbf{\Omega} \cdot \mathbf{Q}_{SH}(\mathbf{r}-s\mathbf{\Omega}) \, \frac{ds}{\lambda_t(\mathbf{r}-s\mathbf{\Omega})}} \tag{4.3}
$$

### 4.2 恢复宏观热流

宏观热流为角通量的一阶角矩：

$$
\mathbf{Q}_t(\mathbf{r}) = \int_{4\pi} q(\mathbf{\Omega}, \mathbf{r}) \, \mathbf{\Omega} \, d^2\Omega
$$

将 (4.3) 代入，作变量变换 $s\mathbf{\Omega} \to -s\mathbf{\Omega}$ 得：

$$
\boxed{\mathbf{Q}_t(\mathbf{r}) = \frac{3}{4\pi} \int_{4\pi} \mathbf{\Omega}\mathbf{\Omega} \, d^2\Omega \int_0^\infty e^{-\tau(\mathbf{r}, \mathbf{r}+s\mathbf{\Omega})} \, \mathbf{Q}_{SH}(\mathbf{r}+s\mathbf{\Omega}) \, \frac{ds}{\lambda_t(\mathbf{r}+s\mathbf{\Omega})}} \tag{4.4}
$$

这正是 (3.2) 的形式，对应核函数为 $W_0 = \exp[-\tau]$。在一维 slab 几何中通过 $S_2$ 离散（取 $\mu = \pm 1/\sqrt{3}$），可验证 $\lambda_t = \sqrt{3} a \lambda_e$ [1, Eq. (19)]。

---

<a name="sec5"></a>
## 5. 从 FP 方程到 SNB 多群扩散方程——迭代推导

> **这是本文档最核心的推导部分**，源自 Schurtz 等 [1, §III.F]。本节展示如何从 FP 方程出发，通过 Jacobian 线性化和迭代求解，在**第一次迭代**中直接获得 SNB 多群扩散方程组。这一推导不仅赋予了 SNB 模型坚实的动理学基础，也揭示了 $H_g(\mathbf{r})$ 的物理意义——$f_0$ 相对 Maxwell 分布的偏离。

### 5.1 问题的建立

在 ICF 等离子体中，$f_0$ 接近但不等同于 Maxwell 分布。设精确解为 $(f_0, \mathbf{f}_1, \mathbf{E})$，从 Maxwell 初始猜测 $(f_0^{\text{MB}}, \mathbf{f}_1^{\text{MB}}, \mathbf{E}^{\text{MB}})$ 出发，通过迭代修正逐步逼近精确解。

定义三个残差函数：

$$
\begin{align}
\mathcal{F}_0(f_0, \mathbf{f}_1, \mathbf{E}) &\equiv C_0(f_0) - v \, \nabla \cdot \mathbf{f}_1 + \frac{e\mathbf{E}}{m_e v^2} \frac{\partial(v^2 \mathbf{f}_1)}{\partial v} = 0 \tag{5.1a} \\[6pt]
\mathcal{F}_1(f_0, \mathbf{f}_1, \mathbf{E}) &\equiv -\nu_{ei}^*(v) \mathbf{f}_1 - \frac{v}{3} \nabla f_0 + \frac{e\mathbf{E}}{3m_e} \frac{\partial f_0}{\partial v} = 0 \tag{5.1b} \\[6pt]
\mathcal{F}_E(f_0, \mathbf{f}_1, \mathbf{E}) &\equiv \int \left[ v \nabla f_0 - \frac{e\mathbf{E}}{m_e} \frac{\partial f_0}{\partial v} \right] v^6 dv = 0 \tag{5.1c}
\end{align}
$$

其中 (5.1c) 是零电流条件的等价形式。由 $\mathbf{J} \propto \int \mathbf{f}_1 v^3 dv = 0$，代入 $\mathbf{f}_1 \propto 1/\nu_{ei}^*(v)$（见 1.9b），在 Lorentz 气体近似下 $\nu_{ei}^*(v) \propto v^{-3}$，故 $v^3/\nu_{ei}^* \propto v^6$——即积分中的 $v^6$ 因子来源于电流矩权重 $v^3$ 与碰撞频率分母 $1/\nu_{ei}^* \propto v^3$ 的乘积。

### 5.2 Jacobian 线性化与 Newton 迭代

#### (a) Newton 迭代法：从一元方程到函数方程

**一元情形**：求 $F(x)=0$ 的根。在 $x^n$ 处 Taylor 展开 $F(x^{n+1}) \approx F(x^n) + F'(x^n)\Delta x = 0$，解得增量 $\Delta x = -F(x^n)/F'(x^n)$，迭代 $x^{n+1} = x^n + \Delta x$。几何意义：用切线近似曲线，求切线与 $x$ 轴交点。

**多元情形**：求 $\mathbf{F}(\mathbf{X})=0$（$\mathbf{F},\mathbf{X}\in\mathbb{R}^m$）的根。同样 Taylor 展开，但导数推广为 Jacobian **矩阵** $[\partial\mathbf{F}/\partial\mathbf{X}]_{ij} = \partial F_i/\partial X_j$：

$$
\mathbf{F}(\mathbf{X}^{n+1}) \approx \mathbf{F}(\mathbf{X}^n) + \underbrace{\left[\frac{\partial\mathbf{F}}{\partial\mathbf{X}}\right]_{\mathbf{X}^n}}_{\mathcal{J}} \Delta\mathbf{X}^n = \mathbf{0} \quad\Rightarrow\quad \mathcal{J}\,\Delta\mathbf{X}^n = -\mathbf{F}(\mathbf{X}^n) \tag{5.2}
$$

**函数空间情形（本问题）**：本节的未知量不是有限维向量，而是**函数** $(f_0(v,\mathbf{r}), \mathbf{f}_1(v,\mathbf{r}), \mathbf{E}(\mathbf{r}))$——$f_0$ 和 $\mathbf{f}_1$ 是速度 $v$ 和位置 $\mathbf{r}$ 的函数，$\mathbf{E}$ 是 $\mathbf{r}$ 的函数。残差 $\mathcal{F}_0, \mathcal{F}_1, \mathcal{F}_E$ 同样是函数。此时 (5.2) 中的 $\mathcal{J}$ 推广为**线性算子矩阵**（Fréchet 导数），"矩阵乘法"变为"算子作用"。这就是 Jacobian 矩阵（5.3）的由来——它是 Newton 迭代法对函数方程的直接推广 [1, §III.F]。

#### (b) 矩阵中占位符 $(\cdot)$ 的含义

矩阵 (5.3) 中的 $(\cdot)$ 是**占位符**（placeholder），表示该矩阵元是一个**线性算子**，$(\cdot)$ 所在的**位置对应它将要作用的变量增量**。具体规则：

- 第 $i$ 行第 $j$ 列的矩阵元 $\mathcal{J}_{ij}$ 是 $\mathcal{F}_i$ 关于 $X_j$ 的 Fréchet 导数，它是一个**线性算子**；
- 当矩阵 $\mathcal{J}$ 乘以增量向量 $\Delta\mathbf{X} = (\Delta f_0, \Delta\mathbf{f}_1, \Delta\mathbf{E})^T$ 时，第 $i$ 行的结果是 $\sum_j \mathcal{J}_{ij}[\Delta X_j]$，即第 $i$ 个残差的线性化增量 $\Delta\mathcal{F}_i$；
- $(\cdot)$ 表示"把作用对象放在这里"：例如第一行第二列 $-v\nabla\cdot(\cdot)$ 作用在 $\Delta\mathbf{f}_1$ 上给出 $-v\nabla\cdot(\Delta\mathbf{f}_1)$；第二行第三列 $\frac{e(\cdot)}{3m_e}\frac{\partial f_0}{\partial v}$ 作用在 $\Delta\mathbf{E}$ 上给出 $\frac{e\Delta\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$（其中 $f_0$ 为当前迭代值）。

**关键**：若某矩阵元不含 $(\cdot)$，则该元是"普通函数/常数乘法"（如 $-\nu_{ei}^*(\cdot)$ 其实仍含占位符，表示乘法算子）；若某元含 $\nabla$ 或 $\partial/\partial v$ 等符号，则表示**微分算子**。

#### (c) 逐元素计算（Fréchet 导数）

对每个残差关于每个未知量求线性化，注意 $\mathcal{F}_i$ 对 $X_j$ 求导时其余变量视为固定：

**$\mathcal{F}_0 = C_0(f_0) - v\nabla\cdot\mathbf{f}_1 + \frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$**（即 (5.1a)）：

- 行 1 列 1：$\partial\mathcal{F}_0/\partial f_0 = \partial C_0/\partial f_0$。$C_0$ 是 $f_0$ 的非线性泛函（碰撞算子零阶矩），其 Fréchet 导数 $\partial C_0/\partial f_0$ 是线性算子（详见 §5.3 与附录 D）。
- 行 1 列 2：$\partial\mathcal{F}_0/\partial\mathbf{f}_1 = -v\nabla\cdot(\cdot) + \frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2(\cdot))}{\partial v}$。第一项来自 $-v\nabla\cdot\mathbf{f}_1$ 对 $\mathbf{f}_1$ 的线性依赖；第二项来自 $\frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$ 对 $\mathbf{f}_1$ 的线性依赖（$v^2\mathbf{f}_1$ 对 $v$ 的偏导也是线性算子）。
- 行 1 列 3：$\partial\mathcal{F}_0/\partial\mathbf{E} = \frac{e(\cdot)}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$。注意这里 $\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$ 是**已知函数**（当前迭代的 $\mathbf{f}_1$），故该元是乘法算子：作用在 $\Delta\mathbf{E}$ 上给出 $\frac{e\Delta\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$。

**$\mathcal{F}_1 = -\nu_{ei}^*\mathbf{f}_1 - \frac{v}{3}\nabla f_0 + \frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$**（即 (5.1b)）：

- 行 2 列 1：$\partial\mathcal{F}_1/\partial f_0 = -\frac{v}{3}\nabla(\cdot) + \frac{e\mathbf{E}}{3m_e}\frac{\partial}{\partial v}(\cdot)$。第一项来自 $-\frac{v}{3}\nabla f_0$；第二项来自 $\frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$（$\frac{\partial}{\partial v}$ 是微分算子）。
- 行 2 列 2：$\partial\mathcal{F}_1/\partial\mathbf{f}_1 = -\nu_{ei}^*(\cdot)$（乘法算子）。
- 行 2 列 3：$\partial\mathcal{F}_1/\partial\mathbf{E} = \frac{e(\cdot)}{3m_e}\frac{\partial f_0}{\partial v}$（$\frac{\partial f_0}{\partial v}$ 为已知函数，乘法算子）。

**$\mathcal{F}_E = \int [v\nabla f_0 - \frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v}]v^6 dv$**（即 (5.1c)）：

- 行 3 列 1：$\partial\mathcal{F}_E/\partial f_0 = \int v\nabla(\cdot)v^6 dv$。这是"先梯度、再对速度加权积分"的算子（输出为矢量）。
- 行 3 列 2：$\partial\mathcal{F}_E/\partial\mathbf{f}_1 = 0$（$\mathcal{F}_E$ 不显含 $\mathbf{f}_1$）。
- 行 3 列 3：$\partial\mathcal{F}_E/\partial\mathbf{E} = -\frac{e(\cdot)}{m_e}\int\frac{\partial f_0}{\partial v}v^6 dv$（$\int\frac{\partial f_0}{\partial v}v^6 dv$ 为已知标量，故为常数乘法算子）。

由此得到完整的 Jacobian 矩阵：

$$
\mathcal{J} = \begin{pmatrix}
\displaystyle \frac{\partial C_0}{\partial f_0} & -v\,\nabla\cdot(\cdot) + \frac{e\mathbf{E}}{m_e v^2}\frac{\partial v^2(\cdot)}{\partial v} & \displaystyle \frac{e(\cdot)}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v} \\[12pt]
\displaystyle \frac{v}{3}\nabla(\cdot) + \frac{e\mathbf{E}}{3m_e}\frac{\partial}{\partial v}(\cdot) & -\nu_{ei}^*(\cdot) & \displaystyle \frac{e(\cdot)}{3m_e}\frac{\partial f_0}{\partial v} \\[12pt]
\displaystyle \int v \nabla(\cdot) v^6 dv & 0 & \displaystyle -\frac{e(\cdot)}{m_e} \int \frac{\partial f_0}{\partial v} v^6 dv
\end{pmatrix} \tag{5.3}
$$

**注意**：(5.3) 中第二行第一列写为 $\frac{v}{3}\nabla(\cdot) + \frac{e\mathbf{E}}{3m_e}\frac{\partial}{\partial v}(\cdot)$——这里 $\mathbf{E}$ 前的系数取当前迭代值（初值为 $\mathbf{E}^{\text{MB}}$）。上述逐元素计算的完整代数细节见附录 C。

$\mathcal{J}$ 作用于完整位形空间，直接求逆不可行。需要构造一个**可解析处理的近似 Jacobian** $\mathcal{L}$。

### 5.3 构造近似 Jacobian

利用以下物理考虑简化 $\mathcal{J}$ [1]:

1. **电场项在高能端可忽略**：所有含 $\mathbf{E}$ 的项相对于碰撞或空间导数项量级为 $k_B T_e/(m_e v^2)$。在高速度端 $v \gg v_T$ 时这些小量，可从 Jacobian 中略去——即电场取前次迭代值。

2. **$\partial C_0/\partial f_0$ 的近似**：用电子-电子的速度依赖碰撞频率 $\nu_{ee}(v)$ 近似 [13]：

   $$
   \frac{\partial C_0}{\partial f_0} \approx -\nu_{ee}(v), \qquad \nu_{ee}(v) \propto \frac{1}{v^3}
   $$

   **物理由来**（完整推导见附录 D）：
   - $C_0(f_0)$ 是**电子-电子碰撞算子**（Landau/Rosenbluth 积分算子）的零阶角矩。它是 $f_0$ 趋向 Maxwell 分布（麦克斯韦化）的主导机制——电子-离子碰撞每次交换的能量比例仅为 $m_e/m_i \sim 10^{-3}$，对 $f_0$ 的能量弛豫几乎无效；而电子-电子碰撞交换能量比例与 $Z$ 同阶，主导 $f_0$ 的弛豫。
   - 关键性质 1：Maxwell 分布是碰撞平衡态，$C_0(f_0^{\text{MB}}) = 0$。
   - 关键性质 2：对 Maxwell 附近的小扰动 $f_0 = f_0^{\text{MB}} + \delta f_0$，线性化 $C_0(f_0) \approx \left.\frac{\partial C_0}{\partial f_0}\right|_{f_0^{\text{MB}}} \delta f_0$。
   - 由于 Landau 算子在速度空间是**积分算子**（非局部），直接保留会破坏 Jacobian 的局部性。**弛豫时间近似（BGK 型近似）**将积分算子替换为局部乘法算子：$\left.\frac{\partial C_0}{\partial f_0}\right|_{f_0^{\text{MB}}}\delta f_0 \approx -\nu_{ee}(v)\delta f_0$，其中 $\nu_{ee}(v)$ 为速度依赖的 e-e 碰撞频率。
   - 速度标度 $\nu_{ee}(v) \propto v^{-3}$ 的来源：Coulomb 散射截面 $\sigma \propto v^{-4}$，碰撞频率 $\nu = n\sigma v \propto v^{-3}$。精确形式 $\nu_{ee}(v) = \frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3}$（详见附录 D）。
   - 物理图像：$1/\nu_{ee}(v)$ 是速度 $v$ 处电子的麦克斯韦化时间。此近似正是 Schurtz 等 [1, §III.F] 所采用的："$\partial C_0/\partial f_0$ is correctly approximated by the electron–electron velocity dependent collision frequency $-\nu_{ee}(v)$"。

3. **碰撞频率的显式表达**：

   $$
   \nu_{ei}^*(v) = \frac{v}{\lambda_{ei}^*(v)}, \qquad \nu_{ee}(v) = \frac{v}{\lambda_{ee}(v)} = \frac{v}{Z \lambda_{ei}(v)}
   $$

   其中速度依赖的 e-i 自由程 $\lambda_{ei}(v) = (v/v_T)^4 \lambda_{ei}$，有效自由程 $\lambda(v) \equiv \sqrt{\lambda_{ee}(v)\lambda_{ei}(v)} \propto v^4$。

在上述简化下，近似 Jacobian $\mathcal{L}$ 为：

$$
\mathcal{L} \approx \begin{pmatrix}
-\nu_{ee}(v) & -v\,\nabla\cdot & 0 \\[6pt]
-\frac{v}{3}\nabla & -\nu_{ei}^*(v) & 0 \\[6pt]
0 & 0 & \times
\end{pmatrix} \tag{5.4}
$$

其中 "$\times$" 表示该矩阵元被置空——电场增量 $\Delta\mathbf{E}$ 不由矩阵求解，而由独立的解析公式（Schurtz 原文 Eq.(54)，见附录 F.1 与 F.3）在每轮迭代后显式更新。**每个矩阵元的详细替换过程见附录 F**（从精确 Jacobian (5.3) 到近似 Jacobian (5.4) 的逐元素对照表）。

**同一矩阵中 $\nu_{ee}$ 与 $\nu_{ei}^*$ 并置的原因**：矩阵元 (1,1)（$-\nu_{ee}$）作用于 $\Delta f_0$——$f_0$ 的偏离由 e-e 碰撞麦克斯韦化（用 $\nu_{ee}$）；矩阵元 (2,2)（$-\nu_{ei}^*$）作用于 $\Delta\mathbf{f}_1$——各向异性扰动由 e-i 有效碰撞弛豫（用 $\nu_{ei}^*$）。两频率作用于**不同对象**，故在同一 Jacobian 中共存（见 §1.3 符号约定）。

### 5.4 初始条件与第 $n=0$ 步的残差

初始猜测：
$$
f_0^0 = f_0^{\text{MB}}, \quad \mathbf{f}_1^0 = \mathbf{f}_1^{\text{MB}}, \quad \mathbf{E}^0 = \mathbf{E}^{\text{MB}}
$$

由构造，$\mathcal{F}_1^0 = 0$ 和 $\mathcal{F}_E^0 = 0$（因为 $\mathbf{f}_1^{\text{MB}}$ 和 $\mathbf{E}^{\text{MB}}$ 精确满足一阶矩方程和零电流条件）。**但 $\mathcal{F}_0^0 \neq 0$**：虽然 $C_0(f_0^{\text{MB}}) = 0$，但对流项和电场项的不为零贡献导致残差非零。

$$
\mathcal{F}_0^0 = -v \, \nabla \cdot \mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2} \frac{\partial(v^2 \mathbf{f}_1^{\text{MB}})}{\partial v} \tag{5.5}
$$

### 5.5 第 $n=0$ 次迭代方程（关键步骤）

将近似 Jacobian (5.4) 与残差代入线性化方程 (5.2)，逐行展开矩阵乘法 $\mathcal{L}\,\Delta\mathbf{X}^0 = -\mathbf{F}(\mathbf{X}^0)$（完整推导见附录 E）：

$$
\begin{pmatrix}
-\nu_{ee}(v) & -v\nabla\cdot & 0 \\
-\frac{v}{3}\nabla & -\nu_{ei}^*(v) & 0 \\
0 & 0 & \times
\end{pmatrix}
\begin{pmatrix}
\Delta f_0 \\ \Delta\mathbf{f}_1 \\ \Delta\mathbf{E}
\end{pmatrix}
= -
\begin{pmatrix}
\mathcal{F}_0^0 \\ \mathcal{F}_1^0 \\ \mathcal{F}_E^0
\end{pmatrix}
\tag{5.6}
$$

**第 $n=0$ 步残差分析**：

- $\mathcal{F}_1^0 = 0$：$\mathbf{f}_1^{\text{MB}}$ 与 $\mathbf{E}^{\text{MB}}$ 是 (1.9b) 的精确解（见 §2.3 的构造），故一阶矩残差为零；
- $\mathcal{F}_E^0 = 0$：$\mathbf{E}^{\text{MB}}$ 由零电流条件确定（§2.2），故电流残差为零；
- $\mathcal{F}_0^0 \neq 0$：虽然 $C_0(f_0^{\text{MB}})=0$，但 (5.1a) 中对流项 $-v\nabla\cdot\mathbf{f}_1^{\text{MB}}$ 与电场项 $\frac{e\mathbf{E}^{\text{MB}}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v}$ 均为非零——这正是"陡温度梯度下 Maxwell 分布无法满足零阶矩方程"的数学体现（见 (5.5)）。

**矩阵乘法逐行展开**：

- 第 1 行：$-\nu_{ee}\Delta f_0 - v\nabla\cdot(\Delta\mathbf{f}_1) = -\mathcal{F}_0^0$，两边乘 $-1$ 得：
  $$
  \nu_{ee}(v)\Delta f_0 + v\nabla\cdot(\Delta\mathbf{f}_1) = \mathcal{F}_0^0 = -v\nabla\cdot\mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v}
  $$
- 第 2 行：$-\frac{v}{3}\nabla(\Delta f_0) - \nu_{ei}^*\Delta\mathbf{f}_1 = -\mathcal{F}_1^0 = 0$，移项得：
  $$
  \nu_{ei}^*(v)\Delta\mathbf{f}_1 = -\frac{v}{3}\nabla(\Delta f_0)
  $$
- 第 3 行：$\mathcal{F}_E^0 = 0$ 且近似 Jacobian 第三行置为 $\times$（电场不参与本轮迭代，见 Schurtz 原文 Eq.(54) 的电场更新公式），故 $\Delta\mathbf{E}$ 本轮不求解。

整理为标准形式 [1, Eqs. (55)-(56)]：

$$
\boxed{\nu_{ee}(v) \, \Delta f_0 + v \, \nabla \cdot (\Delta \mathbf{f}_1) = -v \, \nabla \cdot \mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2} \frac{\partial(v^2 \mathbf{f}_1^{\text{MB}})}{\partial v}} \tag{5.6a}
$$

$$
\boxed{\nu_{ei}^*(v) \, \Delta \mathbf{f}_1 = -\frac{v}{3} \nabla (\Delta f_0)} \tag{5.6b}
$$

**物理图像**：(5.6a) 表明 $\Delta f_0$（$f_0$ 对 Maxwell 分布的偏离）由空间不均匀性（$\nabla\cdot\mathbf{f}_1^{\text{MB}}$）和电场做功（Joule 项）驱动，并被 e-e 碰撞（$\nu_{ee}$）弛豫——**为何用 $\nu_{ee}$**：$\Delta f_0$ 是各向同性部分 $f_0$ 的偏离，其恢复平衡（麦克斯韦化）只能由 e-e 碰撞完成（见 §1.3 符号约定）。(5.6b) 表明 $\Delta\mathbf{f}_1$（热流修正）直接由 $\Delta f_0$ 的梯度驱动——**为何用 $\nu_{ei}^*$**：$\Delta\mathbf{f}_1$ 是各向异性（动量输运）扰动，其弛豫由角度散射（e-i 为主、含 e-e 有效贡献）决定（见 §1.3 符号约定）。高能电子的自由程更长，将 $\Delta f_0$ 的影响"非局域"地传播开来。

### 5.6 消去 $\Delta \mathbf{f}_1$ 得到 $\Delta f_0$ 的扩散方程

由 (5.6b)：$\Delta \mathbf{f}_1 = -\frac{v}{3\nu_{ei}^*(v)} \nabla (\Delta f_0)$

定义碰撞平均自由程：

$$
\lambda_{ei}(v) \equiv \frac{v}{\nu_{ei}^*(v)}, \quad \lambda_{ee}(v) \equiv \frac{v}{\nu_{ee}(v)} = Z \lambda_{ei}(v), \quad \lambda(v) \equiv \sqrt{\lambda_{ee}(v) \lambda_{ei}(v)} \tag{5.7}
$$

代入 (5.6a)：

$$
\nu_{ee} \Delta f_0 - v \nabla \cdot \left( \frac{v}{3\nu_{ei}^*} \nabla (\Delta f_0) \right) = \text{RHS}
$$

即：

$$
\frac{v}{\lambda_{ee}} \Delta f_0 - \nabla \cdot \left( \frac{v^2}{3\nu_{ei}^*} \nabla (\Delta f_0) \right) = \text{RHS}
$$

注意到 $v^2/\nu_{ei}^* = v^3 / (v/\lambda_{ei})^{-1}$，整理得：

$$
\frac{v}{\lambda_{ee}} \Delta f_0 - \nabla \cdot \left( \frac{v \lambda_{ei}}{3} \nabla (\Delta f_0) \right) = \text{RHS}
$$

两边乘以 $m_e v^4/2$（使方程与能量流关联）：

$$
\frac{m_e v^5}{2 \lambda_{ee}} \Delta f_0 - \nabla \cdot \left( \frac{m_e v^5 \lambda_{ei}}{6} \nabla (\Delta f_0) \right) = \frac{m_e v^4}{2} \cdot \text{RHS}
$$

利用 $\lambda_{ee} = Z \lambda_{ei}$ 和 $\lambda(v) = \sqrt{Z} \lambda_{ei}(v)$，可得三个自由程之间的换算关系：

$$
\lambda_{ei}(v) = \frac{\lambda(v)}{\sqrt{Z}}, \qquad \lambda_{ee}(v) = \sqrt{Z} \, \lambda(v) \tag{5.7b}
$$

**验证**：$\sqrt{\lambda_{ee}\lambda_{ei}} = \sqrt{(Z\lambda_{ei})\lambda_{ei}} = \sqrt{Z}\lambda_{ei} = \lambda$ ✓。

**严格代数展开**：将 (5.6b) 代入 (5.6a)，并用 (5.7b) 将 $\nu_{ee} = v/\lambda_{ee} = v/(\sqrt{Z}\lambda)$、$\lambda_{ei} = \lambda/\sqrt{Z}$ 代入：

$$
\frac{v}{\sqrt{Z}\,\lambda}\Delta f_0 - \nabla\cdot\left(\frac{v\lambda}{3\sqrt{Z}}\nabla(\Delta f_0)\right) = \mathcal{F}_0^0
$$

两边乘以 $m_e v^4/2$，利用 (5.8) 的 $\mathcal{H} = \frac{m_e}{2}\sqrt{Z}v^5\Delta f_0$（即 $\Delta f_0 = 2\mathcal{H}/(m_e\sqrt{Z}v^5)$），注意 $v^5$ 与空间坐标无关、可移入 $\nabla$ 内：

- 吸收项：$\frac{m_e v^4}{2}\cdot\frac{v}{\sqrt{Z}\lambda}\Delta f_0 = \frac{m_e v^5}{2\sqrt{Z}\lambda}\Delta f_0 = \frac{1}{Z\lambda}\mathcal{H}$
- 扩散项：$\frac{m_e v^4}{2}\nabla\cdot\left(\frac{v\lambda}{3\sqrt{Z}}\nabla(\Delta f_0)\right) = \nabla\cdot\left(\frac{\lambda}{3Z}\nabla\mathcal{H}\right)$

即严格代数给出 $[\frac{1}{Z\lambda} - \nabla\cdot\frac{\lambda}{3Z}\nabla]\mathcal{H} = \frac{m_e}{2}v^4\mathcal{F}_0^0$，整体乘以 $Z$ 后算子为 $[\frac{1}{\lambda} - \nabla\cdot\frac{\lambda}{3}\nabla]$。

**与 Schurtz 原文 Eq.(57) 的约定衔接**：Schurtz 等 [1, Eqs. (55)–(57)] 从 (5.6a)(5.6b) 直接写出 $(1/\lambda - \nabla\cdot(\lambda/3)\nabla)\mathcal{H}$（无 $1/Z$ 因子），这意味着原文在自由程标度上隐含了 **$Z$ 因子吸收**的约定——等效于直接采用 $\nu_{ee}(v) = \nu_{ei}'(v) = \sqrt{Z}v/\lambda(v)$ 的统一碰撞频率标度（e-e 与 e-i 弛豫频率同阶；$Z\sim1$ 时严格成立，高 $Z$ 时该约定把 $Z$ 因子并入 $\lambda$ 的定义，见附录 D.5）。在原文约定下：

$$
\frac{\sqrt{Z}v}{\lambda}\Delta f_0 - \nabla\cdot\left(\frac{v\lambda}{3\sqrt{Z}}\nabla(\Delta f_0)\right) = \mathcal{F}_0^0
$$

乘以 $m_e v^4/2$ 后（用 (5.8)）：

- 吸收项：$\frac{m_e v^4}{2}\cdot\frac{\sqrt{Z}v}{\lambda}\Delta f_0 = \frac{1}{\lambda}\cdot\frac{m_e\sqrt{Z}v^5}{2}\Delta f_0 = \frac{\mathcal{H}}{\lambda}$
- 扩散项：$\frac{m_e v^4}{2}\nabla\cdot\left(\frac{v\lambda}{3\sqrt{Z}}\nabla(\Delta f_0)\right) = \nabla\cdot\left(\frac{\lambda}{3}\cdot\frac{m_e\sqrt{Z}v^5}{2}\nabla(\Delta f_0)\right) = \nabla\cdot\left(\frac{\lambda}{3}\nabla\mathcal{H}\right)$

（注意此处 $\mathcal{H}$ 定义 (5.8) 中已有的 $\sqrt{Z}$ 因子与扩散项中的 $1/\sqrt{Z}$ 恰好抵消，这正是 $\mathcal{H} \propto \sqrt{Z}v^5\Delta f_0$ 这一选择的动机。）

由此直接得到与 Schurtz 原文 Eq.(57) 完全一致的算子形式：

$$
\boxed{\left[ \frac{1}{\lambda(v)} - \nabla \cdot \frac{\lambda(v)}{3} \nabla \right] \mathcal{H}(v, \mathbf{r}) = \frac{m_e}{2} v^4 \cdot \mathcal{F}_0^0} \tag{5.9}
$$

**符号核对**：由 (5.5)，$\mathcal{F}_0^0 = -v\nabla\cdot\mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v}$，因此

$$
\frac{m_e}{2}v^4\mathcal{F}_0^0 = -\frac{m_e}{2}v^5\nabla\cdot\mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{2}v^2\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v}
$$

利用 $v^5\nabla\cdot\mathbf{f}_1 = \nabla\cdot(v^5\mathbf{f}_1)$（$v^5$ 无空间依赖），恰好与 Schurtz 原文 Eq.(57) 右侧 $- \frac{m_e}{2}\nabla\cdot(v^5 f_1^{mb}) + \frac{eE^{mb}}{2}v^2\frac{\partial(v^2 f_1^{mb})}{\partial v}$ 完全一致。✓

### 5.7 源项的物理含义

由 (5.5) 与 (5.9)，源项可显式展开为 [1, Eq. (57)]：

$$
\text{RHS} = \frac{m_e}{2} v^4 \mathcal{F}_0^0 = -\frac{m_e}{2} \left[ v^5 \nabla \cdot \mathbf{f}_1^{\text{MB}} - \frac{e\mathbf{E}^{\text{MB}}}{m_e} v^2 \frac{\partial(v^2 \mathbf{f}_1^{\text{MB}})}{\partial v} \right]
$$

（上式的核对：$\frac{m_e}{2}v^4\mathcal{F}_0^0 = \frac{m_e}{2}v^4[-v\nabla\cdot\mathbf{f}_1^{MB} + \frac{e\mathbf{E}^{MB}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{MB})}{\partial v}] = -\frac{m_e v^5}{2}\nabla\cdot\mathbf{f}_1^{MB} + \frac{e\mathbf{E}^{MB}v^2}{2}\frac{\partial(v^2\mathbf{f}_1^{MB})}{\partial v}$，与 Schurtz 原文 Eq.(57) 右侧一致。）

第一项的速度积分为 $-\nabla \cdot \mathbf{Q}_{SH}$（SH 热流散度的负值，利用 $Q_{SH} = \frac{m_e}{2}\int v^5 f_1^{MB}dv$）。第二项为 Joule 加热项：

$$
\frac{e\mathbf{E}^{\text{MB}}}{2}\int_0^\infty v^2 \frac{\partial(v^2 \mathbf{f}_1^{\text{MB}})}{\partial v} dv = \frac{e\mathbf{E}^{\text{MB}}}{2}\left[ v^4 \mathbf{f}_1^{\text{MB}} \right]_0^\infty - \frac{e\mathbf{E}^{\text{MB}}}{2}\int_0^\infty 4 v^3 \mathbf{f}_1^{\text{MB}} dv = -2e\mathbf{E}^{\text{MB}} \int_0^\infty v^3 \mathbf{f}_1^{\text{MB}} dv
$$

（分部积分，边界项 $\left[v^4\mathbf{f}_1^{MB}\right]_0^\infty = 0$。）由于 $\mathbf{J} = -e\int\mathbf{f}_1 v^3 dv$（见 (1.9)），上式正比于 $\mathbf{J}\cdot\mathbf{E}^{\text{MB}}$。在零电流条件 $\mathbf{J}=0$ 下 **Joule 加热项的总速度积分为零**——但在每一速度群内贡献非零（在低能端 $\beta<2.44$ 为正，高能端为负）。

因此源项的**总速度积分**为：

$$
\int_0^\infty \text{RHS} \, dv = -\nabla \cdot \mathbf{Q}_{SH} + (\propto \mathbf{J}\cdot\mathbf{E}^{\text{MB}}) \xrightarrow{\mathbf{J}=0} -\nabla \cdot \mathbf{Q}_{SH} \tag{5.10}
$$

### 5.8 引入归一化源函数 $g(v)$

由 (5.9) 与 (5.10) 的对比，源项可写成可分离形式 [1, Eq. (58)]：

$$
\frac{m_e}{2} v^4 \cdot \mathcal{F}_0^0 = -\nabla \cdot \left[ g(v) \mathbf{Q}_{SH} \right] \tag{5.11}
$$

其中 $g(v)$ 是归一化到 1 的速度分布函数（$\int_0^\infty g(v)dv = 1$，保证两侧速度积分均为 $-\nabla\cdot\mathbf{Q}_{SH}$）。**注意**：$g(v)$ 不仅仅是 SH 热流被积函数 $v^9(v^2/v_T^2 - 4)e^{-v^2/v_T^2}$，因为 Joule 加热项改变了速度空间中的源项分布——将主导速度从热流主导速度向下偏移 [1,13]。这一效应在 Fokker-Planck 模拟中已被数值证实。

### 5.9 一阶修正后的热流

修正后的 $\mathbf{f}_1$ 为 $\mathbf{f}_1^1 = \mathbf{f}_1^{\text{MB}} + \Delta \mathbf{f}_1$。一阶热流为：

$$
\begin{aligned}
\mathbf{Q}^{(1)} &= \frac{m_e}{2} \int \mathbf{f}_1^1 v^5 dv \\
&= \frac{m_e}{2} \int \mathbf{f}_1^{\text{MB}} v^5 dv + \frac{m_e}{2} \int \Delta \mathbf{f}_1 v^5 dv \\
&= \mathbf{Q}_{SH} + \frac{m_e}{2} \int \left( -\frac{v}{3\nu_{ei}^*} \nabla (\Delta f_0) \right) v^5 dv \\
&= \mathbf{Q}_{SH} - \frac{m_e}{2} \int \frac{v^5 \lambda_{ei}}{3} \nabla (\Delta f_0) dv
\end{aligned}
$$

（最后一步利用 $\nu_{ei}^* = v/\lambda_{ei}$ 得 $v^6/\nu_{ei}^* = v^5\lambda_{ei}$。）结合定义 (5.8)（$\mathcal{H} = \frac{m_e}{2}\sqrt{Z}v^5\Delta f_0$）并遵循 §5.6 中与 Schurtz 原文 Eq.(57) 一致的**自由程标度约定**（$\lambda_{ei} = \lambda/\sqrt{Z}$，$Z$ 因子由 $\mathcal{H}$ 定义中的 $\sqrt{Z}$ 因子吸收——注意 $\frac{m_e}{2}\sqrt{Z}v^5\nabla(\Delta f_0) = \nabla\mathcal{H}$，因 $v^5$ 与空间坐标无关），一阶热流化为 Schurtz 原文 Eq.(59) 的形式：

$$
\boxed{\mathbf{Q}^{(1)} = \mathbf{Q}_{SH} - \int_0^\infty \frac{\lambda(v)}{3} \nabla \mathcal{H}(v, \mathbf{r}) \, dv} \tag{5.12}
$$

**物理意义**：$\mathbf{Q}^{(1)}$ 由局域 SH 热流减去一个**非局域修正项**构成——该修正项正比于 $\mathcal{H}$（$f_0$ 对 Maxwell 分布的偏离）的梯度，以 $\lambda(v)/3$ 为扩散系数。这正是 SNB 多群方程 (7.5) 的连续速度形式。

### 5.10 与多群 SNB 方程的严格对应

将速度空间离散为 $N_g$ 群，每群的 $\lambda_g$ 和源项权重 $W_g$ 对应的积分形式即为 SNB 方程 (6.4) 和 (7.5)。**所以 SNB 多群扩散方程 (7.4) 就是 Newton 迭代在 $n=0 \to n=1$ 步的直接推论！**

**物理诠释**：
- $H_g(\mathbf{r})$ 正比于该能量群内 $f_0$ 对 Maxwell 分布的偏离 $\Delta f_0$
- 在陡温度梯度区，$\Delta f_0 \neq 0$ → $\nabla H_g \neq 0$ → 非局域修正不为零
- 在平滑梯度极限下，$\Delta f_0 \to 0$ → $H_g \to 0$ → $\mathbf{Q}_{SNB} \to \mathbf{Q}_{SH}$

---

<a name="sec6"></a>
## 6. 能量多群分解

### 6.1 群结构与群自由程

定义无量纲能量 $\beta \equiv E/(k_B T_e) = m_e v^2/(2k_B T_e)$。将能量轴离散为 $N_g$ 群，第 $g$ 群边界为 $\beta_{g-1}$ 和 $\beta_g$，群中心 $\beta_{g-1/2} = (\beta_{g-1} + \beta_g)/2$。

**群平均自由程**（与速度的依赖关系 $\lambda(v) \propto v^4 \propto \beta^2$）：

$$
\boxed{\lambda_g(\mathbf{r}) = 2 \beta_{g-1/2}^2 \, \lambda_e(\mathbf{r})} \tag{6.1}
$$

当 $\beta=4$ 时 $\lambda_g(4) = 32\lambda_e$，给出 LMV 核的推荐参数 $a=32$。

### 6.2 群源项 $W_g$ 的推导

SH 热流的速度分辨贡献可通过以下关系获得 [1,14]。在各向异性扰动中忽略 $(\beta-4)$ 因子（该因子部分被 Joule 加热补偿），简化为：

$$
g_1^m(\beta) \approx -\frac{\lambda_{ei}^*(\beta)}{3} f_0^m(\beta) \frac{\nabla T_e}{T_e}
$$

热流积分 $Q \propto \int v^5 g_1^m(v) dv$。从 $(v,dv)$ 到 $(\beta,d\beta)$ 变换：
- $v^5 dv \propto \beta^2 d\beta$
- $\lambda_{ei}^*(\beta) \propto \beta^2$
- $f_0^m \propto e^{-\beta}$

因此 $v^5 g_1^m dv \propto \beta^4 e^{-\beta} d\beta$。归一化 $\int_0^\infty \beta^4 e^{-\beta} d\beta = \Gamma(5) = 24$：

$$
\boxed{W_g = \frac{1}{24} \int_{\beta_{g-1}}^{\beta_g} \beta^4 e^{-\beta} \, d\beta}, \qquad \mathbf{U}_g(\mathbf{r}) = W_g \, \mathbf{Q}_{SH}(\mathbf{r}) \tag{6.2}
$$

$W_g$ 满足 $\sum_g W_g = 1$，因此 $\sum_g \mathbf{U}_g = \mathbf{Q}_{SH}$。

#### 6.2b $W_g$ 与 $\mathbf{U}_g$ 的物理意义

##### $W_g$：能量群的热流权重——"热流由哪些能量的电子携带"

$W_g$ 是第 $g$ 群电子对 SH 热流的**贡献分数**（无量纲），满足 $0 \le W_g \le 1$ 且 $\sum_g W_g = 1$。它定量回答："总热流 $\mathbf{Q}_{SH}$ 中，有多大比例是由能量处于 $[E_{g-1}, E_g]$ 区间的电子携带的？"

**权重函数 $\beta^4 e^{-\beta}$ 的每个因子都有明确的物理来源**：

| 因子 | 来源 | 物理含义 |
|------|------|---------|
| $\beta^2$ | 相空间体积元 $v^5 dv$（换元 $\beta = m_ev^2/2k_BT_e$ 后 $v^5dv/d\beta \propto \beta^{5/2}\cdot\beta^{-1/2} = \beta^2$） | 速度空间球壳 $4\pi v^2dv$ 与热流矩核 $v^3$ 的组合 |
| $\beta^2$ | 自由程标度 $\lambda_{ei}^*(\beta) \propto \beta^2$（因 $\lambda_{ei}(v)\propto v^4$） | **高能电子自由程更长**，在温度梯度驱动下能积累更大的分布偏离，故携带更多热流 |
| $e^{-\beta}$ | Maxwell 分布 $f_0^m \propto e^{-\beta}$ | 高能电子**数量指数衰减** |

三者综合给出 $\beta^4 e^{-\beta}$，其峰值位于 $\beta=4$（由 $\frac{d}{d\beta}\beta^4e^{-\beta} = \beta^3(4-\beta)e^{-\beta}=0$ 解得）。**物理结论：载热电子的特征能量为 $E \approx 4k_BT_e$（速度 $v\approx2.83v_T$）**——这正是"超热电子（suprathermal）主导热流"这一非局域输运核心事实的量化体现，也是 SNB 模型中 $\lambda_g(4) = 32\lambda_e$ 给出 LMV 参数 $a=32$ 的根源（见 §3.1、§6.1）。

**为什么忽略 $(\beta-4)$ 因子**：完整的热流被积函数来自 (2.4) 的 $g_1^m \propto (\beta-4)e^{-\beta}$，其中 $(\beta-4)$ 使 $\beta<4$ 时权重为负（低速电子"回流"，贡献与热流方向相反的逆流）、$\beta>4$ 时为正（高速载热电子）。有趣的是 $\int_0^\infty\beta^4(\beta-4)e^{-\beta}d\beta = \Gamma(6)-4\Gamma(5) = 120-96 = 24$，与 $\Gamma(5)=24$ **数值上巧合相等**——但 $(\beta-4)$ 会使低能群的 $W_g$ 为负，无法解释为"份额"。SNB 采用忽略 $(\beta-4)$ 的简化（该因子部分被 Joule 加热补偿 [1,13]，见 §5.8 与附录 B），得到全正权重，$W_g$ 才可作为概率/份额使用。

**有限截断的误差**：实际实现取 $\beta_{max}$ 有限（典型 10–20），$\sum_g W_g = \frac{1}{24}\int_0^{\beta_{max}}\beta^4e^{-\beta}d\beta < 1$，丢失高能尾（上不完全 Gamma 函数 $\Gamma(5,\beta_{max})/\Gamma(5)$）：
- $\beta_{max}=10$：丢失 $\approx 2.9\%$
- $\beta_{max}=20$：丢失 $\approx 2\times10^{-5}$（可忽略）

实际 SNB 实现（如 FLASH 中 20 群、0.1 eV 至 100 keV [3]）取 $\beta_{max}\gtrsim10$ 即足够。

##### $\mathbf{U}_g$：能量群的局域热流份额——"每群电子各自携带的热流矢量"

$\mathbf{U}_g(\mathbf{r}) = W_g\mathbf{Q}_{SH}(\mathbf{r})$ 是第 $g$ 群电子的**局域 SH 热流份额**，量纲为热流密度（与 $\mathbf{Q}_{SH}$ 相同）。其等价定义是群内的热流积分：

$$
\mathbf{U}_g(\mathbf{r}) = \frac{m_e}{2}\int_{v_{g-1}}^{v_g} v^5 g_1^m(v)\,dv = W_g\,\mathbf{Q}_{SH}(\mathbf{r}) \tag{6.2b}
$$

（$v_{g-1},v_g$ 为第 $g$ 群的速度边界。）物理含义：**"如果第 $g$ 群电子完全局域输运（SH 假设成立），它们各自携带的热流"**。

**在 SNB 输运方程中的角色——源项**：在群输运方程 (6.3) 中，

$$
\mathbf{\Omega}\cdot\nabla q_g + \frac{q_g}{\lambda_g} = \frac{3}{4\pi\lambda_g}\mathbf{\Omega}\cdot\mathbf{U}_g
$$

$\mathbf{U}_g$ 位于右侧**源项**：第 $g$ 群电子的局域 SH 热流以碰撞注入率 $\sim v_{th}/\lambda_g$ 持续"泵入"角通量场 $q_g$，随后输运方程决定这些热流如何被非局域地重新分布。**高能群（$\beta$ 大）的 $\lambda_g$ 大 → 热流传播距离远 → 非局域性强**（可到达温度梯度上游，即预热效应）；低能群 $\lambda_g$ 小 → 热流局域沉积（在陡梯度区受抑制，即限流效应）。

**群热流之和 = 总热流（能量守恒）**：

$$
\sum_g\mathbf{U}_g = \sum_g W_g\mathbf{Q}_{SH} = \mathbf{Q}_{SH} \tag{6.2c}
$$

这是 (7.5) 中 $\mathbf{Q}_{SNB}$ 能分解为"局域部分 $\mathbf{Q}_{SH}$ + 非局域修正 $\sum_g\lambda_g\nabla H_g/3$"的前提——各群局域源之和精确等于 SH 热流本身。

##### $W_g$ 与 $\mathbf{U}_g$ 的对照（谱 vs 份额）

| | $W_g$ | $\mathbf{U}_g$ |
|--|-------|---------------|
| 类型 | 标量（无量纲） | 矢量（热流密度，W/m² 或 erg/cm²·s） |
| 含义 | 能量谱权重（"热流由谁携带"） | 群热流份额（"每群携带多少热流"） |
| 角色 | 归一化谱函数 | 输运方程 (6.3) 的源项 |
| 关系 | 定义源：$\mathbf{U}_g = W_g\mathbf{Q}_{SH}$ | 求和恢复总热流：$\sum_g\mathbf{U}_g = \mathbf{Q}_{SH}$ |

**整体物理图景**：将电子按能量分组后，$W_g$ 刻画"热流谱"（主力是 $\beta\approx4$ 的载热电子），$\mathbf{U}_g$ 将总 SH 热流按该谱分摊到各群。SNB 中每群独立求解非局域扩散方程（(6.3) → (7.4)），以 $\mathbf{U}_g$ 为驱动源；最终 $\mathbf{Q}_{SNB} = \mathbf{Q}_{SH} - \sum_g\frac{\lambda_g}{3}\nabla H_g$ 是各群修正之和——$H_g$ 反映第 $g$ 群 $f_0$ 对 Maxwell 的偏离，$\lambda_g$ 越大（高能群）修正越显著。

### 6.3 群输运方程

回顾第 5 节的结论——速度群内的非局域效应由输运方程 (4.1) 描述。对各群独立应用：

$$
\boxed{\mathbf{\Omega} \cdot \nabla q_g(\mathbf{\Omega}, \mathbf{r}) + \frac{1}{\lambda_g(\mathbf{r})} q_g(\mathbf{\Omega}, \mathbf{r}) = \frac{1}{\lambda_g(\mathbf{r})} \frac{3}{4\pi} \mathbf{\Omega} \cdot \mathbf{U}_g(\mathbf{r})} \tag{6.3}
$$

总非局域热流为：

$$
\mathbf{Q}_{SNB}(\mathbf{r}) = \sum_{g=1}^{N_g} \int_{4\pi} q_g(\mathbf{\Omega}, \mathbf{r}) \, \mathbf{\Omega} \, d^2\Omega \tag{6.4}
$$

典型的能量分群数 $N_g = 20$–$40$，最大能量 $\beta_{\max} \approx 10$–$20$ [15,16]。

---

<a name="sec7"></a>
## 7. P1 扩散近似与最终控制方程

### 7.1 P1 展开

在 P1 近似中，各群角通量展开为 [17,18]：

$$
\boxed{4\pi q_g(\mathbf{\Omega}, \mathbf{r}) = H_g(\mathbf{r}) + 3 \mathbf{\Omega} \cdot \mathbf{Q}_g(\mathbf{r})} \tag{7.1}
$$

其中零阶矩和一阶矩定义为：

$$
H_g(\mathbf{r}) = \int_{4\pi} q_g(\mathbf{\Omega}, \mathbf{r}) \, d^2\Omega, \qquad
\mathbf{Q}_g(\mathbf{r}) = \int_{4\pi} q_g(\mathbf{\Omega}, \mathbf{r}) \, \mathbf{\Omega} \, d^2\Omega \tag{7.2}
$$

### 7.2 角矩方程的推导

将 P1 展开 (7.1) 代入群输运方程 (6.3)，分别取零阶矩和一阶矩。

#### 零阶矩（$\int d^2\Omega$）

- $\int \mathbf{\Omega} \cdot \nabla H_g \, d^2\Omega = 0$
- $3\int \mathbf{\Omega} \cdot \nabla (\mathbf{\Omega} \cdot \mathbf{Q}_g) d^2\Omega = 3 \cdot \frac{4\pi}{3} \nabla \cdot \mathbf{Q}_g = 4\pi \nabla \cdot \mathbf{Q}_g$
- 吸收项：$\int H_g/\lambda_g d^2\Omega = 4\pi H_g/\lambda_g$
- 源项：$\frac{3}{\lambda_g} \int \mathbf{\Omega} \cdot \mathbf{U}_g d^2\Omega = 0$

得到：

$$
\boxed{\nabla \cdot \mathbf{Q}_g + \frac{H_g}{\lambda_g} = 0} \tag{7.3a}
$$

#### 一阶矩（乘 $\mathbf{\Omega}$ 后 $\int \mathbf{\Omega} d^2\Omega$）

- $\int \mathbf{\Omega} (\mathbf{\Omega} \cdot \nabla H_g) d^2\Omega = \frac{4\pi}{3} \nabla H_g$
- 三阶矩张量在球面上积分为零
- $\frac{3}{\lambda_g} \int \mathbf{\Omega}(\mathbf{\Omega} \cdot \mathbf{Q}_g) d^2\Omega = \frac{4\pi}{\lambda_g} \mathbf{Q}_g$
- 源项：$\frac{3}{\lambda_g} \int \mathbf{\Omega}(\mathbf{\Omega} \cdot \mathbf{U}_g) d^2\Omega = \frac{4\pi}{\lambda_g} \mathbf{U}_g$

得到：

$$
\frac{4\pi}{3} \nabla H_g + \frac{4\pi}{\lambda_g} \mathbf{Q}_g = \frac{4\pi}{\lambda_g} \mathbf{U}_g
$$

化简为：

$$
\boxed{\mathbf{Q}_g = \mathbf{U}_g - \frac{\lambda_g}{3} \nabla H_g} \tag{7.3b}
$$

### 7.3 Helmholtz 型扩散方程

将 (7.3b) 代入 (7.3a)：

$$
\nabla \cdot \left( \mathbf{U}_g - \frac{\lambda_g}{3} \nabla H_g \right) + \frac{H_g}{\lambda_g} = 0
$$

整理得最终控制方程：

$$
\boxed{\left( \frac{1}{\lambda_g(\mathbf{r})} - \nabla \cdot \frac{\lambda_g(\mathbf{r})}{3} \nabla \right) H_g(\mathbf{r}) = -\nabla \cdot \mathbf{U}_g(\mathbf{r})} \tag{7.4}
$$

**算子结构**：
- $1/\lambda_g$——**碰撞吸收项**（碰撞以速率 $\nu_{ee} = v_{th}/\lambda_g$ 将 $H_g$ 耗散至零，恢复 Maxwell 分布；$H_g$ 正比于 $f_0$ 对 Maxwell 分布的偏离，其麦克斯韦化由 e-e 碰撞主导，故此处用 $\nu_{ee}$ 而非 $\nu_{ei}^*$——见 §1.3 符号约定与附录 D）
- $-\nabla \cdot (\lambda_g/3) \nabla$——**空间扩散项**（非局域耦合的特征尺度为 $\sqrt{\lambda_g L_T/3}$）

### 7.4 最终非局域热流公式

总热流为各群贡献之和：

$$
\mathbf{Q}_{SNB}(\mathbf{r}) = \sum_{g=1}^{N_g} \mathbf{Q}_g = \sum_{g=1}^{N_g} \left( \mathbf{U}_g - \frac{\lambda_g}{3} \nabla H_g \right)
$$

利用 $\sum_g \mathbf{U}_g = \sum_g W_g \mathbf{Q}_{SH} = \mathbf{Q}_{SH}$：

$$
\boxed{\mathbf{Q}_{SNB}(\mathbf{r}) = \mathbf{Q}_{SH}(\mathbf{r}) - \sum_{g=1}^{N_g} \frac{\lambda_g(\mathbf{r})}{3} \nabla H_g(\mathbf{r})} \tag{7.5}
$$

方程 (7.4) 和 (7.5) 即为**SNB 非局域电子热传导模型的最终形式**。

### 7.5 物理图像

| 物理效应 | 数学机制 | 物理解释 |
|---------|---------|---------|
| **热流抑制** | $-\sum \frac{\lambda_g}{3}\nabla H_g$ 与 $\mathbf{Q}_{SH}$ 同向 | 在陡梯度区抵消部分局域热流 |
| **预热效应** | $H_g \neq 0$ 在 $\nabla T_e \approx 0$ 区 | 高能电子长自由程将能量"泄漏"至低温区 |
| **SH 恢复** | $\nabla H_g \to 0$ 在平滑梯度极限 | 非局域修正自动消失 |

---

<a name="sec8"></a>
## 8. 电场自洽修正

### 8.1 修正动机

原始 SNB 模型（仅含碰撞吸收项 $1/\lambda_g$）在低密度/无碰撞区（如激光等离子体冕区）会出现 $H_g$ 的过度增长。电场的物理作用是限制高能电子的自由程——在电场 $\mathbf{E}$ 中能量为 $E_g$ 的电子的停止距离为 $\lambda_E = E_g/(eE)$。

### 8.2 Bendib-Luciani-Matte 修正

Bendib、Luciani 和 Matte [19] 提出将电场效应纳入有效自由程修正。Schurtz 等 [1] 将此纳入 SNB 框架：

修改后的有效自由程为调和平均：

$$
\boxed{\frac{1}{\lambda_g'} = \frac{1}{\lambda_g} + \frac{1}{\beta_g \lambda_E}} \tag{8.1}
$$

其中 $\beta_g = E_g/(k_B T_e)$ 为无量纲群能量，电场停止长度为：

$$
\boxed{\lambda_E = \frac{k_B T_e}{|e \mathbf{E}|}} \tag{8.2}
$$

电场由 Spitzer 公式近似 [1, Eqs. (33)-(34)]：

$$
\boxed{\mathbf{E} = \frac{k_B T_e}{e} \left( \nabla \ln n_e + \gamma(Z) \nabla \ln T_e \right)}, \qquad \gamma(Z) \approx 1 + \frac{3}{2} \frac{Z+0.477}{Z+2.15} \tag{8.3}
$$

### 8.3 修正后的 SNB 方程组

仅扩散项中的 $\lambda_g$ 被 $\lambda_g'$ 替代，而吸收项保持不变 [1, Eqs. (36)-(37)]：

$$
\boxed{\left( \frac{1}{\lambda_g} - \nabla \cdot \frac{\lambda_g'}{3} \nabla \right) H_g = -\nabla \cdot \mathbf{U}_g} \tag{8.4}
$$

$$
\boxed{\mathbf{Q}_{SNB} = \mathbf{Q}_{SH} - \sum_g \frac{\lambda_g'}{3} \nabla H_g} \tag{8.5}
$$

### 8.4 电场修正的渐近行为

经过电场修正后，在无碰撞极限 $k\lambda_e \to \infty$ 下，非局域热流自然趋于自由流值 $Q_{FS} = n_e k_B T_e v_T$——这是原始 SNB 模型不具备的关键性质 [1, §IV.B]。

---

<a name="sec9"></a>
## 9. 完整推导链路总结

```
┌──────────────────────────────────────────────────────────────────────┐
│              从 Fokker-Planck 到 SNB 的完整推导链路                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Step 1: 电子 FP 方程 → P1 球谐展开                                     │
│    ∂f/∂t + v·∇f - (eE/me)·∇ᵥf = C(f)                                 │
│    → f(v,Ω) = f₀/4π + 3Ω·f₁/4π                                        │
│    → 矩方程 (1.9a)(1.9b)                                               │
│                                                                      │
│  Step 2: 零阶解 (f₀ = Maxwell, j=0) → Spitzer-Härm 理论                │
│    → Eᴹᴮ = (kBTₑ/e)(∇nₑ/nₑ + 5/2 ∇Tₑ/Tₑ)                            │
│    → f₁ᴹᴮ → Q_SH = -κ_SH ∇Tₑ                                        │
│                                                                      │
│  Step 3: SH 失效（λₑ/L_T > 5×10⁻³）→ LMV 非局域卷积                     │
│    → Q(r) = ∫ W(r,r') Q_SH(r') dr'/λₑ(r')                            │
│                                                                      │
│  Step 4: 卷积 = 输运方程的 Green 函数解                                 │
│    → Ω·∇q + q/λ_t = (3/4πλ_t) Ω·Q_SH                                 │
│                                                                      │
│  Step 5: ★ Jacobian 迭代 (Step 1→Step 4 的动理学桥梁) ★               │
│    → ∂F/∂X · ΔX = -F(X⁰)                                             │
│    → νₑₑΔf₀ + v∇·(Δf₁) = RHS                                         │
│    → νₑᵢ*Δf₁ = -(v/3)∇(Δf₀)                                             │
│    → 消去 Δf₁ → ℋ(v) 的扩散方程                                       │
│    → 速度群离散化 + P1 → SNB 方程！                                    │
│                                                                      │
│  Step 6: 能量多群 + P1 扩散近似 → 最终 SNB 方程组                        │
│    → (1/λ_g - ∇·λ_g/3∇) H_g = -∇·U_g                                │
│    → Q_SNB = Q_SH - Σ_g λ_g/3 ∇H_g                                   │
│                                                                      │
│  Step 7: 电场自洽修正 → λ_g → λ_g'                                     │
│    → 1/λ_g' = 1/λ_g + 1/(β_g λ_E)                                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 推导中的关键近似（供人工核查参考）

| # | 近似 | 位置 | 数学表达 | 影响 |
|---|------|------|---------|------|
| A1 | 稳态输运 | 全局 | $\partial f/\partial t = 0$ | $\tau_{ei} \sim \tau_{\text{hydro}}$ 时失效 |
| A2 | 零电流 | §2.2 | $\mathbf{J}=0$ | 需电场修正 |
| A3 | P1 截断 | §1.2 | $\ell \geq 2$ 忽略 | 高度各向异性时需 P3+ |
| A4 | Lorentz 气体 | §1.3 | 忽略 $C_{ee}$ 对 $\mathbf{f}_1$ | $Z \sim 1$ 时需修正 [5] |
| A5 | Jacobian 对角化 | §5.3 | 丢掉 off-block 项 | 收敛性由 $\mathcal{L}^{-1}\mathcal{J} \approx I$ 保证 |
| A6 | $\partial C_0/\partial f_0 \approx -\nu_{ee}$ | §5.3 | 仅保留 e-e 碰撞频率 | 高频 e-e 碰撞主导 $C_0$ |
| A7 | 源项简化 ($(\beta-4)$ 吸收) | §6.2 | 略去 $(\beta-4)$ 因子 | 被 Joule 加热部分补偿 [1] |
| A8 | 电场唯象修正 | §8 | $\lambda_E$ 调和平均 | 非自洽，但与 FP 模拟吻合良好 [1,20] |

---

<a name="appA"></a>
## 附录 A：P1 球谐展开下矩方程的完整推导

> 本附录补全正文 §1.3 的推导细节，基于整理稿（`tmp_md/矩方程.md`）并对照 Schurtz 等 [1, §III.B] 原始推导修正。其中 A.6 列出对整理稿的勘误。

### A.1 稳态 Fokker-Planck 方程

在完全电离等离子体中，电子分布函数满足 FP 方程（正文 (1.1)）。在准静态近似（$\partial f/\partial t = 0$，碰撞时间远小于流体力学时间）和无磁场假设（$\mathbf{B}=0$）下，方程简化为（正文 (1.2)）：

$$
\mathbf{v}\cdot\nabla f - \frac{e}{m_e}\mathbf{E}\cdot\nabla_v f = C(f), \qquad C(f) = C_{ee}(f) + C_{ei}(f) \tag{A.1}
$$

### A.2 P1 展开与角矩定义

将速度分解为 $v = |\mathbf{v}|$ 和方向单位矢量 $\mathbf{\Omega} = \mathbf{v}/v$。P1 展开（正文 (1.3)）：

$$
f(\mathbf{v},\mathbf{r}) = \frac{1}{4\pi}f_0(v,\mathbf{r}) + \frac{3}{4\pi}\mathbf{\Omega}\cdot\mathbf{f}_1(v,\mathbf{r}) \tag{A.2}
$$

角矩定义（正文 (1.4)）与球面积分恒等式：

$$
f_0 = \int_{4\pi}f\,d^2\Omega, \qquad \mathbf{f}_1 = \int_{4\pi}f\,\mathbf{\Omega}\,d^2\Omega \tag{A.3}
$$

$$
\int d^2\Omega = 4\pi, \quad \int \mathbf{\Omega}\,d^2\Omega = \mathbf{0}, \quad \int \Omega_i\Omega_j\,d^2\Omega = \frac{4\pi}{3}\delta_{ij}, \quad \int \Omega_i\Omega_j\Omega_k\,d^2\Omega = 0 \tag{A.4}
$$

**注意**：三阶角矩 $\int\Omega_i\Omega_j\Omega_k d^2\Omega = 0$ 是被积函数为三个奇函数之积在球面上积分的**精确结果**（角矩正交性），不是近似。这一恒等式在 A.4 中起关键作用。

自洽性验证：$\int\frac{f_0}{4\pi}d^2\Omega = f_0$，$\int\frac{3}{4\pi}(\mathbf{\Omega}\cdot\mathbf{f}_1)\mathbf{\Omega}d^2\Omega = \frac{3}{4\pi}\mathbf{f}_1\cdot\int\mathbf{\Omega}\mathbf{\Omega}d^2\Omega = \frac{3}{4\pi}\cdot\frac{4\pi}{3}\mathbf{f}_1 = \mathbf{f}_1$ ✓

### A.3 零阶矩方程（$\int d^2\Omega$）

对 (A.1) 作全立体角积分。

**对流项**：

$$
\int \mathbf{v}\cdot\nabla f\,d^2\Omega = v\int \mathbf{\Omega}\cdot\nabla f\,d^2\Omega = v\,\nabla\cdot\int \mathbf{\Omega} f\,d^2\Omega = v\,\nabla\cdot\mathbf{f}_1 \tag{A.5}
$$

推导依据：空间梯度 $\nabla$ 与 $\mathbf{\Omega}$ 无关，可移入积分；利用 $\nabla\cdot(\mathbf{\Omega}f) = \mathbf{\Omega}\cdot\nabla f$（$\mathbf{\Omega}$ 与空间坐标无关）；$\int\mathbf{\Omega}f\,d^2\Omega = \mathbf{f}_1$（$f_0$ 部分 $\int\mathbf{\Omega}f_0\,d^2\Omega = \mathbf{0}$ 自动消失）。

**电场项**：

$$
-\frac{e}{m_e}\int \mathbf{E}\cdot\nabla_v f\,d^2\Omega
$$

方法一（球坐标散度）：利用 $\nabla_v\cdot(\mathbf{E}f) = \mathbf{E}\cdot\nabla_v f$（因 $\mathbf{E}$ 与 $\mathbf{v}$ 无关，$\nabla_v\cdot\mathbf{E} = 0$），再写球坐标中速度空间散度：

$$
\nabla_v\cdot\mathbf{A} = \frac{1}{v^2}\frac{\partial}{\partial v}(v^2 A_v) + \text{角度项}, \qquad A_v = \mathbf{A}\cdot\mathbf{\Omega}
$$

角度项在球面无边界，积分贡献为零：

$$
\int \mathbf{E}\cdot\nabla_v f\,d^2\Omega = \int \nabla_v\cdot(\mathbf{E}f)\,d^2\Omega = \frac{1}{v^2}\frac{\partial}{\partial v}\left[v^2\int(\mathbf{E}\cdot\mathbf{\Omega})f\,d^2\Omega\right] = \frac{1}{v^2}\frac{\partial}{\partial v}\left[v^2\,\mathbf{E}\cdot\mathbf{f}_1\right]
$$

因此：

$$
-\frac{e}{m_e}\int \mathbf{E}\cdot\nabla_v f\,d^2\Omega = -\frac{e\mathbf{E}}{m_e v^2}\cdot\frac{\partial(v^2\mathbf{f}_1)}{\partial v} \tag{A.6}
$$

（最后一步：$\mathbf{E}$ 视为常数，$\frac{\partial}{\partial v}(v^2\mathbf{E}\cdot\mathbf{f}_1) = \mathbf{E}\cdot\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$，点乘顺序可交换。）

**碰撞项**：

$$
\int C(f)\,d^2\Omega = C_0(f_0) \tag{A.7}
$$

$C_0(f_0)$ 为碰撞算子的零阶角矩，仅依赖各向同性部分 $f_0$（通过 Rosenbluth 势 [6]）。

**零阶矩方程汇总**：

$$
\boxed{v\,\nabla\cdot\mathbf{f}_1 - \frac{e\mathbf{E}}{m_e v^2}\cdot\frac{\partial(v^2\mathbf{f}_1)}{\partial v} = C_0(f_0)} \tag{A.8}
$$

即正文 (1.5) / (1.9a)。

### A.4 一阶矩方程（乘 $\mathbf{\Omega}$ 后 $\int \mathbf{\Omega}\,d^2\Omega$）

对 (A.1) 乘以 $\mathbf{\Omega}$ 后作 $\int\mathbf{\Omega}\,d^2\Omega$。

**对流项**：

$$
\int \mathbf{\Omega}(\mathbf{v}\cdot\nabla f)\,d^2\Omega = v\int \mathbf{\Omega}(\mathbf{\Omega}\cdot\nabla f)\,d^2\Omega
$$

将 P1 展开代入，分别考虑 $f_0$ 与 $\mathbf{f}_1$ 部分：

(i) $f_0$ 部分：

$$
v\int\mathbf{\Omega}\left(\mathbf{\Omega}\cdot\nabla\frac{f_0}{4\pi}\right)d^2\Omega = \frac{v}{4\pi}\partial_j f_0\int\Omega_i\Omega_j\,d^2\Omega = \frac{v}{4\pi}\cdot\frac{4\pi}{3}\partial_i f_0 = \frac{v}{3}\partial_i f_0 \tag{A.9}
$$

即 $\frac{v}{3}\nabla f_0$（恢复矢量记号）。

(ii) $\mathbf{f}_1$ 部分：

$$
\frac{3v}{4\pi}\int \Omega_i(\Omega_j\partial_j)(\Omega_k f_{1k})\,d^2\Omega = \frac{3v}{4\pi}\partial_j f_{1k}\int\Omega_i\Omega_j\Omega_k\,d^2\Omega = 0 \tag{A.10}
$$

**关键**：三阶角矩 $\int\Omega_i\Omega_j\Omega_k\,d^2\Omega = 0$（见 (A.4)）使 $\mathbf{f}_1$ 部分**精确为零**——这是角矩正交性的结果，而非"P1 近似下被忽略"。

**电场项**：

$$
-\frac{e}{m_e}\int\mathbf{\Omega}(\mathbf{E}\cdot\nabla_v f)\,d^2\Omega
$$

将速度空间梯度分解为径向与角度部分：$\nabla_v f = \mathbf{\Omega}\frac{\partial f}{\partial v} + \frac{1}{v}\nabla_\Omega f$。

(i) 径向部分 $(\mathbf{E}\cdot\mathbf{\Omega})\frac{\partial f}{\partial v}$：

- $f_0$ 部分：

$$
-\frac{e}{m_e}\int\mathbf{\Omega}(\mathbf{E}\cdot\mathbf{\Omega})\frac{1}{4\pi}\frac{\partial f_0}{\partial v}\,d^2\Omega = -\frac{e}{4\pi m_e}\frac{\partial f_0}{\partial v}E_j\int\Omega_i\Omega_j\,d^2\Omega = -\frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v} \tag{A.11}
$$

- $\mathbf{f}_1$ 部分：$\propto\int\Omega_i\Omega_j\Omega_k\,d^2\Omega = 0$（三阶角矩为零）。

(ii) 角度部分 $\frac{1}{v}\mathbf{E}\cdot\nabla_\Omega f$：

- $f_0$ 部分：$\nabla_\Omega f_0 = 0$（$f_0$ 仅依赖 $v$），贡献为零。
- $\mathbf{f}_1$ 部分：利用球面梯度性质 $\nabla_\Omega(\mathbf{\Omega}\cdot\mathbf{f}_1) = \mathbf{f}_1 - \mathbf{\Omega}(\mathbf{\Omega}\cdot\mathbf{f}_1)$，则 $\mathbf{E}\cdot\nabla_\Omega(\mathbf{\Omega}\cdot\mathbf{f}_1) = \mathbf{E}\cdot\mathbf{f}_1 - (\mathbf{E}\cdot\mathbf{\Omega})(\mathbf{\Omega}\cdot\mathbf{f}_1)$。代入后：

$$
\propto \int\Omega_i[\mathbf{E}\cdot\mathbf{f}_1 - (\mathbf{E}\cdot\mathbf{\Omega})(\mathbf{\Omega}\cdot\mathbf{f}_1)]\,d^2\Omega = 0 - E_j f_{1k}\int\Omega_i\Omega_j\Omega_k\,d^2\Omega = 0 \tag{A.12}
$$

（第一项 $\int\mathbf{\Omega}\,d^2\Omega = 0$；第二项三阶角矩为零。）

**结论**：$\mathbf{f}_1$ 部分对一阶矩电场项的贡献精确为零，只有 $f_0$ 部分贡献 $-\frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$。

**碰撞项**：采用 Lorentz 气体近似（正文 (1.7)）：

$$
\int\mathbf{\Omega}\,C(f)\,d^2\Omega = \mathbf{C}_1(\mathbf{f}_1) = -\nu_{ei}^*(v)\mathbf{f}_1, \qquad \nu_{ei}^*(v) = (Z+1)\frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3} \tag{A.13}
$$

**一阶矩方程汇总**：

$$
\boxed{\frac{v}{3}\nabla f_0 - \frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v} = -\nu_{ei}^*(v)\mathbf{f}_1} \tag{A.14}
$$

即正文 (1.6) / (1.9b)。

### A.5 矩方程组与宏观量

将 (A.8) 与 (A.14) 联立即正文 (1.9a)(1.9b)。宏观量由分布函数的矩给出（正文 (1.9) 之后）：

**电流密度**（矢量矩）：

$$
\mathbf{J} = -e\int\mathbf{v}f\,d^3v = -e\int_0^\infty v^3\left[\int_{4\pi}\mathbf{\Omega}f\,d^2\Omega\right]dv = -e\int_0^\infty \mathbf{f}_1 v^3 dv \tag{A.15}
$$

**热流**（能量通量矩）：

$$
\mathbf{Q} = \frac{m_e}{2}\int v^2\mathbf{v}f\,d^3v = \frac{m_e}{2}\int_0^\infty v^5\left[\int_{4\pi}\mathbf{\Omega}f\,d^2\Omega\right]dv = \frac{m_e}{2}\int_0^\infty \mathbf{f}_1 v^5 dv \tag{A.16}
$$

（两式中 $\int_{4\pi}\mathbf{\Omega}f\,d^2\Omega = \mathbf{f}_1$，$f_0$ 部分贡献为零。）

### A.6 对整理稿（`tmp_md/矩方程.md`）的勘误

| # | 整理稿原文 | 问题 | 本附录更正 |
|---|-----------|------|-----------|
| 1 | "含 $\mathbf{f}_1$ 的项会产生三阶张量，**在 P1 近似下被忽略**" | 不准确 | 三阶角矩 $\int\Omega_i\Omega_j\Omega_k d^2\Omega = 0$ 是**精确为零**（角矩正交性），非近似忽略（见 (A.10)） |
| 2 | "因为一阶项贡献**高阶小量**" | 同上 | $\mathbf{f}_1$ 部分的贡献精确为零（见 (A.11)(A.12)） |
| 3 | 电场项仅给出球坐标散度方法 | 可行但不够直接 | 本附录补充 $\nabla_v = \mathbf{\Omega}\frac{\partial}{\partial v}+\frac{1}{v}\nabla_\Omega$ 的直接分解法，两种方法等价 |
| 4 | 未明确 $f_0$ 部分在零阶矩电场项中贡献为零 | 省略 | 本附录明确：$\int\mathbf{\Omega}f_0\,d^2\Omega = 0$（见 A.3 电场项） |

---

<a name="appB"></a>
## 附录 B：(5.1c) 零电流条件的详细证明

**目标**：证明零电流条件 $\mathbf{J} = 0$ 等价于残差 (5.1c)：

$$
\mathcal{F}_E = \int_0^\infty \left[ v\nabla f_0 - \frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v} \right] v^6 dv = 0
$$

### B.1 电流密度的速度矩定义

由 (A.15)（即正文 (1.9) 中电流定义）：

$$
\mathbf{J} = -e\int\mathbf{v}f\,d^3v = -e\int_0^\infty \mathbf{f}_1(v) v^3 dv
$$

零电流条件 $\mathbf{J} = \mathbf{0}$ 等价于：

$$
\boxed{\int_0^\infty \mathbf{f}_1(v)\,v^3 dv = 0} \tag{B.1}
$$

### B.2 代入 $\mathbf{f}_1$ 的显式表达

由一阶矩方程 (A.14) 解出 $\mathbf{f}_1$（对**任意** $f_0$、$\mathbf{E}$ 成立，不限于 Maxwell 分布）：

$$
\mathbf{f}_1(v) = -\frac{v}{3\nu_{ei}^*(v)}\nabla f_0 + \frac{e\mathbf{E}}{3m_e\nu_{ei}^*(v)}\frac{\partial f_0}{\partial v} \tag{B.2}
$$

（即正文 (2.2) 的推广。）代入 (B.1)：

$$
\int_0^\infty \left[ -\frac{v}{3\nu_{ei}^*}\nabla f_0 + \frac{e\mathbf{E}}{3m_e\nu_{ei}^*}\frac{\partial f_0}{\partial v} \right] v^3 dv = 0
$$

提取公因子 $-\frac{1}{3}$ 并整理：

$$
\int_0^\infty \left[ v\nabla f_0 - \frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v} \right]\frac{v^3}{\nu_{ei}^*(v)}\,dv = 0 \tag{B.3}
$$

### B.3 Lorentz 气体近似：$v^3/\nu_{ei}^* \propto v^6$

由 (A.13)，有效碰撞频率的速度标度为：

$$
\nu_{ei}^*(v) = (Z+1)\frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3} \propto v^{-3}
$$

因此：

$$
\frac{v^3}{\nu_{ei}^*(v)} = \frac{m_e^2 v^6}{(Z+1)4\pi n_e e^4\ln\Lambda} \propto v^6
$$

常数因子 $\frac{m_e^2}{(Z+1)4\pi n_e e^4\ln\Lambda}$ 与速度无关，可从积分中提出而不影响零条件（只改变方程整体的非零常数倍数）：

$$
\int_0^\infty \left[ v\nabla f_0 - \frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v} \right] v^6 dv = 0 \tag{B.4}
$$

这正是 (5.1c)。✓

### B.4 物理与数学注释

1. **$v^6$ 权重的来源**：电流矩权重 $v^3$（来自 $\int\mathbf{f}_1 v^3 dv$）乘以碰撞阻尼分母 $1/\nu_{ei}^*(v) \propto v^3$（来自 $\mathbf{f}_1 \propto 1/\nu_{ei}^*$）。两者相乘得到 $v^6$。若 $\nu_{ei}^*(v)$ 不严格 $\propto v^{-3}$，则 (B.3) 中的 $v^3/\nu_{ei}^*(v)$ 应保留在积分内（此时 (B.3) 仍精确，而 (B.4) 是 Lorentz 气体近似下的简化形式）。
2. **(5.1c) 是 $(f_0, \mathbf{E})$ 的函数**：$\mathbf{f}_1$ 已通过 (B.2) 消去，故 $\mathcal{F}_E$ 不显含 $\mathbf{f}_1$——这正是 Jacobian 第三行第二列为零（附录 C）的原因。
3. 零电流条件与电场自洽：在 SH 理论中，(B.4) 与 $f_0 = f_0^{\text{MB}}$ 联立给出电场 (2.3)，即正文 §2.2 的结果。

---

<a name="appC"></a>
## 附录 C：Jacobian 矩阵的详细构造

### C.1 Fréchet 导数与 $( \cdot)$ 占位符约定

正文 §5.2(b) 已说明 $(\cdot)$ 是**占位符**，表示矩阵元是**线性算子**。本节给出每个矩阵元的逐步计算。记未知量增量 $\Delta\mathbf{X} = (\Delta f_0, \Delta\mathbf{f}_1, \Delta\mathbf{E})^T$，矩阵元 $\mathcal{J}_{ij}$ 作用在 $\Delta X_j$ 上给出第 $i$ 个残差的线性化增量。

求导规则：对 $\mathcal{F}_i$ 关于 $X_j$ 求 Fréchet 导数时，**其余变量视为固定（取当前迭代值）**；含空间梯度 $\nabla$ 或速度偏导 $\partial/\partial v$ 的项给出微分算子；不含导数的项给出乘法算子。

### C.2 第 1 行：$\mathcal{F}_0$ 的偏导数

$\mathcal{F}_0 = C_0(f_0) - v\nabla\cdot\mathbf{f}_1 + \frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$（即 (5.1a)）

| 元 | 计算 | 结果 |
|----|------|------|
| $\mathcal{J}_{00} = \frac{\partial\mathcal{F}_0}{\partial f_0}$ | $C_0(f_0)$ 是 $f_0$ 的非线性泛函（Landau 算子零阶矩），其 Fréchet 导数 $\frac{\delta C_0}{\delta f_0}[\delta f_0]$ 是线性算子 | $\frac{\partial C_0}{\partial f_0}$（§5.3 近似为 $-\nu_{ee}(v)(\cdot)$，见附录 D） |
| $\mathcal{J}_{01} = \frac{\partial\mathcal{F}_0}{\partial\mathbf{f}_1}$ | 对 $-v\nabla\cdot\mathbf{f}_1$：变分 $\delta\mathbf{f}_1$ 给出 $-v\nabla\cdot(\delta\mathbf{f}_1)$；对 $\frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$：变分给出 $\frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\delta\mathbf{f}_1)}{\partial v}$ | $-v\nabla\cdot(\cdot) + \frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2(\cdot))}{\partial v}$ |
| $\mathcal{J}_{02} = \frac{\partial\mathcal{F}_0}{\partial\mathbf{E}}$ | 对 $\frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$：变分 $\delta\mathbf{E}$ 给出 $\frac{e\delta\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$，其中 $\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$ 是**已知函数**（当前迭代值） | $\frac{e(\cdot)}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$（乘法算子） |

### C.3 第 2 行：$\mathcal{F}_1$ 的偏导数

$\mathcal{F}_1 = -\nu_{ei}^*\mathbf{f}_1 - \frac{v}{3}\nabla f_0 + \frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$（即 (5.1b)）

| 元 | 计算 | 结果 |
|----|------|------|
| $\mathcal{J}_{10} = \frac{\partial\mathcal{F}_1}{\partial f_0}$ | 对 $-\frac{v}{3}\nabla f_0$：变分 $\delta f_0$ 给出 $-\frac{v}{3}\nabla(\delta f_0)$；对 $\frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$：变分给出 $\frac{e\mathbf{E}}{3m_e}\frac{\partial(\delta f_0)}{\partial v}$（注意 $\mathbf{E}$ 为当前值，$\frac{\partial}{\partial v}$ 为微分算子） | $-\frac{v}{3}\nabla(\cdot) + \frac{e\mathbf{E}}{3m_e}\frac{\partial}{\partial v}(\cdot)$ |
| $\mathcal{J}_{11} = \frac{\partial\mathcal{F}_1}{\partial\mathbf{f}_1}$ | 对 $-\nu_{ei}^*\mathbf{f}_1$：变分给出 $-\nu_{ei}^*\delta\mathbf{f}_1$ | $-\nu_{ei}^*(\cdot)$（乘法算子） |
| $\mathcal{J}_{12} = \frac{\partial\mathcal{F}_1}{\partial\mathbf{E}}$ | 对 $\frac{e\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$：变分 $\delta\mathbf{E}$ 给出 $\frac{e\delta\mathbf{E}}{3m_e}\frac{\partial f_0}{\partial v}$，$\frac{\partial f_0}{\partial v}$ 为已知函数 | $\frac{e(\cdot)}{3m_e}\frac{\partial f_0}{\partial v}$（乘法算子） |

### C.4 第 3 行：$\mathcal{F}_E$ 的偏导数

$\mathcal{F}_E = \int_0^\infty \left[ v\nabla f_0 - \frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v} \right] v^6 dv$（即 (5.1c)）

| 元 | 计算 | 结果 |
|----|------|------|
| $\mathcal{J}_{20} = \frac{\partial\mathcal{F}_E}{\partial f_0}$ | 对 $v\nabla f_0$：变分 $\delta f_0$ 给出 $\int v\nabla(\delta f_0)v^6 dv$（先梯度、再速度加权积分，输出矢量）；对 $\frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v}$：变分给出 $-\int\frac{e\mathbf{E}}{m_e}\frac{\partial(\delta f_0)}{\partial v}v^6 dv$（可用分部积分并入算子） | $\int v\nabla(\cdot)v^6 dv - \frac{e\mathbf{E}}{m_e}\int\frac{\partial(\cdot)}{\partial v}v^6 dv$ |
| $\mathcal{J}_{21} = \frac{\partial\mathcal{F}_E}{\partial\mathbf{f}_1}$ | $\mathcal{F}_E$ 不显含 $\mathbf{f}_1$（见附录 B） | $0$ |
| $\mathcal{J}_{22} = \frac{\partial\mathcal{F}_E}{\partial\mathbf{E}}$ | 对 $-\frac{e\mathbf{E}}{m_e}\frac{\partial f_0}{\partial v}$：变分 $\delta\mathbf{E}$ 给出 $-\frac{e\delta\mathbf{E}}{m_e}\int\frac{\partial f_0}{\partial v}v^6 dv$，$\int\frac{\partial f_0}{\partial v}v^6 dv$ 为已知标量 | $-\frac{e(\cdot)}{m_e}\int\frac{\partial f_0}{\partial v}v^6 dv$（常数乘法算子） |

**关于 $\mathcal{J}_{20}$ 的说明**：正文 (5.3) 中第三行第一列写为 $\int v\nabla(\cdot)v^6 dv$（仅保留梯度项）。在 Schurtz 等 [1] 的近似 Jacobian 构造中，电场相关的行被置零（见 §5.3 第 1 点"电场项在高能端可忽略"），故此处仅保留与空间导数相关的部分，与正文一致。

### C.5 矩阵汇总与验证

汇总以上结果即 (5.3)。**验证示例**：令矩阵乘以 $\Delta\mathbf{X}$，取第 1 行：

$$
\mathcal{J}_{00}\Delta f_0 + \mathcal{J}_{01}\Delta\mathbf{f}_1 + \mathcal{J}_{02}\Delta\mathbf{E} = \frac{\partial C_0}{\partial f_0}\Delta f_0 - v\nabla\cdot(\Delta\mathbf{f}_1) + \frac{e\mathbf{E}}{m_e v^2}\frac{\partial(v^2\Delta\mathbf{f}_1)}{\partial v} + \frac{e\Delta\mathbf{E}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}
$$

这正是 $\mathcal{F}_0$ 在 $(\Delta f_0,\Delta\mathbf{f}_1,\Delta\mathbf{E})$ 方向上的线性化增量 $\Delta\mathcal{F}_0$（一阶变分），与 $\mathcal{F}_0$ 的表达式逐项对应。✓

---

<a name="appD"></a>
## 附录 D：$\partial C_0/\partial f_0 \approx -\nu_{ee}(v)$ 的详细由来

### D.1 $C_0(f_0)$ 是什么

$C_0(f_0) = \int_{4\pi}C_{ee}(f)\,d^2\Omega$ 是**电子-电子碰撞算子**（Landau 算子 [6]）的零阶角矩。Landau 算子是速度空间中的**积分算子**（通过 Rosenbluth 势 [6] 表达）：

$$
C_{ee}(f) = \nabla_v\cdot\int d^3v'\, \mathbf{W}(\mathbf{v},\mathbf{v}')\cdot\left[\frac{\partial f(\mathbf{v})}{\partial\mathbf{v}}f(\mathbf{v}') - \frac{\partial f(\mathbf{v}')}{\partial\mathbf{v}'}f(\mathbf{v})\right] \tag{D.1}
$$

其零阶角矩 $C_0$ 描述 $f_0$ 的麦克斯韦化（弛豫到 Maxwell 平衡态）。

### D.2 为什么 e-e 碰撞主导 $f_0$ 的麦克斯韦化

两种碰撞对 $f_0$ 能量弛豫的效率差异悬殊：

- **电子-离子碰撞**：离子质量远大于电子，每次碰撞电子速度方向改变但**能量交换比例仅 $\Delta E/E \sim m_e/m_i \sim 5\times10^{-4}$**。e-i 碰撞主要使 $\mathbf{f}_1$（动量输运）弛豫，对 $f_0$ 的能量分布（麦克斯韦化）几乎无效。
- **电子-电子碰撞**：同质量粒子碰撞，能量交换比例 $\Delta E/E \sim O(1)$。尽管 $\nu_{ee}/\nu_{ei} \sim 1/Z$，但能量交换效率高 $m_i/m_e \sim 2000$ 倍，综合效应是 **e-e 碰撞主导 $f_0$ 的麦克斯韦化**，弛豫时间 $\tau_{ee} \sim 1/\nu_{ee}$。

**结论**：$f_0$ 的碰撞弛豫算子 $C_0$ 主要由 e-e 碰撞决定，而 $\mathbf{f}_1$ 的弛豫由 e-i 有效碰撞决定（这就是正文中 $\mathbf{f}_1$ 用 $\nu_{ei}^*$、$f_0$ 用 $\nu_{ee}$ 的原因，见 §1.3 符号约定）。两条判断依据可量化对比：

| 弛豫对象 | 主导机制 | 碰撞频率 | 能量交换效率 | 综合判断 |
|---------|---------|---------|-------------|---------|
| $f_0$（能量分布） | e-e 碰撞 | $\nu_{ee} \sim \nu_{ei}/Z$ | $\Delta E/E \sim O(1)$（同质量） | e-e 主导（效率高 $m_i/m_e \sim 2000$ 倍） |
| $\mathbf{f}_1$（角度各向异性） | e-i 碰撞为主 | $\nu_{ei}^* = (Z+1)\nu_{ee}$ | $\Delta E/E \sim m_e/m_i$（但对角度散射有效） | e-i 主导（角度偏转效率高，含 $Z^2$ 散射） |

### D.3 线性化与弛豫时间近似（BGK 型近似）

对 Maxwell 附近的小扰动 $f_0 = f_0^{\text{MB}} + \delta f_0$：

$$
C_0(f_0) = C_0(f_0^{\text{MB}}) + \left.\frac{\partial C_0}{\partial f_0}\right|_{f_0^{\text{MB}}}\delta f_0 + O(\delta f_0^2)
$$

利用 $C_0(f_0^{\text{MB}}) = 0$（Maxwell 分布是碰撞平衡态，正文 §2.1）：

$$
C_0(f_0) \approx \left.\frac{\partial C_0}{\partial f_0}\right|_{f_0^{\text{MB}}}\delta f_0 \tag{D.2}
$$

Landau 算子是**积分算子**，(D.2) 中的 $\partial C_0/\partial f_0$ 仍是速度空间的非局部算子。若直接保留，Jacobian 将变为积分-微分算子，无法解析求逆。**弛豫时间近似（BGK 型近似）**将其替换为局部乘法算子：

$$
\boxed{\left.\frac{\partial C_0}{\partial f_0}\right|_{f_0^{\text{MB}}}\delta f_0 \approx -\nu_{ee}(v)\,\delta f_0} \tag{D.3}
$$

**物理依据**：e-e 碰撞以特征速率 $\nu_{ee}(v)$ 将 $\delta f_0$ 指数衰减（弛豫），即 $\partial_t\delta f_0 \approx C_0(f_0) \approx -\nu_{ee}(v)\delta f_0$，解为 $\delta f_0(t) \propto e^{-\nu_{ee}(v)t}$。该近似是对 Landau 积分算子"弛豫本征模"的零阶捕捉——对主要本征模，积分算子的作用等价于乘 $-\nu_{ee}(v)$。

#### (D.3) 等式的详尽推导

下面从 e-e 碰撞算子的显式形式出发，逐步推导 (D.3)。

**第 1 步：写出 e-e 碰撞算子的 Fokker-Planck 形式（速度大小空间）**

各向同性分布 $f_0(v)$ 的 e-e 碰撞算子（Landau 算子对角度积分后的零阶角矩）可写为**速度大小空间的一维 Fokker-Planck 形式** [6,7,25]：

$$
C_0^{ee}(f_0) = \frac{1}{v^2}\frac{\partial}{\partial v}\left[v^2\left(A(v)\,f_0(v) + B(v)\,\frac{\partial f_0(v)}{\partial v}\right)\right] \tag{D.8}
$$

其中：
- $A(v)$——**摩擦系数**（dynamical friction）：描述背景粒子对 test 电子的平均"拖拽"（慢化）；
- $B(v)$——**速度扩散系数**（velocity-space diffusion）：描述碰撞引起的速度随机游走（麦克斯韦化的直接机制）。

二者由 Rosenbluth 势 [6] 确定（对 $f_0$ 各向同性时角度积分化简，$\Gamma \equiv 4\pi e^4\ln\Lambda/m_e^2$）：

$$
A(v) = -\frac{\Gamma}{v^2}\int_0^v 4\pi u^2 f_0(u)\,du, \qquad
B(v) = \frac{\Gamma}{3v}\int_0^v 4\pi u^4 f_0(u)\,du + \frac{\Gamma v^2}{3}\int_v^\infty 4\pi u f_0(u)\,du \tag{D.9}
$$

**结构验证**：(D.8) 中 $\frac{1}{v^2}\frac{\partial}{\partial v}(v^2\cdots)$ 是球坐标（速度空间）中径向流的散度形式——保证 $\int_0^\infty C_0^{ee}4\pi v^2 dv = 0$（粒子数守恒）；摩擦项 $A f_0$ 使分布整体向低速漂移，扩散项 $B\,\partial f_0/\partial v$ 使分布展宽。

**第 2 步：Maxwell 背景下的系数（Chandrasekhar 函数）**

对 $f_0 = f_0^{\text{MB}}(v) = n_e(\frac{m_e}{2\pi k_BT_e})^{3/2}e^{-m_ev^2/2k_BT_e}$，定义无量纲变量 $x \equiv \frac{m_e v^2}{2k_BT_e} = \frac{v^2}{2v_T^2}$（$v_T = \sqrt{k_BT_e/m_e}$）与 Chandrasekhar 函数：

$$
\psi(x) = \frac{2}{\sqrt{\pi}}\int_0^x dt\,t^{1/2}e^{-t} = \text{erf}(\sqrt{x}) - \frac{2\sqrt{x}}{\sqrt{\pi}}e^{-x} \tag{D.10}
$$

（$\psi$ 满足 $\psi(0)=0$，$\psi(\infty)=1$；$\psi'(x)=\frac{2}{\sqrt{\pi}}x^{1/2}e^{-x}$。）将 $f_0^{\text{MB}}$ 代入 (D.9) 得：

$$
A^{\text{MB}}(v) = -\frac{\Gamma n_e}{v^2}\psi(x), \qquad
B^{\text{MB}}(v) = \frac{\Gamma n_e}{v}\left[\psi(x) - \psi'(x)\right] \tag{D.11}
$$

（推导利用了 $\int_0^v u^2 f_0^{MB}du$ 等积分到 $\psi$ 函数的映射；$\psi$ 正是 NRL Plasma Formulary 中"弛豫速率"一节所定义的函数 [25]。）

**第 3 步：验证平衡性 $C_0^{ee}(f_0^{\text{MB}}) = 0$**

Maxwell 分布满足 $\frac{\partial f_0^{\text{MB}}}{\partial v} = -\frac{m_e v}{k_BT_e}f_0^{\text{MB}} = -\frac{v}{v_T^2}f_0^{\text{MB}}$。碰撞流为：

$$
J^{\text{MB}} = A^{\text{MB}}f_0^{\text{MB}} + B^{\text{MB}}\frac{\partial f_0^{\text{MB}}}{\partial v} = \left(A^{\text{MB}} - \frac{v}{v_T^2}B^{\text{MB}}\right)f_0^{\text{MB}}
$$

代入 (D.11)，利用 $v/v_T^2 = \sqrt{2}x^{1/2}/v_T$ 及 $\psi'$ 的表达式，可得 $A^{\text{MB}} = \frac{v}{v_T^2}B^{\text{MB}}$（即摩擦与扩散精确平衡——Einstein 关系在速度空间的体现），故 $J^{\text{MB}} = 0$，从而：

$$
C_0^{ee}(f_0^{\text{MB}}) = \frac{1}{v^2}\frac{\partial}{\partial v}(v^2\cdot 0) = 0 \quad\checkmark \tag{D.12}
$$

这从**微观层面**确认了"Maxwell 分布是碰撞平衡态"（正文 §2.1 的假设）。

**第 4 步：线性化（含系数的变分）**

令 $f_0 = f_0^{\text{MB}} + \delta f_0$。由于 (D.9) 中系数 $A,B$ 本身是 $f_0$ 的泛函，线性化包含两类贡献：

$$
\left.\frac{\partial C_0^{ee}}{\partial f_0}\right|_{f_0^{\text{MB}}}\delta f_0 =
\frac{1}{v^2}\frac{\partial}{\partial v}\Bigg[v^2\Bigg(\underbrace{A^{\text{MB}}\delta f_0 + B^{\text{MB}}\frac{\partial(\delta f_0)}{\partial v}}_{\text{① 系数固定，作用在 }\delta f_0} + \underbrace{\delta A\,f_0^{\text{MB}} + \delta B\,\frac{\partial f_0^{\text{MB}}}{\partial v}}_{\text{② 系数变分，作用在 }f_0^{\text{MB}}}\Bigg)\Bigg] \tag{D.13}
$$

其中 ① 是**局部（微分）算子**（对角部分），② 中的 $\delta A,\delta B$ 由 (D.9) 对 $f_0$ 的线性变分给出：

$$
\delta A(v) = -\frac{\Gamma}{v^2}\int_0^v 4\pi u^2\delta f_0(u)\,du, \qquad
\delta B(v) = \frac{\Gamma}{3v}\int_0^v 4\pi u^4\delta f_0(u)\,du + \frac{\Gamma v^2}{3}\int_v^\infty 4\pi u\,\delta f_0(u)\,du \tag{D.14}
$$

（② 是**积分（非局部）算子**——这正是 Landau 算子"积分算子"性质的来源。）

**第 5 步：局部扰动的弛豫——BGK 近似的物理基础**

考虑一个速度空间的**窄峰扰动** $\delta f_0(v) = \epsilon\,\delta(v-v_0)$（宽度 $\Delta v \ll v_0$）。分析 (D.13) 在 $v\approx v_0$ 处的效应：

- **①（局部部分）**：扩散项 $B^{\text{MB}}(v_0)\partial^2(\delta f_0)/\partial v^2$ 以速率 $\sim B^{\text{MB}}(v_0)/\Delta v^2$ 使窄峰展宽；摩擦项 $A^{\text{MB}}(v_0)\delta f_0$ 使峰整体向低速漂移。二者共同作用使峰衰减，**特征衰减率**：

$$
\nu_{ee}(v_0) \sim \frac{B^{\text{MB}}(v_0)}{v_0^2} \sim \frac{|A^{\text{MB}}(v_0)|}{v_0} \quad\Rightarrow\quad \nu_{ee}(v) \sim \frac{\Gamma n_e}{v^3}\psi(x) \tag{D.15}
$$

- **②（非局部部分）**：$\delta A,\delta B$ 含 $\int_0^v u^2\delta f_0 du$ 等积分。对窄峰，在 $v>v_0$ 处这些积分 $\sim \epsilon v_0^2$（常数），在 $v<v_0$ 处为零——它们与 $f_0^{\text{MB}}$ 结合给出 $O(\epsilon)$ 的**平滑背景修正**，其速度结构与 $\delta f_0$ 本身不同（是"长程"的重分布），特征弛豫率与①同量级但作用在宽速度范围上。

**关键结论**：对速度 $v$ 附近的局部扰动，e-e 碰撞的主导弛豫由**局部碰撞频率** $\nu_{ee}(v)$ 刻画（①部分）；非局部耦合（②部分）改变的是不同速度模之间的能量重分配，其弛豫率与 $\nu_{ee}(v)$ 同量级。因此，用局部乘法算子 $-\nu_{ee}(v)\delta f_0$ 替代整个线性化算子 (D.13)，**抓住了主导弛豫模**——这就是弛豫时间近似（BGK 型近似）的物理依据。

**第 6 步：NRL 弛豫速率公式的定量佐证**

NRL Plasma Formulary [25] 给出 test 粒子（$\alpha$）在 Maxwell 背景（$\beta$）中的弛豫速率：

$$
\nu_0^{\alpha|\beta} = \frac{4\pi e_\alpha^2 e_\beta^2 \lambda_{\alpha\beta} n_\beta}{m_\alpha^2 v_\alpha^3}, \qquad
x^{\alpha|\beta} = \frac{m_\beta v_\alpha^2}{2kT_\beta} \tag{D.16}
$$

对 e-e 碰撞（$\alpha=\beta=e$）：$e_\alpha e_\beta = e^2$，$m_\alpha = m_e$，$n_\beta = n_e$，$\lambda_{ee} = \ln\Lambda_{ee}$：

$$
\nu_0^{e|e}(v) = \frac{4\pi n_e e^4\ln\Lambda_{ee}}{m_e^2 v^3} \tag{D.17}
$$

慢化率（slowing-down）：$\nu_s^{e|e} = (1+m_e/m_e)\psi(x)\nu_0^{e|e} = 2\psi(x)\nu_0^{e|e}$；高能极限 $x\gg1$ 时 $\psi\to1$，故：

$$
\nu_s^{e|e},\ \nu_\perp^{e|e},\ \nu_\epsilon^{e|e} \xrightarrow{v\gg v_T} 2\nu_0^{e|e}(v) = \frac{8\pi n_e e^4\ln\Lambda}{m_e^2 v^3} \propto v^{-3} \tag{D.18}
$$

（NRL 表格中"Fast"列 $7.7\times10^{-6}\epsilon^{-3/2}$ 正是 $2\nu_0^{e|e}$ 的实用单位形式，$\epsilon^{-3/2}\propto v^{-3}$。）**这说明**：$\nu_{ee}(v)$ 作为 $f_0$ 的能量弛豫速率，其高能极限正比于 $v^{-3}$，数值因子为 $2$（本文正文与附录采用 $\nu_{ee} = \nu_0^{e|e} = \frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3}$ 的量级形式，数值因子 $2$ 不影响速度标度与后续扩散方程结构——它可被吸收进自由程标度约定，见正文 §5.6 与附录 D.5 第 4 点）。

**第 7 步：结论**

综合第 5-6 步，线性化算子对主导弛豫模的作用等价于局部乘法算子，故：

$$
\boxed{\left.\frac{\partial C_0}{\partial f_0}\right|_{f_0^{\text{MB}}}\delta f_0 \approx -\nu_{ee}(v)\,\delta f_0} \tag{D.3}
$$

**近似误差分析**：(D.3) 的误差来自两点——(i) 丢弃了 (D.13) 中的非局部项 ②（不同速度模之间的耦合）；(ii) 用标量 $\nu_{ee}(v)$ 替代了线性化算子的完整本征谱（Landau 算子对不同速度模的弛豫速率有差异）。对 SNB 关心的载热电子（$v\sim 2-4v_T$，高能端），$\nu_{ee}(v)\propto v^{-3}$ 的标度精确，误差主要体现在低速端（$v\lesssim v_T$）的模耦合上，而这些低速电子对热流贡献小（见正文 §2.2 权重函数 $\beta^4(\beta-4)e^{-\beta}$）。

### D.4 $\nu_{ee}(v) \propto v^{-3}$ 的推导

电子-电子碰撞频率：

$$
\nu_{ee}(v) = n_e\,\sigma(v)\,v \tag{D.4}
$$

Coulomb 散射截面（小角度散射累积，含 Coulomb 对数）[7,25]：

$$
\sigma(v) \propto \frac{e^4}{m_e^2 v^4}\ln\Lambda \propto v^{-4} \tag{D.5}
$$

代入 (D.4)：

$$
\boxed{\nu_{ee}(v) \propto n_e\,v^{-4}\cdot v = n_e\,v^{-3} \propto v^{-3}} \tag{D.6}
$$

精确形式（Gaussian 单位）：

$$
\nu_{ee}(v) = \frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3} \tag{D.7}
$$

对比 e-i 有效碰撞频率（正文 (1.8)）：$\nu_{ei}^*(v) = (Z+1)\frac{4\pi n_e e^4\ln\Lambda}{m_e^2 v^3} = (Z+1)\nu_{ee}(v)$。

### D.5 该近似的精度与局限

1. **优点**：将积分算子局部化，使 Jacobian 可解析处理（Schurtz 2000 [1, §III.F] 原文："$\partial C_0/\partial f_0$ is correctly approximated by the electron–electron velocity dependent collision frequency $-\nu_{ee}(v)$"）。
2. **局限**：忽略了对 $\delta f_0$ 不同速度模弛豫速率的差异（Landau 算子对不同 $v$ 的模弛豫速率不同）；仅对"主导弛豫模"精确。
3. **适用范围**：高 $Z$（Lorentz 气体）极限下 $f_0$ 麦克斯韦化仍由 e-e 碰撞主导，此近似仍然合理；数值上该近似保证了迭代算法收敛（$\mathcal{L}^{-1}\mathcal{J}$ 的特征值聚集在 1 附近）[1]。
4. 与正文 §5.6 的约定衔接：正文在从 (5.6a) 过渡到 (5.9) 时采用 $\nu_{ee}(v) = \sqrt{Z}v/\lambda(v) = \nu_{ei}'(v)$ 的标度约定（见 §5.6"碰撞频率的约定"），使最终算子形式与 Schurtz 原文 Eq.(57) 一致——这是对 e-e 与 e-i 弛豫频率同阶的合理简化（$Z \sim 1$ 时 $\nu_{ee} \sim \nu_{ei}'$；高 $Z$ 时该约定吸收 $Z$ 因子进入 $\lambda$ 的定义）。

---

<a name="appE"></a>
## 附录 E：第 $n=0$ 次迭代方程的详细推导

### E.1 初始条件与残差

初始猜测（正文 §5.4）：$\mathbf{X}^0 = (f_0^{\text{MB}}, \mathbf{f}_1^{\text{MB}}, \mathbf{E}^{\text{MB}})$。

由 (5.1) 定义，残差为：

$$
\mathcal{F}_0^0 = \underbrace{C_0(f_0^{\text{MB}})}_{=0} - v\nabla\cdot\mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v} = -v\nabla\cdot\mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v} \tag{E.1}
$$

$$
\mathcal{F}_1^0 = -\nu_{ei}^*\mathbf{f}_1^{\text{MB}} - \frac{v}{3}\nabla f_0^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{3m_e}\frac{\partial f_0^{\text{MB}}}{\partial v} = 0 \tag{E.2}
$$

（$\mathbf{f}_1^{\text{MB}}$ 与 $\mathbf{E}^{\text{MB}}$ 精确满足一阶矩方程 (1.9b)，见正文 §2.3 的构造——将 (2.3)(2.4) 代入 (1.9b) 可逐项验证。）

$$
\mathcal{F}_E^0 = \int_0^\infty\left[v\nabla f_0^{\text{MB}} - \frac{e\mathbf{E}^{\text{MB}}}{m_e}\frac{\partial f_0^{\text{MB}}}{\partial v}\right]v^6 dv = 0 \tag{E.3}
$$

（$\mathbf{E}^{\text{MB}}$ 由零电流条件 (5.1c) 确定，见正文 §2.2 与附录 B。）

### E.2 近似 Jacobian 代入线性化方程

将近似 Jacobian (5.4) 与残差 $\mathbf{F}(\mathbf{X}^0) = (\mathcal{F}_0^0, 0, 0)^T$ 代入线性化方程 (5.2)：

$$
\begin{pmatrix}
-\nu_{ee}(v) & -v\nabla\cdot & 0 \\
-\frac{v}{3}\nabla & -\nu_{ei}^*(v) & 0 \\
0 & 0 & \times
\end{pmatrix}
\begin{pmatrix}
\Delta f_0 \\ \Delta\mathbf{f}_1 \\ \Delta\mathbf{E}
\end{pmatrix}
= -
\begin{pmatrix}
\mathcal{F}_0^0 \\ 0 \\ 0
\end{pmatrix}
\tag{E.4}
$$

### E.3 逐行展开

**第 1 行**：

$$
-\nu_{ee}\Delta f_0 - v\nabla\cdot(\Delta\mathbf{f}_1) = -\mathcal{F}_0^0
$$

两边乘以 $-1$，并代入 (E.1)：

$$
\nu_{ee}\Delta f_0 + v\nabla\cdot(\Delta\mathbf{f}_1) = \mathcal{F}_0^0 = -v\nabla\cdot\mathbf{f}_1^{\text{MB}} + \frac{e\mathbf{E}^{\text{MB}}}{m_e v^2}\frac{\partial(v^2\mathbf{f}_1^{\text{MB}})}{\partial v} \tag{E.5}
$$

**第 2 行**：

$$
-\frac{v}{3}\nabla(\Delta f_0) - \nu_{ei}^*\Delta\mathbf{f}_1 = -\mathcal{F}_1^0 = 0
$$

移项：

$$
\nu_{ei}^*(v)\Delta\mathbf{f}_1 = -\frac{v}{3}\nabla(\Delta f_0) \tag{E.6}
$$

**第 3 行**：$\times\Delta\mathbf{E} = 0$，即电场本轮不更新（保持 $\mathbf{E}^0 = \mathbf{E}^{\text{MB}}$）。事实上 Schurtz 等 [1, Eq. (54)] 给出了电场更新公式 $E^{n+1} = -\frac{m_e}{6e}\frac{\int\partial f_0/\partial v\,v^7 dv}{\int f_0 v^5 dv}$，在 $n \geq 1$ 步才需要。

### E.4 结论

(E.5)、(E.6) 即正文 (5.6a)、(5.6b)，与 Schurtz 原文 Eqs. (55)(56) 完全一致。✓

### E.5 迭代序列的物理内涵

Schurtz 等 [1, §III.F] 明确指出该迭代序列的物理层次：

- **$n=0$ 解**：$\mathbf{f}_1^0 = \mathbf{f}_1^{\text{MB}}$ 给出 Spitzer-Härm **局域**热流；
- **$n=1$ 解**：$f_0^1 = f_0^{\text{MB}} + \Delta f_0$，其中 $\Delta f_0$ 由 (E.5) 的扩散方程驱动（$f_0$ 对 Maxwell 分布的偏离），对应**非局域**热流修正——**这正是 SNB 多群方程 (7.4)(7.5) 的连续速度形式**；
- **$n=2$ 解**：电场修正（非局域 E 场）——对应正文 §8 的电场自洽修正。

因此，SNB 模型 = FP Newton 迭代的第 $n=0\to1$ 步的精确数学推论。

---

<a name="appF"></a>
## 附录 F：近似 Jacobian (5.4) 的逐元素构造与 "$\times$" 记号

本附录回答两个问题：(i) 矩阵 (5.4) 第三行第三列的 "$\times$" 表示什么？(ii) 从精确 Jacobian (5.3) 到近似 Jacobian (5.4)，每个元素是如何被替换的？

### F.1 "$\times$" 记号的含义

(5.4) 第三行第三列的 "$\times$" 表示**该矩阵元被置空（不定义算子，不参与矩阵求解）**。

**原因**：近似 Jacobian 的用途是求解增量 $(\Delta f_0, \Delta\mathbf{f}_1)$——即 (5.2) 线性化系统 (5.6) 的前两个分量。而**电场增量 $\Delta\mathbf{E}$ 不由矩阵方程求解**，而是由独立的解析更新公式在每轮迭代后显式计算（Schurtz 原文 Eq.(54)）：

$$
\mathbf{E}^{n+1} = -\frac{m_e}{6e}\frac{\int \partial f_0/\partial v\,v^7 dv}{\int f_0 v^5 dv} \tag{F.1}
$$

因此，第三行第三列（精确 Jacobian 中本应为 $-\frac{e(\cdot)}{m_e}\int\frac{\partial f_0}{\partial v}v^6 dv$，见 (5.3)）在近似 Jacobian 中用 "$\times$" 标记，表示"**此项不参与增量求解，电场按独立公式更新**"。这不是数值零，而是"不适用/置空"的记号。

**补充说明**：Schurtz 原文 Eq.(51) 中的线性化系统本来就是 $2\times2$ 的（只有 $f_0, f_1$ 两行两列）；本文档 (5.4) 写成 $3\times3$ 是为了与精确 Jacobian (5.3) 保持维度对应，第三行整体"惰性化"（第一、二列置 $0$，第三列置 $\times$）。

### F.2 从精确 Jacobian (5.3) 到近似 Jacobian (5.4) 的逐元素替换

下表逐元素列出 (5.3) → (5.4) 的替换过程。精确值取自附录 C 的 Fréchet 导数表；简化依据是 §5.3 的三条物理考虑：**(S1)** 丢弃所有含 $\mathbf{E}$ 的项（电场项与碰撞/空间导数项之比 $\sim k_BT_e/(m_ev^2)$，高能端可忽略，电场取前次迭代值）；**(S2)** $\partial C_0/\partial f_0 \approx -\nu_{ee}(v)$（BGK 弛豫近似，附录 D）；**(S3)** 碰撞频率用自由程显式表达：$\nu_{ei}^* = v/\lambda_{ei}(v)$，$\nu_{ee} = v/\lambda_{ee}(v)$。

| 矩阵元 | 精确 Jacobian (5.3) | 简化依据 | 近似 Jacobian (5.4) |
|--------|--------------------|---------|---------------------|
| (1,1) $\frac{\partial\mathcal{F}_0}{\partial f_0}$ | $\frac{\partial C_0}{\partial f_0}$（积分算子） | **(S2)**：BGK 弛豫近似，Landau 积分算子 → 局部乘法算子 | $-\nu_{ee}(v)$ |
| (1,2) $\frac{\partial\mathcal{F}_0}{\partial\mathbf{f}_1}$ | $-v\nabla\cdot(\cdot) + \frac{e\mathbf{E}}{m_ev^2}\frac{\partial(v^2(\cdot))}{\partial v}$ | **(S1)**：丢弃含 $\mathbf{E}$ 项 | $-v\nabla\cdot(\cdot)$ |
| (1,3) $\frac{\partial\mathcal{F}_0}{\partial\mathbf{E}}$ | $\frac{e(\cdot)}{m_ev^2}\frac{\partial(v^2\mathbf{f}_1)}{\partial v}$ | **(S1)**：丢弃含 $\mathbf{E}$ 项 | $0$ |
| (2,1) $\frac{\partial\mathcal{F}_1}{\partial f_0}$ | $-\frac{v}{3}\nabla(\cdot) + \frac{e\mathbf{E}}{3m_e}\frac{\partial}{\partial v}(\cdot)$ | **(S1)**：丢弃含 $\mathbf{E}$ 项 | $-\frac{v}{3}\nabla(\cdot)$ |
| (2,2) $\frac{\partial\mathcal{F}_1}{\partial\mathbf{f}_1}$ | $-\nu_{ei}^*(\cdot)$ | **(S3)**：保持形式，$\nu_{ei}^*(v) = v/\lambda_{ei}(v)$ 显式化 | $-\nu_{ei}^*(v)$ |
| (2,3) $\frac{\partial\mathcal{F}_1}{\partial\mathbf{E}}$ | $\frac{e(\cdot)}{3m_e}\frac{\partial f_0}{\partial v}$ | **(S1)**：丢弃含 $\mathbf{E}$ 项 | $0$ |
| (3,1) $\frac{\partial\mathcal{F}_E}{\partial f_0}$ | $\int v\nabla(\cdot)v^6 dv - \frac{e\mathbf{E}}{m_e}\int\frac{\partial(\cdot)}{\partial v}v^6 dv$ | **(S1)** + 第三行整体惰性化（见 F.1） | $0$ |
| (3,2) $\frac{\partial\mathcal{F}_E}{\partial\mathbf{f}_1}$ | $0$ | 不变（$\mathcal{F}_E$ 不显含 $\mathbf{f}_1$，附录 B） | $0$ |
| (3,3) $\frac{\partial\mathcal{F}_E}{\partial\mathbf{E}}$ | $-\frac{e(\cdot)}{m_e}\int\frac{\partial f_0}{\partial v}v^6 dv$ | 电场增量独立更新（F.1），该项置空 | $\times$ |

**逐元注释**：

- **(1,1)**：这是最关键的一步替换——积分算子 $\partial C_0/\partial f_0$ 被局部乘法算子 $-\nu_{ee}(v)$ 替代。完整的推导依据见附录 D（从 Landau 算子的 Fokker-Planck 形式出发，线性化，局部扰动弛豫分析，BGK 近似）。
- **(1,2) 与 (2,1)**：仅丢弃电场项，保留空间导数项。注意 (2,1) 中 $-\frac{v}{3}\nabla$ 来自 $-\frac{v}{3}\nabla f_0$ 项（$f_0$ 的梯度驱动 $\mathbf{f}_1$ 的变分）；保留它是求解 (5.6b) 的关键。
- **(1,3) 与 (2,3)**：电场相关的列被置零——物理上，电场主要影响低能电子（麦克斯韦部分），而 Jacobian 求解的 $\Delta f_0$ 关心高能端偏离（非局域效应来源）。电场对热流的影响通过**源项** $\mathcal{F}_0^0$（含 $\mathbf{E}^{\text{MB}}$ 项，见 (5.5)）已计入，无需在增量方程中显式求解 $\Delta\mathbf{E}$。
- **(3,1)**：精确值含 $\int v\nabla(\cdot)v^6 dv$（非零）。但在近似迭代中，第三行（$\mathcal{F}_E$ 残差，即零电流约束）不参与增量求解——因为 $\mathcal{F}_E^0 = 0$（初值满足零电流），且电场由 (F.1) 独立更新。故置为 $0$。
- **(3,3)**：置为 $\times$（见 F.1）。它与 (3,1) 置零的差异在于：(3,1) 是"该行不参与求解"故置零，而 (3,3) 明确标记"该列对应量（$\Delta\mathbf{E}$）由其他机制求解"。

### F.3 简化后系统的求解结构

代入 (5.4) 后，线性化方程 (5.6) 退化为前两行组成的 $2\times2$ 系统（与 Schurtz 原文 Eq.(51) 一致）：

$$
\begin{pmatrix}
-\nu_{ee}(v) & -v\nabla\cdot \\
-\frac{v}{3}\nabla & -\nu_{ei}^*(v)
\end{pmatrix}
\begin{pmatrix}
\Delta f_0 \\ \Delta\mathbf{f}_1
\end{pmatrix}
=
-
\begin{pmatrix}
\mathcal{F}_0^0 \\ \mathcal{F}_1^0
\end{pmatrix}
\tag{F.2}
$$

求解流程（每轮迭代）：
1. 由 (F.2) 解出 $\Delta f_0, \Delta\mathbf{f}_1$（第 1 轮：$\mathcal{F}_1^0=0$，见附录 E）；
2. 更新 $f_0^{n+1} = f_0^n + \Delta f_0$，$\mathbf{f}_1^{n+1} = \mathbf{f}_1^n + \Delta\mathbf{f}_1$（Schurtz Eqs.(52)(53)）；
3. 由 (F.1) 显式更新 $\mathbf{E}^{n+1}$（Schurtz Eq.(54)）。

**物理理由汇总**（为何可以这样简化）：
1. 电场项的量级 $\sim k_BT_e/(m_ev^2)$ 在高能端（$v\gg v_T$）远小于碰撞项——而 Jacobian 关心的正是高能端的 $\Delta f_0$（载热电子）；
2. 电场主要通过**源项**影响热流（$\mathcal{F}_0^0$ 中已含 $\mathbf{E}^{\text{MB}}$），增量方程中 $\Delta\mathbf{E}$ 的贡献是二阶小量；
3. 零电流约束（第三行）在 $n=0$ 步已由 $\mathbf{E}^{\text{MB}}$ 满足，非局域电场效应（$n=2$ 步）不是 SNB 一阶模型的内容（对应正文 §8 的电场修正，通过修改 $\lambda_g$ 纳入）。

---

<a name="sec10"></a>
## 参考文献（含本地文献对应）

### 核心文献（本地数据库中已收录）

**[1]** G. P. Schurtz, P. D. Nicolaï, and M. Busquet, "A nonlocal electron conduction model for multidimensional radiation hydrodynamics codes," *Physics of Plasmas*, vol. 7, no. 10, pp. 4238–4249, 2000. 
> **本地对应**：ⓘ 参考（无本地PDF，有链接） — 原始 SNB 论文，包含全部核心推导。本文档 §1-§8 的关键公式（Eqs. 1-59）均来源于此文。

**[2]** J. F. Luciani, P. Mora, and J. Virmont, "Nonlocal heat transport due to steep temperature gradients," *Physical Review Letters*, vol. 51, no. 18, pp. 1664–1667, 1983. 
> LMV 非局域卷积公式的原始论文。

**[3]** 袁文强, 赵忠海, 乔宾, "辐射流体程序中的非局域电子热传导," *计算物理*, vol. 40, no. 2, pp. 232–244, 2023. DOI: 10.19596/j.cnki.1001-246x.8616.
> **本地对应**：`txt/袁文强2023-辐射流体程序中的非局域电子热传导.txt` — SNB 在 FLASH 中的实现，包含中文推导和验证（仅有文本提取版，无 PDF）。

**[4]** J. P. Brodrick, R. J. Kingham, M. M. Marinak, et al., "Testing nonlocal models of electron thermal conduction for magnetic and inertial confinement fusion applications," *Physics of Plasmas*, vol. 24, no. 9, p. 092309, 2017. DOI: 10.1063/1.5001079.
> **本地对应**：`SNB_model/Brodrick2017-SNB非局域模型的VFP基准测试.pdf` — SNB vs VFP 基准对比。

**[5]** M. Sherlock, J. P. Brodrick, and C. P. Ridgers, "A comparison of non-local electron transport models for laser-plasmas relevant to inertial confinement fusion," *Physics of Plasmas*, vol. 24, no. 8, p. 082706, 2017. DOI: 10.1063/1.4986095.
> SNB 与 VFP(K2) 详细对比。

### 基础文献

**[6]** M. N. Rosenbluth, W. M. MacDonald, and D. L. Judd, "Fokker-Planck equation for an inverse-square force," *Physical Review*, vol. 107, no. 1, pp. 1–6, 1957. DOI: 10.1103/PhysRev.107.1.
> Fokker-Planck 碰撞算子的标准推导。

**[7]** L. Spitzer, Jr. and R. Härm, "Transport phenomena in a completely ionized gas," *Physical Review*, vol. 89, no. 5, pp. 977–981, 1953. DOI: 10.1103/PhysRev.89.977.
> Spitzer-Härm 热传导理论的原始论文。

**[8]** J. P. Matte, "Electron heat transport in laser-produced plasmas," Ph.D. thesis, École Polytechnique, France, 1987.
> P1 球谐展开在激光等离子体中的系统验证。

**[9]** S. I. Braginskii, "Transport processes in a plasma," in *Reviews of Plasma Physics*, M. A. Leontovich, Ed., vol. 1, pp. 205–311. New York: Consultants Bureau, 1965.
> 磁化等离子体输运系数的经典参考。

**[10]** E. M. Epperlein and M. G. Haines, "Plasma transport coefficients in a magnetic field by direct numerical solution of the Fokker-Planck equation," *Physics of Fluids*, vol. 29, no. 4, pp. 1029–1041, 1986. DOI: 10.1063/1.865901.
> Epperlein-Haines 修正因子 $\xi(Z)$ 的来源。

**[11]** A. Decoster, in *La Fusion Thermonucléaire Inertielle par Laser*, R. Dautray and J. P. Watteau, Eds., vol. 2, p. 827. Paris: Eyrolles, 1993.
> 热流速度分辨贡献的详细推导。

### SNB 后续发展与验证

**[12]** A. R. Bell, R. G. Evans, and D. J. Nicholas, "Electron energy transport in steep temperature gradients in laser-produced plasmas," *Physical Review Letters*, vol. 46, no. 4, pp. 243–246, 1981. DOI: 10.1103/PhysRevLett.46.243.
> Bell 判据——FP 模拟首次定量证实 SH 失效。

**[13]** E. M. Epperlein and R. W. Short, "A practical nonlocal model for electron heat transport in laser plasmas," *Physics of Fluids B*, vol. 3, no. 11, pp. 3092–3098, 1991. DOI: 10.1063/1.859789.
> Epperlein-Short 傅里叶空间非局域模型的原始论文。

**[14]** P. Mora and J. F. Luciani, "Nonlocal electron transport in laser created plasmas," *Laser and Particle Beams*, vol. 12, no. 3, pp. 387–400, 1994. DOI: 10.1017/S0263034600008319.
> 速度分辨的 LMV 传播子 $W_3$ 的详细讨论。

**[15]** 赵斌, 郑坚, "激光等离子体中电子热输运的 Fokker-Planck 模拟," 2012.
> **本地对应**：`pdfs/elec_transport/` — 中文 FP 模拟文献。

**[16]** T. D. Arber, T. Goffrey, and C. Ridgers, "Models of thermal conduction and non-local transport of relevance to space physics with insights from laser–plasma theory," *Frontiers in Astronomy and Space Sciences*, vol. 10, p. 1155124, 2023. DOI: 10.3389/fspas.2023.1155124.
> **本地对应**：`SNB_model/Frontiers2023-Frontiers2023热传导非局域输运综述.pdf` — 非局域热传导模型综述。

### SNB 扩展文献（本地数据库中已收录）

**[17]** Z. H. Chen, Z. Q. Zhao, et al., "An improved nonlocal electron heat transport model for magnetized plasmas," *Physics of Plasmas*, 2025. (cf. arXiv:2508.17309)
> **本地对应**：`SNB_model/Chen2025-磁化非局域热输运改进.pdf` — 磁化 SNB 改进。

**[18]** P. D. Nicolaï, J.-L. A. Feugeas, and G. P. Schurtz, "A practical nonlocal model for heat transport in magnetized laser plasmas," *Physics of Plasmas*, vol. 13, no. 3, p. 032701, 2006. DOI: 10.1063/1.2179392.
> 磁化 SNB 推广的原始论文。

**[19]** A. Bendib, J. F. Luciani, and J. P. Matte, "An improvement of the nonlocal heat flux formula," *Physics of Fluids*, vol. 31, no. 4, pp. 711–713, 1988. DOI: 10.1063/1.866804.
> 电场修正的原始方案。

**[20]** R. J. Henchen, M. Sherlock, W. Rozmus, et al., "Observation of nonlocal heat flux using Thomson scattering," *Physical Review Letters*, vol. 121, p. 125001, 2018. 
> **本地对应**：ⓘ 参考（无本地PDF，有链接） — 非局域热流的实验观测。

**[21]** D. Del Sorbo, J.-L. Feugeas, P. Nicolaï, et al., "Reduced entropic model for studies of multidimensional nonlocal transport in high-energy-density plasmas," *Physics of Plasmas*, vol. 22, no. 8, p. 082706, 2015. 
> **本地对应**：ⓘ 参考（无本地PDF，有链接） — 约化熵模型的扩展。

**[22]** M. Luo, C. Heaton, Y. Wang, et al., "Learning heat transport kernels using a nonlocal heat transport theory-informed neural network," arXiv:2506.16619, 2025.
> **本地对应**：ⓘ 参考（无本地PDF，有链接） — SNB-TINN，神经网络学习热核。

### 数值工具

**[23]** B. Fryxell, K. Olson, P. Ricker, et al., "FLASH: An adaptive mesh hydrodynamics code for modeling astrophysical thermonuclear flashes," *The Astrophysical Journal Supplement Series*, vol. 131, no. 1, pp. 273–334, 2000. DOI: 10.1086/317361.
> FLASH 辐射流体代码，SNB 模型的核心实现平台。

**[24]** R. D. Falgout and U. M. Yang, "hypre: A library of high performance preconditioners," in *Computational Science — ICCS 2002*, ser. LNCS, vol. 2331. Springer, 2002, pp. 632–641. DOI: 10.1007/3-540-47789-6_66.
> HYPRE 科学计算库，用于高效求解 Helmholtz 方程 (7.4)。

### 附录补充文献

**[25]** J. D. Huba, *NRL Plasma Formulary*, Naval Research Laboratory, Washington, DC, 2019.
> **本地对应**：`txt/Huba2019-NRL Plasma Formulary (18th Edition).txt` — 附录 D 中 e-e 弛豫速率公式（$\nu_0^{e|e}$、慢化率/扩散率及其高能极限）的来源。

---

> **文档声明**：本文档中所有公式均基于 Schurtz, Nicolaï & Busquet (2000) [1] 的公开推导步骤，所有引用已在参考文献中明确列出对应本地文献文件名。任何公式错误或不准确之处，欢迎对照原始论文核查指正。
>
> **审阅建议**：关键推导步骤 §5（从 FP 方程到 SNB 的迭代推导）建议对照原文 [1, §III.F, pp. 4243-4245] 仔细核查。
