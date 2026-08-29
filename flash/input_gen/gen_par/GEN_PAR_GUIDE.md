# gen_par — FLASH .par 参数文件生成器说明文档

## 目录
1. [概述](#概述)
2. [.par 文件格式](#par-文件格式)
3. [gen_par 生成器 API](#gen_par-生成器-api)
4. [使用示例](#使用示例)
5. [参考示例 (refs/)](#参考示例-refs)
6. [关键参数分类](#关键参数分类)
7. [维度匹配规则](#维度匹配规则)
8. [常见问题](#常见问题)

---

## 概述

`gen_par` 子包用于生成 FLASH 仿真的 `.par` 参数文件。`.par` 文件定义仿真运行时参数，控制物理过程、I/O、网格、时间步长等。

**生成器类型**: 自包含（硬编码默认参数）
**默认参数来源**: `gen_par/defaults.py` (从 LaserSlab 模板提取)
**维度支持**: 1D, 2D, 3D (自动匹配模板)
**输出文件**: `flash.par` 或自定义名称

### 维度匹配规则

生成器根据仿真维度自动选择默认参数集：

| 维度 | 模板名称 | 默认参数数量 | 说明 |
|------|---------|-------------|------|
| 1D | `example1d.par` | ~135 | 一维仿真 |
| 2D | `example.par` | ~163 | 二维仿真 |
| 3D | `example3d.par` | ~186 | 三维仿真 |

---

## .par 文件格式

### 基本结构

`.par` 文件是纯文本文件，包含键值对：

```
# 注释
key = value
```

### 值类型

| 类型 | 格式 | 示例 |
|------|------|------|
| 字符串 | `"value"` | `basenm = "lasslab_"` |
| 实数 | `1.0` 或 `1.0e-09` | `tmax = 2.0e-09` |
| 整数 | `100` | `plotFileIntervalStep = 100` |
| 布尔 | `.true.` 或 `.false.` | `useHydro = .true.` |

### 参数分类

`.par` 文件通常按以下顺序组织：

1. **基本信息**: `run_comment`, `log_file`, `basenm`
2. **I/O参数**: checkpoint/plot文件间隔
3. **辐射/不透明度参数**: `rt_*`, `op_*`
4. **激光参数**: `ed_*`
5. **热传导参数**: `diff_*`
6. **热交换参数**: `useHeatexchange`
7. **EOS参数**: `eos_*`, `smallt`, `smallx`
8. **流体力学参数**: `order`, `RiemannSolver`, `xl_boundary_type`
9. **初始条件**: `sim_*`, `ms_*`
10. **时间参数**: `tmax`, `cfl`, `dt*`
11. **网格参数**: `geometry`, `xmin`, `xmax`, `lrefine_max`

---

## gen_par 生成器 API

### 类: ParGeneratorExtended

**位置**: `gen_par/generator.py`

**描述**: 功能强大的参数文件生成器，支持维度感知、激光脉冲/光束配置、材料设置。

### 初始化

```python
from gen_par import ParGeneratorExtended

# 1D仿真（使用 PARAMS_1D 默认参数）
generator = ParGeneratorExtended(simulation_name="LaserSlab", dimension=1)

# 2D仿真（使用 PARAMS_2D 默认参数）
generator = ParGeneratorExtended(simulation_name="LaserSlab", dimension=2)

# 3D仿真（使用 PARAMS_3D 默认参数）
generator = ParGeneratorExtended(simulation_name="LaserSlab", dimension=3)
```

### 主要方法

#### set_dimension(dim)

切换仿真维度，重新加载默认参数。

```python
generator = ParGeneratorExtended(dimension=1)
generator.set_dimension(2)  # 切换到2D
```

#### set(key, value)

设置单个参数。

```python
generator.set("tmax", 5.0e-09)
generator.set("cfl", 0.3)
```

#### set_pulse(times, powers)

设置单脉冲的时间-功率曲线。

```python
import numpy as np

times = [0.0, 0.1e-9, 1.0e-9, 1.1e-9]
powers = [0.0, 1.0e9, 1.0e9, 0.0]
generator.set_pulse(times, powers)
```

#### set_pulses(pulses)

设置多脉冲。

```python
pulses = [
    {"pulse_id": 1, "times": [0.0, 0.5e-9, 1.0e-9], "powers": [0.0, 5.0e8, 0.0]},
    {"pulse_id": 2, "times": [1.0e-9, 1.5e-9, 2.0e-9], "powers": [0.0, 5.0e8, 0.0]},
]
generator.set_pulses(pulses)
```

#### set_beams(beams)

设置激光光束配置。

```python
from gen_par.generator import BeamConfig

# 创建光束配置
beam1 = BeamConfig(
    beam_id=1,
    lens_x=1000.0e-04,  # 透镜x坐标 (cm)
    lens_y=0.0,
    lens_z=-1000.0e-04,
    target_x=0.0,
    target_y=0.0,
    target_z=60.0e-04,  # 目标z坐标 (cm)
    pulse_number=1,
    wavelength=1.053,  # 波长 (μm)
    cross_section_type="gaussian2D",
    number_of_rays=4096,
    grid_type="radial2D",
    grid_radial_tics=64,
)

generator.set_beams([beam1])
```

**BeamConfig 参数**:

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `beam_id` | int | 1 | 光束编号 |
| `lens_x, lens_y, lens_z` | float | -0.1, 0.0, 0.0 | 透镜坐标 (cm) |
| `target_x, target_y, target_z` | float | 0.014, 0.0, 0.0 | 目标坐标 (cm) |
| `pulse_number` | int | 1 | 关联的脉冲编号 |
| `wavelength` | float | 1.053 | 波长 (μm) |
| `cross_section_type` | str | "uniform" | 截面类型 ("uniform", "gaussian2D") |
| `number_of_rays` | int | 1 | 光线数 |
| `grid_type` | str | "regular1D" | 网格类型 ("regular1D", "radial2D", "square2D") |
| `grid_radial_tics` | int | 512 | 径向网格刻度数 |

#### set_material(material, target=True)

设置材料参数（靶材或腔室气体）。

```python
from gen_par.materials import Material

# 创建材料
aluminum = Material(
    name="Aluminum",
    rho=2.7,        # 密度 (g/cc)
    A=26.9815386,   # 原子量
    Z=13.0,         # 平均电荷
    file="al-imx-003.cn4",  # EOS表文件
)

# 设置为靶材
generator.set_material(aluminum, target=True)

# 设置腔室气体
helium = Material(
    name="Helium",
    rho=2.655e-07,  # 密度 (g/cc)
    A=4.002602,
    Z=2.0,
    file="he-imx-005.cn4",
)
generator.set_material(helium, target=False)
```

#### set_domain(xmin, xmax, nblockx, ...)

设置计算域和网格参数。

```python
# 1D仿真
generator.set_domain(
    xmin=0.0,
    xmax=160e-4,    # 域大小 (cm)
    nblockx=4,      # x方向块数
)

# 2D仿真
generator.set_domain(
    xmin=0.0,
    xmax=40e-4,
    ymin=0.0,
    ymax=80e-4,
    nblockx=1,
    nblocky=2,
)
```

#### set_time(tmax, dtinit, dtmin, dtmax)

设置时间步长参数。

```python
generator.set_time(
    tmax=2.0e-9,    # 总仿真时间 (s)
    dtinit=1.0e-15, # 初始时间步 (s)
    dtmin=1.0e-16,  # 最小时间步 (s)
    dtmax=3.0e-9,   # 最大时间步 (s)
)
```

#### generate()

生成 `.par` 文件内容字符串。

```python
content = generator.generate()
print(content)
```

#### save(output_path)

生成并保存 `.par` 文件。

```python
output_path = generator.save("path/to/flash.par")
print(f"Saved to: {output_path}")
```

#### preview()

打印预览（等同于 `generate()` + `print`）。

```python
generator.preview()
```

---

## 使用示例

### 示例 1: 生成1D激光-等离子体仿真参数

```python
from gen_par import ParGeneratorExtended
from gen_par.generator import BeamConfig
import numpy as np

# 创建1D生成器
gen = ParGeneratorExtended(simulation_name="LaserSlab1D", dimension=1)

# 设置激光脉冲（方形脉冲）
times = [0.0, 0.1e-9, 1.0e-9, 1.1e-9]
powers = [0.0, 1.0e9, 1.0e9, 0.0]
gen.set_pulse(times, powers)

# 设置1D激光光束
beam = BeamConfig(
    beam_id=1,
    lens_x=-0.1,      # 1D只需x坐标
    target_x=0.014,
    pulse_number=1,
    wavelength=1.053,
    cross_section_type="uniform",
    number_of_rays=1,
    grid_type="regular1D",
)
gen.set_beams([beam])

# 设置材料
gen.set("sim_rhoTarg", 2.7)   # 铝密度
gen.set("sim_teleTarg", 290.11375)

# 设置域
gen.set_domain(xmin=0.0, xmax=160e-4, nblockx=4)

# 设置时间
gen.set_time(tmax=2.0e-9, dtinit=1.0e-15)

# 保存
gen.save("path/to/flash.par")
```

### 示例 2: 生成2D Sod激波管测试参数

```python
from gen_par import ParGeneratorExtended

# 创建2D生成器（但实际上用于1D Sod测试）
gen = ParGeneratorExtended(simulation_name="Sod", dimension=1)

# 设置Sod初始条件
gen.set("sim_rhoLeft", 1.0)
gen.set("sim_rhoRight", 0.125)
gen.set("sim_pLeft", 1.0)
gen.set("sim_pRight", 0.1)

# 设置流体力学参数
gen.set("order", 3)               # 3rd order PPM
gen.set("RiemannSolver", "hllc")
gen.set("xl_boundary_type", "reflect")
gen.set("xr_boundary_type", "outflow")

# 设置网格
gen.set("geometry", "cartesian")
gen.set("xmin", 0.0)
gen.set("xmax", 1.0)
gen.set("nblockx", 2)

# 设置时间
gen.set("tmax", 0.2)
gen.set("cfl", 0.4)

# 保存
gen.save("path/to/sod.par")
```

### 示例 3: 生成3D仿真参数

```python
from gen_par import ParGeneratorExtended

# 创建3D生成器
gen = ParGeneratorExtended(simulation_name="LaserSlab3D", dimension=3)

# 设置3D域
gen.set_domain(
    xmin=0.0, xmax=40e-4,
    ymin=0.0, ymax=40e-4,
    zmin=0.0, zmax=40e-4,
    nblockx=2, nblocky=2, nblockz=2,
)

# 设置3D激光光束（需要y/z坐标）
from gen_par.generator import BeamConfig
beam = BeamConfig(
    beam_id=1,
    lens_x=0.0, lens_y=0.0, lens_z=-1000.0e-4,
    target_x=0.0, target_y=0.0, target_z=20.0e-04,
    wavelength=1.053,
    cross_section_type="gaussian2D",
    number_of_rays=10000,
    grid_type="square2D",
    grid_radial_tics=128,
)
gen.set_beams([beam])

# 保存
gen.save("path/to/laserslab3d.par")
```

### 示例 4: 使用材料数据库

```python
from gen_par import ParGeneratorExtended
from gen_par.materials import MaterialDatabase

# 加载材料数据库
db = MaterialDatabase("path/to/eos_op_data/")

# 查询材料
al = db.get_material("Al", rho=2.7)
he = db.get_material("He", rho=2.655e-07)

# 设置材料
gen = ParGeneratorExtended(dimension=2)
gen.set_material(al, target=True)
gen.set_material(he, target=False)

# 保存
gen.save("path/to/flash.par")
```

---

## 参考示例 (refs/)

`gen_par/refs/` 目录包含 750+ 个 `.par` 文件示例，涵盖各种仿真类型。

### 主要示例类别

| 类别 | 示例文件 | 描述 |
|------|---------|------|
| 激光平板 | `coldstart_2d_3lasers.par` | 2D 3激光束 |
| 激光平板 | `coldstart_3d_5laser.par` | 3D 5激光束 |
| 激光平板 | `example.par` | 2D示例 |
| 激光平板 | `example1d.par` | 1D示例 |
| 激光平板 | `example3d.par` | 3D示例 |
| Sod测试 | `test_UG_1d.par` | 1D Sod |
| Sod测试 | `test_UG_2d.par` | 2D Sod |
| Sedov爆炸 | `test_smoothED.par` | Sedov测试 |
| AMR测试 | `test_pm_3lev.par` | 3级AMR |
| 粒子测试 | `test_restartpart1_1d.par` | 粒子与重启 |

### 如何参考这些示例

1. **查看示例**: 直接读取 `refs/` 中的 `.par` 文件
2. **提取参数**: 了解特定仿真需要哪些参数
3. **修改默认值**: 在 `defaults.py` 中修改默认参数

**示例**: 参考 `coldstart_2d_3lasers.par`

```bash
cat gen_par/refs/coldstart_2d_3lasers.par

# 提取关键参数:
# - ed_numberOfBeams = 3
# - ed_lensX_1, ed_lensX_2, ed_lensX_3
# - ed_targetX_1, ed_targetX_2, ed_targetX_3
```

---

## 关键参数分类

### 1. I/O参数

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `run_comment` | STRING | "..." | 运行注释 |
| `log_file` | STRING | "flash.log" | 日志文件名 |
| `basenm` | STRING | "flash_" | 输出文件基名 |
| `checkpointFileIntervalTime` | REAL | 1.0 | checkpoint间隔时间 (s) |
| `checkpointFileIntervalStep` | INTEGER | 1000 | checkpoint间隔步数 |
| `plotFileIntervalStep` | INTEGER | 100 | plot文件间隔步数 |
| `plotFileIntervalTime` | REAL | 0.01 | plot文件间隔时间 (s) |
| `plot_var_1` ... `plot_var_9` | STRING | "dens", ... | plot变量名 |
| `restart` | BOOLEAN | .false. | 是否重启 |
| `checkpointFileNumber` | INTEGER | 0 | 重启checkpoint编号 |

### 2. 激光参数 (ed_*)

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `useEnergyDeposition` | BOOLEAN | .false. | 是否使用能量沉积 |
| `ed_numberOfBeams` | INTEGER | 1 | 激光束数量 |
| `ed_numberOfPulses` | INTEGER | 1 | 脉冲数量 |
| `ed_maxRayCount` | INTEGER | 10000 | 最大光线数 |
| `ed_gradOrder` | INTEGER | 2 | 梯度阶数 |
| `ed_wavelength_1` | REAL | 1.053 | 光束1波长 (μm) |
| `ed_lensX_1` | REAL | -0.1 | 光束1透镜x坐标 (cm) |
| `ed_targetX_1` | REAL | 0.014 | 光束1目标x坐标 (cm) |
| `ed_power_1_1` ... `ed_power_1_N` | REAL | 0.0 | 脉冲1功率 (W) |
| `ed_time_1_1` ... `ed_time_1_N` | REAL | 0.0 | 脉冲1时间 (s) |

### 3. 流体力学参数

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `useHydro` | BOOLEAN | .true. | 是否使用流体力学 |
| `order` | INTEGER | 3 | 插值阶数 (1/2/3/5) |
| `slopeLimiter` | STRING | "minmod" | 斜率限制器 |
| `RiemannSolver` | STRING | "hllc" | Riemann求解器 |
| `xl_boundary_type` | STRING | "reflect" | x左边界类型 |
| `xr_boundary_type` | STRING | "outflow" | x右边界类型 |
| `cfl` | REAL | 0.4 | CFL数 |
| `use_avisc` | BOOLEAN | .true. | 使用人工粘性 |
| `cvisc` | REAL | 0.1 | 人工粘性系数 |

### 4. 网格参数

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `geometry` | STRING | "cartesian" | 几何类型 |
| `xmin, xmax` | REAL | 0.0, 1.0 | x范围 |
| `ymin, ymax` | REAL | 0.0, 1.0 | y范围 |
| `zmin, zmax` | REAL | 0.0, 1.0 | z范围 |
| `nblockx` | INTEGER | 1 | x方向块数 |
| `nblocky` | INTEGER | 1 | y方向块数 |
| `nblockz` | INTEGER | 1 | z方向块数 |
| `lrefine_max` | INTEGER | 4 | 最大AMR等级 |
| `lrefine_min` | INTEGER | 1 | 最小AMR等级 |

### 5. 时间参数

| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `tmax` | REAL | 1.0e-9 | 总仿真时间 (s) |
| `dtinit` | REAL | 1.0e-15 | 初始时间步 (s) |
| `dtmin` | REAL | 1.0e-16 | 最小时间步 (s) |
| `dtmax` | REAL | 1.0e-9 | 最大时间步 (s) |
| `cfl` | REAL | 0.4 | CFL数 |
| `tstep_change_factor` | REAL | 1.1 | 时间步变化因子 |
| `nend` | INTEGER | 10000000 | 最大步数 |

---

## 维度匹配规则

生成器根据维度自动选择默认参数集：

### 1D仿真

- 使用 `PARAMS_1D`
- 不需要 `nblocky`, `nblockz`
- 激光光束只需 `lens_x`, `target_x`
- 边界条件只需 `xl_`, `xr_`

### 2D仿真

- 使用 `PARAMS_2D`
- 需要 `nblockx`, `nblocky`
- 激光光束需要 `lens_x`, `lens_y`, `target_x`, `target_y`
- 边界条件需要 `xl_`, `xr_`, `yl_`, `yr_`

### 3D仿真

- 使用 `PARAMS_3D`
- 需要 `nblockx`, `nblocky`, `nblockz`
- 激光光束需要完整的3D坐标
- 边界条件需要 `xl_`, `xr_`, `yl_`, `yr_`, `zl_`, `zr_`

### 自动检测维度

生成器可以尝试自动检测维度：

```python
dim = generator._detect_dimension()
# 逻辑:
# - 如果有 nblockz → 3D
# - 如果有 nblocky → 2D
# - 否则 → 1D
```

---

## 常见问题

### 1. 如何添加自定义参数？

**答**: 使用 `set()` 方法：

```python
generator = ParGeneratorExtended(dimension=2)
generator.set("my_custom_param", 1.0)
```

如果参数不在默认参数集中，它会被添加到"ADDITIONAL PARAMETERS"部分。

### 2. 如何生成多个不同配置的 `.par` 文件？

**答**: 创建多个生成器实例，或使用同一个实例但修改参数后保存：

```python
# 方法1: 多个实例
gen1 = ParGeneratorExtended(dimension=1)
gen1.set("tmax", 1.0e-9)
gen1.save("sim1.par")

gen2 = ParGeneratorExtended(dimension=1)
gen2.set("tmax", 2.0e-9)
gen2.save("sim2.par")

# 方法2: 修改后保存
gen = ParGeneratorExtended(dimension=1)
gen.set("tmax", 1.0e-9)
gen.save("sim1.par")
gen.set("tmax", 2.0e-9)
gen.save("sim2.par")
```

### 3. 如何验证生成的 `.par` 文件是否正确？

**答**: 使用FLASH读取 `.par` 文件：

```bash
cd /path/to/FLASH4.8
./flash2 -par file=path/to/flash.par -check_par
```

FLASH会检查参数是否有效。

### 4. 如何为HPC运行优化参数？

**答**: 调整以下参数：

```python
gen = ParGeneratorExtended(dimension=2)

# 增加checkpoint间隔（减少I/O）
gen.set("checkpointFileIntervalTime", 10.0)

# 增加plot间隔（减少I/O）
gen.set("plotFileIntervalStep", 1000)

# 调整AMR参数（提高性能）
gen.set("lrefine_max", 6)
gen.set("refine_var_1", "dens")
gen.set("refine_var_2", "tele")
```

---

## 进阶：扩展默认参数集

如果需要添加新的默认参数集，编辑 `gen_par/defaults.py`：

```python
# 在 defaults.py 中添加
PARAMS_CUSTOM = {
    "custom_param1": 1.0,
    "custom_param2": ".true.",
    # ...
}

DIMENSION_PARAMS[4] = PARAMS_CUSTOM  # 添加新的维度4
```

---

## 参考资料

1. FLASH User Guide - Chapter 5: Runtime Parameters
2. FLASH Source Code - `flash.par` example files
3. PhySimX Documentation - `input_gen/gen_par/`

---

**文档版本**: 1.0
**最后更新**: 2026-07-03
**维护**: PhySimX Team

---

## 行尾注释 (2026-08-29 新增, 全场景生效)

`generate()`/`save()` 输出时自动为**尽可能多**的参数行追加行尾注释，
所有 `#` 按全局对齐列统一（对齐基准 = 可注释行的最大长度 + 2）。

### 覆盖范围

| 类别 | 处理方式 | 示例 |
|------|---------|------|
| 静态字典 `PARAM_COMMENTS` | 常用 I/O / 时间 / 网格 / 激光标量 / MGD / 扩散参数 | `tmax = ... # simulation end time [s]` |
| 静态字典 — PPMLR 水动求解器 | 13 项: `order`, `slopeLimiter`, `LimitedSlopeBeta`, `charLimiting`, `use_avisc`, `cvisc`, `use_flattening`, `use_steepening`, `use_upwindTVD`, `RiemannSolver`, `entropy`, `shockDetect`, `use_hybridOrder` | `shockDetect = .true. # shock detection sensor (used by use_hybridOrder)` |
| 激光脉冲序列 | 动态规则 | `ed_time_1_82 = ... # laser pulse time, beam 1 section 82 [s]` |
| MGD 能群边界 | 动态规则 | `rt_mgdBounds_3 = ... # MGD radiation group boundary 3` |
| plot_var 白名单 | 动态规则 (防漏配提醒) | `plot_var_14 = "fllm" # plotfile output variable whitelist #14` |
| 物种表绑定/材料族 | 动态规则 | `eos_tar1TableFile = ... # tar1 EOS table file`、`sim_rhoCham = ... # cham initial density [g/cm3]` |
| 场景自定义几何 | 动态规则 | `sim_shldRadius = ... # layer geometry: shld radius [cm]` |
| lrefine_max/min | 动态规则 (分辨率公式+结果, 简化格式) | 见下 |

### lrefine 网格分辨率注释 (简化格式)

`lrefine_max`/`lrefine_min` 行尾自动附理论分辨率：

```
lrefine_max = 9        # res = dir_delta/(nxb*nblock*2^(lrefine_max-1)) = 1.525879e-06 cm
```

公式：`res = dir_delta/(nxb*nblock*2^(lrefine-1))`，其中
`dir_delta = xmax - xmin`（沿 x），`nblock = nblockx`，`nxb` 取参数
`nxb`（缺省 16，须与 setup 的 `-nxb` 一致）。域/分块参数缺失时不生成注释。

### 扩展

新增参数的注释：加入模块级 `PARAM_COMMENTS` 字典；模式化参数族在
`_inline_comment()` 中加动态规则。未覆盖的参数不追加注释（保持行尾干净）。
