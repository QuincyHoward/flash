# flash-sim 场景系统 — 使用指南

> flash-sim 场景系统使用指南：从即插即用仿真入口到可参数化、可优化的工程工具。

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

## 场景系统的重要性与广泛应用

场景系统是 flash-sim 的核心价值所在，也是把 FLASH 这一庞大、门槛较高的 HEDP 仿真代码转化为「可计算、可复用、可优化」工程工具的关键枢纽。其应用广泛性体现在多个层次：

- **简单参数扫描**：通过 `params_overrides` 批量覆盖材料厚度、密度、激光功率、AMR 层级等参数，无需改动任何 FLASH 源文件，即可在 Python 循环中自动生成 `.par` 并运行多组仿真（见文末「如何并行运行多个仿真」）。
- **多组仿真数据对比**：每次运行均输出统一规格的 `result.h5`（固定的 `t × x` 插值网格，字段见「输出结构」），天然便于跨工况、跨方案的定量对比与统计，无需自行对齐变分辨率 AMR 网格。
- **参数化接入优化算法 / 优化模型（重点）**：场景以**结构化参数**为唯一输入、以 `result.h5` 物理量为输出，这一「参数 → 物理量」的清晰映射，使其能够无缝接入各类优化框架——无论是网格搜索、贝叶斯优化、遗传算法，还是代理模型（surrogate model）/ 神经网络，都可将场景当作「黑盒仿真器」反复调用，为目标函数评估提供高效、可复现的采样。
- **为靶结构、脉冲波形等设计提供便利性**：将靶层厚度 / 材料、激光脉冲时序与波形等设计变量参数化后，结合上述优化闭环，可系统性地探索设计空间、反演最优靶构型或最优脉冲方案，显著缩短「试错—仿真」迭代周期。

> 💡 简言之：场景系统既降低了 FLASH 仿真的使用门槛（新手可一键运行），也打开了自动化、智能化的上层应用空间（研究者可把仿真嵌入优化与设计循环）。

## 什么是场景系统？

场景系统（`scenarios/`）是 **flash-sim 的顶层仿真入口**，将 FLASH 的完整工作流（源文件管理 → 编译 → 运行 → HDF5 收集 → 时空插值 → 输出）封装为即插即用的 **物理场景**。

用户只需：

```python
from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

engine = FlashSimulatorEngine(get_scenario("thin_layer_sandwich_si"))
output = engine.run()
```

无需手动配置 FLASH 源文件、编写 `.par`、处理编译，也不需要写 HDF5 读取和插值代码。

---

## 外部使用方式

### 前提条件

1. 已安装 FLASH 4.8（在 WSL 或超算上）
2. Python ≥ 3.10，已安装 `h5py`, `numpy`

### 1. 导入 flash 包

```python
import sys
sys.path.insert(0, "/path/to/physimx_sim/src/physimx_sim")

from flash.scenarios.registry import get_scenario, list_scenarios
from flash.scenarios.simulator import FlashSimulatorEngine
```

> 无需安装 flash-sim 包——`sys.path` 指向 `physimx_sim` 根目录即可。

### 2. 列出可用场景

```python
for name, desc in list_scenarios():
    print(f"  {name:30s} → {desc}")
```

输出样例:

```
ch_center                      → CH 靶中心时域演化 5e14 W/cm²
thin_layer_sandwich_al         → Al/CH/He 三层靶 5e11 W/cm² 激光烧蚀 (原始 EOS 表)
thin_layer_sandwich_si         → Si/CH/He 三层靶 5e14 W/cm² 激光烧蚀 (新 EOS 表)
```

### 3. 运行仿真

```python
# 加载场景
scenario = get_scenario("thin_layer_sandwich_si")

# 创建仿真引擎 (verbose=True 显示详细日志)
engine = FlashSimulatorEngine(scenario, verbose=True)

# 运行: 包括 FLASH 编译 + 运行 + 后处理
output = engine.run(
    flash_timeout=900,       # FLASH 运行超时 (秒)
    keep_flash_raw=True,     # 保留原始 chk 文件
)

print(f"✅ result.h5: {output.result_h5_path}")
print(f"   运行目录:   {output.run_dir}")
print(f"   chk 文件数: {output.n_chk}")
print(f"   输出字段:   {output.fields}")
```

### 4. 覆盖默认参数

```python
output = engine.run(
    params_overrides={
        "sim_polyHeight": 5e-4,    # 加厚 CH 泡沫层
        "sim_rhoPoly": 0.5,         # 降低 CH 密度
        "laser_powers": [0, 1e15, 1e15, 0],  # 提高激光功率
        "lrefine_max": 7,           # 提高 AMR 分辨率
    },
    keep_flash_raw=True,
)
```

所有可覆盖参数见 `default_params`:

```python
scenario = get_scenario("thin_layer_sandwich_si")
print(scenario.default_params.keys())
```

> ⚠️ **重要规则**: 未在 `params_overrides` 中指定的参数**保持 defaults.py 中的默认值**。

### 5. 跳过 FLASH（仅生成输入文件）

```python
output = engine.run(run_flash=False)
# → 只生成 .par + 复制 sim_input/，不运行 FLASH
```

### 6. 仅插值现有 chk（跳过 FLASH 运行）

```python
output = engine.run(
    run_flash=False,
    skip_interpolate=False,   # 强制插值
    # 引擎会自动查找已有 chk 文件
)
```

### 7. 清理 vs 保留

| 参数 | 效果 |
|------|------|
| `keep_flash_raw=True` | chk 文件 → `sim_output/` (保留) |
| `keep_flash_raw=False` | 运行后删除 chk（仅保留 result.h5） |

---

## 编译与缓存：flash.par + 预编译 flash4

FLASH 的编译（`./setup` + `make`）只取决于**编译期输入**：`Config`、`Makefile`、`*.F90` 源文件以及 setup 参数（`flash_setup_args`）。运行时参数 `.par` **不参与编译**。

因此，**同一场景只需第一次编译 flash4**，之后可以直接用 **`flash.par` + 已编译的 `flash4`** 反复运行，无需重新编译。

### 方式 A：引擎自动管理（推荐）

`FlashSimulatorEngine.run()` 内置编译缓存，完全自动：

- **首次运行**某场景时执行 `setup + make`，并将编译产物缓存为
  `~/<user>/FLASH/FLASH4.8/<user>/flash4_<sim_name>_<指纹>.bin`
  （指纹 = setup 参数 + `Config`/`Makefile`/`*.F90` 的哈希）；
- **之后运行同一场景**（未改动编译期输入）时自动命中缓存，**跳过编译直接运行**；
- 通过 `params_overrides` 修改 `.par` 参数**不会**触发重新编译；
- 如需强制重新编译（例如升级了 FLASH 或依赖），显式传 `force_recompile=True`。

### 方式 B：手动使用 flash.par + flash4

首次编译完成后，也可以脱离引擎，完全手动仿真：

```bash
# 1. 准备运行目录
mkdir -p /tmp/run_mycase && cd /tmp/run_mycase

# 2. 复制已编译的 flash4、.par、物性表 (.cn4)
cp ~/<user>/FLASH/FLASH4.8/<user>/flash4_<sim_name>_*.bin ./flash4
cp <场景 sim_input 目录>/*.cn4 ./
cp <场景 sim_input 目录>/<sim_name>.par flash.par   # 也可改名为其他 .par 后用 -par_file 指定

# 3. 运行 (N 为 MPI 进程数, 见资源自动配置)
mpirun -np N ./flash4
```

> 同一份 `flash.par` + `flash4` 可反复修改参数多次运行，无需重新编译；
> 修改后的参数文件建议复制新文件再改（如 `mycase2.par`），用 `-par_file` 指定。

### MPI 进程数 N 的来源

N 由**装置 × 维度**自动计算（详见 `flash_run/env/resource_config.py` 与
`scripts/gen_resource_config.py`）：

```
nproc = max(1, int(总核数 × CPU% / 100) ÷ 并行数)     # 取整
```

| 装置 (按总核数) | 1D | 2D | 3D |
|------|------|------|------|
| 笔记本 (<10 核) | 80% CPU，不支持并行 | 80% CPU，不支持并行 | 80% CPU，不支持并行 |
| 台式机 (<30 核) | 80% CPU，2 个并行 | 80% CPU，不支持并行 | 80% CPU，不支持并行 |
| 超算 (≥30 核) | 80% CPU，3 个并行 | 80% CPU，2 个并行 | 80% CPU，不支持并行 |

生成/查看控制文件：

```bash
python scripts/gen_resource_config.py --show          # 自动探测本机并生成控制文件
python -m flash.flash_run.env.resource_config show    # 查看当前配置
```

---

## 场景总览

### thin_layer_sandwich_si

| 属性 | 值 |
|------|-----|
| **物理** | Si/CH/He 三层靶, 双束 351nm 激光相向烧蚀 |
| **应用** | 对撞压缩等离子体制备 |
| **激光** | 5e14 W/cm², 100ps 上升沿 |
| **Si 靶** | A=28.0855, Z=14, ρ=2.33 g/cm³ |
| **CH 泡沫** | ρ=1.05 g/cm³ (lrefine_max=8) |
| **He 填充** | ρ=1e-6 g/cm³ (eos_gam) |
| **EOS 表** | 新生成高分辨 (Z02, Z06, Z14) |
| **初始温度** | 3500 K (见下方说明) |
| **tmax** | 1.2e-9 s (1ns 激光) |
| **输出字段** | 13 个 (dens, tele, tion, trad, pele, pion, prad, pres, velx, ye, sumy, poly, targ) |

> ⚠️ **Si 场景初始温度说明**: Si 场景使用新 EOS/opacity 表（Z02/Z06/Z14，起始 0.01 eV ≈ 116 K），室温 290.11375 K 在 EOS 表有效范围内，但 FLASH 扩散求解器在 He 低密度区与 CH 界面上，290K 时的 opacity 插值会导致 `[Diffuse]: computed dt is not positive!` 错误。因此将默认初始温度提高到 **3500 K（≈ 0.30 eV）** 以保证数值稳定。如需室温，可在 `params_override` 中显式传入 `sim_teleCham=290.11375` 等参数。

### thin_layer_sandwich_al

| 属性 | 值 |
|------|-----|
| **物理** | Al/CH/He 三层靶, 双束 351nm 激光相向烧蚀 |
| **应用** | 对撞压缩等离子体制备（经典验证） |
| **激光** | 5e11 W/cm², 100ps 上升沿 |
| **Al 靶** | A=26.9815, Z=13, ρ=2.7 g/cm³ |
| **EOS 表** | 原始 FLASH EOS (al-imx-003.cn4, he-imx-005.cn4, polystyrene-imx-008.cn4) |
| **tmax** | 3.2e-9 s |
| **备注** | 最稳定版本，适合初次使用 |

### ch_center

| 属性 | 值 |
|------|-----|
| **物理** | CH 泡沫靶 + 两侧 He, 双束 351nm 激光相向 |
| **应用** | 中心等离子体状态时域演化观测 |
| **激光** | 5e14 W/cm² |
| **CH 靶** | ρ=1.0 g/cm³ |
| **He** | ρ=1e-6 g/cm³ (eos_tab) |
| **EOS 表** | 原始 FLASH EOS (he-imx-005.cn4, polystyrene-imx-008.cn4) |
| **tmax** | 1.2e-9 s |
| **输出字段** | 7 个 (dens, tele, tion, trad, ye, sumy, pres) |
| **备注** | 原始 FLASH LaserSlab 配置, 使用旧 EOS 表 + 旧 MGD 组设置 |

---

## 输出结构

运行产生的目录结构:

```
{当前工作目录}/runs_{scenario_name}/{run_id:06d}/
├── sim_input/              ← FLASH 源文件 + .par + .cn4 + 诊断图 (always)
│   ├── Config
│   ├── *.F90
│   ├── *.cn4
│   └── {sim_name}.par
├── sim_output/             ← FLASH 原始 chk HDF5 (keep_flash_raw=True 时)
│   ├── lasslab_hdf5_chk_0000
│   ├── lasslab_hdf5_chk_0001
│   └── ...
└── database/
    ├── flash_in/
    │   ├── input_params.json   ← 输入参数快照 (可追溯)
    │   └── run.log             ← 运行日志
    └── flash_out/
        └── result.h5           ← ★ 核心输出 (变分辨率插值网格)
```

`result.h5` 包含:

| 数据集 | 形状 | 说明 |
|--------|------|------|
| `t` | `(Nt,)` | 时间网格 (s) |
| `x` | `(Nx,)` | 空间网格 (cm) |
| `dens` | `(Nt, Nx)` | 质量密度 (g/cm³) |
| `tele` | `(Nt, Nx)` | 电子温度 (K) |
| `tion` | `(Nt, Nx)` | 离子温度 (K) |
| `trad` | `(Nt, Nx)` | 辐射温度 (K) |
| `pres` | `(Nt, Nx)` | 总压强 (dyne/cm²) |
| `pele` | `(Nt, Nx)` | 电子压强 |
| `pion` | `(Nt, Nx)` | 离子压强 |
| `prad` | `(Nt, Nx)` | 辐射压强 |
| `velx` | `(Nt, Nx)` | x 方向速度 (cm/s) |
| `ye` | `(Nt, Nx)` | 自由电子丰度 |
| `sumy` | `(Nt, Nx)` | 平均电离度 |
| `poly` | `(Nt, Nx)` | CH 泡沫标记 (0/1) |
| `targ` | `(Nt, Nx)` | 靶材标记 (0/1) |

---

## 完整示例

```python
#!/usr/bin/env python3
"""完整示例: 运行 Si 仿真 → 绘图 → 分析"""

import sys
sys.path.insert(0, "/path/to/physimx_sim/src/physimx_sim")

from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

# 1. 加载场景
scenario = get_scenario("thin_layer_sandwich_si")
print(f"场景: {scenario.name} — {scenario.description}")
print(f"源文件: {scenario.sim_input_dir}")

# 2. 创建引擎
engine = FlashSimulatorEngine(scenario, verbose=True)

# 3. 运行 (1ns, 5e14 W/cm²)
output = engine.run(
    params_overrides={
        "laser_powers": [0, 5e14, 5e14, 0],
        "lrefine_max": 8,
    },
    flash_timeout=900,
    keep_flash_raw=True,
)

# 4. 验证输出
import h5py
f = h5py.File(output.result_h5_path, "r")
print(f"时间步: {len(f['t'])}")
print(f"空间点: {len(f['x'])}")
print(f"密度范围: {f['dens'][()].min():.2e} ~ {f['dens'][()].max():.2e}")
print(f"电子温度: {f['tele'][()].min():.2e} ~ {f['tele'][()].max():.2e}")
f.close()

# 5. 读取 run.log
log = open(f"{output.run_dir}/database/flash_in/run.log").read()
print(log[:500])
```

---

## 自定义参数详解

### 仿真几何

| 参数 | 默认 (Si) | 说明 |
|------|-----------|------|
| `xmin_cm` | -0.045 | 左边界 (cm) |
| `xmax_cm` | 0.045 | 右边界 (cm) |
| `nblockx` | 8 | 初始分块数 |
| `lrefine_max` | 8 | 最大 AMR 层级 |
| `lrefine_min` | 1 | 最小 AMR 层级 |

### 材料参数

| 参数 | 默认 (Si) | 说明 |
|------|-----------|------|
| `sim_polyHeight` | 4e-4 | CH 泡沫层半厚 (cm) |
| `sim_rhoPoly` | 1.05 | CH 密度 (g/cm³) |
| `sim_targHeight` | 2e-5 | 靶材层半厚 (cm) |
| `sim_rhoTarg` | 2.33 | 靶材密度 (g/cm³) |
| `sim_rhoCham` | 1e-6 | 填充气体密度 (g/cm³) |

### 激光脉冲

```python
laser_times  = [0,        1e-10,    1e-9,    1.1e-9 ]  # (s)
laser_powers = [0,        5e14,     5e14,    0       ]  # (W/cm²)
#               ↑关        ↑开       ↑关      ↑已关
```

`ed_power_1_1` ~ `ed_power_1_N`: 第 1 束激光的 N 段功率 (两束对称)。

### 时间控制

| 参数 | 默认 (Si) | 默认 (Al) | 说明 |
|------|-----------|-----------|------|
| `tmax` | 1.2e-9 | 3.2e-9 | 总仿真时间 (s) |
| `dtinit` | 1e-16 | 1e-15 | 初始时间步 (s) |
| `dtmin` | 1e-16 | 1e-12 | 最小时间步 (s) |
| `dtmax` | 1e-12 | 3e-9 | 最大时间步 (s) |

> Si 的高激光功率 (5e14 W/cm²) 需要更小的时间步。

---

## 架构说明

```
flash/
├── scenarios/
│   ├── simulator.py              ← FlashSimulatorEngine (统一引擎)
│   ├── base.py                   ← SimulationScenario 数据类
│   ├── registry.py               ← 场景注册表 (get/list/register)
│   ├── README.md                 ← 本文档
│   │
│   ├── collision_compression/    ← 物理专题: 对撞压缩
│   │   └── thin_layer_sandwich/  ← 场景: 三层薄层靶
│   │       ├── __init__.py       ← Si + Al 双场景定义 + 注册
│   │       ├── par_builder.py    ← .par 文件生成器
│   │       ├── interpolator.py   ← 时空插值器
│   │       ├── defaults_si.py    ← Si 靶默认参数
│   │       ├── defaults_al.py    ← Al 靶默认参数
│   │       ├── sim_input_si/     ← Si 靶 FLASH 源文件
│   │       └── sim_input_al/     ← Al 靶 FLASH 源文件
│   │
│   ├── center_evolution/         ← 物理专题: 中心演化
│   │   └── ch_center/            ← 场景: CH 中心演化
│   │       ├── __init__.py       ← 场景定义 + 内联 par_builder
│   │       └── flash_input/      ← FLASH 源文件
│   │
│   └── plasma_preparation/       ← 物理专题: 准备中
│       └── __init__.py
│
├── test/scenarios/               ← 场景接口测试
│   ├── run_all_scenario_tests.py ← 批量测试运行器
│   ├── test_scenarios_imports.py ← 导入与注册表测试
│   ├── test_scenario_par_build.py← .par 生成测试
│   ├── test_engine_dryrun.py     ← 引擎 dry-run 测试
│   └── test_real_flash_run.py    ← 真实 FLASH 端到端测试
│
├── scenarios/flash_demo/        ← 旧版 Demo 迁移至此 (向后兼容)
└── output_processors/            ← HDF5 处理 (引擎底层)
```

### 关键设计原则

1. **场景 = 数据, 非逻辑**: Al/Si 的差异在 `defaults_si.py` / `defaults_al.py` 的材料参数, 不涉及代码分支。
2. **不重写已验证代码**: `par_builder.py`, `interpolator.py` 是共享模块, 所有 thin_layer_sandwich 变体共用。
3. **输出可追溯**: 每次运行都写入 `input_params.json`, 可以精确复现。
4. **chk 可保留**: `keep_flash_raw=True` 保留原始 FLASH HDF5, 无需重新仿真即可更换后处理。

---

## 如何创建新场景

### 第一步: 准备 FLASH 源文件

创建目录:

```
scenarios/{physics_topic}/{scenario_name}/
├── sim_input/
│   ├── Config
│   ├── Makefile
│   ├── Simulation_data.F90
│   ├── Simulation_init.F90
│   ├── Simulation_initBlock.F90
│   ├── Grid_markRefineDerefine.F90  (可选)
│   ├── *.cn4
│   └── ...
├── __init__.py
├── par_builder.py     (可选, 可引用共享)
└── interpolator.py    (可选, 可引用共享)
```

> **关于 sim_input**: 包含所有 FLASH Fortran 源文件 + EOS/opacity 表。`FlashSimulatorEngine.run()` 会自动将其复制到运行目录并编译。

### 第二步: 写 `__init__.py`

```python
"""my_scenario — 我的新场景"""

import sys
from pathlib import Path
from flash.scenarios.base import SimulationScenario
from flash.scenarios.registry import register

_HERE = Path(__file__).parent.resolve()

# 引用共享模块 (可选)
_TLS = _HERE.parents[2] / "collision_compression" / "thin_layer_sandwich"
sys.path.insert(0, str(_TLS))
from interpolator import (
    build_variable_grid,
    interpolate_flash_to_grid,
    DEFAULT_OUTPUT_FIELDS,
)

# .par 生成函数
def _build_par(params):
    """生成我的场景的 .par 文件"""
    lines = []
    # ... 填充 .par 内容 ...
    return "\n".join(lines)

# 网格生成函数
def _build_grid(params):
    return build_variable_grid(
        t_min=0,
        t_max=params.get("tmax", 1e-9),
        t_step=1e-11,
    )

# 插值函数
def _interpolate(flash_files, t_grid, x_grid, var_names):
    return interpolate_flash_to_grid(
        flash_files=[str(f) for f in flash_files],
        t_grid=t_grid, x_grid=x_grid,
        var_names=var_names,
    )

# 场景实例
scenario = SimulationScenario(
    name="my_scenario",
    description="一行描述",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "sim_input",
    sim_name="MyScenario",
    run_dir_name="runs_my_scenario",
    flash_setup_args=(
        "-1d +cartesian -nxb=16 "
        "+hdf5typeio species=cham,targ "
        "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
    ),
    default_params={
        "sim_rhoTarg": 2.33,
        "laser_times": [0, 1e-10, 1e-9, 1.1e-9],
        "laser_powers": [0, 5e14, 5e14, 0],
        "tmax": 1.2e-9,
    },
    default_output_fields=DEFAULT_OUTPUT_FIELDS,
    build_par=_build_par,
    build_grid=_build_grid,
    interpolate=_interpolate,
)

register("my_scenario",
         "flash.scenarios.{physics_topic}.{scenario_name}",
         "scenario")
```

### 第三步: 激活场景

在 `scenarios/{physics_topic}/__init__.py` 中添加导入:

```python
from . import my_scenario_name  # noqa: F401 — 触发 __init__.py 中的 register()
```

### 第四步: 验证

```python
from flash.scenarios.registry import list_scenarios, get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

# 能看到新场景
for name, desc in list_scenarios():
    print(f"{name}: {desc}")

# 能生成 .par
sc = get_scenario("my_scenario")
par = sc.build_par(dict(sc.default_params))
print(f".par 长度: {len(par)} bytes")
```

---

## 常见问题

### Q: FLASH 编译失败？

检查:
1. WSL 中 `~/QC/FLASH/FLASH4.8/` 是否存在
2. `sim_input/Config` 中 `DATAFILES` 指向的 `.cn4` 文件是否齐全
3. 场景 `flash_setup_args` 中的 FLASH 单位是否已安装 (`+laser`, `+uhd3t`, `+mgd`)

### Q: `[Diffuse]: computed dt is not positive!`

EOS/opacity 表不匹配。检查:
- 旧 EOS 表 (`he-imx-*.cn4`) 会与此错误 → 使用新 EOS 表或设 `eos_chamEosType = "eos_gam"`
- `rt_mgdNumGroups` 和 `rt_mgdBounds` 必须与 `.cn4` 文件的 grupbd 匹配
- 初始温度不能低于 EOS 表的最低温度节点

### Q: 如何调整输出网格分辨率？

在 `params_overrides` 中传入:

```python
engine.run(params_overrides={
    "output_t_min": 0,
    "output_t_max": 3e-9,
    "output_t_step": 5e-12,   # 更密的时间步
})
```

空间网格由 `build_grid` 函数自动决定（基于 z 方向边界）。

### Q: 如何在不同目录运行（不污染当前目录）？

`run()` 的 `runs_dir` 参数:

```python
output = engine.run(runs_dir="/data/my_runs")
# → /data/my_runs/runs_thin_layer_sandwich_si/000001/
```

### Q: 如何并行运行多个仿真？

每个 `engine.run()` 调用会自增 run_id（`000001`, `000002`, ...），互不冲突。可在 Python 循环中批量运行:

```python
for factor in [1.0, 1.5, 2.0]:
    engine.run(params_overrides={
        "laser_powers": [0, 5e14*factor, 5e14*factor, 0],
    })
```

---

## EOS/Opacity 表 (`.cn4`) 温度单位

所有 `.cn4` 文件的**温度网格单位为 eV**（电子伏特），而非 K（开尔文）。FLASH 在运行时将 `sim_*` 系列参数（如 `sim_teleCham`）中设定的 K 值自动转换为 eV 进行查表。

换算关系:

| 值 | eV | K |
|-----|-----|-----|
| 室温 | 0.025 eV | 290.11375 K |
| 旧 EOS 表下界 | 2.0 eV | 23209 K |
| 新 EOS 表下界 | 0.01 eV | 116 K |

初始温度注意事项:
- **旧 EOS 表**（`he-imx-*`, `polystyrene-imx-008*`）起始温度 **2.0 eV**（≈23209 K），室温 0.025 eV 低于下界。FLASH 会做**外推 (extrapolation)**，简单场景（CH 靶、低功率 Al）可正常使用。
- **新 EOS 表**（`Z02_*`, `Z06_*`, `Z14_*`）起始温度 **0.01 eV**（≈116 K），室温 0.025 eV **在有效范围内**。
- 各场景初始温度:
  - `ch_center` — **290.11375 K**（旧 EOS 表，外推适用）
  - `thin_layer_sandwich_al` — **290.11375 K**（旧 EOS 表，低功率 5e11 稳定）
  - `thin_layer_sandwich_si` — **3500.00 K**（新 EOS 表，高功率 5e14 下扩散求解器在低温时不稳定，详见场景表脚注）
- 如需自定义，在 `params_override` 中传入 `sim_teleCham=290.11375` 等参数。

> 此说明适用于 `sim_tele*`（电子温度）、`sim_tion*`（离子温度）、`sim_trad*`（辐射温度）所有温度参数。

```bash
# 运行所有接口测试 (无需 FLASH, 快速)
cd flash/test/scenarios
python run_all_scenario_tests.py

# 运行真实 FLASH 端到端测试 (需要 5-10 分钟)
python test_real_flash_run.py --scenario thin_layer_sandwich_si
python test_real_flash_run.py --scenario ch_center
```

---

## 许可、致谢与商用

flash-sim 采用双重许可，完整条款见根目录 [README.md 许可章节](../README.md#许可)、[LICENSE](../LICENSE) 与 [NOTICE](../NOTICE)。

- **出版物致谢**：使用本场景系统（flash-sim）产生的任何出版物，请感谢**绵阳市的 PhySimX 团队**开发了该仿真辅助 Python 包。建议文案：*"We acknowledge the PhySimX team (Mianyang, China) for developing the flash-sim auxiliary Python package used in this work."*
- **商用说明**：flash-sim 的 Python 代码以 Apache 2.0 许可，其商用须遵守所有适用许可（含 FLASH 仿真引擎的 FLASH License Agreement §5）；商用场景下的授权与责任以届时适用的许可及书面约定为准。
