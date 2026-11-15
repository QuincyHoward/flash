"""F4b —— FEOS 原生表（``*.feos``）解析器（布局已由源码定案）。

权威依据
--------
``feos/src/FEOS/Code/FE-01_TABTOOLS.C`` ``write_FEOS_format``（196–355 行）。
三方实测一致：gen_eos_op/feos 产物（Al/SiO2/Au）+ matter++ 全部 ``.feos``
（Al/B/Cr 等 29 个）+ C 源码。此前"数据块列序未定"（风险 R3）**已废除**。

布局（write_FEOS_format）::

    行 0（10 数）: [FileVersion, NRho_decl, NT_decl, Nelements,
                    Tcalclimit, Rhocalclimit, RhoRef, TRef, B0, SESAME#]
    行 1（10 数）: [ElectronOffset, IonOffset, Ecoh, ss_n, ss_m,
                    ss_A, ss_B, Atot, Ztot, Xtot]
    连续流: A[]/Z[]/X[]（各 Nelements 个）
         -> rho 网格（NRho_decl 个，**首点 = Qstart = 0.0 前导哨兵**）
         -> T 网格（NT_decl 个，首点同上）
         -> 16 个二维块（T 外循环、rho 内循环 = T-major）:
            P,E,S,F | Pe,Ee,Se,Fe | Pi,Ei,Si,Fi | PTF,ETF,STF,FTF
            （每块 NRho_decl x NT_decl，含哨兵行列）
         -> Qtot（同形状）
         -> Q（ne 个元素按 **k 最内层交错**: 流序 = for j, for i, for k）

计数公式（全文件数值总数，含两行头部）::

    10 + 10 + 3*ne + NR_decl + NT_decl + (17 + ne) * NR_decl * NT_decl

单位（FEOS 原生，cgs + eV，本模块不换算）:
压强 dyn/cm2；比能/自由能 erg/g；熵 erg/g/eV；rho g/cm3；T eV；
Qtot/Q 无量纲（平均电离度）。

网格语义: ``NR_decl/NT_decl`` = 真实点数 + 1（哨兵行/列计入声明值）；
``decode()`` 返回完整网格（含哨兵），``parse_all`` 输出的 ParsedTable
轴与字段已修剪为严格正的真实网格。

注: matter++ 的 "Inverted EOS Boundaries (nr x ne)" 展示来自 ShowEOS
控制台输出其伴随反演表（``.301`` 族，mpqeos 解析器），不在 ``.feos`` 本体。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ..core.numbers import fortran_numbers as fn
from ..core.text.errors import ParseError
from ..core.text.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "HEADER_FIELDS", "LINE1_FIELDS",
           "FEOS_BLOCKS", "FeosTable", "decode", "find_sibling_301",
           "grid_length", "positive_indices"]

FAMILY = "feos_native"

#: 行 0 的 10 个字段（FE-01_TABTOOLS.C 222–223 行）
HEADER_FIELDS = (
    "file_version", "nrho_decl", "nt_decl", "nelements",
    "tcalc_limit", "rhocalc_limit", "rho_ref", "t_ref", "bulk_modulus",
    "sesame_no",
)

#: 行 1 的 10 个参数（FE-01_TABTOOLS.C 225–226 行）
LINE1_FIELDS = (
    "electron_offset", "ion_offset", "ecoh",
    "ss_n", "ss_m", "ss_A", "ss_B",
    "atot", "ztot", "xtot",
)

#: 16 个二维块写出序（FE-01_TABTOOLS.C 254–340 行；T 外循环、rho 内循环）
FEOS_BLOCKS = (
    "P", "E", "S", "F",
    "Pe", "Ee", "Se", "Fe",
    "Pi", "Ei", "Si", "Fi",
    "PTF", "ETF", "STF", "FTF",
)

#: 各字段原生单位（cgs + eV）
FIELD_UNITS: Dict[str, str] = {
    **{n: "dyn/cm2" for n in ("P", "Pe", "Pi", "PTF")},
    **{n: "erg/g" for n in ("E", "Ee", "Ei", "ETF", "F", "Fe", "Fi", "FTF")},
    **{n: "erg/g/eV" for n in ("S", "Se", "Si", "STF")},
    **{n: "-" for n in ("Qtot",)},
}


@dataclass
class FeosTable:
    """一张已解码的 .feos 表（网格含 Qstart=0.0 前导哨兵）。

    ``nrho/nt`` = 头部声明值（= 真实点数 + 1）；``rho/t/blocks/qtot/q``
    均为完整网格（含哨兵行/列），T-major 一维扁平。
    """
    path: str
    file_version: float
    nrho: int
    nt: int
    nelements: int
    tcalc_limit: float
    rhocalc_limit: float
    rho_ref: float
    t_ref: float
    bulk_modulus: float
    sesame_no: int
    electron_offset: float
    ion_offset: float
    ecoh: float
    softsphere: tuple
    atot: float
    ztot: float
    xtot: float
    a: List[float]
    z: List[float]
    x: List[float]
    rho: List[float]                       # g/cm^3，NRho_decl 个
    t: List[float]                         # eV，NT_decl 个
    blocks: Dict[str, List[float]]         # name -> flat，T-major (nt*nrho)
    qtot: List[float]                      # flat，T-major
    q: Dict[int, List[float]]              # 元素序号(0-based) -> flat


def grid_length(seq, start: int, declared: int) -> int:
    """单调前缀定长辅助（防御性校验用，行为兼容保留）。

    FEOS 网格的 ``0.0`` 哨兵在**前导**（``makeRTPointArray`` 把
    ``array[0] = Qstart`` 写进网格首点，声明 NR/NT = 真实点数 + 1）。
    确定性布局已由 :func:`decode` 按声明维度直接切分，不再依赖猜测；
    本函数仅保留作防御性辅助：从 ``start`` 起取最长严格递增前缀
    ``run``，仅当 ``run >= 2`` 且落在 ``declared-2 .. declared-1`` 窗口内
    才采信；否则退回 ``min(declared, n-start)``（不把非单调序列裁短）。
    """
    n = len(seq)
    if start >= n:
        return 0
    run = 1
    i = start + 1
    while i < n and seq[i] > seq[i - 1]:
        run += 1
        i += 1
    if run >= 2 and declared - 2 <= run < declared:
        return run
    return min(declared, n - start)


def positive_indices(t_axis: List[float], rho_axis: List[float]):
    """返回严格正的 T / rho 索引（前导 0.0 哨兵修剪）。"""
    t_idx = [j for j, tv in enumerate(t_axis) if tv > 0]
    r_idx = [i for i, rv in enumerate(rho_axis) if rv > 0]
    return t_idx, r_idx


def decode(path: str | Path) -> FeosTable:
    """按 write_FEOS_format 布局确定性解码（单一权威实现）。"""
    src = Path(path)
    text = src.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) < 3:
        raise ParseError(f"{src.name}: 文件过短，不是合法 .feos", path=src.name)

    h0 = fn.extract_numbers(lines[0])
    if len(h0) != 10:
        raise ParseError(f"{src.name}: 头部行应有 10 个数，实得 {len(h0)}",
                         path=src.name, header_raw=lines[0])
    h1 = fn.extract_numbers(lines[1])
    if len(h1) != 10:
        raise ParseError(f"{src.name}: 参数行应有 10 个数，实得 {len(h1)}",
                         path=src.name, header_raw=lines[1])
    rest = fn.extract_numbers("\n".join(lines[2:]))

    nrho_decl, nt_decl = int(round(h0[1])), int(round(h0[2]))
    ne = int(round(h0[3]))
    n2d = nrho_decl * nt_decl
    if not (2 <= nrho_decl <= 50000 and 2 <= nt_decl <= 50000 and 1 <= ne <= 32):
        raise ParseError(
            f"{src.name}: 维度不合理 nrho={nrho_decl} nt={nt_decl} ne={ne}",
            path=src.name, header_raw=lines[0])

    def take(n: int, what: str) -> List[float]:
        nonlocal pos
        chunk = rest[pos:pos + n]
        if len(chunk) != n:
            raise ParseError(
                f"{src.name}: 读取 {what} 时数值不足（需要 {n}，剩余 "
                f"{len(rest) - pos}）", path=src.name)
        pos += n
        return chunk

    pos = 0
    a = take(ne, "A[]")
    z = take(ne, "Z[]")
    x = take(ne, "X[]")
    rho = take(nrho_decl, "rho 网格")
    t = take(nt_decl, "T 网格")
    blocks = {name: take(n2d, f"块 {name}") for name in FEOS_BLOCKS}
    qtot = take(n2d, "Qtot")
    # Q 按 k 最内层交错（FE-01_TABTOOLS.C 348–353: for j, for i, for k）
    qstream = take(n2d * ne, "Q[]")
    q = {k: [qstream[idx * ne + k] for idx in range(n2d)] for k in range(ne)}

    expected_rest = 3 * ne + nrho_decl + nt_decl + (17 + ne) * n2d
    if pos != len(rest) or pos != expected_rest:
        raise ParseError(
            f"{src.name}: 数值总数不守恒（消费 {pos}，实有 {len(rest)}，"
            f"公式 {expected_rest}）—— 布局与 write_FEOS_format 不符",
            path=src.name)

    return FeosTable(
        path=str(src), file_version=h0[0], nrho=nrho_decl, nt=nt_decl,
        nelements=ne, tcalc_limit=h0[4], rhocalc_limit=h0[5],
        rho_ref=h0[6], t_ref=h0[7], bulk_modulus=h0[8],
        sesame_no=int(round(h0[9])),
        electron_offset=h1[0], ion_offset=h1[1], ecoh=h1[2],
        softsphere=tuple(h1[3:7]), atot=h1[7], ztot=h1[8], xtot=h1[9],
        a=a, z=z, x=x, rho=rho, t=t, blocks=blocks, qtot=qtot, q=q)


def find_sibling_301(path: str | Path, relpath: str) -> Path | None:
    """找同目录下的 ``.301`` 兄弟文件（用于 NR/NT 交叉校验）。

    实测命名有两种：``Al.feos`` ↔ ``FEOS/Al.feos.301``（**全名 + .301**）、
    ``B.feos`` ↔ ``B.301``（**主干 + .301**）—— 两种都要试。
    """
    p = Path(path)
    names = [p.name + ".301", p.stem + ".301"]
    for nm in names:
        for d in (p.parent / "FEOS", p.parent):
            c = d / nm
            if c.exists():
                return c
    return None


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None) -> list[ParsedTable]:
    """解码并组装 ParsedTable（轴/字段已修剪哨兵，16 块 + Qtot + Q 全解码）。"""
    doc = read_text(path)
    rel = relpath or doc.path.name

    tbl = decode(path)
    nr_real, nt_real = tbl.nrho - 1, tbl.nt - 1
    t_idx, r_idx = positive_indices(tbl.t, tbl.rho)

    def trim_flat(flat: List[float]) -> List[float]:
        return [flat[j * tbl.nrho + i] for j in t_idx for i in r_idx]

    fields: Dict[str, List[float]] = {k: trim_flat(v)
                                      for k, v in tbl.blocks.items()}
    field_units: Dict[str, str] = {k: FIELD_UNITS[k] for k in tbl.blocks}
    fields["Qtot"] = trim_flat(tbl.qtot)
    field_units["Qtot"] = "-"
    for k, flat in tbl.q.items():
        fields[f"Q{k}"] = trim_flat(flat)
        field_units[f"Q{k}"] = "-"
    shape = (len(t_idx), len(r_idx))

    table = ParsedTable(
        table_key=f"FEOS_{tbl.sesame_no}",
        kind="EOS_TOTAL",
        family=FAMILY,
        source_relpath=rel,
        table_id=tbl.sesame_no,
        header_raw=doc.lines[0],
        layout_rule="F4/FEOS-native: write_FEOS_format 源码布局"
                    "（10+10 头 + 3ne 组成 + 哨兵网格 + 16 块 + Qtot + Q 交错）",
    )
    table.axes["rho"] = [tbl.rho[i] for i in r_idx]
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = False
    table.axes["Te"] = [tbl.t[j] for j in t_idx]
    table.axis_units["Te"] = "eV"
    table.axis_log10["Te"] = False
    table.fields = fields
    table.field_shape = {k: shape for k in fields}
    table.field_units = field_units
    table.unit_source = "format:FEOS (cgs + eV)，原生单位未换算"

    table.n_numbers_seen = (20 + 3 * tbl.nelements + tbl.nrho + tbl.nt
                            + (17 + tbl.nelements) * tbl.nrho * tbl.nt)
    table.n_numbers_expected = table.n_numbers_seen

    table.notes.append(
        f"行0 字段: " + ", ".join(
            f"{k}={v:g}" for k, v in zip(HEADER_FIELDS, (
                tbl.file_version, tbl.nrho, tbl.nt, tbl.nelements,
                tbl.tcalc_limit, tbl.rhocalc_limit, tbl.rho_ref, tbl.t_ref,
                tbl.bulk_modulus, tbl.sesame_no)))
    )
    table.notes.append(
        "行1 参数: " + ", ".join(
            f"{k}={v:g}" for k, v in zip(LINE1_FIELDS, (
                tbl.electron_offset, tbl.ion_offset, tbl.ecoh,
                *tbl.softsphere, tbl.atot, tbl.ztot, tbl.xtot)))
    )
    table.notes.append(
        f"计数公式闭合: 20 + 3*{tbl.nelements} + {tbl.nrho} + {tbl.nt} + "
        f"(17+{tbl.nelements})*{tbl.nrho}*{tbl.nt} = {table.n_numbers_expected}")
    table.notes.append(
        f"网格: 声明 {tbl.nt}x{tbl.nrho}（含 Qstart=0.0 前导哨兵）→ "
        f"真实 {shape[0]}x{shape[1]}（哨兵已修剪）")
    if (len(t_idx), len(r_idx)) != (nt_real, nr_real):
        table.notes.append(
            f"⚠️ 非正轴点数与 declared-1 不符: T {len(t_idx)}/{nt_real}, "
            f"rho {len(r_idx)}/{nr_real}")
    table.notes.append(
        "16 块 + Qtot + Q 已解码（FE-01_TABTOOLS.C::write_FEOS_format 定案，"
        "R3 已废除）；Q 按 k 最内层交错还原")

    # 压力反演电离度的简并角落越界（低 T × 低 rho 角点，FEOS 已知局限）
    zb_max, zb_min = max(fields["Qtot"]), min(fields["Qtot"])
    if zb_max > tbl.ztot + 1e-9 or zb_min < -1e-9:
        table.notes.append(
            f"⚠️ 压力反演电离度简并角落越界: Qtot ∈ [{zb_min:.4g}, {zb_max:.4g}] "
            f"(Ztot={tbl.ztot:.4g}) —— FEOS 压力反演在低 T × 低 rho 角点的"
            f"已知病态（仅热力学自洽，非光谱级电离分布）")

    # 与 .301 兄弟文件交叉校验 NR/NT
    sib = find_sibling_301(path, rel)
    if sib is not None:
        sh = fn.extract_numbers(sib.read_text(encoding="utf-8",
                                              errors="replace").splitlines()[0])
        if len(sh) == 4:
            snr, snt = int(round(sh[2])), int(round(sh[3]))
            if (snr, snt) == (tbl.nrho, tbl.nt):
                table.notes.append(
                    f"✓ 与兄弟文件 {sib.name} 的 NR/NT=({tbl.nrho},{tbl.nt}) 一致")
            else:
                table.notes.append(
                    f"⚠️ 与兄弟文件 {sib.name} 的 NR/NT=({snr},{snt}) **不一致**"
                )
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
