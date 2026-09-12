# t002 —— SNB vs FL-SH 简易对比场景

> 创建：2026-09-10 ｜ 位置：`flash/scenarios/private/SNB/SNBtest/Test/t002/`
> 参照：`SNBtest/Test/t001`（SNB 基线）、`tracer/SNB/SNBOneCH`（+ug 最小两区）、
> `tracer/OneCH_ml`（FL-SH 限流参考）、`center_evolution/ch_center`（Z02+Z06_0.50 表对）

---

## 0. 场景定义

极简两区 1D 靶，用于对比 **SNB 非局域电子热传导** 与 **限流模型 FL-SH**：

| 项 | 值 |
|---|---|
| 域 | `x ∈ [-400, 100] µm`（= `[-0.04, 0.01] cm`） |
| 界面 | `x = 0`；`x < 0` 为 `cham`（稀薄 He，"真空"，`Z02_1.00-20260708_0851.cn4`，ρ=1e-6） |
| 靶 | `x ≥ 0` 为 `targ`（常温常压 CH，`Z06_0.50-Z01_0.50-20260708_0850.cn4`，ρ=1.0，290.11375 K） |
| 激光 | 351 nm 单束，左侧入射，`5e14 W/cm²`，梯形波 **50 ps 上升 / 1.0 ns 平台 / 50 ps 下降** |
| 网格 | `+ug` 均匀网格，`-nxb=64` + `iProcs=8` → **512 格**，`dx = 0.9766 µm`（两腿相同） |
| 辐射 | MGD 6 群（与表族一致），`fl_harmonic`，coef 1.0，六面 vacuum |

两个仿真**分文件夹、分 FLASH 树**存放：

| | `sim_flsh/` | `sim_snb/` |
|---|---|---|
| 模型 | FL-SH 限流 Spitzer-Härm（local） | SNB 非局域（Schurtz–Nicolaï–Busquet） |
| FLASH 树 | 标准 `~/QC/FLASH/FLASH4.8` | `~/QC/FLASH/FLASHSNB/FLASH4.8` |
| `diff_eleFlMode` | `fl_minmax` (coef 0.06) | `fl_none` |
| 附加 | — | 18 SNB 诊断 `VARIABLE` + `mgd_qesh.o` + 9 个 SNB 覆盖 F90 |

> **为什么必须两棵树**：SNB 非局域项在 `diff_advanceTherm.F90` 的 `if(NDIM==1)`
> 分支内**无条件执行**，且 Config 中无对应 PARAMETER —— 不存在 par 开关。
> 详见 `docs/snb_vs_flsh_design.md` §2。

---

## 1. 快速使用

```bash
cd <此目录>
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe

# 生成两腿输入（含 par 一致性自检）
$PY scripts/generate/gen_t002_inputs.py --model both --nxb 64 --iprocs 8

# 运行（首次含 setup+make；之后加 --skip-setup --skip-make 只换 par 重跑）
$PY scripts/run/run_t002.py --model both --tmax 2.0e-10 --tag cmp_2e-10
$PY scripts/run/run_t002.py --model both --tmax 1.20e-9 --tag full_1ns \
    --skip-deploy --skip-setup --skip-make

# 覆盖限流器（仅改 par，不需重编；两腿同步生效）
$PY scripts/run/run_t002.py --model both --fl-mode fl_harmonic --fl-coef 0.06 \
    --rebuild --tmax 1.20e-9 --tag full_1ns_h006 --skip-deploy --skip-setup --skip-make

# `+ug` 分辨率/速度矩阵
$PY scripts/probe/ug_resolution_probe.py

# 对比分析出图（旧：plt 源，7 张）
$PY scripts/analysis/compare_models.py --tag full_1ns --target-ns 1.0 --ylim-te 0,2e8

# ★ 对比出图（新：chk 源，上下两联）—— 见 §3
#   (1) 时空彩图：7 物理量 × 上下两联，线性 t[ns]/x[µm]，nele 对数色标
$PY scripts/plot_compare/pcolor/plot_xt_pcolor.py --tag chk_full
#   (2) 10 时刻剖面系列：7 物理量 × 上下两联，线性 x[µm]/y
$PY scripts/plot_compare/profiles/plot_profiles.py --tag chk_full
```

每个 `flash_input/` 内另有 `run_flash.sh`（WSL 手动一键流水线，
支持 `SKIP_SETUP/SKIP_DEPLOY/SKIP_MAKE/TMAX/NPROC` 环境变量）。

---

## 2. 运行结果

### 2.1 运行台账

| tag | 限流器（两腿） | FL-SH 步数 / 墙钟 | SNB 步数 / 墙钟 | plt |
|---|---|---|---|---|
| `smoke_1e-11` | fl_minmax / fl_none | 74 / 0.8 s | 96 / 1.6 s | 1 |
| `cmp_2e-10` | fl_minmax / fl_none | 2144 / **12.92 s** | 3456 / **43.49 s** | 5 |
| `full_1ns` | fl_minmax / fl_none | 10656 / **87.6 s** | 14751 / **139.1 s** | 25 |
| `full_1ns_h006` | fl_harmonic 0.06（两腿） | 10874 / 89.3 s | 14751 / 144.9 s | 25 |
| **`chk_full`** | fl_minmax / fl_none | 10656 / **85.4 s** | 14751 / **135.1 s** | **16 chk** (+3 plt) |

环境：WSL Ubuntu-22.04，24 核 / 11 GB，`mpiexec -n 8`。

> **`chk_full`**：1.2 ns 全脉冲、**以 chk 为绘图数据源**（详见 §3）。
> `checkpointFileIntervalTime = 8e-11` → **16 帧**（0 → 1.2 ns，步长 ~80 ps，
> 两腿时刻对齐到 <1e-4 ns）；`plotFileIntervalTime = 6e-10` → 仅 3 帧（弃用）。
> 输出体积 14 MB (FL-SH) / 17 MB (SNB)。

### 2.2 `+ug` 分辨率/速度矩阵（`results/ug_resolution/matrix.md`）

| 用例 | 模式 | 核数 | 实测格数 | dx [µm] | 墙钟 |
|---|---|---|---|---|---|
| A1 | 固定块 `-nxb=64` | 8 | 512 | 0.9766 | 12.96 s |
| **A2** | 固定块 `-nxb=128` | **8** | **1024** | 0.4883 | 54.20 s |
| A3 | 固定块 `-nxb=128` | 16 | 2048 | 0.2441 | 157.07 s |
| **A4** | `-nofbs` `iGridSize=1024` | 8 | **1024** | 0.4883 | 50.30 s |
| **A5** | `-nofbs` `iGridSize=1024` | **16** | **1024** | 0.4883 | 44.86 s |

**A2**：8 核不变、只把 `-nxb` 加倍 → 格数 512→1024（分辨率 ×2）。
**A4/A5**：`iGridSize` 不变、核数 8→16 → 格数恒为 1024（逐位同解）。
→ **"+ug 分辨率只能靠核数提升"不成立**，详见 `docs/ug_resolution_finding.md`。

### 2.3 ⚠⚠ SNB 腿数值失效（本次最重要的结论）

| 量（1 ns，5e14 W/cm²） | FL-SH | SNB | 判据 |
|---|---|---|---|
| 末帧总质量 [1e-4 g/cm²]（初始 99.610） | 96.715 | 92.331（0.6 ns 曾跌至 **32.904**） | 质量不可创生；跌落后"恢复"非物理 |
| 末帧内能 ÷ 激光注入能量（应 ≤ 1） | **0.438** | **13.115**（0.2 ns 已 4.62） | 能量超注入 13 倍 |
| `fllm` 输出范围 | `[1,1]`（`fl_minmax`）/ `[0.483,1]`（`fl_harmonic`） | `[4.4e22, 1.6e23]` | SNB 腿的 `fllm` 是**限制器调用前的原始量**，非限制因子 |

**根因**：`sim_snb/flash_input/diff_advanceTherm.F90:836-841` 中
**电子各向同性通量限制器调用被注释掉**：

```fortran
     else   ! Do isotropic conduction/diffusion
!        call Diffuse_fluxLimiter(COND_VAR, Temptodiffuse, FLLM_VAR, &
!             diff_eleFlMode, blockCount, blockList)         ← 被注释
!        call Diffuse_solveScalar(Temptodiffuse,COND_VAR, DFCF_VAR, ...)  ← 亦被注释
     end if
```

只有 `if (diff_anisoCondForEle)` 分支才调用限制器，而该开关**必须 `.false.`**
（SNB 块只在 1D 均匀各向同性路径生效）→ 走 `else` → **限制器从不被调用**。

**直接证据**（同网格、同 tmax，仅改 par）：

| 腿 | `diff_eleFlMode` | 步数 | 质量 | intE/激光 | max tele |
|---|---|---|---|---|---|
| FL-SH | `fl_minmax` | 10656 | 94.258 | 0.437 | 2.15e7 K |
| FL-SH | `fl_harmonic` 0.06 | **10874** | 96.715 | 0.438 | 2.62e7 K |
| SNB | `fl_none` | 14751 | 92.331 | 13.115 | 6.76e7 K |
| SNB | `fl_harmonic` 0.06 | **14751（逐位相同）** | **92.331** | **13.115** | **6.76e7 K** |

即 **SNB 腿改限流模式完全无效**；SNB 腿恒为**无界 Spitzer 电导**，
消融面陡梯度处的电子热流可超自由流极限若干量级 → 质量/能量双重不守恒。

**影响范围**：所有基于同一 SNB 覆盖文件的场景都受此影响
（t001 / SNBOneCH / SNBOneCH_ml），且**短时运行（≤1e-10 s）不会暴露** ——
本场景 `2e-10` 短测时 intE/激光 已 4.62、质量尚守恒，必须用更长的 1 ns
与**积分守恒量**才能发现。

---

## 3. 对比绘图（chk 数据源，上下两联）

### 3.1 为什么用 chk 而不是 plt

| 维度 | chk | plt |
|---|---|---|
| 键数（实测 512 格 FL-SH） | **71** | ~25 |
| 变量上限 | 无（完整重启快照） | `plot_var` 白名单硬上限 **12** |
| dtype | **float64** | float32 |
| 覆盖量 | 含 `pion`/`eele`/`ye`/`sumy`/`gamc`/`game`/`qenl`/`mfpe`… | 仅白名单项 |

**关键事实**：chk 与 plt 的 HDF5 布局**完全相同**，但 `+ug` 均匀网格下
**所有块都是叶子块**（`node type` 每块标量 = 1），因此**无需 leaf 过滤** ——
直接按块中心 x 排序拼接即可。`coordinates` 是**块中心**（`(nblocks,3)`），
重建节点坐标须从 `bounding box` 推：`linspace(lo, hi, nxb+1)`，每块取左闭右开。

### 3.2 目录结构

```
scripts/plot_compare/
├── common/plot_common.py          # 唯一公共层：chk 直读 + 单位换算 + 绘图规范
├── pcolor/plot_xt_pcolor.py       # (1) 上下两联时空彩图
└── profiles/plot_profiles.py      # (2) 上下两联 10 时刻剖面系列图
```

### 3.3 图 (1) 时空彩图

7 个物理量各出一张：上联 FL-SH、下联 SNB。**x 轴 [µm] 线性、y 轴 [ns] 线性、
色标线性**（唯 `nele` 对数）。

```bash
$PY scripts/plot_compare/pcolor/plot_xt_pcolor.py --tag chk_full
$PY scripts/plot_compare/pcolor/plot_xt_pcolor.py --tag chk_full --vars tele nele
$PY scripts/plot_compare/pcolor/plot_xt_pcolor.py --tag chk_full --vars trad --per-leg
```

### 3.4 图 (2) 10 时刻剖面系列

在两腿**共同时间窗**内**平均取 10 个时刻**（`np.linspace` 含端点），每点取
**最近的真实 chk 帧**（不插值）。x 轴 [µm] 线性、y 轴**默认线性**
（唯 `nele` 对数）。

```bash
$PY scripts/plot_compare/profiles/plot_profiles.py --tag chk_full
$PY scripts/plot_compare/profiles/plot_profiles.py --tag chk_full --xrange -60 30
```

### 3.5 ⚠ 单位换算表（FLASH 原生 = CGS）

| 量 | chk 原生 | 绘图单位 | 换算 |
|---|---|---|---|
| `tele`/`tion`/`trad` | K | **eV** | `/ 1.1604519e4` |
| `dens` | g/cm³ | **g/cm³** | 原样 |
| `pele`/`pres` | erg/cm³ | **Mbar** | `* 1e-12` |
| `nele` | — | **cm⁻³** | 离线推导 `Ye·6.02e23·ρ` |

`nele` **不走原生场**（SNB 腿 chk 里确有 `nele`），而统一离线推导
`Ye = zbarFrac/abarInv`（`Eos_getAbarZbar.F90:130-152`），理由有二：
① FL-SH 腿**无** `NELE_VAR`，用原场会造成两腿口径不对称；
② 实测 SNB 原生 `nele` 与离线推导差 **~1%**（原生场非全分支刷新，含陈旧值）。

### 3.6 ⚠ `--per-leg`：量值悬殊时的必要开关

默认两联**共享**色标/y 范围（对比的前提）。但 `trad` 是反例 ——
FL-SH 腿 `erad ~1e12 erg/cm³`，SNB 腿 `~1e-5 erg/cm³`（**相差 17 个数量级**，
辐射在 SNB 腿基本解耦），共享色标下 **SNB 联全黑、信息量为零**。
此时加 `--per-leg`：每联独立自动定标，并在 panel title 标注该腿数值区间
`[min .. max]` 补偿色标不可比。两条建议：

- **报告主图用共享色标**（严格可比），仅当弱腿糊掉时才补 `--per-leg` 版本；
- `--per-leg` 版文件名带 `_perleg` 后缀，**不会覆盖**共享版。

### 3.7 交付物

| 路径 | 内容 |
|---|---|
| `results/pcolor/xt_<var>_chk_full.png` | 7 张时空彩图（共享色标） |
| `results/pcolor/xt_trad_chk_full_perleg.png` | `trad` 逐腿定标版（SNB 结构可见） |
| `results/profiles/profiles_<var>_chk_full.png` | 7 张 10 时刻剖面系列（共享 y） |
| `results/profiles/profiles_trad_chk_full_perleg.png` | `trad` 逐腿定标版 |

绘图规范：全英文标签、字号 ≥18 pt、DPI 450、线宽 ≥2.4。

---

## 4. 交付物

| 路径 | 内容 |
|---|---|
| `docs/ug_resolution_finding.md` | `+ug` 分辨率机制：源码证据 + 5 用例实测矩阵 + 旧结论修正 |
| `docs/snb_vs_flsh_design.md` | 两腿逐项对照 + SNB 侧可调项 A/B/C 清单 + 坑位 |
| `results/ug_resolution/matrix.{md,csv}` | 分辨率矩阵原始数据 |
| `scripts/plot_compare/` | 对比绘图套件（chk 源，上下两联；见 §3） |
| `results/cmp_2e-10/` | 2e-10 对比：dens/tele/trad 剖面、热流、限制因子、ΔTe 时空图、峰值演化 |
| `results/full_1ns/` | 1 ns 全脉冲同上 7 图 + `summary.{md,json}` |
| `results/pcolor/` + `results/profiles/` | chk 源上下两联图（§3） |
| `logs/` | 各次运行/编译的完整日志 |

---

## 5. 坑位记录（实操）

1. **`plot_var` 编译期硬上限 = 12**。`IO/IOMain/Config` 只声明
   `PARAMETER plot_var_1..12`，第 13 项起**静默忽略**（`ignoring unknown
   parameter`）→ 原 18 项 SNB 白名单中第 13–18 项从未生效。已裁至 FL-SH 9 项 /
   SNB 12 项，并纳入 `cond`（由 `DiffuseMain/Unsplit/Config` 声明，
   可反算 `q = -κ∇T`）。
2. **非固定块模式必须显式 `-nofbs`**。只"不给 `-nxb`"无效 —— FLASH 默认仍定义
   `FIXEDBLOCKSIZE` 且 `NXB=8`，par 的 `iGridSize` 被忽略（实测 iProcs=8 → 64 格）。
   且 `-nofbs` 强制并行 HDF5 IO，与 `+serialIO` 冲突。
3. `ParGeneratorExtended` 头部硬编码 `log_file="lasslab.log"`/`basenm="lasslab_"`
   （`gen_par/generator.py:375-376`），与场景值重复 → 生成后注释头部占位行。
4. `plotFileIntervalStep` 与 `plotFileIntervalTime` 是 **OR 双触发**
   （`IO_output.F90:367`）→ 注释 step 触发，只按时间输出。
5. `wsl bash -lc "<cmd>"` 的 `$var`/`$(...)` 会被 **Windows 侧外层 shell 提前展开**
   （曾致树探测回落到 `/root/FLASH/FLASH4.8`）→ 探测命令改为无 `$( )` 形式，
   条件判定一律 `if/else` 落盘标记（`$?` 不可靠）。
6. `+ug` 下 par 的 `nblockx`/`lrefine_*` 被 UG 忽略属正常；但生成器为
   `lrefine_max` 自动加的注释 `res = dir_delta/(nxb*nblock*2^(lrefine_max-1))`
   对 `+ug` 无效，勿据此判断分辨率。
7. 编译很快（1D 小规模，单次 20–60 s），改 `-nxb` 重编成本可忽略。
8. **chk 的 `unknown names` 是变量清单的权威来源** —— 不要用 `grep "^VARIABLE"`
   去猜；chk 里 `node type` 是**每块标量**（`(nblocks,)`），与 plt 同。
   另外 **plt 只有 float32**，chk 是 float64 → 定量分析优先 chk。
9. **`matplotlib.cm.get_cmap` 在 mpl ≥3.9 已移除**（本环境 3.11.1）→
   用 `plt.get_cmap(...)` 或 `matplotlib.colormaps[...]`。
10. **`imshow` 的 `extent` 必须显式给时刻端点**，否则 y 轴退化成帧号；
    用 `(x.min, x.max, t.min, t.max)` 并配 `origin="lower"`。
11. **色标共享是双刃剑**（见 §3.6）：量值跨 >10 个数量级时弱腿会全糊，
    需 `--per-leg`；且 `--per-leg` 与默认版**必须用不同文件名**，
    否则后跑的会静默覆盖前者（已修）。
12. `suptitle` 与上联 `ax.set_title` **容易重叠** → `top≈0.89` +
    `suptitle y≈0.955` + `hspace≈0.16` 是实测可用的组合。

---

## 6. 目录结构

```
t002/
├── common/t002_common.py                  # 唯一物理参数源 + WSL 工具 + 树探测
├── scripts/generate/gen_t002_inputs.py    # 两腿输入生成 + par 一致性自检
├── scripts/run/run_t002.py                # 部署→setup→make→mpiexec→收集
├── scripts/probe/ug_resolution_probe.py   # +ug 分辨率/速度矩阵
├── scripts/analysis/compare_models.py     # 对比分析出图（旧，plt 源，7 张）
├── scripts/plot_compare/                  # ★ chk 源上下两联绘图套件（§3）
│   ├── common/plot_common.py              #   chk 直读 + 单位换算 + 绘图规范
│   ├── pcolor/plot_xt_pcolor.py           #   时空彩图
│   └── profiles/plot_profiles.py          #   10 时刻剖面系列
├── docs/                                  # 本文档 + 两份专题文档
├── sim_flsh/{flash_input,flash_output}/   # FL-SH 腿（标准 FLASH 树）
├── sim_snb/{flash_input,flash_output}/    # SNB 腿（FLASHSNB 树，含 9 覆盖 F90）
├── results/{pcolor,profiles}/             # ★ chk 源上下两联图
├── results/{cmp_2e-10,full_1ns,...}/      # 旧 plt 源对比图 + 分辨率矩阵
└── logs/                                  # 运行与编译日志
```

---

## 7. 待用户决策

1. **SNB 腿限流器是否启用**：需放开 `diff_advanceTherm.F90:836-841` 的注释
   （物理代码改动）。启用后 SNB 腿才具备有限限流器，两腿才可比；
   否则 SNB 腿的结论仅代表"无界 Spitzer + SNB 修正"这一非物理组合。
2. **驱动强度/时长**：当前 `5e14 W/cm² × 1 ns` 下 SNB 腿守恒破坏严重。
   若目标是可用的模型对比，降功率或缩短时长可减轻，但根因仍是无界电导。
3. 是否把上述发现回灌到 `t001` / `SNBOneCH` / `SNBOneCH_ml` 的 README
   （它们同样受影响；现有 "稳定到 1e-10" 的说法只覆盖短时窗口）。
