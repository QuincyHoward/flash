"""F6f —— SNOP 输入脚本（``*.SNOP``）与 Fortran namelist 解析。

SNOP（K. Eidmann, *Laser and Particle Beams* **12**(2), 223–244 (1994)）用
Fortran namelist ``&daten`` 接收参数。实测（``mat_C-1.0/C_20G.SNOP``）::

    &daten
      NT=20, NR=20, NG=20, NP=3000,
      Z=6.0, RHO1=1.0E-6, RHO2=100.0, T1=1.0E-3, T2=100.0,
      X1=1.0E-3, X2=10.0, EQ=0.0, IGROUP=4, ...
    /

``doc/SNOP.MANUAL`` 给出全部参数含义与单位为
（``RHO1/RHO2`` g/cm³、``T1/T2`` **keV**、``X1/X2`` **keV**、群划分 ``IGROUP`` 1–5）。

本解析器：解出 namelist 字典 + ``FG`` 群边界数组，并标注单位来源。
它是**参数溯源**文件，不产生 (rho, T) 网格 → KIND 记为 ``AUX``。
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_namelist", "PARAM_UNITS"]

FAMILY = "snop_input"

#: 参数单位（逐字来自 ``doc/SNOP.MANUAL``）
PARAM_UNITS = {
    "RHO1": "g/cm3", "RHO2": "g/cm3",
    "T1": "keV", "T2": "keV",
    "X1": "keV", "X2": "keV",
    "FG": "eV",
}

_NL_START = re.compile(r"^\s*&(\w+)", re.I)
_NL_END = re.compile(r"^\s*/\s*$")


def parse_namelist(lines: list[str]) -> tuple[str | None, dict[str, object], list[float]]:
    """解析 Fortran namelist，返回 ``(名字, 标量字典, FG 数组)``。

    ``FG`` 是群边界数组，可能跨多行并在续行中展开。
    """
    name: str | None = None
    scalars: dict[str, object] = {}
    fg: list[float] = []
    in_nl = False
    buf: list[str] = []

    for ln in lines:
        if not in_nl:
            m = _NL_START.match(ln)
            if m:
                name = m.group(1).lower()
                in_nl = True
                buf = [ln[m.end():]]
            continue
        if _NL_END.match(ln):
            in_nl = False
            continue
        buf.append(ln)

    body = " ".join(buf)
    # 群边界数组 FG(...) = 一串数
    for m in re.finditer(r"FG\s*\([^)]*\)\s*=\s*([\d.eE+\-,\s]+)", body):
        fg.extend(fn.extract_numbers(m.group(1)))
    body_wo_fg = re.sub(r"FG\s*\([^)]*\)\s*=\s*[\d.eE+\-,\s]+", " ", body)

    for part in re.split(r"[,;]", body_wo_fg):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        key = k.strip().upper()
        if not key:
            continue
        nums = fn.extract_numbers(v)
        scalars[key] = nums[0] if len(nums) == 1 else (nums if nums else v.strip())
    return name, scalars, fg


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    name, scalars, fg = parse_namelist(doc.lines)

    table = ParsedTable(
        table_key=f"SNOP_{Path(rel).stem}",
        kind="AUX",
        family=FAMILY,
        source_relpath=rel,
        header_raw=doc.lines[0] if doc.lines else "",
        layout_rule="F6/SNOP-input: Fortran namelist &daten",
    )
    table.n_numbers_seen = len(scalars) + len(fg)
    table.n_numbers_expected = None
    table.n_groups = int(scalars["NG"]) if isinstance(scalars.get("NG"), (int, float)) else None
    if fg:
        table.group_bounds = fg

    table.unit_source = "declared:doc/SNOP.MANUAL"
    table.notes.append(f"namelist=/{name}/ 参数 {len(scalars)} 个: "
                       + ", ".join(f"{k}={v}" for k, v in list(scalars.items())[:12]))
    if fg:
        table.notes.append(f"FG 群边界 {len(fg)} 个，单位 eV（SNOP.MANUAL）")
    for k, u in PARAM_UNITS.items():
        if k in scalars:
            table.notes.append(f"单位声明: {k} [{u}]")
    table.notes.append("辅助参数文件（不产生 (rho,T) 网格）")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
