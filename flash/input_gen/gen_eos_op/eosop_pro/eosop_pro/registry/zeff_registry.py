"""Z̄ 数据源注册表（**文件级**）。

盘点结果（实测，178 个 Z̄ 相关文件 / 79 个目录）
------------------------------------------------
====================  ======  ==========================================  ==============
#                     文件数   布局                                        T 单位
====================  ======  ==========================================  ==============
Z1 ``Thermos/*_Zeff.dat``   45   F2 灰度 ``[log10ρ][log10T][Z̄]``           **keV**
Z2 ``Thermos/*_Z.dat``      45   与 Z1 **完全同构**（已作废）                **eV**
Z3 ``*.ZEFF``/``*.Zeff``   ~12   F2 灰度                                     eV
Z4 ``*_op03z``/``*.ZEFF``   ~6   F2 灰度（SESAME 类型位 2）                   eV
Z5 ``*100ZEFF`` 等          4   F2 灰度                                     eV
Z6 ``mat_CH2/zeff.out``      1   F2 灰度                                     eV
Z7 ``ATOMIC/*.NoFree``       9   4 数头（LEDCOP 魔数）+ 3 段                **keV**
Z8 ``ATOMIC/*.AvSqFree``     9   同 Z7（Z²）                                **keV**
Z9 ``.301/.304/.305`` 第5段   82  内嵌 Z 数组                                **Kelvin**
--   ``material.base`` Z   251  常量名义 Z                                  —
--   ``material.base`` ZEFF 130  指向 Z̄(ρ,T) 表文件                       —
--   ``DatabaseIndex.xml``   134  常量 Zbar                                   —
--   ``EOS.list``/``Opacity.list`` 120  常量 Zbar                             —
====================  ======  ==========================================  ==============

★ 三条硬结论
1. ``f2`` 槽位是**类型码**而非 Zbar（``Al_Zeff.dat`` 头 ``0 6.0 22 21``，
   而 Al 的 Zbar 在 ``DatabaseIndex.xml`` 里是 13）。
2. 单位**必须靠声明**：Z1/Z2 表头与行数完全相同，Δlog10 恰 3.000。
3. Z̄(ρ,T) 覆盖 **130/251** 材料，另 121 个只有常量 Z。
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .. import config
from ..core.hashing import sha256_file
from .material import MaterialRegistry
from .units_registry import UnitsRegistry

__all__ = ["ZeffSource", "ZeffRegistry", "KIND_Z", "KIND_Z2", "KIND_CONST"]

KIND_Z = "Z"        # Z̄(ρ,T) 表
KIND_Z2 = "Z2"      # Z² 表
KIND_CONST = "CONST"  # 常量名义 Z

#: 文件名 → (kind, family, 匹配理由)
_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\.avsqfree$", re.I), KIND_Z2, "ledcop_zeff"),
    (re.compile(r"\.nofree$", re.I), KIND_Z, "ledcop_zeff"),
    (re.compile(r"_zeff\.dat$", re.I), KIND_Z, "multi_opacity"),
    (re.compile(r"^(?![a-z]*_z\.dat$).*zeff", re.I), KIND_Z, "multi_opacity"),
    (re.compile(r"_z\.dat$", re.I), KIND_Z, "multi_opacity"),
    (re.compile(r"op0?3z", re.I), KIND_Z, "multi_opacity"),
    (re.compile(r"\.zeff$", re.I), KIND_Z, "multi_opacity"),
)


@dataclass
class ZeffSource:
    """一个 Z̄ 数据源（文件级）。"""

    relpath: str
    kind: str                 # Z | Z2
    family: str               # 负责解析的家族
    units_T: str = ""
    unit_source: str = ""     # companion | inline | envelope | config_default
    unit_evidence: str = ""
    unit_suspect: bool = False
    grid: str = ""
    shape: str = ""
    sha256: str = ""
    n_groups: int | None = None
    table_ids: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def describe(self) -> str:
        sus = " ⚠️" if self.unit_suspect else ""
        return (f"{self.relpath} kind={self.kind} T={self.units_T}"
                f"[{self.unit_source}]{sus} shape={self.shape}")

    def to_row(self) -> dict:
        d = asdict(self)
        d["table_ids"] = ",".join(f"{k}={v}" for k, v in sorted(self.table_ids.items()))
        d["notes"] = " ;; ".join(self.notes)
        return d


class ZeffRegistry:
    """扫描全树、登记全部 Z̄ 数据源，并裁决其 T 单位。"""

    def __init__(self, matter_dir: str | Path | None = None, *,
                 units: UnitsRegistry | None = None,
                 material: MaterialRegistry | None = None,
                 with_sha: bool = False) -> None:
        self.matter_dir = Path(matter_dir or config.MATTER_DIR)
        self.units = units or UnitsRegistry()
        self.material = material
        self.with_sha = with_sha
        self.sources: list[ZeffSource] = []

    # ── 扫描 ────────────────────────────────────────────────────
    def scan(self) -> list[ZeffSource]:
        out: list[ZeffSource] = []
        for root, dirs, files in os.walk(self.matter_dir):
            dirs.sort()
            for f in sorted(files):
                rel = os.path.relpath(os.path.join(root, f), self.matter_dir)
                rel = rel.replace("\\", "/")
                hit = self._classify(f)
                if hit is None:
                    continue
                kind, family = hit
                src = ZeffSource(relpath=rel, kind=kind, family=family)
                self._fill_units(src)
                if self.with_sha:
                    src.sha256 = sha256_file(os.path.join(root, f))
                out.append(src)

        # Z9：MPQeos 的 .301/.304/.305 内嵌 Z 段
        for root, dirs, files in os.walk(self.matter_dir):
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() not in (".301", ".304", ".305"):
                    continue
                rel = os.path.relpath(os.path.join(root, f), self.matter_dir)
                rel = rel.replace("\\", "/")
                s = ZeffSource(relpath=rel, kind=KIND_Z, family="mpqeos",
                               units_T="Kelvin", unit_source="inline",
                               unit_evidence="MPQeos .30x payload 第 5 段（内部制 Kelvin）")
                s.grid = "线性 ρ × 线性 T"
                s.notes.append("Z 段位于 payload 第 5 段；⚠️ 实测含负值，语义待核")
                out.append(s)

        self.sources = out
        return out

    def _classify(self, fname: str) -> tuple[str, str] | None:
        for rx, kind, fam in _PATTERNS:
            if rx.search(fname):
                return kind, fam
        return None

    def _fill_units(self, src: ZeffSource) -> None:
        d = self.units.decide_T(src.relpath, default="eV")
        src.units_T = d.unit
        src.unit_source = d.source
        src.unit_evidence = d.evidence
        src.unit_suspect = d.suspect
        src.grid = "log10 ρ × log10 T"
        if src.family == "ledcop_zeff" and d.source == "config_default":
            # LEDCOP 拆分件**在文件内嵌声明**了 T in keV（见 ATOMIC/*.txt 头部）
            # → 不能被 config_default 的 eV 覆盖
            src.units_T = "keV"
            src.unit_source = "inline"
            src.unit_evidence = "LEDCOP 内嵌声明「T in keV」（ATOMIC/*.txt 头部）"
            src.unit_suspect = False

    # ── 视图 ────────────────────────────────────────────────────
    def by_family(self) -> dict[str, list[ZeffSource]]:
        out: dict[str, list[ZeffSource]] = {}
        for s in self.sources:
            out.setdefault(s.family, []).append(s)
        return out

    def by_material(self) -> dict[str, list[ZeffSource]]:
        """按材料聚合（依赖 MaterialRegistry）。"""
        if self.material is None:
            self.material = MaterialRegistry(build_annotations=False)
        out: dict[str, list[ZeffSource]] = {}
        for s in self.sources:
            owners = self.material.for_file(s.relpath)
            if not owners:
                out.setdefault("(未登记)", []).append(s)
                continue
            for rec in owners:
                out.setdefault(rec.label, []).append(s)
        return out

    def unit_suspects(self) -> list[ZeffSource]:
        return [s for s in self.sources if s.unit_suspect]

    def summary(self) -> dict[str, int]:
        from collections import Counter
        c_kind = Counter(s.kind for s in self.sources)
        c_unit = Counter(s.units_T for s in self.sources)
        c_src = Counter(s.unit_source for s in self.sources)
        return {
            "total": len(self.sources),
            "kind_Z": c_kind.get(KIND_Z, 0),
            "kind_Z2": c_kind.get(KIND_Z2, 0),
            "units_eV": c_unit.get("eV", 0),
            "units_keV": c_unit.get("keV", 0),
            "unit_source_companion": c_src.get("companion", 0),
            "unit_source_inline": c_src.get("inline", 0),
            "unit_source_envelope": c_src.get("envelope", 0),
            "unit_source_default": c_src.get("config_default", 0),
            "unit_suspect": len(self.unit_suspects()),
        }
