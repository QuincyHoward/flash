# cn4_io.py —— IONMIX `.cn4` 读写内核（F6）

> **适用仿真软件**：IONMIX（CONRAD 格式数据表，被 MULTI/matter++ 等读取）| **官方链接**：无已核实官方 URL（uv），本地权威：`ionmix/ionmix/src/Ionmix/abjt_03.f`（SUBROUTINE OWTF）+ `ionmix/ionmix/docs/IONMIX用户指南.md` §5.4
> **概要**：`.cn4`（EOS + 不透明度合一的定宽文本表）完整读写内核，解析产出 `CN4Table`（可适配为 `ParsedTable`）| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步（uk=无来源确认/uv=未人工核查）；格式权威版本 = [20 手册 §7](../../docs/20_格式规格与物理量单位手册.md)。本族是字典中**唯一 checked 族**（标记省略）。内核层文档，适配层入口见 [ionmix.md](ionmix.md)；只读兄弟格式见 [cnr_io.md](cnr_io.md)。

## 1. 格式布局与计数公式

引 [20 手册 §7.1/§7.2/§7.7](../../docs/20_格式规格与物理量单位手册.md)：一手依据为 `abjt_03.f` `SUBROUTINE OWTF`（isw(21)!=0 分支，line 4662–4743，写 unit 123）。

**4 行头部**（`abjt_03.f:4749–4755` 格式语句）：

```
line 1 : ntemp, ndens            (2i10，格式 923)
line 2 : izgas(...)              (a80 + 5i10，" atomic #s of gases: "，格式 921)
line 3 : fracsp(...)             (a80 + 1p5e10.2，" relative fractions: "，格式 922)
line 4 : ngrups                  (i12 独占一行，格式 982) ← 与 .cnr 的根本区别
```

**18 个数据块**（`991 format (4e12.6)` 定宽，无分隔符）：`tplsma(ntemp)`、`densnn(ndens)`、12 个二维 EOS 场（block 3–14）、`engrup(ngrups+1)`、3 个三维群不透明度（block 16–18）。

**计数守恒公式**（不符抛 `CN4ParseError`，不静默）：

```
N = ntemp + ndens + 12*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens
```

实测锚点：`Z06_0.50-Z01_0.50-20260708_0850.cn4`（51×31×6 群）→ 47519/47519 精确闭合。

**循环嵌套**（源码逐条核对）：2D 场温度内循环/密度外循环 → `reshape(ndens, ntemp)`；3D 场群外循环 → `reshape(ngrups, ndens, ntemp)`。用户指南 §5.4 的措辞与源码**等价**（外循环 vs reshape 轴序），以源码为准。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`eos_op_data/Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/Z06_0.50-Z01_0.50-20260708_0850.cn4`（IONMIX 产物，C/H 各 50% 双组分，ntemp=51 × ndens=31 × ngrups=6，即 §1 计数公式闭合的实测锚点（47519/47519））

**原文摘录**（前 20 行，逐字保留原始空格，含行尾空格；摘录为数据文件原文，不混入任何注释）：

```
        51        31                                                            
 atomic #s of gases:          6         1                                       
 relative fractions:   5.00E-01  5.00E-01                                       
           6
0.100000E+010.121905E+010.148607E+010.181159E+01
0.220841E+010.269215E+010.328186E+010.400074E+01
0.487708E+010.594538E+010.724770E+010.883527E+01
0.107706E+020.131299E+020.160059E+020.195119E+02
0.237859E+020.289961E+020.353476E+020.430903E+02
0.525291E+020.640354E+020.780620E+020.951612E+02
0.116006E+030.141416E+030.172393E+030.210155E+03
0.256189E+030.312306E+030.380715E+030.464109E+03
0.565770E+030.689700E+030.840775E+030.102494E+04
0.124945E+040.152314E+040.185678E+040.226350E+04
0.275931E+040.336372E+040.410053E+040.499873E+04
0.609368E+040.742848E+040.905566E+040.110393E+05
0.134574E+050.164051E+050.199986E+05
0.100000E+170.204188E+170.416927E+170.851314E+17
0.173828E+180.354936E+180.724736E+180.147982E+19
0.302162E+190.616978E+190.125979E+200.257235E+20
```

**逐行说明**（格式 / 物理量与单位 / 顺序，单位与 §2 单位表一致）：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `        51        31` | 头部行 1（格式 923，2i10 右对齐定宽）：`ntemp=51`、`ndens=31`，即温度点数与密度点数——§1 计数公式的两个基数 |
| 2 | ` atomic #s of gases:          6         1` | 头部行 2（格式 921，a80 标签 + 5i10）：组分气体原子序数 `izgas = 6(C), 1(H)`，双组分 |
| 3 | ` relative fractions:   5.00E-01  5.00E-01` | 头部行 3（格式 922，a80 标签 + 1p5e10.2）：组分相对份额 `fracsp`，各 0.50，无量纲（和为 1） |
| 4 | `           6` | 头部行 4（格式 982，i12 独占一行）：`ngrups=6`（光子能群数）——这是 .cn4 与 .cnr 的根本区别（.cnr 此行是 4 网格参数 + ngrups 同行，见 [cnr_io.md §1.1](cnr_io.md)） |
| 5–17 | `0.100000E+01`…`0.199986E+05`（4e12.6 定宽无分隔，4 值/行，末行 3 值） | 数据块 1：温度轴 `tplsma(ntemp=51)`，单位 **eV**（§2）；51 个值按格式 991（4e12.6）排 13 行（12×4+3），自 0.1 eV 起对数递增；18 块中的第 1 块（§1 块顺序） |
| 18–20 | `0.100000E+17`…（4e12.6，4 值/行） | 数据块 2：核子数密度轴 `densnn(ndens=31)` 的前 12 个值，单位 **cm^-3**——是数密度而非质量密度（§2 特别警告）；自 1.0E+17 cm^-3 起对数递增；其后依次为 12 个二维 EOS 场（温度内循环/密度外循环）与群不透明度块（§1） |

## 2. 物理量与单位

摘录字典 ionmix 族条目（完整来源详述见[字典](../../docs/eosop变量控制字典.md)；本族全部 checked，标记省略；单位判定等级见 §5）：

| 字段 | 物理意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `T` (tplsma) | 温度轴 | eV | source code | （省略） |
| `nion` (densnn) | **核子数密度**轴（非质量密度） | cm^-3 | source code | （省略） |
| `zbar` | 平均电荷态 ne/nion | - | source code | （省略） |
| `dzdt` | d(zbar)/dT | 1/eV | source code | （省略） |
| `p_ion` | 离子压力 | J/cm3 | source code | （省略） |
| `p_ele` | 电子压力 | J/cm3 | source code | （省略） |
| `dpion_dt` | d(p_ion)/dT | J/cm3/eV | source code | （省略） |
| `dpele_dt` | d(p_ele)/dT | J/cm3/eV | source code | （省略） |
| `e_ion` / `e_ele` | 离子/电子比内能 | J/g | source code | （省略） |
| `cv_ion` / `cv_ele` | 离子/电子比热 | J/g/eV | source code | （省略） |
| `deion_dn` | d(e_ion)/d(n_ion)，源码自注 not sure，单位暂按手册 :928 | J*cm3/g（暂定） | source code | （省略，不确定性已登记） |
| `deele_dn` | d(e_ele)/d(n_ele)，同上 | J*cm3/g（暂定） | source code | （省略，不确定性已登记） |
| `engrup` | 光子能群边界 | eV | source code | （省略） |
| `opac_rosseland` / `opac_planck_abs` / `opac_planck_ems` | Rosseland / Planck 吸收 / Planck 发射群不透明度 | cm2/g | source code | （省略） |

`p_ion/p_ele` 的 `J/cm3` 为 L4 推导（`densnn*tplsma*1.602E-19`，见 [20 手册 §7.3](../../docs/20_格式规格与物理量单位手册.md)），非猜测。

## 3. 解析器 API 与用法

关键 API（签名经源码核实）：

- `parse_cn4(filepath, *, atomwt=None) -> CN4Table`（别名 `load_cn4`；`CN4Data = CN4Table`）
- `write_cn4(table, out_path, *, write_opacities=True, mantissa_style=None, verbatim=False) -> Path`
- `convert_cn4_to_cn4(src, dst, **opts) -> Path` —— 默认 verbatim 直通的往返
- `cn4_to_parsed_tables(table, relpath="") -> list` —— 拆 4 张 `ParsedTable`（EOS_TOTAL + ROSSELAND/PLANCK/EMISSIVITY）
- `parsed_tables_to_cn4(tables, *, izgas, fracsp, atomwt=None, allow_foreign=False) -> CN4Table`（跨族组装唯一入口）
- `convert_foreign_to_cn4(src, dst, *, izgas, fracsp, atomwt=None, **opts) -> Path`
- `parse_header(lines) -> dict`、`expected_number_count(ntemp, ndens, ngrups) -> int`、`load_cn4_dir(dirpath) -> list`
- 异常：`CN4ParseError(ValueError)`
- CLI：`python -m eosop_pro.parsers.cn4_io <file.cn4> [out.cn4]`

```python
from eosop_pro.parsers.cn4_io import load_cn4, write_cn4

tbl = load_cn4(r"E:/data/Ionmix/he-imx-005.cn4")
print(tbl.summary())            # 组分/维度/网格范围
p = write_cn4(tbl, "out.cn4")   # 逐值重排写出（verbatim=True 则数据区直通）
```

## 4. 陷阱与 unknown 清单

复述 [20 手册 §11](../../docs/20_格式规格与物理量单位手册.md) 本族条目（#1、#2）：

1. **`deion_dn`（block 13）**：源码 `abjt_03.f:4715` 自注 `(not sure)`，量纲无法从源码独立确认 → unknown。
2. **`deele_dn`（block 14）**：同上（`abjt_03.f:4720`）。
   - ⚠️ 20 手册称不确定性登记于 `cn4/units.py` —— **手册过时**，`UNCERTAIN_UNITS` 现位于 `eosop_pro/plotting/style/units.py:221`。

其余陷阱：

- **IONMIX6 电子比熵块不存在（2026-11-14 源码+数据双实证）**：FLASH 手册的 IONMIX6 格式含 block 20「Electron specific entropy [J/g/eV]」（仅 IONMIX6），本仓库 `abjt_03.f` **未实现该块**——L4726 仅一行注释 `c ...    write out electron specific entropy`，L4727 的 write 本身也被注释且写的是全零占位 `(0.0, it=1, ntemp), id=1, ndens`，全源码无任何熵计算语句；OWTF 写出序列从 `d(eele)/d(nele)`（L4720-4725）直接跳到群边界（L4729）。数据侧实证：仓库内全部 20 个 .cn4（eos_op_data 登记表 + Ionmix 样例 + 新生成 `_6g` 文件）数字总数**严格等于 18 块公式** `ntemp + ndens + 12·ntemp·ndens + (ngrups+1) + 3·ngrups·ntemp·ndens`，无一匹配含熵块布局（+ntemp×ndens）。因此本包解析链 `N_BLOCKS = 18` 即完整格式，无第 20 块；若未来需要该量需另行补算（源码无现成数据）。
- **mantissa 双风格**：实测 `"leading0"`（Ionmix 产物 `0.100000E+00`）与 `"dotted"`（BADGER-TOPS `1.000000E-01`）并存；`parse_cn4` 嗅探后记入 notes，`write_cn4(mantissa_style=...)` 按源风格复刻保证 byte-identical。负值实测 13 列（`-.370029E-04`），写出侧不得缩位。
- **`e12.6` 三位指数丢 E 缺陷**：指数 3 位时（`0.638380-140`）Fortran 静默丢 `E`，读取侧 `_PACKED_EXP_RE` 自动还原（实测 h-imx-1grp.cn4 含 89 个此类 token，修复后计数不变）。
- **NaN 占位**：`NAN_PLACEHOLDER_FIELD = "-9.99999+990"`（12 列对齐，解码为 -inf）；`NAN_PLACEHOLDER_CUTOFF = -1.0e98`，`is_nan_placeholder()` 判定；缺失场写占位而非 0。
- **data_raw 逐字保留**：`parse_cn4` 把数据区原文存入 `CN4Table.data_raw`；`write_cn4(..., verbatim=True)`（`convert_cn4_to_cn4` 默认）逐字节直通。
- **原子量三级来源**：用户传入 → 同目录 `ionmxinp` → 内置 IUPAC 元素表；均不可得则 `rho` 不可用（`nion/zbar/p_*/e_*/opacity` 仍可用，不猜）。
- **轴语义**：密度自变量是 `nion`（cm^-3 数密度）；`rho`/`nele` 是派生场；`ParsedTable` 侧二维场已转置为 `(n_Te, n_x)`。
- **单位纪律（转换）**：`parsed_tables_to_cn4` 要求输入带 `field_units`，目标 18 块单位必须是 §2 表值（压力 `J/cm3` 而非 `Mbar`），不匹配拒绝或显式警告（[20 手册 §12](../../docs/20_格式规格与物理量单位手册.md)）。

## 5. 溯源

| 等级 | 含义 | 本族落点 |
|---|---|---|
| L1 format | 一手格式规格文档 | `IONMIX用户指南.md` §5.4（仅 .cn4） |
| L2 declared | 文件内/伴随声明 | 头部组分行（格式 921/922） |
| L3 default | 格式默认约定 | 无 |
| L4 inferred/derived | 推导 | `p_ion`/`p_ele` 的 J/cm3（`abjt_03.f:4693` 量纲链）；`dzdt` 的 1/eV |
| L5 unknown | 无来源确认 | `deion_dn`/`deele_dn`（源码自注 not sure） |

一手依据：`ionmix/ionmix/src/Ionmix/abjt_03.f`（SUBROUTINE OWTF，line 4510 起）；配套文字规格：`ionmix/ionmix/docs/IONMIX用户指南.md` §5.4。单位换算因子集中见 20 手册 §7.9（显示层 Mbar/erg/g 等）。
