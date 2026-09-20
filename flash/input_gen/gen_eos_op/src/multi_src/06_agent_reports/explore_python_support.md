# eosop_pro —— EOS/Opacity 数据格式支持现状调研报告

> 生成时间: 2026-09-18 ｜ 范围: 只读调研，未修改任何文件
> 项目根: `E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op`
> 主包: `eosop_pro/eosop_pro/`（嵌套布局）｜ 测试: `eosop_pro/test/`
> 源数据: `src/Multi1D++Portable20241128/matter++/`（2211 文件 / 1567 MB，已 gitignore）
> 包内自带样品: `eos_op_data/`（FLASH_data / Gen_eos_op_data / Others_data）

---

## A. Parser 清单表

所有解析器位于 `eosop_pro/eosop_pro/parsers/`，统一协议见 `base.py`:
每个模块暴露 `FAMILY` 常量与 `parse(path, relpath)` / `parse_all(...) -> list[ParsedTable]`；
失败抛 `ParseError`/`CountMismatch`（**计数守恒校验不可静默**，`base.check_count`）。
`ParsedTable` 是统一容器：`axes` / `axis_units` / `axis_log10` + `fields` / `field_shape` /
`field_units` / `field_log10` + `n_groups` / `group_bounds` / `unit_source` / `layout_rule` /
`n_numbers_seen` / `n_numbers_expected` / `notes`。二维场统一约定 `(n_Te, n_x)` **T-major**。

| 模块 | 格式 / 扩展名 | 关键公开函数（__all__） | 硬编码解析规则要点 |
|---|---|---|---|
| `base.py` | —（基类） | `ParsedTable`, `TableParser`, `PAYLOAD_LAYOUTS`, `split_payload`, `check_count`, `TwoDim`, `flatten_t_major` | 解析器**不依赖 numpy**（纯 list）。`PAYLOAD_LAYOUTS` 硬编码各族计数公式：multi_inverted_eos=`4+2nr+ne+2nr*ne`；multi_opacity_gray=`4+nr+nt+nr*nt`；multi_opacity_mg=`4+nr+nt+ng*nr*nt`；hyades_eos=`2+nr+nt+2nr*nt`；mpqeos=`4+nr+nt+3nr*nt`；ledcop_zeff=`4+nr+nt+nr*nt`。`split_payload` 按 F1 游标切 `[rho][de][e0][P][T]`。`read_payload_doc`：payload 区才允许 L2 数值提取 |
| `cn4_io.py` | IONMIX `.cn4`（CONRAD，**可读写**） | `parse_cn4`, `load_cn4`, `load_cn4_dir`, `write_cn4`, `parse_header`, `expected_number_count`, `guess_atomwt`, `read_atomwt_from_ionmxinp`, `CN4Table/CN4Data`, `BLOCK_SPEC`, `OPACITY_SPEC`, `N_BLOCKS`, `NAN_PLACEHOLDER_FIELD`, `is_nan_placeholder`, `cn4_to_parsed_tables`, `parsed_tables_to_cn4`, `convert_foreign_to_cn4`, `convert_cn4_to_cn4` | **权威来源=`abjt_03.f SUBROUTINE OWTF` isw(21)!=0 分支（line 4662–4743）+ IONMIX用户指南 §5.4**。4 行头部：`line1 2i10 (ntemp,ndens)`；`line2 a80 'atomic #s of gases: '+5i10`；`line3 a80 'relative fractions: '+1p5e10.2`（正则 `FRAC_RE`，**与数据区 e12.6 不同**）；`line4 i12 (ngrups)`。数据区 **18 块**：`tplsma(ntemp)` eV → `densnn(ndens)` cm^-3 → **12 个 2D 场**（zbar/dzdt/p_ion/p_ele/dpion_dt/dpele_dt/e_ion/e_ele/cv_ion/cv_ele/deion_dn/deele_dn）→ `engrup(ngrups+1)` eV → **3 个 3D 不透明度场**（Rosseland/Planck abs/Planck ems）。计数=`ntemp+ndens+12·n2d+(ngrups+1)+3·ngrups·n2d`。循环嵌套：2D=温度内循环/密度外循环→reshape(ndens,ntemp)；3D=群外循环→reshape(ngrups,ndens,ntemp)。**定宽 `e12.6`（FIXED_WIDTH=12）**，处理 3 类 Fortran 缺陷：①打包指数 `0.638380-140`→`_PACKED_EXP_RE` 还原 `E`；②NaN 占位 `-9.99999+990`（下溢 -inf，阈值 -1e98）；③两种尾数风格 `leading0`/`dotted`（`_sniff_mantissa_style`，byte-identical 往返）。原子量三级来源 user→ionmxinp→内置 IUPAC 表 `ELEMENT_ATOMWT`（不猜）。编码链 utf-8-sig→utf-8→gb18030→latin-1，NUL 一票否决 |
| `cnr_io.py` | IONMIX `.cnr`（late-1986 CONRAD，**只读**） | `parse_cnr`, `load_cnr`, `load_cnr_dir`, `parse_cnr_header`, `solve_ntrad`, `expected_number_count`, `CNRTable`, `CNR_BLOCK_SPEC`, `CNR_N_BLOCKS` | 权威=`abjt_03.f OWTF` isw(8)=1/12/13 分支（line 4598–4621），**用户指南未文档化**。4 行头前三行同 cn4；**第 4 行是 `981 format (4e12.6,i12)`**（≠ cn4 的 `982 i12` 独占行）：`dlgden, log10(rho0), dlgtmp, log10(T0), ngrups`。**只 7 块**：zbar(n2d) / enrgy(n2d) J/g / op2tr(ntrad·n2d) / op2tp(ntrad·n2d) / engrup(ngrups+1) / orgp(ngrups·n2d) / opgpe(ngrups·n2d)。**`ntrad` 不在头部**，由计数余数反解 `solve_ntrad`（不能整除→标 unknown，不猜偏移）。**无 cn4 的 12 个 EOS 2D 场**，不能用于 EOS 路径分析 |
| `coldopacity.py` | `*.coldopacity`（冷不透明度） | `parse`, `parse_all`, `parse_two_line_header`, `FAMILY="coldopacity"` | 两行**自描述表头**：第 1 行列名（Tab 分隔）、第 2 行逐列单位（Tab 分隔），空行分隔，随后数值区。列数=names=units（不等抛错）；每行列数须等于首行列数。第一列作 x 轴，其余为 field。`unit_source="declared:inline (2-line header)"` |
| `feos_aux.py` | FEOS 辅助：`*.PAR` / `*.cst` / `*.mexport` / `*.critical.dat` / `*.isobaric.dat` / `*.INV` | `parse`, `parse_all`, `parse_sections`, `FAMILY="feos_aux"` | 分节标题（`[...]` 或 `Name:`）+ `key = value`（`_KV_RE`）；注释 `%` / `#` / `REM`。统一为 `kind=AUX`，只存 `sections` + `raw_values`，**不猜物理语义** |
| `feos_native.py` | FEOS 原生 `*.feos` | `parse`, `parse_all`, `HEADER_FIELDS`, `find_sibling_301`, `grid_length`, `FAMILY="feos_native"` | 行 0 恒 **10 个数**=`[Z, NR, NT, c1, c2, c3, rho0, T_ref_eV, B0, sesame_no]`（前 3 末 2 由 `.301` 兄弟文件交叉验证）；行 1=10 参数；行 2 起 `[A,Z,..]` 后接 rho 网格。**网格用单调性 `grid_length` 裁剪**（头部 NR 实测多 1 个 `0.0` 哨兵）。**数据块列序未定**（FEOS PDF §16.2 抽取伪影）→ 其余存 `raw_values`。交叉校验同目录 `.301` 的 NR/NT |
| `feos_tabdata.py` | ShowEOS 导出 TSV `*.data.txt` | `parse`, `parse_all`, `FAMILY="feos_tabdata"` | **Tab 分隔**（<2 列回退空格分割）；列数取众数，偏离行抛 CountMismatch；列命名 `colN`；col0/col1 标注为索引。列语义**无本地文档**→ 整体原样保留，unit=unknown |
| `generic_curve.py` | 兜底（`hyades/ionpot.dat`、`PowerLaws/*.dat`、`XrayMassCoef/*`、`Crystal/*.dat`、`Thermos/*.ini` 等） | `parse`, `parse_all`, `is_comment_line`, `COMMENT_PREFIXES`, `FAMILY="generic_curve"` | 注释前缀 `#`/`%`/`REM`/`c `/`C `；列数取众数，偏离行记录在 notes 并剔除；第 0 列作 x 轴，其余 `col1..colN`，单位一律 `unknown`；**绝不按文件名猜物理量**。仅在声明候选全部失败时作 last-resort（`ok_unverified`） |
| `hugoniot.py` | `*.hug`（雨贡纽） | `parse`, `parse_all`, `parse_column_header`, `FAMILY="hugoniot"` | 首行 `#` 注释里**列名+单位写在方括号**（`Rho[g/cm^3]`）；兼容带缩放因子写法 `Rho [1.000000e+000 g/cm^3]`→剥 `×N` 保留为 `(xN)`。列数由数据行决定，payload 须同宽。`unit_source="declared:inline"` |
| `hyades_eos.py` | Hyades / SESAME ASCII（`eos_*.dat`、`qeos_*.dat`、`opc_*.dat`、路径含 `hyades`；`.sesame`） | `parse`, `parse_all`, `parse_header_line`, `solve_dims`, `DOS_EOF`, `FAMILY="hyades_eos"` | 权威=`doc/Hyades 数据格式说明.doc`。行 1=自由文本注释（材料+SESAME#）；行 2=`id zbar abar rho0 L`（5 数），**`L = 2 + NR + NT + 2·NR·NT`**；行 3 起 `NR NT RHO T P E`（**T-major**）。`solve_dims` 解方程（解不唯一，仅交叉校验）。**末尾补零**（`raw_tail`）与 **DOS EOF `\x1a`** 显式处理。单位：rho g/cm3、**T keV→eV**、P dyne/cm2、E erg/g。`opc_*`：两数组=[Rosseland, Planck]，**按"Planck 槽位全零"自动判序** `_opacity_order` |
| `ionmix.py` | IONMIX `.cn4` / `.cnr`（**F6 适配层**） | `FAMILY="ionmix"`, `parse`, `parse_all`, `parse_composition`, `CN4_SUPPORTED=(".cn4",".cnr")` | 包裹 `cn4_io`：`.cn4`→1 张 `ParsedTable`（kind=`cn4_eos`，EOS+三块不透明度合一，形状 `(ngrups,n_Te,n_x)`）；`.cnr`→kind=`cnr_legacy`（7 块，轴用 `nion_index`/`Te_index` 因网格须由步长递推，**不递推**）。**合理性闸门** `1<=ntemp,ndens<=100000`。block13/14 单位源码自注 "not sure"→标 unknown |
| `ledcop_atomic.py` | LEDCOP/ATOMIC 主表 `ATOMIC/*.txt` | `parse`, `parse_all`, `scan_header`, `FAMILY="ledcop_atomic"` | **锚点驱动流式状态机**（Al.txt 有 348636 行，不能按固定行数）。锚点：`Number of T/Rho`、`Temperature/Density grid used ... N points`、`Density Ross Planck NoFree AvSqFree T=...`（灰度块，逐 T 一块）、`Multigroup opacities`（多群段，`nt*nr` 块）。`include_multigroup` 默认 **False**（省内存）。单位由**头行 3 内嵌**：`Opacities in cm**2/gm, T in keV, density in gm/cc` → T keV→eV |
| `ledcop_zeff.py` | LEDCOP 拆分件 `*.NoFree` / `*.AvSqFree` | `parse`, `parse_all`, `LEDCOP_MAGIC`, `FAMILY="ledcop_zeff"` | 极简：4 数头 `<魔数 0.1234567> <1.0> NR NT` + `[log10 rho(NR)][log10 T(NT)][值(NR*NT)]`。计数=`4+NR+NT+NR*NT`。**rho 与 T 均为 log10；T 单位 keV→eV**。魔数校验 `abs(hdr[0]-0.1234567)<1e-6`。`*.NoFree`→Z/ZEFF；`*.AvSqFree`→Z2/ZEFF2 |
| `mpqeos.py` | MPQeos / SESAME 包装 `.301`/`.304`/`.305` | `parse`, `parse_all`, `KIND_BY_EXT`, `FAMILY="mpqeos"` | 头 4 数 `Id Density NR NT`（**用 L2 正则，不能定宽**——ID 宽 16/17 不定）；payload `[R(NR)][T(NT)][P(n2) GPa][E(n2) MJ/kg][Z(n2)]`。**字段宽逐文件推断** `fw.infer_payload_width`（Al=15 / He=16）。计数=`4+nr+nt+3·n2`。单位换算：**T Kelvin→eV（×EV_PER_K）、P GPa→Mbar（×1e-2）、E MJ/kg→Mbar*cm3/g（×1e-2）**。第 5 段 Z 实测含负值→显式告警"语义待核" |
| `multi_inverted_eos.py` | MULTI 反演 EOS（SESAME F1，4×15 定宽） | `parse`, `parse_all`, `parse_header`, `detect_layout`, `LAYOUTS`, `HEADER_FIELDS`, `FAMILY="multi_inverted_eos"` | 每块头 4 数 `table_id rho0 nr ne`；**两种 payload 布局由计数反解**：`with_e0`=`rho(nr) de(ne) e0(nr) P(n2) T(n2)` / `no_e0`=`rho de P T`。**多块串联**（表头相同的 4 数行即块边界，如 `AU_eosd` 2 块）。自变量是 `(rho, de)`，**T 是因变量场**。单位：rho g/cm3 线性、de/e0/P Mbar 系、**T Kelvin→eV**。尾部多余值 `raw_tail` 显式标注 |
| `multi_opacity.py` | MULTI 不透明度/Zeff/NLTE/EPS（F2，4×15 定宽）★最大族 | `parse`, `parse_all`, `parse_header`, `take_numbers`, `LABEL_RE`, `KIND_BY_LABEL`, `KIND_BY_F2`, `VALUE_FIELD_BY_KIND`, `FAMILY="multi_opacity"` | **多群文件 = ng 个独立子表串联，每子表自带完整表头**（`[子表头][能群边界线(E_lo,E_hi)][rho 网格][T 网格][值]`）；`opbe` 是不同 KIND 表串联→拆多张。行 1 的 `f2` 是**类型枚举**（4=Rosseland/6=ZEFF/7=Planck/0.1234567=LEDCOP 魔数，非 Zbar）。`LABEL_RE` 宽松匹配 `PLANCK|ROSSELAND|ROSSLAN|PS|EPS`（**ROSSLAN≠ROSSELAND**）。KIND 判定顺序：label→f2 枚举→文件名 token→SESAME 数字位。**rho/T/值均为 log10**；T 多数族 eV，**ZEFF 表有 eV/keV 两套**（由 unit_hint 传入）。末尾补零→raw_tail |
| `snop_input.py` | SNOP 输入脚本 `*.SNOP` | `parse`, `parse_all`, `parse_namelist`, `PARAM_UNITS`, `FAMILY="snop_input"` | 解析 **Fortran namelist `&daten ... /`**（`_NL_START`/`_NL_END`），含续行合并；解出标量字典 + `FG` 群边界数组。单位逐字来自 `doc/SNOP.MANUAL`：`RHO1/RHO2` g/cm3、`T1/T2` keV、`X1/X2` keV、`FG` eV。kind=`AUX`（**不产生 (rho,T) 网格**） |

---

## B. `registry/field_checks.py` —— 控制字典结构

**定位**: eosop 家族「变量物理意义 / 单位 / 来源 / 核查状态」的**唯一权威登记**
（用户 2026-09-15 规约：一切绘图与分析操作都须经本字典）。

### B.1 核心数据结构

```python
@dataclass(frozen=True)
class FieldCheck:
    meaning: str      # 物理意义（英文长标签，保证 ASCII）
    unit: str         # 单位；"unknown" = 未判定，不猜测
    checked: bool     # 是否已人工核查
    kind: str = KIND_NONE   # 来源类型（受控词表）
    source: str = ""        # 来源详述（长文本，一级出处原文摘录/脚本行号）
    short: str = ""         # 短标签（绘图默认用；空串回退 meaning）
    @property
    def doc(self): ...      # 派生：kind!=none → "doc" 否则 "uk"（单一事实来源）

FIELD_CHECKS: dict[str, dict[str, FieldCheck]]   # family -> field -> FieldCheck
```

- **声明式**：每族一个 `dict[field_name, FieldCheck]`，**内联构造**（长/短标签同处，便于人工对照）。
- `"*"` 键 = 未登记列名的**兜底条目**（`coldopacity` / `generic_curve` / `feos_*` 等动态列族用）。
- `_UNREGISTERED_FAMILY` = 未注册族的兜底（查询永不崩溃，也绝不冒充已核查）。
- 查询 `field_check(family, field)`：精确名 → `"*"` → 未注册兜底。

### B.2 `kind` 受控词表（来源类型）

| 常量 | 值 | 含义 |
|---|---|---|
| `KIND_IN_FILE` | `in-file declaration` | **文件内明文声明**（数据自带头行注释逐字给出名称/单位） |
| `KIND_DOC` | `primary document` | **一级说明文档**（`doc/` 下随数据分发的权威手册，引用须带 `docs/extracted/` 抽取文本路径 + 原文摘录） |
| `KIND_CODE` | `source code` | **源码行号**（数据写出器/解析器源码可指认锚点，如 `abjt_03.f`） |
| `KIND_MEASURED` | `parser-measured` | 解析器实测证据（预留给 `register_family`） |
| `KIND_DERIVED` | `code-derived` | **代码内派生公式**（公式与常数均可指认，如 `n_e = rho*N_A*Zbar/A`） |
| `KIND_NONE` | `none` | **无可指认来源 → 显示 `uk`** |

来源规约铁律：`source` 只引用四类一级出处；`docs/20_格式规格与物理量单位手册.md` 是**中间产物，不得引用**；无一级出处者 `kind="none"` 并如实写明检索结果与不采信理由（PDF 抽取伪影、.doc 乱码）。

### B.3 uk / uv 标记系统

两重独立认证，显示时**折叠为 0~2 个标记**（`tags_label()` 是唯一出口）：

| 状态 | 含义 | 显示标记 |
|---|---|---|
| 无来源确认（`kind=="none"`）+ 未核查 | 完全无源 | `uk, uv` |
| 有来源（`kind!="none"`）+ 未核查 | 有源未核查 | `uv` |
| 有来源 + 已核查（`checked=True`） | 有源且已核查 | **`""`（标记整体省略）** |
| 无来源 + 已核查 | 诚实边界（登记缺陷） | `uk` |

- `uk` = no source acknowledgement（无可指认的一级出处）
- `uv` = unverified（未人工逐条核查）
- 图上 colorbar/x/y 轴一律 `Name (unit, <tags>)`；报告写 `tags=uk,uv`，全通过省略该键。
- **当前唯一 `checked=True` 的族 = `ionmix`（cn4 全 18 块）**。

### B.4 家族覆盖与字段数（实测 `family_check_stats`）

| 族 | 具名字段数 | checked | 主要 kind 来源 | 字段键 |
|---|---|---|---|---|
| `ionmix` (cn4) | **18** | **18** | `source code`（abjt_03.f OWTF + 指南） | T,nion,zbar,dzdt,p_ion,p_ele,dpion_dt,dpele_dt,e_ion,e_ele,cv_ion,cv_ele,deion_dn,deele_dn,engrup,opac_rosseland,opac_planck_abs,opac_planck_ems |
| `multi_inverted_eos` | 7 | 0 | `primary document`（MULTI SESAME docx） | rho,de,P,E,e0_cold,de_energy,T |
| `multi_opacity` | 4 | 0 | `primary document`（+ Z 段为 none） | rho,Te,kappa,Z |
| `hyades_eos` / `hyades_opacity` / `sesame_dat` | 6（**三族共用同一套**） | 0 | `primary document`（Hyades.doc） | rho,Te,P,E,kappa,raw_tail |
| `mpqeos` | 5 | 0 | `primary document`（+ Z 段 none，R3） | rho,Te,P,E,Z |
| `feos_native` | 3 | 0 | **`none`**（PDF 抽取伪影，诚实保持 uk） | rho,Te,raw_values |
| `feos_tabdata` | 0（仅 `*`） | 0 | `none` | — |
| `feos_aux` | 0（仅 `*`） | 0 | `none` | — |
| `ledcop_atomic` | 6 | 0 | `in-file declaration`（头行 3）+ NoFree/AvSqFree 为 none | rho,Te,Ross,Planck,No. Free,Av Sq Free |
| `ledcop_zeff` | 4 | 0 | `primary document`（MULTI docx + LANL TOPS FAQ 联网核查） | rho,Te,NoFree,AvSqFree |
| `coldopacity` | 2（+`*`） | 0 | `in-file declaration`（两行头） | Eph,miu |
| `hugoniot` | 6 | 0 | `in-file declaration`（`# name [unit]`） | Rho,T,P,E,Us,Up |
| `snop_input` | 5 | 0 | `primary document`（SNOP.MANUAL） | T1,T2,X1,X2,FG |
| `generic_curve` | 0（仅 `*`） | 0 | `none`（设计上无来源） | — |
| `derived_axes` | 1 | 0 | `code-derived` | n_e |

**登记族数 17；具名变量条目合计约 76；`checked=True` 仅 `ionmix`（18）。**

### B.5 Markdown 文档再生成

```bash
python -m eosop_pro.registry.field_checks
```
→ 调 `dump_markdown()` 写入 `eosop_pro/docs/eosop变量控制字典.md`（`DICT_DOC_RELPATH`，统一 LF）。
测试**守护该文档与字典逐字同步**（字典改动后必须重生成）。文档顶部含字段图例 + 生成警告「勿手改」。

---

## C. Multi1D++ 格式支持矩阵

来源: `src/Multi1D++Portable20241128/matter++/` 目录实测 + `registry/declared_types.py::EXT_MAP`。
「已支持」= 有专门解析器并经 `FAMILY_PARSERS` 分派。

| Multi1D++ 格式 | Python 已支持? | 实现模块 / 族 | 缺口 / 备注 |
|---|---|---|---|
| ionmix `.cn4` | ✅ 完整（读写） | `cn4_io.py` + `ionmix.py`（F6 `ionmix`） | 18 块全解码 + byte-identical 往返；`block13/14` 单位 unknown；`rho` 需 `ionmxinp` |
| ionmix `.cnr` | ✅ 只读（7 块） | `cnr_io.py` + `ionmix.py` | **无 12 个 EOS 2D 场**，不可转 cn4；`ntrad` 有时不可唯一确定→unknown |
| LEDCOP `NoFree` / `AvSqFree` | ✅ | `ledcop_zeff.py`（F5 `ledcop_zeff`） | 值段 Z/ZEFF、Z2/ZEFF2 |
| LEDCOP `GrayOpacity` (PLANCK/ROSSELAND) | ✅ | `multi_opacity.py`（F2）via 复合扩展名 `.grayopacity_planck` / `.grayopacity_rosseland` | |
| LEDCOP `MultiGroupOpacity` (PLANCK/ROSSELAND) | ✅ | `multi_opacity.py`（F2）via `.multigroupopacity_planck`/`_rosseland` | |
| LEDCOP `ATOMIC/*.txt` 主表 | ✅ | `ledcop_atomic.py`（F5 `ledcop_atomic`） | 锚点状态机；多群段默认**不解析**（`include_multigroup=False`） |
| hyades EOS `eos_*.dat` / `qeos_*.dat` | ✅ | `hyades_eos.py`（F3） | L 公式；末尾补零/EOF 显式处理 |
| hyades opacity `opc_*.dat` | ✅ | `hyades_eos.py`（F3 `hyades_opacity`） | Rosseland/Planck 自动判序 |
| hyades `coldopac.dat` / `ionpot.dat` | ⚠️ 兜底 | `generic_curve.py` | 无专门解析器，列语义 unknown |
| SESAME `.301`/`.304`/`.305`（+`material.base`/`material.list`） | ✅（`.301/.304/.305`）；⚠️ 注册表另处 | `mpqeos.py`（F4）；`material.base` 由 `registry/material_base.py` 解析 | `.301`=EOS_TOTAL/`.304`=EOS_ELECTRON/`.305`=EOS_ION。**`material.base` 不是数据表**，是材料主索引（251 块），由 registry 层解析，非 FAMILY_PARSERS |
| SNOP | ✅ | `snop_input.py`（F6） | 只解 namelist 参数，kind=AUX |
| FEOS `.301`/`.304`/`.305` | ✅ | `mpqeos.py`（F4 `mpqeos`，与 SESAME 包装同源） | 单位换算 GPa→Mbar / MJ/kg→Mbar*cm3/g |
| FEOS `.feos` | ⚠️ 部分 | `feos_native.py`（F4） | **行 0 十字段 + rho/T 网格已解码；payload 列序未定存 `raw_values`**（全树 29 个 `.feos` 均如此）；名实不符时回退 F1 |
| FEOS `*.PAR`/`.cst`/`.mexport`/`.critical.dat`/`.isobaric.dat` | ⚠️ 参数溯源 | `feos_aux.py`（F4） | 只存 kv + raw_values，无物理语义 |
| FEOS ShowEOS `*.data.txt` | ⚠️ 占位 | `feos_tabdata.py`（F4） | 列名 `colN`，语义未定 |
| Thermos `*.ini` | ⚠️ 兜底 | `generic_curve.py`（`.ini`→`AUX`） | 路径含 Thermos→候选 `[multi_opacity, multi_inverted_eos, generic_curve]` |
| Thermos `*_Planck.dat` / `*_Zeff.dat` | ✅ | `multi_opacity.py`（F2） | 多群子表串联；**Zeff 有 eV/keV 两套**（须注释声明） |
| cold opacity `*.coldopacity` | ✅ | `coldopacity.py`（F6） | 两行自描述头；67+ 同类文件 |
| mpqeos | ✅ | `mpqeos.py`（F4） | 与 `.301/.304/.305` 同一实现 |
| multi-inverted EOS（SESAME F1 / `.INV` / `.sesame`） | ✅ | `multi_inverted_eos.py`（F1） | with_e0/no_e0 双布局反解；多块串联拆分 |
| **Crystal**（`CrystalData.dat`/`LatticeSpacing.dat`/`names.txt`） | ❌ 专门解析器缺失 | 仅 `generic_curve.py` 兜底（文件名 token `crystal`→generic_curve） | 无字段语义、无单位 |
| **PowerLaws**（`PowerLaws.dat`/`ScalingLaws.dat`/`Ta2O5_*.dat`） | ❌ 专门解析器缺失 | 仅 `generic_curve.py` 兜底（token `powerlaw`→generic_curve） | 单位 unknown |
| 其它杂项：`Reflectivity.dat`、`XrayMassCoef/*`、`RadiativeCoolingRates.dat`、`DatabaseIndex.xml`、`Albedo.xml`、`PeriodicTable` | ❌ / ⚠️ | `generic_curve` 兜底 或 跳过规则 | XML/表格类走跳过或注册表 |

**汇总缺口**：
1. **Crystal、PowerLaws、Reflectivity、XrayMassCoef、RadiativeCoolingRates** 均无专门解析器（只被 `generic_curve` 兜底，单位/语义 unknown）。
2. **FEOS 原生 `.feos` payload 列序**无法从 PDF 恢复（诚实边界，registry 中 `kind=none`）。
3. **hyades `coldopac.dat` / `ionpot.dat`** 走兜底而非专门解析。
4. **`.cnr` legacy** 无 EOS 2D 场；`ntrad` 可能不可唯一确定。
5. **ledcop_atomic 多群段**默认跳过（性能）。
6. **SESAME `material.base`/`material.list`** 属注册表层（`registry/material_base.py`），不在 `FAMILY_PARSERS` 内。

---

## D. `config.py` 常量（与格式相关）

**唯一常量来源**（其他模块不得硬编码）。可被 `MULTI_EOSOP_*` 环境变量覆盖。

### 目录约定（层级推导）
```python
PACKAGE_ROOT   = .../eosop_pro/eosop_pro
PROJECT_ROOT   = .../eosop_pro
MULTIXD_INNER  = PROJECT_ROOT.parent
MULTI_HOME     = .../src/Multi1D++Portable20241128   # 可用 MULTI_HOME 覆盖
MATTER_DIR     = MULTI_HOME / "matter++"             # 源数据（2211 文件 / 1567 MB）
MATLAB_DIR / DOC_DIR / TABELLE_DIR
OUTPUTS_DIR / H5_DIR / H5_UNINDEXED_DIR / REPORTS_DIR / PLOTS_DIR / LOGS_DIR / INFERENCE_DIR
DOCS_DIR / EXTRACTED_DIR / SCRIPTS_DIR / TEST_DIR
```

### 已知注册表文件（材料注册表三源）
```python
MATERIAL_BASE = MATTER_DIR/"material.base";  MATERIAL_USER = MATTER_DIR/"material.user"
DATABASE_INDEX = MATTER_DIR/"DatabaseIndex.xml";  MATTER_README = MATTER_DIR/"Readme.txt"
EOS_LIST = MATTER_DIR/"hyades"/"EOS.list";  OPACITY_LIST = MATTER_DIR/"hyades"/"Opacity.list"
THERMOS_README = MATTER_DIR/"Thermos"/"Readme.txt"
```

### 编码链与文本卫生
```python
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "latin-1")   # latin-1 永不失败
BOM = "\ufeff";  NUL_BYTE = b"\x00"                        # NUL 一票否决
```

### 物理常量（单位换算的单一来源）
```python
N_A = 6.02214076e23          # mol^-1
EV_PER_K = 8.617333262e-5    # eV/K（T Kelvin→eV）
K_PER_EV = 1/EV_PER_K;  KEV_PER_EV = 1e-3
MBAR_PER_GPA = 1e-2          # 1 GPa = 1e-2 Mbar
MBAR_CM3_G_PER_MJ_KG = 1e-2  # 1 MJ/kg = 1e-2 Mbar*cm^3/g
ERG_G_PER_MBAR_CM3_G = 1e9   # 1 Mbar*cm^3/g = 1e9 erg/g
DYN_CM2_PER_MBAR = 1e12      # 1 Mbar = 1e12 dyne/cm^2
AMU_G = 1.66053906660e-24    # g
```

### 物理包络 / 单位反演阈值
```python
RHO_MIN_G_CM3=1e-8, RHO_MAX_G_CM3=1e6
TE_MIN_EV=1e-2, TE_MAX_EV=1e6;  P_MIN_MBAR=1e-12, P_MAX_MBAR=1e12
LOG_T_EV_IF_GE=4.5;  LOG_T_KEV_IF_LE=2.5      # 单位反演兜底
DIM_MIN=2;  DIM_MAX=50000                      # 布局反演尺寸上限
```

### 统一网格 / 插值 / HDF5
```python
N_X_UNIFIED=128;  N_TE_UNIFIED=128;  UNIFIED_SPACING="log10"
UNIFIED_GRID_IDS=("rho_Te","nion_Te")
INTERP_METHOD="bilinear_log10";  EXTRAPOLATION="nan"
MONOTONIC_ATOL=1e-12;  MONOTONIC_POLICY="error"
SCHEMA_VERSION="1.0";  H5_COMPRESSION="gzip";  H5_COMPRESSION_OPTS=4
AXIS_ORDER=("Te_eV","x");  FLOAT_DTYPE="f8";  NAN_SEMANTICS="out_of_range"
```

### 跳过规则 / 伴随注释
```python
SKIP_EXTENSIONS = {.docx .doc .pdf .xls .xlsx .pptx .ppt .js .gif .png .jpg ...}
SKIP_FILENAMES  = {readme readme.txt modinfo filelist lock material.list checksum ...}
SKIP_PREFIXES   = ("~$",)
ANNOTATION_SUFFIXES = (".info",".inhalt",".readme")
```

> ⚠️ **`DEFAULT_GRUPBD` 不在 `config.py`**：它定义于项目根部 `GEN_EOS_OP_GUIDE.md` 与
> `generator.py`（FLASH 侧生成器），值 = `[1e-1, 1e0, 1e1, 1e2, 1e3, 1e4, 1e5]` eV。
> 约束：FLASH 同一算例中不同材料**不能混用能群**，由 `validate_grupbd_consistency` 校验。
> eosop_pro 侧的能群边界来自数据文件自身（如 cn4 的 `engrup` 块）。

### 绘图样式（PPT 级）
`PLOT_DPI=450`；字号全部 **>18pt**（title 26 / label 22 / tick 20 / legend 20）；
`PLOT_CMAP="viridis"`；守护测试 `test_plot_style_constants_meet_ppt_requirements`。

---

## E. 现有文档清单与写作风格

### E.1 文档清单

| 路径 | 大小 | 2-3 行摘要 |
|---|---|---|
| `GEN_EOS_OP_GUIDE.md`（根） | 11 KB | FLASH 侧 `gen_eos_op` 生成器说明：`eos_op_data/` 目录约定、`DEFAULT_GRUPBD` 能群边界、材料规格（ntemp=61/ndens=71）、材料别名注册表。**中文 + 表格**；只覆盖 ionmix4 `.cn4` |
| `eosop_pro/README.md` | 10 KB | 包总览与命令矩阵、实测闸口数字（已解析 992/跳过 222）、各 step 测试覆盖、控制字典与标记规约摘要 |
| `eosop_pro/docs/README.md` | 8 KB | 文档索引（18 篇导航表）+ 三个常见问题 + 产物位置 + **文档写作约定三条纪律** |
| `docs/01_总览.md` | 13 KB | 项目定位、目录、模块地图、命令矩阵、实测数字 |
| `docs/02_两段式执行.md` | 18 KB | 「声明优先 + 内容兜底」契约与闸口 |
| `docs/03_注释证据通道.md` | 14 KB | 伴随文件/内联声明索引、四级单位仲裁 |
| `docs/10_纯文本提取规范.md` | 13 KB | 编码链、定宽、打包负号、注释剥离 |
| `docs/11_通用识别协议.md` | 22 KB | 给任意格式文件如何识别并提取 |
| `docs/12_HDF5模式.md` | 18 KB | 双轨（native 逐字 + unified 插值） |
| `docs/13_统一网格与插值.md` | 15 KB | `(rho,Te)` / `(nion,Te)`；F1 需先反演 |
| `docs/14_审计报告.md` | 19 KB | 三份报告字段与"报告即接口" |
| `docs/15_单位换算.md` | 14 KB | 四族四种单位、四级仲裁链 |
| `docs/16_Zeff盘点.md` | 11 KB | 九种来源、覆盖 130/251 |
| `docs/17_文档抽取.md` | 16 KB | doc/docx/pdf/xmind → 纯文本 |
| `docs/18_Gitee推送.md` | 6 KB | 推送凭据与三条路径 |
| **`docs/20_格式规格与物理量单位手册.md`** | **48 KB** | ★★ **权威格式规格文档**：合并 8 份旧文档；F1~F6 全部格式规格 + 逐族逐量单位 + 「溯源文档 → 实现脚本」双字段溯源 + 8 处 `unknown` 不猜 |
| `docs/eosop变量控制字典.md` | 34 KB | **由 `field_checks.py` 自动生成**（勿手改）；17 族逐变量表 |
| `docs/uk物理量猜测报告.md` | 12 KB | 无源（uk）物理量的盘点 |
| `docs/archive/04~09_格式规格_F*.md` | 9-19 KB | 原分族规格（已合并入 20，存档备查） |
| `docs/archive/SUPPORTED_TYPES_AND_UNITS.md` | 21 KB | 支持类型与单位溯源清单（存档） |
| `docs/archive/各种类型的eosop数据物理量及其单位说明.md` | 32 KB | 单位说明（存档） |
| `docs/extracted/*.txt` | — | 上游说明书抽取文本（MULTI/Hyades/FEOS/LEDCOP/SNOP 等），含 `MANIFEST` + sha256 |
| `ionmix/ionmix/docs/IONMIX用户指南.md` | 50 KB | **一级权威**（cn4 §5.4 数据排列顺序表） |

### E.2 写作风格 / 约定（自定纪律）

`docs/README.md` 明文三条：
1. **每条规格都标出处** —— 逐字引用上游文档，给 `docs/extracted/` 文件名。
2. **实测数字优先于描述** —— 写"391 个文件"而非"很多文件"；写"115.9 s"而非"较快"。
3. **不确定就写不确定** —— `ok_unverified` / `raw_values` / "列序待定" / `⚠️ 单位存疑` 如实呈现，不粉饰。

其它约定：
- **语言**：中文正文（技术术语、文件名、代码保留原文/ASCII）。
- **表格**：大量使用 Markdown 表格（族表、单位溯源表、字段字典表）。
- **单位溯源五级**：`L1 format:`（写出器源码/官方手册）> `L2 declared:`（文件内嵌声明）> `L3 default:`（程序默认）> `L4 inferred`（量纲反推）> `L5 unknown`（无依据→不猜）。
- **溯源防循环**：单位权威来源必须是**外部权威文档或数据文件自身声明**，**不得指向本项目解析器**（否则循环论证）；文档分别给出「溯源文档」与「实现脚本」两列。
- **诚实纪律**：无一级出处一律 `unknown` + `uk` 标记，不猜、不粉饰。

---

## F. 测试组织 + 样品数据位置

### F.1 测试目录结构（`eosop_pro/test/`）

`run_all.py` 递归发现所有 `test_*.py`，按目录分组打印，退出码 = 失败总数。共享运行器 `_runner.py`（含 sys.path bootstrap）；`_bootstrap.py` / `_migrate_bootstrap.py` 辅助。

| 子目录 | 内容 | 文件数 |
|---|---|---|
| `core/` | 文本/数值内核：anchors / annotations / byteclass / fixedwidth / fortran_numbers / guess / inference / textio_encoding | 8 |
| `registry/` | declared_types / docsrc / identify / material_registry / zeff_registry | 5 |
| `parsers/` | 各格式族解析器：coldopacity / feos_native / generic_curve / hugoniot / hyades_eos / ionmix / ledcop / mpqeos / multi_inverted_eos / multi_opacity | 10 |
| `plotting/` | cn4_plots / plots | 2 |
| `io/` | convert_default / grid_interp / h5_schema / prune | 4 |
| `pipeline/` | batch / gitee_publish | 2 |
| `hygiene/` | config_single_source / suite_hygiene（项目级规约守护） | 2 |
| **`eosopdata/`** | **材料数据模块**（下方详述） | — |

### F.2 `eosopdata/` 三步分组

```
eosopdata/
├── _idealgas.py           # 理想气体参考实现
├── _samples.py            # ★ 样品惰性发现（下文）
├── step01_cn4/            # cn4 专项
│   ├── test_cn4_extract.py     # 提取（块解码、计数守恒）
│   ├── test_cn4_paths.py       # 路径图
│   ├── test_cn4_plots.py       # 彩图（nion-T / ne-T / rho-T 双坐标）
│   └── test_cn4_thermo.py      # 热力学性质（雨贡纽、等温线、声速）
├── step02_families/       # 非 cn4 各族（F1-F6）
│   ├── test_family_extract.py  # 11 族提取（轴语义/场形状/数值合理性）
│   ├── test_family_paths.py    # 物理路径
│   ├── test_family_plots.py    # 彩图 + PPT 字号守护
│   ├── test_field_checks.py    # ★ 两重认证（uk/uv）守护
│   ├── test_plot_labels.py     # 长/短标签双轨守护
│   └── test_plot_<type>.py × 11  # 逐类型批量出图（含 source_data 副本守护）
│         coldopacity/feos_native/generic_curve/hugoniot/hyades_eos/
│         ledcop_atomic/ledcop_zeff/mpqeos/multi_inverted_eos/
│         multi_opacity/sesame_dat
└── step03_transcn4/       # 跨族 → cn4
    └── test_transcn4.py        # 格式骨架(48列)/NaN 占位/跨族组装/往返 byte-identical
```

**产物跟测试走**：各 step 文件夹内的 `_out/`（图/cn4 产物/test_log.txt，已 gitignore）。

### F.3 样品发现机制（`_samples.py`）

- **惰性发现**：`matter++` 全树 1000+ 文件、部分目录 1.5G（已 gitignore），故测试在不同机器/检出上都能跑；找不到样品 → `skip`（返回 None），**不把"数据不在"当缺陷**。
- `find_parseable(family, patterns)` / `find_parseable_many(...)`：找**能被该族解析器成功解析**的前 N 个文件（内容判断交给调用方）。
- `find_all_matching(patterns)`：按名字收全部（含解析失败者，供人工判断）。
- `first_cn4()`：首选 `PREFERRED_CN4 = "Z06_0.50-Z01_0.50-20260708_0850.cn4"`，回退选中等体积（~580KB）。
- `repo_root()` = `_samples.py` 的 `parents[3]`；`matter_dir()` = `config.MATTER_DIR`；`cn4_root()` = `repo_root()/eos_op_data`。
- step02 各族的 `SAMPLE_PATTERNS`（实测可解析）：mpqeos `*.301`、hyades_eos `qeos_*`、feos_native `*.feos`、multi_inverted_eos `AL_eos`、ledcop_atomic `Al.txt`、ledcop_zeff `*.NoFree`、multi_opacity `*.planck`、sesame_dat `*.dat`、coldopacity `*.coldopacity`、generic_curve `ionpot*`、hugoniot `*.hug`。

### F.4 样品数据位置

| 位置 | 内容 |
|---|---|
| **`gen_eos_op/eos_op_data/`**（项目根，仓库自带） | `FLASH_data/`（he-imx-005.cn4、polystyrene-imx-008.cn4）；`Gen_eos_op_data/`（Z02_1.00、Z06_0.50-Z01_0.50、Z06_1.00、Z14_1.00 的 .cn4 + PNG）；`Others_data/`（CH/He/Ti/V-BADGER-TOPS-Final.cn4 ×4） |
| **`src/Multi1D++Portable20241128/matter++/`**（上游源数据，gitignore） | Ionmix/（.cn4/.cnr）、ATOMIC/（LEDCOP 主表 + NoFree/AvSqFree/GrayOpacity/MultiGroupOpacity）、hyades/（sesame/opc_/qeos_/Opacity/）、ColdOpacity/（67 个 .coldopacity）、mat_<元素>-*（MULTI/FEOS 材料目录：.301/.304/.305/.feos/.PAR/eos_/mopp/mopr…）、SNOP/、Thermos/、FEOS/、PowerLaws/、Crystal/、SiO2/、XrayMassCoef/、RadiativeCoolingRates/、material.base/material.list 等 |
| `eosop_pro/outputs/` | h5/（含 _unindexed）、reports/（含 inference_reports）、plots/、logs/ |
| `eosop_pro/docs/extracted/` | 上游说明书抽取纯文本 + MANIFEST |

---

## 关键结论速览

1. **已实现解析器 18 个模块**，覆盖 17 个声明族 / 6 大格式族（F1 MULTI 反演 EOS、F2 MULTI 不透明度、F3 Hyades/SESAME、F4 MPQeos/FEOS、F5 LEDCOP、F6 IONMIX/其他）。
2. **cn4 是唯一"完整解码 + 读写 + byte-identical 往返"的格式**，也是控制字典中唯一 `checked=True` 的族（18/18）。
3. **控制字典 `field_checks.py` 是跨格式字段/单位/来源的唯一权威**；`uk`/`uv` 双标记 + `kind` 六值受控词表；由 `python -m eosop_pro.registry.field_checks` 再生成 `docs/eosop变量控制字典.md`。
4. **明确缺口**：Crystal / PowerLaws / Reflectivity / XrayMassCoef / RadiativeCoolingRates 无专门解析器（仅 generic_curve 兜底，单位 unknown）；FEOS 原生 `.feos` payload 列序不可恢复。
5. **文档体系成熟**：`docs/20_格式规格与物理量单位手册.md`(48KB) 是权威规格手册；三条写作纪律（标出处 / 实测数字 / 不确定就写不确定）+ 五级单位溯源 + 防循环溯源。
6. **测试**：递归跑 `test_*.py`；`eosopdata/` 分 `step01_cn4` / `step02_families` / `step03_transcn4` 三步，样品惰性发现，产物就近存 `_out/`。
