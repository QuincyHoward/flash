"""L1 定宽切分 —— matter++ 的权威解析路径。

字段宽实测：MULTI / SESAME / Hyades 为 **15** 字符，MPQeos ``.301/.304/.305`` 为 **16**。
每行字段数：MULTI / SESAME 为 **4**，Hyades 为 **5**。

注意 L1 是**首选**路径（能正确处理紧邻负数），L2 正则（``fortran_numbers``）是兜底。
两条路径在同一文件上必须给出相同结果 —— 见 ``test_fixedwidth``。
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

from .fortran_numbers import parse_fortran_float

__all__ = [
    "WIDTH_MULTI",
    "WIDTH_MPQEOS",
    "FIELDS_MULTI",
    "FIELDS_HYADES",
    "PLAUSIBLE_WIDTHS",
    "slice_fields",
    "slice_values",
    "fields_per_line",
    "values_from_lines",
    "infer_payload_width",
]

WIDTH_MULTI = 15
WIDTH_MPQEOS = 16
FIELDS_MULTI = 4
FIELDS_HYADES = 5

#: 实测出现过的字段宽（SESAME/MULTI/Hyades=15；MPQeos 变体=16）
PLAUSIBLE_WIDTHS = (15, 16, 20)


def slice_fields(line: str, width: int = WIDTH_MULTI, count: int | None = None,
                 start: int = 0) -> list[str]:
    """按定宽切出字段原始文本（保留内部空白，去掉首尾空白）。

    ``count=None`` 时切到行尾。
    """
    out: list[str] = []
    i = start
    n = len(line)
    while i < n:
        if count is not None and len(out) >= count:
            break
        chunk = line[i:i + width].strip()
        if chunk:
            out.append(chunk)
        i += width
    return out


def slice_values(line: str, width: int = WIDTH_MULTI, count: int | None = None,
                 start: int = 0) -> list[float]:
    """定宽切分并转 ``float``；空字段被跳过（尾部不足一行时必然出现）。"""
    return [parse_fortran_float(t) for t in slice_fields(line, width, count, start)]


def fields_per_line(n_chars: int, width: int = WIDTH_MULTI) -> int:
    """满行时的字段数（``n_chars`` 为行长，尾部余数不计）。"""
    return n_chars // width


def values_from_lines(lines: Iterable[str], width: int = WIDTH_MULTI,
                      start: int = 0) -> list[float]:
    """对多行做定宽切分并汇总。"""
    out: list[float] = []
    for ln in lines:
        out.extend(slice_values(ln, width=width, start=start))
    return out


def infer_payload_width(lines: Sequence[str] | Iterable[str], n_fields: int = FIELDS_MULTI,
                        *, default: int = WIDTH_MULTI) -> int:
    """从 payload 行长度反推字段宽 ``W = len(line) // n_fields``（取众数）。

    实测必要性：``.301/.304/.305`` 家族的字段宽**并不统一**——
    ``mat_Al-1.0/FEOS/Al.feos.301`` 的 payload 行是 60 字符（→ ``W=15``），
    而 ``mat_He/Untitled.304`` 是 64 字符（→ ``W=16``）。
    用固定 16 会切错，用固定 15 也会切错另一批。

    更麻烦的是**表头行**：其 ID 字段宽度为 16 或 17 列（不定），
    因此表头**不可定宽切分**，必须交给 L2 正则（表头全为空格分隔的正数，
    不存在紧邻负数问题）。

    返回落在 :data:`PLAUSIBLE_WIDTHS` 内的众数；无有效样本时返回 ``default``。
    """
    counter: Counter[int] = Counter()
    for ln in lines:
        n = len(ln)
        if n >= n_fields:
            counter[n // n_fields] += 1
    for width, _count in counter.most_common():
        if width in PLAUSIBLE_WIDTHS:
            return width
    return default
