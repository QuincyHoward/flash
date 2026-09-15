"""F6c —— Hugoniot 数据（``*.hug``）：**列名与单位写在注释行里**。

实测（``hyades/sesame/eos_41.hug``，157 行）::

    # Rho[g/cm^3]  T [eV]         P [Mbar]  E [erg/g]      Us [km/s]      Up [km/s]
    2.7059315e+000 2.6771096e-002 1.1245127e-002 3.9018342e+009 4.2385122e+000 ...

第 0 行是 ``#`` 注释，但**列名与单位都在方括号里** → 直接解析为轴/场的单位，
是"注释即证据"的又一例。列数由该行决定，payload 行必须同宽。
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.errors import CountMismatch, ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_column_header"]

FAMILY = "hugoniot"

#: ``Rho[g/cm^3]`` / ``T [eV]`` / ``Us [km/s]`` → (name, unit)
_COL_RE = re.compile(r"([A-Za-z][\w/()^.\-]*)\s*(?:\[([^\]]*)\])?")

#: ★ 第二种写法（实测于 ``mat_Al-1.0/Al.feos.hug``）：括号里带**缩放因子**，例如
#: ``Rho [1.000000e+000 g/cm^3]``、``P [1.000000e+012 dyne/cm^2]``。
#: 此时单位是数字之后的部分，那个数字是列值的缩放倍数。
_SCALE_UNIT_RE = re.compile(r"^\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)\s+(\S.*)$")


def parse_column_header(line: str) -> list[tuple[str, str]]:
    """从注释行解析 ``(列名, 单位)`` 列表。

    兼容两种写法：

    * ``Rho[g/cm^3]``            → ``("Rho", "g/cm^3")``
    * ``Rho [1.0e+000 g/cm^3]``  → ``("Rho", "g/cm^3")``（缩放因子被剥离）
    """
    body = line.lstrip("# \t")
    out: list[tuple[str, str]] = []
    for m in _COL_RE.finditer(body):
        name, unit = m.group(1), (m.group(2) or "")
        unit = unit.strip()
        if unit:
            sm = _SCALE_UNIT_RE.match(unit)
            if sm:
                # 带上缩放因子信息，避免丢失（用 "×N unit" 形式保留）；
                # 缩放因子数值化重排为 :.1e（2026-09-15 晚规约：图上数值
                # 一律 :.1e —— 文件头原文 1.000000e+005 太长，会原样进入
                # 图轴标签），非数值文本解析失败时回退原文
                try:
                    scale_txt = f"{float(sm.group(1)):.1e}"
                except ValueError:
                    scale_txt = sm.group(1)
                unit = f"{sm.group(2).strip()} (x{scale_txt})"
        if name:
            out.append((name.strip(), unit))
    return out


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = [ln for ln in doc.lines if ln.strip()]
    if len(lines) < 2:
        raise ParseError("hugoniot: too few non-blank lines", path=rel)

    cols = parse_column_header(lines[0])
    data_lines = [ln for ln in lines[1:] if not ln.lstrip().startswith("#")]
    rows = [fn.extract_numbers(ln) for ln in data_lines]
    rows = [r for r in rows if r]
    if not rows:
        raise ParseError("hugoniot: no numeric rows", path=rel)

    ncol = len(rows[0])
    if cols and len(cols) != ncol:
        # 注释行可能含额外文字；以数据列数为准并标注
        note_extra = f"注释行列数 {len(cols)} != 数据列数 {ncol}（以数据为准）"
        cols = cols[:ncol]
    else:
        note_extra = ""
    bad = [i for i, r in enumerate(rows) if len(r) != ncol]
    if bad:
        raise CountMismatch(len(rows) - len(bad), len(rows), path=rel,
                            header_raw=f"rows != {ncol} cols at {bad[:8]}")

    table = ParsedTable(
        table_key=f"HUGONIOT_{Path(rel).stem}",
        kind="HUGONIOT",
        family=FAMILY,
        source_relpath=rel,
        header_raw=lines[0],
        layout_rule=f"F6/hugoniot: 注释列头 + {len(rows)} 行 × {ncol} 列",
    )
    table.n_numbers_seen = len(rows) * ncol
    table.n_numbers_expected = len(rows) * ncol

    for j in range(ncol):
        if j < len(cols) and cols[j][0]:
            name, unit = cols[j]
        else:
            name, unit = f"col{j}", "unknown"
        table.fields[name] = [r[j] for r in rows]
        table.field_shape[name] = (len(rows),)
        table.field_units[name] = unit
        table.field_log10[name] = False
        if j == 0:
            table.axes[name] = [r[j] for r in rows]
            table.axis_units[name] = unit
            table.axis_log10[name] = False
            del table.fields[name]
    table.unit_source = "declared:inline (comment column header)"
    table.notes.append(f"列头(名,单位) = {cols}")
    if note_extra:
        table.notes.append(note_extra)
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
