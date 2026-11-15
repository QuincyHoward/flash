# cnr_io.py —— IONMIX `.cnr` 只读内核（F6）

> **适用仿真软件**：IONMIX（late-1986 CONRAD 格式，legacy 输出）| **官方链接**：无已核实官方 URL（uv），本地权威：`ionmix/ionmix/src/Ionmix/abjt_03.f`（SUBROUTINE OWTF，isw(8)=1/12/13 分支，line 4598–4621，写 unit 8）
> **概要**：`.cnr`（仅不透明度 + zbar/enrgy 的 7 块定宽文本表）**只读**内核，解析产出 `CNRTable` | **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步（uk=无来源确认/uv=未人工核查）；格式权威版本 = [20 手册 §7.6/§7.7](../../docs/20_格式规格与物理量单位手册.md)。读写兄弟格式见 [cn4_io.md](cn4_io.md)；适配层入口见 [ionmix.md](ionmix.md)。

## 1. 格式布局与计数公式

引 [20 手册 §7.1/§7.6](../../docs/20_格式规格与物理量单位手册.md)：`.cnr` 与 `.cn4` 同出 `SUBROUTINE OWTF`，是**两个互斥输出分支**（isw(8)=1/12/13 → unit 8）。**`IONMIX用户指南.md` 全文检索 "cnr" 命中 0 次** —— 该格式未被用户指南文档化，单位只能取自源码注释与参数说明块。

**4 行头部**（格式语句见 [20 手册 §7.7](../../docs/20_格式规格与物理量单位手册.md)）：

```
line 1 : ntemp, ndens            (2i10)
line 2 : izgas(...)              (a80 + 5i10)
line 3 : fracsp(...)             (a80 + 1p5e10.2)
line 4 : 981 format (4e12.6,i12) ← 与 .cn4 的根本区别：
         dlgden  log10(rho_0)  dlgtmp  log10(T_0)  ngrups 同一行
```

实测样例（`al-imx-001.cnr`）：`0.250000E+000.190000E+020.250000E+000.000000E+00          30` —— 前 4 个数值是**网格生成参数**（对数密度步长、密度起点 log10、对数温度步长、温度起点 log10），**不是数据块**；`ngrups` 取该行末尾 12 列。

**7 个数据块**（`991 format (4e12.6)`）——**没有** .cn4 的 12 个 EOS 二维场：

| # | 字段 | 形状 | 单位 | 源码行 | 溯源依据 |
|---|---|---|---|---|---|
| 1 | `zbar` | ntemp×ndens | -（无量纲） | 4606 | 赋值 `densne/densnn` → 比值 |
| 2 | `enrgy` | ntemp×ndens | J/g | 4608 | `abjt_03.f:4519` 参数说明 |
| 3 | `op2tr` | ntrad×ntemp×ndens | cm2/g | 4609 | `abjt_03.f:4529` 参数说明 |
| 4 | `op2tp` | ntrad×ntemp×ndens | cm2/g | 4611 | `abjt_03.f:4528` 参数说明 |
| 5 | `engrup` | ngrups+1 | eV | 4613 | 同 .cn4（`(in ev)`，`:4728`） |
| 6 | `orgp` | ngrups×ntemp×ndens | cm2/g | 4614 | `abjt_03.f:4527` 参数说明 |
| 7 | `opgpe` | ngrups×ntemp×ndens | cm2/g | 4616 | `abjt_03.f:4526` 参数说明 |
| H | 头部 4 网格参数 | 4 | **inferred** | 4604 | 指南未文档化，由 `write (8,981)` 语句位置推断 |

**计数守恒**（不符抛 `CNRParseError`，不静默）：

```
N = 2*ntemp*ndens + (ngrups+1) + 2*ngrups*ntemp*ndens + 2*ntrad*ntemp*ndens
```

**`ntrad` 不在头部存储**，必须由计数守恒反解：`rem = N - [2*ntemp*ndens + (ngrups+1) + 2*ngrups*ntemp*ndens]`，`ntrad = rem / (2*ntemp*ndens)`。本仓库 8 个 `.cnr` 实测 8/8 通过（多数 ntrad=51；`al-imx-001`/`helium-imx-002` ntrad=16）。

## 1.1 纯文本示例（原文摘录 + 逐行说明）

样例：`src/Multi1D++Portable20241128/matter++/Ionmix/xe-005grp-lte.cnr`（氙（Xe）5 群 LTE legacy 输出，ntemp=17 × ndens=13 × ngrups=5）

**原文摘录**（前 13 行，逐字保留原始空格，含行尾空格；摘录为数据文件原文，不混入任何注释）：

```
        17        13                                                            
 atomic #s of gases:         54                                                 
 relative fractions:   1.00E+00                                                 
0.250000E+000.184744E+020.250000E+000.000000E+00           5
0.104155E+000.848648E+000.183379E+010.371135E+01
0.629380E+010.865562E+010.133715E+020.194435E+02
0.258921E+020.337161E+020.436490E+020.456580E+02
0.519536E+020.520002E+020.539010E+020.539998E+02
0.540000E+020.791865E-010.769425E+000.169143E+01
0.347037E+010.604288E+010.841183E+010.128291E+02
0.188247E+020.257391E+020.327765E+020.434226E+02
0.449762E+020.519192E+020.519995E+020.538283E+02
0.539996E+020.540000E+020.599971E-010.677112E+00
```

**逐行说明**（格式 / 物理量与单位 / 顺序，单位与 §2 单位表一致）：

| 行 | 内容摘要 | 说明（格式 / 物理量与单位 / 顺序） |
|---|---|---|
| 1 | `        17        13` | 头部行 1（2i10 定宽）：`ntemp=17`、`ndens=13`（温度点数、密度点数） |
| 2 | ` atomic #s of gases:         54` | 头部行 2（a80 标签 + 5i10）：`izgas=54`（氙），单一组分 |
| 3 | ` relative fractions:   1.00E+00` | 头部行 3（a80 标签 + 1p5e10.2）：`fracsp=1.00`，无量纲 |
| 4 | `0.250000E+00…0.000000E+00          5` | 头部行 4（格式 981，4e12.6 + i12）：前 4 个值是**网格生成参数**（对数密度步长 0.25、密度起点 log10 值 18.4744、对数温度步长 0.25、温度起点 log10 值 0.0；这 4 个数的含义为 inferred，见 §4），**不是数据块**；行末 12 列为 `ngrups=5`——与 .cn4（ngrups 独占一行）的根本区别，也是 ionmix 适配层程序化判据所在 |
| 5–9（至行 9 第 1 个值） | `0.104155E+00`…`0.540000E+02` | 数据块 1 `zbar(ntemp×ndens)` 开头（格式 991，4e12.6 定宽无分隔）：**温度内循环 / 密度外循环**（与 .cn4 二维场同序，§1）。第 1 条密度线的 17 个温度点占行 5 至行 9 第 1 列，zbar 自 0.104 升至 54.0——54 正是氙的原子序数（全电离），可作 zbar 无量纲（§1 表单位 `-`）的实测佐证 |
| 9（第 2 个值起）–13 | `0.791865E-01`…`0.540000E+02` | 同块延续：行 9 第 2 个值 0.079 起为第 2 条密度线（同一温度序，17 点/行，至行 13 前两个值 53.99/54.0 收尾），行 13 第 3 个值 0.060 起进入第 3 条密度线——密度序递增、同温度下密度越低 zbar 越高（0.104 → 0.079 → 0.060）。其后依次为 enrgy / op2tr / op2tp / engrup / orgp / opgpe 块（§1 块表） |

## 2. 物理量与单位

上表逐块单位均摘自 [20 手册 §7.6](../../docs/20_格式规格与物理量单位手册.md)（唯一依据 = `abjt_03.f` 源码注释，**非猜测**）。字典 ionmix 族登记的是 .cn4 字段；`.cnr` 特有字段（`op2tr`/`op2tp`/`enrgy`/`orgp`/`opgpe`）未在字典单独登记，以本表为准。头部 4 网格参数为 **inferred**（非 unknown，但必须注明推断依据）。

## 3. 解析器 API 与用法

关键 API（签名经源码核实）：

- `parse_cnr(filepath, *, ...) -> CNRTable`（别名 `load_cnr`；批量 `load_cnr_dir(dirpath) -> list[CNRTable]`）
- `parse_cnr_header(lines) -> dict`、`solve_ntrad(ntemp, ndens, ngrups, n_values) -> Optional[int]`
- `expected_number_count(ntemp, ndens, ngrups, ...) -> int`、`CNR_N_BLOCKS = 7`、`CNR_BLOCK_SPEC`（块规格表）
- 异常：`CNRParseError(CN4ParseError)`；复用 `cn4_io` 的 `FIXED_WIDTH`/`FRAC_RE`/`guess_atomwt` 等定宽内核
- 经适配层调用：`eosop_pro.parsers.ionmix.parse_all` 对 `.cnr` 产 `kind=cnr_legacy` 表

```python
from eosop_pro.parsers.cnr_io import parse_cnr

tbl = parse_cnr(r"E:/data/ionmix/al-imx-001.cnr")
print(tbl.ngrups, tbl.blocks.keys())   # 30; zbar/enrgy/op2tr/op2tp/engrup/orgp/opgpe
```

## 4. 陷阱与 unknown 清单

复述 [20 手册 §11](../../docs/20_格式规格与物理量单位手册.md) 本族条目（#8）：

8. **F6 `.cnr`（`xe-005grp-lte.cnr`）的 `op2tr`/`op2tp`**：`ntrad` 反解不整除（余数不被 `2*ntemp*ndens` 整除），切分点**无法唯一确定** → 两块整体标 **`unknown`**，不给出伪造偏移；但 `engrup`/`orgp`/`opgpe` 仍从文件尾部反向定位成功。

其余陷阱与诚实边界：

- **无 EOS 场，不可转 cn4**：`.cnr` 缺 .cn4 的 12 个 EOS 二维场（压力/比热/离子电子分量），**不能**用于 EOS 路径分析（等温/等压/等熵/雨贡纽/声速），**不能**直接转 `.cn4`（缺 12 个必需块，无法补齐）；[20 手册 §12.2](../../docs/20_格式规格与物理量单位手册.md) 明文 `.cnr` 不能作为 cn4 转换来源。
- **`ntrad` 反解为非整数**：总计数仍闭合但块 3/4 切分点不唯一 → 整体标 `unknown`，不猜（见上）。
- **头部 4 网格参数 inferred**：`dlgden, log10(rho0), dlgtmp, log10(T0)` 的物理含义由 `write (8,981)` 语句位置推断，指南未文档化（[20 手册 §11](../../docs/20_格式规格与物理量单位手册.md) 末"inferred"条）。
- **网格点不递推**：独立变量为 `n_ion`×`T`，网格须由步长/起点自行递推，适配层轴留索引占位。
- **`ntemp`/`ndens` 语义**与 `.cn4` 同为（温度数, 密度数），可直接比较。

## 5. 溯源

| 等级 | 含义 | 本族落点 |
|---|---|---|
| L1 format | 一手格式规格文档 | 无（用户指南对 cnr 检索命中 0） |
| L2 declared | 文件内/伴随声明 | 头部组分行（与 .cn4 共用 921/922） |
| L3 default | 格式默认约定 | 无 |
| L4 inferred | 推断 | 头部 4 网格参数（`abjt_03.f:4604`，语句位置推断） |
| L5 unknown | 无来源确认 | `xe-005grp-lte.cnr` 的 `op2tr`/`op2tp`（切分点不唯一） |

一手依据：`ionmix/ionmix/src/Ionmix/abjt_03.f`（SUBROUTINE OWTF，isw(8)=1/12/13 分支）。块单位取自源码参数说明块（line 4519–4529）与逐条 write 注释。
