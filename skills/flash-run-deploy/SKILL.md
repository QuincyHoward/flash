---
name: flash-run-deploy
description: FLASH 三模式运行体系（wsl/hpc-remote/hpc-insitu）：模式矩阵与解析优先级、目录契约（flash_sim_runs 外置）、环境变量总表、slurm 作业控制、超算分析 python 回退链、三端一致性自检、MPII_F_TRUE 等运行期环境故障。触发词：三模式、wsl 运行、hpc 部署、超算提交、sbatch、slurm、FLASH_RUN_MODE、hpc-insitu、作业链、run_job_chain、MPII_F_TRUE、LD_LIBRARY_PATH。
---

> 最后核对：2026-11-06 · commit 72f6428

# FLASH 三模式运行与超算部署

权威定案文档：`docs/FLASH三模式运行体系.md`；执行知识库：`docs/flash_simulation_execution_knowledge.md`。
代码锚点：`flash/flash_run/`（env / modes / remote）、`scripts/02_hpc/`。

## 1. 模式矩阵

| 模式 | 规范名 | 驱动位置 | FLASH 执行位置 | 入口 |
|---|---|---|---|---|
| ① 本机 WSL | `wsl` | Windows python | WSL（FLASH 树在 WSL $HOME） | `FLASH_RUN_MODE=wsl`（默认） |
| ①' WSL 内直跑 | `wsl`（自动降级） | WSL python | WSL | 同上；`detect_native_linux()` 自动去掉 `wsl bash -c` 包装 |
| ② 超算 SSH 驱动 | `hpc-remote` | Windows python（凭据+RemoteSession） | 超算计算节点（sbatch） | `FLASH_RUN_MODE=hpc`（别名永续） |
| ③ 超算就地 | `hpc-insitu` | **超算登录节点**（.venv-hpc-nce） | 超算计算节点（sbatch） | `--mode hpc-insitu` |

**解析优先级**（`flash.scenarios.core.runner.resolve_run_mode`）：
`--mode` 显式 > 环境变量 `FLASH_RUN_MODE` > 场景模块常量 `RUN_MODE`。
★ 不做平台自动兜底——模式切换必须显式。

**别名（永续兼容）**：`local→wsl`；`hpc/remote/slurm/supercomputer→hpc-remote`；`insitu/in-situ/hpc-in-situ→hpc-insitu`。

## 2. 目录契约

```
Windows 本机                                超算
<repo>/                 代码+venv            ~/PhySimX/.../flash_sim/   代码+venv (git 干净)
  ├─ .venv-win / .venv-linux                 ├─ .venv-hpc-nce/     ★ 命名环境
  └─ (FLASH 树在 WSL $HOME)                  ├─ (FLASH 树在 ~/QC/FLASH{,SNB}/FLASH4.8)
<repo>/../flash_sim_runs/  ← 输出外置        ~/PhySimX/.../flash_sim_runs/   ← 输出外置
  └─ <scenario>/run_NNNNNN/                   └─ <scenario>/run_NNNNNN/
       input/ output/ plots/ logs/ state.json
```

- **输出外置契约**：flash_sim 包目录只放代码+venv，`git status` 永远干净；
  运行输出一律写兄弟目录 `flash_sim_runs/`（`FLASH_RUNS_DIR` 可覆盖）。
- ★ 约束：FLASH `setup/make` 一律在 FLASH 树 objdir 内进行；runs 目录只承载输入快照、sbatch 脚本、作业日志与回收结果。
- **场景资产**（License §3 不入 git 的 cn4 表 / Driver F90 / SNB 覆盖 F90）：
  hpc-remote 由单元包上传补齐；hpc-insitu 需先跑 `sync_snb_assets.py`（本机 → 超算部署树 flash_input/，幂等）。

## 3. 环境变量总表

| 变量 | 作用 | 默认 |
|---|---|---|
| `FLASH_RUN_MODE` | 运行模式（wsl / hpc / hpc-insitu） | 场景 RUN_MODE |
| `FLASH_VENV_DIR` | 项目 venv 显式路径 | .venv-win / .venv-linux / .venv-hpc-nce |
| `FLASH_RUNS_DIR` | 运行输出根目录 | `<包根>/../flash_sim_runs` |
| `FLASH_SIM_USER_DIR` | FLASH 安装前缀目录名（无凭据机器必设，如 QC） | 凭据用户名 → hello |
| `FLASH_HPC_WORKDIR` | hpc-remote 远程工作目录: `temp` / `runs` | temp |
| `FLASH_HPC_PKG_ROOT` | hpc-remote runs 模式的远端包根 | `$HOME/PhySimX/PhySimX/simulation/flash/flash_sim` |
| `FLASH_HPC_PYTHON` | 远端分析 python 显式路径 | 回退链见 §5 |

## 4. slurm 作业控制（`flash/flash_run/remote/slurm_control.py`）

hpc-remote 与 hpc-insitu **共用同一套作业控制**（executor 注入）：
- `LocalExecutor`（in-situ，纯 subprocess）/ `RemoteExecutor`（包装 RemoteSession）
- `SlurmJobSpec` + `render_sbatch` + `run_job_chain`（SNB build→run 双作业、laserslab run→分析 chain 统一表达；par 闸门 / skip-build 补解压为 gate 回调）
- `wait_for_job`：sacct 轮询 + 输出文件 marker 确认（COMPLETED 但 marker 未命中 → WARN 仍返回 True）

## 5. 超算分析 python 回退链

```
FLASH_HPC_PYTHON (env) → $HOME/.venv-hpc-nce/bin/python → module python/3.9.6 (旧路 WARN) → python3 → 本地分析
```

venv 路线自带 h5py 3.14 + yt 4.4.0，替代旧 module 路线。

## 6. 三端一致性自检

```bash
python -m flash.scenarios.core.runner --check-env
```

报告：平台判定 / venv / FLASH 树（含 SNB 树）/ runs_root 可写性 / slurm 可用性 / 凭据存在性 / 三模式各自 ✓✗ / git HEAD（对照超算 bundle 同步）。

## 7. 运行期环境故障：MPII_F_TRUE（已定案，勿重走弯路）

`libmpifort.so.12: undefined symbol: MPII_F_TRUE` 的真因是**环境变量层面的同名 soname 覆盖**，
不是 FLASH 树编译问题，也不是 oneAPI 安装错配：

| # | 真因 | 修法 |
|---|---|---|
| ① | 注入的 oneAPI 库路径写错（真实在 `mpi/latest/lib`） | 不再注入 oneAPI MPI 路径 |
| ② | 计算节点 `module load mpich/3.2-gcc9.3` 的 libmpifort 需要 GFORTRAN_9 符号；注入 gcc 8 的 libgfortran 只到 GFORTRAN_5 | 改用 `gcc/9.3.0-new/lib64`（循环取 9.3.0-new → 9.1.0） |
| ③ | oneAPI 与 mpich 提供同名 soname（libmpi.so.12），同时进 LD_LIBRARY_PATH 互相覆盖 | 只保留 mpich 一套 |

★ **登录节点与计算节点的 module 解析结果不同** ⇒ 任何环境结论**必须在计算节点验证**，登录节点通过不算数。

**实测通过的最终环境块**（已固化进 `deploy/hpc_deploy/patch_job.py` 的 `ENV_BLOCK`）：

```bash
source /public1/soft/modules/module.sh 2>/dev/null || true
module load hdf5/1.8.18 2>/dev/null || true
module load mpich/3.2-gcc9.3 2>/dev/null || true
for _d in /public1/soft/gcc/9.3.0-new/lib64 /public1/soft/gcc/9.1.0/lib64; do
  if [ -d "$_d" ]; then export LD_LIBRARY_PATH="$_d:$LD_LIBRARY_PATH"; break; fi
done
```

## 8. 护栏

- **Windows 侧执行**：必须用 `.venv-win\Scripts\python.exe`（基础托管解释器缺 cryptography → 凭据解密失败 → 脚本静默退出、日志 0 字节）；禁止 DETACHED/nohup。
- **WSL 侧**：`bash -c` 会吞 shell 变量与反引号；含 `$` 的文本落盘再执行。
- **网络抖动**：SSH 失败先判类——网络类失败（Connection refused/No route 等）等 60 s 未恢复才判死；物理/编译错误立即返回不重试。
- 长跑作业跟踪用单次探针脚本 + 宿主轮询，不要用单个阻塞进程死等（网络抖动/任务回收会整体丢失）。

## 关联资源

- `flash/flash_run/README.md` 及 modes/env/remote 三篇子 README
- `scripts/02_hpc/`（hpc_download_results、hpc_laserslab_test、hpc_run_uploader）
- skill `flash-hpc-fetch`（结果批量下载与完整性校验）
- `docs/FLASH三模式运行体系.md`（含 2026-10-23 ch_center in-situ 打通实录）
