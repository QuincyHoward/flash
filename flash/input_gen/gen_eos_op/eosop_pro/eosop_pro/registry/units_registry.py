"""单位注记表 —— 把「T 轴单位」从**猜测**变成**有来源的裁决**。

实测驱动力
----------
``Thermos/mat_Al/Al_Zeff.dat``（keV）与 ``Thermos/mat_Al/Al_Z.dat``（eV）
的**表头与行数完全相同**（均 128 行），logT 区间只差 ``log10(1000) = 3.000`` ——
纯数字**无法区分**。可靠的区分只能来自**声明**。

裁决优先级（高 → 低）
--------------------
1. ``companion``      —— 伴随注释文件的**文件名模式**声明
   （``Thermos/Readme.txt`` 明写 ``*_Z.dat``=eV、``*_Zeff.dat``=keV）
2. ``inline``         —— 文件内嵌单位声明
   （``ATOMIC/*.txt`` 的 ``T in keV``、``.coldopacity`` 的两行表头、``mat_Ge/Readme.txt``）
3. ``envelope``       —— 兜底启发式：由 logT 上限判断（``≥4.5 → eV``；``≤2.5 → keV``）
   并在换算后用**物理包络** ``T ∈ [1e-2, 1e6] eV`` 复核
4. ``config_default`` —— 格式默认（如 F2 默认 eV）

每条裁决都带 ``source`` 与 ``evidence``，写进 h5 的 ``/meta/units``，
使「为什么取这个单位」可追溯。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .. import config
from ..core.annotations import canon_unit
from .annotation_store import AnnotationStore

__all__ = ["UnitDecision", "UnitsRegistry", "infer_T_from_logT_range"]

_T_EV_LIKE = {"ev": 1.0, "kev": 1e3, "mev": 1e6}


@dataclass
class UnitDecision:
    """一个量的单位裁决结果。"""

    quantity: str
    unit: str
    source: str           # companion | inline | envelope | config_default | unknown
    evidence: str = ""
    suspect: bool = False

    def describe(self) -> str:
        flag = " ⚠️unit_suspect" if self.suspect else ""
        return f"{self.quantity}={self.unit} [{self.source}] {self.evidence}{flag}"


def infer_T_from_logT_range(logT: Iterable[float]) -> UnitDecision | None:
    """由 log10(T) 区间兜底推断单位。

    实测：eV 族 ``logT_max ≈ 5.0``；keV 族 ``logT_max ≤ 2.0`` —— 两者无重叠，
    故阈值 ``≥4.5 → eV`` / ``≤2.5 → keV`` 是安全的。
    换算后再用物理包络 ``[1e-2, 1e6] eV`` 复核。
    """
    vals = [v for v in logT if v == v]
    if not vals:
        return None
    lo, hi = min(vals), max(vals)
    if hi >= config.LOG_T_EV_IF_GE:
        cand = "eV"
    elif hi <= config.LOG_T_KEV_IF_LE:
        cand = "keV"
    else:
        return None
    scale = _T_EV_LIKE[cand.lower()]
    t_lo, t_hi = (10.0 ** lo) * scale, (10.0 ** hi) * scale
    inside = (t_lo >= config.TE_MIN_EV * 0.5) and (t_hi <= config.TE_MAX_EV * 2.0)
    return UnitDecision(
        quantity="T",
        unit=cand,
        source="envelope",
        evidence=(f"logT∈[{lo:.3f},{hi:.3f}] → {cand}；换算后 T∈[{t_lo:.3g},{t_hi:.3g}] eV"
                  + ("" if inside else "（**超出物理包络**）")),
        suspect=not inside,
    )


class UnitsRegistry:
    """按文件裁决单位；优先级见模块文档。"""

    def __init__(self, store: AnnotationStore | None = None,
                 matter_dir: str | Path | None = None) -> None:
        self.matter_dir = Path(matter_dir or config.MATTER_DIR)
        self.store = store or AnnotationStore(self.matter_dir).build()

    # ── 声明来源 ────────────────────────────────────────────────
    def declared_T(self, relpath: str) -> UnitDecision | None:
        """① 伴随文件名模式 ② 文件内嵌声明（含单位变更史）。"""
        hint = self.store.unit_hint_for(relpath)
        if hint:
            return UnitDecision(
                quantity="T", unit=canon_unit(hint), source="companion",
                evidence="伴随注释文件按文件名模式声明（如 Thermos/Readme.txt）",
            )
        for ann in self.store.for_file(relpath):
            u = ann.units.get("T")
            if u:
                src = "inline" if ann.kind == "inline" else "companion"
                hist = [n for n in ann.notes if "unit history" in n]
                return UnitDecision(
                    quantity="T", unit=canon_unit(u), source=src,
                    evidence=(hist[0] if hist else f"来自 {ann.source}"),
                )
            if ann.file_unit_hints:
                # 名称模式存在但未命中该文件 → 不采用（避免误配）
                continue
        return None

    def declared_other(self, relpath: str) -> dict[str, UnitDecision]:
        """其余量的声明单位（rho / kappa / P / E ...）。"""
        out: dict[str, UnitDecision] = {}
        for ann in self.store.for_file(relpath):
            for q, u in ann.units.items():
                if q in ("T", "group_bound"):
                    continue
                out.setdefault(q, UnitDecision(
                    quantity=q, unit=canon_unit(u),
                    source="inline" if ann.kind == "inline" else "companion",
                    evidence=f"来自 {ann.source}",
                ))
        return out

    # ── 综合裁决 ────────────────────────────────────────────────
    def decide_T(self, relpath: str, *, logT: Iterable[float] | None = None,
                 default: str = "eV") -> UnitDecision:
        """裁决 T 轴单位（按优先级）。"""
        d = self.declared_T(relpath)
        if d is not None:
            if logT is not None:
                e = infer_T_from_logT_range(logT)
                if e is not None and e.unit.lower() != d.unit.lower():
                    d.suspect = True
                    d.evidence += f" ｜ ⚠️ 与包络推断({e.unit})不一致：{e.evidence}"
            return d
        if logT is not None:
            e = infer_T_from_logT_range(logT)
            if e is not None:
                return e
        return UnitDecision(
            quantity="T", unit=default, source="config_default",
            evidence="无任何声明且包络无法判定 → 采用格式默认值",
        )

    def for_file(self, relpath: str, *, logT: Iterable[float] | None = None,
                 default_T: str = "eV") -> dict[str, UnitDecision]:
        """返回该文件全部量的单位裁决。"""
        out = self.declared_other(relpath)
        out["T"] = self.decide_T(relpath, logT=logT, default=default_T)
        return out

    def summary(self) -> dict[str, int]:
        """全树单位来源统计（用于报告）。"""
        from collections import Counter
        c = Counter()
        import os
        for root, _d, files in os.walk(self.matter_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), self.matter_dir)
                rel = rel.replace("\\", "/")
                d = self.declared_T(rel)
                c[d.source if d else "none"] += 1
        return dict(c)
