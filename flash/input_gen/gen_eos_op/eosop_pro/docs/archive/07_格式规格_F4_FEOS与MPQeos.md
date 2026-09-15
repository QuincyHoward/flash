# 07 · 格式规格 F4 · FEOS / MPQeos

| 项 | 值 |
|---|---|
| **族名** | `mpqeos`（82）/ `feos_native`（25）/ `feos_tabdata`（23）/ `feos_aux`（60） |
| **解析器** | `parsers/mpqeos.py`、`feos_native.py`、`feos_tabdata.py`、`feos_aux.py` |
| **文件数** | **190**（4 个解析器合计，占 15.6%） |
| **扩展名** | `.301` / `.304` / `.305`（MPQeos）、`.feos`（FEOS）、`.data.txt`、`.PAR` / `.cst` / `.mexport` / `.INV` |
| **来源程序** | FEOS / MPQeos / ShowEOS（JWGU Frankfurt，基于 QEOS） |
| **单位** | `P` **GPa → Mbar**；`E` **MJ/kg → Mbar·cm³/g**；`T` **Kelvin → eV**；`rho` g/cm³ 不变 |

**权威依据**：
- `matter++/Readme.txt`：
  > 如果文件名和路径中有 `".feos"`，程序识别为 FEOS 程序文件，**按照一行 4 个 15 字符的数字读入**
  > 如果文件名和路径中有 `".301"` 或 `".304"` 或 `".305"`，程序识别为 MPQeos 生成的**每行 4×16 个字符**
- `docs/extracted/Multi1D_EOS_and_Opacity_-_FEOS程序说明__pdf__54722ef1.txt`（419 765 字符）
- `docs/extracted/FEOS-Package-Documentation2016__pdf__c14ce581.txt`（102 862 字符）
- `docs/extracted/MPQeos-JWGU-Documentation__pdf__6ff27aa7.txt`（47 998 字符）
- `docs/extracted/FEOS-Package-Documentation2012__pdf__f5675065.txt`

---

## 1. MPQeos（`.301` / `.304` / `.305`）—— 82 个文件

### 1.1 上游原文（逐字）

> **MPQeos 计算结果 SESAME 的数据格式和单位制**
>
> MPQeos 程序的计算结果采用的单位制并不是 Multi1D 数据库中数据的单位制：
> SESAME 数据库的单位：压强（**GPa**），能量（**MJ/kg**），密度（g/cc），温度（**Kelvin**）
> MULTI2D 程序中使用 cgs 单位，而其调用的 EOS 数据中的单位为压强 **Mbar**，
> 能量 **Mbar*cm3/g**，密度和温度单位与 SESAME 数据库相同。
>
> 其转化关系如下：
> 压力：`1GPa = 1e9Pa = 1e10 dyne/cm2 = 1e-2 Mbar`
> 能量密度：`1MJ/kg = 1e3 J/g = 1e10 erg/g = 1e-2 Mbar*cm3/g`
>
> 同时，SESAME 数据库使用 301 数据格式，四列多行数据。虽然 MPQeos 采用了
> 四列多行的结构，但是其内容与 Multi1D 的要求并不一致：
>
> 即 MPQeos 的数据为
> ```
> Id(1111)  Density(g/cc)  NR  NT
> R[1-NR]  T[1-NT](K)  P[1-NRxNT](GPa)  E[1-NRxNT](MJ/kg)
> Z[1-NRxNT]
> ```
> 因此 MPQeos 的计算结果**并不能直接用于 Multi1D 的计算**。
> **Multi1D++ 程序将自动识别文件后缀 301/304/305 并对单位制进行转化。**
> 但是，从计算的结果来看，压强、能量甚至 Z 等有负值，原因正在查找。

★ 最后一句是**上游自己承认的数据缺陷**，本项目照原样保留（见 §1.4）。

### 1.2 布局与计数

```
行 0 :  [SESAME id]  [rho0]  [NR]  [NT]        4 个数
行 1+:  R[1..NR]                               NR 个数
        T[1..NT]                               NT 个数
        P[1..NR·NT]                            NR·NT 个数
        E[1..NR·NT]                            NR·NT 个数
        Z[1..NR·NT]                            NR·NT 个数
```

```
N = 4 + NR + NT + 3·NR·NT
```

### 1.3 实测样本

```
mat_Al-1.0/FEOS/Al.feos.301
  hdr = ' 37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01'
      → [37170301, 2.7, 192, 69]      NR=192  NT=69
  layout = F4/MPQeos: 4 + nr + nt + 3*nr*nt (W=15)
  count  = actual=40009  expected=40009   ✅
  验算   = 4 + 192 + 69 + 3·192·69 = 4 + 192 + 69 + 39744 = 40009 ✅

mat_Au-1.0/Au.301
  hdr = '  1111           1.92800000e+001 1.23000000e+002 1.01000000e+002'
      → [1111, 19.28, 123, 101]       NR=123  NT=101
  layout = F4/MPQeos: 4 + nr + nt + 3*nr*nt (W=16)
  count  = actual=37497  expected=37497   ✅
  验算   = 4 + 123 + 101 + 3·123·101 = 4 + 123 + 101 + 37269 = 37497 ✅
```

两行的共同点与差异：

| 项 | `Al.feos.301` | `Au.301` |
|---|---|---|
| 第 1 字段 | `37170301`（真 SESAME 号） | `1111`（**占位符**，不是真 ID） |
| 定宽 W | **15** | **16** |
| `rho0` | `2.70000000e+00` | `1.92800000e+001` |
| 大写/小写 `e` | **小写 `e`** | **小写 `e`** |

★ **`Id(1111)` 是上游文档里写死的占位符**（原文就写作 `Id(1111)`），
所以 `Au.301` 的第 1 字段毫无信息量。**不能靠它识别材料** ——
材料身份必须从路径/`material.base`/伴随文件来。

### 1.4 三个实测坑

#### (a) 定宽宽度在族内不统一（W=15 与 W=16 混用）

这正是上游 Readme 特意区分 `.feos`（4×15）与 `.301`（4×16）的原因。
实测 **同一个扩展名 `.301` 下两种宽度都存在**，所以：

```python
_w = infer_payload_width(line, n_fields)   # core/fixedwidth.py
# 取 len(line) // n_fields，并记进 layout_rule: "…(W=15)" / "…(W=16)"
```

★ 注释里、属性里都写明 `W`，使"我按 15 还是 16 切的"可回溯。

#### (b) 表头**真的**不能按定宽切

```
' 37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01'
```

- `' 37170301       '` = 16 字符（标识字段）
- `'2.70000000e+00'` = **14 字符**，后面跟一个空格（不是 15/16）

按 16 切第 2 段会得到 `'2.70000000e+00 1'` → `float()` 失败。
**表头一律走 L2 数值正则**：

```python
header_nums = extract_numbers(line)      # core/fortran_numbers
```

#### (c) `P` / `E` / `Z` 有真实负值

上游原文已承认（§1.1 末句）。实测与文档一致。
处理方式：

- **native 轨逐字保留**（负值原样）
- **不试图"修正"**：这是上游物理模型问题，不是解析问题
- 统一网格插值时，log 空间中负值 → NaN，并在
  `ds.attrs["out_of_range_count"]` 里计数

---

## 2. FEOS 原生表（`.feos`）—— 25 个文件

### 2.1 行 0 的 10 个字段（**已用 `.301` 兄弟文件独立验证**）

```python
HEADER_FIELDS = ("Z", "NR", "NT", "c1", "c2", "c3",
                 "rho0", "T_ref_eV", "B0", "sesame_no")
```

★ **验证方法**（这是最硬的证据链，写进了解析器 docstring）：

```
mat_B/B.feos        L0 = [12.06, 123, 101, 1.0, 1e-4, 1e-50, 2.34,
                          0.02585257, 1.85e12, 104005]
mat_B/B.301         hdr = [1040050301, 2.34, 123, 101]
                                    ↑      ↑    ↑
                                  rho0    NR   NT      → NR=123 / NT=101 ✓✓

mat_Al-1.0/Al.feos               L0 = [12.06, 192, 69, …, 2.7,
                                        0.02585257, 7.5e11, 3717]
mat_Al-1.0/FEOS/Al.feos.301      hdr = [37170301, 2.7, 192, 69]
                    → NR=192 / NT=69 ✓✓；末尾 3717 = Al 的 SESAME 材料号 ✓
```

三个字段（`NR`、`NT`、`rho0`）**在两个独立文件里逐一对应**，
所以这不是猜测 —— 是交叉验证。

### 2.2 兄弟文件的两种命名

```python
def find_sibling_301(path, relpath) -> Path | None:
    """实测命名有两种：
       Al.feos  ↔  FEOS/Al.feos.301   （**全名 + .301**，兄弟在 FEOS/ 子目录）
       B.feos   ↔  B.301              （**主干 + .301**，兄弟在同目录）
    —— 两种都要试，且两个目录都要找。"""
    names = [p.name + ".301", p.stem + ".301"]
    for nm in names:
        for d in (p.parent / "FEOS", p.parent):
            ...
```

### 2.3 ⚠️ 诚实声明：列序未定案（风险 R3）

```python
"""⚠️ 诚实声明（风险 R3）
---------------------
``FEOS-Package-Documentation2016.pdf`` §16.2 的正文受 PDF 文本抽取的
连字/断词伪影影响（``F ormat`` / ``t able``），无法可靠还原**每个字段的
语义与数据块列序**。因此本解析器：
* **完全解码** 行 0 的 10 个字段（有 ``.301`` 交叉验证）；
* **定位并解码** rho / T 网格；
* 其余数值按原样存入 ``raw_values`` 并标注待定 —— **不猜测列语义**。
真正的数据块列序留待阶段 B 或人工对照 PDF 定案。
"""
```

实测输出：

```
mat_Al-1.0/Al.feos  → feos_native  status=ok_unverified
  axes   rho (192)   Te (69)
  fields raw_values
  layout F4/FEOS-native: L0=10 字段（已解码）+ rho/T 网格 + 数据块（列序待定）
```

★ 这就是本项目的处理原则：**宁可标"待定"，不编一个看起来合理的列序**。
`ok_unverified` 状态与 `列序待定` 的 layout_rule 就是这条不确定性的**记账**。

---

## 3. 一个重要的"命名陷阱"

`mat_Al-1.0/AL_eos.feos` 的**文件名说 `.feos`，内容是 F1 反演 EOS**：

```
mat_Al-1.0/AL_eos.feos
  declared = ['feos_native', 'multi_inverted_eos']
  → fam = multi_inverted_eos
    rule = declared:extension->fallback@1:multi_inverted_eos
  axes  = rho (66)  de (74)
  hdr   = '     37181000    .27000000E+01  .66000000E+02  .74000000E+02'
```

候选回退救了它（`multi_inverted_eos` 在候选第 2 位）。
详见 [02 §4](02_两段式执行.md)。

### 3.1 反向陷阱：`.dat.feos` 是 **Hyades** 布局

更麻烦的一种：

```
hyades/sesame/eos_41.dat.feos     ← 首行 'ALUMINUM  LANL SESAME #3711 …'
hyades/qeos/qeos_392.dat.feos     ← 首行 'Silicon   LLNL QEOS DATED: 062695'
```

这两个文件的**内容**是标准 Hyades 布局（含 `L = 2+NR+NT+2·NR·NT`），
只是被 FEOS 工具重新生成后**在原文件名后追加了 `.feos`**。

初版实现里，`.feos` 扩展名规则**抢先**于 `hyades` 路径规则命中，
于是：

```
declared = ['feos_native', 'multi_inverted_eos']
→ 两个候选都失败
→ last-resort: generic_curve
→ 解析成 4 个泛型列（col1..col4），**Hyades 布局信息全丢**
```

**修法**：把 Readme 的**原文顺序**还原成代码 ——
上游把"文件名和路径中有 `hyades`"列为**第一条**规则：

```python
plow = rel.lower()
if "hyades" in plow:                        # ★ 提到扩展名之前
    fams = (["hyades_opacity", "hyades_eos"] if "/opacity/" in plow
            or low.startswith("opc_")
            else ["hyades_eos", "sesame_dat", "hyades_opacity"])
    merged = fams + [f for f in ext_fams if f not in fams]   # 扩展名降级为回退
    dt.notes.append(f"Readme.txt rule #1: path contains 'hyades' → {fams}"
                    + (f"（扩展名候选 {ext_fams} 已降级为回退）" if ext_fams else ""))
    dt.families = merged
    dt.source = "path"
    dt.evidence = "path contains 'hyades'"
```

修复后：

```
hyades/sesame/eos_41.dat.feos   → fam=hyades_eos  rule=declared:path->first:hyades_eos
                                   axes={'rho': 44, 'Te': 22}  fields=['P','E','raw_tail']
hyades/qeos/qeos_392.dat.feos   → fam=hyades_eos  rule=declared:path->first:hyades_eos
                                   axes={'rho': 68, 'Te': 67}  fields=['P','E','raw_tail']
```

★ 这条修复的价值不在于"多解析了 2 个文件"，而在于
**恢复了 `L` 公式、`Zbar`/`Abar`、`P`/`E` 的物理语义** ——
泛型 4 列是"收下了但什么都没说"，Hyades 解析是"真的解出来了"。
这就是 [02 §3.2](02_两段式执行.md) 里把 `generic_curve` 单列计数的原因：
它不是成功，是**降级**。

---

## 4. **全局陷阱**：路径含 `hyades` 但不含 `hyades` 语义

`matter++/hyades/list.xls`、`hyades/EOS.list`、`hyades/Opacity.list`、
`hyades/### Data from hyades%Data directory.txt` —— 都在 `hyades/` 目录下，
但**不是** Hyades 数据表。它们由**前置的 skip 规则**拦掉：

```python
_SKIP_EXT     = {".xls", ".xlsx", ".doc", ".pdf", …}
_SKIP_NAMES   = {"readme", "readme.txt", "modinfo", "filelist", "lock", …}
_SKIP_PREFIXES = ("~$", "#")
_SKIP_NAME_HINTS = («list», «note», «readme»…)      # 文件名像自由文本
```

skip 规则在 `declare()` 的**第 0 步**，先于一切类型判定 —— 顺序很重要。

---

## 5. 单位换算的落点

```python
table.unit_source = "format:F4 (GPa->Mbar, MJ/kg->Mbar*cm3/g, T Kelvin->eV)"
table.field_units["P"] = "Mbar"
table.field_units["E"] = "Mbar*cm3/g"
table.axis_units["Te"] = "eV"
```

换算常量集中在 `config.py`（`MBAR_PER_GPA = 1e-2`、
`MBAR_CM3_G_PER_MJ_KG = 1e-2`、`EV_PER_K`），换算发生在**解析层**，
口径写进 `unit_source`。详见 [15 单位换算](15_单位换算.md)。

---

## 6. `feos_tabdata` 与 `feos_aux`：**明确不猜**

### 6.1 `feos_tabdata`（`.data.txt`，ShowEOS 导出）

实测 `mat_B/B.data.txt`：**12 524 行 × 10 列，制表符分隔**。

```
0	0	 0.00000000e+00	 0.00000000e+00	 3.53712002e-53	 8.86026323e-54 …
1	0	 2.34000000e-05	 0.00000000e+00	 3.53712002e-53	 2.30141416e+00 …
   ↑  ↑
   列 1、2 是两个索引（i、j）
```

```python
"""由于**本地无该导出的列名文档**，列语义按 ``colN`` 命名并**整体原样保留** ——
绝不猜测物理含义。行内数值可用 ``.301`` 兄弟文件交叉核对。"""
```

实现要点：
- 先试制表符分隔，列数不足 2 时退回 `str.split()`
- 取**众数列数** `ncol`，任何行不等于 `ncol` 则抛 `CountMismatch`
  （**不静默丢弃不合规的行**）

### 6.2 `feos_aux`（`.PAR` / `.cst` / `.mexport` / `.INV` / `*.critical.dat` / `*.isobaric.dat`）

```python
"""这些是 FEOS/ShowEOS 的**参数与导出**文件，不是标准表格。共同特征：
* 分节标题（如 ``Q-table`` / ``Material-7386:``）
* ``key = value`` 行
* 注释以 ``%`` 或 ``#`` 开头（逐字来自 FEOS PDF §4）

本解析器把它们统一为 ``AUX`` 表：``sections``（节名 → kv 字典）+
``numbers``（全部数值，原样保留）。**不猜测物理语义** —— 这些文件的价值在于
**参数溯源**（与伴随注释文件互补），而非数值网格。"""
```

★ 60 个 `feos_aux` 文件的价值是**证据**而非数据：
它们是"这个 FEOS 表是用什么参数算出来的"的档案，
和 [03 注释证据通道](03_注释证据通道.md) 是同一个思路。

---

## 7. 测试覆盖

| 测试文件 | 个数 | 关键断言 |
|---|---|---|
| `test_mpqeos.py` | 9 | `4+nr+nt+3·nr·nt`；两个实测文件计数严格相等；W=15/16 都识别；`Id(1111)` 不当材料身份；GPa/MJ·kg⁻¹ 换算 |
| `test_feos_native.py` | 6 | 行 0 的 10 字段；`find_sibling_301` 两种命名；与 `.301` 的 NR/NT/rho0 **交叉验证**；`raw_values` + 列序待定标记 |
| `test_declared_types.py` | 11 | `.301/.304/.305` → `mpqeos`；`.feos` → `feos_native`；**`hyades` 路径优先于 `.feos`**（§3.1 的回归测试） |
| `test_generic_curve.py` | 5 | `.ini` 等收尾文件的 `expected = seen`（偏差已登记，不再报 mismatch） |
