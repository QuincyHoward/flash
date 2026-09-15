"""``DatabaseIndex.xml`` 解析 —— 材料注册表的第二个来源。

实测结构（139 行）::

    <DatabaseIndex>
      <HYADES>
        <EOS No="11" Material="Deuterium+tritium" File="hyades\\sesame\\eos_11.dat"
             Zbar="1" Abar="2.515" Rho0="0.2205" Notes=""/>
        <EOS No="44" Material="Aluminum" File="hyades\\sesame\\eos_2044.dat"
             ... Notes="*(Preferred)#(electron-table)"/>
        <Opacity No="1022" Material="Quartz" File="hyades\\Opacity\\opc_1022.dat"
             Zbar="10" Abar="20.028"/>
      </HYADES>
    </DatabaseIndex>

实测：``<EOS>`` **98** 条、``<Opacity>`` **36** 条。
``Notes`` 里的 ``*(Preferred)`` 与 ``#(Two-temperature)``/``#(electron-table)`` 是标志位。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .. import config

__all__ = ["DbIndexEntry", "parse_database_index", "DatabaseIndex"]

_BRANCH_KEYS = ("EOS", "IEOS", "EEOS", "OPACITY", "PLANCK", "ROSSELAND", "ZEFF")


@dataclass
class DbIndexEntry:
    """一条 ``<EOS .../>`` 或 ``<Opacity .../>``。"""

    kind: str                    # EOS | OPACITY | ...
    no: int | None = None
    material: str | None = None
    file: str = ""               # 已转成 POSIX 相对路径
    zbar: float | None = None
    abar: float | None = None
    rho0: float | None = None
    notes: str = ""
    preferred: bool = False
    two_temperature: bool = False
    electron_table: bool = False
    ion_table: bool = False
    attrs: dict[str, str] = field(default_factory=dict)

    @property
    def is_opacity(self) -> bool:
        return self.kind.upper() == "OPACITY"

    def describe(self) -> str:
        flags = []
        if self.preferred:
            flags.append("*Preferred")
        if self.two_temperature:
            flags.append("#2T")
        if self.electron_table:
            flags.append("#electron")
        if self.ion_table:
            flags.append("#ion")
        return (f"{self.kind} No={self.no} {self.material} -> {self.file} "
                f"Zbar={self.zbar} Abar={self.abar} Rho0={self.rho0} "
                f"[{' '.join(flags)}]")


def _f(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _norm_file(raw: str) -> str:
    return raw.replace("\\", "/").lstrip("/")


def parse_database_index(path: str | Path | None = None) -> list[DbIndexEntry]:
    """解析 ``DatabaseIndex.xml``（用 stdlib ElementTree，不依赖第三方）。"""
    p = Path(path or config.DATABASE_INDEX)
    root = ET.fromstring(p.read_text(encoding="utf-8", errors="replace"))
    out: list[DbIndexEntry] = []
    for el in root.iter():
        tag = el.tag.upper()
        if tag not in _BRANCH_KEYS:
            continue
        a = dict(el.attrib)
        notes = a.get("Notes", "") or a.get("notes", "")
        entry = DbIndexEntry(
            kind=tag,
            no=int(a["No"]) if a.get("No", "").isdigit() else None,
            material=a.get("Material") or a.get("material"),
            file=_norm_file(a.get("File", "")),
            zbar=_f(a.get("Zbar")),
            abar=_f(a.get("Abar")),
            rho0=_f(a.get("Rho0")),
            notes=notes,
            preferred="*(Preferred)" in notes,
            two_temperature="Two-temperature" in notes,
            electron_table="electron-table" in notes,
            ion_table="ion-table" in notes,
            attrs=a,
        )
        out.append(entry)
    return out


class DatabaseIndex:
    """``DatabaseIndex.xml`` 的索引视图。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or config.DATABASE_INDEX)
        self.entries: list[DbIndexEntry] = parse_database_index(self.path)
        self._by_file: dict[str, list[DbIndexEntry]] = {}
        for e in self.entries:
            if not e.file:
                continue
            self._by_file.setdefault(e.file, []).append(e)
            self._by_file.setdefault(e.file.split("/")[-1], []).append(e)

    def by_file(self, relpath: str) -> list[DbIndexEntry]:
        rel = str(relpath).replace("\\", "/")
        out = list(self._by_file.get(rel, []))
        if not out:
            out = list(self._by_file.get(rel.split("/")[-1], []))
        return out

    def by_no(self, no: int) -> list[DbIndexEntry]:
        return [e for e in self.entries if e.no == no]

    def by_material(self, material: str) -> list[DbIndexEntry]:
        low = material.lower()
        return [e for e in self.entries
                if (e.material or "").lower() == low]

    @property
    def n_eos(self) -> int:
        return sum(1 for e in self.entries if not e.is_opacity)

    @property
    def n_opacity(self) -> int:
        return sum(1 for e in self.entries if e.is_opacity)

    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.entries),
            "eos": self.n_eos,
            "opacity": self.n_opacity,
            "with_zbar": sum(1 for e in self.entries if e.zbar is not None),
            "preferred": sum(1 for e in self.entries if e.preferred),
            "two_temperature": sum(1 for e in self.entries if e.two_temperature),
            "electron_table": sum(1 for e in self.entries if e.electron_table),
            "ion_table": sum(1 for e in self.entries if e.ion_table),
        }


#: SESAME 表号命名约定（``doc/SNOP.MANUAL``）：
#: ``xxxx{2,3,4,5}nnn`` = 平均电离 / Planck / Rosseland / 发射率
SESAME_DIGIT_KIND = {"2": "ZEFF", "3": "PLANCK", "4": "ROSSELAND", "5": "EMISSIVITY"}


def sesame_digit_of(table_id: int | str) -> str | None:
    """取 SESAME 表号的「类型位」。

    约定 ``xxxx{2,3,4,5}nnn``：8 位号里的**第 5 位**（即 ``[-4]``）是类型位。
    用**从右数第 4 位**而非固定下标，兼容 ``20202000`` / ``27003003`` / ``11041`` 等不同长度。

    实测：``20202000`` → ``2``(ZEFF)、``27003003`` → ``3``(Planck)、
    ``27004000`` → ``4``(Rosseland)、``27005003`` → ``5``(emissivity)。
    ⚠️ 早先用 ``str(id)[3]`` 是**错的**（会取到 ``20202000`` 的 ``0``）。
    """
    s = str(int(table_id))
    if len(s) < 4:
        return None
    return s[-4]


def kind_from_sesame_id(table_id: int | str) -> str | None:
    d = sesame_digit_of(table_id)
    return SESAME_DIGIT_KIND.get(d) if d else None
