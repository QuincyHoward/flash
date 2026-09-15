"""材料注册表 —— 三源合并（``material.base`` + ``DatabaseIndex.xml`` + ``*.list``）。

设计
----
* ``material.base`` 是**主索引**：256 个 ``MATERIAL`` 块给出「材料 → 表文件」的权威映射，
  是「一物质一 h5」的依据。
* ``DatabaseIndex.xml`` 补充 ``Zbar/Abar/Rho0`` 与 ``Preferred/2T/electron/ion`` 标志。
* ``EOS.list`` / ``Opacity.list`` 给出 Hyades 号与偏好标志。
* ``AnnotationStore`` 补充伴随注释声明（单位、群数、表号→类型映射）。

⚠️ ``material.list`` 实测为**空文件**，不可作索引。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from .annotation_store import AnnotationStore
from .database_index import DatabaseIndex, DbIndexEntry
from .eos_list import ListEntry, RegistryLists
from .material_base import MaterialBase, MaterialBaseEntry, TableRef

__all__ = ["MaterialRecord", "MaterialRegistry"]


def _safe_name(s: str) -> str:
    """把材料名转成安全的文件名片段。"""
    out = []
    for ch in s:
        if ch.isalnum() or ch in "-_.":
            out.append(ch)
        elif ch in " +":
            out.append("_")
    name = "".join(out).strip("_")
    return name or "unnamed"


@dataclass
class MaterialRecord:
    """一个材料的合并视图。"""

    mid: int | None = None
    name: str | None = None
    formula: str | None = None
    Z: float | None = None
    A: float | None = None
    rho0: float | None = None
    gamma: float | None = None

    base_entry: MaterialBaseEntry | None = None
    index_entries: list[DbIndexEntry] = field(default_factory=list)
    list_entries: list[ListEntry] = field(default_factory=list)
    refs: list[TableRef] = field(default_factory=list)
    unindexed_files: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # ── 视图 ────────────────────────────────────────────────────
    @property
    def label(self) -> str:
        return self.name or self.formula or (f"MID{self.mid}" if self.mid is not None else "unknown")

    @property
    def h5_stem(self) -> str:
        """h5 文件名主干（优先用化学式，避免空格与斜杠）。"""
        stem = self.formula or self.name or f"MID{self.mid}"
        if self.mid is not None and self.mid > 10000:
            stem = f"{stem}_MID{self.mid}"
        return _safe_name(str(stem))

    @property
    def files(self) -> list[str]:
        out: list[str] = [r.relpath for r in self.refs]
        for e in self.index_entries:
            if e.file and e.file not in out:
                out.append(e.file)
        for f in self.unindexed_files:
            if f not in out:
                out.append(f)
        return out

    @property
    def kind_map(self) -> dict[str, str]:
        """``文件 → KIND``（用于 h5 的 ``/tables/<KIND>_<id>``）。"""
        m: dict[str, str] = {}
        for r in self.refs:
            m.setdefault(r.relpath, r.kind)
            m.setdefault(r.file, r.kind)
        for e in self.index_entries:
            m.setdefault(e.file, "OPACITY" if e.is_opacity else "EOS_TOTAL")
        return m

    def describe(self) -> str:
        return (f"{self.label} MID={self.mid} Z={self.Z} A={self.A} rho0={self.rho0} "
                f"files={len(self.files)} sources={','.join(self.sources)}")


class MaterialRegistry:
    """三源合并的材料注册表。"""

    def __init__(self, matter_dir: str | Path | None = None, *,
                 build_annotations: bool = True) -> None:
        self.matter_dir = Path(matter_dir or config.MATTER_DIR)
        self.base = MaterialBase(self.matter_dir / "material.base")
        self.index = DatabaseIndex(self.matter_dir / "DatabaseIndex.xml")
        self.lists = RegistryLists(self.matter_dir / "hyades" / "EOS.list",
                                   self.matter_dir / "hyades" / "Opacity.list")
        self.annotations: AnnotationStore | None = (
            AnnotationStore(self.matter_dir).build() if build_annotations else None
        )
        self.records: list[MaterialRecord] = self._merge()

    # ── 合并 ────────────────────────────────────────────────────
    def _merge(self) -> list[MaterialRecord]:
        recs: list[MaterialRecord] = []
        for e in self.base.entries:
            rec = MaterialRecord(
                mid=e.mid, name=e.name, formula=e.formula, Z=e.Z, A=e.A,
                rho0=e.rho, gamma=e.gamma, base_entry=e,
                refs=list(e.refs), sources=["material.base"],
            )
            # 按文件名把 DatabaseIndex 条目挂上
            files = set(rec.files)
            for f in files:
                for ie in self.index.by_file(f):
                    if ie not in rec.index_entries:
                        rec.index_entries.append(ie)
                        if "DatabaseIndex" not in rec.sources:
                            rec.sources.append("DatabaseIndex")
            # Hyades 号 → *.list
            for r in e.refs:
                num = r.file.rsplit("_", 1)[-1].split(".")[0]
                if num.isdigit():
                    le = self.lists.by_no(int(num))
                    if le is not None and le not in rec.list_entries:
                        rec.list_entries.append(le)
                        if "EOS.list/Opacity.list" not in rec.sources:
                            rec.sources.append("EOS.list/Opacity.list")
            # 补空缺字段
            if rec.Z is None:
                rec.Z = next((ie.zbar for ie in rec.index_entries if ie.zbar), None)
            if rec.A is None:
                rec.A = next((ie.abar for ie in rec.index_entries if ie.abar), None)
            if rec.rho0 is None:
                rec.rho0 = next((ie.rho0 for ie in rec.index_entries if ie.rho0), None)
                if rec.rho0 is None:
                    rec.rho0 = next((le.rho0 for le in rec.list_entries if le.rho0), None)
            recs.append(rec)
        return recs

    # ── 查询 ────────────────────────────────────────────────────
    def by_mid(self, mid: int) -> MaterialRecord | None:
        return next((r for r in self.records if r.mid == mid), None)

    def by_name(self, name: str) -> list[MaterialRecord]:
        low = name.lower()
        return [r for r in self.records
                if (r.name or "").lower() == low or (r.formula or "").lower() == low]

    def for_file(self, relpath: str) -> list[MaterialRecord]:
        """找出引用了某文件的全部材料。"""
        rel = str(relpath).replace("\\", "/")
        base = rel.split("/")[-1]
        out: list[MaterialRecord] = []
        for r in self.records:
            if any(rel == f or base == f.split("/")[-1] for f in r.files):
                out.append(r)
        return out

    def unclaimed_files(self, all_files: list[str]) -> list[str]:
        """在给定文件清单里找出**未被任何材料引用**的（去 ``_unindexed``）。"""
        claimed: set[str] = set()
        for r in self.records:
            for f in r.files:
                claimed.add(f)
                claimed.add(f.split("/")[-1])
        return [f for f in all_files
                if f not in claimed and f.split("/")[-1] not in claimed]

    # ── 报告 ────────────────────────────────────────────────────
    def summary(self) -> dict[str, int]:
        src_hist: dict[str, int] = {}
        for r in self.records:
            for s in r.sources:
                src_hist[s] = src_hist.get(s, 0) + 1
        out = {
            "materials": len(self.records),
            "with_zeff": sum(1 for r in self.records if r.base_entry and r.base_entry.zeff_relpath),
            "with_eos": sum(1 for r in self.records if r.base_entry and r.base_entry.eos_relpath),
            "with_zinfl": sum(1 for r in self.records if r.Z is not None),
            "with_ainfl": sum(1 for r in self.records if r.A is not None),
            "user_materials": sum(1 for r in self.records if r.mid is not None and r.mid > 10000),
            "distinct_files": len({f for r in self.records for f in r.files}),
        }
        out.update({f"src:{k}": v for k, v in sorted(src_hist.items())})
        return out

    def source_diff(self) -> dict[str, list[str]]:
        """三源材料集合的差集（用于审计报告）。"""
        base_names = {(r.name or "").lower() for r in self.records if r.name}
        idx_names = {(e.material or "").lower() for e in self.index.entries if e.material}
        lst_names = {(e.name or "").lower() for e in self.lists.eos_entries + self.lists.opacity_entries}
        return {
            "index_only": sorted(idx_names - base_names),
            "list_only": sorted(lst_names - base_names),
            "base_only_count": len(base_names - idx_names - lst_names),
        }
