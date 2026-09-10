# t002 设计文档 —— SNB 与 FL-SH 两腿逐项对照 + SNB 侧可调项清单

> 场景：`flash/scenarios/private/SNB/SNBtest/Test/t002/`
> 参照：`SNB/SNBtest/Test/t001`（SNB 基线）、`tracer/SNB/SNBOneCH`（+ug 最小两区）、
> `tracer/OneCH_ml`（FL-SH 限流参考）、`center_evolution/ch_center`（Z02+Z06_0.50 表对参考）

---

## 1. 物理场景定义

| 项 | 值 |
|---|---|
| 维度/几何 | 1D cartesian，`+uhd3t`（3T 电子/离子/辐射） |
| 域 | `x ∈ [-400, 100] µm` = `[-0.04, 0.01] cm` |
| 界面 | `x = 0`：`x < 0` 为 `cham`（稀薄 He 真空），`x ≥ 0` 为 `targ`（常温常压 CH） |
| cham | `Z02_1.00-20260708_0851.cn4`，`ρ = 1.0e-6 g/cm³`，A=4.002602，Z=2.0 |
| targ | `Z06_0.50-Z01_0.50-20260708_0850.cn4`，`ρ = 1.0`，A=6.5，Z=3.5，ZMin=0.02 |
| 初温 | 290.11375 K（tele = tion = trad） |
| EOS/不透明度 | `eos_tab` + `ionmix4`；`op_tabpa/tabpe/tabro`，`useOpacity=.true.` |
| 辐射 MGD | `rt_useMGD=.true.`，**6 群**，边界 `0.1/1/10/100/1e3/1e4/1e5`，`fl_harmonic`，coef 1.0，六面 vacuum |
| 激光 | 1 束，`351 nm`，`ed_lensX_1=-1.0`，`ed_targetX_1=0.0`，`uniform` 截面，1 条光线，`regular1D`，512 radial tics，从左侧入射 |
| 脉冲 | 4 段梯形波：`P=0 @ t=0` → `5e14 W/cm² @ 50 ps` → `5e14 @ 1.05 ns` → `0 @ 1.10 ns`（平台 1.0 ns） |
| 边界 | `xl/xr/yl/yr/zl/zr = outflow`；`diff_eleX*/Y*/Z* = neumann` |
| 时间积分 | `tstep_change_factor=1.10`，`cfl=0.2`，`dtinit=1e-15`，`dtmin=1e-16`，`dtmax=2.0e-12` |
| 输出 | `plotFileIntervalTime=5e-11`，`checkpointFileIntervalTime=5.0e-10`（step 触发已注释关闭） |
| 网格 | `+ug`，`-nxb=64`，`iProcs=8` → **512 格**，`dx = 500/(8×64) = 0.9766 µm` |

---

## 2. 两腿唯一差异

SNB 非局域热流在本仓库的实现中**没有 par 开关**（`diff_advanceTherm.F90` 的
`if(NDIM==1)` 分支内在 `diff_useEleCond=.true.` 时**无条件**执行），
因此 FL-SH 腿必须在**标准 FLASH 树**中单独构建。

| 项 | FL-SH 腿 (`sim_flsh/`) | SNB 腿 (`sim_snb/`) |
|---|---|---|
| FLASH 树 | `~/QC/FLASH/FLASH4.8`（标准） | `~/QC/FLASH/FLASHSNB/FLASH4.8` |
| 单元名 / objdir | `T002_FLSH` / `T002_FLSH_obj` | `T002_SNB` / `T002_SNB_obj` |
| `basenm` / `log_file` / par | `t002flsh_` / `t002flsh.log` / `t002flsh.par` | `t002snb_` / `t002snb.log` / `t002snb.par` |
| **`diff_eleFlMode`** | **`fl_minmax`**（coef 0.06） | **`fl_none`** |
| 非局域 SNB 修正项 | 无 | 有（`CORQ → TELE`） |
| Config | 生成器默认 | +18 个 SNB 诊断 `VARIABLE` |
| Makefile | 生成器默认 | `Simulation += Simulation_data.o mgd_qesh.o` |
| 覆盖 F90 | 无 | 9 个（见 §3.2） |
| `plot_var` 白名单 | 9 项（`dens/tele/tion/trad/depo/cham/targ/cond/fllm`） | 12 项（+ `QESX/CORQ/MFPE`） |

其余参数**逐字节相同**（生成器写盘后自动做逐行 diff 自检，
差异仅限 `basenm`/`log_file`/`diff_eleFlMode`/`plot_var_*`）。

### 2.1 ⚠⚠ 差异归因纪律 + SNB 侧限流器**实际不起作用**（实测结论）

两腿同时差在两个因素上：① 限流模式；② SNB 非局域项。更严重的是，
**① 在 SNB 腿根本不可控** —— 见下。

#### 关键发现：FLASHSNB 构建里电子通量限制器被注释掉了

`flash_input/diff_advanceTherm.F90:836-841`：

```fortran
     else   ! Do isotropic conduction/diffusion
!        call Diffuse_fluxLimiter(COND_VAR, Temptodiffuse, FLLM_VAR, &
!             diff_eleFlMode, blockCount, blockList)          ← 被注释
        ...
!        call Diffuse_solveScalar(Temptodiffuse,COND_VAR, DFCF_VAR, ...)  ← 同样被注释
     end if
```

`if (diff_anisoCondForEle)` 分支才调用限制器，而 §3.2 已说明
`diff_anisoCondForEle` **必须 `.false.`** → 走 `else` 分支 → **限制器从不被调用**。

**实测证据**（同场景、同网格、同 tmax，仅改 par 的 `diff_eleFlMode`）：

| 腿 | `diff_eleFlMode` | 步数 | 末帧质量 | 末帧 intE/激光 | max tele |
|---|---|---|---|---|---|
| FL-SH | `fl_minmax` | 10656 | 94.258 | 0.437 | 2.15e7 K |
| FL-SH | `fl_harmonic` 0.06 | **10874** | 96.715 | 0.438 | 2.62e7 K |
| SNB | `fl_none` | 14751 | 92.331 | **13.115** | 6.76e7 K |
| SNB | `fl_harmonic` 0.06 | **14751**（逐位相同） | **92.331** | **13.115** | **6.76e7 K** |

→ FL-SH 腿改模式**有效**（步数/结果变化）；SNB 腿改模式**完全无效**（结果逐位相同）。

因此：

1. **SNB 腿恒为无界 Spitzer 电导**，`diff_eleFlMode`/`diff_eleFlCoef` 对电子传导是死参数
   （仅对离子传导与 `rt_mgdFlMode` 辐射仍有效）。
2. SNB 腿输出的 `fllm` **不是限制因子**，而是限制器调用前的原始量
   （实测 4.4e22 ~ 1.6e23），**不能**用作可分离性证据。
3. 两腿对比的真实差异 = 「SNB 非局域项」+「限流器有无」，且后者无法用 par 对齐。
   要对齐必须改 SNB 源码（放开 `COND_VAR` 的 `Diffuse_fluxLimiter` 调用），
   属于物理代码改动，需用户决策。

#### 后果：SNB 腿数值失效（质量/能量双重不守恒）

| 量（1 ns，5e14 W/cm²） | FL-SH | SNB | 判据 |
|---|---|---|---|
| 末帧总质量 [1e-4 g/cm²]（初始 99.610） | 96.715 | 92.331 | 中途 0.6 ns 跌到 **32.904** 再"恢复" → 质量被销毁又重建 |
| 末帧内能 / 激光注入能量（应 ≤ 1） | 0.438 | **13.115** | 0.2 ns 时已 4.62；超注入 13× |

→ **`fl_none` 与 `fl_harmonic` 两种设置下 SNB 腿都不收敛于物理结果**；
根因是无界 Spitzer 热流（消融面陡梯度处超自由流极限若干量级），
而非 `fl_none` 本身。`fl_none` 只是让这一点更直观。

**归档说明**：即使用户指定的 `fl_none` 在该构建上不生效，仍保留
`fl_none`（`full_1ns/`）与 `fl_harmonic 0.06`（`full_1ns_h006/`）两组归档，
作为"限制器在 SNB 腿惰性"这一结论的直接证据；两组的 SNB 腿逐位相同。


---

## 3. SNB 侧设置清单（回答"SNB 侧可以进行哪些设置"）

### 3.1 A 类 —— **必须与 FL-SH 腿对齐**（不可作为对比变量）

| # | 参数 | 取值 |
|---|---|---|
| 1 | `diff_eleFlMode` / `diff_eleFlCoef` | 本场景按要求设为 `fl_none` / 0.06 |
| 2 | 几何、激光脉冲、`+ug` 的 `nxb`/`iProcs`、EOS/不透明度表、辐射 MGD（群数/边界/限流器）、边界条件、时间步控制 | 见 §1，两腿逐字节一致 |

### 3.2 B 类 —— SNB 专属、**可经 par 调整**

| # | 参数 | 说明 / 本场景取值 |
|---|---|---|
| 3 | `diff_thetaImplct` | 群热流隐式求解权重（t001 = 1.0，本场景 1.0） |
| 4 | `useDiffuse` / `useConductivity` / `diff_useEleCond` | SNB 块入口门控，**三者须为 `.true.`** |
| 5 | `diff_anisoCondForEle` | **必须 `.false.`** —— SNB 块只在 1D 均匀各向同性路径生效 |
| 6 | `diff_eleXl/XrBoundaryType` | 电子热流边界类型（本场景 `neumann`） |
| 7 | `plot_var_N` 白名单 | 仅 FLASHSNB 构建存在的 18 个 SNB 诊断变量可选；**总数 ≤ 12**（见 §4 坑 1） |

### 3.3 C 类 —— SNB 专属、**只能改源码**（无 par 开关）

| # | 量 | 位置 |
|---|---|---|
| 8 | **SNB 能群数 `multigp = 20`** | `flash_input/diff_advanceTherm.F90:158`（局部硬编码）。**与 setup 的 `mgd_meshgroups=10` 无关** —— 后者只是辐射 MGD 的网格组数 |
| 9 | **SNB 群边界能量网格** `energy(m+1) = 0.1 keV × 10^((m-1)/3)` | 同上 `:346-349`，原文 `1e-1*exp(2.3026/3*(m-1))*1.6e-19/1.0e-7` erg |
| 10 | `mgd_qesh.F90` 群热流权重（不完全伽马积分比 `[P(4,x0)−P(4,x1)]/24`） | 场景单元文件 `mgd_qesh.F90` |
| 11 | SNB 非局域热流核（`MFPE`/`MFPR`、`lambda_g`、`CORQ→TELE` 反馈） | `diff_advanceTherm.F90:343-530` |
| 12 | **电子通量限制器调用被注释掉** → `diff_eleFlMode`/`diff_eleFlCoef` 对电子传导是**死参数**（SNB 腿恒为无界 Spitzer 电导） | `diff_advanceTherm.F90:836-841`（`else` 分支内两行均被 `!` 注释）；要启用须改源码 |

> ⚠ 第 12 条是最容易被误判的一条：从 par 看 SNB 腿"设了 `fl_harmonic`/`fl_minmax`"，
> 实际完全不生效。任何 SNB 场景（t001 / SNBOneCH / SNBOneCH_ml / 本场景）都受此影响，
> 且短时（≤1e-10 s）运行不会暴露 —— 需用**质量/能量守恒**这类积分量才能发现。


### 3.4 SNB 腿的 9 个覆盖 F90（FLASHSNB 专用）

`diff_advanceTherm.F90`（SNB 群分辨热流核心）、`mgd_qesh.F90`（群热流权重）、
`Conductivity.F90`（增强泛型）、`Driver_evolveFlash.F90`、`Grid_advanceDiffusion.F90`、
`hy_uhd_DataReconstructNormalDir_PPM.F90`、`hy_uhd_dataReconstOneStep.F90`、
`hy_uhd_getRiemannState.F90`、`hy_uhd_ragelike.F90`。

部署机制：FLASH setup 的 Simulation 单元**后置覆盖**同名单 physics 文件；
`mgd_qesh.o` 无同名 physics 文件，经单元 Makefile 显式加入。
权威副本取自 `tracer/SNB/SNBOneCH/flash_input`（与 WSL FLASHSNB 工作树同源，
含 t001 六补丁修复）；**`SNBtest/src/SNB/SNB_1D_laser` 原始包源未打补丁，不可直接用**。

树级 physics 补丁（幂等同步自 `t001/source_patches`）：
`physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90`、
`physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90`。

---

## 4. 已知坑位（实操记录）

1. **`plot_var` 编译期硬上限 = 12**。`IO/IOMain/Config` 只声明
   `PARAMETER plot_var_1..12`（两棵树实测均为 12）；超过 12 的条目被**静默忽略**
   （启动时打印 `ignoring unknown parameter "plot_var_13"`）。原 SNBOneCH 的
   18 项白名单中第 13–18 项实际从未生效。
2. `ParGeneratorExtended` 头部硬编码 `log_file="lasslab.log"` / `basenm="lasslab_"`
   （`gen_par/generator.py:375-376`），与场景设定值**重复**；生成后注释掉头部占位行。
3. `plotFileIntervalStep` 与 `plotFileIntervalTime` 是 **OR 双触发**
   （`IO_output.F90:367`）；白名单里已有 step 值时会出现意外帧，故注释掉 step 触发。
4. `wsl bash -lc "<cmd>"` 的 `$var` / `$(...)` 会被 **Windows 侧外层 shell 提前展开**；
   内联命令禁用循环变量与 `$?`，条件判定用 `if/else` 落盘标记。
5. `+ug` 下 par 的 `nblockx`/`lrefine_*` 被 UG 忽略属正常（`UG/Config` 明文）；
   `lrefine_max=1` 的自动注释 `res = dir_delta/(nxb*nblock*2^(lrefine_max-1))` 对 `+ug` 无效。
6. 非固定块模式必须显式 `-nofbs`（详见 `docs/ug_resolution_finding.md` §1.1）。

---

## 5. 文件与入口

```
t002/
├── common/t002_common.py             # 唯一物理参数源（PARAMS / LEGS / GRID）+ WSL 工具
├── scripts/generate/gen_t002_inputs.py   # 两腿输入生成 + par 一致性自检
├── scripts/run/run_t002.py               # 部署→setup→make→mpiexec→收集
├── scripts/probe/ug_resolution_probe.py  # +ug 分辨率/速度矩阵
├── scripts/analysis/compare_models.py    # 对比分析出图
├── sim_flsh/{flash_input,flash_output}/  # FL-SH 腿
├── sim_snb/{flash_input,flash_output}/   # SNB 腿（含 9 个 SNB 覆盖 F90）
├── results/                              # 对比图 + 汇总
└── docs/                                 # 本文档 + ug_resolution_finding.md
```

```bash
# 生成（两腿）
python scripts/generate/gen_t002_inputs.py --model both --nxb 64 --iprocs 8
# 跑（首次会 setup+make；之后加 --skip-setup --skip-make 只换 par 重跑）
python scripts/run/run_t002.py --model both --tmax 2.0e-10 --tag cmp_2e-10
python scripts/run/run_t002.py --model both --tmax 1.20e-9 --tag full_1ns \
       --skip-deploy --skip-setup --skip-make
# 分辨率矩阵 / 对比分析
python scripts/probe/ug_resolution_probe.py
python scripts/analysis/compare_models.py --tag full_1ns --target-ns 1.0
```
