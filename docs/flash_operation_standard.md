# FLASH 仿真操作规范 (Operation Standard)

## 1. 绘图语言规范

**所有绘图元素必须使用英文**，包括但不限于：
- 图像标题 (title): 全英文, 如 "Density Distribution (t=1.0e-09s)"
- X/Y 轴标签 (xlabel/ylabel): 全英文, 如 "x [cm]", "Mass density [g/cm^3]"
- 图例 (legend): 全英文, 如 "dens", "tele"
- 颜色条标签 (colorbar label): 全英文, 如 "Electron temperature [K]"

**不需要改英文的地方**:
- 控制台日志输出 (console log)
- 代码注释 (code comments)
- 文档/README (可中英混用)

**执行方法**:
- `output_processors/hdf5processor/flash_hdf5.py` 中 `DATA_CONFIG` 的 `description` 字段全部使用英文
- `output_processors/plotter/plot_generator.py` 中所有 `set_xlabel/set_ylabel/set_title` 使用英文
- 用户调用 `plotter.plot()` 时传入英文 title

### 1.1 字体大小规范 (PPT 友好, 强制)

**所有绘图脚本产出的图片必须适用于 PPT 演示, 字号不得小于 18pt。**

| 元素 | 最小字号 | 默认 (plot_style) |
|------|---------|------------------|
| 图标题 title | 22 | 22 |
| 轴标签 xlabel/ylabel | 20 | 20 |
| 刻度 tick | 18 | 18 |
| 图例 legend | 18 | 18 |
| colorbar 标签 | 18 | 18 |
| 图中注释/文本 | 18 | 18 |

**强制要求**:
1. 包内**所有** matplotlib 绘图脚本必须在 `import matplotlib.pyplot` 之后、任何绘图之前调用:
   ```python
   from output_processors.plotter.plot_style import apply_plot_style
   apply_plot_style()          # 全局 rcParams: 字体≥18, 全英文, dpi=200
   ```
2. 禁止在脚本中手工指定 `fontsize=8/10/12/13/14` 等小于 18 的字号;
   必须依赖 `plot_style` 的全局设置 (或显式 `fontsize>=18`)。
3. 图片中任何文本 (标题/轴标签/图例/colorbar/注释) 禁止出现中文;
   推荐用 `english()` 清洗: `from output_processors.plotter.plot_style import english`。
4. 保存图片建议用 `save_figure(fig, path)` (dpi=200 + tight bbox)。

**统一模块**: `output_processors/plotter/plot_style.py`
- `apply_plot_style()`: 一键应用全局样式
- `english(text)`: CJK/Unicode 符号 → ASCII 英文 (如 μm→um, g/cm³→g/cm^3)
- `new_figure(figsize)`: 创建 PPT 友好画布
- `save_figure(fig, path)`: 保存 (dpi=200, tight)
- `setup_colorbar(cbar, label)` / `setup_legend(ax)`: 统一英文+大字号

**合规检查**: 运行 `python scripts/check_plot_style.py` 扫描全包,
自动列出未调用 `apply_plot_style()` 或图中文本含中文字符的脚本。

## 2. 行尾格式规范

**所有产出文件必须使用 Unix (LF) 换行符**，禁止 Windows CRLF。

### 原因
FLASH 仿真代码（Fortran/Shell）和配置文件（`.par`）主要在 Linux 上运行，CRLF 会导致：
- Shell 脚本报 `$'\r': command not found`
- Fortran 编译器报 `Illegal character` 错误
- `.par` 参数文件解析异常
- Python 脚本在 WSL 中运行时报 `SyntaxError: invalid character in identifier`

### 适用范围
所有文本文件均需使用 LF 换行：
- `.py`, `.F90`, `.f90`, `.f`, `.F` — 源代码
- `.sh`, `.bat`, `.cmd` — 脚本文件
- `.par`, `.cn4`, `.inp` — FLASH 输入参数
- `.md`, `.rst`, `.txt` — 文档
- `.json`, `.yaml`, `.yml`, `.toml` — 配置文件
- `.csv`, `.xml` — 数据文件

### 保障机制
- `.gitattributes`（仓库根目录）：`* text=auto eol=lf`
- git 配置：`core.autocrlf=input`，`core.eol=lf`
- `pre-commit` 钩子可检查新增文件的换行符
- 新提交的文件会自动被 git 归一化为 LF

### 本机设置
```bash
# 确保 git 正确配置（已执行）
git config core.autocrlf input
git config core.eol lf
```

## 3. 仿真运行规范

### 2.1 目录结构

```
flash/
├── scenarios/flash_demo/
│   ├── LaserSlab1d/         # 仿真参考文件 (Config, .par, .cn4, .F90)
│   ├── laserslab1d_local_demo.py              # 本地运行 Demo (v2.1)
│   ├── laserslab1d_supercomputer_demo.py       # 超算运行 Demo (v2.1)
│   ├── laserslab1d_hpc_demo_batch.py           # 超算批量运行 Demo (多功率对比)
│   └── demo_task/           # Demo 运行产物 (自动生成, 不入版本库)
│       ├── laserslab1d_local_demo/
│       │   ├── run/         # ← 独立运行文件夹 (11 个文件 + 一键脚本)
│       │   └── output/      # 仿真输出 (HDF5 + 图像)
│       ├── laserslab1d_supercomputer_demo/
│       │   ├── run/         # ← 独立运行文件夹 (11 个文件 + 一键脚本)
│       │   └── output/      # 仿真输出 (HDF5 + 图像)
│       └── laserslab1d_hpc_demo_batch/
│           ├── run/power_0.5~2.0/   # 各功率独立运行文件夹
│           ├── output/power_0.5~2.0/ # 下载的 HDF5 输出
│           └── plots/               # 对比分析图像
├── output_processors/       # 输出处理包 (全英文绘图)
└── docs/
    └── flash_operation_standard.md  # 本文档
```

### 2.2 一次仿真最少需要的文件 (8个)

| 文件 | 说明 | 必须? |
|------|------|-------|
| `Config` | 配置文件, 声明模块和运行时参数 | 是 |
| `<name>.par` | 运行时参数文件 | 是 |
| `Makefile` | 编译文件 (一般不需修改) | 是 |
| `Simulation_data.F90` | 全局仿真数据声明 | 是 |
| `Simulation_init.F90` | 运行时参数读取和初始化 | 是 |
| `Simulation_initBlock.F90` | 空间网格定义和物质分配 | 是 |
| `<ionmix4>.cn4` (x2) | EOS+不透明度表 (靶材+腔室) | 是 |

### 2.3 运行流程

**本地 (WSL)**:
```bash
# 1. 创建运行目录
mkdir -p /tmp/flash_run_$(date +%Y%m%d_%H%M%S) && cd $_

# 2. 准备文件
cp ~/QC/FLASH/FLASH4.8/object_1d/flash4 ./
cp /path/to/*.par flash.par
cp /path/to/*.cn4 ./

# 3. 运行
export PATH="/usr/local/mpich/bin:/usr/local/hdf5/bin:$PATH"
export LD_LIBRARY_PATH="/usr/local/mpich/lib:/usr/local/hdf5/lib:/usr/local/hypre/lib"
mpirun -np 1 ./flash4

# 4. 验证
ls *hdf5_chk_*  # 应有文件
```

**超算 (SSH)**:
```bash
# 1. 登录
ssh user@host

# 2. 加载环境
source /public1/soft/modules/module.sh
module load hdf5/1.8.18
module load mpich/3.2-gcc9.3  # 或可用版本

# 3. 创建运行目录
mkdir -p ~/QC/AI/flash_run_$(date +%Y%m%d_%H%M%S) && cd $_

# 4. 给 .par 和 .cn4 文件
cp /path/to/*.par flash.par
cp /path/to/*.cn4 ./

# 5. 提交 SLURM 作业
sbatch << 'EOF'
#!/bin/bash
#SBATCH --job-name=FLASH
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=01:00:00
#SBATCH --output=flash_%j.out

source /public1/soft/modules/module.sh
module load hdf5/1.8.18
module load mpich/3.2-gcc9.3
cd $PWD
mpirun -np 4 ~/QC/FLASH/FLASH4.8/object/flash4
EOF
```

**批量超算 (HPC Batch)**:
```bash
# 方式 1: Python 一键批量 (推荐)
python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch
# 自动完成: 生成多功率变体 → 上传(含分析脚本) → sbatch → 远程分析 → 下载结果

# 方式 2: 手动批量
# 先检测可用分区:
python -m physimx_sim.flash.test.remote_connect.test_sbatch
# 为每个功率因子生成独立运行文件夹
# 上传到超算: ~/QC/AI/AItemp/flash_batch_<ts>_p<pf>/
# 提交 sbatch submit_flash.sh
# 用 sacct -j <jobid> 监控状态
# 手动上传并运行远程分析: python remote_analysis.py --dirs ... --powers ...

# 注意: submit_flash.sh 已内置 SLURM_SUBMIT_DIR 和 SLURM_NTASKS 回退机制,
# 既可通过 sbatch 提交，也可直接 bash submit_flash.sh 运行
# HDF5 完整输出保留在超算, 只下载分析结果 (JSON + PNG)
```

### 2.4 批量仿真设计规范

**功率因子变体生成流程**:
1. 使用 `create_input_files()` 生成基准仿真文件 (传入 `platform="hpc"`)
2. 使用 `shutil.copytree()` 为每个功率因子复制独立目录
3. 使用正则替换修改 `.par` 文件中的 `ed_power*` 参数值（乘以 `power_factor`）
4. 修改 `submit_flash.sh` 和 `run_flash.sh` 中的作业名（添加 `_p{pf}` 后缀）
5. 清理基准目录

**SLURM 队列分发策略**:
- 先运行 `test/remote_connect/test_sbatch.py` 检测用户可用分区
- 根据结果配置 `SLURM_PARTITIONS`（当前用户 `scfa2696` 只有 `v5_192` 分区）
- sbatch 失败时自动降级为直接 `bash run_flash.sh`

**远程目录命名规范**:
```
~/<SIM_USER_DIR>/AI/Aitemp/flash_batch_<YYYYMMDD_HHMMSS>_p<POWER_FACTOR>/
```

**资源配置自动计算** (`resource_config.json`):
- `slurm_mem_gb`: `node_mem_total_gb × max_cpu_percent / 100 / max_parallel`
- `slurm_ntasks_per_node`: `node_cores × max_cpu_percent / 100 / max_parallel`
- ShellScriptGenerator 根据 `dimension` + `platform` 自动加载

**远程分析规范**:
- `remote_analysis.py` 自包含脚本, 通过 SCP 随仿真文件一起上传
- 超算上优先使用 `module load python/3.9.6` (唯一有 h5py 3.3.0 的模块)
- `python/3.10.8` 和 `python/3.8.6` 无 h5py (已验证)
- 分析结果 (JSON + PNG) 下载到本地, HDF5 保留在超算

**FLASH HDF5 复合类型 (compound dataset) 处理规范**:
- `real scalars` 是复合类型结构化数组 `[(name, S80), (value, f8)]` **不是 group**
- 不能通过 `f["real scalars"]["time"]` 访问, 必须:
  ```python
  rs = f["real scalars"][()]
  for i in range(len(rs)):
      name = rs["name"][i].decode("utf-8").strip()
      if name == "time":
          t = float(rs["value"][i])
  ```

**SLURM 输出目录命名规范**:
- `submit_flash.sh` 使用 `outputfiles_YYYYMMDD_HHMMSS/` 时间戳命名
- 分析脚本必须动态查找: `ls -d {remote_dir}/outputfiles_*`

**SLURM 脚本回退机制** (submit_flash.sh):
- `SCRIPT_DIR` = `${SLURM_SUBMIT_DIR:-$PWD}`
- `TOTAL_TASKS` = `${SLURM_NTASKS:-4}`

### 2.4 Docker 运行 (WSL Ubuntu-22.04)

```bash
wsl -d Ubuntu-22.04 -u root -- bash -c "cd /tmp/run_dir && export PATH=/usr/local/mpich/bin:/usr/local/hdf5/bin:\$PATH && export LD_LIBRARY_PATH=/usr/local/mpich/lib:/usr/local/hdf5/lib:/usr/local/hypre/lib:\${LD_LIBRARY_PATH:-} && mpirun -np 1 ./flash4"
```

## 3. 结果处理规范

### 3.1 HDF5 输出结构

- checkpoint: float64, `~44` 变量, 完整物理态
- plot: float32, `~9` 变量, 用于可视化
- 命名: `<basename>_hdf5_chk_<NNNN>`, `<basename>_hdf5_plt_cnt_<NNNN>`
- 形状: `(nblocks, Nz, Ny, Nx)` C 顺序
- 边界框: `(nblocks, 3, 2)` min/max for x/y/z

### 3.2 使用 output_processors 绘图

```python
from output_processors.loader import FlashDataLoader
from output_processors.plotter import FlashPlotter

loader = FlashDataLoader("path/to/hdf5_chk_0000")
container = loader.load(compute_derived=True)

# 自动检测维度并绘图 (1D线图/2D伪彩/3D切片)
plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png",
             title="Density Distribution (t=...s)")
```

### 3.3 绘图语言检查清单

- [ ] `title` 参数全英文
- [ ] `_get_label()` 返回英文描述
- [ ] `set_xlabel()`/`set_ylabel()` 全英文
- [ ] `set_title()` 全英文
- [ ] colorbar label 全英文
- [ ] legend 全英文
- [ ] 不依赖系统中文字体
- [ ] 已调用 `apply_plot_style()` (import plot_style)
- [ ] 所有字号 ≥ 18 (无 `fontsize=8/10/12/13/14` 等小字号)
- [ ] 无中文字符出现在任何绘图文本中 (可用 `check_plot_style.py` 验证)
- [ ] 保存使用 dpi≥200 (推荐 `save_figure()`)

## 4. 仿真验证标准

| 检查项 | 标准 | 判定 |
|--------|------|------|
| 仿真完成 | `exiting: reached max SimTime` | PASS |
| 输出文件 | 至少 1 个 `*hdf5_chk_*` | PASS |
| 网格自适应 | 输出显示 `refined: total blocks` | PASS |
| 物理量有效 | `dens` > 0, `tele` > 0 | PASS |
| AMR 正常 | leaf blocks > 初始 blocks | PASS |

## 5. 代码编写规范

### 5.1 路径管理

```
# 文件在: PhySimX/physimx_sim/src/physimx_sim/flash/scenarios/flash_demo/
# Python 包根: PhySimX/physimx_sim/src/
# 到包根需要 .parent x5
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

### 5.2 脚本导入路径

```python
# 从 PhySimX/physimx_sim/src/ 可以导入:
from flash.input_gen.par import ParGenerator
from flash.output_processors.loader import FlashDataLoader
from flash.output_processors.plotter import FlashPlotter
from flash.flash_run.env.env_manager import FlashEnvManager
```

### 5.3 容器属性名

| 属性 | 旧名 (不用) | 标准名 |
|------|-----------|--------|
| 维度 | `dimension` | `ndim` |
| 变量 | `variables` | `data` |
| 派生变量 | - | `derived` |
| 网格信息 | - | `grid`` |
