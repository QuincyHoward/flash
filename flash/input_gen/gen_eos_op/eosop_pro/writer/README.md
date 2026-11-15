> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# writer/ —— HDF5 双轨写出器：native 逐字保留 + unified 统一网格插值

上层依赖：`pipeline`（材料级写出主流程）与 `convert/`（`h5` 目标的 `write_h5_single`）调用本层。本层依赖 `parsers/base`（ParsedTable）、`grid/unified_grid`（UnifiedGrid）、`grid/interpolate`（双线性重采样）、`convert/invert_eos`（F1 反演）与 `ops/reporting`。HDF5 模式详见 [`../docs/12_HDF5模式.md`](../docs/12_HDF5模式.md)。

**双轨设计**：轨道 1 `native/` 原生网格逐字保留（含单位与 log10 标记属性），任何人可逐点核对回源文件；轨道 2 `unified/<gid>/` 插值到统一网格（本轮两套：`rho_Te` / `nion_Te`），轴序固定 `(n_Te, n_x)`，越界写 NaN 并把越界计数写进属性。物理量一律 float64；`gzip level=4 + shuffle`，2D/3D 显式 chunks，1D 轴不压缩；NaN 只表示"落在原生凸包之外"（`nan_semantics="out_of_range"`）。

## 模块

### h5_schema.py —— HDF5 模式常量与属性规范化
定义 `schema_version = 1.0` 的路径常量（`META/TABLES/NATIVE/UNIFIED`）、`/meta/sources` 与 `/meta/zeff_sources` 的列序、以及每张表/每个轴/每个场**必须携带**的属性清单（`REQUIRED_TABLE_ATTRS` / `REQUIRED_AXIS_ATTRS` / `REQUIRED_FIELD_ATTRS`，缺了会被 `test_h5_schema` 挑出来）。

关键 API：
- `dtype_f8() / str_dtype()` —— float64 与变长 UTF-8 字符串 dtype
- `scalar_attrs(**kwargs) -> dict` —— 属性规范化：None 丢弃、dict/list 拼串、numpy 标量取 `.item()`
- `vector_attrs(d) -> dict` —— 把 `{k: {kk: v}}` 展平成 `k_kk` 形式
- `open_mode(path, mode="w")` —— h5py.File 统一入口

### h5_writer.py —— 双轨写出器（本层主模块）
逐表写 `/tables/<key>/`（组属性含 quantity_kind/family/layout_rule/unit_source/计数守恒等），native 轨写轴+场，unified 轨对每个 `UnifiedGrid` 做双线性插值。两处关键正确性细节：`nion_Te` 轨插值前**必须把源 x 轴做同样变换**（rho → n_ion，否则两把尺子量）；F1（de 基）的表先经 `invert_eos.to_Te_grid` 反演成 (rho, Te) 再插值。`field_log10=True` 的场先还原成物理量、插值在 log 空间进行，避免"对 log10 值再取 log10"。同键多表自动去重（`_b2/_b3`…，原名记入 `group_key_disambiguated_from` 属性——实测 `Al_etc.dat` 有两个键同为 `MUGROUP_0` 的表）。

关键 API：
- `write_material_h5(out_path, *, material, tables, grids=None, A=None, sources=(), units=(), warnings=(), annotations=(), zeff_sources=(), native_track=True, extra_root_attrs=None) -> Path` —— 写一个材料的 .h5（`native_track=False` 且 `grids=None` 会被显式拒绝）
- `write_table_group(f, table, grids=None, *, A=None, native_track=True, key_override=None) -> dict` —— 写一张表（native + 可选 unified），返回 `{gid: 越界点数}`
- `write_unified(f, table, grids, *, A=None, skip_inverted_eos=False, key_override=None) -> dict` —— 统一轨；de 基表走反演路径
- `write_native(grp, table) -> None` —— 原生轨：轴与场逐字保留

### provenance.py —— `/meta` 组织：溯源表
每个结论都可追到具体文件与字段。字符串表以 `[n_rows, n_cols]` 变长 UTF-8 数组落盘，列名存 `attrs['columns']`。

关键 API：
- `write_root_attrs(f, *, material, extra=None)` —— 根属性（schema_version/tool_version/generated_utc/grid_convention/nan_semantics）
- `write_sources(f, rows)` —— 溯源表（列序见 `SOURCES_COLUMNS`：table_key/kind/family/source_relpath/sha256/计数/layout_rule/unit_source…）
- `write_units(f, rows)` —— (quantity, unit, source, evidence) 四列单位声明
- `write_warnings(f, warnings)` —— 全部告警（count_mismatch / unit_suspect / …）
- `write_annotations(f, rows)` —— 注释证据（材料名/Z/A/组分/provenance/dims/单位…）
- `write_unified_grid_meta(f, grids)` —— 各统一网格参数（x_axis/n_x/Te 范围…）
- `write_zeff_sources(f, rows)` —— Z̄ 来源表
- `write_str_table(grp, name, columns, rows)` —— 通用字符串列表写出

## 用法示例

```python
from eosop_pro.grid.unified_grid import build_all_grids
from eosop_pro.writer.h5_writer import write_material_h5

grids = build_all_grids(tables, A=26.98)   # 统一网格（rho_Te / nion_Te）
write_material_h5(
    "output/Al.h5",
    material={"material_name": "Al", "family": "hyades_eos"},
    tables=tables, grids=grids, A=26.98,
)
```
