---
title: Eos 常见踩坑 — Newton / out of table / Helmholtz 修改输入 / 3T 不自洽
skill: flash-eos
category: pitfalls
source_anchors:
  - source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_helmholtz.F90:L215-L232
  - source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_initHelmholtz.F90:L222
  - source/physics/Eos/EosMain/multiTemp/Config:L37
  - source/Grid/GridMain/Config:L155-L185
manual_ref: "FLASH 4.8 User Guide §13-15"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - eos
  - pitfall
  - newton
  - helmholtz
  - 3t
---

# Eos 常见踩坑

> **TL;DR**：分 4 大类共 18 条踩坑：**A 启动期**（变体冲突、表加载）+ **B 运行期数值**（Newton 不收敛、out of table、负压）+ **C 模式 / 修改输入陷阱**（Helmholtz 修改输入、dens_ie 副作用）+ **D 3T 专属**（不自洽、Heatexchange 时步）。按 L-012 诊断类问题先引导贴现场。

---

## 0. 诊断引导（按 L-012）

遇到 EOS abort 先贴以下信息：

```bash
# 1. abort 信息原文
grep -B 2 -A 5 "abort\|Newton\|out of table\|negative" 01-data/<basenm>.log | head -40

# 2. Eos_init 打印的参数（确认 parfile 生效）
grep "Eos_init\|eos_type\|Helmholtz\|table" 01-data/<basenm>.log | head -30

# 3. setup 命令（验证变体选择）
cat cases/<case>/setup_call | grep -E "\\+eos|\\+3t|\\+usm"

# 4. parfile EOS 段（贴出来）
grep -A 1 "eosMode\|smalle\|smallt\|smlrho\|eos_" cases/<case>/flash.par

# 5. 物理量范围（看是否超表）
grep "max dens\|min dens\|max temp\|min temp" 01-data/<basenm>.log | tail -10
```

**贴完后能给出针对性诊断。** 下面是常见原因，作为参考。

---

## A. 启动期踩坑

### A.1 `helm_table.dat not found` abort

**症状**：启动时 Eos_init abort，提示找不到表。

**原因**：Helmholtz 表路径错。

**修复**：
1. 确认 `source/physics/Eos/EosMain/Helmholtz/helm_table.dat` 存在（默认 7.7 MB）
2. setup 没把表拷到 objdir → 重新 setup（确认 setup 命令含 `+eos=Helmholtz`）
3. 检查 objdir 是否有 helm_table.dat：`ls cases/<case>/helm_table.dat`

### A.2 `helm_table.bdat corrupted` 或读出来数据不对

**症状**：Helmholtz 启动时报错；或者算例结果明显错（如压力全 0）。

**原因**：`.bdat` 是 Fortran binary，跨架构（如从 x86 复制到 ARM）会读错。

**修复**：删 `.bdat`，重新读 `.dat`：

```bash
rm cases/<case>/helm_table.bdat
# 重新跑 flash4，会重新生成 .bdat
```

源码注释（`eos_initHelmholtz.F90:L222`）。

### A.3 `eos_type mismatch` 或选错变体

**症状**：跑出来结果完全不对（如电子简并算错）。

**原因**：setup 期 eos 变体选择错。

**诊断**：
```bash
cat cases/<case>/setup_call | grep -E "\\+eos|\\+3t|\\+usm"
```

**修复**：
- 想要 Helmholtz → setup 加 `+eos=Helmholtz`
- 想要 3T → `+3t` 或 `+usm3t`
- 默认是 Gamma（理想气体）

### A.4 `+3t` 但没 `+eos=Multitype`（其实不用）

**症状**：用户以为 3T 必须显式写 `+eos=Multitype`。

**原因**：`+3t` 自动选 multiTemp，默认子变体 Multitype（`multiTemp/Config:L5` 的 CHILDORDER）。

**修复**：不需要单独写 `+eos=Multitype`。`+3t` 已经够了。

### A.5 `HDF5 table required but HDF5 not compiled` abort

**症状**：用 `+eos=Tabulated` + HDF5 表启动 abort。

**原因**：HDF5 库没编译进 FLASH。

**修复**：setup 加 `+hdf5typeio`（本机已配 HDF5 库）：
```bash
./setup <problem> -2d -auto +eos=Tabulated +hdf5typeio
```

---

## B. 运行期数值踩坑

### B.1 `Helmholtz Newton did not converge` abort

**症状**：跑几步后 abort，提示 Newton-Raphson 不收敛。

**触发代码**（`source/physics/Eos/EosMain/Helmholtz/SpeciesBased/eos_helmholtz.F90:L215-L218`）：

```fortran
if (.not. converged .and. iter >= eos_maxNewton) then
    call Driver_abortFlash("Helmholtz Newton did not converge")
end if
```

**可能原因**（按概率）：

1. **初始 T 猜测差**：dens_ie 模式 Newton 需要 T 初值。如果 TEMP_VAR 和实际 T 差几个数量级，可能不收敛。
   - 修复：检查 Simulation_initBlock 的初始 T 是否合理

2. **密度/温度超表范围**：Helmholtz 表 ρ ∈ [10⁻¹⁰, 10¹¹] g/cm³，T ∈ [10⁴, 10¹¹] K。超范围外推不可靠。
   - 修复：调 smalle / smallt 让 floor 在表范围内

3. **smalle 太低**：内能极小值导致 Newton 找不到合理 T。
   - 修复：`smalle = 1.e-10`（默认）或更高

4. **Coulomb 修正导致负压**：高密度低温度 Coulomb 项可能让 P 算负。
   - 修复：`eos_coulombMult = 0.0` 关闭修正，或 `eos_coulombAbort = .false.`（警告不 abort）

5. **`eos_maxNewton` 太小**：默认 50 通常够，复杂算例可加大。
   - 修复：`eos_maxNewton = 100`

### B.2 `out of table` 警告

**症状**：日志反复警告 `out of table` 或 `extrapolating outside table`。

**原因**：物理量超出 Helmholtz 或 ionmix 表的 (ρ, T) 范围。

**诊断**：
```bash
grep "out of table\|outside" 01-data/<basenm>.log | wc -l
# 触发次数 / 步 说明问题严重程度
```

**修复**：
- 调整算例参数（如降低最大密度）
- 加 floor values：`smalle = 1.e-10`、`smallt = 1.e-10`、`smlrho = 1.e-10`
- 用范围更大的表

### B.3 出现负压力或负密度

**症状**：plotfile 显示某些 cell PRES < 0 或 DENS < 0。

**可能原因**：

1. **Coulomb 修正**（Helmholtz）：高密度低温度 Coulomb 项可能让 P 算负
   - 修复：`eos_coulombMult = 0.0` 或 `eos_coulombAbort = .false.`

2. **截断太低**：物理量低于 floor 后还在数值不稳定区
   - 修复：提高 smalle / smlrho

3. **Newton 不收敛中间态**：Newton 迭代过程中可能临时出负
   - 修复：同 B.1

4. **`eos_forceConstantInput = .false.` + 物理不一致**：默认行为 Helmholtz 修改输入让自洽。如果输入本身错（如 e < 0），Helmholtz 改了也可能负
   - 修复：检查上游（Hydro / sourceTerms）为什么给 Eos 错误输入

### B.4 `gamma = 0` 或 `gamma < 1` abort

**症状**：Eos 算 GAMC_VAR（声速 γ）出 0 或负。

**原因**：
1. Multispecies 没正确配置（Abar/Zbar 算错）
2. Helmholtz 表外推到极端区域
3. 用户设了不合理 `gamma` 参数（如 0.5）

**修复**：
- 检查 `gamma` 参数（Gamma 变体）
- 检查 Multispecies Config 的 species 声明
- 看 plotfile 的 Abar/Zbar 是否合理

### B.5 算例运行很慢（Eos 占用 80%+ CPU）

**症状**：性能分析显示 Eos_wrapped 占主要时间。

**可能原因**：
1. 3T Multitype（最贵）
2. 重复调用 Eos（每步 7+ 次）
3. Tabulated 表大（per-species 查询）

**修复**（按优先级）：
1. **用 MODE_EOS_NOP 跳过冗余调用**：某些单元知道 Eos 刚调过，用 NOP
2. **guard cell 用 dens_temp**：`hy_eosModeGc = "dens_temp"`（不迭代）
3. **OpenMP 并行**：`threadEosWithinBlock = .true.`
4. **减少 3T 模式重算**：用 `dens_ie_gather` 替代 `dens_ie_recal_gather`（次次重算太贵）

---

## C. 模式 / 修改输入陷阱

### C.1 Helmholtz 修改 dens_ie 输入 e（重要）

**触发代码**（`eos_helmholtz.F90:L228-L232`）：

```fortran
! For Helmholtz, when operating in MODE_DENS_EI, the INPUT energy is updated.
! Similarly, when operating in MODE_DENS_PRES, the INPUT pressure is updated.
! Physicists need to be aware of this.
! This behavior can be turned off by setting the runtime parameter eos_forceConstantInput.
```

**症状**：用户调试时发现 `EINT_VAR` 在 Eos 调用后变了，怀疑 bug。

**机制**：Helmholtz 在 dens_ie 模式：
1. Newton-Raphson 找 T 让 e(T) = e_input
2. 但 Newton 收敛后，重算 e(T_output) 可能和 e_input 略有不同
3. **默认用重算值替换输入**（保持热力学自洽）

**关闭**：`eos_forceConstantInput = .true.`

**为什么默认行为**：物理一致性 > 输入保留。如果用户设的 (ρ, e) 不在 EOS 表面（即没有 T 同时满足 (ρ, T, e)），Helmholtz 修改 e 让它在表面上。

### C.2 dens_temp 模式总是直接（不迭代）

**症状**：用户期望 dens_temp 和 dens_ie 性能相近，实际 dens_temp 快很多。

**原因**：Helmholtz 表是 (ρ, T) 索引的。dens_temp 直接表查询；dens_ie 要 Newton 迭代找 T。

**应用**：guard cell 填充可以用 dens_temp（快），主循环用 dens_ie（准）：

```fortran
hy_eosModeGc = "dens_temp"      # guard cell 用（快）
eosMode = "dens_ie"              # 主循环用（准）
```

### C.3 EOS_TEMP 在 3T 模式的含义不明

**症状**：3T 算例看 plotfile，`TEMP_VAR` 是什么温度？

**原因**：`eos_combinedTempRule`（默认 -10）决定：

| 值 | TEMP_VAR 含义 |
|---|---|
| -10（默认） | 未定义（可能是垃圾） |
| 0 | 平衡 T（贵，假设平衡） |
| 1 | T_ion |
| 2 | T_ele |
| 3 | T_rad |

**修复**：明确设：
```fortran
eos_combinedTempRule = 2     # TEMP_VAR 表示 T_ele
```

### C.4 用 dens_ie_equi 假设有平衡

**症状**：用户用 `eosMode = "dens_ie_equi"` 期望 Eos 做平衡。

**原因**：`_EQUI` 模式**假设** 3 个 component 已平衡，不做平衡。

**修复**：平衡由 **Heatexchange** 单元做（独立 sourceTerm）。`_EQUI` 只在诊断或已知平衡的初始化用。

### C.5 eintSwitch = 0 但 Hydro 还是消去误差

**症状**：高流速算例即使 `eintSwitch = 0`（用 EINT_VAR 直接值）还是数值不稳。

**原因**：Hydro 单元也可能用 `ENER_VAR - EKIN` 算内能。检查 Hydro 配置：

```fortran
# Hydro 单元
use_auxEintEqn = .true.       # 默认 TRUE，确认没关
```

如果 `use_auxEintEqn = .false.`，Hydro 不解辅助内能方程，只能用减法（容易消去误差）。

---

## D. 3T 专属踩坑

### D.1 3T 不自洽（TELE >> TEION 但 Heatexchange 不工作）

**症状**：plotfile 显示 T_ele 远大于 T_ion，Heatexchange 没能让它们平衡。

**可能原因**：

1. **`useHeatexchange = .false.`**：Heatexchange 关了
2. **Heatexchange 系数太小**：算例物理时间太短，平衡来不及
3. **Heatexchange_computeDt 限制 dt 太小**：dt 被耦合时间尺度限制

**诊断**：
```bash
grep "Heatexchange\|hx_dt\|useHeatexchange" 01-data/<basenm>.log | head -10
```

**修复**：
- 确认 `useHeatexchange = .true.`
- 检查 Heatexchange 变体（Constant / ConstCoulomb / Spitzer / LeeMore / Immediate）
- 用 Immediate 变体强制瞬间平衡（调试用）

### D.2 gammaRad 不是 4/3

**症状**：3T 算例辐射压力算错。

**原因**：用户改了 `gammaRad`：

```fortran
gammaRad = 1.6667      # ✗ 错（应为 4/3）
```

**修复**：辐射 γ 必须是 4/3（黑体光子气体推导）：

```fortran
gammaRad = 1.3333      # ✓ 正确（4/3）
```

### D.3 AMR refine 后 3T 不守恒

**症状**：AMR 重细化后总能突然变化。

**原因**：用了 `_GATHER` 模式（廉价）而非 `_RECAL_GATHER`（重算）。

**修复**：
```fortran
eosMode = "dens_ie_recal_gather"
```

`+3t` 默认就是这个，但如果用户改成 `_GATHER` 会出问题。

### D.4 T_ion 和 T_ele 永远不平衡（时间尺度差异）

**症状**：HEDP 短脉冲算例（fs-ps 时间尺度）T_ele 和 T_ion 差几个数量级，正常。

**原因**：电子-离子耦合时间尺度 ~ps，比模拟时间（fs）长。

**修复**：物理上正常。如果想强制平衡：
- 拉长模拟时间（让 Heatexchange 工作）
- 用 `Immediate` Heatexchange 变体（瞬间平衡，非物理）

---

## E. 概念错误踩坑

### E.1 以为 `eosMode` 在 Eos Config

**症状**：用户在 `source/physics/Eos/` 找 `eosMode` 声明，找不到。

**原因**：`eosMode` 在 **Grid 单元 Config**（`source/Grid/GridMain/Config:L155`），因为 Grid 填 guard cell 也要用。

**修复**：知道在哪找就行。parfile 写 `eosMode = "..."` 即可。

### E.2 以为 EOS 自己做 3T 平衡

**症状**：用户期望 `Eos_wrapped` 调用后 T_ion = T_ele。

**原因**：Eos 只算"给定 (ρ, e)，求 (P, T)"，不做平衡。

**修复**：平衡靠 Heatexchange 单元。

### E.3 以为 `helm_table.dat` 是 ionmix 格式

**症状**：用户混淆 Helmholtz 表和 ionmix 表。

**原因**：两者都是 EOS 表但格式和用途完全不同：
- `helm_table.dat`：电子简并自由能表（Helmholtz 专用）
- `*.imx`：物质 EOS + 不透明度（Tabulated 用）

**修复**：见 `knowledge/overview.md §6`（Tabulated vs Helmholtz 对比）。

### E.4 以为 `eos_forceConstantInput` 默认 TRUE

**症状**：用户调试发现 e 变了，以为 bug。

**原因**：默认 FALSE，Helmholtz 会修改输入让自洽。

**修复**：`eos_forceConstantInput = .true.` 关闭（但通常不需要）。

### E.5 以为 `eos_combinedTempRule` 是 -10 就是"自动"

**症状**：3T 算例 `TEMP_VAR` 是垃圾值。

**原因**：`-10` 是"未定义"，不是"自动选"。

**修复**：明确设（如 `= 2` 让 TEMP_VAR = T_ele）。

---

## F. 通用调试流程

按 L-012 诊断类流程：

### F.1 看 abort 信息

```bash
grep "abort\|Newton\|out of table" 01-data/<basenm>.log | head -10
```

### F.2 看 Eos_init 打印的参数

```bash
grep "Eos_init\|eos_type\|Helmholtz\|table" 01-data/<basenm>.log | head -20
```

### F.3 看 parfile EOS 段是否生效

```bash
grep "eosMode\|smalle\|smlrho\|eos_coulomb" 01-data/<basenm>.log | head -10
```

### F.4 看物理量是否超表

```bash
grep "max dens\|min dens\|max temp\|min temp" 01-data/<basenm>.log | tail -10
```

### F.5 跨 skill 协作

| 症状 | 协作链 |
|---|---|
| EOS abort + 激光算例 | `flash-pitfall-finder`（定位）→ `flash-eos`（修参数）→ `flash-laser`（验证） |
| 3T 不平衡 | `flash-eos`（EOS 调用）→ `flash-sourceterms`（Heatexchange，Phase 2） |
| Hydro 后 EOS 报错 | `flash-hydro`（Hydro 给 e）→ `flash-eos`（EOS 算 P,T） |
| 不知道 abort 来源 | `flash-pitfall-finder`（匹配）→ 对应物理 skill |

---

## G. 延伸阅读

- **Eos 总览**：`knowledge/overview.md`
- **完整参数列表**：`knowledge/params.md`
- **Eos_wrapped 流程**：`knowledge/internals.md §2`
- **典型配置**：`knowledge/recipes.md`
- **Helmholtz 表机制**：`knowledge/overview.md §5`
- **3T 设计**：`knowledge/overview.md §4`
- **跨单元踩坑**：`skills/flash-pitfall-finder/knowledge/pitfalls/`
- **Heatexchange 单元**：`flash-sourceterms`（Phase 2 后）

---

## H. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：4 大类 18 踩坑（A 启动 5 + B 数值 5 + C 模式陷阱 5 + D 3T 4 + E 概念 5）+ 诊断引导层（按 L-012）+ 通用调试流程 | claude |
