"""F4a —— MPQeos / FEOS 的 SESAME 包装表（``.301`` / ``.304`` / ``.305``）。

格式（实测）
------------
行 1：``Id  Density  NR  NT``

payload::

    [R(NR)] [T(NT)] [P(NR*NT) GPa] [E(NR*NT) MJ/kg] [Z(NR*NT)]

**计数守恒**：``4 + NR + NT + 3*NR*NT``

★ 两个实测陷阱
--------------
1. **表头不可定宽切分**：ID 字段宽 16 或 17 列**不定** —— 16 与 15 的固定切分都会切出
   污染字段（如 ``'2.70000000e+00 1'``）。表头全为空格分隔的正数、无紧邻负数问题，
   故交给 **L2 正则**；payload 才用**逐文件推断**的定宽 ``W = len(line)/4``。
2. **字段宽逐文件不同**：``mat_Al-1.0/FEOS/Al.feos.301`` payload 行 60 字符（``W=15``），
   而 ``mat_He/Untitled.304`` 是 64 字符（``W=16``）。

实测基准：``Al.feos.301`` 头 ``37170301 2.7 192 69`` → 192+69+3·192·69 = **40005** ✓

单位换算（``Multi1D++`` 自动识别 ``.301/.304/.305`` 并换算）
----------------------------------------------------------
``SESAME`` 库用 压强 GPa / 能量 MJ/kg / 密度 g/cc / 温度 Kelvin；
而 MULTI 内部用 Mbar / Mbar*cm³/g。换算：**1 GPa = 1e-2 Mbar**、
**1 MJ/kg = 1e-2 Mbar*cm³/g**。
"""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..core import fixedwidth as fw
from ..core import fortran_numbers as fn
from ..core.errors import CountMismatch, ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "KIND_BY_EXT"]

FAMILY = "mpqeos"

#: 扩展名 → KIND（``.301`` 总表 / ``.304`` 电子 / ``.305`` 离子）
KIND_BY_EXT = {".301": "EOS_TOTAL", ".304": "EOS_ELECTRON", ".305": "EOS_ION"}


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = [ln for ln in doc.lines if ln.strip()]
    if len(lines) < 2:
        raise ParseError("file too short for F4/MPQeos", path=rel)

    # 表头：4 个数（L2 正则 —— 定宽不可靠）
    hdr = fn.extract_numbers(lines[0])
    if len(hdr) != 4:
        raise ParseError(f"MPQeos header must have 4 numbers, got {len(hdr)}",
                         path=rel, header_raw=doc.lines[0])
    table_id = int(round(hdr[0]))
    density = hdr[1]
    nr, nt = int(round(hdr[2])), int(round(hdr[3]))
    if not (2 <= nr <= 50000 and 2 <= nt <= 50000):
        raise ParseError(f"MPQeos implausible dims nr={nr} nt={nt}",
                         path=rel, header_raw=doc.lines[0])

    payload = lines[1:]
    width = fw.infer_payload_width(payload, fw.FIELDS_MULTI)
    n_blank = sum(1 for ln in doc.lines[1:] if not ln.strip())

    values: list[float] = []
    for ln in payload:
        if fn.has_letters(ln):
            raise ParseError(f"unexpected text in MPQeos payload: {ln!r}",
                             path=rel, header_raw=doc.lines[0])
        values.extend(fw.slice_values(ln, width=width))

    n2 = nr * nt
    expected = 4 + nr + nt + 3 * n2
    if 4 + len(values) != expected:
        raise CountMismatch(4 + len(values), expected, path=rel, header_raw=doc.lines[0])

    p = 0
    R = values[p:p + nr]; p += nr
    T_K = values[p:p + nt]; p += nt
    P_GPa = values[p:p + n2]; p += n2
    E_MJkg = values[p:p + n2]; p += n2
    Z = values[p:p + n2]; p += n2

    ext = Path(rel).suffix.lower()
    kind = KIND_BY_EXT.get(ext, "EOS_TOTAL")

    table = ParsedTable(
        table_key=f"{kind}_{table_id}",
        kind=kind,
        family=FAMILY,
        source_relpath=rel,
        table_id=table_id,
        header_raw=doc.lines[0],
        layout_rule=f"F4/MPQeos: 4 + nr + nt + 3*nr*nt (W={width})",
    )
    table.n_numbers_seen = 4 + len(values)
    table.n_numbers_expected = expected

    table.axes["rho"] = R
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = False
    table.axes["Te"] = [t * config.EV_PER_K for t in T_K]
    table.axis_units["Te"] = "eV"
    table.axis_log10["Te"] = False

    # GPa -> Mbar ；MJ/kg -> Mbar*cm3/g
    table.fields["P"] = [v * config.MBAR_PER_GPA for v in P_GPa]
    table.field_shape["P"] = (nt, nr)
    table.field_units["P"] = "Mbar"
    table.field_log10["P"] = False

    table.fields["E"] = [v * config.MBAR_CM3_G_PER_MJ_KG for v in E_MJkg]
    table.field_shape["E"] = (nt, nr)
    table.field_units["E"] = "Mbar*cm3/g"
    table.field_log10["E"] = False

    table.fields["Z"] = Z
    table.field_shape["Z"] = (nt, nr)
    table.field_units["Z"] = "1"
    table.field_log10["Z"] = False

    table.unit_source = "format:F4 (GPa->Mbar, MJ/kg->Mbar*cm3/g, T Kelvin->eV)"
    table.notes.append(
        f"density={density} W={width} 字段宽逐文件推断（同族 Al=15 / He=16）"
    )
    table.notes.append("表头用 L2 正则解析（ID 列宽 16/17 不定，定宽会切错）")
    table.notes.append(f"n_blank_in_payload={n_blank}")
    n_bad = fn.count_nonfinite(values)
    if n_bad:
        table.notes.append(
            f"⚠️ payload 含 {n_bad} 个非有限值（``inf``/``nan``）—— "
            f"源数据用 MSVC 的 ``1.#INF`` 格式打印了溢出，属**源数据缺陷**，已按原样保留"
        )
    # ★ 第 5 段按 docx 应为 Z（电离度），但实测含**负值且量级异常** →
    # 段语义待核，必须显式告警而不是悄悄当成电离度用。
    finite_z = [v for v in Z if v == v and abs(v) != float("inf")]
    if finite_z:
        neg = sum(1 for v in finite_z if v < 0)
        if neg:
            table.notes.append(
                f"⚠️ 第 5 段（docx 记为 Z 电离度）含 {neg}/{len(finite_z)} 个**负值**，"
                f"值域 [{min(finite_z):.4g}, {max(finite_z):.4g}] —— 与「电离度」语义不符，"
                f"该段语义**待核**（风险 R3）；未用于任何物理推断"
            )
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
