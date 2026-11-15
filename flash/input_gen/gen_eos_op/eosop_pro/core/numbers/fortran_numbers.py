"""Fortran 定宽数值解析内核（L2 正则 + L1 定宽辅助）。

设计纪律
--------
1. ``extract_numbers()`` **只允许作用于已剥离表头的 payload 文本**。
   对整文件调用会把 ``ALUMINUM  LANL SESAME #3711 DATED: 22581 11483``
   里的 ``3711 / 22581 / 11483`` 当成数据 —— 本项目最经典的陷阱。
2. 字段是**定宽**的（15 / 16 字符）。负号会吃掉前导空格，导致字段紧邻、无任何分隔符::

       -0.60000000E+01-0.55789474E+01-0.51578947E+01-0.47368421E+01

   这是 **4 个数**，而 ``str.split()`` 只会得到 1 个。故 L2 正则不可省。
3. 必须覆盖的写法（均在 matter++ 实测到）：

   ========================================  ======================
   写法                                      出处
   ========================================  ======================
   ``.27000000E+01``  （Ramis 无前导零）     ``AL_eos``
   ``1.1041000e+004`` （小写 e + 三位指数）  ``1041_PLANCK``
   ``-0.60000000E+01``（紧邻负数）            ``AU_op03z``
   ``1.``             （空小数）             ``AU_SIMPLE_PLANCK_MG``
   ``.0``             （无整数部分）          ``AL_IDEAL_GAS``
   ``5.00000000E+01`` （纯 Fortran E 格式）  ``eos_41.dat``
   ``1.0D+03``        （D 指数）              老式 Fortran 表
   ========================================  ======================
"""

from __future__ import annotations

import re
from typing import Iterable

__all__ = [
    "FORTRAN_NUM_RE",
    "SPECIAL_FLOAT_RE",
    "parse_fortran_float",
    "is_special",
    "extract_numbers",
    "count_numbers",
    "numeric_coverage",
    "non_numeric_residue",
    "letter_ratio",
    "has_letters",
    "is_payload_line",
    "numbers_from_lines",
    "count_nonfinite",
]

#: 唯一的 Fortran 数值正则定义（L2）。
#: 结构：可选符号 → (含小数点的数 | 无整数部分的小数 | 纯整数) → 可选指数 (E/e/D/d)
FORTRAN_NUM_RE = re.compile(
    r"[-+]?"
    r"(?:(?:\d+\.\d*)|(?:\.\d+)|(?:\d+))"
    r"(?:[EeDd][-+]?\d+)?"
)

#: ★ 非有限值（实测于 ``mat_He/Untitled.304``：payload 里出现 ``-1.#INF0000e+000``）。
#: 这是 MSVC 的无穷/非数打印格式，是**源数据缺陷**；必须识别并显式标注，
#: 否则会被当作"意外文本"而中断整个文件的解析。
#: 注意要连指数尾一起吞掉（``...INF0000e+000``），否则会残留 ``+000`` 被当成额外的 0。
SPECIAL_FLOAT_RE = re.compile(
    r"[-+]?1\.#(?:INF|IND|QNAN|SNAN)[0-9]*(?:[EeDd][-+]?\d+)?"
    r"|[-+]?(?:nan|inf(?:inity)?)",
    re.I,
)

#: 统一的「数值 token」迭代正则 —— **特殊值必须排在前面**，
#: 否则 ``1.#INF...`` 会先被普通模式匹到 ``1.`` 而漏掉 inf 语义。
_ITER_RE = re.compile(
    "(?:" + SPECIAL_FLOAT_RE.pattern + ")|(?:" + FORTRAN_NUM_RE.pattern + ")",
    re.I,
)

_D_ESP = str.maketrans({"D": "E", "d": "e"})


def parse_fortran_float(token: str) -> float:
    """把单个 Fortran 数值 token 转成 ``float``。

    兼容：``D``/``d`` 指数、``1.#INF``（→ ``inf``）、``1.#IND``/``nan``（→ ``nan``）。
    """
    t = token.strip()
    if not t:
        raise ValueError("empty numeric token")
    if SPECIAL_FLOAT_RE.fullmatch(t):
        up = t.upper()
        if "#IND" in up or "#QNAN" in up or "#SNAN" in up or up.lstrip("+-").startswith("NAN"):
            return float("nan")
        return float("-inf") if t.startswith("-") else float("inf")
    return float(t.translate(_D_ESP))


def is_special(token: str) -> bool:
    """该 token 是否是 ``inf``/``nan`` 这类非有限值。"""
    return SPECIAL_FLOAT_RE.fullmatch(token.strip()) is not None


def extract_numbers(text: str) -> list[float]:
    """从**已剥离表头的 payload 文本**中按出现顺序提取全部 Fortran 数值。

    非有限值（``1.#INF`` 等）也会被提取为 ``inf``/``nan`` —— 因为把它们当文本丢掉
    会让计数守恒失真；`inf`/`nan` 会被显式计入并可在报告中筛出。

    >>> extract_numbers("-0.60000000E+01-0.55789474E+01")
    [-6.0, -5.5789474]
    """
    out: list[float] = []
    for m in _ITER_RE.finditer(text):
        try:
            out.append(parse_fortran_float(m.group(0)))
        except ValueError:  # pragma: no cover - 正则已保证可解析
            continue
    return out


def count_numbers(text: str) -> int:
    """只计数，不构造 float 列表（大文件省内存）。"""
    return sum(1 for _ in _ITER_RE.finditer(text))


def numeric_coverage(line: str, *, ignore_space: bool = True) -> float:
    """一行中「被数值匹配覆盖的非空白字符」占比，用于定位头部/payload 分界。

    ``ignore_space=True``（默认）时分母只算非空白字符 —— 这使判别力最强：
    * 纯数值行（``-0.60000000E+01-0.557...``）→ ``1.0``
    * 自由文本行（``ALUMINUM LANL SESAME``）→ ``0.0``

    使用统一正则（含 ``1.#INF`` 等特殊值），使含 inf 的 payload 行仍判为 payload。
    """
    if ignore_space:
        target = re.sub(r"\s", "", line)
    else:
        target = line
    if not target:
        return 0.0
    covered = 0
    for m in _ITER_RE.finditer(target):
        covered += m.end() - m.start()
    return covered / len(target)


def numbers_from_lines(lines: Iterable[str]) -> list[float]:
    """对多行依次提取（仍要求这些行属于 payload 区）。"""
    return extract_numbers("\n".join(lines))


def count_nonfinite(values: Iterable[float]) -> int:
    """统计 ``inf``/``nan`` 个数 —— 用于报告源数据缺陷（实测存在）。"""
    out = 0
    for v in values:
        if v != v or v in (float("inf"), float("-inf")):
            out += 1
    return out


# ── 头部 / payload 分界的**主判据** ──────────────────────────────
# 两个实测教训，缺一不可：
#
# (1) 注释行里**也含数字**（``... SESAME #3711 DATED: 22581 11483``），
#     所以「数值覆盖率」不能单独划界（该行覆盖率 0.359 而非 0）。
# (2) payload 行里**含字母 E**（指数，如 ``-0.60000000E+01``），
#     所以「含字母」必须**先剔除数值 token** 再判，否则每一行都会被误判成表头。
#
# 正确判据：把数值 token 全部删掉后，残留文本里若还有字母 → 该行属头部/注释区。

_ALPHA_RE = re.compile(r"[A-Za-z]")


def non_numeric_residue(line: str) -> str:
    """删掉所有数值 token（含 ``1.#INF`` 等特殊值）后的残留文本。"""
    return _ITER_RE.sub("", line)


def has_letters(line: str) -> bool:
    """删掉数值 token 后，残留文本里是否还有 ASCII 字母。

    * ``-0.60000000E+01-0.55789474E+01`` → ``False``（``E`` 属数值 token）
    * ``ALUMINUM  LANL SESAME #3711``    → ``True``
    * ``     37181000    .27000000E+01`` → ``False``
    """
    return _ALPHA_RE.search(non_numeric_residue(line)) is not None


def letter_ratio(line: str) -> float:
    """非空白字符中，**非数值文本**所占比例（0 = 纯数值 payload 行）。

    * 纯数值 payload 行 → ``0.0``
    * ``ALUMINUM  LANL SESAME #3711 DATED: 22581 11483`` → 约 ``0.64``
    """
    target = re.sub(r"\s", "", line)
    if not target:
        return 0.0
    residue = re.sub(r"\s", "", non_numeric_residue(line))
    return len(residue) / len(target)


def is_payload_line(line: str, *, coverage_min: float = 0.99) -> bool:
    """判定一行是否属于数值 payload 区（主判据 + 辅判据同时成立）。"""
    return (not has_letters(line)) and numeric_coverage(line) >= coverage_min


def is_payload_line(line: str, *, coverage_min: float = 0.99) -> bool:
    """判定一行是否属于数值 payload 区（主判据 + 辅判据同时成立）。"""
    return (not has_letters(line)) and numeric_coverage(line) >= coverage_min
