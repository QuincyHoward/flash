"""F6e —— FEOS 辅助文件（``*.PAR`` / ``*.cst`` / ``*.mexport`` / ``*.critical.dat`` / ``*.isobaric.dat`` / ``*.INV``）。

这些是 FEOS/ShowEOS 的**参数与导出**文件，不是标准表格。共同特征:

* 分节标题（如 ``Q-table`` / ``Material-7386:``）
* ``key = value`` 行
* 注释以 ``%`` 或 ``#`` 开头（逐字来自 FEOS PDF §4）

本解析器把它们统一为 ``AUX`` 表：``sections``（节名 → kv 字典）+
``numbers``（全部数值，原样保留）。**不猜测物理语义** —— 这些文件的价值在于
参数溯源（与伴随注释文件互补），而非数值网格。
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_sections"]

FAMILY = "feos_aux"

_KV_RE = re.compile(r"^\s*([A-Za-z_][\w.\-\[\]%]*)\s*=\s*(.+?)\s*$")
_SECTION_RE = re.compile(r"^\s*\[?([A-Za-z][\w.\- ]*)\]?\s*:?\s*$")
_COMMENT = ("%", "#")


def parse_sections(lines: list[str]) -> tuple[dict[str, dict[str, str]], list[str]]:
    """解析成 ``{节名: {key: value}}``，返回 ``(sections, notes)``。"""
    sections: dict[str, dict[str, str]] = {"__head__": {}}
    cur = "__head__"
    notes: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith(_COMMENT):
            continue
        if s.startswith("REM"):
            continue
        m = _KV_RE.match(s)
        if m:
            sections.setdefault(cur, {})[m.group(1)] = m.group(2)
            continue
        if "=" not in s and not fn.extract_numbers(s):
            m2 = _SECTION_RE.match(s)
            if m2:
                cur = m2.group(1).strip()
                sections.setdefault(cur, {})
                continue
        # 其余忽略（数值行由 numbers 兜底）
    notes.append(f"sections={list(sections)}")
    return sections, notes


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    sections, notes = parse_sections(doc.lines)
    numbers = fn.extract_numbers("\n".join(doc.lines))

    table = ParsedTable(
        table_key=f"AUX_{Path(rel).stem}[:AUX]",
        kind="AUX",
        family=FAMILY,
        source_relpath=rel,
        header_raw=doc.lines[0] if doc.lines else "",
        layout_rule="F6/FEOS-aux: 分节 + key=value（% / # 注释）",
    )
    table.n_numbers_seen = len(numbers)
    table.n_numbers_expected = None
    if numbers:
        table.fields["raw_values"] = numbers
        table.field_shape["raw_values"] = (len(numbers),)
        table.field_units["raw_values"] = "unknown"
    kv_count = sum(len(v) for v in sections.values())
    table.unit_source = "none (辅助参数文件)"
    table.notes.append(f"解析出 {len(sections)} 节 / {kv_count} 个 key=value")
    table.notes.extend(notes)
    table.notes.append(
        "⚠️ 辅助文件：语义按 key 名溯源，**不参与统一网格**（非 (rho,T) 表）"
    )
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
