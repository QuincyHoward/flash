# eosop 变量控制字典

> 由 `registry/field_checks.py::dump_markdown()` 自动生成 ——
> **勿手改本文件**；人工核查后请直接改 `field_checks.py` 中对应
> 条目的 `checked=True`（或补 `source`），再重跑上述命令同步本文档。
> 标记规约（2026-09-15）：只有 `uk`（无来源确认）/ `uv`（未人工
> 核查）两个标记；两者都通过则**省略**（当前仅 cn4）。
> 标签双轨（2026-09-15 晚）：每条目含**短标签**（物理量简写，
> 绘图默认）与**长标签**（meaning，报告/核查）两个设置，显示时
> 都带 uk/uv 标记。
> 来源规约（2026-09-15）：`source` 只引用一级出处（文件内声明 /
> 一级说明文档 / 源码行号 / 派生公式），并尽量原文摘录；
> `docs/20` 手册属中间产物，**不得**作为来源引用。

## 字段说明（每列含义）

| 字段 | 含义 |
|---|---|
| 变量 | 解析器/绘图链路使用的字段名或轴名；`*` = 未登记列名的兜底条目 |
| 短标签 | 物理量标准简写（ASCII）；**绘图默认用**（用户 2026-09-15 晚裁定），空回退长标签 |
| 物理意义 | 英文长标签表述（报告/人工核查用，保证 ASCII），括注坐标制与已知陷阱 |
| 单位 | 推荐记法；`unknown` = 未判定，**不猜测** |
| 来源类型 | `in-file declaration` 文件内声明 / `primary document` 一级说明文档 / `source code` 源码行号 / `code-derived` 派生公式 / `none` 无可指认来源 |
| 标记 | `uk, uv` 无源未核查 / `uv` 有源未核查 / `（已核查，省略）` 有源已核查 |
| 来源详述 | 一级出处原文摘录 + 脚本/行号锚点；无源条目如实写明检索结果与不采信理由 |

登记族数：17；变量条目总数：94

## coldopacity

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `Eph` | E_ph | Photon energy axis (typical; per-file declared) | eV | in-file declaration | uv | 逐文件两行头明文声明列名与单位（实测 Ac.coldopacity：'#Eph<TAB>miu' + '#eV<TAB>cm2/g'）；解析器 parsers/coldopacity.py 读取该头逐列登记；本条 unit 为典型值，以逐文件头为准。 |
| `miu` | miu | Opacity column (typical; per-file declared) | cm2/g | in-file declaration | uv | 逐文件两行头明文声明列名与单位（实测 Ac.coldopacity：'#Eph<TAB>miu' + '#eV<TAB>cm2/g'）；解析器 parsers/coldopacity.py 读取该头逐列登记；本条 unit 为典型值，以逐文件头为准。 |
| `*` | col | Per-file column (see in-file name/unit header lines) | unknown | in-file declaration | uv | 逐文件两行头明文声明列名与单位（实测 Ac.coldopacity：'#Eph<TAB>miu' + '#eV<TAB>cm2/g'）；解析器 parsers/coldopacity.py 读取该头逐列登记；兜底列名/单位由逐文件头实时登记（查询兜底不猜）。 |

## derived_axes

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `n_e` | n_e | Electron number density (derived: n_e = rho*N_A*Zbar/A) | cm^-3 | code-derived | uv | 代码内派生公式：plotting/gridmap.py::_derive_ne，常数 N_A 取 config.py 单一来源（公式与常数均可指认，单位由量纲确定）—— 待人工核查。 |

## feos_aux

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `*` | raw | raw_values (auxiliary parameter file) | unknown | none | uk, uv | 辅助参数文件的未解码载荷：无可指认的一级来源（中间产物草稿不作依据）—— 待人工核查。 |

## feos_native

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis | g/cm3 | none | uk, uv | 网格经 .301 兄弟文件交叉校验逐值一致（parsers/feos_native.py 模块头'交叉校验证据'：Al/B 两例 NR/NT 双验证）；但 .feos 自身的单位声明无法从一级文档可靠还原 —— FEOS-Package-Documentation2016.pdf §16.2 正文受 PDF 抽取连字伪影影响（解析器模块头'诚实声明（风险 R3）'）→ 无可指认来源，待人工对照 PDF 原件核查。 |
| `Te` | Te | Electron temperature axis | eV | none | uk, uv | 网格由单调递增前缀裁剪定位（parsers/feos_native.py::grid_length，头部声明 NR/NT 实测可能多 1 个 0.0 哨兵）；行 0 十字段含 T_ref[eV]，但网格单位的文档级声明不可得（同 rho：PDF 抽取伪影）→ 待人工核查。 |
| `raw_values` | raw | Undecoded payload (PDF extraction artefacts; column semantics not recoverable) | unknown | none | uk, uv | 未解码载荷：解析器只完全解码行 0 十字段（有 .301 交叉验证）并定位 rho/T 网格，其余数值按原样存 raw_values、绝不猜列语义（feos_native.py 模块头'诚实声明（风险 R3）'）—— 设计上无来源可用。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | 未登记名兜底，不猜。 |

## feos_tabdata

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `*` | col | All columns (colN naming; no local column-name doc) | unknown | none | uk, uv | colN 占位列名：本地无任何一级列名文档（仅有中间产物草稿提及，不作依据）—— 语义待人工核查，不猜。 |

## generic_curve

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `*` | y | Fallback family - column semantics not documented, never guessed | unknown | none | uk, uv | 兜底族设计立场：列语义不文档化、绝不猜测（parsers/generic_curve.py）—— 无来源可用，人工核查前保持 uk, uv。 |

## hugoniot

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `Rho` | rho | Mass density (per-file declared) | g/cm3 | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准 |
| `T` | T | Temperature (per-file declared) | eV | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准 |
| `P` | P | Pressure (per-file declared) | Mbar | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准 |
| `E` | E | Specific internal energy (per-file declared) | erg/g | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准 |
| `Us` | Us | Shock velocity (per-file declared) | km/s | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准 |
| `Up` | Up | Particle velocity (per-file declared) | km/s | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准 |
| `*` | col | Per-file column (see '# [...] [unit]' comment header) | unknown | in-file declaration | uv | 逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' 与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit 仅为典型值，绘图以解析器逐文件提取（table.field_units）为准；兜底列由逐文件头实时登记。 |

## hyades_eos

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis | g/cm3 | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g'（逐字）；解析器 parsers/hyades_eos.py 模块头同文摘录（36-38 行）。 |
| `Te` | Te | Electron temperature axis (file in keV) | eV | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'温度 keV'（文件原生 keV，解析器换算为 eV 后登记）。 |
| `P` | P | Pressure (CGS native) | dyne/cm2 | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'压强 dyne/cm2'（CGS 原生单位，解析器原样保留）。 |
| `E` | E | Specific internal energy (CGS native) | erg/g | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'比内能 erg/g'（CGS 原生单位）。 |
| `kappa` | kappa | Opacity (opc_* = [Rosseland, Planck]) | cm2/g | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'不透明度参数使用同样的格式，压强处为平均Rosseland值，比内能处为平均Planck值，单位cm2/g'；且'本来应该存储Planck平均不透明度的位置用0代替'（Rosseland-only 判序依据，解析器 hyades_eos.py 模块头 32-34 行自动判序实现）。 |
| `raw_tail` | tail | Trailing residual values | unknown | none | uk, uv | 尾部残余值：L = 2 + NR + NT + 2*NR*NT 之外的余数，解析器 hyades_eos.py 按原样保存为 raw_tail 并记 unit=unknown —— 任何一级来源都未定义其含义，不猜。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | Hyades docx 未定义其它列名；未登记名兜底，不猜。 |

## hyades_opacity

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis | g/cm3 | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g'（逐字）；解析器 parsers/hyades_eos.py 模块头同文摘录（36-38 行）。 |
| `Te` | Te | Electron temperature axis (file in keV) | eV | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'温度 keV'（文件原生 keV，解析器换算为 eV 后登记）。 |
| `P` | P | Pressure (CGS native) | dyne/cm2 | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'压强 dyne/cm2'（CGS 原生单位，解析器原样保留）。 |
| `E` | E | Specific internal energy (CGS native) | erg/g | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'比内能 erg/g'（CGS 原生单位）。 |
| `kappa` | kappa | Opacity (opc_* = [Rosseland, Planck]) | cm2/g | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'不透明度参数使用同样的格式，压强处为平均Rosseland值，比内能处为平均Planck值，单位cm2/g'；且'本来应该存储Planck平均不透明度的位置用0代替'（Rosseland-only 判序依据，解析器 hyades_eos.py 模块头 32-34 行自动判序实现）。 |
| `raw_tail` | tail | Trailing residual values | unknown | none | uk, uv | 尾部残余值：L = 2 + NR + NT + 2*NR*NT 之外的余数，解析器 hyades_eos.py 按原样保存为 raw_tail 并记 unit=unknown —— 任何一级来源都未定义其含义，不猜。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | Hyades docx 未定义其它列名；未登记名兜底，不猜。 |

## ionmix

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `T` | T | Temperature axis (tplsma) | eV | source code | （已核查，省略） | abjt_03.f:4684 '(in ev)' + guide S5.4 |
| `nion` | n_ion | Ion (nucleon) number density axis (densnn) | cm^-3 | source code | （已核查，省略） | abjt_03.f:4686 + guide S5.1 mass-density formula |
| `zbar` | Zbar | Average charge state ne/nion | - | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4687 |
| `dzdt` | dZ/dT | d(zbar)/dT | 1/eV | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4691 (L4 derivation) |
| `p_ion` | P_ion | Ion pressure | J/cm3 | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4693 (L4) + guide :920 |
| `p_ele` | P_ele | Electron pressure | J/cm3 | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4696 (L4) + guide :921 |
| `dpion_dt` | dP_ion/dT | d(p_ion)/dT | J/cm3/eV | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4699 + guide :922 |
| `dpele_dt` | dP_ele/dT | d(p_ele)/dT | J/cm3/eV | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4702 + guide :923 |
| `e_ion` | E_ion | Ion specific internal energy | J/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4706 + guide :924 |
| `e_ele` | E_ele | Electron specific internal energy | J/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4708 + guide :925 |
| `cv_ion` | cv_ion | Ion specific heat | J/g/eV | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4711 + guide :926 |
| `cv_ele` | cv_ele | Electron specific heat | J/g/eV | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4713 + guide :927 |
| `deion_dn` | de_ion/dn | d(e_ion)/d(n_ion) | J*cm3/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4717-4719; source self-notes 'not sure' - unit provisional per guide :928 (uncertainty registered in cn4.units) |
| `deele_dn` | de_ele/dn | d(e_ele)/d(n_ele) | J*cm3/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4722-4725; source self-notes 'not sure' - unit provisional per guide :929 (uncertainty registered in cn4.units) |
| `engrup` | E_groups | Photon group boundaries | eV | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4729 '(in ev)' |
| `opac_rosseland` | kappa_R | Rosseland group opacity | cm2/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4525/:4733 + guide :931 |
| `opac_planck_abs` | kappa_P_abs | Planck absorption group opacity | cm2/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4526/:4736 + guide :932 |
| `opac_planck_ems` | kappa_P_ems | Planck emission group opacity | cm2/g | source code | （已核查，省略） | abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4 :4739 + guide :933 |

## ledcop_atomic

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis | g/cm3 | in-file declaration | uv | 文件头第 3 行明文声明（实测 Al.txt）：'Opacities in cm**2/gm, T in keV, density in gm/cc' —— density（gm/cc）项。 |
| `Te` | Te | Electron temperature axis (file declares keV inline) | eV | in-file declaration | uv | 文件头第 3 行明文声明（实测 Al.txt）：'Opacities in cm**2/gm, T in keV, density in gm/cc' —— T 项（文件原生 keV，解析器换算 eV）。 |
| `Ross` | kappa_R | Rosseland opacity | cm2/g | in-file declaration | uv | 文件头第 3 行明文声明（实测 Al.txt）：'Opacities in cm**2/gm, T in keV, density in gm/cc' —— Opacities 项。 |
| `Planck` | kappa_P | Planck opacity | cm2/g | in-file declaration | uv | 文件头第 3 行明文声明（实测 Al.txt）：'Opacities in cm**2/gm, T in keV, density in gm/cc' —— Opacities 项。 |
| `No. Free` | N_free | Free-electron count (dimensionless, normalization unchecked) | - | none | uk, uv | 列名来自解析器对数据列的切分命名；文件内无该列的单位/语义声明；Atomic(LEDCOP)说明.doc 抽取为乱码（ole2 双对齐失败）不可引用 → 无可指认来源，待人工核查。 |
| `Av Sq Free` | Nsqr_free | Mean-square free-electron count | - | none | uk, uv | 同 'No. Free'：文件内无声明、说明 .doc 抽取乱码不可引用 → 待人工核查。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | 未登记列名兜底，不猜。 |

## ledcop_zeff

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis (log10 values) | g/cm3 | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）（Zeff 节）：'温度和密度采用对数坐标系…密度单位是g/cm3'；解析器 parsers/ledcop_zeff.py 模块头（log10 rho 布局）。 |
| `Te` | Te | Electron temperature axis (log10 values, keV) | keV | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）（Zeff 节）：'温度单位是keV'，并明文与不透明度族区分（'与不透明度不同，不透明度温度单位为eV'）、文件名约定 X_Zeff.dat(keV) vs X_Z.dat(eV)；解析器 parsers/ledcop_zeff.py 模块头。 |
| `NoFree` | N_free | Free-electron number (Zbar equivalent) | - | primary document | uv | LANL TOPS FAQ（https://aphysics2.lanl.gov/static/opacdocs/opac-faq.html）Q1 逐字定义：'the free electron number is the average number of free electrons per ion'（每离子平均自由电子数；逐离子态布居加权，混合物按数分数加权平均）。LEDCOP 为 TOPS 官方文件格式之一（opac-help.html：'The LEDCOP files are older cross section files'），NoFree 列名即 TOPS 输出约定；最佳引用 Magee et al. 1995（LANL T-1）。*.NoFree 值段解析器 _field_for 登记为 Z/ZEFF；文件内无单位声明（.doc 抽取乱码不可引用）→ 无量纲。 |
| `AvSqFree` | Nsqr_free | Mean-square free-electron number (Z^2 equivalent) | - | primary document | uv | LANL TOPS FAQ（https://aphysics2.lanl.gov/static/opacdocs/opac-faq.html）Q7 逐字定义：'This is the average of the square of the number of free electrons over the ion stages of an element' （自由电子数平方对离子态的平均）→ <Z^2>，与 NoFree=<Z> 配套（差值即离子态方差）。同 NoFree：LEDCOP/TOPS 同源（LANL T-1，最佳引用 Magee et al. 1995），无量纲；解析器 _field_for 登记 Z2/ZEFF2。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | 未登记列名兜底，不猜。 |

## mpqeos

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis | g/cm3 | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）（MPQeos/SESAME 节）：'SESAME数据库的单位：…密度（g/cc）'，数据布局 'Id(1111)  Density(g/cc)  NR  NT'；解析器 parsers/mpqeos.py:107-109。 |
| `Te` | Te | Electron temperature axis (file in Kelvin) | eV | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）（MPQeos/SESAME 节）：'温度(Kelvin)'、布局 'T[1-NT](K)'，且'Multi1D++程序将自动识别文件后缀301/304/305并对单位制进行转化'；解析器 parsers/mpqeos.py:110-111 乘 config.EV_PER_K 转 eV。 |
| `P` | P | Pressure (file in GPa) | Mbar | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）（MPQeos/SESAME 节）：'压强（GPa）' + 换算式 '1GPa= 1e9Pa= 1e10 dyne/cm2=1e10erg/cm3=1e12 erg/cm2=1e-2Mbar'；解析器 parsers/mpqeos.py:115-117（config.MBAR_PER_GPA）。 |
| `E` | E | Specific internal energy (file in MJ/kg) | Mbar*cm3/g | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）（MPQeos/SESAME 节）：'能量（MJ/kg）' + 换算式 '1MJ/kg= 1e3J/g= 1e10 erg/g= 1e12 erg*cm/g=1e-2Mbar*cm3/g'；解析器 parsers/mpqeos.py:120-122（config.MBAR_CM3_G_PER_MJ_KG）。 |
| `Z` | Z | Average ionisation (5th payload segment) | - | none | uk, uv | docx 布局第 5 段 'Z[1-NRxNT]'，但同一 docx 自述'压强、能量甚至Z等有负值，原因正在查找'；解析器 parsers/mpqeos.py:142-152 实测负值并显式告警（风险 R3：段语义待核）。⚠️ 与'平均电离度'语义相矛盾的证据在案，不冒充有源 —— 待人工核查。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | MPQeos 布局只有 R/T/P/E/Z 五段；未登记名兜底，不猜。 |

## multi_inverted_eos

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis (linear) | g/cm3 | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'r[nr]  密度(g/cc)'；同文明文'因变量和自变量都没有使用对数坐标系，而是使用线性坐标系'；解析器 parsers/multi_inverted_eos.py:234-236 同值实现。 |
| `de` | de | Specific internal energy axis (above cold curve) | Mbar*cm3/g | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'de[ne]  能量(能量列表，与冷能量的差距, 单位Mbar*cm3/g)'；解析器 parsers/multi_inverted_eos.py:238-240。 |
| `P` | P | Pressure P(rho, de+e0) | Mbar | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'P[ne*nr]  压力 P[(0~nr-1)+nr*i]为密度为r[0~nr-1]，能量de[i]+e0[0~ nr-1]时的压力，单位为Mbar'；解析器 parsers/multi_inverted_eos.py:242-245。 |
| `E` | E | Specific internal energy (de + e0_cold) | Mbar*cm3/g | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：de 为'与冷能量的差距'，总比能 = de + e0；解析器 parsers/multi_inverted_eos.py:249-259 合成（无 e0 布局以 de 为基准并显式注记）。 |
| `e0_cold` | e0_cold | Cold curve specific energy (1-D over rho) | Mbar*cm3/g | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'e0[nr]  冷能量(密度对应的冷能量列表，单位Mbar*cm3/g)'；解析器 parsers/multi_inverted_eos.py:247-252。 |
| `de_energy` | de | Energy-axis spacing (same array as axis de) | Mbar*cm3/g | primary document | uv | 能量轴 de 另注册为一维场以便出图；单位继承 de 的 doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt） 声明；解析器 parsers/multi_inverted_eos.py:266-268。 |
| `T` | T | Temperature field T(rho, de+e0) (file in Kelvin, parser converts) | eV | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'T[ne*nr] 密度为r[0~nr-1]，能量de[i]+e0[0~ nr-1]时的温度（Kelvin）'；解析器 parsers/multi_inverted_eos.py:261-264 乘 config.EV_PER_K 转 eV（常数单一来源）。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | MULTI SESAME docx 的 F1 布局只定义 r/de/e0/P/T 五段（计数公式 '参数个数为4+2*nr+ne+2*nr*ne'），解析器 with_e0/no_e0 布局之外不承认其它列 —— 未登记名一律兜底，不猜。 |

## multi_opacity

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis (log10) | g/cm3 | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'剩下的数据依次为 r[nr]: log(密度g/cc)'，且'不透明度为logloglog全部采用对数存储数据'（log10 坐标）；解析器 parsers/multi_opacity.py 模块头'单位'节（另引 bundled 脚本 matlab/outputMULTIOpacity.m 逐行佐证）。 |
| `Te` | Te | Electron temperature axis (log10; eV/keV dual trap) | eV | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'t[nt] log(温度eV)'；⚠️ ZEFF 族例外为 keV —— 同 docx Zeff 节'温度单位是keV'并明文以 X_Z.dat(eV) / X_Zeff.dat(keV) 区分文件名，由解析器 unit_hint 传入（multi_opacity.py 模块头'单位'节）。 |
| `kappa` | kappa | Opacity (per-group subtables, log10) | cm2/g | primary document | uv | doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-word__3e289d7f.txt）：'z[nr*nt]表格数据（log坐标,cm2/g）'；多群子表头自带逐群 (E_lo, E_hi)，标签 PLANCK/ROSSLAN/EPS 分别对应 Planck 平均/Rosseland 平均/NLTE 因子（docx 数据类型表）；解析器 parsers/multi_opacity.py（LABEL_RE / KIND_BY_LABEL）。 |
| `Z` | Z | Mean ionisation (NZ kind) | - | none | uk, uv | NZ kind 值段（opbe.inhalt 表号 NZ；f2 枚举实测 547 个 F2-like 文件，见 multi_opacity.py 模块头）。⚠️ 不冒充有源：一级文档中 'Z' 指不透明度表格角值（docx：'其中Z的单位为cm2/g'），并非平均电离度 —— NZ 段语义未获任何一级来源确认，待人工核查定案。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | 未登记列名兜底；不猜，人工核查后补条目。 |

## sesame_dat

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `rho` | rho | Mass density axis | g/cm3 | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g'（逐字）；解析器 parsers/hyades_eos.py 模块头同文摘录（36-38 行）。 |
| `Te` | Te | Electron temperature axis (file in keV) | eV | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'温度 keV'（文件原生 keV，解析器换算为 eV 后登记）。 |
| `P` | P | Pressure (CGS native) | dyne/cm2 | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'压强 dyne/cm2'（CGS 原生单位，解析器原样保留）。 |
| `E` | E | Specific internal energy (CGS native) | erg/g | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'比内能 erg/g'（CGS 原生单位）。 |
| `kappa` | kappa | Opacity (opc_* = [Rosseland, Planck]) | cm2/g | primary document | uv | doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）：'不透明度参数使用同样的格式，压强处为平均Rosseland值，比内能处为平均Planck值，单位cm2/g'；且'本来应该存储Planck平均不透明度的位置用0代替'（Rosseland-only 判序依据，解析器 hyades_eos.py 模块头 32-34 行自动判序实现）。 |
| `raw_tail` | tail | Trailing residual values | unknown | none | uk, uv | 尾部残余值：L = 2 + NR + NT + 2*NR*NT 之外的余数，解析器 hyades_eos.py 按原样保存为 raw_tail 并记 unit=unknown —— 任何一级来源都未定义其含义，不猜。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | Hyades docx 未定义其它列名；未登记名兜底，不猜。 |

## snop_input

| 变量 | 短标签 | 物理意义 | 单位 | 来源类型 | 标记 | 来源详述（一级出处 / 脚本 / 文件内声明） |
|---|---|---|---|---|---|---|
| `T1` | T1 | Temperature bound 1 (lowest) | keV | primary document | uv | doc/SNOP.MANUAL（SNOP 程序手册；抽取文本 docs/extracted/SNOP__text__79a5123d.txt）：'T1  Lowest temperature (in keV)'；解析器 parsers/snop_input.py:33-38 PARAM_UNITS 逐字摘录。 |
| `T2` | T2 | Temperature bound 2 (highest) | keV | primary document | uv | doc/SNOP.MANUAL（SNOP 程序手册；抽取文本 docs/extracted/SNOP__text__79a5123d.txt）：'T2  Highest temperature (in keV)'；解析器 parsers/snop_input.py:33-38 PARAM_UNITS 逐字摘录。 |
| `X1` | hnu1 | Photon energy bound 1 (lowest) | keV | primary document | uv | doc/SNOP.MANUAL（SNOP 程序手册；抽取文本 docs/extracted/SNOP__text__79a5123d.txt）：'X1  Lowest photon energy (in keV)'；★ 修正：此前登记为 'Density bound'，系中间产物手册笔误 —— SNOP.MANUAL 原文为光子能量边界；解析器 parsers/snop_input.py:33-38 PARAM_UNITS 逐字摘录。 |
| `X2` | hnu2 | Photon energy bound 2 (highest) | keV | primary document | uv | doc/SNOP.MANUAL（SNOP 程序手册；抽取文本 docs/extracted/SNOP__text__79a5123d.txt）：'X2  Highest photon energy (in keV)'；修正说明同 X1；解析器 parsers/snop_input.py:33-38 PARAM_UNITS 逐字摘录。 |
| `FG` | groups | Photon group boundaries (user-supplied if IGROUP=0) | eV | primary document | uv | doc/SNOP.MANUAL（SNOP 程序手册；抽取文本 docs/extracted/SNOP__text__79a5123d.txt）：'FG(NG+1)Group boundaries (in eV) given by user if IGROUP = 0'；解析器 parsers/snop_input.py:33-38 PARAM_UNITS 逐字摘录。 |
| `*` | field | Unregistered field | unknown | none | uk, uv | SNOP.MANUAL 定义的其余 namelist 参数未逐一登记；未登记名兜底，不猜。 |
