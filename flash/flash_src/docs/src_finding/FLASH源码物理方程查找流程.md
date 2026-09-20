# FLASH4.8 源码物理方程查找流程

> 本文档记录了在 FLASH4.8 大型 Fortran 源码库中，根据物理方程定位对应代码的系统化方法。
> 
> 项目路径：`FLASH4.8/`

## 目录

1. [概述](#1-概述)
2. [FLASH 物理模块架构](#2-flash-物理模块架构)
3. [六步查找工作流](#3-六步查找工作流)
4. [四大方程的源码定位](#4-四大方程的源码定位)
5. [搜索技巧](#5-搜索技巧)
6. [3T 算子分裂总览](#6-3t-算子分裂总览)
7. [附录：关键变量与常量](#7-附录关键变量与常量)

---

## 1. 概述

FLASH4.8 是一个大型自适应网格细化（AMR）天体物理与激光等离子体模拟框架，包含 **6800+ 个 Fortran 90 源文件**。查找特定物理方程的源代码时，高效的方法不是挨个阅读文件（这会撑爆上下文），而是：

1. **先看目录结构**：理解 FLASH 的模块划分
2. **再搜文档**：在 `docs/flash4_ug_4p8.md` 中定位相关章节
3. **搜索关键词**：搜索源码中的物理常数、变量名和子程序名
4. **精确提取**：只读关键文件的关键行

### 约定

- 所有路径相对于 `FLASH4.8/source/` 目录
- 文档引用：`docs/flash4_ug_4p8.md`
- 源码文件：`source/physics/` 下的 `.F90` 文件

---

## 2. FLASH 物理模块架构

```
FLASH4.8/
├── docs/
│   ├── flash4_ug_4p8.md      ← 使用说明书（方程定义）
│   └── flash4_ug_4p8.pdf
├── source/                    ← 源码目录
│   └── physics/               ← 物理模块
│       ├── Hydro/             ← 流体动力学
│       │   └── HydroMain/
│       │       ├── unsplit/              ← 非分裂格式（主流）
│       │       │   ├── Hydro_Unsplit/    ← 纯流体（无磁场）
│       │       │   ├── MHD_StaggeredMesh/← MHD
│       │       │   ├── multiFluid/       ← 多流体
│       │       │   ├── multiTemp/        ← 多温度
│       │       │   └── threadWithinBlock/← 线程并行
│       │       └── split/    ← 分裂格式
│       ├── RadTrans/         ← 辐射输运
│       │   └── RadTransMain/
│       │       ├── MGD/      ← 多群扩散
│       │       │   ├── ExpRelax/
│       │       │   └── Unified/
│       │       └── NeutrinoLeakage/  ← 中微子泄漏
│       ├── Diffuse/          ← 扩散方程求解器
│       │   └── DiffuseMain/
│       ├── sourceTerms/      ← 物理源项
│       │   ├── EnergyDeposition/  ← 激光能量沉积
│       │   │   └── EnergyDepositionMain/Laser/
│       │   └── Heatexchange/     ← 离子-电子热交换
│       └── materialProperties/   ← 材料物性
│           ├── Conductivity/     ← 热导率
│           │   └── ConductivityMain/
│           │       ├── Spitzer/  ← Spitzer模型
│           │       ├── LeeMore/  ← Lee-More模型
│           │       ├── Constant/ ← 常数
│           │       └── EppHain/  ← Epperlein-Haines
│           ├── Opacity/          ← 不透明度
│           └── Eos/              ← 状态方程
└── setup*     ← 编译配置脚本
```

---

## 3. 六步查找工作流

### 第1步：理解方程 → 映射到 FLASH 单元

| 方程 | FLASH单元 | 文档章节 |
|------|-----------|---------|
| **质量/动量/能量守恒** | `Hydro` | 第15章 |
| **激光能量沉积（Q_las）** | `EnergyDeposition`（`sourceTerms/`） | 第14章 |
| **电子热传导（Spitzer）** | `Conductivity` + `Diffuse` | 第19+23章 |
| **多群辐射扩散** | `RadTrans` + `Opacity` + `Diffuse` | 第25章 |
| **离子-电子热交换** | `Heatexchange` | 第18章 |
| **状态方程** | `Eos` | 第17章 |

### 第2步：扫描目录树 → 确定候选文件

用 `find` 命令快速了解目标模块的文件结构：

```bash
find source/physics/Hydro/HydroMain/unsplit -name "*.F90" | head -30
```

注意文件名前缀规律：
- `hy_` = Hydro 单元
- `ed_` = Energy Deposition 单元
- `rt_` = RadTrans 单元
- `Cond` = Conductivity 单元
- `Diffuse_` = Diffuse 单元

### 第3步：读文件头 → 找对应子程序

每个 `.F90` 文件前 40-60 行是注解头，包含：
- `!! NAME`：子程序名
- `!! DESCRIPTION`：功能描述 + 引用文献

### 第4步：关键词搜索 → 定位方程实现行

用 `grep` 搜索物理常数和方程关键词：

```bash
# Spitzer热导率
grep -n "ck\s*="  source/physics/materialProperties/Conductivity/.../Conductivity.F90

# 辐射扩散系数
grep -n "rt_speedlt3\s*/\s*max" source/physics/RadTrans/.../RadTrans.F90

# 辐射吸收
grep -n "change = change + urad \* C" source/physics/RadTrans/.../RadTrans.F90

# 质量通量
grep -n "F01DENS_FLUX" source/physics/Hydro/HydroMain/unsplit/hy_uhd_prim2flx.F90
```

### 第5步：提取方程代码 → 只读关键行

找到行号后用 `Read` 读该行 ±10 行上下文，提取方程实现。

### 第6步：追踪耦合 → 跨单元协作

FLASH 中一个物理效应常跨多个单元。用 `use XXX_interface` 追踪：
- Radiation → `use Opacity_interface`（辐射调不透明度）
- Radiation → `use Diffuse_interface`（辐射调用扩散求解）
- Diffuse → `use Conductivity_interface`（热传导调热导率）

---

## 4. 四大方程的源码定位

### 4.1 质量、动量、能量守恒（Euler方程）

**文档方程**（第15章）：
```text
连续性: ∂ρ/∂t + ∇·(ρv) = 0
动量:   ∂(ρv)/∂t + ∇·(ρvv + P·I) = 0
总能:   ∂(ρE)/∂t + ∇·[(ρE + P)v] = 0
```

**源码定位**：

| 功能 | 文件 | 实现位置 |
|------|------|----------|
| 原始变量→通量 | `source/physics/Hydro/HydroMain/unsplit/hy_uhd_prim2flx.F90` | 行53-121 |
| 守恒变量更新 | `source/physics/Hydro/HydroMain/unsplit/hy_uhd_unsplitUpdate.F90` | 行1364-1419 |
| 主驱动 | `source/physics/Hydro/HydroMain/unsplit/Hydro_Unsplit/hy_uhd_unsplit.F90` | 整体流程 |

**核心实现（hy_uhd_prim2flx.F90，X方向）**：
```fortran
! 无磁场分支 #ifdef FLASH_UHD_HYDRO
F(F01DENS_FLUX) = dens*velx                 ! 质量通量: ρ·u
F(F02XMOM_FLUX) = (dens*velx)*velx + pres   ! x动量通量: ρ·u²+P
F(F03YMOM_FLUX) = (dens*velx)*vely           ! y动量通量: ρ·u·v
F(F04ZMOM_FLUX) = (dens*velx)*velz           ! z动量通量: ρ·u·w
F(F05ENER_FLUX) = (ener + pres)*velx         ! 能量通量: (E+P)·u
```

### 4.2 激光能量沉积

**文档方程**（第14章，式14.7b）：
```text
∂(ρ·e_ele)/∂t |_laser = Q_las
```

**源码定位**：

| 功能 | 文件 | 说明 |
|------|------|------|
| 主驱动（几何光学追迹） | `source/physics/sourceTerms/EnergyDeposition/EnergyDepositionMain/Laser/EnergyDeposition.F90` | 创建光线→追迹→更新等离子体 |
| 光束功率计算 | `.../LaserBeams/ed_computeBeamPower.F90` | 时间脉冲插值 |

**核心流程**：`ed_createRays` → `ed_traceRays` → `ed_updatePlasma(3T)` → 写入 `ed_depoVar`

### 4.3 电子热传导（限流Spitzer）

**文档方程**（第14章，式14.9-10）：
```text
q_ele = -κ_ele·∇T_ele
∂(ρ·e_ele)/∂t |_cond = ∇·(κ_ele·∇T_ele)
```

**源码定位（两单元协作）**：

| 层次 | 模块 | 文件 | 内容 |
|------|------|------|------|
| **热导率** | Conductivity | `source/physics/materialProperties/Conductivity/ConductivityMain/Spitzer/Conductivity.F90`（行87） | κ = 9.2e-7·T^2.5 |
| **扩散通量** | Diffuse | `source/physics/Diffuse/DiffuseFluxBased/Diffuse_therm.F90`（行40-49） | F = -κ·∇T |
| **限流器** | Diffuse | `source/physics/Diffuse/DiffuseMain/Diffuse_fluxLimiter.F90` | λ∈(0, 1/3] |

**Spitzer 实现**：
```fortran
real, parameter :: ck = 9.2e-7     ! Spitzer常数
real, parameter :: cexp = 2.5       ! 温度指数
condLoc = ck * xtemp**cexp          ! κ = 9.2e-7·T^2.5
```

### 4.4 多群辐射扩散

**文档方程**（第25章）：
```text
第g群:
∂u_g/∂t = ∇·(D_g·∇u_g) + Q_emis,g - Q_abs,g

D_g = c/(3κ_tr,g)            (扩散系数)
Q_abs,g = c·κ_a,g·u_g        (吸收)
Q_emis,g = κ_e,g·c·aT^4·ΔP  (发射, Planck积分)
```

**源码定位**：

| 功能 | 文件 | 行号 |
|------|------|------|
| **MGD主驱动（逐群扩散）** | `source/physics/RadTrans/RadTransMain/MGD/RadTrans.F90` | 行250-509 |
| 扩散系数 D_g | 同上 | 行312: `COND_VAR = rt_speedlt3 / max(TINY, trans_opac)` |
| 吸收项 c·κ_a | 同上 | 行319: `ABSR_VAR = C * absorb_opac` |
| 发射项（Planck） | 同上 | 行322-333 |
| 吸收后处理 | 同上 | 行490: `change = change + urad * C * absorb_opac` |
| 辐射限流器 | `.../MGD/RadTrans_computeFluxLimiter.F90` | 委托 Diffuse |
| 不透明度 | `source/physics/materialProperties/Opacity/OpacityMain/.../Opacity.F90` | 返回 κ_a, κ_e, κ_tr |
| Planck积分函数 | `source/physics/RadTrans/RadTransMain/RadTrans_planckInt.F90` | / |

**核心实现（MGD/RadTrans.F90）**：
```fortran
! 逐群循环:
do gloc = 1, NGROUPS
  ! 1. 能量密度转换: u_g = e_g·ρ
  ! 2. 不透明度查询: Opacity() → absorb_opac, emit_opac, trans_opac
  ! 3. 扩散系数:     D_g = c/(3·κ_tr)
  ! 4. 吸收项:       ABSR_VAR = c·κ_a
  ! 5. 发射项:       emiss = κ_e·c·a·T⁴·[P(x_g)-P(x_{g+1})]
  ! 6. 通量限流:     call Diffuse_fluxLimiter(COND_VAR, ...)
  ! 7. 隐式扩散求解: call Diffuse_solveScalar(gvar, COND_VAR, DFCF_VAR, ...)
  ! 8. 吸收后处理:   change += urad · c · κ_a
end do
```

---

## 5. 搜索技巧

### grep关键词速查

| 要找的物理量 | grep 搜索词 |
|-------------|------------|
| Spitzer 热导率常数 | `ck = `、`9.2e-7` |
| 辐射扩散系数 | `rt_speedlt3 / max` |
| 辐射吸收项 | `urad * C * absorb_opac` |
| 辐射发射项（Planck） | `RadTrans_planckInt` |
| 通用限流器 | `FLLM_VAR`、`rt_mgdFlCoef` |
| 质量通量（Hydro） | `F01DENS_FLUX` |
| 动量通量（Hydro） | `F02XMOM_FLUX`、`F03YMOM_FLUX` |
| 能量通量（Hydro） | `F05ENER_FLUX` |
| 能量沉积 | `ed_depoVar`、`Qlas` |
| 限流模式 | `rt_mgdFlMode`、`cond_useConductivity` |

---

## 6. 3T 算子分裂总览

3T（三温度：离子+电子+辐射）的算子分裂流程：

```
┌───────────────────────────────────────┐
│  3T 完整算子分裂 (第14章)              │
│                                        │
│  1. Hydro 单元                         │
│     守恒律 + 压力做功                  │
│     → hy_uhd_unsplit.F90              │
│                                        │
│  2. Heatexchange 单元                  │
│     离子-电子热交换                    │
│     → sourceTerms/Heatexchange/        │
│                                        │
│  3. Diffuse 单元                       │
│     电子热传导 (限流Spitzer)           │
│     → Diffuse_therm + Conductivity     │
│                                        │
│  4. RadTrans 单元                      │
│     多群辐射扩散                       │
│     → MGD/RadTrans + Opacity           │
│                                        │
│  5. EnergyDeposition 单元              │
│     激光加热 Qlas                      │
│     → Laser/EnergyDeposition           │
└───────────────────────────────────────┘
```

---

## 7. 附录：关键变量与常量

| 变量/常量 | 值 | 所在文件 | 含义 |
|-----------|-----|---------|------|
| `ck` | 9.2e-7 | `Conductivity.F90` 行55 | Spitzer热导率常数 |
| `cexp` | 2.5 | `Conductivity.F90` 行56 | Spitzer温度指数 |
| `rt_speedlt` | c (光速) | `rt_data.F90` | 真空中光速 |
| `rt_speedlt3` | c/3 | `rt_data.F90` | c/3 |
| `rt_boltz` | k_B | `RadTrans_data.F90` | 玻尔兹曼常数 |
| `rt_radconst` | a (辐射常数) | `RadTrans_data.F90` | 辐射常数 a=4σ/c |
| `rt_mgdFlCoef` | 用户设定 | `rt_data.F90` | 辐射限流系数 |
| `rt_mgdNumGroups` | 用户设定 | `rt_data.F90` | 辐射能量群数 |
| `TEMP_VAR/TELE_VAR/TION_VAR/TRAD_VAR` | — | `Flash.h` | 各温度变量索引 |
| `DENS_VAR` | — | `Flash.h` | 密度变量索引 |
| `ERAD_VAR` | — | `Flash.h` | 总辐射能变量索引 |
| `MGDC_VAR` | — | `Flash.h` | 辐射能量变化量索引 |
| `COND_VAR` | — | `Flash.h` | 扩散系数变量索引 |
| `ABSR_VAR` | — | `Flash.h` | 吸收率变量索引 |
| `EMIS_VAR` | — | `Flash.h` | 发射率变量索引 |
| `FLLM_VAR` | — | `Flash.h` | 通量限流变量索引 |

---

> **更新记录**：2026-06-23 初版建立
