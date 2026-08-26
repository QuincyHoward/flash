# -*- coding: utf-8 -*-
"""
IONMIX .cn4 数据通用绘图模块
==============================

提供 PPT 演讲级绘图风格 (全英文字符、大字号、高分辨率) 与
2D 彩图 (热图) 通用绘制函数, 支持后续扩展其他物理量。

约定 (来自用户项目规范):
- 全英文字符 (title/labels/ticks/colorbar)
- title >= 24pt, labels >= 20pt, ticks >= 20pt, colorbar >= 20pt
- DPI >= 450
- 密度/温度坐标默认对数, 物理量线性
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# ---------------------------------------------------------------
# 全局绘图风格
# ---------------------------------------------------------------

FONT_SIZE_TITLE = 26
FONT_SIZE_LABEL = 22
FONT_SIZE_TICK = 20
FONT_SIZE_CBAR = 20
DPI = 450


def setup_style() -> None:
    """设置 PPT 演讲级 matplotlib 全局风格"""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": FONT_SIZE_TICK,
        "axes.titlesize": FONT_SIZE_TITLE,
        "axes.labelsize": FONT_SIZE_LABEL,
        "axes.linewidth": 2.0,
        "xtick.labelsize": FONT_SIZE_TICK,
        "ytick.labelsize": FONT_SIZE_TICK,
        "xtick.major.size": 8,
        "ytick.major.size": 8,
        "xtick.major.width": 2.0,
        "ytick.major.width": 2.0,
        "legend.fontsize": 20,
        "legend.frameon": True,
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        # 全局网格线 (便于读数): 主次刻度均显示, 浅灰细线
        "axes.grid": True,
        "axes.grid.which": "both",
        "grid.alpha": 0.35,
        "grid.linestyle": ":",
        "grid.linewidth": 0.8,
        "grid.color": "#888888",
    })


# ---------------------------------------------------------------
# 通用 2D 热图
# ---------------------------------------------------------------

def compute_r2(y: np.ndarray, yfit: np.ndarray) -> float:
    """计算决定系数 R^2, 衡量拟合优度"""
    y = np.asarray(y, dtype=float)
    yfit = np.asarray(yfit, dtype=float)
    ss_res = np.sum((y - yfit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def apply_axes_style(ax, lw: float = 2.0, tick_size: float = 6,
                     n_exclude: list = None) -> None:
    """统一设置坐标轴边框/刻度线宽 (PPT 演讲级风格)"""
    if n_exclude is None:
        n_exclude = []
    for name, spine in ax.spines.items():
        if name not in n_exclude:
            spine.set_linewidth(lw)
    ax.tick_params(labelsize=FONT_SIZE_TICK, width=lw, length=tick_size)
    # 网格线 (主次刻度, 便于读数)
    ax.grid(True, which="both", alpha=0.35, linestyle=":", linewidth=0.8,
            color="#888888")


def save_fig(fig, outfile: str, tag: str = "fig", base_dir: str = None) -> str:
    """
    统一保存图像 (DPI=450, tight bbox)。
    outfile 为 None 时按 base_dir/tag.png 生成 (base_dir 缺省为 cwd)。
    """
    if outfile is None:
        d = base_dir or os.getcwd()
        outfile = os.path.join(d, f"{tag}.png")
    outfile = os.path.abspath(outfile)
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    fig.savefig(outfile, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return outfile


def plot_heatmap(
    temperature: np.ndarray,      # (ntemp,) eV, 升序
    density: np.ndarray,          # (ndens,) cm^-3, 升序
    field: np.ndarray,            # (ndens, ntemp) 物理量场
    quantity_label: str,          # 物理量名称 (colorbar 标签)
    title: str = "",
    cmap: str = "cubehelix",
    vmin: float = None,
    vmax: float = None,
    xlog: bool = True,
    ylog: bool = True,
    zlog: bool = False,
    figsize: tuple = (10.0, 7.5),
    outfile: str = None,
    xlabel: str = "Temperature (eV)",
    ylabel: str = r"Ion Number Density $n_i$ ($\mathrm{cm^{-3}}$)",
    hull_xy: np.ndarray = None,   # 数据覆盖域凸包顶点 (N,2) 原始坐标, 画虚线边界
    nan_color: str = "white",     # NaN 区域填充色 (数据域外留白)
) -> str:
    """
    绘制 2D 彩图: x=温度(eV), y=纵轴物理量, 颜色=物理量。

    Args:
        temperature: 温度数组 (eV)
        density: 纵轴数组 (ndens,), 可为离子数密度/电子数密度/质量密度
        field: 物理量场, shape (ndens, ntemp); 允许含 NaN (显示为 nan_color)
        quantity_label: colorbar 标签 (英文)
        title: 图标题 (英文)
        cmap: colormap 名称, 默认 cubehelix
        vmin/vmax: 颜色映射范围, None=自动
        xlog/ylog: 温度/纵轴是否对数坐标 (默认 True)
        zlog: 物理量是否对数颜色 (默认 False, 线性)
        figsize: 图尺寸 (英寸)
        outfile: 输出 PNG 路径; None 时自动生成
        xlabel/ylabel: 坐标轴标签 (英文, 默认温度/离子数密度)
        hull_xy: 数据覆盖域凸包顶点数组 (N,2) (第0列=x坐标, 第1列=y坐标,
                 与 temperature/density 同单位); 提供时在其上画黑色虚线边界
        nan_color: NaN/数据域外填充色, 默认白色

    Returns:
        str: 保存的 PNG 文件路径
    """
    setup_style()

    fig, ax = plt.subplots(figsize=figsize)

    # 坐标网格: 温度 x, 纵轴 y
    X, Y = np.meshgrid(temperature, density)

    norm = None
    if zlog:
        norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
    else:
        if vmin is None:
            vmin = np.nanmin(field)
        if vmax is None:
            vmax = np.nanmax(field)
        if vmin == vmax:          # 恒定场保护
            vmax = vmin + 1.0
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    # NaN 掩膜: 数据域外显示为 nan_color (默认白色留白)
    if np.isnan(field).any():
        field_plot = np.ma.masked_invalid(field)
        cmap_plot = plt.get_cmap(cmap).copy()
        cmap_plot.set_bad(nan_color)
    else:
        field_plot = field
        cmap_plot = cmap

    sm = ax.pcolormesh(
        X, Y, field_plot,
        cmap=cmap_plot,
        norm=norm,
        shading="auto",
        rasterized=True,
    )

    if xlog:
        ax.set_xscale("log")
    if ylog:
        ax.set_yscale("log")

    # 坐标轴标签与刻度
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    # 数据覆盖域凸包边界 (虚线框)
    if hull_xy is not None:
        hull_xy = np.asarray(hull_xy, dtype=float)
        if ylog:
            hull_xy = hull_xy.copy()
            hull_xy[:, 1] = np.log10(hull_xy[:, 1])
        if xlog:
            hull_xy = hull_xy.copy()
            hull_xy[:, 0] = np.log10(hull_xy[:, 0])
        # 闭合多边形
        hull_closed = np.vstack([hull_xy, hull_xy[0]])
        ax.plot(hull_closed[:, 0], hull_closed[:, 1],
                color="black", ls="--", lw=2.0, zorder=5,
                label="Data coverage domain")

    # 颜色条
    cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(quantity_label, fontsize=FONT_SIZE_CBAR)
    cbar.ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    cbar.outline.set_linewidth(2.0)

    fig.tight_layout()

    if outfile is None:
        outfile = "heatmap.png"
    outfile = os.path.abspath(outfile)
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    fig.savefig(outfile, dpi=DPI)
    plt.close(fig)
    return outfile


# ---------------------------------------------------------------
# zbar 专用封装 (保留后续扩展空间)
# ---------------------------------------------------------------

def plot_zbar(
    temperature: np.ndarray,
    density: np.ndarray,
    zbar: np.ndarray,
    species_label: str = "",
    outdir: str = ".",
    basename: str = "zbar",
    cmap: str = "cubehelix",
) -> str:
    """
    绘制电离度 zbar 随温度、密度变化的彩图。

    - x 轴: 温度 (eV, 对数)
    - y 轴: 离子数密度 (cm^-3, 对数)
    - 颜色: zbar (线性)
    - 色条: cubehelix
    """
    title = "Average Ionization State $\\langle Z \\rangle$"
    if species_label:
        title = f"{title} of {species_label}"

    return plot_heatmap(
        temperature=temperature,
        density=density,
        field=zbar,
        quantity_label="Average charge state $\\langle Z \\rangle$",
        title=title,
        cmap=cmap,
        outfile=os.path.join(outdir, f"{basename}.png"),
    )


if __name__ == "__main__":
    # 自测: 合成高斯数据
    t = np.logspace(0, 4, 40)
    n = np.logspace(16, 25, 30)
    T, N = np.meshgrid(t, n)
    z = 3.5 * np.exp(-((np.log10(T) - 2.0) ** 2) / 1.0) * np.clip(np.log10(N) - 15, 0, 1) / 10
    out = plot_heatmap(
        t, n, z,
        quantity_label="Test field",
        title="Test Heatmap",
        outfile="_test_heatmap.png",
    )
    print("test ok:", out)
    os.remove(out)
