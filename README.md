# flash-sim — FLASH 等离子体辐射流体力学仿真 Python 接口

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![FLASH: Separate License](https://img.shields.io/badge/FLASH-Separate_License-orange.svg)](https://flash.rochester.edu)
[![Version](https://img.shields.io/badge/version-0.0.0-green.svg)]()

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
| **版本标签** | `0.0.0` (第零发行版) — `git tag -l` 查看全部 |
| **问题反馈** | 通过 Gitee Issues 提交 (登录后新建 Issue) |

> 发布包已通过全局测试 (233 passed / 3 skipped) 与 FLASH 版权合规检查, (详见 [许可](#许可) 与 [NOTICE](NOTICE))。

---

## 目录

- [概述](#概述)
- [核心特性](#核心特性)
- [模块架构](#模块架构)
- [安装](#安装)
- [快速开始](#快速开始)
- [API 速览](#api-速览)
- [典型工作流](#典型工作流)
- [运行环境](#运行环境)
- [开发指南](#开发指南)
- [文档索引](#文档索引)
- [许可](#许可)

---

## 概述

FLASH 是芝加哥大学 Flash Center 开发的多物理、多维度自适应网格 (AMR) 流体力学仿真框架，广泛应用于激光聚变 (ICF)、天体物理、实验室天体物理等领域。

**重要声明：** `flash-sim` 是独立开发的第三方 Python 接口和自动化工作流工具，**并非** Flash Center for Computational Science 的官方产品，与其无关联。FLASH 仿真引擎需从 [flash.rochester.edu](https://flash.rochester.edu) 单独获取并接受其许可协议。

`flash-sim` 封装了从仿真配置、编译运行到结果分析的完整流程：

```
物理参数设计 → .par 文件生成 → FLASH 编译运行
                                    ↓
                              HDF5 输出处理
                                    ↓
               自适应可视化 (1D/2D/3D) + 物理量分析
```

支持 **独立模式**（作为独立 Python 包使用）和 **PhySimX 插件模式**（作为 `physimx_sim` 的子模块）。

---

## 核心特性

### 场景系统 (`scenarios/`)

| 模块 | 功能 |
|------|------|
| `scenarios/base.py` | `SimulationScenario` 数据类 — 场景声明式配置 |
| `scenarios/registry.py` | 场景注册表 — `get_scenario()`, `list_scenarios()` |
| `simulator.py` | `FlashSimulatorEngine` 统一引擎 — 集成 WSL 执行 + chk 收集 + 插值 + 输出 |

**即插即用**:

```python
from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

engine = FlashSimulatorEngine(get_scenario("thin_layer_sandwich_si"))
output = engine.run()  # 自动编译→运行→插值→输出
```

详见 [`scenarios/README.md`](scenarios/README.md)。

### 仿真输入生成 (`input_gen/`)

| 模块 | 功能 |
|------|------|
| `gen_par/` | 参数化 `.par` 文件生成，支持多维度(1D/2D/3D)，默认值中心化 (`defaults.py`) |
| `gen_config/` | FLASH `Config` 文件生成，模块依赖自动管理 |
| `gen_makefile/` | `Makefile` 生成，含 MPI/HDF5/HYPRE 路径注入 |
| `gen_sim_data/` | `Simulation_data.F90` — 全局仿真数据声明 |
| `gen_sim_init/` | `Simulation_init.F90` — 运行时参数读取和初始化 |
| `gen_sim_initblock/` | `Simulation_initBlock.F90` — 空间网格和物质分配（1D/2D/3D 对称域） |
| `gen_eos_op/` | IONMIX4 格式 `.cn4` EOS/不透明度表生成与复制 |
| `gen_shell_script/` | 平台感知的运行脚本生成（本地 WSL / 超算 SLURM） |
| `gen_checker/` | 依赖检查 + 脉冲/密度/射线可视化诊断 |
| `gen_Grid_markRefineDerefine/` | FLASH 网格细化/粗化 Fortran 生成器 |

### 运行管理 (`flash_run/`)

| 模块 | 功能 |
|------|------|
| `env/` | 多环境管理（本地 WSL / SSH 超算），维度感知资源配置 |
| `remote/` | 远程部署、SSH 多路由自动选择、SBATCH 作业提交/监控/结果下载 |

### 输出处理 (`output_processors/`)

| 模块 | 功能 |
|------|------|
| `hdf5processor/` | 纯 h5py 底层 HDF5 读取，自动检测 1D/2D/3D，AMR 块结构解析；内含 `DataCalculator` 派生变量计算与 `extract_var_yt_style` 坐标重建 |
| `loader/` | `FlashDataLoader` + `FlashDataContainer` 结构化数据加载（自动维度检测、派生变量、全局坐标） |
| `plotter/` | `FlashPlotter` 自适应维度可视化（1D 线图 / 2D 伪彩 / 3D 切片），AMR 网格绘图 |
| `parallel.py` | 多文件 / 多变量 / 多文件夹并行加载与插值加速 |

### 仿真驱动 (`interface.py`)

`FlashSimulator` 类提供统一仿真接口：
- **Mock 模式**：基于 Planck 辐射 / Saha 电离闭合公式的确定性模拟，适合 pipeline 开发和测试
- **Real 模式**：调用本地或远程 FLASH 二进制，解析 HDF5 输出

### 完整 Demo 套件 (`scenarios/flash_demo/`)

- `hello_flash/` — 零依赖快速上手包（一键安装 + 运行 + 分析）
- `LaserSlab1d/` — 1D 激光烧蚀参考仿真文件（含 Config / .par / .cn4）
- `new_struture/` — 自定义对称域 1D 仿真 + CH 靶中心物理量时域分析
- `laserslab1d_local_demo.py` / `laserslab1d_supercomputer_demo.py` — 本地/超算一键运行
- `laserslab1d_hpc_demo_batch.py` — 多功率因子批量仿真工作流

---

## 模块架构

> 本节从**分层架构**、**双模式运行机制**、**端到端数据流**三个角度，说明 `flash` 包如何把"物理参数 → FLASH 运行 → HDF5 输出 → 可视化/分析"串成一条可复用的管线。读完后即可按图索骥定位任一功能的代码位置。

### 分层架构总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 接口/适配层   interface.py (FlashSimulator: mock/real) · __init__.py       │
│               └─ 契约来源：内置 _core/（dataclass schema，自包含）         │
├──────────────────────────────────────────────────────────────────────────┤
│ 输入生成层   input_gen/   gen_par · gen_config · gen_makefile ·            │
│               gen_sim_data · gen_sim_init · gen_sim_initblock ·           │
│               gen_eos_op · gen_shell_script · gen_Grid_markRefineDerefine  │
├──────────────────────────────────────────────────────────────────────────┤
│ 仿真执行层   scenarios/ (base · registry · simulator · 物理场景)           │
│               flash_run/ (env 环境管理 · remote 远程部署) · config/         │
├──────────────────────────────────────────────────────────────────────────┤
│ 输出处理层   output_processors/   hdf5processor → loader → plotter         │
│               (+ parallel 并行加速)                                        │
├──────────────────────────────────────────────────────────────────────────┤
│ 核心抽象层   _core/   interface/BaseSimulator · schema 数据契约 ·          │
│               registry · credentials(加密凭据)                             │
└──────────────────────────────────────────────────────────────────────────┘
        支撑模块: scenarios/flash_demo/ (示例) · docs/ (文档) · scripts/ (工具) · test/ (测试)
```

各层职责：

| 层 | 关键模块/类 | 职责 |
|----|------------|------|
| 接口/适配 | `interface.py::FlashSimulator`, `flash/__init__.py` | 对外统一入口。`mock` 模式用 Planck/Saha 闭式公式产出确定性假数据；`real` 模式调用 FLASH 二进制 |
| 核心抽象 | `_core/interface.py::BaseSimulator`, `_core/schema.py` | 定义 `capability()` / `simulate()` 契约与 `SimulationRequest` / `SimulationResult` 数据结构；凭据经 `credentials.py` (Fernet) 加密 |
| 输入生成 | `input_gen/*/generator.py` | 把结构化参数翻译成 FLASH 需要的 `.par`、Fortran 源、`Config`、`Makefile`、`.cn4` 表、运行脚本 |
| 仿真执行 | `scenarios/simulator.py::FlashSimulatorEngine`, `flash_run/env`, `flash_run/remote` | 编排"编译 → 运行 → 采集 → 插值 → 保存"；管理本地 WSL 与超算 SSH/SLURM 环境 |
| 输出处理 | `output_processors/{hdf5processor,loader,plotter,parallel}` | 纯 h5py 解析 FLASH AMR HDF5，结构化加载，自适应 1D/2D/3D 绘图 |

### 自包含运行机制

`flash` 是**完全自包含**的独立包：基础契约（`BaseSimulator`、`SimulationRequest`、
`SimulationResult` 等 schema）全部定义在内置的 `_core/` 子包中，不依赖任何
PhySimX 内部包，所有运行时依赖均可从 PyPI 解析。

```python
# flash/__init__.py 与 interface.py 中
from ._core.interface import BaseSimulator      # dataclass 版契约
from ._core.schema import SimulationRequest     # 无 pydantic 依赖
```

- 安装即用：`pip install -e ".[full,dev]"` 之后 `import flash` 立即可用，无需任何额外私有源。
- `flash.__standalone__` 常量恒为 `True`，保留该常量仅为向后兼容。

### 端到端数据流

`FlashSimulatorEngine.run(params_override)` 是管线的中枢，单条调用串起下述全部步骤（源码见 `scenarios/simulator.py`）：

```
参数 override
   │ ① scenario.default_params 合并 override
   ▼
构建运行目录 runs/{id}/
   ├─ sim_input/          ← .F90 / Config / Makefile / .cn4 + {sim_name}.par
   ├─ sim_output/         ← FLASH 原始 chk 文件（keep_flash_raw=True 时保留）
   ├─ database/flash_in/  ← input_params.json + run.log
   └─ database/flash_out/ ← result.h5（最终规整网格插值结果）
   │ ② build_par(params) 生成 .par；复制源文件；生成预诊断图
   ▼
③ 生成 run_flash.sh / submit_flash.sh（WSL / SLURM 双版本，LF 换行）
   │
   ▼
④ WSL:  setup -auto … → make -j → mpirun ./flash4
      （超算:  sbatch submit_flash.sh → srun ./flash4）
   │ 产出 lasslab_hdf5_chk_*（FLASH AMR checkpoint）
   ▼
⑤ 从 WSL /tmp 采集 HDF5 回本地临时目录
   │
   ▼
⑥ scenario.build_grid(params)       构造 (t_grid, x_grid)
   scenario.interpolate(flash_files, t_grid, x_grid, fields)  变分辨率插值
   │
   ▼
⑦ _save_output_hdf5 → database/flash_out/result.h5
   （数据集 t, x, {field:(Nt,Nx)} + 输入参数 attrs，gzip 压缩）
   │
   ▼
⑧ 自动诊断图 → sim_output_plots/（profile / t-x / center_evolution）
```

**输出数据的两种消费方式**：

1. **引擎内置（端到端）**：`result.h5` 是统一规整网格 `(t, x)` 的压缩 HDF5，便于后续优化与跨算例对比。
2. **output_processors 独立消费（原始 AMR 文件）**：直接解析 FLASH 产出的 checkpoint/plot 文件：

```python
from flash.output_processors.loader import FlashDataLoader
from flash.output_processors.plotter import FlashPlotter

loader = FlashDataLoader("lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)        # 自动计算派生变量
print(container.ndim, container.nblocks, container.simulation_time)
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png")
```

   其链路为：`FlashHDF5File`（解析 AMR 块结构 + `extract_var_yt_style` 坐标重建，纯 h5py 无需 yt）→ `FlashDataLoader` / `FlashDataContainer`（结构化容器）→ `FlashPlotter`（自适应 1D 线图 / 2D 伪彩 / 3D 切片）。派生变量（电子密度梯度、压强等）由 `hdf5processor.DataCalculator` 在加载时自动计算。

### 场景驱动机制（即插即用入口）

所有物理问题都封装为 `SimulationScenario` 数据类，引擎只关心它的三个可调用钩子：

| 钩子 | 签名 | 作用 |
|------|------|------|
| `build_par` | `(params) → str` | 生成 FLASH `.par` 内容 |
| `build_grid` | `(params) → (t_grid, x_grid)` | 定义输出规整网格 |
| `interpolate` | `(flash_files, t_grid, x_grid, var_names) → {field: array}` | 把 AMR chk 插值到规整网格 |

新增场景只需：在 `sim_input_dir` 备好 `.F90` / `Config` / `.cn4` → 定义 `scenario = SimulationScenario(...)` → `register("name", __name__)` → 引擎即可 `get_scenario("name").run()`。

### 目录地图（实际结构）

```
flash/
├─ interface.py            # FlashSimulator（旧版 mock/real 统一接口）
├─ _core/                  # 核心抽象：BaseSimulator / schema / registry / credentials(加密)
├─ scenarios/              # 场景系统
│  ├─ base.py              #   SimulationScenario 数据类
│  ├─ registry.py          #   register / get_scenario / list_scenarios
│  ├─ simulator.py         #   FlashSimulatorEngine 统一引擎（管线中枢）
│  └─ {collision_compression, center_evolution, plasma_preparation}/  # 物理场景
├─ input_gen/              # 输入生成（按产物分子包，每个含 generator.py）
│  ├─ gen_par/  gen_config/  gen_makefile/  gen_sim_data/  gen_sim_init/
│  ├─ gen_sim_initblock/  gen_eos_op/  gen_shell_script/  gen_Grid_markRefineDerefine/
├─ flash_run/              # 运行管理
│  ├─ env/                 #   FlashEnvManager / FlashEnvironment / resource_config
│  └─ remote/              #   FlashRemoteDeploy（SSH/SFTP + SBATCH + 路由优选）
├─ output_processors/      # 输出处理
│  ├─ hdf5processor/       #   FlashHDF5File / DataCalculator / DATA_CONFIG
│  ├─ loader/              #   FlashDataLoader / FlashDataContainer
│  ├─ plotter/             #   FlashPlotter（自适应维度）
│  └─ parallel.py          #   多文件 / 多变量并行加速
├─ config/                 # FlashConfig 运行配置
├─ scenarios/flash_demo/  # 参考示例与一键脚本
├─ docs/ scripts/ utils/   # 文档 / Git 工具 / 辅助脚本
└─ test/                   # 测试套件
```

---

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone <your-repo-url>
cd flash

# 安装核心依赖
pip install -e .

# 安装完整功能（含 h5py / matplotlib / yt）
pip install -e ".[full]"

# 安装开发工具
pip install -e ".[dev]"

# 建议安装好后运行flash\scripts\run_global_tests.py进行全局测试
```

### 最小依赖（独立模式）

```
cryptography>=41.0   # 凭据加密
numpy>=1.24          # 数值计算
pydantic>=2.0        # 数据校验
```

### 可选依赖

| 依赖包 | 用途 | 安装方式 |
|--------|------|----------|
| `h5py>=3.8` | HDF5 文件读取 | `pip install h5py` |
| `matplotlib>=3.7` | 可视化 | `pip install matplotlib` |
| `yt>=4.1` | FLASH HDF5 专业可视化 | `pip install yt` |
| `paramiko` | SSH 远程连接 | `pip install paramiko` |

---

## 快速开始

### 0. 环境准备

```bash
# WSL 上确保 FLASH 4.8 已安装
./setup -auto ...  # (按 FLASH 安装文档)
```

### 0.5 两个常用脚本入口（推荐）

仓库根目录提供两个开箱即用的脚本，覆盖「安装验证」与「场景仿真」两类日常操作。

**① `start_flash.py` — 一键安装 + 全局测试 + 报告**

自动完成：检查/创建项目专属虚拟环境 `.venv` → 安装 flash 包及全部依赖 → 运行三套全局测试 → 生成纯文本报告 `INSTALL_TEST_REPORT.txt`。

```bash
python start_flash.py   # 用系统 Python 运行（自动创建 .venv，约 3-4 分钟）
```

- 虚拟环境：项目根目录 `.venv`（被 .gitignore 排除、不随仓库分发；不存在时自动全新创建，存在则复用，设 `FLASH_FORCE_CLEAN=1` 强制重建）；
  首次运行需要手动设置一下 *Python解释器*
- 报告内容：安装验证、三套件统计（framework / input_gen / output_processors）、失败明细
- 环境隔离：绝不触碰共享环境（如 `envs/default`）

**② `laserslab1d_local_custom.py` — LaserSlab 1D 场景仿真（超算 / 本地 WSL 双模式）**

`scenarios/center_evolution/ch_center/` 下的可配置一维对称域 LaserSlab 仿真：CH 靶居中、两侧真空、两束 351nm 激光相向入射。自动完成：生成 FLASH 输入文件 → 运行（超算 SLURM 或本地 WSL）→ HDF5 分析 → 输出 PNG。

```bash
# 超算模式（默认，需 SSH 凭据 flash_ssh）
.venv\Scripts\python.exe scenarios\center_evolution\ch_center\laserslab1d_local_custom.py

# 本地 WSL 模式：将脚本顶部 RUN_MODE 改为 "wsl" 后运行
```

- 运行模式：脚本顶部 `RUN_MODE = "hpc"`（超算）/ `"wsl"`（本地 WSL），一行切换
- EOS 表：使用随仓库分发的自研 ionmix 表（`Gen_eos_op_data/`：`ch_mix` / `helium_hires`），克隆即自带，无需额外获取 FLASH 分发原始表
- 输出：`scenarios/center_evolution/ch_center/flash_output/plots/{dens,tele,trad}_hpc.png`（超算）/ `{dens,tele,trad}_wsl.png`（本地）

### 1. 场景系统 — 即插即用（推荐）

```python
import sys
sys.path.insert(0, "path/to/physimx_sim/src/physimx_sim")

from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

# 列出所有可用场景
from flash.scenarios.registry import list_scenarios
for name, desc in list_scenarios():
    print(f"{name}: {desc}")

# 运行一个场景 (自动完成: 编译 → 运行 → 插值 → 输出)
engine = FlashSimulatorEngine(get_scenario("thin_layer_sandwich_si"))
output = engine.run()

print(f"✅ 输出 HDF5: {output.result_h5_path}")
print(f"   运行目录:   {output.run_dir}")
print(f"   chk 文件:   {output.n_chk}")
print(f"   输出字段:   {output.fields}")
```

详见 [`scenarios/README.md`](scenarios/README.md)。

### 2. 仿真输入生成

```python
from flash.input_gen.gen_par.generator import ParGeneratorExtended

gen = ParGeneratorExtended()
par_content = gen.generate(
    dimension=1,
    sim_name="LaserSlab1D",
    tmax=1.0e-9,
    nblockx=4,
    lrefine_max=6,
)
with open("laserslab.par", "w") as f:
    f.write(par_content)
```

### 3. HDF5 输出分析

```python
from flash.output_processors.loader import FlashDataLoader
from flash.output_processors.plotter import FlashPlotter

# 加载 checkpoint 文件
loader = FlashDataLoader("laserslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)

print(f"仿真时间: {container.simulation_time:.4e} s")
print(f"维度: {container.ndim}D, 块数: {container.nblocks}")
print(f"变量: {list(container.data.keys())}")

# 自适应维度绘图
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png",
             title="Density Distribution")
plotter.plot("tele", save_path="tele.png",
             title="Electron Temperature")
```

### 4. 远程超算运行

```python
from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    # 上传参数文件
    deploy.upload("laserslab.par", "~/run/laserslab.par")

    # 提交 SLURM 作业
    job_id = deploy.submit_job(
        par_file="laserslab.par",
        nprocs=4,
        wall_time="01:00:00",
        job_name="LaserSlab1D",
    )
    print(f"Job submitted: {job_id}")

    # 等待完成并下载结果
    deploy.wait_for_job(job_id, timeout=3600)
    deploy.download_results(
        remote_output_dir="~/run",
        local_output_dir="./outputs",
        pattern="*.h5",
    )
```

### 5. 使用 `FlashSimulator` 统一接口

```python
from flash import FlashSimulator
from flash._core.schema import SimulationRequest

sim = FlashSimulator(mock=True)
result = sim.simulate(SimulationRequest(
    request_id="demo-001",
    params={"temperature": 5000.0, "density": 1e-3},
))
print(result.output_data)
```

---

## API 速览

### 核心类

| 类 | 包路径 | 说明 |
|----|--------|------|
| `FlashSimulatorEngine` | `flash.scenarios.simulator` | **统一仿真引擎** — 场景驱动, 封装 WSL 执行 + 插值 + 输出管线 |
| `SimulationScenario` | `flash.scenarios.base` | 场景声明式配置数据类 |
| `FlashSimulator` | `flash` | 旧版统一仿真接口, 支持 mock/real 双模式 (旧接口) |
| `FlashConfig` | `flash.config` | 全局配置管理器 |
| `ParGeneratorExtended` | `flash.input_gen.gen_par.generator` | `.par` 参数文件生成器 |
| `ConfigGenerator` | `flash.input_gen.gen_config.generator` | `Config` 文件生成器 |
| `BlockGenerator` | `flash.input_gen.gen_sim_initblock.generator` | `Simulation_initBlock.F90` 生成器 |
| `FlashHDF5File` | `flash.output_processors.hdf5processor.flash_hdf5` | 底层 HDF5 文件读取器 |
| `FlashDataLoader` | `flash.output_processors.loader.data_loader` | 结构化数据加载器 |
| `FlashDataContainer` | `flash.output_processors.loader.data_loader` | 数据容器（含 data / derived / grid） |
| `FlashPlotter` | `flash.output_processors.plotter.plot_generator` | 自适应维度绘图器 |
| `FlashEnvManager` | `flash.flash_run.env.env_manager` | 多环境管理器 |
| `FlashRemoteDeploy` | `flash.flash_run.remote.remote_deploy` | 远程部署管理器 |

### CLI 命令

```bash
# 凭据管理交互式菜单
flash-cred

# 启动初始化配置
flash-setup
```

---

## 典型工作流

### 1. 完整仿真工作流

```
Config 编译配置  →  setup + make →  FLASH 二进制
     ↑                              ↓
  生成 Config                    生成 .par  →  mpirun
  (gen_config/)                              (flash_run/)
                                                 ↓
                                             HDF5 输出
                                                 ↓
                                        output_processors/
                                        自适应绘图 + 分析
```

### 2. 批量参数扫描

```python
# 多功率因子批量仿真
from flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch import (
    create_power_variants, deploy_to_supercomputer,
    run_flash_remotely, analyze_and_plot,
)

power_factors = [0.5, 1.0, 1.5, 2.0]
variants = create_power_variants(power_factors)
deploy_to_supercomputer(variants)
job_ids = run_flash_remotely(variants)
analyze_and_plot(variants)
```

### 3. 自定义网格细化

`input_gen/gen_Grid_markRefineDerefine/` 提供 FLASH `Grid_markRefineDerefine.F90` 的 Python 生成器，支持密度/温度梯度和多物质界面的自适应加密。

### 4. 多环境管理与切换

```python
from flash.flash_run.env import get_env_manager

mgr = get_env_manager()
print(mgr.summary())
# [local_wsl] LOCAL(WSL) - 当前
# [supercomputer_nc_e] SSH(flash_ssh)
# [supercomputer_bscc_t6] SSH(flash_ssh_2)

mgr.set_active("supercomputer_nc_e")
```

---

## 运行环境

flash-sim 支持三平台部署：

| 平台 | 访问方式 | MPI | HDF5 | HYPRE | 典型核数 |
|------|----------|-----|------|-------|----------|
| 本地 WSL (Ubuntu) | 本地 | 源码编译 → `/usr/local/mpich/` | 源码编译 → `/usr/local/hdf5/` | 源码编译 → `/usr/local/hypre/` | 1 |
| ParaCloud NC-E | SSH port 22 | `module load mpich/3.2-gcc9.3` | `module load hdf5/1.8.18` | 用户空间 `~/QC/FLASH/local/hypre/` | 4 |
| ParaCloud BSCC-T6 | SSH port 8443 | `module load mpich/3.2-gcc9.3` | `module load hdf5/1.8.18` | 用户空间 `~/QC/FLASH/local/hypre/` | 4 |

> **关键提示**: FLASH的默认安装路径为"~/QC/FLASH/FLASH4.8"，其中"QC"是专属用户名，可在"flash\\_core\credentials\manage.py"设置。
> **HPC 关键提示**: 超算上 HYPRE_PATH 可能因符号链接 `/public1/home → /publicfs01/fs1-e/home` 导致编译失败。必须使用 `readlink -f` 解析真实路径后写入 `Makefile.h`。
---

## 开发指南

### 代码规范

- **行尾**: 所有文件强制 Unix LF（`.gitattributes` 已配置）
- **格式化**: Black (`--line-length=120`), Ruff linting
- **绘图**: 全英文字符，标题≥24pt，标签≥20pt，DPI≥450
- **Python**: 3.10+，类型注解优先

### 运行测试

```bash
# Flash 框架测试（核心）
make test
# 或
pytest test/ -v

# 全局测试（全部模块）
make test-all

# 代码检查
make lint
make format
```

### Git 工作流

```bash
# 安装 Git 钩子（pre-commit + pre-push）
bash scripts/install-git-hooks.sh

# 提交触发 ≈ 代码风格检查
# 推送触发 ≈ 框架测试
# 打标签前运行全局测试:
bash scripts/git-tag-with-test.sh v1.0.0

# 完整发布流程（格式检查 + 测试 + 构建 + 打标签）
bash scripts/tag-release.sh v1.0.0
```

### 发布

```bash
# 构建分发包
make build
# 或
python -m build

# 产物在 dist/
# flash-sim-1.0.0.tar.gz, flash_sim-1.0.0-py3-none-any.whl
```

---

## 文档索引

### 根目录文档

| 文件 | 说明 |
|------|------|
| `README.md` | **本文档** — 项目概述与快速入门 |
| `scenarios/README.md` | **场景系统使用指南** — 即插即用仿真入口 |
| `docs/README.md` | FLASH 仿真使用指南（详细版，含所有子模块 API） |
| `docs/flash_operation_standard.md` | 仿真操作规范（绘图语言/行尾格式/运行流程） |
| `docs/flash_simulation_execution_knowledge.md` | 仿真执行知识库（LaserSlab 变体/SLURM/HDF5 复合类型） |
| `docs/par_format_guide.md` | `.par` 排版规范 |
| `docs/GIT_WORKFLOW.md` | Git 工作流与测试分层策略 |
| `docs/VERSIONING.md` | 版本号命名协议 (SemVer) |
| `docs/skills-map.md` | 技能 ↔ 文档 ↔ Python 模块索引 |
| `flash_run/PROCESS.md` | 仿真运行流程（环境配置→SSH→提交→监控→后处理） |

### 子模块文档

| 文档 | 位置 |
|------|------|
| Output Processors 使用说明 | `output_processors/docs/output_processors_usage.md` |
| Hello FLASH 快速上手 | `scenarios/flash_demo/hello_flash/README.md` |
| 网格细化实施指南 | `input_gen/gen_Grid_markRefineDerefine/README.md` |
| 新参数生成指南 | `input_gen/gen_newpara/README.md` |
| F90 参考文件详解 | `input_gen/gen_otherf90s/ref_f90s/FLASH_F90_参考文件详解_总览.md` |
| 多区密度剖面参考 | `input_gen/gen_newpara/RP_Reference.md` |

### Skills (WorkBuddy AI 辅助)

- `flash-orchestrator-activator` — 模块编排入口
- `input-gen-generator` — 仿真输入文件生成
- `physimx-workflow-orchestrator` — 工作流编排

---

## 许可

flash-sim 采用**双重许可结构**，并严格遵守 [FLASH License Agreement](docs/license_agreement.txt)（官方协议全文见 `docs/license_agreement.txt`）：

| 组件 | 许可 | 说明 |
|------|------|------|
| **flash-sim Python 代码** | [Apache 2.0](LICENSE) | PhySimX Contributors 原创 wrapper / 工具 / 工作流代码 |
| **FLASH 仿真引擎** | [FLASH License Agreement](https://flash.rochester.edu) | 由 Flash Center for Computational Science 开发维护 |

**重要说明（依据 FLASH License Agreement）：**

- **本包不包含、亦不再分发** FLASH 源代码、二进制、源码包、SimulationMain 示例（含 LaserSlab）、FLASH 分发的 EOS/不透明度表（`*.cn4` 等）、FLASH 用户手册、IONMIX 源码或 MultiEOS 数据（协议 §3 禁止用户再分发 FLASH Code 及其任何组件）。
- 用户必须从 [flash.rochester.edu](https://flash.rochester.edu) **独立获取** FLASH 并接受其许可协议后才能使用本包。
- 包内场景输入中的部分 `.F90` 文件（如 `Simulation_data.F90` 等）是 FLASH 示例问题的**修改版**，已按协议 §4(a) 在文件头与 [NOTICE](NOTICE) 中声明修改、保留 FLASH 头（§4(c)）并显示致谢（§4(b)）。
- FLASH 的商业使用需获得 Flash Center 主任的事先书面批准（FLASH License §5）。
- 使用 FLASH 的所有出版物必须致谢 Flash Center（详见 [NOTICE](NOTICE) 文件）。

### flash-sim 包附加条款：PhySimX 团队致谢与商用说明

flash-sim（flash 仿真辅助 Python 包）由**绵阳市的 PhySimX 团队**原创开发。除 FLASH Center 的致谢要求外，另有以下附加条款：

**出版物致谢（Publications Acknowledgment）**

使用 flash-sim 产生的任何出版物，请在致谢部分感谢**绵阳市的 PhySimX 团队**开发了该仿真辅助 Python 包。建议致谢文案：

> "We acknowledge the PhySimX team (Mianyang, China) for developing the flash-sim auxiliary Python package used in this work."

**商用说明（Commercial Use）**

flash-sim 的 Python 代码以 Apache 2.0 许可，但其商用须遵守所有适用许可条款，包括 FLASH 仿真引擎的 [FLASH License Agreement](https://flash.rochester.edu) §5（商用须经 Flash Center 主任事先书面批准）。本包由绵阳市的 PhySimX 团队原创开发，商用场景下的授权与责任以届时适用的许可及书面约定为准。

> 注：Apache 2.0 仅覆盖本包的 Python 代码，不授予 FLASH 仿真引擎的任何商用权利；flash-sim 不对任何商用后果作担保。

© 2026 PhySimX Contributors. Apache 2.0 License.

---

> **flash-sim v1.0.0** — Build FLASH simulations smarter, not harder. ⚡


---

# flash-sim — English Overview

**flash-sim** is a full-featured Python interface and automation toolkit for the
[FLASH](https://flash.rochester.edu) high-energy-density physics (HEDP) simulation
code. It provides an end-to-end workflow: physics scenario design → `.par` file
generation → FLASH compile & run → HDF5 output processing → adaptive visualization
(1D/2D/3D) and physical analysis.

## Repository

Hosted on **Gitee (Chinese GitHub-equivalent platform)**:

```
https://gitee.com/physimx/flash
```

Clone with HTTPS: `git clone https://gitee.com/physimx/flash.git`

## Key Features

- **Scenario System** (`scenarios/`): declarative `SimulationScenario` definitions,
  a registry (`get_scenario()` / `list_scenarios()`), and a unified
  `FlashSimulatorEngine` that integrates WSL/remote execution, checkpoint
  collection, interpolation and result output.
  Built-in scenarios: `ch_center`, `grad_dens_sandwich`,
  `thin_layer_sandwich_si`, `thin_layer_sandwich_al`.
- **Input Generation** (`input_gen/`): parameter-file editor/calculator, EOS &
  opacity table tooling, Makefile generation, shell-script generation.
- **Output Processing** (`output_processors/`): HDF5 loading (1D/2D/3D), derived
  variables, unit conversion, batch/lazy loading, AMR visualization.
- **Multi-Environment Execution**: local WSL (Ubuntu) and HPC clusters over SSH
  (ParaCloud), with SLURM/SBATCH support.
- **Credential Management** (`_core/credentials/`): encrypted storage for Gitee
  tokens, SSH accounts and API keys.
- **Dual Mode**: standalone Python package (`flash.*`) or PhySimX plugin
  (`physimx_sim.flash.*`).

## Quick Start

```python
from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

scenario = get_scenario("thin_layer_sandwich_si")
engine = FlashSimulatorEngine(scenario, verbose=True)
output = engine.run(run_flash=False)   # dry-run: generate inputs only
```

See [README.md] (Chinese) for the full documentation, or run the global test
suite:

```bash
python scripts/run_global_tests.py     # framework + input + output suites
```

## License

flash-sim is dual-licensed: the Python wrapper/tool code is **Apache 2.0**
(© 2026 PhySimX Contributors); the FLASH simulation engine is governed by the
separate [FLASH License Agreement](https://flash.rochester.edu). This package
does **not** redistribute any FLASH source code, binaries, distributed EOS /
opacity tables (`*.cn4` etc.), user manuals, IONMIX sources or MultiEOS data
(per §3 of the FLASH License). Obtain FLASH independently from
[flash.rochester.edu](https://flash.rochester.edu).

**flash-sim Package — PhySimX Team Attribution (additional terms)**

*Publications Acknowledgment.* Any publication resulting from the use of
flash-sim (the flash auxiliary Python package) should acknowledge the
**PhySimX team (Mianyang, China)** for developing this auxiliary
Python package. Suggested text: "We acknowledge the PhySimX team
(Mianyang, China) for developing the flash-sim auxiliary Python
package used in this work."

*Commercial Use.* The flash-sim Python code is released under Apache 2.0,
but any commercial use must comply with all applicable licenses, including
Section 5 of the FLASH License Agreement (commercial use of FLASH requires
prior written approval from the Director of the Flash Center). flash-sim was
originally developed by the PhySimX team (Mianyang, China); commercial
licensing and liability are governed by the applicable license and any
written agreement in force at the time. The Apache 2.0 license covers only
the flash-sim Python code and does not grant any commercial rights to the
FLASH simulation engine.

## Contact

- Repository: https://gitee.com/physimx/flash
- Issues & feedback: via Gitee Issues

*English overview generated for search-engine discoverability. The authoritative
documentation remains the Chinese README above.*

