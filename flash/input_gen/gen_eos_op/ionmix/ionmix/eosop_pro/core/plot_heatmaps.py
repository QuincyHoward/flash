# -*- coding: utf-8 -*-
"""
IONMIX .cn4 二维彩图绘制模块
============================

任务A: 以 T / tele / nion / nele / rho 为 x/y 轴的二维彩图。
任务A-不透明度: 各能群的 Rosseland / Planck吸收 / Planck发射 / 透射率 彩图。

坐标轴规则:
    T    : 温度 (eV),          1D 网格 (ntemp,)
    tele : 电子温度 (eV),      与 T 相同 (IONMIX 单温假设)
    nion : 离子数密度 (cm^-3), 1D 网格 (ndens,)
    nele : 电子数密度 (cm^-3), 2D 派生量 (ndens, ntemp) -> 作轴时散点插值
    rho  : 质量密度 (g/cm^3),  1D (仅与密度行有关, 与温度无关)

用法示例:
    from cn4_parser import load_cn4
    from plot_heatmaps import plot_quantity_heatmap, plot_all_opacity_figures

    d = load_cn4("Z06_0.50-Z01_0.50.cn4", atomwt=[12.011, 1.008])

    # EOS 物理量彩图: zbar 在 (T, nion) 平面
    plot_quantity_heatmap(d, "zbar", x_axis="T", y_axis="nion",
                          outfile="zbar_T_nion.png")

    # 不透明度彩图: 第 1 群 Rosseland 不透明度
    plot_group_opacity_heatmap(d, "rosseland", ig=1,
                               outfile="rosseland_g1.png")

    # 单群大图: 2x2 子图 (Rosseland / Planck-abs / Planck-ems / Transmission)
    plot_opacity_group_figure(d, ig=1, outfile="opacity_group_1.png")

    # 全部 6 群大图
    plot_all_opacity_figures(d, outdir="plots/CH")
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from cn4_parser import CN4Data
from plot_utils import plot_heatmap, setup_style, FONT_SIZE_LABEL, FONT_SIZE_TICK

# ---------------------------------------------------------------
# 坐标轴定义
# ---------------------------------------------------------------

AXES = {
    "T":    dict(label="Temperature",           unit="eV",
                 short=r"$T$",          fn=lambda d: d.temperature, dim=1),
    "tele": dict(label="Electron Temperature",  unit="eV",
                 short=r"$T_e$",        fn=lambda d: d.temperature, dim=1),
    "nion": dict(label="Ion Number Density",    unit="cm$^{-3}$",
                 short=r"$n_i$",        fn=lambda d: d.density,    dim=1),
    "rho":  dict(label="Mass Density",          unit="g/cm$^3$",
                 short=r"$\rho$",       fn=lambda d: d.rho[:, 0],  dim=1),
    "nele": dict(label="Electron Number Density", unit="cm$^{-3}$",
                 short=r"$n_e$",        fn=lambda d: d.nele,       dim=2),
}


def axis_label(name: str) -> str:
    """生成坐标轴 LaTeX 标签, 如 'Temperature T (eV)'"""
    a = AXES[name]
    return f"{a['label']} {a['short']} ({a['unit']})"


# ---------------------------------------------------------------
# 任意物理量的二维彩图 (支持任意 x/y 轴组合)
# ---------------------------------------------------------------

def plot_quantity_heatmap(
    data: CN4Data,
    quantity: str,
    x_axis: str = "T",
    y_axis: str = "nion",
    outfile: str = None,
    title: str = None,
    cmap: str = "cubehelix",
    zlog: bool = None,           # None=按物理量自动建议
    vmin: float = None,
    vmax: float = None,
    xlog: bool = True,
    ylog: bool = True,
    transmission_L: float = None,  # 仅 quantity='transmission' 时使用 (cm)
    ig: int = 1,                   # 不透明度群号, 仅 quantity 为 opac_*/transmission
    figsize: tuple = (10.0, 7.5),
) -> str:
    """
    绘制任意物理量在 (x_axis, y_axis) 平面上的彩图。

    Args:
        data: CN4Data
        quantity: 物理量名, 见 CN4Data.quantity() 别名表;
                  额外支持 'opac_rosseland'/'opac_planck_abs'/'opac_planck_ems'
                  (需 ig 参数) 与 'transmission' (透射率, 需 transmission_L)。
        x_axis/y_axis: AXES 键名 ('T','tele','nion','nele','rho'), 两者不可相同
        outfile: 输出 PNG 路径; None 时自动 <dir>/<basename>_<q>_<x>-<y>.png
        zlog: 颜色对数色标; None=自动 (量纲宽或建议对数时启用)
        transmission_L: 透射率计算的特征长度 (cm), 默认 0.01 cm
        ig: 不透明度群号, 仅 quantity 以 'opac_' 或 'transmission' 开头时需要
    """
    if x_axis == y_axis:
        raise ValueError(f"x/y 轴不能相同: {x_axis}")

    # ---- 物理量场 (ndens, ntemp) ----
    field, qlabel, qlog_suggest = _resolve_quantity(data, quantity, transmission_L, ig)

    # ---- 坐标轴准备 ----
    xs, ys, field2, hull = _prepare_axes(data, x_axis, y_axis, field)

    if zlog is None:
        zlog = qlog_suggest

    if outfile is None:
        base = data.basename
        outfile = os.path.join(
            os.path.dirname(data.filepath),
            f"{base}_{quantity.replace(' ', '_')}_{x_axis}-{y_axis}.png",
        )
    if title is None:
        title = f"{qlabel} of {data.species_label}"

    return plot_heatmap(
        temperature=xs,
        density=ys,
        field=field2,
        quantity_label=qlabel,
        title=title,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        xlog=xlog,
        ylog=ylog,
        zlog=zlog,
        figsize=figsize,
        outfile=outfile,
        xlabel=axis_label(x_axis),
        ylabel=axis_label(y_axis),
        hull_xy=hull,
    )


def _resolve_quantity(data: CN4Data, quantity: str, transmission_L: float, ig: int):
    """解析物理量名 -> (场 (ndens,ntemp), 色条标签, 是否建议对数色标)"""
    q = quantity.lower()
    if q == "transmission":
        if transmission_L is None:
            transmission_L = 0.01           # 默认 100 um 特征长度
        kappa = data.opac_planck_abs        # (ngrups, ndens, ntemp) cm^2/g
        rho = data.rho                      # (ndens, ntemp) g/cm^3
        field = np.exp(-kappa[ig - 1] * rho * transmission_L)
        return field, "Transmission $e^{-\\kappa \\rho L}$", False

    if q.startswith("opac_"):
        name = q.replace("opac_", "")
        opts = {"rosseland": "Rosseland", "planck_abs": "Planck (absorption)",
                "planck_ems": "Planck (emission)"}
        if name not in opts:
            raise KeyError(f"未知不透明度 '{quantity}'. 可选: "
                           f"{['opac_' + k for k in opts]}, transmission")
        arr = getattr(data, f"opac_{name}")
        if not 1 <= ig <= data.ngrups:
            raise ValueError(f"群号 ig 越界: 1..{data.ngrups}")
        field = arr[ig - 1]
        return field, f"{opts[name]} opacity (cm$^2$/g)", True

    # 声速场: 等熵声速 (cm/s -> um/ns 显示)
    if q == "cs":
        from eos_paths import sound_speed
        field = sound_speed(data) * 1.0e-5      # cm/s -> um/ns
        return field, "Sound speed $c_s$ (um/ns)", True

    # EOS 物理量 (CN4Data.quantity 别名表)
    meta = _QUANTITY_META.get(q)
    if meta is not None:
        label, zlog = meta
        field = data.quantity(q)
        scale = _QUANTITY_SCALE.get(q, 1.0)     # 单位换算 (显示单位)
        if scale != 1.0:
            field = field * scale
        return field, label, zlog
    # 兜底: 让 CN4Data.quantity 抛错
    data.quantity(q)
    raise AssertionError("unreachable")


# EOS 物理量 -> (色条标签, 建议对数)  [数值已按 units.py 换算为显示单位]
_QUANTITY_META = {
    "zbar":      ("Average charge state $\\langle Z \\rangle$", False),
    "dzdt":      ("$\\partial \\langle Z \\rangle / \\partial T$ (eV$^{-1}$)", False),
    "p_ion":     ("Ion pressure (Mbar)", True),
    "p_ele":     ("Electron pressure (Mbar)", True),
    "dpion_dt":  ("$\\partial P_i / \\partial T$ (Mbar/eV)", False),
    "dpele_dt":  ("$\\partial P_e / \\partial T$ (Mbar/eV)", False),
    "e_ion":     ("Ion specific energy (erg/g)", True),
    "e_ele":     ("Electron specific energy (erg/g)", True),
    "cv_ion":    ("Ion specific heat (erg/g/eV)", False),
    "cv_ele":    ("Electron specific heat (erg/g/eV)", False),
    "deion_dn":  ("$\\partial e_i / \\partial n_i$", False),
    "deele_dn":  ("$\\partial e_e / \\partial n_e$", False),
    "nele":      ("Electron number density (cm$^{-3}$)", True),
    "rho":       ("Mass density (g/cm$^3$)", True),
}

# 单位换算因子 (cn4 J/g、J/cm^3 -> 显示单位; 见 units.py)
_QUANTITY_SCALE = {
    "p_ion": 1.0e-5, "p_ele": 1.0e-5,
    "dpion_dt": 1.0e-5, "dpele_dt": 1.0e-5,
    "e_ion": 1.0e7, "e_ele": 1.0e7,
    "cv_ion": 1.0e7, "cv_ele": 1.0e7,
}


def _prepare_axes(data: CN4Data, x_axis: str, y_axis: str, field: np.ndarray):
    """
    构造 (x, y, field_plot, hull) 用于 plot_heatmap。
    约定: plot_heatmap 内部 meshgrid(temperature, density) -> shape (nY, nX);
          因此返回的 field 形状必须为 (nY, nX)。
    规则网格直接返回; 含 nele 轴时在 log 空间散点插值。
    """
    from scipy.interpolate import griddata
    from scipy.spatial import ConvexHull

    ax_dims = {x_axis: AXES[x_axis]["dim"], y_axis: AXES[y_axis]["dim"]}

    # ---- 情况1: 两轴均 1D (T/nion/rho) -> 规则网格 ----
    if all(v == 1 for v in ax_dims.values()):
        x1 = np.asarray(AXES[x_axis]["fn"](data), dtype=float)
        y1 = np.asarray(AXES[y_axis]["fn"](data), dtype=float)
        # cn4 场存储: (行=密度, 列=温度) = (nD, nT)
        # 目标形状: (nY, nX) where nX=len(x_axis), nY=len(y_axis)
        if x_axis in ("T", "tele") and y_axis in ("nion", "rho"):
            return x1, y1, field, None                  # (nD, nT) = (nY, nX) ✓
        if x_axis in ("nion", "rho") and y_axis in ("T", "tele"):
            return x1, y1, field.T, None                # (nT, nD) = (nY, nX) ✓
        raise ValueError(
            f"x/y 轴组合需至少一个为温度轴 (T/tele): got x={x_axis}, y={y_axis}")

    # ---- 情况2: nele 作轴 -> log 空间散点插值 ----
    nele = data.nele                                   # (nD, nT)
    T_grid, NI_grid = np.meshgrid(data.temperature, data.density)

    pts_x = np.log10(T_grid.ravel())
    pts_y = np.log10(nele.ravel())
    pts = np.column_stack([pts_x, pts_y])
    vals = field.ravel()

    nT = data.ntemp
    nE = data.ndens
    T_new = np.logspace(np.log10(data.temperature[0]),
                        np.log10(data.temperature[-1]), nT)
    n_e_min, n_e_max = np.nanmin(nele), np.nanmax(nele)
    nele_new = np.logspace(np.log10(n_e_min), np.log10(n_e_max), nE)

    hull_xy = None
    if len(pts) >= 3:
        hull = ConvexHull(pts)
        hull_xy = np.column_stack([10.0 ** pts[hull.vertices, 0],
                                   10.0 ** pts[hull.vertices, 1]])

    # 目标形状 (nY, nX) = meshgrid(xs, ys) 默认 XY 索引
    # x=T, y=nele:  (nY=nE, nX=nT) -> meshgrid(T, nE) shape (nE, nT)
    #   query 顺序: pts (T_log, nE_log), griddata 需 (X=T_log_query, Y=nE_log_query)
    #   meshgrid(T_log, nE_log) 默认 XY 索引 shape (nE, nT), X[i,j]=T_log[j], Y[i,j]=nE_log[i] ✓
    # x=nele, y=T:  (nY=nT, nX=nE) -> meshgrid(nE, T) shape (nT, nE)
    #   默认 XY 索引: X[i,j]=nE_log[j], Y[i,j]=T_log[i] -> griddata 把 (nE, T) 当查询, 但 pts 是 (T, nE), 错!
    #   修正: 用 indexing='ij' 让 X[i,j]=T_log[i], Y[i,j]=nE_log[j]
    T_log = np.log10(T_new)
    ne_log = np.log10(nele_new)
    if x_axis == "T" or x_axis == "tele":
        Xg, Yg = np.meshgrid(T_log, ne_log)
        Z = griddata(pts, vals, (Xg, Yg), method="linear")    # (nE, nT) ✓
        return T_new, nele_new, Z, hull_xy
    else:  # y_axis == 'T'
        Xg, Yg = np.meshgrid(T_log, ne_log, indexing="ij")
        Z = griddata(pts, vals, (Xg, Yg), method="linear")    # (nT, nE) ✓
        return nele_new, T_new, Z, hull_xy


# ---------------------------------------------------------------
# 群不透明度彩图 (单群单量)
# ---------------------------------------------------------------

OPACITY_NAMES = {
    "rosseland":  ("Rosseland opacity",            "opac_rosseland"),
    "planck_abs": ("Planck absorption opacity",    "opac_planck_abs"),
    "planck_ems": ("Planck emission opacity",      "opac_planck_ems"),
}


def plot_group_opacity_heatmap(
    data: CN4Data,
    opac_name: str,
    ig: int,
    outfile: str = None,
    cmap: str = "cubehelix",
    figsize: tuple = (10.0, 7.5),
) -> str:
    """绘制单群单种不透明度彩图: x=T(eV), y=nion(cm^-3), 颜色=不透明度 (cm^2/g, log)"""
    if opac_name not in OPACITY_NAMES:
        raise KeyError(f"未知不透明度 '{opac_name}'. 可选: {list(OPACITY_NAMES)}")
    label, attr = OPACITY_NAMES[opac_name]
    field = getattr(data, attr)[ig - 1]
    elo, ehi = data.group_bounds[ig - 1], data.group_bounds[ig]
    qlabel = f"{label} (cm$^2$/g)"
    if outfile is None:
        base = data.basename
        outfile = os.path.join(os.path.dirname(data.filepath),
                               f"{base}_{opac_name}_g{ig}.png")
    return plot_heatmap(
        temperature=data.temperature,
        density=data.density,
        field=field,
        quantity_label=qlabel,
        title=f"{label} of {data.species_label}, group {ig} "
              f"({elo:.1e}-{ehi:.1e} eV)",
        cmap=cmap,
        xlog=True, ylog=True, zlog=True,
        figsize=figsize,
        outfile=outfile,
        xlabel=axis_label("T"),
        ylabel=axis_label("nion"),
    )


# ---------------------------------------------------------------
# 单群大图: 2x2 子图 (Rosseland / Planck-abs / Planck-ems / Transmission)
# ---------------------------------------------------------------

def plot_opacity_group_figure(
    data: CN4Data,
    ig: int,
    outfile: str = None,
    transmission_L: float = 0.01,     # 透射率特征长度 (cm)
    cmap: str = "cubehelix",
    figsize: tuple = (18.0, 13.0),
) -> str:
    """
    绘制单个能群的大图: 2x2 子图
        (a) Rosseland opacity      (b) Planck absorption opacity
        (c) Planck emission opacity (d) Transmission exp(-kappa*rho*L)

    每张子图: x = T (eV, log), y = nion (cm^-3, log), 颜色 = 物理量 (log)。
    不透明度单位统一标注 cm^2/g; 透射率无量纲 (0~1)。
    """
    setup_style()
    elo, ehi = data.group_bounds[ig - 1], data.group_bounds[ig]
    title_main = (f"{data.species_label} Group Opacity / Emission / "
                  f"Transmission, group {ig} ({elo:.2e} - {ehi:.2e} eV)")
    sub_titles = [
        "(a) Rosseland opacity",
        "(b) Planck absorption opacity",
        "(c) Planck emission opacity",
        "(d) Transmission  $e^{-\\kappa_{\\rm abs}\\rho L}$, $L$=%.2g cm" % transmission_L,
    ]
    fields = [
        data.opac_rosseland[ig - 1],
        data.opac_planck_abs[ig - 1],
        data.opac_planck_ems[ig - 1],
        np.exp(-data.opac_planck_abs[ig - 1] * data.rho * transmission_L),
    ]
    cb_labels = [
        "Rosseland opacity (cm$^2$/g)",
        "Planck absorption opacity (cm$^2$/g)",
        "Planck emission opacity (cm$^2$/g)",
        "Transmission",
    ]
    cmaps = [cmap, cmap, cmap, "viridis"]
    zlogs = [True, True, True, False]

    X, Y = np.meshgrid(data.temperature, data.density)

    fig, axes = plt.subplots(2, 2, figsize=figsize)
    for ax, field, st, cbl, cm_, zlog in zip(
            axes.ravel(), fields, sub_titles, cb_labels, cmaps, zlogs):
        fmin = np.nanmin(field)
        fmax = np.nanmax(field)
        if zlog:
            # 保护非正值: 用 masked array
            fplot = np.ma.masked_invalid(field)
            pos = fplot > 0
            fplot = np.ma.masked_where(~pos, fplot)
            vmin = 10.0 ** np.floor(np.log10(np.nanmin(fplot)))
            vmax = 10.0 ** np.ceil(np.log10(np.nanmax(fplot)))
            norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
        else:
            fplot = field
            norm = mcolors.Normalize(vmin=fmin, vmax=fmax)
        sm = ax.pcolormesh(X, Y, fplot, cmap=cm_, norm=norm,
                           shading="auto", rasterized=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(axis_label("T"))
        ax.set_ylabel(axis_label("nion"))
        ax.set_title(st, fontsize=FONT_SIZE_LABEL)
        ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
        for spine in ax.spines.values():
            spine.set_linewidth(2.0)
        cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(cbl, fontsize=FONT_SIZE_LABEL)
        cbar.ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
        cbar.outline.set_linewidth(2.0)

    fig.suptitle(title_main, fontsize=26, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    if outfile is None:
        base = data.basename
        outfile = os.path.join(os.path.dirname(data.filepath),
                               f"{base}_group{ig}_all.png")
    outfile = os.path.abspath(outfile)
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    fig.savefig(outfile, dpi=450, bbox_inches="tight")
    plt.close(fig)
    return outfile


def plot_all_opacity_figures(
    data: CN4Data,
    outdir: str = "plots",
    transmission_L: float = 0.01,
) -> list:
    """为所有能群生成单群大图, 返回输出路径列表"""
    os.makedirs(outdir, exist_ok=True)
    outs = []
    base = data.basename
    for ig in range(1, data.ngrups + 1):
        out = os.path.join(outdir, f"{base}_group{ig}_all.png")
        outs.append(plot_opacity_group_figure(
            data, ig, outfile=out, transmission_L=transmission_L))
        print(f"  [ok] group {ig}: {out}")
    return outs


if __name__ == "__main__":
    import sys
    from cn4_parser import load_cn4
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    d = load_cn4(sys.argv[1], atomwt=[12.011, 1.008])
    print(plot_all_opacity_figures(d, outdir=os.path.join(
        os.path.dirname(os.path.abspath(sys.argv[1])), "plots")))
