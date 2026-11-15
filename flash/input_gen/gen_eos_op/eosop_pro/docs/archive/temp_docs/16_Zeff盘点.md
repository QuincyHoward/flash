# 16 · Z̄ 数据源盘点

> **用户的要求**：*"做 Z̄ 数据源盘点。"*

Z̄（平均电离度 / mean ionisation）在物理上是"密度与温度的函数"，
在数据上却有**九种不同来源、四种不同温度单位**。
本篇的结论是：

> **Z̄(ρ,T) 表覆盖 130/251 材料；其余 121 个只有常量 Z。
> 单位必须靠声明裁决 —— 0 个文件单位存疑（都定案了）。**

---

## 1. 为什么 Z̄ 要单独盘点

Z̄ 是 `(n_ele, Te)` 网格的**必需输入**（`n_ele = ρ·Z̄(ρ,T)·N_A/Ā`，
见 [13 §1](13_统一网格与插值.md)）。所以"某个材料能不能做 `nele_Te` 网格"
等价于"这个材料有没有 Z̄(ρ,T) 表"。

Z̄ 在 `matter++` 里散落在**九种不同文件**里，且**温度单位不同**：

| # | 来源 | 文件数 | 布局 | T 单位 |
|---|---|---|---|---|
| Z1 | `Thermos/*_Zeff.dat` | 45 | F2 灰度 `[log10ρ][log10T][Z̄]` | **keV** |
| Z2 | `Thermos/*_Z.dat` | 45 | 与 Z1 **完全同构**（已作废） | **eV** |
| Z3 | `*.ZEFF` / `*.Zeff` | ~12 | F2 灰度 | eV |
| Z4 | `*_op03z` / `*.ZEFF` | ~6 | F2 灰度（SESAME 类型位 2） | eV |
| Z5 | `*100ZEFF` 等 | 4 | F2 灰度 | eV |
| Z6 | `mat_CH2/zeff.out` | 1 | F2 灰度 | eV |
| Z7 | `ATOMIC/*.NoFree` | 9 | 4 数头（LEDCOP 魔数）+ 3 段 | **keV** |
| Z8 | `ATOMIC/*.AvSqFree` | 9 | 同 Z7（是 **Z²**，不是 Z̄） | **keV** |
| Z9 | `.301/.304/.305` 第 5 段 | 82 | 内嵌 Z 数组 | **Kelvin** |

另有**常量 Z** 的四条来源：

| 来源 | 条数 | 含义 |
|---|---|---|
| `material.base` 的 `Z` 关键字 | **251** | 常量名义 Z（每个 MATERIAL 块都有） |
| `material.base` 的 `ZEFF` 行 | **130** | 指向 Z̄(ρ,T) 表文件（**覆盖度定义的核心**） |
| `DatabaseIndex.xml` | 134 | 常量 Zbar |
| `EOS.list` / `Opacity.list` | 120 | 常量 Zbar |

---

## 2. 三条硬结论

### 2.1 结论一：`f2` 槽位是**类型码**，不是 Zbar

`Thermos/mat_Al/Al_Zeff.dat` 的 L0 逐字（`cat -A`）：

```
00000000        0.60000000E+01 2.2000000e+001 2.1000000e+001
↑                ↑              ↑             ↑
SESAME id       类型码 6.0      nr = 22       nt = 21
（全 0，占位符）
```

而铝的 Zbar 在 `DatabaseIndex.xml` 里是 **13**。所以第 2 字段 `6.0`
**不可能是 Zbar**。它是 [20_格式规格与物理量单位手册.md §3.1](20_格式规格与物理量单位手册.md) 里
定案的类型码（`4=ROSSELAND, 6=ZEFF, 7=PLANCK`）。

★ 如果误把 `6.0` 当 Zbar，会得出一张"铝的电离度只有 6"的错表。
这条结论是**两条独立证据**交叉验证出来的（`AU_op03z` 的文件名 + 类型码表）。

计数的顺带验证：`4 + 22 + 21 + 22×21 = 4 + 22 + 21 + 462 = 509`。
文件 128 行：L0 有 4 个数，其后 126 行 × 4 = 504，末行 1 个数 →
`4 + 504 + 1 = 509` ✅

### 2.2 结论二：单位**必须**靠声明

`Thermos/mat_Al/Al_Zeff.dat` 与 `Al_Z.dat`：

```
行数       完全相同（实测各 128 行）
表头       完全同构（仅第 2 字段的类型码与 nr/nt 不同）
logT 区间  差 log10(1000) = 3.000
```

**纯数字无法区分**。裁决依据是上游 `Thermos/Readme.txt` 的文件名模式约定
（详见 [15 §2.1](15_单位换算.md)）：

| 文件 | 裁定 | 依据 |
|---|---|---|
| `*_Zeff.dat` | **keV** | 原文功能句：`X_Zeff.dat`(温度单位为 keV) |
| `*_Z.dat` | **eV** | 原文功能句：以与之前的 `X_Z.dat`(温度单位为 eV) 相区分 |

★ 这条裁定由 `test_zeff_registry.py::test_thermos_zeff_is_keV_and_z_is_eV_by_declaration`
固化 —— 一旦上游修正文档或改文件名约定，测试会提醒我们更新。

### 2.3 结论三：覆盖度 **130/251**

`material.base` 的 251 个 `MATERIAL` 块中，**130 个**声明了 `ZEFF` 行。
其余 121 个只有常量 `Z` → **只能做 Z̄ = const 的近似**，
不能做严格的 `(n_ele, Te)` 网格。

---

## 3. 材料级盘点结果（实测报告）

```
样本总数:            251
Z̄(ρ,T) 表覆盖:       130 个材料   （51.8%）
仅常量 Z:             63 个材料   （25.1%）
按文件名归属:         58 个材料   （23.1%）
都无:                  0 个材料
Z̄ 相关文件:          217
单位存疑:              0          ← ★
```

### 3.1 覆盖度四类

| coverage | materials | 含义 | 能否做 `nele_Te` |
|---|---|---|---|
| `table` | **130** | `material.base` 显式声明 `ZEFF` | ✅ 严格 |
| `table_by_name` | **58** | 仅按文件名 token 归属（未在 registry 声明） | ⚠️ 需人工确认 |
| `nominal_only` | **63** | 只有常量名义 `Z` | ⚠️ 只能近似 |
| `none` | 0 | — | — |

★ `table_by_name` 是**刻意单列**的：这 58 个材料的 Z̄ 表存在，
但 `material.base` **没有引用它们** —— 意味着上游可能弃用了这些文件，
或者只是忘了登记。单列出来让人能逐条判，而不是混进 130 里。

`130 + 58 + 63 = 251` ✅

### 3.2 单位裁决来源分布（文件级，217 个）

| unit_source | files | pct |
|---|---|---|
| `inline` | 100 | 46.1% |
| `companion` | 96 | 44.2% |
| `config_default` | 21 | 9.7% |
| （`envelope`） | **0** | — |

★ **`envelope` 是 0** 是个好消息：说明 90.3% 的 Z̄ 文件单位是**声明来的**
（`inline` + `companion`），只有 9.7% 靠族默认。
**包络反演在 Z̄ 上完全没派上用场** —— 因为它本来就判不出
`Al_Z` vs `Al_Zeff`（§2.2）。

### 3.3 T 单位分布（文件级，217 个）

| T_unit | files | pct |
|---|---|---|
| **Kelvin** | 82 | 37.8% |
| **eV** | 69 | 31.8% |
| **keV** | 66 | 30.4% |

★ **三种单位几乎均分**。这就是为什么"不靠声明、靠猜"必然失败 ——
任何单一默认值都会让约 2/3 的文件错 3 个数量级。

Kelvin 的 82 个全部来自 Z9（`.301/.304/.305` 的第 5 段 Z 数组），
它们的单位由 **F4 族的文档**（MPQeos 用 Kelvin）确定。

### 3.4 解析家族分布（文件级，217 个）

| family | files | pct |
|---|---|---|
| `multi_opacity` | 117 | 53.9% |
| `mpqeos` | 82 | 37.8% |
| `ledcop_zeff` | 18 | 8.3% |

---

## 4. 报告中出现的三个"多单位"材料

| material | mid | Z | n_tables | T_units |
|---|---|---|---|---|
| Gold | 9 | 79.0 | 7 | `Kelvin, eV, keV` |
| Gold | 10 | 79.0 | 7 | `Kelvin, eV, keV` |
| C | 16 | 6.0 | 3 | `eV` |
| DT | 19 | 1.0 | 1 | `eV` |

★ **Gold 一个材料有三种单位的 Z̄ 表**（`AU_op03z` eV、
`Thermos/mat_Au/AuMG_Zeff.dat` keV、`.301` 内嵌 Kelvin）。
这不是错误 —— 是三个不同来源程序各自生成的。
盘点报告把 `T_units` 列成 `Kelvin,eV,keV`，**让人一眼看到这个材料有三种口径**，
而不是"选一个用"。

真实处理：取 `material.base` 的 `ZEFF` 引用（最高优先级），
其余作为备选来源登记在 `/meta/zeff_sources`。

---

## 5. 交付物

| 文件 | 内容 |
|---|---|
| `outputs/reports/zeff_inventory.csv` | 251 行材料级明细（`to_row()`） |
| `outputs/reports/zeff_inventory.md` | 人读：6 个分节 |
| HDF5 `/meta/zeff_sources` | `[n_z × 7]`，随材料 h5 一起落盘 |

`ZEFF_COLUMNS`（`writer/h5_schema.py`）：

```python
ZEFF_COLUMNS = ("relpath", "kind", "family", "units_T", "unit_source",
                "grid", "unit_suspect")
```

★ 每条 Z̄ 来源都带 `units_T`、`unit_source` 与 `unit_suspect` ——
"这个材料的 Z̄ 是从哪个文件、以什么单位来的、单位有没有疑点"
在 h5 里可直接查。

另有一张更细的溯源表 `SOURCES_COLUMNS`（20 列）挂在
`/meta/sources`，逐表记录 `table_key`/`kind`/`family`/`declared_type`/
`inferred_type`/`type_agreement`/`dispatch_rule`/`status`/`sha256`/
`n_numbers_actual`/`n_numbers_expected`/`nr`/`nt`/`n_groups`/
`layout_rule`/`unit_source`/`field_width`/`encoding_used`/`newline_style`
—— 这张表就是"审计报告的一个切片随数据一起走"。

---

## 6. 盘点是怎么"可复核"的

### 6.1 注册表 docstring 就是审计基线

`registry/zeff_registry.py` 的模块 docstring 里维护着完整的九源表
（§1 的那张表）。它同时是：
- 文档（人读）
- 覆盖面检查表（`test_zeff_registry.py` 逐条断言）

★ **改动覆盖面时，docstring 与测试一起改** —— 两者不同步就会被测试抓到。

### 6.2 `unit_source` 逐文件可查

```python
@dataclass
class UnitDecision:
    quantity: str
    unit: str
    source: str        # companion | inline | envelope | config_default | unknown
    evidence: str      # ★ 判定依据原文
```

`evidence` 的实测内容举例：

```
"Thermos/Readme.txt: 'X_Zeff.dat(温度单位为 keV)' → 文件名模式 *_Zeff.dat"
"ATOMIC/Al.txt: 'Opacities in cm**2/gm, T in keV, density in gm/cc'"
"F2 族默认（无针对性声明）"
```

### 6.3 "单位存疑: 0" 不是"没有问题"，而是"没有未定案的"

报告中 `单位存疑: 0` 的含义是：**217 个 Z̄ 文件每一个都有明确的单位裁定**
（不是"没发现冲突"）。0 这个数之所以能报出来，是因为
`UnitRegistry` 对每个文件都给出 `source != "unknown"`。

如果某个文件的单位真判不出来，`source` 会是 `unknown`，
`infer_T_from_logT_range` 会失败，报告中这个数会变成非 0。

---

## 7. 对 `(n_ele, Te)` 后补的直接影响

| 覆盖度 | 材料数 | `(n_ele, Te)` 网格可行性 |
|---|---|---|
| `table` (130) | 51.8% | ✅ 严格：`n_ele = ρ·Z̄(ρ,T)·N_A/Ā` |
| `table_by_name` (58) | 23.1% | ⚠️ 表存在但未被 registry 引用；需人工判 |
| `nominal_only` (63) | 25.1% | ⚠️ 只能 `Z̄ = const` 近似，**误差不可估** |

★ 也就是说：**`nele_Te` 网格只能在约一半材料上严格成立**。
这是后补时需要明确声明的边界 ——
[13 §1.2](13_统一网格与插值.md) 里预留的接口不变，
但"哪些材料能做"要用这张盘点表来筛。

---

## 8. 测试覆盖

`test_zeff_registry.py`（9 个测试）：

| 测试 | 断言 |
|---|---|
| 九源表 | Z1–Z9 每条来源的布局与单位 |
| `*_Zeff.dat` = keV | **按声明**（`companion`） |
| `*_Z.dat` = eV | 同上 |
| 类型码非 Zbar | `Al_Zeff.dat` 的 `6.0` 被判为类型码，**不是** Zbar=13 |
| `sesame_digit_of` | 用 `s[-4]`（`20202000`→2、`27003003`→3） |
| `ATOMIC/*.NoFree` = keV | 单位从主表**内联声明**继承 |
| `ATOMIC/*.AvSqFree` | 标为 Z²（不是 Z̄） |
| `NELEF` 枚举 | 从 `material.base` 的 `ZEFF` 行枚举材料 |
| `newline` | 输出行的列顺序与 `ZEFF_COLUMNS` 一致 |

`test_material_registry.py`（16 个测试）另有：

| 测试 | 断言 |
|---|---|
| 覆盖度 130/251 | `material.base` 的 `ZEFF` 行数 == 130 |
| 四类覆盖度计数 | `table + table_by_name + nominal_only + none == 251` |
| 单位冲突检出 | 包络与声明不一致时标 warning（而非静默采用） |
