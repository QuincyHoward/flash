"""
gen_flychk_his.preview — 输入预诊断图
=====================================

生成 FLYCHK history 输入的**先验检查图**（提交前人工核对 te / 密度 / size
的时间演化是否符合物理预期）。绘图规范遵循项目约定:

- 全英文标注 (title / axis / legend / tick)
- 字号 >= 18 pt (title 26, label 22, tick 20, legend 18)
- DPI >= 450, 线宽 >= 2, 标记 >= 8

时间轴单位按跨度自动选择 fs / ps / ns / us。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import units
from .builder import HistoryTable

# ── PPT 演讲级绘图参数 ─────────────────────────────────────
STYLE = {
    "title": 26,
    "label": 22,
    "tick": 20,
    "legend": 18,
    "linewidth": 2.5,
    "markersize": 9,
    "dpi": 450,
}

_AXIS_FOR_COLUMN = {
    "te": ("Temperature (eV)", "Electron temperature Te"),
    "ti": ("Temperature (eV)", "Ion temperature Ti"),
    "tr": ("Temperature (eV)", "Radiation temperature Tr"),
    "rho": ("Density (g/cm$^3$)", "Mass density"),
    "ne": ("Density (cm$^{-3}$)", "Electron number density"),
    "ni": ("Density (cm$^{-3}$)", "Ion number density"),
    "size": ("Size (cm)", "Plasma size (path length)"),
}


def time_axis_label(time_seconds: np.ndarray) -> Tuple[np.ndarray, str]:
    """按跨度选择时间单位，返回 (换算后时间, 轴标签)。"""
    t = np.asarray(time_seconds, dtype=np.float64)
    span = float(np.nanmax(t) - np.nanmin(t)) if t.size else 0.0
    for unit, scale in (("fs", 1e-15), ("ps", 1e-12), ("ns", 1e-9), ("us", 1e-6)):
        if span and span < 1000.0 * scale:
            return t / scale, f"Time ({unit})"
    if span == 0.0:
        return t / 1e-12, "Time (ps)"
    return t / 1e-9, "Time (ns)"


def plot_input_preview(table: HistoryTable, output_path,
                       element: Optional[str] = None, z: Optional[int] = None,
                       title: Optional[str] = None,
                       dpi: Optional[int] = None) -> Path:
    """绘制 FLYCHK 输入预诊断图 (温度 / 密度 / size 随时间)。"""
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    cols = list(table.columns)
    elem = element or table.element
    zz = z or table.z
    region = table.meta.get("region", "region")

    t_sec = table.column("time") / (1.0 / units.to_s(1.0, table.meta.get("time_unit", "s")))
    t_plot, tlabel = time_axis_label(t_sec)

    temp_cols = [c for c in ("te", "ti", "tr") if c in cols]
    dens_cols = [c for c in ("rho", "ne", "ni") if c in cols]
    has_size = "size" in cols

    panels: List[Tuple[str, str, List[Tuple[str, np.ndarray]]]] = []
    if temp_cols:
        panels.append(("Temperature", "Temperature (eV)",
                       [(c.upper(), table.column(c)) for c in temp_cols]))
    if dens_cols:
        c = dens_cols[0]
        ylabel, label = _AXIS_FOR_COLUMN[c]
        panels.append(("Density", ylabel, [(label, table.column(c))]))
    if has_size:
        panels.append(("Plasma size", "Size (cm)",
                       [("Path length", table.column("size"))]))
    if not panels:
        raise ValueError(f"表中无可绘图列 (columns={cols})")

    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(7.2 * n, 5.6), squeeze=False)
    axes = axes.ravel()

    colors = ["#C0392B", "#1F4E79", "#1E8449", "#8E44AD", "#B9770E"]
    for ax, (pname, ylabel, series) in zip(axes, panels):
        for i, (lbl, arr) in enumerate(series):
            ax.plot(t_plot, arr, "-o", color=colors[i % len(colors)],
                    linewidth=STYLE["linewidth"], markersize=STYLE["markersize"],
                    label=lbl)
        if ylabel.startswith("Density") and len(series) == 1 and \
                (np.nanmax(series[0][1]) / max(np.nanmin(series[0][1]), 1e-30)) > 1e2:
            ax.set_yscale("log")
        ax.set_xlabel(tlabel, fontsize=STYLE["label"])
        ax.set_ylabel(ylabel, fontsize=STYLE["label"])
        ax.tick_params(labelsize=STYLE["tick"])
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(fontsize=STYLE["legend"], loc="best")
        ax.set_title(pname, fontsize=STYLE["label"])

    fig.suptitle(
        title or f"FLYCHK history input preview - {elem} (Z={zz}), region '{region}', "
                 f"{table.n_steps} time steps",
        fontsize=STYLE["title"])
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi or STYLE["dpi"], bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    return out


def plot_region_overview(tables: Dict[str, HistoryTable], output_path,
                         element: str = "Ti", z: int = 22,
                         dpi: Optional[int] = None) -> Path:
    """多区域概览图: 温度与密度各一张子图，叠加所有区域曲线。"""
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    if not tables:
        raise ValueError("tables 为空")

    fig, axes = plt.subplots(1, 2, figsize=(14.4, 5.6))
    colors = ["#C0392B", "#1F4E79", "#1E8449", "#8E44AD", "#B9770E", "#0E6655"]
    first = next(iter(tables.values()))
    tu = first.meta.get("time_unit", "s")
    factor = 1.0 / units.to_s(1.0, tu)

    for i, (label, tb) in enumerate(tables.items()):
        t_sec = tb.column("time") / factor
        t_plot, tlabel = time_axis_label(t_sec)
        c = colors[i % len(colors)]
        if "te" in tb.columns:
            axes[0].plot(t_plot, tb.column("te"), "-o", color=c,
                         linewidth=STYLE["linewidth"],
                         markersize=STYLE["markersize"], label=label)
        dens_col = next((x for x in ("rho", "ne", "ni") if x in tb.columns), None)
        if dens_col:
            axes[1].plot(t_plot, tb.column(dens_col), "-s", color=c,
                         linewidth=STYLE["linewidth"],
                         markersize=STYLE["markersize"], label=label)

    axes[0].set_xlabel(tlabel, fontsize=STYLE["label"])
    axes[0].set_ylabel("Electron temperature Te (eV)", fontsize=STYLE["label"])
    axes[1].set_xlabel(tlabel, fontsize=STYLE["label"])
    axes[1].set_ylabel("Density (g/cm$^3$ or cm$^{-3}$)", fontsize=STYLE["label"])
    for ax in axes:
        ax.tick_params(labelsize=STYLE["tick"])
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.legend(fontsize=STYLE["legend"], loc="best")
    fig.suptitle(f"FLYCHK history inputs by region - {element} (Z={z}), "
                 f"{len(tables)} regions", fontsize=STYLE["title"])
    fig.tight_layout(rect=(0, 0, 1, 0.93))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi or STYLE["dpi"], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


__all__ = ["plot_input_preview", "plot_region_overview", "time_axis_label", "STYLE"]
