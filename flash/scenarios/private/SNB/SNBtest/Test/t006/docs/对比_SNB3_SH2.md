# SNB×3 + FL-SH×2 五腿对比 —— 辐射开关 × 电子限流模式

> 场景: `flash/scenarios/private/SNB/SNBtest/Test/t006`
> 数据源: chk（float64，71 键），时间窗 0 → 0.8 ns，网格 1024 格（`+ug`，iProcs=8 × nxb=128）
> 生成: `flnone_test/plot_5leg.py`　校验: `flnone_test/verify_md_images.py`

---

## 0. 结论速览

| # | 腿 | 热传导 | 辐射 | `diff_eleFlMode` | 说明 |
|---|---|---|---|---|---|
| 1 | **SNB radON (fl_harmonic)** | 作者 SNB 多群 | 开 | `fl_harmonic` | 基线 |
| 2 | **SNB radON (fl_none)** | 作者 SNB 多群 | 开 | `fl_none` | ★ 本报告的新增腿 |
| 3 | **SNB radOFF (fl_harmonic)** | 作者 SNB 多群 | 关 | `fl_harmonic` | — |
| 4 | **FL-SH radON** | 限流 Spitzer-Härm | 开 | `fl_harmonic` | 对照 |
| 5 | **FL-SH radOFF** | 限流 Spitzer-Härm | 关 | `fl_harmonic` | 对照 |

**三条主要结论**

1. **`diff_eleFlMode = "fl_none"` 在 SNB 场景下可正常运行、无异常**，且与 `fl_harmonic` 的结果
   **逐位相同** —— 该参数在 SNB 电子路径上是 **no-op**（详见 §2 与 §5.1）。
2. **保护 SNB 腿的不是限流器**，而是 SNB 多群非局域公式本身；SNB 热流始终建立在
   **无界 Spitzer 电导**之上（`diff_advanceTherm.F90:364`），再由多群扩散做非局域修正。
3. **辐射开关对两个模型的作用方向相反**：关辐射使 FL-SH **减速**（0.956×），
   却使 SNB **加速**（1.196×）—— 这是本矩阵最值得注意的物理信号（§4.1）。

---

## 1. 实验设计

### 1.1 受控性（par 键级差分）

五条腿的 par 均由核心模块生成，两两之间**只允许**出现预先声明的差异键。
本报告涉及的三类配对：

| 配对 | 允许差异键 | 实测 |
|---|---|---|
| 腿 1 vs 腿 2（限流模式） | `diff_eleFlMode` + `basenm`/`log_file` | 3 个键，全部在范围内 ✓ |
| 腿 1 vs 腿 3（辐射开关） | `rt_useMGD`/`useOpacity`/`useRadTrans` + `basenm`/`log_file` | 5 个键 ✓ |
| 腿 4 vs 腿 5（辐射开关） | 同上 | 5 个键 ✓ |

> ★ 两个检查缺一不可：**帧时间戳**（证明按同一时刻配对）与 **par 键级差分**
> （证明基线干净）。本工作曾因遗漏后者而得到过一次**虚假的差异结论**，详见 §5.1。

### 1.2 三条并列前提（缺一不可）

| # | 前提 | 违反后果 |
|---|---|---|
| 1 | **`gr_hypreUseFloor = .false.`** | FLASH 默认 `.true.` → HYPRE 隐式扩散解失真 → 过度压缩 → ρmax 冲高后崩塌（12.1 → 0.26，质量守恒破裂） |
| 2 | **`dtmax = 2.0e-14`** | `dt` 增长越过稳定阈值（**必要条件，非充分条件**） |
| 3 | **SNB 腿 `driver-variant = radon`** | 作者原版把 `call RadTrans` 注释了 → 辐射永不推进、par 三开关失效 |

### 1.3 判据铁律

1. `dtmax` 是否生效**不能看 par 文本**（会被命令行覆写）——必须读 chk 里 `real scalars` 的
   `dt` **实测值**。五条腿均实测 `dt` 全程钳位 `2.000e-14` ✓。
2. **`dt` 钳位正确 ≠ 结果正确** —— 还须检查 ρmax 走势与总质量守恒。
3. **帧配对必须按时间戳**，不能按帧序号（chk 间隔是纯 IO 参数，各腿可以不同）。

---

## 2. 核心实验：`fl_none` vs `fl_harmonic`

### 2.1 静态分析给出的预期

`snb_package/diff_advanceTherm.F90` 的**各向同性电子分支**中，两处关键调用**均被注释**：

```fortran
838|     else   ! Do isotropic conduction/diffusion
839|!        call Diffuse_fluxLimiter(COND_VAR, Temptodiffuse, FLLM_VAR, &
840|!             diff_eleFlMode, blockCount, blockList)
847|!        call Diffuse_solveScalar(Temptodiffuse,COND_VAR, DFCF_VAR, ...)
```

而本场景 `diff_anisoCondForEle = .false.` → **不进入**各向异性分支（`:818` 那个调用点也不进入）。
⇒ `diff_eleFlMode` 在电子路径上**没有任何存活的消费者**，故预期二者**逐位相同**。

### 2.2 实测判决

**短时可行性测试（先做）**：`tmax = 1×10⁻¹¹ s`，chk 加密到 `1×10⁻¹²`（11 帧）

- 正常退出：`exiting: reached max SimTime`，无 `DRIVER_ABORT` / `Negative 3T internal energy`
- 墙钟 **14.9 s**
- `dt` 全程钳位 `2.000e-14` ✓
- 受控短时基线（`smoke_harmonic`，同设置 `fl_harmonic`）墙钟相当

**全长测试（后做）**：`tmax = 0.8 ns`，17 帧

- 正常退出：`exiting: reached max SimTime`，无 `DRIVER_ABORT`
- 墙钟 **1376.3 s**（比基线 SNB radON 腿同量级）
- `dt` 全程钳位 `2.000e-14` ✓；ρmax 1.0400 → **12.1112**；Te_max **1513.09 eV**；Trad_max **68.5380 eV**
- 按时间戳配对 **17/17 帧**，其中**存在差异的帧数 = 0/17**

| 变量 | max&#124;Δ&#124;（全时间窗上确界） | max 相对差 | 判定 |
|---|---|---|---|
| `dens` | **0.000000e+00** | 0.000e+00 | 逐位相同 |
| `tele` | **0.000000e+00** | 0.000e+00 | 逐位相同 |
| `tion` | **0.000000e+00** | 0.000e+00 | 逐位相同 |
| `trad` | **0.000000e+00** | 0.000e+00 | 逐位相同 |
| `pele` | **0.000000e+00** | 0.000e+00 | 逐位相同 |
| `pres` | **0.000000e+00** | 0.000e+00 | 逐位相同 |

**量级分类：逐位相同（bit-identical to the last digit）**

⇒ **短时腿（t = 1e-11 s）与全长腿（t = 0.8 ns）两个尺度上，结论一致且互相印证。**
静态分析的预期得到实测确认：`diff_eleFlMode` 在 SNB 电子路径上是 **no-op**。

完整报告见 `flnone_test/results/flnone_vs_harmonic.md`（全长）与
`flnone_test/results/smoke_flnone_vs_harmonic.md`（短时）。

### 2.3 核心判据图

![fl_none 与 fl_harmonic 逐帧比对：末帧剖面叠加 + 相对差时间走势](../images/flnone5/fig1_flnone_vs_harmonic.png)

*图 1 — 三个剖面（Tₑ / ρ / T_rad）都在 t = 0.800 ns 末帧；两条曲线完全重合，
`max|Δ|` 标注在每个面板内均为 `0.0e+00`；右下角为相对差随时间的走势（恒为 0，故落在坐标轴下界）。*

---

## 3. 五腿定量对比

### 3.1 定量表（t = 0.8 ns）

| 腿 | x_a [µm] | x_c [µm] | Ṁ [g/cm²/s] | ρmax | Te_max [eV] | Trad_max [eV] |
|---|---|---|---|---|---|---|
| SNB radON (fl_harmonic) | −31.69 | −1.75 | 5.3393e+05 | 12.111 | 1513.1 | 68.538 |
| **SNB radON (fl_none)** | **−31.69** | **−1.75** | **5.3393e+05** | **12.111** | **1513.1** | **68.538** |
| SNB radOFF (fl_harmonic) | −34.03 | −1.12 | 6.3882e+05 | 12.231 | 1522.1 | 0.047 |
| FL-SH radON | −31.10 | −13.28 | 5.0346e+05 | 6.739 | 1649.7 | 63.110 |
| FL-SH radOFF | −31.69 | −12.65 | 4.8139e+05 | 6.731 | 1655.2 | 0.132 |

> ★ 腿 1 与腿 2 的**每一个数字都完全相同**（不是"接近"，是逐位相同）——
> 这正是 §2 判决在定量表上的体现。
> 完整时间序列见 `images/flnone5/metrics_5leg.csv`，同表见 `images/flnone5/metrics_5leg.md`。

### 3.2 烧蚀指标

![烧蚀面轨迹 x_a(t) 与烧蚀速率 Ṁ 柱状对比](../images/flnone5/fig4_metrics_5leg.png)

*图 2 — 左：烧蚀面轨迹；右：后期线性拟合的烧蚀速率。*

### 3.3 电子温度剖面

![五腿电子温度剖面（8 个时刻）](../images/flnone5/fig2_profiles_tele_5leg.png)

*图 3 — 颜色表示时刻（0 → 0.8 ns）。*

### 3.4 质量密度剖面

![五腿质量密度剖面（8 个时刻）](../images/flnone5/fig3_profiles_dens_5leg.png)

*图 4 — 致密靶区的压缩与稀疏波结构。*

### 3.5 电子温度时空图

![五腿电子温度时空分布](../images/flnone5/fig5_xt_tele_5leg.png)

*图 5 — x–t 分布，共享色标。*

### 3.6 辐射温度剖面（辐射开关的直接判据）

![五腿辐射温度剖面（8 个时刻）](../images/flnone5/fig6_profiles_trad_5leg.png)

*图 6 — 辐射开腿 T_rad 达数十 eV，辐射关腿被压到 0.05–0.13 eV，开关确实生效。*

---

## 4. 物理讨论

### 4.1 辐射开关效应（**作用方向相反**）

| 模型 | Ṁ(辐射开) | Ṁ(辐射关) | 关/开 | 方向 |
|---|---|---|---|---|
| FL-SH | 5.0346e+05 | 4.8139e+05 | **0.956×** | 关辐射 → **减速** |
| SNB | 5.3393e+05 | 6.3882e+05 | **1.196×** | 关辐射 → **加速** |

两个模型对同一开关的响应方向相反，幅度也不同（−4.4% vs +19.6%）。
这说明**辐射与电子热输运之间存在耦合**，而耦合方式依赖于热流模型本身——
是后续需要用实际烧蚀速率（而非仅 x_a）来约束模型的重要依据。

### 4.2 模型效应（同辐射状态）

| 辐射状态 | SNB / FL-SH | x_a 对比 |
|---|---|---|
| 开 | **1.061×** | −31.69 vs −31.10 µm |
| 关 | **1.327×** | −34.03 vs −31.69 µm |

辐射开时两模型只差 6%（非局域修正的量级很小）；关辐射后差异放大到 33%。

### 4.3 ⚠ 未解问题：SNB 的 ρmax 系统性偏高

| 腿 | ρmax [g/cm³] |
|---|---|
| FL-SH radON / radOFF | 6.739 / 6.731 |
| SNB radON / radOFF | **12.111 / 12.231** |

SNB 两腿的峰值密度比 FL-SH 高 **≈1.8×**，且**开/关辐射都成立** → 与辐射无关。
该偏差自 t004 起就存在，**原因尚未定位**，是当前最值得追查的一条线索。

---

## 5. 附录

### 5.1 SH 侧 `gr_hypreUseFloor` 单变量 A/B

**动机**：扫描留存 par 时发现一个配置代际差异——

| 数据 | `gr_hypreUseFloor` | 状态 |
|---|---|---|
| `sim_snb/radon`、`sim_snb/radoff` | `.false.`（显式） | 修复后 ✓ |
| `sim_snb/smoke_radon`、`smoke_radoff` | **缺** → 默认 `.true.` | **修复前**（已废弃） |
| `sim_flsh/radon`、`sim_flsh/radoff` | **缺** → 默认 `.true.` | 早于该修正 |

该键在标准树中确实存在且是**运行时参数**：
`Grid/GridSolvers/HYPRE/Config:92`、`gr_hypreInit.F90:123`。
因此必须实测界定"现有 FL-SH 两腿是否受影响"，否则五腿对比的 SH 半边存疑。

**做法**：短时（`tmax=1e-11`）单变量 A/B，只翻这一个键，其余逐键对齐。

**结果**（`flnone_test/results/sh_hypre_ab.md`）：

| 变量 | max&#124;Δ&#124; | max 相对差 |
|---|---|---|
| `dens` | 9.55e-11 | 9.19e-11 |
| `tele` | 1.17e+01 | 3.45e-05 |
| `tion` | 3.56e+00 | 8.42e-06 |
| `trad` | 8.18e+01 | 9.01e-04 |
| `pele` | 2.40e+04 | 4.85e-08 |
| `pres` | 2.89e+04 | 5.00e-08 |

**整体最大相对差 9.01e-04（≤0.1%）→ 分类「轻微」**。

**结论**：该键对 FL-SH 路径**不是逐位中性**，但影响 ≤0.1%，**远小于本报告所讨论的
物理差异（6%–33%）**。因此现有 FL-SH 两腿的结论**仍然可用**，只需在引用其数值时
注明这一 ≤0.1% 的配置不确定性。

**对照价值**：同一个键在 **SNB** 侧曾造成 **1.6×** 的物理级差异（导致崩塌）。
⇒ 该键的危害是**路径相关**的：它钳位的是"隐式求解的那个变量"，
SNB 多群解对钳位敏感，而 SH 单标量解基本不敏感。**不能因 SH 侧量级小就认为它普遍无害。**

### 5.2 ⚠ 已废弃的数据

`sim_snb/smoke_radon`、`sim_snb/smoke_radoff` 是 `gr_hypreUseFloor` 修正**之前**产生的，
**不得**再作为基线使用（其 par 里没有该键）。t006 早先的 `*_smoke.png` 与
`summary_4way_smoke.md` 同源，引用时需注意。

作为替代，本报告使用**受控短时基线** `sim_snb/smoke_harmonic`：
与 `sim_snb/smoke_flnone` **逐键对齐**，唯一差别就是 `diff_eleFlMode`。

### 5.3 复现命令

```bash
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
cd flash/scenarios/private/SNB/SNBtest/Test/t006/flnone_test

$PY run_flnone_test.py --stage prep            # 生成 par + 键级差分自检
$PY run_flnone_test.py --stage smoke           # 短时可行性（~15 s）
$PY run_flnone_test.py --stage smoke-base      # 受控短时基线
$PY run_flnone_test.py --stage smoke-compare   # 早期判决
$PY run_flnone_test.py --stage full            # 全长（~24 min）
$PY run_flnone_test.py --stage check           # chk 健康检查
$PY run_flnone_test.py --stage compare         # 全长逐帧判决
$PY run_flnone_test.py --stage sh-hypre-ab     # 附录 A/B
$PY run_flnone_test.py --stage plot            # 五腿出图

$PY verify_md_images.py ../../t006/docs/对比_SNB3_SH2.md   # 校验图片引用
```

> 若 objdir 已被清理，加 `--rebuild`（会重新 deploy/setup/make，约 10 min）。

### 5.4 图片引用的写法（保证 md 中能正常显示）

本文件位于 `t006/docs/`，图片位于 `t006/images/flnone5/`，故引用一律写成：

```markdown
![说明](../images/flnone5/fig1_flnone_vs_harmonic.png)
```

三条硬规则：

1. **相对路径相对于 .md 文件自身**（不是相对于仓库根）→ 必须带 `../` 上跳一层；
2. **只用 POSIX 正斜杠 `/`**，反斜杠 `\` 在多数渲染器上会断链；
3. **文件名不含空格**（无需 `%20` 编码）。

`flnone_test/verify_md_images.py` 会逐条检查以上三点并验证文件确实存在，
可作为文档提交前的门禁。

### 5.5 文件清单

| 路径 | 内容 |
|---|---|
| `flnone_test/run_flnone_test.py` | 驱动：par 生成 / 运行 / 比对 / 编排（全部调用核心模块） |
| `flnone_test/plot_5leg.py` | 五腿绘图（本报告全部图） |
| `flnone_test/verify_md_images.py` | md 图片引用校验器 |
| `flnone_test/results/flnone_vs_harmonic.md` | §2 全长逐帧比对报告 |
| `flnone_test/results/smoke_flnone_vs_harmonic.md` | 短时腿早期判决 |
| `flnone_test/results/sh_hypre_ab.md` | §5.1 A/B 报告 |
| `scene/sim_snb/flash_input/snb_flnone.par` | fl_none 全长 par |
| `scene/sim_snb/flash_input/snb_flnone_smoke.par` | fl_none 短时 par |
| `scene/sim_snb/flash_input/snb_harm_smoke.par` | 受控短时基线 par |
| `scene/sim_flsh/flash_input/flsh_h{T,F}_smoke.par` | §5.1 的 A/B par 对 |
| `images/flnone5/*.png` | 本报告全部图（6 张） |

---

## 6. 已知问题 / 待办

1. **§4.3** SNB `ρmax ≈ 1.8×FL-SH` 的成因未定位（最高优先级）。
2. `sim_snb/smoke_*`、`sim_flsh/{radon,radoff}` 均早于 `gr_hypreUseFloor` 修正：
   - SH 侧影响已量化为 ≤0.1%（§5.1），可接受；
   - SNB 侧 smoke 数据已废弃（§5.2）。
   若追求完全一致，可把 SH 两腿的 par 补上 `gr_hypreUseFloor = .false.` 后重跑。
3. ~~`SNB/docs/05_坑位清单.md` 的 P1 条目需按 §2 的实测结果更正。~~
   **已随本报告一并更正完成** —— 见 `SNB/SNB/docs/05_坑位清单.md` 的 P1
   更正块（2026-09-12）。
