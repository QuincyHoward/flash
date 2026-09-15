"""阶段 B2 —— 把「声明类型」与「内容反演类型」比对，产出冲突清单。

五类结果（**严格区分，不混为一谈**）
----------------------------------
===================  ==================================================
``agree``            反演族命中声明候选 → 内容与声明一致
``agree_structure``  ★ 反演族与声明族**结构等价**（同一条计数公式，
                     只是字段语义不同）→ **不是缺陷**
``order_mismatch``   反演族在声明候选里，但**不是第一候选** →
                     说明声明的优先级被内容证据推翻
                     （典型：``mat_Al-1.0/AL_eos.feos`` 声明 ``feos_native``
                      但内容实为 SESAME，回退到 ``multi_inverted_eos``）
``conflict``         反演族**不在**声明候选里 → 声明的路径/命名规则被内容否定
===================  ==================================================

★ 为什么要单独有 ``agree_structure``
-----------------------------------
``hyades_eos`` 与 ``hyades_opacity`` **共用同一条计数公式**
``L = 2 + nr + nt + 2*nr*nt`` —— 反演（只看结构）无法区分它们，
于是 37 个 ``hyades/Opacity/opc_*.dat`` 会被报成 ``order_mismatch``。
但它们**没有任何问题**：声明说"这是不透明度"（对），
反演说"这是 Hyades 布局"（也对）。把它们记成 37 条 mismatch 只会**淹没
真正的 10 条 conflict**（见 docs/14）。所以这里显式声明"结构等价组"。

⚠️ 反演「无结论」（``ambiguous`` / ``unrecognized``）**不算冲突** ——
很多格式（多群子表串联、含前导边界的结构）本就无法用扁平模板表达，
把它们记成冲突会淹没真正的信号。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .. import config, reporting
from ..core.inference import InferenceResult, infer_file
from . import declared_types as dt_mod
from .declared_types import DeclaredType

__all__ = ["TypeComparison", "identify", "sweep", "write_report"]

_AGREE = "agree"
_AGREE_STRUCT = "agree_structure"
_ORDER = "order_mismatch"
_CONFLICT = "conflict"
_DECLARED_ONLY = "declared_only"
_INFERRED_ONLY = "inferred_only"

#: ★「结构等价组」—— 组内家族共用**同一条**计数公式，仅**字段语义**不同。
#: 反演只看结构，故无法区分组内成员；比对时应判为 ``agree_structure``
#: 而不是 ``order_mismatch``。
#:
#: 实测：``hyades_eos`` 与 ``hyades_opacity`` 的公式都是
#: ``L = 2 + nr + nt + 2*nr*nt``（见 doc/Hyades 数据格式说明.doc：
#: 不透明度"使用同样的格式，压强处为平均 Rosseland 值，比内能处为平均 Planck 值"）。
STRUCT_EQUIV: tuple[frozenset[str], ...] = (
    frozenset({"hyades_eos", "hyades_opacity"}),
)


def same_structure(a: str | None, b: str | None) -> bool:
    """两个族是否结构等价（同组）。"""
    if a is None or b is None:
        return False
    if a == b:
        return True
    return any(a in grp and b in grp for grp in STRUCT_EQUIV)


@dataclass
class TypeComparison:
    """一个文件的「声明 vs 内容」比对结果。"""

    relpath: str
    declared_first: str | None = None
    declared_families: list[str] = field(default_factory=list)
    inferred_family: str | None = None
    inferred_template: str | None = None
    inferred_dims: tuple[int, int] | None = None
    inference_status: str = ""
    agreement: str = _DECLARED_ONLY
    notes: list[str] = field(default_factory=list)

    def describe(self) -> str:
        return (f"{self.relpath}: declared={self.declared_first} "
                f"inferred={self.inferred_family}({self.inferred_template},"
                f"{self.inferred_dims}) -> {self.agreement}")

    def to_row(self) -> dict:
        d = asdict(self)
        d["declared_families"] = ",".join(self.declared_families)
        d["inferred_dims"] = (f"{self.inferred_dims[0]}x{self.inferred_dims[1]}"
                              if self.inferred_dims else "")
        d["notes"] = " ;; ".join(self.notes)
        return d


def identify(relpath: str, *, declared: DeclaredType | None = None,
             inference: InferenceResult | None = None,
             registry=None, store=None) -> TypeComparison:
    """比对单个文件的声明类型与内容反演类型。"""
    if declared is None:
        declared = dt_mod.declare(relpath, registry=registry, store=store)
    c = TypeComparison(
        relpath=relpath,
        declared_first=declared.family,
        declared_families=list(declared.families),
    )
    if inference is None:
        try:
            inference = infer_file(config.MATTER_DIR / relpath)
        except Exception as exc:  # noqa: BLE001
            c.inference_status = "error"
            c.notes.append(f"infer failed: {type(exc).__name__}: {exc}")
            c.agreement = _DECLARED_ONLY
            return c

    c.inference_status = inference.status
    if inference.ok and inference.best is not None:
        c.inferred_family = inference.best.family
        c.inferred_template = inference.best.template
        c.inferred_dims = inference.best.dims
        fams = list(declared.families)
        # ★ 判定顺序（前三档都是"没问题"，后两档才是信号）：
        #   1. 反演族 == 第一候选                       → agree
        #   2. 反演族与**第一候选**结构等价             → agree_structure
        #      （同一条计数公式、仅字段语义不同 → 反演无法区分，不是缺陷）
        #   3. 反演族在候选列表里但非第一、且不同构     → order_mismatch
        #      （声明优先级被内容推翻；候选回退通常已救回来）
        #   4. 反演族不在候选列表里                     → conflict
        if c.inferred_family == declared.family:
            c.agreement = _AGREE
        elif same_structure(c.inferred_family, declared.family):
            c.agreement = _AGREE_STRUCT
            c.notes.append(
                f"反演族 {c.inferred_family!r} 与声明第一候选 "
                f"{declared.family!r} **结构等价**（同一计数公式，仅字段语义"
                f"不同，反演无法区分）—— **不计为冲突**")
        elif c.inferred_family not in fams:
            c.agreement = _CONFLICT
            c.notes.append(
                f"反演族 {c.inferred_family!r} 不在声明候选 {fams} 中 —— "
                f"路径/命名规则被内容否定"
            )
        else:
            c.agreement = _ORDER
            c.notes.append(
                f"反演族 {c.inferred_family!r} 在候选内但非第一候选 "
                f"({declared.family!r}) —— 声明优先级被内容证据推翻"
            )
    else:
        # 反演无结论 → 不算冲突（很多结构本就超出扁平模板的表达力）
        c.agreement = (_INFERRED_ONLY if not declared.families else _DECLARED_ONLY)
        c.notes.append(
            f"反演无结论（{inference.status}）—— 记 declared_only，**不计为冲突**"
        )
        for n in inference.notes[:3]:
            c.notes.append("  · " + n)
    return c


def sweep(*, registry=None, store=None,
          relpaths: Iterable[str] | None = None,
          max_bytes: int = 4_000_000) -> list[TypeComparison]:
    """对全树（或指定清单）做「声明 vs 内容」比对。

    ``max_bytes``：超过此大小的文件**跳过内容反演**（只在清单里记 declared_only
    并注明原因）—— 反演要逐行读全文件，几十 MB 的文件会让全树扫描不可用。
    这是**显式的取舍**，不是静默忽略。
    """
    if registry is None or store is None:
        reg, sto = dt_mod.default_registry()
        registry = registry or reg
        store = store or sto
    if relpaths is None:
        relpaths = dt_mod.iter_source_files()
    out: list[TypeComparison] = []
    for rel in relpaths:
        d = dt_mod.declare(rel, registry=registry, store=store)
        if d.is_skipped:
            continue
        p = config.MATTER_DIR / rel
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        if size > max_bytes:
            c = TypeComparison(relpath=rel, declared_first=d.family,
                               declared_families=list(d.families),
                               inference_status="skipped_large")
            c.notes.append(
                f"文件 {size / 1e6:.1f} MB > 上限 {max_bytes / 1e6:.0f} MB → "
                f"跳过内容反演（显式取舍，非静默忽略）"
            )
            out.append(c)
            continue
        try:
            inf = infer_file(p)
        except Exception:  # noqa: BLE001
            inf = None
        out.append(identify(rel, declared=d, inference=inf))
    return out


def write_report(comparisons: list[TypeComparison],
                 outdir: str | Path | None = None) -> tuple[Path, Path]:
    """写 ``type_conflict.csv`` 与 ``type_conflict.md``。"""
    od = Path(outdir or config.REPORTS_DIR)
    od.mkdir(parents=True, exist_ok=True)
    from collections import Counter

    csv_p = reporting.write_csv(od / "type_conflict.csv",
                                [c.to_row() for c in comparisons])
    by = Counter(c.agreement for c in comparisons)
    inf = Counter(c.inference_status for c in comparisons)

    md = [reporting.md_header(
        "声明类型 vs 内容反演 比对报告", str(config.MATTER_DIR), len(comparisons),
        extra=[
            ("agree", f"{by.get(_AGREE, 0)}"),
            ("order_mismatch", f"**{by.get(_ORDER, 0)}**"),
            ("conflict", f"**{by.get(_CONFLICT, 0)}**"),
            ("declared_only（反演无结论，不计冲突）", f"{by.get(_DECLARED_ONLY, 0)}"),
        ])]
    md.append("\n## 1. 比对结果分布\n")
    md.append(reporting.counter_table(by, "agreement", "files"))
    md.append("\n## 2. 反演状态分布\n")
    md.append(reporting.counter_table(inf, "inference_status", "files"))

    for key, title in ((_CONFLICT, "3. 真冲突（反演族不在声明候选中）"),
                       (_ORDER, "4. 声明优先级被推翻（反演族非第一候选）")):
        rows = [c for c in comparisons if c.agreement == key]
        md.append(f"\n## {title}（{len(rows)}）\n")
        md.append(reporting.md_table(
            [{"relpath": c.relpath, "declared_first": c.declared_first or "-",
              "declared_all": ",".join(c.declared_families),
              "inferred": f"{c.inferred_family}({c.inferred_template})",
              "dims": f"{c.inferred_dims}" if c.inferred_dims else "-"}
             for c in rows],
            ["relpath", "declared_first", "declared_all", "inferred", "dims"],
            max_rows=120, shorten_to=80))

    md_path = reporting.write_md(od / "type_conflict.md", "\n".join(md))
    return csv_p, md_path
