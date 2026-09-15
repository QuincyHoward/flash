# -*- coding: utf-8 -*-
"""时间演化绘图 —— (t, x) 二维彩图与特征点时间曲线。

数据来源说明
------------
IONMIX ``cn4`` 输出是 **(T, n_ion) 静态表格，不含时间维度**。
"随时间变化" 的数据来自 **FLASH 辐射流体模拟的 HDF5 时间序列**：

============================  ===================================
文件形态                       说明
============================  ===================================
``*hdf5_plt_cnt_*``           FLASH 原生 plot 文件，逐个时刻
``*plt_cnt_*.hdf5``           同上（命名变体）
``result.h5``                 优化/聚合引擎输出，含 ``ed_time``
============================  ===================================

两种呈现形式
------------
**形式 A** :func:`plot_time_series`
    ``(t, x)`` 二维彩图，展示波前传播 / 加热演化。
**形式 B** :func:`plot_center_series`
    固定空间位置（如靶中心 ``x=0``）的物理量时间曲线。

单位纪律
--------
本模块**不做物理量换算**，只负责排版；调用方负责把时间和坐标换成
**显示单位**（时间 ns、长度 um，换算函数见 :mod:`.units` 的
:func:`~.units.time_ns` / :func:`~.units.length_um`）。
输入为 **cm / s** 时请先转换，否则坐标轴标签与实际量纲不符。
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Optional

import numpy as np

from .. import config

__all__ = [
    "plot_time_series", "plot_center_series",
    "flash_extract", "read_flash_h5",
]


def _plt():
    from .style import apply_style
    return apply_style()


def _save(fig, outfile: str | os.PathLike | None, tag: str) -> str:
    """落盘并关闭 figure（批量场景必须关闭）。"""
    from .style import assert_ascii
    from pathlib import Path as _P
    if outfile is None:
        safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in tag)
        outfile = os.path.join(os.getcwd(), f"{safe}.png")
    outfile = str(outfile)
    _P(outfile).parent.mkdir(parents=True, exist_ok=True)
    assert_ascii(fig)
    fig.savefig(outfile, dpi=config.PLOT_DPI, bbox_inches="tight")
    _plt().close(fig)
    return outfile


# ================================================================
# 形式 A / B
# ================================================================

def plot_time_series(
    times: np.ndarray,
    xgrid: np.ndarray,
    field: np.ndarray,
    *,
    xlabel: str = "x (um)",
    quantity_label: str = "Quantity",
    time_label: str = "Time (ns)",
    title: str = "",
    cmap: str = "inferno",
    zlog: bool | None = None,
    outfile: str | os.PathLike | None = None,
    figsize: tuple[float, float] = (11.0, 8.0),
) -> str:
    """形式 A：``(t, x)`` 时间-空间二维彩图。

    Args:
        times: ``(nt,)`` 时间数组，**显示单位**（通常 ns）
        xgrid: ``(nx,)`` 空间坐标，**显示单位**（通常 um）
        field: ``(nt, nx)`` 物理量场（``field[i]`` = 第 i 个时刻的剖面）
        zlog: 颜色对数色标；``None`` = 量纲跨 >4 个数量级且全正时自动启用

    Returns:
        输出文件路径
    """
    import matplotlib.colors as mcolors

    plt = _plt()
    times = np.asarray(times, dtype=float)
    xgrid = np.asarray(xgrid, dtype=float)
    field = np.asarray(field, dtype=float)
    if field.shape != (times.size, xgrid.size):
        raise ValueError(
            f"field 形状 {field.shape} != (nt={times.size}, nx={xgrid.size})")

    fig, ax = plt.subplots(figsize=figsize)
    X, Y = np.meshgrid(times, xgrid)
    # field 为 (nt, nx)，meshgrid 目标形状 (nx, nt) -> 转置
    fplot = np.ma.masked_invalid(field).T

    if zlog is None:
        fmin = float(np.nanmin(field)) if np.isfinite(field).any() else 0.0
        fmax = float(np.nanmax(field)) if np.isfinite(field).any() else 1.0
        zlog = bool(fmin > 0 and (np.log10(fmax) - np.log10(fmin)) > 4)
    norm = mcolors.LogNorm() if zlog else None

    mesh = ax.pcolormesh(X, Y, fplot, cmap=cmap, norm=norm,
                         shading="auto", rasterized=True)
    ax.set_xlabel(time_label)
    ax.set_ylabel(xlabel)
    if title:
        ax.set_title(title)
    ax.tick_params(which="both", direction="in", top=True, right=True,
                   labelsize=config.PLOT_TICK_FONTSIZE, width=2.0, length=6)
    for s in ax.spines.values():
        s.set_linewidth(2.0)
    cb = fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label(quantity_label, fontsize=config.PLOT_LABEL_FONTSIZE)
    cb.ax.tick_params(labelsize=config.PLOT_TICK_FONTSIZE, width=2.0, length=6)
    cb.outline.set_linewidth(2.0)
    fig.tight_layout()
    return _save(fig, outfile, title or "time_series")


def plot_center_series(
    times: np.ndarray,
    xgrid: np.ndarray,
    field: np.ndarray,
    *,
    x_center: float = 0.0,
    ylog: bool = True,
    xlog: bool = False,
    quantity_label: str = "Quantity",
    time_label: str = "Time (ns)",
    outfile: str | os.PathLike | None = None,
    figsize: tuple[float, float] = (10.0, 7.0),
) -> str:
    """形式 B：给定空间位置（默认靶中心）的物理量时间演化曲线。

    取离 ``x_center`` 最近的网格点。
    """
    plt = _plt()
    times = np.asarray(times, dtype=float)
    xgrid = np.asarray(xgrid, dtype=float)
    field = np.asarray(field, dtype=float)
    if field.shape != (times.size, xgrid.size):
        raise ValueError(
            f"field 形状 {field.shape} != (nt={times.size}, nx={xgrid.size})")

    i = int(np.argmin(np.abs(xgrid - x_center)))
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(times, field[:, i], lw=config.PLOT_LINEWIDTH, marker="o",
            ms=config.PLOT_MARKERSIZE - 2,
            label=f"x = {xgrid[i]:.1e}")
    if xlog:
        ax.set_xscale("log")
    if ylog:
        ax.set_yscale("log")
    ax.set_xlabel(time_label)
    ax.set_ylabel(quantity_label)
    ax.set_title(f"{quantity_label} at x = {xgrid[i]:.1e}")
    ax.grid(True, which="both", alpha=0.3)
    ax.tick_params(which="both", direction="in", top=True, right=True,
                   labelsize=config.PLOT_TICK_FONTSIZE, width=2.0, length=6)
    for s in ax.spines.values():
        s.set_linewidth(2.0)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE)
    fig.tight_layout()
    return _save(fig, outfile, f"center_{quantity_label}")


# ================================================================
# FLASH HDF5 提取
# ================================================================

def read_flash_h5(fp: str | os.PathLike, var: str = "tele",
                  xvar: str = "x") -> tuple[float, np.ndarray, np.ndarray]:
    """读取**单个** FLASH plot 文件，返回 ``(time_s, xgrid_cm, field)``。

    FLASH 原生输出用 ``sim time`` 作为时刻；若缺失则回退到文件名解析出的
    时间戳，最后回退 ``0.0``。

    Returns:
        ``(time, x, field)``；时间/坐标均为 **FLASH 原始单位**（s / cm）。
    """
    import h5py

    with h5py.File(str(fp), "r") as h:
        time = float(h["sim time"][()]) if "sim time" in h else _time_from_name(fp)
        if xvar not in h:
            raise KeyError(f"{fp} 中无 '{xvar}' 数据集；可用: {list(h.keys())[:20]}")
        x = np.asarray(h[xvar][()], dtype=float)
        if var not in h:
            raise KeyError(f"{fp} 中无 '{var}' 数据集；可用: {list(h.keys())[:20]}")
        f = np.asarray(h[var][()], dtype=float)
    return time, x, f


def _time_from_name(fp: str | os.PathLike) -> float:
    """从 FLASH 文件名解析时间戳（``..._hdf5_plt_cnt_0123`` -> 0.0 兜底）。

    FLASH 文件名本身不含物理时间，故仅作为**兜底**并返回 0.0，
    真正的时刻来自文件内 ``sim time``。
    """
    return 0.0


def flash_extract(
    run_dir: str | os.PathLike,
    var: str = "tele",
    *,
    xvar: str = "x",
    out_h5: str | os.PathLike | None = None,
    pattern: str = "*",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """从 FLASH 输出目录提取变量沿 ``x`` 剖面的时间演化。

    扫描顺序：
      1. 若 ``out_h5`` 给出且存在 -> 直接读聚合文件（形式最快）
      2. 否则扫描 ``run_dir`` 下 ``*plt_cnt*.h5*`` / ``*.hdf5``，
         逐文件读 ``sim time``，按时间**升序**排序返回

    Args:
        run_dir: FLASH 输出目录（或聚合文件所在目录）
        var: 变量名（如 ``tele`` / ``dens`` / ``pres``）
        xvar: 空间坐标数据集名（默认 ``x``）
        out_h5: 聚合 HDF5 路径（含 ``ed_time`` 时间数组）
        pattern: 额外 glob 过滤子串

    Returns:
        ``(times (nt,), xgrid (nx,), field (nt, nx))``，**原始单位**（s / cm）。
        ⚠️ 与 FLASH 输出一致，剖面的空间长度可能逐文件不同；本函数以
        **最后一个文件的网格**为准，并要求所有文件网格长度一致。
    """
    if out_h5 and os.path.exists(str(out_h5)):
        return _read_aggregate(out_h5, var)

    run_dir = Path(str(run_dir))
    cands: list[str] = []
    for pat in ("*plt_cnt*.h5", "*plt_cnt*.hdf5", "*.hdf5", "*.h5"):
        cands.extend(sorted(glob.glob(str(run_dir / pat))))
    # 去重并按名字排序（FLASH cnt 编号即时间序）
    seen: set[str] = set()
    files = [f for f in cands
             if pattern in os.path.basename(f)
             and not (f in seen or seen.add(f))]
    if not files:
        raise FileNotFoundError(f"run_dir 下未找到 HDF5 文件: {run_dir}")

    recs: list[tuple[float, np.ndarray, np.ndarray, str]] = []
    for fp in files:
        try:
            t, x, f = read_flash_h5(fp, var, xvar)
        except (KeyError, OSError) as exc:
            # 单文件不适用（如非该变量的输出）-> 跳过而不中断
            print(f"  [skip] {os.path.basename(fp)}: {exc}")
            continue
        recs.append((t, x, f, fp))
    if not recs:
        raise ValueError(f"没有文件同时含 '{var}' 与 '{xvar}'：{run_dir}")

    # 仅保留最长网格的那批（FLASH 重启动可能改分辨率）
    nmax = max(r[1].size for r in recs)
    recs = [r for r in recs if r[1].size == nmax]
    recs.sort(key=lambda r: r[0])

    times = np.array([r[0] for r in recs], dtype=float)
    xgrid = recs[0][1]
    field = np.vstack([r[2] for r in recs])
    return times, xgrid, field


def _read_aggregate(fp: str | os.PathLike, var: str):
    """读取聚合 ``result.h5``：时间数组 + 变量二维场。"""
    import h5py

    with h5py.File(str(fp), "r") as h:
        keys = list(h.keys())
        tkey = "ed_time" if "ed_time" in h else next(
            (k for k in keys if "time" in k.lower()), None)
        if tkey is None:
            raise KeyError(f"{fp} 中未找到时间数组；keys={keys[:20]}")
        times = np.asarray(h[tkey][()], dtype=float)

        vkey = var if var in h else next(
            (k for k in keys if var.lower() in k.lower()), None)
        if vkey is None:
            raise KeyError(f"{fp} 中未找到变量 '{var}'；keys={keys[:20]}")
        field = np.asarray(h[vkey][()], dtype=float)

        xkey = "x" if "x" in h else next(
            (k for k in keys if k.lower() in ("x", "xgrid", "position")), None)
        xgrid = (np.asarray(h[xkey][()], dtype=float) if xkey
                 else np.arange(field.shape[1], dtype=float))
    return times, xgrid, field
