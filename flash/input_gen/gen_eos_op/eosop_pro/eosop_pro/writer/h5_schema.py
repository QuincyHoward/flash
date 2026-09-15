"""HDF5 模式常量 —— ``/meta``、``/tables/<KIND>_<id>``、``native`` / ``unified`` 的路径与属性名。

模式（``schema_version = 1.0``）
--------------------------------
::

    /                              attrs: schema_version, tool_version, material_*, …
    /meta/sources                  [n_tables] 溯源表（每张表一行）
    /meta/annotations              [n_files]  注释证据
    /meta/units                    [k,3]      (quantity, unit, 来源)
    /meta/warnings                 [m]        全部告警（count_mismatch / unit_suspect / …）
    /meta/unified_grids/<gid>/     attrs: x_axis, x_min, x_max, n_x, Te_min_eV, …
    /meta/zeff_sources             [n_z]      Z̄ 来源

    /tables/<KIND>_<key>/          attrs: quantity_kind, family, table_id, …
        native/                    **轨道 1**：原生网格逐字保留
        unified/<gid>/             **轨道 2**：统一网格插值

统一约定
--------
* 物理量一律 ``float64``；2D 场轴序固定 ``(n_Te, n_x)``。
* ``gzip level=4 + shuffle``；2D/3D 显式 ``chunks``；1D 轴不压缩。
* NaN 只表示"落在原生凸包之外"（``nan_semantics="out_of_range"``）。
"""

from __future__ import annotations

import numpy as np

from .. import config

__all__ = [
    "META", "TABLES", "NATIVE", "UNIFIED", "SOURCES_COLUMNS",
    "ZEFF_COLUMNS", "dtype_f8", "str_dtype", "scalar_attrs",
    "vector_attrs", "open_mode",
]

META = "meta"
TABLES = "tables"
NATIVE = "native"
UNIFIED = "unified"

#: ``/meta/sources`` 的列（顺序即写盘顺序）
SOURCES_COLUMNS = (
    "table_key", "kind", "family", "source_relpath", "declared_type",
    "inferred_type", "type_agreement", "dispatch_rule", "status", "sha256",
    "n_numbers_actual", "n_numbers_expected", "nr", "nt", "n_groups",
    "layout_rule", "unit_source", "field_width", "encoding_used",
    "newline_style",
)

#: ``/meta/zeff_sources`` 的列
ZEFF_COLUMNS = ("relpath", "kind", "family", "units_T", "unit_source",
                "grid", "unit_suspect")

#: 每张表都要带的属性（缺了会被 ``test_h5_schema`` 挑出来）
REQUIRED_TABLE_ATTRS = (
    "quantity_kind", "family", "source_relpath", "table_key",
)

#: 每个 1D 轴数据集都要带的属性
REQUIRED_AXIS_ATTRS = ("units", "log10", "axis")

#: 每个场数据集都要带的属性
REQUIRED_FIELD_ATTRS = ("units", "log10")


def dtype_f8():
    return np.dtype(config.FLOAT_DTYPE)


def str_dtype():
    """变长 UTF-8 字符串 dtype（h5py）。"""
    import h5py
    return h5py.string_dtype(encoding="utf-8")


def scalar_attrs(**kwargs):
    """规范化属性字典：``None`` 丢弃、``bool`` 保留、其余原样。"""
    out = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        if isinstance(v, (bool, int, float, str, np.generic)):
            out[k] = v.item() if isinstance(v, np.generic) else v
        elif isinstance(v, dict):
            out[k] = ", ".join(f"{kk}={vv}" for kk, vv in v.items())
        elif isinstance(v, (list, tuple)):
            out[k] = ", ".join(str(x) for x in v)
        else:
            out[k] = str(v)
    return out


def vector_attrs(d: dict) -> dict:
    """把 ``{k: v}`` 展平成 ``k_v`` 形式（供 axis/field 的 units/log10 批量写）。"""
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                out[f"{k}_{kk}"] = vv
    return out


def open_mode(path: str, mode: str = "w"):
    """统一入口，便于后续切换压缩/驱动。"""
    import h5py
    return h5py.File(path, mode)
