"""跨格式转换接口 —— 为后期「不同文件格式的相互转换」留出的**唯一入口**。

设计
----
所有解析器把文件读成统一的 :class:`~eosop_pro.parsers.base.ParsedTable`；
所有写出器都实现 ``write(table, out_path, **opts) -> Path``。
于是任意两个家族之间的转换只需
``read(A) -> ParsedTable -> write(B)``，**不需要 N×N 个转换器**。

已经把「参考实现」找齐（这是关键 —— 逆变换必须与正向格式严格一致）：

==============================  ===========================================================
目标格式                         权威参考
==============================  ===========================================================
``multi_opacity`` (F2)          ``matlab/outputMULTIOpacity.m``（``%15.7e``×4，log10，keV→eV×1000）
``hyades_eos`` (F3)             ``matlab/outputHyadesEOS.m``（``%15.8e``×5，L=2+nr+nt+2nr·nt，T keV）
``multi_inverted_eos`` (F1)     ``doc/FEOS/...`` + F1 解析器（4 数头，``with_e0``/``no_e0``）
``h5``                          :mod:`eosop_pro.writer.h5_writer`（双轨：native + unified）
==============================  ===========================================================

用法
----
::

    from eosop_pro.convert import convert, list_targets
    convert(table, "out.cn4")                    # 默认目标 = cn4
    convert(table, "out.dat", target="hyades_eos")   # 指定其他目标
    convert(table, "out.op", target="multi_opacity")
    for t in list_targets(): print(t.name, t.description)

**默认目标**：``cn4``（FLASH IONMIX 主格式，跨族互转的枢纽 —— 用户工作流
"跨族转 cn4" 占绝大多数）。``set_default_target("h5")`` 可全局改默认；
``target=...`` 显式传参永远优先于默认值。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from ..parsers.base import ParsedTable

__all__ = [
    "ConvertTarget", "REGISTRY", "register", "get_target",
    "list_targets", "convert", "convert_tables",
    "DEFAULT_TARGET", "get_default_target", "set_default_target",
]

#: 不显式指定 ``target`` 时 :func:`convert` / :func:`convert_tables` 使用的目标。
#: cn4 是 FLASH IONMIX 主格式、跨族互转的枢纽（其余格式 -> cn4 是高频路径）。
DEFAULT_TARGET: str = "cn4"


def get_default_target() -> str:
    """当前默认目标格式名。"""
    return DEFAULT_TARGET


def set_default_target(name: str) -> str:
    """把默认目标改为 ``name``（须已注册），返回旧值。"""
    global DEFAULT_TARGET
    if name not in REGISTRY:
        raise KeyError(f"unknown convert target {name!r}; "
                       f"available={sorted(REGISTRY)}")
    old = DEFAULT_TARGET
    DEFAULT_TARGET = name
    return old


@dataclass
class ConvertTarget:
    """一个可写出的目标格式。"""

    name: str
    description: str
    writer: Callable[..., Path]
    #: 需要的 KIND（``"*"`` = 任意）
    requires: tuple[str, ...] = ("*",)
    #: 需要的场名（缺一个就跳过并给出说明，而不是写出坏文件）
    requires_fields: tuple[str, ...] = ()
    #: 需要的坐标轴名（缺一个就跳过 —— 例如 F1 是 (rho,de) 基，没有 Te 轴）
    requires_axes: tuple[str, ...] = ()
    notes: str = ""
    examples: list[str] = field(default_factory=list)

    def can_write(self, table: ParsedTable) -> tuple[bool, str]:
        if "*" not in self.requires and table.kind not in self.requires:
            return False, f"kind {table.kind!r} 不在 {self.requires} 中"
        missing = [f for f in self.requires_fields if f not in table.fields]
        if missing:
            return False, f"缺少场 {missing}（实际有 {sorted(table.fields)}）"
        missing_ax = [a for a in self.requires_axes if a not in table.axes]
        if missing_ax:
            return False, (
                f"缺少坐标轴 {missing_ax}（实际有 {sorted(table.axes)}）—— "
                f"若源表是 F1 的 (rho,de) 基，请先经 "
                f"convert.invert_eos.to_Te_grid 反演到 (rho,Te)"
            )
        return True, ""


REGISTRY: dict[str, ConvertTarget] = {}


def register(target: ConvertTarget) -> ConvertTarget:
    REGISTRY[target.name] = target
    return target


def get_target(name: str) -> ConvertTarget:
    if name not in REGISTRY:
        raise KeyError(f"unknown convert target {name!r}; "
                       f"available={sorted(REGISTRY)}")
    return REGISTRY[name]


def list_targets() -> list[ConvertTarget]:
    return [REGISTRY[k] for k in sorted(REGISTRY)]


def convert(table: ParsedTable, out_path: str | Path,
            target: str | None = None, *, skip_axes_check: bool = False,
            **opts) -> Path:
    """把一张表写成目标格式。

    ``target=None``（默认）时使用 :data:`DEFAULT_TARGET`（``cn4``）——
    即"默认转 cn4，其他类型也可设置"。

    ``skip_axes_check=True``（配合写出器的 ``invert=True``）：跳过「必需坐标轴」检查 ——
    因为写出器会先把 ``(rho, de)`` 反演成 ``(rho, Te)``，此时源表没有 ``Te`` 轴是正常的。
    """
    if target is None:
        target = DEFAULT_TARGET
    t = get_target(target)
    if skip_axes_check:
        if "*" not in t.requires and table.kind not in t.requires:
            raise ValueError(f"cannot convert {table.table_key} -> {target}: "
                             f"kind {table.kind!r} 不在 {t.requires} 中")
        missing = [f for f in t.requires_fields if f not in table.fields]
        if missing:
            raise ValueError(f"cannot convert {table.table_key} -> {target}: "
                             f"缺少场 {missing}")
    else:
        ok, why = t.can_write(table)
        if not ok:
            raise ValueError(f"cannot convert {table.table_key} -> {target}: {why}")
    return t.writer(table, Path(out_path), **opts)


def convert_tables(tables: Iterable[ParsedTable], outdir: str | Path,
                   target: str | None = None, *, on_skip: str = "collect",
                   **opts) -> tuple[list[Path], list[str]]:
    """批量转换；返回 ``(写出的路径, 跳过原因列表)``。

    ``target=None``（默认）时使用 :data:`DEFAULT_TARGET`（``cn4``）。
    """
    if target is None:
        target = DEFAULT_TARGET
    od = Path(outdir)
    od.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    skipped: list[str] = []
    for tb in tables:
        ok, why = get_target(target).can_write(tb)
        if not ok:
            skipped.append(f"{tb.table_key}: {why}")
            if on_skip == "raise":
                raise ValueError(f"{tb.table_key}: {why}")
            continue
        written.append(convert(tb, od / tb.table_key, target, **opts))
    return written, skipped
