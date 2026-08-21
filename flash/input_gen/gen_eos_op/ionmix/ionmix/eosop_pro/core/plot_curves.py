# -*- coding: utf-8 -*-
"""
IONMIX .cn4 一维变化曲线模块 (任务B: 物理量随单变量变化)
========================================================

场景:
  1. 固定离子数密度, 扫描温度: 物理量(T) | n_i 固定
  2. 固定温度, 扫描离子数密度: 物理量(n_i) | T 固定
  3. 不透明度随温度/密度变化 (按群多条曲线对比)
  4. 沿二维场对角线/自定义路径取样

用法示例:
    from cn4_parser import load_cn4
    from plot_curves import plot_vs_temperature, plot_vs_density

    d = load_cn4("Z06_0.50-Z01_0.50.cn4", atomwt=[12.011, 1.008])

    # zbar 随 T 变化, 取 3 条不同密度的曲线
    plot_vs_temperature(d, "zbar", density_idx=[0, 10, 20],
                        outfile="zbar_vs_T.png")

    # 第 1 群 Rosseland 不透明度随密度变化, 3 条温度曲线
    plot_vs_density(d, "opac_rosseland", ig=1, temp_idx=[0, 20, 40],
                    outfile="rosseland_g1_vs_nion.png")
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cn4_parser import CN4Data
from plot_heatmaps import axis_label, _resolve_quantity
from plot_utils import setup_style, FONT_SIZE_LABEL, FONT_SIZE_TICK, save_fig


def _field(data, quantity, ig):
    field, qlabel, _ = _resolve_quantity(data, quantity, None, ig)
    return field, qlabel


def plot_vs_temperature(
    data: CN4Data,
    quantity: str,
    density_idx=None,          # 密度行索引列表; None=全部 (最多 6 条)
    ig: int = 1,               # 不透明度群号 (opac_*/transmission 时有效)
    xlog: bool = True,
    ylog: bool = None,         # None=量纲宽时自动对数
    outfile: str = None,
    title: str = None,
    figsize: tuple = (10.0, 7.5),
) -> str:
    """
    固定密度行, 绘制物理量随温度 T (eV) 的变化曲线。
    多条曲线 = 不同密度的离子数密度 n_i。
    """
    field, qlabel = _field(data, quantity, ig)
    idxs = _pick_indices(data.ndens, density_idx, 6)
    setup_style()
    fig, ax = plt.subplots(figsize=figsize)
    for i in idxs:
        ax.plot(data.temperature, field[i], lw=2.5, marker="o", ms=5,
                label=f"$n_i$ = {data.density[i]:.2e} cm$^{{-3}}$")
    if xlog:
        ax.set_xscale("log")
    if ylog is None:
        ylog = _auto_log(field[idxs])
    if ylog:
        fmin = np.nanmin(field[idxs])
        ax.set_yscale("log")
    ax.set_xlabel(axis_label("T"))
    ax.set_ylabel(qlabel)
    ax.set_title(title or f"{qlabel} vs Temperature of {data.species_label}")
    ax.legend(fontsize=FONT_SIZE_TICK)
    for spine in ax.spines.values():
        spine.set_linewidth(2.0)
    ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    fig.tight_layout()
    return _save(fig, outfile, data, f"{quantity}_vs_T")


def plot_vs_density(
    data: CN4Data,
    quantity: str,
    temp_idx=None,             # 温度列索引列表; None=全部 (最多 6 条)
    ig: int = 1,
    xlog: bool = True,
    ylog: bool = None,
    outfile: str = None,
    title: str = None,
    figsize: tuple = (10.0, 7.5),
) -> str:
    """固定温度列, 绘制物理量随离子数密度 n_i (cm^-3) 的变化曲线"""
    field, qlabel = _field(data, quantity, ig)
    idxs = _pick_indices(data.ntemp, temp_idx, 6)
    setup_style()
    fig, ax = plt.subplots(figsize=figsize)
    for j in idxs:
        ax.plot(data.density, field[:, j], lw=2.5, marker="s", ms=5,
                label=f"$T$ = {data.temperature[j]:.2e} eV")
    if xlog:
        ax.set_xscale("log")
    if ylog is None:
        ylog = _auto_log(field[:, idxs])
    if ylog:
        ax.set_yscale("log")
    ax.set_xlabel(axis_label("nion"))
    ax.set_ylabel(qlabel)
    ax.set_title(title or f"{qlabel} vs Ion Density of {data.species_label}")
    ax.legend(fontsize=FONT_SIZE_TICK)
    for spine in ax.spines.values():
        spine.set_linewidth(2.0)
    ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    fig.tight_layout()
    return _save(fig, outfile, data, f"{quantity}_vs_nion")


def _pick_indices(n_total, idxs, max_n=6):
    """选取曲线索引: 用户指定 -> 全取; 否则均匀取 max_n 条"""
    if idxs is not None:
        return sorted(set(int(i) for i in idxs))
    if n_total <= max_n:
        return list(range(n_total))
    return [round(i * (n_total - 1) / (max_n - 1)) for i in range(max_n)]


def _auto_log(field2d):
    """量纲跨越 >4 个量级时建议对数 y 轴"""
    vmin, vmax = np.nanmin(field2d), np.nanmax(field2d)
    return vmin > 0 and (np.log10(vmax) - np.log10(vmin)) > 4


def _save(fig, outfile, data, tag):
    """保存图像: 默认输出到数据文件同目录 <basename>_<tag>.png"""
    if outfile is None:
        outfile = os.path.join(os.path.dirname(data.filepath),
                               f"{data.basename}_{tag}.png")
    return save_fig(fig, outfile, tag)


if __name__ == "__main__":
    import sys
    from cn4_parser import load_cn4
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    d = load_cn4(sys.argv[1])
    print(plot_vs_temperature(d, "zbar"))
    print(plot_vs_density(d, "opac_rosseland", ig=1))
