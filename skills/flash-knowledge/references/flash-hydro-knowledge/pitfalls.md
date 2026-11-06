---
title: Hydro 常见踩坑 — CFL / 负密度 / Riemann / MHD divB / 限幅器
skill: flash-hydro
category: pitfalls
source_anchors:
  - source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L126-L131
  - source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L145-L154
  - source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L173-L180
  - source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:L229-L233
  - source/physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90:L412-L462
  - source/physics/Hydro/HydroMain/unsplit/hy_uhd_shockDetect.F90:L80-L81
manual_ref: "FLASH 4.8 User Guide §9-12"
created: 2026-07-19
last_verified: 2026-07-19
verifier: claude
status: draft
tags:
  - hydro
  - pitfall
  - cfl
  - nan
  - riemann
  - mhd
---

# Hydro 常见踩坑

> **TL;DR**：分 4 大类共 20+ 条踩坑：**A 启动期**（变体冲突、几何 abort）+ **B 运行期数值**（NaN、负密度、CFL 不稳）+ **C Riemann/限幅器选错** + **D MHD 专属**（divB 发散、prolMethod）。

---

## A. 启动期踩坑

### A.1 `use_upwindTVD forced off because NGUARD <= 4` abort

**触发代码**：

```fortran
! source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:145-154
if (use_upwindTVD .and. NGUARD <= 4) then
    use_upwindTVD = .FALSE.
    call Driver_abortFlash("use_upwindTVD requires NGUARD >= 6")
end if
```

**原因**：PPM upwind TVD 需要更宽的模板（6 层 guard cell），但默认 NGUARD=4。

**修复**：
- 选项 A：setup 加 `SupportPpmUpwind`（让 Hydro Config 自动设 NGUARD=6）
- 选项 B：在 unit Config 加 `GUARDCELLS 6`，重新 setup+make
- 选项 C：放弃 PPM upwind，用默认 order=2

### A.2 `use_3dFullCTU only supported for Cartesian` abort

**触发代码**：

```fortran
! source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:173-180
if (hy_use3dFullCTU .and. gr_geometry /= CARTESIAN) then
    call Driver_abortFlash("use_3dFullCTU only supported for Cartesian geometry")
end if
```

**原因**：Full CTU 的 corner coupling 只在笛卡尔几何下推导。

**修复**：
- 笛卡尔几何：保持 `use_3dFullCTU=.TRUE.`
- 柱坐标 / 球坐标：`use_3dFullCTU = .false.`（接受 CFL≤1/2）

### A.3 `prolMethod forced to Balsara for cylindrical` 警告

**触发代码**：

```fortran
! source/physics/Hydro/HydroMain/unsplit/Hydro_init.F90:229-233
if (gr_geometry == CYLINDRICAL .and. hy_prolMethod /= BALSR_PROL) then
    hy_prolMethod = BALSR_PROL
    print *, "Warning: prolMethod forced to Balsara for cylindrical geometry"
end if
```

**原因**：cylindrical 几何下，face-var prolongation 必须考虑几何权重。

**修复**：直接在 parfile 设 `prolMethod = "balsara_prol"`，避免警告。

### A.4 `RiemannSolver HLLD requires MHD` abort

**原因**：HLLD 是 MHD 专用（5 中间态），纯流体不能解。

**修复**：
- 纯流体：用 HLLC（默认）
- MHD：setup 加 `+usm`（启用 USM-MHD）

### A.5 `use_Biermann requires conserveAngField` abort（cylindrical + 3T）

**原因**：cylindrical 几何 + 3T 模式下，Biermann battery 必须用角向场守恒形式。

**修复**：parfile 设 `conserveAngField = .true.`。

---

## B. 运行期数值踩坑

### B.1 跑几步出现 NaN

**症状**：日志 `NaN in cell (i,j,k)` 或 plotfile 显示 NaN。

**可能原因**（按优先级）：

1. **CFL 太大**：cfl > 算例实际上限
   - 修复：降到 0.3，逐步加大

2. **截断太低**：smlrho/smallp/smalle 默认 1E-10，天体算例需要 1E-30
   - 修复：按算例密度尺度调

3. **Riemann solver 选错**：HLLC 在强激波可能崩
   - 修复：换 Hybrid 或 HLL

4. **限幅器关掉**：`charLimiting = .false.` → 激波附近振荡
   - 修复：恢复 `charLimiting = .true.`（默认）

5. **initial condition 有奇点**：如密度=0、温度=0
   - 修复：检查 `Simulation_initBlock`，确保 floor values

**诊断流程**：

```bash
# 1. 找 NaN 位置
grep "NaN" 01-data/<basenm>.log | head -5

# 2. 看是哪个变量变 NaN（plotfile 用 yt 或 Visit）
# 3. 看 NaN 出现时的物理条件（激波？边界？）
# 4. 试着换 Riemann / 降 CFL / 加截断
```

### B.2 出现负密度（"density below floor" 警告或 abort）

**症状**：日志反复警告 `density in cell (i,j,k) below smlrho`。

**可能原因**：

1. **强激波附近数值不稳定**：Riemann solver 给出非物理解
   - 修复：换 Hybrid 或 HLL；降 CFL；激波探测

2. **smlrho 太高**：算例本身密度低
   - 修复：降到物理合理值

3. **AMR 边界 flux 不守恒**：粗-细边界漏能量
   - 修复：确认 `flux_correct = .true.`（默认）；UG 模式关掉

4. **limiter 太锐**：MC limiter 在强激波可能崩
   - 修复：换 vanLeer（默认）

### B.3 `CFL too small` 持续降 dt

**症状**：dt 持续降到极小值，算例卡死。

**可能原因**：

1. **局部数值不稳定**：某个 cell 出现极端值（如 Mach 数爆炸）
2. **AMR 过度细化**：lrefine_max 太高，小 cell 限制 dt
3. **物理真的需要小 dt**：如激波加速、磁重联

**诊断**：

```bash
# 看 dt decomposition（Driver 日志）
grep "dt decomposition\|dt limiting" 01-data/<basenm>.log | tail -10
```

**修复**：
- 找到限制 dt 的 cell（dtMinLoc）
- 修复该 cell 的物理（可能是 NaN / 负密度）
- 如果是 AMR 过度细化，降 lrefine_max 或加 `refine_filter`

### B.4 能量不守恒（总能量随时间漂移）

**症状**：能量监控显示总能不再守恒（应等于初始能量 + 边界通量 + 源项）。

**可能原因**：

1. **AMR 边界 flux 不守恒**：flux_correct 关了
2. **边界 BC 错**：outflow 实际是流入
3. **EOS 不自洽**：dens/ener/temp 不一致
4. **use_auxEintEqn 关了**：KE ≫ IE 时消去误差

**诊断**：在 parfile 加 `energyFix = .true.`（虽然默认 TRUE，但 USM-MHD 下默认 FALSE，确认）。

---

## C. Riemann / 限幅器选错

### C.1 HLLC 在强激波崩（出现负密度）

**症状**：纯流体 + 强激波算例（如 Mach > 10）跑出 NaN。

**原因**：HLLC 在中间状态可能给出负压力（特别是在跨音速激波附近）。

**修复**：换 `RiemannSolver = "Hybrid"`（激波处用 HLL）。

### C.2 用 Roe 没开 entropy fix

**症状**：跨音速稀疏波附近出现非物理激波。

**原因**：Roe solver 在跨音速稀疏波会产生"膨胀激波"（违反熵条件）。

**修复**：

```fortran
RiemannSolver = "Roe"
entropy = .true.                      # ★ 必开
entropyFixMethod = "HARTENHYMAN"      # 推荐
```

### C.3 关掉 charLimiting 后激波失真

**症状**：激波附近出现振荡（密度/压力 wiggle）。

**原因**：charLimiting=.FALSE. 让限幅器作用在原始变量，不同波族耦合。

**修复**：恢复 `charLimiting = .true.`（默认）。

### C.4 MC limiter 在强激波崩

**症状**：用 `slopeLimiter = "mc"` 后出现 NaN。

**原因**：MC（monotonized central）是最锐的 TVD limiter，对非线性敏感。

**修复**：换 `slopeLimiter = "vanLeer"`（默认，平衡）。

### C.5 order=3 (PPM) 但 NGUARD=4

**症状**：setup 通过但跑出来精度不对，或出现边界 artifact。

**原因**：PPM 重构需要更宽模板。

**修复**：要么用 `order=2`（默认 MUSCL-Hancock），要么 NGUARD 加到 6。

---

## D. MHD 专属踩坑

### D.1 `divB nonzero` 警告（USM-MHD）

**症状**：日志反复警告 `divB = X in cell (i,j,k)`，X 不是机器精度。

**可能原因**：

1. `killdivb = .false.` → CT 关了
2. 初始条件 B 场不自洽（∇·B ≠ 0）
3. 边界 BC 让 B 不闭合
4. 用了 `ForceHydroLimit = .true.`（关闭 B 更新，但仍初始化了 B）

**诊断**：

```bash
grep "divB\|divb" 01-data/<basenm>.log | head -20
```

**修复**：
- 确认 `killdivb = .true.`（默认）
- 检查 `Simulation_initBlock` 的 B 初始条件
- 边界 BC 用 `reflecting` 或 `outflow`（不要 `periodic` + 非零净通量）

### D.2 用 8-wave 但期望 CT 精度

**症状**：用 `+8wave` 后 ∇·B 漂移。

**原因**：Powell 8-wave 不保证 ∇·B = 0，只是加源项让它"不爆炸"。

**修复**：
- 想要 CT 精度 → 用 `+usm`（USM-MHD with CT）
- 必须用 8-wave → 接受 ∇·B 漂移

### D.3 Hall MHD 时步爆炸

**症状**：启用 `use_Hall = .true.` 后 dt 变得极小。

**原因**：Hall 项引入电子回旋频率尺度，比离子时间步小很多。

**修复**：
- 接受（如果物理真的需要）
- 用 Hall sub-cycling（部分算例支持）
- 降低 Hall 系数（如果是数值实验）

### D.4 柱坐标 MHD 没用 Balsara prolongation

**症状**：USM-MHD + cylindrical 跑出磁场 artifact。

**原因**：见 A.3。

**修复**：parfile 设 `prolMethod = "balsara_prol"`（或让 Hydro_init 自动强制）。

### D.5 3T MHD 没 conserveAngField

**症状**：3T + MHD + cylindrical 出现非物理角向场。

**修复**：parfile 设 `conserveAngField = .true.`。

---

## E. 概念错误踩坑

### E.1 parfile 写 `hy_cfl` 而不是 `cfl`

**症状**：parfile 写 `hy_cfl = 0.5`，但实际跑的是默认 0.8。

**原因**：runtime parameter 名是 `cfl`（**无 hy_ 前缀**）。`hy_cfl` 只是 Hydro_data 模块的内部变量。

**修复**：parfile 写 `cfl = 0.5`。详见 `knowledge/params.md §0`。

### E.2 parfile 写 `hy_RiemannSolver`

同 E.1。**正确名是 `RiemannSolver`**。

### E.3 以为 `+mhd` 是有效 shortcut

**症状**：setup 命令用 `+mhd` 报错或不生效。

**原因**：**没有** `+mhd` shortcut。

**修复**：用 `+usm`（推荐 USM-MHD）或 `+8wave`（split MHD）。

### E.4 以为 `+split` 是 unsplit 的反义词

**症状**：setup 用 `+split` 报错或不生效。

**原因**：**没有** `+split` shortcut。要用 `+splitHydro`。

### E.5 以为 unsplit 永远比 split 好

**症状**：所有算例都强制 unsplit。

**原因**：燃烧 / 火焰算例社区习惯用 split PPM，且验证充分。

**修复**：燃烧算例仍可用 split PPM。

### E.6 以为 RiemannSolver 名字大小写不敏感

**症状**：写 `riemannsolver = "hllc"` 偶尔失败。

**原因**：FLASH runtime parameter 名**大小写敏感**（虽然 Fortran 不敏感）。

**修复**：严格按 Config 声明的大小写：`RiemannSolver`、`HLLC`。

---

## F. 通用调试流程

遇到 Hydro 相关 abort 时：

### F.1 看 abort 信息

```bash
grep "Driver_abortFlash\|abort" 01-data/<basenm>.log
```

### F.2 看 Hydro 初始化

```bash
grep "Hydro_init\|RiemannSolver\|cfl\|order" 01-data/<basenm>.log | head -30
```

应该看到 Hydro_init 打印的所有参数值。

### F.3 看 NaN / 负密度位置

```bash
grep "NaN\|below floor\|negative" 01-data/<basenm>.log | head -20
```

### F.4 看 dt 历史

```bash
grep "^.*dt = " 01-data/<basenm>.log | tail -20
```

dt 应该稳定或缓慢变化；突然爆降通常意味着局部数值不稳定。

### F.5 跨 skill 协作

| 症状 | 协作链 |
|---|---|
| 激光算例 + Hydro 崩 | `flash-pitfall-finder`（定位）→ `flash-hydro`（修参数）→ `flash-laser`（验证） |
| 网格细化但 Hydro 算错 | `flash-grid`（AMR）→ `flash-hydro`（flux correction） |
| 3T 变量不自洽 | `flash-hydro`（hydro）→ `flash-eos`（EOS 调和，Phase 2） |
| 不知道 abort 来源 | `flash-pitfall-finder`（匹配）→ 对应物理 skill |

---

## G. 延伸阅读

- **Hydro 参数完整字典**：`knowledge/params.md`
- **CTU 内部流程**：`knowledge/internals.md §3`
- **典型配置**：`knowledge/recipes.md`
- **变体对比**：`knowledge/overview.md §2`
- **跨单元踩坑**：`skills/flash-pitfall-finder/knowledge/pitfalls/`
- **Driver 主循环**：`flash-driver/knowledge/internals.md`
- **Grid 单元**：`flash-grid/knowledge/overview.md`

---

## H. 变更日志

| 日期 | 改动 | 改动人 |
|---|---|---|
| 2026-07-19 | 初始创建（draft）：4 大类 20+ 踩坑（A 启动 5 + B 数值 4 + C Riemann/限幅器 5 + D MHD 5 + E 概念 6）+ 通用调试流程 + 跨 skill 协作 | claude |
