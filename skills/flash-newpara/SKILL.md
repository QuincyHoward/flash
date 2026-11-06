---
name: flash-newpara
description: FLASH 新参数/多区密度剖面生成器（gen_newpara）：新增 sim_* 运行时参数的 5 步流程、增量边界多区划分、5 种密度剖面（常量/指数衰减/指数增长/线性/高斯）、物种名 4 字符约束。创建全新仿真需要自定义参数、多区（>2 物质）密度、渐变剖面时必须优先使用。触发词：新参数、sim_ 参数注册、多区密度、密度剖面、gen_newpara、NewParaGenerator、增量边界、渐变剖面、物种名截断。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 来源：用户级 flash-newpara 技能吸收（API 已按本仓 gen_newpara 现行代码校正）

# 新变量/多区密度剖面生成（flash-newpara）

## 适用场景

- 添加新的 `sim_*` 运行时参数（非 defaults.py 已有参数）
- 多区域（>2 物质）密度划分、增量边界（ReDo 风格）
- 渐变密度剖面（5 种类型）

只改已有参数的值 → 用 `flash-input-gen` + `defaults.py`，不需要本技能。

## 前置条件

- `flash/input_gen/gen_newpara/`（自包含，依赖 gen_config/gen_sim_data/gen_sim_init/gen_sim_initblock）
- 权威文档：`flash/input_gen/gen_newpara/README.md`（5 步流程详解）、`flash/input_gen/gen_newpara/RP_Reference.md`（FLASH 4.8 内置运行时参数）

## 操作步骤

### 1. NewParaGenerator 现行 API

```python
from flash.input_gen.gen_newpara import NewParaGenerator

gen = NewParaGenerator()
gen.vacuum_height = 0.005        # 真空/腔室区厚度 [cm]
gen.base_density = 2.7           # TARG 物质基准密度 [g/cm^3]
gen.chamber_density = 1e-6
gen.species_list = ["cham", "targ"]

# 逐个添加区域（增量边界自动生成 sim_zone{i}Height 系列）
gen.add_zone(height=0.004, profile=1, p1=5.0e-4, name="指数衰减靶层")
gen.add_zone(height=0.002, profile=0, name="常数第二靶层")

gen.validate()                   # 校验（错误列表）
result = gen.generate_all("./sim_input")   # 一键生成 par/Config/F90 全套
# 或分步：gen.generate_config() / generate_sim_data() / generate_sim_init()
#         / generate_init_block() / generate_par_content()
```

⚠️ 旧技能中的 `gen.set()` / `gen.set_profile()` / `gen.gen_par()` 方法**已不存在**；
现行接口为属性赋值 + `add_zone()` + `generate_all()`，以 `gen_newpara/generator.py` 为准。

### 2. 新参数 5 步流程（手工添加时）

| # | 文件 | 操作 | 示例 |
|---|------|------|------|
| 1 | `Config` | `D` 描述行 + `PARAMETER` 声明 | `PARAMETER sim_polyHeight REAL 0.005` |
| 2 | `Simulation_data.F90` | 声明 Fortran 变量 | `real, save :: sim_polyHeight` |
| 3 | `Simulation_init.F90` | 读取 | `call RuntimeParameters_get('sim_polyHeight', sim_polyHeight)` |
| 4 | `Simulation_initBlock.F90` | 区域逻辑中使用 | `bound3 = bound2 + sim_polyHeight` |
| 5 | `.par` | 初始值 | `sim_polyHeight = 20.0e-04` |

TYPE 对照：REAL→real 模块变量；INTEGER→integer；BOOLEAN→logical；STRING→无需声明。

### 3. 5 种密度剖面（`PROFILE_TYPES`）

| 类型 | 名称 | 公式 | 参数 |
|------|------|------|------|
| 0 | constant | `ρ = ρ₀` | 无 |
| 1 | exp_decay | `ρ = ρ₀·exp(-x_local/p1)` | p1 = e-folding 长度 (cm)，须 >0 |
| 2 | exp_growth | `ρ = ρ₀·exp(+x_local/p1)` | p1 须 >0 |
| 3 | linear | `ρ = ρ₀·(p1 + p2·x_local/w)` | p1=截距, p2=斜率 |
| 4 | gaussian | `ρ = ρ₀·exp(-0.5·((x_local-p1·w)/(p2·w))²)` | p1=中心, p2=宽度，须 >0 |

`x_local` = 距区域左边界距离，`w` = 区域宽度。5 种类型已经 WSL 实测全扫描验证（exp_decay R²=0.9939；原 `test/newpara/flash_profile/` 扫描工件已清理，历史记录见 gen_newpara/README.md）。

## 护栏与铁律

1. **物种名 ≤4 字符**（FLASH 静默截断）：`cham/targ/poly/samp/shld` ✅；`targ2` → 截断为 `targ` 冲突 ❌
2. **Config/F90 必须在已验证 LaserSlab 模板上微调**，禁止 Python 字符串模板从零生成；新材料必须同时加 DATAFILES 声明，否则 setup 不复制 .cn4
3. 漏掉 `RuntimeParameters_get` → 参数**静默无效**（不报错）；Config 类型与 F90 声明不一致 → 编译错误
4. 绘图标签全英文
5. 生成后必须 setup → make → run 实际验证（同 flash-input-gen 护栏 5）

## 常见坑

- 增量边界硬编码固定区间 → 改用 `bound{i} = bound{i-1} + sim_zone{i}Height` 累积式
- 剖面参数漏传导致用 `PROFILE_DEFAULTS` 静默兜底，仿真前 `validate` 一下
- `.par` 键顺序 = defaults.py 键顺序；新参数按功能放入对应 Section

## 关联资源

- `flash/input_gen/gen_newpara/README.md` / `RP_Reference.md`（权威详解）
- `test/newpara/`（多区控制完整 F90 示例）、`test/newpara/flash_profile/`（剖面全扫描测试）
- `flash-input-gen`（标准 8 文件流程）、`flash-par-gen`（.par 排版规范）
