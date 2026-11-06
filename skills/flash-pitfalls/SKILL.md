---
name: flash-pitfalls
description: FLASH 报错→根因→修复速查库：编译期错误、运行期 abort、物理失真（崩塌/不守恒/辐射不生效）、静默失败。遇到报错信息或异常症状时先查此库。触发词：FLASH 报错、abort、DRIVER_ABORT、bad size、undefined symbol、Negative、崩塌、不守恒、静默失败。
---

> 最后核对：2026-11-06 · commit 72f6428
> 上游：FLASH-Expert @ 25013c5（flash-pitfall-finder 19 条实战报错库）
> 本仓条目来源：flash-scenario-setup / flash-scenario-family（条目只列要点，全文走对应 skill，避免漂移）

# FLASH 报错速查库（报错/症状 → 根因 → 修法）

检索建议：用报错原文关键词（routine 名 / 引号内短语）直接 Ctrl-F，或按表内"症状"列扫读。
来源标注：`[上游]` = FLASH-Expert pitfall-finder 实战库；`[本仓]` = flash-sim 工程铁律（详见对应 skill）。

## A. 编译 / setup / 链接期

| 报错/症状 | 根因 | 修法/指引 |
|---|---|---|
| `undefined reference to '__simulation_data_MOD_*'` / `eos_initphysdata_`，但 `nm xxx.o` 能看到符号 [上游] | setup 生成的 Makefile.\<Unit\> 漏对象文件：漏 setup 选项（如缺 `+mtmmmt` 整个变体没进链接）或 Makefile.Simulation bug 漏 `Simulation_data.o` | `make -n` 对比已知好 case 的链接列表；`grep xxx.o Makefile.\<Unit\>` 确认缺项 → 补 setup 选项重 setup，或手动补一行 `Unit += xxx.o` |
| `SetupError: Unit not found` / `Unit ... is ambiguous` [上游] | 拼写/大小写错，或 SimulationMain 下多前缀匹配歧义 | `ls source/Simulation/SimulationMain/ \| grep -i <名>`；用完整唯一名 |
| `SetupError: No site file found for host '<host>'` [上游] | `sites/<hostname>/Makefile.h` 缺失或残缺 | 从已跑通的 case 拷 Makefile.h 建 `sites/<host>/`；检查 MPI_PATH/HDF5_PATH 变量齐全 |
| `ld: warning: libmpi.so.40 may conflict with libmpi.so.12` [上游·本机特定] | 系统 OpenMPI 与用户自建 mpich ABI 不共（HYPRE 链 mpich） | 链接期仅 warning 可忽略；运行期保证 LD_LIBRARY_PATH 指向 mpich；详查上游 libmpi-conflict 条目 |
| `Cannot open module file 'xxx.mod'` [本仓] | 覆盖 F90 的模块名与树内不一致，或依赖模块未先编译 | 核对覆盖文件 module 名；make 顺序（详见 flash-scenario-setup） |

## B. 运行期 abort（启动 / 早崩）

| 报错/症状 | 根因 | 修法/指引 |
|---|---|---|
| `DRIVER_ABORT: [hy_uhd_unsplitUpdateMultiTemp] Negative 3T internal energy`（首步~第3步）[上游] | 3T+MGD + 极高密度对比（≥1e3）+ 辐射浴瞬时启动 → HLLC 在陡梯度界面通量过冲，advection 推负内能 | 降 CFL / 降 order / dtmax 钳位（本仓 `dtmax=2.0e-14` 量级）；辐射渐启；加 diffusive hydro 选项 |
| `DRIVER_ABORT: [Eos] too many iterations in Newton-Raphson`（multitemp/multitype）[上游] | 低密度+高内能+混合物质：EOS 表外推 + Abar/Zbar 界面跳变 | `eos_maxNewton=100`、`eos_tolerance=1e-6`、加 `smlrho/smalle` floor；缩小光斑避免直射界面；换覆盖更宽的表 |
| `[ed_setupBeams] Not enough beam runtime parameters` / `undefined reference to ed_wavelength_7` [上游] | parfile 束数超 setup 期 `ed_maxBeams`（默认 6）槽位 | setup 加 `ed_maxBeams=N` 重新 setup+make（runtime 改无效） |
| `no IONMIX file found: xxx.cn4` [上游+本仓] | parfile 引用的表未进 objdir：Config `DATAFILES` 漏声明，或场景模板 `tables` 复制清单漏该分支的表 | Config 加 `DATAFILES xxx.cn4`；或模板 tables 清单按 SHLD_MATERIAL/TI_LAYER 分支全覆盖；临时 `cp` 表到 case 目录 |
| `op_readIonmix4Tables: bad size of IONMIX4 energy group grid`（报错两数=表群数+par 群数）[本仓] | 全体物种 cn4 表能群数必须一致，且 == par `rt_mgdNumGroups` == setup `mgd_meshgroups` | 读表头第 4 行核对群数；统一 6 群或 10 群族约定；换配套 bounds |
| XrayImaging 六连环 abort：`No X-ray detector defined` → `2D cylindrical without 3D in 2D` → `energy level count must be > 0` → `energy must be >= 10 eV` … [上游] | xray_* 参数链逐个缺失；能级参数名是 `xray_detectorEnergy_\<det\>_Level_\<level\>`（不是 detectorEnergyXrays） | 按序补 `xray_numberOfDetectors`、`xray_3Din2D=.true.`、`xray_detectorEnergyLevelCount_1`、`xray_detectorEnergy_1_Level_1/Fraction_1`；详见上游 xray-imaging-setup 条目 |
| `double free or corruption` → SIGABRT（XrayImaging side-on、演化态）[上游·已修复 2026-08-13] | gr_findNeghID NONEXISTENT 分支：level-1 无父块 / 父块不在本进程缓存 → 未初始化索引越界 → 堆损坏 | 源码补丁已入树（gr_findNeghID 双保险）；face-on 不触发，side-on 演化态（≥6 ns）必现；升级后再跑 |
| `Invalid communicator ... MPI_COMM_NULL`（ROMIO Allreduce，长跑后期）[上游] | MPI-IO 集合写高频施压后内部通信子失效（2 rank 同时同错） | 可 restart 续跑；降低 plotfile 写频（见 D 表"每步一个 plotfile"）；详查上游 mpi-romio-null-comm-allreduce 条目 |
| MPI 死锁（CPU 0% 挂起）/ `MPI_Recv: message truncated` [上游] | rank 分支不对称（仅 MASTER 内通信）、消息大小不匹配；或 FLASH 自己的 abort 经 MPI_ABORT 呈现 | 先看 abort 信息 `[routine]` 前缀定位真正单元；再查 MPI 分支对称性 |
| `flash4` exit=1 且秒退 [本仓] | objdir 内 flash4 缺失或 flash.par 0 字节（编译/复制被中断） | 检查 objdir（FLASH 树内 LaserSlab_* 目录）flash4 存在 + par 非 0 字节；单独重跑恢复；`python -m flash.scenarios.core.runner --check-env` |
| restart 后 `Restart requested but checkpoint not found` / 版本不匹配 / NXB 不一致 [上游] | setup 变了（NXB/物种/物理单元/几何）或版本不同 | restart 与原 run 的 setup 必须逐项一致；`io_checkBlockShape.F90:L39-L41` 强校验 NXB/NYB/NZB |

## C. 物理失真（不 abort 但结果错）

| 报错/症状 | 根因 | 修法/指引 |
|---|---|---|
| ρmax 崩塌、质量守恒破裂（SNB 腿）★★ [本仓] | FLASH 默认 `gr_hypreUseFloor=.true.` → HYPRE 隐式扩散 floor 失真，dtmax 正确也照样崩 | **par 显式写 `gr_hypreUseFloor = .false.`**（SNB 五铁律之首，见 flash-scenario-setup §1） |
| dt 增长越过 ~4.6e-14 后失稳 [本仓] | dtmax 未钳位 | `dtmax = 2.0e-14`；**判据看 chk 的 real scalars 实测 dt**（par 文本会被 sed 覆写），不看 par |
| `trad` 冻结在初值（如 0.04 eV，对照腿 60+ eV）★★ [本仓] | SNB 腿 Driver 的辐射调用被注释——par 三开关设 .true. 也不涨 | 换 radON 变体 Driver（恢复辐射调用的驱动）+ par 三开关（rt_useMGD/useOpacity/useRadTrans）显式写回 |
| `diff_eleFlMode="fl_harmonic"` 不生效 [本仓] | SNB 路径各向同性分支限流调用被注释，实测 no-op | 仅作意图声明保留；勿指望它改结果；`fl_none` 逐位相同不破坏守恒 |
| 两腿 x-t 图"前沿速度不同"★★ [本仓] | 绘制 bug：imshow 假设等间隔帧（实测 Δt 差 52.7×） | **必须 pcolormesh + 真实逐帧时间坐标，禁 imshow** |
| TELE/TEION 不趋同、能量不交换 [上游] | `useHeatexchange` 默认 .false.；或没用 3T EOS（REQUIRES multiTemp）；或 DRIVER_EDEARLY 顺序错 | par 开 useHeatexchange；确认 +uhd3t/+mtmmmt；查 Driver_sourceTerms 顺序 |
| 激光沉积能量比预期少 30% [上游] | pulse 时段不覆盖 simTime / target 椭圆小 / grid 边界丢 ray / 临界密度反射 / 单位错 | 按 flash-laser pitfalls §C.1 五步诊断 |
| 数值 NaN / `forrtl: error (65): floating invalid` / ffpe-trap [上游] | 除零（gaussianRadius=0 等）/ 函数发散 / CFL 违反 / EOS 表外推 / 初值非物理 | 用 debug 构建复现定位行号；先查参数除零，再降 CFL，再查表范围 |
| MGD 辐射能量爆炸 / NaN [上游] | `rt_mgdFlMode` 默认 fl_none（光学薄超光速）/ 群边界未设（默认 -1）/ 表与群数不匹配 / BC 选错 | 用 fl_harmonic；显式设 N+1 个 rt_mgdBounds（eV）；表群结构与 mgd_meshgroups 对齐 |
| plotfile 帧间物理量跳变但无法解释 [本仓] | 结果差异出现在第 1 帧 → 查初始/求解器配置，不往数值累积想 | 启动日志参数回显差分（~前 1400 行可解析 1200+ 键）做配置溯源 |

## D. 静默失败（无报错，最具迷惑性）

| 报错/症状 | 根因 | 修法/指引 |
|---|---|---|
| `./flash4 -parfile=xxx.par` 跑的不是自己的参数 ★ [上游] | 唯一正确旗标是 **`-par_file X`**（下划线+空格）；`-parfile=X` 精确匹配失败静默回退默认 flash.par | 永远写 `./flash4 -par_file flash.par`；用 basenm 前缀核对实际读入 |
| plot_var 第 13 项起没输出 [本仓] | plot_var 白名单 **≤12 项且从 1 连续编号**，超限静默忽略 | 精选 12 项；改用 plot_grid_var 或分批输出 |
| plotfile 数量≈步数、磁盘暴涨 [上游] | `plotFileIntervalTime < dt`（语义是模拟时间间隔）→ 每步都触发 | 按物理分辨率设（如 0.1 ns）；IntervalTime ≥ 5×dt；总帧数控制在 100-500 |
| restart 续跑后 plotfile 从 0 重新编号、覆盖旧文件 [上游] | par 里 `plotFileNumber=0` 优先级高于 chk 内计数器 | restart 三件套：`restart=.true.` + `checkpointFileNumber=N` + `plotFileNumber=原序列末+1` |
| restart 后定时 plotfile 是 ~0.2 MB 空壳（只有 AMR 元数据，yt 报 KeyError: 'dens'），日志却显示 wrote 240 blocks [上游] | FLASH 4.8 + pm4dev + hdf5typeio 的 restart 写路径 bug，根因未定位 | 定时帧全废但 forced plotfile/checkpoint 正常；用 chk 或收尾帧替代；升级版本再验 |
| h5py 自算径向轮廓球边界偏大 ~20%（yt 是对的）[上游] | FLASH HDF5 cell 数组按 Fortran order 存，h5py 默认 C order 解释 → coord 与 dens 错位 | h5py 读后按 Fortran order 转置/展平，或直接用 yt（FlashDataLoader extraction_mode="yt"） |
| `RuntimeParameters_read: ignoring unknown parameter "ms_tar1A"...` [上游] | species 名 4 处不一致（setup 用 targ1 / parfile 写 tar1）；且 >4 字符名触发 HDF5 `name already exists` 冲突 | species 名**≤4 字符**且 setup/Flash.h/parfile/initBlock 四处逐字一致 |
| 分辨率改了没效果 [本仓] | +ug 忽略 nblockx/lrefine；非固定块需显式 `-nofbs`，只"不给 -nxb"进不去 | 显式 `-nofbs` + par `iGridSize=M`；或 `-nxb=N`（分辨率=iProcs×N） |
| 核数与 iProcs 不符 → 挂死 [本仓] | +ug 要求 `mpiexec -n` **严格等于** `iProcs` | 两者必须相等；核数伸缩非单调（131 核实测最快，256 ABORT），生产用验证过的核数 |
| 薄层（0.1 µm）里物种全空、相邻层贴爆 [本仓] | sim_smallX=1e-99 格心判据：dx>层厚则该层物种采样不到 | dx ≤ 层厚/3（0.1 µm 层 ⇒ dx ≤ 0.03 µm） |
| par 改了不生效（尤其 tmax/密度）[本仓] | **参数三副本**：模板 par、部署 par、运行时 par——FLASH 只认 objdir 内被 sed 改过的那份 | 读 chk 的 `real runtime parameters` 实测值核对，不读 par 文本；SCENE VARS 变更后 `rm -rf` flash_input/ 强制再生（tmax 再生守卫有 1e-12 容差消化 9.999…e-12 渲染） |
| 场景覆盖 F90 改动不生效（无报错）[本仓] | 覆盖 F90 没放 `<TREE>/source/Simulation/SimulationMain/<SimName>/`（放错位置静默不生效） | 看 objdir 软链接指向核实生效文件；部署单元走 sha256 指纹自检（详见 flash-scenario-setup） |
| 数值注入 2.329 变 2.33 [本仓] | f"{rho:.2f}" 舍入 | 注入用 `repr(rho)` |
| 物种 par 绑定没生效 [本仓] | 运行时覆写必须走 `par_gen.set(f"sim_rho{X}", ...)` / `eos_{X}TableFile` / `op_{X}FileName` 绑定链 | 核对 species_defs → Config PARAMETER → par_gen.set 链路（详见 flash-scenario-family §1） |
| WSL 下 HDF5 分析误判 FAIL [本仓] | Windows "页面文件太小"（WinError 1455）内存分配失败，FLASH 本体正常 | 错峰重跑即可 |

## E. 元纪律（[本仓] flash-scenario-setup §8 五类结构性根因）

- **M1** 穷尽哈希比对再解释（中文路径用 `git ls-files -z`）；**M2** 单变量 A/B（一次只改一键）；**M3** 读实测值（chk 的 real scalars / runtime parameters），不读文本。
- 结构性根因占比：两层目录职责重叠 ~35% / 参数三副本 ~25% / +ug 隐式约束 ~20% / 静默失败 ~15% / 平台差异 ~5%。
