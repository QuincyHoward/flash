"""F1 —— MULTI「反演 EOS」解析器（默认 SESAME 族，4×15 定宽）。

格式（实测）
------------
每个**块**以一行 4 数表头开始::

    table_id   rho0(未用)   nr   ne

其后为 payload（T-major，rho 快变，索引 = ``i_de*nr + j_rho``）。

★ 两种 payload 布局（实测并存，由**计数守恒唯一确定**）
------------------------------------------------------
=========================  ==========================================  ================
布局                        数组                                       实测文件
=========================  ==========================================  ================
``with_e0``（含冷能）        ``rho(nr) de(ne) e0(nr) P(nr·ne) T(nr·ne)``  ``AL_eos`` 9978
``no_e0``（无冷能）          ``rho(nr) de(ne) P(nr·ne) T(nr·ne)``          ``AU_eosd`` 4770
=========================  ==========================================  ================

计数公式：
``with_e0`` → ``4 + 2*nr + ne + 2*nr*ne``；``no_e0`` → ``4 + nr + ne + 2*nr*ne``。
两者只差一个 ``nr``，因此**必须用实测计数反解**，不能假定。

实测基准
--------
* ``mat_Al-1.0/AL_eos``    头 ``37181000 2.7 66 74`` → **9978** = 4+132+74+9768 ✓
* ``mat_Au-1.0/AU_eos``    头 ``27001000 19.300003 101 23``
* ``mat_Be-1.0/BE_eos``    头 ``2020 0.0 101 50``
* ``mat_Au-1.0/AU_eosd``   **2 个块**串联（行 0 与 1194），每块 **4770** → ``no_e0`` 布局

★ 多块串联
----------
``AU_eosd`` 在 2388 行里放了 2 个同表头的块 → 由 :func:`parse_all` 拆成 2 张表。
块边界由「又出现一行与首块表头完全相同的 4 数行」确定。

单位
----
=================  ====================  =============================
量                  单位                  换算
=================  ====================  =============================
rho                g/cm^3                原样（**线性**）
de（冷曲线之上能量）  Mbar*cm^3/g           原样
e0（冷能）           Mbar*cm^3/g           原样
P                   Mbar                  原样
T                   **Kelvin**            ``* EV_PER_K`` → eV
=================  ====================  =============================

⚠️ F1 的**自变量是 (rho, de)**，温度 T 是**因变量（场）** —— 这正是"Inverted EOS"的含义。
要得到 ``(rho, Te)`` 网格需在 de 方向反演，见 :mod:`eosop_pro.convert.invert_eos`。
"""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..core import fortran_numbers as fn
from ..core.errors import ParseError
from ..core.textio import read_text
from ..registry.database_index import sesame_digit_of
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_header", "detect_layout",
           "LAYOUTS", "HEADER_FIELDS"]

FAMILY = "multi_inverted_eos"
HEADER_FIELDS = ("table_id", "rho0", "nr", "ne")

#: 布局名 → payload 段列表（``n`` 为网格个数，``n2`` 为 nr*ne）
LAYOUTS: dict[str, tuple[str, ...]] = {
    "with_e0": ("rho", "de", "e0", "P", "T"),
    "no_e0": ("rho", "de", "P", "T"),
}

_LAYOUT_FORMULA = {
    "with_e0": lambda nr, ne, n2: 2 * nr + ne + 2 * n2,
    "no_e0": lambda nr, ne, n2: nr + ne + 2 * n2,
}


def detect_layout(nr: int, ne: int, n_payload: int) -> tuple[str, int]:
    """由实测 payload 数量反解布局，返回 ``(布局名, 尾部多余个数)``。

    先求**精确解**（尾部 = 0）。若唯一精确解不存在，允许 1..nr 个**尾部未声明数值**
    （实测 ``mat_Be-1.0/BE_eos_i`` 就多 2 个零）——但这必须被**显式标注**，
    不能静默吸收，否则计数守恒就失去意义。

    :raises ParseError: 精确解不唯一，或无布局能解释该数量
    """
    n2 = nr * ne
    exact = [name for name, f in _LAYOUT_FORMULA.items() if f(nr, ne, n2) == n_payload]
    if len(exact) == 1:
        return exact[0], 0
    if len(exact) > 1:  # pragma: no cover - 两公式恒差 nr≥2，不可能并列
        raise ParseError(f"F1 layout ambiguous: {exact} nr={nr} ne={ne}")

    tails = []
    for name, f in _LAYOUT_FORMULA.items():
        tail = n_payload - f(nr, ne, n2)
        if 0 < tail <= nr:
            tails.append((name, tail))
    if len(tails) == 1:
        return tails[0]
    raise ParseError(
        f"F1 payload layout unmatched: n_payload={n_payload} nr={nr} ne={ne} "
        f"candidates=" + ", ".join(
            f"{k}={v}" for k, v in
            ((n, _LAYOUT_FORMULA[n](nr, ne, n2)) for n in _LAYOUT_FORMULA)
        )
    )


def parse_header(line: str) -> dict:
    """解析块表头（4 个数）。"""
    nums = fn.extract_numbers(line)
    if len(nums) != 4:
        raise ParseError(f"F1 header must have 4 numbers, got {len(nums)}",
                         header_raw=line)
    return {
        "table_id": int(round(nums[0])),
        "rho0": nums[1],
        "nr": int(round(nums[2])),
        "ne": int(round(nums[3])),
        "raw": line,
        "n_header_nums": 4,
    }


def _find_block_starts(lines: list[str], table_id: int, nr: int, ne: int) -> list[int]:
    """找出全部「与首块表头完全相同」的行号 —— 即块边界。"""
    out: list[int] = []
    for i, ln in enumerate(lines):
        if fn.has_letters(ln):
            continue
        nums = fn.extract_numbers(ln)
        if len(nums) != 4:
            continue
        if (int(round(nums[0])) == table_id
                and int(round(nums[2])) == nr and int(round(nums[3])) == ne):
            out.append(i)
    return out


def parse_all(path: str | Path, relpath: str = "") -> list[ParsedTable]:
    """解析文件，返回全部块（``AU_eosd`` 这类多块串联会拆成多张表）。"""
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = doc.lines
    if len(lines) < 2:
        raise ParseError("file too short for F1", path=rel)

    first = None
    for ln in lines:
        if ln.strip():
            first = ln
            break
    if first is None:
        raise ParseError("F1: empty file", path=rel)
    hdr0 = parse_header(first)
    if not (config.DIM_MIN <= hdr0["nr"] <= config.DIM_MAX
            and config.DIM_MIN <= hdr0["ne"] <= config.DIM_MAX):
        raise ParseError(f"F1 implausible dims nr={hdr0['nr']} ne={hdr0['ne']}",
                         path=rel, header_raw=first)

    starts = _find_block_starts(lines, hdr0["table_id"], hdr0["nr"], hdr0["ne"])
    if not starts:
        starts = [lines.index(first)]

    tables: list[ParsedTable] = []
    for bi, s in enumerate(starts):
        end = starts[bi + 1] if bi + 1 < len(starts) else len(lines)
        payload_lines = lines[s + 1:end]
        n_blank = sum(1 for ln in payload_lines if not ln.strip())
        values = fn.extract_numbers("\n".join(payload_lines))
        tables.append(_build(rel, hdr0, values, bi, len(starts), n_blank, s))
    return tables


def parse(path: str | Path, relpath: str = "") -> ParsedTable:
    """解析并返回**第一个块**（多块文件请用 :func:`parse_all`）。"""
    tables = parse_all(path, relpath)
    if len(tables) > 1:
        tables[0].notes.append(
            f"⚠️ 本文件含 {len(tables)} 个块（同表头串联）—— parse() 只返回第一块，"
            f"其余为 {[t.table_key for t in tables[1:]]}"
        )
    return tables[0]


def _build(rel: str, hdr: dict, values: list[float], block_idx: int,
           n_blocks: int, n_blank: int, line_no: int) -> ParsedTable:
    nr, ne = hdr["nr"], hdr["ne"]
    layout, tail = detect_layout(nr, ne, len(values))
    n2 = nr * ne

    # payload 逐段累积切分（任何长度不符立刻暴露）
    parts: dict[str, list[float]] = {}
    i = 0
    for name in LAYOUTS[layout]:
        take = {"rho": nr, "de": ne, "e0": nr, "P": n2, "T": n2}[name]
        parts[name] = list(values[i:i + take])
        i += take
    tail_vals = list(values[i:i + tail])
    i += tail
    if i != len(values):  # pragma: no cover - detect_layout 已保证
        raise ParseError(f"F1 cursor mismatch: consumed {i} of {len(values)}",
                         path=rel, header_raw=hdr["raw"])

    suffix = f"_b{block_idx + 1}" if n_blocks > 1 else ""
    table = ParsedTable(
        table_key=f"EOS_{hdr['table_id']}{suffix}",
        kind=_kind_from_name(rel),
        family=FAMILY,
        source_relpath=rel,
        table_id=hdr["table_id"],
        sesame_digit=sesame_digit_of(hdr["table_id"]),
        header_raw=hdr["raw"],
        layout_rule=f"F1/{layout}: 4 + {'2*nr' if layout == 'with_e0' else 'nr'} + ne + 2*nr*ne",
    )
    table.n_numbers_seen = 4 + len(values)
    table.n_numbers_expected = (
        4 + (2 * nr if layout == "with_e0" else nr) + ne + 2 * n2 + tail
    )
    if table.n_numbers_seen != table.n_numbers_expected:
        from ..core.errors import CountMismatch
        raise CountMismatch(table.n_numbers_seen, table.n_numbers_expected,
                            path=rel, header_raw=hdr["raw"])

    rho = parts["rho"]
    de = parts["de"]
    P = parts["P"]
    T_K = parts["T"]

    table.axes["rho"] = rho
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = False
    # ⚠️ 自变量是 (rho, de)，T 是因变量场
    table.axes["de"] = de
    table.axis_units["de"] = "Mbar*cm3/g"
    table.axis_log10["de"] = False

    table.fields["P"] = P
    table.field_shape["P"] = (ne, nr)
    table.field_units["P"] = "Mbar"
    table.field_log10["P"] = False

    if "e0" in parts:
        e0 = parts["e0"]
        table.fields["E"] = [de[a] + e0[b] for a in range(ne) for b in range(nr)]
        table.fields["e0_cold"] = e0
        table.field_shape["e0_cold"] = (nr,)
        table.field_units["e0_cold"] = "Mbar*cm3/g"
    else:
        # 无冷能数组 → 比能偏移以 0 为基准
        table.fields["E"] = [de[a] for a in range(ne) for _ in range(nr)]
        table.notes.append("本块**无 e0 冷能数组**（no_e0 布局）→ E 以 de 为基准")
    table.field_shape["E"] = (ne, nr)
    table.field_units["E"] = "Mbar*cm3/g"
    table.field_log10["E"] = False

    table.fields["T"] = [t * config.EV_PER_K for t in T_K]
    table.field_shape["T"] = (ne, nr)
    table.field_units["T"] = "eV"
    table.field_log10["T"] = False

    table.fields["de_energy"] = de
    table.field_shape["de_energy"] = (ne,)
    table.field_units["de_energy"] = "Mbar*cm3/g"

    table.unit_source = "format:F1 (rho g/cm3, P Mbar, T Kelvin->eV)"
    table.notes.append(f"rho0={hdr['rho0']} layout={layout} n_blank_in_payload={n_blank}")
    table.notes.append("自变量为 (rho, de)；T 为因变量场 —— 取 (rho,Te) 网格需反演")
    if tail:
        table.fields["raw_tail"] = tail_vals
        table.field_shape["raw_tail"] = (tail,)
        table.field_units["raw_tail"] = "unknown"
        table.notes.append(
            f"⚠️ 尾部 {tail} 个未声明数值（已按原样保存为 raw_tail）—— "
            f"精确布局公式差 {tail} 项，需人工定性"
        )
    if n_blocks > 1:
        table.notes.append(f"文件含 {n_blocks} 个同表头块，本表为第 {block_idx + 1} 块（行 {line_no}）")
    return table


def _kind_from_name(rel: str) -> str:
    """由文件名 token 判定 KIND（``_eos_e``/``_eos_i``/``_ieos``/``_eosd``）。"""
    base = Path(rel).name.lower()
    if "_eos_e" in base or "_ieeos" in base:
        return "EOS_ELECTRON"
    if "_eos_i" in base or "_ieos" in base or "_imi" in base:
        return "EOS_ION"
    return "EOS_TOTAL"
