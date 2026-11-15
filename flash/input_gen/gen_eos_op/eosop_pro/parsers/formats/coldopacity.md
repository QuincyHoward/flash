# coldopacity.py —— 冷不透明度（F6b）

> **适用仿真软件**：matter++（`*.coldopacity` 冷/灰不透明度表，实测同类文件 67 个）
> **官方链接**：无已核实官方 URL（uv），本地权威：数据文件自身两行表头（逐文件声明）
> **概要**：解析「第 1 行列名 / 第 2 行逐列单位」的两行自描述表头表——全库最直白的单位声明
> **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §8/§8.1](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

```
Eph	miu          ← 第 1 行：列名（制表符分隔）
eV	cm2/g        ← 第 2 行：逐列单位（制表符分隔，按列对齐）
<空行>
10	486606.52638
10.1617	469396.24406
```

（实测 `matter++/ColdOpacity/Al.coldopacity`）

- 表头在前 6 行内取前两个**非空行**（`parse_two_line_header`）；列名数 ≠ 单位数即抛 `ParseError`
- 数值区跳过空行逐行取数；**每行列数必须 = 表头列数**（不符抛 `CountMismatch`）
- 第 1 列作 x 轴（axis），其余列作物理量场（fields）
- 无行数公式 —— 行数即数据点数

**变体写法**：`hyades/coldopac.dat` 用另一套写法（`c` 开头注释 + `z = N` + 点数列），不属两行表头范式。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/ColdOpacity/Al.coldopacity`（Al 冷不透明度表，两行自描述表头范式；前 8 行 = 两行表头 + 空行 + 前 4 个数据点）

**原文摘录**（前 8 行，逐字保留原始空格）：

```
Eph	miu
eV	cm2/g
	
	
10	486606.52638
10.1617	469396.24406
10.3261	452791.00338
10.4931	436776.37403
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `Eph<TAB>miu` | 第 1 行表头：列名（制表符分隔）——第 1 列 Eph 作 x 轴（axis），第 2 列 miu 作物理量场 |
| 2 | `eV<TAB>cm2/g` | 第 2 行表头：逐列单位按列对齐（uv，in-file declaration）——Eph = eV、miu = cm2/g；与 §2 单位表典型值一致；本文件头不带 `#` 前缀（§2 实测的 Ac.coldopacity 头带 `#`，两写法并存，均按「前两个非空行」取头） |
| 3–4 | 仅含制表符的空行（各一个 TAB） | 表头与数值区之间的空行；解析器跳过空行逐行取数 |
| 5–8 | `10<TAB>486606.52638` 等 4 行 | 数值区两列：Eph（eV）升序 10 → 10.4931…、miu（cm2/g）随光子能量上升而下降（冷不透明度谱）；每行列数必须 = 表头列数（2），不符抛 CountMismatch；行数即数据点数 |


## 2. 物理量与单位（含 uk/uv 标记）

摘录自《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》`coldopacity` 族（条目数 3）：

| 字段 | 意义 | 单位（典型值） | 来源类型 | 标记 |
|---|---|---|---|---|
| `Eph` | 光子能量轴（典型；逐文件声明） | eV | in-file declaration | uv |
| `miu` | 不透明度列（典型；逐文件声明） | cm2/g | in-file declaration | uv |
| `*` | 逐文件兜底列（由两行头实时登记） | unknown | in-file declaration | uv |

实测两行头原文（Ac.coldopacity）：`#Eph<TAB>miu` + `#eV<TAB>cm2/g`；字典 unit 为**典型值**，以逐文件头为准。

## 3. 解析器 API 与用法

真实签名（`parsers/coldopacity.py`）：

- `parse_two_line_header(lines: list[str]) -> tuple[list[str], list[str], int]` —— 返回 `(names, units, payload_start)`
- `parse_all(path, relpath="", *, unit_hint_T=None) -> list[ParsedTable]`
- `parse(path, relpath="", *, unit_hint_T=None) -> ParsedTable`

```python
from eosop_pro.parsers.coldopacity import parse

t = parse(r".../matter++/ColdOpacity/Al.coldopacity", "ColdOpacity/Al.coldopacity")
print(t.summary())       # nr≈, axes=Eph, fields=miu
print(t.field_units)     # miu = cm2/g（读自文件第 2 行）
print(t.unit_source)     # declared:inline (2-line header)
```

## 4. 陷阱与 unknown 清单

1. **设计性不确定（20 手册 §8.3）**：单位从文件自身头部**读出**而非硬编码；文件**未声明**时解析器**不给单位**（`unit_source` 显示实际来源）——保守行为是设计使然。
2. **hyades/coldopat.dat 变体**：`c` 开头注释 + `z = N` 写法不经两行表头范式，由兜底族（generic_curve）或相应族处理，勿硬套本解析器。
3. **表头列名/单位数不等** → `ParseError`（抛错不猜）。
4. 20 手册 §11 本族无 unknown 条目；L2 范式最佳范例（20 手册 §8.1）。

## 5. 溯源（L1-L5 等级表）

| 等级 | 量 | 依据 |
|---|---|---|
| L2 `declared:` | 全部列单位 | 数据文件自身第 1 行列名 / 第 2 行单位（逐列对齐，逐文件） |
| L1 `format:` | 两行表头结构 | 实测 67 个同类文件一致；解析器 `parse_two_line_header` |

本地原始文档（gen_eos_op 相对路径）：

- 无族级外部手册 —— **文件内声明即权威**
- 数据实测：`src/Multi1D++Portable20241128/matter++/ColdOpacity/Al.coldopacity`（及同目录 67 个同类文件）；变体 `src/Multi1D++Portable20241128/matter++/hyades/coldopac.dat`
