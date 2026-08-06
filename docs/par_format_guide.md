# .par 参数文件排版规范

## 概述

本文档定义 PhySimX FLASH 仿真中 `.par` 参数文件的排版规则。
所有通过 `input_gen/gen_par` 和 `input_gen/gen_newpara` 生成的 `.par` 文件必须遵循此规范。

**权威参考**: `input_gen/gen_par/defaults.py` — 所有参数默认值的最终来源。
**模板参考**: `scenarios/flash_demo/LaserSlab/LaserSlabca1d/example1d.par` — 排版样式参考。

---

## 1. Section 顺序（固定）

生成 `.par` 时，section 必须严格按照以下顺序排列：

| # | Section 标题 | 包含参数前缀 | 
|---|-------------|-------------|
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

**MESH PARAMETERS 必须放在最后**，section 10 是固定位置。

---

## 2. Section 标题格式

```par
##########################
#                        #
#     I/O PARAMETERS     #
#                        #
##########################
```

规则：
- 边框宽度 = `len(标题) + 12`
- 标题居中，两侧各 5 个空格
- 上下各有一行空白的 `#  #`

---

## 3. 子段落注释（Subsection）

```par
### Checkpoint Options ###
### Plot Options ###
### Restart Options ###
```

用于在 section 内部对参数进行逻辑分组。格式：
```
### 标题 ###
```

---

## 4. 键值对对齐（Column Alignment）

### 4.1 等号 `=` 对齐

同一段落内，所有 `=` 按**最长 key** 左对齐：

```par
checkpointFileIntervalTime = 1.0
checkpointFileIntervalStep = 20
plotFileNumber             = 0
plotFileIntervalStep       = 10
```

对齐规则：
- 计算当前段落内最长 key 的字符数 `max_key_len`
- 每行格式为 `{key:<{max_key_len}} = {value}`

### 4.2 数值右端对齐（遵循）

数值应当根据其长度自然右端对齐，通过左侧 key 和 `= ` 的固定宽度实现。

---

## 5. 数值格式

| 类型 | 格式规则 | 示例 |
|------|---------|------|
| bool | `.true.` / `.false.` | `useHydro = .true.` |
| str | 双引号包围 | `slopeLimiter = "minmod"` |
| float 0.0 | `"0.0"` | `xmin = 0.0` |
| float 整数值 | 保留小数位 | `rt_mgdFlCoef = 1.0` |
| float \|v\|\>=10000 或 \|v\|\<=0.01 | 科学计数法 | `dt_diff_factor = 1.0e+100` |
| 其余 float | repr 保留完整精度 | `sim_teleTarg = 290.11375` |

---

## 6. Section Header # 边框对齐

所有 section header 的 `#` 边框必须对齐：
- 顶部 border: `#` 重复 width 次
- 空白行: `#` + width-2 个空格 + `#`
- 标题行: `#     {标题}     #`（两侧各 5 空格）

---

## 7. 代码实现

### 7.1 `gen_par/generator.py`

核心格式化方法：
- `_format_value(value)` — 值格式化规则
- `_format_param_line(key, value, key_width)` — 单行格式化（含对齐）
- `_section_block(title, key_groups)` — 完整 section 生成
- `_section_header(title)` — section 标题边框
- `_subsection_header(title)` — ### 子标题 ###

### 7.2 `gen_newpara/generator.py`

- `_format_value(value)` — 同 gen_par 规则
- `_section_header(title)` — 同 gen_par 规则
- `_subsection_header(title)` — 同 gen_par 规则
- `_format_param_line(key, value, key_width)` — 同 gen_par 规则

### 7.3 `defaults.py`

- 每个 PARAMS_XD 字典的键顺序 = .par 输出顺序
- 注释标记 section 和 subsection 边界
- 新增参数按功能放入对应 section

---

## 8. 新增参数流程

1. 在 `defaults.py` 对应 Section 位置添加键值对
2. 如果参数属于新功能模块，在 `gen_par/generator.py` 的 `_build_sections()` 中添加对应 section
3. 如果需要在 par 中有 inline comment，在 `_section_block()` 中配置 `inline_comments` 参数

---

## 9. 与 example1d.par 的差异说明

生成的 `.par` 与 `example1d.par` 在值上是等价的，但在以下方面做了规范化：

1. **数值格式统一**：浮点数使用一致的格式化规则（科学计数法、精度等）
2. **Section 结构标准化**：所有 section 的边框宽度按标题长度动态计算
3. **子段落分组**：更细致的 `###` 子段落注释，提升可读性
4. **对齐严格化**：同一段落内 `=` 号保持严格列对齐

---

*最后更新: 2026-06-30*
*维护者: PhySimX Team*
