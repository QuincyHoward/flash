# gen_checker — 依赖检查器说明文档

## 概述

`gen_checker` 子包提供 FLASH 仿真依赖检查功能，验证仿真目录是否包含所有必需的文件。同时提供绘图工具，用于可视化脉冲、密度分布、光线追踪等。

**主要功能**:
1. 依赖检查（7个关键文件）及其内在关联代码检查
2. 脉冲绘图（pulse_plotter）
3. 密度绘图（density_plotter）
4. 光线绘图（ray_plotter）

## 依赖检查

### 检查项

依赖检查器验证以下7个关键文件是否存在：

1. `.par` - 参数文件
2. `.cn4` - EOS表文件
3. `Config` - 配置文件
4. `Simulation_initBlock.F90` - 块初始化
5. `Simulation_init.F90` - 仿真初始化
6. `Simulation_data.F90` - 数据模块
7. `Makefile` - 编译配置


### 检查项的内在关联

`check_relations.py` 是比"文件是否存在"更深一层的检查：它校验 **7 个关键文件之间的内容一致性**。
即使 7 个文件都存在，若它们彼此矛盾，FLASH 编译/运行时仍会失败。内在关联按层级分为
**文件级引用**、**参数级一致性**、**维度/光束级约束**、**脚本级装配**四类。

#### A. 文件级引用关联（`.par` ↔ `Config` ↔ 磁盘 `.cn4`）

1. **`.par` 引用的 EOS/Opacity 表必须在磁盘存在**：
   - `.par` 中 `eos_*TableFile`（如 `eos_targTableFile`）与 `op_*FileName`
     （如 `op_targFileName`）指定的 `*.cn4`，必须在仿真目录中真实存在，
     否则运行时报错 `Eos_*: table file not found`。
2. **`.par` 引用的 `.cn4` 必须在 `Config` 的 `DATAFILES` 声明**：
   - 每个被 `.par` 引用的 `.cn4` 都应在 `Config` 中有一行 `DATAFILES *.cn4`，
     否则 `setup` 不会把它复制进对象目录，运行时报 `eos files not found`。
   - 注意：`DATAFILES` 中声明的文件可以多于 `.par` 实际引用（多余无害）；
     `.par` 引用但 `DATAFILES` 缺失才是错误。
3. **`Config` 的 `PARAMETER` 需定义 `.par` 用到的表绑定**：
   - `Config` 中应有类似
     ```text
     PARAMETER eos_*TableFile STRING "*.cn4"
     PARAMETER op_*FileName  STRING "*.cn4"
     ```
     的运行时参数，否则 `.par` 里 `set` 这些键会被 FLASH 当作未知参数告警/报错。

#### B. 参数级一致性关联（`.par` ↔ `Config` ↔ `Simulation_*.F90`）

4. **`.par` 中的 `sim_*` 运行时参数应在 `Config` 有对应 `PARAMETER` 定义**：
   - FLASH 启动时用 `Config` 中声明的参数白名单校验 `.par`。`.par` 里出现
     `Config` 未声明的 `sim_*` 键，会触发 "Unknown runtime parameter" 告警。
   - 反向：`Config` 中 `PARAMETER` 若未给出默认值且 `.par` 未设置，也会告警。
5. **`Simulation_data.F90` 声明的模块变量应与 `Simulation_init.F90` 的读取一一对应**：
   - `Simulation_init.F90` 中每一条 `call RuntimeParameters_get('X', sim_X)`
     左侧目标 `sim_X` 必须在 `Simulation_data.F90` 中以 `real/integer/... , save :: sim_X`
     声明；否则编译报 "undefined variable"。
6. **`.par` 的 `sim_*` 键应与 `Simulation_init.F90` 读取的键一致**：
   - `RuntimeParameters_get('sim_rhoTarg', ...)` 读取的键名必须与 `.par` 中
     出现的 `sim_rhoTarg` 同名。名称不一致时参数取不到值（保持默认/报错）。

#### C. 维度 / 光束 / 脉冲级约束关联（`.par` 内部 + `run_flash.sh`）

7. **维度一致性**：`.par` 中的网格维度参数应与 `setup` 指令的维度 flag 一致：
   - 1D：有 `nblockx`，无 `nblocky`/`nblockz`；`setup` 用 `-1d`。
   - 2D：有 `nblockx`、`nblocky`；`setup` 用 `-2d`。
   - 3D：有 `nblockx`、`nblocky`、`nblockz`；`setup` 用 `-3d`。
   - 几何：`.par` 的 `geometry`（cartesian/cylindrical/spherical）应与 `setup`
     的 `+cartesian`/`+cylindrical`/`+spherical` 一致。
8. **光束数目一致性**：`ed_numberOfBeams = N` 时，应存在 `ed_lensX_1..N`、
   `ed_targetX_1..N`（及对应 `ed_pulseNumber_i`、`ed_wavelength_i`）；
   多了或少了都会使激光模块行为异常。
9. **脉冲-光束绑定**：`ed_pulseNumber_i` 引用的脉冲号应在 `ed_numberOfPulses`
   范围内（`1..ed_numberOfPulses`）。
10. **脉冲组数上限**：若 `ed_numberOfSections_*`（或 `ed_time_*`/`ed_power_*` 组数）
    超过 20，`setup` 指令需加 `ed_maxPulseSections=<值>`，否则超出的功率段被截断。
11. **靶/透镜位置**：1D 激光下 `ed_lensX_i` 与 `ed_targetX_i` 应在仿真域
    `[xmin, xmax]` 范围内（或按需在域外），保证光线能进入计算域。

#### D. 脚本级装配关联（`run_flash.sh` ↔ 其余文件）

12. **`.par` 文件名与脚本一致**：`run_flash.sh` 的 `PAR_FILE` 应与磁盘上的
    `.par` 文件名一致，否则 `mpirun ... -par_file` 找不到参数文件。
13. **`setup` 的 `species=` 与 `Config` 的 `SPECIES` 一致**：`setup` 指令中
    `species=cham,targ` 应与 `Config` 中的 `SPECIES cham`/`SPECIES targ` 对应。
14. **`Makefile` 引用的 `.o` 与存在的 `Simulation_*.F90` 对应**：`Makefile` 中
    `Simulation += Simulation_data.o` 应能在源目录找到 `Simulation_data.F90`
    （`setup` 会据此把该模块纳入编译）。

---

### 检查脚本：`check_relations.py`

上述关联由 **`check_relations.py`** 统一实现（新增，独立于仅查文件是否存在的
`checker.py`）。它扫描一个仿真目录，返回所有关联检查项的结果，便于场景脚本在
编译/运行前调用。详见该脚本文件头与 `CHECK_RELATIONS.md`。

#### 如何扩展自定义关联

`check_relations.py` 采用 **注册式规则引擎**，扩展无需改动主流程：

1. 在 `rules/` 目录新增一个检查器模块（或直接在 `check_relations.py` 内
   追加一个函数），返回 `RelationResult` 列表；
2. 通过 `REGISTRY`（或装饰器 `@relation_rule`）注册到规则表；
3. 主流程 `run_all()` 自动遍历执行，报告自动汇总。

新增规则时遵循固定签名：

```python
@relation_rule(id="my_rule", description="自定义关联说明")
def my_rule(sim_dir: Path, ctx: RelationContext) -> RelationResult:
    # 解析需要的文件 → 检查 → 返回 RelationResult(status, message, details)
    return RelationResult(name="my_rule", status=True, message="...", details={...})
```

扩展后无需修改 `run_all()`，新规则自动纳入。规则之间共享的解析结果（已解析的
`.par` 字典、`Config` 行集等）缓存在 `ctx` 中，避免重复解析。

### 可选检查

- FLASH二进制是否存在
- Python依赖（numpy, matplotlib, h5py）
- MPI是否可用

## gen_checker API

### 类: DependencyChecker

**位置**: `gen_checker/checker.py`

### 使用示例

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

## 绘图工具

### pulse_plotter

绘制激光脉冲时间-功率曲线。

```python
from gen_checker.ploter import pulse_plotter

# 从.par文件读取脉冲数据并绘图
pulse_plotter.plot(
    par_file="path/to/flash.par",
    output_file="pulse_plot.png"
)
```

### density_plotter

绘制密度分布图。

```python
from gen_checker.ploter import density_plotter

# 从FLASH输出文件读取密度数据并绘图
density_plotter.plot(
    hdf5_file="path/to/plotfile.h5",
    output_file="density_plot.png"
)
```

### ray_plotter

绘制光线追踪图。

```python
from gen_checker.ploter import ray_plotter

# 绘制激光光线传播路径
ray_plotter.plot(
    par_file="path/to/flash.par",
    output_file="ray_plot.png"
)
```

## 集成到仿真流程

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

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team
