# FLASH 三模式运行体系（wsl / hpc-remote / hpc-insitu）

> 2026-10-22 三模式统一改造定案。收敛原有 5 种运行方式，统一执行入口与目录契约，
> 保证 Windows / WSL / 超算三端 flash 包功能一致。

## 1. 模式矩阵

| 模式 | 规范名 | 驱动位置 | FLASH 执行位置 | 对应原方式 | 典型入口 |
|---|---|---|---|---|---|
| ① 本机 WSL | `wsl` | Windows python | WSL（FLASH 树在 WSL $HOME） | 模式① | `FLASH_RUN_MODE=wsl`（默认） |
| ①' WSL 内直跑 | `wsl`（自动降级） | WSL python | WSL | 模式② | 同上；`detect_native_linux()` 自动去掉 `wsl bash -c` 包装 |
| ② 超算 SSH 驱动 | `hpc-remote` | Windows python（凭据+RemoteSession） | 超算计算节点（sbatch） | 模式③④ | `FLASH_RUN_MODE=hpc`（别名永续） |
| ③ 超算就地 | `hpc-insitu` | **超算登录节点**（.venv-hpc-nce） | 超算计算节点（sbatch） | 模式⑤ | `--mode hpc-insitu` / `FLASH_RUN_MODE=hpc-insitu` |

**解析优先级**（`flash.scenarios.runner.resolve_run_mode`）：
`--mode` 显式 > 环境变量 `FLASH_RUN_MODE` > 场景模块常量 `RUN_MODE`。
★ 不做平台自动兜底——模式切换必须显式。

**别名（永续兼容）**：`local→wsl`；`hpc/remote/slurm/supercomputer→hpc-remote`；
`insitu/in-situ/hpc-in-situ→hpc-insitu`。

## 2. 目录契约

```
Windows 本机                                超算 NC-E (scfa2696)
<repo>/                 代码+venv            ~/PhySimX/PhySimX/simulation/flash/flash_sim/   代码+venv (git 干净)
  ├─ .venv-win / .venv-linux                 ├─ .venv-hpc-nce/     ★ 命名环境 (py3.10.8)
  └─ (FLASH 树在 WSL $HOME)                  ├─ (FLASH 树在 ~/QC/FLASH{,SNB}/FLASH4.8)
<repo>/../flash_sim_runs/  ← 输出外置        ~/PhySimX/.../flash_sim_runs/   ← 输出外置
  └─ <scenario>/run_NNNNNN/                   └─ <scenario>/run_NNNNNN/
       input/ output/ plots/ logs/ state.json
```

- **输出外置契约**：flash_sim 包目录只放代码+venv，`git status` 永远干净；
  运行输出一律写兄弟目录 `flash_sim_runs/`（`FLASH_RUNS_DIR` 可覆盖）。
- ★ 约束：FLASH `setup/make` 一律在 FLASH 树 objdir 内进行；runs 目录只承载
  输入快照、sbatch 脚本、作业日志与回收结果。
- **场景资产**（License §3 不入 git 的 cn4 表 / Driver F90 / SNB 覆盖 F90）：
  hpc-remote 由单元包上传补齐；hpc-insitu 需先跑
  `sync_snb_assets.py`（本机 → 超算部署树 flash_input/，idempotent）。

## 3. 环境变量总表

| 变量 | 作用 | 默认 |
|---|---|---|
| `FLASH_RUN_MODE` | 运行模式（wsl / hpc / hpc-insitu） | 场景 RUN_MODE |
| `FLASH_VENV_DIR` | 项目 venv 显式路径 | .venv-win / .venv-linux / .venv-hpc-nce |
| `FLASH_RUNS_DIR` | 运行输出根目录 | `<包根>/../flash_sim_runs` |
| `FLASH_SIM_USER_DIR` | FLASH 安装前缀目录名（无凭据机器必设，如 QC） | 凭据用户名 → hello |
| `FLASH_HPC_WORKDIR` | hpc-remote 远程工作目录: `temp`(AI/Aitemp) / `runs`(flash_sim_runs) | temp |
| `FLASH_HPC_PKG_ROOT` | hpc-remote runs 模式的远端包根 | `$HOME/PhySimX/PhySimX/simulation/flash/flash_sim` |
| `FLASH_HPC_PYTHON` | 远端分析 python 显式路径 | 回退链见 §5 |

## 4. slurm 作业控制（`flash/flash_run/remote/slurm_control.py`）

hpc-remote 与 hpc-insitu **共用同一套作业控制**（executor 注入）：
- `LocalExecutor`（in-situ，纯 subprocess）/ `RemoteExecutor`（包装 RemoteSession）
- `SlurmJobSpec` + `render_sbatch` + `run_job_chain`（SNB build→run 双作业、
  laserslab run→分析 chain 统一表达；par 闸门 / skip-build 补解压为 gate 回调）
- `wait_for_job`：sacct 轮询 + 输出文件 marker 确认（COMPLETED 但 marker
  未命中 → WARN 仍返回 True，与 SNB 原版语义一致）

## 5. 超算分析 python 回退链（ch_center）

```
FLASH_HPC_PYTHON (env)  →  $HOME/.venv-hpc-nce/bin/python  →  module python/3.9.6 (旧路 WARN)  →  python3  →  本地分析
```
venv 路线自带 h5py 3.14 + yt 4.4.0，替代旧 module 路线。

## 6. 三端一致性自检

```bash
python -m flash.scenarios.runner --check-env
```
报告：平台判定 / venv / FLASH 树（含 SNB 树）/ runs_root 可写性 / slurm 可用性 /
凭据存在性 / 三模式各自 ✓✗ / git HEAD（对照超算 bundle 同步）。

## 7. 已验证（2026-10-22）

| 项 | 结果 |
|---|---|
| Windows 全量 pytest | 166 passed（含 36 项新增单测） |
| SNBOneCH_m `--mode hpc-insitu --tmax 1e-11` | build Job 4917098 + run Job 4917099 均 COMPLETED，RUN_EXIT=0（31.9s），就地收集 chk=2/plt跳过=2 → flash_sim_runs/SNBOneCH_m/run_000001 |
| hpc-remote 回归（SNB `--mode hpc`） | 重构前后行为一致 |
| bundle 增量同步 | 本地 HEAD == 超算 HEAD（fetch+ff-merge，git 1.8.3 兼容） |
| ch_center `--mode hpc-insitu` | ✅ 已打通（2026-10-23 定位 `MPII_F_TRUE` 真因并修复，计算节点实跑产出 8 chk + 28 plt，见 §8） |

## 8. ✅ 已解决（2026-10-23）：QC 通用树的 `MPII_F_TRUE` 运行期符号错误

> 2026-10-22 曾记为"已知限制（待修）"，2026-10-23 由探针实测**定位真因并修复**，
> 计算节点实跑通过（推进 139 步、产出 8 chk + 28 plt）。原结论保留在 §8.1 供追溯。

### 8.0 修复结论（探针实测，脚本 probe7–probe23）

`libmpifort.so.12: undefined symbol: MPII_F_TRUE` 的真因是**环境变量层面的
同名 soname 覆盖**，不是 FLASH 树编译问题，也**不是** oneAPI 安装错配：

| # | 真因 | 证据 | 修法 |
|---|---|---|---|
| ① | 注入的 oneAPI 库路径**写错**：`oneAPI/2022.1/lib`（不存在）真实在 `oneAPI/2022.1/mpi/latest/lib` | `ls` 实测；`nm -D mpi/latest/lib/release/libmpi.so.12 \| grep -c MPII_F_TRUE` = **1**（符号存在） | 不再注入 oneAPI MPI 路径 |
| ② | 站点 `module load mpich/3.2-gcc9.3` 在**计算节点**解析到 mpich/3.2，其 `libmpifort.so.12` 需要 `GFORTRAN_9` 符号版本；注入 gcc 8.1.0 的 `libgfortran.so.5` 只到 GFORTRAN_5 ⇒ 混用即崩 | 计算节点报错 `version 'GFORTRAN_9' not found (required by mpich/3.2/lib/libmpifort.so.12)` | 改用 `gcc/9.3.0-new/lib64`（循环取 9.3.0-new → 9.1.0） |
| ③ | oneAPI 与 mpich 提供**同名 soname**（`libmpi.so.12` / `libmpifort.so.12`），同时进 `LD_LIBRARY_PATH` 互相覆盖 | `ldd` 对比：注 oneAPI 时解析到 oneAPI，注 mpich 时解析到 mpich | 只保留 mpich 一套 |

★ **登录节点与计算节点的 `module load mpich/3.2-gcc9.3` 解析结果不同**：
登录节点 → Intel 2018 MPI（`/public1/soft/intel/2018/.../mpi/intel64/bin/mpirun`）；
计算节点 → mpich/3.2（`/public1/soft/mpich/3.2/bin/mpirun`）。
⇒ 任何环境结论**必须在计算节点验证**，登录节点通过不算数。

**✅ 实测通过的最终环境块**（已固化进 `deploy/hpc_deploy/patch_job.py` 的 `ENV_BLOCK`）：

```bash
source /public1/soft/modules/module.sh 2>/dev/null || true
module load hdf5/1.8.18 2>/dev/null || true
module load mpich/3.2-gcc9.3 2>/dev/null || true
for _d in /public1/soft/gcc/9.3.0-new/lib64 /public1/soft/gcc/9.1.0/lib64; do
  if [ -d "$_d" ]; then export LD_LIBRARY_PATH="$_d:$LD_LIBRARY_PATH"; break; fi
done
```

实测结果（作业 4917836，v5_192 分区，`mpirun -np 2`）：
`MPIRUN_RC=0`、推进 **139 步**至 `t=1.0057e-11`、**8 个 chk + 28 个 plt**、
`exiting: reached max SimTime` ⇒ 端到端全通。

⇒ **原"修复路径 1（QC 树按 mpich 重新 setup+编译）"不需要做**：树本身无需重编，
  只需正确的运行时环境。

### 8.1 原结论（2026-10-22，保留供追溯，**已被 8.0 推翻**）

> ~~`/public1/soft/oneAPI/2022.1` 目录疑似 mpifort/libmpi 版本错配（Frankenstein 安装）~~
> —— 实为路径取错 + mpich 覆盖所致；oneAPI 的 `mpi/latest/lib` 自洽无缺。

ch_center in-situ 六轮冒烟的其它修复成果全部保留：
`read_text(newline=)` py3.10 兼容、`FLASH_NO_MODULE_PURGE` 开关、Intel MPI 库路径
注入（含 cd 修复+成功校验）、gen_checker 在超算源码树首跑通过。
