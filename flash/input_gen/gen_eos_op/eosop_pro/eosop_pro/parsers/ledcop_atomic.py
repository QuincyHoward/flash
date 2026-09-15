"""F5a —— LEDCOP / ATOMIC 主表解析器（``ATOMIC/*.txt``）。

必须用**锚点驱动的流式状态机**，不能按固定行数（``ATOMIC/Al.txt`` 有 **348636 行**）。

结构（实测锚点）
----------------
::

    Number of T =  69  Number of rho =  50  Number of materials =   1
    TOPS results for  Li              on Jul  2, 2017
     Opacities in cm**2/gm, T in keV, density in gm/cc      <- ★ 内嵌单位声明
    Normalized composition for requested elements
    No. Fraction Mass Fraction  At. No.  Chem. Sym.  Mat ID.
      5.0000E-01   8.7320E-01      3         Li        4922
    Temperature grid used the following  69 points        <- 其后 69 个数（6/行）
      ...temperature points...
    Density grid used the following  50 points             <- 其后 50 个数
      ...density points...
    Density     Ross opa    Planck opa  No. Free    Av Sq Free  T=  5.0000E-04
      ...nr 行 5 列...
    (以上 T 块重复 nt 次)
    Multigroup opacities
    Energy      Ross mg     Planck mg    for T, density =   5.0000E-04  1.0000E-03
      ...np 行 3 列...  ← 逐 (T, rho) 重复 nt*nr 次（体积主体）

★ 内存纪律
----------
多群段有 ``nt*nr`` 个块（Al 为 69×50=3450 块 × 99 行 ≈ 34 万行）。
故 ``include_multigroup`` 默认 **False**；开启时才解析（并会显著吃内存）。
灰度段（``T=`` 块）只占 nt 块，开销小。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core import anchors as an
from ..core import fortran_numbers as fn
from ..core import textio
from ..core.errors import CountMismatch, ParseError
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "scan_header"]

FAMILY = "ledcop_atomic"


def scan_header(lines: list[str]) -> dict[str, Any]:
    """从头部若干行抽声明信息（维度、单位、材料、组分）。"""
    from ..core.annotations import extract_from_text

    head = "\n".join(lines[:40])
    ann = extract_from_text(head, source="", kind="inline")
    out: dict[str, Any] = {
        "n_t": ann.dims.get("NT"), "n_rho": ann.dims.get("NR"),
        "n_mat": ann.dims.get("NMAT"),
        "units": dict(ann.units),
        "material": ann.material_name,
        "composition": ann.composition,
        "provenance": list(ann.provenance),
    }
    src = an.find(head, "ledcop_source")
    if src:
        out["material"] = out["material"] or src.group(2)
        out["date"] = src.group(3).strip()
    return out


def parse_all(path: str | Path, relpath: str = "", *,
              include_multigroup: bool = False,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    rel = relpath or Path(path).name
    it = textio.iter_lines(path)

    n_t = n_rho = None
    t_grid: list[float] = []
    rho_grid: list[float] = []
    head_lines: list[str] = []

    mode: str | None = None
    need = 0
    gray_T: list[float] = []
    gray_rows: list[list[float]] = []
    cur_T: float | None = None

    photon_E: list[float] = []
    mg: list[tuple[float, float, list[tuple[float, float, float]]]] = []
    cur_mg: tuple[float, float, list[tuple[float, float, float]]] | None = None

    for raw in it:
        ln = raw
        s = ln.strip()

        if len(head_lines) < 40:
            head_lines.append(ln)

        # ── 维度声明 ──
        m = an.find(ln, "ledcop_n_t")
        if m and n_t is None:
            n_t = int(m.group(1))
            continue
        m = an.find(ln, "ledcop_n_rho")
        if m and n_rho is None:
            n_rho = int(m.group(1))
            continue

        # ── 网格起始 ──
        if an.find(ln, "ledcop_t_grid_hdr"):
            m2 = an.find(ln, "ledcop_t_grid_hdr")
            mode, need, t_grid = "t_grid", int(m2.group(1)), []
            continue
        if an.find(ln, "ledcop_rho_grid_hdr"):
            m2 = an.find(ln, "ledcop_rho_grid_hdr")
            mode, need, rho_grid = "rho_grid", int(m2.group(1)), []
            continue

        # ── 灰度块头（含 T= 值）──
        m = an.find(ln, "ledcop_block_T")
        if m:
            mode = "gray"
            cur_T = float(m.group(1))
            if cur_T not in gray_T:
                gray_T.append(cur_T)
            need = 0
            continue

        # ── 多群段 ──
        if s.lower().startswith("multigroup"):
            mode = "mg_idle"
            continue
        m = an.find(ln, "ledcop_mg_block")
        if m:
            if not include_multigroup:
                mode = "mg_skip"
                continue
            mode = "mg"
            cur_mg = (float(m.group(1)), float(m.group(2)), [])
            mg.append(cur_mg)
            photon_E = []
            continue

        if not s:
            continue
        vals = fn.extract_numbers(ln)
        if not vals:
            continue

        if mode == "t_grid":
            t_grid.extend(vals)
            if len(t_grid) >= need:
                mode = None
        elif mode == "rho_grid":
            rho_grid.extend(vals)
            if len(rho_grid) >= need:
                mode = None
        elif mode == "gray":
            if len(vals) >= 5:
                gray_rows.append(vals[:5])
        elif mode == "mg":
            if len(vals) >= 3 and cur_mg is not None:
                cur_mg[2].append((vals[0], vals[1], vals[2]))
        # mode == 'mg_skip' / None → 忽略

    if n_t is None and t_grid:
        n_t = len(t_grid)
    if n_rho is None and rho_grid:
        n_rho = len(rho_grid)
    if not (n_t and n_rho):
        raise ParseError(f"LEDCOP: cannot determine dims (n_t={n_t} n_rho={n_rho})",
                         path=rel)

    hdr = scan_header(head_lines)
    unit = (unit_hint_T or hdr["units"].get("T") or "keV")
    scale = {"ev": 1.0, "kev": 1e3}.get(str(unit).lower(), 1e3)

    if len(t_grid) != n_t:
        raise CountMismatch(len(t_grid), n_t, path=rel, header_raw="T grid")
    if len(rho_grid) != n_rho:
        raise CountMismatch(len(rho_grid), n_rho, path=rel, header_raw="rho grid")

    # 灰度段：nt 块 × nr 行，列 = Density Ross Planck NoFree AvSqFree
    if len(gray_T) != n_t:
        raise CountMismatch(len(gray_T), n_t, path=rel, header_raw="gray T blocks")
    if len(gray_rows) != n_t * n_rho:
        raise CountMismatch(len(gray_rows), n_t * n_rho, path=rel,
                            header_raw="gray rows")

    table = ParsedTable(
        table_key=f"LEDCOP_{Path(rel).stem}",
        kind="PLANCK",
        family=FAMILY,
        source_relpath=rel,
        header_raw=head_lines[0] if head_lines else "",
        layout_rule="F5/LEDCOP: 锚点状态机（维度/网格/灰度块/多群段）",
    )
    table.n_numbers_seen = len(gray_rows) * 5
    table.n_numbers_expected = n_t * n_rho * 5

    table.axes["rho"] = list(rho_grid)
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = False
    table.axes["Te"] = [t * scale for t in t_grid]
    table.axis_units["Te"] = "eV"
    table.axis_log10["Te"] = False

    cols = ["Ross", "Planck", "NoFree", "AvSqFree"]
    for ci, name in enumerate(cols, start=1):
        flat = [row[ci] for row in gray_rows]
        table.fields[name] = flat
        table.field_shape[name] = (n_t, n_rho)
        table.field_units[name] = "cm2/g" if name in ("Ross", "Planck") else "1"
        table.field_log10[name] = False
    # 第一列是 density，用于交叉校验
    dens = [row[0] for row in gray_rows]
    first_block = dens[:n_rho]
    if first_block and rho_grid:
        drift = max(abs(a - b) for a, b in zip(first_block, rho_grid))
        table.notes.append(f"灰表格内 Density 列与 rho 网格最大偏差 = {drift:.3g}")

    if include_multigroup and mg:
        table.n_groups = len(mg[0][2]) if mg[0][2] else None
        table.notes.append(
            f"多群段：{len(mg)} 个 (T,rho) 块，每块 {len(mg[0][2])} 个光子能量点"
        )
        table.fields["mg_photon_eV"] = [p[0] for p in mg[0][2]]
        table.field_shape["mg_photon_eV"] = (len(mg[0][2]),)
        table.notes.append("⚠️ 多群段体积极大，仅在 include_multigroup=True 时解析")

    table.unit_source = f"declared:{unit} (文件内嵌单位行)"
    table.notes.append(f"material={hdr['material']} composition={hdr['composition']}")
    table.notes.append(f"provenance={hdr['provenance']}")
    if hdr["units"]:
        # 文件内嵌单位声明行（如 `Opacities in cm**2/gm, T in keV, density in gm/cc`）
        table.notes.append(
            "文件内嵌单位声明: "
            + ", ".join(f"{k}={v}" for k, v in sorted(hdr["units"].items()))
        )
    table.notes.append(f"gray blocks = {len(gray_T)} = n_t={n_t}（逐 T 一块）")
    if not include_multigroup:
        table.notes.append("多群段已跳过（include_multigroup=False，控制内存）")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          include_multigroup: bool = False,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, include_multigroup=include_multigroup,
                     unit_hint_T=unit_hint_T)[0]
