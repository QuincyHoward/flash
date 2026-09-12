# SNBOneCH —— OneCH_ml 几何/材料 + SNB 非局域热传导（双标记）

> 位置：`flash/scenarios/private/tracer/SNB/SNBOneCH`
> 派生自：`tracer/OneCH_ml`（local，Spitzer+限流）× `SNB/SNB` 核心模块（nonlocal）

---

## 1. 定位

与 `tracer/SNB/SNBOneCH_ml` 同族，但**只用两个物种标记**：`cham` + `targ`。

| 项 | `OneCH_ml`（local） | `SNBOneCH`（nonlocal，本场景） |
|---|---|---|
| 电子热传导 | Spitzer + flux limiter | **SNB 多群非局域** |
| 域 | `x ∈ [-0.04, 0.01]` cm | 同 |
| 固体靶 | CH，`x ∈ [0, 56.1]` µm，1.0 g/cm³ | 同（多层合并为**单层**） |
| 腔室 | He，1.0e-6 g/cm³ | 同 |
| 激光 | 0.351 µm，82 段，透镜 x=−1.0 cm，靶 x=0 | 同 |
| 表 | `He-BADGER-TOPS-Final.cn4` + `CH-QC-1-001.cn4` | 同 |
| 辐射 | MGD 10 群 + 三开关 | 同（**默认开**） |
| EOS / 流体 | — | 同（`RiemannSolver="hllc"` 等一律沿用） |
| 物种 | 8 标记 | **2 标记（cham/targ）** |
| 网格 | AMR lrefine 9 | **`+ug` 均匀网格**（SNB 铁律） |
| 数据源 | `plt`（float32） | `chk`（float64） |

**唯一的物理差异 = 电子热传导模型** ⇒ 两场景可直接做 local vs nonlocal 对比。

---

## 2. SNB 设置（本场景默认）

| # | 项 | 值 | 说明 |
|---|---|---|---|
| 1 | **辐射** | `rt_useMGD` / `useOpacity` / `useRadTrans` = `.true.` ×3，且用 **radON 驱动变体** | 默认**开启**；作者原版把 `call RadTrans` 注释了，必须用变体 |
| 2 | **电子限流模式** | `diff_eleFlMode = "fl_none"` | 项目约定默认（该键在 SNB 电子路径上实测为 **no-op**） |
| 3 | **`gr_hypreUseFloor`** | **`.false.`** | ★★★ SNB 崩塌真正主因；生成后**硬校验** |
| 4 | **`dtmax`** | `2.0e-14` | SNB 并列前提（非充分条件） |
| 5 | **网格** | `+ug`，`iProcs` × `nxb`，`mpiexec -n` 必须 == `iProcs` | AMR 粗细界面会破坏非局域积分 |
| 6 | **首次使用场景** | **强制 setup+make** | 由 `run_scene.py` 的**构建指纹**判定 |

---

## 3. 目录结构

```
SNBOneCH/
├── SNBOneCH.py                 ← 生成 + 运行编排（复用 SNB/SNB 核心模块）
├── plot_compare_onech.py       ← 与 OneCH_ml 的 nele/tele/pele 对比图
├── README.md                   ← 本文
├── scene/                      ← 生成物（可删除重建）
│   └── sim_snb/flash_input/
│       ├── Config              ← ★ SNB 包 Config 基座 + 本场景物种参数
│       ├── Makefile            ← 含 mgd_qesh.o
│       ├── Simulation_{data,init,initBlock}.F90
│       ├── diff_advanceTherm.F90 / mgd_qesh.F90 / Conductivity.F90 /
│       │   Driver_evolveFlash.F90(radON) / Grid_advanceDiffusion.F90 / hy_uhd_*4
│       ├── {He-BADGER,CH-QC-1-001}.cn4
│       ├── snb_onech.par            ← 正式时间
│       └── snb_onech_smoke.par      ← 短时验证
│   └── flash_output/sim_snb/{smoke,full}/   ← chk 输出
├── images/                     ← 对比图
└── logs/                       ← 运行日志
```

---

## 4. 用法

```bash
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
cd flash/scenarios/private/tracer/SNB/SNBOneCH

$PY SNBOneCH.py --stage generate    # 只生成输入（含承重键 + 键集自检）
$PY SNBOneCH.py --stage smoke       # ★ 先短时 (tmax=1e-11)
$PY SNBOneCH.py --stage full        # 正式 (tmax=1.6e-9，与 OneCH_ml 规范时间对齐)
$PY SNBOneCH.py --stage check       # chk 健康检查
$PY SNBOneCH.py --stage plot        # 与 OneCH_ml 对比出图
```

跑对比前需有 OneCH_ml 的数据（**chk 优先**，因其含 `pele` 且为 float64）：

```bash
cd flash
$PY -m flash.scenarios.private.tracer.OneCH_ml.OneCH_ml --tmax 1.6e-9
```

> ★ 若已有他人/他处的 FL-SH 结果，直接放到
> `tracer/OneCH_ml/flash_output/outputfiles/run_<NNNNNN>/` 即可 ——
> `plot_compare_onech.py` 会**自动挑最新且含输出的 `run_*` 子目录**，
> 并**优先读 chk**（plt 受 `plot_var` 上限 12 约束，旧版本不含 `pele`）。

> ★ **首次使用某场景必须重新编译**：`objdir` 名由核心模块固定
> （`SNB_SCENE_obj`），不同场景会**复用同一 objdir**。`run_scene.py`
> 以 `flash_input/` 全文件内容 + setup 参数的 **SHA256 构建指纹**判断：
> 指纹不一致或 `flash4` 缺失 → **无视 `--skip-setup/--skip-make` 强制** setup+make。

---

## 5. 本轮踩到的坑（都已做成自动拦截）

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| 1 | make 报一串 `Symbol 'qesh_var' at (1) has no IMPLICIT type`（QESH/QESX/GRQX/MFPE/NELE…） | 用 `input_gen` 生成的 Config **只有物种参数**，缺 SNB 包的 `REQUESTS`（`Conductivity/SpitzerHighZ` 等）与 **18 个 SNB 诊断 `VARIABLE`** | **以 SNB 包 Config 为基座**，替换 `DATAFILES` 后**追加**其未声明的物种参数 |
| 2 | 链接期缺 `mgd_qesh` 符号 | `input_gen` 生成的 Makefile 不含 `mgd_qesh.o` | 生成后自动补 `Simulation += Simulation_data.o mgd_qesh.o` |
| 3 | FLASH 可能因未注册参数报错 | par 基线 `CH_FLASH_PAR` 为 8 标记场景而设，2 标记下残留 `sim_targetRadius`/`ms_targZMin` 等 | 剔除；并把 `ZMin` 用 `sim_zmin<Cap>`（生成器的声明名）；加**材料类键集自检**拦截 |
| 4 | `setup` 因脉冲段数超限失败 | 82 段激光 | `ed_maxPulseSections=300`（已进入 `run_scene.py` 的 setup 标志） |
| 5 | `mpiexec` 挂死 | `+ug` 下一块一进程 | `--iprocs` 与 `mpiexec -n` 严格相等（脚本已保证） |
| 6 | 编译不过 / 结果不匹配 | `gr_hypreUseFloor` 缺失 → 退回默认 `.true.` | 生成后**硬校验**该键；缺即拒绝运行 |
| 7 | 长时运行被健康检查**误判为崩塌** | 原判据「ρmax 末值 < 峰值×0.5」对 **1.6 ns 长时**场景过粗 —— 冲击波过后靶稀疏化会合法地把 ρmax 降一半以上 | ★ 改为看**单帧最大相对跌幅**：>30% 才算断崖崩塌；否则报「平滑衰减」并提示与 FL-SH 同窗口对照（`chk_probe.py` 与 `run_scene.verify_run_health` 同步修正） |

---

## 6. 生成后自动执行的校验

`--stage generate` 结束时打印并强制：

1. **承重键校验**：`gr_hypreUseFloor` / `diff_eleFlMode` / `dtmax` /
   `rt_useMGD` / `useOpacity` / `useRadTrans` 必须落在生成的 par 里。
2. **材料类键集自检**：par 中 `sim_/ms_/eos_/op_` 前缀的键必须在 Config 中声明
   （白名单仅放行属其它 FLASH 单元的 `eos_useLogTables` / `eos_maxNewton` /
   `op_tableEnergyTolerance`）。

---

## 7. 对比口径（`plot_compare_onech.py`）

★ **数据提取统一走项目自带的 `flash.output_processors`**（2026-09-12 起）：

```python
FlashDataLoader(path).load(compute_derived=False, extraction_mode="h5py")
    → container.data / container.x      # 只取 node_type==1 的叶子块
DataCalculator(container.data).compute("nele")   # 项目 DATA_CONFIG 的权威公式
```

| 量 | 来源 | 说明 |
|---|---|---|
| `nele` | **`DataCalculator`** | 项目公式 `nele = ye·dens·NA`（`NA = 6.02214076e23`，取项目常数） |
| `nion` | **`DataCalculator`** | 项目公式 `nion = sumy·dens·NA` |
| `zbar` | `ye/sumy` | 平均电离度，诊断用 |
| `tele`/`tion`/`trad` | 直接读，K → eV | |
| `pele`/`pres` | 直接读，dyne/cm² → Mbar | |

**为什么必须用 `extraction_mode="h5py"`**：它走 `extract_var`，**只取叶子块**。
本场景 OneCH_ml 是 **AMR**，默认的 `load()` 不过滤 `node type`，会把**父块的陈旧
粗网格值**混进来并把坐标错位 —— 这是已知的坑（见项目记忆）。

### ★★ `nele` 与 `dens` 形态差异大是**物理**，不是提取错误

`ye` 是**电离态相关**的电子丰度（mol e⁻/g），不是常数。实测 OneCH_ml：

| 时刻 | `dens` [g/cm³] | `ye` | `zbar = ye/sumy` | `nele` [cm⁻³] |
|---|---|---|---|---|
| t = 0 | 1.0e-6 … 1.0 | 3.4e-4 … 2.9e-3 | **0.001 … 0.019** | **2.0e14 … 1.8e21** |
| t = 0.363 ns | 1.0e-6 … 7.6 | 1.9e-3 … 5.4e-1 | 0.008 … 3.499 | 2.0e15 … 2.3e23 |
| t = 1.6 ns | 6.1e-3 … 1.9 | 8.7e-2 … 5.4e-1 | 0.566 … 3.493 | 2.0e21 … 1.5e23 |

⇒ 室温冷态靶 **`zbar ≈ 0.001–0.02`（几乎中性）**，故 `nele` 只有 ~1e14–1e21；
加热到 `zbar ≈ 3.5` 后才到 1e23。**`nele` 因此比 `dens` 多好几个十进跨度**
（t=1.6 ns：dens 2.5 个十进 vs nele 1.9 个十进；t=0 时 nele 达 7 个十进）。
**这不是数据提取错误** —— 用固定"完全电离"Z/A 去算才会与它差 2 个量级以上。

> ⚠ **显示建议**：若用固定色标范围（例如 `value_lim=[1e18, 1e24]`），
> t=0 冷态（`nele ~1e14`）会**落到色标下限之外被压成同一个最暗色**，
> 从而"看不见"早期结构。要看全时段演化，应把下限放宽（如 `1e13`）或用自动范围。

### ★★ 与 `CASES_Comp/plots/cmap/OneCH/` 彩图的一致性核验（2026-09-12）

对"本脚本的图与 `Paper_My/SimComp` 的 OneCH 彩图为何看起来不同"做了逐项核验：

| 核验项 | 结果 |
|---|---|
| **数据源是否同一份** | `tracer/OneCH_ml/.../run_000001` 与 `SimComp` 的 `run_dir`<br>（`FLASHProjectData/data/input/CASES/OneCH_ml/.../run_000001`）<br>**383 个文件逐字节相同（md5 全等，0 个不同）** → **复制无误** |
| **数值是否相同** | 对方预抽 H5 `CASES_Comp/data/OneCH.h5` 的 `nele`：<br>t=0 时 x=−100 µm = **2.0442e14**、x=+40 µm = **1.7455e21**<br>本脚本提取：min = **2.044e14**、max = **1.745e21** → **一致** |
| **物理自洽** | 对方 H5 同帧：`dens(40 µm)=1.0`、`zbar=0.0189`；<br>`nele = zbar·sumy·dens·NA = 0.0189×0.1532×1.0×6.022e23 = 1.744e21` ✓ |

⇒ **两边数据与数值完全一致，不存在提取错误**。图像"看着不相符"来自**显示约定**：

1. 对方 `cases_plot_cmap.py` 用**固定** `value_lim=[1e18, 1e24]`；本脚本用**数据实际范围**。
   冷态 `nele` 跨 14.3–21.2 个十进，在固定范围内被压到色标下半段，
   `1e18` 以下全部压成一个最暗色 → 早期结构被"抹平"。
2. 对方横轴限幅 `x ∈ [−190, 50] µm`；本脚本按物理区间取值（并叠加了 SNB 对照腿）。
3. t=0 靶区 `nele ≈ 1.75e21` 比"完全电离"估计 `3.24e23` **低 186 倍** ——
   因为冷 CH `zbar ≈ 0.019`（几乎中性）。这是**物理**，不是提取错误。

> 若需要与本脚本做**逐像素样式对齐**，可把横轴限成 `[−190, 50] µm`、
> `nele` 色标固定为 `[1e18, 1e24]`；判据仍是上面的两组数值（已经一致）。

产出：`fig1_profiles_nele.png`、`fig2_profiles_tele.png`、`fig3_profiles_pele.png`、
`fig4_xt_compare.png`（x-t 2×3，上行 SNB / 下行 OneCH_ml，**每列共享色标**）、
`fig5_front_zoom.png`（靶前区放大）、`metrics_compare.csv`。

> 说明：`OneCH_ml` 的 plt 变量受 `plot_var` 白名单**硬上限 12** 限制。
> 为使其输出 `pele`，已在 `OneCH_ml.py` 的 `_PLOT_VARS` 中以 `pele` 顶替
> `depo`（仅输出白名单变化，**不改物理**），并补了 `plotFileIntervalTime`。
> 本次对比实际使用的 FL-SH 数据由其 chk 提供，**不受该白名单影响**。

---

## 8. 运行结果（2026-09-12）

> ★ 正式时间已由 `2.0e-10` 延长到 **`1.6e-9`**，与 OneCH_ml 的规范 tmax 对齐
> （0.2 ns 太短，靶尚未充分压缩/烧蚀，与 FL-SH 侧不可比）。

### 8.1 本场景

| 阶段 | 设置 | 结果 |
|---|---|---|
| 首次编译 | `+ug`，iProcs=16 × nxb=128 = 2048 格，dx≈0.2441 µm | setup + make 通过 |
| **smoke** | `tmax=1e-11`，chk=1e-12 | 正常退出，11 帧，墙钟 **14.2 s**，`dt` 钳位 `2.000e-14` ✓ |
| **full** | `tmax=1.6e-9`，chk=2e-11 | 正常退出，**81 帧**，墙钟 **3608.4 s（≈60 min）**，`dt` 全程钳位 `2.000e-14` ✓ |

全长健康判据（`--stage check`）：

| 帧 | t [ns] | dt [s] | ρmax | ρsum | Te_max [eV] | Tr_max [eV] |
|---|---|---|---|---|---|---|
| 0000 | 0.000 | 1.0e-15 | 1.0000 | 2.300018e+02 | 0.03 | 0.020 |
| 0040 | 0.800 | **2.000e-14** | 6.1769 | 2.297038e+02 | 1850.55 | 91.33 |
| 0080 | 1.600 | **2.000e-14** | 1.9666 | 1.978760e+02 | 1534.63 | 88.64 |

**ρmax 后期下降的定性（重要）**

ρmax 峰值 **6.565**（t≈0.50 ns）→ 末值 **1.967**（0.30×）。这**不是**数值崩塌：

* `dt` **全程钳位** `2.000e-14`，无 NaN/Inf；
* 下降是**平滑单调**的（峰值之后**单帧最大跌幅仅 5.9%**），不是断崖；
* ★ **同窗口 FL-SH（local）表现一致且跌得更多**：峰值 8.096 → 末值 1.928（0.238×）
  ⇒ 该行为**与热传导模型无关**，属冲击波过后靶膨胀的**物理稀疏化**。

> ⚠ 总质量相对漂移 **1.40e-01**（出流边界 + 烧蚀吹除；`+ug` 下 Σρ ∝ 总质量）。
> 注：FL-SH 侧是 AMR（Δx 非均匀），其 `ρsum` **不能**当作质量代理，故两腿该数字不可直接比。

### 8.2 与 OneCH_ml 的对比（t = 1.6 ns）

| 模型 | nele_max [cm⁻³] | tele_max [eV] | pele_max [Mbar] |
|---|---|---|---|
| **SNBOneCH（nonlocal）** | 1.4568e+23 | 1534.63 | 11.085 |
| OneCH_ml（local） | 1.4941e+23 | 1510.96 | 11.040 |
| 相对差（local vs nonlocal） | **+2.6%** | **−1.5%** | **−0.4%** |

⇒ **到 1.6 ns 时两模型的全域极值已很接近（≤3%）**，差异主要体现在**空间结构**上，
而非极值本身 —— 这也是为什么必须看剖面/时空图而不能只看极值。

### 8.3 ★★ `fig4` "两种烧蚀速度明显不同" —— 是**绘制 bug**，已修（2026-09-12）

**现象**：`fig4_xt_compare.png` 上行（SNB）与下行（OneCH_ml）看起来"前沿速度明显不同"。

**根因**：`fig_xt()` 原用 `imshow(..., extent=(x0,x1,t0,t1))`。
**`imshow` 假设各帧在时间轴上等间距**，而 FLASH 的 chk 是**按步数**间隔输出的：

| 腿 | 帧数 | Δt 范围 | 最大/最小 |
|---|---|---|---|
| SNBOneCH（`+ug` chk） | 81 | `2.0000e-11`（**恒定**） | **1.00×** |
| **OneCH_ml（AMR chk）** | 317 | **`1.36e-12` … `7.19e-11`** | **52.7×** |

⇒ OneCH 行的**时间轴被局部拉偏最多 ~3576%** —— 同一物理运动在两行上就"显得"速度不同。
（`+ug` 腿的帧是等时间间隔的，AMR 腿不是；两腿采样方式不同是假象来源。）

**修正**：`imshow` → **`pcolormesh` + 真实逐帧时间坐标** `np.meshgrid(xg, ts*1e9)`。
修正后两行的结构与时序**完全对得上**。

**定量验证**（`temp_test/front_compare.py`，阈值法取电子密度临界面 `x_c(t)`，
阈值 = `n_c(0.351 µm) = 9.05e21 cm⁻³`）：

| t [ns] | SNBOneCH（nonlocal） | OneCH_ml chk（local） | OneCH_ml H5（预抽） |
|---|---|---|---|
| 0.2 | 1.676 | 1.605 | 1.630 |
| 0.4 | 8.989 | 8.680 | 8.704 |
| 0.8 | 34.107 | 34.099 | 34.249 |
| 1.2 | 64.999 | 68.876 | 68.909 |
| 1.6 | 98.694 | 99.315 | 99.755 |
| **拟合速度** | **+0.0803 µm/ps** | **+0.0796 µm/ps** | **+0.0853 µm/ps** |

⇒ 三方速度**相差 ≤7%**；SNB 与 FL-SH 的临界面轨迹本质相同。
**"两种烧蚀速度不同"纯属绘图假象。**

> 注：`x_c` 到 1.6 ns 已达 ~99 µm（接近域边界 100 µm）—— 冕区已膨胀到边界，
> 故该时刻"前沿位置"不再有判别力（与 §8.2 的结论一致）。

> ⚠ **另一个已知的"数据形态"差异（不影响结论）**：同一台仿真的
> **原始 chk** 与**预抽统一网格 H5**（`CASES_Comp/data/OneCH.h5`）逐时刻对拍
> （`temp_test/check_flsh_sources.py`）：**t ≥ 0.4 ns 时中位相对差 ≤0.2%**；
> 仅 **t = 0 / 0.2 ns** 在**材料界面与热前沿**处出现 18–49% 的局部差 ——
> 这是把 AMR 数据线性插值到不同网格（界面/陡梯度处）的固有差异，
> **不是提取错误，也不影响前沿速度结论**。

**图中所见的主要差异**（`images/fig4_xt_compare.png`、`fig2/fig5*.png`）：

1. ★ **热前沿到 1.6 ns 已"饱和"**：用阈值法（Te 首次降到给定值处）测量，
   末帧两模型的热前沿**都已抵达计算域边界** `x ≈ −400 µm`（两者仅差 **0.37 µm**）。
   ⇒ 在此时间点**"前沿深度"不再是有效的模型判别量**；0.2 ns 时才有区分度。
   （⚠ 这也提醒：**不要凭 x-t 色图目视判断前沿位置** —— 共享色标与插值会误导。）
2. ★ **剖面定量高度一致**：末帧 Te 在固定位置上的两模型差：

   | x [µm] | SNB [eV] | local [eV] | 相对差 |
   |---|---|---|---|
   | −20 | 909.1 | 937.8 | **+3.2%** |
   | −50 | 1035.5 | 1057.4 | +2.1% |
   | −100 | 1196.2 | 1207.4 | +0.9% |
   | −150 | 1313.5 | 1315.2 | +0.1% |
   | −200 | 1399.2 | 1392.8 | −0.5% |
   | −300 | 1502.1 | 1483.7 | −1.2% |

   ⇒ 全域相差 **≤3.2%**；趋势是 **local 在近前沿（x > −150 µm）略热**、
   **SNB 在深部（x < −200 µm）略热**（两模型剖面在 x≈−175 µm 附近交叉）。
3. **前沿形态**：`OneCH_ml` 的 x-t 图呈明显**阶梯状**（AMR 自适应细化所致），
   `SNBOneCH` 用 `+ug` 均匀网格，前沿平滑 —— 这是两场景**网格策略**不同的直接体现，
   **不是**热传导模型差异。
4. **电子压力结构**：SNB 呈较宽的楔形高压区，local 的高压区更窄更陡。

> ⚠ **可比性限制（解读时必须注明）**：
> * 网格策略不同（`SNBOneCH` 为 `+ug` 均匀网格 2048 格；`OneCH_ml` 为 AMR lrefine 9），
>   故**前沿位置/厚度与局部梯度**的定量比较受分辨率影响；
> * 物种标记数不同（2 vs 8），但**几何/密度/材料/激光/辐射完全一致**；
> * 两腿数据源均为 **chk（float64）**，此点已对齐。
>
> **小结**：在**本算例**（0.2–1.6 ns、CH 1.0 g/cm³、辐射开）下，
> **local 与 nonlocal 的 Te/pele 差异在剖面上一层 ≤3%**，远小于两模型
> 在文献中常见的差异量级。若要凸显非局域效应，宜转向梯度更陡的时段
> （如 0.2 ns 附近）或更陡的初始构型。

### 8.4 产出

| 路径 | 内容 |
|---|---|
| `images/fig1_profiles_nele.png` | 电子数密度剖面（多时刻 × 双模型） |
| `images/fig2_profiles_tele.png` | 电子温度剖面 |
| `images/fig3_profiles_pele.png` | 电子压力剖面 |
| `images/fig4_xt_compare.png` | x-t 对比 2×3，**每列共享色标**（上行 SNB / 下行 OneCH_ml） |
| `images/fig5_front_zoom.png` | 靶前区放大（x ∈ [−10, 20] µm） |
| `images/metrics_compare.csv` | 末帧定量对照 |
| `scene/flash_output/sim_snb/{smoke,full}/` | chk 输出（11 帧 / 腿） |
| `logs/run_{smoke,full}.log` | 运行日志 |
| `temp_test/check_flsh_sources.py` | FL-SH 两形态（原始 chk vs 预抽 H5）逐时刻对拍 |
| `temp_test/front_compare.py` | 前沿速度三方定量对拍（阈值法 `x_c(t)` + Δt 均匀性诊断） |

> `temp_test/` 是**诊断用临时目录**：`check_flsh_sources.py` 定位了"两形态差异只在
> 界面/前沿处"；`front_compare.py` 定位并证实了 `fig4` 的**时间轴 bug**。
> 两者都不产生正式交付物，可随时删除。
