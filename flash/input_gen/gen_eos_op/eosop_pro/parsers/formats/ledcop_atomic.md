# ledcop_atomic.py —— LEDCOP/ATOMIC 原子主表（F5a）

> **适用仿真软件**：LANL TOPS（ATOMIC 为最新数据文件，LEDCOP 为早期截面文件，均出自 LANL T-1 / XCP-5 团队）
> **官方链接**：https://aphysics2.lanl.gov/static/opacdocs/opac-faq.html 与 https://aphysics2.lanl.gov/static/opacdocs/opac-help.html（2026-09 联网核实）；最佳引用 Magee et al. 1995（ASP Conf. Ser. 78, 51，FAQ Q13 指定）
> **概要**：锚点驱动的流式状态机，解析 `ATOMIC/*.txt` 主表（可达 34 万行），灰度段产出 Ross/Planck/NoFree/AvSqFree 四场
> **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §6.1](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

**必须用锚点驱动的流式状态机，不能按固定行数**（`ATOMIC/Al.txt` 有 **348636 行**）。

结构（实测锚点，`matter++/ATOMIC/Al.txt`）：

```
Number of T =  69  Number of rho =  50  Number of materials =   1   ← 维度锚点
TOPS results for  Li              on Jul  2, 2017
 Opacities in cm**2/gm, T in keV, density in gm/cc     ← ★ 内嵌单位声明（L2，第 3 行）
Normalized composition for requested elements
No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
  5.0000E-01   8.7320E-01      3         Li        4922
Temperature grid used the following  69 points    ← 其后 69 个数（6/行）
Density grid used the following  50 points        ← 其后 50 个数
Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  5.0000E-04
  ...nr 行 × 5 列...                                ← 灰度块（逐 T 一块，重复 nt 次）
Multigroup opacities                                ← 多群段起点
Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.0000E-03
  ...逐 (T, rho) 重复 nt*nr 次（体积主体）...
```

计数守恒（内置校验，不符抛 `CountMismatch`）：

- T 网格数 = `n_t`；rho 网格数 = `n_rho`
- 灰度 T 块数 = `n_t`；灰度数据行数 = `n_t × n_rho`（每行 5 列）
- 多群段块数 = `n_t × n_rho`（默认不解析，见 §4）

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/ATOMIC/Al.txt`（LEDCOP/ATOMIC 原子主表，Al，全文 348636 行；前 40 行 = 全部头部声明 + T/rho 网格 + 光子网格起点）

**原文摘录**（前 40 行，逐字保留原始空格）：

```
 Number of T =  69  Number of rho =  50  Number of materials =   1
 TOPS results for  Li              on Jul  2, 2017
 Opacities in cm**2/gm, T in keV, density in gm/cc
Normalized composition for requested elements
No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
  1.0000E+00   1.0000E+00     13         Al        9173
Temperature grid used the following  69 points
  5.0000E-04  6.0000E-04  8.0000E-04  1.0000E-03  1.2500E-03  1.5000E-03
  2.0000E-03  2.5000E-03  3.0000E-03  3.5000E-03  4.0000E-03  5.0000E-03
  6.0000E-03  7.0000E-03  8.0000E-03  9.0000E-03  1.0000E-02  1.2500E-02
  1.5000E-02  2.0000E-02  2.5000E-02  3.0000E-02  4.0000E-02  5.0000E-02
  6.0000E-02  7.0000E-02  8.0000E-02  9.0000E-02  1.0000E-01  1.2500E-01
  1.5000E-01  1.7500E-01  2.0000E-01  2.2500E-01  2.5000E-01  2.7500E-01
  3.0000E-01  3.5000E-01  4.0000E-01  4.5000E-01  5.0000E-01  5.5000E-01
  6.0000E-01  6.5000E-01  7.0000E-01  8.0000E-01  9.0000E-01  1.0000E+00
  1.1250E+00  1.2500E+00  1.3750E+00  1.5000E+00  1.6250E+00  1.7500E+00
  1.8750E+00  2.0000E+00  2.1250E+00  2.2500E+00  2.3750E+00  2.5000E+00
  2.6250E+00  2.7500E+00  3.0000E+00  3.5000E+00  4.0000E+00  5.0000E+00
  6.0000E+00  8.0000E+00  1.0000E+01
Density grid used the following  50 points
  1.0000E-03  1.2068E-03  1.4563E-03  1.7575E-03  2.1210E-03  2.5595E-03
  3.0888E-03  3.7276E-03  4.4984E-03  5.4287E-03  6.5513E-03  7.9060E-03
  9.5410E-03  1.1514E-02  1.3895E-02  1.6768E-02  2.0236E-02  2.4421E-02
  2.9471E-02  3.5565E-02  4.2919E-02  5.1795E-02  6.2506E-02  7.5431E-02
  9.1030E-02  1.0985E-01  1.3257E-01  1.5999E-01  1.9307E-01  2.3300E-01
  2.8118E-01  3.3932E-01  4.0949E-01  4.9417E-01  5.9636E-01  7.1969E-01
  8.6851E-01  1.0481E+00  1.2649E+00  1.5264E+00  1.8421E+00  2.2230E+00
  2.6827E+00  3.2375E+00  3.9069E+00  4.7149E+00  5.6899E+00  6.8665E+00
  8.2864E+00  1.0000E+01
Photon grid used the following  99 points
  1.0000E-03  1.1359E-03  1.2902E-03  1.4655E-03  1.6646E-03  1.8907E-03
  2.1476E-03  2.4393E-03  2.7707E-03  3.1472E-03  3.5747E-03  4.0604E-03
  4.6120E-03  5.2386E-03  5.9503E-03  6.7588E-03  7.6770E-03  8.7200E-03
  9.9047E-03  1.1250E-02  1.2779E-02  1.4515E-02  1.6487E-02  1.8727E-02
  2.1271E-02  2.4161E-02  2.7443E-02  3.1172E-02  3.5407E-02  4.0217E-02
  4.5681E-02  5.1887E-02  5.8936E-02  6.6943E-02  7.6038E-02  8.6369E-02
  9.8103E-02  1.1143E-01  1.2657E-01  1.4377E-01  1.6330E-01  1.8548E-01
  2.1068E-01  2.3930E-01  2.7182E-01  3.0875E-01  3.5069E-01  3.9834E-01
  4.5245E-01  5.1392E-01  5.8374E-01  6.6305E-01  7.5313E-01  8.5545E-01
  9.7167E-01  1.1037E+00  1.2536E+00  1.4239E+00  1.6174E+00  1.8371E+00
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | ` Number of T =  69  Number of rho =  50  Number of materials =   1` | 维度锚点：n_t=69、n_rho=50、材料数 1（uv，in-file declaration）；据此灰度块 69 个（逐 T 一块、每块 50 行 5 列），多群段 69×50 块（§1 计数公式） |
| 2 | ` TOPS results for  Li              on Jul  2, 2017` | 生成信息行（材料名沿用 TOPS 模板写 `Li`，与本文件名 Al 不一致；解析以第 1 行维度锚点与第 6 行组分为准） |
| 3 | ` Opacities in cm**2/gm, T in keV, density in gm/cc` | ★ 内嵌单位声明原文（L2）：不透明度 cm**2/gm（≡cm2/g）、T keV、密度 gm/cc（≡g/cm3）；与 §2 单位表一致 |
| 4 | `Normalized composition for requested elements` | 组分段标题 |
| 5 | `No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.` | 组分列头：数分数、质量分数、原子序数、化学符号、材料 ID（列序固定） |
| 6 | `  1.0000E+00   1.0000E+00     13         Al        9173` | 单一组分数据行：数分数 1.0、质量分数 1.0、Z=13、Al、Mat ID 9173（列序同第 5 行列头） |
| 7 | `Temperature grid used the following  69 points` | T 网格锚点：其后连续 69 个数（6/行） |
| 8–19 | T 网格 69 个值（12 行 = 11 行×6 + 末行 3） | 电子温度轴，单位 keV（uv，第 3 行声明），升序 5.0000E-04 → 1.0000E+01；解析器换算为 eV（×1e3，§2/§3） |
| 20 | `Density grid used the following  50 points` | rho 网格锚点：其后连续 50 个数（6/行） |
| 21–29 | rho 网格 50 个值（9 行 = 8 行×6 + 末行 2） | 质量密度轴，单位 g/cm3（uv，第 3 行 density 项），升序 1.0000E-03 → 1.0000E+01 |
| 30 | `Photon grid used the following  99 points` | 光子网格锚点（99 点），供多群段使用；文件未对该网格单独声明单位；多群段默认不解析（§4） |
| 31–40 | Photon grid 前 10 行（每行 6 个，升序） | 光子能量网格数值起点；本摘录未及其后的灰度块与多群段锚点 |
| （第 40 行后） | 未摘录部分 | 光子网格其余数值 → 灰度块行 `Density  Ross opa  Planck opa  No. Free  Av Sq Free  T=…`（5 列：Ross/Planck = cm2/g uv；No. Free/Av Sq Free 无量纲 uk,uv，§2）逐 T 重复 69 块 → `Multigroup opacities` 多群段 |


## 2. 物理量与单位（含 uk/uv 标记）

摘录自《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》`ledcop_atomic` 族（条目数 7）：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `rho` | 质量密度轴 | g/cm3 | in-file declaration | uv |
| `Te` | 电子温度轴（文件原生 keV，解析器换算 eV） | eV | in-file declaration | uv |
| `Ross` | Rosseland 不透明度 | cm2/g | in-file declaration | uv |
| `Planck` | Planck 不透明度 | cm2/g | in-file declaration | uv |
| `No. Free` | 自由电子数（解析器登记名 NoFree；归一化未核查） | - | none | uk, uv |
| `Av Sq Free` | 自由电子数平方均值（解析器登记名 AvSqFree） | - | none | uk, uv |
| `*` | 未登记列兜底 | unknown | none | uk, uv |

内嵌声明原文（实测 Al.txt 第 3 行）：`Opacities in cm**2/gm, T in keV, density in gm/cc`。

## 3. 解析器 API 与用法

真实签名（`parsers/ledcop_atomic.py`）：

- `scan_header(lines: list[str]) -> dict[str, Any]` —— 头部 40 行抽维度/单位/材料/组分
- `parse_all(path, relpath="", *, include_multigroup=False, unit_hint_T=None) -> list[ParsedTable]`
- `parse(path, relpath="", *, include_multigroup=False, unit_hint_T=None) -> ParsedTable`

```python
from eosop_pro.parsers.ledcop_atomic import parse

t = parse(r".../matter++/ATOMIC/Al.txt", "matter++/ATOMIC/Al.txt")
print(t.summary())                 # nr=50, nt=69, fields=Ross/Planck/NoFree/AvSqFree
print(t.field_units)               # Ross/Planck = cm2/g（读自内嵌声明行）
print(t.unit_source)               # declared:keV (文件内嵌单位行)
```

`unit_source` 记为 `declared:<unit> (文件内嵌单位行)`；T 轴单位可由 `unit_hint_T` 覆盖（`{"ev":1.0,"kev":1e3}`）。

## 4. 陷阱与 unknown 清单

1. **T 单位 keV，差 1000 倍**（20 手册跨族铁律 §0.3/§10）：F5 的温度是 keV，其余族换算后是 eV。解析器读内嵌行后统一转 eV。
2. **`No. Free` / `Av Sq Free` 为 uk**：文件内无该列的语义/单位声明；本地权威 `Atomic(LEDCOP)说明.doc` 抽取乱码（ole2 双对齐失败）**不可引用** → 无可指认来源，不猜。可参考 lanl TOPS FAQ 的 NoFree/AvSqFree 定义（见 [ledcop_zeff.md](ledcop_zeff.md) §2）。
3. **多群段默认跳过**：`include_multigroup=False`（默认）。多群段有 nt*nr=3450 块 × ~99 行 ≈ 34 万行，体积极大；开启才解析并记 notes。
4. **灰度块 Density 列与 rho 网格交叉校验**：偏差写入 notes（`table.notes`），用于发现数据异常。
5. 20 手册 §11 本族无 unknown 条目（该清单 #7 为 generic_curve；本族 uk 仅 `No. Free`/`Av Sq Free` 两列，见字典）。

## 5. 溯源（L1-L5 等级表）

| 等级 | 量 | 依据 |
|---|---|---|
| L2 `declared:` | `Te`（keV→eV）、`Ross`/`Planck`（cm2/g） | `ATOMIC/*.txt` 第 3 行内嵌声明 |
| L2 `declared:` | `rho`（g/cm3） | 同上（density 项）；`gm/cc` ≡ `g/cm3` |
| L1 `format:` | 结构布局（锚点序列、计数公式） | `Atomic(LEDCOP)不透明度格式说明.docx`（`matter++/ATOMIC/`） |
| L5 `unknown` | `No. Free` / `Av Sq Free` 语义与归一化 | 无可指认来源（说明 .doc 抽取乱码不可引用） |

本地原始文档（gen_eos_op 相对路径）：

- `src/Multi1D++Portable20241128/doc/Atomic(LEDCOP)说明.doc`（抽取文本原存 docs/extracted/Atomic_LEDCOP_说明__ole2-word__ac285300.txt，2026-11-06 已清理，**内容乱码不可引用，仅存档**）
- `src/Multi1D++Portable20241128/matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx`（抽取文本原存 docs/extracted/Atomic_LEDCOP_不透明度格式说明__ooxml-word__4ed7421a.txt，2026-11-06 已清理）
- 数据实测：`src/Multi1D++Portable20241128/matter++/ATOMIC/Al.txt`（348636 行）
