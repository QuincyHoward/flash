"""解析审计记录 —— 每个文件一条，**所有不确定都必须留下数值证据**。

``ParseSnapshot`` 是审计报告 ``audit_all.<ts>.csv`` 的行结构，也是 h5 里
``/meta/sources`` 的来源。任何 ``count_mismatch`` / ``ambiguous_layout`` /
``unit_suspect`` 都不允许被静默丢弃。
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["STATUSES", "ParseSnapshot", "TableRecord", "SNIP_COLUMNS"]

#: 允许的状态取值
STATUSES = (
    "ok",                  # 表头推导计数 == 实测计数
    "ok_unverified",       # 表头无法推导总数，仅记录实测值
    "count_mismatch",      # 实测 != 推导 —— 默认不写 h5
    "ambiguous_layout",    # 多个候选布局同时自洽
    "unrecognized",        # 所有候选布局都不自洽
    "type_conflict",       # 声明类型与内容反演结果冲突
    "unit_suspect",        # 单位换算后超出物理包络
    "unit_conflict",       # 注释声明单位与包络推断冲突
    "skipped_non_numeric", # 明确的非数值文件（登记但跳过）
    "binary_suspect",      # 含 NUL / 可打印率过低
    "error",               # 解析抛异常
)

#: 审计 CSV 的列（顺序即写盘顺序）
SNIP_COLUMNS = (
    "relpath", "family", "declared_type", "inferred_type", "type_agreement",
    "dispatch_rule", "status", "sha256", "size_bytes", "mtime_utc",
    "encoding_used", "newline_style", "n_blank_in_payload",
    "field_width", "n_fields_per_line",
    "n_numbers_actual", "n_numbers_expected", "nr", "nt", "ne", "n_groups",
    "layout_rule", "layout_confidence", "unit_source", "elapsed_ms",
    "skipped_reason", "diagnostics",
)


@dataclass
class ParseSnapshot:
    """单个文件的解析审计记录。"""

    relpath: str
    abs_path: str = ""
    family: str | None = None
    declared_type: str | None = None      # 阶段 A：来自后缀/路径/注册表
    inferred_type: str | None = None      # 阶段 B：来自内容反演
    type_agreement: str | None = None     # agree | conflict | declared_only | inferred_only
    dispatch_rule: str = ""
    status: str = "ok"
    sha256: str = ""
    size_bytes: int = 0
    mtime_utc: str = ""

    encoding_used: str = ""
    newline_style: str = "none"
    n_blank_in_payload: int = 0
    field_width: int | None = None
    n_fields_per_line: int | None = None

    header_tokens: list[str] = field(default_factory=list)
    header_raw: str = ""
    n_numbers_actual: int = 0
    n_numbers_expected: int | None = None
    nr: int | None = None
    nt: int | None = None
    ne: int | None = None
    n_groups: int | None = None

    layout_rule: str = ""
    layout_confidence: str = ""
    unit_source: str = ""
    elapsed_ms: float = 0.0
    skipped_reason: str | None = None
    diagnostics: list[str] = field(default_factory=list)

    # ── 便捷方法 ────────────────────────────────────────────────
    def note(self, msg: str) -> None:
        self.diagnostics.append(msg)

    @property
    def count_delta(self) -> int | None:
        if self.n_numbers_expected is None:
            return None
        return self.n_numbers_actual - self.n_numbers_expected

    @property
    def is_ok(self) -> bool:
        return self.status in ("ok", "ok_unverified")

    @property
    def should_write_h5(self) -> bool:
        """默认只有 ``ok`` / ``ok_unverified`` 才写 h5（``--allow-mismatch`` 可覆盖）。"""
        return self.is_ok

    def finalize(self) -> "ParseSnapshot":
        if self.n_numbers_expected is not None and self.status == "ok":
            self.status = "ok" if self.count_delta == 0 else "count_mismatch"
            if self.status == "count_mismatch":
                self.note(
                    f"COUNT_MISMATCH: actual={self.n_numbers_actual} "
                    f"expected={self.n_numbers_expected} delta={self.count_delta}"
                )
        return self

    def as_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["diagnostics"] = " ;; ".join(self.diagnostics)
        d["header_tokens"] = " ".join(self.header_tokens)
        return {k: d.get(k) for k in SNIP_COLUMNS}


@dataclass
class TableRecord:
    """一个已解析的表格（后续写 h5 的单元）。"""

    table_key: str
    kind: str                       # EOS_TOTAL / PLANCK / ZEFF / ...
    source_relpath: str
    family: str
    table_id: int | None = None
    sesame_digit: str | None = None
    f2_or_label: str | None = None
    header_raw: str = ""

    axes: dict[str, Any] = field(default_factory=dict)       # name -> ndarray
    axis_log10: dict[str, bool] = field(default_factory=dict)
    axis_units: dict[str, str] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)     # name -> ndarray
    field_units: dict[str, str] = field(default_factory=dict)
    field_log10: dict[str, bool] = field(default_factory=dict)

    n_groups: int | None = None
    group_bounds: Any = None
    unit_source: str = ""
    layout_rule: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def nr(self) -> int | None:
        for name in ("rho", "n_ion", "x"):
            ax = self.axes.get(name)
            if ax is not None:
                return len(ax)
        return None

    @property
    def nt(self) -> int | None:
        ax = self.axes.get("Te")
        return len(ax) if ax is not None else None


class Stopwatch:
    """毫秒级计时（写进 snapshot 的 ``elapsed_ms``）。"""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    @property
    def ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0


def utc_mtime(path: str | Path) -> str:
    try:
        ts = Path(path).stat().st_mtime
    except OSError:
        return ""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
