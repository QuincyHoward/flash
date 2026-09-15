# 04 · 格式规格 F1 · MULTI 反演 EOS

| 项 | 值 |
|---|---|
| **族名** | `multi_inverted_eos` |
| **解析器** | `eosop_pro/parsers/multi_inverted_eos.py` |
| **文件数** | 41 → **51**（见 §5：4 处分派错误修好后增加 10 个） |
| **典型文件** | `mat_Al-1.0/AL_eos`、`mat_Au-1.0/AU_eos`、`mat_Au-1.0/AU_eosd` |
| **扩展名** | （无）· `.sesame` · `.inv` · `.SESAME_` · `.feos`（仅作回退） |
| **独立变量** | **`(rho, de)`** —— 密度 + **比内能**（**不是**温度！） |
| **定宽** | 4 字段 × 15 字符 / 行 |
| **精度** | `%15.7e`（大写 `E`）与 `%14.7e`（小写 `e`）混用 |
| **单位** | `rho` g/cc；`de`、`e0` Mbar·cm³/g；`P` Mbar；`T` **Kelvin** |
| **坐标系** | **线性**（不是 log10） |

**权威依据**：
- `matter++/Readme.txt`（默认族规则）
- `docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt`
  → "EOS数据" / "Inverted EOS" 两节
- `docs/extracted/AL_eos` 实样 + `mat_Au-1.0/AU_IDEAL_GA`

---

## 1. 为什么"反演"是必需的

MULTI 求解的是 Lagrangian 隐式流体力学，状态量是
`(密度, 比电子能, 比离子能)`（见 `docs/extracted/manual__text__f41e8d74.txt`：

> `ts` – an integer specifying the thermodynamic state, that is
> **density, and specific electron and ion energies**. Other quantities,
> i.e. electron temperature are evaluated in function of these.

也就是说，**温度是导出量**。而源数据库（SESAME / Hyades / MPQeos）
给的是**正表** `P(ρ,T)`、`E(ρ,T)`。为了省去运行时的反演开销，
上游预先把正表**反演**成 `P(ρ,E)`、`T(ρ,E)` 并以定宽文本存盘：
这就是 `Inverted EOS`。

原文：

> 为了在计算时直接使用 EOS 数据，省去转化，需要将 EOS 数据表格中的
> `P(R, T)`，`E(R, T)` 转化为 `P(R,E)`，`T(R,E)`。
> 对于 `P(R, E)`：对某个密度 R，首先根据 `E(R, T)` 找到对应的温度 `T(R, E)`，
> 这个过程需要差值；`P(R, E) = P(R, T(R, E))`，这里同样需要差值。

★ **本项目最重要的一个纠正**：最初把 F1 的独立变量写成了 `(rho, Te)`，
于是把温度数组当网格、把真实网格当依赖量，得到的是自洽但**物理错误**的结果。
正确结论来自上面两段原文的交叉印证：

```
F1 的轴         =  (rho, de)
F1 的依赖字段   =  P, T   （外加可选的 e0）
```

这一点在统一网格插值时会直接决定成败（见 [13](13_统一网格与插值.md) §5）。

---

## 2. 布局（两种变体）

### 2.1 `with_e0`（含冷能量数组）

```
行 0:  [MID]      [rho0]    [nr]      [ne]
行 1:  [rho_0]    [rho_1]   [rho_2]   [rho_3]      ┐
  …                                               │ nr 个：rho 网格
行 ceil(nr/4)-1:  …                               ┘
行 n:  [de_0]     [de_1]    [de_2]    [de_3]      ┐
  …                                               │ ne 个：de 网格
                …                                 ┘
行 m:  [e0_0]     [e0_1]    [e0_2]    [e0_3]      ┐
  …                                               │ nr 个：冷能量
                …                                 ┘
行 p:  [P_0]      [P_1]     [P_2]     [P_3]      ┐
  …                                               │ ne*nr 个：压力
                …                                 ┘
行 q:  [T_0]      [T_1]     [T_2]     [T_3]      ┐
  …                                               │ ne*nr 个：温度
                …                                 ┘
```

### 2.2 `no_e0`（无冷能量数组）

与上面相同，但**跳过 `e0` 段**。

### 2.3 计数公式

```
with_e0 :  N = 4 + nr + ne + nr + 2*nr*ne  =  4 + 2*nr + ne + 2*nr*ne
no_e0   :  N = 4 + nr + ne + 2*nr*ne
```

★ 这正是上游文档里写的原式（去掉空格后）：
`4+2*nr+ne+2*nr*ne` —— 见 `docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt`。

### 2.4 布局自动判别

```python
def _detect_layout(n_numbers, nr, ne) -> str | None:
    if n_numbers == 4 + 2*nr + ne + 2*nr*ne:  return "with_e0"
    if n_numbers == 4 + nr + ne + 2*nr*ne:    return "no_e0"
    return None
```

判别**由计数决定**，不做启发式猜测。两个公式在 `nr, ne >= 2` 时
不会相等（差 `nr`，而 `nr >= 2`），所以判别唯一。

---

## 3. 实测样本（`mat_Al-1.0/AL_eos`）

### 3.1 原始文本（`header_raw` 逐字）

```
L0 (len=60): '     37181000    .27000000E+01  .66000000E+02  .74000000E+02'
L1 (len=60): '  .00000000E+00  .27000000E-05  .54000000E-05  .13500000E-04'
```

按 15 字符切片（**F1 的表头确实是干净的 4×15 定宽**）：

```python
L0 → ['     37181000  ', '  .27000000E+01', '  .66000000E+02', '  .74000000E+02']
     → [37181000,        2.7,             66.0,             74.0]

L1 → ['  .00000000E+00', '  .27000000E-05', '  .54000000E-05', '  .13500000E-04']
     → [0.0,             2.7e-06,          5.4e-06,          1.35e-05]
```

★ 注意首字段 `37181000` **不是**裸 MID，而是**完整的 SESAME EOS 表号**：
`3718`（Al 的材料号）+ `1`（EOS-total 类型位）+ `000`（表序号）。
所以不要用 `MID = int(field[0])` 去查材料 —— 那会得到 `37181000`。
正确做法见 [03 §4.1](03_注释证据通道.md)：`sesame_digit_of()` 取 `s[-4]`，
材料号取 `s[:-4]`。

### 3.2 解析结果（结构 + 单位）

```
status        ok
family        multi_inverted_eos
dispatch_rule declared:default->first:multi_inverted_eos
layout        F1/with_e0: 4 + 2*nr + ne + 2*nr*ne
count         actual=9978  expected=9978   ← 严格相等
nr=66  ne=74

axes        rho (66)            de (74)
fields      P (74,66)  E (74,66)  T (74,66)   e0_cold (66)   de_energy (74)
axis_units  rho: g/cm3          de: Mbar*cm3/g
field_units P: Mbar   E: Mbar*cm3/g   e0_cold: Mbar*cm3/g   T: eV
unit_source format:F1 (rho g/cm3, P Mbar, T Kelvin->eV)
notes       rho0=2.7 layout=with_e0 n_blank_in_payload=0
            自变量为 (rho, de)；T 为因变量场 —— 取 (rho,Te) 网格需反演
```

**计数验算**：`4 + 2·66 + 74 + 2·66·74 = 4 + 132 + 74 + 9768 = 9978` ✅

### 3.3 三个实测数据特征（不是格式问题，是上游数据本身）

| 现象 | 实测值 | 影响 |
|---|---|---|
| **`rho[0] == 0.0`** | `rho[:6] = [0.0, 2.7e-06, 5.4e-06, 1.35e-05, 2.7e-05, 5.4e-05]` | `log10(0) = -inf` → 统一网格插值必须先把 `rho<=0` 剔除；`interpolate.log10_or_nan()` 就是为此存在 |
| **`rho` 网格是 log 等距 + 首位 0** | 66 点 = `0` + 65 个从 `2.7e-6` 到 `27.0` 的 log 等距点 | `make_log_uniform(lo, hi, n)` 不能用首点当 `lo` |
| **`P` 有真实负值** | `P range = [-0.047517216, 1355246.1] Mbar` | 上游文档也承认："从计算的结果来看，压强、能量甚至Z等有负值，原因正在查找"。负压**照原样保留**（native 轨逐字），只在统一轨插值时按 log 空间处理会得到 NaN —— 如实记录，不静默修数据 |

### 3.4 零先验反演的独立确证

不看扩展名、不看路径、只有 4 个表头整数时：

```
=== 通用布局反演报告 ===
状态: ok
行剖面: lines=2495 blank=0 modal_len=60 header=0 payload=2494 header_end=0
列剖面: rows=2494 max_len=60 blank_cols=4 W_gap=15 W_len=15 -> W=15
表头数值: [37181000.0, 2.7, 66.0, 74.0]
维度候选: [(66, 74)]
自洽候选 (1):
  - f1_with_e0(d1=66,d2=74,ng=1) payload=9974 mono=True env=True score=2.00
      · 前导表头行数 k=1
  ! k=1: dims=[(66, 74)] values=9974
  ! k=2: dims=[(66, 74)] values=9970
  ! k=3: dims=[(66, 74)] values=9966
```

`payload=9974` 是**去掉表头 4 个数之后**的 payload 计数（`9978 - 4 = 9974`）；
解析器的 `n_numbers_actual=9978` 是**含表头**的总数。两者不矛盾，
只是口径不同 —— 报告里都写清楚，避免读者以为差 4 是 bug。

---

## 4. 五个必须注意的坑

### 4.1 表头可以切片，但**不能靠切片取语义**

F1 的表头确实是干净的 4×15（见 §3.1，实测 60 字符）。但：
- **字段 1 是 8 位 SESAME 表号**，不是 MID（见 §3.1 的 ★）
- 少数文件（如 `mat_Al-1.0/FEOS/*`）表头字段宽度会漂移

所以纪律是：**语义从 L2 数值正则取，定宽只用于 payload 分段**。

```python
header_nums = [float(x) for x in FORTRAN_NUM_RE.findall(line)]   # 语义
payload     = [line[i:i+15] for i in range(0, len(line), 15)]    # 分段
```

对比一下 `.301/.304/.305`（F4/MPQeos）的表头 —— 那里**切片真的会错**：

```
 37170301       2.70000000e+00 1.92000000e+02 6.90000000e+01
```

小写 `e`、标识字段宽 16 但数值字段宽 15、且 `2.70000000e+00` 只有 14 字符 ——
按 16 切片会得到 `'2.70000000e+00 1'`。这就是"payload 定宽 + 表头走 L2 正则"
这条纪律的**根本原因**，细节见 [07](07_格式规格_F4_FEOS与MPQeos.md) §5。

### 4.2 多块拼接（`AU_eosd` 的 `CountMismatch`）

`mat_Au-1.0/AU_eosd` 一个文件里**串了 2 块**，每块有自己的表头。
只按单块计数会得到 `actual ≈ 2×expected - 4`，报 `count_mismatch`。

```python
def _find_block_starts(lines) -> list[int]:
    """找所有「表头行」：4 个整数、且第 3/4 个是 DIM_MIN..DIM_MAX 的维度。"""
```

修法：先扫块起点，逐块解析再合并，并**登记块数**到 `notes`。

### 4.3 打包负号

```
-0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01
```

这是 **4 个数**，不是 1 个。负数吃掉了前导空格，字段**紧贴无分隔符**。
`str.split()` 返回长度 1 的列表，`float()` 直接抛异常。

```python
# core/fortran_numbers.py
FORTRAN_NUM_RE = re.compile(
    r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][+-]?\d+)?")
```

**为什么 F1 特别容易踩**：`de` 网格是**几何网格**（实测 `n=74`，
相邻比值中位数 `1.0851`，范围 `1.0272 .. 3.7696`），跨度
`0 → 75799.9 Mbar·cm³/g`；配 `%15.7e` 的 13 字符宽度，
相邻字段在负号处必然紧贴。**实测 `de` 严格单调递增** ✅。

对照：F2 不透明度族的 `rho`/`T` 网格在 log 空间是**严格等距**的
（见 [05](05_格式规格_F2_MULTI不透明度.md) §4），那里的打包负号更密集。

### 4.4 `T` 段在文件里是 Kelvin，解析时归一化为 eV

```python
# parsers/multi_inverted_eos.py
table.fields["T"] = [t * config.EV_PER_K for t in T_K]
table.field_units["T"] = "eV"
table.unit_source = "format:F1 (rho g/cm3, P Mbar, T Kelvin->eV)"
```

★ **换算发生在解析层，口径写进 `unit_source`**。这样：
- `ParsedTable` 内部**只有一种温度口径**（eV），下游不会混淆
- 但"文件里本来是 Kelvin"这件事**没有被抹掉** —— `unit_source` 字符串
  就是可审计的痕迹，`h5` 的 `/tables/<key>` 属性里也带着它

任何新写的 F1 下游代码都不需要再管 Kelvin；任何审计都能看到这一步换算。

### 4.5 `T` 是**依赖字段**，不是轴

`AL_eos` 的 `T` 数组长度是 `ne*nr = 4884`，与 `P` 相同。
如果把它当轴（长度应是 `ne=74` 或 `nr=66`），形状检查会拒绝 ——
**但危险的是形状恰好撞上**（如 `ne == nr`），此时会静默错位。

所以 `ParsedTable` 里显式记录 `axis` 与 `field` 的区分，并且**显式记形状**：

```python
table.axes        = {"rho": [...], "de": [...]}            # 网格
table.fields      = {"P": [...], "T": [...], "e0_cold": [...]}  # 依赖量
table.field_shape = {"P": (ne, nr), "T": (ne, nr)}          # ★ 形状显式
```

`sweep` 阶段的断言就是"轴长度 ∈ {nr, ne}，字段长度 ∈ {nr, ne, nr·ne}"。

---

## 5. ★ 扩展名不只是 `.feos` 与（无后缀）：4 类被漏掉的 F1 文件

第一次全量 `identify` 跑出 **10 条 `conflict`** —— 反演说是 F1，声明说是别的族。
逐条查证后确认：**反演是对的，声明的路径/扩展名规则错了 4 处**。

### 5.1 `.sesame`（6 个文件）—— 上游文档里的同一个布局

```
SiO2/eos_21.sesame        L0 = ' 0.0000000E+000 1.0000000E+000 4.3000000E+001 1.7650000E+003'
SiO2/eos_22.sesame        L0 = ' 0.0000000E+000 1.0000000E+000 3.6000000E+001 1.7920000E+003'
SiO2/eos_23.sesame        L0 = ' 0.0000000E+000 1.0000000E+000 7.5000000E+001 2.6950000E+003'
SiO2/eos_24.sesame        L0 = ' 0.0000000E+000 1.0000000E+000 7.3000000E+001 2.4740000E+003'
Ta2O5/PowerLawTa2O5_EOS.SESAME  L0 = ' 0.1234567E+000 1.0000000E+000 3.0000000e+000 1.9000000e+001'
mat_Au/Au_2003POPHammerRosen_EOS.SESAME
                           L0 = ' 0.1234567E+000 1.0000000E+000 6.0000000e+000 3.1000000e+001'
```

`L0 = [MID/magic, rho0, nr, ne]` —— 与 §3.1 里 `AL_eos` 的
`[37181000, 2.7, 66, 74]` **逐个字段对应**。计数验算（**精确**）：

| 文件 | `(nr, ne)` | F1 计数公式 | 文件实际数值个数 |
|---|---|---|---|
| `eos_22.sesame` | (36, 1792) | `4+72+1792+129024 = 130892` | `32723 行 × 4 = 130892` ✅ |
| `eos_24.sesame` | (73, 2474) | `4+146+2474+361204 = 363828` | `90957 行 × 4 = 363828` ✅ |
| `eos_21.sesame` | (43, 1765) | `4+86+1765+151790 = 153645` | `38411 行 × 4 + 1 = 153645` ✅ |
| `PowerLawTa2O5_EOS.SESAME` | (3, 19) | `4+6+19+114 = 143` | 36 行（3/4 列混排）= 143 ✅ |

**结论**：`.sesame` 就是 F1。旧实现把**无解析器的** `sesame_dat` 放第一候选，
于是只能退化成 `generic_curve`（4 个泛型列，物理语义全丢）。

```python
# 修法
".sesame": (("multi_inverted_eos", "sesame_dat", "hyades_eos",
             "generic_curve"), None),
#            ↑ 真有解析器的放第一；sesame_dat 只作语义标记保留
```

### 5.2 `.INV` —— `INVerted`，**不是** FEOS 导出

```
mat_CPC/AU.INV   L0 = ' 1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02'
mat_CPC/BE.INV   L0 = ' 1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02'
```

→ `[SESAME id, 0.0, nr=123, ne=100]`；6238 行 × 4 = **24952**；
`F1/with_e0(123,100) = 24950`（+2 尾部填充）✅
其余布局都差得远（`MPQeos` 37127、`F2 gray` 12527、`no_e0` 24827）。

`INV` 就是 MULTI 术语里的 **Inverted**，而旧实现的名字 token 里有
`|\.INV$` 把它归给了 `feos_aux`（FEOS 参数文件）。

```python
# 修法
".inv": (("multi_inverted_eos", "feos_aux"), "EOS_TOTAL"),   # EXT_MAP
".inv" in EXT_SPECIFIC                                        # 语义唯一
# 并去掉名字 token 里的 |\.INV$
```

### 5.3 `Thermos/` 下的理想气体 EOS

```
Thermos/mat_Mo/Mo_Ideal_Gas   L0 = ' 0.1234567E+000          10.22 0.2000000E+001 0.2000000E+001'
Thermos/mat_U/U_IdealGas_EOS  L0 = ' 0.1234567E+000           19.1 0.2000000E+001 0.2000000E+001'
Thermos/mat_W/W_Ideal_Gas     L0 = ' 0.1234567E+000          19.25 0.2000000E+001 0.2000000E+001'
```

★ **决定性证据**：第 2 字段正好是对应材料的**固体密度**：

| 材料 | 文件中第 2 字段 | 手册固体密度 |
|---|---|---|
| Mo | **10.22** | 10.22 g/cm³ ✅ |
| U | **19.1** | 19.1 g/cm³ ✅ |
| W | **19.25** | 19.25 g/cm³ ✅ |

`nr = ne = 2`，计数 `18 == F1/with_e0(2,2)`，
且与上游文档里 `mat_Au-1.0/AU_IDEAL_GAS` 的 5 行布局**逐行同构**：

```
AU_IDEAL_GAS:  [2002, 0.0, 2, 2] / [0,1,0,1] / [0,0,0,0] / [0,0.2168,0,0] / [24654.354, 24654.354]
Mo_Ideal_Gas:  [0.1234567, 10.22, 2, 2] / [0,1,0,1] / [0,0,0,0] / [0,0.6667,0,0] / [18020.116, 18020.116]
```

`Thermos/` 目录里既有 Z̄ 表也有理想气体 EOS，所以路径规则要两个都给：

```python
dt.families = ["multi_opacity", "multi_inverted_eos", "generic_curve"]
#               ↑ 多数派                          ↑ 理想气体 EOS
```

### 5.4 扩展名尾部的下划线

```
Ta2O5/PowerLawTa2O5_EOS.SESAME_     ← 尾部多一个 `_`（Windows 复制冲突的常见产物）
```

`.sesame_` 不在 `EXT_MAP` 里 → 扩展名规则失配 → 名字 token `powerlaw`
抢到 `generic_curve`。但内容是 F1（计数 143 **精确**吻合 `4+2*3+19+2*3*19`）。

```python
def _ext_of(fname: str) -> str:
    """扩展名（小写），**剥掉尾部下划线与空白**。"""
    return os.path.splitext(fname)[1].lower().rstrip("_ \t")
```

### 5.5 修复效果

| 指标 | 修复前 | 修复后 |
|---|---|---|
| `conflict` 条数 | **10** | **0** |
| 这 10 个文件的解析状态 | `generic_curve` 降级 / F1 未识别 | 全部 `multi_inverted_eos` + `status=ok` |
| `multi_inverted_eos` 文件数 | 41 | **51** |

回归测试：`test_declared_types.py::test_the_four_dispatch_fixes_end_to_end`
逐个断言这 10 个文件的家族、状态与 `(nr, ne)`。

---

## 6. 在项目里的下游用途

### 5.1 统一网格插值（必须反演）

F1 的轴是 `(rho, de)`，统一网格的轴是 `(rho, Te)`。所以
`writer/h5_writer.py::_write_unified_from_de_table()` 先调用
`convert/invert_eos.py::to_Te_grid()`：

```python
res = to_Te_grid(table, list(g.Te), fields=("P", "E", "T"), log_value=("T",))
```

反演算法（对每个密度列独立做）：

```
给定 rho_j 与目标 T 序列 {T*_k}：
  1. 在该列上由 E(rho_j, T) 单调反解 T(E)        ← 单调递减，用插值
  2. k=0..K: E*_k = E(rho_j, T*_k)
  3. P*_k = P(rho_j, T*_k)
  4. 写 /unified/<gid>/{P,E,T} 并标 origin="inverted-from-(rho,de)"
```

反演出的数据带 `ds.attrs["origin"] = "inverted-from-(rho,de)"`，
使"这条曲线是算出来的、不是源头给的"可追溯。

### 5.2 跨格式转换（接口示例）

F1 → Hyades（F3）是本项目验证过的一个完整用例：

```bash
python -m eosop_pro.cli convert mat_Al-1.0/AL_eos \
    --to hyades_eos --out AL_from_F1.dat --invert
```

- `--invert` 表示"源表是 `(rho,de)` 基，先反演到 `(rho,Te)` 再写"
- 写出的 Hyades 表 `L = 2 + nr + nt + 2·nr·nt = 9910`
- 回读一致性通过（`test_h5_schema.py` 覆盖）

`AL_from_F1.dat` 与 `mat_Al-1.0/AL_eos` 出自同一份物理数据，
但格式与单位体系完全不同 —— 这正是"统一 `ParsedTable` 中间表示"的价值。

---

## 7. 测试覆盖

`test_multi_inverted_eos.py`（10 个测试）：

| 测试 | 断言 |
|---|---|
| 计数公式 | `4+2nr+ne+2nr·ne` vs `4+nr+ne+2nr·ne` |
| 布局自动判别 | `with_e0` / `no_e0` 唯一判定 |
| 多块检测 | `AU_eosd` 识别出 2 块，总计数 = 两块之和 |
| 字段形状 | `P`、`T` 形状为 `(ne, nr)`；`e0` 为 `(nr,)` |
| 轴 vs 字段 | `de` 在 `axes`，`T` 在 `fields` |
| 打包负号 | 紧贴负数字段被正确切分 |
| 单位 | `T` 标 Kelvin，`de`/`e0` 标 `Mbar*cm3/g` |
| 已知文件回归 | `AL_eos` → `nr=66, ne=74`，`n_numbers=9974` |
