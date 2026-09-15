"""PPT / 演讲级绘图样式 —— 全英文、大字号、高 DPI。

硬性要求（用户长期约定，全部可测）
----------------------------------
============  ==========================
项             要求
============  ==========================
title         ≥ 24 pt
轴标签         ≥ 20 pt
刻度           ≥ 20 pt
图例           ≥ 18 pt
DPI           ≥ 450
linewidth     ≥ 2
markersize    ≥ 8
文本语言       **仅 ASCII（英文）**
============  ==========================

``test_plots`` 会逐条断言这些，**包括「文本必须全 ASCII」**（正则 ``^[\\x00-\\x7F]*$``）——
因为中文在 PPT 里常出现字体缺失与乱码。
"""

from __future__ import annotations

import re

from .. import config

__all__ = ["apply_style", "ASCII_RE", "assert_ascii", "all_text_ascii", "style_report"]

#: 允许的字符集（可打印 ASCII + 常见空白）
ASCII_RE = re.compile(r"^[\x00-\x7F]*$")


def apply_style():
    """应用全局 rcParams（幂等）。返回 ``matplotlib`` 模块。"""
    import matplotlib
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.dpi": config.PLOT_DPI,
        "savefig.dpi": config.PLOT_DPI,
        "figure.figsize": config.PLOT_FIGSIZE,
        "font.size": config.PLOT_TICK_FONTSIZE,
        "axes.titlesize": config.PLOT_TITLE_FONTSIZE,
        "axes.labelsize": config.PLOT_LABEL_FONTSIZE,
        "xtick.labelsize": config.PLOT_TICK_FONTSIZE,
        "ytick.labelsize": config.PLOT_TICK_FONTSIZE,
        "legend.fontsize": config.PLOT_LEGEND_FONTSIZE,
        "lines.linewidth": config.PLOT_LINEWIDTH,
        "lines.markersize": config.PLOT_MARKERSIZE,
        "axes.linewidth": 1.5,
        "xtick.major.width": 1.5,
        "ytick.major.width": 1.5,
        "xtick.major.size": 7,
        "ytick.major.size": 7,
        "savefig.bbox": "tight",
        "figure.autolayout": False,
        # 只用 ASCII 字体族，避免中文字形缺失导致的乱码与告警
        "font.family": "DejaVu Sans",
        "axes.unicode_minus": False,
    })
    return plt


def all_text_ascii(fig) -> tuple[bool, list[str]]:
    """检查图中所有可见文本是否纯 ASCII。返回 ``(ok, offenders)``。"""
    bad: list[str] = []
    for ax in fig.get_axes():
        texts = [ax.get_title(), ax.get_xlabel(), ax.get_ylabel()]
        for t in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            texts.append(t.get_text())
        leg = ax.get_legend()
        if leg is not None:
            texts.extend(t.get_text() for t in leg.get_texts())
        for t in texts:
            if t and not ASCII_RE.match(str(t)):
                bad.append(str(t))
    supt = getattr(fig, "_suptitle", None)
    if supt is not None and supt.get_text() and not ASCII_RE.match(supt.get_text()):
        bad.append(supt.get_text())
    return (not bad), bad


def assert_ascii(fig) -> None:
    ok, bad = all_text_ascii(fig)
    if not ok:
        raise AssertionError(f"图中存在非 ASCII 文本（PPT 会乱码）: {bad[:5]}")


def style_report() -> dict:
    """返回当前关键 rcParams（供测试与文档核对）。"""
    import matplotlib.pyplot as plt
    return {
        "figure.dpi": plt.rcParams["figure.dpi"],
        "axes.titlesize": plt.rcParams["axes.titlesize"],
        "axes.labelsize": plt.rcParams["axes.labelsize"],
        "xtick.labelsize": plt.rcParams["xtick.labelsize"],
        "legend.fontsize": plt.rcParams["legend.fontsize"],
        "lines.linewidth": plt.rcParams["lines.linewidth"],
        "lines.markersize": plt.rcParams["lines.markersize"],
        "font.family": plt.rcParams["font.family"],
    }
