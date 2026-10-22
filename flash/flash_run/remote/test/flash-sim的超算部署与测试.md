# flash-sim 的超算部署与测试

> 日期: 2026-10-22 ｜ 目标超算: 中卫 NC-E（ParaCloud），账号 scfa2696（凭据名 `flash_ssh`）
> 部署目录: `~/PhySimX/PhySimX/simulation/flash/flash_sim/`（后期作 Gitee 同步目录）
> 驱动机: Windows（本仓库根），SSH/SFTP 经 `RemoteSession`（paramiko，凭据 Fernet 加密于 `~/.physimx/flash/credentials.enc`）

---

## 1. 部署架构与环境命名

```
Windows 本机 (联网)                      超算 NC-E (scfa2696, 离线)
─────────────────────                   ─────────────────────────────────────────
.venv-win        (Win/py3.13, 在线)      ~/PhySimX/PhySimX/simulation/flash/
.venv-linux      (WSL/py3.10.12, 离线)     flash_sim/         ← git clone (bundle, HEAD=7b13054)
packages/                                  ├── start_flash.py
  ├── flash_sim_all.bundle  (42MB)         ├── flash/ scripts/ test/
  ├── wheelhouse-linux/     (82 whl,       └── .venv-hpc-nce/  ★ 命名环境 (py3.10.8, 离线)
  │                          164.8MB)       ── 由 module python/3.10.8 创建
  └── deploy.tar.gz         (~212MB)      ~/PhySimX/.../flash_sim_pkg/  ← 中转区
                                           (bundle + wheelhouse + 安装日志/哨兵)
```

| 环境 | 位置 | Python | 模式 | 用途 |
|---|---|---|---|---|
| `.venv-win` | 本机 | 3.13.9 | 在线 | Windows 日常 + 01a 预演 |
| `.venv-linux` | 本机 WSL | 3.10.12 | **离线**（复刻超算路径） | 01b 预演 |
| `.venv-hpc-nce` ★ | 超算部署目录 | 3.10.8 (module) | **离线**（`--no-index` 硬闸门） | 超算正式环境（用户要求显式命名） |

WSL 3.10.12 与超算 3.10.8 同为 3.10 系列，01b 离线预演与超算安装**代码路径完全一致**，
是本轮成功的关键前置。

## 2. 端到端流程（9 步，均可独立重跑）

| 步 | 脚本（★2026-10-22 起收编至根目录 `deploy/hpc_deploy/`） | 作用 | 结果 |
|---|---|---|---|
| **00** | `remote_clean.py` | 清空超算安装目录（归档腾空，可回滚） | PASS（归档 `flash_sim.bak-<ts>`） |
| 01a | `local_env_windows.py` | Win 在线建环境+三套测试 | PASS（166/83/45） |
| 01b | `local_env_wsl.py --offline` | WSL 离线预演（Linux 路径） | PASS（166/83/45） |
| 02 | `probe_remote_env.py` | 超算只读探测（9 项） | PASS 9/9 |
| 03 | `build_wheelhouse_linux.py` | 交叉造 Linux wheelhouse | PASS（82 whl/164.8MB/审计 rc=0） |
| 04 | `build_bundle.py` | git bundle 制作+verify | PASS（42MB） |
| 05 | `package_and_upload.py` | tar 上传（SHA 双端比对）+远端 clone/增量 ff 同步 | PASS（上传 120s） |
| 06 | `remote_install.py` | 超算命名环境离线安装+三套测试 | **PASS（166/83/45，73s）** |
| 07 | `run_snb_smoke.py` | SNBOneCH_m `--tmax 1e-11` 极短仿真 | **PASS（RUN_EXIT=0，29.6s 墙钟）** |
| **08** | `run_public_tests.py` | **全局 pytest + 三个 public 子场景 sbatch 真跑** | 见 §8 |

编排入口: `python deploy/hpc_deploy/run_all.py [--from N | --only N | --skip a,b]`
> 本目录保留诊断脚本（diag_*/_probe_*/try_yt*）；部署链 00–08 已迁 `deploy/hpc_deploy/`，
> 其日志/包/结果统一落根目录 `artifacts/`（logs/hpc_deploy/、packages/）。

远端安装命令（等价手工操作）:
```bash
module load python/3.10.8
cd ~/PhySimX/PhySimX/simulation/flash/flash_sim
FLASH_VENV_DIR=$PWD/.venv-hpc-nce python3 start_flash.py \
    --offline --wheelhouse ~/PhySimX/PhySimX/simulation/flash/flash_sim_pkg/wheelhouse-linux \
    --profile full
```

## 3. Linux wheelhouse 交叉造包要点（Windows 上构建 manylinux/cp310）

```
pip download --only-binary=:all: \
    --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 \
    --python-version 3.10.8 --implementation cp --abi cp310 --abi abi3 \
    --dest packages/wheelhouse-linux <依赖闭包>
```

必须**手动补齐**的包（pip 交叉下载按当前解释器求值环境标记，会漏装）:
- py3.10 垫片: `typing-extensions tomli exceptiongroup importlib-metadata zipp backports.tarfile pytz`
- Linux 条件依赖: `jeepney secretstorage`（paramiko keyring 后端）、`pexpect ptyprocess`（ipython 的 `sys_platform!="win32"` 依赖，**WSL 离线预演实测抓出**）

**glibc 2.17 上限锁定**（NC-E = CentOS 7，`ldd 2.17`，pip 22.2.2 最高支持 manylinux_2_17）:

| 包 | 锁定版本 | 原因 |
|---|---|---|
| pandas | 2.3.2 | 2.3.3 只发 2_24+ |
| h5py | 3.14.0 | 3.15/3.16 只发 2_28 |
| pillow | 12.2.0 | 12.3 只发 2_27+ |
| ewah-bool-utils | 1.2.2 | 1.3.0 只发 2_24 |
| **yt** | **4.4.0** | 见 §4.3 |

`--python-version` 必须写**完整版本 3.10.8**（写 3.10 被视为 3.10.0，yt 4.4.0 的
`Requires-Python >=3.10.3` 会被误拒）。

## 4. 实测问题与逐项恢复记录（9 项）

1. **过时测试 `test_scenarios_package_import`**：2026-10-21 场景目录重组（3752b77）后未同步。
   修复：改为从 `flash.scenarios.public` 导入，且占位目录（plasma_preparation/
   collision_compression 未入 git）容错跳过。
2. **managed python 缺 cryptography**：SSH 脚本必须用项目 `.venv` 解释器跑
   （凭据 Fernet 解密依赖）。
3. **超算 git 1.8.3.1 不支持 `git -C`**（1.8.5 引入）：远端命令一律 `cd dir && git ...`。
4. **★ /tmp 是登录节点本地盘**：动态路由把不同会话分到不同登录节点，/tmp 下文件互相
   不可见（脚本"消失"假象）。安装脚本/日志/哨兵全部移到 **$HOME 并行盘**。
5. **系统裸 python3=3.6.8**：远端必须 `module load python/3.10.8`（用 `bash -lc` 保登录环境）。
6. **Lustre 并行盘 pip 大事务随机 ENOENT**：96 包连续小文件写入时 dist-info 随机缺失
   （sympy/fonttools 先后中招；单包安装正常、SHA 校验无损）。
   对策：**断点续装循环**——pip 失败不删 venv，重复 `pip install`（已装自动跳过），
   6 轮内装齐。
7. **paramiko exec `nohup ... & echo` 返回不可靠**：经常"返回失败但命令已实际执行"
   （曾致 3 个并发编排器竞争同一 venv ⇒ 健康检查 SIGSEGV(-11)、venv 凭空消失）。
   对策：启动重试后**先 ps 查重再轮询**；轮询用并行盘哨兵文件（跨节点 kill -0 无效）。
8. **★ yt 4.3.1 在 NC-E 全节点 SIGSEGV(139)**：import 即崩（登录+计算节点复现，
   .so SHA256 与 wheel 一致、GLIBC 符号 ≤2.14、ELF 特征与 numpy 无异，根因未完全定位）。
   版本矩阵实测：4.1.4/4.3.0 = numpy1 构建与 numpy2 ABI 冲突（干净报错）；
   **4.4.0（numpy2 构建，requires-python≥3.10.3）实测全绿** ⇒ 锁定。
   连带修复：output_processors 45 用例从段错误恢复为全过。
9. **`test_engine_dryrun` fresh-clone 失败**：`_primary_scenario()` 无条件优先私有场景
   thin_layer_sandwich_si，但其 sim_input_si/ 的 F90/cn4 因 FLASH License §3 被
   .gitignore 排除 ⇒ 部署树缺 .F90。修复：私有场景仅在 sim_input 实际完整（含 .F90）
   时选用，否则回落 ch_center（其生成器超算实测 14 文件生成成功）。
10. **`MPII_F_TRUE: undefined symbol`（NC-E QC 树运行期）**：原判「oneAPI 安装错配」被
    探针实测**推翻**。三条真因：① 注入的 oneAPI 库路径写错（真实在
    `oneAPI/2022.1/mpi/latest/lib`）；② 计算节点 `module load mpich/3.2-gcc9.3` 的
    `libmpifort.so.12` 需 `GFORTRAN_9` 符号版本，而注入的 gcc 8.1.0 只到 GFORTRAN_5；
    ③ oneAPI 与 mpich 提供**同名 soname**（`libmpi.so.12`/`libmpifort.so.12`）互相覆盖。
    修法：`module load hdf5/1.8.18` + `module load mpich/3.2-gcc9.3` +
    `LD_LIBRARY_PATH` 追加 `gcc/9.3.0-new/lib64`（回退 9.1.0）⇒ 计算节点实跑通过。
    ★ **登录节点与计算节点 module 解析不同**（登录节点=Intel 2018 MPI，
    计算节点=mpich/3.2）⇒ 环境结论必须在计算节点验证。
11. **paramiko exec 丢回显 + 启动重试多起实例**：远端脚本「回显失败」但作业其实已在跑，
    重试每次都**真的多起一个实例**（ch_center 曾被提交 3 次：4917970/4917971/4917975）。
    对策：① **PID 锁**防重入（`echo $$ > LOCK` + `trap 'rm -f $LOCK' EXIT`）；
    ② 启动判据改为「回显 LAUNCHED，**或**日志已出现/哨兵已生成」。
12. **★ sandwich 场景 cn4 路径层级错误（2026-10-23）**：两个 sandwich 生成器用
    `SCRIPT_DIR.parents[2]` 定位中央表库 ⇒ 实际指向 `flash/scenarios/input_gen`（多一层）
    ⇒ cn4 复制静默失败 ⇒ gencheck 报 `eos_files missing`。
    ★ **本地能过只因 `sim_input/` 有历史遗留 cn4** —— 干净克隆必失败。
    修法：改为**向上搜索** `input_gen/gen_eos_op/eos_op_data`，不再硬编码层数；
    并加 fresh-clone 回归（本地 `git clone` 到临时目录实测）。
13. **★ public 测试执行顺序错（A1 先于 A2）**：`test_engine_dryrun` 会把场景 sim_input
    复制到临时目录并断言含 `*.cn4`；生成目录被 .gitignore 排除 ⇒ pytest 先行必然失败。
    修法：`run_public_tests.py` 把 **A2（生成输入）提到 A1（pytest）之前**。
    配套：`ensure_sim_input` 判定一律要求 `*.cn4` 存在（原来只查 Config+par / 目录存在
    ⇒ cn4 缺失仍误判就绪）；`_primary_scenario` 同时要求 `*.F90` 与 `*.cn4`
    （否则会选中「有 F90 缺 cn4」的场景，失败信息掩盖真正根因）。

## 5. 超算最终验证结果（INSTALL_TEST_REPORT.txt，已回收至 results/）

```
项目目录 : ~/PhySimX/PhySimX/simulation/flash/flash_sim   (Git 7b130545437d)
虚拟环境 : .venv-hpc-nce   Python(venv): 3.10.8
安装模式 : ★ 离线（--no-index，未联网）  wheelhouse: flash_sim_pkg/wheelhouse-linux
套件              passed  failed  skipped  error  结论
framework           132      0       1       0     PASS
input_gen            83      0       0       0     PASS
output_processors    45      0       0       0     PASS
整体结论: 安装验证通过
环境版本快照: numpy 2.2.6 / scipy 1.15.3 / h5py 3.14.0 / matplotlib 3.10.9 /
              yt 4.4.0 / pandas 2.3.2 / paramiko 5.1.0 / pytest 9.1.1
```

SNB 冒烟（标准验证命令）:
```
python flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py \
    --mode hpc --account flash_ssh --tmax 1.0e-11
```
构建 Job 4917038 COMPLETED → 运行 Job 4917041 COMPLETED，`RUN_EXIT=0`、墙钟 29.6s，
chk_0000/0001 + LaserEnergyProfile.dat 回收至 `results/snb_smoke_20261022_130256/`。

## 6. 后续 Gitee 同步操作指引（该目录 = Gitee 同步目录）

超算不可直连，同步走"增量 bundle"（超算侧 origin 已指向 `https://gitee.com/physimx/flash.git`，
临时可联网时可直接 `git pull`）:

```bash
# ── 本地（联网机）────────────────────────────────────
git bundle create flash_sim_incr.bundle origin/master..master   # 增量（通常 <1MB）
# sftp 上传 flash_sim_incr.bundle 到 flash_sim_pkg/，然后：
# ── 超算 ────────────────────────────────────────────
cd ~/PhySimX/PhySimX/simulation/flash/flash_sim
git fetch ../flash_sim_pkg/flash_sim_incr.bundle 'refs/heads/master:refs/heads/incr'
git merge --ff-only incr && git branch -d incr
```

`package_and_upload.py` 已内置同样的增量 ff 同步逻辑（HEAD 不一致时自动 fetch+merge）。
wheelhouse 更新：重跑 Step 03 → Step 05（tar 内含 wheelhouse，远端自动解压覆盖）。

## 7. 工作区产物索引

```
flash/flash_run/remote/test/
├── scripts/          # 01a–07 + run_all + diag_*/try_*/wait_* 诊断探针（全部入库）
├── packages/         # bundle / wheelhouse-linux / deploy.tar.gz（git 忽略，不入库）
├── logs/             # 每步日志 + 诊断日志（git 忽略）
└── results/
    ├── INSTALL_TEST_REPORT_hpc_final.txt    # 超算最终安装报告
    ├── hpc_framework.log 等                 # 超算三套测试完整日志
    └── snb_smoke_20261022_130256/           # chk_0000/0001 + LaserEnergyProfile.dat
```

## 8. Step 08：全局测试 + public 子场景测试（超算 sbatch 真跑）

脚本 `deploy/hpc_deploy/run_public_tests.py`。**真实仿真一律 `sbatch` 提交**，
不在登录节点直接跑（登录节点无 FLASH 环境、也无计算节点 GPU/核资源）。

### 8.1 三阶段结构

| 阶段 | 内容 | 位置 | 判据 |
|---|---|---|---|
| **A2**（先） | 三个 public 场景 `gen_flash_inputs.py --force` + `DependencyChecker`（+ ch_center 的 `RelationChecker`） | 登录节点 | `A2_RC=0` |
| **A1**（后） | 三套全局 pytest：`test/`、`flash/input_gen/test/`、`flash/output_processors/test/` | 登录节点 | `A1_PYTEST_RC=0` |
| **B** | 三个 public 场景真实 FLASH 仿真，**sbatch 串行提交** | 计算节点 | `B_RC=0` |

★ **A2 必须先于 A1**（根因见 §4 第 13 条）：生成目录被 .gitignore 排除，
干净克隆上 pytest 先行必然缺 `*.cn4`。

### 8.2 三个 public 场景

| 场景 | 目录 | 说明 |
|---|---|---|
| `ch_center` | `flash/scenarios/public/center_evolution/ch_center/` | LaserSlab1D，CH 靶 + He 侧，双束 351nm 相向入射 |
| `grad_dens_sandwich` | `flash/scenarios/public/sandwich/grad_dens_sandwich/` | HE-CH-Si-CH-HE 渐变密度 |
| `thin_layer_sandwich_si` | `flash/scenarios/public/sandwich/thin_layer_sandwich/` | Si/CH/He 三层靶 |

### 8.3 阶段 B 的作业脚本补丁（`patch_job.py`，**不用 sed**）

三个场景自带的 `submit_flash.sh` 形态差异极大：

| 场景 | `#SBATCH` 形态 |
|---|---|
| ch_center | 长选项 `#SBATCH --output=FILE` |
| grad_dens | 短选项 `#SBATCH -o NAME_%%j.out` |
| thin_layer | **一行多选项** `#SBATCH --job-name=... --output=... --partition=... --ntasks=4 --time=...`，且 `R=` 出现在**行中** |

⇒ `sed` 无法覆盖（正则分隔符与 `|` 冲突、行内 `R=` 不锚定行首），
改用 `shlex.split` 解析 `#SBATCH` 逐选项改写。

补丁三处：
1. SBATCH 输出路径 → 并行盘 `WORK/out/{tag}_%j.out`（★ 绝不用 `/tmp`）
2. 运行目录 `R=` → 并行盘（`/tmp` 是计算节点本地盘，作业结束即丢）
3. par 的 `tmax`/`dtmax` → `1e-11` / `1e-13`（只验证「能跑出 chk」，不产生物理结果）

★ 短选项输出必须用空格（`-N=1` 会被 SLURM 拒）。
★ 环境块必须排在**所有 `#SBATCH` 之后、正文之前**（SLURM 只在首个非注释行前解析 `#SBATCH`）。
★ 禁 `module purge`（会清掉 hdf5/编译器 runtime 路径）。

### 8.4 判定口径

| 结果 | 含义 |
|---|---|
| `PASS` | chk 数 > 0 |
| `KNOWN_LIMIT` | 撞已知站点限制（如实记录，不改判 PASS） |
| `FAIL` | 编译失败 / 作业 FAILED / 无 chk |

★ **chk 文件名无 `.h5` 后缀**（形如 `lasslab_hdf5_chk_0007`），
统计时不能只匹配 `*.h5`。
★ **防重入**：远端脚本用 PID 锁（paramiko exec 常丢 `LAUNCHED` 回显，
启动重试每次都会**真的多起一个实例**）。
★ 启动判据 = 「回显 LAUNCHED，**或**日志已出现/哨兵已生成」。

### 8.5 产物位置

- 报告：`WORK/PUBLIC_TEST_REPORT.txt`（含 `A1_PYTEST_RC` / `A2_RC` / `B_RC`）
- 日志：`WORK/logs/`（`pytest_*.log`、`gencheck_*.log`、`relation_*.log`、`public_test.log`）
- 场景输出：`WORK/out/{tag}_*.out` / `*.err`

