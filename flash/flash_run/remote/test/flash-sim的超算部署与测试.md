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

## 2. 端到端流程（8 步，均可独立重跑）

| 步 | 脚本（★2026-10-22 起收编至根目录 `deploy/hpc_deploy/`） | 作用 | 结果 |
|---|---|---|---|
| 01a | `local_env_windows.py` | Win 在线建环境+三套测试 | PASS（132/83/45） |
| 01b | `local_env_wsl.py --offline` | WSL 离线预演（Linux 路径） | PASS（132/83/45，432s） |
| 02 | `probe_remote_env.py` | 超算只读探测（9 项） | PASS 9/9 |
| 03 | `build_wheelhouse_linux.py` | 交叉造 Linux wheelhouse | PASS（82 whl/164.8MB/审计 rc=0） |
| 04 | `build_bundle.py` | git bundle 制作+verify | PASS（42MB，HEAD=7b13054） |
| 05 | `package_and_upload.py` | tar 上传（SHA 双端比对）+远端 clone/增量 ff 同步 | PASS（上传 145s） |
| 06 | `remote_install.py` | 超算命名环境离线安装+三套测试 | **PASS（132/83/45，82s）** |
| 07 | `run_snb_smoke.py` | SNBOneCH_m `--tmax 1e-11` 极短仿真 | **PASS（RUN_EXIT=0，29.6s 墙钟）** |

编排入口: `python deploy/hpc_deploy/run_all.py [--from N | --only N | --skip a,b]`
> 本目录保留诊断脚本（diag_*/_probe_*/try_yt*）；部署链 01–07 已迁 `deploy/hpc_deploy/`，
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
