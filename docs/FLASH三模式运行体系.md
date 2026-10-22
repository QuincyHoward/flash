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
| ch_center `--mode hpc-insitu` | ⚠ 链接已打通（FLASH_NO_MODULE_PURGE + Intel MPI LIBRARY_PATH 注入后 flash4 产出），卡在 NC-E 站点问题，见 §8 |

## 8. 已知限制：QC 通用树在 NC-E 的 Intel MPI 运行期符号错误（待修）

ch_center in-situ 冒烟 6 轮迭代后：链接成功（`FLASH_NO_MODULE_PURGE=1` 禁 module
purge/load + 注入 Intel MPI 2022.1 库路径后 flash4 正常产出），但运行期报
`libmpifort.so.12: undefined symbol: MPII_F_TRUE`。

诊断结论（探针实测，脚本 _probe_link/_probe_impi/_probe_pair/_probe_mpihello）：
- oneAPI MPI 自身自洽：mpiifort 编译的最小程序 `mpiexec -n 2` 登录节点直接跑通；
- 但 `lib/libmpifort.so.12` 引用的 `MPII_F_TRUE` 在配套 `libmpi.so.12`（含
  lib/release 子目录）的动态符号表中**不存在**——`/public1/soft/oneAPI/2022.1`
  目录疑似 mpifort/libmpi 版本错配（Frankenstein 安装）；
- 该问题与三模式架构无关，**hpc-remote 模式同样受影响**（同一 submit_flash.sh）。

修复路径（择一，属树级一次性配置）：
1. ★ 推荐：QC 通用树按 **mpich/3.2** 重新 setup+编译（Makefile.h 对齐 SNB 树方案
   `MPI_PATH=/public1/soft/mpich/3.2` + mpif90 wrapper——SNB 树同方案已在 NC-E
   验证编译/运行全通）；作业脚本恢复 module load mpich/3.2+hdf5。
2. 或排查 oneAPI 2022.1 安装完整性（libmpifort 与 libmpi 版本配对）。

ch_center in-situ 六轮冒烟的其它修复成果全部保留：
`read_text(newline=)` py3.10 兼容、`FLASH_NO_MODULE_PURGE` 开关、Intel MPI 库路径
注入（含 cd 修复+成功校验）、gen_checker 在超算源码树首跑通过。
