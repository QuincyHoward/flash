"""``/meta`` 组织 —— 溯源表（每个结论都可追到具体文件与字段）。"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np

from .. import config, reporting
from . import h5_schema as S

__all__ = ["write_root_attrs", "write_sources", "write_units", "write_warnings",
           "write_annotations", "write_unified_grid_meta", "write_zeff_sources",
           "write_str_table"]


def write_str_table(grp, name: str, columns: Sequence[str], rows: Sequence[dict]):
    """写一张「字符串列」表。

    ``{name}.attrs['columns']`` 存列名；数据集本体是 ``[n_rows, n_cols]`` 的
    变长 UTF-8 字符串数组（用 object 数组 + ``string_dtype`` 构造，避免 numpy
    把字符串截断成定长字节串）。
    """
    cols = list(columns)
    if not rows:
        arr = np.empty((0, len(cols)), dtype=object)
    else:
        arr = np.empty((len(rows), len(cols)), dtype=object)
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                arr[i, j] = _cell(r.get(c))
    ds = grp.create_dataset(name, data=arr, dtype=S.str_dtype())
    ds.attrs["columns"] = ", ".join(cols)
    return ds


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        return " ;; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return " ;; ".join(f"{k}={vv}" for k, vv in v.items())
    return str(v)


def write_root_attrs(f, *, material: dict, extra: dict | None = None) -> None:
    """写文件根属性。"""
    a = {
        "schema_version": config.SCHEMA_VERSION,
        "tool_version": config.TOOL_VERSION,
        "generated_utc": reporting.utc_now(),
        "grid_convention": "axis_order=['Te_eV','x']; NaN=out_of_range",
        "nan_semantics": config.NAN_SEMANTICS,
    }
    a.update({k: v for k, v in (material or {}).items() if v is not None})
    a.update(extra or {})
    for k, v in S.scalar_attrs(**a).items():
        f.attrs[k] = v


def _meta(f):
    return f.require_group(S.META)


def write_sources(f, rows: Iterable[dict]) -> None:
    write_str_table(_meta(f), "sources", S.SOURCES_COLUMNS, list(rows))


def write_units(f, rows: Iterable[dict]) -> None:
    """``(quantity, unit, source, evidence)`` 四列。"""
    write_str_table(_meta(f), "units", ("quantity", "unit", "source", "evidence"),
                    list(rows))


def write_warnings(f, warnings: Iterable[str]) -> None:
    grp = _meta(f)
    arr = np.array([str(w) for w in warnings], dtype=object)
    grp.create_dataset("warnings", data=arr, dtype=S.str_dtype())


def write_annotations(f, rows: Iterable[dict]) -> None:
    cols = ("source", "kind", "material_name", "material_z", "material_a",
            "composition", "provenance", "dims", "units", "table_ids",
            "file_unit_hints", "group_scheme", "powerlaw", "notes")
    write_str_table(_meta(f), "annotations", cols, list(rows))


def write_unified_grid_meta(f, grids: dict[str, Any]) -> None:
    grp = _meta(f).require_group("unified_grids")
    for gid, g in grids.items():
        sub = grp.require_group(gid)
        for k, v in S.scalar_attrs(**g.attrs).items():
            sub.attrs[k] = v


def write_zeff_sources(f, rows: Iterable[dict]) -> None:
    write_str_table(_meta(f), "zeff_sources", S.ZEFF_COLUMNS, list(rows))
