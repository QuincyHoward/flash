# t004 —— 「辐射开关」2×2 受控矩阵（FL-SH / SNB × 辐射开 / 关）

**目的**：按用户要求，分别在 **FL-SH 侧**与 **SNB 侧**各跑「开启辐射 / 关闭辐射」
两个仿真，共 **4 个仿真**，并做四腿对比。

**几何/激光/材料**：完全继承 t003（即作者示例 `SNB_1D_laser`），
因此结论可与 t003 直接互引。

---

## 1. 关辐射的权威机制（用户指定参考 tracer `_F` 变体）

`flash/scenarios/private/tracer/VCH_ml_F/VCH_ml_F.py:293-303` 明文规定：

> 关闭辐射输运（F 变体，`RADIATION_OFF=True`）— 机制学习自参考
> `ReDo042sp_*umF` vs `*umL` 对比：**源码/setup/编译完全不变**
> （Makefile / 全部 F90 逐字节相同），**纯运行时关闭三处开关**：
> - `rt_useMGD`  `.true.` → `.false.`   （MGD 多群辐射输运）
> - `useOpacity` `.true.` → `.false.`   （不透明度）
> - `useRadTrans`         → `.false.`   （辐射输运总开关）

其余 `rt_mgd*` / `op_*` 参数原样保留（关闭后不生效）。

### ★ SNB 侧的关键差异（本场景要解决的核心问题）

用户指出「SNB 侧现在还不知道如何关闭辐射」。t003 的诊断已查明：

**SNB 侧不能只靠 par 三开关** —— 因为作者 `Driver_evolveFlash.F90:301,325`
的 `call RadTrans(...)` 被**注释掉**了。后果：

| 配置 | 结果 |
|---|---|
| 作者原版 Driver + par 三开关=`.true.` | 辐射**仍然不开**（`call RadTrans` 从未执行） |
| 作者原版 Driver + par 三开关=`.false.` | 辐射关闭 |

即：**SNB 侧辐射本来就"永远关闭"**，par 三开关形同虚设。

→ **解决办法**：SNB 侧两腿**统一使用 t003 的 `radON` 驱动变体**
（恢复 `call RadTrans`），**再用与 FL-SH 完全相同的 par 三开关**开/关辐射。
这样两侧的"关辐射"手段**逐字一致**，四腿对比才受控。

> 该变体由 t003 的 `scripts/generate/make_therm_variant.py` 生成
> （仅取消 2 行注释，498 行不变），本场景 `sync_variant()` 会复制并断言校验。

---

## 2. 四腿矩阵设计

| 腿 | tag | 树 | Driver | `diff_advanceTherm` | par 辐射三开关 |
|---|---|---|---|---|---|
| FL-SH radON  | `radon`  | 标准 FLASH | 原生（本就调用 `RadTrans`） | 原生 | `.true.` |
| FL-SH radOFF | `radoff` | 标准 FLASH | 原生 | 原生 | **`.false.` ×3** |
| SNB radON    | `radon`  | FLASHSNB | **`radON` 变体** | 作者 SNB 版 | `.true.` |
| SNB radOFF   | `radoff` | FLASHSNB | **`radON` 变体** | 作者 SNB 版 | **`.false.` ×3** |

**受控性由生成器自动断言**（`check_controlled()`）：

```
[flsh] 键数 191 vs 191; 差异键: [basenm, log_file, rt_useMGD, useOpacity, useRadTrans]
[snb]  键数 191 vs 191; 差异键: [basenm, log_file, rt_useMGD, useOpacity, useRadTrans]
[跨侧] 键数 191 vs 191; 差异键: [basenm, log_file]
```

→ **同侧两腿只差辐射三开关；跨侧只差腿标识**。

**效率设计**：辐射是纯 par 开关 → **同侧两腿共用 objdir 与二进制**，
每侧只 deploy/setup/make 一次，换 par 跑两次。故 `--side` 可分两侧并行。

---

## 3. 快速使用

```bash
cd <此目录>
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe

# 生成四腿输入（含变体同步 + 受控性自检）
$PY scripts/generate/gen_t004_inputs.py

# 短时验证（★ SNB 侧必须带 --dtmax 2e-14）
$PY scripts/run/run_t004.py --side both --tmax 1.0e-11 --tag-prefix smoke_ --dtmax 2.0e-14

# 完整四腿（两侧可并行）
$PY scripts/run/run_t004.py --side flsh --tmax 0.8e-9 --dtmax 2.0e-14
$PY scripts/run/run_t004.py --side snb  --tmax 0.8e-9 --dtmax 2.0e-14

# 四腿对比出图 + 定量表
$PY scripts/analysis/compare_4way.py --tag-prefix ""

# 单侧两腿对比（复用 t003 绘图套件，tag = radon / radoff）
$PY scripts/plot_compare/pcolor/plot_xt_pcolor.py  --tag radon
$PY scripts/plot_compare/profiles/plot_profiles.py --tag radon
```

---

## 4. 目录结构（分门别类）

```
t004/
├── common/t004_common.py                    # 唯一参数源（继承 t003 物理 + 2×2 矩阵）
├── scripts/generate/gen_t004_inputs.py      # 四腿输入生成 + 受控性自检 + 变体同步
├── scripts/run/run_t004.py                  # 运行驱动（--side 支持两侧并行）
├── scripts/analysis/compare_4way.py         # ★ 四腿对比（图 + 定量表）
├── scripts/plot_compare/{common,pcolor,profiles}/   # 单侧 2 腿绘图（chk 源）
├── variants/Driver_evolveFlash_radON.F90    # SNB 侧共用的辐射开启驱动
├── docs/                                    # 说明文档
├── sim_flsh/{flash_input, flash_output/{radon,radoff}}   # FL-SH 侧
├── sim_snb/{flash_input,  flash_output/{radon,radoff}}   # SNB 侧
├── results/
│   ├── pcolor/    xt4_<var>_full.png        # 2×2 四联时空彩图（7 张）
│   ├── profiles/  prof4_<var>_full.png      # 2×2 四联 10 时刻剖面（7 张）
│   ├── ablation/  ablation_4way_full.csv    # 时间序列
│   └── compare/   summary_4way_full.md      # 四腿定量汇总
├── logs/
└── README.md
```

---

## 4b. 运行结果与结论（tmax = 0.8 ns，1024 格，dtmax = 2e-14）

| 腿 | 墙钟 | x_a [µm] | ΔM_abl [1e-3 g/cm²] | Ṁ_abl [g/cm²/s] | ρ_max | Te_max [eV] | **Trad_max [eV]** |
|---|---|---|---|---|---|---|---|
| FL-SH radON  | 1166 s | −31.10 | 0.4236 | 5.03e5 | 6.74 | 1650 | **63.11** |
| FL-SH radOFF | 459 s  | −31.69 | 0.4244 | 4.81e5 | 6.73 | 1655 | **0.132** |
| SNB radON    | —      | −31.69 | 0.4968 | 5.34e5 | **12.11** | 1513 | **68.54** |
| SNB radOFF   | —      | **−34.03** | 0.5308 | **6.39e5** | **12.23** | 1522 | **0.047** |

### ★ 核心结论：辐射开关的效应**在两侧不对称**

| 对比 | 比值 | 解读 |
|---|---|---|
| FL-SH：关辐射 / 开辐射 | **0.956×** | 关辐射使烧蚀**略慢** 4%（基准行为） |
| **SNB：关辐射 / 开辐射** | **1.196×** | 关辐射使烧蚀**快 20%** |
| 同为 radON：SNB / FL-SH | **1.061×** | **两模型基本一致（仅差 6%）** |
| 同为 radOFF：SNB / FL-SH | **1.327×** | 偏差扩大到 33% |

**判读**：
1. **在物理自洽的「辐射开启」配置下，SNB 与 FL-SH 的烧蚀速率只差 6%**
   （x_a 差 0.59 µm）→ SNB 非局域输运带来的烧蚀增强是**物理**的，量级很小。
2. **作者原版 SNB（辐射被注释 = 等效关辐射）给出的 1.27×，正好落在
   「辐射关」分支的 1.327× 上** → 该偏差来自**辐射通道被关闭**这一
   代码/设置问题，而非 SNB 模型本身。
3. **辐射关时 SNB 反而加速（1.196×）而 FL-SH 略减速（0.956×）** —— 这一
   不对称说明 SNB 代码路径在缺辐射时还有独立的能量收支偏差（见 ），
   不能仅用少了辐射泄放一句话解释。
4. ⚠ **：SNB ≈ 12.1 vs FL-SH ≈ 6.7（1.8×），且在开/关辐射下都成立**
   → 该差异**与辐射无关**，属 SNB 输运（或 D1/D2/D3 代码缺陷）的独立效应，
   需进一步工作判定。
5. 辐射开启时  两腿均 63–69 eV ✓；关闭时降至 0.05–0.13 eV ✓
   —— 证明**三开关确实生效**，四腿配置符合设计。

### 计算开销
关闭辐射使单腿墙钟从 **1166 s 降到 459 s（2.5× 加速）** —— MGD 多群辐射
扩散是主要开销来源。

---

## 5. 判据与单位（与 t003 一致）

- 数据源 **chk**（71 键、float64；plt 受 `plot_var` 12 项上限）
- `K → eV`（/1.1604519e4）；`erg/cm³ → Mbar`（×1e-12）；`nele` 离线推导 `Ye·6.02e23·ρ`
- 烧蚀面 `x_a` = ρ 剖面最陡处；致密面 = **最外侧** 0.5ρ_solid 跨越；
  临界密度面 `n_c = 9.05e21 cm⁻³`（限定在烧蚀面上方 80 µm 的 corona 窗口内）
- **Ṁ_abl = −dM_dense/dt**，取**后 30% 时段**线性拟合（避开上升沿前的静默期）

---

## 6. 注意事项

1. **SNB 侧必须 `--dtmax 2e-14`**（t003 结论：`dtmax=2e-12` 时启动 8.2 ps 即
   因负 3T 内能中止）。FL-SH 侧不强制，但**为受控对比两侧统一使用**。
2. **SNB 侧两腿必须用 `radON` 驱动**，否则 radON 腿的辐射开不起来（见 §1）。
3. 本场景**不改动 t003 的任何文件**；`radON` 变体从 t003 `variants/` 复制而来，
   若缺失需先运行 t003 的 `make_therm_variant.py`。
4. 绘图脚本已加 `--name-suffix`（数据 tag 与输出文件名解耦），
   避免同侧 radon/radoff 输出互相覆盖。
