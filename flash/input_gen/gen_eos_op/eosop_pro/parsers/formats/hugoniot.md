# hugoniot.py —— 雨贡纽曲线（F6c）

> **适用仿真软件**：Hyades / FEOS（`*.hug` 由 SESAME/FEOS 工具链导出）
> **官方链接**：无已核实官方 URL（uv），本地权威：数据文件自身 `# name [unit]` 注释头（逐文件声明）
> **概要**：解析 `#` 注释列头（列名与单位写在方括号里）的雨贡纽单列曲线表，兼容带缩放因子写法
> **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §8/§8.1](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

第 0 行是 `#` 注释，但**列名与单位都在方括号里** → 直接解析为轴/场的单位（「注释即证据」，L2 范式之一）：

```
# Rho[g/cm^3]  T [eV]         P [Mbar]  E [erg/g]      Us [km/s]      Up [km/s]
2.7059315e+000 2.6771096e-002 1.1245127e-002 3.9018342e+009 4.2385122e+000 ...
```

（实测 `matter++/hyades/sesame/eos_41.hug`，157 行）

- 列数由注释头决定，payload 数据行**必须同宽**（不符抛 `CountMismatch`）
- 第 0 列登记为轴（axis），其余为场（fields）
- 无行数公式 —— 单列曲线表，行数即数据点数

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/mat_Al-1.0/Al.feos.hug`（FEOS 工具链导出的 Al 雨贡纽曲线，前 8 行 = 注释列头 + 前 7 个数据点）

**原文摘录**（前 8 行，逐字保留原始空格）：

```
# Rho [1.000000e+000 g/cm^3]  T [1.000000e+000 eV]  P [1.000000e+012 dyne/cm^2]  E [1.000000e+000 erg/g]  Us [1.000000e+005 cm/s]  Up [1.000000e+005 cm/s]
2.700000e+000  2.585257e-002  2.578641e-004  1.041546e+005  0.000000e+000  0.000000e+000
2.762324e+000  2.598183e-002  1.876615e-002  7.959303e+007  5.512012e+000  1.243633e-001
2.770417e+000  2.611174e-002  2.121301e-002  1.011632e+008  5.525820e+000  1.404527e-001
2.783347e+000  2.637351e-002  2.514512e-002  1.409700e+008  5.548098e+000  1.661380e-001
2.793950e+000  2.663791e-002  2.839078e-002  1.784976e+008  5.566558e+000  1.871821e-001
2.803189e+000  2.690495e-002  3.123553e-002  2.147879e+008  5.582790e+000  2.055103e-001
2.815405e+000  2.731055e-002  3.502065e-002  2.678932e+008  5.604460e+000  2.297297e-001
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `# Rho [1.000000e+000 g/cm^3]  T [1.000000e+000 eV]  P [1.000000e+012 dyne/cm^2]  E [1.000000e+000 erg/g]  Us [1.000000e+005 cm/s]  Up [1.000000e+005 cm/s]` | 第 0 行 `#` 注释列头（`[缩放因子 单位]` 写法，逐文件声明 uv）：列顺序固定 Rho、T、P、E、Us、Up 共 6 列；单位 Rho g/cm^3、T eV、P dyne/cm^2（记 `dyne/cm^2 (x1.0e+12)`）、E erg/g、Us/Up cm/s（记 `(x1.0e+5)`）——P、Us、Up 与 §2 典型值（Mbar、km/s）不同，以本文件头为准（§4 陷阱 1） |
| 2 | `2.700000e+000  2.585257e-002  2.578641e-004  1.041546e+005  0.000000e+000  0.000000e+000` | 首数据点（冷态起点）：rho=2.7 g/cm^3、T≈0.0259 eV、P、E、Us=0、Up=0（无冲击态）；列序与列头一致 |
| 3–8 | 后续数据行（每行 6 列，空格分隔） | 沿雨贡纽路径 Rho ↑ 伴随 T/P/E ↑；数据行必须与列头同宽（6 列），不符抛 CountMismatch；无行数公式，行数即数据点数 |


## 2. 物理量与单位（含 uk/uv 标记）

摘录自《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》`hugoniot` 族（条目数 7）：

| 字段 | 意义 | 单位（典型值） | 来源类型 | 标记 |
|---|---|---|---|---|
| `Rho` | 质量密度（逐文件声明） | g/cm3 | in-file declaration | uv |
| `T` | 温度（逐文件声明） | eV | in-file declaration | uv |
| `P` | 压力（逐文件声明） | Mbar | in-file declaration | uv |
| `E` | 比内能（逐文件声明） | erg/g | in-file declaration | uv |
| `Us` | 冲击波速度（逐文件声明） | km/s | in-file declaration | uv |
| `Up` | 质点速度（逐文件声明） | km/s | in-file declaration | uv |
| `*` | 逐文件兜底列（见 `# [...] [unit]` 头） | unknown | in-file declaration | uv |

## 3. 解析器 API 与用法

真实签名（`parsers/hugoniot.py`）：

- `parse_column_header(line: str) -> list[tuple[str, str]]` —— 解析 `(列名, 单位)` 列表
- `parse_all(path, relpath="", *, unit_hint_T=None) -> list[ParsedTable]`
- `parse(path, relpath="", *, unit_hint_T=None) -> ParsedTable`

```python
from eosop_pro.parsers.hugoniot import parse, parse_column_header

print(parse_column_header("# Rho [1.0e+000 g/cm^3]"))
# → [("Rho", "g/cm^3 (x1.0e+0)")]
t = parse(r".../mat_Al-1.0/Al.feos.hug", "mat_Al-1.0/Al.feos.hug")
print(t.field_units)   # 逐文件提取，Al.feos.hug 的 P 为 dyne/cm^2
```

`unit_source = "declared:inline (comment column header)"`。

## 4. 陷阱与 unknown 清单

1. **设计性不确定（20 手册 §8.3，必须复述）**：本族单位**不硬编码**，从文件自身注释头**读出**——不同实例单位可不同。实测 `mat_Al-1.0/Al.feos.hug` 声明 `P [1.000000e+012 dyne/cm^2]`，与 `eos_41.hug` 的 `P [Mbar]` **不同**。若文件**未声明**，解析器**不给单位**（记 unknown）——这是正确的保守行为。
2. **`[scale unit]` 缩放因子剥离**：`Rho [1.000000e+000 g/cm^3]` 中数字是列值缩放倍数，单位记 `g/cm^3 (x1.0e+0)` 形式保留（数值化 `:.1e`，解析失败回退原文）。
3. **注释行列数与数据列数不一致**时以**数据列数为准**并在 notes 标注。
4. 20 手册 §11 本族无 unknown 条目；字典 unit 列仅为**典型值**，绘图以解析器逐文件提取（`table.field_units`）为准。

## 5. 溯源（L1-L5 等级表）

| 等级 | 量 | 依据 |
|---|---|---|
| L2 `declared:` | 全部列单位 | 数据文件自身第 0 行 `# name [unit]` 注释（逐文件） |
| L1 `format:` | 列头语法（两种写法） | 实测 `eos_41.hug` / `Al.feos.hug`；解析器 `_COL_RE`/`_SCALE_UNIT_RE` |

本地原始文档（gen_eos_op 相对路径）：

- 无族级外部手册 —— **文件内声明即权威**
- 数据实测：`src/Multi1D++Portable20241128/matter++/hyades/sesame/eos_41.hug`、`src/Multi1D++Portable20241128/matter++/mat_Al-1.0/Al.feos.hug`
