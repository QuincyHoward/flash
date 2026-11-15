# ledcop_zeff.py —— LEDCOP 平均电离度拆分件（F5b）

> **适用仿真软件**：LANL TOPS / LEDCOP（`*.NoFree` / `*.AvSqFree` 为 `ATOMIC/<El>.txt` 主表的预拆分版本）
> **官方链接**：https://aphysics2.lanl.gov/static/opacdocs/opac-faq.html 与 https://aphysics2.lanl.gov/static/opacdocs/opac-help.html（2026-09 联网核实；NoFree/AvSqFree 逐字定义见 FAQ Q1/Q7）；最佳引用 Magee et al. 1995（LANL T-1）
> **概要**：解析极简结构（4 数头 + 3 段）的预拆分件，值字段含义由文件名 token 决定
> **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §6.2](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式

```
<魔数 0.1234567E+000>  <1.0>  NR  NT      ← 第 1 行 4 个数
[log10 rho (NR)] [log10 T (NT)] [值 (NR*NT)]   ← 3 段连续数值
```

计数守恒：**`4 + NR + NT + NR*NT`**（不符抛 `CountMismatch`）。

实测基准：`matter++/ATOMIC/Al.NoFree` → NR=50, NT=69，总数 **3573** = 4+50+69+3450。

| 文件 | 值字段含义 | 解析器 kind |
|---|---|---|
| `*.NoFree` | 自由电子数（<Z>，Z̄ 等价量） | `ZEFF`，字段名 `Z` |
| `*.AvSqFree` | 自由电子数平方均值（<Z²>） | `ZEFF2`，字段名 `Z2` |

魔数校验：`LEDCOP_MAGIC = 0.1234567`；首字段不符时**不抛错**，在 notes 记 `⚠️` 告警。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/ATOMIC/Al.NoFree`（自由电子数 <Z> 预拆分件，实测基准 NR=50、NT=69、总数 3573；前 16 行 = 4 数头 + log10 rho 段 + log10 T 段起点）

**原文摘录**（前 16 行，逐字保留原始空格）：

```
 0.1234567E+000 1.0000000e+000 5.0000000e+001 6.9000000e+001
-3.0000000e+000-2.9183647e+000-2.8367492e+000-2.7551047e+000
-2.6734593e+000-2.5918449e+000-2.5102102e+000-2.4285707e+000
-2.3469419e+000-2.2653042e+000-2.1836725e+000-2.1020432e+000
-2.0204061e+000-1.9387738e+000-1.8571414e+000-1.7755187e+000
-1.6938753e+000-1.6122366e+000-1.5306051e+000-1.4489772e+000
-1.3673504e+000-1.2857122e+000-1.2040783e+000-1.1224501e+000
-1.0408155e+000-9.5919994e-001-8.7755474e-001-7.9590716e-001
-7.1428520e-001-6.3264408e-001-5.5101557e-001-4.6939054e-001
-3.8775670e-001-3.0612362e-001-2.2449149e-001-1.4285453e-001
-6.1225177e-002 2.0402721e-002 1.0205619e-001 1.8366836e-001
 2.6531320e-001 3.4693946e-001 4.2857211e-001 5.1020978e-001
 5.9183230e-001 6.7347249e-001 7.5510463e-001 8.3673542e-001
 9.1836589e-001 1.0000000e+000-3.3010300e+000-3.2218487e+000
-3.0969100e+000-3.0000000e+000-2.9030900e+000-2.8239087e+000
-2.6989700e+000-2.6020600e+000-2.5228787e+000-2.4559320e+000
```

**逐行说明**：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | ` 0.1234567E+000 1.0000000e+000 5.0000000e+001 6.9000000e+001` | 第 1 行 4 数头（空格分隔）：魔数 0.1234567（不符不抛错，记 notes 告警）、比例因子 1.0、NR=50、NT=69 |
| 2–14 | 连续数值流：每行 4 个**定宽 15 字符**字段（无分隔符，正数以空格占位） | log10 rho 段共 50 个：-3.0000000e+000 → 1.0000000e+000，10^x 还原 = 1e-3 → 1 g/cm3（uv，§2）；段在第 14 行第 2 字段处结束 |
| 14–16 | log10 T 段起点：-3.3010300、-3.2218487、-3.0969100、-3.0000000 | 三段**连续排布、段间不换行**（rho 段末直接接 T 段）；log10 keV（uv，§2/§4：本族固定 keV，文件自身不声明）；10^-3.30103 ≈ 5.0e-4 keV，与 `Al.txt` T 网格首点 5.0000E-04 一致 |
| （第 16 行后） | 未摘录部分 | T 段共 69 个，其后为 NR×NT = 3450 个 Z̄ 值（文件名 token `NoFree` → 字段 Z，无量纲 uv，FAQ Q1 定义）；总计数 4+50+69+3450 = 3573（§1 计数守恒） |


## 2. 物理量与单位（含 uk/uv 标记）

摘录自《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》`ledcop_zeff` 族（条目数 5）——**本族是唯一有已核实互联网定义的族**（LANL TOPS FAQ Q1/Q7 逐字引文入字典）：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `rho` | 质量密度轴（log10 值） | g/cm3 | primary document | uv |
| `Te` | 电子温度轴（log10 值，keV） | keV | primary document | uv |
| `NoFree` | 每离子平均自由电子数 <Z>（FAQ Q1 逐字定义） | - | primary document | uv |
| `AvSqFree` | 自由电子数平方的离子态平均 <Z²>（FAQ Q7 逐字定义） | - | primary document | uv |
| `*` | 未登记名兜底 | unknown | none | uk, uv |

**定义原文摘录**（一级出处）：

- Q1：*"the free electron number is the average number of free electrons per ion"*（逐离子态布居加权；混合物按数分数加权平均）→ **<Z> 无量纲**
- Q7：*"the average of the square of the number of free electrons over the ion stages"* → **<Z²> 无量纲**，与 <Z> 配套（差值给出离子态方差）

## 3. 解析器 API 与用法

真实签名（`parsers/ledcop_zeff.py`）：

- `parse_all(path, relpath="", *, unit_hint_T=None) -> list[ParsedTable]`
- `parse(path, relpath="", *, unit_hint_T=None) -> ParsedTable`
- 常量 `LEDCOP_MAGIC = 0.1234567`；内部 `_field_for(rel)` 按文件名 token 定字段

```python
from eosop_pro.parsers.ledcop_zeff import parse, LEDCOP_MAGIC

t = parse(r".../matter++/ATOMIC/Al.NoFree", "ATOMIC/Al.NoFree")
print(t.summary())        # nr=50, nt=69, field=Z, axis log10 标记
print(t.axes["Te"][:3])   # log10 keV → 10**x 线性还原（keV→eV 乘 1e3）
```

轴处理：`rho`/`Te` 存储为 log10 值，解析器 `10.0**x` 还原为线性（`axis_log10=True`）；T 单位默认 keV，可由 `unit_hint_T` 覆盖（`{"ev":1.0,"kev":1e3}`）。

## 4. 陷阱与 unknown 清单

1. **Te 单位是 keV（与不透明度族 eV 相反，差 1000 倍）**。本族文件自身**不声明**单位，判定依据 = `ATOMIC/*.txt` 内嵌行 `T in keV` 佐证（20 手册记 L3 `default:`）+ `MULTI使用的SESAME数据文件格式.docx` Zeff 节明文 `温度单位是keV`。
2. **文件名单位约定**：`X_Zeff.dat`(keV) 与 `X_Z.dat`(eV) 是 **Thermos/F2 族**的约定（`matter++/Thermos/Readme.txt` L2 声明）；本族 `*.NoFree`/`*.AvSqFree` 固定 keV。两者别混淆。
3. **字段含义来自文件名 token**（NoFree→Z、AvSqFree→Z2），文件内无列名；无单位声明（说明 .doc 抽取乱码不可引用）→ 无量纲。
4. **magic 不符不抛错**：只记 notes 告警，交上层裁决。
5. 20 手册 §11 本族无 unknown 条目；守护测试：`test_zeff_registry.py::test_ledcop_split_tables_are_keV`。

## 5. 溯源（L1-L5 等级表）

| 等级 | 量 | 依据 |
|---|---|---|
| L1 `format:` | NoFree/AvSqFree 定义（<Z>/<Z²>） | LANL TOPS FAQ Q1/Q7（已核实互联网一级出处） |
| L1 `format:` | 结构布局（4 数头 + 3 段） | `Atomic(LEDCOP)说明.doc` 族；实测 Al.NoFree 计数闭合 |
| L3 `default:` | `Te` = keV | 由 `ATOMIC/*.txt` 内嵌行佐证；文件自身不声明 |
| L1 | rho log10 g/cm3、Zeff 无量纲 | `MULTI使用的SESAME数据文件格式.docx`（Zeff 节，log 坐标 + keV） |

本地原始文档（gen_eos_op 相对路径）：

- `src/Multi1D++Portable20241128/doc/Atomic(LEDCOP)说明.doc`（抽取乱码不可引用，仅存档）
- `src/Multi1D++Portable20241128/matter++/ATOMIC/Al.NoFree`（实测基准）
- 字典升级记录：`eosop_pro/docs/20_格式规格与物理量单位手册.md` 附录 C.1（TOPS FAQ 逐字引文与字典动作；原 uk物理量猜测报告 §4.1 已抢救归档于此）
