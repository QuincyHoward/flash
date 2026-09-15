"""F4b —— FEOS 原生表（``*.feos``）解析器。

格式（实测 + 与 ``.301`` 兄弟文件交叉校验）
------------------------------------------
行 0（**10 个数**）—— 字段含义已用 ``.301`` 兄弟文件**独立验证**::

    [Z, NR, NT, c1, c2, c3, rho0, T_ref[eV], B0, SESAME#]

交叉校验证据（这是最硬的证据）::

    mat_B/B.feos   L0 = [12.06, 123, 101, 1.0, 1e-4, 1e-50, 2.34, 0.02585257, 1.85e12, 104005]
    mat_B/B.301    hdr = [1040050301, 2.34, 123, 101]     -> NR=123 / NT=101 ✓✓
    mat_Al-1.0/Al.feos L0 = [12.06, 192, 69, ..., 2.7, 0.02585257, 7.5e11, 3717]
    mat_Al-1.0/FEOS/Al.feos.301 hdr = [37170301, 2.7, 192, 69]  -> NR=192 / NT=69 ✓✓

行 1 = 10 个参数（部分已解：``A``、``Z``、…）。
行 2 起：``[A, Z, ...]`` 之后紧跟 **rho 网格**（与 ``.301`` 的 R 数组逐值一致）。

⚠️ 诚实声明（风险 R3）
---------------------
`FEOS-Package-Documentation2016.pdf` §16.2 的正文受 PDF 文本抽取的连字/断词伪影影响
（``F ormat``/``t able``），无法可靠还原**每个字段的语义与数据块列序**。
因此本解析器：
* **完全解码** 行 0 的 10 个字段（有 ``.301`` 交叉验证）；
* **定位并解码** rho / T 网格；
* 其余数值按原样存入 ``raw_values`` 并标注待定 —— **不猜测列语义**。
真正的数据块列序留待阶段 B 或人工对照 PDF 定案。
"""

from __future__ import annotations

from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.errors import ParseError
from ..core.textio import read_text
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "HEADER_FIELDS", "find_sibling_301",
           "grid_length"]

FAMILY = "feos_native"


def grid_length(seq, start: int, declared: int) -> int:
    """**单调性驱动**地确定网格真实长度。

    FEOS 头部声明的 ``NR``/``NT`` 实测可能比真实网格多 1（尾部含一个
    ``0.0`` 哨兵）。盲切会把哨兵并入网格，导致轴非单调 —— 进而破坏
    插值、等温线与雨贡纽拟合。

    策略：从 ``start`` 起取最长**严格递增**前缀 ``run``。仅当
    ``run`` 是**有效网格长度**（``>= 2``）且落在 ``declared - 2 .. declared - 1``
    这个"差一两个点"的窗口内时，才采信 ``run``；否则退回 ``declared``
    （无法判定时保持历史行为，绝不把非单调序列裁得更短）。
    """
    n = len(seq)
    if start >= n:
        return 0
    run = 1
    i = start + 1
    while i < n and seq[i] > seq[i - 1]:
        run += 1
        i += 1
    # ``run >= 2`` 排除"首对即递减"（那是格式不同，不是哨兵）
    if run >= 2 and declared - 2 <= run < declared:
        return run
    return min(declared, n - start)

#: 行 0 的 10 个字段名（前 3 个与末 2 个已由 ``.301`` 交叉验证）
HEADER_FIELDS = (
    "Z", "NR", "NT", "c1", "c2", "c3", "rho0", "T_ref_eV", "B0", "sesame_no",
)


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
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = doc.lines
    if len(lines) < 3:
        raise ParseError("file too short for FEOS native", path=rel)

    h0 = fn.extract_numbers(lines[0])
    if len(h0) != 10:
        raise ParseError(f"FEOS native header must have 10 numbers, got {len(h0)}",
                         path=rel, header_raw=lines[0])
    hdr = dict(zip(HEADER_FIELDS, h0))
    nr, nt = int(round(hdr["NR"])), int(round(hdr["NT"]))
    if not (2 <= nr <= 50000 and 2 <= nt <= 50000):
        raise ParseError(f"FEOS native implausible dims nr={nr} nt={nt}",
                         path=rel, header_raw=lines[0])

    params = fn.extract_numbers(lines[1])
    rest = fn.extract_numbers("\n".join(lines[2:]))

    table = ParsedTable(
        table_key=f"FEOS_{int(round(hdr['sesame_no']))}",
        kind="EOS_TOTAL",
        family=FAMILY,
        source_relpath=rel,
        table_id=int(round(hdr["sesame_no"])),
        header_raw=lines[0],
        layout_rule="F4/FEOS-native: L0=10 字段（已解码）+ rho/T 网格 + 数据块（列序待定）",
    )
    table.n_numbers_seen = 10 + len(params) + len(rest)
    table.n_numbers_expected = None  # 数据块列序待定 → 无法给出精确公式

    # 行 2 起的前 4 个数是 [A, Z, ?, ?]，其后紧接 rho 网格
    lead = rest[:4]
    if len(rest) >= 4 + nr:
        # ⚠️ 不能用头部声明的 NR/NT **盲切**：实测 ``Al.feos`` 声明 NR=192，
        # 但真实 rho 网格只有 **191** 点，盲切会把随后的 ``0.0`` 吞进
        # rho 尾部、把 payload 首值吞进 Te 尾部（两个轴同时被污染，
        # 表现为"轴非单调"）。改用**严格单调性**作为网格终止判据。
        rho_n = grid_length(rest, 4, nr)
        rho = rest[4:4 + rho_n]
        after = rest[4 + rho_n:]
        te_n = grid_length(after, 0, nt)
        T_guess = after[:te_n]
        payload = after[te_n:]
        table.axes["rho"] = rho
        table.axis_units["rho"] = "g/cm3"
        table.axis_log10["rho"] = False
        table.axes["Te"] = [t for t in T_guess]
        table.axis_units["Te"] = "eV"
        table.axis_log10["Te"] = False
        table.notes.append(
            f"由 [A,Z,..] 之后定位 rho 网格（{len(rho)} 点，声明 {nr}）"
            f"与 T 网格（{len(T_guess)} 点，声明 {nt}）；lead={lead}"
        )
        if rho_n != nr or te_n != nt:
            table.notes.append(
                f"⚠️ 网格实际长度与头部声明不符：rho {rho_n}/{nr}, "
                f"Te {te_n}/{nt} —— 已按单调性裁到真实长度（声明值疑似含"
                f"尾部哨兵点）"
            )
        if payload:
            table.fields["raw_values"] = payload
            table.field_shape["raw_values"] = (len(payload),)
            table.field_units["raw_values"] = "unknown"
            table.notes.append(
                f"其余 {len(payload)} 个数值按原样保存 —— **数据块列序未定**"
                f"（FEOS PDF §16.2 正文受抽取伪影影响，见模块文档 R3）"
            )
    else:
        table.notes.append("⚠️ 行 2 起的数值不足以定位完整 rho 网格")

    # 与 .301 兄弟文件交叉校验 NR/NT
    sib = find_sibling_301(path, rel)
    if sib is not None:
        sh = fn.extract_numbers(sib.read_text(encoding="utf-8",
                                              errors="replace").splitlines()[0])
        if len(sh) == 4:
            snr, snt = int(round(sh[2])), int(round(sh[3]))
            if (snr, snt) == (nr, nt):
                table.notes.append(f"✓ 与兄弟文件 {sib.name} 的 NR/NT=({nr},{nt}) 一致")
            else:
                table.notes.append(
                    f"⚠️ 与兄弟文件 {sib.name} 的 NR/NT=({snr},{snt}) **不一致**"
                )

    table.unit_source = "format:FEOS (cgs + eV)"
    table.notes.append(
        "行0 字段: " + ", ".join(f"{k}={v:g}" for k, v in hdr.items())
    )
    table.notes.append(f"行1 参数(10): {params}")
    return [table]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T)[0]
