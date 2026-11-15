# generic_curve.py —— 通用曲线兜底（F6g）

> **适用仿真软件**：不适用（本族是 matter++ 数据树内「无专门解析器、但明显是列式数值表」文件的**保守兜底**，非特定外部软件格式）
> **官方链接**：无已核实官方 URL（uv），本地权威：[20 手册 §8.2](../../docs/20_格式规格与物理量单位手册.md)
> **概要**：剥注释 → 众数列宽 → 第 0 列作 x 轴、其余 `colN`；单位一律 unknown，**绝不猜测物理语义**
> **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §8.2](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

无固定布局 —— 兜底族的「布局」就是保守统计规则：

1. **剥离注释行**：`COMMENT_PREFIXES = ("#", "%", "REM", "rem", "c ", "C ")`（`c`/`C` 实测见 `hyades/coldopac.dat`）
2. **众数列宽**：统计各数据行数值个数取众数 `ncol`；**非众数行记异常，不静默丢**（行号写入 notes）
3. **命名**：第 0 列作 x 轴，其余列 `col1..colN`
4. `n_numbers_expected = n_numbers_seen`（偏离行已显式记录，不误报 count_mismatch —— .ini 文件实测踩过）

适用文件实例：`hyades/ionpot.dat`、`PowerLaws/*.dat`、`XrayMassCoef/*`、`Crystal/*.dat`、`Thermos/*.ini`。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/hyades/ionpot.dat`（Scofield 电离电势表，兜底族典型实例；前 22 行 = 头部注释块 + z=1/2/3 三个元素节）

**原文摘录**（前 22 行，逐字保留原始空格）：

```
c
c__Ionization potentials (keV)
c__From J.H. Scofield - UCID-16848
c
c__Last Update: September 26, 2000
c
c
c__hydrogen
c
z = 1
.013527
c
c--helium
c
z = 2
.024587,.054416
c
c__lithium
c
z = 3
.005392,.075638,.122451
c
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1–9 | `c` / `c__…` / `c--…` 注释块 | 注释行（无缩进）：声明物理量 `Ionization potentials`、单位 **keV**、出处 `J.H. Scofield - UCID-16848`、更新日期。注意：本文件注释前缀为裸 `c`/`c__`/`c--`（无空格），不匹配解析器 `COMMENT_PREFIXES` 的 `c ` 项（该项实测针对 `hyades/coldopac.dat` 的 `c ` 写法）；列语义按 §2 纪律不猜测，全部列 uk,uv |
| 10 | `z = 1` | 元素锚点：Z=1（hydrogen，注释第 8 行） |
| 11 | `.013527` | Z=1 的第 1 个逐电荷态电离电势值（keV，注释第 2 行声明；语义仍属 uk 猜测层，未写回字典） |
| 13–16 | `c--helium` → `z = 2` → `.024587,.054416` | 元素节三行模式：注释标题 → `z = N` 锚点 → 值行；Z=2 给 2 个值（逐电荷态，**逗号分隔**单行排布）；元素按 Z 递增排序 |
| 18–21 | `c__lithium` → `z = 3` → `.005392,.075638,.122451` | Z=3 给 3 个值（每元素值个数 = Z） |
| — | 全文件规律（兜底实测） | 无固定列宽（每元素 1~Z 个数一行）→ 兜底族适用；实测本文件众数列宽 11、453 行偏离众数被记 notes 剔除（expected==seen，不触发 CountMismatch）——印证 §1 规则 2 |


## 2. 物理量与单位（含 uk/uv 标记）

摘录自《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》`generic_curve` 族（条目数 1）：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `*` | 兜底族——列语义不文档化，绝不猜测 | unknown | none | uk, uv |

`unit_source = "none（列语义无文档 → 不猜测）"`。本族**全列 uk,uv** —— 设计立场即无来源可用，人工核查前保持。

## 3. 解析器 API 与用法

真实签名（`parsers/generic_curve.py`）：

- `is_comment_line(line: str) -> bool`
- `parse_all(path, relpath="", *, unit_hint_T=None) -> list[ParsedTable]`
- `parse(path, relpath="", *, unit_hint_T=None) -> ParsedTable`

```python
from eosop_pro.parsers.generic_curve import parse

t = parse(r".../matter++/hyades/ionpot.dat", "hyades/ionpot.dat")
print(t.summary())     # 列宽直方图 + 众数列宽
print(t.notes[:3])     # 注释原文（前 5 条）—— 供人工判定物理量
```

notes 至少含：列宽直方图、偏离众数行号（如有）、注释原文（前 5 条）、兜底告警。

## 4. 陷阱与 unknown 清单

1. **绝不因文件名猜物理量** —— 命名必须来自文档或注释证据（20 手册 §8.2 原文纪律）。文件名 `ionpot.dat` 看似电离电势，但**无生成者文档，不写回字典**（uk 报告 §3.8 明确：猜测层与事实层分离）。
2. **非众数行不静默丢**：行号显式记入 notes；但 `expected == seen`，不触发 CountMismatch。
3. **无数值行** → 抛 `ValueError`（`no numeric rows`）。
4. 20 手册 §11 条目 #7（**必须复述**）：

   > `generic_curve` 全部列 `unknown`（L5）—— 兜底族，列语义无文档，溯源定位 `generic_curve.py:89`，实现脚本 `parsers/generic_curve.py`。

## 5. 溯源（L1-L5 等级表）

| 等级 | 量 | 依据 |
|---|---|---|
| L5 `unknown` | 全部列（x 轴 + colN） | 兜底族无任何文档 → 不猜测（20 手册 §8.2/§11） |
| L1 `format:` | 剥注释/众数列宽策略 | 解析器设计约定（20 手册 §8.2 登记为策略，非单位依据） |

本地原始文档（gen_eos_op 相对路径）：

- 无族级原始文档（这正是 uk 的原因）
- 数据实例：`src/Multi1D++Portable20241128/matter++/hyades/ionpot.dat` 等
- 盲读猜测（GUESS ONLY，不作为来源）：ionpot.dat 疑为 eV 电离电势表——仅猜测，未写回字典；历史猜测报告 §3.8 已随 temp_docs 整合删除（缺失清单存档于 `eosop_pro/docs/20_格式规格与物理量单位手册.md` 附录 C.3 #5）
