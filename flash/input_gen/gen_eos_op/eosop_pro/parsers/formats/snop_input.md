# snop_input.py —— SNOP 输入脚本（F6f）

> **适用仿真软件**：SNOP（K. Eidmann, *Laser and Particle Beams* **12**(2), 223–244 (1994)）
> **官方链接**：无已核实官方 URL（uv），本地权威：`src/Multi1D++Portable20241128/doc/SNOP.MANUAL`
> **概要**：解析 Fortran namelist `&daten` 输入脚本，标量字典 + `FG` 群边界数组；参数溯源文件，不产生 (rho,T) 网格
> **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §8](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

Fortran namelist `&daten` ... `/`（实测 `matter++/mat_C-1.0/C_20G.SNOP`）：

```
&daten
  NT=20, NR=20, NG=20, NP=3000,
  Z=6.0, RHO1=1.0E-6, RHO2=100.0, T1=1.0E-3, T2=100.0,
  X1=1.0E-3, X2=10.0, EQ=0.0, IGROUP=4, ...
/
```

- namelist 起点 `/^\s*&(\w+)/`，终点 `/^\s*\/\s*$/`；内部按 `,`/`;` 切分 `k=v`
- **`FG` 群边界数组**可能跨多行续行展开，用 `FG(...) = 数串` 单独正则提取（提取后从标量区剔除）
- 无计数守恒公式 —— `n_numbers_expected = None`；`n_groups` 由标量 `NG` 给出
- `kind = AUX`：**参数溯源文件**，不参与统一网格

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/mat_C-1.0/C_20G.SNOP`（碳的 SNOP 输入脚本，Fortran namelist `&daten`；前 20 行 = namelist 起点至 LINEPRO 行）

**原文摘录**（前 20 行，逐字保留原始空格）：

```
&daten
   NT       = 20,
   NR       = 20,
   NG       = 20,
   NP       = 3000,
   RHO1     = 1e-06,
   RHO2     = 100,
   T1       = 0.001,
   T2       = 100,
   X1       = 0.001,
   X2       = 10,
   IGROUP   = 0,
   F0       = 1,
   F1       = 10000,
   FG(1)    = 1,10,50,100,150,250,400,550,700,900,1200,1600,2000,2200,2400,2600,2800,3100,3500,4000,5000,
   EQ       = 0,
   Z        = 6,
   AW       = 12,
   IDEG     = 1,
   LINEPRO  = 0,
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `&daten` | namelist 起点（`/^\s*&(\w+)/`）；终点为单独 `/` 行，位于本摘录之后 |
| 2–4 | `NT = 20,` / `NR = 20,` / `NG = 20,` | 网格维度参数；本件为参数溯源文件（kind=AUX），不产生统一 (rho,T) 网格；n_groups 由 NG=20 给出 |
| 5 | `NP = 3000,` | 未登记参数（§2 兜底 `*`，uk,uv，不猜语义） |
| 6–7 | `RHO1 = 1e-06,` / `RHO2 = 100,` | 密度下/上界，g/cm3（§3 `PARAM_UNITS` 登记） |
| 8–9 | `T1 = 0.001,` / `T2 = 100,` | 温度下/上界，**keV**（uv，primary document：SNOP.MANUAL `T1 Lowest temperature (in keV)`） |
| 10–11 | `X1 = 0.001,` / `X2 = 10,` | **光子能量**下/上界，keV（uv，primary document；§2 修正史：不是密度边界，密度是 RHO1/RHO2） |
| 12 | `IGROUP = 0,` | 群划分模式 = 0：FG 由用户给定（IGROUP 1–5 为内置群划分，SNOP.MANUAL） |
| 13–14 | `F0 = 1,` / `F1 = 10000,` | 未登记参数（兜底 `*`，uk,uv） |
| 15 | `FG(1) = 1,10,50,…,5000,` | **FG 群边界数组**：21 个值 = NG+1 = 20+1，单位 **eV**（uv，primary document）——与 T1/T2/X1/X2 的 keV 双轨并存（§4 陷阱 2）；本件单行展开，亦可跨多行续行（单独正则提取后从标量区剔除） |
| 16–20 | `EQ = 0,` `Z = 6,` `AW = 12,` `IDEG = 1,` `LINEPRO = 0,` | 未逐一登记的 namelist 参数（兜底 `*`，uk,uv）；每参数一行、`k = v,` 逗号结尾写法 |


## 2. 物理量与单位（含 uk/uv 标记）

摘录自《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》`snop_input` 族（条目数 6）；单位全部逐字来自 `SNOP.MANUAL`（解析器 `PARAM_UNITS` 摘录）：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `T1` | 温度下界（lowest） | keV | primary document | uv |
| `T2` | 温度上界（highest） | keV | primary document | uv |
| `X1` | **光子能量**下界（lowest） | keV | primary document | uv |
| `X2` | **光子能量**上界（highest） | keV | primary document | uv |
| `FG` | 光子能群边界（IGROUP=0 时用户给定，NG+1 个） | eV | primary document | uv |
| `*` | 其余 namelist 参数（未逐一登记） | unknown | none | uk, uv |

**修正史**：`X1/X2` 曾被误登记为 "Density bound"——系中间产物手册笔误；SNOP.MANUAL 原文为光子能量边界（`X1  Lowest photon energy (in keV)`），字典已按修正后登记。注意 `T1/T2/X1/X2` 是 **keV** 而 `FG` 是 **eV**。

## 3. 解析器 API 与用法

真实签名（`parsers/snop_input.py`）：

- `parse_namelist(lines: list[str]) -> tuple[str | None, dict[str, object], list[float]]` —— 返回 `(名字, 标量字典, FG 数组)`
- `parse_all(path, relpath="", *, unit_hint_T=None) -> list[ParsedTable]`
- `parse(path, relpath="", *, unit_hint_T=None) -> ParsedTable`
- 常量 `PARAM_UNITS = {"RHO1": "g/cm3", "RHO2": "g/cm3", "T1": "keV", "T2": "keV", "X1": "keV", "X2": "keV", "FG": "eV"}`

```python
from eosop_pro.parsers.snop_input import parse

t = parse(r".../mat_C-1.0/C_20G.SNOP", "mat_C-1.0/C_20G.SNOP")
print(t.n_groups)       # 20（来自 NG）
print(t.group_bounds)   # FG 群边界数组（如有）
print(t.unit_source)    # declared:doc/SNOP.MANUAL
```

## 4. 陷阱与 unknown 清单

1. **X1/X2 是光子能量边界，不是密度边界**（见 §2 修正史）；密度边界是 `RHO1/RHO2`（g/cm3）。
2. **单位双轨**：`T1/T2/X1/X2` keV、`FG` eV —— 同一脚本内两种能量单位并存，勿混。
3. **只覆盖已登记 5 参数**：SNOP.MANUAL 定义的其余 namelist 参数（NP/EQ/IGROUP 等）未逐一登记，兜底 `*` 不猜。
4. **IGROUP=0 时 FG 才由用户给定**；IGROUP 1–5 为内置群划分（SNOP.MANUAL）。
5. 20 手册 §11 本族无 unknown 条目；输出文件（.PLANCK/.MUGROUP）格式**无手册**（uk 报告 §5-2，属缺失参考件）。

## 5. 溯源（L1-L5 等级表）

| 等级 | 量 | 依据 |
|---|---|---|
| L1 `format:` | `T1`/`T2`/`X1`/`X2` = keV、`FG` = eV | `SNOP.MANUAL` 逐字（`T1  Lowest temperature (in keV)` 等） |
| L1 `format:` | namelist 语法与 FG 跨行展开 | 实测 `C_20G.SNOP`；解析器 `parse_namelist` |

本地原始文档（gen_eos_op 相对路径）：

- `src/Multi1D++Portable20241128/doc/SNOP.MANUAL`（抽取文本原存 docs/extracted/SNOP__text__79a5123d.txt，2026-11-06 已清理）
- 数据实测：`src/Multi1D++Portable20241128/matter++/mat_C-1.0/C_20G.SNOP`
