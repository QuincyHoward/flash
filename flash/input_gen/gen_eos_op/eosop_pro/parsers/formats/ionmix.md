# ionmix.py —— IONMIX `.cn4`/`.cnr` 适配层入口（F6）

> **适用仿真软件**：IONMIX（CONRAD 格式数据表）| **官方链接**：无已核实官方 URL（uv），本地权威：`ionmix/ionmix/src/Ionmix/abjt_03.f` + `ionmix/ionmix/docs/IONMIX用户指南.md`
> **概要**：按扩展名把 `.cn4`/`.cnr` 分派到对应内核并适配为 `ParsedTable` | **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步（uk=无来源确认/uv=未人工核查）；格式权威版本 = [20 手册 §7](../../docs/20_格式规格与物理量单位手册.md)。**格式规格细节不在本页展开**：`.cn4` 读写内核见 [cn4_io.md](cn4_io.md)，`.cnr` 只读内核见 [cnr_io.md](cnr_io.md)。

## 1. 格式布局与计数公式（综述）

`.cn4` 与 `.cnr` 是 `abjt_03.f` `SUBROUTINE OWTF`（line 4510）的两个互斥输出分支：

| | `.cn4` | `.cnr` |
|---|---|---|
| 源码分支 | `isw(21) != 0` → unit 123 | `isw(8) = 1/12/13` → unit 8 |
| 块数 | **18**（含完整 EOS） | **7**（无 EOS 场） |
| 头部第 4 行 | `ngrups` 独占一行（982） | 4 网格参数 + `ngrups` 同行（981） |
| 程序化判据 | 第 4 行能否被 `int()` 解析 —— 能 = `.cn4`，不能 = `.cnr` | |

计数公式与逐块布局分别见 [cn4_io.md §1](cn4_io.md)（`ntemp + ndens + 12*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens`）与 [cnr_io.md §1](cnr_io.md)。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`eos_op_data/Gen_eos_op_data/Z06_0.50-Z01_0.50-20260708_0850/Z06_0.50-Z01_0.50-20260708_0850.cn4`（入口页短例：同 [cn4_io.md §1.1](cn4_io.md) 的 IONMIX 产物（C/H 各 50%，51×31×6 群），只摘 4 行头部 + 前 2 行数据区）

**原文摘录**（前 6 行，逐字保留原始空格，含行尾空格；摘录为数据文件原文，不混入任何注释）：

```
        51        31                                                            
 atomic #s of gases:          6         1                                       
 relative fractions:   5.00E-01  5.00E-01                                       
           6
0.100000E+010.121905E+010.148607E+010.181159E+01
0.220841E+010.269215E+010.328186E+010.400074E+01
```

**逐行说明**（格式 / 物理量与单位 / 顺序，单位与 §2 单位表一致）：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `        51        31` | 头部行 1（2i10 定宽）：`ntemp=51`、`ndens=31`（温度点数、密度点数）；完整块布局与计数公式见 [cn4_io.md §1](cn4_io.md) |
| 2 | ` atomic #s of gases:          6         1` | 头部行 2（a80 + 5i10）：组分原子序数 `izgas = 6(C), 1(H)` |
| 3 | ` relative fractions:   5.00E-01  5.00E-01` | 头部行 3（a80 + 1p5e10.2）：组分相对份额各 0.50，无量纲 |
| 4 | `           6` | 头部行 4（i12 独占一行）：`ngrups=6`——能被 `int()` 解析即判定为 .cn4（§1 程序化判据）；.cnr 的此行是 4 网格参数 + ngrups 同行 |
| 5–6 | `0.100000E+010.121905E+01…` | 数据区开头：温度轴 `tplsma` 前 8 个值（格式 991，4e12.6 定宽无分隔，4 值/行），单位 **eV**（§2）；注意密度轴是 cm^-3 数密度而非 g/cm3（§2 第一坑） |

## 2. 物理量与单位

字典 ionmix 族共 18 条目（`T`/`nion`/`zbar`/`dzdt`/`p_ion`/`p_ele`/`dpion_dt`/`dpele_dt`/`e_ion`/`e_ele`/`cv_ion`/`cv_ele`/`deion_dn`/`deele_dn`/`engrup`/`opac_rosseland`/`opac_planck_abs`/`opac_planck_ems`），全部 source code 来源且 **checked —— 唯一可省略 uk/uv 标记的族**。逐条单位表见 [cn4_io.md §2](cn4_io.md)，此处不重复。

三条最容易踩的坑（引 [20 手册 §10](../../docs/20_格式规格与物理量单位手册.md)）：

- **`densnn` 是数密度 `cm^-3`，不是质量密度**（[20 手册 §7.5](../../docs/20_格式规格与物理量单位手册.md)，`IONMIX用户指南.md` §5.1 权威）：其余族的密度轴都是 `g/cm3`，混用会得到量级完全错误的结果。转质量密度需 `rho = n_ion * <A> / N_A`。
- **P/E 是 SI 派生单位**：`J/cm3` / `J/g`，与 F1/F4 的 `Mbar` 系及 F3 的 CGS 都不同。
- **T 恒为 eV**：`unit_hint_T` 不接受非 eV 覆盖（见 §4）。

**原子量三级来源**（影响 `<A>` 与 `rho` 派生场）：用户传入 → 同目录 `ionmxinp`（`atomwt(i)` 行，权威）→ 内置 IUPAC 元素表（便利回退）；均不可得则 `rho` 不可用，不猜。

## 3. 解析器 API 与用法

关键 API（签名经源码核实）：

- `parse_all(path, relpath="", *, unit_hint_T=None, atomwt=None) -> list[ParsedTable]` —— **主入口**，按扩展名分派：
  - `.cn4` → `cn4_io` 全 18 块解码，产 **1 张** `kind=cn4_eos` 总表（EOS 与 3 块不透明度合一，保持 cn4 原子性；表键 `IONMIX_<stem>`，轴 `nion`×`Te`）
  - `.cnr` → `cnr_io` 7 块解码，产 **1 张** `kind=cnr_legacy` 表（仅组分/zbar/enrgy/群与 2-T 不透明度）
- `parse(path, relpath="", *, ...) -> ParsedTable`（返回 `parse_all(...)[0]`）
- `parse_composition(head: list[str]) -> dict` —— 从头部抽组分与维度（保留旧 API；自动识别 cn4/cnr 头部）
- `FAMILY = "ionmix"`；`CN4_SUPPORTED = (".cn4", ".cnr")`
- 异常：`eosop_pro.core.text.errors.ParseError`

若需按"一表一族"把 cn4 总表拆成 4 张（EOS + Ross/Planck_abs/Planck_ems），用 `cn4_io.cn4_to_parsed_tables`；反向组装用 `cn4_write.parsed_tables_to_cn4`。

```python
from eosop_pro.parsers.ionmix import parse_all

tables = parse_all(r"E:/data/Ionmix/he-imx-005.cn4", "Ionmix/he-imx-005.cn4")
t = tables[0]
print(t.kind, t.summary())      # cn4_eos; 轴 nion(cm-3) × Te(eV)
```

## 4. 陷阱与 unknown 清单

复述 [20 手册 §11](../../docs/20_格式规格与物理量单位手册.md) 本族条目（#1、#2、#8）：

1. **`deion_dn`（cn4 block 13）**：源码自注 `(not sure)` → unknown；解析器 notes 同步告警。
2. **`deele_dn`（cn4 block 14）**：同上。两处不确定性登记于 `eosop_pro/plotting/style/units.py:221`（`UNCERTAIN_UNITS`；20 手册所写 `cn4/units.py` 已过时）。
8. **`.cnr`（`xe-005grp-lte.cnr`）`op2tr`/`op2tp`**：`ntrad` 反解不整除 → 标 `unknown`（详见 [cnr_io.md §4](cnr_io.md)）。

其余陷阱：

- **`unit_hint_T` 忽略**：cn4 的 T 单位由源码确定为 eV；传入非 eV 值会被记为 note 而不生效。
- **`ngrups=0`**：无群不透明度，三维块为空（记 note）。
- **维度合理性闸门**：`ntemp`/`ndens` 超出 1..100000 视为非 cn4 文件，抛 `ParseError`。
- **2D 场转置**：cn4 原始 density-major，适配层转置为 `ParsedTable` 约定的 `(n_Te, n_x)`；3D 不透明度重排为 `(ngrups, n_Te, n_x)`。
- **`.cnr` 无 EOS 场**：不可用于 EOS 路径分析、不可直接转 `.cn4`（详见 [cnr_io.md](cnr_io.md)）。

## 5. 溯源

| 等级 | 含义 | 本族落点 |
|---|---|---|
| L1 format | 一手格式规格文档 | `ionmix/ionmix/docs/IONMIX用户指南.md` §5.4（仅 .cn4） |
| L2 declared | 文件内/伴随声明 | 头部组分行（格式 921/922） |
| L3 default | 格式默认约定 | 无 |
| L4 inferred/derived | 推导 | `p_ion`/`p_ele` 的 J/cm3；`dzdt` 的 1/eV；cnr 头部 4 网格参数 |
| L5 unknown | 无来源确认 | `deion_dn`/`deele_dn`；`xe-005grp-lte.cnr` 的 `op2tr`/`op2tp` |

一手依据：`ionmix/ionmix/src/Ionmix/abjt_03.f`（SUBROUTINE OWTF）+ `ionmix/ionmix/docs/IONMIX用户指南.md` §5.4/§5.1。
