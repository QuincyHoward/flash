# -*- coding: utf-8 -*-
"""
eosop_pro - IONMIX .cn4 结果后处理与可视化模块
=============================================

模块分类 (按任务):
    cn4_parser.py        数据解析: .cn4 -> CN4Data 结构化对象
    plot_utils.py        通用 PPT 级绘图风格与 2D 热图基础函数
    plot_heatmaps.py     任务A: rho/nion/nele/tele 为轴的二维彩图
                          + 群不透明度/发射/透射率彩图
    plot_curves.py       任务B: 物理量随 T 或 n_i 的一维变化曲线
    plot_time_series.py  任务C: 物理量随时间演化 (FLASH HDF5 接口)
    fit_relations.py     任务D: 幂律/指数/理想气体/通用函数拟合
    eos_paths.py         任务E: 等温/等压/等熵/冲击雨贡纽研究
    plot_eosop.py        CLI 入口 (任意物理量彩图 + 群不透明度)
    run_ch_opacity_plots.py  CH 材料不透明度全套彩图一键脚本

典型用法:
    from cn4_parser import load_cn4
    from plot_heatmaps import plot_quantity_heatmap, plot_all_opacity_figures

    data = load_cn4('xxx.cn4', atomwt=[12.011, 1.008])
    plot_quantity_heatmap(data, 'zbar', x_axis='T', y_axis='nion',
                          outfile='zbar.png')
    plot_all_opacity_figures(data, outdir='plots/CH')
"""

from cn4_parser import CN4Data, load_cn4, load_cn4_dir                 # noqa: F401
from plot_utils import (                                               # noqa: F401
    plot_heatmap, plot_zbar, setup_style, compute_r2,
    apply_axes_style, save_fig, FONT_SIZE_LABEL, FONT_SIZE_TICK, DPI,
)
from plot_heatmaps import (                                             # noqa: F401
    AXES, axis_label,
    plot_quantity_heatmap, plot_group_opacity_heatmap,
    plot_opacity_group_figure, plot_all_opacity_figures,
)
from plot_curves import plot_vs_temperature, plot_vs_density            # noqa: F401
from plot_time_series import (                                          # noqa: F401
    plot_time_series, plot_center_series, flash_extract,
)
from fit_relations import (                                             # noqa: F401
    fit_power_law, fit_exponential, fit_ideal_gas, fit_generic,
)
from eos_paths import (                                                 # noqa: F401
    trace_isotherm, trace_isobar, compute_entropy,
    trace_isentrope, trace_hugoniot,
)

__all__ = [
    "CN4Data", "load_cn4", "load_cn4_dir",
    "plot_heatmap", "plot_zbar", "setup_style", "compute_r2",
    "apply_axes_style", "save_fig", "FONT_SIZE_LABEL", "FONT_SIZE_TICK", "DPI",
    "AXES", "axis_label",
    "plot_quantity_heatmap", "plot_group_opacity_heatmap",
    "plot_opacity_group_figure", "plot_all_opacity_figures",
    "plot_vs_temperature", "plot_vs_density",
    "plot_time_series", "plot_center_series", "flash_extract",
    "fit_power_law", "fit_exponential", "fit_ideal_gas", "fit_generic",
    "trace_isotherm", "trace_isobar", "compute_entropy",
    "trace_isentrope", "trace_hugoniot",
]

__version__ = "2.0.0"
