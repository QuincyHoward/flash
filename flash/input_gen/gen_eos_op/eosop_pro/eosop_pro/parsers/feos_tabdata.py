"""F6a —— ShowEOS 导出的 TSV 数值表（``*.data.txt``）。

实测（``mat_B/B.data.txt``，12524 行 × 10 列，**制表符**分隔）::

    0	0	 0.00000000e+00	 0.00000000e+00	 3.53712002e-53	 8.86026323e-54	 2.65109369e-53	...
    1	0	 2.34000000e-05	 0.00000000e+00	 3.53712002e-53	 2.30141416e+00	-2.30141482e+00	...

列 1、2 是两个索引（``i``、``j``），其后为材料参数与 EOS/不透明度量。
由于**本地无该导出的列名文档**，列语义按 ``colN`` 命名并**整体原样保留** ——
绝不猜测物理含义。行内数值可用 ``.301`` 兄弟文件交叉核对。
"""

from __future__ import annotations

from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.errors import CountMismatch, ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all"]

FAMILY = "feos_tabdata"


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    rows: list[list[float]] = []
    n_blank = 0
    for ln in doc.lines:
        if not ln.strip():
            n_blank += 1
            continue
        cells = [c for c in ln.split("\t") if c.strip()]
        if len(cells) < 2:
            cells = ln.split()
        vals: list[float] = []
        for c in cells:
            vals.extend(fn.extract_numbers(c))
        if vals:
            rows.append(vals)

    if not rows:
        raise ParseError("feos_tabdata: no numeric rows", path=rel)

    ncol_hist: dict[int, int] = {}
    for r in rows:
        ncol_hist[len(r)] = ncol_hist.get(len(r), 0) + 1
    ncol = max(ncol_hist, key=lambda k: ncol_hist[k])
    if ncol < 3:
        raise ParseError(f"feos_tabdata: modal column count {ncol} too small", path=rel)

    bad = [i for i, r in enumerate(rows) if len(r) != ncol]
    if bad:
        raise CountMismatch(len(rows) - len(bad), len(rows), path=rel,
                            header_raw=f"rows with != {ncol} columns at {bad[:10]}")

    table = ParsedTable(
        table_key=f"TABDATA_{Path(rel).stem}",
        kind="AUX",
        family=FAMILY,
        source_relpath=rel,
        header_raw=doc.lines[0] if doc.lines else "",
        layout_rule=f"F6/TSV: {len(rows)} 行 × {ncol} 列（制表符）",
    )
    table.n_numbers_seen = len(rows) * ncol
    table.n_numbers_expected = len(rows) * ncol

    for j in range(ncol):
        name = f"col{j}"
        table.fields[name] = [r[j] for r in rows]
        table.field_shape[name] = (len(rows),)
        table.field_units[name] = "unknown"
    # 列 1/2 是索引 → 明确标注，避免被误当物理量
    if ncol >= 2:
        table.notes.append("col0/col1 为行/列索引（实测为递增整数）")
    table.unit_source = "none (列语义无本地文档)"
    table.notes.append(
        f"⚠️ 列语义**未定**（本地无该导出格式的列名文档）→ 按 colN 原样保留；"
        f"可用同族 .301 兄弟文件交叉核对。n_blank={n_blank}"
    )
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
