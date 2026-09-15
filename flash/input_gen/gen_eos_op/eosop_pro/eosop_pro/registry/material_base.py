"""``material.base`` 解析 —— 「一物质一 h5」的**主索引**。

实测语法（251 个块，3805 行，utf-8）
------------------------------------
::

    MATERIAL MID9                      <- 块头；数字部分即 MID
    REM Gold modelled by tabulated ...  <- `REM` 注释
       A 196.97                         <- 标量键（数值）
       Z 79
       GammaG 3.1
       c0 0.306e6
       s 1.57
       Formula Au                       <- 文本键
       Name Gold
       RHO 19.32
       IonizationModel Constant
       EOS        mat_Au-1.0   AU_eos      <- 表引用键：<模块名> <文件名>
       PLANCK     mat_Au-1.0   AU_op03p
       ROSSELAND  mat_Au-1.0   AU_op03r
       NONLTE     mat_Au-1.0   AU_op03e
       ZEFF       mat_Au-1.0   AU_op03z

实测关键字频次：``A``/``Z``/``NAME``/``RHO`` 各 251、``FORMULA`` 245、
``PLANCK``/``ROSSELAND`` 各 236、``EOS`` 217、**``ZEFF`` 130**、``GAMMAG``/``C0``/``S`` 各 72、
``EEOS``/``IEOS`` 各 36。

注释：``REM`` 与 ``#``。块内空行忽略。MID<100 为 Ramis 公布材料，>10000 为用户材料。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from ..core import textio

__all__ = [
    "TABLE_KEYS",
    "SCALAR_KEYS",
    "TEXT_KEYS",
    "TableRef",
    "MaterialBaseEntry",
    "parse_material_base",
    "MaterialBase",
]

#: 「表引用」键 —— 值为 ``<模块名> <文件名>``
TABLE_KEYS = frozenset({
    "EOS", "IEOS", "EEOS", "PLANCK", "ROSSELAND", "NONLTE", "ZEFF",
    "EMS", "COLDOPACITY", "OPACITY", "MUGROUP",
})

#: 标量键
SCALAR_KEYS = frozenset({
    "A", "Z", "RHO", "GAMMA", "GAMMAG", "C0", "S", "TOLERANCE",
    "COLDTEMPERATURE", "COLDDENSITY", "REFERENCEPRESSURE",
    "SHEARMODLULS", "YIELDSTRENGTH", "POISSONSRATIO", "SURFACETENSION",
    "NUMBEROFELEMENTS",
})

#: 文本键
TEXT_KEYS = frozenset({
    "FORMULA", "NAME", "IONIZATIONMODEL", "NLTEMODEL", "IONEOSMODEL",
})

_RE_MATERIAL = re.compile(r"^\s*MATERIAL\s+(\S+)")
_RE_MID = re.compile(r"MID\s*(\d+)", re.I)


@dataclass
class TableRef:
    """一条表引用：``EOS mat_Au-1.0 AU_eos``。"""

    key: str          # EOS / PLANCK / ROSSELAND / NONLTE / ZEFF / ...
    module: str       # mat_Au-1.0
    file: str         # AU_eos

    @property
    def relpath(self) -> str:
        return f"{self.module}/{self.file}"

    @property
    def kind(self) -> str:
        """把键映射到 h5 的 KIND 名。"""
        return {
            "EOS": "EOS_TOTAL", "IEOS": "EOS_ION", "EEOS": "EOS_ELECTRON",
            "PLANCK": "PLANCK", "ROSSELAND": "ROSSELAND", "NONLTE": "NONLTE",
            "ZEFF": "ZEFF", "EMS": "EMISSIVITY", "COLDOPACITY": "COLDOPACITY",
        }.get(self.key.upper(), self.key.upper())


@dataclass
class MaterialBaseEntry:
    """一个 ``MATERIAL`` 块。"""

    mid: int
    raw_name: str = ""
    name: str | None = None
    formula: str | None = None
    A: float | None = None
    Z: float | None = None
    rho: float | None = None
    gamma: float | None = None
    gammag: float | None = None
    c0: float | None = None
    s: float | None = None
    ionization_model: str | None = None
    nlte_model: str | None = None
    ion_eos_model: str | None = None

    refs: list[TableRef] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    others: dict[str, list[str]] = field(default_factory=dict)
    line_no: int = 0

    # ── 便捷视图 ────────────────────────────────────────────────
    @property
    def is_user_material(self) -> bool:
        """用户材料 MID>10000（Ramis 公布材料 MID<100）。"""
        return self.mid > 10000

    @property
    def ref_by_key(self) -> dict[str, TableRef]:
        return {r.key.upper(): r for r in self.refs}

    @property
    def eos_relpath(self) -> str | None:
        r = self.ref_by_key.get("EOS")
        return r.relpath if r else None

    @property
    def zeff_relpath(self) -> str | None:
        r = self.ref_by_key.get("ZEFF")
        return r.relpath if r else None

    @property
    def files(self) -> list[str]:
        return [r.relpath for r in self.refs]

    def describe(self) -> str:
        return (
            f"MID{self.mid} {self.name or '?'} formula={self.formula or '?'} "
            f"Z={self.Z} A={self.A} rho={self.rho} refs={len(self.refs)}"
        )


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_material_base(path: str | Path | None = None) -> list[MaterialBaseEntry]:
    """解析 ``material.base``，返回全部 251 个块。"""
    p = Path(path or config.MATERIAL_BASE)
    doc = textio.read_text(p)
    entries: list[MaterialBaseEntry] = []
    cur: MaterialBaseEntry | None = None

    for i, ln in enumerate(doc.lines):
        s = ln.strip()
        if not s:
            continue
        m = _RE_MATERIAL.match(s)
        if m:
            mid_m = _RE_MID.search(m.group(1))
            mid = int(mid_m.group(1)) if mid_m else -1
            cur = MaterialBaseEntry(mid=mid, raw_name=m.group(1), line_no=i)
            entries.append(cur)
            continue
        if cur is None:
            continue
        if s.upper().startswith("REM"):
            cur.comments.append(s[3:].strip())
            continue
        if s.startswith("#"):
            cur.comments.append(s.lstrip("#").strip())
            continue

        parts = s.split()
        key = parts[0]
        ku = key.upper()

        if ku in TABLE_KEYS and len(parts) >= 3:
            cur.refs.append(TableRef(key=ku, module=parts[1], file=parts[2]))
            continue
        if ku in TABLE_KEYS and len(parts) == 2:
            # 极少数只给文件名（模块缺省）
            cur.refs.append(TableRef(key=ku, module="", file=parts[1]))
            continue

        value = " ".join(parts[1:]) if len(parts) > 1 else ""
        if ku in TEXT_KEYS:
            attr = {
                "FORMULA": "formula", "NAME": "name",
                "IONIZATIONMODEL": "ionization_model",
                "NLTEMODEL": "nlte_model", "IONEOSMODEL": "ion_eos_model",
            }[ku]
            if ku == "FORMULA":
                cur.formula = value
            else:
                setattr(cur, attr, value)
            continue
        if ku in SCALAR_KEYS:
            val = _to_float(value)
            attr = {
                "A": "A", "Z": "Z", "RHO": "rho", "GAMMA": "gamma",
                "GAMMAG": "gammag", "C0": "c0", "S": "s",
            }.get(ku)
            if attr:
                setattr(cur, attr, val)
            else:
                cur.others.setdefault(ku, []).append(value)
            continue

        cur.others.setdefault(ku, []).append(value)

    return entries


class MaterialBase:
    """``material.base`` 的索引视图。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or config.MATERIAL_BASE)
        self.entries: list[MaterialBaseEntry] = parse_material_base(self.path)
        self._by_mid = {e.mid: e for e in self.entries}
        self._by_file: dict[str, list[tuple[MaterialBaseEntry, TableRef]]] = {}
        for e in self.entries:
            for r in e.refs:
                self._by_file.setdefault(r.relpath, []).append((e, r))
                # 同时登记「仅文件名」，便于按 basename 反查
                self._by_file.setdefault(r.file, []).append((e, r))

    # ── 查询 ────────────────────────────────────────────────────
    def by_mid(self, mid: int) -> MaterialBaseEntry | None:
        return self._by_mid.get(mid)

    def by_name(self, name: str) -> list[MaterialBaseEntry]:
        low = name.lower()
        return [e for e in self.entries
                if (e.name or "").lower() == low or (e.formula or "").lower() == low]

    def by_file(self, relpath: str) -> list[tuple[MaterialBaseEntry, TableRef]]:
        """按 ``模块/文件名`` 或仅文件名反查引用它的材料。"""
        rel = str(relpath).replace("\\", "/")
        out = list(self._by_file.get(rel, []))
        if not out:
            out = list(self._by_file.get(rel.split("/")[-1], []))
        return out

    def refs_for_file(self, relpath: str) -> list[TableRef]:
        return [r for _e, r in self.by_file(relpath)]

    @property
    def n_zeff(self) -> int:
        return sum(1 for e in self.entries if e.zeff_relpath)

    @property
    def n_eos(self) -> int:
        return sum(1 for e in self.entries if e.eos_relpath)

    def summary(self) -> dict[str, int]:
        refs = [r for e in self.entries for r in e.refs]
        return {
            "materials": len(self.entries),
            "with_eos": self.n_eos,
            "with_zeff": self.n_zeff,
            "table_refs": len(refs),
            "distinct_files": len({r.relpath for r in refs}),
        }
