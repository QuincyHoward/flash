# -*- coding: utf-8 -*-
"""
IONMIX .cn4 结果可视化主脚本
=============================

读取 IONMIX 输出的 .cn4 文件, 绘制二维彩图。
默认绘制平均电离度 zbar 随温度、离子数密度的变化 (双对数坐标, cubehelix 色条)。

支持物理量 (--quantity):
    zbar, dzdt, p_ion, p_ele, dpion_dt, dpele_dt,
    e_ion, e_ele, cv_ion, cv_ele, deion_dn, deele_dn,
    nele (电子数密度), rho (质量密度, 需原子量)

纵轴 (y 轴) 随物理量自动选择:
    - 默认   : 离子数密度 n_i (cm^-3)
    - nele 图: 电子数密度 n_e (cm^-3), 每行取最大电子密度代表该密度行
    - rho 图 : 质量密度 rho (g/cm^3)

用法示例:
    python plot_eosop.py -i <file.cn4>                          # zbar vs T, ni
    python plot_eosop.py -i <file.cn4> -q nele                  # zbar vs T, ne
    python plot_eosop.py -i <file.cn4> -q rho                   # zbar vs T, rho
    python plot_eosop.py -i <file.cn4> -q e_ion -o e_ion.png
    python plot_eosop.py -i <file.cn4> -q p_ion --zlog
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cn4_parser import load_cn4            # noqa: E402
from plot_utils import plot_heatmap        # noqa: E402

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
    # nele / rho 仅用于选择纵轴; 颜色场固定为 zbar
    "nele":      ("Average charge state $\\langle Z \\rangle$", False),
    "rho":       ("Average charge state $\\langle Z \\rangle$", False),
}

DEFAULT_CMAP = "cubehelix"


def _interp_to_nele_grid(data, nT: int = None, nE: int = None):
    """
    将 (T, n_i, zbar) 散点数据插值重采样到规则 (T, n_e) 网格。

    物理: n_e = <Z>(T, n_i) * n_i 是派生量, 数据本质是散点集
          {(T, n_i) -> (n_e, <Z>)}。画 "zbar 随 (T, n_e)" 必须插值。

    散点: X = T  (广播 ndens×ntemp)
          Y = n_e = zbar * n_i   (逐点, 每个 (T,n_i) 唯一对应)
          Z = zbar
    目标: T_t = 原温度网格 (或 logspace 均匀 nT 点)
          n_e_t = logspace(log10(n_e_min), log10(n_e_max), nE)
    插值: scipy.interpolate.griddata(method='linear'), 凸包外 → NaN
    返回: (T_t, n_e_t, Z_interp(ndens_new, ntemp_new), hull_xy(N,2) 原始坐标)
    """
    from scipy.interpolate import griddata
    from scipy.spatial import ConvexHull

    ntemp, ndens = data.ntemp, data.ndens
    if nT is None:
        nT = ntemp
    if nE is None:
        nE = ndens

    nele = data.nele                       # (ndens, ntemp)
    zbar = data.zbar

    # 散点 (log10 空间, 保证插值在幂律区域更准)
    T_grid, NI_grid = np.meshgrid(data.temperature, data.density)
    pts_x = np.log10(T_grid.ravel())
    pts_y = np.log10(nele.ravel())
    pts = np.column_stack([pts_x, pts_y])
    vals = zbar.ravel()

    # 目标规则网格 (log10 空间)
    T_new = np.logspace(np.log10(data.temperature[0]),
                        np.log10(data.temperature[-1]), nT)
    n_e_min = np.nanmin(nele)
    n_e_max = np.nanmax(nele)
    nele_new = np.logspace(np.log10(n_e_min), np.log10(n_e_max), nE)

    Tx, Ny = np.meshgrid(np.log10(T_new), np.log10(nele_new))
    Z_interp = griddata(pts, vals, (Tx, Ny), method="linear")

    # 数据覆盖域凸包 (原始坐标, 用于画虚线框)
    hull_xy = None
    if len(pts) >= 3:
        hull = ConvexHull(pts)
        # 凸包顶点: 转回原始坐标
        hull_xy = np.column_stack([
            10.0 ** pts[hull.vertices, 0],
            10.0 ** pts[hull.vertices, 1],
        ])

    return T_new, nele_new, Z_interp, hull_xy


def parse_args():
    p = argparse.ArgumentParser(
        description="Plot 2D heatmap from IONMIX .cn4 output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-i", "--input", required=True, help="input .cn4 file path")
    p.add_argument("-o", "--output", default=None,
                   help="output PNG path (default: <input_dir>/<basename>_<quantity>.png)")
    p.add_argument("-q", "--quantity", default="zbar",
                   choices=list(QUANTITY_META),
                   help="physical quantity to plot")
    p.add_argument("--cmap", default=DEFAULT_CMAP,
                   help="matplotlib colormap name (default: cubehelix)")
    p.add_argument("--vmin", type=float, default=None, help="color scale min")
    p.add_argument("--vmax", type=float, default=None, help="color scale max")
    p.add_argument("--zlog", action="store_true", help="log color scale for quantity")
    p.add_argument("--no-xlog", action="store_true", help="linear temperature axis")
    p.add_argument("--no-ylog", action="store_true", help="linear y-axis")
    p.add_argument("--dpi", type=int, default=None, help="output DPI (default 450)")
    p.add_argument("--figsize", default="10,7.5",
                   help="figure size in inches, e.g. '10,7.5'")
    return p.parse_args()


def main():
    args = parse_args()

    data = load_cn4(args.input)

    quantity = args.quantity
    qlabel, qlog_suggest = QUANTITY_META[quantity]

    # nele: 颜色场=zbar, 且 (T, n_e) 平面需散点插值重采样 (n_e 是派生量)
    if quantity == "nele":
        xdata, ydata, field, hull_xy = _interp_to_nele_grid(data)
        ylabel = r"Electron Number Density $n_e$ ($\mathrm{cm^{-3}}$)"
        field_orig_min = float(np.nanmin(field)) if field.size else float("nan")
        field_orig_max = float(np.nanmax(field)) if field.size else float("nan")
    elif quantity == "rho":
        # rho 与温度无关, (T, rho) 天然规则网格, 无需插值
        xdata = data.temperature
        ydata = data.rho[:, 0]
        field = data.zbar
        hull_xy = None
        ylabel = r"Mass Density $\rho$ ($\mathrm{g\,cm^{-3}}$)"
    else:
        xdata = data.temperature
        ydata = data.density
        field = data.quantity(quantity)
        hull_xy = None
        ylabel = r"Ion Number Density $n_i$ ($\mathrm{cm^{-3}}$)"

    zlog = args.zlog or qlog_suggest

    figsize = tuple(float(x) for x in args.figsize.split(","))

    # 默认输出路径: 与输入同目录, 文件名 <basename>_<quantity>.png
    if args.output is None:
        base = os.path.splitext(data.basename)[0]
        outfile = os.path.join(
            os.path.dirname(os.path.abspath(args.input)),
            f"{base}_{quantity}.png",
        )
    else:
        outfile = args.output

    if args.dpi is not None:
        import matplotlib
        matplotlib.use("Agg")
        import plot_utils
        plot_utils.DPI = args.dpi

    out = plot_heatmap(
        temperature=xdata,
        density=ydata,
        field=field,
        quantity_label=qlabel,
        title=f"{qlabel} of {data.species_label}",
        cmap=args.cmap,
        vmin=args.vmin,
        vmax=args.vmax,
        xlog=not args.no_xlog,
        ylog=not args.no_ylog,
        zlog=zlog,
        figsize=figsize,
        outfile=outfile,
        ylabel=ylabel,
        hull_xy=hull_xy,
    )
    print(f"quantity : {quantity}")
    print(f"y-axis   : {ylabel}")
    print(f"y range  : {ydata.min():.4e} ~ {ydata.max():.4e}")
    if quantity == "nele":
        print(f"range    : {field_orig_min:.4e} ~ {field_orig_max:.4e}"
              f" (zbar, interpolated, NaN masked)")
    else:
        print(f"range    : {field.min():.4e} ~ {field.max():.4e}"
              f" ({'log' if zlog else 'linear'} color scale)")
    print(f"output   : {out}")


if __name__ == "__main__":
    main()
