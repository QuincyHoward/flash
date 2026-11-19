# multi_eos_reader.py —— MULTI 反演 EOS（F1）

> **适用仿真软件**：MULTI（默认 SESAME 族输入）| **官方链接**：无已核实官方 URL（uv），本地权威：`src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx`（抽取文本原存 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt，2026-11-06 已清理）
> **概要**：4×15 定宽文本表（反演 EOS：自变量 (rho, de)，T 为因变量场），解析产出 `ParsedTable`（`family="multi_eos"`）| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步（uk=无来源确认/uv=未人工核查）；格式权威版本 = [20 手册 §2](../../docs/20_格式规格与物理量单位手册.md)
>
> **定位说明（解析 vs 转换）**：本页 = **解析器文档**（对应 `parsers/multi_eos_reader.py`，读 F1 → ParsedTable）；
> **转换**（cn4 → F1 正演反演、F1 → (rho,Te) 反演）实现在 `convert/writers_multi.py` + `convert/invert_eos.py`，
> 公式与算法口径见 [../../convert/转换公式详解.md](../../convert/转换公式详解.md)。

## 1. 格式布局与计数公式

引 [20 手册 §2.1](../../docs/20_格式规格与物理量单位手册.md)：每个**块**以一行 4 数表头开始：

```
table_id   rho0(未用)   nr   ne
```

其后为 payload（T-major，rho 快变，索引 = `i_de*nr + j_rho`）。

**两种 payload 布局并存**（实测，由**计数守恒唯一确定**，不能假定）：

| 布局 | 数组 | 计数公式 | 实测文件 |
|---|---|---|---|
| `with_e0`（含冷能） | `rho(nr) de(ne) e0(nr) P(nr·ne) T(nr·ne)` | `4 + 2*nr + ne + 2*nr*ne` | `mat_Al-1.0/AL_eos` → 9978 ✓ |
| `no_e0`（无冷能） | `rho(nr) de(ne) P(nr·ne) T(nr·ne)` | `4 + nr + ne + 2*nr*ne` | `mat_Au-1.0/AU_eosd` → 每块 4770 ✓ |

两公式只差一个 `nr`。其余实测锚点：`AU_eos` 头 `27001000 19.300003 101 23`、`BE_eos` 头 `2020 0.0 101 50`。

**多块串联**：`AU_eosd` 在 2388 行里放了 2 个同表头块 → 块边界由"又出现一行与首块表头完全相同的 4 数行"确定，`parse_all` 拆成 2 张表。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/mat_Al-1.0/AL_eos`（铝反演 EOS，with_e0 布局，nr=66 × ne=74，计数公式 4+2·nr+ne+2·nr·ne=9978 实测闭合（§1 表锚点））

**原文摘录**（前 20 行，逐字保留原始空格，含行尾空格；摘录为数据文件原文，不混入任何注释）：

```
     37181000    .27000000E+01  .66000000E+02  .74000000E+02
  .00000000E+00  .27000000E-05  .54000000E-05  .13500000E-04
  .27000000E-04  .54000000E-04  .13500000E-03  .27000000E-03
  .54000000E-03  .13500000E-02  .27000000E-02  .40500000E-02
  .67500000E-02  .10800000E-01  .16200000E-01  .27000000E-01
  .40500000E-01  .67500000E-01  .10800000E+00  .16200000E+00
  .27000000E+00  .29700000E+00  .33750000E+00  .37800000E+00
  .40500000E+00  .47250000E+00  .54000000E+00  .60750000E+00
  .67500000E+00  .75600000E+00  .81000000E+00  .94500000E+00
  .10800000E+01  .12150000E+01  .13500000E+01  .14850000E+01
  .16200000E+01  .17550000E+01  .18900000E+01  .20250000E+01
  .21600000E+01  .22950000E+01  .24300000E+01  .24975000E+01
  .25650000E+01  .26325000E+01  .26595000E+01  .27000000E+01
  .27270000E+01  .28350000E+01  .29700000E+01  .32400000E+01
  .37800000E+01  .43200000E+01  .48600000E+01  .54000000E+01
  .67500000E+01  .81000000E+01  .94500000E+01  .10800000E+02
  .13500000E+02  .16200000E+02  .18900000E+02  .21600000E+02
  .24300000E+02  .27000000E+02  .00000000E+00  .41054175E-03
  .15475747E-02  .38774499E-02  .87183351E-02  .94796336E-02
  .10240265E-01  .11000368E-01  .11760085E-01  .12519558E-01
```

**逐行说明**（格式 / 物理量与单位 / 顺序，单位与 §2 单位表一致）：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `     37181000    .27000000E+01  .66000000E+02  .74000000E+02` | 块表头（4×15 定宽，每值 15 列）：`table_id=37181000`、`rho0=2.70 g/cm3`（声明但解析中未用）、`nr=66`、`ne=74`——§1 计数公式的两个维度 |
| 2–18（行 18 仅前 2 值） | `.00000000E+00`…`.27000000E+02` | 一维段 1：`rho(nr=66)` 质量密度轴，单位 g/cm3，**线性坐标**（非 log10，§2；docx 明文）；66 个值按 4 值/行占 17 行（行 2–17 每行 4 值 + 行 18 前 2 值），自 0 排到 27.0 g/cm3 |
| 18（后 2 值）–20 | `.00000000E+00` `.41054175E-03`… | 一维段 2 开头：`de(ne=74)` 比内能轴（冷曲线之上能量），单位 **Mbar·cm3/g**（§2），自行 18 第 3 个值 0 起、按 4 值/行续排（74 个值占 19 行）；with_e0 布局下其后依次为 `e0(nr)`、`P(nr·ne)`、`T(nr·ne)`（§1 LAYOUTS 顺序）——注意 T 的文件原生单位是 Kelvin，解析器乘 `config.EV_PER_K` 转 eV（§2） |

## 2. 物理量与单位

摘录字典 multi_eos 族条目（完整来源详述见[字典](../../docs/eosop变量控制字典.md)；来源均为一级文档 `MULTI使用的SESAME数据文件格式.docx`）。**2026-11-14 人工裁定**：全族 7 条目经操作者视图交叉验证转 checked（标记省略，见 §2.1）：

| 字段 | 物理意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `rho` | 质量密度轴（**线性**坐标，docx 明文"没有使用对数坐标系"） | g/cm3 | primary document | （已核查，省略） |
| `de` | 比内能轴（冷曲线之上能量） | Mbar*cm3/g | primary document | （已核查，省略） |
| `P` | 压力 P(rho, de+e0) | Mbar | primary document | （已核查，省略） |
| `E` | 比内能（de + e0_cold 合成；无 e0 布局以 de 为基准并显式注记） | Mbar*cm3/g | primary document | （已核查，省略） |
| `e0_cold` | 冷曲线比能（rho 上的一维列表） | Mbar*cm3/g | primary document | （已核查，省略） |
| `de_energy` | 能量轴 de 另注册的一维场（出图用） | Mbar*cm3/g | primary document | （已核查，省略） |
| `T` | 温度场 T(rho, de+e0)；**文件为 Kelvin，解析器乘 `config.EV_PER_K` 转 eV** | eV（文件原生 Kelvin） | primary document | （已核查，省略） |
| `*` | 未登记名兜底（docx F1 布局只定义 r/de/e0/P/T 五段） | unknown | none | uk, uv |

## 2.1 mat_CELIA/CH_ieos 操作者视图交叉验证（2026-11-14 人工裁定）

用户查看工具对 `matter++/mat_CELIA/CH_ieos`（SESAME 7590 聚苯乙烯）渲染的边界/维度与解析器独立读出的结果**逐项吻合**（核查实现：`parsers/test/test_multi/test_celia_combined.py`，6 测试全 PASS）：

| 量 | 解析器读出的原生值 | 操作者视图 | 换算关系 | 结论 |
|---|---|---|---|---|
| 维度 | 表头 `7590 / 0 / 101 / 100` | dimension(nr x ne) : 101 x 100 | — | ✓ 一致 |
| rho 轴末端 | 20880 g/cm3（线性，101 点） | density(g/cm3) : [0, 20880] | — | ✓ 一致 |
| de 轴末端 | 3.13208e4 Mbar·cm3/g（100 点） | de(erg/g) : [0, 3.13208e+016] | ÷1e12 | ✓ 一致 |
| P 最大 | 4.8908e8 Mbar | pressure(dyne/cm2) : [0, 4.89085e+020] | ÷1e12 | ✓ 一致 |
| E 最大 | 3.502e4 Mbar·cm3/g | (de_max + e0_max) = 3.502e16 erg/g | ÷1e12 | ✓ 合成关系数值吻合 |
| e0 最大 | 3.70145e3 Mbar·cm3/g 量级 | e0(erg/g) : [0, 3.70145e+015] | ÷1e12 | ✓ 量级一致 |
| T 最大 | 原生 3.714e8 K ×8.617e-5 ≈ 32003 eV | temperature(eV) : [0, 32001.1] | ×8.617e-5 | ✓ **视图的 eV 标注是换算后显示值，Kelvin 原生约定确认** |

**裁定记录**：字典 7 条目 `checked=True`（单位 Mbar / Mbar·cm3/g / eV(K→eV) 均维持原登记）；操作者工具的 dyne/cm²、erg/g、eV 标注为其显示层换算，**不构成对文件原生单位的改判**。计数守恒 20508 = with_e0 公式 + 2 尾部数值（raw_tail 显式登记）。

## 3. 解析器 API 与用法

关键 API（签名经源码核实）：

- `parse(path, relpath="") -> ParsedTable`、`parse_all(path, relpath="") -> list[ParsedTable]`（多块文件拆多张）
- `parse_header(line: str) -> dict` —— 块表头 4 数（`table_id`/`rho0`/`nr`/`ne`）
- `detect_layout(nr: int, ne: int, n_payload: int) -> tuple[str, int]` —— 由实测 payload 数反解布局，返回 `(布局名, 尾部多余个数)`
- `LAYOUTS = {"with_e0": ("rho","de","e0","P","T"), "no_e0": ("rho","de","P","T")}`、`HEADER_FIELDS = ("table_id","rho0","nr","ne")`
- `FAMILY = "multi_eos"`；异常：`eosop_pro.core.text.errors.ParseError`

```python
from eosop_pro.parsers.multi_eos_reader import parse_all

tables = parse_all(r"E:/data/multi/mat_Al-1.0/AL_eos", "multi/mat_Al-1.0/AL_eos")
t = tables[0]
print(t.summary())              # 轴 rho(g/cm3) × de(Mbar*cm3/g)；场 P/E/T
```

## 4. 陷阱与 unknown 清单

[20 手册 §11](../../docs/20_格式规格与物理量单位手册.md) 无本族 unknown 条目（字典兜底条 `*` 为 uk,uv）。陷阱：

- **"Inverted" 的含义**：自变量是 **(rho, de)**，温度 T 是**因变量（场）**。要得到 (rho, Te) 网格需在 de 方向反演，见 `eosop_pro.convert.invert_eos`。
- **布局必须反解**：`with_e0` 与 `no_e0` 只差一个 `nr`，由 `detect_layout` 按实测计数唯一确定；精确解不唯一或无解即抛 `ParseError`。
- **尾部未声明数值**：`detect_layout` 允许 1..nr 个尾部未声明数值（实测 `mat_Be-1.0/BE_eos_i` 多 2 个零），但**必须显式标注**，不能静默吸收。
- **T 的文件原生单位是 Kelvin**：eV 是解析器换算后的结果；换算常数单一来源 `config.EV_PER_K`。
- **rho 轴为线性**（非 log10）——与 F2 multi_opacity 的 log10 存储不同（[20 手册 §10](../../docs/20_格式规格与物理量单位手册.md)）。

## 4.1 cn4 来源转换口径（2026-11-14 裁定）

`eosop_pro.convert.writers_multi.write_multi_eos_from_cn4` 支持从 cn4（IONMIX）直接生成 F1 文件，**固定 `no_e0` 布局**：

- **de 口径**：`de ≡ E_total = e_ion + e_ele`。依据：① 一手 docx 仅保证文件层面 `E_total = de + e0`（"pressures at energy de[i]+e0"、"e0=冷能量"）；② IONMIX 能量零点构造性位于冷态（T=0 时 E≡0），故 cn4 侧 E_c≡0，`de` 即文献口径 `E−E_c`（SESAME 301−306 分表之差），不引入假冷曲线（`e0(ρ)=E(ρ,T_min)` 的 with_e0 变体留作可选，未默认实现）。
- **单位链**：P：J/cm³ ÷1e5 → Mbar；E：J/g ÷1e5 → Mbar·cm³/g；T：eV（writer 按 MULTI 约定写 Kelvin）。
- **正演反演**：`eosop_pro.convert.invert_eos.to_de_grid`（与 `to_Te_grid` 互逆）：每条 rho 列在 (log10 E, log10 T) 空间反解 T(E)，同一插值权重用于 P（log 空间）；越界列端点延拓（`extrapolate="edge"`，记入 notes，无 NaN）。
- **轴适配**：`cn4_eos_to_rho_base` 把 nion(cm⁻³) 轴替换为 rho(g/cm³)（`rho = nion·⟨A⟩/N_A`，取 rho 派生场第 0 行并校验列常值）。
- **验证**：往返闭合（生成 F1 → `to_Te_grid` 反演 → 与 cn4 原始比较）P 中位相对误差 0.03%、E 0.32%（Z06_0.50-Z01_0.50 样品，`parsers/test/test_multi/test_cn4_to_multi.py`）。

## 5. 溯源

| 等级 | 含义 | 本族落点 |
|---|---|---|
| L1 format | 一手格式规格文档 | `MULTI使用的SESAME数据文件格式.docx`（布局/单位全表） |
| L2 declared | 文件内/伴随声明 | 无（表头不含单位声明） |
| L3 default | 格式默认约定 | 无 |
| L4 inferred/derived | 推导 | `E = de + e0` 合成；`T` 的 K→eV 换算 |
| L5 unknown | 无来源确认 | 字典兜底条 `*`（未登记名，uk,uv） |

一手依据：`src/Multi1D++Portable20241128/doc/MULTI使用的SESAME数据文件格式.docx`；实测计数锚点见 §1 表；2026-11-14 人工裁定证据见 §2.1（操作者视图 × 解析器输出交叉验证，`parsers/test/test_multi/`）。
