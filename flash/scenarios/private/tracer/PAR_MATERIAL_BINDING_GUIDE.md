# PAR 物性绑定改造指南

> 适用对象：`flash/scenarios/private/tracer/` 下全部 29 个场景脚本
> 目的：让"换材料"只需改一处声明，且漏改无法通过生成流程
> 状态：**待确认稿**。确认后按 §9 逐场景执行。

---

## 0. 一句话结论

`scenarios/` 目前把**一份历史 CH 算例的 `flash.par` 全文**（337 键）当通用模板用，
其中的物性键（`ms_*A/Z`、`sim_rho*`、`eos_*TableFile`、`op_*FileName`）在运行期
**覆盖 Config 里正确的 `PARAMETER` 默认值**。由于没有任何"值比对"护栏，
这类错误可以完整通过生成 → 编译 → 运行 → 出图全流程而不报错。

---

## 1. 缺陷机制（四环，逐环有据）

| 环 | 事实 | 证据 |
|---|---|---|
| ① 模板冻结了某次算例的物性 | `_par_layers.py` docstring 自述"原 runfiles 的 flash.par 全文解析后内嵌于此"；`ms_shldA=6.509 / ms_shldZ=3.5 / sim_rhoShld=1.0`、`op_shldFileName=CH-QC-1-001.cn4` | `_par_layers.py:294–300, 64, 69` |
| ② 场景整块装载成显式赋值 | `tmp_params = dict(CH_FLASH_PAR)` → `par_gen._params.clear()` → `for k,v: par_gen.set(k,v)` | 例 `VTi/VTi1.py:243, 257, 259–260` |
| ③ 运行期 par 覆盖 Config 默认值 | `Config` 的 `PARAMETER ms_shldA REAL 50.9415` 只是**默认值** | `gen_config/generator.py:93–125` |
| ④ 无护栏 | 唯一相关规则只看 `sim_*` 的**键存在性**，不覆盖 `ms_*`，更不比对数值 | `gen_checker/relations/rules_parameter.py:20` |

**量级**：V 层按 CH 的 A/Z 反算 `abar`/`Ye` 送 EOS ⇒ t=0 压强
`3.93e11 → 5.92e12 dyn/cm²`（×15.1），屏蔽层 0.3 ns 内爆开成 −40 µm 稀薄冕区。

**旁证**：两份额外模板 `CH_FLASH_PAR`(337 键) 与 `TI_FLASH_PAR`(331 键) 的**值**差异只有 12 个键，
其中 6 个是物性/密度，3 个几何、2 个域、1 个分辨率；而 82 段激光脉冲两份**逐字节相同**。
⇒ "通用部分"确实通用，"物性部分"才是场景特有的，二者不该混在同一份快照里。

---

## 2. 铁律与分层

| 层 | 位置 | 放什么 | 不放什么 |
|---|---|---|---|
| 通用层 | `flash/input_gen/gen_par/` | 与材料无关的参数默认值（`PARAMS_1D` 135 键）、激光脉冲形状、边界/水物理开关 | 任何具体材料、任何具体几何 |
| 场景层 | 各 `<Scene>/<Scene>N.py` | **本场景**物种物性五元组、分层几何、域/网格、运行控制 | 整份 par 快照 |

**铁律**：物性五元组（`sim_rho<Cap>`、`ms_<sp>A/Z`、`eos_<sp>TableFile`、`op_<sp>FileName`）
**只能**由该场景自己声明。任何"默认物性"都不允许存在。

> 关于"跨文件树不使用模板"：判定标准是**模板是否为某一次算例的全文快照**。
> 全文快照携带那次算例的物性，跨场景复用必然错，一律退役；
> `gen_input` 的参数级默认值不携带任何具体材料，可继续作为通用层。

---

## 3. 参照实现：`SNBOneCH.py` 已经在用正确写法

这一点很重要 —— 改造不是引入新范式，而是把项目内**已验证可用**的写法提升为通用 API。

`SNB/SNBOneCH/SNBOneCH.py` 已具备：

| 能力 | 位置 |
|---|---|
| 逐物种注入 `sim_rho<Cap>` / `ms_<sp>A/Z` / `eos_*` / `op_*` | `:262–281` |
| `ms_*ZMin` → `sim_zmin<Cap>` 的正确映射（Config 只声明后者） | `:270–273` |
| 剔除 Config 未声明的残留键（`sim_targetRadius/Height`、`ms_*ZMin`） | `:227–240` |
| **键集自检**：par 的 `sim_/ms_/eos_/op_` 必须在 Config 声明 | `_undeclared_material_keys()` `:509–524` |

它缺的只有两件：① 物性仍然从 `CH_FLASH_PAR` 继承基线；② 自检只查存在性、不查值。
本次改造把这两点补齐并推广到全部场景。

---

## 4. 现有材料指纹（实测，28 个场景共 8 种）

> 来源：逐场景导入模块、调用其 `build_species_defs()` 得到的**解析后真值**，
> 已落盘 `ref/material_declarations.json`（非人工抄录）。

| 编号 | EOS/op 表文件 | ρ [g/cm³] | A | Z | 使用场景数 |
|---|---|---|---|---|---|
| M-He | `He-BADGER-TOPS-Final.cn4` | 1e-6 | 4.002602 | 2.0 | 24 |
| M-CH | `CH-QC-1-001.cn4` | 1.0 | 6.509 | 3.5 | 23 |
| M-Ti | `Ti-BADGER-TOPS.cn4` | 4.54 | 47.867 | 22 | 18 |
| M-V | `V-BADGER-TOPS.cn4` | 6.11 | 50.9415 | 23 | 11 |
| M-C | `Z06_1.00-20260902_2228.cn4` | 3.515 | 12.011 | 6 | 2 |
| M-Si | `Z14_1.00-20260708_0850.cn4` | 2.329 | 28.0855 | 14.0 | 2 |
| M-He2 | `Z02_1.00-20260708_0851.cn4` | 1e-6 | 4.002602 | 2.0 | 4 |
| M-Au | `Z79_1.00-20261009_1256.cn4` | 19.32 | 196.97 | 79 | 1 |

⚠ 注意：`M-He` 与 `M-He2` 物理相同但表文件不同；`OneC/OneSi` 系用 `Z##` 编号表而非 BADGER 表。
这是场景差异，**必须保留原样**，不得统一。

---

## 5. 场景 × 物种 映射（实测）

| 场景文件 | 物种 → 材料 | 备注 |
|---|---|---|
| `TiTi/TiTi1.py` | cham=M-He shld=M-Ti samp=M-CH tar1=M-Ti tar2/3/4/6=M-CH | **主模板** |
| `TiTi/TiTi2.py` | …, tar2=M-Ti | |
| `TiTi/TiTi3.py` | …, tar3=M-Ti | |
| `VTi/VTi1.py` | cham=M-He shld=**M-V** samp=M-CH tar1=M-Ti … | |
| `VTi/VTi2.py` | …, tar2=M-Ti | |
| `VTi/VTi3.py` | …, tar3=M-Ti | |
| `CHTi/CHTi1..3.py` | cham=M-He shld=M-CH samp=M-CH tarN=M-Ti | 无屏蔽层 |
| `CHTi_F/CHTi1..3_F.py` | 同上 | 关辐射 |
| `VCH_ml/VCH_ml.py` | cham=M-He shld=M-V samp/tar*=M-CH | **无 Ti 层** |
| `VCH_ml_F/VCH_ml_F.py` | 同上 | 关辐射 |
| `OneCH_ml/OneCH_ml.py` | cham=M-He 其余全 M-CH | |
| `OneC_ml{, _F}` | cham=M-He2 其余全 M-C | |
| `OneSi_ml{, _F}` | cham=M-He2 其余全 M-Si | |
| `SNB/SNBVTi1um.py` | cham=M-He shld=M-V tar1=M-Ti 其余 M-CH | |
| `SNB/SNBVTi2{, _ml, um}.py` | …, tar2=M-Ti | 3 个脚本 |
| `SNB/SNBVTi3um.py` | …, tar3=M-Ti | |
| `SNB/SNBOneCH_m.py`、`_ml.py` | cham=M-He 其余全 M-CH | |
| `SNB/SNBOneCH.py` | cham=M-He targ=M-CH | **已是参照实现** |
| `Au/VAuTi/VAuTi.py` | cham=M-He shld=M-V samp=**M-Au** targ=M-Ti | ⚠ 见 §12(2) |
| `layer_tracer_Ti/layer_tracer_Ti.py` | cham=M-He shld=**M-V** samp=M-CH targ=M-Ti | ⚠ 见 §12(1) |

---

## 6. 将新增的基础设施（`flash/input_gen/`）

| # | API | 作用 |
|---|---|---|
| A1 | `ParGeneratorExtended.set_species_material(name, *, rho, A, Z, eos_file, op_file=None, zmin=None)` | 写全 5 族键；`zmin` 写 `sim_zmin<Cap>`（**不写 `ms_*ZMin`**） |
| A2 | `ParGeneratorExtended.retain_species(names)` | **取代 `_params.clear()`**：只剪掉不属于本场景物种的参数族与 `sim_targetRadius/Height`、`sim_vacuumHeight` |
| A3 | `ParGeneratorExtended.assert_material_binding(species_defs)` | 写出前逐物种比对 5 族键，返回不一致清单 |
| A4 | `defaults.LASER_PULSE_5E14_82` | 82 段脉冲公开常量（现藏于模板里） |
| A5 | `gen_checker` 规则 `par_material_in_config` | par 值 vs Config 默认值**逐一比对**，不是存在性检查 |
| A6 | `generate_input_files()` 末尾统一调用 A3/A5 | 不过即 `raise`，不产出 par |

**为什么不直接 `_params.clear()`**：`PARAMS_1D` 含 `targ`、`cham` 的 `ms_/sim_/eos_/op_` 族，
以及 `sim_targetRadius/Height`、`sim_vacuumHeight`。多数场景没有 `targ` 物种。
**实测校正（2026-10-21）**：FLASH 对 par 中**未声明**的键并不 abort（`ms_shldZMin`
在各场景 par 里存在而 Config 从未声明，运行正常，只是**静默不生效**）；
真正会 abort 的是**类型不匹配**——实测把 `plotFileNumber` 写成 `0.0`（浮点）即
`RuntimeParameters_read: "plotFileNumber" with unrecognized value` 直接中止。
所以仍需"保留 + 裁剪"，但理由要改成"避免无效键与多余的 targ 族混入"，
而非"会报错"。

> ⚠ 上表 §6/§7 为**计划期设计**。实际实现改用"载入族物理基线"方案（更强、更少重复），
> 见文末 **§13 实施记录**，以 §13 为准。

---

## 7. 统一改法（6 步）

```python
from flash.input_gen.gen_par import ParGeneratorExtended
from flash.input_gen.gen_par.defaults import LASER_PULSE_5E14_82

par_gen = ParGeneratorExtended(simulation_name=SIM_NAME, dimension=1)

# ① 剪枝：只保留本场景物种的参数族（不 clear！）
par_gen.retain_species(SPECIES_LIST)

# ② 域 / 网格：本场景显式值
par_gen.set_domain(xmin=cfg["xmin"], xmax=cfg["xmax"], nblockx=cfg["nblockx"])
par_gen.set("lrefine_max", cfg["lrefine_max"])

# ③ ★ 物性五元组：本场景逐物种显式声明（唯一真源）
for sp in species_defs:
    par_gen.set_species_material(
        sp["name"], rho=sp["rho"], A=sp["A"], Z=sp["Z"],
        eos_file=sp["file"], zmin=sp.get("zmin"),
    )

# ④ 分层几何（Simulation_initBlock 引用的参数表达式）
par_gen.set("sim_shldRadius", delta_cm)
par_gen.set("sim_tar1Radius", L1)   # … tar2/3/4/6
par_gen.set("sim_sampHeight", D)

# ⑤ 激光：引用通用脉冲 + 本场景峰值
par_gen.set_pulses([{ "pulse_id": 1, **LASER_PULSE_5E14_82 }])

# ⑥ 运行控制 + 输出白名单
par_gen.set("tmax", cfg["tmax"])
par_gen.set("plotFileIntervalStep", cfg["plot_interval_step"])
par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])
for i, v in enumerate(_PLOT_VARS, 1):
    par_gen.set(f"plot_var_{i}", f"{v:<4s}")

par_gen.assert_material_binding(species_defs)      # ⑦ 门禁
par_gen.save(par_path)
```

### 7.1 改前 / 改后（以 `TiTi/TiTi1.py` 为例）

| 位置 | 改前 | 改后 |
|---|---|---|
| `:136` | `from ..._par_layers import CH_FLASH_PAR` | **删除** |
| `:243–260` | `tmp_params = dict(CH_FLASH_PAR)` + `_TARG_KEYS` 删除循环 + `_params.clear()` + 重灌循环（18 行） | 换成 §7 的 ①② |
| `:276–304` | `SHLD_MATERIAL == "V"/"Ti"/else` 三分支设 `sim_rhoShld`/`eos_shldTableFile`/`op_shldFileName` + `ms_shldA/Z` + 两条手写 `assert`（29 行） | **全部删除**，由 ③ 统一承担 |
| `:305–321` | 手写 `eos_tar*` / `op_tar*` 循环 + Ti 层三处绑定 | **全部删除**，由 ③ 承担 |
| `:527–530` | `tmp_params.items()` 取脉冲画图 | 改用 `LASER_PULSE_5E14_82` |
| `build_species_defs()` | `SHLD_MATERIAL` 决定 shld 材质 | **保留**（这就是"场景自声明"，是三处唯一真源） |

改造后 `TiTi1.py` 与 `VTi1.py` 的差异仍然只有 `SCENE VARS` 块（`SHLD_MATERIAL = "Ti"` vs `"V"`），
家族生成器机制不变。

---

## 8. 三个隐性依赖（不同步改会运行即崩）

| # | 依赖 | 处置 |
|---|---|---|
| D1 | `tmp_params` 被脉冲预诊断图复用（如 `VTi1.py:527,529`、`SNBVTi1um.py:842,844`） | 改用 `LASER_PULSE_5E14_82` |
| D2 | par 不能写 `ms_*ZMin`（Config 声明的是 `sim_zmin<Cap>`） | A1 内部自动映射 |
| D3 | 非本场景物种族 + `sim_targetRadius/Height` + `sim_vacuumHeight` 必须剔除 | A2 `retain_species()` |

---

## 9. 逐场景改动清单（精确行号锚点，实测）

> 列释义：`dict`=模板拷贝行、`clear`=`_params.clear()` 行、`loop`=重灌循环行、`save`=`par_gen.save()` 行。
> 统一动作：删除 `dict`→`loop` 区间及物性手写段；按 §7 重写；按 §5 表核实物性。

### 批次 1：TiTi / VTi（先改主模板，再跑家族生成器）

| 文件 | dict | clear | loop | save | 物性 |
|---|---|---|---|---|---|
| `TiTi/TiTi1.py` | 244 | 259 | 260 | 345 | shld=M-Ti, tar1=M-Ti |
| `TiTi/TiTi2.py` | 243 | 258 | 259 | 344 | shld=M-Ti, tar2=M-Ti |
| `TiTi/TiTi3.py` | 243 | 258 | 259 | 344 | shld=M-Ti, tar3=M-Ti |
| `VTi/VTi1.py` | 243 | 258 | 259 | 344 | shld=M-V, tar1=M-Ti |
| `VTi/VTi2.py` | 243 | 258 | 259 | 344 | shld=M-V, tar2=M-Ti |
| `VTi/VTi3.py` | 243 | 258 | 259 | 344 | shld=M-V, tar3=M-Ti |

改完 `TiTi1.py` 后必须执行：
`python flash/scenarios/private/tracer/build_titi_family.py` 与 `build_vti_family.py`，
否则 `TiTi2/3`、`VTi1/2/3` 会被主模板覆盖或与之不一致。

### 批次 2：CHTi / VCH（结构同族）

| 文件 | dict | clear | loop | save | 物性 |
|---|---|---|---|---|---|
| `CHTi/CHTi1.py` | 242 | 257 | 258 | 320 | shld=M-CH, tar1=M-Ti |
| `CHTi/CHTi2.py` | 237 | 252 | 253 | 315 | shld=M-CH, tar2=M-Ti |
| `CHTi/CHTi3.py` | 237 | 252 | 253 | 315 | shld=M-CH, tar3=M-Ti |
| `CHTi_F/CHTi1_F.py` | 237 | 252 | 253 | 315 | 同上 + 关辐射 |
| `CHTi_F/CHTi2_F.py` | 237 | 252 | 253 | 315 | 同上 |
| `CHTi_F/CHTi3_F.py` | 237 | 252 | 253 | 315 | 同上 |
| `VCH_ml/VCH_ml.py` | 214 | 229 | 230 | 283 | shld=M-V，无 Ti 层 |
| `VCH_ml_F/VCH_ml_F.py` | 237 | 252 | 253 | 324 | 同上 + 关辐射 |

### 批次 3：单材料族（OneC / OneSi / OneCH）

| 文件 | dict | clear | loop | save | 物性 |
|---|---|---|---|---|---|
| `OneCH_ml/OneCH_ml.py` | 216 | 231 | 232 | 275 | 全 M-CH |
| `OneC_ml/OneC_ml.py` | 239 | 261 | 262 | 336 | 全 M-C |
| `OneC_ml_F/OneC_ml_F.py` | 237 | 259 | 260 | 334 | 全 M-C |
| `OneSi_ml/OneSi_ml.py` | 239 | 261 | 262 | 336 | 全 M-Si |
| `OneSi_ml_F/OneSi_ml_F.py` | 237 | 259 | 260 | 334 | 全 M-Si |

### 批次 4：SNB 族

| 文件 | dict | clear | loop | save | 物性 |
|---|---|---|---|---|---|
| `SNB/SNBVTi1um/SNBVTi1um.py` | 561 | 574 | 575 | 708 | shld=M-V, tar1=M-Ti |
| `SNB/SNBVTi2/SNBVTi2.py` | 527 | 540 | 541 | 667 | shld=M-V, tar2=M-Ti |
| `SNB/SNBVTi2_ml/SNBVTi2_ml.py` | 484 | 497 | 498 | 624 | shld=M-V, tar2=M-Ti |
| `SNB/SNBVTi2um/SNBVTi2um.py` | 559 | 572 | 573 | 706 | shld=M-V, tar2=M-Ti |
| `SNB/SNBVTi3um/SNBVTi3um.py` | 561 | 574 | 575 | 708 | shld=M-V, tar3=M-Ti |
| `SNB/SNBOneCH_m/SNBOneCH_m.py` | 382 | 397 | 398 | 522 | 全 M-CH |
| `SNB/SNBOneCH_ml/SNBOneCH_ml.py` | 361 | 376 | 377 | 495 | 全 M-CH |
| `SNB/SNBOneCH/SNBOneCH.py` | 214（`p = dict`） | — | 无 clear | 305 附近 | 全 M-CH（**参照实现**，仅需去掉模板基线） |

### 批次 5：特殊结构

| 文件 | dict | clear | loop | 说明 |
|---|---|---|---|---|
| `Au/VAuTi/VAuTi.py` | 209 | 220 | 221 | 4 物种、`samp=M-Au`；**参数集与主流不同**，需单独核对 |
| `layer_tracer_Ti/layer_tracer_Ti.py` | 181 | 184 | 185 | 仅 191 行就到 `save`，section 极短；依赖 `TI_FLASH_PAR`；⚠ §12(1) |

---

## 10. 禁止项（改完用这 4 条 grep 自查）

```bash
grep -rn 'dict(CH_FLASH_PAR)\|dict(TI_FLASH_PAR)' flash/scenarios/  # 必须为空
grep -rn '_params\.clear()'                        flash/scenarios/  # 必须为空
grep -rn 'SHLD_MATERIAL =='                        flash/scenarios/  # 只允许出现在 build_species_defs 内
grep -rn 'assert.*ms_shldA'                        flash/scenarios/  # 必须为空（由 A3 承担）
```

---

## 11. 验收（5 项）

| # | 动作 | 判据 |
|---|---|---|
| V1 | 改完 `gen_input` 跑其自带测试 | 全绿 |
| V2 | 全场景重跑生成器（只出 par/Config） | 无异常；par 键数 ≥ 旧值（防丢键） |
| V3 | `audit_material_bindings.py --all` | 28+ 场景 × N 物种全 `OK`；`src_*` 显示 par 与 Config 一致 |
| V4 | 负向样本：手工把某场景 `ms_shldA` 改回 6.509 | 门禁必须 raise，并报出物种名与两处值 |
| V5 | 新旧 par 逐键 diff | 差异**只出现在物性族**；几何/激光/网格零差异 |
| V6 | 极短重算：本地 WSL `--tmax 1e-11` | `pres_shld(t=0) ≈ 3.93e11`（而非 5.92e12）；收敛正常 |

> V6 是最有说服力的一位数验证：A/Z 错则压强必差 15.1 倍。

---

## 12. 待确认的 3 个问题

**(1) `layer_tracer_Ti` 的屏蔽层到底是 V 还是 Ti？**
脚本 `:121` 声明 `shld = V`（表 `V-BADGER-TOPS.cn4`，ρ=6.11）；
但目录名、`TI_FLASH_PAR` 命名、以及 docstring 都指向 Ti。
其 `TI_FLASH_PAR` 模板恰好也是 V 值（`ms_shldA=50.9415`），所以历史结果自洽 —— 即"能跑"不代表"是本意"。
→ 请确认：**保持 V**（则改目录/模板命名）还是**改为 Ti**（则历史结果需重算）。

**(2) `Au/VAuTi` 的 `samp` 是 Au（Z79，ρ=19.32）—— 这是本意吗？**
`shld=V / samp=Au / targ=Ti` 的层序与其它家族（shld 在最前、samp 为 CH 基体）不同。
若 `samp=Au` 是对的，则它使用一张自定义表 `Z79_1.00-20261009_1256.cn4`，需确认该表已随场景分发。

**(3) 是否保留 `_par_layers.py` 作为历史对照？**
建议：字典内容导出为 `ref/flash_par_history/{CH,TI}_FLASH_PAR.json` 后，
`_par_layers.py` 改为只读 + `DeprecationWarning` 的过渡 shim，一个版本后删除。
`compare_old_par.py` 改为读 JSON，继续保留"与历史 par 逐字节对照"的能力。

---

*本文档由静态/运行期实测生成，材料指纹与行号均非人工抄录。*

---

# 13. 实施记录（2026-10-21 已完成）

> 本节是**实际交付状态**，优先级高于 §6/§7 的计划期设计。

## 13.1 最终架构

```
通用层  flash/input_gen/gen_par/defaults.py
        LAYER_TRACER_BASELINE   277 键：族内不变、与材料无关的物理/数值设置
        pulse_from_params()     只读访问器（波形只存一份真源）

通用层  flash/input_gen/gen_par/generator.py
        ParGeneratorExtended.reset_to(params)        载入基线（替代 _params.clear()）
        .retain_species(names)                       按物种裁剪（备用）
        .unset(*keys)                                局部相反覆写（如 6 群删 bounds_8..11）
        .set_species_material / .set_species_materials   逐物种声明五元组
        .material_binding_report / .assert_material_binding   写出门禁

护栏    flash/input_gen/gen_checker/relations/rules_parameter.py
        rule "par_material_in_config"                 par 值 vs Config 默认值逐一比对
        （新增 config_parameter_defaults() 解析器 + 哨兵值/权威性判据）
```

**基线的数据来源（非人工挑选）**：对同一生成机制产出的 6 份 par
（`CHTi1/2/3`、`OneCH_ml`、`OneC_ml`、`OneSi_ml`）做逐键取值比对 ——
364 个共有键中 **335 个族内取值完全相同**，其中 69 个属"物性（`ms_*A/Z`、`eos_*` 表、
`op_*` 表、`sim_rho*`、温度）与分层几何（`sim_*Radius/Height`）"已剔除，
余 266 键即族基线；再加 11 个 MGD 10 群结构键（族内 22/28 场景用 10 群，
OneC/OneSi 用 6 群，后者显式覆写并删除 `bounds_8..11`），共 **277 键**。

## 13.2 场景改造模式（统一 6 步，已落地）

```python
from flash.input_gen.gen_par.defaults import LAYER_TRACER_BASELINE, pulse_from_params

par_gen = ParGeneratorExtended(simulation_name=SIM_NAME, dimension=1)
par_gen.reset_to(LAYER_TRACER_BASELINE)          # ① 族基线（无物性）
# ② 6 群场景另加： par_gen.unset("rt_mgdBounds_8", ..._9, ..._10, ..._11)
# ③ 域/网格/运行控制        par_gen.set_domain(...) / set("tmax", ...) …
# ④ 物性五元组（唯一真源）   par_gen.set_species_materials(species_defs)
par_gen.assert_material_binding(species_defs)     # ⑤ 门禁：不一致即 raise
# ⑥ plot_var 白名单
```

`_par_layers.py` 已加退役横幅、**零 import**、内容原样保留作参考（按你的要求）。

## 13.3 验收结果

| 项 | 结果 |
|---|---|
| V1 `flash/input_gen/test` | **83 passed**（含新增规则；修复了 1 例哨兵误报 + 1 例权威性误报） |
| V2 全场景重生成 | **27/27 成功**，内置 `assert_material_binding` 全部通过 |
| V3 外部审计 | 27/27 场景 `par_material_in_config` = **True** |
| V4 负向样本 | API 层（改 `ms_shldA`→6.509）与规则层（CHTi 改成 50.9415）**均被拦截并报出键名/两处值** |
| V5 par 逐键 diff | `TiTi1` / `CHTi1` 对旧正确 par **值差异 0**；仅少 2 个无效键 `ms_*ZMin`、多 29 个显式物性声明 |
| V6 极短重算 | TiTi1、VTi1 均 `FLASH exit code: 0`；FLASH 实际加载参数经 `chk` 的 `real runtime parameters` 核对（下表） |

**V6 端到端读数（`lasslab_hdf5_chk_0000` 的 `real runtime parameters`，即 FLASH 真正生效的值）**

| 场景 | ms_shldA | ms_shldZ | sim_rhoShld | ms_tar1A | ms_tar1Z | ms_sampA/Z |
|---|---|---|---|---|---|---|
| TiTi1 | **47.867** | **22** | **4.54** | 47.867 | 22 | 6.509 / 3.5 |
| VTi1 | **50.9415** | **23** | **6.11** | 47.867 | 22 | 6.509 / 3.5 |

VTi1 这一行就是原始缺陷的判据：修复前该层按 CH 的 6.509/3.5 计算。

## 13.4 实施中发现并修复的问题（只有真跑才暴露）

1. **`PARAMS_1D` 不能当通用基线**：它是 LaserSlab demo 默认值，会把
   `diff_eleFlCoef` 从 0.08 改成 0.06、脉冲从 82 段/0.351 µm 变 5 段/1.053 µm、
   MGD 10 群变 6 群。若直接"不清空"，物理设置会被静默改写 → 改为数据驱动的族基线。
2. **整数参数被写成浮点导致 FLASH abort**：基线提取时统一 `float()` 使
   `plotFileNumber = 0.0`，FLASH 报 `unrecognized value` 中止。已改为
   "纯整数串 → int"，并复查全部 46 个整型键。
3. **规则误报**：早期手写 Config 用 `-999.0 / op_undefined / NOT SPECIFIED` 表示
   "必须由 par 指定"，且部分 Config 被手工裁掉 `ms_*` 声明 —— 已加哨兵白名单与
   "Config 必须声明 `ms_<sp>A` 才算权威"的判据。
4. **`SNBVTi*` 的域覆写依赖旧模板**：原逻辑"若 cfg 域 ≠ 模板域才写入"，
   模板退役后会 `NameError`；已改为**无条件显式写入** cfg 的域值（更稳）。

## 13.5 遗留

- `VTi/flash_output/outputfiles/run_00000{1,2}`、`TiTi/flash_output/...run_000002`
  为本轮 V6 验证产物（tmax=1e-11，仅 t=0 帧有效），可随时删除。
- `run_wsl` 的 "HDF5 files: 0" 汇总计数与实际产物不符（收集目录 glob 模式问题），
  属报告口径缺陷，不影响运行，建议后续单独修。

---

# 14. 后续修复与公开示例收尾（2026-10-21 晚）

## 14.1 VAuTi 段错误 —— 基线不该带 plot_var

**现象**：`FLASH exit 139 (SIGSEGV)`，堆栈
`io_getZeroBasedVarInfo.F90:186` ← `io_create_grid_header` ← `io_writeplotfile`
← `io_outputInitial`（写初始 plotfile 时崩）。

**根因**：`LAYER_TRACER_BASELINE` 最初含 16 个 `plot_var_*`（提取自 8 物种 par），
其中 8 条是物种名。VAuTi 只有 **4 物种**（cham/shld/samp/targ），自己写了 12 条后，
基线残留的 `plot_var_13..16 = tar3/tar4/tar6/fllm` 仍会被写入 ⇒ FLASH 请求不存在的
变量 ⇒ 段错误。

**修法**：把 `plot_var_*` 全部移出基线（277 → **261 键**）。
判据是"这条设置是否与材料/物种无关"——`plot_var` 是**输出白名单**，其内容随物种数
变化，因此不属于族基线。27 个场景本来就各自 `set()` 自己的白名单。

> 附带教训：`batch_short_run` 原先"取目录里最新的 chk_0000"，
> 场景跑挂时会拿到**上次运行**的 chk 从而误报 PASS（VAuTi 就这样被误判过）。
> 现已按"运行起始时间戳"过滤，只接受本次产出。

## 14.2 `scenarios/public/` 目录整理后的三处断裂

| 症状 | 根因 | 修复 |
|---|---|---|
| `场景包 center_evolution 加载失败: No module named ...` | `scenarios/__init__.py` 的包列表仍是旧一级名 | 改为 `("public", "flash_demo", "private")` |
| `ch_center` 进了注册表却显示"加载失败" | `register()` 的 `module_path` 缺 `public` | `flash.scenarios.public.center_evolution.ch_center` |
| 两个 sandwich 场景根本没注册 | `sandwich/__init__.py` **不导入子包** | 补容错导入（同 center_evolution 风格） |

另修：`public/__init__.py` 原是空文件 → 补 4 个专题子包的容错导入；
`test_gen_checker.py` 的 ch_center 路径同步（此前 2 个用例**静默 skip**，83→81 passed）。

## 14.3 极短验证的提示机制

新增两个文件：

- **`flash/scenarios/hints.py`**
  `is_short_run(tmax)` + `short_validation_notice(tmax, scene, where, extra)`
  —— 打印三段信息：本次只保证什么（输入生成 / setup 编译 / 启动写首帧 / 无 NaN）、
  **不产生物理结果**的原因、正式仿真应该改哪个时间参数。
- **`flash/scenarios/public/run_demo.py`** —— 公开示例统一入口：
  ```bash
  python flash/scenarios/public/run_demo.py --list
  python flash/scenarios/public/run_demo.py --scene ch_center --tmax 1e-11
  python flash/scenarios/public/run_demo.py --all --tmax 1e-11
  ```
  `WHERE_TO_CHANGE` 里登记了每个示例的正式时间参数位置：
  `ch_center` → `__init__.py: params['tmax']`（默认 1.2e-9 s）/
  `laserslab1d_local_custom.py: cfg['tmax_multiplier']`；
  `grad_dens_sandwich` → `defaults.py: DEFAULT_TMAX = 1.4e-9 s`；
  `thin_layer_sandwich_si` → `defaults_si.py: DEFAULT_TMAX = 1.2e-9 s`。

## 14.4 结果

| 项 | 结果 |
|---|---|
| `pytest flash/input_gen/test` | **83 passed / 0 skipped** |
| 27 场景重生成 + `par_material_in_config` | 全通过 |
| 27 场景极短验证（`tmax=1e-11`） | **27/27 PASS**（矩阵见 `tools_local/final_validation_matrix.csv`） |
| 公开示例极短真跑 | **3/3**：ch_center（chk_0010）、grad_dens_sandwich（chk_0005）、thin_layer_sandwich_si（chk_0033） |
| VAuTi | 修复后 **rc=0**（修复前 rc=1 + signal 11） |
