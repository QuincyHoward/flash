"""解析器基类与共享数据结构。

设计约定
--------
* 阶段 A 的解析器**不依赖 numpy** —— 全部用内置 ``list``，便于在最小解释器上测试。
  numpy 只在 ``writer/h5_writer`` 与 ``grid/interpolate`` 里引入。
* 每个解析器暴露 ``FAMILY`` 常量与 ``parse(path, relpath) -> ParsedTable``。
  失败时抛 :class:`~eosop_pro.core.errors.ParseError`（携带表头原文便于溯源）。
* **计数守恒校验**是每个解析器的内置职责：实测数与表头推导数不一致即抛
  :class:`~eosop_pro.core.errors.CountMismatch`（不可静默）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence

from .. import config
from ..core import fortran_numbers as fn
from ..core import textio

__all__ = ["ParsedTable", "TableParser", "PAYLOAD_LAYOUTS", "split_payload",
           "check_count", "TwoDim", "flatten_t_major"]


@dataclass
class ParsedTable:
    """一张已解析的表（后续写 h5 / 做格式互转的单元）。"""

    table_key: str
    kind: str
    family: str
    source_relpath: str

    table_id: int | None = None
    sesame_digit: str | None = None
    f2_or_label: str | None = None
    header_raw: str = ""

    #: 轴：name -> 一维值列表
    axes: dict[str, list[float]] = field(default_factory=dict)
    axis_units: dict[str, str] = field(default_factory=dict)
    axis_log10: dict[str, bool] = field(default_factory=dict)

    #: 物理量：name -> 展平的值列表
    fields: dict[str, list[float]] = field(default_factory=dict)
    #: 物理量形状（与 ``fields`` 对应）；二维场按 ``(n_Te, n_x)`` 语义存储
    field_shape: dict[str, tuple[int, ...]] = field(default_factory=dict)
    field_units: dict[str, str] = field(default_factory=dict)
    field_log10: dict[str, bool] = field(default_factory=dict)

    n_groups: int | None = None
    group_bounds: list[float] | None = None

    unit_source: str = ""
    layout_rule: str = ""
    n_numbers_seen: int = 0
    n_numbers_expected: int | None = None
    notes: list[str] = field(default_factory=list)

    # ── 便捷视图 ────────────────────────────────────────────────
    @property
    def nr(self) -> int | None:
        for name in ("rho", "x"):
            if name in self.axes:
                return len(self.axes[name])
        return None

    @property
    def nt(self) -> int | None:
        return len(self.axes["Te"]) if "Te" in self.axes else None

    def axis(self, name: str) -> list[float]:
        return self.axes[name]

    def field2d(self, name: str) -> list[list[float]]:
        """把二维场解成 ``[i_Te][j_x]`` 的嵌套列表。"""
        shape = self.field_shape.get(name)
        flat = self.fields[name]
        if not shape or len(shape) != 2:
            raise ValueError(f"field {name!r} is not 2-D (shape={shape})")
        n_i, n_j = shape
        return [flat[i * n_j:(i + 1) * n_j] for i in range(n_i)]

    def summary(self) -> str:
        return (f"{self.family}/{self.kind} id={self.table_id} "
                f"nr={self.nr} nt={self.nt} ng={self.n_groups} "
                f"axes={list(self.axes)} fields={list(self.fields)}")


class TableParser(Protocol):
    """解析器协议。"""

    FAMILY: str

    def parse(self, path: str | Path, relpath: str) -> ParsedTable:  # pragma: no cover
        ...


# ── 计数守恒校验（不可静默） ────────────────────────────────────
def check_count(actual: int, expected: int, *, path: str, header_raw: str,
                table: ParsedTable | None = None) -> None:
    """实测数 != 表头推导数 → 抛 :class:`CountMismatch`。"""
    from ..core.errors import CountMismatch

    if table is not None:
        table.n_numbers_seen = actual
        table.n_numbers_expected = expected
    if actual != expected:
        raise CountMismatch(actual, expected, path=path, header_raw=header_raw)


# ── payload 布局模板 ────────────────────────────────────────────
#: 已知家族的计数公式。用于**布局反演**（阶段 B）与自校验。
#: 每项 = (布局名, 公式函数 f(nr, nt, ne, ng) -> 期望总数)
PAYLOAD_LAYOUTS: dict[str, Any] = {
    # F1 反演 EOS：4 头 + 2*nr + ne + 2*nr*ne
    "multi_inverted_eos": lambda nr, nt, ne, ng: 4 + 2 * nr + ne + 2 * nr * ne,
    # F2 灰度不透明度：4 头 + nr + nt + nr*nt
    "multi_opacity_gray": lambda nr, nt, ne, ng: 4 + nr + nt + nr * nt,
    # F2 多群：4 头 + nr + nt + ng*nr*nt
    "multi_opacity_mg": lambda nr, nt, ne, ng: 4 + nr + nt + ng * nr * nt,
    # F3 Hyades：L = 2 + nr + nt + 2*nr*nt（L 已含 2 个头部数字）
    "hyades_eos": lambda nr, nt, ne, ng: 2 + nr + nt + 2 * nr * nt,
    # F4 MPQeos：4 头 + nr + nt + 3*nr*nt
    "mpqeos": lambda nr, nt, ne, ng: 4 + nr + nt + 3 * nr * nt,
    # F5 LEDCOP 拆分件：4 头 + nr + nt + nr*nt
    "ledcop_zeff": lambda nr, nt, ne, ng: 4 + nr + nt + nr * nt,
}


def split_payload(values: Sequence[float], *, nr: int, ne: int) -> dict[str, list[float]]:
    """按 F1 布局切分 payload：``[rho(nr)] [de(ne)] [e0(nr)] [P(nr*ne)] [T(nr*ne)]``。

    采用**累积游标**切分（而非解析式索引），任何长度不符都会立刻暴露。
    """
    out: dict[str, list[float]] = {}
    i = 0
    out["rho"] = list(values[i:i + nr]); i += nr
    out["de"] = list(values[i:i + ne]); i += ne
    out["e0"] = list(values[i:i + nr]); i += nr
    n2 = nr * ne
    out["P"] = list(values[i:i + n2]); i += n2
    out["T"] = list(values[i:i + n2]); i += n2
    out["_consumed"] = [float(i)]
    return out


class TwoDim:
    """二维场的小工具（不依赖 numpy）。"""

    @staticmethod
    def shape(n_i: int, n_j: int) -> tuple[int, int]:
        return (n_i, n_j)

    @staticmethod
    def get(flat: Sequence[float], n_j: int, i: int, j: int) -> float:
        return flat[i * n_j + j]


def flatten_t_major(rows: Sequence[Sequence[float]]) -> list[float]:
    """把 ``[i_Te][j_x]`` 嵌套列表展平成 T-major（与源文件一致，行主序）。"""
    return [v for row in rows for v in row]


def read_payload_doc(path: str | Path, *, skip_lines: int,
                     blank_counter: list[int] | None = None) -> tuple[textio.TextDoc, list[float]]:
    """读取文件、跳过前 ``skip_lines`` 行、对 rest 做 L2 数值提取。

    **只有 payload 区允许走 L2** —— 这是本项目最核心的纪律（见模块文档与测试）。
    """
    doc = textio.read_text(path)
    body = doc.lines[skip_lines:]
    n_blank = sum(1 for ln in body if textio.is_blank(ln))
    if blank_counter is not None:
        blank_counter.append(n_blank)
    return doc, fn.extract_numbers("\n".join(body))
