# FLASH 仿真使用指南

## 概述

FLASH 是高性能等离子体辐射流体力学仿真软件，广泛应用于 ICF 等领域。
PhySimX 的 FLASH 模块提供完整的仿真工作流：一键安装 → 参数编辑 → 编译运行 → 结果分析。

### 核心子模块 (v2.0+)

| 模块 | 功能 |
|------|------|
| `input_gen/gen_par/` | .par 参数文件生成 (ParGeneratorExtended) |
| `input_gen/gen_config/` | Config 文件生成 (ConfigGenerator) |
| `input_gen/gen_makefile/` | Makefile 生成 (MakefileGenerator) |
| `input_gen/gen_sim_data/` | Simulation_data.F90 生成 (SimDataGenerator) |
| `input_gen/gen_sim_init/` | Simulation_init.F90 生成 (SimInitGenerator) |
| `input_gen/gen_sim_initblock/` | Simulation_initBlock.F90 生成 (BlockGenerator) |
| `input_gen/gen_eos_op/` | .cn4 EOS 表文件复制/生成 (EOSOpacityGenerator) |
| `input_gen/gen_shell_script/` | 平台运行脚本 (ShellScriptGenerator) |
| `input_gen/gen_checker/` | 依赖检查 + 脉冲/密度/射线绘图 |
| `output_processors/` | HDF5 输出分析 (自适应 1D/2D/3D) |
| `scenarios/flash_demo/` | 一键执行 Demo |

> 旧模块 (`par_calculator`, `par_editor`, `flash_setup`, `first_run`, `env_manager`) 已迁移至 `input_gen/gen_*` 子包。

---

## 快速开始

### 1. 一键安装 (WSL/Ubuntu)

```python
from flash.input_gen.first_run import FlashFirstRun

runner = FlashFirstRun(install_dir="~/QC/FLASH", setup_name="LaserSlab")
runner.generate_install_script("install_flash.sh")
# Windows WSL:
# runner.run_local_wsl()
```

### 2. .par 文件编辑

```python
from flash.input_gen.par_editor import ParEditor

editor = ParEditor()
editor.read("flash.par")
editor.modify_variable("dt_init", 1e-15)
editor.modify_variable("useGravity", False)
editor.serial_time_power(time_arr, power_arr, section="Laser")
editor.write("flash_modified.par")
```

### 3. 脉冲参数计算

```python
from flash.input_gen.par_calculator import ParCalculator

time, power = ParCalculator.generate_pulse_points(
    shape="trapezoid", duration=5e-9, peak_power=1e12, n_points=100
)
peak = ParCalculator.calculate_peak_power(
    energy_j=100, pulse_duration_s=5e-9, spot_radius_cm=3e-2
)
```

### 4. SLURM 提交脚本

```python
from flash.input_gen.flash_setup import FLASHSetupGenerator

gen = FLASHSetupGenerator(config={
    "flash_home": "~/QC/FLASH",
    "slurm_partition": "cpu",
    "slurm_nodes": 1,
})
gen.generate_env_script("FLASH_env.sh")
gen.generate_run_script("FLASH_run.sh", nprocs=4, par_file="flash.par")
gen.generate_slurm_script("submit.slurm")
```

### 5. 多环境管理

```python
from flash import FlashEnvManager, get_env_manager

mgr = get_env_manager()
mgr.add_environment("local_wsl", FlashEnvironment(
    name="local_wsl", env_type="local_wsl",
    flash_home="/home/user/QC/FLASH",
))
mgr.add_environment("paracloud", FlashEnvironment(
    name="paracloud", env_type="remote_sbatch",
    flash_home="~/QC/FLASH",
    ssh_credential="flash_ssh",
    slurm_partition="cpu",
))

# 获取运行命令
env = mgr.get_environment("paracloud")
cmd = env.get_run_command(par_file="flash.par", nprocs=32)
```

### 6. 输出分析

```python
from flash.temp_delete.output_analysis import FlashOutputReader

reader = FlashOutputReader("flash_hdf5_plt_cnt_0000")
print(reader.list_variables())
reader.close()
```

---

## Demo / 快速入门

### 新增：Python 一键 Demo（推荐）

`scenarios/flash_demo/` 目录包含一键执行的 Python demo 脚本，使用 Python API 完成从参数生成到结果可视化的完整流程。

| Demo 文件 | 功能 | 运行环境 | 说明 |
|-----------|------|----------|------|
| `laserslab1d_local_demo.py` | LaserSlab1D 仿真 + 密度分布绘图 | 本地 WSL | 一键完成：参数生成 → 本地运行 → 输出处理 → 绘图 |
| `laserslab1d_supercomputer_demo.py` | LaserSlab1D 仿真 + 密度分布绘图 | 超算 SSH | 一键完成：参数生成 → 提交作业 → 下载结果 → 输出处理 → 绘图 |
| `laserslab1d_hpc_demo_batch.py` | 多功率批量仿真 + 对比分析 | 超算 SSH + SLURM | 一键完成：多功率变体生成 → 并行提交 → 下载 → 对比绘图 |
| `new_struture/laserslab1d_local_custom.py` | 自定义对称域 1D 仿真 (CH靶, 2束相向) | 超算 SSH + SLURM | 可配置参数：L0, 靶宽, 密度, 激光功率, 波长 |

> **v2.1 更新**: 每个 Demo 创建**独立的运行文件夹** (`demo_task/<demo>/run/`)，包含全部 11 个执行必需文件（.par, Config, Makefile, .F90 x3, .cn4 x2, 脚本 x3），可直接执行一键脚本启动 FLASH。

**运行方式**:

```bash
# 本地运行 Demo
cd E:/ProgramsPATH/AI/WorkBuddy/WorkBuddyFiles/AItest/Plan_for_py/PhySimX
python -m physimx_sim.flash.scenarios.flash_demo.demo_local.laserslab1d_local_demo

# 超算运行 Demo
python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_supercomputer_demo

# 超算批量运行 Demo (多功率对比)
python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch

# 自定义对称域仿真 (CH靶, 2束相向激光)
python -m physimx_sim.flash.scenarios.flash_demo.new_struture.ch_center.laserslab1d_local_custom
```

**控制仿真用户目录**: 通过环境变量 `FLASH_SIM_USER_DIR` 控制，默认 `QC`:
```bash
# 使用自定义用户目录
FLASH_SIM_USER_DIR=myuser python -m physimx_sim.flash.scenarios.flash_demo.demo_local.laserslab1d_local_demo
```

**输出**:

```
demo_task/laserslab1d_local_demo/
├── run/                          ← 独立运行文件夹（可一键执行）
│   ├── laserslab1d_demo.par      # 生成的 .par 参数文件
│   ├── Config / Makefile
│   ├── Simulation_*.F90 (x3)
│   ├── al-imx-003.cn4 / he-imx-005.cn4
│   ├── run_flash.bat             # Windows WSL 一键脚本
│   ├── run_flash.sh              # WSL/Linux 一键脚本
│   └── submit_flash.sh           # SLURM 提交脚本
└── output/                       ← 仿真输出
    ├── lasslab_hdf5_chk_*         # 41 个 checkpoint 文件 (t=0 ~ t=1e-9s)
    ├── lasslab_hdf5_plt_cnt_*     # 80 个 plot 文件
    └── plots/                     # 密度/温度分布图
        ├── dens_initial.png       # 初始密度分布 (t=0)
        ├── dens_final.png         # 最终密度分布 (t=1e-9s)
        ├── dens_t*.png            # 多时间步密度演化
        ├── tele_initial.png       # 初始电子温度
        └── tele_final.png         # 最终电子温度
```

**一键执行方式**:
```bash
# 方式 1: 使用 Python Demo 脚本（推荐）
cd E:/ProgramsPATH/AI/WorkBuddy/WorkBuddyFiles/AItest/Plan_for_py/PhySimX
python -m physimx_sim.flash.scenarios.flash_demo.demo_local.laserslab1d_local_demo

# 方式 2: 直接运行独立文件夹中的脚本
cd scenarios/flash_demo/demo_task/laserslab1d_local_demo/run/
bash run_flash.sh               # WSL 一键执行
# 或
./run_flash.bat                  # Windows 一键执行
```

### 批量 Demo 工作流 (多功率对比)

`laserslab1d_hpc_demo_batch.py` 实现了完整的批量仿真工作流，使用不同的功率因子进行多个仿真并对比结果。

**功率因子**: `[0.5, 1.0, 1.5, 2.0]` — 修改 `.par` 文件中 `ed_power*` 参数，实现不同激光功率的对比。

**执行流程 (5 步骤, v1.1)**:

| 步骤 | 说明 | 关键方法 |
|------|------|----------|
| 1. 生成变体 | 生成基准 .par → 为每个功率因子复制并修改功率 | `create_power_variants()` |
| 2. 上传超算 | 将各功率变体 + 远程分析脚本上传到超算 | `deploy_to_supercomputer()` |
| 3a. sbatch 提交 | 将功率提交到 SLURM 队列 (可用分区通过 `test/remote_connect/test_sbatch.py` 检测) | `run_flash_remotely() 3a` |
| 3b. 直接运行 (fallback) | sbatch 失败时降级为直接 `bash run_flash.sh` | `run_flash_remotely() 3b` |
| 3c. 等待完成 | 轮询 `sacct` 等待所有作业完成 (最长 1h) | `run_flash_remotely() 3c` |
| 4. 远程分析 | 在超算上运行 `remote_analysis.py` (module load python/3.10.8) | `run_remote_analysis_and_download()` |
| 5. 下载结果 | 仅下载分析结果 (JSON + PNG), HDF5 保留在超算上 | `run_remote_analysis_and_download()` |

**SLURM 分区自动检测**: 使用 `test/remote_connect/test_sbatch.py` 检测可用分区。
当前测试: 用户 `scfa2696` 只有 `v5_192` 分区可用 (`queue` 和 `all` 均无权限):

```python
SLURM_PARTITIONS = ["v5_192"]  # 根据 test_sbatch.py 结果配置
```

**资源配置自动计算**: `resource_config.json` 定义了维度感知的资源分配:

| 配置 | 节点 | 1D | 2D | 3D |
|------|------|----|----|----|
| 最大并行数 | — | 4 | 3 | 2 |
| CPU 使用率 | — | 95% | 95% | 95% |
| 每任务内存 | 192GB | 45G (192×0.95/4) | 60G (192×0.95/3) | 91G (192×0.95/2) |
| 每任务核数 | 48核 | 11 (48×0.95/4) | 15 (48×0.95/3) | 22 (48×0.95/2) |

`ShellScriptGenerator` 根据 `dimension` (1/2/3) 和 `platform` (local/hpc) 自动加载:

```python
gen = ShellScriptGenerator({'dimension': 1, 'platform': 'hpc'})
# slurm_ntasks_per_node=11, slurm_mem_gb=45
```

**输出** (HDF5 保留在超算, 只下载分析结果):
```
demo_task/laserslab1d_hpc_demo_batch/
&#x251C;&#x2500;&#x2500; run/
  &#x2502;   &#x251C;&#x2500;&#x2500; power_0.5/          &#x2190; 各功率独立运行文件夹 (11 文件)
  &#x2502;   &#x251C;&#x2500;&#x2500; power_1.0/
  &#x2502;   &#x251C;&#x2500;&#x2500; power_1.5/
  &#x2502;   &#x2514;&#x2500;&#x2500; power_2.0/
&#x2514;&#x2500;&#x2500; plots/                   &#x2190; 仅下载的分析结果
    &#x251C;&#x2500;&#x2500; batch_results.json              # 密度/温度摘要
    &#x251C;&#x2500;&#x2500; batch_results_dens_comparison.png # 密度对比
    &#x251C;&#x2500;&#x2500; batch_results_tele_comparison.png # 温度对比
    &#x2514;&#x2500;&#x2500; batch_results_peak_density_vs_power.png # 峰值曲线
```

**运行方式**:
```bash
cd PhySimX
python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch
```

**控制超算凭据**: 通过 `credential_name` 参数控制 SSH 连接:
```python
# 使用默认凭据 (flash_ssh)
python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch

# 代码中支持指定凭据: main(credential_name="flash_ssh")
```

### 本地 Demo 真实测试结果 (2026-06-22, v2.1)

使用 `create_input_files` + 自定义 SETUP_CMD 创建独立运行文件夹并完成真实 FLASH 仿真测试：

| 指标 | 值 |
|------|-----|
| 运行文件夹 | `scenarios/flash_demo/demo_task/laserslab1d_local_demo/run/` (11 个独立文件) |
| FLASH 二进制 | `~/QC/FLASH/FLASH4.8/QC/LaserSlab_local/flash4` (自定义路径) |
| SETUP_CMD | `./setup -auto QC/LaserSlab_local -1d +cartesian ... -objdir=QC/LaserSlab_local -par_file=laserslab1d_demo.par` |
| 运行环境 | WSL Ubuntu-22.04, mpirun -np 1 |
| 输出 | 41 个 checkpoint + 80 个 plot 文件 |
| 成功标志 | `exiting: reached max SimTime`, `*** Wrote checkpoint file` |
| 一键执行 | `cd run/ && bash run_flash.sh`

### 超算 Demo 真实测试结果 (2026-06-18)

在 ParaCloud NC-E 超算 (SSH1) 上完成完整 FLASH 仿真测试：
（文件生成模式已更新为 v2.1 自定义 SETUP_CMD，但未重新运行 SSH 测试）

| 指标 | 值 |
|------|-----|
| 超算节点 | ia0213 (v5_192 分区), 4 cores |
| 编译 | `./setup -auto QC/LaserSlab_hpc -1d ... -objdir=QC/LaserSlab_hpc -par_file=laserslab1d_sc_demo.par` + `make -j4` (~2 min) |
| 仿真 | `mpirun -np 4 ./flash4` (~30 秒) |
| 输出 | 41 checkpoint + 80 plot 文件 |
| 作业ID | 4723585 |
| 工作目录 | `~/QC/AI/flash_demo_20260618_172906/` |
| 输出目录 | `demo_task/laserslab1d_supercomputer_demo/output/` |
| 生成图像 | 初始/最终密度、电子温度、多时间步演化 (全英文标注) |

**运行方式**:
```bash
# 方式 1: 使用 Python Demo 脚本 (需 paramiko + 凭据)
python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_supercomputer_demo

# 方式 2: 手动 SSH + sbatch
ssh cn-zhongwei-1.paracloud.com
cd ~/QC/FLASH/FLASH4.8/
module load hdf5/1.8.18 mpich/3.2-gcc9.3
./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=object_new
cd object_new && make -j4
sbatch submit.slurm
```

**测试结果分析**:
- **密度**: 初始呈阶跃分布（真空区 ρ≈0, 靶区 ρ=2.7 g/cm³）→ 激光烧蚀后出现密度尖峰，靶材压缩
- **温度**: 电子温度在激光辐照区域显著升高（从 290K → ~数万 K）
- 输出文件路径: `scenarios/flash_demo/demo_task/laserslab1d_local_demo/output/plots/`

### 批量 Demo 设计说明 (v1.0, 2026-06-22)

`laserslab1d_hpc_demo_batch.py` 目前处于开发阶段，核心流程已确定：

| 特性 | 状态 |
|------|------|
| 多功率变体生成 (`create_power_variants`) | ✅ 完成 |
| 远程部署 (`deploy_to_supercomputer`) | ✅ 完成 (含 CRLF 转换) |
| sbatch 并行提交 + fallback | ✅ 完成 (含队列轮询分发) |
| sbatch 作业状态轮询 (`sacct`) | ✅ 完成 |
| SCP 批量下载 + tar 打包 | ✅ 完成 |
| 对比分析绘图 | ✅ 完成 (密度/温度/峰值曲线) |

**关键设计决策**:
- 各功率变体共享基准 `.par` 文件，仅 `ed_power*` 参数乘以功率因子
- 使用 `create_input_files()` 生成基础模板，然后 `copytree` 复制 + `_modify_power_in_par` 修改
- SLURM 队列按轮询分发：`power_0.5 → v5_192, power_1.0 → queue, power_1.5 → v5_192, power_2.0 → queue`
- 多功率任务独立运行在不同目录，互不干扰
- 支持 `credential_name` 参数切换 SSH 凭据

---

### Hello FLASH! — 一键安装 + 仿真入门包

`scenarios/flash_demo/hello_flash/` 是完全自包含的快速上手入门包，
不依赖任何外部模块，适合首次体验 FLASH。

```bash
# 进入 hello_flash 目录
cd scenarios/flash_demo/hello_flash/

# 一键完整流程：安装 → 仿真 → 密度分析
bash run_hello_flash.sh

# 或分步执行:
bash install_flash_wsl.sh      # Step 1: 安装 FLASH → ~/QC/FLASH/
bash run_and_collect.sh        # Step 2: 仿真 + 收集 HDF5
python3 analyze_density.py     # Step 3: 密度时空演化图
```

详见 [`scenarios/flash_demo/hello_flash/README.md`](../scenarios/flash_demo/hello_flash/README.md)

### Python API 安装脚本生成

```bash
# 通过 Python API 生成安装脚本
python -c "from flash.input_gen.first_run import quick_install; quick_install()"
```

---

## LaserSlab 仿真配置与执行

### 1. LaserSlab 变体概述

| 仿真名称 | 说明 | 章节 | Setup 快捷键 |
|-----------|------|--------|--------------|
| **LaserSlab (全物理)** | 2D圆柱几何，3T流体力学+表格EOS+激光 ray tracing | 35.7.5 | `+laser +mtmmt +uhd3t +mgd` |
| **LaserSlab + Thomson** | 增加Thomson散射诊断 | 35.7.6 | `+thsc` |
| **Z-pinch** | Z-pinch等离子体压缩仿真 | 35.7.7 | 参考LaserSlab |

### 2. LaserSlab 1D 快速Setup

```bash
# 进入FLASH源码目录
cd ~/QC/FLASH/FLASH4.8/

# LaserSlab 1D 配置
./setup -auto LaserSlab -1d +cartesian -nxb=16 \
  +hdf5typeio species=cham,targ \
  +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10

# 编译
cd object/
make
```

### 3. 激光参数配置 (flash.par)

#### 3.1 激光脉冲 (Pulse) 参数

```python
# 脉冲数量
ed_numberOfPulses = 1

# 脉冲功率-时间点对 (trapezoid形状示例)
ed_power_1_1 = 0.0        # 起始功率 (W)
ed_time_1_1 = 0.0          # 起始时间 (s)
ed_power_1_2 = 1.0e12      # 峰值功率 (W)
ed_time_1_2 = 1.0e-9      # 上升时间 (s)
ed_power_1_3 = 1.0e12      # 维持功率 (W)
ed_time_1_3 = 4.0e-9      # 平台结束时间 (s)
ed_power_1_4 = 0.0        # 结束功率 (W)
ed_time_1_4 = 5.0e-9      # 总脉宽 (s)
```

#### 3.2 激光光束 (Beam) 参数

```python
# 光束数量
ed_numberOfBeams = 1

# 激光波长 (m)
ed_wavelength_1 = 3.5e-7

# 光束透镜坐标 (激光出发位置)
ed_lens_1_x = 0.0
ed_lens_1_y = 0.0
ed_lens_1_z = -0.01

# 光束目标坐标 (激光照射点)
ed_target_1_x = 0.0
ed_target_1_y = 0.0
ed_target_1_z = 0.0
```

### 4. Setup 时的常见参数设置

```bash
# 在setup命令中指定最大脉冲数和光束数
./setup -auto LaserSlab -1d +cartesian -nxb=16 \
  +hdf5typeio species=cham,targ \
  +mtmmmt +laser \
  -maxblocks=2048  \
  +uhd3t +mgd mgd_meshgroups=10
```

### 5. 激光能量沉积输出

```python
# 在 Simulation/SimulationMain/LaserSlab/Config 中添加
REQUIRES VARIABLE lase

# 这样 lase 变量会出现在HDF5输出文件中
# 可用于可视化激光能量沉积分布
```

### 6. 激光射线追踪调试 (LaserIO)

```python
# 在 flash.par 中启用 LaserIO
ed_useLaserIO = .true.
ed_laserIOMaxNumberOfRays = 1000
ed_laserIOMaxNumberOfPositions = 100

# 输出文件: <basename>LaserRaysPrint<PID>.txt
# 包含射线轨迹信息，用于调试激光设置
```

### 7. 运行仿真

```bash
# WSL/本地运行
cd ~/QC/FLASH/FLASH4.8/object/
mpirun -np 1 ./flash4

# 超算并行运行 (Paracloud)
cd ~/QC/FLASH/FLASH4.8/object/
mpirun -np 4 ./flash4

# 或使用SLURM提交作业
sbatch submit_laserslab1d.slurm
```

### 8. 详细知识库

完整的仿真执行知识（包括运行时参数、输出分析、常见问题）已提取到：
```
docs/flash_simulation_execution_knowledge.md
```

---

## 目录结构

```
physimx_sim/flash/
├── __init__.py              # FlashSimulator + FlashEnvManager
├── interface.py             # Simulator 接口 (mock/real)
├── env_manager.py           # 多环境管理器 (local/remote)
├── input_gen/               # 输入文件生成器 v2.0 (自包含)
│   ├── __init__.py          # create_input_files() 一键生成
│   ├── gen_par/             # .par 参数文件 (ParGeneratorExtended)
│   ├── gen_config/          # Config 文件 (ConfigGenerator)
│   ├── gen_makefile/        # Makefile (MakefileGenerator)
│   ├── gen_sim_data/        # Simulation_data.F90 (SimDataGenerator)
│   ├── gen_sim_init/        # Simulation_init.F90 (SimInitGenerator)
│   ├── gen_sim_initblock/   # Simulation_initBlock.F90 (BlockGenerator)
│   ├── gen_eos_op/          # .cn4 EOS 表 (EOSOpacityGenerator)
│   ├── gen_shell_script/    # 平台运行脚本 (ShellScriptGenerator)
│   │   ├── generator.py     # 生成器: 支持 dimension/platform 资源自适应
│   │   └── resource_config.json  # 资源配置 (local/hpc, 1d/2d/3d)
│   └── gen_checker/         # 依赖检查 + 绘图
├── output_processors/       # 输出分析 (自适应 1D/2D/3D)
│   ├── __init__.py
│   ├── hdf5processor/       # 核心 HDF5 I/O
│   │   └── flash_hdf5.py    # FlashHDF5File: 打开/读取/维度检测
│   ├── loader/              # 数据加载层
│   │   └── data_loader.py   # FlashDataLoader → FlashDataContainer
│   ├── calculator/          # 数值计算
│   │   └── data_processor.py # 全场统计、切片、展平
│   └── plotter/             # 自适应可视化
│       └── plot_generator.py # 1D线图/2D伪彩色/3D切片
├── output_analysis/         # 输出分析 (旧版)
├── config/                  # 运行配置
│   └── __init__.py          # FlashConfig 类
├── flash_src/               # 源码包 (tar.gz)
│   ├── FLASH4.8.tar.gz
│   ├── mpich-3.2.tar.gz
│   ├── hdf5-1.8.12.tar.gz
│   └── hypre-2.9.0b.tar.gz
├── scenarios/flash_demo/    # 演示和快速上手
│   ├── LaserSlab/           # 标准 LaserSlab 参考文件 (2D)
│   ├── LaserSlab1d/         # LaserSlab 1D 参考文件 (Config, .par, .cn4, .F90)
│   ├── LaserSlab1d_2beams/  # 双光束变体参考文件
│   ├── LaserSlab1d_3beams/  # 三光束变体参考文件
│   ├── LaserSlab1d_new/     # 自定义 1D 仿真参考文件
│   ├── LaserSlabpy/         # Python API 相关
│   ├── laserslab1d_local_demo.py      # Python 一键本地 Demo
│   ├── laserslab1d_supercomputer_demo.py # Python 一键超算 Demo
│   ├── laserslab1d_hpc_demo_batch.py    # Python 批量超算 Demo (多功率对比)
│   ├── demo_task/           # Demo 运行产物
│   │   ├── laserslab1d_local_demo/    # 本地 Demo 输出 (HDF5 + 图像)
│   │   ├── laserslab1d_supercomputer_demo/ # 超算 Demo 输出
│   │   └── laserslab1d_hpc_demo_batch/    # 批量 Demo 输出
│   │       ├── run/power_0.5/ ...     # 各功率独立运行文件夹
│   │       ├── output/power_0.5/ ...  # 下载的 HDF5
│   │       └── plots/                 # 对比分析图像
│   └── hello_flash/         # 🚀 完全独立的一键入门包
│       ├── README.md            # 三机器配置说明 (WSL/SSH1/SSH2)
│       ├── deploy_flash.py      # 一键部署脚本 (交互式选择机器)
│       ├── run_hello_flash.sh   # 一键完整流程入口
│       ├── install_flash_wsl.sh # WSL 安装脚本
│       ├── run_and_collect.sh   # 仿真运行 + 收集
│       ├── analyze_density.py   # 密度时空分析 (支持source suffix)
│       ├── setup_hpc_flash.sh   # 超算配置参考脚本
│       └── outputfiles/         # 仿真输出
│           ├── hdf5files/           # WSL 本地数据
│           ├── hdf5filesfrom_ssh1/  # SSH1 (NC-E) 数据
│           ├── hdf5filesfrom_ssh2/  # SSH2 (BSCC-T6) 数据
│           ├── plots/               # WSL 分析图
│           ├── plotsfrom_ssh1/      # SSH1 分析图
│           └── plotsfrom_ssh2/      # SSH2 分析图
└── docs/
    └── README.md            # 本文档
```

---

## 迁移说明 (从 OldVersion)

| 旧模块 | 新位置 | 说明 |
|--------|--------|------|
| `OldVersion/PAR/ParCalculator.py` | `input_gen/par_calculator.py` | 脉冲形状/功率计算 |
| `OldVersion/PAR/ParEditor.py` | `input_gen/par_editor.py` | Section 感知 .par 编辑器 |
| `OldVersion/BASEINFO/FLASH_GenShell.py` | `input_gen/flash_setup.py` | 编译/SLURM 脚本生成 |
| `OldVersion/FirstRun/FLASH_one_click_install.sh` | `input_gen/first_run.py` | 一键安装 (适配最新 Ubuntu) |
| `OldVersion/FirstRun/analyze_density.py` | `output_analysis/` | HDF5 密度分析 |

---

### 10. HPC 超算首次配置

与 WSL 安装的核心差异：

| 差异项 | WSL (本地) | SSH1 (NC-E) | SSH2 (BSCC-T6) |
|--------|-----------|-------------|-----------------|
| MPI/HDF5 | 从源码编译 → `/usr/local/` | `module load` | `module load` |
| HYPRE | `/usr/local/hypre/` | `~/QC/FLASH/local/hypre/` | `~/QC/FLASH/local/hypre/` |
| sudo 权限 | 有 | **无** | **无** |
| 运行方式 | `mpirun -np 1` | `mpirun -np 4` 或 sbatch | `mpirun -np 4` 或 sbatch |
| 编译方式 | 本地编译 | 登录节点编译 | 登录节点编译 |
| SSH 端口 | — | 22 | 8443 |
| Credential | — | `flash_ssh` | `flash_ssh_2` |

**超算配置参考脚本**: `scenarios/flash_demo/hello_flash/setup_hpc_flash.sh`
**一键部署脚本**: `scenarios/flash_demo/hello_flash/deploy_flash.py`（交互式选择 WSL/SSH1/SSH2）

超算 module 加载示例（Paracloud，两台机器相同）：
```bash
source /public1/soft/modules/module.sh
module load hdf5/1.8.18
module load mpich/3.2-gcc9.3

# HYPRE 用户空间编译 (无 sudo)
./configure --prefix=$(readlink -f ~/QC/FLASH/local/hypre) CC=mpicc CXX=mpicxx FC=gfortran F77=gfortran
```

> **重要**: ParaCloud 上 `$HOME` 是符号链接（`/public1/home/USER` → `/publicfs01/fs1-e/home/USER`），Makefile.h 中 HYPRE_PATH 必须使用 `readlink -f` 解析真实路径，否则编译会报 `HYPREf.h: No such file or directory`。

SLURM 作业提交：
```bash
sbatch ${FLASH_HOME}/submit_laserslab1d.slurm
squeue -u $(whoami)   # 查看作业状态
```

---

完整的远程仿真流程：连接超算 → 上传分析脚本 → 提交仿真作业 → 监控状态 → 分析输出 → 下载结果。

```python
# 使用 remote_workflow.py 一键执行
python -m physimx_sim.flash.remote_workflow

# 或使用 deploy_flash.py 交互式部署
python scenarios/flash_demo/hello_flash/deploy_flash.py
```

**核心步骤**（也可用 `legacy/scripts/ssh_workflow.py` 单独控制）：

| 步骤 | 功能 |
|------|------|
| SSH 直连 | 使用 CredentialManager 加密凭据连接超算 |
| 提交作业 | 基于 sbatch 模板提交 FLASH 仿真 |
| 监控状态 | 轮询 squeue/sacct 等待作业完成 |
| 上传脚本 | 通过 SFTP 将本地 Python 分析脚本上传到超算 |
| 远端执行 | 在超算上利用 anaconda3 环境执行分析（h5py + matplotlib） |
| 下载结果 | 通过 SFTP 将 PNG 图像等产物下载到本地 |

### 8. CHK 文件密度分析

```bash
# 在超算上运行（需要 h5py + numpy + matplotlib）
python3 analyze_dens.py /path/to/chk/dir --output density_evolution.png

# 在本地分析不同来源的数据
FLASH_SOURCE_SUFFIX=from_ssh1 python3 analyze_density.py  # SSH1 (NC-E)
FLASH_SOURCE_SUFFIX=from_ssh2 python3 analyze_density.py  # SSH2 (BSCC-T6)
```

脚本特性：
- 自动扫描 `*chk*` 文件并按仿真时间排序
- 支持 1D/2D FLASH AMR 块结构数据重构
- 自动检测仿真维度
- 多子图展示密度空间分布随时间演化
- 支持 `FLASH_SOURCE_SUFFIX` 环境变量切换数据来源
- 所有图表文字使用英文，避免中文渲染错误

### 9. 完整端到端流程示例

```bash
# 方式一：一键部署（推荐）
python deploy_flash.py
# 选择 [2] SSH1 或 [3] SSH2

# 方式二：手动步骤
# 1. 创建 AI 工作目录 (~/QC/AI/AItemp/)
# 2. 上传源码包到超算
# 3. 解压 FLASH + 配置 Makefile.h + 编译
# 4. 运行 LaserSlab 1D 仿真
# 5. 下载 HDF5 结果到本地
# 6. 运行密度分析绘图
```

---

## 创建新仿真 (Python API)

### 11. 创建自定义 FLASH 仿真

使用 Python API 自动生成仿真所需的全部输入文件。

一个 FLASH 仿真最少需要以下 8 个文件：
1. **Config** — 配置文件，声明 Runtime Parameters 和所需物理模块
2. **example1d.par** — 运行时参数（脉冲、网格、时间步长等）
3. **Makefile** — 编译文件（一般不修改）
4. **Simulation_data.F90** — 全局仿真数据声明
5. **Simulation_init.F90** — 运行时参数读取和初始化
6. **Simulation_initBlock.F90** — 空间网格定义和物质分配
7. **al-imx-003.cn4** — 铝（靶材）的状态参数表
8. **he-imx-005.cn4** — 氦（腔室）的状态参数表

这些文件需要放入 `FLASH4.8/source/Simulation/SimulationMain/QC/<sim_name>/` 目录。

#### 11.1 使用 ParGenerator 生成 .par 文件

```python
from flash.input_gen.par import ParGenerator, PulseShape

# 创建生成器
gen = ParGenerator(simulation_name="LaserSlab1d_new")

# 设置高斯脉冲（ICF 聚变功率密度 ~1e14 W/cm², 10个时间-功率点）
times, powers = PulseShape.from_intensity(
    intensity_w_cm2=1e14,
    spot_radius_cm=0.005,    # 50 um 焦斑半径
    duration=5e-9,            # 5 ns 脉宽
    n_points=10,              # 10 个时间-功率点对
)
gen.set_pulse(times, powers)

# 调整仿真时间和域参数
gen.set_time(tmax=1.75e-08, dtinit=1e-15)
gen.set_domain(xmin=0.0, xmax=160e-4, nblockx=4)
gen.set_target(height=20e-4, vacuum_height=140e-4)

# 保存
gen.save("example1d_new.par")

# 预览
print(gen.pulse_summary)
```

#### 11.2 使用 GridBuilder + BlockGenerator 生成 Simulation_initBlock.F90

```python
from flash.input_gen.block import BlockGenerator, GridBuilder, BlockVisualizer

# 构建网格
builder = GridBuilder(dim=1, geometry="cartesian", domain=(0, 160e-4))
builder.set_material("cham", rho=1e-6, tele=290.11375)
builder.set_material("targ", rho=2.7, tele=290.11375)
builder.add_region("vacuum", species="cham", 
                   x_range=(0, 140e-4), is_target=False)
builder.add_region("target", species="targ", 
                   x_range=(140e-4, 160e-4), is_target=True)

# 生成 F90 文件
gen = BlockGenerator(simulation_name="LaserSlab1d_new", 
                     sim_path="QC/LaserSlab1d_new")
gen.build(builder)
gen.save("Simulation_initBlock.F90")

# 可视化网格划分
viz = BlockVisualizer(builder)
viz.plot_1d("grid_preview.png")
print(viz.summary())
```

#### 11.3 编译和运行

```bash
# 假设文件已放入 FLASH4.8/source/Simulation/SimulationMain/QC/LaserSlab1d_new/

cd ~/QC/FLASH/FLASH4.8/

# Setup
./setup -auto QC/LaserSlab1d_new -1d +cartesian -nxb=16 -maxblocks=2048 \
  +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd \
  mgd_meshgroups=10 -objdir=QC/object -parfile=example1d_new.par

# 编译
cd QC/object/
make

# 运行
mpirun -np 1 ./flash4
```

#### 11.4 输出分析

```python
# 密度分析
python
analyze_density.py / path / to / output / hdf5files /

# 或使用内置分析器
from flash.temp_delete.output_analysis import FlashOutputReader

reader = FlashOutputReader("lasslab_new_hdf5_chk_0001")
print(reader.list_variables())
reader.close()
```

---

### 12. 材料数据库与替换

`input_gen/par/materials.py` 提供常见 ICF 材料的预设参数库，使材料切换标准化。

#### 12.1 可用靶材

| 名称 | 标识符 | cn4 文件 | rho (g/cm³) | A | Z | 用途 |
|------|--------|----------|-------------|---|---|------|
| 铝 (Al) | `aluminum` | al-imx-003.cn4 | 2.7 | 26.98 | 13 | 标准 ICF 靶材 |
| 聚苯乙烯 (CH) | `polystyrene` | polystyrene-imx-008.cn4 | 1.1 | 6.5 | 3.5 | 低密度塑料靶 |
| 铍 (Be) | `beryllium` | be-imx-003.cn4 | 1.848 | 9.01 | 4 | 低 Z 烧蚀层 |
| 金 (Au) | `gold` | au-imx-003.cn4 | 19.32 | 196.97 | 79 | 高 Z 腔壁 |
| 铜 (Cu) | `copper` | cu-imx-003.cn4 | 8.96 | 63.55 | 29 | 通用金属 |
| 碳 (C) | `carbon` | c-imx-003.cn4 | 3.515 | 12.01 | 6 | 金刚石靶 |

#### 12.2 腔室气体

| 名称 | 标识符 | cn4 文件 | rho (g/cm³) |
|------|--------|----------|-------------|
| 氦气 (He) | `helium` | he-imx-005.cn4 | 1.0e-06 |
| 氢气 (H₂) | `hydrogen` | h-imx-003.cn4 | 1.0e-07 |

#### 12.3 使用材料对象

```python
from flash.input_gen.par import ParGenerator, MATERIALS, CHAMBER_GASES, list_materials

# 查看所有可用材料
print(list_materials("target"))    # 靶材列表
print(list_materials("chamber"))   # 气体列表

# 创建仿真，指定靶材和腔室
gen = ParGenerator(simulation_name="LaserSlab1d_CH")

# 靶材用聚苯乙烯替代铝
gen.set_material(MATERIALS["polystyrene"])

# 腔室用氦气
gen.set_material(CHAMBER_GASES["helium"], target=False)

# 预览材料配置
print(gen.material_summary)
# 靶材: 聚苯乙烯 (CH), 低密度塑料靶材, 密度 1.1 g/cm³
#   rho=1.1 g/cm³, A=6.5, Z=3.5, file=polystyrene-imx-008.cn4
# 腔室: 氦气 (He), 1.6 mbar, 密度 ~1e-6 g/cm³
```

#### 12.4 材料替换时的关键步骤

1. **参数自动更新**: `set_material()` 自动替换 `sim_rho`, `A`, `Z`, `ZMin`, `eos_file`
2. **Config DATAFILES**: 必须声明新材料文件，使用 `gen.generate_config()` 自动生成
3. **cn4 文件**: 新材料文件需放入仿真目录
4. **不透明度**: `radiation_section` 中 `op_*FileName` 也需同步更新

```python
# 完整材料替换示例
gen = ParGenerator(simulation_name="LaserSlab1d_CH")
gen.set_material(MATERIALS["polystyrene"])  # 自动更新 rho/A/Z/eos_file

# 生成 .par 和 Config (DATAFILES 自动包含新材料)
gen.save("example1d_CH.par")
gen.save_config("Config")
```

---

### 13. 多光束/多脉冲配置

FLASH 激光系统层级结构:
```
Pulses (脉冲) → 时间-功率曲线
Beams (光束)  → 每个光束关联一个脉冲，定义空间方向和聚焦
```

#### 13.1 添加入射激光 (多光束)

**关键规则**:
- 必须设置 `ed_numberOfBeams = N`（N 为光束总数）
- `ed_lensX/Y/Z` 必须在仿真域外（`xmin` 之前或 `xmax` 之后）
- 对于 1D: 只需要 `lens_x` 和 `target_x`
- 对于 2D/3D: 还需 `lens_y/z`, `target_y/z`, `targetSemiAxisMajor/Minor` 等
- 参考文件: `scenarios/flash_demo/LaserSlab/example3d.par`, `3Din2D.par`

**如果所有光束时间功率相同**: 使用统一脉冲，不同光束通过 `pulse_number` 指向同一脉冲。

```python
from flash.input_gen.par import ParGenerator, BeamConfig, PulseShape

gen = ParGenerator(simulation_name="LaserSlab1d_2beams")

# 统一的脉冲 (所有光束共用)
times, powers = PulseShape.trapezoid(peak_power=1e12)
gen.set_pulse(times, powers)

# 2个光束，从两侧入射
gen.set_beams([
    BeamConfig(beam_id=1, lens_x=-1.0, target_x=0.0e-04),    # 左侧→中心
    BeamConfig(beam_id=2, lens_x=1.0, target_x=0.0e-04),     # 右侧→中心
])

gen.save("example1d_2beams.par")
print(gen.beam_summary)
```

#### 13.2 多脉冲 (不同光束不同功率曲线)

如果光束的时间功率**不同**，必须设置 `ed_numberOfPulses = M`：

```python
from flash.input_gen.par import PulseConfig

# 脉冲1: 方波, 6个时间点
t1 = [0.0, 0.1e-9, 1.0e-9, 4.0e-9, 4.1e-9, 5.0e-9]
p1 = [0.0, 1e11, 1e11, 1e11, 1e11, 0.0]

# 脉冲2: 高斯, 6个时间点  
t2 = [0.0, 0.5e-9, 1.0e-9, 1.5e-9, 2.0e-9, 2.5e-9]
p2 = [0.0, 5e10, 1e11, 5e10, 2e10, 0.0]

gen.set_pulses([
    PulseConfig(pulse_id=1, times=t1, powers=p1),  # 6 sections
    PulseConfig(pulse_id=2, times=t2, powers=p2),  # 6 sections
])

gen.set_beams([
    BeamConfig(beam_id=1, lens_x=-1.0, target_x=0.0, pulse_number=1),
    BeamConfig(beam_id=2, lens_x=1.0, target_x=0.0, pulse_number=2),
])
```

#### 13.3 2D/3D 光束扩展参数

```python
# 2D 圆柱几何 / 3D Cartesian 需要额外参数
BeamConfig(
    beam_id=2,
    lens_x=0.0, lens_y=-0.01, lens_z=0.0,
    target_x=0.0, target_y=0.0, target_z=0.0,
    cross_section_type="gaussian2D",
    grid_type="radial2D",
    grid_radial_tics=1024,
    number_of_rays=64,
    gaussian_radius_major=0.005,     # 光斑长半径 (cm)
    gaussian_radius_minor=0.003,     # 光斑短半径 (cm)
    gaussian_exponent=2.0,
    target_semi_axis_major=0.01,
    target_semi_axis_minor=0.005,
    lens_semi_axis_major=1.0,
    semi_axis_major_torsion_axis="x",
    semi_axis_major_torsion_angle=30.0,
)
```

---

### 14. LaserSlab1d_3beams 仿真示例

三光束对称入射铝靶仿真，验证多光束 + 材料预设 API。

```python
from flash.input_gen.par import (
    ParGenerator, BeamConfig, PulseShape, MATERIALS, CHAMBER_GASES
)

gen = ParGenerator(simulation_name="LaserSlab1d_3beams")
gen.set_material(MATERIALS["aluminum"])
gen.set_material(CHAMBER_GASES["helium"], target=False)

times, powers = PulseShape.trapezoid(peak_power=1e12)
gen.set_pulse(times, powers)

gen.set_beams([
    BeamConfig(beam_id=1, lens_x=-1.0, target_x=0.0e-04),
    BeamConfig(beam_id=2, lens_x=1.0, target_x=0.0e-04),
    BeamConfig(beam_id=3, lens_x=-1.0, target_x=140.0e-04),
])
gen.set_domain(xmin=-160.0e-04, xmax=160.0e-04, nblockx=6)
gen.set_time(tmax=1.2e-09, dtinit=1e-15)

gen.save("example1d_3beams.par")
gen.save_config("Config")

# 仿真文件位于: scenarios/flash_demo/LaserSlab1d_3beams/
```

**Setup/编译/运行** (WSL):
```bash
cd ~/QC/FLASH/FLASH4.8/
./setup -auto QC/LaserSlab1d_3beams -1d +cartesian -nxb=16 \
  -maxblocks=2048 +hdf5typeio species=cham,targ \
  +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/object_3beams
cd QC/object_3beams/ && make
cd outputfiles && mpirun -np 1 ../flash4
```

**密度分析**:
```bash
python run_and_analyze.py --hdf5-dir output/laserslab1d_3beams/hdf5files \
                          --output-dir output/laserslab1d_3beams/plots
```

---

## 操作规范

所有 FLASH 仿真操作须遵守以下规范，详见：

- **[flash_operation_standard.md](flash_operation_standard.md)** — FLASH 仿真完整操作规范
  - 绘图语言规范: 所有图表标题、轴标签、图例、颜色条必须使用英文
  - 仿真运行规范: 8个必要文件、WSL/超算运行流程、Docker 命令
  - 结果处理规范: HDF5 结构、output_processors 使用、绘图检查清单
  - 仿真验证标准: 完成标志、输出文件检查、AMR 验证
  - 代码编写规范: 路径管理、导入路径、容器属性名

---

## 依赖

```bash
# 必需
pip install numpy

# HDF5 输出分析 (可选)
pip install h5py

# 绘图 (可选)
pip install matplotlib

# SSH 远程运行 (可选)
pip install paramiko
```

---

## 代码规范

### 行尾格式

**所有源文件必须使用 Unix (LF) 换行符**，禁止 Windows CRLF。

原因: FLASH 仿真代码在 Linux 上运行，CRLF 会导致 Shell 脚本 `$'\r'` 错误、Fortran 编译异常、`.par` 文件解析失败。

保障机制:
- `.gitattributes` 强制 `* text=auto eol=lf`
- Git 配置 `core.autocrlf=input`, `core.eol=lf`
- 所有文件已归一化为 LF (956 个 CRLF 文件已转换)

详细规范参见 `docs/flash_operation_standard.md` 第 2 节，Git 工作流参见 `docs/GIT_WORKFLOW.md`。
