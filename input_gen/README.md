# input_gen — FLASH 仿真输入文件生成器总览

**版本**: 2.0  
**最后更新**: 2026-07-04  
**维护**: PhySimX Team

---

## 目录

1. [概述](#概述)
2. [架构图](#架构图)
3. [子模块速查表](#子模块速查表)
4. [一键生成接口](#一键生成接口)
5. [典型工作流](#典型工作流)
6. [子模块详细说明](#子模块详细说明)
7. [测试覆盖](#测试覆盖)
8. [常见问题](#常见问题)

---

## 概述

`input_gen` 是 PhySimX 项目中用于 **自动生成 FLASH 4.8 仿真输入文件** 的核心模块。它包含所有 `gen_*` 子包，每个子包负责生成一种类型的 FLASH 输入文件。

**设计原则**:
- 所有 `gen_*` 子包完全自包含，不依赖外部模板文件
- 默认参数从 FLASH 示例文件中提取，硬编码到生成器中
- 支持 1D/2D/3D 维度自动匹配

**输出文件**: FLASH 仿真所需的 8 个关键文件：
1. `Config` - 仿真配置文件
2. `*.par` - 运行时参数文件
3. `Makefile` - 编译配置文件
4. `Simulation_data.F90` - 参数数据模块
5. `Simulation_init.F90` - 仿真初始化程序
6. `Simulation_initBlock.F90` - 块初始化程序
7. `*.cn4` - EOS 表文件
8. 运行脚本 (`run_flash.sh` / `run_flash.bat` / `submit_flash.slurm`)

---

## 架构图

```
input_gen/
├── __init__.py              # 一键生成接口 create_input_files()
│
├── gen_par/                # .par 参数文件生成器
├── gen_config/             # Config 文件生成器
├── gen_makefile/          # Makefile 生成器
├── gen_sim_data/          # Simulation_data.F90 生成器
├── gen_sim_init/          # Simulation_init.F90 生成器
├── gen_sim_initblock/     # Simulation_initBlock.F90 生成器
├── gen_eos_op/           # EOS/Opacity 数据文件管理器
├── gen_shell_script/      # 运行脚本生成器
├── gen_checker/           # 依赖检查器 + 绘图工具
├── gen_Grid_markRefineDerefine/  # AMR 网格细化参考示例
├── gen_otherf90s/        # 其他 Fortran 文件参考库
├── gen_newpara/           # 多区密度剖面生成器
├── gen_f90/              # (预留)
│
└── test/                 # 测试套件
```

**生成流程**:
```
create_input_files()
    │
    ├─ gen_par          → .par 文件
    ├─ gen_config       → Config 文件
    ├─ gen_makefile     → Makefile
    ├─ gen_sim_data     → Simulation_data.F90
    ├─ gen_sim_init     → Simulation_init.F90
    ├─ gen_sim_initblock→ Simulation_initBlock.F90
    ├─ gen_eos_op       → 复制 .cn4 文件
    └─ gen_shell_script → 运行脚本
```

---

## 子模块速查表

| 子模块 | 生成器类 | 输出文件 | 状态 | 说明 |
|--------|----------|---------|------|------|
| `gen_par` | `ParGeneratorExtended` | `*.par` | ✅ 完整 | 支持 1D/2D/3D，激光脉冲/光束配置 |
| `gen_config` | `ConfigGenerator` | `Config` | ✅ 完整 | 硬编码 LaserSlab 模板 |
| `gen_makefile` | `MakefileGenerator` | `Makefile` | ✅ 完整 | 简单硬编码 |
| `gen_sim_data` | `SimDataGenerator` | `Simulation_data.F90` | ✅ 完整 | 硬编码 LaserSlab 模板 |
| `gen_sim_init` | `SimInitGenerator` | `Simulation_init.F90` | ✅ 完整 | 硬编码 LaserSlab 模板 |
| `gen_sim_initblock` | `BlockGenerator` + `GridBuilder` | `Simulation_initBlock.F90` | ✅ 完整 | 支持动态区域构建 |
| `gen_eos_op` | `EOSOpacityGenerator` | `.cn4` 文件复制 | ✅ 完整 | 内置材料数据库 |
| `gen_shell_script` | `ShellScriptGenerator` | `run_flash.*` | ✅ 完整 | 资源配置驱动 |
| `gen_checker` | `DependencyChecker` | (无生成) | ✅ 完整 | 依赖检查 + 绘图 |
| `gen_newpara` | `NewParaGenerator` | 多区剖面文件 | ✅ 完整 | 5 种密度剖面 |
| `gen_Grid_markRefineDerefine` | (无) | (手动复制) | ⚠️ 参考 | 277 个参考文件 |
| `gen_otherf90s` | (无) | (手动复制) | ⚠️ 参考 | AMR 细化条件参考 |
| `gen_f90` | (无) | (无) | ⚠️ 预留 | 空模块 |

---

## 一键生成接口

### `create_input_files()`

`input_gen/__init__.py` 提供了统一的一键生成函数：

```python
from flash.input_gen import create_input_files

result = create_input_files(
    output_dir="./my_simulation",
    dimension=1,
    simulation_name="LaserSlab",
    target_material="aluminum",
    chamber_gas="helium",
    n_beams=1,
    par_filename="laserslab.par",
    generate_scripts=True,
    copy_eos_files=True,
    setup_cmd=None,
    sim_user_dir="QC",
    platform="local",
)

# result 包含生成文件的路径
print(result)
# {
#   "par": "./my_simulation/laserslab.par",
#   "config": "./my_simulation/Config",
#   "makefile": "./my_simulation/Makefile",
#   ...
# }
```

---

## 典型工作流

### 工作流 1: 生成 1D 激光-等离子体仿真

```python
from flash.input_gen import create_input_files

# 一键生成所有文件
result = create_input_files(
    output_dir="./flash_input_1d",
    dimension=1,
    simulation_name="LaserSlab",
    target_material="aluminum",
    chamber_gas="helium",
    platform="local",
)

# 检查生成的文件
from flash.input_gen.gen_checker import DependencyChecker

checker = DependencyChecker("./flash_input_1d")
print(checker.summary())
```

### 工作流 2: 自定义 .par 参数

```python
from flash.input_gen.gen_par import ParGeneratorExtended
from flash.input_gen.gen_shell_script import ShellScriptGenerator

# 创建生成器
gen = ParGeneratorExtended(dimension=1)

# 设置激光脉冲
import numpy as np
times = [0.0, 0.1e-9, 1.0e-9, 1.1e-9]
powers = [0.0, 1.0e9, 1.0e9, 0.0]
gen.set_pulse(times, powers)

# 设置光束
from flash.input_gen.gen_par.generator import BeamConfig
beam = BeamConfig(
    beam_id=1,
    lens_x=-0.1,
    target_x=0.014,
    pulse_number=1,
    wavelength=1.053,
)
gen.set_beams([beam])

# 保存
gen.save("./flash_input_1d/laserslab.par")
```

### 工作流 3: 多区密度剖面

```python
from flash.input_gen.gen_newpara import NewParaGenerator

# 创建生成器
gen = NewParaGenerator()

# 添加区域（常量 → 指数衰减 → 高斯）
gen.add_zone(height=0.004, profile=0, name="constant")
gen.add_zone(height=0.004, profile=1, p1=0.001, name="exp_decay")
gen.add_zone(height=0.004, profile=4, p1=0.5, p2=0.25, name="gaussian")

# 生成所有文件
files = gen.generate_all("./flash_input_multizone")
print(files)
```

---

## 子模块详细说明

### 1. gen_par — .par 参数文件生成器

**生成器**: `ParGeneratorExtended`

**关键功能**:
- 维度感知 (1D/2D/3D 自动匹配模板)
- 激光脉冲配置 (`set_pulse()`, `set_pulses()`)
- 激光光束配置 (`set_beams()`, `BeamConfig`)
- 材料设置 (`set_material()`, `Material`, `MaterialDatabase`)
- 域和网格配置 (`set_domain()`)
- 时间步长配置 (`set_time()`)

**默认参数来源**: `gen_par/defaults.py`
- `PARAMS_1D` — 135 个参数
- `PARAMS_2D` — 163 个参数
- `PARAMS_3D` — 186 个参数

**参考示例**: `gen_par/refs/` (750+ `.par` 文件)

**文档**: `gen_par/GEN_PAR_GUIDE.md`

---

### 2. gen_config — Config 文件生成器

**生成器**: `ConfigGenerator`

**关键功能**:
- 生成 FLASH Config 文件
- 定义 REQUIRES/REQUESTS 物理模块
- 定义 PARAMETER 运行时参数
- 定义 VARIABLE 额外变量
- 定义 DATAFILES 数据文件

**默认模板**: 基于 `SimulationMain/LaserSlab/Config`

**文档**: `gen_config/GEN_CONFIG_GUIDE.md`

---

### 3. gen_makefile — Makefile 生成器

**生成器**: `MakefileGenerator`

**关键功能**:
- 生成 FLASH Makefile
- 指定额外编译对象 (`Simulation_data.o`, `Simulation_init.o`, ...)

**当前状态**: 非常简单，只生成基本 Makefile 内容

**文档**: `gen_makefile/GEN_MAKEFILE_GUIDE.md`

---

### 4. gen_sim_data — Simulation_data.F90 生成器

**生成器**: `SimDataGenerator`

**关键功能**:
- 生成 `Simulation_data.F90` 模块
- 定义和存储仿真运行时参数变量
- 变量必须以 `sim_` 开头，使用 `save` 属性

**默认模板**: 基于 `LaserSlab1d/Simulation_data.F90`

**文档**: `gen_sim_data/GEN_SIM_DATA_GUIDE.md`

---

### 5. gen_sim_init — Simulation_init.F90 生成器

**生成器**: `SimInitGenerator`

**关键功能**:
- 生成 `Simulation_init.F90` 子程序
- 从 `.par` 文件读取运行时参数
- 存储在 `Simulation_data` 模块变量中

**默认模板**: 基于 `LaserSlab/Simulation_init.F90`

**文档**: `gen_sim_init/GEN_SIM_INIT_GUIDE.md`

---

### 6. gen_sim_initblock — Simulation_initBlock.F90 生成器

**生成器**: `BlockGenerator` + `GridBuilder`

**关键功能**:
- 生成 `Simulation_initBlock.F90` 子程序
- 使用 `GridBuilder` 构建仿真网格区域
- 支持 `Region` 对象定义不同区域（靶、腔室、真空等）
- 自动生成 Fortran 代码

**核心类**:
- `GridBuilder` — 构建网格区域
- `Region` — 表示仿真域中的一个区域
- `BlockGenerator` — 生成 Fortran 代码

**预设配置**: `from_laserslab_1d()` 等

**文档**: `gen_sim_initblock/GEN_SIM_INITBLOCK_GUIDE.md`

---

### 7. gen_eos_op — EOS/Opacity 数据文件管理器

**生成器**: `EOSOpacityGenerator`

**关键功能**:
- 管理 EOS 和不透明度数据文件
- 内置常用材料映射（铝、氦、聚苯乙烯等）
- 复制 EOS 文件到目标目录
- 列出所有可用材料

**数据库目录**: `gen_eos_op/eos_op_data/`

**支持格式**: ionmix4 (`.cn4`), sesame (`.ses`)

**文档**: `gen_eos_op/GEN_EOS_OP_GUIDE.md`

---

### 8. gen_shell_script — 运行脚本生成器

**生成器**: `ShellScriptGenerator`

**关键功能**:
- 生成运行脚本（shell/bat/slurm）
- 支持本地和 HPC 环境
- 资源配置驱动（`resource_config.json`）

**输出文件**:
- `run_flash.bat` — Windows 批处理脚本
- `run_flash.sh` — WSL/Linux shell 脚本
- `submit_flash.sh` — SLURM 提交脚本

**文档**: `gen_shell_script/GEN_SHELL_SCRIPT_GUIDE.md`

---

### 9. gen_checker — 依赖检查器

**核心类**: `DependencyChecker`

**关键功能**:
1. **依赖检查** — 验证 7 个关键文件是否存在
2. **脉冲绘图** — `pulse_plotter`
3. **密度绘图** — `density_plotter`
4. **光线绘图** — `ray_plotter`

**检查项**:
1. `.par` - 参数文件
2. `.cn4` - EOS 表文件
3. `Config` - 配置文件
4. `Simulation_initBlock.F90` - 块初始化
5. `Simulation_init.F90` - 仿真初始化
6. `Simulation_data.F90` - 数据模块
7. `Makefile` - 编译配置

**文档**: `gen_checker/GEN_CHECKER_GUIDE.md`

---

### 10. gen_newpara — 多区密度剖面生成器

**生成器**: `NewParaGenerator`

**关键功能**:
- 新参数 5 步流程封装
- 增量边界区域划分
- 5 种密度剖面（常量/指数衰减/指数增长/线性/高斯）
- 多区单仿真混合

**核心类**:
- `NewParaGenerator` — 主生成器
- `ZoneConfig` — 区域配置

**文档**: `gen_newpara/README.md`

---

### 11. gen_Grid_markRefineDerefine — AMR 网格细化参考

**当前状态**: 无自动生成器，需手动编写或从 `refs/` 复制

**参考文件**: `refs/Grid_markRefineDerefine.F90` 及多个变体

**关键要点**:
- AMR 细化变量配置规则
- 1D/2D/3D 坐标获取差异
- 典型细化逻辑（LaserSlab 1D）

**文档**: `gen_Grid_markRefineDerefine/GEN_GRID_GUIDE.md`

---

### 12. gen_otherf90s — 其他 Fortran 文件参考库

**当前状态**: 无生成器，仅参考文件库

**文件数量**: 277 个 Fortran 文件 (`.F90`)

**分类目录**:
- `custom/` — 自定义 prolongation 文件
- `gr/` — 引力相对论相关文件
- `grid_re_de/` — 网格细化参考
- ...

**使用场景**:
1. 手动复制参考文件
2. 学习 FLASH 模块实现
3. 作为生成器模板（未来扩展）

**文档**: `gen_otherf90s/GEN_OTHER_F90S_GUIDE.md`

---

## 测试覆盖

`input_gen/test/` 目录包含完整的测试套件：

| 测试文件 | 测试对象 | 状态 |
|---------|---------|------|
| `test_gen_par.py` | `gen_par` | ✅ 完整 |
| `test_gen_config.py` | `gen_config` | ✅ 完整 |
| `test_gen_makefile.py` | `gen_makefile` | ✅ 完整 |
| `test_gen_sim_data.py` | `gen_sim_data` | ✅ 完整 |
| `test_gen_sim_init.py` | `gen_sim_init` | ✅ 完整 |
| `test_gen_sim_initblock.py` | `gen_sim_initblock` | ✅ 完整 |
| `test_gen_shell_script.py` | `gen_shell_script` | ✅ 完整 |
| `test_gen_checker.py` | `gen_checker` | ✅ 完整 |
| `test_gen_eos_op.py` | `gen_eos_op` | ✅ 完整 |
| `test_demo_scripts_compat.py` | 兼容性 | ✅ 完整 |

**重要编码规范**:
- 所有 `read_text()` / `write_text()` 必须显式指定 `encoding="utf-8"`，避免 Windows GBK 默认解码报错
- 所有生成的脚本自动使用 Unix (LF) 换行符（`write_text` 默认 LF，无需特殊处理）
- `.gitattributes` 已强制 `* text=auto eol=lf`，提交时自动归一化

**运行测试**:
```bash
cd /path/to/PhySimX
python -m pytest physimx_sim/src/physimx_sim/flash/input_gen/test/
```

---

## 常见问题

### 1. 如何添加新的仿真类型（非 LaserSlab）？

**答**: 当前大多数生成器使用硬编码的 LaserSlab 模板。如需其他类型（如 Sod、Sedov），可以：

1. 生成默认文件
2. 手动修改以匹配目标仿真的需求
3. 或将需要的示例复制到 `refs/` 目录，并扩展生成器以支持多个模板

### 2. 如何验证生成的文件是否正确？

**答**: 使用 `gen_checker` 的依赖检查功能：

```python
from flash.input_gen.gen_checker import DependencyChecker

checker = DependencyChecker("./my_simulation")
print(checker.summary())
```

### 3. 维度匹配规则是什么？

**答**: 生成器根据仿真维度自动选择默认参数集：

| 维度 | 模板名称 | 说明 |
|------|---------|------|
| 1D | `example1d.par` | 一维仿真，只需 `nblockx` |
| 2D | `example.par` | 二维仿真，需要 `nblockx`, `nblocky` |
| 3D | `example3d.par` | 三维仿真，需要 `nblockx`, `nblocky`, `nblockz` |

### 4. 如何扩展生成器支持多个模板？

**答**: 可以在生成器中添加模板选择功能，例如：

```python
class ConfigGenerator:
    def __init__(self, template="LaserSlab"):
        self.templates = {
            "LaserSlab": DEFAULT_CONFIG,
            "Sod": self._load_template("Sod"),
            "Sedov": self._load_template("Sedov"),
        }
        self.content = self.templates.get(template, DEFAULT_CONFIG)
```

### 5. FLASH 新参数添加的 5 步流程是什么？

**答**: 参见 `gen_newpara/README.md`：

```
Config → Simulation_data.F90 → Simulation_init.F90 → Simulation_initBlock.F90 → .par 文件
```

1. **Config** — 用 `PARAMETER` 行注册参数
2. **Simulation_data.F90** — 声明 Fortran 变量
3. **Simulation_init.F90** — 用 `RuntimeParameters_get` 读取
4. **Simulation_initBlock.F90** — 在初始条件中使用
5. **.par 文件** — 设置参数初始值

---

## 参考资料

1. FLASH User Guide — Chapter 4: Simulation Configuration
2. FLASH User Guide — Chapter 5: Runtime Parameters
3. FLASH Source Code — `source/Simulation/SimulationMain/*/`
4. PhySimX Documentation — `input_gen/*/GEN_*_GUIDE.md`

---

**文档版本**: 2.0  
**最后更新**: 2026-07-04  
**维护**: PhySimX Team
