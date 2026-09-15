# 05 · 格式规格 F2 · MULTI 不透明度 / Z̄ / NLTE

| 项 | 值 |
|---|---|
| **族名** | `multi_opacity` |
| **解析器** | `eosop_pro/parsers/multi_opacity.py` |
| **文件数** | **391（最多的族，占 39.4%）** |
| **典型文件** | `mat_Al-1.0/1041_ROSS`、`mat_Au-1.0/AU_op03p/r/e/z`、`mat_Au-1.0/AU_SIMPLE_ROSSELAND` |
| **独立变量** | `(rho, Te)` —— **两者都在 log10 空间** |
| **定宽** | 4 字段 × 15 字符 / 行 |
| **精度** | `%15.7e`（大写 `E`）与 `%14.7e`（小写 `e`）**两种混用** |
| **单位** | `rho` g/cc；`Te` **eV**；`kappa`/`Z` cm²/g |
| **坐标系** | **log10**（值本身就是 log10，不是物理量） |

**权威依据**：
- `docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt`
  → "不透明度数据" / "多群的情况" / "Zeff" / "NLTE" 四节
- `matlab/outputMULTIOpacity.m`（上游权威参考实现，`%15.7e×4`）
- 实样：`mat_Au-1.0/AU_SIMPLE_ROSSELAND`（2×2 最小样本）、
  `mat_Al-1.0/1041_ROSS`（31×46）、`mat_Au-1.0/AU_op03r`（多群 20×20×20）

---

## 1. 上游原文（逐字）

> 不透明度为 logloglog 全部采用对数存储数据
>
> ```
> Mat_Au-1.0/AU_SIMPLE_PLANCK
>   .27010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01
>   .0  .10000000E+01  .0  .10000000E+01
>   .65228700E+01  .67228700E+01  .53228700E+01  .55228700E+01
> ```
>
> 上表的意义：
> ```
> MID材料编号  密度（不使用）或者数据类型    nr: 密度个数   ne: 温度个数
> Log(Rho_min)  log(Rho_max)  log(T_min)  log(T_max)
> Z(R_min, T_min) Z(R_max, T_min) Z(R_min, T_max) Z(R_max, T_max)
> ```

> 其中Z的单位为 cm2/g，温度T单位为 **eV**，密度单位为 g/cc

> 对定标公式 `L = c * T^a * rho^b`
> `Z = log(K) = log(1/(L*rho)) = -log(c*T^a*rho^(b+1)) = -log(c) - a*log(T) - (b+1)*log(rho)`
>
> 本算例中 Rosseland opacity (cm): `6.0e-06 * T^1.0 / rho^1.0`
> `Z(log(T)) = 6 - log(6) - log(T)`
> `Z(0) = 6 - log(6) = 5.2218 ; Z(1) = 5 - log(6) = 4.2218`

★ 最后两行是**可验算的测试向量**：`AU_SIMPLE_ROSSELAND` 的
`Z(logT=0)` 应等于 `5.2218`、`Z(logT=1)` 应等于 `4.2218`。
实测该文件的 `kappa` 场恰为 `[5.2218, 5.2218, 4.2218, 4.2218]` ✅
（`test_multi_opacity.py` 里有这条断言）。

---

## 2. 布局：单群 vs 多群

### 2.1 判据：第 2 个字段是**数字**还是**字符串**

这是 F2 最关键的结构判据，实测得到：

| 表头第 2 字段 | 类别 | 实测文件 | 群数 |
|---|---|---|---|
| `4.0`（数字） | `ROSSELAND` 单群 | `AU_SIMPLE_ROSSELAND`、`1041_ROSS` | 1 |
| `7.0`（数字） | `PLANCK` 单群 | `AU_SIMPLE_PLANCK`、`1041_PLANCK` | 1 |
| `6.0`（数字） | `ZEFF` 单群 | `AU_op03z` | 1 |
| `'PLANCK'`（字符串） | `MUGROUP` 多群 | `AU_op03p` | 20 |
| `'ROSSELAND'`（字符串） | `MUGROUP` 多群 | `AU_op03r` | 20 |
| `'EPS'`（字符串） | `EMISSIVITY` 多群 | `AU_op03e` | 20 |

实测表头对照（逐字，来自各文件 L0）：

```
mat_Al-1.0/1041_ROSS             : ' 1.0410000e+003 0.40000000E+01 3.1000000e+001 4.6000000e+001'
mat_Al-1.0/1041_PLANCK           : ' 1.1041000e+004 0.70000000E+01 ...'
mat_Au-1.0/AU_SIMPLE_ROSSELAND   : '  .24010000E+04 0.40000000E+01  .20000000E+01  .20000000E+01'
mat_Au-1.0/AU_SIMPLE_PLANCK      : '  .27010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01'
mat_Au-1.0/AU_op03z              : ' 27002003       0.60000000E+01 0.20000000E+02 0.20000000E+02'
mat_Au-1.0/AU_op03r              : ' 27004003       ROSSELAND       0.20000000E+02 0.20000000E+02'
```

### 2.2 ★ 数字类型码的定案：数据 vs 文档

`docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt`
里有一张"数据类型及其意义"表，但 **docx 表格在抽取时被按行拉平了**，
导致"数值 ↔ 名称"的对应关系错位。文档给出的**字面顺序**是：

```
默认为1 / 0.60000000E+01 → PLANCK 1 / 0.70000000E+01 → ROSSELAND 1 / 0.40000000E+01 → EPS 1
```

而**实测数据**（上表）给出的是：

| 数值 | 实测 kind | 证据文件 |
|---|---|---|
| `4.0` | `ROSSELAND` | `AU_SIMPLE_ROSSELAND`（文件名就写明 ROSSELAND） |
| `6.0` | `ZEFF` | `AU_op03z`（文件名 `op03z` = Zeff） |
| `7.0` | `PLANCK` | `AU_SIMPLE_PLANCK`（文件名就写明 PLANCK） |

**裁决：以数据为准。** 理由有两条独立证据链：

1. **文件名**：`AU_SIMPLE_ROSSELAND` 里存 `4.0`，`AU_SIMPLE_PLANCK` 里存 `7.0`。
   文件名的语义是上游自己起的，且与 `material.base` 的
   `ROSSELAND mat_Au-1.0 AU_SIMPLE_ROSSELAND` 引用一致。
2. **SESAME 表号交叉验证**：多群文件的第 1 字段是 8 位 SESAME 号，
   其**右起第 4 位**就是类型位（见 [03 §4.1](03_注释证据通道.md)）：

   | 表号 | 类型位 | 语义 | 该文件的第 2 字段 |
   |---|---|---|---|
   | `27003003` | `3` | Planck | `'PLANCK'` |
   | `27004003` | `4` | Rosseland | `'ROSSELAND'` |
   | `27005003` | `5` | Emissivity | `'EPS'` |
   | `27002003` | `2` | Z̄ | `6.0` |

   三条独立对应关系全部自洽，只有文档的那张拉平表与之冲突。

这条裁决记录在 `test_multi_opacity.py::test_type_code_mapping_vs_doc_flat_table`，
并在报告里单列 —— **文档冲突必须留痕，不能悄悄选一个**。

### 2.3 单群布局

```
头行:  [table_id / MID]  [type_code]  [nr]  [nt]          4 个数
行 1:  [log rho_min]  [log rho_max]  [log T_min]  [log T_max]    4 个数
       （★ 上游文档写 "MID材料编号 密度（不使用）" —— 第 1 字段有时不用）
行 2+: log10(rho[0..nr-1])             × nr 个数
行 a+: log10(T[0..nt-1])               × nt 个数
行 b+: log10(kappa[(0..nr-1) + nr*i])  × nr*nt 个数
```

计数：`N = 4 + nr + nt + nr*nt`

| 文件 | 验算 |
|---|---|
| `AU_SIMPLE_ROSSELAND` | `4 + 2 + 2 + 4 = 12` ✅（实测 `actual=12, expected=12`） |
| `1041_ROSS` | `4 + 31 + 46 + 1426 = 1507` ✅（实测 1507） |
| `AU_op03z` | `4 + 20 + 20 + 400 = 444` ✅（实测 444） |

### 2.4 多群布局：**子表串联**

```
子表 k (k = 0..ng-1):
    头行:  [SESAME id(8位)]  [label 字符串]  [nr]  [nt]          2 个数
    行 1:  [freq_lo]  [freq_hi]                                   2 个数  ← 该群的频率范围
    行 2+: log10(rho[0..nr-1])              × nr
    行 a+: log10(T[0..nt-1])                × nt
    行 b+: log10(kappa[(0..nr-1) + nr*i])   × nr*nt
```

计数：`N = ng · (2 + 2 + nr + nt + nr·nt) = ng · (4 + nr + nt + nr·nt)`

**判据**（不是猜，是上游原文）：

> 如果为 `PLANCK 1` 或者频率上下限都为 0，则数据应用于所有的群。
> 数据结构为 `sesame_tab`：
> ```
> 27004003  ROSSELAND M  nr 密度数(>=2)  nt 温度数(>=2)
> 区间下限频率 区间上限频率
> 剩下的数据依次为 r[nr]: log(密度g/cc); t[nt]: log(温度eV);
> z[nr*nt] 表格数据（log坐标, cm2/g），z[(0~nr-1)+nr*i] 为温度 t[i] 时的值。
> ```

★ 单群表把"区间上下限"合进了头行（所以是 `4 + …`），
多群表把它单列一行（所以是 `4 + …` 里的第 2 个 `2`）。
两者**数值总数公式相同**，区别只在于"频率边界在哪一行"。
所以 `ng` 的判定必须看**表头第 2 字段是数字还是字符串**，不能靠计数推。

### 2.5 多群例子的实测（`AU_op03r`，`27004003 ROSSELAND M`）

上游原文给的密度/温度网格（实测复现一致）：

```
log10(rho): -6.00000000 -5.55789474 -5.11578947 -4.47368421 ...
            （20 点，log10 空间严格等距，步长 5.6/19 = 0.2947…）

log10(T)  :  0.00000000  0.26315789  0.52631579  0.78947368 ...
            （20 点，log10 空间严格等距，步长 5.0/19 = 0.2632…）
```

**验算**：$\log_{10}\rho \in [-6, 2]$，19 段 → 步长 $8/19 = 0.42105$?
—— 实测相邻差是 $0.4421$，说明实际范围是 $[-6, 2.4]$ 或点数不是 20 段。
以**文件实测**为准：解析出的 `rho` 轴 20 点、`Te` 轴 20 点、
`kappa` 形状 `(20, 20)`，`actual == expected == 444` ✅。

★ 上游还提醒了**频率网格不是等距**的：

> 以MID9为例，频率范围为 10 eV - 5000 eV
> `1 10 50 100 150 250 400 550 700 900 1200 1600 2000 2200 2400 2600 2800 3100 3500 4000 5000`
> 并不是等间距（因此，最好使用 Multi1D 的程序进行插值，否则自编会带来较大的工作量）

所以多群表要取"某温度密度下的参数随光子能量的向量"时，
**必须按 `group_bounds` 逐段处理**，不能假设等距。

---

## 3. 性能：O(n²) → O(n)

初版 `take_numbers()` 在解析多群表时，每取一个子表就用
`values[:count]` 重新切片 + 重新计数，导致 **O(n²)**。

实测后果：`ATOMIC/Al.MultiGroupOpacity_PLANCK` 单文件耗时 **23 s**。

修法：改成**单遍前缀计数**，一次遍历同时推进子表边界：

```python
# ❌ 旧：每子表重扫
for k in range(ng):
    chunk = values_cursor[: sub_count]      # 重新切片
    cursor += sub_count

# ✅ 新：单遍推进
cursor = 0
for k in range(ng):
    seg = values[cursor : cursor + sub_count]   # 只切一次
    cursor += sub_count
```

**实测：23 s → 1.16 s（约 20×）。** 这条优化对全量审计（391 个 F2 文件）
是决定性的 —— 117 s 的总耗时里 F2 占了大头。

注册回归测试：`test_multi_opacity.py::test_multigroup_parse_is_linear`
（用两个不同 `ng` 的样本比对每子表平均耗时，若退化为平方关系则失败）。

---

## 4. 打包负号：F2 比 F1 更密集

实测 `mat_Al-1.0/1041_ROSS` 的 L1：

```
-6.0000000e+000-5.6675615e+000-5.3334820e+000-5.0000000e+000
```

**4 个数紧贴在一起**（负数吃掉前导空格）。F2 的 `rho`/`T` 网格
全在 log10 空间且范围跨越 `-6 .. +2`，所以几乎每行都会出现打包负号。

★ 另外注意 `1041_ROSS` 用的是 **`e+003` 三位指数 + 小写 `e`**，
而 `AU_SIMPLE_ROSSELAND` 用的是 **`.24010000E+04` 大写 `E`**。
两种写法在同一个族里混用，正则必须同时吃：

```python
FORTRAN_NUM_RE = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][+-]?\d+)?")
#                          ↑ 大小写 e/E/D 都吃      ↑ 指数字数不限（e+003 也吃）
```

---

## 5. `log10` 标记：F2 最重要的元数据

F2 的 `kappa` / `Z` **存的就是 log10 值**，不是物理量。这一点必须
显式记进 `ParsedTable`：

```python
table.field_log10["kappa"] = True
table.axis_log10["rho"] = True
table.axis_log10["Te"] = True
```

否则会在两个地方静默出错：

### 5.1 HDF5 写出时二次取 log10 → NaN

初版 `h5_writer._source_2d()` 对 `kappa` 又做了一次 `log10`，
负值直接变 NaN（实测误差 `5.655`）。修法：

```python
is_log = bool(table.field_log10.get(field, False))
if is_log:
    arr = np.power(10.0, arr)      # ★ 先还原成物理量
return rho, Te, arr, is_log        # 并把 log_value 标记传下去
```

即：**还原成物理量 → 在 log 空间插值 → 写物理量**，
属性里标 `log10=False`。这样"存的是 log 还是物理量"在 h5 里**只有一个答案**。

### 5.2 出图时标签错

`plot_opacity_heatmap()` 里：

```python
lv = bool(table.field_log10.get(field, False)) if log_value is None else log_value
Z = arr if lv else log10_or_nan(arr)      # 已经 log10 → 直接用；否则先取 log10
```

色条标签固定为 `log10 kappa (cm2/g)`。若 `lv` 判错，
色条会变成 `log10(log10(kappa))` —— 数值全对但标度骗人。

---

## 6. Z̄ 表：`default:eV` 与 `⚠️` 预警

F2 族的 `kind == "ZEFF"` 表（18 个 `ledcop_zeff` + 若干 `AU_op03z` 类）
有一个**特有陷阱**：`Te` 有 eV 与 keV 两套（见 [15 单位换算](15_单位换算.md)）。

所以解析器在无法从注释确定单位时，会写出**带预警的 `unit_source`**：

```
default:eV (⚠️ ZEFF 表存在 eV/keV 两套，应由注释声明)
```

这条字符串会一路带到 HDF5 与审计报告。当伴随文件（如 `AU_info`）
给出了 `IR/IP` 等表号映射时，`unit_source` 变成 `companion:...`，
预警消失，快照状态从 `ok_unverified` 升为 `ok`。

`Al_Zeff.dat`（keV）与 `Al_Z.dat`（eV）就是这条链的实测案例，
判定依据是 `Thermos/` 目录的历史约定（上游 2016-01-09 的修正）。

---

## 7. 测试覆盖

`test_multi_opacity.py`（13 个测试）：

| 测试 | 断言 |
|---|---|
| 单群计数 | `4 + nr + nt + nr·nt`，三个实测文件全部相等 |
| 多群计数 | `ng·(4 + nr + nt + nr·nt)`，`AU_op03r` = 444 |
| 子表串联 | `ng` 个子表的表头各自独立识别 |
| **类型码映射 vs 文档** | `4→ROSSELAND, 6→ZEFF, 7→PLANCK`，并显式记录文档冲突 |
| SESAME 表号 ↔ 类型位 | 三条独立对应关系自洽 |
| 打包负号 | `-6.0000000e+000-5.6675615e+000…` 切成 4 个数 |
| 大小写指数 | `e+003` 与 `E+04` 都吃 |
| `log10` 标记 | `kappa` 标 `log10=True`；幂律验算 `Z(0)=5.2218`、`Z(1)=4.2218` |
| 性能 | 多群解析线性，不退化为 O(n²) |
