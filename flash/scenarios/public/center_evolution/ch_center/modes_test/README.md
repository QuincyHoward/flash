# ch_center 多执行模式测试（modes_test）

同一子场景（`ch_center`：CH 靶居中、两束 351 nm 激光相向入射）在**五种执行路径**
下的测试与维护工具集。子场景本身只关心物理搭建；执行方式由运行模式参数控制，
默认 `auto` 按平台自适应（判定表唯一实现：`flash.flash_run.execution.resolve_target`）。

## 1. 模式矩阵

| key | 驱动进程平台 | 场景运行模式 | 覆盖的用户场景 |
|---|---|---|---|
| `win-wsl` | Windows | `wsl` | a. Windows 中执行 python 脚本 → WSL FLASH 运算与分析 |
| `win-hpc` | Windows | `hpc-remote` | a. Windows 中执行 python 脚本 → 超算 FLASH（上传/提交/分析/下载） |
| `wsl-wsl` | WSL | `wsl` | b. WSL 中执行 python 脚本 → WSL FLASH 运算与分析 |
| `wsl-hpc` | WSL | `hpc-remote` | b. WSL 中执行 python 脚本 → 超算 FLASH（上传/提交/分析/下载） |
| `hpc-insitu` | 超算登录节点 | `hpc-insitu` | c. 超算中执行 python 脚本 → 超算 FLASH（就地 sbatch） |

五种路径共用**同一份输入**（只通过 `--tmax` 改终止时间，脉冲/网格/EOS/激光逐字
不变），因此 dens/nele 演化曲线可直接叠加对比。

## 2. 目录结构

```
ch_center/modes_test/
├── README.md                 本文
├── plot_style.py             统一绘图风格（全英文 / Times New Roman / >=18pt）
├── run_mode_test.py          单模式驱动（run / fetch-insitu 两个子命令）
├── analyze_modes.py          跨模式 dens/nele 对比分析
└── results/                  （gitignore；产物，可重新生成）
    ├── <key>/chk/            该模式回传的全部 checkpoint（chk-only 策略）
    ├── <key>/logs/           驱动日志 + 场景 WSL 运行日志
    ├── <key>/plots/          场景本地/远端诊断图（按模式防覆盖）
    ├── <key>/summary.json    该模式状态摘要（ok/n_chk/墙钟/目标解析）
    ├── hpc-insitu/           同上；由超算侧生成后经 fetch-insitu 回传
    └── comparison/           跨模式对比产物（CSV + 3 张图 + 报告）
```

## 3. 运行方法

### 3.1 Windows → WSL（`win-wsl`）

```bat
cd /d E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\run_mode_test.py --mode-key win-wsl --tmax 2e-10
```

### 3.2 Windows → 超算（`win-hpc`）

```bat
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\run_mode_test.py --mode-key win-hpc --tmax 2e-10
```

内部流程：上传 `flash_input/` → `sbatch submit_flash.sh`（v5_192，4 任务）→
远端 `hpc_analyze_ch_center.py` 分析 → 回传 chk + PNG。凭据来自
`~/.physimx/flash/`（Windows 侧）。

### 3.3 WSL → WSL（`wsl-wsl`）与 WSL → 超算（`wsl-hpc`）

Windows 上直接调用会自动转投 WSL 执行（驱动进程必须真的在 WSL 里）：

```bash
.venv/Scripts/python.exe flash/scenarios/public/center_evolution/ch_center/modes_test/run_mode_test.py --mode-key wsl-wsl --tmax 2e-10
.venv/Scripts/python.exe flash/scenarios/public/center_evolution/ch_center/modes_test/run_mode_test.py --mode-key wsl-hpc  --tmax 2e-10
```

等价地，在 WSL 内手动执行：

```bash
cd /mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash
.venv-linux/bin/python flash/scenarios/public/center_evolution/ch_center/modes_test/run_mode_test.py --mode-key wsl-wsl --tmax 2e-10
```

`wsl-hpc` 的凭据处理：WSL 内 `HOME` 默认 `/root`，其中没有 `~/.physimx`；
驱动会把 `HOME` 指向 `/mnt/c/Users/<Windows用户名>`（**只读引用**，不复制、
不修改凭据），并用 `FLASH_SSH_BACKEND=paramiko` 直连。

### 3.4 超算就地（`hpc-insitu`）

先把本目录同步到超算仓库（`~/PhySimX/PhySimX/simulation/flash/flash_sim`），
再在**登录节点**执行：

```bash
# 同步（任选其一：git 同步链，或直接 scp 本目录）
scp -r flash/scenarios/public/center_evolution/ch_center/modes_test \
    scfa2696@<hpc>:~/PhySimX/PhySimX/simulation/flash/flash_sim/flash/scenarios/public/center_evolution/ch_center/

# 超算登录节点执行（建议 nohup + 轮询日志，防网络断连）
cd ~/PhySimX/PhySimX/simulation/flash/flash_sim
PYTHONUNBUFFERED=1 nohup .venv-hpc-nce/bin/python \
    flash/scenarios/public/center_evolution/ch_center/modes_test/run_mode_test.py \
    --mode-key hpc-insitu --tmax 2e-10 \
    > flash/scenarios/public/center_evolution/ch_center/modes_test/results/hpc-insitu/logs/driver_hpc-insitu.log 2>&1 &
```

回传产物到本地：

```bat
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\run_mode_test.py fetch-insitu
```

## 4. 对比分析

```bat
.venv\Scripts\python.exe flash\scenarios\public\center_evolution\ch_center\modes_test\analyze_modes.py
```

输出（`results/comparison/`）：

| 文件 | 内容 |
|---|---|
| `modes_summary.csv` | 五模式全时序：t / dens_c / nele_c / tele_c(eV) / dens_max |
| `dens_nele_evolution.png` | dens、nele 中心区随时间演化（五模式叠加，1×2） |
| `final_profiles.png` | 末态共同时刻 dens/nele/tele 空间剖面（1×3） |
| `mode_deviation.png` | 各模式相对参考模式（默认 `win-wsl`）偏差，对数轴 |
| `MODES_TEST_REPORT.md` | 状态表 + 末值表 + 偏差结论 |

物理量约定：`nele = ye × dens × N_A`（cm^-3）；chk 内温度为 **K**，图中折算
eV（÷11604.518）；中心分析区 |x| ≤ 5 µm（与场景 `analysis_half_width_um` 一致）。

## 4b. 首轮测试结果（2026-10-24，tmax = 1.188 ns 全时长）

| 模式 | 结果 | chk | t_end (s) | 墙钟 (s) | max rel.dev（dens / nele，vs win-wsl） |
|---|---|---|---|---|---|
| win-wsl | 成功 | 342 | 1.188e-09 | 73 | 参考 |
| wsl-wsl | 成功 | 342 | 1.188e-09 | 72 | **0 / 0（逐位一致）** |
| win-hpc | 成功 | 341 | 1.188e-09 | 727 | 4.36e-03 / 5.36e-03 |
| wsl-hpc | 成功 | 341 | 1.188e-09 | 694 | 4.36e-03 / 5.36e-03 |
| hpc-insitu | 成功 | 341 | 1.188e-09 | 143 | 4.36e-03 / 5.36e-03 |

结论：
- **驱动进程平台不影响结果**：win-wsl 与 wsl-wsl（同一 WSL 二进制、同 4 MPI
  进程、同网格分解）输出**逐位一致**（偏差 0）；
- **三个超算路径彼此逐位一致**（同一 HPC 二进制），与 WSL 参考的偏差
  ~5e-3 且集中在激波压缩段（t > 0.35 ns），来源为 Intel/gcc 不同编译器
  的浮点细节；激波到达前（t < 0.35 ns）偏差 ~1e-13；
- 物理合理性：中心密度由 1.0 → 峰值 ~5 g/cm³（激波汇聚）→ 末态 2.0 g/cm³，
  与 1D CH 靶对向驱动压缩图像一致。

## 5. 驱动设置的环境变量

| 变量 | 值 | 用途 |
|---|---|---|
| `FLASH_COLLECT_DIR` | `results/<key>/chk` | 每轮独立收纳 chk（chk-only 回传策略） |
| `FLASH_RUN_WORKDIR` | `/root/flash_modes_work/<key>`（WSL 两模式） | 每轮独立运行 cwd，**防 objdir 历史 chk 污染**；必须落 WSL 原生 ext4（见维护要点 1） |
| `FLASH_FETCH_LIMIT` | `0` | 回传全部帧（交互模式默认只取 10） |
| `FLASH_LS_LIMIT` | `2000` | 远端 `ls \| head` 上限（默认 50 会截断批量矩阵） |
| `FLASH_SSH_BACKEND` | `paramiko`（wsl-hpc） | WSL 内 paramiko 直连 |
| `HOME` | `/mnt/c/Users/<Windows用户名>`（wsl-hpc） | 凭据来源（只读） |
| `FLASH_WSL_WORK_ROOT` | `/root/flash_modes_work` | WSL 工作根目录（可改；禁 `/mnt/*`） |

> 注：**不设** `FLASH_NO_MODULE_PURGE` —— ch_center 二进制已预置，超算作业走
> module 路径（mpich + hdf5）获得 libhdf5/libgfortran，见维护要点 9。

## 6. 维护要点（历史坑）

0. **★★ wsl.exe 命令串拆分（2026-10-24 实测，代价一次完整跑崩）★★**：
   本机 `wsl bash -c "..."` 会把命令串在**顶层 `;` / `&&` / `||`** 处拆成多次
   独立执行（`false; echo $?`→0；`X=5; echo $X`→空；
   `false > log 2>&1 && echo RC=0 || echo RC=$?`→恒写 RC=0；仅最后一段 rc 透传）。
   ⇒ 复合命令、env 前缀、行内哨兵**全部不可信**。旧 `main_wsl` 的
   `; echo "FLASH_EXIT_CODE=$?"` 哨兵恒为 0，FLASH 崩溃（exit 134）被报成
   "运行成功"。现解法：逻辑收进脚本文件 `flash_input/run_flash_wsl.sh`
   （main_wsl 自动生成，**必须 LF 行尾**——Windows `write_text` 的 CRLF 会让
   bash 解析崩），wsl 侧只发一条简单命令 `bash <wrapper> <args...>`。
   **任何新增 `wsl bash -c` 调用都不得使用顶层 `;`/`&&`/`||`。**
1. **WSL 运行工作目录必须落原生 ext4**：FLASH 的 HDF5 MPI-IO 写 `/mnt/e`
   （drvfs）会间歇失败（`ADIOI_GEN_READCONTIG: No data available` →
   SIGABRT 134），短跑偶然通过、全长跑必崩。驱动把
   `FLASH_RUN_WORKDIR` 固定到 `/root/flash_modes_work/<key>`
   （可用 `FLASH_WSL_WORK_ROOT` 改根）；产物收集目录仍在 `/mnt/e`
   （普通 cp，非 MPI-IO）。
2. **产物完整性判据**：`n_chk>0` 会把"崩溃后的部分产物"判成成功（首跑
   57/340 chk 假成功即此）。驱动现要求末 chk 时间 ≥ 98% tmax。
3. **输入只生成一次、跨模式共享**：`flash_input/` 由 `gen_flash_inputs.py` 经
   input_gen 生成（gitignore）。首次运行自动重建 `run_flash.sh` 为支持
   `FLASH_RUN_WORKDIR` 的新版；之后五模式复用同一份输入，保证"同一算例"。
   ⚠ `--tmax` 只在**输入生成时**生效（.par 写死）；改 tmax 必须
   `gen_flash_inputs.py --force` 重建，否则五模式会用旧 .par 的 tmax。
4. **objdir 按平台分化**：Windows 凭据用户名为 `QC` ⇒ 生成 `OBJ_DIR=QC/LaserSlab_ChCenter`；
   WSL 侧该 objdir 二进制已存在（跳过编译）。超算侧原本只有 `hello/LaserSlab_ChCenter`，
   已通过 `cp -a` 预置 `QC/LaserSlab_ChCenter`（2026-10-24），因此三个超算路径
   均跳过编译。若在干净克隆/新机器上复现，需二选一：
   `cp -a hello/LaserSlab_ChCenter QC/LaserSlab_ChCenter`，或让本地生成使用
   `FLASH_SIM_USER_DIR=hello` 并接受一次编译。
5. **超算提交类操作超时 ≠ 未提交**：`sbatch` 前有 40–60 s 的 `module load`，
   场景已放宽到 180 s 并回查队列（`slurm_control.latest_job_by_name`）。
6. **chk-only 回传**：plt 不回传（`fetch_policy` 统一策略）；本地分析本就优先 chk。
   驱动在每轮结束后按同一策略清理 collect 目录里的 plt。
7. **绘图规范**：全部英文标注、Times New Roman、≥18pt（`plot_style.py` 强制）。
8. **paramiko SFTP 两坑**（2026-10-24 实测，上传 0/18 全败）：① `~` **不展开**
   —— `sftp.put("~/QC/...")` 会落进主目录下字面名为 `~` 的垃圾目录，
   `_paramiko_put` 现已对 `~/` 开头路径经同一连接 exec 探 $HOME 展开；
   ② **尾斜杠** —— `upload(local, "{dir}/")` 让 `sftp.put` 报
   `OSError: Failure`，现已归一（剥斜杠 + 目录意图补 basename）。
   场景侧 `remote_dir` 也改为先 `printf $HOME` 解析成绝对路径。
9. **超算跑已预置二进制必须走 module 路径**：`module purge + load
   mpich/3.2-gcc9.3 + hdf5/1.8.18` 提供 `libhdf5.so.10`/`libgfortran.so.5`
   （计算节点 ambient 环境**没有**，诊断作业 7 种 LD_LIBRARY_PATH 组合全部
   `libhdf5.so.10: cannot open`）；mpich 的 soname 是 `libmpi.so`（无 .12
   后缀），不冲突二进制链接的 Intel `libmpi.so.12`。`FLASH_NO_MODULE_PURGE=1`
   只适用于 objdir **需重新编译**的场景（保 oneAPI 链接栈）。
10. **Intel MPI 库路径笔误**：`libmpifort.so.12` 只在 `mpi/latest/lib/`，且
    `MPII_F_TRUE` 是**导入**符号，须由 `mpi/latest/lib/release/libmpi.so.12`
    提供（R 已定义）；注入写成不存在的 `mpi/latest/release` 会让计算节点
    加载其它副本（intelpython 内置精简 MPI）⇒ `undefined symbol: MPII_F_TRUE`
    ⇒ SIGSEGV(174)。已改为 `lib/release:lib` 顺序。
11. **insitu 收集三坑**（2026-10-24 修复，之前静默收集 0 文件）：
    ① `select_fetch_files(basenm="")` 的 prefix 过滤只放行 `wsl_run_`，
    全部 chk 被滤掉 —— basenm 改从 .par 解析（`basenm = "lasslab_"`）；
    ② `ls -d outputfiles_* | head -1` 取**最旧**目录（insitu 的 flash_input
    多轮复用），改 `sort | tail -1` 取最新；
    ③ 分析脚本不在 flash_input/（insitu 无上传步骤），先 `shutil.copy2`
    拷入再跑。成功判据同时承认 `FLASH_COLLECT_DIR` 里的产物。
12. **nohup 与自带 Tee 不得写同一文件**（两个独立偏移互相覆盖）：Tee 现接管
    `sys.stdout`，外层启动把 stdout 导向**另一个**文件（`nohup_stdout.log`）。
