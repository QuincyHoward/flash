"""F5b —— LEDCOP 拆分件（``*.NoFree`` / ``*.AvSqFree``）解析器。

这些是 ``ATOMIC/<El>.txt`` 主表的**预拆分**版本，结构极简（4 数头 + 3 段）::

    <魔数 0.1234567E+000>  <1.0>  NR  NT
    [log10 rho (NR)] [log10 T (NT)] [值 (NR*NT)]

**计数守恒**：``4 + NR + NT + NR*NT``

====================  ============================================
文件                   值字段含义
====================  ============================================
``*.NoFree``          自由电子数（Z̄ 等价量）
``*.AvSqFree``        自由电子数平方均值（Z² 等价量）
====================  ============================================

单位：rho log10 g/cm3；**T log10 keV**（由 ``ATOMIC/*.txt`` 的内嵌声明
``Opacities in cm**2/gm, T in keV, density in gm/cc`` 佐证）。

实测基准：``ATOMIC/Al.NoFree`` → NR=50, NT=69, 总数 **3573** = 4+50+69+3450。
"""

from __future__ import annotations

from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.errors import CountMismatch, ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "LEDCOP_MAGIC"]

FAMILY = "ledcop_zeff"

#: LEDCOP 魔数（实测 ``0.1234567E+000``）
LEDCOP_MAGIC = 0.1234567


def _field_for(rel: str) -> tuple[str, str]:
    base = Path(rel).name.lower()
    if base.endswith(".avsqfree") or "avsqfree" in base:
        return "Z2", "ZEFF2"
    if base.endswith(".nofree") or "nofree" in base:
        return "Z", "ZEFF"
    return "Z", "ZEFF"


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = [ln for ln in doc.lines if ln.strip()]
    if len(lines) < 2:
        raise ParseError("file too short for LEDCOP split table", path=rel)

    hdr = fn.extract_numbers(lines[0])
    if len(hdr) != 4:
        raise ParseError(f"LEDCOP header must have 4 numbers, got {len(hdr)}",
                         path=rel, header_raw=doc.lines[0])
    nr, nt = int(round(hdr[2])), int(round(hdr[3]))
    if not (2 <= nr <= 50000 and 2 <= nt <= 50000):
        raise ParseError(f"LEDCOP implausible dims nr={nr} nt={nt}",
                         path=rel, header_raw=doc.lines[0])

    values = fn.extract_numbers("\n".join(lines[1:]))
    expected = 4 + nr + nt + nr * nt
    if 4 + len(values) != expected:
        raise CountMismatch(4 + len(values), expected, path=rel, header_raw=doc.lines[0])

    log_rho = values[:nr]
    log_T_keV = values[nr:nr + nt]
    flat = values[nr + nt:]

    field, kind = _field_for(rel)
    magic_ok = abs(hdr[0] - LEDCOP_MAGIC) < 1e-6

    table = ParsedTable(
        table_key=f"{kind}_{Path(rel).stem}",
        kind=kind,
        family=FAMILY,
        source_relpath=rel,
        header_raw=doc.lines[0],
        layout_rule="F5/LEDCOP-split: 4 + nr + nt + nr*nt",
    )
    table.n_numbers_seen = 4 + len(values)
    table.n_numbers_expected = expected

    table.axes["rho"] = [10.0 ** x for x in log_rho]
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = True
    unit = (unit_hint_T or "keV").lower()
    scale = {"ev": 1.0, "kev": 1e3}.get(unit, 1e3)
    table.axes["Te"] = [(10.0 ** x) * scale for x in log_T_keV]
    table.axis_units["Te"] = "eV"
    table.axis_log10["Te"] = True

    table.fields[field] = flat
    table.field_shape[field] = (nt, nr)
    table.field_units[field] = "1"
    table.field_log10[field] = False

    table.unit_source = f"declared:{unit_hint_T}" if unit_hint_T else "format:T in keV"
    if magic_ok:
        table.notes.append(f"LEDCOP 魔数匹配 ({hdr[0]:.7g})")
    else:
        table.notes.append(f"⚠️ 首字段 {hdr[0]:.7g} 与 LEDCOP 魔数 {LEDCOP_MAGIC} 不符")
    table.notes.append("字段含义来自文件名 token（NoFree=自由电子数 / AvSqFree=其平方均值）")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
