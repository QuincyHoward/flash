"""异常类型。

原则：**任何不确定都必须变成带数值证据的诊断，而不是静默兜底。**
"""

from __future__ import annotations


class MultiEosOpError(Exception):
    """本项目所有异常的基类。"""


class ParseError(MultiEosOpError):
    """无法解析某个文件（携带文件路径与原始表头，便于溯源）。"""

    def __init__(self, message: str, *, path: str = "", header_raw: str = "") -> None:
        self.path = path
        self.header_raw = header_raw
        parts = [message]
        if path:
            parts.append(f"path={path}")
        if header_raw:
            parts.append(f"header={header_raw!r}")
        super().__init__(" | ".join(parts))


class CountMismatch(MultiEosOpError):
    """实测数值个数与表头推导个数不一致 —— **不可静默吞掉**。"""

    def __init__(self, actual: int, expected: int, *, path: str = "", header_raw: str = "") -> None:
        self.actual = actual
        self.expected = expected
        self.delta = actual - expected
        self.path = path
        self.header_raw = header_raw
        super().__init__(
            f"COUNT_MISMATCH: actual={actual} expected={expected} delta={self.delta} "
            f"| path={path} | header={header_raw!r}"
        )


class BinarySuspect(MultiEosOpError):
    """文件含 NUL 字节或可打印字符率过低 —— 不走文本解析路径。"""


class UnrecognizedFormat(MultiEosOpError):
    """所有候选布局都不自洽 —— 拒绝猜测。"""


class AmbiguousFormat(MultiEosOpError):
    """多个候选布局同时自洽 —— 必须列出全部并列候选交人工定案。"""

    def __init__(self, candidates: list) -> None:
        self.candidates = list(candidates)
        super().__init__(f"AMBIGUOUS: {len(self.candidates)} 个候选布局同时自洽")


class UnitConflict(MultiEosOpError):
    """注释声明单位与数值包络推断单位冲突。"""
