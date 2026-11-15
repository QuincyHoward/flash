# feos_aux.py —— FEOS 辅助参数文件（F6e；`.PAR` / `.cst` / `.mexport` / `.critical.dat` / `.isobaric.dat` / `.INV`）★ 诚实登记型

> **适用仿真软件**：FEOS 包 / ShowEOS 的参数与导出文件 | **官方链接**：FEOS 项目页 https://physik.faik.de/feos.php（2026-09 联网核实）。⚠️ 官方 URL 仅证实 FEOS 包本体；本族键值对的物理语义无文档。本地权威：`src/Multi1D++Portable20241128/doc/FEOS/FEOS-Package-Documentation2016.pdf` §4（**仅给出注释符约定 `%` / `#`**，不含键值语义）
> **概要**：分节 + `key = value` 的参数/导出文件，统一为 `AUX` 表；价值在**参数溯源**，不参与统一网格，不猜物理语义。| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §5.3](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

共同特征（非标准数值表格）：

```
% 或 # 开头    = 注释（逐字来自 FEOS PDF §4）
REM 开头      = 注释（同样跳过）
节标题行       = 无 "=" 且非纯数值的独立行（如 "Q-table" / "Material-7386:"）
key = value   = 键值对（key 匹配 [A-Za-z_][\w.\-\[\]%]*，value 为行内其余文本）
```

解析产物：`sections`（节名 → kv 字典，隐式 `__head__` 节收容首节前的 kv）+ `numbers`（全文 L2 数值提取，原样保留）。

计数守恒：`n_numbers_seen = len(numbers)`，`n_numbers_expected = None`——键值语义无公式可推导，诚实登记。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/mat_B/B.PAR`（FEOS 辅助参数文件（硼 B）；分节 + key = value——aux 三族中最小者）

**原文摘录**（前 40 行，逐字保留原始空格与制表符）：

```
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% This file contains all the data needed for  
%% 1) computing an EOS for a material included in the material db  
%% 2) showing an EOS table (isotherms, isochores, isentropes) or   
%%    calculating the principal Hugoniot from this table           
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Material: aluminum (Al)                                        
%% Last change: 2021-06-19 19:07:51                   
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% EOS table calculation (feos):                                  
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

                   Computation-Settings

Material-Number = 104005       % Material number in FEOS parameter database
Maxwell_Flag = 1             % Maxwell construction desired? (0: no, 1: yes)
SoftSphere_Flag = 0          % Replace TF cold curve for densities < Rsolid with 
                             %   soft sphere function? (0: no, 1: yes)
UserCalculations_Flag = 1    % Perform user-defined calculations? (0: no, 1: yes)

%%%%%%%%%%%%%%%%%%%%%%%%

                   Q-table

% Distribution of densities:
Rhonorm = 2.34     % Norm in g/cm^3
% Rhoratiox defines number of logarithmically distributed density 
%   points in range Rnorm*1.0e(x-1) to Rnorm*1.0ex, x=-6...6
% Attention: Take care of lower density library limit!
Rhoratio-6 = 0
Rhoratio-5 = 0
Rhoratio-4 = 4
Rhoratio-3 = 4
Rhoratio-2 = 10
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1–6 | `%%...%%` 注释块（文件用途说明） | `%` 开头 = 注释（FEOS PDF §4 唯一有据约定）：自述文件包含计算 EOS 与显示 EOS 表/Hugoniot 所需全部数据，逐字跳过 |
| 7–8 | 空行 ×2 | 空行跳过 |
| 9–12 | `%%` 注释块（Material: aluminum (Al) / Last change: 2021-06-19） | 注释：材料名与最后修改时间戳——参数溯源线索（L2 `declared:`） |
| 13–14 | 空行 ×2 | 空行跳过 |
| 15–17 | `%%` 注释块（EOS table calculation (feos)） | 注释：本节为 feos EOS 表计算参数 |
| 18, 20, 26, 28, 30 | 空行 | 空行跳过 |
| 19 | `Computation-Settings` | 节标题：无 `=` 且非纯数值的独立行 → `sections` 新节（隐式 `__head__` 之前的行归其收容） |
| 21 | `Material-Number = 104005` | key=value：104005 与同目录 `B.feos` 行 0 SESAME#（104005）一致——参数溯源线索；键值语义仍 `uk, uv`（不因 key 名冒充有源） |
| 22 | `Maxwell_Flag = 1` | key=value + 行内 `%` 注释（注释不入 kv 值以外登记，`value` 取行内其余文本） |
| 23–24 | `SoftSphere_Flag = 0`（+ 跨行注释续行） | key=value；其解释注释在第 24 行续行（仍 `%` 注释，跳过） |
| 25 | `UserCalculations_Flag = 1` | key=value |
| 27 | `%%%%%%%%` | 注释分隔线，跳过 |
| 29 | `Q-table` | 节标题（无 `=` 且非纯数值独立行）→ 新节 |
| 31 | `% Distribution of densities:` | 注释：密度分布说明 |
| 32 | `Rhonorm = 2.34` | key=value：2.34 与 `B.feos` 行 0 rho0（2.34）一致；行内注释自述单位 g/cm^3（`%` 后文本随 value 保留，语义仍 uk, uv） |
| 33–35 | `% Rhoratiox defines...` 注释块 | 注释：解释 Rhoratio-x 键族定义（对数密度分段点数），跳过 |
| 36–40 | `Rhoratio-6 = 0` ... `Rhoratio-2 = 10` | key=value 组（key 匹配 `[A-Za-z_][\w.\-\[\]%]*`，连字符键合法）：-6/-5/-4/-3/-2 各对数段密度点数配置 |

全文件性质：非数值表格（AUX），`n_numbers_expected = None` 诚实登记；解析产物为 `sections`（节名 → kv）+ `numbers`（全文 L2 数值提取原样保留，`raw_values`，uk, uv）。本样例为三族 aux 文件（.PAR/.cst/.mexport）中最小的 `B.PAR`（6546 字节）。

## 2. 物理量与单位（含 uk/uv 标记）——诚实登记型

控制字典 `feos_aux` 族条目摘录：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `*`（raw_values） | raw_values (auxiliary parameter file) | `unknown` | none | **uk, uv** |

字典理由（照录）：辅助参数文件的未解码载荷——无可指认的一级来源（中间产物草稿不作依据）——待人工核查。解析器 `unit_source = "none (辅助参数文件)"`。**不得因 key 名（如看起来像 T/P/rho）冒充有源单位**；语义按 key 名溯源仅作线索，不参与 (rho,T) 统一网格。

## 3. 解析器 API 与用法

```python
FAMILY = "feos_aux"

def parse(path, relpath="", *, unit_hint_T: str | None = None) -> ParsedTable
def parse_all(path, relpath="", *, unit_hint_T: str | None = None) -> list[ParsedTable]
def parse_sections(lines: list[str]) -> tuple[dict[str, dict[str, str]], list[str]]
    # -> ({节名: {key: value}}, notes)
```

示例：

```python
from eosop_pro.parsers.feos_aux import parse

t = parse("E:/data/mat_B/B.PAR", "mat_B/B.PAR")
print(t.summary())          # kind=AUX，sections + raw_values
print(t.notes[:2])          # "解析出 N 节 / M 个 key=value" 等
```

## 4. 陷阱与 unknown 清单

1. **20 手册 §11 条目 #4（必须复述）**：F4 `feos_aux` 的 `raw_values`——辅助参数文件，语义无文档 → 标 `unknown`（`feos_aux.py:78,80`）。
2. **注释符是唯一有据的格式约定**（`%`/`#`，FEOS PDF §4）；`REM` 为解析器兼容性扩展跳过。
3. **参数溯源用途**：本族文件价值在于与伴随注释文件互补的参数溯源记录；**不参与统一网格**、不进 EOS/不透明度物理分析路径。
4. `parse_sections` 对既无 `=` 又含数值的行不作节标题处理（数值行由 `numbers` 兜底原样保留）。
5. 与 `feos_tabdata.md` / `feos_native.md` 同属 FEOS 生态诚实登记型：三者均不猜测语义，`.301` 兄弟文件可作数值侧旁证（见 `feos_native.md`）。

## 5. 溯源

| 等级 | 记号 | 依据 | 本地定位（gen_eos_op 相对路径） |
|---|---|---|---|
| L1 | `format:` | `FEOS-Package-Documentation2016.pdf` §4（仅注释符 `%`/`#` 约定） | `src/Multi1D++Portable20241128/doc/FEOS/FEOS-Package-Documentation2016.pdf` |
| L2 | `declared:` | 数据文件自身的节标题与 key 名（语义线索，**非单位证据**） | 逐文件 |
| L5 | `unknown` | `raw_values`：键值/数值语义无一级文档 | `parsers/feos_aux.py:78,80` |

实现脚本：`eosop_pro/parsers/feos_aux.py`。uk/uv 标记不得自行改判；人工核查通过后在 `registry/field_checks.py` 置 `checked=True` 并重跑 `dump_markdown()` 同步字典。
