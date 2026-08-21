# -*- coding: utf-8 -*-
"""
IONMIX .cn4 结果可视化命令行入口
=================================

功能:
  1. 任意 EOS 物理量彩图 (zbar/dzdt/p_ion/p_ele/e_ion/e_ele/cv_ion/cv_ele/
     nele/rho/dpion_dt/dpele_dt/deion_dn/deele_dn)
  2. 群不透明度彩图: -q opac_rosseland|opac_planck_abs|opac_planck_ems --ig N
  3. 透射率彩图: -q transmission --ig N [-L 长度cm]
  4. 单群大图 (2x2: Rosseland/Planck-abs/Planck-ems/Transmission): -g N
  5. 全部群大图: -A

用法示例:
    python plot_eosop.py -i <file.cn4>                          # zbar vs T, ni
    python plot_eosop.py -i <file.cn4> -q e_ion -o e_ion.png
    python plot_eosop.py -i <file.cn4> -q nele                  # zbar vs T, ne
    python plot_eosop.py -i <file.cn4> -q rho                   # zbar vs T, rho
    python plot_eosop.py -i <file.cn4> -q opac_rosseland --ig 1
    python plot_eosop.py -i <file.cn4> -q transmission -L 0.01 --ig 2
    python plot_eosop.py -i <file.cn4> -g 1                     # 单群大图
    python plot_eosop.py -i <file.cn4> -A                       # 全部群大图

数据需配合原子量 (计算 rho/透射率): --atomwt "12.011,1.008"
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cn4_parser import load_cn4                      # noqa: E402
from plot_utils import plot_heatmap                  # noqa: E402
from plot_heatmaps import (                          # noqa: E402
    axis_label, plot_quantity_heatmap,
    plot_group_opacity_heatmap, plot_opacity_group_figure,
    plot_all_opacity_figures,
)

# 颜色场物理量 -> (图内标签, 是否建议对数色)
QUANTITY_META = {
    "zbar":      ("Average charge state $\\langle Z \\rangle$", False),
    "dzdt":      ("$\\partial \\langle Z \\rangle / \\partial T$ (eV$^{-1}$)", False),
    "p_ion":     ("Ion pressure (J/cm$^3$)", True),
    "p_ele":     ("Electron pressure (J/cm$^3$)", True),
    "dpion_dt":  ("$\\partial P_i / \\partial T$ (J/cm$^3$/eV)", False),
    "dpele_dt":  ("$\\partial P_e / \\partial T$ (J/cm$^3$/eV)", False),
    "e_ion":     ("Ion specific energy (J/g)", True),
    "e_ele":     ("Electron specific energy (J/g)", True),
    "cv_ion":    ("Ion specific heat (J/g/eV)", False),
    "cv_ele":    ("Electron specific heat (J/g/eV)", False),
    "deion_dn":  ("$\\partial e_i / \\partial n_i$", False),
    "deele_dn":  ("$\\partial e_e / \\partial n_e$", False),
    "nele":      ("Average charge state $\\langle Z \\rangle$", False),
    "rho":       ("Average charge state $\\langle Z \\rangle$", False),
}

DEFAULT_CMAP = "cubehelix"


def parse_args():
    p = argparse.ArgumentParser(
        description="Plot 2D heatmap from IONMIX .cn4 output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-i", "--input", required=True, help="input .cn4 file path")
    p.add_argument("-o", "--output", default=None,
                   help="output PNG path (default: <input_dir>/<basename>_<q>.png)")
    p.add_argument("-q", "--quantity", default="zbar",
                   help="physical quantity: EOS量 / opac_rosseland | "
                        "opac_planck_abs | opac_planck_ems | transmission")
    p.add_argument("--ig", type=int, default=1,
                   help="opacity group number (1-based)")
    p.add_argument("-L", "--length", type=float, default=0.01,
                   help="transmission reference length L (cm)")
    p.add_argument("--atomwt", default=None,
                   help="atomic weights, e.g. '12.011,1.008' (for rho/transmission)")
    p.add_argument("-g", "--group-figure", type=int, default=None,
                   help="single group big figure (2x2 subplots) for group N")
    p.add_argument("-A", "--all-groups", action="store_true",
                   help="plot group big figures for all groups")
    p.add_argument("-x", "--x-axis", default="T",
                   choices=["T", "tele", "nion", "nele", "rho"],
                   help="x-axis quantity")
    p.add_argument("-y", "--y-axis", default="nion",
                   choices=["T", "tele", "nion", "nele", "rho"],
                   help="y-axis quantity")
    p.add_argument("--cmap", default=DEFAULT_CMAP,
                   help="matplotlib colormap name (default: cubehelix)")
    p.add_argument("--vmin", type=float, default=None, help="color scale min")
    p.add_argument("--vmax", type=float, default=None, help="color scale max")
    p.add_argument("--zlog", action="store_true", help="log color scale")
    p.add_argument("--no-xlog", action="store_true", help="linear temperature axis")
    p.add_argument("--no-ylog", action="store_true", help="linear y-axis")
    p.add_argument("--dpi", type=int, default=None, help="output DPI (default 450)")
    p.add_argument("--figsize", default="10,7.5",
                   help="figure size in inches, e.g. '10,7.5'")
    return p.parse_args()


def main():
    args = parse_args()

    # ---- 原子量解析 ----
    atomwt = None
    if args.atomwt:
        atomwt = [float(x) for x in args.atomwt.split(",")]

    data = load_cn4(args.input, atomwt=atomwt)

    # ---- 单群大图 ----
    if args.group_figure is not None:
        out = plot_opacity_group_figure(
            data, args.group_figure, outfile=args.output,
            transmission_L=args.length)
        print(f"output : {out}")
        return
    if args.all_groups:
        outdir = args.output if args.output else os.path.join(
            os.path.dirname(os.path.abspath(args.input)), "plots")
        outs = plot_all_opacity_figures(data, outdir=outdir,
                                        transmission_L=args.length)
        for o in outs:
            print(f"output : {o}")
        return

    quantity = args.quantity

    # ---- 群不透明度 / 透射率 ----
    if quantity in ("opac_rosseland", "opac_planck_abs",
                    "opac_planck_ems", "transmission"):
        out = plot_quantity_heatmap(
            data, quantity, x_axis=args.x_axis, y_axis=args.y_axis,
            ig=args.ig, transmission_L=args.length,
            outfile=args.output, cmap=args.cmap,
            vmin=args.vmin, vmax=args.vmax,
            zlog=None if not args.zlog else True,
            xlog=not args.no_xlog, ylog=not args.no_ylog)
        print(f"quantity : {quantity} (group {args.ig}, L={args.length} cm)")
        print(f"output   : {out}")
        return

    # ---- 原有 EOS 物理量彩图 (兼容模式) ----
    out = plot_quantity_heatmap(
        data, quantity, x_axis=args.x_axis, y_axis=args.y_axis,
        outfile=args.output, cmap=args.cmap,
        vmin=args.vmin, vmax=args.vmax,
        zlog=None if not args.zlog else True,
        xlog=not args.no_xlog, ylog=not args.no_ylog)
    print(f"quantity : {quantity}")
    print(f"y-axis   : {axis_label(args.y_axis)}")
    print(f"output   : {out}")


if __name__ == "__main__":
    main()
