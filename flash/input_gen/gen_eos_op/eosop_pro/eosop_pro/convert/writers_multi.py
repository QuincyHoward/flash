"""MULTI / Hyades / SESAME 格式的写出器 —— 各解析器的**逆变换**。

逆变换必须与正向格式严格一致，故每一条都对照**权威参考实现**：

* ``matlab/outputMULTIOpacity.m`` —— F2 的列宽（``%15.7e``×4）、log10 用法、
  ``keV→eV`` ×1000、以及 ``kappa`` 的 **T-major** 展平顺序
* ``matlab/outputHyadesEOS.m``   —— F3 的 ``%15.8e``×5、``L=2+nr+nt+2·nr·nt``、
  ``T`` 以 **keV** 写出、``P``/``E`` 的 T-major 展平顺序
* F1 解析器 + ``doc/MULTI使用的SESAME数据文件格式.docx`` —— 4 数头 + 段顺序

换行：实测 ``mat_*``（MULTI 族）是 **LF**，``hyades/*`` 是 **CRLF**；
MATLAB 写出器一律用 ``\\r\\n``。故本模块按目标族给出默认值，并可覆盖。
"""

from __future__ import annotations

import math
from pathlib import Path

from .. import config
from ..parsers.base import ParsedTable

__all__ = [
    "write_multi_opacity", "write_hyades_eos", "write_multi_inverted_eos",
    "fmt15", "fmt16", "dump_values",
]


def _invert_to_te(table: ParsedTable):
    """把 F1（``de`` 基）表反演到 ``(rho, Te)``，返回一张新的 ``ParsedTable``。

    目标 Te 轴：取源 ``T`` 场的正区间，**点数与 ``ne`` 相同**、log10 等距。
    """
    from ..grid.monotonic import make_log_uniform
    from .invert_eos import to_Te_grid

    shape = table.field_shape.get("T")
    if not shape or len(shape) != 2:
        raise ValueError("invert requires a 2-D 'T' field")
    ne, nr = shape
    T = [v for v in table.fields["T"] if v == v and v > 0]
    if len(T) < 2:
        raise ValueError("invert requires positive T values")
    Te_axis = make_log_uniform(min(T), max(T), max(2, ne))
    res = to_Te_grid(table, Te_axis, fields=("P", "E", "T"), log_value=("T",))

    from ..parsers.base import ParsedTable as _PT
    new = _PT(
        table_key=f"{table.table_key}_on_Te",
        kind=table.kind, family=table.family,
        source_relpath=table.source_relpath, table_id=table.table_id,
        sesame_digit=table.sesame_digit,
        header_raw=table.header_raw,
        layout_rule=f"{table.layout_rule} + invert(rho,de)->(rho,Te)",
        unit_source="inverted",
        notes=list(table.notes) + [
            f"由 (rho,de) 反演得到；目标 Te 轴 log10 等距 {len(Te_axis)} 点",
            *res.notes,
        ],
    )
    new.axes["rho"] = list(res.rho)
    new.axes["Te"] = list(res.Te)
    new.axis_units["rho"] = table.axis_units.get("rho", "g/cm3")
    new.axis_units["Te"] = "eV"
    for nm, arr in res.fields.items():
        new.fields[nm] = [float(x) for x in arr.reshape(-1)]
        new.field_shape[nm] = (arr.shape[0], arr.shape[1])
        new.field_units[nm] = "Mbar" if nm == "P" else (
            "Mbar*cm3/g" if nm == "E" else "eV")
    new.n_numbers_seen = sum(len(v) for v in new.fields.values())
    new.n_numbers_expected = new.n_numbers_seen
    return new


def fmt15(v: float) -> str:
    """Fortran/C 风格 15 字符科学计数（对应 ``%15.8e``）。"""
    if v != v or v in (float("inf"), float("-inf")):
        return f"{v:>15}".replace("inf", "1.#INF")[:15].rjust(15)
    return f"{v:15.8e}"

def fmt16(v: float) -> str:
    return f"{v:16.8e}"


def dump_values(path: Path, values, *, per_line: int = 4, fmt=fmt15,
                newline: str = "\n") -> None:
    """按定宽多列写数值（每行 ``per_line`` 个）。"""
    buf: list[str] = []
    for i, v in enumerate(values):
        buf.append(fmt(v))
        if (i + 1) % per_line == 0:
            buf.append(newline)
    if len(values) % per_line:
        buf.append(newline)
    path.write_text("".join(buf), encoding="utf-8", newline="")


def _log10(v: float) -> float:
    return math.log10(v) if v > 0 else float("nan")


# ── F2：不透明度 / Zeff / EPS ───────────────────────────────────
def write_multi_opacity(table: ParsedTable, out_path: Path, *,
                        field: str | None = None,
                        newline: str = "\n") -> Path:
    """逆变换 F2（支持灰度与多群子表串联）。"""
    rho = table.axes["rho"]
    Te = table.axes["Te"]
    nr, nt = len(rho), len(Te)
    fname = field or ("kappa_g" if "kappa_g" in table.fields else
                      ("kappa" if "kappa" in table.fields else
                       next(iter(table.fields))))
    flat = table.fields[fname]
    shape = table.field_shape[fname]
    ng = 1 if len(shape) == 2 else shape[0]
    t_log = [_log10(x) for x in Te]
    r_log = [_log10(x) for x in rho]

    head_id = table.table_id or 0
    enum_or_label = table.f2_or_label
    per_grid = nr * nt

    lines: list[str] = []
    bounds = table.group_bounds or []
    for g in range(ng):
        # 子表头：id + （类型枚举 或 文本标签）+ nr + nt
        if enum_or_label is not None and not _is_num(enum_or_label):
            head = f"{fmt15(float(head_id))}{_pad_label(str(enum_or_label))}"
        else:
            head = f"{fmt15(float(head_id))}{fmt15(float(enum_or_label or 0.0))}"
        lines.append(head + fmt15(float(nr)) + fmt15(float(nt)) + newline)
        if ng > 1 and bounds:
            lo = bounds[g] if g < len(bounds) else float("nan")
            hi = bounds[g + 1] if g + 1 < len(bounds) else float("nan")
            lines.append(fmt15(lo) + fmt15(hi) + newline)
        seg = flat[g * per_grid:(g + 1) * per_grid] if ng > 1 else flat
        # 每个子表自带网格（与实测的多群结构一致）
        lines.extend(_dump_lines(r_log, newline))
        lines.extend(_dump_lines(t_log, newline))
        # ★ F2 的 kappa 在表里**本身就是 log10 值**（``field_log10=True``），
        #   所以直接写、**不能再取一次 log10**（否则会把值写坏）。
        lines.extend(_dump_lines(seg, newline, log_value=False))
    out_path.write_text("".join(lines), encoding="utf-8", newline="")
    return out_path


def _is_num(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _pad_label(lbl: str) -> str:
    return f"{lbl:<15}"


def _dump_lines(values, newline: str, *, log_value: bool = False,
                per_line: int = 4) -> list[str]:
    out: list[str] = []
    buf = ""
    for i, v in enumerate(values):
        x = _log10(v) if log_value else v
        buf += fmt15(x)
        if (i + 1) % per_line == 0:
            out.append(buf + newline)
            buf = ""
    if buf:
        out.append(buf + newline)
    return out


# ── F3：Hyades / SESAME ────────────────────────────────────────
def write_hyades_eos(table: ParsedTable, out_path: Path, *,
                     zbar: float = 1.0, abar: float = 1.0, rho0: float = 1.0,
                     comment: str | None = None, newline: str = "\r\n",
                     invert: bool = False) -> Path:
    """逆变换 F3：``L = 2 + nr + nt + 2*nr*nt``，T 以 **keV** 写出。

    ``invert=True``：若源表是 F1 的 ``(rho, de)`` 基（无 ``Te`` 轴），
    先用 :func:`eosop_pro.convert.invert_eos.to_Te_grid` 反演到 ``(rho, Te)``
    再写。目标 Te 轴取源 T 场的范围、点数与 ``ne`` 相同（log10 等距）——
    这是**显式的约定**，会在 ``comment`` 里注明。
    """
    if "Te" not in table.axes:
        if not invert:
            raise ValueError(
                "hyades writer requires a 'Te' axis; 源表是 (rho,de) 基 → "
                "请传 invert=True，或先经 convert.invert_eos.to_Te_grid"
            )
        table = _invert_to_te(table)
    rho = table.axes["rho"]
    Te = table.axes.get("Te")
    if Te is None:
        raise ValueError("hyades writer requires a 'Te' axis")
    nr, nt = len(rho), len(Te)
    if "P" not in table.fields:
        raise ValueError(f"hyades writer requires field 'P'; have {sorted(table.fields)}")
    if "E" not in table.fields:
        raise ValueError(f"hyades writer requires field 'E'; have {sorted(table.fields)}")

    P = table.fields["P"]
    E = table.fields["E"]
    T_keV = [t * config.KEV_PER_EV for t in Te]
    L = 2 + nr + nt + 2 * nr * nt

    head = (comment or f"{table.table_key} regenerated by eosop_pro "
                       f"(from {table.source_relpath})")
    lines = [head + newline,
             f"{int(table.table_id or 0):>6}{zbar:15.8e}{abar:15.8e}{rho0:15.8e}{L:>8}" + newline]
    body: list[float] = [float(nr), float(nt)]
    body += list(rho)
    body += list(T_keV)
    body += list(P)     # T-major（与解析器的 field_shape=(nt,nr) 行主序一致）
    body += list(E)
    lines.extend(_dump_lines(body, newline, per_line=5))
    out_path.write_text("".join(lines), encoding="utf-8", newline="")
    return out_path


# ── F1：反演 EOS ───────────────────────────────────────────────
def write_multi_inverted_eos(table: ParsedTable, out_path: Path, *,
                             newline: str = "\n") -> Path:
    """逆变换 F1：有 ``e0_cold`` 则写 ``with_e0`` 布局，否则 ``no_e0``。"""
    if "de" not in table.axes:
        raise ValueError("F1 writer requires a 'de' axis")
    rho = table.axes["rho"]
    de = table.axes["de"]
    nr, ne = len(rho), len(de)
    P = table.fields["P"]
    T = table.fields.get("T")
    if T is None:
        raise ValueError("F1 writer requires field 'T'")
    T_K = [t / config.EV_PER_K for t in T]

    lines = [f"{fmt15(float(table.table_id or 0))}{fmt15(0.0)}"
             f"{fmt15(float(nr))}{fmt15(float(ne))}" + newline]
    body: list[float] = list(rho) + list(de)
    if "e0_cold" in table.fields:
        body += list(table.fields["e0_cold"])
    body += list(P)
    body += T_K
    lines.extend(_dump_lines(body, newline, per_line=4))
    out_path.write_text("".join(lines), encoding="utf-8", newline="")
    return out_path
