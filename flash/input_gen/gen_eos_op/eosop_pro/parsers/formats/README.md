> 最后核对：2026-11-14 · commit f8225de

# formats/ —— 按解析器命名的每格式专门说明

与 `parsers/*.py` 一一对应：每个 md 讲一种数据格式的布局、物理量单位（含 uk/uv 标记）、解析器 API 与陷阱。单位与来源的**权威登记处**是《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》（由 `registry/field_checks.py::dump_markdown()` 自动生成）；格式规格的**权威版本**是《[20 手册](../../docs/20_格式规格与物理量单位手册.md)》。本文档只**引用 + 摘录**它们，不照抄。

## 16 文档导航表

| md 名 | 族 | 一句话 |
|---|---|---|
| [ionmix.md](ionmix.md) | F6 IONMIX | `.cn4`/`.cnr`（abjt_03.f 逐块 18/7 块），密度轴是**数密度 cm^-3**，P/E 为 SI 派生 J/cm3、J/g |
| [cn4_io.md](cn4_io.md) | F6 `.cn4` 读写内核 | cn4 全 18 块读写 + byte-identical 往返、mantissa style、NaN 占位 |
| [cnr_io.md](cnr_io.md) | F6 `.cnr` 只读内核 | legacy 7 块格式（用户指南未文档化），ntrad 由计数守恒反解 |
| [multi_eos.md](multi_eos.md) | F1 | MULTI 反演 EOS，自变量 (rho, de)、T 是因变量，with_e0/no_e0 双布局 |
| [multi_opacity.md](multi_opacity.md) | F2 | MULTI 不透明度多群子表串联；ZEFF 表 eV/keV 双套陷阱 |
| [hyades_eos.md](hyades_eos.md) | F3 | Hyades/SESAME 5×15 定宽；CGS 原生 dyne/cm2、erg/g |
| [mpqeos.md](mpqeos.md) | F4a | `.301/.304/.305` SESAME 包装表，GPa→Mbar、MJ/kg→Mbar*cm3/g |
| [feos_native.md](feos_native.md) | F4b | `.feos` 十字段头（.301 交叉验证），raw_values 不猜列序 |
| [feos_tabdata.md](feos_tabdata.md) | F4 | ShowEOS 导出 TSV，列语义无本地文档 → colN 整体保留 |
| [feos_aux.md](feos_aux.md) | F6e | FEOS 辅助参数（分节 + key=value），参数溯源用 |
| [generic_curve.md](generic_curve.md) | F6g | 兜底族：众数列宽、全列 unknown，绝不因文件名猜物理量 |
| [hugoniot.md](hugoniot.md) | F6c | 雨贡纽曲线，单位写在 `# name [unit]` 注释头（逐文件可变） |
| [coldopacity.md](coldopacity.md) | F6b | 冷不透明度，两行自描述表头（列名/单位）——全库最直白单位声明 |
| [ledcop_atomic.md](ledcop_atomic.md) | F5a | LANL ATOMIC 主表（34 万行），锚点状态机，文件头内嵌 T in keV 声明 |
| [ledcop_zeff.md](ledcop_zeff.md) | F5b | LEDCOP 拆分件 NoFree/AvSqFree，唯一有已核实互联网定义（TOPS FAQ）的族 |
| [snop_input.md](snop_input.md) | F6f | SNOP 输入 namelist &daten，X1/X2 是光子能量边界（keV） |

## uk/uv 标记规约

与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》头部声明同步：

- `uk` = 无来源确认（无可指认的一级出处）；`uv` = 未人工核查
- 两者都通过则**省略**（当前仅 cn4 族）；组合折叠为 `uk, uv` / `uv` / 空
- 权威判定处 = `registry/field_checks.py`（`checked`/`source` 字段）+ 自动生成的字典 md

## 三条硬纪律

1. **字典 md（`docs/eosop变量控制字典.md`）由 `field_checks.py::dump_markdown()` 自动生成，勿手改**；人工核查后改 `field_checks.py` 对应条目的 `checked=True`（或补 `source`）再重新生成。
2. **本文档只引用 + 摘录字典 / 20 手册，不照抄**——避免双权威漂移；20 手册本身属中间产物，不得作为单位来源引用（来源只引一级出处）。
3. **改判 uk/uv 标记的唯一路径**：修改 `registry/field_checks.py` 的 `checked` → 重跑生成命令同步字典 md → 再同步本文档。不得在文档里自行改判。

## 阅读顺序建议

- 新手上路：[ionmix.md](ionmix.md)（最重要一族，F6）→ [cn4_io.md](cn4_io.md) / [cnr_io.md](cnr_io.md)
- 按族直接查：跨族单位差异先看 20 手册 §10 速查表（T 单位 eV/keV、密度 cm^-3、P/E 三套体系）
- 只关心某格式的单位：直接看对应 md 的「§2 物理量与单位」表
