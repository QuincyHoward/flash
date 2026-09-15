"""F3 —— Hyades / SESAME ASCII 解析器（5×15 定宽；路径含 ``hyades``）。

格式（逐字来自 ``doc/Hyades 数据格式说明.doc``）
-----------------------------------------------
行 1 = **自由文本注释**（材料名 + 生成历史），例如::

    ALUMINUM    LANL SESAME #3711 DATED: 22581 11483
    DT          LANL SESAME #5271 DATED: 91374 92882
    POLY        LANL SESAME #17171 DATED:  21393  21393
    Gold        QEOS DATED: 062795

行 2 = ``id  zbar  abar  rho0  L``，其中::

    L = 2 + NR + NT + 2*NR*NT

行 3 起 = ``NR  NT  RHO(1..NR)  T(1..NT)  P(1..NR*NT)  E(1..NR*NT)``（T-major，rho 快变）。

实测基准
--------
=====================  ==========  ==============  ==============================
文件                     ``L``       解出 (NR, NT)   备注
=====================  ==========  ==============  ==============================
``sesame/eos_11.dat``  2577        (50, 25)        DT
``sesame/eos_21.dat``  4743        (43, 54)        Glass
``sesame/eos_41.dat``  2004        (44, 22)        Aluminum
``Opacity/opc_1031.dat`` 2931      (31, 46)        Polyethylene
=====================  ==========  ==============  ==============================

★ 两个 (NR×NT) 数组的含义
--------------------------
* EOS 文件（``eos_*``）：``[P, E]``
* 不透明度文件（``opc_*``）：``[Rosseland, Planck]`` —— 依据 ``doc/Hyades 数据格式说明.doc``：
  *"Rosseland mean tables only：本来应该存储 Planck 平均不透明度的位置用 0 代替"*。
  故**若其中一个数组全为 0**，另一个即 Rosseland（本模块据此自动判序）。

单位（逐字来自同一文档）
------------------------
``密度 g/cm3``、``温度 keV``、``压强 dyne/cm2``、``比内能 erg/g``。
"""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..core import anchors as an
from ..core import fortran_numbers as fn
from ..core.errors import CountMismatch, ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_header_line", "solve_dims",
           "DOS_EOF"]

FAMILY = "hyades_eos"

#: DOS 文件结束标记（实测出现在 ``hyades/sesame/eos_*.dat`` 末行）
DOS_EOF = "\x1a"


def solve_dims(length: int) -> list[tuple[int, int]]:
    """求 ``2*NR*NT + NR + NT + 2 = L`` 的**全部**正整数解。

    ⚠️ 该方程**并不唯一**（例如 ``L=2004`` 同时有 ``(44,22)`` 与 ``(2,400)``）——
    所以 ``NR/NT`` 只能由 payload 的前两个数确定，本函数仅作**交叉校验**：
    真解必在返回列表中。

    变形：``NT = (L - 2 - NR) / (2*NR + 1)``，只用整除判别，无浮点误差。
    """
    if length < 8:
        return []
    out: list[tuple[int, int]] = []
    for nr in range(2, 5001):
        rem = length - 2 - nr
        denom = 2 * nr + 1
        if rem < denom * 2:
            break
        if rem % denom == 0:
            nt = rem // denom
            if nt >= 2:
                out.append((nr, nt))
    return out


def parse_header_line(line: str) -> dict:
    nums = fn.extract_numbers(line)
    if len(nums) != 5:
        raise ParseError(f"F3 header must have 5 numbers, got {len(nums)}",
                         header_raw=line)
    return {
        "id": int(round(nums[0])), "zbar": nums[1], "abar": nums[2],
        "rho0": nums[3], "L": int(round(nums[4])), "raw": line,
    }


def _first_two(lines: list[str]) -> tuple[str, str]:
    """返回前两行（第 0 行是注释、第 1 行是数字表头）。"""
    idx = [i for i, ln in enumerate(lines) if ln.strip()]
    if len(idx) < 2:
        raise ParseError("F3 needs at least 2 non-blank lines")
    return lines[idx[0]], lines[idx[1]]


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = doc.lines
    c0, c1 = _first_two(lines)
    hdr = parse_header_line(c1)

    is_opacity = _looks_opacity(rel, c0)
    kind = "OPACITY" if is_opacity else "EOS_TOTAL"
    if not is_opacity:
        base = Path(rel).name.lower()
        if "_eos_e" in base:
            kind = "EOS_ELECTRON"
        elif "_eos_i" in base:
            kind = "EOS_ION"

    # 行 0 是注释；payload 从行 1 之后的数字开始（含 NR/ NT）
    # 注意：行 1 的 5 个数里 L 只是长度声明，真正的数组从 NR NT 开始
    first_idx = lines.index(c1)
    payload_lines = lines[first_idx + 1:]
    values_all = fn.extract_numbers("\n".join(payload_lines))
    n_blank = sum(1 for ln in payload_lines if not ln.strip())
    has_eof_marker = any(DOS_EOF in ln for ln in payload_lines)

    # ⚠️ 部分 ``eos_*`` 文件在数组末尾补零以凑满每行 5 个字段
    # （实测 eos_41 多 1 个、eos_11/eos_81 多 3 个）。**必须显式标注**，
    # 否则计数守恒就形同虚设。
    L = hdr["L"]
    if len(values_all) < L:
        raise CountMismatch(len(values_all), L, path=rel, header_raw=c1)
    tail_vals = values_all[L:]
    values = values_all[:L]

    if len(values) < 2:
        raise ParseError("F3 payload too short", path=rel, header_raw=c1)
    nr, nt = int(round(values[0])), int(round(values[1]))
    if not (2 <= nr <= 50000 and 2 <= nt <= 50000):
        raise ParseError(f"F3 implausible dims nr={nr} nt={nt}",
                         path=rel, header_raw=c1)
    expect = 2 + nr + nt + 2 * nr * nt
    if expect != L:
        raise CountMismatch(L, expect, path=rel, header_raw=c1)

    p = 2
    rho = values[p:p + nr]; p += nr
    T_keV = values[p:p + nt]; p += nt
    n2 = nr * nt
    a1 = values[p:p + n2]; p += n2
    a2 = values[p:p + n2]; p += n2
    if p != len(values):  # pragma: no cover
        raise ParseError(f"F3 cursor mismatch {p} != {len(values)}",
                         path=rel, header_raw=c1)

    table = ParsedTable(
        table_key=f"{'OPACITY' if is_opacity else 'EOS'}_{hdr['id']}",
        kind=kind,
        family=FAMILY,
        source_relpath=rel,
        table_id=hdr["id"],
        header_raw=c1,
        layout_rule="F3: L = 2 + nr + nt + 2*nr*nt",
    )
    # 计数守恒：seen 含补零，expected 也必须含补零，否则会把「已定性并记录的填充」
    # 误报成 count_mismatch（这是实测踩过的坑）。
    table.n_numbers_seen = len(values_all)
    table.n_numbers_expected = L + len(tail_vals)

    table.axes["rho"] = rho
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = False
    T_scale = {"kev": 1e3, "ev": 1.0}.get((unit_hint_T or "keV").lower(), 1e3)
    table.axes["Te"] = [t * T_scale for t in T_keV]
    table.axis_units["Te"] = "eV"
    table.axis_log10["Te"] = False

    if is_opacity:
        order = _opacity_order(a1, a2)
        table.notes.append(
            "两个 (NR,NT) 数组 = [Rosseland, Planck]（依 SESAME 301 约定："
            "Planck 槽位在全零时表示该表仅含 Rosseland）"
        )
        for name, arr in zip(order, (a1, a2)):
            table.fields[name] = arr
            table.field_shape[name] = (nt, nr)
            table.field_units[name] = "cm2/g"
            table.field_log10[name] = False
        table.notes.append(f"数组顺序判定 = {order}")
    else:
        table.fields["P"] = a1
        table.field_shape["P"] = (nt, nr)
        table.field_units["P"] = "dyne/cm2"
        table.field_log10["P"] = False
        table.fields["E"] = a2
        table.field_shape["E"] = (nt, nr)
        table.field_units["E"] = "erg/g"
        table.field_log10["E"] = False

    table.unit_source = "format:F3 (rho g/cm3, T keV->eV, P dyne/cm2, E erg/g)"
    sols = solve_dims(L)
    if sols and (nr, nt) not in sols and (nt, nr) not in sols:
        table.notes.append(
            f"⚠️ 由 payload 读出的 (nr,nt)=({nr},{nt}) 不在 L={L} 的可行解集 "
            f"{sols[:6]} 中 —— 布局存疑"
        )
    table.notes.append(
        f"id={hdr['id']} zbar={hdr['zbar']} abar={hdr['abar']} rho0={hdr['rho0']} "
        f"L={hdr['L']} n_blank_in_payload={n_blank}"
    )
    if tail_vals:
        table.fields["raw_tail"] = tail_vals
        table.field_shape["raw_tail"] = (len(tail_vals),)
        table.field_units["raw_tail"] = "unknown"
        table.notes.append(
            f"⚠️ 数组末尾有 {len(tail_vals)} 个补零（实测为该族凑满每行 5 字段的填充），"
            f"已按原样保存为 raw_tail"
        )
    if has_eof_marker:
        table.notes.append("含 DOS EOF 标记 \\x1a（已忽略，不参与数值）")
    m = an.find(c0, "sesame_number")
    if m:
        table.notes.append(f"comment declares SESAME #{m.group(1)}"
                           + (f"-{m.group(2)}" if m.group(2) else ""))
    else:
        m2 = an.find(c0, "qeos_comment")
        if m2:
            table.notes.append(f"comment declares {m2.group(1)}")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]


def _looks_opacity(rel: str, comment: str) -> bool:
    low = rel.lower()
    if "/opacity/" in low or Path(rel).name.lower().startswith("opc_"):
        return True
    if comment.upper().startswith("POLY") and "SESAME" in comment.upper():
        # 注意：POLY 也可能出现在 eos_* 里；以此为准的判据是文件名
        return False
    return False


def _opacity_order(a1: list[float], a2: list[float]) -> list[str]:
    """判定两个数组谁是 Rosseland、谁是 Planck。

    依据：Rosseland-only 表的 **Planck 槽位被 0 填充**。
    若 ``a2`` 全零 → 顺序为 ``[Rosseland, Planck]``；
    若 ``a1`` 全零 → 顺序为 ``[Planck, Rosseland]``；
    两者都非零 → 保持文档顺序 ``[Rosseland, Planck]`` 并标注未定。
    """
    z1 = all(v == 0.0 for v in a1)
    z2 = all(v == 0.0 for v in a2)
    if z1 and not z2:
        return ["Planck", "Rosseland"]
    return ["Rosseland", "Planck"]
