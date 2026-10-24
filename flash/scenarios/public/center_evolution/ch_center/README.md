# ch_center — CH 靶中心演化场景（LaserSlab1D Custom v1.1）

一维对称域 LaserSlab 算例：**CH 靶居中、两侧近真空 He 腔、两束 351 nm 激光
相向入射**，观测中心等离子体状态（密度 / 电子数密度 / 电子温度）的时域演化。
本场景只关心**物理搭建**；执行方式（本机 / WSL / 超算 / 就地）由运行模式
参数控制，默认 `auto` 按平台自适应。

- 场景脚本：`laserslab1d_local_custom.py`（`main(mode=..., tmax=...)` 唯一入口）
- 输入生成：`gen_flash_inputs.py`（经 `flash.input_gen`，`flash_input/` 不入库）
- 多模式测试：`modes_test/`（五执行路径同算例对比，见其 README）
- 执行契约：`flash/flash_run/execution.py`（目标判定唯一实现）

---

## 1. 物理设置

| 项 | 值 | 说明 |
|---|---|---|
| 域 | `[-100, +100] µm`（对称） | 1D，两侧 outflow |
| CH 靶 | `[-30, +30] µm`，ρ = 1.0 g/cm³ | `ch_mix`：Z06_0.50-Z01_0.50（A=6.5, Z=3.5），T = 290.11 K |
| 两侧腔 | 近真空 He，ρ = 1e-6 g/cm³ | `helium_hires`：Z02_1.00（A=4.0026, Z=2.0） |
| 激光 | 2 束 × 5e14 W/cm²，λ = 0.351 µm | 相向入射；平顶 1.0 ns + 40 ps 升降沿；透镜位于 ±1.0 cm（域外） |
| 网格 | nblockx=4，lrefine_max=4（nxb=16） | 自适应细化 |
| 方程 | MGD 辐射 Hydro（6 能群）+ 三热流 + 激光 | `+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=6` |
| EOS/不透明度 | 自研 IONMIX 表（随包分发） | `Z06_0.50-Z01_0.50-*.cn4`（CH）+ `Z02_1.00-*.cn4`（He），**6 群不可与他群数表混用** |
| tmax | 1.188e-9 s（脉冲总长 1.08 ns × 1.1） | dtmax = 1e-12 s |
| 输出 | chk 每 20 步、plt 每 5 步 | chk-only 回传策略（plt 默认不回传） |
| 并行 | nprocs = 4 | 本地/超算作业一致 |

所有物理参数集中在脚本顶部 `config_constants` 字典，改参数只改这里。

## 2. 目录结构

```
ch_center/
├── README.md                  本文
├── laserslab1d_local_custom.py  场景主脚本（main / 五种模式分支 / 输入生成）
├── gen_flash_inputs.py         必须文件生成器 CLI（--check/--force/--status）
├── hpc_analyze_ch_center.py    超算端自包含分析（h5py+numpy+matplotlib）
├── flash_input/                生成的 FLASH 输入（.gitignore；可随时重建）
│   ├── laserslab_chcenter.par / Config / Makefile / Simulation_*.F90
│   ├── run_flash.sh / submit_flash.sh / run_flash_wsl.sh（运行时生成）
│   └── *.cn4（EOS 表，由生成器从 input_gen/gen_eos_op/eos_op_data 复制）
├── flash_output/plots/         场景本地/远端分析 PNG
└── modes_test/                 多执行模式测试框架（驱动/分析/报告/产物）
```

## 3. 快速开始

### 3.1 统一入口（推荐）

```bash
# 平台自适应：Windows→wsl，WSL/Linux→local，超算登录节点→hpc-insitu
python -m flash.scenarios.cli run ch_center

# 显式指定模式与终止时间
python -m flash.scenarios.cli run ch_center --mode wsl --tmax 2e-10
python -m flash.scenarios.cli run ch_center --mode hpc-remote
python -m flash.scenarios.cli explain ch_center        # 只打印目标判定轨迹
```

### 3.2 直跑场景脚本（等价，兼容保留）

```bash
python flash/scenarios/public/center_evolution/ch_center/laserslab1d_local_custom.py
```

> ⚠ 该脚本**没有 argparse**——`--mode` 会被忽略；模式只能由环境变量或脚本内
> `RUN_MODE` 常量指定。测试驱动 `modes_test/run_mode_test.py` 以 API 方式调用
> `main(mode=..., tmax=...)`，不受此限。

## 4. 运行模式与切换方式

四种执行目标（`auto` 判定表唯一实现：`flash_run/execution.py`）：

| 模式 | 驱动进程 | 流程 |
|---|---|---|
| `wsl` | Windows | wsl.exe → WSL 内 `run_flash.sh`（setup→编译→运行→收集→本地分析） |
| `local` | WSL/Linux | 不套 wsl.exe，直接 `bash run_flash.sh`（与 wsl 同一代码路径） |
| `hpc-remote` | Windows/WSL | SSH 上传 `flash_input/` → `sbatch` → sacct 轮询 → 远端分析 → 回传 chk+PNG |
| `hpc-insitu` | 超算登录节点 | 就地 sbatch+收集，**绝不 SSH 自连**；产物外置 `flash_sim_runs/ch_center/run_NNNNNN/` |

### 切换优先级（三者任一）

1. **API/CLI 参数**：`main(mode="hpc-remote")` 或 `--mode hpc-remote`（推荐，最可测）；
2. **环境变量**：`FLASH_RUN_MODE=wsl python laserslab1d_local_custom.py`；
3. **脚本常量**：`laserslab1d_local_custom.py` 顶部 `RUN_MODE = "auto"`。

缺省 `auto` = 平台自适应（Windows 有 WSL → `wsl`；非 Windows → `local`；
超算且 slurm 控制器可达 → `hpc-insitu`）。场景策略 `DEFAULT_POLICY` 允许全部
四种目标；SNB 族场景则只允许两个 hpc 目标（禁本地，原因见其场景文档）。

### 常用环境变量

| 变量 | 作用 |
|---|---|
| `FLASH_RUN_MODE` | 运行模式（等同 `--mode`） |
| `FLASH_RUN_WORKDIR` | 每轮独立运行 cwd（WSL 侧防历史 chk 污染；**必须落原生 ext4**，禁 `/mnt/*`） |
| `FLASH_COLLECT_DIR` | chk 收纳目录（批量矩阵跨模式对比用） |
| `FLASH_FETCH_LIMIT` / `FLASH_LS_LIMIT` | 回传帧数上限 / 远端 ls 上限（批量模式置 0 / 2000） |
| `FLASH_SIM_USER_DIR` | 覆盖用户名（默认取凭据，干净环境回落 `hello`；**勿硬编码**） |
| `FLASH_HPC_WORKDIR` | `temp`（默认，一次性目录）/ `runs`（包目录外置契约） |
| `FLASH_EXTRACTION_MODE` | 本地分析提取方案（`yt` / `h5py`） |

> ★ 不设 `FLASH_RUN_WORKDIR` / `FLASH_COLLECT_DIR` 时，场景会**自动分配**
> 每轮独立的工作目录（WSL ext4：`/root/flash_ch_center_work`）与收集目录
> （`flash_input/outputfiles/`），并在收集前清空旧产物 —— 否则短跑的
> 3 个 chk 会与上一轮长跑的数百个 chk 混成一份（静默污染）。

### 3.3 统一入口（推荐）

```bash
# 三个公开场景统一入口，缺省 --mode auto
python -m flash.scenarios.cli run ch_center --tmax 1e-13
python -m flash.scenarios.cli list
python -m flash.scenarios.cli explain ch_center     # 只打印判定轨迹
```

### 3.4 `tmax` 覆盖规则（极短验证）

`--tmax` 只改**终止时间**，脉冲/网格/EOS/激光逐字不变 ⇒ 仍是同一算例。
但它必须落到 par 文件才生效：

- **场景脚本路径**：`main(tmax=...)` 会核对 par 中的 tmax，不一致时**强制重建
  输入**（否则覆盖被静默忽略 —— 输入已就绪时旧实现直接跑旧 tmax）。
- **引擎路径**：`build_par(params)` 直接取 `params["tmax"]`。
- **dt 联动**：`dtmax ≤ tmax×1.05`、`dtinit ≤ tmax×0.1`（统一实现在
  `flash/scenarios/public/time_control.py`），否则 FLASH 会浪费步长跨越 tmax
  甚至第一步就结束。

## 5. 多执行模式测试（modes_test/）

同一算例在五种执行路径下的对比测试框架（2026-10-24 建成，五模式全绿）：

```bash
# Windows 一键（wsl-* 自动转投 WSL 执行）
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\run_mode_test.py --mode-key win-wsl  --tmax 1.188e-9
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\run_mode_test.py --mode-key wsl-hpc  --tmax 1.188e-9
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\run_mode_test.py --mode-key hpc-insitu --tmax 1.188e-9   # 超算登录节点

# 跨模式 dens/nele 对比（图 + CSV + 报告）
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\analyze_modes.py
```

| mode-key | 驱动平台 | 场景模式 |
|---|---|---|
| `win-wsl` | Windows | `wsl` |
| `wsl-wsl` | WSL | `wsl` |
| `win-hpc` | Windows | `hpc-remote` |
| `wsl-hpc` | WSL | `hpc-remote` |
| `hpc-insitu` | 超算登录节点 | `hpc-insitu` |

首轮结果（tmax=1.188 ns）：win-wsl 与 wsl-wsl **逐位一致**；三个超算路径
彼此一致、与 WSL 参考最大偏差 5.4e-3（编译器浮点差，集中在激波段）。
产物、用法与 12 条维护坑见 [`modes_test/README.md`](modes_test/README.md)。

## 6. 输入文件的生成与重建

`flash_input/` 不入库（`.gitignore`），任何克隆环境可一键重建：

```bash
python flash/scenarios/public/center_evolution/ch_center/gen_flash_inputs.py            # 缺失才生成（幂等）
python flash/scenarios/public/center_evolution/ch_center/gen_flash_inputs.py --force    # 强制全量重建
python flash/scenarios/public/center_evolution/ch_center/gen_flash_inputs.py --check    # 仅检查（退出码 0/1）
```

- ⚠ **`--tmax` 只在输入生成时生效**（写进 .par）：改终止时间必须
  `gen_flash_inputs.py --force` 重建，否则各模式会沿用旧 .par 的 tmax；
- 生成物含 7 项必须文件 + 关联检查（`gen_checker`：.par ↔ Config ↔ cn4 ↔
  F90 ↔ 脚本装配，15 条规则）；
- `run_flash.sh` 旧版（无 `FLASH_RUN_WORKDIR` 标记）会在运行时自动重建——
  这是防"历史 chk 污染"的强制项。

## 7. 输出与物理量约定

| 量 | 单位/算法 | 备注 |
|---|---|---|
| `dens` | g/cm³ | chk 原值 |
| `nele` | cm⁻³，`nele = ye × dens × N_A` | 派生量（N_A = 6.02214076e23） |
| `tele` | **chk 内为 K**，显示 eV 须 ÷11604.518 | 常见坑 |
| 中心分析区 | \|x\| ≤ 5 µm | `analysis_half_width_um` |
| 回传策略 | chk-only（`fetch_policy`） | plt 默认不回传；批量对比置 `FLASH_FETCH_LIMIT=0` |

物理合理性参考（tmax=1.188 ns）：中心密度 1.0 → 峰值 ~5 g/cm³（激波汇聚）
→ 末态 ~2.0 g/cm³；`nele` 末态 ~2.9e23 cm⁻³；`tele` 末态 ~86 eV。

## 8. 超算侧约定

- 账户/路由：凭据 `flash_ssh`（默认）+ `~/.physimx/flash/hpc_accounts.json`；
  文档与脚本**不出现账号名**，用户名解析见 `get_sim_user_dir()`
  （`FLASH_SIM_USER_DIR` > 凭据 > 默认 `hello`；当前机为 `QC`）；
- objdir：`<user>/LaserSlab_ChCenter`（按生成平台分化，二进制已预置则跳过编译）；
- 远端分析 python 三级回退：`FLASH_HPC_PYTHON` → `repo/.venv-hpc-nce` →
  `module python/3.9.6` → 系统 `python3`；
- 已知工程铁律（wsl.exe 命令串拆分、drvfs MPI-IO、SFTP `~`/尾斜杠、
  Intel MPI 库路径、sbatch 超时≠未提交等）汇总于
  [`modes_test/README.md` §6](modes_test/README.md) 与
  [`flash_run/README.md` §8](../../flash_run/README.md)。

## 9. 挂账

- `run_meta.json` 运行元数据契约未定；
- tracer 20 个脚本尚未迁 `SceneSpec`；
- SNB 执行体收编（B7）进行中——本场景的五模式执行体是事实参照。
