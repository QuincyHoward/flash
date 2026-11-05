# flash_run — FLASH 仿真运行管理模块

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：改动本目录下 .py 后必须同步本文模块表

管理 FLASH 仿真在**四种执行目标**上的运行：本机（local）、本机 WSL（wsl）、超算远程（hpc-remote）、超算就地（hpc-insitu）。场景层只声明物理与策略，"在哪跑、怎么跑"由本模块统一裁决。

子包文档：[env/README.md](env/README.md) · [remote/README.md](remote/README.md) · [modes/README.md](modes/README.md)。超算终端常用命令见 [`deploy/hpc_deploy/超算终端常用指令.md`](../../deploy/hpc_deploy/超算终端常用指令.md)。

---

## 1. 分层铁律（机器可校验）

```
scenarios/  →  flash_run/  →  flash/_core/        （禁止反向依赖）
```

- 场景**不得**内联 SSH/SLURM/wsl 启动逻辑；一切经 `execution.py` 契约下发；
- `flash_run` 不 import `scenarios`（`R-LAYER-*` 护栏，基线只降不升，见根 README「分层护栏」）。

## 2. 模块清单

| 文件 | 行数 | 职责 | 关键 API |
|---|---|---|---|
| `__init__.py` | 50 | PEP 562 惰性导出（import 不拉起 paramiko） | `__getattr__` |
| `execution.py` | 472 | **唯一执行契约**：目标解析 + 策略校验 + 转调执行体 | `run_scene()` / `normalize_target()` / `SceneSpec` / `ExecutionPolicy` / `EXEC_TARGETS` |
| `hpc.py` | 176 | 超算技能统一 CLI（本地驱动/登录节点两侧可调） | `python -m flash.flash_run.hpc …` |
| `modes/runner.py` | 1051 | wsl/hpc-remote 执行体（自 scenarios 迁入，唯一归属） | `run_wsl()` / `WslSpec` / `allocate_run_id()` / `resolve_venv_python()` / `discover_flash_home()` |
| `modes/hpc_insitu.py` | 237 | hpc-insitu 执行体（就地 sbatch，**绝不 SSH 自连**） | `run_insitu()` |
| `remote/session.py` | 719 | **全仓唯一 SSH**（动态路由 + paramiko/CLI 双后端） | `RemoteSession`（run/upload/download/exists/listdir/mkdir_p） |
| `remote/executors.py` | 288 | 统一命令面（local/wsl/ssh/hpc 四 target 同构） | `make_executor` / `LocalExecutor` / `WslExecutor` / `SSHExecutor` |
| `remote/slurm_control.py` | 322 | SLURM 操作唯一下沉点（场景层禁内联 squeue） | `submit()` / `job_state()` / `wait_for_job()` / `latest_job_by_name()` |
| `remote/job_layout.py` | 427 | 超算作业**目录拓扑**（scratch/shared 分离）+ 资源规格 | `JobLayout` / `ResourceSpec` / `scratch_probe_script()` |
| `remote/job_scripts.py` | 271 | 作业体渲染（stage → build → run → archive） | `BuildSpec` / `RunSpec` / `render_job_body()` |
| `remote/job_submit.py` | 224 | **通用提交服务**（渲染 → 落盘 → sbatch），不认识任何场景 | `JobRequest` / `render_job()` / `submit_job()` |
| `remote/fetch_policy.py` | 139 | 产物回传选择**唯一入口**（chk-only 默认） | `select_fetch_files()` / `classify_names()` |
| `remote/artifacts.py` | 79 | `fetch_policy` 的唯一执行点 | `fetch_artifacts()` |
| `remote/route_tester.py` | 485 | SSH 多路由延迟实测择优（缓存 `~/.physimx/route_cache/`） | `RouteTester` / `test_and_select_best_route()` |
| `remote/remote_deploy.py` | 811 | 遗留高层部署器（**兼容壳**，新代码用 `RemoteSession`） | `FlashRemoteDeploy` |
| `remote/remote_workflow.py` / `remote_check.py` / `ssh_check.py` | 143/71/108 | 临时调试脚本（连接→检查→分析链） | CLI |
| `env/devices.py` | 276 | 超算装置参数唯一事实源（分区/模块/库路径） | `device_default()` / `credential_name()` |
| `env/resource_config.py` | 666 | 维度感知资源配置（laptop/desktop/hpc 三档，不含场景名） | `get_resource_config()` / `classify_device()` |
| `env/env_manager.py` | 536 | 环境配置管理（单例） | `FlashEnvManager` / `FlashEnvironment` / `get_env_manager()` |
| `env/venv_paths.py` | 166 | venv 路径**单一事实源**（纯 stdlib） | `repo_root()` / `venv_python()` / `require_venv_python()` |

## 3. 四种执行目标与平台自适应

`EXEC_TARGETS = ("local", "wsl", "hpc-remote", "hpc-insitu")`，别名归一：`hpc`/`remote`/`ssh`/`slurm`/`supercomputer` → `hpc-remote`；`insitu` → `hpc-insitu`。

| 目标 | 含义 | 典型驱动进程所在 |
|---|---|---|
| `local` | Linux 宿主（含 WSL 内）直接 `bash run_flash.sh` | WSL / Linux |
| `wsl` | Windows 经 `wsl.exe` 中转执行（WSL 内运行时自动等价 local） | Windows |
| `hpc-remote` | 本机 → SSH(RemoteSession) → 超算：上传→sbatch→sacct 轮询→远程分析→回传 | Windows / WSL |
| `hpc-insitu` | 驱动脚本**已在超算登录节点**：就地 sbatch+收集，禁 SSH 自连 | 超算登录节点 |

`auto`（默认）判定顺序——唯一实现 `execution.run_scene()`（auto 判定唯一实现）：
1. `--mode` 显式参数 → 2. 环境变量 `FLASH_RUN_MODE` → 3. 场景 `policy.preferred` → 4. 本机 slurm 健康 → `hpc-insitu` → 5. 非 Windows → `local` → 6. Windows 有 WSL → `wsl` → 7. 报错（**绝不静默降级**）。

场景可用 `ExecutionPolicy` 硬性约束：`allowed`（如 SNB 族仅允许两个 hpc 目标）、`nproc`（`exact`/`at_most`，执行层强制）、`forbid_reason`。策略校验失败即 `ok=False`，**绝不吞错返回假成功**。

## 4. 用户名与路径规范（文档与脚本同律）

**禁止在代码/文档/脚本里硬编码用户名。** 统一经 `get_sim_user_dir()`（`modes/runner.py`）解析：`环境变量 FLASH_SIM_USER_DIR > 凭据用户名（~/.physimx）> 默认 "hello"`。文档示例一律写 `<user>` 占位；FLASH 安装根可经 `discover_flash_home()` 自动发现（判据 = 同时存在 `setup` 与 `source/Simulation/SimulationMain`）；超算账号由 `~/.physimx/flash/hpc_accounts.json` 决定（权威声明见 [`../_core/credentials/README.md`](../_core/credentials/README.md) §4）。

## 5. 快速开始

### 5.1 场景统一入口（推荐）

```bash
# 平台自适应（推荐）：--mode 缺省 auto   ★ CLI 现居 core/entry/cli.py
python -m flash.scenarios.core.entry.cli list
python -m flash.scenarios.core.entry.cli run <场景>                    # auto
python -m flash.scenarios.core.entry.cli run <场景> --mode wsl --tmax 2e-10
python -m flash.scenarios.core.entry.cli explain <场景>                 # 只打印目标判定轨迹

# 提交超算（作业内 stage → 编译 → 运行 → 归档）
python -m flash.scenarios.core.entry.cli submit <场景> [--run-id 000002] [--ntasks 16]
python -m flash.scenarios.core.entry.cli submit <场景> --dry-run         # 只渲染作业脚本
```

### 5.2 超算技能 CLI

```bash
python -m flash.flash_run.hpc status    [--job ID]      # squeue (+sacct)
python -m flash.flash_run.hpc submit    --par x.par --nprocs 131 --account flash_ssh
python -m flash.flash_run.hpc cancel    --job ID
python -m flash.flash_run.hpc wait      --job ID [--timeout 3600]
python -m flash.flash_run.hpc download  --remote <dir> --local <dir> [--pattern "*.h5"]
python -m flash.flash_run.hpc route-test                 # 多路由实测择优
python -m flash.flash_run.hpc nodes                      # sinfo 分区速览
```

约定：远端操作**串行**（超算 SSH 限并发，并行提交会全部卡在路由选择）；提交前必查 `squeue`（父进程网络死亡 ≠ 远端作业结束）。

### 5.3 Python API

```python
from flash.flash_run.execution import ExecOptions, run_scene, SceneSpec

scene = SceneSpec(name="my_scene", objdir="<user>/MyObjDir",
                  basenm="mybase_", policy=DEFAULT_POLICY)
result = run_scene(scene, ExecOptions(mode="auto", tmax=1.188e-9))
print(result.ok, result.target, result.run_dir)
```

```python
# 装置默认值（**与场景无关**）：SLURM 计费账户 / venv / 装置档位
from flash.flash_run.env.devices import device_default, credential_name
ACCOUNT   = device_default("account")     # → nc-e（★ SLURM 计费账户）
VENV      = device_default("insitu_venv") # → .venv-hpc-nce
CRED      = credential_name()             # → flash_ssh（★ SSH 凭据名，选路由用）

# 场景专属默认值（**场景层**）：核数等由网格决定的量
from flash.scenarios.core.scene_reg.device_defaults import get_scene_nprocs
NPROCS  = get_scene_nprocs("SNBOneCH_ml")  # → 131
```

★ **`account` 与凭据名必须分开**（超算实测 2026-10-26）：`#SBATCH --account=flash_ssh` 会被拒（"Invalid account or account/partition combination specified"）——凭据名只用于选 SSH 路由，计费账户取 `sacct -X --format=Account`（`nc-e`）。

★ **边界**：`flash_run` 只提供**通用机制**。任何"某场景族"的常量都在场景层：

| 场景层内容 | 归属模块 |
|---|---|
| 场景族执行策略（仅超算 / 核数即网格） | `flash.scenarios.core.scene_reg.policies` |
| 场景专属核数默认值 | `flash.scenarios.core.scene_reg.device_defaults` |
| 场景超算提交声明（输入目录 / 单元名 / setup 参数） | `flash.scenarios.core.hpc.hpc_job` |
| 通用超算提交实现（渲染 → 落盘 → sbatch） | `flash.flash_run.remote.job_submit` |

护栏 `R-LAYER-03` 机械校验：执行层出现场景名即 CI 失败。

## 6. 标准运行流程（hpc-remote 全链路）

```
① 连接与路由实测（RemoteSession 动态择优，paramiko/CLI 双后端）
② 上传 flash_input/（SFTP；remote_dir 必须是绝对路径，见 §8.3）
③ sed 归一行尾 →（按策略可选）禁 module purge → 注入 Intel MPI 库路径
④ sbatch submit_flash.sh（超时 ≥180s：module load 本身 40~60s；
   超时后回查队列，提交类操作超时 ≠ 未提交）
⑤ sacct 轮询（15s 间隔，max 1h；FAILED/CANCELLED/TIMEOUT/NODE_FAIL 即终止）
⑥ 远端分析（hpc_analyze_*.py；python 三级回退：FLASH_HPC_PYTHON →
   repo/.venv-hpc-nce → module python → 系统 python3）
⑦ 回传：chk-only（fetch_policy，plt 默认不回传；批量对比用
   FLASH_FETCH_LIMIT=0 + FLASH_LS_LIMIT 放大远端 ls 上限）
⑧ 本地 output_pro 分析出图
```

断点续跑：`hpc_task.json` 记录 job_id/remote_dir/output，网络中断后可按凭据 + job_id 恢复，不重复提交。

## 7. 工程铁律（全部来自实战事故，违反即静默失败）

### 7.1 wsl.exe 命令串拆分（假成功级）
本机 `wsl bash -c "..."` 会把命令串在**顶层 `;`/`&&`/`||`** 处拆成多次独立执行（`false; echo $?`→0；`X=5; echo $X`→空）⇒ 复合命令、env 前缀、行内哨兵**全不可信**。规则：逻辑收进**脚本文件**（`flash_input/run_flash_wsl.sh`，**必须 LF 行尾**——Windows `write_text` 的 CRLF 会让 bash 解析崩），wsl 侧只发**单条简单命令**；退出码以脚本内哨兵 `FLASH_EXIT_CODE=` 为准。

### 7.2 WSL 运行目录必须落原生 ext4
FLASH 的 HDF5 MPI-IO 写 `/mnt/e`（drvfs）间歇 `ADIOI_GEN_READCONTIG: No data available` → SIGABRT 134（短跑偶然通过、全长跑必崩）。`FLASH_RUN_WORKDIR` 用 `/root/...` 类原生路径，产物再普通 cp 回 `/mnt/e`（非 MPI-IO，安全）。

### 7.3 paramiko SFTP 两坑
`~` **不展开**（文件落进主目录下字面 `~` 垃圾目录）；**尾斜杠**使 `sftp.put` 报 `OSError: Failure`。⇒ `remote_dir` 先 `printf '%s' "$HOME"` 解析成绝对路径；`_paramiko_put` 已做路径归一。

### 7.4 超算运行已预置二进制走 module 路径
计算节点 ambient 环境**没有** `libhdf5.so.10`——submit 脚本的 `module purge + load mpich/3.2-gcc9.3 + hdf5/1.8.18` 必须生效（mpich 的 soname 无 `.12` 后缀，不冲突二进制链接的 Intel `libmpi.so.12`）。`FLASH_NO_MODULE_PURGE=1` 只适用于 objdir **需重新编译**的场景。Intel MPI：`libmpifort.so.12` 在 `mpi/latest/lib/`，`MPII_F_TRUE` 靠 `mpi/latest/lib/release/libmpi.so.12` 提供——注入路径少写一层即 `undefined symbol` → SIGSEGV。

### 7.5 提交超时 ≠ 未提交
`sbatch` 前的 `module load` 要 40~60s；超时后必须回查队列（`slurm_control.latest_job_by_name`）再判定，否则会把已提交当失败而重复提交。

### 7.6 chk-only 回传与产物完整性
plt 默认不回传（`fetch_policy`）；批量矩阵对比需 `FLASH_FETCH_LIMIT=0`。成功判据必须是「rc==0 **且** 末帧时间 ≥ 98% tmax」——崩溃后的部分产物（如 57/342 chk）曾被打包成"成功"。

### 7.7 insitu 收集三坑
`select_fetch_files(basenm="")` 的 prefix 过滤只放行 `wsl_run_`，会把全部 chk 滤掉——basenm 必须从 .par 解析（如 `lasslab_`）；`ls outputfiles_* | head -1` 取**最旧**目录（flash_input 多轮复用）⇒ `sort | tail -1`；分析脚本不在 flash_input/（insitu 无上传步）⇒ 先拷入再跑。

## 8. 配置存储与依赖

| 内容 | 位置 |
|---|---|
| 环境配置 | `~/.physimx/flash_envs/environments.json` |
| 资源配置 | `~/.physimx/flash_resource/resource_config.json` |
| 路由缓存 | `~/.physimx/route_cache/best_routes.json` |
| 超算账户 | `~/.physimx/flash/hpc_accounts.json` + `credentials.enc`（Agent 只读） |

依赖：`paramiko`（SSH/SFTP，惰性导入）、`flash._core.credentials`（密码管理）、`h5py`/`numpy`/`matplotlib`（按需）。

## 9. 测试入口

分层护栏见 `test/test_arch_guards.py`（R-LAYER-*）；全链路验证走场景 `hpc-remote` 冒烟（见根 README §测试）。

## 10. 已知边界（挂账）

- 声明式 `build_inputs` 路径暂只接 `local`/`wsl`；hpc-* 请提供 `SceneSpec.runner`（B7 收编中）；
- `is_hpc_login_node()` 与 `probe_insitu` 仍是两份实现，待合一；
- `remote_deploy.FlashRemoteDeploy` 为兼容壳，不推荐新代码使用。

## 11. 导航

上级：[../../README.md](../../README.md)（仓库根） · 子包：[env/](env/README.md) / [remote/](remote/README.md) / [modes/](modes/README.md) · 下游消费：[../scenarios/README.md](../scenarios/README.md)
