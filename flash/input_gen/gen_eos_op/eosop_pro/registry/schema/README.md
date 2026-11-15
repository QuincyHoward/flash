> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# registry/schema/ —— 声明式类型证据链：类型表、伴随注释与 DatabaseIndex

阶段 A 的证据层：`declared_types.py` 汇总**四类声明证据**给出每个文件的候选族
（零内容推断）；`annotation_store.py` 发现并配对伴随注释文件；`database_index.py`
解析 `DatabaseIndex.xml`。上层 `identify/dispatch.py` 按这里的候选族调解析器，
`material/material.py` 合并 DatabaseIndex 数据，`zeff/units_registry.py` 消费
注释里的单位声明。

## 模块

### declared_types.py
**声明式类型表**——零内容推断。类型来源按优先级：① 扩展名（`.301/.304/.305/
.cn4/.cnr/.coldopacity/.feos/.sesame/.ini/.snop/.hug`…）；② 路径规则
（`matter++/Readme.txt` 原文：含 `hyades` → Hyades，含 `.feos` → FEOS，
含 `.301/.304/.305` → MPQeos，否则默认 SESAME 4×15）；③ 文件名 token 约定
（`_eos_e`/`_mopp`/`ZEFF`/`PLANCK`/`op03p`/`eos_<n>`/`opc_<n>`…）；④ 外部注册表
（`material.base` 的 EOS/PLANCK/ROSSELAND/ZEFF 行直接给出 KIND）；⑤ 伴随注释
（`.info` 的 `IME=304`/`IMI=305`）。实测：150 个无扩展名文件中 95 个由注册表
定案、约 50 个由文件名 token 定案，仅约 5 个交阶段 B。⚠️ `AL_eos.feos` 名为
FEOS 实为 SESAME——阶段 A 只按声明取候选顺序，真正的内容识别留待阶段 B。

关键 API：
- `declare(relpath, *, registry=None, store=None) -> DeclaredType` —— 单文件判定
- `scan_declared(matter_dir=None, *, registry=None, store=None)
  -> list[DeclaredType]` —— 全树扫描
- `default_registry() -> tuple[MaterialRegistry, AnnotationStore]` ——
  构建一次、处处复用的默认证据源
- `iter_source_files(matter_dir=None)` —— 遍历 matter++ 数据文件
- `FAMILIES` / `KINDS` / `EXT_MAP` —— 受控词表与扩展名映射
- `DeclaredType` —— 判定结果 dataclass：`families`（候选族，按声明顺序）、
  `kind`、`source`（extension | path | name_token | registry | companion |
  default）、`evidence`、`mid`、`sesame_id`；属性 `family`（第一候选）、
  `is_skipped`、`is_unresolved`、`describe()`

### annotation_store.py
伴随注释文件发现与配对——阶段 A 的**声明式**证据来源。三类配对规则：
① 同名/前缀（`BE_eos.info` ↔ `BE_eos_e`、`Mix20keV.info` ↔ `Mix20keV.PLANCK`）；
② 目录级（`README`/`Readme.txt`/`MODINFO` 作用于本目录全部数据）；③ `#` 前缀
（`#LEDCOP` 是说明文件而非数据，内容含「文件名 → 来源」映射）。实测配对实例：
`AU_info` 声明 NG=20 + 单位 keV + Z/P/R/E 表号映射；`opbe.inhalt` 的 NG=40 是
拆分 opbe 的钥匙；`Thermos/Readme.txt` 明写 `*_Z.dat`=eV、`*_Zeff.dat`=keV。

关键 API：
- `AnnotationStore(matter_dir=None)`；`build(*, force=False) -> AnnotationStore`
  —— 扫描全树建索引
- `for_file(relpath) -> list[Annotation]` / `for_directory(rel_dir)` —— 查询
- `merged_units(relpath) -> dict[str, str]` —— 合并本文件 + 目录级单位声明
- `unit_hint_for(relpath, *, axis="T") -> str | None` —— T 轴单位声明提示
- `COMPANION_SUFFIXES`（`.info/.inhalt/.readme`）与
  `COMPANION_SUFFIXES_UNDERSCORE`（`_info/_inhalt/_readme`，MULTI 惯例变体，
  只认点号会漏掉 `AU_info`）、`COMPANION_FILENAMES`、`COMPANION_PREFIXES`

### database_index.py
`DatabaseIndex.xml` 解析——材料注册表第二来源。实测 139 行：`<HYADES>` 分支下
`<EOS>` 98 条、`<Opacity>` 36 条，属性含 `No/Material/File/Zbar/Abar/Rho0/Notes`；
`Notes` 里 `*(Preferred)` 与 `#(Two-temperature)`/`#(electron-table)` 是标志位。

关键 API：
- `parse_database_index(path=None) -> list[DbIndexEntry]` —— 逐条解析（`file`
  已归一为 POSIX 相对路径）
- `DatabaseIndex` —— 索引视图：`by_file(relpath)` / `by_no(no)` /
  `by_material(material)` / `n_eos()` / `n_opacity()` / `summary()`
- `DbIndexEntry` —— 单条条目（kind/no/material/file/zbar/abar/rho0/notes/
  preferred/two_temperature）
- `sesame_digit_of(table_id) -> str | None` /
  `kind_from_sesame_id(table_id) -> str | None` —— SESAME 表号 → 类型位

用法示例：
```python
from eosop_pro.registry.schema.declared_types import scan_declared, default_registry

reg, store = default_registry()
for d in scan_declared(registry=reg, store=store):
    if d.is_unresolved:
        print(d.relpath, "→ 阶段 B")
    else:
        print(d.relpath, d.families, d.source)
```
