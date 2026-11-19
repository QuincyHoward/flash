# hyades_eos.py —— Hyades / SESAME ASCII（F3；含 hyades_eos / hyades_opacity / sesame_dat 三族）

> **适用仿真软件**：Hyades（1D Lagrangian 辐射流体）/ Multi1D++ 数据生态的 Hyades 与 SESAME ASCII 输出 | **官方链接**：无已核实官方 URL（uv），本地权威：`src/Multi1D++Portable20241128/doc/Hyades 数据格式说明.doc`
> **概要**：5×15 定宽 ASCII 表，行 1 自由文本注释 + 行 2 五数表头，一个解析器实现 EOS（`eos_*`）、不透明度（`opc_*`）与 SESAME 库（`.sesame` / 默认回退）三个声明族。| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §4](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

逐字来自 `Hyades 数据格式说明.doc`：

```
行 1 = 自由文本注释（材料名 + 生成历史），例如：
    ALUMINUM    LANL SESAME #3711 DATED: 22581 11483
    DT          LANL SESAME #5271 DATED: 91374 92882
    Gold        QEOS DATED: 062795
行 2 = id  zbar  abar  rho0  L，其中 L = 2 + NR + NT + 2*NR*NT
行 3 起 = NR  NT  RHO(1..NR)  T(1..NT)  A1(1..NR*NT)  A2(1..NR*NT)
          （T-major，rho 快变；场索引 [i_Te][j_rho]）
```

两个 (NR×NT) 数组的含义：

| 族 | 文件 | A1 / A2 |
|---|---|---|
| `hyades_eos` | `eos_*` | `[P, E]` |
| `hyades_opacity` | `opc_*` / `Opacity/` 路径 | `[Rosseland, Planck]`（见判序） |
| `sesame_dat` | `.sesame` / 默认回退 | 同 `eos_*` |

**opc_* 自动判序**：依同一 doc——"本来应该存储 Planck 平均不透明度的位置用 0 代替"。故若一个数组**全为 0**，另一个即 Rosseland（`_opacity_order`：a1 全零 → `[Planck, Rosseland]`，否则 `[Rosseland, Planck]` 并记 notes）。

**实测基准**：

| 文件 | `L` | 解出 (NR, NT) | 备注 |
|---|---|---|---|
| `sesame/eos_11.dat` | 2577 | (50, 25) | DT |
| `sesame/eos_21.dat` | 4743 | (43, 54) | Glass |
| `sesame/eos_41.dat` | 2004 | (44, 22) | Aluminum |
| `Opacity/opc_1031.dat` | 2931 | (31, 46) | Polyethylene |

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/hyades/sesame/eos_41.dat`（SESAME Aluminum EOS 总表；5×15 定宽 ASCII，L=2004 → (NR,NT)=(44,22)，与 §1 实测基准同文件）

**原文摘录**（前 12 行，逐字保留原始空格与制表符）：

```
ALUMINUM    LANL SESAME #3711 DATED: 22581 11483
    41     1.30000000E+01 2.69820000E+01 2.75681460E+00    2004
 4.40000000E+01 2.20000000E+01 0.00000000E+00 2.75681460E-04 4.04645046E-04
 5.93937702E-04 8.71781324E-04 1.27959999E-03 1.87819593E-03 2.75681460E-03
 4.04645046E-03 5.93937702E-03 8.71781324E-03 1.27959999E-02 1.87819593E-02
 2.75681460E-02 4.04645046E-02 5.93937702E-02 8.71781324E-02 1.27959999E-01
 1.87819593E-01 2.75681460E-01 4.04645046E-01 5.93937702E-01 8.71781324E-01
 1.27959999E+00 1.87819593E+00 2.75681460E+00 4.04645046E+00 5.93937702E+00
 8.71781324E+00 1.27959999E+01 1.87819593E+01 2.75681460E+01 4.04645046E+01
 5.93937702E+01 8.71781324E+01 1.27959999E+02 1.87819593E+02 2.75681460E+02
 4.04645046E+02 5.93937702E+02 8.71781324E+02 1.27959999E+03 1.87819593E+03
 2.75681460E+03 0.00000000E+00 2.56922879E-05 7.99989660E-05 9.99987075E-05
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `ALUMINUM    LANL SESAME #3711 ...` | 行 1 自由文本注释：材料名 ALUMINUM + LANL SESAME 号 #3711 + 生成日期（22581 11483）。仅作锚点（`sesame_number`/材料识别），不参与计数（§4 陷阱 4） |
| 2 | `41  1.30000000E+01 2.69820000E+01 2.75681460E+00  2004` | 五数表头：`id`=41、`zbar`=13.0（平均电离/核电荷，e）、`abar`=26.982（g/mol）、`rho0`=2.75681460（g/cm3，uv）、`L`=2004（= 2 + NR + NT + 2·NR·NT，可反解 (NR,NT)=(44,22)，与 §1 实测基准一致） |
| 3 | `44  22  0.0  2.75681460E-04  4.04645046E-04` | payload 开始：前 2 数 = NR=44、NT=22；随后按顺序进入 RHO 网格（rho[1]=0、rho[2]、rho[3]），定宽 5×15（每行 5 个 15 列字段），格式为 e 科学计数 |
| 4–11 | rho 网格续行（每行 5 数，对数升序） | RHO(1..44) 的续行（g/cm3，uv）：行 3 已给 3 点，这 8 行给 40 点；对数间隔自 rho[2]≈2.76e-4 升至 ≈1.88e+2 |
| 12 | `2.75681460E+03  0.0  2.56922879E-05  ...` | 第 1 数 = RHO[44]（密度网格收尾，对数升序至 ≈2.76e+3 g/cm3）；其后 4 数 = T[1..4]（T[1]=0，随后对数升序）——进入温度网格：文件内 keV（一级文档逐字），解析器换算登记 `eV`（uv） |

摘录未覆盖的后续顺序（§1 布局铁律）：T(1..22) → A1(1..44×22=968) → A2(1..968)，T-major、rho 快变，场索引 [i_Te][j_rho]；本样例（eos_* 族）A1/A2 = [P, E]（dyne/cm2 / erg/g，均 uv）。尾部凑满每行 5 字段的补零填充归 `raw_tail`（uk, uv）。**三族头部结构相同**：`opc_*` 与 `.sesame` 文件同为"注释行 + 五数表头 + payload"，差异仅在 A1/A2 语义——`opc_*` 为 [Rosseland, Planck]（cm2/g，A1 全零时自动判序为 [Planck, Rosseland]），`.sesame` 与 eos_* 相同。

## 2. 物理量与单位（含 uk/uv 标记）

**本族是 CGS 原生**（`dyne/cm2` / `erg/g`），与 F1/F4 的 `Mbar` 体系**不同**。
以下摘录控制字典 `hyades_eos` / `hyades_opacity` / `sesame_dat` 三族条目（三者登记**同文**）：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `rho` | Mass density axis | `g/cm3` | primary document | uv |
| `Te` | Electron temperature axis（文件内 keV） | `eV` | primary document | uv |
| `P` | Pressure（CGS native） | `dyne/cm2` | primary document | uv |
| `E` | Specific internal energy（CGS native） | `erg/g` | primary document | uv |
| `kappa` | Opacity（opc_* = [Rosseland, Planck]） | `cm2/g` | primary document | uv |
| `raw_tail` | Trailing residual values | `unknown` | none | **uk, uv** |
| `*` | 未登记名兜底 | `unknown` | none | **uk, uv** |

单位判定的一级出处（字典逐字摘录）：`doc/Hyades 数据格式说明.doc`——"密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g"；不透明度"压强处为平均Rosseland值，比内能处为平均Planck值，单位cm2/g"。`Te` 的 eV 是解析器换算结果（`T_scale = {"kev":1e3, "ev":1.0}`），文件原生 keV。

## 3. 解析器 API 与用法

```python
FAMILY = "hyades_eos"
DOS_EOF = "\x1a"  # DOS 文件结束标记（实测出现在 hyades/sesame/eos_*.dat 末行）

def parse(path, relpath="", *, unit_hint_T: str | None = None) -> ParsedTable
def parse_all(path, relpath="", *, unit_hint_T: str | None = None) -> list[ParsedTable]
def parse_header_line(line: str) -> dict        # -> {id, zbar, abar, rho0, L, raw}
def solve_dims(length: int) -> list[tuple[int, int]]  # L 方程全部正整数解（交叉校验用）
```

示例（与 `parsers/README.md` 底本一致）：

```python
from eosop_pro.parsers.hyades_eos import parse

t = parse("E:/data/hyades/sesame/eos_41.dat", "hyades/sesame/eos_41.dat")
print(t.summary())             # family/kind/id/nr/nt/axes/fields
print(t.field2d("P")[0][:5])   # [i_Te][j_rho] 视图
```

`kind` 分派：不透明度文件 → `OPACITY`；`*_eos_e` → `EOS_ELECTRON`；`*_eos_i` → `EOS_ION`；其余 → `EOS_TOTAL`。

## 4. 陷阱与 unknown 清单

1. **20 手册 §11 条目 #6（必须复述）**：F3 `hyades_eos` 的 `raw_tail`——`L = 2 + NR + NT + 2*NR*NT` 之外的尾部残余，无任何一级文档定义 → 单位 `unknown`，解析器按原样保存（`hyades_eos.py:216`）。实测为该族**凑满每行 5 字段的补零填充**（eos_41 多 1 个、eos_11/eos_81 多 3 个）；计数守恒时 seen 与 expected **都必须含补零**，否则把已定性的填充误报成 count_mismatch。
2. `solve_dims` 方程**不唯一**（如 L=2004 同时有 (44,22) 与 (2,400)）——NR/NT 只能由 payload 前两数确定，`solve_dims` 仅作交叉校验；真解不在解集时会显式告警"布局存疑"。
3. DOS EOF 标记 `\x1a`（已忽略，不参与数值）。
4. 行 1 自由文本仅作注释/锚点（`sesame_number`、`qeos_comment`），不参与计数。
5. 跨族铁律（20 手册 §0.3/§10）：本族 T 文件内 **keV**（其余族多为 eV/K）；P/E 为 CGS（F1/F4 是 Mbar 系）——混用会差 10^12 量级。

### 4.1 实测变体与冻结清单（2026-11-15 sesame/ 全量审计，详见 20 手册 §4.3）

- **F3b 三数组变体**（8 文件，`L = 2+nr+nt+3*nr*nt`）：第三数组语义未定，以 `X3`（unit=unknown）中性登记；kind 布局判定为 `n_arrays ∈ {2,3}`（计数唯一区分）。
- **截断指数 token**（`eos_332.dat` 末行 ` 7.4E`）：payload 非数值残留检查（`fn.has_letters`）→ ParseError 显式拒绝；声明层 `_KNOWN_CORRUPT` 冻结 skip——**绝不产出静默错值表**（用户裁定"忽略+告警"）。
- **宽度变体**：`CSi2.5_eos.dat`（13 字符/字段、小写 e）、`EOS_Al10Au3.DAT`（14 字符数值）——`fn.extract_numbers` 正则与宽度无关，无需特判；后者注释行无 SESAME#/QEOS 模式 → notes 登记。
- **nt=1 退化表**（`eos_541.dat`）：维度闸门放宽至 nt>=1 + notes 登记。

### 4.2 id 语义与 kind 判定优先级（2026-11-15 加固）

文件名 `eos_<id>.dat` 的 `id` 是 **Hyades 材料编号**（非 LANL 库号）。kind 判定优先级：

1. 文件名 token `_eos_e` / `_eos_i`（历史行为，最高优先）
2. `eos_<id>.dat` 命名 + **id ∈ [2001,2999] → `EOS_ELECTRON`**、**[3001,3999] → `EOS_ION`**（编号约定逐字出处：`Hyades 数据格式说明.doc`；保守边界：仅命名匹配且 id≥1000 才改 kind）
3. id ∈ [1001,1999]（灰度不透明度编号）→ 不自动改 kind，仅 notes 登记
4. 其余 → `EOS_TOTAL`

文件名编号与表头 `id` 不一致时 notes 显式登记（语义存疑）。⚠️ h5 表路径随 kind 变化（如 `/tables/EOS_ELECTRON_2044`），固化断言见 `test/parsers/test_hyades_eos.py::test_flow_id_semantics` 与 `test/eosopdata/step02_families/test_family_extract.py::test_sesame_flow_files_kind_semantics`。

## 5. 溯源

| 等级 | 记号 | 依据 | 本地定位（gen_eos_op 相对路径） |
|---|---|---|---|
| L1 | `format:` | `Hyades 数据格式说明.doc`（格式规格逐字来源，`doc/` 与 `matter++/hyades/` 两处副本） | `src/Multi1D++Portable20241128/doc/Hyades 数据格式说明.doc` |
| L1 | `format:` | `MULTI使用的SESAME数据文件格式.docx`（SESAME 库约定） | `src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx` |
| L2 | `declared:` | 数据文件行 0 注释（材料名/SESAME 号/QEOS 生成历史） | 逐文件 |
| L5 | `unknown` | `raw_tail`：尾部残余无任何文档说明 | `parsers/hyades_eos.py:216` |

实现脚本：`eosop_pro/parsers/hyades_eos.py`（本目录上一级）。uk/uv 标记不得自行改判；人工核查通过后请在 `registry/field_checks.py` 置 `checked=True` 并重跑 `dump_markdown()` 同步字典。
