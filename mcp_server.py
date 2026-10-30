# -*- coding: utf-8 -*-
"""flash-sim MCP Server — 零第三方依赖的 Model Context Protocol stdio server.

为 flash-sim 项目 (FLASH 等离子体辐射流体力学仿真 Python 接口) 提供 MCP 接入:
任何 Agent 连接本 server 后, 可从零快速理解并使用整个 flash 项目包
(项目概述 / 场景清单 / API 参考 / 工作流指南 / 文档搜索 / 环境自检)。

实现说明
--------
* 纯 Python 标准库实现 (json / sys / os / pathlib / subprocess 等),
  **不依赖** `mcp` / `fastmcp` 包 —— 目标环境可能未安装这些包。
* 协议: MCP JSON-RPC 2.0 over stdio。**每行一个 JSON 对象** (换行分隔,
  非 LSP Content-Length 头风格)。MCP 官方 stdio 传输即采用换行分隔 JSON,
  与本实现一致。
* 支持方法: initialize, notifications/initialized, ping, tools/list,
  tools/call, resources/list, resources/read, resources/templates/list,
  logging/setLevel (no-op)。

WorkBuddy 接入方法
------------------
在 `~/.workbuddy/mcp.json` 的 `mcpServers` 中添加 (路径按实际环境替换,
**本文件不含任何硬编码绝对路径**; args 的第二个元素即本文件的绝对路径)::

    "flash-docs": {
        "command": "<python.exe 绝对路径>",
        "args": ["<本文件绝对路径>"]
    }

保存后重启会话, 并在「连接器管理页」对该 MCP server 点击 **Trust** 激活。

运行自测 (Windows Git Bash)::

    printf '%s\\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \\
                  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \\
                  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \\
                  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"flash_overview","arguments":{}}}' \\
        | python mcp_server.py
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 项目根目录定位: 本文件位于仓库根目录 (与 start_flash.py 同级)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# 源码仓库模式 = PROJECT_ROOT 下有 README.md/docs/; wheel 安装模式
# (flash/mcp_server.py 随包分发) 下文档工具无法工作, 会在 env_check 中提示。
IS_SOURCE_CHECKOUT: bool = (PROJECT_ROOT / "README.md").is_file()

SERVER_NAME = "flash-docs"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

# 文档搜索/读取时跳过的目录名
SKIP_DIRS = {"flash_src", "__pycache__", "runs", ".venv", ".venv-win", ".venv-linux", ".venv-mac", ".git"}

# read_doc 白名单外仍允许读取的约束: 必须在 PROJECT_ROOT 下且后缀为 .md
MAX_SEARCH_HITS_DEFAULT = 10
MAX_DOC_CHARS_DEFAULT = 20000

# ---------------------------------------------------------------------------
# 内置知识内容 (来自 README.md / docs/, 已人工核实)
# ---------------------------------------------------------------------------

OVERVIEW_TEXT = f"""\
# flash-sim 项目概览

**flash-sim** 是 FLASH 高能量密度物理 (HEDP) 仿真代码的全功能 Python 封装
(Gitee: https://gitee.com/physimx/flash)。提供**场景系统**（即插即用仿真入口）、
参数文件生成、多环境运行管理、HDF5 输出分析与自适应可视化的一站式工作流:

    物理参数设计 → .par 文件生成 → FLASH 编译运行
                                      ↓
                                HDF5 输出处理
                                      ↓
                 自适应可视化 (1D/2D/3D) + 物理量分析

注意: flash-sim 是第三方 Python 接口 (Apache 2.0, PhySimX 团队), FLASH 引擎本身
需从 flash.rochester.edu 单独获取。本包不分发任何 FLASH 源码/二进制/EOS 表。

## 分层架构 (项目根: {PROJECT_ROOT})

| 层 | 模块 | 职责 |
|----|------|------|
| 接口/适配层 | interface.py (FlashSimulator: mock/real), __init__.py | 对外统一入口; mock 模式用 Planck/Saha 闭式公式, real 模式调 FLASH 二进制 |
| 输入生成层 | input_gen/ (gen_par, gen_config, gen_makefile, gen_sim_data, gen_sim_init, gen_sim_initblock, gen_eos_op, gen_shell_script, gen_Grid_markRefineDerefine ...) | 结构化参数 → .par / Fortran 源 / Config / Makefile / .cn4 表 / 运行脚本 |
| 仿真执行层 | scenarios/ (base, registry, simulator), flash_run/ (env, remote) | FlashSimulatorEngine 编排 "编译→运行→采集→插值→保存"; 本地 WSL 与超算 SSH/SLURM |
| 输出处理层 | output_pro/ (hdf5pro → loader → plotter, parallel) | 纯 h5py 解析 FLASH AMR HDF5, 结构化加载, 自适应 1D/2D/3D 绘图 |
| 核心抽象层 | _core/ (BaseSimulator, schema, registry, credentials) | capability()/simulate() 契约, SimulationRequest/Result 数据结构, 加密凭据 |

## 5 分钟上手步骤

1. **环境安装/自检** (自愈式): `python start_flash.py` — 创建平台专属 venv
   (Windows→.venv-win, Linux/WSL→.venv-linux), 安装依赖, 跑三套全局测试,
   生成 INSTALL_TEST_REPORT.txt。只装不测: `python start_flash.py --no-tests`。
2. **一键场景仿真** (默认 RUN_MODE="wsl", 零修改即可跑):
   Windows:  `.venv-win\\Scripts\\python.exe flash\\scenarios\\center_evolution\\ch_center\\laserslab1d_local_custom.py`
   WSL:      `.venv-linux\\bin\\python flash/scenarios/center_evolution/ch_center/laserslab1d_local_custom.py`
   超算模式: 脚本顶部 RUN_MODE 改 "hpc", 或环境变量 `FLASH_RUN_MODE=hpc`。
3. **场景系统调用**:
   ```python
   from flash.scenarios.core.registry import get_scenario, list_scenarios
   from flash.scenarios.core.simulator import FlashSimulatorEngine
   engine = FlashSimulatorEngine(get_scenario("thin_layer_sandwich_si"))
   output = engine.run()   # 自动编译→运行→插值→输出
   ```
4. **HDF5 分析**: `FlashDataLoader("...chk_0001").load(compute_derived=True)`
   → `FlashPlotter(container).plot("dens", save_path="dens.png")`。

## start_flash.py 用法 (统一部署入口)

    python start_flash.py                                  # 在线安装 + 三套测试 + 报告
    python start_flash.py --no-tests                       # 只装环境
    python start_flash.py --make-wheelhouse                # 联网机造 wheelhouse
    python start_flash.py --export-usb D:\\usb_pkg          # 导出 U 盘离线包
    python start_flash.py --offline --wheelhouse D:\\pkg\\wheelhouse   # 离线安装 + 测试
    python start_flash.py --offline --check                # 只校验不改动

高级变量: FLASH_VENV_DIR / FLASH_FORCE_CLEAN=1 / FLASH_NO_AUTO_REBUILD=1 /
FLASH_SIM_USER_DIR (指定 FLASH 安装用户目录)。
"""

MODULE_MAP_TEXT = """\
# flash-sim 模块地图 (分层架构 → 文件路径)

| 层 | 关键类 | 文件路径 (相对 PROJECT_ROOT) |
|----|--------|------------------------------|
| 接口/适配 | FlashSimulator (mock/real) | `flash/interface.py`; 导出: `flash/__init__.py` |
| 接口/适配 | FlashConfig 全局配置 | `flash/config/` |
| 核心抽象 | BaseSimulator 契约 | `flash/_core/interface.py` |
| 核心抽象 | SimulationRequest/Result schema | `flash/_core/schema.py` (无 pydantic 依赖) |
| 核心抽象 | 凭据加密 (Fernet) | `flash/_core/credentials/` |
| 输入生成 | ParGeneratorExtended (.par) | `flash/input_gen/gen_par/generator.py` |
| 输入生成 | ConfigGenerator | `flash/input_gen/gen_config/generator.py` |
| 输入生成 | MakefileGenerator | `flash/input_gen/gen_makefile/generator.py` |
| 输入生成 | SimDataGenerator (Simulation_data.F90) | `flash/input_gen/gen_sim_data/generator.py` |
| 输入生成 | SimInitGenerator (Simulation_init.F90) | `flash/input_gen/gen_sim_init/generator.py` |
| 输入生成 | BlockGenerator (Simulation_initBlock.F90) | `flash/input_gen/gen_sim_initblock/generator.py` |
| 输入生成 | EOSOpacityGenerator (.cn4 表) | `flash/input_gen/gen_eos_op/` (表数据: `eos_op_data/Gen_eos_op_data/`) |
| 输入生成 | ShellScriptGenerator (WSL/SLURM 脚本) | `flash/input_gen/gen_shell_script/generator.py` |
| 输入生成 | gen_checker 依赖检查 + 诊断绘图 | `flash/input_gen/gen_checker/` |
| 输入生成 | GridMarkRefineDerefineGenerator (AMR 细化) | `flash/input_gen/gen_Grid_markRefineDerefine/` |
| 输入生成 | NewParaGenerator 多区密度剖面 | `flash/input_gen/gen_newpara/` |
| 仿真执行 | SimulationScenario 数据类 | `flash/scenarios/base.py` |
| 仿真执行 | register / get_scenario / list_scenarios | `flash/scenarios/registry.py` |
| 仿真执行 | FlashSimulatorEngine 管线中枢 | `flash/scenarios/simulator.py` |
| 仿真执行 | 场景: ch_center (一键入口脚本) | `flash/scenarios/center_evolution/ch_center/` (`laserslab1d_local_custom.py`) |
| 仿真执行 | 场景: sandwich 三明治靶 | `flash/scenarios/sandwich/` |
| 仿真执行 | 场景: plasma_preparation | `flash/scenarios/plasma_preparation/` |
| 仿真执行 | 环境管理 FlashEnvManager | `flash/flash_run/env/env_manager.py` |
| 仿真执行 | 远程部署 FlashRemoteDeploy (SSH/SFTP/SBATCH) | `flash/flash_run/remote/remote_deploy.py` |
| 输出处理 | FlashHDF5File / DataCalculator (AMR 块解析) | `flash/output_pro/hdf5pro/flash_hdf5.py` |
| 输出处理 | FlashDataLoader / FlashDataContainer | `flash/output_pro/loader/data_loader.py` |
| 输出处理 | FlashPlotter (1D 线图/2D 伪彩/3D 切片, x-t 图) | `flash/output_pro/plotter/plot_generator.py` |
| 输出处理 | parallel 并行加载/插值 | `flash/output_pro/parallel.py` |
| 示例/支撑 | Demo 套件 (hello_flash 一键入门包等) | `flash/scenarios/flash_demo/` |
| 示例/支撑 | 文档 / 脚本 / 测试 | `docs/`, `scripts/`, `test/` |

典型数据流 (FlashSimulatorEngine.run): 参数合并 override → 构建 runs/{{id}}/ 目录
→ build_par 生成 .par → 生成 run_flash.sh / submit_flash.sh (LF) → WSL: setup -auto
→ make -j → mpirun ./flash4 → 从 WSL /tmp 采集 chk → scenario.build_grid +
interpolate 插值到规整网格 → 保存 database/flash_out/result.h5 → 自动诊断图。
"""

API_REFERENCE_TEXT = """\
# flash-sim API 参考

## 核心类 (来自 README「核心类」表)

| 类 | 包路径 | 说明 |
|----|--------|------|
| `FlashSimulatorEngine` | `flash.scenarios.core.simulator` | **统一仿真引擎** — 场景驱动, 封装 WSL 执行 + 插值 + 输出管线 |
| `SimulationScenario` | `flash.scenarios.core.base` | 场景声明式配置数据类 (钩子: build_par / build_grid / interpolate) |
| `FlashSimulator` | `flash` | 旧版统一仿真接口, mock/real 双模式 |
| `FlashConfig` | `flash.config` | 全局配置管理器 |
| `ParGeneratorExtended` | `flash.input_gen.gen_par.generator` | `.par` 参数文件生成器 |
| `ConfigGenerator` | `flash.input_gen.gen_config.generator` | `Config` 文件生成器 |
| `BlockGenerator` | `flash.input_gen.gen_sim_initblock.generator` | `Simulation_initBlock.F90` 生成器 |
| `FlashHDF5File` | `flash.output_pro.hdf5pro.flash_hdf5` | 底层 HDF5 文件读取器 (varnames / simulation_time) |
| `FlashDataLoader` | `flash.output_pro.loader.data_loader` | 结构化数据加载器 |
| `FlashDataContainer` | `flash.output_pro.loader.data_loader` | 数据容器 (data / derived / grid) |
| `FlashPlotter` | `flash.output_pro.plotter.plot_generator` | 自适应维度绘图器 (含 plot_xt_map) |
| `FlashEnvManager` | `flash.flash_run.env.env_manager` | 多环境管理器 (get_env_manager) |
| `FlashRemoteDeploy` | `flash.flash_run.remote.remote_deploy` | 远程部署管理器 (SSH/SFTP + SBATCH) |

CLI 命令: `flash-cred` (凭据管理交互菜单), `flash-setup` (初始化配置)。

## loader / plotter 典型用法

```python
from flash.output_pro.loader import FlashDataLoader
from flash.output_pro.plotter import FlashPlotter

# 加载 checkpoint 文件 (自动维度检测 + AMR 块结构解析)
loader = FlashDataLoader("lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)   # 自动计算派生变量

print(f"仿真时间: {{container.simulation_time:.4e}} s")
print(f"维度: {{container.ndim}}D, 块数: {{container.nblocks}}")
print(f"变量: {{list(container.data.keys())}}")

# 自适应维度绘图: 1D 线图 / 2D 伪彩 / 3D 切片
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png", title="Density Distribution")
plotter.plot("tele", save_path="tele.png", title="Electron Temperature")
```

## .par 生成典型用法

```python
from flash.input_gen.gen_par import ParGeneratorExtended, PulseShape

gen = ParGeneratorExtended(simulation_name="LaserSlab1d_new")
times, powers = PulseShape.from_intensity(1e14, spot_radius_cm=0.005, duration=5e-9)
gen.set_pulse(times, powers)
gen.set_time(tmax=1.75e-08, dtinit=1e-15)
gen.set_domain(xmin=0.0, xmax=160e-4, nblockx=4)
gen.set_target(height=20e-4, vacuum_height=140e-4)
gen.save("example1d_new.par")
```

## 场景引擎典型用法

```python
from flash.scenarios.core.registry import get_scenario
from flash.scenarios.core.simulator import FlashSimulatorEngine

engine = FlashSimulatorEngine(get_scenario("thin_layer_sandwich_si"))
output = engine.run()          # 自动编译→运行→插值→输出 result.h5
# engine.run(run_flash=False)  # dry-run: 只生成输入文件
print(output.result_h5_path, output.run_dir, output.n_chk, output.fields)
```
"""

# ---------------------------------------------------------------------------
# workflow_guide 主题内容
# ---------------------------------------------------------------------------

WORKFLOW_GUIDES: Dict[str, str] = {
    "full_simulation": """\
# 完整仿真工作流 (full_simulation)

流程: Config 编译配置 → setup + make → FLASH 二进制 → 生成 .par → mpirun →
HDF5 输出 → output_pro 自适应绘图 + 分析。

推荐路径 (场景驱动, 一条命令串全程):
1. 场景: `FlashSimulatorEngine(get_scenario("ch_center")).run()`
2. 一键脚本: `.venv-win\\Scripts\\python.exe flash\\scenarios\\center_evolution\\ch_center\\laserslab1d_local_custom.py`
   (RUN_MODE="wsl" 默认; "hpc" 走超算; 环境变量 FLASH_RUN_MODE 优先级更高)

引擎管线内部步骤 (scenarios/simulator.py):
① scenario.default_params 合并 override → ② build runs/{id}/ 目录
(sim_input / sim_output / database/flash_in / database/flash_out)
→ ③ build_par 生成 .par + 复制源文件 + 预诊断图 → ④ 生成 run_flash.sh /
submit_flash.sh (WSL/SLURM 双版本, LF 换行) → ⑤ WSL: setup -auto → make -j →
mpirun ./flash4 (超算: sbatch → srun) → ⑥ 从 WSL /tmp 采集 chk →
⑦ build_grid + interpolate 插值到规整 (t_grid, x_grid) → ⑧ 保存 result.h5
(数据集 t, x, {field:(Nt,Nx)}, gzip) → ⑨ 自动诊断图 (profile / t-x /
center_evolution)。

输出的两种消费方式:
1. 引擎内置: result.h5 统一规整网格, 便于优化与跨算例对比。
2. 独立消费原始 AMR chk: FlashDataLoader → FlashDataContainer → FlashPlotter
   (见 api_reference 工具)。

FLASH 默认安装路径解析顺序: FLASH_SIM_USER_DIR 环境变量 → 加密凭据
default_user_name (~/.physimx/flash/credentials.enc) → 自动扫描
$HOME/*/FLASH/FLASH4.8 (判据: 同时有 setup 与 source/Simulation/SimulationMain)
→ 回落字面量 hello。干净克隆没有 credentials.enc, 依赖第 3 步扫描。
""",
    "par_generation": """\
# .par 参数文件生成指南 (par_generation)

核心类: `flash.input_gen.gen_par.generator.ParGeneratorExtended`。

```python
from flash.input_gen.gen_par import (
    ParGeneratorExtended, PulseShape, BeamConfig, PulseConfig,
    MATERIALS, CHAMBER_GASES, list_materials,
)

gen = ParGeneratorExtended(simulation_name="LaserSlab1d_new")
# 激光脉冲: 高斯/梯形, 由强度反推时间-功率点对 (单位 SI: s / W)
times, powers = PulseShape.from_intensity(
    intensity_w_cm2=1e14, spot_radius_cm=0.005, duration=5e-9, n_points=10)
gen.set_pulse(times, powers)
gen.set_time(tmax=1.75e-08, dtinit=1e-15)
gen.set_domain(xmin=0.0, xmax=160e-4, nblockx=4)
gen.set_target(height=20e-4, vacuum_height=140e-4)
gen.save("example1d_new.par")
gen.save_config("Config")   # DATAFILES 自动包含新材料 cn4
```

关键点:
- **显式覆写**: `gen.set(key, value)` 修改的值必须显式覆写默认域值
  (xmin/xmax/nblockx/tmax/dtinit 等) —— 生成器是"默认值中心化"
  (input_gen/gen_par/defaults.py), 不覆写就沿用默认, 极易与预期几何不符。
- 激光层级: Pulses (时间-功率曲线) → Beams (每束关联一个 pulse_number,
  定义 lens/target 坐标)。ed_lens 必须在仿真域外; 1D 只需 lens_x/target_x。
- 多束同曲线: 统一 set_pulse + 多个 BeamConfig; 不同曲线: set_pulses 多脉冲。
- 材料: `gen.set_material(MATERIALS["polystyrene"])` 自动更新 rho/A/Z/ZMin/
  eos_file; 新材料 cn4 需放入仿真目录, Config DATAFILES 与 radiation_section
  的 op_*FileName 同步更新。
- 材料库: aluminum / polystyrene / beryllium / gold / copper / carbon;
  腔室气体 helium / hydrogen。`list_materials("target"/"chamber")` 查看。
- FLASH .par 排版规范见 docs/par_format_guide.md (resources 可直接读)。
- 相关 pitfall: par_gen.set() 须显式覆写域值 (见 workflow_guide("common_pitfalls"))。
""",
    "hdf5_analysis": """\
# HDF5 输出分析指南 (hdf5_analysis)

FLASH 输出: `*hdf5_chk_*` (checkpoint, 全变量) 与 `*hdf5_plt_cnt_*` (plot)。
AMR 块结构: chk 数据集形状为 **(nblocks, 1, 1, ncell)** (1D), 叶块坐标需经
extract_var_yt_style 重建 (hdf5pro 内置, 纯 h5py 无需 yt)。

底层读取:
```python
from flash.output_pro.hdf5pro import FlashHDF5File
ff = FlashHDF5File("flash_hdf5_plt_cnt_0000")
print(ff.varnames)          # 可用变量名
print(ff.simulation_time)   # 仿真时间
ff.close()
```

结构化加载 + 绘图:
```python
from flash.output_pro.loader import FlashDataLoader
from flash.output_pro.plotter import FlashPlotter

loader = FlashDataLoader("lasslab_hdf5_chk_0001")
container = loader.load(compute_derived=True)   # nele=ye·dens·N_A, nion, zbar, 梯度标长...
print(container.ndim, container.nblocks, container.simulation_time)
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png")
plotter.plot_xt_map("tele")   # 时空图: pcolormesh 用真实逐帧时间
```

要点:
- 派生变量由 DataCalculator 在加载时自动计算 (hdf5pro)。
- **温度单位是 K** (chk 中 tele/tion/trad); eV 换算: eV = K / 11604.518。
- **chk 是 (nblocks,1,1,ncell) 块结构**: 不要直接当规则网格 reshape; 用 loader
  或 extract_var_yt_style 重建全局坐标。
- x-t 图必须用 pcolormesh + 真实逐帧时间: chk 每隔 N 步写出, Δt 高度非均匀
  (实测 52.7x), imshow 会扭曲时间轴。time_uniformity() 可先检查均匀性。
- 批量/并行: flash/output_pro/parallel.py (多文件/多变量/多文件夹)。
- 大文件读取性能与索引对齐: 见 skill `physimx-h5py-batch-read`; 批量提取防挂起
  见 skill `flaky-io-watchdog-extraction`。
""",
    "remote_hpc": """\
# 远程超算运行指南 (remote_hpc)

支持平台: 本地 WSL (Ubuntu, mpirun -np 1) / ParaCloud NC-E (SSH 22) /
ParaCloud BSCC-T6 (SSH 8443), 凭据 flash_ssh / flash_ssh_2。

## Python API
```python
from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    deploy.upload("laserslab.par", "~/run/laserslab.par")
    job_id = deploy.submit_job(par_file="laserslab.par", nprocs=4,
                               wall_time="01:00:00", job_name="LaserSlab1D")
    deploy.wait_for_job(job_id, timeout=3600)
    deploy.download_results(remote_output_dir="~/run",
                            local_output_dir="./outputs", pattern="*.h5")
```

## 多环境管理
```python
from flash.flash_run.env import get_env_manager
mgr = get_env_manager()
print(mgr.summary())          # [local_wsl] / [supercomputer_nc_e] / [supercomputer_bscc_t6]
mgr.set_active("supercomputer_nc_e")
```

## 超算首次配置差异 (WSL vs SSH1 vs SSH2)
- MPI/HDF5: WSL 源码编译到 /usr/local/; 超算 `module load mpich/3.2-gcc9.3`
  + `module load hdf5/1.8.18` (先 `source /public1/soft/modules/module.sh`)。
- HYPRE: 超算无 sudo, 用户空间编译到 ~/hello/FLASH/local/hypre/。
  ★ $HOME 是符号链接 (/public1/home → /publicfs01/fs1-e/home),
  Makefile.h 的 HYPRE_PATH 必须 `readlink -f` 解析真实路径, 否则报
  `HYPREf.h: No such file or directory`。
- 运行: sbatch submit_flash.sh → squeue/sacct 监控; SLURM 分区按
  test/remote_connect/test_sbatch.py 实测 (如 v5_192)。
- 资源配置 (resource_config.json, 维度感知): 1D → 4 并行/45G/11核;
  2D → 3 并行/60G/15核; 3D → 2 并行/91G/22核 (192GB 节点, 48 核)。

## 一键脚本
- `python scenarios/flash_demo/hello_flash/deploy_flash.py` (交互选择机器)
- 批量多功率: `flash/scenarios/flash_demo/demo_hpc/laserslab1d_hpc_demo_batch.py`
- 运行流程详解: `flash/flash_run/PROCESS.md`
""",
    "offline_deploy": """\
# 离线部署指南 (offline_deploy)

统一入口: `start_flash.py` (只做参数翻译与转发, 逻辑不漂移; 底层
build_wheelhouse.py / usb_backup.py 仍可独立运行)。

```bash
# ---- 联网机 ----
python start_flash.py --make-wheelhouse                 # 造 wheelhouse
python start_flash.py --make-wheelhouse --export-profile lite   # 精简档 full/runtime/lite
python start_flash.py --export-usb D:\\usb_pkg            # 源码+wheelhouse 导出 U 盘

# ---- 离线机 ----
python start_flash.py --offline --wheelhouse D:\\pkg\\wheelhouse   # 离线安装 + 三套测试
python start_flash.py --offline --check                 # 只校验: 清单+平台+依赖覆盖度
python start_flash.py --offline --no-tests              # 快速安装
```

四道前置门 (任一失败即中止, 不留半成品 venv):
1. wheelhouse 存在且含 MANIFEST.json
2. 清单校验: 每个包的存在性 + 大小 + SHA256 (U 盘传输易静默损坏)
3. 平台/Python 版本匹配 (wheel cp3XX ABI 标签)
4. 依赖覆盖: pyproject.toml 闭包 ⊆ wheelhouse

`--no-index` 是硬门: pip 物理上无法联网。Linux/WSL 无需 apt: 无 python3-venv
时脚本从 wheelhouse 内 pip-*.whl 离线 bootstrap (--without-pip 骨架)。

自愈机制: venv 健康检查不过 (关键依赖缺/pytest 起不动) 或三套件全部
「0 用例启动失败」→ 自动清零重建重测, 无需手动 FLASH_FORCE_CLEAN=1。

平台隔离 venv: Windows→.venv-win (PE), Linux/WSL→.venv-linux (ELF),
macOS→.venv-mac; 物理上不能共用 (已编译扩展 win_amd64 vs manylinux)。
两目录互不删除, Windows/WSL 可随意切换。包体差异主要来自 Python 版本
(Win 3.13 vs Linux 3.10), 两台机器请用同一 Python 版本。
离线自检另有 183 项: deploy/test_offline_install.py。
""",
    "common_pitfalls": """\
# 常见坑与规避 (common_pitfalls)

1. **venv 平台隔离 (.venv-win / .venv-linux)**: 两平台 venv 物理上不能共用
   —— 解释器一个是 PE (.venv-win\\Scripts\\python.exe) 一个是 ELF
   (.venv-linux/bin/python), numpy/scipy/h5py 编译扩展分别是 win_amd64 与
   manylinux。start_flash.py 按平台分目录 (Windows→.venv-win,
   Linux/WSL→.venv-linux, macOS→.venv-mac), 对方平台的目录**保留不删**,
   可来回切换。旧的无后缀 .venv 若属本平台仍沿用; FLASH_VENV_DIR 显式指定优先。

2. **FLASH 默认名 flash.par (只读默认)**: FLASH 运行时按约定读取当前目录的
   `flash.par`; 不要假设可随意改名 (引擎在运行目录内生成/复制为 flash.par)。

3. **chk 是 (nblocks, 1, 1, ncell) 块结构**: 1D FLASH AMR checkpoint 的数据集
   形状是块结构而非规则网格; 直接 reshape 会得到错误坐标。必须经
   hdf5pro 的 extract_var_yt_style / FlashDataLoader 重建全局坐标。

4. **chk 温度单位是 K**: tele/tion/trad 存开尔文; 换算 eV: eV = K / 11604.518
   (1 eV ≈ 11604.518 K)。分析脚本里别把 K 当 eV 用。

5. **par_gen.set() 须显式覆写域值**: ParGeneratorExtended 是默认值中心化;
   `gen.set("xmin", ...)` 等域参数 (xmin/xmax/nblockx/tmax/dtinit) 必须**显式
   覆写**, 否则沿用 defaults.py 默认值, 几何/时长与预期不符。

6. **`+ug` 时叶块步长 = W/(iProcs*nxb), 与 lrefine_max 无关**: 使用
   `+ug` (uniform grid) 编译时, 每块叶块步长固定为域宽 W / (iProcs*nxb),
   **不要**指望调 lrefine_max 改变分辨率 —— +ug 下 AMR 细化不生效,
   想加密只能加 iProcs 或 nxb。

7. **fresh clone 须验证"生成目录类" bug**: 干净克隆没有 flash_input/ 等生成
   目录 (被 .gitignore 排除, 同 output_pro 的 inputfiles/ 模式), 也没有
   credentials.enc (FLASH_HOME 解析会误回落 ~/hello 报 FLASH_HOME not found)。
   引擎 ensure_sim_input() 会自动补齐输入文件; 也可单独跑
   `python flash/scenarios/center_evolution/ch_center/gen_flash_inputs.py`
   (--check / --force); FLASH 位置用 FLASH_SIM_USER_DIR 强制指定。

8. **wheel 排除项与 .gitignore 成对维护**: 发布包排除的路径 (flash_input/、
   inputfiles/ 等) 同时被 .gitignore 排除; 修改打包规则时两边必须**成对同步**,
   否则出现 "本地能跑、wheel 装完缺文件" 或反之。

9. **WSL .sh 必须 LF 换行**: CRLF 会导致 `$'\\r'` 错误、Fortran 编译异常、.par
   解析失败。仓库 .gitattributes 强制 `* text=auto eol=lf`; 引擎生成的
   run_flash.sh / submit_flash.sh 均为 LF; 自建脚本也要保证 LF。

10. **HDF5 "real scalars" 是复合类型不是 group**: 结构化数组
    `[(name, S80), (value, f8)]`, 不能 `f["real scalars"]["time"]`; 须遍历
    `rs["name"][i].decode().strip() == "time"` 取 `rs["value"][i]`。

11. **x-t 图禁用 imshow**: chk 按步数写出, Δt 高度非均匀 (实测 52.7×);
    FlashPlotter.plot_xt_map 用 pcolormesh + 每帧真实时间, 自建图也要如此。
""",
    # ── 操作规范 (docs/flash_operation_standard.md 摘要) ──
    "operation_standard": """\
# 仿真操作规范 (operation_standard, 源: docs/flash_operation_standard.md)

## 绘图规范 (强制)
- **所有绘图元素全英文**（即英文文献插图风格）: title / xlabel / ylabel / legend / colorbar;
  控制台日志、代码注释、文档可中文。
- **字号 ≥ 18pt (PPT 友好)**: title 22 / 轴标签 20 / 刻度·图例·colorbar·注释 18;
  禁止手工 fontsize=8/10/12/13/14。
- 统一入口 `output_pro/plotter/plot_style.py`:
  `apply_plot_style()` 一键全局样式 (≥18pt, 全英文, dpi=200);
  `english(text)` 清洗 Unicode (μm→um, g/cm³→g/cm^3);
  `save_figure(fig, path)` 保存 (dpi=200 + tight)。
- 合规检查: `python scripts/01_env_diagnose/check_plot_style.py` 扫描全包。

## 行尾规范
所有文本文件 LF (禁 CRLF): .py/.F90/.sh/.bat/.par/.cn4/.md/.json/.toml…
CRLF 危害: shell `$'\\r'` 错、Fortran Illegal character、.par 解析异常。

## 一次仿真最少 8 个文件
Config / `<name>.par` / Makefile / Simulation_data.F90 / Simulation_init.F90 /
Simulation_initBlock.F90 / 2 个 `<ionmix4>.cn4` (靶材+腔室)。

## 仿真验证标准
| 检查项 | PASS 判定 |
|---|---|
| 仿真完成 | 日志含 `exiting: reached max SimTime` |
| 输出文件 | ≥1 个 `*hdf5_chk_*` |
| 网格自适应 | 日志含 `refined: total blocks` |
| 物理量有效 | dens > 0 且 tele > 0 |
| AMR 正常 | leaf blocks > 初始 blocks |

## 代码规范
- 路径管理: 以包根为基准 sys.path.insert, 禁止绝对路径硬编码。
- FlashDataContainer 属性标准名: `ndim` (非 dimension) / `data` (非 variables)
  / `derived` / `grid`。
""",
    # ── FLASH 执行知识库 (docs/flash_simulation_execution_knowledge.md 摘要) ──
    "flash_execution_knowledge": """\
# FLASH 仿真执行知识库 (flash_execution_knowledge, 源: FLASH4.8 UG 提取)

## Setup 快捷键 (LaserSlab 典型)
`./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio species=cham,targ
+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10`
- `+laser` 激光射线追踪 / `+mtmmmt` 多物种多温度 / `+uhd3t` 3T 非分裂流体
  / `+mgd` 多群辐射扩散 / `+ug` 均匀网格 (AMR 失效, 见 common_pitfalls #6)。
编译: `cd object/ && make`; 运行: `mpirun -np N ./flash4`。

## 激光参数 (ed_*)
- 脉冲: `ed_numberofPulses` + `(ed_power_1_1, ed_time_1_1)` 功率-时间点对 (W, s)。
- 光束: `ed_wavelength_1` (m, 351nm=3.5e-7); lens 在**仿真域外**仅定义方向
  (1D 中 ed_lensX=-1 → 左入射), target 在**域内**是照射点; 能量沉积发生在
  射线穿过域内时。`ed_maxPulses`/`ed_maxBeams` 是 setup 期上限。
- 激光 IO: `ed_useLaserIO=.true.` + ed_laserIOMaxNumberOfRays/Positions。

## 输出文件
- chk `*_hdf5_chk_*`: float64, ~44 变量, 重启用; plt `*_hdf5_plt_cnt_*`:
  float32, ~9 变量, 可视化用。形状 (nblocks, Nz, Ny, Nx), 边界框 (nblocks,3,2)。
- "real scalars" 复合类型取法见 common_pitfalls #10。

## HPC 批量规范 (摘要)
- 目录命名 `~/<SIM_USER_DIR>/AI/Aitemp/flash_batch_<ts>_p<power_factor>/`;
  submit_flash.sh 内置 SLURM_SUBMIT_DIR / SLURM_NTASKS 回退, 输出目录
  `outputfiles_<ts>/` 须动态 `ls -d` 查找。
- 资源自动计算 (resource_config.json): mem/ntasks 由 node 资源 × max_cpu_percent
  ÷ max_parallel 派生, ShellScriptGenerator 按 dimension+platform 加载。
- 远程分析: python/3.9.6 是唯一带 h5py 的超算模块 (3.10.8/3.8.6 无, 已验证);
  分析结果 (JSON+PNG) 下载本地, HDF5 保留超算。
""",
}

GUIDE_TOPICS = tuple(WORKFLOW_GUIDES.keys())

RESOURCES_DOC_LIST = [
    ("README.md", "项目概述与快速入门 (主 README)"),
    ("docs/README.md", "FLASH 仿真使用指南 (详细版, 含所有子模块 API)"),
    ("docs/flash_operation_standard.md", "仿真操作规范 (绘图语言/行尾格式/运行流程)"),
    ("docs/par_format_guide.md", ".par 排版规范"),
    ("docs/skills-map.md", "技能 ↔ 文档 ↔ Python 模块索引"),
    ("flash/scenarios/README.md", "场景系统使用指南 (即插即用仿真入口)"),
]

# 静态场景清单 (动态导入失败时的回落; 与 docs 一致)
STATIC_SCENARIOS: List[Tuple[str, str]] = [
    ("ch_center", "CH 靶居中一维对称域 LaserSlab 演化场景 (两束 351nm 相向入射)"),
    ("thin_layer_sandwich_si", "三明治薄层靶场景 (Si, 私有场景, 发布环境可能未注册)"),
    ("thin_layer_sandwich_al", "三明治薄层靶场景 (Al, 私有场景, 发布环境可能未注册)"),
    ("grad_dens_sandwich", "梯度密度三明治靶场景 (私有场景, 发布环境可能未注册)"),
]

# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------


def tool_flash_overview() -> str:
    """返回项目简介、分层架构、5 分钟上手步骤、一键运行命令与 start_flash.py 用法。"""
    return OVERVIEW_TEXT


def tool_module_map() -> str:
    """返回分层架构表 (接口/输入生成/仿真执行/输出处理/核心抽象 + 文件路径)。"""
    return MODULE_MAP_TEXT


def tool_api_reference() -> str:
    """返回 README「核心类」表 + loader/plotter 典型用法代码片段。"""
    return API_REFERENCE_TEXT


def tool_docs_index() -> str:
    """动态枚举项目内全部 *.md 文档 (路径 + 大小 + 首个标题), 零硬编码。

    Agent 可据此决定用 read_doc / resources/read 深读哪份文档。
    """
    lines = ["# flash-sim 文档索引 (动态扫描)"]
    for path in _iter_md_files():
        rel = _rel(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            title = next(
                (ln.lstrip("# ").strip() for ln in text.splitlines() if ln.strip().startswith("#")),
                "(无标题)",
            )
            n_lines = text.count("\n") + 1
        except OSError as exc:
            title, n_lines = f"(读取失败: {exc})", 0
        lines.append(f"- **{rel}** ({n_lines} 行) — {title}")
    lines.append(
        "\n深读方式: `read_doc(rel_path)` 或 resources/read (file:// URI); "
        "关键词定位用 `search_docs(query)`。"
    )
    return "\n".join(lines)


def tool_workflow_guide(topic: str) -> str:
    """返回指定主题的工作流指南文本。

    Args:
        topic: full_simulation / par_generation / hdf5_analysis /
               remote_hpc / offline_deploy / common_pitfalls 之一。
    """
    key = str(topic).strip().lower()
    if key not in WORKFLOW_GUIDES:
        return (
            f"未知 topic: '{topic}'。可用主题: {', '.join(GUIDE_TOPICS)}。"
            "其中 common_pitfalls 汇总了 venv 平台隔离 / flash.par / chk 块结构 / "
            "温度单位 / 域值覆写 / +ug 步长 / fresh clone / wheel 排除 / LF 换行 共 9 个高频坑。"
        )
    return WORKFLOW_GUIDES[key]


def _register_scenarios_via_import() -> List[str]:
    """尝试导入 ch_center / sandwich 场景包以填充注册表 (register 调用在包 __init__)。"""
    for mod in (
        "flash.scenarios.center_evolution.ch_center",
        "flash.scenarios.sandwich.thin_layer_sandwich",
        "flash.scenarios.sandwich.grad_dens_sandwich",
    ):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # 场景依赖缺失 (如 numpy) 的 UserWarning 走回落路径, 不污染 stderr
                __import__(mod)
        except Exception:
            pass  # 私有/缺失场景静默跳过


def tool_list_scenarios() -> str:
    """动态 import flash.scenarios.core.registry 返回 list_scenarios(); 失败回落静态清单。"""
    try:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        _register_scenarios_via_import()
        from flash.scenarios.core.registry import list_scenarios  # type: ignore

        pairs = list_scenarios()
        if not pairs:
            pairs = STATIC_SCENARIOS
            note = "(注册表为空, 返回静态清单; 场景在各自包 __init__ 中 register)"
        else:
            note = "(动态导入成功)"
        lines = [f"## 可用场景 {note}"] + [f"- **{n}**: {d}" for n, d in pairs]
        lines.append(
            "\n用法: engine = FlashSimulatorEngine(get_scenario(name)); output = engine.run()"
        )
        return "\n".join(lines)
    except Exception as exc:  # 回落静态清单 + 错误原因
        lines = [
            f"## 可用场景 (动态导入失败: {type(exc).__name__}: {exc})",
            "返回静态清单 (来自文档, 仅供参考):",
        ]
        lines += [f"- **{n}**: {d}" for n, d in STATIC_SCENARIOS]
        return "\n".join(lines)


def _iter_md_files() -> List[Path]:
    """收集 PROJECT_ROOT 根目录、docs/、flash/ 下所有 *.md (跳过 SKIP_DIRS)。"""
    roots: List[Path] = [PROJECT_ROOT]
    for sub in ("docs", "flash"):
        p = PROJECT_ROOT / sub
        if p.is_dir():
            roots.append(p)
    found: List[Path] = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if fn.lower().endswith(".md"):
                    found.append(Path(dirpath) / fn)
    return sorted(set(found))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def tool_search_docs(query: str, limit: int = MAX_SEARCH_HITS_DEFAULT) -> str:
    """在项目所有 *.md 中做大小写不敏感关键词搜索。

    Returns:
        文本报告, 每条命中含 {文件, 行号, 匹配行}。跳过 flash_src/、
        __pycache__、runs/、.venv* 等目录。
    """
    q = str(query).strip()
    if not q:
        return "错误: query 不能为空。"
    try:
        max_hits = max(1, int(limit))
    except (TypeError, ValueError):
        max_hits = MAX_SEARCH_HITS_DEFAULT

    needle = q.lower()
    hits: List[str] = []
    total = 0
    for md in _iter_md_files():
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if needle in line.lower():
                total += 1
                if total <= max_hits:
                    snippet = line.strip()
                    if len(snippet) > 240:
                        snippet = snippet[:240] + "..."
                    hits.append(f"- `{_rel(md)}:{lineno}`: {snippet}")
        if total >= max_hits * 20:  # 防止超大命中集拖慢
            break
    header = f"## 文档搜索: '{q}' — 共 {total} 处命中"
    if total > max_hits:
        header += f" (仅显示前 {max_hits} 条)"
    if not hits:
        return header + "\n无命中。可尝试更短的关键词 (如 'lrefine', 'chk', 'wheelhouse')。"
    return header + "\n" + "\n".join(hits)


def tool_read_doc(rel_path: str, max_chars: int = MAX_DOC_CHARS_DEFAULT) -> str:
    """读取白名单内 (或任意 PROJECT_ROOT 下的) .md 文档, 超长截断。

    Args:
        rel_path: 相对 PROJECT_ROOT 的路径 (如 docs/par_format_guide.md)。
        max_chars: 最大返回字符数 (默认 20000, 超长截断并注明)。
    """
    rel = str(rel_path).strip().replace("\\", "/")
    candidate = (PROJECT_ROOT / rel).resolve()
    # 路径穿越检查
    try:
        candidate.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return f"错误: 路径越界 — '{rel_path}' 不在项目根目录内。"
    if candidate.suffix.lower() != ".md":
        return f"错误: 仅允许读取 .md 文件, 收到 '{candidate.suffix}'。"
    if not candidate.is_file():
        known = "\n".join(f"- {r}" for r, _ in RESOURCES_DOC_LIST)
        return f"错误: 文件不存在: {rel}\n白名单常用文档:\n{known}"
    try:
        max_n = max(200, int(max_chars))
    except (TypeError, ValueError):
        max_n = MAX_DOC_CHARS_DEFAULT
    text = candidate.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_n:
        return (
            text[:max_n]
            + f"\n\n--- [截断: 共 {len(text)} 字符, 仅显示前 {max_n}; "
            "可用更大的 max_chars 或 search_docs 定位片段] ---"
        )
    return text


def _detect_flash_home() -> str:
    """按项目规则探测 FLASH 安装目录, 返回说明文本 (不读取凭据内容)。"""
    lines: List[str] = []
    env_val = os.environ.get("FLASH_SIM_USER_DIR", "")
    if env_val:
        lines.append(f"1. 环境变量 FLASH_SIM_USER_DIR = '{env_val}' (命中)")
    else:
        lines.append("1. 环境变量 FLASH_SIM_USER_DIR 未设置")
    cred = Path.home() / ".physimx" / "flash" / "credentials.enc"
    if cred.is_file():
        try:
            with open(cred, "rb"):
                pass
            lines.append(f"2. 凭据文件存在且可读: {cred} (内容经 Fernet 加密, 此处不解析)")
        except OSError:
            lines.append(f"2. 凭据文件存在但不可读, 跳过: {cred}")
    else:
        lines.append(f"2. 凭据文件不存在, 跳过: {cred}")
    home = Path.home()
    found: Optional[Path] = None
    try:
        for child in sorted(home.iterdir()):
            cand = child / "FLASH" / "FLASH4.8"
            if (cand / "setup").is_file() and (cand / "source" / "Simulation" / "SimulationMain").is_dir():
                found = cand
                break
    except OSError:
        pass
    if found is not None:
        lines.append(f"3. 自动扫描命中: {found} (判据: 同时有 setup 与 source/Simulation/SimulationMain)")
    else:
        lines.append("3. 自动扫描未发现 $HOME/*/FLASH/FLASH4.8")
    lines.append("4. 以上都无时项目回落字面量 'hello' → ~/hello/FLASH/FLASH4.8")
    return "\n".join(lines)


def tool_env_check() -> str:
    """环境自检: Python 版本 / venv 平台目录 / flash 包可导入性 / FLASH_HOME 探测。"""
    lines = [f"# 环境自检 (PROJECT_ROOT = {PROJECT_ROOT})"]
    lines.append(f"- Python: {sys.version.split()[0]} ({sys.executable})")
    if not IS_SOURCE_CHECKOUT:
        lines.append(
            "- ⚠ wheel 安装模式: 本文件来自 flash 包分发 (flash/mcp_server.py), "
            "search_docs / read_doc / resources 需要 flash-sim 源码仓库才能工作。"
            "MCP 建议直接指向仓库根目录的 mcp_server.py。"
        )

    venv_win = PROJECT_ROOT / ".venv-win"
    venv_linux = PROJECT_ROOT / ".venv-linux"
    lines.append(f"- .venv-win 存在: {venv_win.is_dir()} ({venv_win / 'Scripts' / 'python.exe'})")
    lines.append(f"- .venv-linux 存在: {venv_linux.is_dir()} ({venv_linux / 'bin' / 'python'})")

    # flash 包可导入性 (在干净子进程中测试, 避免污染本进程)
    ok, msg = False, ""
    try:
        probe = subprocess.run(
            [sys.executable, "-c", "import flash; print(flash.__name__, getattr(flash, '__standalone__', 'n/a'))"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        ok = probe.returncode == 0
        msg = (probe.stdout.strip() or probe.stderr.strip().splitlines()[-1] if probe.stderr.strip() else "")
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
    lines.append(f"- flash 包可导入: {ok}" + (f" ({msg})" if msg else ""))

    lines.append("- FLASH_HOME 探测:")
    for ln in _detect_flash_home().splitlines():
        lines.append(f"    {ln}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 工具注册表 (名称 → (schema, 可调用))
# ---------------------------------------------------------------------------


def _build_tools() -> Dict[str, Tuple[Dict[str, Any], Callable[..., str]]]:
    """构造 tools/list 的 schema 与 tools/call 的分发表。"""
    tools: Dict[str, Tuple[Dict[str, Any], Callable[..., str]]] = {}

    def add(name: str, desc: str, props: Dict[str, Any], required: List[str], fn: Callable[..., str]) -> None:
        schema: Dict[str, Any] = {
            "name": name,
            "description": desc,
            "inputSchema": {"type": "object", "properties": props, "required": required},
        }
        tools[name] = (schema, fn)

    add(
        "flash_overview",
        "项目简介 + 分层架构 + 5 分钟上手步骤 + 一键运行命令 + start_flash.py 用法。接入本包后第一个调用。",
        {}, [], tool_flash_overview,
    )
    add(
        "list_scenarios",
        "列出所有已注册仿真场景 (动态导入 flash.scenarios.core.registry; 失败回落静态清单)。",
        {}, [], tool_list_scenarios,
    )
    add(
        "api_reference",
        "核心类表 (FlashSimulatorEngine / FlashDataLoader / FlashPlotter 等) + loader/plotter/.par 生成典型用法代码。",
        {}, [], tool_api_reference,
    )
    add(
        "workflow_guide",
        "返回指定主题的工作流指南 (8 主题): full_simulation | par_generation | hdf5_analysis | "
        "remote_hpc | offline_deploy | common_pitfalls | operation_standard | flash_execution_knowledge。",
        {"topic": {"type": "string", "description": "指南主题", "enum": list(GUIDE_TOPICS)}},
        ["topic"], tool_workflow_guide,
    )
    add(
        "search_docs",
        "在项目根目录与 docs/、flash/ 下所有 *.md 中做大小写不敏感关键词搜索, 返回 {文件, 行号, 匹配行}。",
        {
            "query": {"type": "string", "description": "搜索关键词 (大小写不敏感)"},
            "limit": {"type": "integer", "description": "最多返回命中条数 (默认 10)"},
        },
        ["query"], tool_search_docs,
    )
    add(
        "read_doc",
        "读取项目内的 .md 文档 (限定 PROJECT_ROOT 下, 防路径穿越), 超长截断。如 docs/par_format_guide.md。",
        {
            "rel_path": {"type": "string", "description": "相对项目根的路径, 如 'docs/README.md'"},
            "max_chars": {"type": "integer", "description": "最大返回字符数 (默认 20000)"},
        },
        ["rel_path"], tool_read_doc,
    )
    add(
        "env_check",
        "环境自检: Python 版本、.venv-win/.venv-linux 是否存在、flash 包可导入性、FLASH_HOME 探测链。",
        {}, [], tool_env_check,
    )
    add(
        "docs_index",
        "动态枚举项目内全部 *.md 文档 (相对路径 + 行数 + 首个标题), 用于决定深读哪份。",
        {}, [], tool_docs_index,
    )
    add(
        "module_map",
        "分层架构表: 接口/输入生成/仿真执行/输出处理/核心抽象 各层的关键类与文件路径。",
        {}, [], tool_module_map,
    )
    return tools


TOOLS = _build_tools()


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def _read_resource_file(rel: str) -> str:
    """读取 resource 对应文件全文 (UTF-8, errors=replace)。"""
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="replace")


def build_resources_list() -> List[Dict[str, Any]]:
    """构造 resources/list 的返回项 (file:// URI + 名称 + 描述 + mimeType)。"""
    items: List[Dict[str, Any]] = []
    for rel, desc in RESOURCES_DOC_LIST:
        uri = (PROJECT_ROOT / rel).as_uri()
        items.append(
            {
                "uri": uri,
                "name": rel,
                "description": desc,
                "mimeType": "text/markdown",
            }
        )
    return items


def read_resource(uri: str) -> Dict[str, Any]:
    """按 file:// URI 读取 resource 内容; 返回 MCP resources/read 的 contents 字段。"""
    from urllib.parse import unquote
    from urllib.request import url2pathname

    if not uri.startswith("file:"):
        raise ValueError(f"不支持的 URI scheme (仅支持 file://): {uri}")
    if uri.startswith("file://"):
        rest = uri[len("file://"):]
    else:
        rest = uri[len("file:"):]
    if os.name == "nt":
        # Windows: file:///E:/... → url2pathname → \E:\... → 去掉开头的 /\ → E:\...
        path = Path(unquote(url2pathname(rest)).lstrip("/\\"))
    else:
        path = Path(unquote(rest))
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise ValueError(f"URI 越界: {uri} 不在项目根目录内")
    if resolved.suffix.lower() != ".md" or not resolved.is_file():
        raise ValueError(f"resource 不可读: {resolved}")
    text = _read_resource_file(_rel(resolved))
    return [{"uri": uri, "mimeType": "text/markdown", "text": text}]


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 over stdio (每行一个 JSON 对象)
# ---------------------------------------------------------------------------


def _make_result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _make_error(req_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """处理单条 JSON-RPC 请求; 通知 (无 id) 返回 None。"""
    method = str(req.get("method", ""))
    req_id = req.get("id")
    params = req.get("params") or {}

    # 通知: 无 id
    if req_id is None:
        if method in ("notifications/initialized", "notifications/cancelled", "initialized"):
            return None
        return None

    if method == "initialize":
        return _make_result(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "flash-sim 项目 MCP server: 先调用 flash_overview 建立全局认知, "
                    "再用 workflow_guide(topic) 深入具体工作流, 用 search_docs/read_doc 查文档细节。"
                ),
            },
        )

    if method == "ping":
        return _make_result(req_id, {})

    if method == "tools/list":
        return _make_result(req_id, {"tools": [schema for schema, _ in TOOLS.values()]})

    if method == "tools/call":
        name = str(params.get("name", ""))
        args = dict(params.get("arguments") or {})
        if name not in TOOLS:
            return _make_error(req_id, -32602, f"Unknown tool: {name}", {"available": sorted(TOOLS)})
        try:
            text = TOOLS[name][1](**args)
        except TypeError as exc:
            return _make_error(req_id, -32602, f"Invalid arguments for tool '{name}': {exc}")
        except Exception as exc:
            return _make_result(
                req_id,
                {"content": [{"type": "text", "text": f"工具执行出错: {type(exc).__name__}: {exc}"}], "isError": True},
            )
        return _make_result(req_id, {"content": [{"type": "text", "text": text}], "isError": False})

    if method == "resources/list":
        return _make_result(req_id, {"resources": build_resources_list()})

    if method == "resources/read":
        uri = str(params.get("uri", ""))
        try:
            contents = read_resource(uri)
        except Exception as exc:
            return _make_error(req_id, -32602, f"Resource read failed: {exc}")
        return _make_result(req_id, {"contents": contents})

    if method == "resources/templates/list":
        return _make_result(req_id, {"resourceTemplates": []})

    if method == "logging/setLevel":
        return _make_result(req_id, {})

    return _make_error(req_id, -32601, f"Method not found: {method}")


def serve(stdin: Any = None, stdout: Any = None) -> int:
    """主循环: 逐行读取 JSON-RPC 请求, 逐行写出响应。Ctrl-D / 空行结束。"""
    reader = stdin if stdin is not None else sys.stdin
    writer = stdout if stdout is not None else sys.stdout
    for raw in reader:
        line = raw.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = _make_error(None, -32700, f"Parse error: {exc}")
        else:
            if not isinstance(req, dict):
                resp = _make_error(None, -32600, "Invalid Request: not an object")
            else:
                resp = _handle_request(req)  # type: ignore[arg-type]
        if resp is not None:
            writer.write(json.dumps(resp, ensure_ascii=False) + "\n")
            writer.flush()
    return 0


def main() -> int:
    """入口: 在 UTF-8 模式下运行 stdio 服务。"""
    if os.name == "nt":
        # Windows 控制台强制 UTF-8 读写, 避免中文内容编码错误
        try:
            sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
