# mpqeos.py —— MPQeos / FEOS 的 SESAME 包装表（F4a；`.301` / `.304` / `.305`）

> **适用仿真软件**：FEOS 包（Faik et al.，MPQeos 模型）经 Multi1D++/SESAME 包装输出的 `.301/.304/.305` 表 | **官方链接**：FEOS 项目页 https://physik.faik.de/feos.php（2026-09 联网核实）；Faik et al. 2018, DOI: 10.1016/j.cpc.2018.01.008。本地权威：`src/Multi1D++Portable20241128/doc/FEOS/MPQeos-JWGU-Documentation.pdf`
> **概要**：4 数表头 + 五段 payload 的定宽表，扩展名定 kind，文件内 GPa / MJ/kg / Kelvin 三重换算为 Mbar / Mbar·cm³/g / eV。| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §5.1](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

```
行 1 = Id  Density  NR  NT        （表头不可定宽切分，见陷阱 1）
payload = [R(NR)] [T(NT)] [P(NR*NT)] [E(NR*NT)] [Z(NR*NT)]
计数守恒 = 4 + NR + NT + 3*NR*NT
```

- **表头**：ID 字段宽 16 或 17 列**不定**，固定切分会产生污染字段（如 `'2.70000000e+00 1'`）。表头全为空格分隔正数、无紧邻负数问题 → 交给 **L2 正则**（`fortran_numbers.extract_numbers`）。
- **payload**：才用**逐文件推断**的定宽 `W = len(line)/4`（`core/numbers/fixedwidth.infer_payload_width`）。
- **kind 由扩展名**（`KIND_BY_EXT`）：`.301` = `EOS_TOTAL`（总表）、`.304` = `EOS_ELECTRON`（电子）、`.305` = `EOS_ION`（离子）；Multi1D++ 程序自动识别后缀并对单位制进行转化。

**实测基准**：`mat_Al-1.0/FEOS/Al.feos.301` 头 `37170301 2.7 192 69` → 4 + 192 + 69 + 3·192·69 = **40005** ✓

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/mat_Au-1.0/Au.301`（Au 的 SESAME 包装 EOS 总表（kind=EOS_TOTAL）；4 数表头 + 五段 payload 定宽表）

**原文摘录**（前 12 行，逐字保留原始空格与制表符）：

```
  1111           1.92800000e+001 1.23000000e+002 1.01000000e+002
 0.00000000e+000 1.92800000e-004 3.42852270e-004 6.09687133e-004
 1.08419407e-003 1.92800000e-003 3.42852270e-003 6.09687133e-003
 1.08419407e-002 1.92800000e-002 2.42720819e-002 3.05567408e-002
 3.84686574e-002 4.84291704e-002 6.09687133e-002 7.67550625e-002
 9.66288986e-002 1.21648576e-001 1.53146484e-001 1.92800000e-001
 2.16325158e-001 2.42720819e-001 2.72337239e-001 3.05567408e-001
 3.42852270e-001 3.84686574e-001 4.31625436e-001 4.84291704e-001
 5.43384229e-001 6.09687133e-001 6.84080214e-001 7.67550625e-001
 8.61205966e-001 9.66288986e-001 1.08419407e+000 1.21648576e+000
 1.36491947e+000 1.53146484e+000 1.71833181e+000 1.92800000e+000
 2.04224118e+000 2.16325158e+000 2.29143229e+000 2.42720819e+000
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `  1111           1.92800000e+001 1.23000000e+002 1.01000000e+002` | 表头 Id Density NR NT（4 数）：`Id`=1111、`Density`=1.928e+1 = 19.28（g/cc）、NR=123、NT=101。表头不可定宽切分（ID 列宽 16/17 不定，陷阱 1）——全为空格分隔正数，交 L2 正则提取 |
| 2 | `0.0  1.92800000e-004  3.42852270e-004  6.09687133e-004` | payload 第 1 行（每行 4 个定宽数字段）：R 段开头，rho[1]=0、rho[2]=1.928e-4、rho[3]、rho[4]——密度网格（g/cc → 登记 g/cm3，uv），自 rho[2] 起对数升序 |
| 3–12 | R 段续行（每行 4 数，对数升序） | rho 网格 123 点的续行：对数间隔自 1.928e-4 升至 ≈2.43 g/cc（第 12 行末）。payload 定宽 `W = len(line)/4` 逐文件推断（本文件每行 4 数） |

摘录未覆盖的后续顺序（§1 布局）：R(123) → T(101，文件内 Kelvin → 换算登记 eV，uv) → P(123×101，文件内 GPa → 换算登记 Mbar，uv) → E(123×101，文件内 MJ/kg → 换算登记 Mbar·cm3/g，uv) → Z(123×101，平均电离度段，**uk, uv**——语义待核、解析器对负值显式告警)。计数守恒 = 4 + 123 + 101 + 3·123·101 = 37497 数；kind 由扩展名判定（`.301` = EOS_TOTAL）。

## 2. 物理量与单位（含 uk/uv 标记）

SESAME 库单位：压强 GPa / 能量 MJ/kg / 密度 g/cc / 温度 Kelvin；MULTI 内部：Mbar / Mbar·cm³/g。**换算式（一级文档逐字摘录）**：

- `1GPa = 1e9Pa = 1e10 dyne/cm2 = 1e10erg/cm3 = 1e12 erg/cm2 = 1e-2 Mbar`
- `1MJ/kg = 1e3J/g = 1e10 erg/g = 1e12 erg*cm/g = 1e-2 Mbar*cm3/g`
- `Kelvin → eV`：乘 `config.EV_PER_K`（常数单一来源，不在解析器硬编码）

控制字典 `mpqeos` 族条目摘录：

| 字段 | 意义 | 文件内单位 | 登记单位 | 来源类型 | 标记 |
|---|---|---|---|---|---|
| `rho` | Mass density axis | —（g/cc） | `g/cm3` | primary document | uv |
| `Te` | Temperature axis | Kelvin | `eV` | primary document | uv |
| `P` | Pressure | GPa | `Mbar` | primary document | uv |
| `E` | Specific internal energy | MJ/kg | `Mbar*cm3/g` | primary document | uv |
| `Z` | Average ionisation（第 5 payload 段） | — | `-` | none | **uk, uv** |
| `*` | 未登记名兜底（布局只有 R/T/P/E/Z 五段） | — | `unknown` | none | **uk, uv** |

⚠️ `Z` 段 uk 的理由（照字典录，不得自行改判）：docx 布局第 5 段记为 `Z[1-NRxNT]`，但同一 docx 自述"压强、能量甚至Z等有负值，原因正在查找"；解析器实测负值并显式告警（**风险 R3：段语义待核**），未用于任何物理推断。

## 3. 解析器 API 与用法

```python
FAMILY = "mpqeos"
KIND_BY_EXT = {".301": "EOS_TOTAL", ".304": "EOS_ELECTRON", ".305": "EOS_ION"}

def parse(path, relpath="", *, unit_hint_T: str | None = None) -> ParsedTable
def parse_all(path, relpath="", *, unit_hint_T: str | None = None) -> list[ParsedTable]
```

示例：

```python
from eosop_pro.parsers.mpqeos import parse

t = parse("E:/data/mat_Al-1.0/FEOS/Al.feos.301", "mat_Al-1.0/FEOS/Al.feos.301")
print(t.summary())            # nr=192, nt=69, axes rho/Te, fields P/E/Z
print(t.field_units)          # P: Mbar, E: Mbar*cm3/g, Z: 1
```

## 4. 陷阱与 unknown 清单

1. **表头不可定宽切分**：ID 列宽 16/17 不定——16 与 15 的固定切分都会切出污染字段；必须走 L2 正则。
2. **字段宽逐文件不同**：`Al.feos.301` payload 行 60 字符（`W=15`），`mat_He/Untitled.304` 是 64 字符（`W=16`）——`W = len(line)/4` 逐文件推断，不得全局假定。
3. **`Z` 段负值（风险 R3）**：与"电离度"语义矛盾的证据在案（docx 自述负值原因未明），解析器对含负值的表显式告警，不冒充有源——字典登记 `uk, uv`。
4. **非有限值**：payload 实测含 MSVC `1.#INF` 打印的溢出（`inf`/`nan`），属源数据缺陷，解析器按原样保留并计入 notes。
5. 20 手册 §11 的 8 条 `unknown` 中**无 mpqeos 专属条目**（本族有源字段均为 L1/uv；不确定项以字典 `Z`/`*` 两条 uk 为准）。
6. 跨族铁律（20 手册 §10）：本族 P/E 与 F3 Hyades 的 CGS（`dyne/cm2` / `erg/g`）**不同**；与 F6 IONMIX 的 `J/cm3` / `J/g` 也**不同**。

## 5. 溯源

| 等级 | 记号 | 依据 | 本地定位（gen_eos_op 相对路径） |
|---|---|---|---|
| L1 | `format:` | `MULTI使用的SESAME数据文件格式.docx`（MPQeos/SESAME 节：布局与单位、三重换算式逐字来源） | `src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx` |
| L1 | `format:` | `Multi1D++ EOS and Opacity - FEOS程序说明.pdf`（`.301/.304/.305` 的换算说明，明写 `1 GPa = 1e-2 Mbar`） | `src/Multi1D++Portable20241128/doc/FEOS/Multi1D++ EOS and Opacity - FEOS程序说明.pdf` |
| L1 | `format:` | `MPQeos-JWGU-Documentation.pdf`（MPQeos 模型与单位） | `src/Multi1D++Portable20241128/doc/FEOS/MPQeos-JWGU-Documentation.pdf` |
| L2 | `declared:` | 表头 `Id Density NR NT` 自声明维度 | 逐文件 |
| L5 | `unknown` | 第 5 段 `Z` 语义待核（docx 自述负值未明） | `parsers/mpqeos.py:142-152` |

实现脚本：`eosop_pro/parsers/mpqeos.py`。uk/uv 标记不得自行改判；人工核查通过后在 `registry/field_checks.py` 置 `checked=True` 并重跑 `dump_markdown()` 同步字典。
