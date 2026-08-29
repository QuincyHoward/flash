# gen_checker — 依赖检查器说明文档

**模块**: `flash/input_gen/gen_checker`
**维护**: PhySimX Team
**合并说明**: 本文档由 `GEN_CHECKER_GUIDE.md`（模块总览）与 `CHECK_RELATIONS.md`（关联检查设计与验证报告）合并而成（2026-08-28）。

## 概述

`gen_checker` 子包提供 FLASH 仿真依赖检查功能，分两个层级：

1. **存在性检查**（`checker.py` / `DependencyChecker`）：验证仿真目录是否包含 7 个关键文件；
2. **内在关联检查**（`check_relations.py` / `RelationChecker`）：在存在性之上校验 7 个关键文件之间的**内容一致性**，让矛盾在编译/运行前就暴露。

同时提供绘图工具，用于可视化脉冲、密度分布、光线追踪等。

**主要功能**:
1. 依赖检查（7个关键文件）及其内在关联检查
2. 脉冲绘图（pulse_plotter）
3. 密度绘图（density_plotter）
4. 光线绘图（ray_plotter）

## 架构

```
gen_checker/
├── checker.py            # 文件存在性检查 DependencyChecker
├── check_relations.py    # 内在关联检查主脚本 + CLI
├── relations/            # 规则子包（注册式规则引擎）
│   ├── __init__.py       # 导入所有规则模块，完成注册
│   ├── _core.py          # RelationResult / RelationContext / relation_rule / REGISTRY
│   ├── _parsers.py       # 公共解析工具（.par/Config/F90/脚本 提取）
│   ├── rules_reference.py  # A类 规则 1-3 文件级引用
│   ├── rules_parameter.py  # B类 规则 4-6 参数级一致性
│   ├── rules_dimension.py  # C类 规则 7-11 维度/光束/脉冲
│   └── rules_script.py     # D类 规则 12-14 脚本级装配
└── ploter/               # 绘图工具
```

**行数**：主脚本 `check_relations.py` 217 行（≪1000），规则拆分至 `relations/` 各模块，清晰可维护。

## 1. 依赖检查（存在性）

依赖检查器验证以下 7 个关键文件是否存在：

1. `.par` - 参数文件
2. `.cn4` - EOS表文件
3. `Config` - 配置文件
4. `Simulation_initBlock.F90` - 块初始化
5. `Simulation_init.F90` - 仿真初始化
6. `Simulation_data.F90` - 数据模块
7. `Makefile` - 编译配置

但"文件都在"并不代表"能跑通"。例如：`.par` 引用了某个 `.cn4` 但 `Config` 没在
`DATAFILES` 里声明、或 `Simulation_data.F90` 忘了声明 `Simulation_init.F90` 要用的
变量——这些都会在编译/运行时才暴露，排查成本高。这正是第 2 节内在关联检查的意义。

### 类: DependencyChecker

**位置**: `gen_checker/checker.py`

```python
from gen_checker import DependencyChecker

# 创建检查器
checker = DependencyChecker("path/to/Simulation/")

# 执行所有检查
results = checker.check_all()

# 打印摘要
print(checker.summary())

# 检查是否所有依赖都满足
if checker.all_passed():
    print("All dependencies satisfied!")
else:
    print("Missing files:")
    for result in results:
        if not result.status:
            print(f"  - {result.name}: {result.message}")
```

### 输出示例

```
=== FLASH Simulation Dependency Check ===
✓ .par file exists
✓ .cn4 EOS table exists
✓ Config file exists
✓ Simulation_initBlock.F90 exists
✓ Simulation_init.F90 exists
✓ Simulation_data.F90 exists
✓ Makefile exists
✗ FLASH binary not found (optional)

Passed: 7/8
```

## 2. 内在关联检查（内容一致性）

`check_relations.py` 是比"文件是否存在"更深一层的检查：它校验 **7 个关键文件之间的
内容一致性**。即使 7 个文件都存在，若它们彼此矛盾，FLASH 编译/运行时仍会失败。
内在关联按层级分为**文件级引用**、**参数级一致性**、**维度/光束级约束**、
**脚本级装配**四类，共 14 条规则。

### 2.1 A类 — 文件级引用关联（`rules_reference.py`，`.par` ↔ `Config` ↔ 磁盘 `.cn4`）

| id | 规则与判定 |
|----|-----------|
| `par_cn4_on_disk` | **`.par` 引用的 EOS/Opacity 表必须在磁盘存在**：`.par` 中 `eos_*TableFile`（如 `eos_targTableFile`）与 `op_*FileName`（如 `op_targFileName`）指定的 `*.cn4` 必须真实存在，否则运行时报错 `Eos_*: table file not found`。缺失 → FAIL |
| `par_cn4_in_config_datafiles` | **`.par` 引用的 `.cn4` 必须在 `Config` 的 `DATAFILES` 声明**：每个被引用的 `.cn4` 都应有一行 `DATAFILES *.cn4`，否则 `setup` 不会把它复制进对象目录。注意：`DATAFILES` 声明多于 `.par` 实际引用无害；`.par` 引用但声明缺失才是错误。引用未声明 → FAIL |
| `config_table_parameter` | **`Config` 的 `PARAMETER` 需定义 `.par` 用到的表绑定**：应有 `PARAMETER eos_*TableFile STRING "*.cn4"` / `PARAMETER op_*FileName STRING "*.cn4"` 之类定义，否则 `.par` 里 `set` 这些键会被 FLASH 当作未知参数告警/报错。`*TableFile`/`*FileName` 键取值应为 `.cn4/.ses` 文件名，误填模式名/类型名 → FAIL |

### 2.2 B类 — 参数级一致性关联（`rules_parameter.py`，`.par` ↔ `Config` ↔ `Simulation_*.F90`）

| id | 规则与判定 |
|----|-----------|
| `par_sim_in_config` | **`.par` 的 `sim_*` 运行时参数应在 `Config` 有对应 `PARAMETER` 定义**：FLASH 启动时用 `Config` 声明的参数白名单校验 `.par`，未声明的 `sim_*` 键触发 "Unknown runtime parameter" 告警；反向，`Config` 中 `PARAMETER` 未给默认值且 `.par` 未设置也会告警。白名单外 → FAIL |
| `simdata_init_consistency` | **`Simulation_data.F90` 声明的模块变量应与 `Simulation_init.F90` 的读取一一对应**：每条 `call RuntimeParameters_get('X', sim_X)` 左侧目标 `sim_X` 必须在 `Simulation_data.F90` 中以 `real/integer/..., save :: sim_X` 声明，否则编译报 "undefined variable"。未声明 → FAIL |
| `par_init_key_match` | **`.par` 的 `sim_*` 键应与 `Simulation_init.F90` 读取的键一致**：`RuntimeParameters_get('sim_rhoTarg', ...)` 读取的键名必须与 `.par` 中同名；名称不一致时参数取不到值（保持默认/报错）。`.par` 设了但 init 没读 → FAIL |

### 2.3 C类 — 维度 / 光束 / 脉冲级约束关联（`rules_dimension.py`，`.par` 内部 + `run_flash.sh`）

| id | 规则与判定 |
|----|-----------|
| `dimension_grid_vs_setup` | **维度一致性**：`.par` 网格维度应与 `setup` 维度 flag 一致——1D 有 `nblockx` 无 `nblocky/z`、`setup -1d`；2D 有 `nblockx/y`、`-2d`；3D 有 `nblockx/y/z`、`-3d`；`geometry`（cartesian/cylindrical/spherical）应与 `setup` 的 `+cartesian` 等一致。不一致 → FAIL |
| `beam_number_match` | **光束数目一致性**：`ed_numberOfBeams = N` 时应存在 `ed_lensX_1..N`、`ed_targetX_1..N`（及对应 `ed_pulseNumber_i`、`ed_wavelength_i`），多了或少了都会使激光模块行为异常。缺失 → FAIL |
| `pulse_beam_binding` | **脉冲-光束绑定**：`ed_pulseNumber_i` 引用的脉冲号应在 `1..ed_numberOfPulses` 范围内。越界 → FAIL |
| `pulse_sections_limit` | **脉冲组数上限**：若 `ed_numberOfSections_*`（或 `ed_time_*`/`ed_power_*` 组数）超过 20，`setup` 指令需加 `ed_maxPulseSections=<值>`，否则超出的功率段被截断。缺参数 → FAIL |
| `beam_in_domain` | **靶/透镜位置**：靶 `ed_targetX_i` 应在仿真域 `[xmin, xmax]` 内（透镜可域外），保证光线能进入计算域。目标在域外 → FAIL |

### 2.4 D类 — 脚本级装配关联（`rules_script.py`，`run_flash.sh` ↔ 其余文件）

| id | 规则与判定 |
|----|-----------|
| `par_file_in_script` | **`.par` 文件名与脚本一致**：`run_flash.sh` 的 `PAR_FILE` 应与磁盘 `.par` 名一致，否则 `mpirun ... -par_file` 找不到参数文件。不一致 → FAIL |
| `species_setup_match` | **`setup` 的 `species=` 与 `Config` 的 `SPECIES` 一致**：`species=cham,targ` 应与 `Config` 的 `SPECIES cham`/`SPECIES targ` 对应。未声明 → FAIL |
| `makefile_f90_match` | **`Makefile` 引用的 `.o` 与存在的 `Simulation_*.F90` 对应**：`Simulation += Simulation_data.o` 应能在源目录找到 `Simulation_data.F90`（`setup` 据此纳入编译）。缺文件 → FAIL |

### 2.5 使用方式

#### CLI

```bash
# 检查一个仿真目录
python check_relations.py <仿真目录> [--verbose]

# 只跑指定规则
python check_relations.py <目录> --rule par_cn4_on_disk

# 列出所有规则
python check_relations.py --rules

# 只输出结论行
python check_relations.py <目录> --summary-only
```

#### Python API

```python
from flash.input_gen.gen_checker import RelationChecker

rc = RelationChecker("/path/to/sim_dir")
results = rc.run_all()        # List[RelationResult]
print(rc.summary())           # 文本报告
if rc.all_passed():           # 是否无失败
    print("内在关联全部一致")
else:
    for r in rc.failed():
        print(r.rule_id, r.message)
```

### 2.6 场景集成（ch_center）

`flash/scenarios/center_evolution/ch_center/laserslab1d_local_custom.py` 的步骤 1
已集成关联检查：文件存在检查 → 内在关联检查 → WSL/HPC 运行。若关联不一致，
脚本打印 `[FAIL]` 明细并 `return False` 停止，避免带病编译/运行。

**运行日志（磨合验证）**：
```
[-] 进行文件内在关联检查 (check_relations)...
[OK] 内在关联检查通过（14 条规则全部通过/跳过）
```

### 2.7 验证结果

对 `ch_center/flash_input` 实测：**通过 13 / 失败 0 / 跳过 1**（`species_setup_match`
因该场景 `Config` 无 `SPECIES` 声明而跳过）。

构造性错误检测（人为破坏后）均正确 FAIL：

| 注入错误 | 命中规则 | 结果 |
|---------|---------|------|
| `Config` 删除 `DATAFILES` | `par_cn4_in_config_datafiles` | FAIL，exit=1 |
| `.par` 引用不存在的 `NOPE.cn4` | `par_cn4_on_disk` | FAIL |
| `ed_numberOfBeams=3` 但只有 2 束 | `beam_number_match` | FAIL |
| 脚本 `PAR_FILE` 改名 | `par_file_in_script` | FAIL |

### 2.8 如何扩展自定义关联

采用**注册式规则引擎**，新增关联无需改主流程：

1. 在 `relations/` 新增/追加规则函数，用 `@relation_rule(id, name)` 装饰：

   ```python
   @relation_rule(id="my_rule", name="我的自定义关联")
   def my_rule(ctx: RelationContext) -> RelationResult:
       ...
       return RelationResult(rule_id="my_rule", name="我的自定义关联",
                             status=True, message="...", details={...})
   ```

2. 在 `relations/__init__.py` 末尾 `from . import my_module`（若新增模块）即可。
3. `run_all()` 自动遍历 `REGISTRY`，新规则自动纳入，无需改 `check_relations.py`。

**共享缓存**：规则之间共享的解析结果（已解析的 `.par` 字典、`Config` 行集等）
缓存在 `RelationContext`（`_core.py`）中，避免重复解析，规则间可安全复用。

## 3. 可选检查

- FLASH二进制是否存在
- Python依赖（numpy, matplotlib, h5py）
- MPI是否可用

## 4. 绘图工具

### pulse_plotter

绘制激光脉冲时间-功率曲线。

```python
from gen_checker.ploter import pulse_plotter

pulse_plotter.plot(
    par_file="path/to/flash.par",
    output_file="pulse_plot.png"
)
```

### density_plotter

绘制密度分布图。

```python
from gen_checker.ploter import density_plotter

density_plotter.plot(
    hdf5_file="path/to/plotfile.h5",
    output_file="density_plot.png"
)
```

### ray_plotter

绘制光线追踪图。

```python
from gen_checker.ploter import ray_plotter

ray_plotter.plot(
    par_file="path/to/flash.par",
    output_file="ray_plot.png"
)
```

## 5. 集成到仿真流程

```python
from gen_checker import DependencyChecker

# 在编译前检查依赖
checker = DependencyChecker("path/to/Simulation/")
if not checker.all_passed():
    print("Cannot compile: missing dependencies")
    print(checker.summary())
    exit(1)

# 编译...
# 运行...

# 运行后绘图
from gen_checker.ploter import pulse_plotter, density_plotter
pulse_plotter.plot("flash.par", "pulse.png")
density_plotter.plot("plotfile.h5", "density.png")
```

## 6. 相关文档

- 文件存在性检查：`checker.py` / `DependencyChecker`
- 内在关联检查：`check_relations.py` / `RelationChecker`（规则实现见 `relations/` 各模块文件头）

---

**文档版本**: 2.0（合并版）
**最后更新**: 2026-08-28
**维护**: PhySimX Team
