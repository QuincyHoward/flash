# -*- coding: utf-8 -*-
"""IONMIX ``.cnr`` (late-1986 CONRAD 格式) 数据表只读内核。

格式权威来源
============
``.cnr`` **不在** IONMIX 用户指南中（该指南只描述 ``.cn4``，见
``ionmix/ionmix/docs/IONMIX用户指南.md`` §5.4，全文检索 "cnr" 零命中）。
因此本模块的唯一一手依据仍是本地源码::

    ionmix/ionmix/src/Ionmix/abjt_03.f
        SUBROUTINE OWTF (line 4510)
            isw(8) == 1 或 12 或 13 分支 (line 4598–4621)
                → 写 unit 8，注释原文:
                  "write output in 'original' (i.e., late 1986)
                   CONRAD-acceptable format"

对应的头部格式语句::

    980 format (a80)              <- header 字符串（一行 80 字符）
    981 format (4e12.6,i12)       <- 关键: 4 个 e12.6 + 1 个 i12 **同一行**
    991 format (4e12.6)           <- 数据区

⚠️ 与 ``.cn4`` 的根本差异（本文档最重要的事实）
------------------------------------------------
``.cn4`` 第 4 行是 ``ngrups`` **独占一行**（``982 format (i12)``）。

``.cnr`` 第 4 行是 ``981 format (4e12.6,i12)``，即::

    dlgden  log10(rho_0)  dlgtmp  log10(T_0)  ngrups
    └──────────── 4 × e12.6 ────────────┘  └─ i12 ─┘

实测样例（``al-imx-001.cnr``）::

    0.250000E+000.190000E+020.250000E+000.000000E+00          30
    └── 0.25 ──┘└─ 19.0 ─┘└─ 0.25 ─┘└─ 0.0 ──┘          └ 30 ┘

即前 4 个数值是**网格生成参数**（对数密度步长、密度起点 log10、对数温度
步长、温度起点 log10），**不是数据块**；``ngrups`` 取该行**末尾 12 列**。

数据块顺序（源码 line 4600–4620 逐条 ``write(8,991)``）
-------------------------------------------------------
与 ``.cn4`` 完全不同 —— 只有 7 个数据区，且**没有** 12 个 EOS 二维场::

    块 1 : densne/densnn = zbar        (ntemp*ndens)         无量纲
    块 2 : enrgy                       (ntemp*ndens)         J/g
    块 3 : op2tr  2-T Rosseland        (ntrad*ntemp*ndens)   cm^2/g
    块 4 : op2tp  2-T Planck           (ntrad*ntemp*ndens)   cm^2/g
    块 5 : engrup(1..ngrups+1)         能群边界               eV
    块 6 : orgp   Rosseland 群不透明度  (ngrups*ntemp*ndens)  cm^2/g
    块 7 : opgpe  Planck 发射群不透明度  (ngrups*ntemp*ndens)  cm^2/g

``ntrad`` **不在头部存储** —— 必须由计数守恒反解::

    rem = N - [ 2*ntemp*ndens + (ngrups+1) + 2*ngrups*ntemp*ndens ]
    ntrad = rem / (2*ntemp*ndens)

本模块的诚实边界（严格遵守"不猜"）
----------------------------------
* ``ntrad`` 反解为**整数**时: 块 3/4 正常切分，标注 ``ntrad=<n>``。
* 反解为**非整数**时: 总计数仍闭合，但块 3/4 的切分点无法唯一确定
  → 块 3/4 整体标 ``unknown``，**不给出**伪造偏移。
* ``.cnr`` **无** EOS 的 12 个二维场（压力/比热/离子电子分量等全部缺失），
  因此**不能**用于 EOS 路径分析，也不能直接转 ``.cn4``。
* 两个格式的 ``ntemp``/``ndens`` 语义同为 (温度数, 密度数)，可直接比较。

计数守恒
--------
::

    expected = 2*ntemp*ndens + (ngrups+1) + 2*ngrups*ntemp*ndens + 2*ntrad*ntemp*ndens

实测不符即抛 :class:`CNRParseError` —— 不静默。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from .cn4_io import (
    CN4ParseError,
    ELEMENT_ATOMWT,
    FRAC_RE,
    FIXED_WIDTH,
    _parse_fixed_width,
    guess_atomwt,
)

# ── 头部标记（与 .cn4 共用 921/922 格式语句） ──────────────────────
_ATOMIC_MARK = "atomic"
_FRACTION_MARK = "fraction"


class CNRParseError(CN4ParseError):
    """``.cnr`` 解析失败（头部畸形 / 计数不闭合）。"""


# ── 块规格: (属性名, 显示标签, 单位, 是否随 ntrad 变化) ──────────────
CNR_BLOCK_SPEC: tuple[tuple[str, str, str, bool], ...] = (
    ("zbar",   "zbar",   "-",      False),   # 源码 line 4602
    ("enrgy",  "enrgy",  "J/g",    False),   # 源码 line 4604
    ("op2tr",  "op2tr",  "cm2/g",  True),    # 源码 line 4605（2-T Rosseland）
    ("op2tp",  "op2tp",  "cm2/g",  True),    # 源码 line 4607（2-T Planck）
    ("engrup", "engrup", "eV",     False),   # 源码 line 4609（群边界）
    ("orgp",   "orgp",   "cm2/g",  False),   # 源码 line 4611（群 Rosseland）
    ("opgpe",  "opgpe",  "cm2/g",  False),   # 源码 line 4613（群 Planck 发射）
)

#: ``.cnr`` 数据区块数（不含头部行）
CNR_N_BLOCKS = 7


@dataclass
class CNRTable:
    """``.cnr`` 文件的结构化数据容器（只读、可审计）。

    Attributes:
        filepath: 源文件路径。
        dlgden / rho0_log / dlgtmp / t0_log: 头部 981 行的 4 个网格参数。
            **网格语义推断见模块 docstring，标 ``units="inferred"``。**
        ntemp / ndens / ngrups: 网格与能群规模。
        ntrad: 2-T 不透明度表的辐射温度点数；``None`` 表示无法唯一确定。
        izgas / fracsp: 元素原子序数与数分数。
        blocks: 块名 → 扁平数值列表。``op2tr``/``op2tp`` 在 ``ntrad is None``
            时为空列表并进入 :attr:`unknown_blocks`。
        unknown_blocks: 无法唯一切分的块名元组（诚实标注，不猜）。
        raw_tail_values: 数据区全部原始数值（保底可审计）。
    """

    filepath: str
    dlgden: float
    rho0_log: float
    dlgtmp: float
    t0_log: float
    ntemp: int
    ndens: int
    ngrups: int
    ntrad: Optional[int]
    izgas: List[int] = field(default_factory=list)
    fracsp: List[float] = field(default_factory=list)
    blocks: dict = field(default_factory=dict)
    unknown_blocks: tuple = ()
    raw_tail_values: List[float] = field(default_factory=list)
    atomwt: Optional[List[float]] = None
    atomwt_source: str = "unavailable"
    notes: List[str] = field(default_factory=list)
    header_lines: List[str] = field(default_factory=list)

    # ── 便捷访问 ────────────────────────────────────────────────
    @property
    def basename(self) -> str:
        return os.path.basename(self.filepath)

    @property
    def ngases(self) -> int:
        return len(self.izgas)

    @property
    def n2d(self) -> int:
        """单个二维场（ntemp × ndens）的元素个数。"""
        return self.ntemp * self.ndens

    def field(self, name: str) -> List[float]:
        """取二维场（``zbar`` / ``enrgy``）的扁平值，缺失返回 ``[]``。"""
        return list(self.blocks.get(name, []))

    def group_opacity(self, name: str, ig: int) -> List[float]:
        """取第 ``ig`` 群（0-based）的三维不透明度切片（长度 ``ntemp*ndens``）。"""
        flat = self.blocks.get(name)
        if flat is None:
            return []
        start = ig * self.n2d
        return list(flat[start:start + self.n2d])

    def summary(self) -> str:
        lines = [
            f"CNRTable  {self.basename}",
            f"  species      : Z={self.izgas}  frac={self.fracsp}",
            f"  grid         : ntemp={self.ntemp}  ndens={self.ndens}"
            f"  => n2d={self.n2d}",
            f"  groups       : ngrups={self.ngrups}",
            f"  ntrad        : {self.ntrad if self.ntrad is not None else 'unknown'}",
            f"  header       : dlgden={self.dlgden} rho0_log={self.rho0_log}"
            f"  dlgtmp={self.dlgtmp} t0_log={self.t0_log}",
            f"  atomwt       : {self.atomwt} (source={self.atomwt_source})",
            f"  blocks       : {sorted(self.blocks)}",
        ]
        if self.unknown_blocks:
            lines.append(f"  UNKNOWN      : {list(self.unknown_blocks)}")
        for n in self.notes:
            lines.append(f"  note         : {n}")
        return "\n".join(lines)


def parse_cnr_header(lines: Sequence[str]) -> dict:
    """解析 ``.cnr`` 的前 4 行头部。

    Returns:
        dict: ``ntemp`` / ``ndens`` / ``ngrups`` / ``izgas`` / ``fracsp``
              / ``dlgden`` / ``rho0_log`` / ``dlgtmp`` / ``t0_log``
              / ``ngases`` / ``raw``

    Raises:
        CNRParseError: 头部缺行、缺标记、或 981 行不是 5 个字段。
    """
    if len(lines) < 4:
        raise CNRParseError(f".cnr 至少需要 4 行头部, 实际 {len(lines)} 行")

    # line 1: ntemp, ndens  (923 format: 2i10)
    try:
        toks = lines[0].split()
        ntemp, ndens = int(toks[0]), int(toks[1])
    except (IndexError, ValueError) as exc:
        raise CNRParseError(
            f".cnr 第 1 行应为 2 个整数 (2i10), 实际 {lines[0]!r}"
        ) from exc

    # line 2: " atomic #s of gases: " + 5i10  (921 format)
    if _ATOMIC_MARK not in lines[1].lower():
        raise CNRParseError(f".cnr 第 2 行缺少 'atomic #s of gases' 标记: {lines[1]!r}")
    tail2 = lines[1][20:] if len(lines[1]) > 20 else ""
    izgas = [int(t) for t in re.findall(r"\d+", tail2)]
    if not izgas:
        raise CNRParseError(f".cnr 第 2 行未解析出任何原子序数: {lines[1]!r}")

    # line 3: " relative fractions: " + 1p5e10.2  (922 format)
    if _FRACTION_MARK not in lines[2].lower():
        raise CNRParseError(f".cnr 第 3 行缺少 'relative fractions' 标记: {lines[2]!r}")
    fracsp = [float(t.replace("D", "E").replace("d", "e"))
              for t in FRAC_RE.findall(lines[2])]
    if not fracsp:
        raise CNRParseError(f".cnr 第 3 行未解析出任何丰度: {lines[2]!r}")

    # line 4: dlgden, log10(rho0), dlgtmp, log10(T0), ngrups
    #         (981 format: 4e12.6 + i12 —— 与 .cn4 的 982 i12 完全不同)
    line4 = lines[3].rstrip("\r\n")
    if len(line4) < 5 * FIXED_WIDTH:
        raise CNRParseError(
            f".cnr 第 4 行长度 {len(line4)} < 60 (需 5×12 列, 981 format): {line4!r}"
        )
    parsed = _parse_fixed_width(line4)
    if len(parsed) < 5:
        raise CNRParseError(
            f".cnr 第 4 行 (981 format 4e12.6,i12) 应含 5 个字段, 实得 {len(parsed)}: "
            f"{line4!r}"
        )
    dlgden, rho0_log, dlgtmp, t0_log = parsed[0], parsed[1], parsed[2], parsed[3]
    ngrups = int(round(parsed[4]))

    if len(izgas) != len(fracsp):
        raise CNRParseError(
            f"头部不一致: izgas 有 {len(izgas)} 项, fracsp 有 {len(fracsp)} 项"
        )
    for name, v in (("ntemp", ntemp), ("ndens", ndens)):
        if v <= 0:
            raise CNRParseError(f"{name}={v} 非正数")
    if ngrups < 0:
        raise CNRParseError(f"ngrups={ngrups} 为负")

    return {
        "ntemp": ntemp, "ndens": ndens, "ngrups": ngrups,
        "dlgden": dlgden, "rho0_log": rho0_log,
        "dlgtmp": dlgtmp, "t0_log": t0_log,
        "izgas": izgas, "fracsp": fracsp, "ngases": len(izgas),
        "raw": [lines[0], lines[1], lines[2], lines[3]],
    }


def solve_ntrad(ntemp: int, ndens: int, ngrups: int, n_values: int) -> Optional[int]:
    """由计数守恒反解 ``ntrad``。

    ``n_values = 2*n2d + (ngrups+1) + 2*ngrups*n2d + 2*ntrad*n2d``

    Returns:
        正整数 ``ntrad``；不能整除（无法唯一确定）时返回 ``None``。

    Raises:
        CNRParseError: 计数小于最小可能值（非 ``.cnr`` 或已损坏）。
    """
    n2d = ntemp * ndens
    fixed = 2 * n2d + (ngrups + 1) + 2 * ngrups * n2d
    rem = n_values - fixed
    if rem < 0:
        raise CNRParseError(
            f".cnr 计数不足: 实得 {n_values} < 最小可能 {fixed} "
            f"(ntemp={ntemp} ndens={ndens} ngrups={ngrups})"
        )
    denom = 2 * n2d
    if denom == 0:
        return None
    if rem % denom != 0:
        return None
    nt = rem // denom
    return nt if nt > 0 else None


def parse_cnr(filepath: str | os.PathLike, *,
              atomwt: Optional[Sequence[float]] = None) -> CNRTable:
    """解析一个 ``.cnr`` 文件为 :class:`CNRTable`。

    Args:
        filepath: ``.cnr`` 路径。
        atomwt: 可选原子量列表（权威来源应为同目录 ``ionmxinp``）。

    Raises:
        CNRParseError: 头部畸形或计数不闭合。
    """
    p = Path(filepath)
    text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) < 5:
        raise CNRParseError(f"{p.name}: 行数 {len(lines)} 不足 (需 >=5)")

    head = parse_cnr_header(lines)
    ntemp, ndens, ngrups = head["ntemp"], head["ndens"], head["ngrups"]
    n2d = ntemp * ndens

    # 数据区: 第 5 行起，按 4e12.6 逐行定宽切分
    vals: List[float] = []
    for ln in lines[4:]:
        vals.extend(_parse_fixed_width(ln))

    ntrad = solve_ntrad(ntemp, ndens, ngrups, len(vals))

    notes: List[str] = []
    unknown: tuple = ()
    blocks: dict = {}
    off = 0

    # 块 1: zbar (ntemp*ndens)
    blocks["zbar"] = vals[off:off + n2d]; off += n2d
    # 块 2: enrgy (ntemp*ndens)  [J/g]
    blocks["enrgy"] = vals[off:off + n2d]; off += n2d

    # 块 3/4: op2tr / op2tp  (各 ntrad*ntemp*ndens)
    if ntrad is not None:
        n_op2t = ntrad * n2d
        blocks["op2tr"] = vals[off:off + n_op2t]; off += n_op2t
        blocks["op2tp"] = vals[off:off + n_op2t]; off += n_op2t
    else:
        blocks["op2tr"] = []
        blocks["op2tp"] = []
        unknown = ("op2tr", "op2tp")
        notes.append(
            "ntrad 无法由计数守恒唯一确定（余数不被 2*ntemp*ndens 整除）"
            "→ op2tr/op2tp 切分点不确定，标 unknown（不猜）；"
            "engrup/orgp/opgpe 仍可从尾部反向定位"
        )

    # 块 5: engrup (ngrups+1)  [eV]
    n_eg = ngrups + 1
    if ntrad is not None:
        blocks["engrup"] = vals[off:off + n_eg]; off += n_eg
        # 块 6/7: orgp / opgpe (各 ngrups*ntemp*ndens)
        n_grp = ngrups * n2d
        blocks["orgp"] = vals[off:off + n_grp]; off += n_grp
        blocks["opgpe"] = vals[off:off + n_grp]; off += n_grp
    else:
        # 从尾部反向定位: opgpe, orgp, engrup 依次靠后
        n_grp = ngrups * n2d
        tail = vals[len(vals) - (n_grp * 2 + n_eg):] if len(vals) >= n_grp * 2 + n_eg else []
        if len(tail) == n_grp * 2 + n_eg:
            blocks["engrup"] = tail[:n_eg]
            blocks["orgp"] = tail[n_eg:n_eg + n_grp]
            blocks["opgpe"] = tail[n_eg + n_grp:]
        else:
            blocks["engrup"] = []
            blocks["orgp"] = []
            blocks["opgpe"] = []
            unknown = ("op2tr", "op2tp", "engrup", "orgp", "opgpe")

    # 原子量三级来源（不猜）
    src = "unavailable"
    aw: Optional[List[float]] = None
    if atomwt is not None:
        aw = [float(x) for x in atomwt]
        src = "user"
    else:
        auto = _read_atomwt_from_ionmxinp(p.parent, head["ngases"])
        if auto is not None:
            aw = auto
            src = "ionmxinp"
        else:
            auto = guess_atomwt(head["izgas"])
            if auto is not None:
                aw = auto
                src = "element_table"
    if aw is None:
        notes.append("原子量不可得（无 ionmxinp、元素表缺项）→ atomwt=unknown")

    # 网格语义说明（诚实标注推断性质）
    notes.append(
        "头部 981 行的 4 个值为网格生成参数: (dlgden, log10(rho0), dlgtmp, "
        "log10(T0))；其物理含义由源码 line 4609 的 write 语句位置推断，"
        "IONMIX 用户指南未文档化 .cnr 格式 → 标 inferred"
    )
    notes.append(
        ".cnr (late-1986 CONRAD) 不含 .cn4 的 12 个 EOS 二维场"
        "（压力/比热/离子电子分量），不可用于 EOS 路径分析"
    )

    return CNRTable(
        filepath=str(p),
        dlgden=head["dlgden"], rho0_log=head["rho0_log"],
        dlgtmp=head["dlgtmp"], t0_log=head["t0_log"],
        ntemp=ntemp, ndens=ndens, ngrups=ngrups, ntrad=ntrad,
        izgas=head["izgas"], fracsp=head["fracsp"],
        blocks=blocks, unknown_blocks=unknown,
        raw_tail_values=vals,
        atomwt=aw, atomwt_source=src,
        notes=notes,
        header_lines=head["raw"],
    )


def _read_atomwt_from_ionmxinp(dirpath: Path, ngases: int) -> Optional[List[float]]:
    """从同目录 ``ionmxinp`` 读取 ``atomwt(i) = ...``（权威来源）。"""
    import re as _re
    f = dirpath / "ionmxinp"
    if not f.exists():
        return None
    pat = _re.compile(
        r"atomwt\s*\(\s*(\d+)\s*\)\s*=\s*([-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?)"
    )
    found: dict = {}
    try:
        for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = pat.search(ln)
            if m:
                found[int(m.group(1))] = float(m.group(2).replace("D", "E").replace("d", "e"))
    except OSError:
        return None
    if not found:
        return None
    vals = [found.get(i) for i in range(1, ngases + 1)]
    if any(v is None for v in vals):
        return None
    return [float(v) for v in vals]  # type: ignore[arg-type]


def load_cnr(filepath: str | os.PathLike, *,
             atomwt: Optional[Sequence[float]] = None) -> CNRTable:
    """``parse_cnr`` 的兼容别名（与 ``load_cn4`` 命名一致）。"""
    return parse_cnr(filepath, atomwt=atomwt)


def load_cnr_dir(dirpath: str | os.PathLike) -> List[CNRTable]:
    """解析目录下所有 ``.cnr`` 文件。"""
    d = Path(dirpath)
    out: List[CNRTable] = []
    for name in sorted(os.listdir(d)):
        if name.lower().endswith(".cnr"):
            out.append(parse_cnr(d / name))
    return out


def expected_number_count(ntemp: int, ndens: int, ngrups: int,
                          ntrad: int) -> int:
    """``.cnr`` 块布局推导的数值总数（不含头部行）。"""
    n2d = ntemp * ndens
    return 2 * n2d + (ngrups + 1) + 2 * ngrups * n2d + 2 * ntrad * n2d
