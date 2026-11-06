---
title: Hydro 典型配置 — 变体 / Riemann / CFL / MHD / 3T
skill: flash-hydro
category: recipes
source_anchors:
  - bin/setup_shortcuts.txt:L61-L76
  - source/physics/Hydro/HydroMain/Config:L5-L7
  - source/physics/Hydro/HydroMain/unsplit/Config:L80-L226
manual_ref: "FLASH 4.8 User Guide §9-12"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - hydro
  - recipe
  - riemann
  - cfl
  - mhd
  - 3t
---

# Hydro 典型配置 recipes

> **TL;DR**：6 类 recipe：变体选择（setup 命令）+ Riemann solver 选择（parfile）+ CFL 调优 + MHD 配置 + 3T 配置 + 强激波鲁棒配置。每个 recipe 标适用场景，按需选。

---

## 0. 通用准备

### 0.1 setup 命令结构回顾

源码：`bin/setup_shortcuts.txt:L61-L76`

| Shortcut | 选什么变体 | 何时用 |
|---|---|---|
| （不指定） | unsplit / Hydro_Unsplit（默认） | 99% 算例 |
| `+uhd` / `+unsplitHydro` | 同上（明确写） | 强调用 unsplit |
| `+usm` | unsplit / MHD_StaggeredMesh（USM-MHD） | 磁流体 |
| `+usmr` | unsplit_rad / MHD_StaggeredMesh | 辐射 MHD（RadFLAH） |
| `+usm3t` | +3t + usm | 三温 MHD |
| `+splitHydro` | split / PPM | 燃烧算例 |
| `+8wave` | split / MHD_8Wave | 旧 MHD 算例移植 |
| `+uhdr` | unsplit_rad / Hydro_Unsplit | 辐射流体 |

**注意**：**没有** `+mhd` 或 `+split` 这两个 shortcut。要用 MHD 选 `+usm`（推荐）或 `+8wave`。

### 0.2 parfile 关键段位置

Hydro 参数在 parfile 顶层（不在 sourceTerm 段）：

```fortran
# 主控
useHydro = .true.
cfl = 0.5

# Riemann solver
RiemannSolver = "HLLC"

# 限幅器
slopeLimiter = "vanLeer"
charLimiting = .true.

# 截断
smlrho = 1.e-10
smallp = 1.e-10
```

---

## 1. 变体选择 recipe

### Recipe 1.1：unsplit pure hydro（默认）

**适用**：99% 算例（激波管、ICF、激光沉积、外爆）。

```bash
./setup Sedov -2d -auto +cartesian \
    -nxb=8 -nyb=8 \
    -objdir=cases/Sedov
# 不写 +uhd 也是 unsplit（默认）
```

**为什么默认**：见 `knowledge/overview.md §3`。CTU 无分裂误差、CFL≤1、支持所有扩展。

### Recipe 1.2：USM-MHD（磁流体）

**适用**：MHD 算例（磁场演化、磁重联、Alfvén 波）。

```bash
./setup <problem> -3d -auto +usm \
    -nxb=8 -nyb=8 -nzb=8 \
    -objdir=cases/<problem>_mhd
```

**为什么 USM**：见 `knowledge/overview.md §6`。CT 保持 ∇·B 机器精度、支持非理想 MHD（Hall/Biermann/Nernst）。

### Recipe 1.3：split PPM（燃烧）

**适用**：燃烧算例（SN Ia、XRB、detonation）。

```bash
./setup <problem> -2d -auto +splitHydro +flame \
    -objdir=cases/<problem>_flame
```

**为什么 split PPM**：FLASH 早期燃烧验证都基于 PPM，社区习惯。**新算例如不需要燃烧，仍推荐 unsplit**。

### Recipe 1.4：8-wave MHD（移植旧算例）

**适用**：从 FLASH 3 移植的 MHD 算例。

```bash
./setup <problem> -3d -auto +8wave \
    -objdir=cases/<problem>_8w
```

**为什么不推荐新算例**：Powell 8-wave 加伪源项，∇·B 漂移（虽然稳定）。USM-CT 更精确。

---

## 2. CFL 调优 recipe

### Recipe 2.1：标准（默认 0.8）

**适用**：大多数算例（弱-中等激波）。

```fortran
cfl = 0.8       # 默认
```

**为什么 0.8**：CTU 理论稳定限 CFL≤1，0.8 留 20% 余量。

### Recipe 2.2：强激波（降到 0.4-0.5）

**适用**：高 Mach 数激波（>10）、Sedov、激波碰撞。

```fortran
cfl = 0.4
shockDetect = .true.          # 探测激波
shockLowerCFL = .true.        # 激波 cell 自动降 CFL
```

**为什么降**：强激波附近非线性效应使实际稳定限低于 1。0.4 是经验"安全值"。

### Recipe 2.3：保守起步（0.3）

**适用**：第一次跑新算例，不确定稳定性。

```fortran
cfl = 0.3
```

**怎么用**：跑通后逐步加大（0.3 → 0.5 → 0.8），观察是否稳定。最高稳定值就是该算例的"上限"。

### Recipe 2.4：自适应 CFL（高级）

**适用**：算例里有局部强激波但其他区域温和。

```fortran
cfl = 0.8                      # 全局
shockDetect = .true.
shockLowerCFL = .true.         # 激波处自动降到 0.8 * factor
hy_cflFallbackFactor = 0.5     # 降到原来的 50%
```

---

## 3. Riemann solver 选择 recipe

### Recipe 3.1：HLLC（默认）

**适用**：99% 算例。

```fortran
RiemannSolver = "HLLC"
```

**为什么默认**：见 `knowledge/overview.md §5`。恢复接触间断、不需 entropy fix、稳定。

### Recipe 3.2：HLLD（MHD）

**适用**：MHD 算例（+usm）。

```fortran
RiemannSolver = "HLLD"     # 需要 +usm setup
```

**为什么 MHD 用 HLLD**：MHD 有 7 波结构（快/Alfvén/慢/熵/慢/Alfvén/快），HLLC 只能解 3 波。

### Recipe 3.3：Hybrid（强激波鲁棒）

**适用**：极强激波（Mach > 20）、HLLC 出现负密度。

```fortran
RiemannSolver = "Hybrid"   # 自动启用 shockDetect
shockDetect = .true.
```

**机制**：激波处用 HLL（最鲁棒），其他用 HLLC（精度）。

### Recipe 3.4：Roe（接触陡峭）

**适用**：流体界面需要清晰（如 Rayleigh-Taylor 不稳定性）。

```fortran
RiemannSolver = "Roe"
entropy = .true.                # entropy fix（必开）
entropyFixMethod = "HARTENHYMAN"
```

**为什么 Roe 锐但需 entropy fix**：Roe 是线性化精确 Riemann，但跨音速稀疏波会产生"膨胀激波"非物理解。entropy fix 修复这个。

### Recipe 3.5：LLF（调试）

**适用**：算例崩了，怀疑是 Riemann solver 问题；用最鲁棒的 solver 验证。

```fortran
RiemannSolver = "LLF"       # Local Lax-Friedrichs
```

**注意**：LLF 极度耗散，只用于诊断。生产算例不要用。

---

## 4. MHD 配置 recipe

### Recipe 4.1：基础 MHD（USM + CT）

```bash
./setup <problem> -3d -auto +usm \
    -objdir=cases/<problem>_mhd
```

parfile：
```fortran
# MHD 必备
RiemannSolver = "HLLD"
killdivb = .true.                # CT 清理 ∇·B（默认）
prolMethod = "INJECTION_PROL"    # 默认 prolongation
```

### Recipe 4.2：cylindrical MHD（强制 Balsara）

**适用**：柱坐标 MHD（如激光 RZ 算例 + 磁场）。

parfile：
```fortran
RiemannSolver = "HLLD"
killdivb = .true.
prolMethod = "balsara_prol"      # ★ cylindrical 强制（Hydro_init:L229-L233）
```

**为什么强制 Balsara**：cylindrical 几何下，INJECTION_PROL 的 prolongation 不正确（face-var 的几何权重不对）。Balsara 方法考虑了几何。

### Recipe 4.3：Hall MHD（HEDP）

**适用**：激光等离子体 Hall 效应（电子-离子尺度分离）。

parfile：
```fortran
use_Hall = .true.
use_Nernst = .true.              # 通常一起开
use_CrossField = .true.
currFlMode = "fl_harmonic"       # 电流 limiter
```

### Recipe 4.4：Biermann battery（磁场种子）

**适用**：模拟无初始磁场的磁流体（磁场从 0 通过 Biermann 机制产生）。

parfile：
```fortran
use_Biermann = .true.
use_Biermann3T = .true.          # 3T 版本（推荐）
hy_biermannCoef = 1.0            # 正常物理系数
```

**机制**：$\partial B/\partial t \propto \nabla n_e \times \nabla T_e$，温度梯度和密度梯度不平行时产生磁场。

---

## 5. 3T 配置 recipe

### Recipe 5.1：基础 3T（usm3t）

**适用**：激光算例（电子/离子/辐射温度分离）。

```bash
./setup LaserSlab -2d -auto +cylindrical +usm3t +laser +mgd \
    -objdir=cases/LaserSlab_3t
```

parfile：
```fortran
# 3T 相关
hy_3Torder = -1                  # -1 = 同 order（推荐）
addThermalFlux = .false.         # ★ 3T 时自动关（unsplit 热传导与 3T 不兼容）
```

**为什么 3T 关热传导通量**：unsplit 的热传导 operator 假设单一温度。3T 模式下需要用 Diffuse 单元处理电子/离子/辐射的扩散。

### Recipe 5.2：3Torder 单独调

**适用**：默认 3Torder=-1（同 order）在某些算例数值不稳。

parfile：
```fortran
hy_3Torder = 1                   # 3T 变量用 1 阶（更稳但精度低）
order = 3                        # 主变量用 PPM
```

**经验**：3T 强激波算例可能需要把 ion temp 用 1 阶（避免振荡），其他用高阶。

---

## 6. 强激波鲁棒配置 recipe

**适用**：高 Mach 数（>20）、Sedov、激波碰撞、超新星。

```fortran
# 降 CFL
cfl = 0.4

# 用 Hybrid Riemann（激波处 HLL）
RiemannSolver = "Hybrid"

# 激波探测 + 自适应 CFL
shockDetect = .true.
shockLowerCFL = .true.

# 保守限幅器
slopeLimiter = "vanLeer"         # 不用 MC（太锐）
charLimiting = .true.

# positivity preservation
use_hybridOrder = .true.         # 激波附近自动降阶
PosKappa1 = 0.4
PosKappa2 = 0.4

# 辅助内能方程（避免能量消去）
use_auxEintEqn = .true.          # 默认开，确认

# 截断（按算例调）
smlrho = 1.e-10                  # 实验室尺度
smallp = 1.e-10
smalle = 1.e-10
```

---

## 7. 完整可抄配置（最小可运行 Hydro 算例）

```bash
./setup Sedov -2d -auto +cartesian -nxb=8 -nyb=8 \
    -objdir=cases/Sedov_default
```

parfile 关键段：
```fortran
# Hydro 主控
useHydro = .true.
cfl = 0.5                        # 保守起步

# Riemann（默认）
RiemannSolver = "HLLC"

# 限幅器（默认）
slopeLimiter = "vanLeer"
charLimiting = .true.

# 截断
smlrho = 1.e-10
smallp = 1.e-10
smalle = 1.e-10
smallt = 1.e-10

# 重构（默认 2 阶）
order = 2
use_3dFullCTU = .true.
```

**验证**：跑几步看日志：
```bash
grep "Hydro\|CFL\|Riemann" 01-data/<basenm>.log | head -20
```

应该看到每步的 dt、block 数等信息。

---

## 8. 通用检查清单

设 Hydro 参数前确认：

- [ ] **变体对**：`cat cases/<case>/setup_call | grep -E "\\+uhd|\\+usm|\\+split|\\+8wave"`
- [ ] **CFL 合理**：强激波 < 0.5；温和 0.8；保守 0.3
- [ ] **Riemann 匹配物理**：MHD 用 HLLD；纯流体 HLLC；强激波 Hybrid
- [ ] **截断匹配尺度**：实验室 1E-10；天体 1E-30
- [ ] **charLimiting 开**：默认 TRUE，激波附近不要关
- [ ] **3T 模式关 addThermalFlux**：自动关，确认
- [ ] **MHD 用 USM**：cylindrical 用 Balsara prolongation
- [ ] **NGUARD 够**：PPM Upwind 需要 6（默认 4）

---

## 9. 延伸阅读

- **完整参数列表**：`knowledge/params.md`
- **CTU 内部流程**：`knowledge/internals.md`
- **常见错误**：`knowledge/pitfalls.md`
- **变体对比**：`knowledge/overview.md §2`
- **MHD 处理**：`knowledge/overview.md §6`
- **Grid 单元（unk 数组）**：`flash-grid` skill

---

## 10. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：6 类 recipe（变体/CFL/Riemann/MHD/3T/强激波）+ 完整可抄最小配置 + 8 项检查清单 | claude |
