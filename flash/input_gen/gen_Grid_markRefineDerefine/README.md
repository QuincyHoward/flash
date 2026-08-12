# gen_Grid_markRefineDerefine — 网格细化约束生成器

> FLASH AMR 网格细化/粗化自定义约束（逐材料区域层级约束）的一站式生成与说明文档。
> 自动生成器 + 手写参考实现（来自 `thin_layer_sandwich` 场景）双轨并存。

---

**flash-sim** 是 [FLASH](https://flash.rochester.edu/) 高能量密度物理 (HEDP) 仿真代码的全功能 Python 封装。提供**场景系统**（即插即用仿真入口）、参数文件生成、多环境运行管理、HDF5 输出分析与自适应可视化的一站式工作流。

## 仓库地址 (Repository)

本项目托管于 Gitee (码云), 支持 HTTPS 克隆与在线浏览:

```
https://gitee.com/physimx/flash
```

| 操作 | 命令 |
|------|------|
| **HTTPS 克隆** | `git clone https://gitee.com/physimx/flash.git` |
| **在线浏览** | https://gitee.com/physimx/flash (Code/Issues/Releases 页签) |
| **版本标签** | `0.1.0` (PyPI 首次发布) — `git tag -l` 查看全部 |
| **问题反馈** | 通过 Gitee Issues 提交 (登录后新建 Issue) |

> 发布包已通过全局测试 (233 passed / 3 skipped) 与 FLASH 版权合规检查, (详见 [许可](#许可) 与 [NOTICE](NOTICE))。

---

## 概述

`gen_Grid_markRefineDerefine` 子包用于生成 FLASH AMR（自适应网格细化）的 **`Grid_markRefineDerefine.F90`** 文件 —— 这是一个**可选的** FLASH 自定义组件，定义「何时细化 / 何时粗化」网格。

本子包提供**两种工作方式**，互为补充：

1. **自动生成器（推荐）** —— `generator.py` 中的 `GridMarkRefineDerefineGenerator`，按参数生成基于**模式 C3（边界框重叠法）**的约束代码。
2. **手写参考实现** —— 来自 `scenarios/collision_compression/thin_layer_sandwich/` 场景的 `sim_input_al/Grid_markRefineDerefine.F90` 与 `sim_input_si/Grid_markRefineDerefine.F90`，是已在实际仿真中验证通过的成品模板。

> ⚠️ **文档修订说明**：早期 `GEN_GRID_GUIDE.md` 中「暂无自动生成器，需手动编写或从 refs/ 复制」的描述**已过时**——生成器 `generator.py` 现已存在。本 README 已将其合并并纠正，原 `GEN_GRID_GUIDE.md` 中的「复制/手动编写」步骤仅作为手写参考保留。

### 它能做什么

- 对 FLASH 仿真中**不同材料区域**施加不同的网格细化层级约束
- 例如：Al 靶区需要 `lref ∈ [lrefine_max-2, lrefine_max]`，CH 泡沫区 `lref ≤ lrefine_max/2`，He 填充区 `lref ≤ lrefine_min`
- 使用**边界框重叠法**（模式 C3），确保超薄层区域（如 0.2µm Al）也能被正确检测和细化

### 它不做什么

- ❌ 不修改物理求解器逻辑
- ❌ 不生成 `.par` 文件或 `Config` 文件
- ❌ 不替换 FLASH 的标准二阶梯度加密机制——它只是一个**附加约束层**

### 适用场景与参考实现

| 方式 | 位置 | 用途 |
|------|------|------|
| 自动生成器 | `input_gen/gen_Grid_markRefineDerefine/generator.py` | 参数化生成模式 C3 约束代码 |
| 手写模板 `al` 变体 | `scenarios/collision_compression/thin_layer_sandwich/sim_input_al/Grid_markRefineDerefine.F90` | 三层靶（Al/CH/He）1D 实测模板 |
| 手写模板 `si` 变体 | `scenarios/collision_compression/thin_layer_sandwich/sim_input_si/Grid_markRefineDerefine.F90` | 同结构、不同材料表的变体 |

`thin_layer_sandwich` 场景的物理背景：**1D 笛卡尔坐标、激光烧蚀多层靶**，域范围 `x ∈ [-200, 200] µm`（实际 `.par` 中 `xmin=-0.045, xmax=0.045` cm），材料对称布局：

| 位置 \|x\| (µm) | 材料 | 目标细化 |
|----------------|------|----------|
| ≤ 0.2 | Al 靶材 | 高精度 (如 6~8 级) |
| (0.2, 4] | CH 泡沫 | 中精度 (如 1~4 级) |
| > 4 | He 填充 | 不强制（低精度） |

---

## Grid_markRefineDerefine.F90 用途

这个 Fortran 子程序定义 AMR 网格细化和粗化条件。FLASH 根据用户输入的 `refine_var_*` 参数（标准二阶梯度加密），**再叠加本文件定义的材料区域约束**，调用此子程序判断是否细化或粗化特定区域的网格。

> 本文件是 FLASH 自定义组件，**必须随仿真算例一起编译**（放在 `SimulationMain/<算例>/` 目录下），而非独立的 Python 运行步骤。

---

## 关键技术要点（已为用户核心规范）

### 1. AMR 细化变量配置规则

在 `.par` 文件中配置标准二阶梯度加密变量（数字越大优先级越靠后）：

```python
lrefine_max = 8          # 最大细化等级
lrefine_min = 1          # 最小细化等级
refine_var_1 = "dens"    # 细化变量1：密度
refine_var_2 = "tele"    # 细化变量2：电子温度
```

`thin_layer_sandwich/sim_input_al/grid_rede.par` 中的实测配置即为此形式（`refine_var_1=dens`、`refine_var_2=tele`）。

### 2. 1D / 2D / 3D 坐标获取差异

| 维度 | 坐标获取 | 循环结构 |
|------|---------|---------|
| 1D | 只需 `xcent(i)` / 边界框 `boundBox(*, IAXIS)` | `do i = ...` |
| 2D | 需要 `xcent(i)`, `ycent(j)` | `do j = ...; do i = ...` |
| 3D | 需要 `xcent(i)`, `ycent(j)`, `zcent(k)` | `do k = ...; do j = ...; do i = ...` |

> 当前生成器与 `thin_layer_sandwich` 模板均为 **1D（IAXIS）实现**；2D/3D 需相应扩展坐标判断。

### 3. 典型细化逻辑（LaserSlab 1D）

```fortran
! 在靶区域 (x < sim_targetRadius) 细化到最高等级
if (xcent(i) < sim_targetRadius) then
    need_refine = .true.
endif

! 在密度梯度大的区域细化
if (abs(dens(i+1) - dens(i)) / dx > threshold) then
    need_refine = .true.
endif
```

### 4. 边界框重叠法（核心设计，来自 thin_layer_sandwich 模板）

`thin_layer_sandwich` 的 F90 注释（2026-07-02）明确指出：

- **旧「块中心法」的缺陷**：当目标区域宽度 < 最小块尺寸时完全失效。例如 Al 区仅 0.2µm，远小于 `lref=1` 时的块尺寸 50µm —— 没有任何块的中心落在 Al 或 CH 范围内，所有块都会被误判为 He → `lref ≤ 1` → **永远达不到高分辨率**。
- **新「边界框重叠法」**：检查块的 `[LOW, HIGH]` 区间是否与目标区域重叠（`boundBox(HIGH,IAXIS) >= -var .and. boundBox(LOW,IAXIS) <= var`），**即使块远大于目标区域，只要覆盖即触发约束**。

```fortran
! 判断块是否与 Al 靶材区重叠: Al 区范围 x ∈ [-sim_targHeight, sim_targHeight]
if (boundBox(HIGH, IAXIS) >= -sim_targHeight .and. &
    boundBox(LOW, IAXIS)  <=  sim_targHeight) then
    ! ═══ Al 靶材区 ═══ 约束: lref ∈ [lrefine_max-2, lrefine_max]
    if (lrefine(lb) < al_lower_lref) then
        refine(lb)   = .true.
        derefine(lb) = .false.
    else if (lrefine(lb) > al_target_lref) then
        refine(lb)   = .false.
        derefine(lb) = .true.
    end if
else if (boundBox(HIGH, IAXIS) >= -sim_polyHeight .and. &
         boundBox(LOW, IAXIS)  <=  sim_polyHeight) then
    ! ═══ CH 泡沫区 ═══ 约束: lref ≤ lrefine_max/2
    ...
else
    ! ═══ He 填充区 ═══ 约束: lref ≤ lrefine_min（仅 derefine 方向）
    ...
end if
```

**分层约束（由 `lrefine_max` 自适应，不硬编码）**：

| 区域 | 上限 | 下限 | 说明 |
|------|------|------|------|
| Al 靶材 | `lrefine_max` | `lrefine_max - 2` | 确保亚微米层有足够分辨率 |
| CH 泡沫 | `lrefine_max / 2`（不低于 2） | 不设下限 | 避免界面梯度引起的非物理过度细化 |
| He 填充 | `lrefine_min` | 不设下限 | 自然退粗到最粗网格 |

**过渡机制**：PARAMESH 要求相邻块细化层级差 `|Δlref| ≤ 1`，即使 CH 区标记为退粗到 4，Al 边界附近的块也会被 PARAMESH 维持在高一级（被动产生平滑过渡带）。

### 5. FLASH 版权合规头（手写模板必备）

`thin_layer_sandwich` 的 F90 文件头部包含 FLASHCenter 合规声明，任何修改版 FLASH 源文件都应保留：

```fortran
!!  MODIFIED BY: PhySimX Contributors — derivative of the FLASH Center's
!!  source/Simulation/SimulationMain/LaserSlab_Custom/Grid_markRefineDerefine
!!  (modified for a new physics setup; original FLASH header preserved
!!  intact per FLASH License Agreement §4(c); modification declared per §4(a)).
```

> ⚠️ **注意**：自动生成器 `_header()` 当前**未自动插入**上述 `MODIFIED BY` 合规头。通过生成器产出的 F90 在正式提交前应**手动补回**该段声明，以满足 FLASH License Agreement §4(a)。

### 6. 依赖的 Simulation_data 半宽变量

区域判断依赖 `Simulation_data.F90` 中的半宽变量（来自 `thin_layer_sandwich/sim_input_al/Simulation_data.F90`）：

| 变量 | 含义 | `.par` 实测值 |
|------|------|---------------|
| `sim_targHeight` | Al 靶材层半高 (µm / cm) | `2e-5` |
| `sim_polyHeight` | CH 泡沫层半高 (µm / cm) | `4e-4` |

这些变量必须在 `Simulation_data.F90` 中声明、并在 `Simulation_init` 中从 `.par` 读取后，本约束文件才能编译运行。

---

## 使用方法（自动生成器 GridMarkRefineDerefineGenerator）

### 重要：生成顺序

本生成器应在 **`.par` 文件生成之后** 调用，因为 `lrefine_max` / `lrefine_min` 需从 `.par` 文件中读取，以保证 F90 注释中的理论分辨率与实际仿真参数一致。

```python
from input_gen.gen_Grid_markRefineDerefine import (
    GridMarkRefineDerefineGenerator, ZoneConfig
)

# 创建生成器（simulation_name 仅用于注释路径; sim_src_subdir 默认读 credentials）
gen = GridMarkRefineDerefineGenerator("my_simulation")

# 所有参数均无默认值，必须逐项传入
# 这些值来自：setup 命令（nxb, nblockx）、.par 文件（xmin, xmax, lrefine_max/min）
gen.set_domain(xmin=-0.02, xmax=0.02, nxb=16, nblockx=8)
gen.set_refinement(lrefine_max=8, lrefine_min=1)

# 添加区域约束（按优先级从高到低 → 对应 if / else if / else）
gen.add_zone(ZoneConfig(
    "Al",                     # 区域名称
    "sim_targHeight",         # Simulation_data 中的半宽变量
    lref_lower_ratio=0.75,    # 下限: lrefine_max × 0.75（=6，当 lrefine_max=8）
    lref_upper_ratio=1.0      # 上限: lrefine_max（=8）
))
gen.add_zone(ZoneConfig(
    "CH",
    "sim_polyHeight",
    lref_lower_ratio=None,    # 不设下限（不主动 refine）
    lref_upper_ratio=0.5      # 上限: lrefine_max × 0.5（=4）
))
gen.add_zone(ZoneConfig(
    "He", None, None, None    # Fallback: 无约束
))

# 生成并保存（强制 LF 换行）
gen.save("sim_input/Grid_markRefineDerefine.F90")
```

### ZoneConfig 参数说明

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `name` | str | 区域名称（仅用于注释） | `"Al"` |
| `sim_var_name` | str/None | Simulation_data 中的半宽变量名。None=fallback | `"sim_targHeight"` |
| `lref_lower_ratio` | float/None | 下限比例因子。相对 `lrefine_max`。None=不设下限 | `0.75`, `0.5`, `None` |
| `lref_upper_ratio` | float/None | 上限比例因子（同上）。None=不设上限 | `1.0`, `0.5`, `None` |
| `use_bounding_box` | bool | 使用边界框重叠法（默认 True，推荐） | `True` |
| `zone_margin` | float | 缓冲区扩展系数（>1.0 时区域判断边界向两侧扩展，减少界面数值不稳定性；默认 1.0） | `1.0`, `1.2` |

### ratio 值的含义（比例因子）

所有 ratio 值均为**比例因子**，相对于 `lrefine_max`：

| 值 | 含义 | F90 表达式（lrefine_max=8 时） |
|----|------|-------------------------------|
| `None` | 无约束 | — |
| `1.0` | lrefine_max | `lrefine_max` → 8 |
| `0.75` | lrefine_max × 0.75 | `lrefine_max * 3 / 4` → 6 |
| `0.5` | lrefine_max × 0.5 | `lrefine_max / 2` → 4 |
| `0.25` | lrefine_max × 0.25 | `lrefine_max / 4` → 2 |

> 💡 **薄层材料陷阱**：`ZoneConfig` 文档指出，厚度 ≤ 几倍 `res_min` 的薄层材料（如 Al 靶），`lref_lower_ratio` **必须设为 `1.0`**，否则初始化阶段可能达不到 `lrefine_max`，导致薄层分辨率不足。

### 生成的 F90 结构（5 段）

生成器产出的 `Grid_markRefineDerefine()` 子程序依次包含：

1. **USE 语句** —— 导入 FLASH 模块与 `Simulation_data` 半宽变量
2. **变量声明** —— 含 `zone_margin > 1.0` 时为区域生成的 `*_zone_half` 缓冲变量
3. **标准二阶梯度加密流程** —— `gr_markDerefineByTime` / `gr_setMaxRefineByTime` / `Grid_fillGuardCells` / `gr_markRefineDerefine`
4. **区域约束（边界框重叠）** —— `Grid_getListOfBlocks` + `Grid_getBlkBoundBox`，逐叶块 `if / else if / else` 标记 `refine`/`derefine`
5. **标准后处理收尾** —— PARAMESH2 兼容、粒子计数加密、最大精度强制、`gr_unmarkRefineByLogRadius`、Sink 粒子加密、**非叶块标志清理（`where (nodetype(:) /= LEAF)` 必须清零，否则 PARAMESH 崩溃）**

---

## 分辨率核算（来自 thin_layer_sandwich F90 注释）

### 公式

```
res_min = |xmax - xmin| / (NXB * nblockx * 2^(lrefine_max-1))
res_max = |xmax - xmin| / (NXB * nblockx * 2^(lrefine_min-1))
```

（单位换算：若 `xmin/xmax` 以 cm 传入，需 ×1e4 换算为 µm；生成器 `_calc_resolution` 已内置此换算。）

### 1D 示例（域 400µm，NXB=8，nblockx=1）

| lrefine_max | res_min (µm) | 是否满足 Al < 0.03µm |
|-------------|--------------|----------------------|
| 12 | 400/(8×1×2¹¹) ≈ **0.0244** | ✅ |
| 11 | 400/(8×1×2¹⁰) ≈ 0.0488 | ❌ |
| 10 | 400/(8×1×2⁹)  ≈ 0.0977 | ❌ |
| 8  | 400/(8×1×2⁷)  ≈ 0.391  | ❌ |

| lrefine_min | res_max (µm) |
|-------------|--------------|
| 4 | 400/(8×1×2³) ≈ 6.25 |
| 3 | 400/(8×1×2²) ≈ 12.5 |

> **结论**：满足 Al 分辨率 < 0.03µm 的最小 `lrefine_max = 12`，推荐 `lrefine_max=12, lrefine_min=4, nblockx=1`（高分辨率需求场景）；常规演示可用 `thin_layer_sandwich` 的 `lrefine_max=8, lrefine_min=1, nblockx=8`。

---

## ⚠️ 重要：必须人工核查

本生成器生成的代码是**自定义 AMR 细化约束器**，实际细化结果受以下因素影响：

1. **`refine_var` 梯度判据** —— `.par` 文件中的 `refine_var_*` 设置
2. **PARAMESH 邻接限制** —— 相邻块 `|Δlref| ≤ 1`
3. **`lrefine_max` / `lrefine_min`** —— 全局限制

**建议进行小批量 flash 仿真进行人工核查后再正式使用。**

---

## 参考文件与实现位置

| 类型 | 路径 |
|------|------|
| 自动生成器 | `input_gen/gen_Grid_markRefineDerefine/generator.py` |
| 手写 `al` 模板 | `scenarios/collision_compression/thin_layer_sandwich/sim_input_al/Grid_markRefineDerefine.F90` |
| 手写 `si` 模板 | `scenarios/collision_compression/thin_layer_sandwich/sim_input_si/Grid_markRefineDerefine.F90` |
| 配套半宽变量声明 | `scenarios/collision_compression/thin_layer_sandwich/sim_input_al/Simulation_data.F90` |
| 配套参数文件 | `scenarios/collision_compression/thin_layer_sandwich/sim_input_al/grid_rede.par` |

> ⚠️ **废弃引用**：早期文档提到的 `refs/Grid_markRefineDerefine.F90`、`refs/Al_CH_He_laser_cart1D/`、`refs/Grid_markRefineDerefine_编写指南.md` 等 `refs/` 目录**当前不存在**。请以本仓库内 `thin_layer_sandwich` 的 F90 文件作为权威手写模板。

---

## 致谢与商用说明

本生成器产出的 `Grid_markRefineDerefine.F90` 属于 flash-sim（flash 仿真辅助 Python 包）的一部分，相关署名与商用条款如下：

- **出版物致谢**：使用 flash-sim 产生的任何出版物，请感谢**绵阳市的 PhySimX 团队**开发了该仿真辅助 Python 包。建议文案：*"We acknowledge the PhySimX team (Mianyang, China) for developing the flash-sim auxiliary Python package used in this work."*
- **商用说明**：flash-sim 的 Python 代码以 Apache 2.0 许可，其商用须遵守所有适用许可（含 FLASH 仿真引擎的 FLASH License Agreement §5），商用场景下的授权与责任以届时适用的许可及书面约定为准。

完整条款见根目录 [README.md 许可章节](../../README.md#许可)、[LICENSE](../../LICENSE) 与 [NOTICE](../../NOTICE)。

---

**文档版本**: 2.0（合并 `README.md` + `GEN_GRID_GUIDE.md`，并补充 `thin_layer_sandwich` F90 参考实现）
**最后更新**: 2026-08-03
**维护**: PhySimX Team
