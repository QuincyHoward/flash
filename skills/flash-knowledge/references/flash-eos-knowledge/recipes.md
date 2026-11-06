---
title: Eos 典型配置 — 变体 / 模式 / 3T / ionmix 表
skill: flash-eos
category: recipes
source_anchors:
  - source/physics/Eos/EosMain/Config:L13-L20
  - source/physics/Eos/EosMain/Helmholtz/Config:L5
  - source/physics/Eos/EosMain/multiTemp/Config:L5
  - source/Grid/GridMain/Config:L155-L185
  - bin/setup_shortcuts.txt:L61-L76
manual_ref: "FLASH 4.8 User Guide §13-15"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - eos
  - recipe
  - helmholtz
  - 3t
  - ionmix
---

# Eos 典型配置 recipes

> **TL;DR**：6 类 recipe：变体选择（setup 命令）+ EOS 模式选择（parfile）+ 3T 配置 + ionmix 表加载 + Coulomb 修正 + 性能调优。每个 recipe 标适用场景。

---

## 0. 通用准备

### 0.1 EOS 变体选择

EOS 变体是 **setup 期决定**（编译期），换变体要重新 setup+make。

| 场景 | setup 命令 | 变体 |
|---|---|---|
| 教学 / 测试 | `./setup Sod -auto` | Gamma（默认） |
| 多物质非简并 | `./setup <problem> -auto +eos=Multigamma` | Multigamma |
| HEDP / ICF / 激光 | `./setup <problem> -auto +eos=Helmholtz +laser ...` | Helmholtz |
| 复杂原子（Fe/Au） | `./setup <problem> -auto +eos=Tabulated` + 表文件 | Tabulated |
| 3T 激光 | `./setup <problem> -auto +3t +laser +mgd ...` | multiTemp/Multitype |
| VoF 双流体 | `./setup <problem> -auto +vof ...` | multiFluid |

### 0.2 parfile EOS 关键段

```fortran
# 主控（在顶层）
eosMode = "dens_ie"
eosModeInit = "dens_ie"
smalle = 1.e-10
smallt = 1.e-10
smlrho = 1.e-10
smallx = 1.e-10

# Eos 顶层
eintSwitch = 0.0          # 默认关（用 EINT_VAR 直接值）
gamma = 1.6667            # 仅 Gamma 变体

# Helmholtz 专属
eos_coulombMult = 1.0
eos_tolerance = 1.e-8
eos_maxNewton = 50
eos_forceConstantInput = .false.

# 3T 专属（仅 multiTemp）
eos_combinedTempRule = -10
```

---

## 1. 变体选择 recipe

### Recipe 1.1：Gamma（默认，快速测试）

**适用**：教学、Sod 激波管、简单测试。

```bash
./setup Sod -1d -auto +cartesian \
    -objdir=cases/Sod
```

parfile：
```fortran
gamma = 1.6667           # 单原子理想气体
eosMode = "dens_ie"
```

**为什么用 Gamma**：解析、快、无表。教学和单元测试首选。

### Recipe 1.2：Helmholtz（HEDP 默认）

**适用**：ICF、激光等离子体、白矮星、超新星。

```bash
./setup LaserSlab -2d -auto +cylindrical +laser +mgd +uhd3t +eos=Helmholtz \
    -nxb=16 -nyb=16 \
    -objdir=cases/LaserSlab
```

**为什么 Helmholtz**：电子简并 + Coulomb + 黑体辐射覆盖 14 数量级密度。

**子变体选择**（默认 SpeciesBased）：
- **SpeciesBased**：用 Multispecies 跟踪 mass fractions → 自动算 Abar/Zbar（推荐）
- **Ye**：只跟踪 Ye（电子分数），适合核合成
- **ExternalAbarZbar**：从外部表读 Abar/Zbar

### Recipe 1.3：Tabulated（复杂原子）

**适用**：Fe、Au、CH foam 等部分电离物质；和不透明度共用一张表。

```bash
./setup <problem> -2d -auto +eos=Tabulated
```

加自己的 ionmix 表（在算例 Config 加）：
```
DATAFILES myMaterial.imx
```

parfile：
```fortran
eos_useLogTables = .true.
eos_tabUseGeoSpace = .true.
```

### Recipe 1.4：3T Multitype（生产级激光默认）

**适用**：激光 HEDP 三温算例。

```bash
./setup LaserSlab -2d -auto +cylindrical +usm3t +laser +mgd \
    +eos=Multitype \
    -nxb=16 -nyb=16 \
    -objdir=cases/LaserSlab_3t
```

**为什么 Multitype**：电子用 Helmholtz + Tabulated 电离状态；离子用 Tabulated；辐射用黑体。生产级最准。

**+3t setup shortcut** 自动选 multiTemp（具体子变体看其他 setup 变量，默认 Multitype）。

### Recipe 1.5：Multigamma（多物质非简并）

**适用**：多种气体混合（如 H+He 大气），不简并、不电离。

```bash
./setup <problem> -2d -auto +eos=Multigamma species=H,He
```

每个 species 有自己的 γ（在 Multispecies Config 声明）。

---

## 2. EOS 模式选择 recipe

### Recipe 2.1：dens_ie（默认）

**适用**：大多数算例（Hydro 主循环）。

```fortran
eosMode = "dens_ie"
eosModeInit = "dens_ie"
```

**为什么默认**：Hydro 演化能量（守恒变量），从 (ρ, e) 算 (P, T) 最自然。

### Recipe 2.2：dens_temp（初始化）

**适用**：初始化时直接指定 (ρ, T)。

```fortran
eosModeInit = "dens_temp"     # 仅初始化用
eosMode = "dens_ie"            # 运行时仍用 dens_ie
```

**为什么**：用户在 `Simulation_initBlock` 设 (ρ, T)（直观），Eos 用 dens_temp 算 e, P。运行时回到 dens_ie（Hydro 用能量）。

### Recipe 2.3：dens_pres（Riemann 后）

**适用**：调试 Riemann solver 时（已知压力）；导数测试。

```fortran
eosMode = "dens_pres"
```

**注意**：不推荐生产用。Helmholtz 在 dens_pres 模式会修改输入 P（保持自洽），可能掩盖物理 bug。

### Recipe 2.4：3T 模式（dens_ie_recal_gather）

**适用**：3T 算例（`+3t`）。

```fortran
eosMode = "dens_ie_recal_gather"
```

**为什么 recal_gather**：完全重算所有 component，最贵但最准。AMR refine 后必须用这个（保证新 block 自洽）。

`+3t` setup 自动设此模式（`source/Grid/GridMain/Config:L155-L158`）。

### Recipe 2.5：3T 平衡模式（dens_ie_equi）

**适用**：假设 3 个 component 已平衡的诊断调用。

```fortran
# 不是 parfile 设的，是某次调用 Eos_wrapped 时传入的 mode
call Eos_wrapped(MODE_DENS_EI_EQUI, blkLimits, blockID, CENTER)
```

**注意**：Eos 不做平衡（Heatexchange 做）。这模式只是假设平衡。

---

## 3. 3T 配置 recipe

### Recipe 3.1：基础 3T（+3t）

```bash
./setup <problem> -2d -auto +cartesian +3t +laser \
    -objdir=cases/<problem>_3t
```

`+3t` 自动：
- 选 multiTemp 变体（默认 Multitype）
- 设 `eosMode = "dens_ie_recal_gather"`
- REQUEST Heatexchange 单元
- 启用 3T UNK 变量（TEION/TELE/TERAD/EION/EELE/ERAD/...）

### Recipe 3.2：完整 HEDP 3T 激光

**典型 LaserSlab 配置**：

```bash
./setup LaserSlab -2d -auto +cylindrical \
    +laser +mgd +uhd3t \
    species=cham,targ \
    mgd_meshgroups=6 \
    -nxb=16 -nyb=16 \
    -objdir=cases/LaserSlab
```

parfile 关键段：
```fortran
# EOS 主控
eosMode = "dens_ie_recal_gather"
smalle = 1.e-10
smallt = 1.e-10
smlrho = 1.e-10

# Helmholtz
eos_coulombMult = 1.0
eos_tolerance = 1.e-8

# 3T
gammaIon = 1.6667      # 离子 γ
gammaEle = 1.6667      # 电子 γ
gammaRad = 1.3333      # 辐射 γ（4/3）

# Heatexchange
useHeatexchange = .true.
# Heatexchange 单元变体由 setup 选（默认 Constant）
```

### Recipe 3.3：调试 3T 不平衡

查看 T_ion / T_ele / T_rad 比值（诊断变量）：

```fortran
# 这些是 Eos 写入的诊断变量（不是参数）
TITE = T_ion / T_ele       # 接近 1 = 平衡；>> 1 = 离子比电子热
PIPE = P_ion / P_ele
TRTE = T_rad / T_ele
PRPE = P_rad / P_ele
```

在 plotfile 用 Visit 看。如果 TITE 在某些区域 >> 1，说明 Heatexchange 时间尺度不够（增大 dt 或换更强的耦合模型）。

---

## 4. ionmix 表加载 recipe

### Recipe 4.1：加自己的 ionmix 表

1. 把 `.imx` 文件放到算例目录或 `source/physics/Eos/EosMain/Tabulated/`

2. 在算例 Config 文件加：
   ```
   DATAFILES myMaterial.imx
   ```

3. setup 自动把表文件拷到 objdir

4. parfile 加（按算例需求）：
   ```fortran
   eos_useLogTables = .true.
   eos_tabUseGeoSpace = .true.
   ```

5. 用 `+eos=Tabulated` setup

### Recipe 4.2：HDF5 表（OPACPLOT）

需要 HDF5 库（本机已配）：
```bash
./setup <problem> -2d -auto +eos=Tabulated +hdf5typeio
```

parfile 同上。

### Recipe 4.3：表的范围检查

ionmix 表有 (ρ, T) 范围限制。算例物理量超范围 → 插值外推（不可靠）。

**诊断**：跑几步后看日志 `out of table` 警告：

```bash
grep "out of table\|outside" 01-data/<basenm>.log | head -20
```

**修复**：
- 用范围更大的表
- 调整算例参数避免超范围
- 加 floor values（smalle、smallt）让数值不超出

---

## 5. Coulomb 修正 recipe

### Recipe 5.1：默认 Coulomb 修正

```fortran
eos_coulombMult = 1.0       # 默认，正常物理
eos_coulombAbort = .true.   # Coulomb 负压 abort（默认）
```

**为什么默认开**：HEDP 算例 Coulomb 修正在高密度下显著（影响压力 ~10%）。

### Recipe 5.2：关闭 Coulomb（避免负压）

某些算例 Coulomb 修正导致负压（密度极低或温度极高时）：

```fortran
eos_coulombMult = 0.0       # 关闭
# 或
eos_coulombMult = 0.5       # 部分修正
eos_coulombAbort = .false.  # 负压时警告不 abort（危险）
```

### Recipe 5.3：forceConstantInput（关闭输入修改）

Helmholtz 默认会修改 dens_ie 的输入 e（让 (ρ,T) 自洽）。某些场景要关闭：

```fortran
eos_forceConstantInput = .true.
```

**何时用**：调试时保持输入完全不变；某些物理一致性问题需要固定 e。

---

## 6. 性能调优 recipe

### Recipe 6.1：减少 Eos 调用次数

Eos_wrapped 是热点（3T Multitype 单次 ~30 ms）。优化：

1. **`MODE_EOS_NOP`**：调用方知道 Eos 刚调过，用 NOP 跳过 kernel
2. **`MODE_EOS_WRAPPERONLY`**：只 getData + putData（不调 kernel），用于数据搬运
3. **`hy_eosModeGc`**：guard cell 用 dens_temp（不迭代，比 dens_ie 快）

### Recipe 6.2：OpenMP 并行

```fortran
threadEosWithinBlock = .true.
```

block 内 (k, j) 循环 OpenMP 并行。NDIM > 1 时有效。

setup 加 `+threadWithinBlock`：
```bash
./setup <problem> -3d -auto +threadWithinBlock ...
```

### Recipe 6.3：Helmholtz 缓存

第一次启动慢（读 helm_table.dat 7.7 MB ASCII）。后续启动快（读 helm_table.bdat）。

**注意**：换机器后删 .bdat（endian 可能不同）。

---

## 7. 完整可抄配置（最小可运行 Helmholtz 算例）

```bash
./setup Sedov -2d -auto +cartesian +eos=Helmholtz \
    -nxb=8 -nyb=8 \
    -objdir=cases/Sedov_helm
```

parfile 关键段：
```fortran
# 主控
eosMode = "dens_ie"
eosModeInit = "dens_ie"
smalle = 1.e-10
smallt = 1.e-10
smlrho = 1.e-10

# Helmholtz
eos_coulombMult = 1.0
eos_tolerance = 1.e-8
eos_maxNewton = 50
eos_forceConstantInput = .false.

# Eos 顶层
eintSwitch = 0.0
```

**验证**：
```bash
# 跑几步看日志
grep "Eos_init\|Helmholtz\|table" 01-data/<basenm>.log | head -20
```

应该看到：
- `Reading helm_table.dat` 或 `Reading helm_table.bdat`
- `eos_type = EOS_HLM`
- 表加载成功

---

## 8. 通用检查清单

- [ ] **变体对**：`cat cases/<case>/setup_call | grep -E "\\+eos|\\+3t"`
- [ ] **eosMode 合法**：parfile 写的字符串能映射到 MODE_DENS_*
- [ ] **截断匹配尺度**：实验室 1E-10；天体 1E-30
- [ ] **Helmholtz 表就位**：`helm_table.dat` 在 objdir 或 source 路径
- [ ] **3T 算例用 recal_gather**：`eosMode = "dens_ie_recal_gather"`
- [ ] **Coulomb 不导致负压**：低密度算例考虑 `eos_coulombMult = 0.0`
- [ ] **gamma 合理**：单原子 5/3；双原子 7/5；辐射 4/3
- [ ] **gammaRad = 4/3**（3T 黑体辐射）
- [ ] **eintSwitch 默认 0**（Hydro 用辅助内能方程）

---

## 9. 延伸阅读

- **Eos 总览**：`knowledge/overview.md`
- **完整参数列表**：`knowledge/params.md`
- **Eos_wrapped 流程**：`knowledge/internals.md §2`
- **常见错误**：`knowledge/pitfalls.md`
- **Helmholtz 表机制**：`knowledge/overview.md §5`
- **3T 设计**：`knowledge/overview.md §4`
- **Heatexchange（3T 平衡）**：`flash-sourceterms`（Phase 2 后）

---

## 10. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：6 类 recipe（变体/模式/3T/ionmix/Coulomb/性能）+ 完整可抄最小配置 + 9 项检查清单 | claude |
