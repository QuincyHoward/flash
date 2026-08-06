"""Unified PPT-friendly plotting style (plot_style).

This module defines the **mandatory** matplotlib style rules for ALL plotting
scripts inside the flash-sim package, so that every generated figure is
directly usable in PPT/report presentations.

Rules (mandatory)
=================
1. **Large fonts (PPT friendly)**: every text element must be >= 18 pt.
   - title   >= 22
   - labels  >= 20
   - ticks   >= 18
   - legend  >= 18
   - colorbar>= 18
2. **English only**: every title / axis label / legend / colorbar / annotation
   must be written in English (ASCII preferred). Use `english()` to sanitize
   any string that may contain CJK or non-ASCII math symbols.
3. **No Chinese font dependency**: only explicit English font families are
   used, so figures render identically on any machine (no glyph warnings).
4. **High DPI output**: default dpi=200, suitable for printing & projection.

Usage
=====
Call once at the top of any plotting script, right after importing pyplot::

    import matplotlib.pyplot as plt
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()

Or use the convenience helpers::

    from output_processors.plotter.plot_style import (
        new_figure, save_figure, english, PPT_FIGSIZE_WIDE,
    )
    fig, ax = new_figure(PPT_FIGSIZE_WIDE)        # 12x6 inch canvas
    ax.set_title(english("Density Profile"), fontsize=22)
    save_figure(fig, "density.png")               # dpi=200, tight bbox

Compliance
==========
Run `python scripts/check_plot_style.py` to scan the package for scripts that
miss `apply_plot_style()` or still contain CJK characters in plot text.
"""

from __future__ import annotations

import re

import matplotlib

# ── PPT-friendly font sizes (minimum 18) ──────────────────────
FONT_TITLE = 22        # figure / axes title
FONT_LABEL = 20        # axis label / colorbar label
FONT_TICK = 18         # tick labels
FONT_LEGEND = 18       # legend text
FONT_ANNOT = 18        # in-figure annotation / text
FONT_CBAR = 18         # colorbar label

# ── Preset canvas sizes (inches) ──────────────────────────────
PPT_FIGSIZE_WIDE = (12, 6)       # wide 2:1 (default recommended)
PPT_FIGSIZE_SQUARE = (8, 8)      # square
PPT_FIGSIZE_PANEL = (16, 6)      # double panel
PPT_FIGSIZE_TALL = (8, 10)       # tall

# ── Common English labels (ASCII) ─────────────────────────────
X_LABEL = "x [um]"
Y_LABEL_DENS = "Mass density [g/cm^3]"
Y_LABEL_TEMP = "Temperature [K]"
Y_LABEL_PRESS = "Pressure [dyne/cm^2]"
T_LABEL = "Time [s]"
T_LABEL_PS = "Time [ps]"

# ── CJK / Unicode symbol -> ASCII replacement table ───────────
_ENGLISH_MAP = {
    "μm": "um",
    "µm": "um",
    "μ": "u",
    "g/cm³": "g/cm^3",
    "g/cm3": "g/cm^3",
    "cm³": "cm^3",
    "℃": " C",
    "°C": " C",
    "°": " deg",
    "×": "x",
    "—": "-",
    "–": "-",
    "−": "-",
    "≥": ">=",
    "≤": "<=",
    "≈": "~",
    "≠": "!=",
    "→": "->",
    "←": "<-",
    "↑": "^",
    "↓": "v",
    # Common CJK plot titles
    "双密度对比": "Density Comparison",
    "末时刻密度空间剖面": "Density Profile (Final Time)",
    "中心点密度时间演化": "Central Density vs Time",
    "密度演化热图": "Density x-t Heatmap",
    "密度时间演化": "Density vs Time",
    "密度空间剖面": "Density Profile",
    "激光脉冲": "Laser Pulse",
    "初始密度": "Initial Density",
    "温度演化": "Temperature Evolution",
    "压力演化": "Pressure Evolution",
    "速度演化": "Velocity Evolution",
    "密度统计": "Density Statistics",
    "时间演化": "Time Evolution",
    "空间剖面": "Spatial Profile",
    "对比": "Comparison",
    "演化": "Evolution",
    "剖面": "Profile",
    "密度": "Density",
    "温度": "Temperature",
    "压力": "Pressure",
    "速度": "Velocity",
}

# Regex for CJK range: \u4e00-\u9fff (CJK Unified Ideographs)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


# Map keys sorted by length (descending) so longer phrases win first
_ENGLISH_MAP_SORTED = sorted(_ENGLISH_MAP.items(), key=lambda kv: len(kv[0]),
                             reverse=True)


def english(text: str) -> str:
    """Sanitize a string to pure English/ASCII for plot text.

    Replaces common CJK plot phrases and Unicode unit symbols with
    ASCII equivalents so matplotlib never hits a missing-glyph warning
    and the output is PPT-safe. Longer phrases are matched first.

    Examples:
        english("x (μm)")               -> "x (um)"
        english("density (g/cm³)")      -> "density (g/cm^3)"
        english("双密度对比 — 密度剖面") -> "Density Comparison - Density Profile"
    """
    if not isinstance(text, str):
        return str(text)
    for zh, en in _ENGLISH_MAP_SORTED:
        text = text.replace(zh, en)
    return text


def contains_cjk(text: str) -> bool:
    """Return True if the string contains any CJK Unified Ideograph."""
    return bool(_CJK_RE.search(text or ""))


def apply_plot_style(dpi: int = 200) -> None:
    """Apply the global PPT-friendly matplotlib style via rcParams.

    Must be called once, after `import matplotlib.pyplot`, before any
    plotting. All subsequent figures inherit large fonts (>= 18),
    English-only fonts, and high DPI.
    """
    matplotlib.rcParams.update({
        # ── Font family: explicit English, no CJK font dependency ──
        "font.family": "sans-serif",
        "font.sans-serif": [
            "DejaVu Sans", "Arial", "Helvetica", "Liberation Sans",
            "Nimbus Sans", "Noto Sans", "Tahoma", "Verdana",
        ],
        "font.size": 18,
        "axes.titlesize": FONT_TITLE,      # 22
        "axes.labelsize": FONT_LABEL,      # 20
        "xtick.labelsize": FONT_TICK,      # 18
        "ytick.labelsize": FONT_TICK,      # 18
        "legend.fontsize": FONT_LEGEND,    # 18
        "figure.titlesize": FONT_TITLE,    # 22
        "axes.titleweight": "bold",
        "axes.labelweight": "bold",

        # ── Output quality ──
        "figure.dpi": 150,
        "savefig.dpi": dpi,
        "savefig.bbox": "tight",

        # ── Grid & lines ──
        "axes.grid": True,
        "grid.alpha": 0.3,
        "lines.linewidth": 2.5,
        "lines.markersize": 8,
        "axes.linewidth": 1.2,

        # ── Legend ──
        "legend.framealpha": 0.9,
        "legend.edgecolor": "0.6",
        "legend.handlelength": 2.0,
    })


def new_figure(figsize=PPT_FIGSIZE_WIDE, dpi: int = 200):
    """Create a PPT-friendly figure + axes with the global style applied.

    Returns:
        (fig, ax): a fresh canvas; call `fig.colorbar(..., ax=ax)` or
        `ax.set_title(...)` etc. as usual.
    """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    return fig, ax


def save_figure(fig, path: str, dpi: int = 200, tight: bool = True) -> str:
    """Save a figure with the standard PPT settings and close it.

    Args:
        fig: the matplotlib figure to save.
        path: output file path (png/pdf/svg...).
        dpi: output resolution (default 200).
        tight: use bbox_inches="tight" (default True).

    Returns:
        the saved path.
    """
    import matplotlib.pyplot as plt
    fig.savefig(path, dpi=dpi, bbox_inches="tight" if tight else None,
                facecolor="white")
    plt.close(fig)
    return str(path)


def setup_colorbar(cbar, label: str = "", fontsize: int = FONT_CBAR) -> None:
    """Set a colorbar label in English with the standard font size."""
    cbar.set_label(english(label), fontsize=fontsize)


def setup_legend(ax, fontsize: int = FONT_LEGEND, **kwargs) -> None:
    """Add a legend with the standard English font size.

    Args:
        ax: the axes to add the legend to.
        fontsize: legend font size (default 18).
        **kwargs: forwarded to ax.legend().
    """
    ax.legend(fontsize=fontsize, **kwargs)
