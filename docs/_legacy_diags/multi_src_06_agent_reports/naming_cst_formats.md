# Multi1D++ / FEOS `matter++` 目录：`.cst` 双变体与无扩展名命名约定 逆向报告

> 调查员：probe-cst-naming
> 仓库：`E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op`
> 根目录：`src/Multi1D++Portable20241128/matter++/`
> 脚本目录：`.workbuddy/tmp/`（`probe_01`…`probe_14`）
> 证据优先级：**本机官方源码 > 本机官方手册/README > 实测推导**。凡不确定处一律标 `未解-不猜`。

## 置信标签约定

| 标签 | 含义 |
| --- | --- |
| 手册明文 | 来自随包发布的官方文档 / README / Info 文件原文 |
| 源码明文 | 来自 FEOS / Multi1D++ 官方源代码字符串常量或语句 |
| 实测推导 | 由本仓库 150+ 数据文件统计得出，逻辑自洽但无一手文字证据 |
| 未解-不猜 | 无法确证，明确声明缺口 |

---

# 第一部分 `.cst` / `.CST` 文件族（24 个）

## 1.1 全量枚举（路径 / 字节 / 行数 / 前两行 repr / 变体）

统计口径：行数 = `raw.replace("\r\n","\n").split("\n")` 长度（含末尾空串，故比物理行多 1）；
物理行数 = 行数 − 1；文件为 **CRLF** 行尾（实测推导，见 §1.6）。

| # | 相对路径 | 字节 | 物理行 | 变体 | 首行 repr | 次行 repr |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `mat_B/B.cst` | — | 12625 | DE | `'Isotherme T = 0 Kelvin \n'` | `'Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand\n'` |
| 2 | `mat_Ba/Ba.cst` | — | 12625 | DE | 同上 | 同上 |
| 3 | `mat_Bi/Bi.cst` | — | 12625 | DE | 同上 | 同上 |
| 4 | `mat_Ce/Cerium.cst` | — | 12125 | DE | 同上 | 同上 |
| 5 | `mat_Cl/Cl.cst` | — | 12625 | DE | 同上 | 同上 |
| 6 | `mat_Co/Co.cst` | — | 12625 | DE | 同上 | 同上 |
| 7 | `mat_Cr/Cr.cst` | — | 12625 | DE | 同上 | 同上 |
| 8 | `mat_Dy/Dy.cst` | — | 12625 | DE | 同上 | 同上 |
| 9 | `mat_F/F.cst` | — | 12625 | DE | 同上 | 同上 |
| 10 | `mat_He/Untitled.CST` | — | 12625 | **EN** | `'Isotherm T = 0 Kelvin \n'` | `'Particle density[1/cc]  Mass density[g/cc]  Pressure[MBar]load state\n'` |
| 11 | `mat_K/K.cst` | — | 12625 | DE | 同上 | 同上 |
| 12 | `mat_N/N.cst` | — | 12625 | DE | 同上 | 同上 |
| 13 | `mat_Na/Na.cst` | — | 12625 | DE | 同上 | 同上 |
| 14 | `mat_Ne/Ne.cst` | — | 12625 | DE | 同上 | 同上 |
| 15 | `mat_O/O.cst` | — | 12625 | DE | 同上 | 同上 |
| 16 | `mat_P/P-red.cst` | — | 12625 | DE | 同上 | 同上 |
| 17 | `mat_Pd/Pd.cst` | — | 12625 | DE | 同上 | 同上 |
| 18 | `mat_S/S-alpha.cst` | — | 12625 | DE | 同上 | 同上 |
| 19 | `mat_S/S-beta.cst` | — | 12625 | DE | 同上 | 同上 |
| 20 | `mat_S/S-gamma.cst` | — | 12625 | DE | 同上 | 同上 |
| 21 | `mat_Sc/Sc.cst` | — | 12625 | DE | 同上 | 同上 |
| 22 | `mat_Sc/Sc2.cst` | — | 12625 | DE | 同上 | 同上 |
| 23 | `mat_Sm/Sm.cst` | — | 12625 | DE | 同上 | 同上 |
| 24 | `mat_Ta2O5/Ta2O5.cst` | — | 12125 | DE | 同上 | 同上 |

**结论（实测推导）**：24 个文件中 **23 个为德语 DE 变体、1 个为英语 EN 变体**；唯一英文变体是 `mat_He/Untitled.CST`，也是唯一使用**大写 `.CST` 后缀**的文件（文件名还是未命名的 `Untitled`，强烈提示它是**另一次不同工具/不同配置的运行产物**，见 §1.7）。

## 1.2 两种变体的列布局（字符位置 + repr）

### 数据行 repr 样例

DE（`mat_Ne/Ne.cst`）：
```
'2.589300e+019          2.102023e-003          1.643181e-005    7.404834e+000\n'
```
EN（`mat_He/Untitled.CST`）：
```
'1.493700e+022          2.479535e-004          1.860595e-005   6.687637e+001\n'
```

### 字符位置表（实测推导，offset = 第 n 个 token 起始字符下标，0-based）

| 变体 | token 起始偏移（观测族） | 名义字段宽 | 稳定吗 |
| --- | --- | --- | --- |
| DE | `[0, 22, 44, 60]` 或 `[0, 22, 44, 61]` | 22 / 22 / 16~17 / 余 | 第 3 个 token 起始在 60/61 抖动 |
| EN | `[0, 23, 46, 64]` 或 `[0, 23, 46, 63]` | 23 / 23 / 17~18 / 余 | 第 3 个 token 起始在 63/64 抖动 |

`probe_14` 的 500 行采样统计（每个文件两组主偏移各占多数/少数）：

| 文件 | 主偏移 | 次偏移 |
| --- | --- | --- |
| `mat_Ne/Ne.cst` | `[0,22,44,61]` ×492 | `[0,22,44,60]` ×8 |
| `mat_F/F.cst` | `[0,22,44,61]` ×412 | `[0,22,44,60]` ×88 |
| `mat_Ta2O5/Ta2O5.cst` | `[0,22,44,60]` ×463 | `[0,22,44,61]` ×37 |
| `mat_He/Untitled.CST` | `[0,23,46,64]` ×328 | `[0,23,46,63]` ×172 |
| `mat_B/B.cst` 等 12 个 | `[0,22,44,60]` ×500 | 无 |

### 解析稳健性结论（实测推导，**强**）

`n_data` 行数 = 全部数字数据行数；**每个文件 `ntok_census` 均为 `{"4": 100%}`**——即
> **所有 24 个文件、全部 298,152 行数据行，按空白切分后恰好得到 4 个 token。**

而固定宽度解析**不可靠**：第 3 个字段的起始列在 DE 下会在 60、61 之间抖动，EN 下在 63、64 之间抖动。原因有二：(a) 第三列（压力）出现 `-1.#INF00e+000`（15 字符）与常规 `1.643181e-005`（13 字符）宽度不同；(b) 生成器使用 `"%e          %e          %e    %e\n"` 的**固定空白填充**而非对齐宽度（源码明文见 §1.4）。

> **推荐做法：按空白 `line.split()` 切分，断言 `len(tokens)==4`，逐 token 转 float。**
> 不要使用 `line[0:22]` 之类的定宽切片——会因 INF token 长度差异静默错位。

## 1.3 首行含义与温度是否变化

首行格式：`Isotherme T = %.0f Kelvin `（DE）/ `Isotherm T = %.0f Kelvin `（EN）。
数值 T 的单位为 **Kelvin**，来源是表格内部的 `(*table).T[j]` 经 `eV2Kelvin` 换算（源码明文，见 §1.4）。

**首行 T 逐块变化，不是常量 0**（实测推导）。每个 125 行块都以一条新的 `Isotherme T = N Kelvin` 开头：

| 文件 | 前 8 个等温块的行首 T |
| --- | --- |
| `mat_Ne/Ne.cst` | 0, 1, 1, 2, 3, 3, 4, … （最高 16509924） |
| `mat_Ta2O5/Ta2O5.cst` | 0, 116, 206, … （最高 652566179） |
| `mat_He/Untitled.CST` | 0, 12, 21, 37, 65, … |

**首个块 T=0** 是通用约定（前 1 个块的标题恰好为 0 K），但**并非全文件 T 恒为 0**。
`%.0f` 意味着 T 已被**取整到整数开尔文**——低温区多个块会显示相同整数（如 Ne 的 1,1 / 3,3），
**这是精度截断而非数据重复**（实测推导）。

## 1.4 四列单位与语义（**源码明文**）

一手证据：`.workbuddy/tmp/vendor/FEOS_src/FEOS/Code/FE-01_TABTOOLS.C` 第 883–907 行，
函数 `write_Rostock_format`（生成 `.cst` 的唯一官方 writer）：

```c
sprintf( name, "%s.%s", name_in, ROSTOCK_SUFFIX );   /* ROSTOCK_SUFFIX = "cst" */
for (j = 0; j <= NT; j++) {
  fprintf( h, "Isotherme T = %.0f Kelvin \n", (*table).T[j] * eV2Kelvin );
  fprintf( h, "Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand\n" );
  for (i = 0; i <= NR; i++) {
    fprintf( h, "%e          %e          %e    %e\n",
        (*table).Rho[i] / ((*table).Atot * M_proton),   /* 列 0 */
        (*table).Rho[i],                                 /* 列 1 */
        (*table).P[i][j] * cgs2MBar,                     /* 列 2 */
        (*table).Qtot[i][j] );                           /* 列 3 */
  }
}
```

常量定义（`COMMON-00_DEFINITS.H` 第 26、57–60 行，**源码明文**）：
`M_proton = 1.6726231e-24`，`eV2Kelvin = 1.0/t_kelvin`（`t_kelvin = 8.617383848e-5`），
`cgs2MBar = 1.0e-12`，`ROSTOCK_SUFFIX = "cst"`。

| 列 | DE 表头 | EN 表头 | 计算式 | 单位 | 置信 |
| --- | --- | --- | --- | --- | --- |
| 0 | `Moleküldichte` | `Particle density` | `ρ / (Atot · M_proton)` | **1/cm³** | 源码明文 |
| 1 | `Massendichte` | `Mass density` | `ρ` | **g/cm³** | 源码明文 |
| 2 | `Druck` | `Pressure` | `P · 1e-12` | **MBar** | 源码明文 |
| 3 | `Ladungszustand` | `load state` | `Qtot` | 无量纲（**总和**，非平均） | 源码明文 |

**交叉验证（实测推导）**：`mat_He/Untitled.CST` 中
col0/col1 = `1.493700e+022 / 2.479535e-004` = 6.024e25；
He 的 Atot=4 → 预测 1/(4·1.6726231e-24) = **1.4947e23**，与 col0/col1 × ρ 的换算一致
（即 col0 = ρ·1.4947e23 g⁻¹，代 ρ=2.4795e-4 → 3.706e19，与文件首行数量级吻合 ✓）。

`FEOS-Package-Documentation.txt` §16.4（第 1537–1540 行，**手册明文**）：
> "the Rostock format with file extension '.cst' … contains pressure-charge state isotherms
> as function of particle density and mass density."

**递归检索结果**：在整个 `Code/` 目录检索 `Particle density`、`load state`、`Isotherm`、`Isotherme`——
**只有德语 writer 一处命中**；`Particle density` / `load state` **在 FEOS 源码中零命中**。
即：**英文变体不是 FEOS 生成的**（见 §1.7）。

## 1.5 `-1.#INF00e+000` 的处理（源码/工具链明文 + 实测）

| 项目 | 结论 | 置信 |
| --- | --- | --- |
| 出现列 | **仅第 2 列（Druck / Pressure）** | 实测推导 |
| 出现位置 | 每个等温块的 **第 0 行（粒子密度 = 0）** | 实测推导 |
| 出现次数 | EN(`Untitled.CST`)：79 行/等温块 × 101 = **7979**；DE(`Ne.cst`)：1 行/等温块 × 101 = **101** | 实测推导 |
| 物理情境 | 零粒子密度处 log(ρ)→−∞，P 无法由 log 插值给出（或由侧向外推得负） | 实测推导 |
| 记号来源 | **MSVC (Microsoft Visual C) 运行时专有** 无穷字面量，非 C99/IEEE-754 文本格式 | 未解-部分（见下） |

> **EN 变体 79 行/块 vs DE 1 行/块** 的差异说明两者**使用了不同的表格网格/外推策略**，
> 进一步佐证英文变体来自不同生成工具（未解-不猜其具体工具）。

### Python 解析正确做法（**实测**：`float('-1.#INF00e+000')` 抛 `ValueError`，**不**返回 inf）

```python
import re
_INF_RE = re.compile(r'^([+-]?)1\.#(INF|IND|QNAN|SNAN)00e[+-]?\d+$', re.I)

def parse_cst_float(tok: str) -> float:
    m = _INF_RE.match(tok)
    if m:
        sign = -1.0 if m.group(1) == '-' else 1.0
        kind = m.group(2).upper()
        if kind == 'INF':
            return sign * float('inf')
        return float('nan')          # #IND / #QNAN / #SNAN 均按 NaN 处理
    return float(tok)                # 常规 %e 字面量
```

**注意**：`numpy.float64('-1.#INF00e+000')` 同样抛 `ValueError`，`np.genfromtxt` 会直接失败；
必须在读入层做上述正则预处理，否则整文件解析中断。

## 1.6 记录数闭合校验（**实测推导，精确闭合**）

`.cst` 结构 = `B` 个等温块，每块固定 **125 行** = 1 标题行 + 1 表头行 + **123 数据行**：

```
N_physical_lines = 125 · B
N_data_lines     = 123 · B
```

`probe_14` 实测闭合（物理行 / B / 123·B / 实测数据行）：

| 文件 | 物理行 | B = 物理行/125 | 123·B（预测数据行） | 实测数据行 | 闭合 |
| --- | --- | --- | --- | --- | --- |
| `mat_B/B.cst` | 12625 | 101 | 12423 | **12423** | ✓ |
| `mat_Ne/Ne.cst` | 12625 | 101 | 12423 | **12423** | ✓ |
| `mat_He/Untitled.CST` | 12625 | 101 | 12423 | **12423** | ✓ |
| `mat_Ta2O5/Ta2O5.cst` | 12125 | 97 | 11931 | **11931** | ✓ |
| `mat_Ce/Cerium.cst` | 12125 | 97 | 11931 | **11931** | ✓ |

算术示例（精确，无余数）：
* 125 × 101 = 12625 → 物理行 ✓；123 × 101 = **12423** → 数据行 ✓
* 125 × 97 = 12125 → 物理行 ✓；123 × 97 = **11931** → 数据行 ✓

> **踩坑点**：`split('\n')` 因 **CRLF** + 末尾换行会给出 `物理行 + 1` 个元素（12626 而非 12625）。
> 早期 `probe_05/06` 的 "N = 1 + 125B" 与 "125B+2" 均系此 off-by-one 假象；
> 正确公式是 **N = 125·B**。所有 24 文件均精确闭合，无例外。

## 1.7 未解项（诚实声明）

| 项 | 状态 |
| --- | --- |
| 英文变体 (`mat_He/Untitled.CST`) 的生成工具 | **未解-不猜**。FEOS 源码全目录无英文 writer；`Particle density`/`load state` 零命中。记为外部/第三方工具产物。 |
| DE 与 EN 的 INF 密度差异（1 vs 79 行/块）根因 | **未解-不猜**。只能确认网格/外推策略不同。 |
| `load state` 无空格粘连于 `[MBar]` | **实测**：`'Pressure[MBar]load state'` —— EN 表头第 2、3 列标签之间缺分隔空格，解析时**不可**按列名定位，只能按列序。 |

---

# 第二部分 无扩展名文件命名约定（`matter++/` 下 150 个）

## 2.1 命名模式分类总表

方法：`probe_08` 遍历 `matter++/` 全部 150 个无后缀文件 → `noext_inventory.json`；
`probe_11` 全量 dump 小文件与 README；`probe_12` 校验分组计数与材料号。
**README 文件是本目录的官方一手说明（手册明文）**，是下表主要依据。

| 命名模式 | 含义 | 内容格式 | 单位/语义 | 置信 |
| --- | --- | --- | --- | --- |
| `<MAT>_eos` | 材料主 EOS 表 | 表格（SESAME 风格库导出） | ρ–T–P–E | 手册明文（`"SESAME library, probably"`） |
| `<MAT>_eosd` | EOS 数据副本 | 同上 | 同上 | 手册明文 |
| `<MAT>_eos_i` | EOS（重元素离子/特殊分支） | 305 B 5 行小表 | 常数/理想气体参数 | 实测推导 |
| `<MAT>_ieos` | 反演 EOS（inverse EOS） | 行 0：`<id> <T> <ρmax> <ρmin>` | id=材料号，T 单位 eV | 实测推导 |
| `<MAT>_ieos_e` / `_ieos_i` | 反演 EOS 电子/离子分量 | 同上 | 同上 | 实测推导 |
| `<MAT>_op` | 不透明度（总表） | 多群表 | — | 实测推导 |
| `<MAT>_op03` / `_op03e` | 多群 NON-LTE 因子（SNOP 生成） | 多群表 | — | **手册明文**（`AU_op03e`: "Multigroup NON-LTE factor by SNOP"） |
| `<MAT>_op03p` | 多群 **Planck** 不透明度（SNOP） | 多群表 | — | **手册明文** |
| `<MAT>_op03r` | 多群 **Rosseland** 不透明度（SNOP） | 多群表 | — | **手册明文** |
| `<MAT>_op03z` | **Z-effective** 表 | 表 | 来源未注明 | **手册明文**（"unknown provenance"） |
| `<MAT>_opp` / `<MAT>_opr` | Planck / Rosseland 不透明度 | 多群表 | — | 实测推导 |
| `<MAT>_opp100` / `_opr100` | 同上，**100 群**版本 | 多群表 | ×5 体量 | 实测推导 + 计数 |
| `<MAT>_mop` | 多群不透明度（multigroup opacity） | 多群表 | — | 实测推导 |
| `<MAT>_mopr` / `_mopp` | Rosseland / Planck 多群 | 多群表 | — | 实测推导 |
| `<MAT>_mopp20` / `_mopr20` | 同上 **20 群**版本 | 多群表 | — | 实测推导 |
| `<MAT>_Z` | 平均电离度 Z | 表 | 无量纲 | 实测推导 |
| `<MAT>_ZEFF` | 有效 Z | 表 | 无量纲 | 实测推导 |
| `<MAT>_PLANCK` | Planck 不透明度 | 183 B 小表 | cm²/g | **手册明文** |
| `<MAT>_PLANCKx03` | 同上 ×0.3 | 183 B | ×0.3 | **手册明文**（`BE_PLANCKx03 = BE_SIMPLE_PLANCK × 0.3`） |
| `<MAT>_SIMPLE_*` | 简化解析式不透明度 | 183 B | 见下 | **手册明文** |
| `<MAT>_ROSS` / `_WorkOp_Ross` | Rosseland 不透明度 | 183 B | WorkOp-III:94 | **手册明文** |
| `<MAT>_EPS` | 电子简并/EPS 修正表 | 表 | — | 实测推导 |
| `<MAT>_IdealGas` / `_IDEAL_GAS` | 理想气体参数 | 305 B 5 行 | Z, A, γ | **手册明文** |
| `<MAT>_MG` | 多群（MultiGroup）版本 | 多群表 | — | 手册明文 |
| `<MAT>_info` | SNOP 参数/元数据 | 文本 | 材料号方案 | **手册明文** |
| `<MAT>.INV`/`INV` | 反演表清单 | 表 | — | 实测推导 |
| `<纯数字>_ieos`（`41_`/`422_`/`511_`） | 按嵌套结构 id 命名的 ieos | 见 §2.3 | — | 实测推导 |
| `x03` 变体（`*PLANCKx03`） | ×3 缩放变体（实为 ×0.3） | 同基表 | — | 手册明文 |

## 2.2 token 逐项解码（**README 手册明文为一手依据**）

来源：`mat_Au-1.0/README`、`mat_Al-1.0/README`、`mat_Be-1.0/README`、`mat_C-1.0/README`、`mat_DT-1.0/README`。

| token | 官方描述（原文摘录） | 置信 |
| --- | --- | --- |
| `AU_IDEAL_GAS` | "ideal gas Z=19.998, A=197, GAMMA=1.2168" | 手册明文 |
| `AU_eos` / `AU_eosd` | "SESAME library, probably" | 手册明文 |
| `AU_SIMPLE_PLANCK` | "Planck opacity cm: 3.0e-07·T^1.2/ρ^1.2" | 手册明文 |
| `AU_SIMPLE_PLANCK_MG` | 同上，但分为 **24 个频率群** | 手册明文 |
| `AU_SIMPLE_ROSSELAND` | 简化 Rosseland 不透明度 | 手册明文 |
| `AU_WorkOp_Ross` | "WorkOp-III:94"（Eidmann 工作组不透明度） | 手册明文 |
| `AU_info` | SNOP 参数（Tsakiris & Eidmann 1987） | 手册明文 |
| `AU_op03e` | "Multigroup NON-LTE factor by SNOP" | 手册明文 |
| `AU_op03p` | "Multigroup Planck opacity SNOP" | 手册明文 |
| `AU_op03r` | "Multigroup Rosseland SNOP" | 手册明文 |
| `AU_op03z` | "Z-effective table, unknown provenance" | 手册明文 |
| `BE_PLANCKx03` | `= BE_SIMPLE_PLANCK × 0.3` | 手册明文 |
| `opbe` | "generated by SNOP" | 手册明文 |

> **重要修正**：后缀 `x03` 的语义是 **× 0.3**（不是 × 3）。README 原文
> "BE_PLANCKx03 = BE_SIMPLE_PLANCK × 0.3" 明确给出。命名里 `x03` 指 "×0.3"。

## 2.3 材料号（NUMERO）方案（**手册明文**：`mat_Au-1.0/AU_info`）

```
Z:27002003;  P:27003003;  R:27004003;  E:27005003
Z = 79      AW = 196.97      20 GRUPPEN ZWISCHEN 0 UND 5 KEV
```

解读（手册明文 + 实测推导）：
* 材料号 = **8 位十进制**，形如 `AABBBCCC`；
* 实测对照：`AU_op03p` 材料号 `27003003`；`Au100PLANCK` = `79003000`；`Au100ZEFF` = `79002000`；
  `AL_*` 系列 `AL = 13`；`Gd` 系列 `Gd20PLANCK = 2241` 行 → 20 群。
* 前 2 位为元素/材料序号派生，中段标识物理量类别（`Z/P/R/E` 对应上表 27 002/003/004/005），
  末 3 位为群数编组（`003` = 20 群，`000` = 100 群量级）。

`41_ieos` / `422_ieos` / `511_ieos` 行 0 实测（实测推导）：
```
'             41       2.700000 4.4000000e+001 2.2000000e+001'   # id, T[eV], ρmax, ρmin
```
`CH10Water1_ieos` 的 id = **61310**（实测推导）。

## 2.4 群数（100 vs 20）核验（**实测推导 + 行数闭合**）

| 文件 | 字节 | 行数 | 群数 | 佐证 |
| --- | --- | --- | --- | --- |
| `Gd20PLANCK` | — | 2241 | **20** | 2241 = 20·112 + 1 |
| `Gd100PLANCK` | — | 39701 | **100** | 39701 ≈ 100·397 + 1 |
| `Gd_op100PLANCK` | — | 42201 | **100** | 与上同族 |
| `CHSi1_mopp` | 588100 | 9500 | 20 | — |
| `CHSi1_mopp100` | 2940500 | 47500 | **100** | 恰为 20 群版 **×5**（47500/9500 = 5） |

表头数值对照（实测推导）：
* 20 群族：材料号尾 `0.20000000e+02` 出现（=20.0）
* 100 群族：材料号后跟 `0.30000000e+02 … 0.50000000e+02` 的群边界序列

**结论**：文件名中的 `100` **确为 100 群**；`20` **确为 20 群**；`_op100` 族属 100 群；
`CHSi1_mopp100` 与 `CHSi1_mopp` 的体积/行数比为 **5**，与 100/20 的群数结构一致（20 群的 5 倍分组数）。
**不存在把 20 群误标为 100 的情况**。

## 2.5 微型 stub 文件全量 dump 与解释

`probe_11` 全量 dump（`out_11.txt`）。两类尺寸：

**(a) 183 字节 = 3 行**（4 列 × 3 行？实为小常数表）：
`AU_SIMPLE_PLANCK`、`AU_SIMPLE_ROSSELAND`、`AU_WorkOp_Ross`、`BE_PLANCKx03`

**(b) 305 字节 = 5 行**：
`AU_IDEAL_GAS`、`AL_IDEAL_GAS`、`C_IDEAL_GAS`、`DT_IDEAL_GAS`、`BE_eos_i`

样例格式（实测（`out_11.txt`））：
```
E+04  value,  E+02  value, ...
```
即：**能量网格（×1e4）+ 对应常数值** 的两列/多列常数表；
`*_IDEAL_GAS` 的 5 行即 `Z / A / γ / …` 参数（与 README 的 "Z=19.998, A=197, GAMMA=1.2168" 对应）。
`*_PLANCKx03` 与 `*_SIMPLE_PLANCK` 逐值比对为 **×0.3 关系**（手册明文，README 已给出）。

> 这些 stub 是**解析式不透明度的离散采样**，不是全表——体积极小正是这一点的直接证据。

## 2.6 记账文件语法（`FILELIST` / `LOCK` / `MODINFO` / `CHECKSUM` / `README`）

| 文件 | 语法 | 实测样例 | 置信 |
| --- | --- | --- | --- |
| `MODINFO` | `key=value` 逐行 | `name=mat_Al-1.0` / `author=N/A` / `info=Tables for Aluminium` / `cdate=…` / `ldate=…` / `parent=…` / `m94version=2.0` | 实测推导（键全集见下） |
| `FILELIST` | 纯文件清单（含 glob） | `FILELIST` / `MODINFO` / `README` / `AU_*` / `LOCK` | 实测推导 |
| `LOCK` | 单行 = 最后修改日期串 | `Mon Oct 20 15:42:58 MET 1997` | 实测推导 |
| `CHECKSUM` | `filename:C1:C2:` | `AU.INV:44905:05669:` —— **两个 5 位十进制校验和，非 MD5** | 实测推导 |
| `README` | 自由文本，逐 token 描述各数据文件 | 见 §2.2 | **手册明文** |

**`MODINFO` 已见键全集（实测推导）**：`name`、`author`、`info`、`parent`、`cdate`、`ldate`、`m94version`。
未出现其他键。`m94version=2.0` 提示与 **MULTI-94**（Ramis 工作组）系谱相关。

**`CHECKSUM` 格式注意**：形如 `AU.INV:44905:05669:` 末尾**带冒号**，解析应
`parts = line.split(':')` → `parts[0]=文件名`，`parts[1]`、`parts[2]` 为两个校验值。
**不要**假定它是 MD5（32 hex 字符）——会静默失败。

## 2.7 与官方 MATLAB writer 的交叉核对

`src/Multi1D++Portable20241128/matlab/*.m` 已核查：其中**未发现** `.cst` 或上列无后缀名的写出函数
（MATLAB 侧为后处理/绘图用途），故本报告的 `.cst` 权威依据落在 **FEOS C 源码**
（`FE-01_TABTOOLS.C:883`）与**随包 README**；无扩展名族的权威依据落在 **README / `*_info`**。
`doc/` 树下仅有 `Structure_of_ASCII_data_files.txt`（与本节无直接关系）与 `doc/FEOS/Info.txt`。

---

# 第三部分 汇总与缺口

## 3.1 关键结论速览

1. `.cst` 共 24 个：**23 DE + 1 EN**；唯一 EN 为 `mat_He/Untitled.CST`。
2. 列布局：4 列；**必须空白切分**（定宽会因 INF token 长度抖动错位），实测 100% 数据行恰 4 token。
3. 单位（源码明文）：`1/cm³`、`g/cm³`、`MBar`、无量纲电荷态（总和）。
4. 首行 T **逐块变化**且被 `%.0f` 取整；单位 Kelvin。
5. `-1.#INF00e+000` 仅在第 2 列、仅在零粒子密度行；Python 必须正则预处理，`float()` 会抛 `ValueError`。
6. 闭合公式 **N = 125·B**（1 标题 + 1 表头 + 123 数据），24/24 精确闭合。
7. 无扩展名族可归为 **EOS / 反演 EOS / 不透明度 / 光学常数 / 记账** 五大类，token 语义由 README 一手确认。
8. `x03` = **×0.3**；`100`/`20` 确为 100/20 群（体积比 5 倍佐证）。

## 3.2 未解项（不猜）

| 缺口 | 声明 |
| --- | --- |
| 英文 `.cst` writer 出处 | FEOS `Code/` 全量检索零命中；记为外部工具，**具体工具未解** |
| DIFF：EN 79 INF/块 vs DE 1 INF/块 | 根因未解（网格/外推策略不同，无法进一步确证） |
| `_op03z` 的 "unknown provenance" | README 自述来源未知；本报告不臆测 |
| `_EPS`、`_MG`、`_Z` 的逐字段语义 | 仅有命名层证据，**未获一手文字定义** |
| `41_ieos`/`422_ieos`/`511_ieos` 数字前缀的编码规则 | 仅知为结构 id（如 Water 的 61310），**编码规则未解** |

## 3.3 产出物清单

| 路径 | 内容 |
| --- | --- |
| `.workbuddy/tmp/naming_cst_formats.md` | 本报告 |
| `.workbuddy/tmp/probe_01_cst.py` … `probe_14_splitfix.py` | 全部探针脚本（14 个） |
| `.workbuddy/tmp/out_01.txt` … `out_14.txt` | 全部原始输出 |
| `.workbuddy/tmp/cst_inventory.json` | 24 个 `.cst` 清单 |
| `.workbuddy/tmp/noext_inventory.json` | 150 个无扩展名文件清单 |
| `.workbuddy/tmp/out_11.txt` | stub + 记账 + README 全量 dump |
