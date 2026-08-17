# -*- coding: utf-8 -*-
"""
eosop_pro - IONMIX .cn4 结果后处理模块
=====================================

提供:
- cn4_parser.py : .cn4 数据文件解析, 输出结构化 CN4Data 对象
- plot_utils.py : 通用 PPT 级 2D 彩图绘制工具
- plot_eosop.py : 命令行入口, 支持任意物理量的可视化

典型用法:
    from cn4_parser import load_cn4
    from plot_utils import plot_heatmap
    data = load_cn4('xxx.cn4')
    plot_heatmap(data.temperature, data.density, data.zbar,
                 quantity_label='Average charge state',
                 title='zbar of CH mixture',
                 outfile='zbar.png')
"""

from cn4_parser import CN4Data, load_cn4, load_cn4_dir     # noqa: F401
from plot_utils import plot_heatmap, plot_zbar             # noqa: F401

__all__ = [
    "CN4Data",
    "load_cn4",
    "load_cn4_dir",
    "plot_heatmap",
    "plot_zbar",
]

__version__ = "1.0.0"