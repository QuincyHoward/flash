# t001 — SNB 模型首次跑通（tmax=1e-11 快速验证）

> 日期：2026-08-29
> 目标：在 **SNB 专用 FLASH 代码**（`FLASHSNB/FLASH4.8`，与常用场景 FLASH 严格隔离）中，
> 以极短时间 `tmax = 1.0e-11 s` 将 SNB（Schurtz–Nicolaï–Busquet 非局域热传导）模型**编译并跑通**，
> 产出初始/最终 plotfile + checkpoint，物理量合理。
> 本目录保存本次尝试的全部代码补丁、输入参数与输出文件。

---

## 1. 本次结果（验证判读清单）

| 项目 | 结果 |
|---|---|
| 编译 | ✅ `flash4` 生成（12.3 MB，无 error） |
| 运行 | ✅ `mpiexec -n 4 ./flash4` exit 0 |
| 步进 | 73 步到达 `tmax = 1.0e-11`，日志 "exiting: reached max SimTime" |
| 输出 | 初始 plt + 最终 plt + forced plt + chk_0000/0001 全部生成 |
| 物理量 | tele 290→9895 K（激光刚启动合理）、dens 1e-6→1.04 g/cm³、SH 热流 qesx ±5e11、SNB 变量 corq/grqx/mfpe 非零、4 个叶子块 |

**Setup 命令行**（SNB 专用 FLASH 内执行）：
```
./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=SNB_1D_laser_obj
cd SNB_1D_laser_obj && make -j4 && mpiexec -n 4 ./flash4
```

## 2. 目录结构

```
t001/
├── README.md                      # 本文件（修正记录 + 运行方法 + HPC 执行）
├── run_snb.py                     # 一键仿真脚本（补丁同步→setup→make→运行→收集, WSL）
├── run_snb_hpc.py                 # HPC 一键执行脚本（上传→编译→运行→收集, 双账号）
├── probe_hpc_env.py / probe2_hpc_env.py / probe3_sbatch_smoke.py / probe4_bscc_smoke.py
│                                  # HPC 环境探测/作业冒烟（诊断用）
├── 首次SNB代码微调说明.md          # 代码修改原因/风险/物理影响 + src/SNB 核查
├── flash_input/
│   └── flash.par                  # 运行用 par（含 iProcs=4；tmax=1.0e-11 已内置）
├── flash_output/                  # 全部输出（已从 WSL 转移，WSL 不占空间）
│   ├── NonLTConduct.log           # FLASH 主日志
│   ├── wsl_run_snb.log            # 控制台日志（含 73 步推进）
│   ├── NonLTConduct_2D.dat
│   ├── NonLTConduct_2D_LaserEnergyProfile.dat
│   ├── NonLTConduct_2D_hdf5_plt_cnt_0000   # 初始 plotfile
│   ├── NonLTConduct_2D_hdf5_plt_cnt_0001   # tmax 时刻 plotfile
│   ├── NonLTConduct_2D_forced_hdf5_plt_cnt_0000  # forced plotfile
│   ├── NonLTConduct_2D_hdf5_chk_0000 / _0001     # checkpoint
│   └── hpc_flash_ssh/             # NC-E (scfa2696) 远程输出（与本地逐字节一致）
├── hpc_pack/
│   ├── flashsnb_f4.tgz            # WSL FLASHSNB 源码树打包 (58.5MB, 不入库)
│   └── Makefile.h.hpc             # HPC Makefile.h 参考（实际用各账号常规树覆盖）
└── source_patches/                # 本次修改/补齐的 FLASHSNB 源文件（含场景与 physics 单元）
    ├── SimulationMain/SNB_1D_laser/   # 场景代码（diff_advanceTherm/mgd_qesh/hy_uhd_*）
    └── physics/                       # FLASH 标准单元补丁（Diffuse_computeDt/hy_uhd_getFaceFlux）
```

## 3. 编译问题与修正记录（根因 → 修正）

> 所有修改均在 **SNB 专用 FLASH 代码**（FLASHSNB）内完成，不触碰常用场景 FLASH。
> 每个文件同时归档于 `source_patches/` 对应路径，可直接对照覆盖。

### 3.1 场景 `diff_advanceTherm.F90` — 续行符缺失（语法错）
- **报错**：`Error: Zero is not a valid statement label` @ 377 行（QENL 热流散度中心差分块）
- **根因**：QENL 块第 376–380 行**缺 `&` 续行符**（`= -(` 后未续行），后续行被当作新语句解析。
- **修正**：`= -(` → `= -(&`，后续 4 行行尾补 ` &`。
- **注意**：该文件含 GBK 中文注释，**必须用二进制模式修改**（UTF-8 模式会解码失败）。

### 3.2 场景 `mgd_qesh.F90` — 文件缺失（编译失败）
- **报错**：`make: *** [Makefile:165: mgd_qesh.o] Error 1`（找不到源文件）
- **根因**：场景 `Makefile` 声明 `Simulation += ... mgd_qesh.o`，但 FLASHSNB 场景目录**缺 `mgd_qesh.F90`**；
  该文件存在于常用 FLASH 的 SNB_1D_laser 场景（两库场景文件 diff 仅此一项差异）。
- **修正**：从常用 FLASH 复制 `mgd_qesh.F90` 到 FLASHSNB 场景目录，objdir 建符号链接后编译通过。
- **函数语义**：计算多群 SH 热流权重 `fra = [P(4,x0) - P(4,x1)]/24`（不完全伽马积分），
  被 `diff_advanceTherm` 在 QEXG/GRGX/GRQG 群分辨热流计算中调用。

### 3.3 标准单元 `Diffuse_computeDt.F90` — Conductivity 泛型数组/标量版本冲突
- **报错**：`There is no specific subroutine for the generic 'conductivity'`
- **根因**：FLASHSNB 的 `Conductivity_interface` 是"增强泛型"（`Conductivity` 6 参数旧版 +
  `Conductivity_fullState` 标量版 + `Conductivity_anisoFullState` 数组版），
  而 `Diffuse_computeDt` 无条件用数组 `diff_coeff_vec(3)` 调 `Conductivity` → 泛型无匹配。
- **修正**（最小侵入，不动接口）：按 aniso 分支分流——
  `diff_anisoCondForEle/Ion=.true.` 时调 `Conductivity_anisoFullState`（数组版），
  否则调标量版 `Conductivity(diffCoeff=标量)`；ion 分支新增 `diff_coeff_ion` 局部变量。

### 3.4 标准单元 `hy_uhd_getFaceFlux.F90`（unsplit）— ★含一次自我修正
- **根因**：`call Conductivity(U(:,i,j,k), cond_zone, component=2)`，`cond_zone(3)` 数组 → 标量版 fullState 不匹配。
- **初版（错误）**：改 `Conductivity_anisoFullState` —— 编译通过但该过程是 **stub（返回 0）**，热导会被置零。
- **最终版（正确，与用户源码语义一致）**：改标量调用
  `call Conductivity(U(:,i,j,k), diffCoeff=cond_zone(1), component=2)` + `cond(i,j,k)=cond_zone(1)`，
  取真实 Spitzer 热导。tmax=1e-11 下新旧版输出逐点一致（maxΔ=0），但**长时算例必须用最终版**。

### 3.5 场景 `hy_uhd_DataReconstructNormalDir_PPM.F90` / `hy_uhd_getRiemannState.F90` — 模块名不匹配
- **报错**：`Cannot open module file 'hy_uhd_slopelimiters.mod'`
- **根因**：场景代码 use `hy_uhd_slopeLimiters`，FLASHSNB 提供的标准模块名是 `hy_slopeLimiters`（HydroMain 根目录）。
- **修正**：两文件 use 语句 `hy_uhd_slopeLimiters` → `hy_slopeLimiters`（符号 minmod/mc 不变）。

### 3.6 运行期修正 — `iProcs`
- **报错**：`Driver_init: Must set runtime parameters iProcs, jProcs, kProcs...`
- **修正**：flash.par 中 `#iProcs = 8` → `iProcs = 4`（1D 时 4 进程沿 x 分解，jProcs/kProcs 默认 1）。

## 4. 关键经验（后续 SNB 调试注意）

1. **并行编译竞态**：`-j4` 下 `use` 模块可能未先编译（diff_advanceTherm 首报 anisoFullState not found、
   PPM 报 slopelimiter mod 缺失）。处置：先单独 `make 模块.o` 生成 `.mod` 再全量 make；若 `.mod` 为旧版，
   `rm -f *.o 对应 .mod` 强制重编。
2. **FLASH 4.8 的 Conductivity 接口有两套并存**：官方 `object/` 残留显示官方为单一数组版
   `Conductivity(solnVec,isochoricCond(3),diffCoeff(3),component)`；FLASHSNB 为增强泛型（6 参数旧版 +
   标量 fullState + anisoFullState）。**场景 SNB 代码依赖增强泛型**（6 参数调用 + anisoFullState），
   因此修调用方而非接口。
3. **输出文件无 `.h5` 后缀**（`+hdf5typeio` 模式，如 `NonLTConduct_2D_hdf5_plt_cnt_0001`）。
4. 本场景 `+ug`（uniform grid）→ par 中 `lrefine_*`/`refine_var_*` 被忽略属正常。
5. **tmax 极短**：`plotFileIntervalTime = 1e-11` 与 tmax 相同 → 仅初始 + 结束共 2 帧 plt（符合预期）。

## 5. 下一步（P2 之后）

- 按 SNBtest 计划书进入正式算例：恢复规范 tmax、域 750 µm 均匀 lrefine 6、`fl_harmonic 0.06`、
  19 个 SNB 诊断变量、local(SH) vs nonlocal(SNB) 对比。
- 本 t001 的 6 个补丁文件为后续 SNB 场景的**基线**，新场景基于它们迭代。
- **一键运行**：`python run_snb.py`（补丁同步→setup→make→运行→输出收集全流程；
  常用 `--skip-setup --skip-make` 复用现有编译；`--tmax 1e-10` 覆写时长；
  身份通过专用函数获取、FLASHSNB 自动探测，不硬编码）。
- **代码微调说明**：`首次SNB代码微调说明.md`（含修改原因/风险/物理影响 + src/SNB 源码"第二种修改"核查结果）。

## 6. HPC 超算执行（tmax=1e-11, 双账号端到端通过）

> 流程与代码参考 `flash_demo/demo_hpc/`（RemoteSession 动态路由 + sbatch + sacct 轮询 + SCP）。
> 身份/用户目录一律走凭据系统，不硬编码。

### 6.1 一键命令
```
python run_snb_hpc.py --account flash_ssh    # scfa2696 @ NC-E    (分区 v5_192)
python run_snb_hpc.py --account flash_ssh_2  # sch0348 @ BSCC-T6  (分区 v6_384)
python run_snb_hpc.py --skip-upload          # 复用远端已部署 FLASHSNB 树
python run_snb_hpc.py --skip-build           # 复用远端已编译 flash4
```
流程：上传 WSL 打包的 `hpc_pack/flashsnb_f4.tgz`（58.5MB, ~30s）→ 解压到
`~/<user>/FLASH/FLASHSNB/FLASH4.8` → **复制该账号常规树已验证的 `Makefile.h`** →
sbatch 作业内 setup + make → 上传 par（覆写 tmax）→ sbatch 运行 → 下载
`NonLTConduct*` 到 `flash_output/hpc_<account>/`（远端 objdir 输出随即清理）。

### 6.2 账号结果（2026-09-07/08）

| 账号 | 分区 | 工具链 (常规树 Makefile.h) | 编译 | 运行 | 输出一致 |
|---|---|---|---|---|---|
| flash_ssh (NC-E) | v5_192 | oneAPI 2021.5 `mpiifort` (-r8) | ✅ BUILD_OK (~44s) | ✅ reached max SimTime, RUN_EXIT=0 | chk_0000 183988B / dat 15676B 与 WSL 本地**逐字节一致** |
| flash_ssh_2 (BSCC-T6) | v6_384 | mpich/3.2 `mpif90` + **gcc/9.3.0-new** (-fdefault-real-8) | ✅ BUILD_OK (~2min) | ✅ reached max SimTime, RUN_EXIT=0 | chk_0000 183988B / dat 15676B 与本地**逐字节一致** |

### 6.3 ⚠️ 超算环境铁律（probe2/3/4 实测 + 多次构建排错, 已内嵌 run_snb_hpc.py）
1. **禁止 `module purge`**：登录环境（NC-E=oneAPI）由 module 系统自动加载，purge 会连
   oneAPI 一起清掉 → 作业内只补库不 purge。
2. **`module load` 在非交互/作业 shell 不更新环境变量**（modulecmd 缺陷）→ 一律在作业
   脚本内**显式 export PATH/LD_LIBRARY_PATH**：
   - NC-E：oneAPI mpi 运行库登录已含，仅补 hdf5 lib（从 Makefile.h 提取 `HDF5_PATH`）。
   - BSCC：`mpif90` wrapper 按 PATH 选 gfortran → **必须 prepend gcc/9.3.0-new/bin**
     （系统 gfortran 4.8.5 编 hypre 源 `gr_uhypreParamesh.F90` 会 ICE/segfault）；
     LD 追加 gcc/9.3.0-new/lib64 + hdf5 lib + mpich/3.2/lib（运行需 libgfortran.so.5）。
3. **`HYPRE_PATH` 不可清空**：清空后 setup 仍编 hypre 源但 `-I${HYPRE_PATH}/include`
   退化为 `-I/include` → 缺 `HYPRE_config.h`。保留常规树原值（home hypre 已在编译
   机存在），hypre 源编译崩溃交给 gcc 版本解决（见上）。
4. **作业脚本必须 LF**：Windows `write_text` 默认转 CRLF，远端 `bash -n` 报
   "unexpected end of file" → 写脚本强制 `newline="\n"`（scp 上传方式替代超长 base64
   单命令，后者在 BSCC 网关不可靠）。
5. **分区探测**：`sinfo -s` 首行可能是不可用分区（NC-E 首行 `all inact`）→
   取 avail=up 分区且已知映射（v5_192/v6_384）优先。

### 6.4 flash_demo 本地参照（非 SNB 常规 demo, tmax=1e-11 通过）
WSL 常规树 `object/flash4` = 官方 LaserSlab demo（`-auto LaserSlab -1d +cartesian
-nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd`）。
复制 `run_laserslab/` 为 `run_laserslab_t1e11/`、sed `tmax 1e-9→1e-11` 后运行：
`RUN_EXIT=0` + "reached max SimTime"，产出 chk_0000–0004 + forced plt（WSL 保留）。
