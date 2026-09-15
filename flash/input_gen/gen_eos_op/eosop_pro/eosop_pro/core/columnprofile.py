"""③ 定宽推断 —— **不预设** 15 / 16，由**列占用直方图**反推字段宽。

算法
----
1. 对 payload 区逐行切到「非空白字符出现过的列位」；
2. 一个**恒为空白的列**是天然的字段边界 → 其位置序列的间距众数即字段宽 ``W``；
3. 用 ``W × 每行字段数 ≈ 行长`` 交叉校验。

退化情形（实测很常见）
----------------------
matter++ 里**负号会吃掉前导空格**，导致字段紧邻、**没有任何空白列**。

    -0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01

此时空白列法失效 → 退化为「行长 // 预期字段数」，或直接用 L2 正则计每行 token 数。
故本模块返回 :class:`ColumnProfile`，**同时给出两条路径的结果与所用判据**，
让人能看出结论是怎么来的。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import fortran_numbers as fn
from .fixedwidth import PLAUSIBLE_WIDTHS, WIDTH_MULTI

__all__ = ["ColumnProfile", "profile_columns"]


@dataclass
class ColumnProfile:
    """payload 区的列占用画像。"""

    n_rows: int = 0
    max_len: int = 0
    #: 恒为空白（从未被占用）的列位
    blank_columns: list[int] = field(default_factory=list)
    #: 相邻空白列间距的众数（= 候选字段宽）
    width_from_gaps: int | None = None
    #: 由「行长 // token 数」推出的候选字段宽
    width_from_length: int | None = None
    tokens_per_line: int | None = None
    width: int = WIDTH_MULTI
    rule: str = ""
    conflicts: list[str] = field(default_factory=list)

    def describe(self) -> str:
        return (f"rows={self.n_rows} max_len={self.max_len} "
                f"blank_cols={len(self.blank_columns)} "
                f"W_gap={self.width_from_gaps} W_len={self.width_from_length} "
                f"-> W={self.width} ({self.rule})")


def profile_columns(payload_lines: list[str], *, default: int = WIDTH_MULTI
                    ) -> ColumnProfile:
    """由 payload 行推断字段宽。"""
    rows = [ln for ln in payload_lines if ln.strip()]
    p = ColumnProfile(n_rows=len(rows))
    if not rows:
        p.rule = "no payload rows -> default"
        p.width = default
        return p

    p.max_len = max(len(ln) for ln in rows)
    occ = [False] * p.max_len
    for ln in rows:
        for i, ch in enumerate(ln):
            if not ch.isspace():
                occ[i] = True
    p.blank_columns = [i for i, used in enumerate(occ) if not used]

    # 路径 A：空白列间距众数（字段边界可见时最可靠）
    if len(p.blank_columns) >= 2:
        gaps = [p.blank_columns[i + 1] - p.blank_columns[i]
                for i in range(len(p.blank_columns) - 1)]
        cand = Counter(g for g in gaps if g >= 2)
        if cand:
            p.width_from_gaps = cand.most_common(1)[0][0]

    # 路径 B：行长 // 每行 token 数
    tok_counts = Counter(len(fn.extract_numbers(ln)) for ln in rows)
    if tok_counts:
        p.tokens_per_line = tok_counts.most_common(1)[0][0]
        if p.tokens_per_line:
            p.width_from_length = p.max_len // p.tokens_per_line

    # 选宽：**长度法优先**（实测在 Al=15 / He=16 上均正确），空白列法作为佐证。
    # 理由：定宽字段多为**右对齐**，字段内的前导空白会产生大量散碎空白列，
    # 使「空白列间距众数」不可靠；而 ``行长 // token 数`` 在满行语义下是精确的。
    if p.width_from_length and p.width_from_length in PLAUSIBLE_WIDTHS:
        p.width = p.width_from_length
        p.rule = "line-length // tokens-per-line（满行语义下精确）"
    elif p.width_from_gaps and p.width_from_gaps in PLAUSIBLE_WIDTHS:
        p.width = p.width_from_gaps
        p.rule = "blank-column gap mode（字段边界可见时的备选）"
    else:
        p.width = default
        p.rule = f"fallback default {default}"

    if (p.width_from_gaps and p.width_from_length
            and p.width_from_gaps != p.width_from_length):
        p.conflicts.append(
            f"空白列法得 {p.width_from_gaps}，长度法得 {p.width_from_length} —— "
            f"取 {p.width}（{p.rule}）；右对齐字段的散碎空白列常使前者偏小"
        )
    if not p.blank_columns or len(p.blank_columns) < 2:
        p.conflicts.append(
            "未发现可用的空白列 → 字段紧邻（负号吃掉前导空格的典型情形），"
            "只能依赖长度法 —— 这也是 matter++ 的常态"
        )
    del occ
    return p
