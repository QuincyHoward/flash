# Hello FLASH! — 快速入门指南

> 零依赖、一键安装 + LaserSlab 1D 仿真 + 密度分析，开箱即用


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
| **版本标签** | 以 `git tag -l` 查看全部 (PyPI 按阶段更新) |
| **问题反馈** | 通过 Gitee Issues 提交 (登录后新建 Issue) |

> 发布包已通过全局测试 (233 passed / 3 skipped) 与 FLASH 版权合规检查, (详见 [许可](#许可) 与 [NOTICE](NOTICE))。

---

## 概述

`hello_flash/` 是 FLASH 快速上手包，包含从零安装到运行首个仿真并生成分析图表的完整流程。

**所有代码完全自包含**，无需外部模块依赖，适合以下用户：

- **首次接触 FLASH** 的新手，快速验证安装
- **WSL (Windows Subsystem for Linux)** 环境用户
- **超算 / HPC** 首次配置验证


---

## 前期准备工作（必读）

只需 3 步准备，全部就绪后安装约 30–60 分钟。

### a. 安装 WSL + Ubuntu

Windows PowerShell（管理员）运行：

```powershell
wsl --install -d Ubuntu
```

> 首次启动会设置 Linux 用户名和密码（**请记住密码**，sudo 安装依赖需要）；完成后重启电脑，从开始菜单启动 Ubuntu。

### b. 下载 4 个软件包（放入 flash/flash_src/）

| 软件包              | 文件名                   | 下载地址（多个备用，任选其一）                                                                        |
|---|---|---|
| **FLASH** 4.8    | `FLASH4.8.tar.gz`     | <https://flash.rochester.edu/site/flashcode/>                                          |
| **HDF5** 1.8.12  | `hdf5-1.8.12.tar.gz`  | <https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.8/hdf5-1.8.12/obtain51812.html> |
|                  |                       | <https://github.com/HDFGroup/hdf5/releases>                                            |
| **HYPRE** 2.9.0b | `hypre-2.9.0b.tar.gz` | <https://pkgs.org/download/hypre>                                                      |
|                  |                       | <https://github.com/hypre-space/hypre/releases>                                        |
| **MPICH** 3.2    | `mpich-3.2.tar.gz`    | <https://www.mpich.org/downloads/>                                                     |
|                  |                       | <https://www.mpich.org/static/downloads/3.2/>                                          |

保存到 `flash/flash_src/`（或 `hello_flash/` 目录），校验 4 个文件齐全：

```bash
ls -la flash_src/*.tar.gz
```


### c. （可选）下载 IONMIX — 生成自定义材料表用

📌 **与首次安装运行无关**，仅当后期需要用 `gen_eos_op` 生成自定义 EOS/不透明度表（`.cn4`）时才下载：

- **来源**：<https://elsevier.digitalcommonsdata.com/datasets/8n4r3rh8kr/1> （DOI `10.17632/8n4r3rh8kr.1`）
- **文件**：`abjt_v1_0.gz` → 解压到 `input_gen/gen_eos_op/ionmix/ionmix/src/Ionmix/`

### d. 点击执行 flash/_core/credentials/manage.py 设置凭证文件的用户名（默认为hello）

> ⚠️ **不要直接执行脚本！** 完成以上准备后，把本 README 与脚本交给 **Agent AI 助手**执行（它会自动微调适配你的装置状态），操作要点见后续「推荐方法」章节。

---

## Agent 使用记录

### Agent 对话
用户：
```
仿照“flash\scenarios\flash_demo\hello_flash”帮我在当前的WSL中安装FLASH4.8，并使用LaserSlab一维仿真进行测试

你可能需要微调代码，注意提取使用flash\_core\credentials设置的专属用户名字段
```
AgentAI:

> 📌 截图说明：以下 Agent 使用记录截图（`screenshots/`）与分析图（`outputfiles/plots/`）为**本地运行产物，不随发布包分发**，请在本地运行后查看生成的分析图。
>
> - `screenshots/hello_flash_task_talk.png` — Agent 对话与任务截图（本地开发记录）
> - `outputfiles/plots/density_heatmap_and_stats.png` — 密度 x-t 热图与统计（本地运行生成）
> - `outputfiles/plots/density_snapshots.png` — 密度快照对比（本地运行生成）
> - `outputfiles/plots/density_vs_x_evolution.png` — 密度演化曲线（本地运行生成）

---
---
---



以下内容用户可以只简单了解即可，由AgentAI进行具体理解和执行。

## 目录结构

```
scenarios/flash_demo/hello_flash/
├── deploy_flash.py              ← 一键部署脚本 (WSL/SSH1/SSH2 交互式菜单)
├── install_flash_wsl.sh         ← [阶段1] WSL 安装脚本 (6步幂等安装)
├── run_hello_flash.sh           ← [入口] 一键完成安装+仿真+分析
├── run_and_collect.sh           ← [阶段2] 仿真运行 + 结果收集 + 密度分析
├── run_simulation.sh            ← 仅运行仿真 (独立步骤)
├── compile_flash.sh             ← 仅编译 FLASH (独立步骤)
├── collect_hdf5.sh              ← 仅收集 HDF5 文件 (独立步骤)
├── analyze_density.py           ← [阶段3] 密度时空演化分析 (HDF5 → PNG)
├── flash_user_lib.sh            ← 用户名解析库 (credentials → 默认 hello, 勿硬编码)
├── FLASH_one_click_install.sh   ← 完整一键安装 (含仿真+分析, 旧版)
├── FLASH_Install_WSL.sh         ← 早期 WSL 安装脚本 (历史遗留)
├── setup_hpc_flash.sh           ← 超算配置参考 (不自动执行)
├── setup_makefile.sh            ← Makefile.h 配置 (独立步骤)
│
└── outputfiles/                 ← 自动生成的输出目录
    ├── hdf5files/laserslab1d/         ← 本地 WSL checkpoint 文件
    ├── hdf5filesfrom_ssh1/laserslab1d/ ← SSH1 (NC-E) checkpoint 文件
    ├── hdf5filesfrom_ssh2/laserslab1d/ ← SSH2 (BSCC-T6) checkpoint 文件
    ├── plots/                         ← 本地 WSL 分析图表
    ├── plotsfrom_ssh1/                ← SSH1 分析图表
    └── plotsfrom_ssh2/                ← SSH2 分析图表
```

> **源码包说明（重要）：** 本发布包**不包含** FLASH / MPICH / HDF5 / HYPRE / IONMIX 等第三方源码包（受 FLASH License Agreement §3 约束，禁止再分发）。
>
> 源码包目录 `flash_src/` 中的 `.tar.gz` 文件需**用户自行下载**，具体下载地址与说明请参见：
>
> - 本 README「前期准备工作 → b. FLASH 相关软件包的获取与下载」（完整下载地址表）
> - `input_gen/gen_eos_op/ionmix/ionmix/docs/IONMIX用户指南.md`（IONMIX EOS/不透明度表生成源码，来自 Elsevier Digital Commons Data）
>
> 下载完成后放入 `flash_src/` 目录，安装脚本会自动检测；缺失时脚本会明确报错并列出所需文件。

---

## 推荐方法：通过 Agent AI 微调适配（强烈建议）

> ⚠️ **不要直接点击脚本执行！** 本教程的脚本是给 **Agent AI 助手**使用的"操作蓝图"。
>
> 推荐做法：把本教程与脚本交给 Agent AI，由 Agent **结合你当前装置的实际情况**（WSL/Ubuntu 版本、gcc 编译器版本、内存核数、网络环境、sudo 权限等）**自动微调适配**后执行。

### 为什么推荐 Agent 方式？

| 直接执行脚本                               | 通过 Agent AI 微调适配                          |
|---|---|
| 需要手工处理环境差异（gcc 版本、sudo 密码、网络代理等）     | Agent 自动检测环境并调整编译参数                       |
| Ubuntu 26.04 等新版源无 gcc-9 → 编译报错需自行排查 | Agent 自动改用系统编译器 + 兼容标志，或安装旧版 gcc-9        |
| 脚本默认参数（如 `-np 1`）可能与你的装置不匹配          | Agent 根据核数/内存自动选择并行度                      |
| 出错时需逐行排查日志                           | Agent 读取日志、定位根因、修复后重跑                     |
| 用户名/路径需手动配置                          | Agent 自动读取 `flash._core.credentials` 的用户名 |

### 使用步骤（推荐工作流）

1. **准备**：完成上文「前期准备工作」（WSL + 4 个软件包下载到位）。
2. **打开 Agent AI 助手**，并把以下信息告诉它：
   - 你的环境：`cat /etc/os-release`、`nproc`、`free -g`、`uname -a` 的输出
   - 源码包位置（如 `flash/flash_src/`）
   - 目标：安装 FLASH 4.8 并运行 LaserSlab 1D 仿真 + 密度分析
3. **Agent 会依次执行**：
   - 检测并微调脚本（编译器版本、路径、并行度等）
   - 安装系统依赖 → 编译 MPICH/HDF5/HYPRE → 解压配置 FLASH → 编译 flash4
   - 运行 LaserSlab 1D 仿真 → 收集 HDF5 → 调用 `analyze_density.py` 生成图表
4. **核对结果**：确认 `outputfiles/plots/` 下 3 张分析图生成。

> 本仓库的实际 Agent 使用记录与截图见上文「Agent 使用记录」章节，可参考其格式补充你自己的使用记录。

---
## 第一次使用：三阶段操作指南

### 📦 阶段 1：安装 FLASH

选择合适的安装方式：

**方式 A：一键部署（推荐）**

```bash
cd scenarios/flash_demo/hello_flash
python deploy_flash.py
```

> 💡 **Agent 方式（推荐）**：直接把 `python deploy_flash.py` 交给 Agent AI 执行（见「推荐方法：通过 Agent AI 微调适配」），它会自动适配你的环境，无需手动点选菜单。

交互菜单选 `[1] Local WSL`，脚本自动完成：

- 安装系统依赖 (gcc-9, gfortran-9, LAPACK 等)
- 从源码编译 MPICH 3.2 / HDF5 1.8.12 / HYPRE 2.9.0b
- 解压并配置 FLASH 4.8
- 编译 LaserSlab 1D 可执行文件

> 耗时约 30-60 分钟（取决于网络和 CPU）

**方式 B：手动分步安装（适合排查问题）**

```bash
# 第1步：安装 FLASH 到 ~/<用户名>/FLASH/
bash install_flash_wsl.sh

# 查看安装日志
ls -la ~/<用户名>/FLASH/FLASH4.8/object/flash4  # 确认可执行文件
```

> **用户名说明**：`<用户名>` 通过 **`flash._core.credentials`** 设置（`python -m flash._core.credentials user <名字>`）。
>
> 脚本会自动读取设置的用户名；读取不到时使用默认用户名 `hello`（默认密码 `123`，见 credentials 的 SSH 凭据模板）。
>
> 所有脚本均不硬编码用户名，详见下方「用户名设置」。

**方式 C：仅编译（重新编译或修复编译错误）**

```bash
bash compile_flash.sh
```

---

### 🎯 阶段 2：运行仿真

安装完成后，运行 LaserSlab 1D 基准测试：

**方式 A：总入口脚本**

```bash
# 如果已安装，跳过安装阶段
bash run_hello_flash.sh --skip-install
```

**方式 B：分步运行**

```bash
# 第2步：运行仿真 + 收集 HDF5 + 密度分析
bash run_and_collect.sh
```

**方式 C：仅运行仿真（不分析）**

```bash
bash run_simulation.sh
```

仿真输出：

- 41 个 checkpoint 文件 (`lasslab_hdf5_chk_*`)
- 80 个 plot 文件 (`lasslab_hdf5_plt_cnt_*`)
- 网格从 4 块加密至约 36 块 (约 20 leaf)
- 耗时约 3-10 分钟

---

### 📊 阶段 3：结果分析

**方式 A：自动分析（已在阶段 2 中包含）**

`run_and_collect.sh` 会自动调用 `analyze_density.py`。

**方式 B：手动分析**

```bash
# 分析本地 WSL 数据（默认）
python3 analyze_density.py

# 分析 SSH1 数据
FLASH_SOURCE_SUFFIX=from_ssh1 python3 analyze_density.py
```

生成 3 张分析图：

| 文件名                             | 内容                              |
|---|---|
| `density_vs_x_evolution.png`    | 全部时间步 dens vs x 曲线 (viridis 色带) |
| `density_heatmap_and_stats.png` | x-t 密度谱 + 最大/平均密度统计             |
| `density_snapshots.png`         | 首/中/末时间步密度对比                    |

输出路径：`outputfiles/plots/`

---

## 各脚本详细说明

| 脚本                           | 行数  | 核心功能                                                          | 适用阶段  |
|---|---|---|---|
| `deploy_flash.py`            | 793 | Python 一键部署，交互菜单选目标机，自动完成上传→安装→编译→运行→下载→分析                    | 🚀 首次 |
| `install_flash_wsl.sh`       | 411 | WSL 6步安装：系统依赖 → MPICH → HDF5 → HYPRE → 解压FLASH → 编译。幂等设计，中断可续 | 📦 安装 |
| `run_hello_flash.sh`         | 140 | Shell 总入口，`--skip-install` 跳过安装，自动查找源码包目录                     | 🚀 首次 |
| `run_and_collect.sh`         | 249 | 核心流程：检测已有结果 → 运行仿真 → 复制HDF5 → 调用分析脚本                          | 🎯 运行 |
| `run_simulation.sh`          | 65  | 纯仿真运行：准备运行目录 → 复制EOS表+参数文件 → `mpirun -np 1`                   | 🔧 调试 |
| `compile_flash.sh`           | 53  | 纯编译：`./setup` + `make -j$(nproc)`，验证 flash4 生成                | 🔧 调试 |
| `collect_hdf5.sh`            | 36  | 纯收集：从 FLASH 运行目录复制 HDF5 到 outputfiles/                        | 🔧 调试 |
| `analyze_density.py`         | 410 | Python 密度分析：读 HDF5 → 提取 dens → 输出 3 种分析图                      | 📊 分析 |
| `FLASH_one_click_install.sh` | 654 | 旧版一键安装(含仿真+分析)，环境变量驱动配置                                       | (历史)  |
| `FLASH_Install_WSL.sh`       | 329 | 早期 WSL 安装步骤(手动)，**仅参考**                                       | (历史)  |
| `setup_hpc_flash.sh`         | 295 | 超算配置参考，提供完整安装思路但**不自动执行**                                     | 📋 参考 |
| `setup_makefile.sh`          | 51  | 配置 FLASH Makefile.h：替换 MPI/HDF5/HYPRE 路径，添加 LAPACK            | 🔧 调试 |

---

## 用户名设置（重要）

FLASH 安装路径为 `~/<用户名>/FLASH/FLASH4.8/`。**用户名必须通过 `flash._core.credentials` 设置**，所有脚本（`install_flash_wsl.sh`、`run_hello_flash.sh`、`deploy_flash.py` 等）会自动读取；**读取不到时使用默认用户名 `hello`（默认密码 `123`）**。

```bash
# 查看当前用户名
python -m flash._core.credentials user

# 设置专属用户名 (例如 physimx_user)
python -m flash._core.credentials user physimx_user

# 等价 Python 方式
python -c "from flash._core.credentials import set_user_name; set_user_name('physimx_user')"
```

> - 代码中**不得硬编码用户名**（具体用户名仅存在于 flash.\_core.credentials 中）；未读取到时的回退默认值为 hello。
> - 设置后 FLASH 安装/运行路径自动变为 `~/<用户名>/FLASH/FLASH4.8/`。
> - SSH 超算凭据（含默认密码 `123`）同样通过 `flash._core.credentials` 管理：`python -m flash._core.credentials`（交互菜单）。

---
## 环境变量

| 变量                    | 默认值                            | 说明                                |
|---|---|---|
| `FLASH_SIM_USER_DIR`  | 动态（credentials 用户名，回退 `hello`） | FLASH 用户名，优先于 credentials 读取      |
| `FLASH_USER_HOME`     | `~/<用户名>`（旧变量名，值已动态化）          | 用户个性命名文件夹（兼容旧配置）                  |
| `FLASH_SOURCE_SUFFIX` | (空)                            | 数据来源后缀 (`from_ssh1`, `from_ssh2`) |

安装后写入 `~/.bashrc` 的环境变量：

```bash
export MPI_HOME=/usr/local/mpich
export HDF5_HOME=/usr/local/hdf5
export HDF5_ROOT=/usr/local/hdf5
export HYPRE_HOME=/usr/local/hypre
export PATH=$MPI_HOME/bin:$HDF5_HOME/bin:$PATH
export LD_LIBRARY_PATH=$MPI_HOME/lib:$HDF5_HOME/lib:$HYPRE_HOME/lib:$LD_LIBRARY_PATH
```

---
## 三平台配置参考

### 1. 本地 WSL (Ubuntu-22.04)

| 项目             | 值                                          |
|---|---|
| **FLASH 安装路径** | `~/<用户名>/FLASH/FLASH4.8/`                  |
| **MPI**        | 从源码编译 → `/usr/local/mpich/`                |
| **HDF5**       | 从源码编译 → `/usr/local/hdf5/`                 |
| **HYPRE**      | 从源码编译 → `/usr/local/hypre/`                |
| **sudo**       | 可用                                         |
| **运行方式**       | `mpirun -np 1`                             |
| **输出后缀**       | (无) → `outputfiles/hdf5files/laserslab1d/` |

### 2. SSH1 — ParaCloud NC-E

| 项目           | 值                                                          |
|---|---|
| **SSH**      | `ssh.cn-zhongwei-1.paracloud.com:22`, 凭据: `flash_ssh`      |
| **MPI/HDF5** | `module load mpich/3.2-gcc9.3` + `module load hdf5/1.8.18` |
| **HYPRE**    | 用户空间 `~/<用户名>/FLASH/local/hypre/` (需 `readlink -f` 解析符号链接) |
| **运行方式**     | `mpirun -np 4` (或 sbatch)                                  |
| **输出后缀**     | `from_ssh1` → `outputfiles/hdf5filesfrom_ssh1/`            |

### 3. SSH2 — ParaCloud BSCC-T6

| 项目      | 值                                                         |
|---|---|
| **SSH** | `ssh.cn-zhongwei-1.paracloud.com:8443`, 凭据: `flash_ssh_2` |
| **状态**  | 端口 8443 当前不可达                                             |

---
## 已知问题与解决方案

### HYPRE_PATH 符号链接问题 (超算)

`~` 展开路径与符号链接路径不一致，编译时报错 `HYPREf.h: No such file or directory`。

**解决**：

```bash
REAL_HYPRE=$(readlink -f ~/<用户名>/FLASH/local/hypre)
sed -i "s|^HYPRE_PATH = .*|HYPRE_PATH = $REAL_HYPRE|" Makefile.h
```

### MPICH --allow-run-as-root (WSL)

MPICH 3.2 **不支持** `--allow-run-as-root`（这是 OpenMPI 的参数）。WSL 默认以 root 运行，直接省略此参数即可。

### Python 命令 (WSL)

FLASH 的 `setup` 脚本需要 `python`（不是 `python3`）。

**解决**：

```bash
sudo ln -sf $(which python3) /usr/local/bin/python
```

### FLASHBINARY ifeq 块

Makefile.h 模板包含 `ifeq ($(FLASHBINARY),true)` 块，可能引起编译错误。需要注释掉整个块。

### libgfortran 版本冲突 (超算)

提示 `libgfortran.so.3, needed by liblapack.so, may conflict with libgfortran.so.5` —— 仅为**警告**，不影响编译。

---
## 参考与致谢

- **FLASH 仿真软件**：FLASH（radiation-hydrodynamics code）由 University of Chicago / University of Rochester 的 **Flash Center for Computational Science**（<https://flash.rochester.edu>）开发维护。使用> FLASH 前必须在该网站接受 **FLASH License Agreement**；本包对 FLASH Center 协议的合规声明见 `LICENSE`、`NOTICE` 与 `docs/FLASH_CENTER_COMPLIANCE.md`。
- **flash-sim（flash 仿真辅助 Python 包）致谢与商用**：使用本包产生的任何出版物，请感谢**绵阳市的 PhySimX 团队**开发了该仿真辅助 Python 包；flash-sim 的 Python 代码以 Apache 2.0 许可，其商用须遵守所有适用许可（含 FLASH 仿真引擎的 FLASH License Agreement §5），商用场景下的授权与责任以届时适用的许可及书面约定为准。建议致谢文案：*"We acknowledge the PhySimX team (Mianyang, China) for developing the flash-sim auxiliary Python package used in this work."* 完整条款见 `LICENSE`、`NOTICE` 与 `docs/FLASH_CENTER_COMPLIANCE.md`。
- **安装、依赖配置与初次使用建议**：本指南中关于 FLASH 的安装流程（gcc/gfortran 版本选择、mpich / hdf5 / hypre 的源码编译安装与环境变量配置）、`./setup` + `make` 编译流程、`flash.par` 与 `mpirun -np N ./flash4 -par_file xxx.par` 的运行方式、按算例分目录管理 `-objdir` 等**具体操作，参考了知乎专栏文章《FLASH个人总结（4）——FLASH的安装、依赖配置以及初次使用建议》**（<https://zhuanlan.zhihu.com/p/17167173342>）。

  **衷心感谢该文作者**的详细总结与无私分享，本指南中的安装脚本与初次使用流程从中获益良多（本仓库实际使用 FLASH 4.8，安装与使用思路与该文一致）。

---
## 后续步骤

完成 Hello FLASH 后，可以探索完整工作流：

```
scripts/
└── run_global_tests.py  ← 全局测试

flash/scenarios/             ← 即插即用场景系统
└──  center_evolution/  ← CH 中心演化

input_gen/             ← 参数文件生成 (par_editor, par_calculator)
flash_run/             ← 编译和运行管理
output_processors/     ← HDF5 输出分析和自适应可视化
```

详见 `docs/README.md`。

---

