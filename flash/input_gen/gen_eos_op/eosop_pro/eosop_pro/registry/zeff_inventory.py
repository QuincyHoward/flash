"""Z̄ 数据源盘点（**材料级**）—— 回答「某个材料能不能算出 Z̄(ρ,T)」。

覆盖度定义
----------
* ``table``        —— 该材料有 Z̄(ρ,T) 表（来自 ``material.base`` 的 ``ZEFF`` 行
  或按文件名 token 归属）→ **可以**做 ``(n_ele, Te)`` 网格
* ``nominal_only`` —— 只有常量名义 Z（``material.base`` 的 ``Z`` 关键字）
  → 只能做近似（Z̄ = const）
* ``none``         —— 两者都无

实测结论：``material.base`` 的 251 个 MATERIAL 块中 **130 个** 声明了 ``ZEFF``，
即 Z̄(ρ,T) 表覆盖 **130/251**；其余 121 个只有常量 Z。
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .. import config, reporting
from .material import MaterialRegistry
from .zeff_registry import ZeffRegistry, ZeffSource

__all__ = ["MaterialZeff", "ZeffInventory"]

_COVERAGE_TABLE = "table"                 # material.base 显式声明 ZEFF
_COVERAGE_TABLE_BY_NAME = "table_by_name"  # 仅按文件名归属（未在 material.base 声明）
_COVERAGE_NOMINAL = "nominal_only"
_COVERAGE_NONE = "none"


@dataclass
class MaterialZeff:
    """一个材料的 Z̄ 可得性。"""

    material: str
    mid: int | None = None
    formula: str | None = None
    nominal_Z: float | None = None
    nominal_source: str = ""
    coverage: str = _COVERAGE_NONE
    declared_zeff: bool = False
    declared_zeff_file: str = ""
    tables: list[ZeffSource] = field(default_factory=list)
    list_entries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def n_tables(self) -> int:
        return len(self.tables)

    @property
    def table_units(self) -> list[str]:
        return sorted({t.units_T for t in self.tables if t.units_T})

    def describe(self) -> str:
        return (f"{self.material} MID={self.mid} Z={self.nominal_Z} "
                f"coverage={self.coverage} tables={self.n_tables} "
                f"units={self.table_units}")

    def to_row(self) -> dict:
        d = asdict(self)
        d["tables"] = " ;; ".join(t.relpath for t in self.tables)
        d["table_units"] = ",".join(self.table_units)
        d["table_kinds"] = ",".join(sorted({t.kind for t in self.tables}))
        d["unit_sources"] = ",".join(sorted({t.unit_source for t in self.tables}))
        d["list_entries"] = ",".join(self.list_entries)
        d["notes"] = " ;; ".join(self.notes)
        return d


class ZeffInventory:
    """把 :class:`ZeffRegistry`（文件级）与材料注册表合成**材料级**覆盖度。"""

    def __init__(self, zeff: ZeffRegistry | None = None,
                 material: MaterialRegistry | None = None) -> None:
        self.material = material or MaterialRegistry(build_annotations=False)
        self.zeff = zeff or ZeffRegistry(material=self.material)
        if not self.zeff.sources:
            self.zeff.scan()
        self.rows: list[MaterialZeff] = []

    def build(self) -> list[MaterialZeff]:
        # 文件 → 材料 归属
        owners: dict[str, list[str]] = {}
        for s in self.zeff.sources:
            for rec in self.material.for_file(s.relpath):
                owners.setdefault(rec.label, []).append(s.relpath)

        out: list[MaterialZeff] = []
        for rec in self.material.records:
            mz = MaterialZeff(
                material=rec.label, mid=rec.mid, formula=rec.formula,
                nominal_Z=rec.Z,
                nominal_source="material.base 的 Z 关键字" if rec.Z is not None else "",
            )
            # ① material.base 显式声明 ZEFF 表 → **权威覆盖**
            if rec.base_entry and rec.base_entry.zeff_relpath:
                rel = rec.base_entry.zeff_relpath
                mz.declared_zeff = True
                mz.declared_zeff_file = rel
                hit = next((s for s in self.zeff.sources if s.relpath == rel), None)
                if hit is not None:
                    mz.tables.append(hit)
                    mz.notes.append("ZEFF 表由 material.base 显式声明")
                else:
                    mz.notes.append(f"material.base 声明 ZEFF={rel} 但未在扫描中命中")
            # ② 按文件名归属的额外 Z̄ 文件（**未经声明**，仅记录，不计入覆盖）
            for rel in owners.get(rec.label, []):
                hit = next((s for s in self.zeff.sources if s.relpath == rel), None)
                if hit is not None and hit not in mz.tables:
                    mz.tables.append(hit)
                    if not mz.declared_zeff:
                        mz.notes.append(f"按文件名归属的 Z̄ 文件（未声明）：{rel}")
            # ③ 同名 *.list 条目
            for le in rec.list_entries:
                mz.list_entries.append(f"{le.no}:{le.name}")

            if mz.declared_zeff:
                mz.coverage = _COVERAGE_TABLE
            elif mz.tables:
                mz.coverage = _COVERAGE_TABLE_BY_NAME
            elif rec.Z is not None:
                mz.coverage = _COVERAGE_NOMINAL
            else:
                mz.coverage = _COVERAGE_NONE
            out.append(mz)

        self.rows = out
        return out

    # ── 统计与报告 ──────────────────────────────────────────────
    def summary(self) -> dict[str, int]:
        if not self.rows:
            self.build()
        from collections import Counter
        c = Counter(r.coverage for r in self.rows)
        return {
            "materials": len(self.rows),
            "coverage_table": c.get(_COVERAGE_TABLE, 0),
            "coverage_table_by_name": c.get(_COVERAGE_TABLE_BY_NAME, 0),
            "coverage_nominal_only": c.get(_COVERAGE_NOMINAL, 0),
            "coverage_none": c.get(_COVERAGE_NONE, 0),
            "zeff_files_total": len(self.zeff.sources),
            "zeff_unit_suspect": len(self.zeff.unit_suspects()),
        }

    def write_reports(self, outdir: str | Path | None = None) -> tuple[Path, Path]:
        """写 ``zeff_inventory.csv`` 与 ``zeff_inventory.md``。"""
        if not self.rows:
            self.build()
        od = Path(outdir or config.REPORTS_DIR)
        od.mkdir(parents=True, exist_ok=True)

        csv_path = reporting.write_csv(od / "zeff_inventory.csv",
                                       [r.to_row() for r in self.rows])
        sm = self.summary()
        md = [reporting.md_header(
            "Z̄ 数据源盘点（材料级）", str(config.MATTER_DIR), sm["materials"],
            extra=[
                ("Z̄(ρ,T) 表覆盖", f"**{sm['coverage_table']}** 个材料"),
                ("仅常量 Z", f"{sm['coverage_nominal_only']} 个材料"),
                ("都无", f"{sm['coverage_none']} 个材料"),
                ("Z̄ 相关文件", f"{sm['zeff_files_total']}"),
                ("单位存疑", f"{sm['zeff_unit_suspect']}"),
            ])]

        md.append("\n## 1. 单位裁决来源分布（文件级）\n")
        from collections import Counter
        md.append(reporting.counter_table(
            Counter(s.unit_source for s in self.zeff.sources), "unit_source", "files"))
        md.append("\n## 2. T 单位分布（文件级）\n")
        md.append(reporting.counter_table(
            Counter(s.units_T for s in self.zeff.sources), "T_unit", "files"))
        md.append("\n## 3. 解析家族分布（文件级）\n")
        md.append(reporting.counter_table(
            Counter(s.family for s in self.zeff.sources), "family", "files"))
        md.append("\n## 4. 覆盖度分组（材料级）\n")
        md.append(reporting.counter_table(
            Counter(r.coverage for r in self.rows), "coverage", "materials"))

        md.append("\n## 5. 有 Z̄(ρ,T) 表的材料（可做 (n_ele,Te) 网格）\n")
        md.append(reporting.md_table(
            [{"material": r.material, "mid": r.mid, "Z": r.nominal_Z,
              "n_tables": r.n_tables, "T_units": ",".join(r.table_units),
              "files": " ;; ".join(t.relpath for t in r.tables)}
             for r in self.rows if r.coverage == _COVERAGE_TABLE],
            ["material", "mid", "Z", "n_tables", "T_units", "files"],
            max_rows=140, shorten_to=80))

        md.append("\n## 6. 单位存疑清单\n")
        md.append(reporting.md_table(
            [{"relpath": s.relpath, "T": s.units_T, "source": s.unit_source,
              "evidence": s.unit_evidence}
             for s in self.zeff.unit_suspects()],
            ["relpath", "T", "source", "evidence"], max_rows=80, shorten_to=90))

        md_path = reporting.write_md(od / "zeff_inventory.md", "\n".join(md))
        return csv_path, md_path
