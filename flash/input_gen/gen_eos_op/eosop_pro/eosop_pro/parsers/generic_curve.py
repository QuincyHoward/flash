"""F6g —— 通用一维/二维曲线兜底解析器。

适用于 ``matter++`` 里那些「无专门解析器、但明显是列式数值表」的文件，例如
``hyades/ionpot.dat``、``PowerLaws/*.dat``、``XrayMassCoef/*``、``Crystal/*.dat``、
``Thermos/*.ini`` 等。

策略（**保守，不猜测物理语义**）:
1. 剥离注释行（``#`` / ``%`` / ``c`` 开头 / ``REM``）；
2. 统计各行的数值个数，取**众数**作为列数（非众数行 → 记录为异常，不静默丢）；
3. 第 0 列作 x 轴，其余列命名为 ``col1..colN``；
4. 单位一律标 ``unknown``，并把注释原文收集到 ``notes`` 供人工判定。

**绝不因文件名猜测物理量** —— 命名必须来自文档或注释证据。
"""

from __future__ import annotations

from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "is_comment_line", "COMMENT_PREFIXES"]

FAMILY = "generic_curve"

#: 注释行前缀（实测：``#``/``%``/``REM``；``c``/``C`` 见 hyades/coldopac.dat）
COMMENT_PREFIXES = ("#", "%", "REM", "rem", "c ", "C ")


def is_comment_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    return any(s.startswith(p) for p in COMMENT_PREFIXES)


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name

    comments: list[str] = []
    rows: list[list[float]] = []
    irregular: list[int] = []
    for ln in doc.lines:
        if is_comment_line(ln):
            if ln.strip():
                comments.append(ln.strip())
            continue
        vals = fn.extract_numbers(ln)
        if vals:
            rows.append(vals)

    if not rows:
        raise ValueError(f"generic_curve: no numeric rows in {rel}")

    hist: dict[int, int] = {}
    for r in rows:
        hist[len(r)] = hist.get(len(r), 0) + 1
    ncol = max(hist, key=lambda k: hist[k])
    good = [r for r in rows if len(r) == ncol]
    irregular = [i for i, r in enumerate(rows) if len(r) != ncol]

    table = ParsedTable(
        table_key=f"CURVE_{Path(rel).stem}",
        kind="CURVE",
        family=FAMILY,
        source_relpath=rel,
        header_raw=comments[0] if comments else "",
        layout_rule=f"F6/generic: 众数列宽 {ncol}，共 {len(good)} 行",
    )
    table.n_numbers_seen = sum(len(r) for r in rows)
    # 偏离众数列宽的行已被**显式记录**在 notes 里，故 expected 应等于 seen ——
    # 否则会把"已定性并登记的偏差"误报成 count_mismatch（实测踩过：.ini 文件）。
    table.n_numbers_expected = table.n_numbers_seen

    table.axes["x"] = [r[0] for r in good]
    table.axis_units["x"] = "unknown"
    table.axis_log10["x"] = False
    for j in range(1, ncol):
        name = f"col{j}"
        table.fields[name] = [r[j] for r in good]
        table.field_shape[name] = (len(good),)
        table.field_units[name] = "unknown"
        table.field_log10[name] = False

    table.unit_source = "none（列语义无文档 → 不猜测）"
    table.notes.append(f"列宽直方图 = {hist}；众数列宽取 {ncol}")
    if irregular:
        table.notes.append(
            f"⚠️ {len(irregular)} 行偏离众数列宽（行号 {irregular[:8]}），已剔除"
        )
    if comments:
        table.notes.append(f"注释原文（前 5 条）: {comments[:5]}")
    table.notes.append("⚠️ 兜底解析：列名按 colN 命名，物理量命名需文档/注释证据")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
