# 06 · 格式规格 F3 · Hyades / SESAME ASCII

| 项 | 值 |
|---|---|
| **族名** | `hyades_eos`（EOS）/ `hyades_opacity`（不透明度） |
| **解析器** | `eosop_pro/parsers/hyades_eos.py` |
| **文件数** | EOS 99 + 不透明度 36 = **135** |
| **目录** | `matter++/hyades/{sesame,qeos,Opacity}/` |
| **典型文件** | `hyades/sesame/eos_41.dat`（Al）、`hyades/Opacity/opc_1031.dat`（Polyethylene） |
| **定宽** | **5 字段 × 15 字符 / 行** |
| **独立变量** | `(rho, T)` —— **正表**（不是反演表） |
| **单位** | `rho` g/cm³；`T` **keV** → 归一到 eV；`P` dyne/cm²；`E` erg/g |
| **坐标系** | **线性** |

**权威依据（以上游说明书为准）**：
- `docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt`
  （源：`doc/Hyades 数据格式说明.doc` / `matter++/hyades/Hyades 数据格式说明.doc`）
  → "Appendix III - Equation of State ASCII Material File Format"
- `matter++/Readme.txt`：*"如果文件名和路径中有 `hyades`，程序识别为 hyades 程序的文件"*
- 实样：`hyades/sesame/eos_41.dat`、`hyades/Opacity/opc_1031.dat`

---

## 1. 上游原文（逐字）

### 1.1 文件格式

> **EOS ASCII 数据格式 (Appendix III - Equation of State ASCII Material File Format)**
>
> 例：`eos_2051.dat`
> ```
> GOLD  LANL SESAME #2700-304 DATED: 81678 101582
>   2051  7.90000000E+01 1.96967000E+02 1.93000000E+01  4772
>  1.01000000E+02 2.30000000E+01 0.00000000E+00 1.50781250E-01 2.87685800E-01
>  4.24600000E-01 8.15425000E-01 1.20625000E+00 1.99433269E+00 2.78242310E+00
>  ...
> ```
> 行 1：材料名和生成的历史信息
> 行 2：HYADES EOS 编号，Zbar, Abar, Rho, **数组长度**
> 行 3 起：`NR, NT, RHO(1~NR), T(1~NT), P(1~NR*NT), E(1~NR*NT)`
> **数组长度 = 2 + NR + NT + 2*NR*NT**

**验算（上游自己的例子）**：`NR=101, NT=23`
→ `2 + 101 + 23 + 2·101·23 = 2 + 101 + 23 + 4646 = 4772` ✅
和行 2 第 5 字段 `4772` 严格一致。

### 1.2 单位（逐字）

> **单位：密度 g/cm3; 温度 keV; 压强 dyne/cm2; 比内能 erg/g**

★ 注意 **温度是 keV**（MULTI 族是 eV，差 10³）。

### 1.3 编号约定

> 状态方程材料编号 < 998；使用双温表格时，**电子流编号 2001-2999，离子流编号 3001-3999**
> 灰度不透明度模型编号 **1001-1999**

### 1.4 不透明度文件

> 不透明度参数使用同样的格式，**压强处为平均 Rosseland 值，比内能处为平均 Planck 值，单位 cm2/g**
>
> 例：`opc_1151.dat`
> ```
> DEUTERIUM  LANL SESAME #15264 DATED:  21793  21793
>   1151  ...
> ```
> 数组长度 = 2 + NR + NT + 2*NR*NT

以及附录 I 的一条关键说明：

> `*` Rosseland mean tables only —— **本来应该存储 Planck 平均不透明度的位置用 0 代替。**

★ 这一条决定了 `opc_*` 文件的**数组顺序判定规则**（见 §3）。

### 1.5 Hyades 数据库的文件清单（原文摘录）

| 文件 / 目录 | 内容 |
|---|---|
| `Ionpot.dat` | 离化势文件（用于产生和再启动 phase） |
| `Coldopac.dat` | 冷不透明度（多群在线计算在低温不可靠，故提供室温分频数据，能点较少） |
| `Eoslib.lbf` | EOS 数据库（**二进制**） |
| `Opaclib.lbf` | 不透明度数据库（**二进制**） |
| `Tfdat.lbf` | QEOS 的 Thomas-Fermi 数据库（**二进制**） |
| `Opacity/` | 不透明度数据库（**都是单群**） |
| `Qeos/` | EOS 数据库，QEOS 模型 |
| `Sesame/` | EOS 数据库，SESAME |

三个 `.lbf` 是二进制 → 走 `skipped_non_numeric`（登记但不算问题）。

---

## 2. 实测样本（`hyades/sesame/eos_41.dat`）

### 2.1 原始文本

```
L0 (48 chars) : 'ALUMINUM    LANL SESAME #3711 DATED: 22581 11483'
L1            : '    41     1.30000000E+01 2.69820000E+01 2.75681460E+00    2004'
L2 (75 chars) : ' 4.40000000E+01 2.20000000E+01 0.00000000E+00 2.75681460E-04 4.04645046E-04'
L3            : ' 5.93937702E-04 8.71781324E-04 1.27959999E-03 1.87819593E-03 2.75681460E-03'
```

- `L0` 是**自由文本注释**，48 字符（不是 5×15=75）
- `L1` 是 5 个数：`id=41, Zbar=13.0, Abar=26.982, rho0=2.7568, L=2004`
- `L2` 起是 **75 字符 = 5×15** 的定宽 payload，前两个数是 `NR=44, NT=22`
- 文件共 **404 行**

### 2.2 解析结果

```
status   ok          family  hyades_eos
nr 44   nt 22
count    actual=2005   expected=2005     ← 相等
axes     rho (44)   Te (22)
fields   P (22,44)  E (22,44)  raw_tail (1,)
axis_units   rho: g/cm3        Te: eV
field_units  P: dyne/cm2       E: erg/g        raw_tail: unknown
layout   F3: L = 2 + nr + nt + 2*nr*nt
unit_source  format:F3 (rho g/cm3, T keV->eV, P dyne/cm2, E erg/g)
```

**验算**：`2 + 44 + 22 + 2·44·22 = 2 + 44 + 22 + 1936 = 2004 = L` ✅
（`actual = 2005 = L + 1`，多出来的 1 是**尾部补零**，见 §4.2）

### 2.3 三个基准文件（解析器 docstring 里长期维护）

| 文件 | `L` | 解出 `(NR, NT)` | 材料 |
|---|---|---|---|
| `sesame/eos_11.dat` | 2577 | (50, 25) | DT |
| `sesame/eos_21.dat` | 4743 | (43, 54) | Glass |
| `sesame/eos_41.dat` | 2004 | (44, 22) | Aluminum |
| `Opacity/opc_1031.dat` | 2931 | (31, 46) | Polyethylene |

---

## 3. 不透明度文件：`[Rosseland, Planck]` 的顺序判定

`opc_1031.dat` 实测：

```
status  ok        family  hyades_opacity
nr 31   nt 46
count   actual=2931   expected=2931
fields  Rosseland (46,31)   Planck (46,31)
field_units  Rosseland: cm2/g   Planck: cm2/g
```

**验算**：`2 + 31 + 46 + 2·31·46 = 2 + 31 + 46 + 2852 = 2931 = L` ✅

### 判定算法

上游约定是"压强处 = Rosseland，比内能处 = Planck"，但
`*` 标记的 Rosseland-only 表会把 **Planck 槽位填 0**。所以：

```python
def _opacity_order(a1, a2) -> tuple[str, str]:
    """SESAME 301 约定：Planck 槽位全零 ⇒ 该表只含 Rosseland。"""
    zero1 = all(v == 0 for v in a1)
    zero2 = all(v == 0 for v in a2)
    if zero2 and not zero1:
        return ("Rosseland", "Planck")     # 槽位 2 全零 → a1 是 Rosseland
    if zero1 and not zero2:
        return ("Planck", "Rosseland")     # 槽位 1 全零 → a2 是 Rosseland
    return ("Rosseland", "Planck")         # 无零 → 按上游默认顺序
```

判定结果写进 `table.notes`：`数组顺序判定 = ('Rosseland', 'Planck')`，
**报告里能查到是怎么判的**。

---

## 4. 四个必须注意的坑

### 4.1 `L` 反解维度**不唯一** —— 维度必须来自 payload

方程 `2·NR·NT + NR + NT + 2 = L` 对 `L = 2004` 有多个正整数解：

| `(NR, NT)` | 验算 |
|---|---|
| `(44, 22)` | `2 + 44 + 22 + 1936 = 2004` ✅ |
| `(2, 400)` | `2 + 2 + 400 + 1600 = 2004` ✅ |
| … | 还有更多 |

**所以 `NR/NT` 只能由 payload 的前两个数确定**，不能解方程：

```python
def solve_dims(length) -> list[tuple[int, int]]:
    """求 2*NR*NT + NR + NT + 2 = L 的**全部**正整数解，仅作交叉校验。

    变形：NT = (L - 2 - NR) / (2*NR + 1)，只用整除判别，无浮点误差。
    """
```

解析后**双向校验**：若 payload 读出的 `(nr,nt)` 不在 `solve_dims(L)` 里，
在 `notes` 里写 `⚠️ … 布局存疑` 而不是硬改。这比"相信方程"安全，
因为 `L` 字段本身可能被上游写错。

### 4.2 尾部补零：不能当成 `count_mismatch`

`eos_41.dat` 实测有 **1 个**尾部补零 —— 上游为了让每行凑满 5 个字段
而额外补的数。这是**有意的填充**，不是数据错误。

但如果 `expected` 只算公式值（2004）而 `seen` 算实际数（2005），
就会误报 `count_mismatch`。修法（源码注释写得很直白）：

```python
# 计数守恒：seen 含补零，expected 也必须含补零，否则会把「已定性并记录的填充」
# 误报成 count_mismatch（这是实测踩过的坑）。
table.n_numbers_seen     = len(values_all)
table.n_numbers_expected = L + len(tail_vals)
```

并把补零**原样保留**成一个独立字段：

```python
table.fields["raw_tail"]      = tail_vals
table.field_shape["raw_tail"] = (len(tail_vals),)
table.field_units["raw_tail"] = "unknown"
```

并在 `notes` 里留痕：

> `⚠️ 数组末尾有 1 个补零（实测为该族凑满每行 5 字段的填充），已按原样保存为 raw_tail`

★ 注意 `field_units["raw_tail"] = "unknown"` —— **不猜单位**。
一个未知语义的填充值不该被赋予任何物理量纲。

### 4.3 DOS EOF 标记

`hyades/sesame/eos_*.dat` 的末行可能有 `\x1a`（DOS Ctrl-Z 文件结束符）。
若不处理，最后一个字段会变成 `"1.234E+00\x1a"` → `float()` 失败。

```python
DOS_EOF = "\x1a"
# 扫描时剥离，并登记：
table.notes.append("含 DOS EOF 标记 \\x1a（已忽略，不参与数值）")
```

### 4.4 `T` 是 keV，解析时归一到 eV

```python
T_scale = {"kev": 1e3, "ev": 1.0}.get((unit_hint_T or "keV").lower(), 1e3)
table.axes["Te"] = [t * T_scale for t in T_keV]
table.axis_units["Te"] = "eV"
table.unit_source = "format:F3 (rho g/cm3, T keV->eV, P dyne/cm2, E erg/g)"
```

★ `unit_hint_T` 来自**伴随文件/内联注释**（见 [03](03_注释证据通道.md)）。
缺省按族约定 `keV`，但这个缺省**会体现在 `unit_source` 里**——
`format:F3 (… T keV->eV …)` 就是"我用的是族默认值"的痕迹。

---

## 5. 与 F1 的关系：互为反演对

上游文档在 Hyades 那篇的最后专门写了一段：

> **Inverted EOS**
> 为了在 Multi1D 中使用 Hyades 的 EOS 数据，需要将 Hyades 的 EOS 数据进行 Invert，
> 将 `P(R, T)`，`E(R, T)` 转化为 `P(R,E)`，`T(R,E)`。
> 对于 `P(R, E)`：对某个密度 R，首先根据 `E(R, T)` 找到对应的温度 `T(R, E)`，
> 这个过程需要差值；`P(R, E) = P(R, T(R, E))`，这里同样需要差值。

也就是说：

```
F3（Hyades/SESAME 正表）  ──invert──▶  F1（MULTI 反演表）
        (rho, T) → P, E                   (rho, de) → P, T
```

**这两个方向在本项目里都已实现**：

| 方向 | 实现 | 入口 |
|---|---|---|
| F1 → F3 | `convert.write_hyades_eos(invert=True)` | `cli convert <F1> --to hyades_eos --invert` |
| F3 → 统一网格 | `writer._write_unified_from_te_table` 直接插值（F3 已是 `(rho,Te)`） | `cli h5 <F3>` |

实测 F1 → F3 的往返：

```
EOS_37181000 -> hyades_eos: outputs/logs/t3.dat
re-parsed: EOS_37181000 66 74 9910
```

`L = 2 + 66 + 74 + 2·66·74 = 2 + 66 + 74 + 9768 = 9910` ✅
写出的 Hyades 表能被 F3 解析器**原样读回**，形成闭环。

---

## 6. 测试覆盖

`test_hyades_eos.py`（10 个测试）：

| 测试 | 断言 |
|---|---|
| `L` 公式 | 4 个基准文件的 `2+nr+nt+2nr·nt == L` |
| 维度来源 | `(nr,nt)` 来自 payload 前两数；`solve_dims` 只做交叉校验 |
| `solve_dims` 多解 | `L=2004` 至少返回 2 个解（证明不能唯一反解） |
| 尾部补零 | `expected == L + len(raw_tail)`；`raw_tail` 单位标 `unknown` |
| 补零留痕 | `notes` 含"补零"字样 |
| DOS EOF | `\x1a` 被剥离且登记 |
| 不透明度顺序 | `opc_1031.dat` → `Rosseland`/`Planck`；全零槽位时有序交换 |
| 单位归一 | `Te` 标 eV，`unit_source` 含 `keV->eV` |
| T-major | `P` 形状 `(nt, nr)`，rho 快变 |
| 往返 | F3 → h5 → 再解析，维度与计数一致 |
