"""坐标轴单调性与重复点诊断 —— **默认不静默修复**。

约定
----
* 重复点判定用**相对容差** ``atol``（默认 ``1e-12``）。
* 非单调点/重复点一律**列出索引与数值** —— 写进 ``/meta/warnings`` 供人工判定。
* ``policy="error"``（默认）直接报错；``"average"`` / ``"keep_last"`` 是显式的
  探索性选项，使用者必须**主动**选择，且动作会记入 ``notes``。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .. import config

__all__ = ["AxisDiagnosis", "diagnose_axis", "repair_axis", "make_log_uniform",
           "log10_list", "minmax"]


@dataclass
class AxisDiagnosis:
    """一条坐标轴的诊断结果。"""

    n: int = 0
    is_increasing: bool = False
    is_decreasing: bool = False
    is_monotonic: bool = False
    duplicates: list[tuple[int, float]] = field(default_factory=list)
    non_monotonic: list[tuple[int, float, float]] = field(default_factory=list)
    is_log_uniform: bool = False
    span: tuple[float, float] = (0.0, 0.0)
    n_nonfinite: int = 0

    @property
    def clean(self) -> bool:
        return not self.duplicates and not self.non_monotonic and not self.n_nonfinite

    def describe(self) -> str:
        return (f"n={self.n} inc={self.is_increasing} dec={self.is_decreasing} "
                f"dup={len(self.duplicates)} nonmono={len(self.non_monotonic)} "
                f"loguniform={self.is_log_uniform} span={self.span} "
                f"nonfinite={self.n_nonfinite}")


def _finite(v: float) -> bool:
    return v == v and v not in (float("inf"), float("-inf"))


def diagnose_axis(x, *, atol: float = None) -> AxisDiagnosis:
    """诊断一维坐标轴。"""
    atol = config.MONOTONIC_ATOL if atol is None else atol
    vals = list(x)
    d = AxisDiagnosis(n=len(vals))
    if not vals:
        return d
    d.n_nonfinite = sum(1 for v in vals if not _finite(v))
    fin = [v for v in vals if _finite(v)]
    if not fin:
        return d
    d.span = (min(fin), max(fin))

    inc = dec = True
    dup: list[tuple[int, float]] = []
    nonmono: list[tuple[int, float, float]] = []
    for i in range(1, len(vals)):
        a, b = vals[i - 1], vals[i]
        if not (_finite(a) and _finite(b)):
            continue
        scale = max(abs(a), abs(b), 1.0)
        if abs(b - a) <= atol * scale:
            dup.append((i, b))
            inc = dec = False
            continue
        if b < a:
            inc = False
            nonmono.append((i, a, b))
        else:
            dec = False
    d.is_increasing = inc and len(vals) > 1
    d.is_decreasing = dec and len(vals) > 1
    d.is_monotonic = d.is_increasing or d.is_decreasing
    d.duplicates = dup
    d.non_monotonic = nonmono
    d.is_log_uniform = _is_log_uniform(fin, atol)
    return d


def _is_log_uniform(vals: list[float], atol: float) -> bool:
    pos = [v for v in vals if v > 0]
    if len(pos) < 3:
        return True
    lg = [math.log10(v) for v in pos]
    d0 = lg[1] - lg[0]
    if d0 == 0:
        return False
    for i in range(2, len(lg)):
        if abs((lg[i] - lg[i - 1]) - d0) > 1e-6 * max(1.0, abs(d0)):
            return False
    return True


def repair_axis(x, *, policy: str = None, atol: float = None) -> tuple[list[float], list[str]]:
    """按显式策略修复坐标轴，返回 ``(新轴, notes)``。

    ``policy="error"``（默认）在有重复点/非单调时抛 ``ValueError``。
    """
    policy = policy or config.MONOTONIC_POLICY
    d = diagnose_axis(x, atol=atol)
    notes: list[str] = []
    if d.clean:
        return list(x), notes
    if policy == "error":
        raise ValueError(
            f"axis is not clean: {d.describe()} "
            f"dup_idx={[i for i, _ in d.duplicates][:8]} "
            f"nonmono_idx={[i for i, _a, _b in d.non_monotonic][:8]}"
        )
    out = list(x)
    notes.append(f"repair policy={policy} on {d.describe()}")
    if policy == "keep_last":
        keep: list[float] = []
        for v in out:
            if not keep or (abs(v - keep[-1]) > (atol or config.MONOTONIC_ATOL) * max(1.0, abs(v))):
                keep.append(v)
        out = keep
    elif policy == "average":
        groups: list[list[float]] = []
        for v in out:
            if groups and abs(v - groups[-1][-1]) <= (atol or config.MONOTONIC_ATOL) * max(1.0, abs(v)):
                groups[-1].append(v)
            else:
                groups.append([v])
        out = [sum(g) / len(g) for g in groups]
    else:
        raise ValueError(f"unknown monotonic policy: {policy!r}")
    out.sort()
    notes.append(f"repaired axis length {d.n} -> {len(out)}")
    return out, notes


# ── 统一网格构造 ────────────────────────────────────────────────
def make_log_uniform(lo: float, hi: float, n: int) -> list[float]:
    """构造 log10 等距的一维网格（含端点）。"""
    if not (lo > 0 and hi > 0):
        raise ValueError(f"log-uniform grid requires positive bounds, got {lo}, {hi}")
    if n < 2:
        raise ValueError("n must be >= 2")
    a, b = math.log10(lo), math.log10(hi)
    step = (b - a) / (n - 1)
    return [10.0 ** (a + i * step) for i in range(n)]


def log10_list(values) -> list[float]:
    return [math.log10(v) if v > 0 else float("nan") for v in values]


def minmax(values) -> tuple[float, float]:
    fin = [v for v in values if _finite(v) and v > 0]
    if not fin:
        return (float("nan"), float("nan"))
    return (min(fin), max(fin))
