# multi_opacity.py —— MULTI 不透明度 / Zeff / NLTE / EPS（F2）★最大族

> **适用仿真软件**：MULTI / matter++（Thermos、ATOMIC 等）| **官方链接**：无已核实官方 URL（uv），本地权威：`src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx`（抽取文本原存 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt，2026-11-06 已清理）+ `src/Multi1D++Portable20241128/matter++/Thermos/Readme.txt`（温度单位声明权威）
> **概要**：4×15 定宽文本表（不透明度/Zeff/NLTE/EPS，多群子表串联），解析产出 `ParsedTable`（kind 可为 `MUGROUP`/`PLANCK`/`ROSSELAND`/`ZEFF`/`ZEFF2`/`EMISSIVITY`/`NONLTE`）| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步（uk=无来源确认/uv=未人工核查）；格式权威版本 = [20 手册 §3](../../docs/20_格式规格与物理量单位手册.md)
>
> **定位说明（解析 vs 转换）**：本页 = **解析器文档**（对应 `parsers/multi_opacity.py`，读 F2 → ParsedTable）；
> **转换**（cn4 → F2 的 log10 κ 存储与群边界写出）实现在 `convert/writers_multi.py`，
> 公式与算法口径见 [../../convert/转换公式详解.md](../../convert/转换公式详解.md)。

## 1. 格式布局与计数公式

引 [20 手册 §3.1](../../docs/20_格式规格与物理量单位手册.md)（实测推翻"单一扁平表"假设）：**多群文件是 `ng` 个独立子表的串联，每个子表自带完整表头**：

```
[子表头1] [能群边界线] [rho 网格] [T 网格] [值]
[子表头2] [能群边界线] [rho 网格] [T 网格] [值] ...
```

每子表 payload 数 = `nr + nt + nr*nt`（表头 + 2 数边界线 + 网格 + 值）。行数算术精确验证（最硬证据）：

| 文件 | 算术 | 结果 |
|---|---|---|
| `AU_op03p` | 20 子表 × (1 头 + 1 边界 + 110 payload) | 2240 行 ✓ |
| `Thermos/Al_Planck.dat` | 25 子表 × (1 + 1 + 127) | 3225 行 ✓ |
| `AU_SIMPLE_PLANCK_MG` | 24 子表 × (1 + 1 + 2) | 96 行 ✓ |

子表头之间是**逐群变化的光子能量区间**（`1.0 10.0` → `10.0 50.0` → …），故"行 2 的光子能量标记"实为该群的 `(E_lo, E_hi)`。

**行 1 的 `<f2>` 是类型枚举（不是 Zbar！）**，实测于 547 个 F2-like 文件：0=EOS/理想气体类、1=含义待定（出现 34 次，风险 R2）、4=Rosseland 类、6=**ZEFF**（119 次）、7=Planck 类；其它实为 `rho0` 密度；`0.1234567` 为 LEDCOP 魔数。文本标签：`PLANCK M`/`ROSSLAN M`/`PLANCK`/`ROSSLAN`/`PS M`/`EPS M` 等 —— ⚠️ 是 **`ROSSLAN`**（非 `ROSSELAND`）。

`opbe` 类文件是**不同 KIND 的表**串联（`opbe.inhalt` 声明 4 个表号 `NPLA/NROSS/NEPS/NZ`）→ `parse_all` 拆成多张表。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/Thermos/mat_Al/Al_Planck.dat`（铝 Planck 不透明度，25 个逐群子表串联，行数算术 25×(1+1+127)=3225 行实测闭合（§1 表锚点））

**原文摘录**（前 22 行，逐字保留原始空格，含行尾空格；摘录为数据文件原文，不混入任何注释）：

```
00000000       PLANCK M        2.2000000e+001 2.1000000e+001
 1.0000000e-001 1.0000000e+000
-6.0000000e+000-5.5789474e+000-5.1578947e+000-4.7368421e+000
-4.3157895e+000-3.8947368e+000-3.4736842e+000-3.0526316e+000
-2.6315789e+000-2.2105263e+000-1.7894737e+000-1.3684211e+000
-9.4736842e-001-5.2631580e-001-1.0526316e-001 3.1578948e-001
 7.3684211e-001 1.1578947e+000 1.5789474e+000 2.0000000e+000
 3.0000000e+000 4.0000000e+000-1.3979400e+000 0.0000000e+000
 2.6315789e-001 5.2631579e-001 7.8947368e-001 1.0526316e+000
 1.3157895e+000 1.5789474e+000 1.8421053e+000 2.1052632e+000
 2.3684211e+000 2.6315789e+000 2.8947368e+000 3.1578947e+000
 3.4210526e+000 3.6842105e+000 3.9473684e+000 4.2105263e+000
 4.4736842e+000 4.7368421e+000 5.0000000e+000 2.1325541e+000
 2.1331244e+000 2.1336949e+000 2.1342651e+000 2.1348355e+000
 2.1354058e+000 2.1357418e+000 2.1334938e+000 2.1324754e+000
 2.1369298e+000 2.1511762e+000 2.2376477e+000 2.9981843e+000
 4.7966631e+000 6.0648470e+000 7.1724910e+000 7.3559933e+000
 7.5304725e+000 8.5448792e+000 8.8619491e+000 9.2408382e+000
 9.7220158e+000 3.7789260e+000 3.9275119e+000 4.0762207e+000
 4.2250455e+000 4.3739837e+000 4.5230300e+000 4.6715465e+000
 4.7428476e+000 4.7904744e+000 4.9281008e+000 4.9416682e+000
 5.0388768e+000 4.9913405e+000 5.8308102e+000 6.4675503e+000
```

**逐行说明**（格式 / 物理量与单位 / 顺序，单位与 §2 单位表一致）：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `00000000       PLANCK M        2.2000000e+001 2.1000000e+001` | 子表头（定宽，标签与数字紧贴——§4"表头紧贴"陷阱）：`table_id=0`、类型标签 `PLANCK M`（Planck 类，§1 f2 枚举 7=Planck）、`nr=22`、`nt=21`。多群文件是 25 个这样的子表串联，每个子表自带完整表头（§1） |
| 2 | ` 1.0000000e-001 1.0000000e+000` | 本群光子能量区间边界 `(E_lo, E_hi) = (0.1, 1.0)`；下一子表的这一行变为下一个区间（§1"逐群变化"）。能量单位未在 §2 单位表单独登记（兜底条 `*`，uk,uv） |
| 3–8（行 8 仅前 2 值） | `-6.0000000e+000`…` 4.0000000e+000` | 子表网格 1：`rho(nr=22)`，**log10 存储**（g/cm3 的 log10，还原需 10^x，§2）；22 个值按 4 值/行占 6 行（行 3–7 每行 4 值 + 行 8 前 2 值），从 log10=-6 到 4 |
| 8（后 2 值）–13（行 13 前 3 值） | `-1.3979400e+000`…` 5.0000000e+000` | 子表网格 2：`Te(nt=21)`，log10(eV)（§2；ZEFF 族 keV 例外见 §4）；21 个值占行 8 后 2 值至行 13 前 3 值，从 log10(0.04)≈-1.398 到 5.0 |
| 13（末值）–22 | ` 2.1325541e+000`… | 子表值段开头：`kappa(nr·nt=462)`，log10(cm2/g)（§2）；462 个值 + 尾部补零凑满 4 值/行 → 127 行 payload（§4"文件末尾补零"）；每子表 1 表头 + 1 边界 + 127 payload = 129 行，25 子表合计 3225 行（§1 算术验证） |

## 2. 物理量与单位

摘录字典 multi_opacity 族条目（完整来源详述见[字典](../../docs/eosop变量控制字典.md)；来源均为一级文档 docx）。**2026-11-14 人工裁定**：rho/Te/kappa 三轴经操作者视图交叉验证转 checked（见 §2.1）；Z（NZ 段）经 45 元素族校准裁定转 checked（见 §2.2）；兜底保持 uk,uv：

| 字段 | 物理意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `rho` | 质量密度轴（**log10** 存储，docx："不透明度为logloglog全部采用对数存储数据"） | g/cm3 | primary document | （已核查，省略） |
| `Te` | 电子温度轴（log10；docx："t[nt] log(温度eV)"）；⚠️ ZEFF 族例外为 keV（见 §4） | eV | primary document | （已核查，省略） |
| `kappa` | 不透明度（逐群子表，log10；docx："z[nr*nt]表格数据（log坐标,cm2/g)"） | cm2/g | primary document | （已核查，省略） |
| `Z` | 平均电离度 $\bar Z$（NZ kind 值段），**载荷为 log10 存储**（见 §2.2）；哨兵 -10 = log10(1e-10) 近零电离 | log10(zbar) | parser-measured | （已核查，省略） |
| `*` | 未登记列名兜底 | unknown | none | **uk, uv** |

## 2.1 mat_CELIA/C_AN.PLANCK 操作者视图交叉验证（2026-11-14 人工裁定）

用户查看工具对 `matter++/mat_CELIA/C_AN.PLANCK`（单群灰 PLANCK）渲染的边界/维度与解析器独立读出的结果**逐项吻合**（核查实现：`parsers/test/test_multi/test_celia_combined.py`）：

| 量 | 解析器读出的原生值 | 操作者视图 | 结论 |
|---|---|---|---|
| 类型标签 | `PLANCK 1`（单群灰，kind=PLANCK） | Opacity(log10(cm2/g))，无逐群边界列表 | ✓ 一致（区别于多群 "PLANCK M"） |
| 维度 | 表头 `nr=20 / nt=20` | "20 temperatures" + "20 densities" | ✓ 一致 |
| rho 轴 | log10 [-6, 2] → [1e-6, 100] g/cm3 | Density(g/cm3) : [1e-6,100] | ✓ 一致（5% 容差断言通过） |
| Te 轴 | log10 [0, 5] → [1, 1e5] eV | Temperature(eV) : [1,100000] | ✓ 一致 |
| κ 数值范围 | ±14（log10 存储） | Opacity(log10(cm2/g)) : [-14,14] | ✓ 一致 |
| 计数守恒 | 444 = 1+1+20+20+400+2(尾部补零) | — | ✓ seen == expected |

**裁定记录**：字典 rho/Te/kappa 三条目 `checked=True`（log10 存储与单位 g/cm3 / eV / cm2/g 维持原登记）；本文件同时充当 material.base MID201 的 PLANCK 与 ROSSELAND（单文件双角色）。

## 2.2 ZEFF 载荷 = log10(zbar)（2026-11-14 45 元素族校准 + 人工裁定）

**结论**：`*_Zeff.dat`（kind=ZEFF，f2=6）的值段载荷是 $\log_{10}\bar Z$ 而非线性 $\bar Z$。

**校准证据**（45 个元素 `Thermos/mat_*/[A-Z]*_Zeff.dat`，高温全电离端 $10^Z$ 应趋近核电荷数 $Z_{\rm nucleus}$）：

| 元素 | 载荷 max | $10^{\max}$ | 核电荷数 |
|---|---|---|---|
| He | 0.346 | 2.2 | 2 |
| C | 0.792 | 6.2 | 6 |
| Si | 1.1715 | 14.8 | 14 |
| Fe | 1.423 | 26.5 | 26 |
| U | 1.966 | 92.5 | 92 |

全部吻合（高压端略超核电荷数，压致电离的合理物理行为）；哨兵值 -10 = $\log_{10}(10^{-10})$（近零电离）。物理交叉验证：cn4 zbar 与 $10^Z$ 软对比中位差 **11.97%**（校准前线性误读为 931%）——核查实现 `test_multi/test_si_combined.py`。

**裁定落库**：字典 `Z` 条目 `checked=True`（kind=parser-measured，单位 log10(zbar)）；解析器 `field_units["Z"]="log10(zbar"`、`field_log10["Z"]=True`。⚠️ **ZEFF2（Z2 字段）Thermos 无样本文件**，无法族校准，本裁定不适用、语义另行核查。

## 3. 解析器 API 与用法

关键 API（签名经源码核实）：

- `parse_all(path, relpath="", *, unit_hint=None, ng_hint=None) -> list[ParsedTable]` —— **主入口**；连续同 (label, kind, id, nr, nt) 的子表归为一张多群表；多 KIND 串联拆多张
- `parse(path, relpath="", *, ...) -> ParsedTable` —— 只返回第一张表（多表文件会记 note 提醒用 `parse_all`）
- `parse_header(line: str) -> dict` —— 子表头（`table_id`/`f2`/`label`/`nr`/`nt`/`packed` 等）
- `kind_of(header, relpath) -> (kind|None, 依据)` —— KIND 判定链：标签 → f2 枚举 → 文件名 token → SESAME 数字位
- `take_numbers(lines, start, need) -> (values, pos)`、`is_marker_line(line) -> bool`
- `LABEL_RE`（宽松标签匹配）、`KIND_BY_LABEL`、`KIND_BY_F2 = {4.0:"ROSSELAND", 6.0:"ZEFF", 7.0:"PLANCK"}`、`VALUE_FIELD_BY_KIND`
- `FAMILY = "multi_opacity"`；异常：`eosop_pro.core.text.errors.ParseError`

```python
from eosop_pro.parsers.multi_opacity import parse_all

tables = parse_all(r"E:/data/matter++/Thermos/mat_Al/Al_Zeff.dat",
                   "Thermos/mat_Al/Al_Zeff.dat", unit_hint="keV")
t = tables[0]
print(t.kind, t.summary())      # ZEFF; 轴 rho × Te（log10 存储）
```

## 4. 陷阱与 unknown 清单

[20 手册 §11](../../docs/20_格式规格与物理量单位手册.md) 无本族条目；字典 uk,uv 条目（`Z` NZ 段、`*` 兜底）已在 §2 保留标记。陷阱：

- **★ ZEFF eV/keV 双套陷阱**（[20 手册 §3.3](../../docs/20_格式规格与物理量单位手册.md)，本项目第二易错处）：`*_Z.dat` = **eV**、`*_Zeff.dat` = **keV**（以 `matter++/Thermos/Readme.txt` 文件名约定为准，L2 companion）。实测反例 `Thermos/mat_Al/Al_Zeff.dat`（keV）与 `Al_Z.dat`（eV）表头与行数完全相同（均 128 行），`logT` 区间只差 `log10(1000)=3.000` —— **纯数字无法区分**。
- **四级单位仲裁链**（实现于 `registry/units_registry.py`，优先级高→低）：
  1. `companion` —— 伴随注释文件的文件名模式声明（如 `Thermos/Readme.txt`）
  2. `inline` —— 文件内嵌单位声明（`ATOMIC/*.txt`、`.coldopacity` 两行表头）
  3. `envelope` —— 兜底启发式：logT 上限判断（≥4.5→eV；≤2.5→keV），并用物理包络 `T ∈ [1e-2, 1e6] eV` 复核
  4. `config_default` —— 格式默认（F2 默认 eV）
  未声明时回退 `default:eV` 并在 `unit_source` 显式标注；裁决记录写入 h5 `/meta/units` 可追溯。
- **`ROSSLAN` 拼写**：旧写法 `ROS+LAN?D?` 正则**匹配不到** `ROSSELAND`（实测踩过）；解析器用宽松 `LABEL_RE` 并由 `norm_label` 归一。
- **表头紧贴**：多群子表头常见 id/魔数与标签紧贴（`.27100000E+04PLANCK M`、`0.1234567E+000PLANCK 1`）。
- **`f2` 枚举 0/1 语义未定**（0=EOS 类，1=含义待定，风险 R2），留 `None` 不猜。
- **文件末尾补零**：该族有凑满每行 4 字段的习惯，尾部补零显式记为 `raw_tail` 并计入 expected，避免误报 count_mismatch。
- **全部数值 log10 存储**：rho/T/值均为 log10（`matlab/outputMULTIOpacity.m` 逐行佐证）；轴还原时需 10^x。

## 4.1 cn4 来源转换口径（2026-11-14 裁定）

`eosop_pro.convert.writers_multi.write_multi_opacity_from_cn4` 支持从 cn4（IONMIX）三维不透明度块直接生成 F2 多群文件：

- cn4 的 κ（cm²/g，线性）**取 log10 后写出**（F2 存储约定 log10，writer 不再二次取对数）；全部正值校验（非正值直接报错，不静默）。
- 轴适配：`cn4_opac_to_rho_base` 把 nion(cm⁻³) 轴替换为 rho(g/cm³)（`rho = nion·⟨A⟩/N_A`）。
- 群结构：每群一个独立子表 + `(E_lo,E_hi)` 边界行，边界取 cn4 `engrup`（eV）；标签映射 ROSSELAND→`ROSSLAN M`(f2=4)、PLANCK→`PLANCK M`(f2=7)，EMISSIVITY 无一级来源映射、须显式传 `label`。
- **对比策略**：cn4 群数/边界与 MULTI 现有文件（C_1G/C_20G/C_100G）不同 → 除非边界相同，只转换+绘图，不做数值对比（用户裁定；验证见 `parsers/test/test_multi/test_cn4_to_multi.py`）。

## 5. 溯源

| 等级 | 含义 | 本族落点 |
|---|---|---|
| L1 format | 一手格式规格文档 | `MULTI使用的SESAME数据文件格式.docx`（布局/坐标制/单位） |
| L2 declared | 文件内/伴随声明 | `Thermos/Readme.txt`（ZEFF eV/keV 文件名约定）；`ATOMIC/*.txt` 内嵌单位行 |
| L3 default | 格式默认约定 | 未声明时 Te 默认 eV（显式标注） |
| L4 inferred/derived | 推导 | envelope 启发式（logT 包络复核） |
| L5 unknown | 无来源确认 | NZ 段 `Z`（uk,uv）；兜底列 `*`（uk,uv） |

一手依据：`src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx`、`src/Multi1D++Portable20241128/matter++/Thermos/Readme.txt`；2026-11-14 人工裁定证据见 §2.1（`parsers/test/test_multi/`）。
