---
name: flash-par-gen
description: FLASH .par 参数文件生成与排版规范：10 个 section 固定顺序、边框对齐、键值对等号对齐、数值格式（bool/str/科学计数法/repr）、gen_par 与 gen_newpara 生成器结构、defaults.py 权威默认值、新增参数流程。触发词：par 生成、par 排版、参数文件、gen_par、gen_newpara、defaults.py、section 顺序、新增参数、数值格式。
---

> 最后核对：2026-11-06 · commit 14e320f（skill 巡检：分工声明补齐）
> 分工：本 skill 管 .par **排版规范与生成器结构**；生成 8+ 种输入文件的全流程用 `flash-input-gen`（其 references/api-reference.md 为 API 速查）。


# .par 参数文件生成与排版规范

权威参考：
- `flash/input_gen/gen_par/defaults.py` — 所有参数默认值的**最终来源**
- `docs/par_format_guide.md` — 排版规范全文
- 代码锚点：`flash/input_gen/gen_par/generator.py`、`flash/input_gen/gen_newpara/generator.py`

## 1. Section 顺序（固定，10 个）

| # | Section 标题 | 包含参数前缀 |
|---|---|---|
| 1 | I/O PARAMETERS | `checkpoint*`, `plot*`, `restart` |
| 2 | RADIATION/OPACITY PARAMETERS | `rt_*`, `op_*`, `useOpacity` |
| 3 | LASER PARAMETERS | `ed_*`, `useEnergyDeposition` |
| 4 | CONDUCTION PARAMETERS | `diff_*`, `useDiffuse`, `useConductivity` |
| 5 | HEAT EXCHANGE PARAMETERS | `useHeatexchange` |
| 6 | EOS PARAMETERS | `eos*`, `smallt`, `smallx` |
| 7 | HYDRO PARAMETERS | `useHydro`, `order`, `*boundary_type` |
| 8 | INITIAL CONDITIONS | `sim_*`, `ms_*` |
| 9 | TIME PARAMETERS | `tstep*`, `cfl`, `dt_*`, `tmax`, `nend` |
| 10 | MESH PARAMETERS | `geometry`, `xmin/xmax`, `nblock*`, `lrefine*` |

**MESH PARAMETERS 必须放最后**（section 10 固定位置）。

## 2. 格式规则

**Section 标题边框**：宽度 = `len(标题) + 12`；标题居中两侧各 5 空格；上下各一行空白 `#  #`。

```par
##########################
#                        #
#     I/O PARAMETERS     #
#                        #
##########################
```

**子段落注释**：`### Checkpoint Options ###` 格式，用于 section 内逻辑分组。

**等号对齐**：同一段落内所有 `=` 按最长 key 左对齐：

```par
checkpointFileIntervalTime = 1.0
checkpointFileIntervalStep = 20
plotFileNumber             = 0
```

**数值格式**：

| 类型 | 规则 | 示例 |
|------|------|------|
| bool | `.true.` / `.false.` | `useHydro = .true.` |
| str | 双引号包围 | `slopeLimiter = "minmod"` |
| float 0.0 | `"0.0"` | `xmin = 0.0` |
| float 整数值 | 保留小数位 | `rt_mgdFlCoef = 1.0` |
| float \|v\|≥10000 或 \|v\|≤0.01 | 科学计数法 | `dt_diff_factor = 1.0e+100` |
| 其余 float | repr 保留完整精度 | `sim_teleTarg = 290.11375` |

## 3. 生成器代码结构

### gen_par/generator.py

- `_format_value(value)` — 值格式化
- `_format_param_line(key, value, key_width)` — 单行格式化（含对齐）
- `_section_block(title, key_groups, inline_comments=...)` — 完整 section 生成
- `_section_header(title)` / `_subsection_header(title)` — 标题边框

### gen_newpara/generator.py

`_format_value` / `_section_header` / `_subsection_header` / `_format_param_line` 与 gen_par 同规则。
多区密度剖面生成详见 `flash/input_gen/gen_newpara/README.md` 与 `RP_Reference.md`。

### defaults.py

- 每个 PARAMS_XD 字典的**键顺序 = .par 输出顺序**
- 注释标记 section / subsection 边界；新增参数按功能放入对应 section

## 4. 新增参数流程

1. 在 `defaults.py` 对应 Section 位置添加键值对
2. 新功能模块 → 在 `gen_par/generator.py` 的 `_build_sections()` 中添加对应 section
3. 需要 inline comment → 在 `_section_block()` 配置 `inline_comments`

## 5. 与 example1d.par 的差异

生成的 .par 与官方 example1d.par 值等价，但做了规范化：数值格式统一（科学计数法/精度）、
section 边框宽度按标题动态计算、`###` 子段落分组、等号严格列对齐。

## 6. 护栏

- 运行时覆写用 `par_gen.set(key, value)`；数值注入用 `repr(rho)` 保持完整精度（`:2f` 会舍入）。
- par 会被部署脚本 `sed` 覆写（tmax/iProcs 常见）——**一切"实际生效值"只从 chk 的
  `real runtime parameters` 读**，不从 par 文本读（详见 skill `flash-scenario-setup` 判据 A）。
- 新场景 par 复核：`flash/input_gen/gen_checker/`（含 baseline_guards.txt 护栏基线）。
