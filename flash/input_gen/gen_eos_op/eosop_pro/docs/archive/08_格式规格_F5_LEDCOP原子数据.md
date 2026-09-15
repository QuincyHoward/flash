# 08 · 格式规格 F5 · LEDCOP / ATOMIC 原子数据

| 项 | 值 |
|---|---|
| **族名** | `ledcop_atomic`（13）/ `ledcop_zeff`（18） |
| **解析器** | `parsers/ledcop_atomic.py`、`parsers/ledcop_zeff.py` |
| **文件数** | **31** |
| **目录** | `matter++/ATOMIC/` |
| **典型文件** | `ATOMIC/Al.txt`（**348 636 行 / 13.5 MB**）、`ATOMIC/Al.NoFree`、`ATOMIC/Al.AvSqFree` |
| **维度** | 实测 `Number of T = 69  Number of rho = 50` |
| **单位** | `kappa` cm²/g；**`T` keV**；`rho` g/cm³（三者都在**内联声明**里写明） |
| **坐标系** | 灰度段线性输出；多群段按 `Energy` 列（eV）给出 |

**权威依据**：
- `docs/extracted/Atomic_LEDCOP_不透明度格式说明__ooxml-word__4ed7421a.txt`
  （源：`matter++/ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx`，22 092 字符）
- `docs/extracted/Atomic_LEDCOP_说明__ole2-word__ac285300.txt`
  （源：`doc/Atomic(LEDCOP)说明.doc`，19 119 字符）
- 实样：`ATOMIC/Al.txt`、`ATOMIC/Al.NoFree`

---

## 1. 上游原文（逐字）

> **网站导出的 LEDCOP 不透明度格式说明**
>
> **SESAME 格式**：与 MULTI 默认的格式不同，比较难以解析，此处略。
>
> **LEDCOP 格式**：文件名 `Al.txt`
>
> ```
> Number of T =  69  Number of rho =  50  Number of materials =  2
>
>  TOPS results for  LiH  on Sep  6, 2016
>
>  Opacities in cm**2/gm, T in keV, density in gm/cc
>
> Normalized composition for requested elements
>
> No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
>   5.0000E-01  8.7320E-01  3  Li  4922
>   5.0000E-01  1.2680E-01  1  H  4525
>
> Temperature grid used the following  69 points
> 5.0000E-04  6.0000E-04  8.0000E-04  ...
>
> Density grid used the following  50 points
>   1.0000E-03  1.2068E-03  1.4563E-03  ...
>
> Rosseland and Planck opacities and free electrons
>  Density  Ross opa  Planck opa  No. Free  Av Sq Free  T=  5.0000E-04
>   1.0000E-03  8.8707E+04  2.1555E+06  1.2280E-02  1.2280E-02
>   ...
>
> Multigroup opacities
>   Energy  Ross mg  Planck mg  for T, density =  5.0000E-04  1.0000E-03
>   1.0000E-03  1.9954E+04  1.9957E+04
>   ...
> ```

★ 这一页是**整个 F5 族的规格**，而且它的第 3 行
`Opacities in cm**2/gm, T in keV, density in gm/cc` 就是
**全库唯一的内联单位声明**（后面 [§3](#3-锚点即证据) 会用它给 18 个拆分件定单位）。

---

## 2. 必须用锚点驱动的**流式状态机**

### 2.1 为什么不能按固定行数

`ATOMIC/Al.txt` 有 **348 636 行**、13.5 MB。多群段的大小是
`nt × nr` 个块：

```
69 × 50 = 3450 个 (T, rho) 块
每块 ≈ 99 行（1 行头 + 98 行数据）
合计 ≈ 341 550 行  ← 全文行数的 98%
```

任何"先把全文读进内存再处理"的做法都会：
1. 峰值内存 ×3～5（原始字符串 + 行列表 + 数值列表）
2. 无法增量控制（不能只解析灰度段）

### 2.2 状态机

```python
# 状态：见 parsers/ledcop_atomic.py
INIT → DIMS → SOURCE → UNITS → COMPOSITION → T_GRID_HDR → T_GRID
     → RHO_GRID_HDR → RHO_GRID → GRAY_BLOCK (×nt) → MG_HEADER → MG_BLOCK (×nt×nr)
```

每一次状态迁移都由**锚点命中**触发，不由行号：

```python
ANCHORS = {
  "ledcop_n_t":         r"Number\s+of\s+T\s*=\s*(\d+)",
  "ledcop_n_rho":       r"Number\s+of\s+rho\s*=\s*(\d+)",
  "ledcop_n_mat":       r"Number\s+of\s+materials\s*=\s*(\d+)",
  "ledcop_units":       r"Opacities\s+in\s+cm\*\*2/gm,\s*T\s+in\s+(\w+),"
                        r"\s*density\s+in\s+(\S+)",
  "ledcop_source":      r"(TOPS|Ledcop|LEDCOP)\s+results\s+for\s+(\S+)\s+on\s+(.+)",
  "ledcop_comp_header": r"No\.\s+Fraction\s+Mass\s+Fraction\s+At\.\s*No\.\s+"
                        r"Chem\.\s*Sym\.\s+Mat\s+ID\.",
  "ledcop_t_grid_hdr":  r"Temperature\s+grid\s+used\s+the\s+following\s+(\d+)\s+points",
  "ledcop_rho_grid_hdr":r"Density\s+grid\s+used\s+the\s+following\s+(\d+)\s+points",
  "ledcop_block_T":     r"Density\s+Ross\s+opa\s+Planck\s+opa\s+No\.\s+Free\s+"
                        r"Av\s+Sq\s+Free\s+T\s*=\s*",
  "ledcop_mg_block":    r"Energy\s+Ross\s+mg\s+Planck\s+mg\s+for\s+T,\s*density\s*=",
}
```

用到 `textio.iter_lines()`（**流式**），不 `read_text()`。

### 2.3 内存纪律（写进 docstring）

```python
"""★ 内存纪律
多群段有 ``nt*nr`` 个块（Al 为 69×50=3450 块 × 99 行 ≈ 34 万行）。
故 ``include_multigroup`` 默认 **False**；开启时才解析（并会显著吃内存）。
灰度段（``T=`` 块）只占 nt 块，开销小。"""
```

对应到 CLI：`audit` / `convert-all` 都有 `--multigroup`，**默认关闭**。
所以 13 个 `ledcop_atomic` 文件默认只解析出**头 + 灰度段**，
多群留到真正需要时再开。这个取舍被显式记录在
[01 §8 已知边界](01_总览.md)。

---

## 3. 锚点即证据

### 3.1 内联单位声明决定 `ledcop_zeff` 的单位

`ATOMIC/*.NoFree` / `*.AvSqFree` 是主表的**预拆分件**，自身**没有单位声明**：

```
<魔数 0.1234567E+000>  <1.0>  NR  NT
[log10 rho (NR)] [log10 T (NT)] [值 (NR*NT)]
```

但主表 `ATOMIC/Al.txt` 里写了 `T in keV`。所以解析器的结论是：

> 单位：rho log10 g/cm3；**T log10 keV**（由 ``ATOMIC/*.txt`` 的内嵌声明
> ``Opacities in cm**2/gm, T in keV, density in gm/cc`` 佐证）。

★ **拆分件的单位是从主表的注释里继承来的** —— 这是
[03 注释证据通道](03_注释证据通道.md) 的一个跨文件案例：
证据不在文件自己身上，而在同族的另一个文件里。

### 3.2 两个拆分件的物理含义

| 文件后缀 | 值字段含义 | 对应量 |
|---|---|---|
| `*.NoFree` | 自由电子数 | **Z̄（平均电离度）等价量** |
| `*.AvSqFree` | 自由电子数平方均值 | **Z² 等价量** |

后者是 Z̄ 之外的第二个矩，用于诊断电离度分布的展宽 ——
这是 Z̄ 盘点（[16](16_Zeff盘点.md)）里 `by_name` 类来源之一。

### 3.3 计数

```
N = 4 + NR + NT + NR·NT
```

实测基准（解析器 docstring 里长期维护）：

```
ATOMIC/Al.NoFree  →  NR=50, NT=69,  总数 3573 = 4 + 50 + 69 + 3450  ✅
```

---

## 4. 灰度段与多群段的差异

| 段 | 头行 | 块数 | 每块内容 |
|---|---|---|---|
| **灰度** | `Density Ross opa Planck opa No. Free Av Sq Free T= <T>` | `nt`（69） | `nr` 行 × 5 列 |
| **多群** | `Energy Ross mg Planck mg for T, density = <T> <rho>` | `nt×nr`（3450） | `np` 行 × 3 列 |

灰度段的 5 列全部有明确语义（`Density`、`Ross opa`、`Planck opa`、
`No. Free`、`Av Sq Free`），所以在 `ParsedTable` 里能命名：

```python
table.fields = {"Ross_opacity": [...], "Planck_opacity": [...],
                "n_free": [...], "av_sq_free": [...]}
table.field_shape = {"Ross_opacity": (nt, nr), ...}
```

多群段每块是一个**独立能量网格**（`np` 不固定），
所以按 `group_bounds` + 每块的 `np` 逐块登记。

---

## 5. 单位：F5 是 keV，而 F2 是 eV

这是全库**最容易出错的一处**：

| 族 | T 单位 | 来源 |
|---|---|---|
| F2 `multi_opacity`（`AU_op03z` 等） | **eV** | 上游 SESAME 文档 |
| F2 `*.Zeff.dat`（Thermos） | **keV** | 上游 2016-01-09 修正 |
| F3 `hyades_eos` | **keV**（文件里） | Hyades 说明书 |
| F4 `mpqeos` | **Kelvin**（文件里） | MPQeos 说明 |
| **F5 `ledcop_*`** | **keV** | **内联声明** |
| F1 `multi_inverted_eos` | **Kelvin**（文件里） | MULTI 说明 |

F5 的 keV 是**声明来的**（不是族默认值），所以 18 个 `ledcop_zeff` 的
`unit_source` 是 `inline:...` 而不是 `default:...`。

详见 [15 单位换算](15_单位换算.md)。

---

## 6. 实测结果（`ATOMIC/` 目录）

| 文件 | NR | NT | 说明 |
|---|---|---|---|
| `Al.txt` | 50 | 69 | 主表，348 636 行 |
| `C.txt` | 50 | 69 | 主表 |
| `CH2.txt` | 50 | 69 | 化合物 |
| `CH2Al0.02.txt` 等 | 50 | 69 | 掺 Al 变体 |
| `Al.NoFree` | 50 | 69 | 总 3573 |
| `Al.AvSqFree` | 50 | 69 | 总 3573 |

`ATOMIC/` 下的 `*.MixedOpacity_*`、`*.MultiGroupOpacity_*`、
`*.GrayOpacity_*`、`*.Rosseland`、`*.Planck` 等后缀另有专门的候选链
（`ATOMIC/` 路径规则给出 `["ledcop_atomic", "ledcop_zeff", "multi_opacity"]`）。

---

## 7. 单位与规模的"陷阱清单"

| 陷阱 | 后果 | 修法 |
|---|---|---|
| 用 `read_text()` 读 348 636 行 | 峰值内存 >1 GB | `iter_lines()` 流式 |
| 默认解析多群段 | 单文件耗时 >10 s，全树不可行 | `include_multigroup=False` 默认 |
| 假设灰度段行数固定 | 状态机错位 | 全部由锚点驱动 |
| 假设拆分件自带单位 | `ledcop_zeff` 全部 `ok_unverified` | 从主表注释继承单位 |
| 把 `np` 当常量 | 多群块间错位 | 每块独立读 `np` |

---

## 8. 测试覆盖

`test_ledcop.py`（9 个测试）：

| 测试 | 断言 |
|---|---|
| 锚点解析 | 11 条 `ledcop_*` 锚点在真实头部全部命中 |
| 维度 | `Number of T/rho` 与实测网格长度一致（69 / 50） |
| 内联单位 | `ledcop_units` 抽出的 `T in keV` 进入 `unit_source`（`inline:` 前缀） |
| 拆分件计数 | `Al.NoFree` = 3573 = `4+50+69+3450` |
| 拆分件单位继承 | `ledcop_zeff` 的 `Te` 单位标 keV，且 `unit_source` 指回主表声明 |
| 灰度块 | `T=` 块数 == `nt` |
| 多群默认关闭 | 不传 `include_multigroup` 时多群段不参与计数 |
| 流式 | 解析 `Al.txt` 的峰值内存受控（不构建全行列表） |
| 成分块 | `Mat ID.` 行解析出 `(fraction, mass_fraction, Z, symbol, mat_id)` |
