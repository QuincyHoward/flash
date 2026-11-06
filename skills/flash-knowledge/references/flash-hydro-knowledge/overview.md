---
title: Hydro 单元总览 — 角色、6 变体、split/unsplit 设计、Riemann solver、MHD
skill: flash-hydro
category: overview
source_anchors:
  - source/physics/Hydro/HydroMain/Config:L5-L7
  - source/physics/Hydro/HydroMain/unsplit/Config:L14-L156
  - source/physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90:L412-L462
  - source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90:L64
  - source/physics/Hydro/HydroMain/split/PPM/Config
  - source/physics/Hydro/HydroMain/hy_slopeLimiters.F90:L39-L84
manual_ref: "FLASH 4.8 User Guide §9-12"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - hydro
  - overview
  - split
  - unsplit
  - Riemann
  - MHD
---

# Hydro 单元总览

> **TL;DR**：Hydro 是 FLASH 的"流体求解器核心"，解流体守恒律方程：
>
> ```
> ∂U/∂t + ∇·F(U) = S
> ```
>
> 其中 U = (ρ, ρu, ρv, ρw, E) 是守恒变量（密度、动量、能量），F 是通量，S 是源项。这是经典 **Euler 方程**（描述可压缩无粘流体运动，不是常微分方程里的 Euler 方法）。
>
> FLASH 提供 **6 个互斥变体**（split: PPM/MHD_8Wave/RHD；unsplit: Hydro_Unsplit/MHD_StaggeredMesh；unsplit_rad），按 setup 命令选择。**默认 = unsplit/Hydro_Unsplit + HLLC Riemann + vanLeer limiter**。

---

## 1. Hydro 在 FLASH 里扮演什么角色

### 1.1 一句话定位

Hydro 单元 = **解流体力学方程的求解器**。给 Grid 里的 `unk` 数组（密度、动量、能量）做一步时间推进，考虑：
- **对流**（Euler 方程的通量项）
- **激波捕获**（Riemann solver + limiter）
- **几何/守恒修正**（cylindrical/spherical 下体积、面积加权）
- **MHD 扩展**（磁场演化 + ∇·B 处理）

### 1.2 为什么 Hydro 是"求解器核心"

FLASH 是**显式 Godunov 类**有限体积代码。每步：

```
U^{n+1} = U^n - (dt/dV) * [F(U^{n+1/2}_right) - F(U^{n+1/2}_left)] * A + S * dt
```

这里 `F(U)` 是数值通量，**核心就是 Hydro 单元算的**。其他物理过程（EOS、激光、扩散）都是源项 `S` 或修改 `U`，Hydro 是骨架。

### 1.3 与其他单元的耦合

```
┌────────────────────────────────────────────────┐
│ Driver_evolveFlash                             │
│   ├── Grid_fillGuardCells(CENTER, ALLDIR) ★    │  ← Grid 填 guard cell
│   ├── Hydro_computeDt ★                        │  ← Hydro 算每 block 的 CFL 限制
│   │       └── Driver_computeDt 汇总全局 dt
│   ├── Hydro(blockCount, blockList, dt, ...) ★  │  ← Hydro 主推进
│   │   ├── 读 unk（CENTER）via Grid_getBlkPtr
│   │   ├── 算 Riemann flux
│   │   ├── 保守更新 U^{n+1}
│   │   ├── AMR flux correction（Grid_putFluxData/Grid_conserveFluxes）
│   │   └── EOS 调和（让 dens/ener/temp 自洽）
│   ├── Eos_wrapped（让变量一致）
│   ├── Driver_sourceTerms（含激光）
│   └── Grid_updateRefinement（每 nrefs 步）
└────────────────────────────────────────────────┘
```

---

## 2. 6 个变体一览

源码：`source/physics/Hydro/HydroMain/Config:L5-L7`

```
DEFAULT unsplit
EXCLUSIVE split unsplit unsplit_old unsplit_tiles simpleUnsplit unsplit_rad
```

| 变体 | 路径 | setup 命令 | 用途 |
|---|---|---|---|
| **Hydro_Unsplit**（默认） | `unsplit/Hydro_Unsplit/` | `+uhd` / `+unsplitHydro` 或不指定 | **纯流体 CTU**——99% 算例 |
| **MHD_StaggeredMesh** | `unsplit/MHD_StaggeredMesh/` | `+usm` | **USM-MHD with CT**——磁场演化 |
| **split/PPM** | `split/PPM/` | `+splitHydro` | Fryxell-Mueller PPM，燃烧算例遗产 |
| **split/MHD_8Wave** | `split/MHD_8Wave/` | `+8wave` | Powell 8-wave MHD，分裂法 |
| **split/RHD** | `split/RHD/` | （罕见） | 相对论流体（HLLE）；Config 写"PLUTO 更好" |
| **unsplit_rad** | `unsplit_rad/` | `+uhdr` / `+usmr` | RadFLAH 辐射流体耦合 |

### 2.1 默认选择链

不指定时层层回退：

```
HydroMain/Config: DEFAULT unsplit
  → unsplit/Config: DEFAULT Hydro_Unsplit
```

所以**默认 = unsplit/Hydro_Unsplit**（纯流体 CTU + HLLC + vanLeer + order=2）。

### 2.2 为什么有这么多变体

不同物理问题对求解器需求**根本不同**：

| 物理 | 必须的特性 | 推荐变体 |
|---|---|---|
| 普通流体（激波管、ICF） | 多维 Godunov、CFL≤1 | Hydro_Unsplit |
| 磁流体（MHD） | ∇·B 控制（CT） | MHD_StaggeredMesh (USM) |
| 燃烧 / XRB / SN Ia | 简单可靠 + 历史验证 | split/PPM（Strang 分裂） |
| 相对论流（RHD） | 协变形式 | split/RHD（或 PLUTO） |
| 辐射流体 | Eddington 张量耦合 | unsplit_rad |

如果只有 1 个变体，某些物理问题就做不了。

---

## 3. Split vs Unsplit 设计差异（核心概念）

### 3.1 数学差别

流体方程 $\partial U/\partial t + \nabla \cdot F = 0$ 展开成三维：

$$\frac{\partial U}{\partial t} + \frac{\partial F_x}{\partial x} + \frac{\partial F_y}{\partial y} + \frac{\partial F_z}{\partial z} = 0$$

**Split (Strang 分裂)**：把 3D 更新拆成 3 个 1D 更新：

```
U^{n+1} = R_x(Δt/2) R_y(Δt/2) R_z(Δt) R_y(Δt/2) R_x(Δt/2) U^n
```

每个 R_* 是 1D Godunov sweep（用 Riemann solver 算 1D 通量）。

**Unsplit (CTU / Corner Transport Upwind)**：一次更新，同时考虑 6 个面的通量 + transverse correction：

```
U^{n+1}_{i,j,k} = U^n_{i,j,k} - (dt/dV) * Σ_faces [F(U) * A] + transverse corrections
```

### 3.2 为什么默认 unsplit

| 角度 | Split | Unsplit |
|---|---|---|
| **精度** | 2 阶（Strang），但有 O(Δt·Δx²) 分裂误差 | 2 阶 CTU，**无分裂误差** |
| **CFL 限制** | CFL ≤ 1（每维） | CFL ≤ 1（3D 全 CTU）或 ≤ 1/2（简化） |
| **多维激波** | 斜激波有分裂误差 | 正确处理斜激波 |
| **MHD 兼容** | 勉强（Powell 8-wave 加源项） | 自然（CT） |
| **3T / 多流体 / Hall** | 不支持 | 支持 |
| **性能** | 3 次 sweep，cache 不友好 | 1 次更新，可向量化 |
| **代码复杂度** | 简单 | 复杂（transverse flux） |

**结论**：unsplit 综合优势大，FLASH 4 默认。split 留给燃烧算例（PPM 历史悠久、验证充分）和移植旧算例。

### 3.3 什么时候选 split

- **燃烧 / 火焰算例**：FLASH 早期燃烧验证都基于 split PPM
- **SN Ia / XRB 模拟**：社区习惯用 PPM
- **从 FLASH 2/3 移植的旧算例**：可能依赖 PPM 的具体行为

新算例**不要默认用 split**，除非有上述特殊需求。

---

## 4. CTU 流程（unsplit 主循环）

源码：`source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90:L64`

```
Hydro(blockCount, blockList, dt, ...)
└── 对每个 block:
    └── hy_uhd_unsplit(blockID, ...)
        │
        ├── 1. 填 guard cell（含 EOS 调和）
        │   └── Grid_fillGuardCells(CENTER, ALLDIR, eosMode=hy_eosModeGc, mask=hy_gcMask)
        │
        ├── 2. 激波探测（可选）
        │   └── hy_uhd_shockDetect → 标记 SHOK_VAR
        │
        ├── 3. 数据重构（计算每个面的 left/right state）
        │   ├── hy_uhd_dataReconstOneStep 或
        │   ├── hy_uhd_DataReconstructNormalDir_PCM/MH/PPM/WENO/GP
        │   │   （按 order 选：1=PCM, 2=MH, 3=PPM, 5=WENO, 6=GP）
        │   └── 应用 slope limiter（hy_uhd_TVDslope）
        │
        ├── 4. Riemann solver（每个面算通量）
        │   └── hy_uhd_getFaceFlux → 按hy_RiemannSolver dispatch:
        │       ├── HLL → hy_uhd_HLL
        │       ├── HLLC → hy_uhd_HLLC ★ 默认
        │       ├── HLLD → hy_uhd_HLLD（MHD only）
        │       ├── Roe → hy_uhd_Roe（含 entropyFix）
        │       ├── LLF → hy_uhd_LLF
        │       ├── Marquina → hy_uhd_Marquina
        │       └── Hybrid → 激波处 HLL，其他 HLLC
        │
        ├── 5. Transverse flux（3D CTU）
        │   └── 跨方向修正（如果 use_3dFullCTU=TRUE）
        │
        ├── 6. AMR flux correction
        │   ├── Grid_putFluxData → 存到 gr_xflx/yflx/zflx
        │   ├── Grid_conserveFluxes → 跨 block 守恒修正
        │   └── Grid_getFluxData → 读回修正后通量
        │
        ├── 7. 保守更新
        │   └── hy_uhd_unsplitUpdate → U^{n+1} = U^n - dt/dV * Σ(F*A)
        │
        ├── 8. 能量修正（避免 KE ≫ IE 时消去误差）
        │   └── hy_uhd_energyFix
        │
        ├── 9. MHD 专属（如果是 USM-MHD）
        │   ├── hy_uhd_staggeredDivb → CT 清理 ∇·B
        │   ├── hy_uhd_getElectricFields → 算 edge E 场
        │   └── 非理想 MHD（Hall/Biermann/Nernst/Resistive）
        │
        └── 10. EOS 调和（让 dens/ener/temp 自洽）
            └── Eos_wrapped（CENTER, MODE_DENS_IE）
```

### 4.1 为什么是这个顺序

- **填 guard cell 在最前**：Riemann solver 要看邻居 cell，没有正确 guard cell 会算错
- **激波探测在 Riemann 前**：让 Hybrid solver 知道哪里用 HLL
- **数据重构在 Riemann 前**：要先有 left/right state 才能算通量
- **AMR flux correction 在更新前**：保证 block 边界通量守恒
- **能量修正在更新后**：检查更新结果是否合理
- **EOS 在最后**：让变量物理自洽

---

## 5. Riemann solver 总览

### 5.1 为什么需要 Riemann solver

Godunov 方法需要在每个 cell 界面解 **Riemann 问题**（左状态 U_L、右状态 U_R，求界面通量 F*）。精确解太贵，所以用近似 Riemann solver。

### 5.2 8 个选项（默认 HLLC）

源码：`source/physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90:L412-L462`

| Solver | 物理模型 | 恢复的波 | 何时选 |
|---|---|---|---|
| **HLLC**（默认） | 3 中间态（信号速度 L、*、R） | 接触间断 | **大多数情况** |
| HLL | 2 中间态 | 不恢复接触 | 极强激波、需要鲁棒 |
| HLLD | 5 中间态 | Alfvén + 接触 + 慢磁声波 | MHD 推荐 |
| Roe | 线性化精确 | 全部 7（MHD 9）波 | 接触陡峭，需 entropy fix |
| LLF (Local Lax-Friedrichs) | 1 中间态 | 不恢复 | 最鲁棒但最耗散，调试用 |
| Marquina | 特征分裂 | 全部波 | 强激波鲁棒，昂贵 |
| MarquinaModified | Marquina 改进 | 全部波 | 改进版 |
| Hybrid | 自适应 | 看情况 | 激波区 HLL + 其他 HLLC |
| Zero | 0 通量 | — | 调试 |

### 5.3 为什么默认 HLLC

HLLC（Toro 1994）的**关键改进**：在 HLL 的两信号速度之间加了**接触波**（"C" = Contact）。

**为什么重要**：
- **接触间断** = 密度跳变但压力、速度连续（如两种流体界面）
- HLL 假设中间只有一个均匀态，会**抹平接触**（数值耗散）
- HLLC 恢复接触间断，**密度界面清晰**

**为什么不默认 Roe**：
- Roe 更精确（解线性 Riemann 问题），但需要：
  - 计算 Roe 平均（特征值、特征向量）
  - entropy fix（避免膨胀激波）
  - 不保守（MHD 下）
- HLLC 简单、保守、稳定，**够用**就用它

### 5.4 何时换其他

| 场景 | 换成 | 原因 |
|---|---|---|
| MHD | HLLD | MHD 有 7 波（Alfvén、慢/快磁声波），HLLC 不能解 |
| 极强激波（高 Mach 数） | Hybrid 或 HLL | HLLC 可能在强激波崩（负密度） |
| 需要接触陡峭（如流体界面） | Roe | Roe 比利普 less diffusive |
| 调试 / 单位测试 | LLF 或 Zero | 最简最鲁棒 |

---

## 6. MHD 处理（USM vs 8-wave）

### 6.1 MHD 加了什么

纯流体 5 个变量（ρ, ρu, ρv, ρw, E）。MHD 加：
- 3 个磁场分量（Bx, By, Bz）
- 磁压（p_mag = B²/2μ₀）加到总压
- 5 个额外通量（电磁感应方程 ∂B/∂t = -∇×E）
- 7 波 Riemann 结构（快/Alfvén/慢/熵/慢/Alfvén/快）

### 6.2 ∇·B 问题（MHD 核心难点）

Maxwell 方程要求 ∇·B = 0（无磁单极子）。但数值离散后 ∇·B 可能非零，导致：
- 非物理力（沿 ∇·B 方向的伪力）
- 能量不守恒
- 长时间漂移

### 6.3 3 种处理方法

| 方法 | 怎么做 | 优点 | 缺点 | 在 FLASH 里 |
|---|---|---|---|---|
| **Constrained Transport (CT)** | 磁场在 **face 中心**（staggered），用电场的 edge curl 更新 | ∇·B 保持机器精度 | 实现复杂 | **USM-MHD**（默认 +usm） |
| **Powell 8-wave** | 加源项 -B(∇·B)，让方程"容忍" ∇·B ≠ 0 | 简单，可分裂 | ∇·B 漂移但稳定 | split/MHD_8Wave（+8wave） |
| **GLM-MHD** (Dedner) | 加 ψ 场，扩散+对流清理 ∇·B | 介于两者 | 需要 c_h、α 参数 | UG + `FLASH_UGLM_MHD` |

### 6.4 USM-CT 怎么实现

源码：`source/physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh/`

```
B 场在 face 中心（facevarx/y/z），不是 cell 中心
│
├── hy_uhd_unsplit 算出 face flux（含磁场通量）
│
├── hy_uhd_getElectricFields  ★ 从通量算 edge 电场
│   └── E = -(v × B) 在 cell 边
│
├── hy_uhd_staggeredDivb  ★ 用 CT 公式更新 B
│   └── B^{n+1}_face = B^n_face + dt * curl(E_edge)
│   └── 离散 curl 保证 div(B) = div(curl(E)) ≡ 0（恒等）
│
└── ∇·B 保持机器精度
```

### 6.5 为什么 USM 是默认

- **精度高**：∇·B 保持机器精度，长时间 MHD 模拟稳定
- **支持非理想 MHD**：Hall、Biermann、Nernst 等扩展都基于 USM
- **社区标准**：现代 HEDP（激光等离子体）都用 USM

### 6.6 什么时候选 8-wave

- 旧算例移植（依赖 Powell 8-wave 的具体行为）
- 简单算例不需要 CT 的精度（如教学示例）
- 配合 split PPM（MHD_8Wave 是 split 体系）

---

## 7. 限幅器（slope limiter）

### 7.1 为什么需要

Godunov 方法在每个 cell 内用**重构**得到 left/right state。如果直接用线性重构（无限制），激波附近会出**振荡**（Gibbs 现象）。限幅器的作用：在陡峭处降低重构阶数，保证 TVD（Total Variation Diminishing）。

### 7.2 6 个选项（默认 vanLeer）

源码：`source/physics/Hydro/HydroMain/hy_slopeLimiters.F90:L39-L84`，调度在 `hy_uhd_TVDslope.F90:L89`

| Limiter | 性质 | 何时选 |
|---|---|---|
| minmod | 最耗散 | 数值不稳定时的兜底 |
| **vanLeer**（默认） | 平衡 | 大多数情况 |
| vanLeer1.5 | 略锐 | vanLeer 不够锋利时 |
| MC (monotonized central) | 锐 | 想要更高分辨率 |
| hybrid | 特征变量用 minmod，原始变量用 vanLeer | 兼顾稳定和精度 |
| limited | 自定义 β | 实验用 |

### 7.3 charLimiting（特征变量限制）

源码：`source/physics/Hydro/HydroMain/unsplit/Config:L96`

`charLimiting=.TRUE.`（默认）让限幅器作用在**特征变量**上（投影到特征空间），而不是原始变量。

**为什么**：每族波（声波、熵波、剪切波）应该独立限制。在原始变量空间限制会**耦合不同波族**，导致激波附近失真。

### 7.4 为什么默认 vanLeer + charLimiting

- vanLeer 平衡耗散和锋利度，激波附近稳定
- charLimiting 让限制物理上合理
- 组合是经过大量算例验证的"安全默认"

---

## 8. CFL 与时间步

### 8.1 hy_cfl 默认 0.8

源码：`source/physics/Hydro/HydroMain/Config:L26`

```fortran
PARAMETER REAL cfl 0.8 CONSTANT
```

**为什么 0.8**：
- CTU 理论稳定限 CFL ≤ 1（Colella 1990）
- 非线性效应（强激波、高温）实际限更低
- 0.8 留 20% 余量，覆盖大多数算例
- 强激波算例降到 0.4-0.5（更稳但慢）

### 8.2 CFL 怎么算

源码：`source/physics/Hydro/HydroMain/unsplit/Hydro_computeDt.F90`

```
dt_CFL = CFL * min(Δx / (|v_x| + c_s))
```

c_s 是声速（MHD 用 fast magnetosonic speed）。每个 cell 算一个 dt，取最小。

### 8.3 shockLowerCFL（自适应 CFL）

如果 `shockLowerCFL=.TRUE.`（默认 FALSE），在 `hy_uhd_shockDetect` 标记的激波 cell 自动降低 CFL（避开强激波崩溃）。

---

## 9. 与其他单元的耦合

### 9.1 上游（谁调 Hydro）

- **Driver_evolveFlash**：每步调 `Hydro` + `Hydro_computeDt`
- **Grid**：提供 unk 数组（通过 Grid_getBlkPtr）+ AMR flux correction 机制
- **Eos**：Hydro 在 Riemann state 重构和最终更新后调 Eos 让变量自洽

### 9.2 下游（Hydro 调谁）

- **Grid**：guard cell 填充、flux 存储/读取
- **Eos**：MODE_DENS_IE / MODE_DENS_PRES 调和
- **RuntimeParameters**：读 hy_* 参数
- **物理常量**：c, m_e, e（用于单位转换）

### 9.3 边界

| Hydro 不做 | 谁做 |
|---|---|
| 网格结构 / AMR | Grid |
| 主循环调度 | Driver |
| 三温耦合 | Eos |
| 时间步汇总 | Driver_computeDt |
| 重力源项 | Gravity（按 source term 加） |
| 激光 / 燃烧 | sourceTerms |

---

## 10. 延伸阅读

- **参数完整字典**：`knowledge/params.md`
- **CTU 流程详解**：`knowledge/internals.md`
- **典型配置**：`knowledge/recipes.md`
- **常见错误**：`knowledge/pitfalls.md`
- **Grid 单元**：`skills/flash-grid/knowledge/overview.md`
- **Driver 主循环**：`skills/flash-driver/knowledge/internals.md`
- **手册章节**：FLASH 4.8 User Guide §9-12（opencode 转写中）

---

## 11. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：11 段总览 + 6 变体对比 + split/unsplit 设计差异 + Riemann solver 选型 + MHD USM-CT 详解 + 限幅器 + CFL 默认值依据；按 L-011 重点讲"为什么" | claude |
