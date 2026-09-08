# 首次 SNB 代码微调说明

> 场景：`SNBtest/Test/t001`（SNB 模型首次跑通，`tmax = 1.0e-11`）
> 日期：2026-08-29
> 适用范围：**SNB 专用 FLASH 代码（FLASHSNB，与常用场景 FLASH 严格隔离）**
> 配套文档：`README.md`（运行/归档）、`run_snb.py`（一键仿真脚本）

---

## 0. 结论速览

| # | 文件 | 修改类型 | 是否影响物理 | 风险等级 |
|---|------|---------|------------|---------|
| 1 | 场景 `diff_advanceTherm.F90` | 续行符补齐（语法） | **不影响** | 低 |
| 2 | 场景 `mgd_qesh.F90`（新增） | 补齐缺失源文件 | **影响（正）**：群热流权重函数 | 中 |
| 3 | `Diffuse/DiffuseMain/Diffuse_computeDt.F90` | aniso/标量调用分流 | **不影响**（非 aniso 路径与官方一致） | 低 |
| 4 | `Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90` | 数组调用 → 标量 fullState | **影响（修正）**：避免 anisoFullState stub 置零 | 中 |
| 5 | 场景 `hy_uhd_DataReconstructNormalDir_PPM.F90` / `hy_uhd_getRiemannState.F90` | use 模块名对齐 | **不影响**（函数实现逐行一致） | 低 |
| 6 | 场景 `flash.par` | `iProcs=4`（1D 进程分解） | **不影响**（运行参数） | 低 |

其中 #4 经历了一次**自我修正**：初版改为无条件 `Conductivity_anisoFullState`（编译通过但该过程是 stub、返回 0，物理错误），
随后按用户源码语义改为标量 `Conductivity_fullState` 调用（真实 Spitzer 热导），并以最终版重新编译、重跑验证。

---

## 1. 逐条修改说明

### 1.1 场景 `diff_advanceTherm.F90` — QENL 热流散度块续行符缺失

**现象**：编译报 `Error: Zero is not a valid statement label`（约 377 行）。

**原因**：SNB 群分辨热流散度（`solnVec(QENL_VAR,i,j,1) = -( ... ) / del(DIR_X)**2`）多行表达式中，
`= -(` 之后与后续 4 行**缺少 `&` 续行符**，Fortran 自由格式把后续行当作新语句解析。
该问题在**用户提供的 src/SNB 场景原版中同样存在**（与 FLASHSNB 修改前逐字节一致，43790 B）。

**修改**：`= -(` → `= -(&`，后续 4 行行尾补 ` &`。
**注意**：文件含 GBK 中文注释，修改必须用二进制模式（UTF-8 读取会解码失败；shell 的 perl `\s*$`
会吞掉换行符损坏文件，已发生并修复）。

**物理影响**：无。仅还原为代码作者本意的多行表达式，不改变任何数值。

### 1.2 场景 `mgd_qesh.F90` — 缺失源文件补齐

**现象**：`make: *** [Makefile:165: mgd_qesh.o] Error 1`（找不到源文件）。

**原因**：场景 `Makefile` 声明 `Simulation += ... mgd_qesh.o`，但 FLASHSNB（及 src/SNB）场景目录中
**均无 `mgd_qesh.F90`**；该文件存在于常用 FLASH 的 SNB_1D_laser 场景中（两库场景文件对比仅此一项缺失）。

**函数语义**（关键，直接影响 SNB 物理）：`mgd_qesh(x0,x1,..) -> fra` 计算多群 SH 热流权重，
即不完全伽马积分 `[P(4,x0) − P(4,x1)]/24`（`P(4,x)=∫₀ˣ t³e⁻ᵗdt`）。`diff_advanceTherm` 用它把
Spitzer–Härm 热流按能量群分解（`QEXG_VAR = frac_x * QESX_VAR`、`GRGX/GRQG` 群分辨散度），
是 SNB 非局域修正中"群分辨热流"环节的必需函数。

**修改**：自常用 FLASH 复制（两库该文件需确认一致；本次取自常用 FLASH 的 SNB_1D_laser 场景，
其公式来源标注为 Zheng Chunkai）。

**物理影响**：**有**——若缺失（编译不过）或取错版本，群分辨热流无法计算。本次补入的公式
`(x⁴+4x³+12x²+24x+24)e⁻ˣ/24` 正是 `P(4,x)/Γ(4)` 闭式（Γ(4)=6 的 1/24 即 1/Γ(5)），与 SH 热流
群分解标准一致。**风险**：该函数无官方参照（非 FLASH 标准库），如与原作者群边界定义不一致
会导致群权重偏差，需在正式算例中与 QESX/GRGX 剖面交叉校验。

### 1.3 `Diffuse_computeDt.F90` — Conductivity 调用按 aniso/标量分流

**现象**：`There is no specific subroutine for the generic 'conductivity'`。

**原因**：FLASHSNB 的 `Conductivity_interface` 是"增强泛型"——`Conductivity` 泛型内含
6 参数旧版（`xtemp,xden,massfrac,κ,D,component`）、标量版 `Conductivity_fullState`、
`Conductivity_aniso`，另有独立 `Conductivity_anisoFullState`（数组版）。
而 `Diffuse_computeDt` 原实现**无条件**用数组 `diff_coeff_vec(3)` 调 `Conductivity` → 泛型无匹配。
该问题同样存在于 FLASHSNB 初版；**用户提供的 src/SNB 中已存在一份分流修改版**（ion 分支用
`diffCoeff=diff_coeff_vec(1)`），本次修改方向与其一致、细节等价。

**修改**（只改调用方，不动接口）：
- aniso 开关为真 → `Conductivity_anisoFullState(..., diffCoeff=diff_coeff_vec(3))`（数组版）
- aniso 开关为假（本场景默认）→ 标量版 `Conductivity(..., diffCoeff=diff_coeff, ...)`
- ion 非 aniso 分支新增局部标量 `diff_coeff_ion` 承接离子热导，再与电子热导取 max

**物理影响**：无。非 aniso 路径与官方行为一致（`diff_coeff` 取热导标量）；aniso 路径本次未启用
（par 中 `diff_anisoCondForEle` 未开启）。

### 1.4 `hy_uhd_getFaceFlux.F90`（unsplit）— 修正热导调用，避免 stub 置零 ⚠️

**现象**：`There is no specific subroutine for the generic 'conductivity'`。

**原因**：FLASHSNB 该文件用 `cond_zone(3)` 数组调 `Conductivity` → 与标量 fullState 泛型不匹配。

**初版修改（错误）**：无条件改 `Conductivity_anisoFullState` —— **编译通过但物理错误**：
FLASHSNB 的 `Conductivity_anisoFullState` 是 **stub**（`isochoricCond=0, diffCoeff=0`），
会把 Hydro 热流的热导**恒置 0**，长时运行将完全丢失热传导。

**最终修改（正确，与用户源码语义一致）**：改为标量 fullState 调用——
`call Conductivity(U(:,i,j,k), diffCoeff=cond_zone(1), component=2)` + `cond(i,j,k)=cond_zone(1)`，
取 Spitzer 真实热导（数组首元素即各向同性值）。

**物理影响**：**修正了一处潜在错误**。tmax=1e-11 极短验证中，新旧版输出**逐点一致**
（maxΔ=0，因 1e-11s 内热传导输运可忽略），但**正式长时算例必须用最终版**。

### 1.5 场景 `hy_uhd_DataReconstructNormalDir_PPM.F90` / `hy_uhd_getRiemannState.F90` — 模块名对齐

**现象**：`Cannot open module file 'hy_uhd_slopelimiters.mod'`。

**原因**：场景代码 `use hy_uhd_slopeLimiters`；FLASHSNB 提供的标准模块是 `hy_slopeLimiters`
（HydroMain 根目录）。**用户 src/SNB 中同时存在 `hy_uhd_slopeLimiters.F90`**（unsplit 子目录，
内容与 `hy_slopeLimiters.F90` 逐行一致、仅模块名不同）。

**修改**：场景两文件 use 名改为 `hy_slopeLimiters`（符号 `minmod`/`mc` 不变）。
**等价替代方案**：把 src/SNB 的 `hy_uhd_slopeLimiters.F90` 移植进 FLASHSNB 亦可，功能相同。

**物理影响**：无。两个模块的函数实现（`checkMedian/vanLeer/vanLeer15/mc/minmod`）逐行相同。

### 1.6 场景 `flash.par` — `iProcs=4`

**现象**：运行报 `Driver_init: Must set runtime parameters iProcs, jProcs, kProcs ...`。

**原因**：1D 仿真 4 进程需沿 x 分解，par 中 `iProcs` 原被注释。

**修改**：`#iProcs = 8` → `iProcs = 4`（jProcs/kProcs 默认 1，`4×1×1×1=4` 与 `mpiexec -n 4` 匹配）。

**物理影响**：无，纯运行/并行参数。

---

## 2. src/SNB 源码核查结果（"第二种修改"专项）

按用户要求，对"本次为跑通 SNB 的修改"与"用户提供的 src/SNB 源码树"做了逐文件对比，
**确认存在第二组修改/版本**，需特别谨慎对待：

### 2.1 场景层（`src/SNB/SNB_1D_laser/SNB_1D_laser/`，17 文件 vs FLASHSNB 场景源）
- **13 个完全相同**（Config/Simulation_*/Conductivity.F90/hy_uhd_dataReconstOneStep/hy_uhd_ragelike/…）
- **4 个差异 = 本次修改的全部场景层改动**：
  `diff_advanceTherm.F90`（+6B，续行符）、`flash.par`（-1B，iProcs）、
  `hy_uhd_DataReconstructNormalDir_PPM.F90`/`hy_uhd_getRiemannState.F90`（-4B，模块名）
- **结论**：场景层无遗漏的第二种修改；用户源码中同样缺续行符与 `mgd_qesh.F90`。

### 2.2 `src/SNB/f90/`（独立备份的两个文件）⚠️
- `f90/Conductivity.F90`（2763B）＝ 场景 `Conductivity.F90`（完全相同）。
- `f90/diff_advanceTherm.F90`（18213B）＝ **官方 Unsplit 标准版**（无 multigp 群循环、
  无 mgd_qesh/energy 群分辨、无 SNB 诊断变量），**与场景完整版（43790B，含 SNB 群分辨逻辑）完全不同**。
- **风险**：若误以 f90/ 版替换场景版，将**丢失全部 SNB 非局域群分辨逻辑**（QEXG/GRGX/GRQG/QENL 计算）。
  当前编译与运行均使用场景完整版，勿混用。

### 2.3 physics 层（`src/SNB/physics/physics/`，318 个文件差异，大部分为版本噪声）
- **必须注意的"第二种修改"**：
  - `Diffuse/DiffuseMain/Diffuse_computeDt.F90`：src/SNB 版已做 aniso/标量分流
    （ion 非 aniso 用 `diffCoeff=diff_coeff_vec(1)`），与本次修改等价；**src/SNB 版可直接使用**。
  - `Hydro/.../unsplit/hy_uhd_getFaceFlux.F90`：src/SNB 版为标量调用
    （`call Conductivity(U(:,i,j,k),cond(i,j,k),component=2)`），**与最终修改版语义一致**。
  - `Hydro/.../unsplit/hy_uhd_slopeLimiters.F90`：src/SNB 独有（FLASHSNB 无），内容= `hy_slopeLimiters` 改名版。
- **其余 300+ 差异**（Eos/Gravity/TreeRay/split PPM/IncompNS 等）为 FLASH 版本级差异
  （src/SNB 的 physics 树为另一 FLASH 版本布局，如 ConductivityAniso/ 子目录、BHTree 等），
  与本次 SNB 编译无直接关系，**不建议整体移植**。
- **接口一致性**：src/SNB 与 FLASHSNB 的 `Conductivity_interface.F90`（104 行）**完全相同**
  （增强泛型），确认接口架构同源。

### 2.4 处理建议
1. 本次 t001 的 `source_patches/` 已归档**最终版**补丁（含 1.4 修正后的 hy_uhd_getFaceFlux）。
2. 后续正式算例若重 setup：场景文件用 t001 补丁覆盖；physics 层仅需
   `Diffuse_computeDt` + `hy_uhd_getFaceFlux`（unsplit）两处补丁（或直接采用 src/SNB 对应版本）。
3. `f90/` 精简版**仅作官方版参照**，禁止替换场景完整版。

---

## 3. 验证与运行结果

- 编译：`make -j4` 无 error，`flash4` 生成（约 12 MB）。
- 运行：`mpiexec -n 4 ./flash4` exit 0，73 步到达 `tmax=1.0e-11`（"exiting: reached max SimTime"）。
- 输出：初始/最终/forced plotfile 各 1 + checkpoint 2，全部归档 `flash_output/`。
- 物理量（最终版）：
  `tele 290→9895 K`（激光刚启动，合理）、`dens 1e-6→1.04 g/cm³`、`qesx ±5e11`（SH 热流）、
  `corq ±5.7e14`、`mfpe 0.28→8.3e7 cm`，SNB 诊断变量非零。
- 一键脚本 `run_snb_t001.py` 全流程实测通过（参数检查→定位→编译检查→运行→转移→输出确认）。

## 4. 风险登记与后续注意

| 风险 | 说明 | 缓解 |
|---|---|---|
| `mgd_qesh` 公式版本 | 无官方参照，可能与原作者群定义有出入 | 正式算例中比对 QESX/GRGX 剖面与群积分一致 |
| anisoFullState stub | FLASHSNB 该过程恒 0，任何 aniso 开关启用都会置零热导 | 保持 `diff_anisoCondFor*` 关闭；aniso 场景需另实现 |
| `f90/` 精简版混用 | 会丢失 SNB 群分辨 | 归档标记、禁止替换场景版 |
| 版本噪声误移植 | src/SNB physics 为另一版本布局 | 只取 2.3 列出的两处补丁 |
| 并行编译竞态 | -j4 下 use 模块未先编译 | 先单独 make 模块 .o；旧 .mod 强删重编 |
| GBK 注释文件 | UTF-8 读写损坏 | 一律 Python 二进制模式修改 |
