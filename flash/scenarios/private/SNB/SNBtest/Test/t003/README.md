# t003 —— SNB vs FL-SH 受控对比（烧蚀速率成因核查）

**目的**：核查「SNB 的质量烧蚀速率显著快于 FL-SH」是**物理**还是**代码/设置**问题。

**场景**：忠实复现 SNB 作者示例 `SNB_1D_laser`（`src/SNB/SNB_1D_laser/`），
在其几何/激光/材料之上做**单变量受控双仿真**。

---

## 1. 结论速览

### ★ 判决性结果（辐射通道恢复后，SNB 与 FL-SH 基本一致）

| 腿 | Ṁ_abl [g/cm²/s] | vs FL-SH | x_a [µm] | Trad_max [eV] | ρ_max |
|---|---|---|---|---|---|
| FL-SH（基准） | 5.03e5 | 1.00× | −31.10 | 63.1 | 6.74 |
| **SNB 作者原版**（辐射**关**） | **6.39e5** | **1.27×** | −34.03 | **0.04** | 12.23 |
| **SNB + 恢复辐射** | **5.34e5** | **1.06×** | **−31.69** | **68.5** | 12.11 |

> **→ 把作者的 `call RadTrans` 注释恢复后，SNB 的烧蚀速率从 1.27× 降到 1.06×，
> 烧蚀面偏差从 2.93 µm 收到 0.59 µm。**
> **"SNB 烧蚀远快于 FL-SH" 主要是代码/设置问题，而非 SNB 物理。**

| # | 结论 | 证据 |
|---|---|---|
| **C1** | ★★ **辐射被关闭是主因**：SNB 腿实际无辐射输运，少一条能量泄放 → Te 偏高 → 烧蚀偏快 | 恢复 RadTrans 后 Ṁ 由 1.27× 降至 **1.06×**；`trad` 0.04 → 68.5 eV |
| **C2** | 扣除该缺陷后，**SNB 仅快 6%** —— 属非局域预热的正常物理量级 | x_a 差 0.59 µm（原为 2.93 µm） |
| **C3** | t002 观察到的「13× 能量超注入」**不是 SNB 物理**，而是 `fl_none` + 数值失稳 | t003 两腿统一 `fl_harmonic`/0.06，质量损失均仅 ~1.5% |
| **C4** | **启动失稳的主因是 `dtmax` 过大**（数值设置），**不是** λ_g 限制缺陷 | `dtmax` 2e-12→2e-14：从 8.2 ps 中止变为跑满 0.8 ns |
| **C5** | 恢复 λ_g 限制（D1）反而**降低稳定性** | limiterON 在 284 ps 中止；基线跑满 800 ps |
| **C6** | SNB 腿的冲击压缩显著更强（ρ_max 12.1 vs 6.74，**1.8×**），且**与辐射开关无关** | 两版 SNB 的 ρ_max 均 ≈12.2 → 这是**真实的模型差异**，值得单独研究 |

> **总体判断**：
> 1. **辐射通道被关闭** → 主导了「SNB 烧蚀快」的表观现象（代码/设置问题）；
> 2. 修正后 SNB 只快 **6%** → 属物理量级；
> 3. 但 SNB 腿的**冲击压缩强度仍是 FL-SH 的 1.8×**，且不随辐射开关改变
>    → 这一条**不能排除**是 SNB 输运本身（或 D1/D2/D3）的真实效应，需进一步工作。

---

## 2. 两腿受控设计

| 项 | FL-SH 腿 | SNB 腿 |
|---|---|---|
| FLASH 树 | 标准 `~/QC/FLASH/FLASH4.8` | `~/QC/FLASH/FLASHSNB/FLASH4.8` |
| `diff_advanceTherm.F90` | 树**原生**（纯限流 SH） | 作者 SNB 版（多群非局域） |
| 其余 7 覆盖 F90 | 原生 | 作者版 |
| Config / Makefile / Simulation_* / mgd_qesh / cn4 | **逐字节相同** | **逐字节相同** |
| par | 190 键 | 190 键，**仅 basenm/log_file 不同** |
| `diff_eleFlMode` / `Coef` | `fl_harmonic` / 0.06 | **同** |

受控性由生成器自动断言：`gen_t003_inputs.py` 的 `check_controlled()`（逐文件比对）
与 `par_consistency()`（190 键逐键比对 + 重复键检查）。
`--therm-variant` / `--driver-variant` 是**为诊断而开**的显式单变量开关，默认不启用。

---

## 3. 快速使用

```bash
cd <此目录>
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe

# 输入（含补丁自检 + 受控性自检）
$PY scripts/generate/gen_t003_inputs.py

# 诊断变体（λ_g 限制 / 辐射开启）
$PY scripts/generate/make_therm_variant.py

# 短时验证
$PY scripts/run/run_t003.py --model both --tmax 1.0e-11 --tag smoke

# 完整时间（★ 必须带 --dtmax 2e-14，否则 SNB 腿启动失稳）
$PY scripts/run/run_t003.py --model flsh --tmax 0.8e-9 --tag full --dtmax 2.0e-14
$PY scripts/run/run_t003.py --model snb  --tmax 0.8e-9 --tag full --dtmax 2.0e-14

# 诊断腿
$PY scripts/run/run_t003.py --model snb --tmax 0.8e-9 --tag full_limiter \
    --dtmax 2.0e-14 --therm-variant limiter --skip-setup
$PY scripts/run/run_t003.py --model snb --tmax 0.8e-9 --tag full_radon \
    --dtmax 2.0e-14 --driver-variant radon --skip-setup

# 绘图（chk 源）+ 定量分析
$PY scripts/plot_compare/pcolor/plot_xt_pcolor.py   --tag full
$PY scripts/plot_compare/profiles/plot_profiles.py  --tag full
$PY scripts/analysis/ablation_rate.py --tag full
$PY scripts/analysis/diag_matrix.py            # 成因隔离矩阵
```

---

## 4. 运行台账（WSL，`mpiexec -n 8`，1024 格 dx≈0.2930 µm）

| tag | 腿 | dtmax | tmax 达成 | chk | 墙钟 | 结果 |
|---|---|---|---|---|---|---|
| `smoke` | FL-SH | 2e-12 | 1e-11 | 2 | 1.6 s | ✅ |
| `smoke` | SNB | 2e-12 | 8.2 ps | 1 | 4.9 s | ❌ 负 3T 内能 |
| `diag_dtmax2e14` | SNB | **2e-14** | **2e-10** | 5 | 222 s | ✅ |
| `diag_limiterON` | SNB | 2e-12 | 8.1 ps | 1 | — | ❌ 负 3T 内能 |
| `full` | FL-SH | 2e-14 | **0.8 ns** | **17** | 987 s | ✅ |
| `full` | SNB | 2e-14 | **0.8 ns** | **17** | 838 s | ✅ |
| `full_limiter` | SNB | 2e-14 | 284 ps | 6 | 327 s | ❌ 负 3T 内能 |
| `full_radon` | SNB（辐射开启） | 2e-14 | **0.8 ns** | **17** | ~1100 s | ✅ |

---

## 5. 定量结果（t = 0.8 ns）

| 量 | FL-SH | SNB（辐射关，作者原版） | **SNB（辐射开）** |
|---|---|---|---|
| 烧蚀面 `x_a` [µm] | −31.10 | −34.03 | **−31.69** |
| 致密面 `x_solid` [µm] | −30.25 | −33.75 | −31.89 |
| 临界密度面 `x_c` [µm] | 48.88 | 45.95 | 48.29 |
| ΔM_abl [1e-3 g/cm²] | 0.4236 | 0.5308 | **0.4968** |
| **Ṁ_abl [g/cm²/s]** | 5.03e5 | **6.39e5** | **5.34e5** |
| **Ṁ 相对 FL-SH** | 1.00× | **1.27×** | **1.06×** |
| ρ_max [g/cm³] | 6.74 | 12.23 | **12.11** |
| Te_max [eV] | 1650 | 1522 | 1513 |
| Ti_max [eV] | 869 | 860 | — |
| **Trad_max [eV]** | 63.1 | **0.037** ⚠ | **68.5** |
| 质量变化 | −1.43% | −1.49% | −1.46% |

判据：烧蚀面 = ρ 最陡处；致密面 = 0.5ρ_solid 的外侧跨越；`n_c = 9.05e21 cm⁻³`；
`Ṁ_abl = −dM_dense/dt`（取后 30% 时段线性拟合，避开上升沿前的静默期）。

---

## 6. 源码级诊断（详见 `docs/snb_source_diagnosis.md`）

| 编号 | 缺陷 | 位置 | 实测影响 |
|---|---|---|---|
| **D1** | 1D 分支算出 `lambda_g` 后**注释掉不用**，改用无界 λ | `diff_advanceTherm.F90:456-458`（对照 2D 第 671-672 行） | 见 §7：**不**导致启动失稳；反而恢复限制会降低稳定性 |
| **D2** | `massfrac` 在 `Conductivity` **调用之后**才赋值 | `:253` vs `:267-270`（标准版为 `:230` 先于 `:244`） | 界面邻格组分错 1 格 → 该处 κ 算错 |
| **D3** | 限流器 + 经典 SH 扩散被整段注释 | `:839-840`、`:847-849` | 电子热输运只剩 SNB 通道 |
| **D3′** | **`call RadTrans` 被注释 → 辐射完全关闭** | `Driver_evolveFlash.F90:301, 325` | `Trad` 冻结 → 少一条能量泄放 → 烧蚀偏快 |
| D4 | `QESH_VAR`(= iFactorA) 强制置 0 → 椭圆型多群求解 | `:468-469` | SNB 标准形式，**非缺陷** |
| D5 | 原始包源未打补丁（编译失败） | 3 个文件 | 已修 + 加断言 |

### 编译必需补丁（t001 六补丁基线 #1/#2/#5）
| 文件 | 补丁 |
|---|---|
| `diff_advanceTherm.F90` | `QENL_VAR,i,j,1) = -(` → `-(&`（补 4 行续行符） |
| `hy_uhd_DataReconstructNormalDir_PPM.F90` | `use hy_uhd_slopeLimiters` → `use hy_slopeLimiters` |
| `hy_uhd_getRiemannState.F90` | 同上 |
| `Makefile` | 含 `mgd_qesh.o`（`mgd_qesh.F90` 仓库原缺失，已归档） |

---

## 7. 成因隔离矩阵（`scripts/analysis/diag_matrix.py`）

| 用例 | 单变量 | 结果 |
|---|---|---|
| 基线 | dx 0.293 µm, `dtmax=2e-12` | ❌ t=8.20e-12 中止（103 步） |
| C | + **λ_g 限制启用** | ❌ t=8.12e-12 中止（87 步） |
| **D** | + **`dtmax`→2e-14** | ✅ **跑满**（10022 步，222 s） |
| B | `dtmax=2e-12`, dx≈1.172 µm | ⚠ 未中止但极病态：11.5 万步仅到 57 ps |

→ **`dtmax` 是启动失稳的唯一主导因素**；λ_g 限制与其无关。

**长时间行为**（`dtmax=2e-14`）：
- λ_g 限制**关**（作者原版）→ 跑满 0.8 ns ✅
- λ_g 限制**开**（诊断变体）→ **284 ps 中止** ❌
→ 作者关掉该限制在本配置下反而更稳健；"修复"D1 并非无代价。

---

## 8. 目录结构

```
t003/
├── common/t003_common.py                     # 唯一参数源（源自示例 flash.par）
├── scripts/generate/gen_t003_inputs.py       # 复制示例件 + 生成 par + 3 项自检
├── scripts/generate/make_therm_variant.py    # 诊断变体（λ_g / 辐射）
├── scripts/run/run_t003.py                   # 部署→setup→make→run→收集
├── scripts/analysis/diag_matrix.py           # 成因隔离矩阵
├── scripts/analysis/ablation_rate.py         # 烧蚀速率定量
├── scripts/plot_compare/{common,pcolor,profiles}/   # chk 源上下两联绘图
├── variants/                                 # 诊断变体 F90（由脚本生成）
├── docs/snb_source_diagnosis.md              # ★ 源码级诊断报告
├── sim_flsh/, sim_snb/                       # 两腿输入与输出
└── results/{pcolor,profiles,ablation}/       # 图与定量表
```

---

## 9. 坑位记录

1. **`src/SNB/SNB_1D_laser/` 是未打补丁的原始包源** —— 直接复制编译失败
   （`Cannot open module file 'hy_uhd_slopelimiters.mod'`、QENL 续行符缺失）。
   已同步为 WSL 工作副本的已打补丁版本，并加 `verify_example_patches()` 断言。
2. **`mgd_qesh.F90` 仓库原缺失**（Makefile 引用它）—— 已从 WSL 工作副本归档。
   缺它会在链接期失败。
3. **`+ug` 固定块模式**：`总格数 = iProcs × nxb`；`mpiexec -n` 必须严格等于 `iProcs`。
4. **`dtmax` 必须收紧到 2e-14**，否则该场景 SNB 腿启动即失稳（见 §7）。
5. **两腿 `dtmax` 必须一致**（本场景统一 2e-14），否则引入时间积分混淆。
6. **`wsl bash -lc` 双层展开**：`$var`/`$(...)`/shell 循环变量全部失效
   （`for f in ...; do ... $f ...` 会展开为空）→ 一律用显式绝对路径，
   或把脚本落盘后用 `wsl bash <file>` 执行。
7. **`run_leg` 可选参数位移陷阱**：新增 `driver_variant` 后若仍用位置传参，
   `par_overrides` 会落到 `driver_variant` 上并**静默失效**
   （表现为 `--dtmax` 不生效）→ 一律关键字传参。
8. `analysis/ablation_rate.py` 的**判据方向**：`x_solid`/`x_c` 必须取
   **最外侧**跨越点；`x_c` 还须限定在烧蚀面上方 80 µm 的 corona 窗口内
   （否则会被激光入射口 x≈233 µm 的人为稠密斑拉走）。
9. 绘图规范：全英文标签、字号 ≥18 pt、DPI 450、线宽 ≥2.4。
   共享色标对比为主，量值悬殊时用 `--per-leg`（文件名带 `_perleg` 区分）。
