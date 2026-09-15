"""F6b —— 冷不透明度（``*.coldopacity``）：**两行自描述表头**。

实测（``ColdOpacity/Al.coldopacity``，67 个同类文件）::

    Eph	miu          <- 第 1 行：列名（制表符分隔）
    eV	cm2/g        <- 第 2 行：**逐列单位**（制表符分隔）
    <空行>
    10	486606.52638
    10.1617	469396.24406

这是全库最直白的**单位声明**——列名与单位各占一行、按列对齐。
本解析器把这两行解析为 ``column_names`` 与 ``column_units``，
数值区按列拆成独立的 ``fields``。

另有 ``hyades/coldopac.dat`` 用另一套写法（``c`` 开头注释 + ``z = N`` + 点数列）。
"""

from __future__ import annotations

from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.errors import CountMismatch, ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_two_line_header"]

FAMILY = "coldopacity"


def parse_two_line_header(lines: list[str]) -> tuple[list[str], list[str], int]:
    """解析「列名 / 单位」两行表头，返回 ``(names, units, payload_start)``。"""
    idx = [i for i, ln in enumerate(lines[:6]) if ln.strip()]
    if len(idx) < 2:
        raise ParseError("coldopacity: fewer than 2 non-blank header lines")
    i, j = idx[0], idx[1]
    names = [t for t in lines[i].split() if t]
    units = [t for t in lines[j].split() if t]
    if len(names) != len(units):
        raise ParseError(
            f"coldopacity: column count mismatch names={names} units={units}"
        )
    return names, units, j + 1


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    names, units, start = parse_two_line_header(doc.lines)
    ncol = len(names)

    rows: list[list[float]] = []
    n_blank = 0
    for ln in doc.lines[start:]:
        if not ln.strip():
            n_blank += 1
            continue
        vals = fn.extract_numbers(ln)
        if vals:
            rows.append(vals)
    if not rows:
        raise ParseError("coldopacity: no numeric rows", path=rel)

    bad = [i for i, r in enumerate(rows) if len(r) != ncol]
    if bad:
        raise CountMismatch(len(rows) - len(bad), len(rows), path=rel,
                            header_raw=f"rows with != {ncol} cols at {bad[:8]}")

    table = ParsedTable(
        table_key=f"COLDOPACITY_{Path(rel).stem}",
        kind="COLDOPACITY",
        family=FAMILY,
        source_relpath=rel,
        header_raw=doc.lines[0] + " | " + doc.lines[1],
        layout_rule=f"F6/coldopacity: 2 行自描述表头 + {len(rows)} 行 × {ncol} 列",
    )
    table.n_numbers_seen = len(rows) * ncol
    table.n_numbers_expected = len(rows) * ncol

    # 第一列作 x 轴，其余作物理量场
    table.axes[names[0]] = [r[0] for r in rows]
    table.axis_units[names[0]] = units[0]
    table.axis_log10[names[0]] = False
    for j, nm in enumerate(names[1:], start=1):
        table.fields[nm] = [r[j] for r in rows]
        table.field_shape[nm] = (len(rows),)
        table.field_units[nm] = units[j]
        table.field_log10[nm] = False
    table.unit_source = "declared:inline (2-line header)"
    table.notes.append(f"列名={names} 单位={units}（文件内嵌声明）")
    table.notes.append(f"n_blank={n_blank}")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
