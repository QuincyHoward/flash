---
name: flash-grid-refine-constraint
description: FLASH AMR 网格细化约束生成器（gen_Grid_markRefineDerefine）：逐材料区域的层级约束 Grid_markRefineDerefine.F90 生成，区域分层细化、多材料不同细化层级、超薄层保护。需要自定义 AMR 细化行为时使用。触发词：网格细化约束、Grid_markRefineDerefine、AMR 分区细化、lrefine 约束、ZoneConfig、超薄层、细化层级。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 来源：用户级 flash-grid-refine-constraint 技能吸收（导入路径与参考文件已按本仓现行代码校正）

# AMR 网格细化约束（flash-grid-refine-constraint）

## 适用场景

- 按材料区域施加不同细化层级（如 Al 靶 lrefine_max、CH 缓冲区减半、He 无约束）
- 超薄层材料（厚度 ≤ 几倍 res_min）的初始化细化保护
- 生成可选附加文件 `Grid_markRefineDerefine.F90`（不修改物理求解器）

## 前置条件

- `flash/input_gen/gen_Grid_markRefineDerefine/generator.py`（生成器源码，参数权威）
- `sim_var_name` 引用的参数已完成 5 步注册（见操作步骤 3.1）

## 操作步骤

### 1. 导入（注意：包 `__init__.py` 为空，须从 generator 模块导入）

```python
from flash.input_gen.gen_Grid_markRefineDerefine.generator import (
    GridMarkRefineDerefineGenerator, ZoneConfig
)
```

### 2. 快速使用

```python
gen = GridMarkRefineDerefineGenerator("my_sim", sim_src_subdir=None)
#   sim_src_subdir=None → 从 flash._core.credentials 读取用户目录（勿硬编码）
gen.set_domain(xmin=-0.02, xmax=0.02, nxb=16, nblockx=8)   # 与 .par/setup 一致
gen.set_refinement(lrefine_max=8, lrefine_min=2)           # .par 生成后调用

# 添加区域（按优先级从高到低，决定 if-else 顺序）
gen.add_zone(ZoneConfig(
    "Al", "sim_targHeight",
    lref_lower_ratio=1.0,     # 超薄层必须 1.0（初始化细化陷阱）
    lref_upper_ratio=1.0,
))
gen.add_zone(ZoneConfig(
    "CH", "sim_polyHeight",
    lref_lower_ratio=None,    # 不设下限
    lref_upper_ratio=0.5,     # 上限 lrefine_max/2
))
gen.add_zone(ZoneConfig("He", None, None, None))   # fallback：无约束

gen.save("sim_input/Grid_markRefineDerefine.F90")
```

### 3. ZoneConfig 字段（`generator.py:32` 权威）

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 区域名（仅注释用） |
| `sim_var_name` | str/None | Simulation_data 半宽变量，区域 `|x| ≤ sim_var`；None=fallback |
| `lref_lower_ratio` | float/None | 下限比例（相对 lrefine_max）；**薄层材料必须 1.0** |
| `lref_upper_ratio` | float/None | 上限比例；None=不强制 derefine |
| `use_bounding_box` | bool | 边界框重叠法（默认 True，推荐） |
| `zone_margin` | float | 缓冲区扩展系数（>1.0 时区域边界外扩，默认 1.0） |

生成文件 = 标准梯度加密流程 + 区域约束（核心定制）+ 标准后处理三段。

### 4. 使用本生成器的额外必做工作

1. **参数 5 步注册**：`sim_var_name` 须在 Config（PARAMETER）/ Simulation_data.F90 / Simulation_init.F90 / Simulation_initBlock.F90 / .par 五处一致（流程同 flash-newpara）
2. **initBlock 一致性**：`sim_var_name` 对应物理边界必须与 initBlock 材料区域完全一致
3. **.par 配梯度判据**：`refine_var_1="dens"` + `refine_cutoff_1`/`derefine_cutoff_1`
4. **文件放置**：先存 `sim_input/`，再复制到 FLASH 树 `source/Simulation/SimulationMain/<用户目录>/<sim_name>/`，setup 自动包含
5. **独立调用**：本生成器是可选组件，`create_input_files()` 不包含它，须单独调用

## 护栏与铁律

1. `set_domain`/`set_refinement` 的值必须与 setup 命令和 .par 完全一致（生成 F90 注释中的分辨率据此计算）
2. 生成的约束是 AMR"建议"，实际细化还受 ①refine_var 梯度判据 ②PARAMESH 邻接限制（|Δlref|≤1）③lrefine_max/min 全局限制影响
3. 必须 setup → make → run 实际验证，检查 checkpoint 中各区域 lrefine 是否符合预期
4. 薄层材料 `lref_lower_ratio=1.0`，否则初始化阶段可能达不到 lrefine_max

## 常见坑

- ⚠️ 旧导入 `from flash.input_gen.gen_Grid_markRefineDerefine import ...` 无效（包 `__init__` 为空），必须 `.generator` 结尾
- ⚠️ 旧参考 `refs/Grid_markRefineDerefine_编写指南.md`、`refs/Al_CH_He_laser_cart1D/` 已删除；非 C3 模式（模式 B/E 几何/阈值判据）需求现参考 `flash/input_gen/gen_otherf90s/README.md` 与 FLASH-Expert 上游（`temp/FLASH-Expert/`）

## 关联资源

- `flash/input_gen/gen_Grid_markRefineDerefine/generator.py`（参数权威）
- `flash/input_gen/gen_otherf90s/README.md`（其他 F90 定制）
- `flash-knowledge`（grid/AMR 参数语义）、`flash-newpara`（参数 5 步注册）
