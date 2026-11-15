> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# parsers/ —— 每格式族一个解析器，把纯文本数据表解析为统一的 ParsedTable

上层依赖：`convert/`（格式互转）、`writer/`（写 h5）、`registry/identify/dispatch`（按族分派解析器）。本层依赖 `core/`（textio 数值提取、errors、infer 锚点）与 `config`。**解析器之间禁止互相 import**（唯一例外：`cnr_io`/`ionmix` 复用 `cn4_io` 的定宽内核）。计数守恒校验（实测数 vs 表头推导数）是每个解析器的内置职责，不一致即抛错，**不可静默**。

## 模块

### base.py
解析器基类与共享数据结构。不依赖 numpy（纯 list）。定义统一容器 `ParsedTable`（轴/场/单位/log10 标记/计数守恒字段）、解析器协议 `TableParser`（`FAMILY` 常量 + `parse(path, relpath) -> ParsedTable`）、payload 布局公式表 `PAYLOAD_LAYOUTS`（供布局反演）与计数校验。

关键 API：
- `ParsedTable` —— 一张已解析表；便捷属性 `nr`/`nt`，方法 `axis(name)`、`field2d(name) -> [i_Te][j_x]`、`summary()`
- `check_count(actual, expected, *, path, header_raw) -> None` —— 不符即抛 `CountMismatch`
- `split_payload(values, *, nr, ne) -> dict` —— 按 F1 布局 `rho/de/e0/P/T` 累积游标切分
- `flatten_t_major(rows) -> list` —— `[i_Te][j_x]` 展平为 T-major（行主序）
- `read_payload_doc(path, *, skip_lines, blank_counter)` —— 读文件跳头部，**仅 payload 区**走 L2 数值提取
- `TwoDim.shape/get` —— 无 numpy 的二维场小工具

### cn4_io.py —— IONMIX `.cn4` 读写内核（全包最大模块）
`.cn4`（CONRAD 格式）的完整读写。布局权威来源是本地 FORTRAN 源码 `abjt_03.f` 的 `SUBROUTINE OWTF`（isw(21)!=0 分支，逐条 write 语句核对）+ `docs/IONMIX用户指南.md` §5.4。文件布局：4 行头部（`ntemp,ndens` / `izgas` / `fracsp` / `ngrups`）+ 18 个数据块（温度、数密度、12 个二维 EOS 场、群边界、3 个三维群不透明度），数据区 `4e12.6` 定宽。循环嵌套：2D 温度内循环/密度外循环 → `(ndens, ntemp)`；3D 群外循环 → `(ngrups, ndens, ntemp)`。计数守恒公式 `ntemp + ndens + 12*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens`，不符抛 `CN4ParseError`。

核心要点：
- **mantissa style 机制**：实测两种 `e12.6` 尾数风格并存——`"leading0"`（Ionmix 产物，`0.100000E+00`）与 `"dotted"`（BADGER-TOPS 系列，`1.000000E-01`）。`parse_cn4` 嗅探后记入 notes；`write_cn4(mantissa_style=...)` 按源风格复刻，保证 byte-identical 往返。负值实测为 13 列（`-.370029E-04`），写出侧不得为凑 12 列缩位
- **data_raw 逐字保留**：`parse_cn4` 把数据区原文存入 `CN4Table.data_raw`；`write_cn4(..., verbatim=True)`（`convert_cn4_to_cn4` 默认）逐字节直通，处理 BADGER 系列同文件混用两种尾数风格、`-Infinity` 字面量等逐值重排无法复刻的情形
- **NaN 占位**：`NAN_PLACEHOLDER_FIELD = "-9.99999+990"`（12 列对齐，解码为 -inf），`is_nan_placeholder()` 判定；缺失场写占位而非 0
- **打包指数缺陷修复**：`0.638380-140`（Fortran 3 位指数丢 E）读取侧自动还原
- **原子量三级来源**：用户传入 → 同目录 `ionmxinp` → 内置 IUPAC 元素表；均不可得则 `rho` 不可用（不猜）
- **跨族组装**：`parsed_tables_to_cn4(..., allow_foreign=True)` 接受任意族 ParsedTable，缺失场写 NaN 占位、**单位不换算**、单温总 EOS 均分到 ion/ele 槽并记 notes；`convert_foreign_to_cn4()` 为用户级入口
- **CLI**：`python -m eosop_pro.parsers.cn4_io <file.cn4> [out.cn4]`（打印 summary/计数/原子量来源，可顺带写出）

关键 API：
- `parse_cn4(filepath, *, atomwt=None) -> CN4Table`（别名 `load_cn4`；`CN4Data = CN4Table`）
- `write_cn4(table, out_path, *, write_opacities=True, mantissa_style=None, verbatim=False) -> Path`
- `convert_cn4_to_cn4(src, dst, **opts) -> Path` —— 默认 verbatim 直通的往返
- `cn4_to_parsed_tables(table, relpath="") -> list` —— 拆成 4 张表（EOS + Ross/Planck_abs/Planck_ems）
- `parsed_tables_to_cn4(tables, *, izgas, fracsp, atomwt=None, allow_foreign=False) -> CN4Table`
- `convert_foreign_to_cn4(src, dst, *, izgas, fracsp, atomwt=None, **opts) -> Path`
- `parse_header(lines) -> dict`、`expected_number_count(ntemp, ndens, ngrups) -> int`、`load_cn4_dir(dirpath) -> list`

用法示例：
```python
from eosop_pro.parsers.cn4_io import load_cn4, write_cn4

tbl = load_cn4(r"E:/data/Ionmix/he-imx-005.cn4")
print(tbl.summary())          # 组分/维度/网格范围
p = write_cn4(tbl, "out.cn4") # 逐值重排写出（verbatim=True 则数据区直通）
```

### cnr_io.py —— `.cnr`（late-1986 CONRAD）只读内核
`.cnr` 是 OWTF 的 isw(8)=1/12/13 分支输出：仅 7 块（zbar、enrgy、2 块 2-T 不透明度、群边界、2 块群不透明度），**无** cn4 的 12 个 EOS 场，不可用于 EOS 分析、不可直接转 cn4。格式特征：头部第 4 行为 `981 (4e12.6,i12)`——4 个网格生成参数 + ngrups 同行（与 cn4 的独占行不同）。`ntrad` 不存头部，由计数守恒反解；反解非整数时相关块诚实标 `unknown`（不猜）。独立变量：`n_ion`×`T`（网格点须由步长/起点递推，本层不做）。典型用法：`from eosop_pro.parsers.cnr_io import parse_cnr` → `CNRTable`。

### ionmix.py —— F6d：cn4/cnr → ParsedTable 适配层
按扩展名分派：`.cn4` 走 `cn4_io` 全 18 块解码产 1 张 `kind=cn4_eos` 总表（EOS 与 3 块不透明度合一，保持 cn4 原子性）；`.cnr` 走 `cnr_io` 产 `kind=cnr_legacy` 表（轴留索引占位，不递推网格）。格式特征：4 行头 + 18/7 块定宽。独立变量：`nion`（cm^-3）×`Te`（eV）。典型用法：`from eosop_pro.parsers.ionmix import parse_all`；需按"一表一族"拆 4 张表用 `cn4_io.cn4_to_parsed_tables`。

### multi_opacity.py —— F2：MULTI 不透明度/Zeff/NLTE/EPS（4×15 定宽）
★ 最大族。多群文件是 `ng` 个独立子表串联，每个子表自带完整表头 + `(E_lo, E_hi)` 边界线 + rho/T 网格 + 值；行 1 的 `f2` 是类型枚举（4=Rosseland、6=ZEFF、7=Planck）或文本标签（`PLANCK M`/`ROSSLAN M`，注意拼写）。`opbe` 类多 KIND 串联由 `parse_all` 拆多张表。rho/T/值均为 log10 存储；T 单位 eV，但 ZEFF 表存在 eV/keV 两套，须由 `unit_hint` 声明。独立变量：`rho`（g/cm3）×`Te`（eV）。典型用法：`from eosop_pro.parsers.multi_opacity import parse_all` → `MUGROUP/PLANCK/ZEFF` 等 kind 的表。

### multi_inverted_eos.py —— F1：MULTI 反演 EOS（默认 SESAME 族）
每块 4 数表头 `table_id rho0 nr ne`；两种 payload 布局（`with_e0` 含冷能 / `no_e0`）由计数守恒唯一反解（`detect_layout`），多块同表头串联拆多张表。**自变量是 (rho, de)，T 是因变量场**——这正是 "Inverted" 的含义；要 (rho, Te) 网格需经 `convert.invert_eos` 反演。单位：rho g/cm3 线性、de/e0/P Mbar 系、T Kelvin→eV。典型用法：`from eosop_pro.parsers.multi_inverted_eos import parse`。

### hyades_eos.py —— F3：Hyades/SESAME ASCII（5×15 定宽）
行 0 自由文本注释（材料名 + SESAME 号），行 1 = `id zbar abar rho0 L`（`L = 2+NR+NT+2*NR*NT`），行 2 起 payload。EOS 文件两数组为 [P, E]；`opc_*` 为 [Rosseland, Planck] 且按"Planck 槽位全零"自动判序。末尾补零显式记为 `raw_tail`。单位：rho g/cm3、T keV→eV、P dyne/cm2、E erg/g。独立变量：`rho`×`Te`。典型用法：`from eosop_pro.parsers.hyades_eos import parse_all`。

### mpqeos.py —— F4a：MPQeos/FEOS 的 SESAME 包装表（`.301/.304/.305`）
头 4 数 `Id Density NR NT`，payload `[R(NR)] [T(NT)] [P(GPa)] [E(MJ/kg)] [Z(NR*NT)]`，计数 `4+NR+NT+3*NR*NT`。两陷阱：表头 ID 列宽 16/17 不定（走 L2 正则）；字段宽逐文件不同（`infer_payload_width` 推断）。单位换算：GPa→Mbar、MJ/kg→Mbar*cm3/g、Kelvin→eV。第 5 段实测含负值，语义标"待核"。扩展名定 kind：`.301`=EOS_TOTAL、`.304`=电子、`.305`=离子。典型用法：`from eosop_pro.parsers.mpqeos import parse_all`。

### feos_native.py —— F4b：FEOS 原生表（`*.feos`）
行 0 十字段 `[FileVersion, NRho_decl, NT_decl, Nelements, Tcalclimit, Rhocalclimit, RhoRef, TRef, B0, SESAME#]` + 行 1 十参数 + `A/Z/X`（各 ne 个）+ rho/T 网格（**前导 `Qstart=0.0` 哨兵**，声明值 = 真实点数+1，确定性切分后修剪）+ **16 个 T-major 二维块**（P,E,S,F|Pe,Ee,Se,Fe|Pi,Ei,Si,Fi|PTF,ETF,STF,FTF）+ Qtot + Q（k 最内层交错）——布局由 FE-01_TABTOOLS.C::write_FEOS_format 定案（2026-11，R3 废除），计数公式闭合、无猜测。单位 cgs + eV 原生不换算。典型用法：`from eosop_pro.parsers.feos_native import parse_all`；权威解码 `decode()`（feos_to_cn4 复用）；详见 [`formats/feos_native.md`](formats/feos_native.md)。

### feos_aux.py —— F6e：FEOS 辅助文件（`.PAR/.cst/.mexport/.critical.dat/.isobaric.dat/.INV`）
分节 + `key=value`（`%`/`#` 注释），统一解析为 `kind=AUX` 表：`sections`（节名→kv）+ 全部数值原样。参数溯源用，不参与统一网格，不猜物理语义。典型用法：`from eosop_pro.parsers.feos_aux import parse_sections`。

### feos_tabdata.py —— F6a：ShowEOS 导出 TSV（`*.data.txt`）
制表符分隔数值表，列语义无本地文档 → 按 `colN` 命名整体保留；col0/col1 为行列索引。列宽取众数，偏离行报 `CountMismatch`。可用 `.301` 兄弟文件交叉核对。典型用法：`from eosop_pro.parsers.feos_tabdata import parse_all`。

### ledcop_atomic.py —— F5a：LEDCOP/ATOMIC 主表（`ATOMIC/*.txt`，可达 34 万行）
**锚点驱动的流式状态机**（不能按固定行数读）：维度声明 → T/rho 网格 → 逐 T 灰度块（Density/Ross/Planck/NoFree/AvSqFree 5 列）→ `Multigroup opacities` 段（nt*nr 块，体积极大，`include_multigroup=False` 默认跳过控内存）。文件内嵌单位声明行（`T in keV, density in gm/cc`）。独立变量：`rho`×`Te`（keV→eV）。典型用法：`from eosop_pro.parsers.ledcop_atomic import parse_all(path, include_multigroup=False)`。

### ledcop_zeff.py —— F5b：LEDCOP 拆分件（`*.NoFree`/`*.AvSqFree`）
极简结构：`<魔数 0.1234567E+000> <1.0> NR NT` + `[log10 rho] [log10 T(keV)] [值]`，计数 `4+NR+NT+NR*NT`。字段含义由文件名 token 决定（NoFree→Z/ZEFF，AvSqFree→Z2/ZEFF2）。轴 log10 线性还原。典型用法：`from eosop_pro.parsers.ledcop_zeff import parse_all`；魔数校验经 `LEDCOP_MAGIC`。

### coldopacity.py —— F6b：冷不透明度（`*.coldopacity`）
**两行自描述表头**：第 1 行列名、第 2 行逐列单位（制表符分隔），数值区按列拆 fields；第一列作 x 轴。全库最直白的内嵌单位声明。典型用法：`from eosop_pro.parsers.coldopacity import parse_two_line_header` / `parse_all`。

### hugoniot.py —— F6c：雨贡纽数据（`*.hug`）
列名与单位写在 `#` 注释行方括号里（`Rho[g/cm^3]`、`T [eV]`），兼容带缩放因子写法（`Rho [1.0e+000 g/cm^3]` → 单位记 `g/cm^3 (x1.0e+0)`）。第一列作轴，数据行须同宽。典型用法：`from eosop_pro.parsers.hugoniot import parse_column_header` / `parse_all`。

### generic_curve.py —— F6g：通用一维/二维曲线兜底
适用于无专门解析器的列式数值表（`ionpot.dat`、`PowerLaws/*.dat` 等）。策略：剥注释（`#/%/REM/c`）→ 众数列宽 → 第 0 列作 x 轴、其余 `colN`；单位一律 unknown，注释原文进 notes。**绝不因文件名猜物理量**。典型用法：`from eosop_pro.parsers.generic_curve import parse_all`。

### snop_input.py —— F6f：SNOP 输入脚本（`*.SNOP`）
Fortran namelist `&daten`：解出标量字典 + `FG` 群边界数组（可能跨行）。参数单位逐字来自 `doc/SNOP.MANUAL`（`RHO1/RHO2` g/cm3、`T1/T2` 与 `X1/X2` keV）。参数溯源文件，`kind=AUX`，不产生 (rho,T) 网格。典型用法：`from eosop_pro.parsers.snop_input import parse_namelist` / `parse_all`。

## 使用说明

所有解析器统一签名 `parse(path, relpath="") -> ParsedTable`（多块文件另有 `parse_all(...) -> list[ParsedTable]`）。格式族背景、单位换算与不确定单位清单见 [`../docs/20_格式规格与物理量单位手册.md`](../docs/20_格式规格与物理量单位手册.md)（格式权威版本）；逐变量单位/来源/标记见 [`../docs/eosop变量控制字典.md`](../docs/eosop变量控制字典.md)；每解析器的专门说明见 [`formats/`](formats/README.md)。

```python
from eosop_pro.parsers.hyades_eos import parse

t = parse("E:/data/hyades/sesame/eos_41.dat", "hyades/sesame/eos_41.dat")
print(t.summary())             # family/kind/id/nr/nt/axes/fields
print(t.field2d("P")[0][:5])   # [i_Te][j_x] 视图
```

## formats/ —— 每解析器一份格式说明

[`formats/`](formats/README.md) 下 16 份 `<解析器名>.md`（与本目录 .py 同名一一对应）：
适用仿真软件 / 官方链接 / 格式布局与计数公式 / 物理量与单位（含 uk/uv 标记）/ API 用法 / 陷阱与 unknown 清单 / 溯源。人工核对解析器理解是否有歧义时，以该文档为入口。

## test/ —— 产物核查套件（人工核查用）

[`test/`](test/README.md)：每解析器一个 `test_<名>.py`（与 formats/ 文档同名同序），
真实解析样例并产出**解析统计 summary.txt + 代表性图像**到 `test/_out/<解析器名>/`：

```bash
cd <gen_eos_op>
python eosop_pro/parsers/test/run_all.py      # 全量 + 汇总 log（_out/test_log.txt）
```

独立 runner，不接入主测试体系；与 [`../test/parsers/`](../test/parsers/README.md)（纯断言测试，进 run_all.py）分工互补。

## 格式支持状态

### 当前支持格式

| 族 | 解析器 | 扩展名 | 来源 | 状态 |
|---|---|---|---|---|
| cn4（IONMIX） | cn4_io.py + ionmix.py | .cn4 | IONMIX/CONRAD（abjt_03.f） | ✅ 全字段已核查（唯一标记省略族；仅 deion_dn/deele_dn 源码 not sure → unknown） |
| cnr（IONMIX legacy） | cnr_io.py + ionmix.py | .cnr | 同上（仅源码） | ⚠️ 只读不可转 cn4；头部 4 网格参数 inferred；部分文件 op2tr/op2tp unknown |
| F1 MULTI 反演 EOS | multi_inverted_eos.py | .dat/.inv/.sesame | MULTI（本地 docx） | ✅ 支持（T Kelvin→eV） |
| F2 MULTI 不透明度/Z̄/NLTE | multi_opacity.py | .dat（Thermos 树） | MULTI | ✅ 支持（★391 文件最大族；ZEFF eV/keV 双套陷阱；NZ 段 uk,uv） |
| F3 Hyades/SESAME | hyades_eos.py（3 族） | .dat（hyades 树）/sesame | Hyades、LANL SESAME | ✅ 支持（raw_tail uk,uv） |
| F4a MPQeos | mpqeos.py | .301/.304/.305 | JWGU MPQeos | ✅ 支持（Z 段 uk,uv） |
| F4b FEOS 原生 | feos_native.py | .feos | JWGU FEOS | ✅ 全解码（FE-01_TABTOOLS.C 定案，16 块+Qtot+Q；kind=code，uv；3 位指数变体 1 文件拒收） |
| FEOS TSV 导出 | feos_tabdata.py | .data.txt | ShowEOS | ⚠️ 结构支持、列语义全 unknown（uk,uv） |
| FEOS 辅助 | feos_aux.py | .PAR/.cst/.mexport 等 | FEOS | ⚠️ 结构支持、参数语义 uk,uv |
| F5a LEDCOP/ATOMIC | ledcop_atomic.py | ATOMIC/*.txt | LANL TOPS | ✅ 支持（官方 FAQ 已核实；No. Free/Av Sq Free uk,uv；多群段默认跳过） |
| F5b LEDCOP 拆分件 | ledcop_zeff.py | *.NoFree/*.AvSqFree | LANL TOPS | ✅ 支持（TOPS FAQ 逐字定义，全条目 uv） |
| 冷不透明度 | coldopacity.py | *.coldopacity | 通用 | ✅ 支持（两行自描述表头，全库最直白） |
| Hugoniot | hugoniot.py | *.hug | 通用 | ✅ 支持（单位逐文件可变，字典登记典型值） |
| SNOP 输入 | snop_input.py | *.SNOP | SNOP | ✅ 支持（X1/X2=光子能量边界） |
| 通用曲线兜底 | generic_curve.py | 兜底 | — | ⚠️ 结构兜底：全列 unknown（uk,uv），不猜物理量 |

### 不确定/受限项（uk/uv 标识，人工核查入口）

1. **uk,uv（无来源确认 + 未核查）**：feos_tabdata 全列、feos_aux raw_values、generic_curve 全列、hyades_eos raw_tail、multi_opacity NZ 段、mpqeos Z 段、ledcop_atomic No. Free/Av Sq Free（feos_native 已于 2026-11 定案升级为 kind=code/uv）
2. **unknown（有源但源码存疑）**：.cn4 的 deion_dn/deele_dn（abjt_03.f 自注 not sure）
3. **inferred（推断）**：.cnr 头部 4 网格参数（唯一非 unknown 的存疑项）
4. **受限**：.cnr 只读不可转 cn4；ledcop 多群段需 `--multigroup` 显式开启；generic_curve 仅收列式数值（x/colN 占位）
5. **标记规约**：uk=无来源确认 / uv=未人工核查（权威：`registry/field_checks.py`）；逐变量明细见《eosop变量控制字典》对应族；人工核查通过后改 field_checks.py 的 `checked` 并重生成字典，文档随之同步
