> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# registry/material/ —— 三源合并的材料注册表：「材料 → 表文件」的权威映射

回答「哪个材料引用了哪些表文件」。三源为 `material.base`（主索引，256 个
`MATERIAL` 块）、`DatabaseIndex.xml`（补 Zbar/Abar/Rho0 与标志位）、
`hyades/EOS.list`·`Opacity.list`（Hyades 号与偏好标志），再由
`AnnotationStore` 补充伴随注释声明。上层 `schema/declared_types` 用注册表把
无扩展名文件定案为具体族；`zeff/`、`pipeline/batch.py`（convert-all 的
`--A` 参数）都经这里取材料事实。⚠️ `material.list` 实测为**空文件**，不可作索引。

## 模块

### material_base.py
`material.base` 解析——「一物质一 h5」的**主索引**。实测 251 个块、3805 行
（utf-8）：块头 `MATERIAL MID9`，键分三类——标量键（`A`/`Z`/`RHO`/`GAMMAG`/
`C0`/`S`…）、文本键（`Name`/`Formula`）、表引用键（`EOS`/`PLANCK`/`ROSSELAND`/
`NONLTE`/`ZEFF`…，值为 `<模块名> <文件名>`）。关键字频次：`A`/`Z`/`NAME`/`RHO`
各 251、`ZEFF` 130（→ Z̄(ρ,T) 表覆盖 130/251）。注释 `REM` 与 `#`；MID<100 为
Ramis 公布材料，>10000 为用户材料。

关键 API：
- `parse_material_base(path=None) -> list[MaterialBaseEntry]` —— 逐块解析
- `MaterialBase` —— 整表视图容器
- `MaterialBaseEntry` —— 单块条目；`refs` 为 `TableRef` 列表，含
  `zeff_relpath`（ZEFF 行指向的 Z̄ 表）
- `TABLE_KEYS` / `SCALAR_KEYS` / `TEXT_KEYS` —— 键分类 frozenset
- `TableRef` —— 一条表引用（kind + 模块名 + 文件名）

### database_index.xml 之外的第二源 → eos_list.py（见 schema/ 的 database_index.py）与本文件
`eos_list.py` 解析 `hyades/EOS.list`（84 行）与 `hyades/Opacity.list`（36 行）。
字段可缺失（`1032  Polystyrene  3.500` 只有 1 个数值），**不能按列数硬解析**；
规则：`id` = 首 token，`name` = 其后第一个非数值 token，其余数值 token 依序填入
`[Zbar, Abar, rho0]`。标志位：`*` = Preferred，`#` = Two-temperature；
不透明度号 ≈ EOS 号 + 1000。

关键 API：
- `parse_eos_list(path=None) / parse_opacity_list(path=None) -> list[ListEntry]`
- `parse_list_file(path) -> list[ListEntry]` —— 通用逐行解析
- `ListEntry` —— 单行条目（no/name/zbar/abar/rho0/preferred/two_temperature）；
  `describe()` 给人读摘要
- `RegistryLists` —— 两份 list 的合并视图，`by_no(no)` 按 Hyades 号查询

### material.py
三源合并为 `MaterialRecord`：以 `material.base` 的 251 块为骨架，按文件名挂上
`DatabaseIndex` 条目、按 Hyades 号挂上 `*.list` 条目、补齐空缺的 Z/A/rho0，
每个字段都留 `sources` 溯源。`MaterialRegistry` 构造时可选构建 `AnnotationStore`。

关键 API：
- `MaterialRegistry(matter_dir=None, *, build_annotations=True)` —— 构建即合并
- `by_mid(mid) -> MaterialRecord | None` / `by_name(name) -> list[MaterialRecord]`
  —— 按块号 / 名称或化学式查询
- `for_file(relpath) -> list[MaterialRecord]` —— 找出引用某文件的全部材料
- `unclaimed_files(all_files) -> list[str]` —— 无任何材料认领的文件
- `summary() -> dict[str, int]` / `source_diff() -> dict[str, list[str]]` ——
  统计与三源差异
- `MaterialRecord` —— 合并视图；属性 `label`、`h5_stem`、`files`（引用的全部
  表文件）、`kind_map`（文件 → 表类型）、`describe()`

用法示例：
```python
from eosop_pro.registry.material.material import MaterialRegistry

reg = MaterialRegistry(build_annotations=False)
rec = reg.by_mid(9)                     # MATERIAL MID9（Gold）
print(rec.label, rec.files, rec.sources)
hits = reg.for_file("mat_Au-1.0/AU_eos")  # 谁引用了这个文件
```
