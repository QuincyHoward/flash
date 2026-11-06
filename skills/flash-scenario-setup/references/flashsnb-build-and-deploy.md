# 参考: FLASHSNB 构建、编译报错速修与三机部署

> 本文件原为独立技能 ，2026-09-12 合并进 （两者职责重叠、触发词冲突）。
> **何时看这里**：编译不过、链接缺符号、泛型不匹配，或要把场景部署到 WSL / NC-E / BSCC 超算时。
> **何时看上一级 SKILL.md**：参数怎么填、结果怎么判、分享规则。

---


# SNB 专用 FLASH (FLASHSNB) 构建修复工作流

> **与 `snb-flash-scenario-setup` 的边界（两者有重叠，按此分工以免触发歧义）**
> * **本 skill** = **"怎么修 / 怎么部署"**：FLASHSNB 树级 6 补丁、编译报错速修
>   （泛型不匹配、模块名、缺 `.o`）、WSL/NC-E/BSCC 三机部署与 HPC 作业。
> * `snb-flash-scenario-setup` = **"怎么设"**：setup 标志、par 参数、`+ug`、dtmax 判据、
>   限流器/辐射开关、分享规则、场景生成/运行工作流、绘图与诊断纪律。
> * 走到"**参数怎么填**"或"**结果怎么判**"时，转 `snb-flash-scenario-setup`。

## 适用范围与红线
- SNB 模型尝试**必须在 FLASHSNB**（`~/QC/FLASH/FLASHSNB/FLASH4.8`）中编译运行，
  objdir 一律 `SNB_` 前缀；**不碰**常用场景 FLASH（`~/QC/FLASH/FLASH4.8`）。
- 常用 FLASH 的 `object/` 残留（官方接口 + flash4）只作官方组合参照，不直接使用。
- 身份信息不硬编码：路径用环境变量/占位描述，文档与脚本不出现固定用户名。

## 已确认基线（t001 首跑通过，2026-08-29）
场景：`SNB_1D_laser`（4 物种 cham/tar1/tar2/tar3，CH+He，激光 0.351µm，10 群 MGD）。
setup 行：
```
./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=SNB_1D_laser_obj
cd SNB_1D_laser_obj && make -j4 && mpiexec -n 4 ./flash4
```
首跑：exit 0，73 步到 `tmax=1.0e-11`，tele 290→9895K、dens 1e-6→1.04 均合理。

## 编译错误 → 修复对照表（按出现顺序）
| 报错 | 根因 | 修复 |
|---|---|---|
| `Zero is not a valid statement label`（场景 diff_advanceTherm.F90 377 行附近） | QENL 块缺 `&` 续行符 | `= -(` → `= -(&`，后续 4 行行尾补 ` &`；**文件含 GBK 注释必须用 Python 二进制模式改** |
| `unable to build mgd_qesh.o` | 场景缺 `mgd_qesh.F90`（Makefile 已声明） | 自常用 FLASH `source/Simulation/SimulationMain/SNB_1D_laser/` 复制，objdir 建符号链接 |
| `There is no specific subroutine for the generic 'conductivity'`（Diffuse_computeDt / hy_uhd_getFaceFlux） | FLASHSNB 为增强泛型接口（6参数旧版+标量fullState+anisoFullState）；标准调用方传数组(3) | **修调用方不修接口**：aniso 分支调 `Conductivity_anisoFullState`（数组），非 aniso 调标量版 |
| `Cannot open module file 'hy_uhd_slopelimiters.mod'`（场景 hy_uhd 文件） | 场景 use `hy_uhd_slopeLimiters`，标准名 `hy_slopeLimiters` | use 语句改 `hy_slopeLimiters` |
| `Driver_init: Must set runtime parameters iProcs...` | par 未设进程分解 | flash.par `iProcs = 4`（1D 4 进程） |
| 并行编译 `-j4` 报 use 模块 not found | 模块依赖竞态/旧 .mod | 先 `make 模块.o` 生成 .mod；旧 .mod 需 `rm -f` 强重编 |

## ★ 关键陷阱：anisoFullState 是 stub（返回 0）
FLASHSNB 的 `Conductivity_anisoFullState` 实现是 **stub**（`isochoricCond=0, diffCoeff=0`）。
任何调用方若无条件走 anisoFullState（如 unsplit `hy_uhd_getFaceFlux` 的 `cond_zone(3)` 数组调用），
编译能过但**热导恒置 0**，长时运行丢失热传导。正确做法（用户最终版）：
`call Conductivity(U(:,i,j,k), diffCoeff=cond_zone(1), component=2)`（标量 fullState，取真实 Spitzer 热导）。
`Diffuse_computeDt` 的 aniso 分支用 anisoFullState 是安全的（par 中 `diff_anisoCondFor*` 默认关闭）。
tmax=1e-11 极短验证下新旧版输出逐点一致（热输运可忽略），**正式算例必须用最终版**。

## src/SNB 源码核查要点（"第二种修改"）
用户提供的 `SNBtest/src/SNB/` 含多个版本并存：
- `f90/diff_advanceTherm.F90`（18KB）= **官方精简版**（无 multigp 群分辨/mgd_qesh），
  与场景完整版（43KB，含 SNB 群分辨逻辑）完全不同——**严禁混用**；
- `Diffuse_computeDt.F90` 用户版已做 aniso/标量分流（ion 用 `diffCoeff=diff_coeff_vec(1)`），与自改等价；
- `hy_uhd_slopeLimiters.F90` = `hy_slopeLimiters` 改名版；`Conductivity_interface.F90`（104行）与 FLASHSNB 同源；
- 其余 300+ physics 差异为 FLASH 版本噪声，不移植。

## 一键脚本 run_snb.py（t001）
- 流程：补丁同步(source_patches→FLASHSNB source/)→setup→make→mpiexec→输出收集→清理。
- 身份：`flash._core.credentials.get_user_name()`（专用函数）→ 环境变量 → `--user`，**不硬编码**。
- FLASHSNB 定位：`find "$HOME" -maxdepth 3 -type d -name FLASHSNB` 自动探测
  （勿用凭据 user_name 拼路径——凭据名与 WSL 目录名可能不一致）。

## 接口认知（关键）
- FLASH 4.8 **官方**接口：单一数组版 `Conductivity(solnVec, isochoricCond(3), diffCoeff(3), component)`。
- **FLASHSNB** 接口：增强泛型 `interface Conductivity`（6 参数旧版 + 标量 `Conductivity_fullState` +
  `Conductivity_aniso`）+ 独立 `Conductivity_anisoFullState`。SNB 场景代码（diff_advanceTherm）
  依赖增强泛型（`call Conductivity(xtemp,xdens,massfrac,κ,D,component=...)` 6 参数 +
  `Conductivity_anisoFullState`），所以接口保持不动。

## 运行与归档规范
- `+hdf5typeio` 输出**无 .h5 后缀**（`NonLTConduct_2D_hdf5_plt_cnt_0001` 等）。
- `+ug` uniform grid → par 中 `lrefine_*`/`refine_var_*` 被忽略属正常。
- 输出（plt/chk/dat/log）用后即转场景 `flash_output/`（如 `SNBtest/Test/tNNN/`），WSL 不占空间。
- 修改过的 FLASHSNB 源文件**同步归档**到场景 `source_patches/`（按 source/ 相对路径）。

## 工具提醒
- 改 Fortran 源用 Python 二进制模式（`open(path,"rb")` + `b"..."` 替换）。
  **禁止 perl `s/\s*$/.../`**（`\s` 含 `\n`，会吃掉换行损坏整个文件）。
- 最小复现泛型解析问题：单独写小 .F90 use 接口模块编译（含 `#include "Flash.h"`，`-I.`）。

## ★ SNBOneCH_ml 场景范式（2026-09-08，OneCH_ml 几何 + SNB 模型）
新 SNB 场景 = 在 FLASHSNB 建**新 SimulationMain 单元**：生成 5 件套
（Config[8 物种 + 18 个 SNB VARIABLE]/Makefile[`Simulation += Simulation_data.o
mgd_qesh.o`]/Simulation_data·init·initBlock.F90）+ 从 SNB_1D_laser **原样复制
9 个 SNB 覆盖文件**（diff_advanceTherm/mgd_qesh/Conductivity/Driver_evolveFlash/
Grid_advanceDiffusion/4×hy_uhd_*；与场景层解耦已核查，部署时复制不入库）。
物种/几何经 `import build_species_defs` 与 tracer 场景同源。setup 后置覆盖机制
自动替换 physics 同名文件。参照实现：`flash/scenarios/private/tracer/SNB/SNBOneCH_ml/`。

### SNB 场景三条实测铁律
1. **★★ SNB 模式必须 +ug 均匀网格（2026-09-08 用户铁律，旧结论作废）**：
   SNB 非局域热流跨平均自由程积分，AMR 粗细界面是破缺点。实证：t001(+ug) 与
   SNBOneCH(+ug, dx 0.98~7.8µm 四档) 全部稳定跑完 1e-10，SNBOneCH_ml(AMR lrefine9)
   稳定到 1e-11、1e-10 失稳。**勿再为分辨率切 AMR。**
   稳定化参数随之分家：+ug 用 t001 基线 tstep=1.10/dtmax=2e-12；AMR 细网格
   （历史）才需要 tstep=1.05/dtmax=2e-14。
   另：**覆盖文件权威来源 = WSL FLASHSNB SNB_1D_laser 工作副本（含 6 补丁）**；
   `SNBtest/src/...` 原始包源未打补丁（QENL 续行符缺失、`use hy_uhd_slopeLimiters`
   应为 `hy_slopeLimiters`），直接复制编译报 `hy_uhd_slopelimiters.mod` 缺失。

1b. **★ +ug 分辨率机制（2026-09-10 t002 实测修正 —— 旧说法"只能靠 iProcs"作废）**：
   源码 `Grid/GridMain/UG/Grid_init.F90:186-194`，UG 一块一进程 →
   `mpiexec -n` 必须严格 == `iProcs`。分辨率有**三条**独立路径：
   ① 固定块 `-nxb=N` → 总格数 = `iProcs × NXB`（**核数不变、加大 nxb 即可细化**）；
   ② 非固定块 `-nofbs` + par `iGridSize=M` → 总格数 = M，**与核数完全解耦**；
   ③ `iProcs` 本身（固定块模式下等价于分辨率旋钮）。
   ★ **坑**：只"不给 `-nxb`"**进不了**非固定块模式 —— FLASH 默认仍定义
   `FIXEDBLOCKSIZE` 且 `NXB=8`，`iGridSize` 被静默忽略（实测 iProcs=8→64 格）。
   必须显式 `-nofbs`（`bin/parseCmd.py:282`）；且 `not fixedBlockSize` 会强制
   并行 HDF5 IO，与 `+serialIO`/`parallelIO=False` 冲突（SETUPERROR）。
   实测（域 500 µm, tmax=2e-10）：nxb=64/ip8→512 格 12.5s；nxb=128/ip8→1024 格 54s；
   nxb=128/ip16→2048 格 164s；-nofbs iGridSize=1024 ip8→1024 格 56s；
   **同 iGridSize ip16→1024 格 47s（分辨率不变、逐位同解）**。分辨率×2 价 ≈ 4.3×。

1c. **★★ SNB 腿的 `diff_eleFlMode`/`diff_eleFlCoef` 对电子传导是死参数
   （2026-09-10 t002 实测）**：覆盖文件 `diff_advanceTherm.F90` 的
   `else`（各向同性）分支里 `call Diffuse_fluxLimiter(COND_VAR, ...)` 与
   `call Diffuse_solveScalar(Temptodiffuse,COND_VAR,...)` **均被 `!` 注释**；
   只有 `if (diff_anisoCondForEle)` 分支才调用限制器，而该开关必须 `.false.`
   （SNB 块只在 1D 均匀各向同性路径生效）。→ **FLASHSNB 构建恒为无界 Spitzer
   电导**。实测：改 `fl_none`→`fl_harmonic` 0.06，SNB 腿步数与结果**逐位相同**；
   FL-SH（标准树）同改则步数变化 → 限制器在标准树有效、在 SNB 树无效。
   后果（t002, 5e14 W/cm², 500µm, 1 ns）：质量 99.6→32.9（0.6ns）再回升到 92.3、
   内能/激光注入比达 **13.1**（0.2ns 已 4.6）→ 质量/能量双重不守恒；
   日志**无** negative/NaN/abort，单帧剖面看似正常 ——
   **必须用积分守恒量体检**（t002 `scripts/analysis/check_conservation.py`）。
   注意：短时（≤1e-10 s）运行不暴露，故 t001/SNBOneCH "稳定到 1e-10" 的说法
   只覆盖短时窗口，不能外推。
2. **启动瞬态稳定化（仅 AMR 细网格）**：细网格 + He|CH 6 量级密度跳变下
   dt×1.1/步 → hypre 500 iter 不收敛 → 温度超 EOS 表 Tmax(1e13K) → 负内能
   中止。AMR 场景须 `tstep_change_factor=1.05` + `dtmax≈2e-14`；+ug 不需要。
3. **wsl 双层 bash 展开**：`wsl bash -lc "<cmd>"` 先被外层 bash 展开 `$var/$?/
   $(...)`——循环变量为空、`$?` 恒 0。内联命令 Python 端全展开（显式 cp 链 +
   if/else 落盘 RUN_EXIT/MAKE_OK 标记）；make 判定**禁 grep error**（源文件名
   含 error 误报，flash4 实际已生成）。另两条 WSL 传输坑：par 全文（~15KB）
   heredoc 内嵌命令行超 WinError 206 32K 限制 → 本地落盘 + `cp /mnt/...`；
   输出目录先 `mkdir -p`。

## ★ HPC 超算执行（2026-09-08 双账号端到端跑通）
参照 `flash_demo` laserslab1d_hpc_demo_batch.py 的 sbatch+sacct 轮询流程；
一键脚本范式：`run_snb_hpc.py`（Remote→deploy_source→apply_makefile_h→build_remote
→run_remote→collect_outputs）。账号/分区映射：flash_ssh→v5_192、flash_ssh_2→v6_384。

### 部署与构建
- 超算无专用 FLASHSNB 树时：本地打包源码 tgz 上传（scp 替代超长 base64 单命令，
  BSCC 网关会丢包），解压到 `~/<sim_user>/FLASH/FLASHSNB/FLASH4.8`（sim_user 经
  `get_sim_user_dir()` 获取，不硬编码）。
- **Makefile.h 必须复制该账号常规树已验证版本**覆盖 FLASHSNB 顶层（objdir 内是软链）。
- 构建/运行均走 sbatch 作业；partition 探测要收 avail=up 分区 + 已知映射优先
  （sinfo 首行可能是 `all inact` 不可用分区，不能盲取首行）。

### HPC 环境铁律（多轮实测）
1. 登录自动加载 oneAPI（module 默认）→ **禁止 `module purge`**（会清掉 oneAPI，
   LD_LIBRARY_PATH 只剩 slurm lib）。
2. `module load` 在非交互/作业 shell 不更新环境变量（modulecmd 缺陷）→ 必须显式 `export`。
3. BSCC 的 mpif90 wrapper 按 PATH 选 gfortran：系统 4.8.5 编 hypre 源 ICE(segfault)，
   必须 prepend `/public1/soft/gcc/9.3.0-new/bin`（=module mpich/3.2-gcc9.3）+ LD
   加 gcc lib64 (libgfortran.so.5)。
4. **HYPRE_PATH 不可清空**：清空后 setup 仍编 hypre 源，-I 变 `-I/include` 缺
   HYPRE_config.h；保留常规树原值，hypre 崩溃交给 gcc 版本解决。
5. 运行期缺 libhdf5.so.10 → 作业内显式补 hdf5 lib 路径（NC-E oneAPI libmpi.so.12
   已由登录脚本解析）。
6. 作业脚本必须 LF：Windows `write_text` 默认 CRLF → 远端 bash 报错；一律
   `newline="\n"` 强制 LF（`cat -A` 可查 `^M$`）。
7. 构建/运行"完成但 marker 未确认"时先人工核验输出文件（`BUILD_OK` 在 out txt），
   勿急着回退重跑。

### 双账号结果对照（2026-09-08）
NC-E (scfa2696) 构建 jobID 4857085 + 运行 4857086 COMPLETED；BSCC (sch0348) 构建
36178794 (~2min) + 运行 36178818 COMPLETED。两超算 chk_0000=183988B、dat=15676B
与 WSL 本地逐字节一致（log 差异仅 MPI tasks stamp 之类 meta，非物理量）。

## ★ 多机核数探测 + 三机速度对比（2026-09-08 SNBOneCH_ml 跑通）

- 工作流：`--probe-cores 4,8,16,32 --probe-tmax 2e-12`（wsl/hpc 双路径，hpc 单 sbatch
  内循环各核数，`PROBE_WALL_N=<bc 实算秒>` 解析）→ `recommend_cores` → 正式跑
  `--tmax X --nproc N --skip-build`。实测推荐：WSL 4 核、NC-E 8 核、BSCC 16 核。
- 结果：tmax=1e-11 三机墙钟 WSL(4c) 39.8s < NC-E(8c) 59.9s < BSCC(16c) 84.3s；
  一致性主体 median≤1e-6（偏差集中界面尖峰格点 = AMR 分块+编译器差异）。
- **tmax=1e-10 不可达**：负 3T 内能，t≈2.6~8.9e-11（随 MPI 分解漂移，cfl=0.1 无效，
  时间确定性物理失稳）——SNB+细网格临界稳定问题。
- **sbatch 输出路径**：`--output=~/{dir}/x` 不展开波浪号 → 输出落字面 `~` 目录、
  作业 marker 校验全空。一律用相对路径（相对 sbatch 提交目录）。
- **remote_ssh_helper 路由键**：凭据记录 route_key 为 "nc_e"/"bscc_t6"，裸比较
  =="scfa2696" 永不匹配 → flash_ssh 误路由 BSCC（同密码登录"成功"难察觉）。
  必须用 `RouteTester.routes_for_account(cred_name, cred)`；多账号操作串行 + whoami 核验。
- **BSCC v6_384 运行库**：LD_LIBRARY_PATH 必须补
  `/public1/soft/miniforge/24.11/lib`（libgfortran.so.5 唯一来源；
  gcc/9.3.0-new/lib64 只有 .so/.a/.la 无 .so.5）。

## ★ cn4 表温度网格陷阱 (2026-09-08 SNBOneCH_ml 实证)

- 室温冷启动场景的 cn4 表必须核对**温度网格下限**：CH-QC-1-001 下限 2.0 eV
  (~23,200 K)，290 K (0.025 eV) 完全在表外 → EOS 钳位、状态不一致；
  CH/He-BADGER-TOPS-Final 下限 0.01 eV 覆盖室温。两族均 10 群（组数一致可互换）。
- 换表不保证稳定：SNBOneCH_ml 换 BADGER 后启动瞬态更早发散（QC 钳位客观起阻尼）。
  冷启动 + 6 量级 He|CH 密度跳变 + 细网格的组合，先修启动（过渡区/初压平衡）再换表。
- 实验矩阵与结论详见 SNBOneCH_ml README §4.6；t001 粗网格 (dx≈9.4µm, dtmax=2e-12)
  @1e-10/2e-10 无负内能——粗网格天然平滑界面瞬态。

## ★★ chk vs plt 数据源选择 + chk 直读 (2026-09-10, t002 实证)

**定量分析 / 绘图一律用 chk, plt 只当快速健全性检查。**

| 维度 | chk | plt |
|---|---|---|
| 键数 (512 格实测) | **71** | ~25 |
| 变量上限 | 无 (完整重启快照) | `plot_var` 白名单硬上限 **12** |
| dtype | **float64** | float32 |
| 独有量 | pion/eele/ye/sumy/gamc/game/qenl/mfpe | — |

### chk 直读要点 (h5py, 约 40 行, 无需 yt / FlashDataLoader)

- ★ **chk 与 plt 的 HDF5 布局完全相同**。`+ug` 均匀网格下**所有块都是叶子块**
  —— `node type` 是**每块标量** (`(nblocks,)`, 恒 =1) → **无需 leaf 过滤**。
  ⚠ 这与 AMR 场景 (SNBOneCH_ml) 根本不同, 不可套用同一假设。
- 布局: `coordinates (nb,3)` = **块中心** (非节点坐标);
  变量 `(nb, 1, 1, nxb)`; `block size (nb,3)`; `bounding box (nb,3,2)`。
- **重建节点坐标**: `linspace(bbox[b,0,0], bbox[b,0,1], nxb+1)`, 拼接时
  **每块取左闭右开** (`[:-1]`) 以避免共享界面节点重复; 再 `+0.5*dx` 得格心。
- **块排序**: 按块中心 x 升序 (`argsort(coordinates[:,0])`), 与 gid 顺序等价。
- ★ **`unknown names` 是变量清单的权威来源** (勿 `grep '^VARIABLE'` 猜)。
- 时刻: `real scalars` 组内 `name`/`value` 配对读, 取 `time`。
- 帧号排序**必须按解析出的整数**, 不能直接 `sorted(str)`。
- 惰性读取: `load_frame(path, variables=[...])` 只读需要的键 (省 IO)。
- ★ `plot_var` 是**纯运行时参数** (`IO_init.F90:240`),
  改白名单**无需重新 setup/make** (前提: 目标 `*_VAR` 已在 objdir/Flash.h)。
- `nele` 不入白名单, 统一**离线推导** `Ye·6.02e23·dens`
  (`Ye = zbarFrac/abarInv`, `Eos_getAbarZbar.F90:130-152`) —— FL-SH 腿无 NELE_VAR,
  用原场会造成两腿口径不对称; SNB 原生 nele 与推导差 ~1% (含陈旧值)。
- chk 频率可当"时间分辨率旋钮": `checkpointFileIntervalTime=8e-11`
  → 1.2 ns 内 16 帧, 单帧 0.6 MB (512 格), 写盘开销 <1 s 可忽略。

### 绘图坑 (实测)

1. **`matplotlib.cm.get_cmap` 在 mpl ≥3.9 已移除** → 用 `plt.get_cmap(...)`。
2. **色标共享是双刃剑**: 两腿量值跨 >10 个数量级时共享色标会让弱腿全黑
   (实例: `trad` 的 FL-SH `erad~1e12` vs SNB `~1e-5` erg/cm³, **差 17 个数量级**)
   → 提供逐腿定标模式, 并在 panel title 标出该腿 `[min .. max]`;
   **逐腿版文件名必须与共享版区分**, 否则静默覆盖。
3. `imshow` 的 `extent` 必须显式给 `(x.min,x.max,t.min,t.max)` +
   `origin="lower"`, 否则 y 轴退化成帧号。
4. `suptitle` 与上联 `ax.set_title` 易重叠 → 实测可用组合:
   `top≈0.89` + `suptitle y≈0.955` + `hspace≈0.16`。

## ★ 相关 skill 与可分享文档集 (2026-09-11)

- **设置方法与分享规则** → skill `snb-flash-scenario-setup`（本 skill 侧重"构建修复"，
  那个侧重"如何设置 + 如何合规分享"）。
- **可分享文档集**（仓库内，10 个文件，已过分享安全检查）：
  `flash/scenarios/private/SNB/SNB/`
  - `README.md`：总览与分享规则速查
  - `docs/01_设置方法.md`：setup/par 全参数清单（几何·物种·激光·辐射·热传导·时间·输出）
  - `docs/02_端到端流程.md`：从零到出图（每步含判据）+ 耗时参考
  - `docs/03_编译与依赖.md`：编译前置、树级补丁性质、常见错误速查
  - `docs/04_辐射开关.md`：par 三开关 + SNB 侧"辐射被注释"陷阱 + 四腿实测
  - `docs/05_坑位清单.md`：22 条实测坑位（物理/网格/数据/平台）
  - `docs/06_分享与保密规则.md`：分享红线 + gitignore 机制 + 历史泄漏处置
  - `scripts/check_share_safety.py`：**提交前强制自检**（类型闸门 + 内容闸门）
  - `scripts/snb_params.py`：参数速查 / par 关键设置校验
- ★ **分享红线**：SNB 场景**不分享 F90 源码**，**不分享会生成/复制 F90 的 py 脚本**，
  **不分享逐字引用算法片段的文档**。提交前务必跑 `check_share_safety.py`。
