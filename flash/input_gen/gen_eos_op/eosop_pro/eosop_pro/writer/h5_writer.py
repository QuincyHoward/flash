"""HDF5 双轨写出器。

**轨道 1 ``native/``** —— 原生网格逐字保留（含单位与 log10 标记属性），
使任何人可逐点核对回源文件。

**轨道 2 ``unified/<gid>/``** —— 插值到统一网格（本轮两套：``rho_Te`` / ``nion_Te``）。
轴序固定 ``(n_Te, n_x)``；越界写 NaN，并把越界计数写进属性。

★ 两处关键正确性细节
--------------------
1. ``nion_Te`` 的 x 轴是 ``n_ion``，而源表的 x 轴是 ``rho``（g/cm³）——
   插值前**必须把源 x 也做同样变换**（``rho → n_ion``），否则等于拿两把不同的尺子量。
2. F1（``de`` 基）的表要先经 :func:`eosop_pro.convert.invert_eos.to_Te_grid`
   反演成 ``(rho, Te)``，再统一插值 —— 这是格式转换接口的一个实际用例。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from .. import config
from ..grid import interpolate as interp
from ..grid.unified_grid import UnifiedGrid, x_from_rho
from ..parsers.base import ParsedTable
from . import h5_schema as S
from . import provenance as prov

__all__ = ["write_material_h5", "write_table_group", "write_native", "write_unified"]

_CHUNK = config.H5_CHUNK_MAX


def _mk_kwargs(shape: tuple[int, ...], *, compress: bool = True) -> dict:
    kw: dict[str, Any] = {}
    if compress and len(shape) >= 2:
        kw.update(compression=config.H5_COMPRESSION,
                  compression_opts=config.H5_COMPRESSION_OPTS,
                  shuffle=config.H5_SHUFFLE)
        kw["chunks"] = tuple(min(s, _CHUNK) if s > 1 else 1 for s in shape)
    return kw


def write_native(grp, table: ParsedTable) -> None:
    """写原生轨（轴 + 场），逐字保留。"""
    for name in sorted(table.axes):
        ax = np.asarray(table.axes[name], dtype=float)
        ds = grp.create_dataset(name, data=ax)
        ds.attrs["units"] = table.axis_units.get(name, "unknown")
        ds.attrs["log10"] = bool(table.axis_log10.get(name, False))
        ds.attrs["axis"] = True
        ds.attrs["n"] = int(ax.size)

    for name in sorted(table.fields):
        flat = np.asarray(table.fields[name], dtype=float)
        shape = tuple(table.field_shape.get(name, (flat.size,)))
        arr = flat.reshape(shape)
        ds = grp.create_dataset(name, data=arr, **_mk_kwargs(arr.shape))
        ds.attrs["units"] = table.field_units.get(name, "unknown")
        ds.attrs["log10"] = bool(table.field_log10.get(name, False))
        ds.attrs["axis"] = False
        ds.attrs["shape"] = str(shape)


def _source_2d(table: ParsedTable, field: str):
    """取出 ``(rho_src, Te_src, arr2d_physical, log_value)``；不适用则 ``None``。

    ★ ``field_log10=True`` 表示**表里存的就是 log10 值** ——
    这里先还原成物理量，并把 ``log_value=True`` 一并返回，供插值在 log 空间进行。
    否则会出现"对已经是 log10 的值再取 log10"的经典错误（负值直接变 NaN）。
    """
    shape = table.field_shape.get(field)
    if not shape or len(shape) != 2:
        return None
    if "rho" not in table.axes or "Te" not in table.axes:
        return None
    if tuple(shape) != (len(table.axes["Te"]), len(table.axes["rho"])):
        return None
    arr = np.asarray(table.fields[field], dtype=float).reshape(shape)
    is_log = bool(table.field_log10.get(field, False))
    if is_log:
        with np.errstate(over="ignore", invalid="ignore"):
            arr = np.power(10.0, arr)
    return (np.asarray(table.axes["rho"], dtype=float),
            np.asarray(table.axes["Te"], dtype=float),
            arr, is_log)


def _write_unified_from_te_table(sub, table: ParsedTable, g: UnifiedGrid,
                                 A: float | None) -> int:
    """源表已是 ``(rho, Te)`` 形态：直接做 x 变换 + 双线性。"""
    sub.create_dataset("x", data=np.asarray(g.x, dtype=float))
    sub.create_dataset("Te", data=np.asarray(g.Te, dtype=float))
    n_oor = 0
    for field in sorted(table.fields):
        got = _source_2d(table, field)
        if got is None:
            continue
        rho_src, Te_src, arr, log_v = got
        # ★ 源 x 必须做与目标 x 相同的变量变换，否则 nion_Te 轨会错
        x_src = np.array([x_from_rho(g.gid, r, A) for r in rho_src], dtype=float)
        res = interp.resample_2d(x_src, Te_src, arr,
                                 np.asarray(g.x, dtype=float),
                                 np.asarray(g.Te, dtype=float),
                                 logs=("x", "y"), log_value=log_v)
        ds = sub.create_dataset(field, data=res.values, **_mk_kwargs(res.values.shape))
        ds.attrs["units"] = table.field_units.get(field, "unknown")
        ds.attrs["log10"] = False
        ds.attrs["interp_method"] = config.INTERP_METHOD
        ds.attrs["extrapolation"] = res.extrapolation
        ds.attrs["out_of_range_count"] = res.out_of_range
        ds.attrs["coverage"] = round(res.coverage, 6)
        n_oor += res.out_of_range
    return n_oor


def _write_unified_from_de_table(sub, table: ParsedTable, g: UnifiedGrid) -> int:
    """F1（``de`` 基）：先反演到 ``(rho, Te)`` 再落盘。"""
    from ..convert.invert_eos import to_Te_grid

    res = to_Te_grid(table, list(g.Te), fields=("P", "E", "T"), log_value=("T",))
    sub.create_dataset("x", data=np.asarray(g.x, dtype=float))
    sub.create_dataset("Te", data=np.asarray(g.Te, dtype=float))
    rho_axis = np.asarray(table.axes["rho"], dtype=float)
    sub.create_dataset("rho_of_x", data=rho_axis)
    n_oor = 0
    for nm, arr in res.fields.items():
        ds = sub.create_dataset(nm, data=arr, **_mk_kwargs(arr.shape))
        ds.attrs["units"] = table.field_units.get(nm, "unknown")
        ds.attrs["log10"] = False
        ds.attrs["origin"] = "inverted-from-(rho,de)"
        n_oor += int(np.isnan(arr).sum())
    sub.attrs["interp_method"] = "invert-(rho,de)->(rho,Te) + log10-bilinear"
    return n_oor


def write_unified(f, table: ParsedTable, grids: dict[str, UnifiedGrid],
                  *, A: float | None = None,
                  skip_inverted_eos: bool = False,
                  key_override: str | None = None) -> dict[str, int]:
    """写统一轨；返回 ``{gid: 越界点总数}``（``-1`` 表示整轨跳过）。

    ``key_override`` 见 :func:`write_table_group` —— 同键多表必须用同一个
    去重后的键，否则两张表的 ``unified`` 轨会撞进同一个组。
    """
    key = key_override or table.table_key
    base = f.require_group(f"{S.TABLES}/{key}/{S.UNIFIED}")
    is_de_based = "de" in table.axes and "Te" not in table.axes
    if is_de_based and skip_inverted_eos:
        return {"_skipped": -1}

    stats: dict[str, int] = {}
    for gid, g in grids.items():
        sub = base.require_group(gid)
        if is_de_based:
            n_oor = _write_unified_from_de_table(sub, table, g)
            note = "invert-(rho,de)->(rho,Te) + log10-bilinear"
        else:
            n_oor = _write_unified_from_te_table(sub, table, g, A)
            note = config.INTERP_METHOD
        sub.attrs["interp_method"] = note
        sub.attrs["extrapolation"] = config.EXTRAPOLATION
        sub.attrs["out_of_range_count"] = n_oor
        sub.attrs["x_axis"] = g.x_axis
        if A is not None:
            sub.attrs["A_amu"] = float(A)
        stats[gid] = n_oor
    if not stats:
        return {}
    return stats


def write_table_group(f: Any, table: ParsedTable,
                      grids: dict[str, UnifiedGrid] | None = None,
                      *, A: float | None = None,
                      native_track: bool = True,
                      key_override: str | None = None) -> dict[str, int]:
    """写一张表（``native`` + 可选 ``unified``）。

    ``native_track=False`` 时只写统一轨（用于"只要插值结果"的场景）；
    两轨都关掉是没有意义的，调用方需保证至少开一轨。

    ``key_override``：★ 用于**同一文件含多张同键表**的情形。
    实测 ``mat_Al-1.0/Al_etc.dat`` 含 2 个 F2 多群块，两者的 SESAME id 都是
    ``00000000`` → ``table_key`` 都是 ``MUGROUP_0``。若不做区分，
    第二次 ``create_dataset`` 会抛
    ``ValueError: Unable to synchronously create dataset (name already exists)``
    （实测导致 ``convert-all`` 有 1 个 write_failed）。
    """
    key = key_override or table.table_key
    g = f.require_group(f"{S.TABLES}/{key}")
    attrs = S.scalar_attrs(
        table_key=table.table_key, quantity_kind=table.kind, family=table.family,
        source_relpath=table.source_relpath, table_id=table.table_id,
        sesame_digit=table.sesame_digit, f2_or_label=table.f2_or_label,
        header_raw=table.header_raw, layout_rule=table.layout_rule,
        unit_source=table.unit_source, n_groups=table.n_groups,
        n_native_x=table.nr, n_native_Te=table.nt,
        n_numbers_seen=table.n_numbers_seen,
        n_numbers_expected=table.n_numbers_expected,
        axis_order="['Te_eV','x']",
    )
    for k, v in attrs.items():
        g.attrs[k] = v
    if key != table.table_key:
        g.attrs["group_key_disambiguated_from"] = table.table_key
    for k, v in table.axis_units.items():
        g.attrs[f"native_units_{k}"] = v
    for k, v in table.field_units.items():
        g.attrs[f"native_units_{k}"] = v
    if table.notes:
        g.attrs["notes"] = " ;; ".join(table.notes[:20])
    if table.group_bounds:
        ds = g.create_dataset("group_bounds_eV",
                              data=np.asarray(table.group_bounds, dtype=float))
        ds.attrs["units"] = "eV"
        ds.attrs["axis"] = True

    if native_track:
        write_native(g.require_group(S.NATIVE), table)
    g.attrs["has_native_track"] = bool(native_track)
    stats: dict[str, int] = {}
    if grids:
        # ★ 必须把 key_override 传下去 —— write_unified 自己会算
        #   ``/tables/<key>/unified`` 路径；不传的话同键多表会撞进同一个组。
        stats = write_unified(f, table, grids, A=A, key_override=key)
        g.attrs["has_unified_track"] = bool(stats)
    return stats


def write_material_h5(out_path: str | Path, *,
                      material: dict,
                      tables: Sequence[ParsedTable],
                      grids: dict[str, UnifiedGrid] | None = None,
                      A: float | None = None,
                      sources: Iterable[dict] = (),
                      units: Iterable[dict] = (),
                      warnings: Iterable[str] = (),
                      annotations: Iterable[dict] = (),
                      zeff_sources: Iterable[dict] = (),
                      native_track: bool = True,
                      extra_root_attrs: dict | None = None) -> Path:
    """写一个材料的 ``.h5``（双轨）。返回文件路径。

    ``native_track=False`` → 只有 ``unified/<gid>``；
    ``grids=None`` → 只有 ``native``。两轨都关会被显式拒绝（写出来的东西没有意义）。

    ★ 同一文件里出现**同键多表**时自动去重（``_b2`` / ``_b3`` …），
    并把原名写进 ``group_key_disambiguated_from`` 属性。
    实测 ``mat_Al-1.0/Al_etc.dat`` 含 2 个 SESAME id 都是 ``00000000`` 的
    F2 多群块 → 键都是 ``MUGROUP_0``。
    """
    if not native_track and not grids:
        raise ValueError(
            "write_material_h5: native_track=False 且 grids=None —— 两轨都关会写出空文件")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # ★ 同键去重（顺序敏感：第一张保持原名，其后加 _bN）
    seen: dict[str, int] = {}
    keys: list[str] = []
    for tb in tables:
        n = seen.get(tb.table_key, 0) + 1
        seen[tb.table_key] = n
        keys.append(tb.table_key if n == 1 else f"{tb.table_key}_b{n}")
    n_dup = sum(1 for v in seen.values() if v > 1)
    with S.open_mode(out, "w") as f:
        prov.write_root_attrs(f, material=material, extra=extra_root_attrs)
        f.attrs["native_track"] = bool(native_track)
        f.attrs["unified_track"] = bool(grids)
        f.attrs["n_duplicate_table_keys"] = n_dup
        if n_dup:
            f.attrs["duplicate_table_keys"] = " ;; ".join(
                k for k, v in seen.items() if v > 1)
        if grids:
            prov.write_unified_grid_meta(f, grids)
        for tb, key in zip(tables, keys):
            write_table_group(f, tb, grids, A=A, native_track=native_track,
                              key_override=key)
        prov.write_sources(f, sources)
        prov.write_units(f, units)
        prov.write_warnings(f, warnings)
        prov.write_annotations(f, annotations)
        prov.write_zeff_sources(f, zeff_sources)
        f.attrs["n_tables"] = len(tables)
    return out
