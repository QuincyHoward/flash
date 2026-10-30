# flash_run — FLASH 仿真运行管理模块

> **本文件是 `flash/flash_run/` 的唯一入口文档**（2026-10-24 合并重写：
> 原 `README.md` + `PROCESS.md` 合一，旧文内 `physimx_sim.*` 路径、
> 已迁移实现、硬编码用户名一并更正）。子包级 API 见
> [`env/README.md`](env/README.md) 与 [`remote/README.md`](remote/README.md)，
> 超算终端常用命令见 [`deploy/hpc_deploy/超算终端常用指令.md`](../../deploy/hpc_deploy/超算终端常用指令.md)，
> 超算部署与测试记录见 [`deploy/hpc_deploy/flash-sim的超算部署与测试.md`](../../deploy/hpc_deploy/flash-sim的超算部署与测试.md)。

管理 FLASH 仿真在**四种执行目标**上的运行：本机（local）、本机 WSL（wsl）、
超算远程（hpc-remote）、超算就地（hpc-insitu）。场景层只声明物理与策略，
"在哪跑、怎么跑"由本模块统一裁决。

---

## 1. 分层铁律（机器可校验）

```
scenarios/  →  flash_run/  →  flash/_core/        （禁止反向依赖）
```

- 场景**不得**内联 SSH/SLURM/wsl 启动逻辑；一切经 `execution.py` 契约下发；
- `flash_run` 不 import `scenarios`（`R-LAYER-*` 护栏，基线只降不升，
  见根 README「分层护栏」）。

## 2. 模块地图

| 子模块 | 职责 | 关键 API |
|---|---|---|
| `execution.py` | **唯一执行契约**：目标解析 + 策略校验 + 转调执行体 | `resolve_target()` / `run_scene()` / `SceneSpec` / `ExecutionPolicy` / `EXEC_TARGETS` |
| `modes/runner.py` | wsl/hpc-remote 执行体（自 `scenarios/runner.py` 迁入，唯一归属） | `run_wsl()` / `WslSpec` / `allocate_run_id()` / `resolve_venv_python()` / `discover_flash_home()` |
| `modes/hpc_insitu.py` | hpc-insitu 执行体（就地 sbatch，**绝不 SSH 自连**） | `run_insitu()` |
| `remote/session.py` | **全仓唯一 SSH**（动态路由 + paramiko/CLI 双后端） | `RemoteSession`（run/upload/download/exists/listdir/mkdir_p） |
| `remote/executors.py` | 统一命令面（本地/WSL/SSH 同构） | `LocalExecutor` / `WslExecutor` / `SSHExecutor` |
| `remote/slurm_control.py` | SLURM 操作唯一下沉点（场景层禁内联 squeue） | `submit()` / `job_state()` / `wait_for_job()` / `latest_job_by_name()` / `sbatch_available()` |
| `remote/job_layout.py` | 超算作业**目录拓扑**（scratch/shared 分离）+ 资源规格 | `JobLayout` / `ResourceSpec` / `scratch_probe_script()` / `compile_parallel_jobs()` |
| `remote/job_scripts.py` | 作业体渲染（stage → build → run → archive） | `BuildSpec` / `RunSpec` / `render_job_body()` |
| `remote/job_submit.py` | **通用提交服务**（渲染 → 落盘 → sbatch），不认识任何场景 | `JobRequest` / `render_job()` / `submit_job()` |
| `remote/fetch_policy.py` | 产物回传选择**唯一入口**（chk-only 默认） | `select_fetch_files()` / `classify_names()` |
| `remote/artifacts.py` | `fetch_policy` 的唯一执行点 | `fetch_artifacts()` |
| `remote/route_tester.py` | SSH 多路由延迟实测择优 | `RouteTester` / `test_and_select_best_route()` |
| `remote/remote_deploy.py` | 遗留高层部署器（兼容壳，新代码用 `RemoteSession`） | `FlashRemoteDeploy` |
| `env/env_manager.py` | 环境配置管理（单例） | `FlashEnvManager` / `FlashEnvironment` / `get_env_manager()` |
| `env/resource_config.py` | 维度感知资源配置（**通用算法**，不含场景名） | `get_resource_config()` / `classify_device()` |
| `env/venv_paths.py` | venv 路径**单一事实源**（纯 stdlib） | `repo_root()` / `venv_dir()` / `venv_python()` / `require_venv_python()` |
| `hpc.py` | 超算技能统一 CLI（本地驱动/登录节点两侧可调） | `python -m flash.flash_run.hpc …` |

## 3. 四种执行目标与平台自适应

`EXEC_TARGETS = ("local", "wsl", "hpc-remote", "hpc-insitu")`，别名归一：
`hpc`/`remote`/`ssh`/`slurm`/`supercomputer` → `hpc-remote`；`insitu` → `hpc-insitu`。

| 目标 | 含义 | 典型驱动进程所在 |
|---|---|---|
| `local` | Linux 宿主（含 WSL 内）直接 `bash run_flash.sh` | WSL / Linux |
| `wsl` | Windows 经 `wsl.exe` 中转执行（WSL 内运行时自动等价 local） | Windows |
| `hpc-remote` | 本机 → SSH(RemoteSession) → 超算：上传→sbatch→sacct 轮询→远程分析→回传 | Windows / WSL |
| `hpc-insitu` | 驱动脚本**已在超算登录节点**：就地 sbatch+收集，禁 SSH 自连 | 超算登录节点 |

`auto`（默认）判定顺序——唯一实现 `execution.resolve_target()`：

1. `--mode` 显式参数 → 2. 环境变量 `FLASH_RUN_MODE` → 3. 场景 `policy.preferred`
→ 4. 本机 slurm 健康（sbatch+sacct+sinfo 且控制器可达）→ `hpc-insitu`
→ 5. 非 Windows → `local` → 6. Windows 有 WSL → `wsl` → 7. 报错（绝不静默降级）。

场景可用 `ExecutionPolicy` 硬性约束：`allowed`（如 SNB 族仅允许两个 hpc 目标）、
`nproc`（`exact`/`at_most`，执行层强制）、`forbid_reason`。策略校验失败即
`ok=False`，**绝不吞错返回假成功**。

## 4. 用户名与路径规范（文档与脚本同律）

**禁止在代码/文档/脚本里硬编码用户名。** 统一经 `get_sim_user_dir()`
（`modes/runner.py`）解析，优先级：

```
环境变量 FLASH_SIM_USER_DIR  >  凭据用户名（~/.physimx）  >  默认 "hello"
```

- 本机当前凭据用户名为 `QC`，但**默认值恒为 `hello`**——干净克隆/离线机无凭据
  时必须有确定行为；
- 文档与示例一律写 `$HOME/<user>/FLASH/FLASH4.8` 或 `~/<user>/...`，
  用 `<user>` 占位；FLASH 安装根另可经 `discover_flash_home()` 自动发现
  （扫描 `$HOME`，判据 = 同时存在 `setup` 与 `source/Simulation/SimulationMain`）；
- 超算账号同样不落文档：由 `~/.physimx/flash/hpc_accounts.json` 与凭据名
  （默认 `flash_ssh`）决定，路由表常量名（`ROUTES_*`）除外。

## 5. 快速开始

### 5.1 场景统一入口（推荐）

```bash
# 平台自适应（推荐）：--mode 缺省 auto
python -m flash.scenarios.core.cli list
python -m flash.scenarios.core.cli run <场景>                    # auto
python -m flash.scenarios.core.cli run <场景> --mode wsl --tmax 2e-10
python -m flash.scenarios.core.cli explain <场景>                 # 只打印目标判定轨迹

# 提交超算（作业内 stage → 编译 → 运行 → 归档）
python -m flash.scenarios.core.cli submit <场景> [--run-id 000002] [--ntasks 16]
python -m flash.scenarios.core.cli submit <场景> --dry-run         # 只渲染作业脚本
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

约定：远端操作**串行**（超算 SSH 限并发，并行提交会全部卡在路由选择）；
提交前必查 `squeue`（父进程网络死亡 ≠ 远端作业结束）。

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
from flash.scenarios.core.device_defaults import get_scene_nprocs
NPROCS  = get_scene_nprocs("SNBOneCH_ml")  # → 131
```

★ **`account` 与凭据名必须分开**（超算实测 2026-10-26）：
`#SBATCH --account=flash_ssh` 会被拒（"Invalid account or
account/partition combination specified"）——
凭据名只用于选 SSH 路由，计费账户取 `sacct -X --format=Account`（`nc-e`）。

★ **边界**：`flash_run` 只提供**通用机制**（策略 / 目标判定 / 目录规划 /
作业体渲染 / 提交 / 轮询 / 回收）。任何"某场景族"的常量都在场景层：

| 场景层内容 | 归属模块 |
|---|---|
| 场景族执行策略（仅超算 / 核数即网格） | `flash.scenarios.core.policies` |
| 场景专属核数默认值 | `flash.scenarios.core.device_defaults` |
| 场景超算提交声明（输入目录 / 单元名 / setup 参数） | `flash.scenarios.core.hpc_job` |
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

断点续跑：`hpc_task.json` 记录 job_id/remote_dir/output，网络中断后可按
凭据 + job_id 恢复，不重复提交。

## 7. 子模块要点

### env/ — 环境与资源配置
- `FlashEnvManager`（单例）：多环境（local_wsl / 各超算）注册、切换、
  从凭据自动创建；`FlashEnvironment.build_run_command()` 生成运行命令；
- `FlashResourceConfig`：1D/2D/3D × 本地/超算 的 CPU 占比与并行数；
- 装置默认值（nprocs/account/分区）下沉 `resource_config.py`，按场景名
  最长前缀匹配——换装置只改该文件，不改场景源码；
- `venv_paths.py`：`repo_root()` 向上探测 pyproject+start_flash；
  `venv_dir(root, kind)`，**绝不回落 `sys.executable`**。

### remote/ — 远程层
- `RemoteSession`：唯一 SSH 入口；`run/upload/download/exists/listdir/mkdir_p`；
  路由每次连接实测择优并缓存；paramiko（Windows 默认）/CLI 双后端
  （`FLASH_SSH_BACKEND` 可强制）；
- `executors.py`：`LocalExecutor`/`WslExecutor`/`SSHExecutor` 统一
  `run/listdir/copy_from/put/exists` 命令面（artifacts/insitu 复用）；
- `slurm_control.py`：sbatch/sacct/squeue 唯一封装；
- `fetch_policy.py`：回传选择唯一入口——`basenm` 前缀归属 + chk/plt/fixed
  三分类，`frames` 等间隔抽帧（首尾必取）；
- `remote_deploy.py`（`FlashRemoteDeploy`）：遗留兼容壳，保留 8 个方法供
  旧工具脚本；新代码用 `RemoteSession` + `execution.run_scene`。

## 8. 工程铁律（全部来自实战事故，违反即静默失败）

### 8.1 wsl.exe 命令串拆分（假成功级）
本机 `wsl bash -c "..."` 会把命令串在**顶层 `;`/`&&`/`||`** 处拆成多次独立
执行（`false; echo $?`→0；`X=5; echo $X`→空；`A && B || C` 的 B/C 恒执行）
⇒ 复合命令、env 前缀、行内哨兵**全不可信**。规则：逻辑收进**脚本文件**
（`flash_input/run_flash_wsl.sh`，**必须 LF 行尾**——Windows `write_text`
的 CRLF 会让 bash 解析崩），wsl 侧只发**单条简单命令**；退出码以脚本内哨兵
`FLASH_EXIT_CODE=` 为准。

### 8.2 WSL 运行目录必须落原生 ext4
FLASH 的 HDF5 MPI-IO 写 `/mnt/e`（drvfs）间歇
`ADIOI_GEN_READCONTIG: No data available` → SIGABRT 134（短跑偶然通过、
全长跑必崩）。`FLASH_RUN_WORKDIR` 用 `/root/...` 类原生路径，产物再普通
cp 回 `/mnt/e`（非 MPI-IO，安全）。

### 8.3 paramiko SFTP 两坑
`~` **不展开**（文件落进主目录下字面 `~` 垃圾目录）；**尾斜杠**使
`sftp.put` 报 `OSError: Failure`。⇒ `remote_dir` 先 `printf '%s' "$HOME"`
解析成绝对路径；`_paramiko_put` 已做路径归一（`~` 经同一连接 exec 展开、
目录意图补 basename）。

### 8.4 超算运行已预置二进制走 module 路径
计算节点 ambient 环境**没有** `libhdf5.so.10`——submit 脚本的
`module purge + load mpich/3.2-gcc9.3 + hdf5/1.8.18` 必须生效（mpich 的
soname 无 `.12` 后缀，不冲突二进制链接的 Intel `libmpi.so.12`）。
`FLASH_NO_MODULE_PURGE=1` 只适用于 objdir **需重新编译**的场景
（保 oneAPI 链接栈）。Intel MPI：`libmpifort.so.12` 在
`mpi/latest/lib/`，`MPII_F_TRUE` 靠 `mpi/latest/lib/release/libmpi.so.12`
提供——注入路径少写一层即 `undefined symbol` → SIGSEGV。

### 8.5 提交超时 ≠ 未提交
`sbatch` 前的 `module load` 要 40~60s；超时后必须回查队列
（`slurm_control.latest_job_by_name`）再判定，否则会把已提交当失败而重复提交。

### 8.6 chk-only 回传与产物完整性
plt 默认不回传（`fetch_policy`）；批量矩阵对比需 `FLASH_FETCH_LIMIT=0`。
成功判据必须是「rc==0 **且** 末帧时间 ≥ 98% tmax」——崩溃后的部分产物
（如 57/342 chk）曾被打包成"成功"。

### 8.7 insitu 收集三坑
`select_fetch_files(basenm="")` 的 prefix 过滤只放行 `wsl_run_`，会把全部
chk 滤掉——basenm 必须从 .par 解析（如 `lasslab_`）；
`ls outputfiles_* | head -1` 取**最旧**目录（flash_input 多轮复用）⇒
`sort | tail -1`；分析脚本不在 flash_input/（insitu 无上传步）⇒ 先拷入再跑。

## 9. 配置存储与依赖

| 内容 | 位置 |
|---|---|
| 环境配置 | `~/.physimx/flash_envs/environments.json` |
| 资源配置 | `~/.physimx/flash_resource/resource_config.json` |
| 路由缓存 | `~/.physimx/route_cache/best_routes.json` |
| 超算账户 | `~/.physimx/flash/hpc_accounts.json` + `credentials.enc`（Agent 只读） |

依赖：`paramiko`（SSH/SFTP，惰性导入——`import flash.flash_run` 不拉起）、
`flash._core.credentials`（密码管理）、`h5py`/`numpy`/`matplotlib`（分析与绘图，
按需）。

## 10. 命令行速查

```bash
python -m flash.flash_run.hpc route-test                 # 路由实测择优
python -m flash.flash_run.remote.route_tester            # 同上（模块直跑）
python -m flash.flash_run.env.resource_config            # 查看资源配置
python -m flash.scenarios.core.cli list                       # 场景清单（统一入口）
```

## 11. 已知边界（挂账）

- 声明式 `build_inputs` 路径暂只接 `local`/`wsl`；hpc-* 请提供
  `SceneSpec.runner`（存量脚本适配），B7 收编中；
- `is_hpc_login_node()` 与 `probe_insitu` 仍是两份实现，待合一；
- `remote_deploy.FlashRemoteDeploy` 为兼容壳，不推荐新代码使用。
