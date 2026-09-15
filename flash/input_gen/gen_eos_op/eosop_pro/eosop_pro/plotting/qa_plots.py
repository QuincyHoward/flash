"""质量保证出图 —— EOS 等压线 / 不透明度热图 / Zeff 图（全英文、PPT 级）。

所有函数都返回 :class:`matplotlib.figure.Figure` 并可写出 PNG；
文本一律英文（由 :func:`plotting.style.assert_ascii` 保证）。

★ 标签纪律（用户 2026-09-15 第十二轮裁定）：所有 x/y 轴与 colorbar
标签一律经 :func:`.labels.field_label` 从控制字典实时取物理意义 / 单位
/ 认证标记 —— 人工核查翻 ``checked`` 后下一次出图自动同步，本模块
不硬编码任何物理量标签。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .. import config
from ..grid.interpolate import log10_or_nan
from ..parsers.base import ParsedTable
from .labels import field_label
from .style import apply_style, assert_ascii

__all__ = ["plot_eos_isobars", "plot_opacity_heatmap", "plot_zeff",
           "plot_loglog_curve", "save_fig"]

plt = None  # 由 apply_style() 惰性注入


def _plt():
    global plt
    if plt is None:
        plt = apply_style()
    return plt


def save_fig(fig, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    assert_ascii(fig)
    fig.savefig(p, dpi=config.PLOT_DPI, bbox_inches="tight")
    return p


def _grid_mesh(axis_x, axis_y):
    X, Y = np.meshgrid(np.asarray(axis_x, float), np.asarray(axis_y, float))
    return X, Y


def _close_if_saved(fig, out_path):
    """★ 落盘后关闭 figure，避免批量出图时 pyplot 累积。

    实测 ``plot-all`` 出 60 组图时报
    ``RuntimeWarning: More than 20 figures have been opened`` —— 内存持续增长。
    只在**传了 out_path**（即调用方不再需要这个 figure）时关闭；
    不传 out_path 则保留，便于调用方继续检查或二次保存（测试就是这么用的）。
    """
    if out_path is not None:
        _plt().close(fig)


def plot_eos_isobars(table: ParsedTable, field: str = "P", *,
                     densities=(0.01, 0.1, 1.0, 10.0), out_path=None):
    """EOS 等密度线：``field`` vs ``Te``（各密度一条曲线）。

    适用于 F1（``(rho, de)`` 基）与 F4（``(rho, Te)`` 基）。
    """
    P = _plt()
    fig, ax = P.subplots()
    Te = np.asarray(table.axes.get("Te", []), dtype=float)
    rho = np.asarray(table.axes.get("rho", []), dtype=float)
    if Te.size == 0 or rho.size == 0:
        raise ValueError("table has no (rho, Te) axes for isobar plot")
    arr = np.asarray(table.fields[field], dtype=float)
    shape = table.field_shape.get(field, (Te.size, rho.size))
    if len(shape) != 2 or shape[0] != Te.size:
        raise ValueError(f"field {field!r} is not a (Te, rho) 2-D field")
    arr = arr.reshape(shape)

    # ★ rho 可能含 0（实测 F1 的 rho[0] == 0.0）→ log10 会给 -inf 并触发
    #   "divide by zero encountered in log10"；只在正 rho 上选等密度线。
    pos = rho > 0
    if not pos.any():
        raise ValueError("table has no positive rho for isobar plot")
    log_rho_pos = np.log10(rho[pos])
    idx_pos = np.nonzero(pos)[0]
    for d in densities:
        if d <= 0:
            continue
        j = int(idx_pos[int(np.argmin(np.abs(log_rho_pos - np.log10(d))))])
        y = arr[:, j]
        # ★ 散点规约（用户 2026-09-15 晚）：uk/uv 数据一律散点（lw=0），
        #   不连线 —— 未核查数据不得呈现插值连续性暗示。
        ax.plot(Te, y, marker="o", markersize=config.PLOT_MARKERSIZE - 2,
                linewidth=0, linestyle="none",
                label=f"rho = {rho[j]:.3g} g/cc")
    ax.set_xscale("log")
    ax.set_yscale("log")
    # 轴标签走控制字典（意义 + 单位 + uk/uv 标记，实时同步）
    ax.set_xlabel(field_label(table.family, "Te",
                              parser_unit=table.axis_units.get("Te", "")))
    ax.set_ylabel(field_label(table.family, field,
                              parser_unit=table.field_units.get(field, "")))
    ax.set_title(f"{table.table_key}: EOS isobars")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    if out_path:
        save_fig(fig, out_path)
    _close_if_saved(fig, out_path)
    return fig


def plot_opacity_heatmap(table: ParsedTable, field: str = "kappa", *,
                         out_path=None, log_value: bool | None = None):
    """不透明度热图：``log10(kappa)`` 在 ``(log rho, log T)`` 平面上的等值图。"""
    P = _plt()
    rho = np.asarray(table.axes["rho"], dtype=float)
    Te = np.asarray(table.axes["Te"], dtype=float)
    arr = np.asarray(table.fields[field], dtype=float)
    shape = table.field_shape[field]
    if len(shape) != 2:
        raise ValueError(f"{field!r} is not 2-D")
    arr = arr.reshape(shape)
    lv = bool(table.field_log10.get(field, False)) if log_value is None else log_value
    Z = arr if lv else log10_or_nan(arr)

    fig, ax = P.subplots()
    X = log10_or_nan(rho)
    Y = log10_or_nan(Te)
    im = ax.pcolormesh(X, Y, Z, shading="nearest", cmap=config.PLOT_CMAP)
    cb = fig.colorbar(im, ax=ax)
    # 轴/colorbar 显示的是 log10 变换值：意义/单位/标记仍走控制字典，
    # 前缀 "log10 " 描述本图实际画的数值（对数坐标）。
    cb.set_label("log10 " + field_label(
        table.family, field, parser_unit=table.field_units.get(field, "")))
    ax.set_xlabel("log10 " + field_label(
        table.family, "rho", parser_unit=table.axis_units.get("rho", "")))
    ax.set_ylabel("log10 " + field_label(
        table.family, "Te", parser_unit=table.axis_units.get("Te", "")))
    ax.set_title(f"{table.table_key}: opacity map")
    if out_path:
        save_fig(fig, out_path)
    _close_if_saved(fig, out_path)
    return fig


def plot_zeff(table: ParsedTable, field: str = "Z", *,
              out_path=None):
    """Z̄(ρ,T) 图：若干密度下的 Z̄ vs T。"""
    P = _plt()
    rho = np.asarray(table.axes["rho"], dtype=float)
    Te = np.asarray(table.axes["Te"], dtype=float)
    arr = np.asarray(table.fields[field], dtype=float).reshape(
        table.field_shape.get(field, (Te.size, rho.size)))
    fig, ax = P.subplots()
    picks = np.linspace(0, rho.size - 1, min(4, rho.size)).astype(int)
    for j in picks:
        # ★ 散点规约（用户 2026-09-15 晚）：uk/uv 数据一律散点（lw=0）。
        ax.plot(Te, arr[:, j], marker="s", markersize=config.PLOT_MARKERSIZE,
                linewidth=0, linestyle="none",
                label=f"rho = {rho[j]:.3g} g/cc")
    ax.set_xscale("log")
    ax.set_xlabel(field_label(table.family, "Te",
                              parser_unit=table.axis_units.get("Te", "")))
    ax.set_ylabel(field_label(table.family, field,
                              parser_unit=table.field_units.get(field, "")))
    ax.set_title(f"{table.table_key}: effective charge")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    if out_path:
        save_fig(fig, out_path)
    _close_if_saved(fig, out_path)
    return fig


def plot_loglog_curve(x, y, *, xlabel="x", ylabel="y", title="curve",
                      out_path=None):
    """通用 log-log 曲线（用于冷不透明度等一维表）。

    ★ 散点规约（用户 2026-09-15 晚）：本函数画的是原始表数据点
    （多为 uk/uv 族），一律散点呈现（lw=0），不连线。
    """
    P = _plt()
    fig, ax = P.subplots()
    ax.plot(x, y, linewidth=0, linestyle="none",
            marker="o", markersize=config.PLOT_MARKERSIZE - 3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.3)
    if out_path:
        save_fig(fig, out_path)
    _close_if_saved(fig, out_path)
    return fig
