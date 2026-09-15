# -*- coding: utf-8 -*-
"""cn4 数据可视化 —— 二维彩图与一维变化曲线（PPT 演讲级、全英文）。

本模块把参考实现 ``ionmix/ionmix/eosop_pro/core/`` 下的
``plot_utils.py`` + ``plot_heatmaps.py`` + ``plot_curves.py`` 三份脚本
**整体并入** ``eosop_pro``，并改造为包内相对导入、复用 :mod:`..config`
与 :mod:`..plotting.style` 的单一来源常量。

能力分区
--------
**任务 A —— 二维彩图** (:func:`plot_quantity_heatmap`)
    以 ``T`` / ``tele`` / ``n_ion`` / ``n_ele`` / ``rho`` 任意组合为 x/y 轴，
    颜色为任意 EOS 物理量、群不透明度或透射率。

**任务 A′ —— 群不透明度大图** (:func:`plot_opacity_group_figure`)
    单个能群的 2x2 大图: Rosseland / Planck 吸收 / Planck 发射 / 透射率。

**任务 B —— 一维曲线** (:func:`plot_vs_temperature` / :func:`plot_vs_density`)
    固定一个变量扫描另一个变量，多条曲线对比。

坐标轴约定
----------
============  ====================  ==========================
轴名          物理量                 网格维度
============  ====================  ==========================
``T``        温度 (eV)              1D ``(ntemp,)``
``tele``     电子温度 (eV)          1D（IONMIX 单温假设，同 ``T``）
``nion``     离子数密度 (cm^-3)      1D ``(ndens,)``
``nele``     电子数密度 (cm^-3)      2D 派生量 -> 作轴时散点插值 + 凸包
``rho``      质量密度 (g/cm^3)       1D（与温度无关）
============  ====================  ==========================

单位纪律
--------
**内部一律 cn4 原始单位**（J/cm^3、J/g、cm^-3、eV），仅在**出图/返回值**
处经 :mod:`.units` 换算到显示单位（Mbar、erg/g、um/ns）。换算因子全部
来自 :mod:`.units`，本模块不新增硬编码常数。

多文件批处理
------------
:func:`plot_cn4_directory` 与 :func:`plot_all_opacity_figures` 面向
**目录级批处理**：逐文件独立出图、每图落盘后立即 ``close`` 释放内存、
单文件失败不中断整批（记录到返回报告的 ``errors``），适配
``eosop_pro`` 的多文件流水线（见 :mod:`..batch`）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from .. import config
from .cn4_io import CN4ParseError, CN4Table
from .units import pressure_mbar, energy_ergg, velocity_umns

__all__ = [
    "AXES", "axis_label", "display_scale",
    "plot_quantity_heatmap", "plot_group_opacity_heatmap",
    "plot_opacity_group_figure", "plot_all_opacity_figures",
    "plot_all_quantities_dual_axes", "DUAL_Y_AXES", "Y_AXIS_SUFFIX",
    "plot_vs_temperature", "plot_vs_density",
    "plot_cn4_directory", "SUPPORTED_QUANTITIES",
]


# ================================================================
# 坐标轴定义与显示单位换算
# ================================================================

#: 五个可选坐标轴。``fn`` 取 1D 轴数组（``nele`` 特殊，见 ``_prepare_axes``）。
AXES: dict[str, dict] = {
    "T": dict(label="Temperature", unit="eV", short=r"$T$", dim=1),
    "tele": dict(label="Electron temperature", unit="eV", short=r"$T_e$", dim=1),
    "nion": dict(label="Ion number density", unit="cm$^{-3}$",
                 short=r"$n_i$", dim=1),
    "nele": dict(label="Electron number density", unit="cm$^{-3}$",
                 short=r"$n_e$", dim=2),
    "rho": dict(label="Mass density", unit="g/cm$^3$", short=r"$\rho$", dim=1),
}

#: EOS 物理量 -> (色条标签, 是否建议对数色标)。
#: ⚠️ 标签中的单位 = **显示单位**（数值由 :func:`display_scale` 换算）。
_QUANTITY_META: dict[str, tuple[str, bool]] = {
    "zbar":     (r"Average charge state $\langle Z \rangle$", False),
    "dzdt":     (r"$\partial \langle Z \rangle/\partial T$ (eV$^{-1}$)", False),
    "p_ion":    ("Ion pressure (Mbar)", True),
    "p_ele":    ("Electron pressure (Mbar)", True),
    "dpion_dt": (r"$\partial P_i/\partial T$ (Mbar/eV)", False),
    "dpele_dt": (r"$\partial P_e/\partial T$ (Mbar/eV)", False),
    "e_ion":    ("Ion specific energy (erg/g)", True),
    "e_ele":    ("Electron specific energy (erg/g)", True),
    "cv_ion":   ("Ion specific heat (erg/g/eV)", False),
    "cv_ele":   ("Electron specific heat (erg/g/eV)", False),
    "deion_dn": (r"$\partial e_i/\partial n_i$ (unit unknown)", False),
    "deele_dn": (r"$\partial e_e/\partial n_e$ (unit unknown)", False),
    "nele":     ("Electron number density (cm$^{-3}$)", True),
    "rho":      ("Mass density (g/cm$^3$)", True),
}

#: 物理量 -> cn4 原始单位 -> 显示单位的乘因子（缺省 1.0 表示不变）。
#: 每个因子的推导链见 :mod:`.units`；**不在此重复硬编码常数**。
_QUANTITY_SCALE: dict[str, float] = {}

#: 群不透明度名 -> (标签, ``CN4Table`` 属性名)。
OPACITY_NAMES: dict[str, tuple[str, str]] = {
    "rosseland":  ("Rosseland opacity", "opac_rosseland"),
    "planck_abs": ("Planck absorption opacity", "opac_planck_abs"),
    "planck_ems": ("Planck emission opacity", "opac_planck_ems"),
}

#: 允许作为 ``quantity`` 传入的全部名字（供 CLI 的 choices 与文档使用）。
SUPPORTED_QUANTITIES: tuple[str, ...] = tuple(
    sorted(set(_QUANTITY_META) | {
        "opac_rosseland", "opac_planck_abs", "opac_planck_ems",
        "transmission", "cs", "dzdt",
    })
)


def axis_label(name: str) -> str:
    """生成坐标轴标签，例如 ``'Temperature $T$ (eV)'``。"""
    if name not in AXES:
        raise KeyError(f"未知坐标轴 '{name}'，可选: {sorted(AXES)}")
    a = AXES[name]
    return f"{a['label']} {a['short']} ({a['unit']})"


def display_scale(quantity: str) -> float:
    """返回物理量 ``quantity`` 的 **cn4 原始单位 -> 显示单位** 乘因子。

    因子来自 :mod:`.units`；未声明显式换算的量返回 ``1.0``。
    """
    q = quantity.lower()
    if q in ("p_ion", "p_ele", "dpion_dt", "dpele_dt"):
        from .units import P_JCM3_TO_MBAR
        return P_JCM3_TO_MBAR
    if q in ("e_ion", "e_ele"):
        from .units import E_JG_TO_ERG_G
        return E_JG_TO_ERG_G
    if q in ("cv_ion", "cv_ele"):
        from .units import CV_TO_ERG_G_EV
        return CV_TO_ERG_G_EV
    return 1.0


def _axis_values(tbl: CN4Table, name: str) -> np.ndarray:
    """取某坐标轴的一维值数组（1D 轴专用；``nele`` / ``rho`` 见注释）。"""
    if name in ("T", "tele"):
        return np.asarray(tbl.temperature, dtype=float)
    if name == "nion":
        return np.asarray(tbl.density, dtype=float)
    if name == "rho":
        # rho 与温度无关，逐密度点唯一 -> 取任一温度列即可
        return np.asarray(tbl.rho_flat(), dtype=float).reshape(
            tbl.ndens, tbl.ntemp)[:, 0]
    raise KeyError(f"'{name}' 不是一维坐标轴")


def _arr2d(tbl: CN4Table, name: str, ig: int = 1) -> np.ndarray:
    """取物理量为 ``(ndens, ntemp)`` numpy 数组；支持 1-based 群不透明度。"""
    low = name.lower()
    if low in ("opac_rosseland", "opac_planck_abs", "opac_planck_ems"):
        flat = tbl.group_opacity(low.replace("opac_", ""), ig)
    else:
        flat = tbl.quantity(low)
    return np.asarray(flat, dtype=float).reshape(tbl.ndens, tbl.ntemp)


# ================================================================
# 通用绘图原语
# ================================================================

def _plt():
    """惰性应用全局样式并返回 ``matplotlib.pyplot``。"""
    from ..plotting.style import apply_style
    return apply_style()


def _save(fig, outfile: str | os.PathLike, tag: str = "fig") -> str:
    """落盘并关闭 figure。

    ★ 批量出图时**必须**关闭，否则 pyplot 会累积 figure 句柄
    （实测 60 张即触发 ``More than 20 figures have been opened``）。
    文本 ASCII 由 :func:`..plotting.style.assert_ascii` 在存盘前校验。
    """
    from ..plotting.style import assert_ascii
    from pathlib import Path as _P
    outfile = str(outfile)
    _P(outfile).parent.mkdir(parents=True, exist_ok=True)
    assert_ascii(fig)
    fig.savefig(outfile, dpi=config.PLOT_DPI, bbox_inches="tight")
    _plt().close(fig)
    return outfile


def _style_axes(ax, tick_size: int | None = None, spine_lw: float = 1.5) -> None:
    """统一坐标轴视觉：内向刻度、四边框、加粗线宽（PPT 级）。"""
    ax.tick_params(which="both", direction="in", top=True, right=True,
                   labelsize=tick_size or config.PLOT_TICK_FONTSIZE,
                   width=spine_lw, length=6)
    for s in ax.spines.values():
        s.set_linewidth(spine_lw)


def _colorbar(fig, mappable, ax, label: str):
    """加一个统一风格的 colorbar。"""
    cb = fig.colorbar(mappable, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label(label, fontsize=config.PLOT_LABEL_FONTSIZE)
    cb.ax.tick_params(labelsize=config.PLOT_TICK_FONTSIZE,
                      width=1.5, length=6)
    cb.outline.set_linewidth(1.5)
    return cb


# ================================================================
# 任务 A —— 二维彩图
# ================================================================

def plot_quantity_heatmap(
    tbl: CN4Table,
    quantity: str = "zbar",
    x_axis: str = "T",
    y_axis: str = "nion",
    *,
    outfile: str | None = None,
    title: str | None = None,
    cmap: str = "cubehelix",
    zlog: bool | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    xlog: bool = True,
    ylog: bool = True,
    transmission_L: float | None = None,
    ig: int = 1,
    figsize: tuple[float, float] = (10.0, 7.5),
) -> str:
    """绘制任意物理量在 ``(x_axis, y_axis)`` 平面上的二维彩图。

    Args:
        tbl: :class:`CN4Table`
        quantity: 物理量名。三类均可：
            * EOS 量（``zbar``/``p_ion``/``e_ele``/``cv_ion``/``nele``/``rho`` …）
            * 群不透明度（``opac_rosseland``/``opac_planck_abs``/``opac_planck_ems``，需 ``ig``）
            * ``transmission``（透射率，需 ``transmission_L``）或 ``cs``（等熵声速）
        x_axis / y_axis: :data:`AXES` 键名，两者不可相同
        outfile: 输出路径；``None`` 时写到 ``<cn4 同目录>/<basename>_<q>_<x>-<y>.png``
        zlog: 颜色对数色标；``None`` = 按物理量自动判定
        transmission_L: 透射率特征长度 (cm)，默认 0.01
        ig: 不透明度群号（**1-based**）

    Returns:
        输出文件路径
    """
    if x_axis == y_axis:
        raise ValueError(f"x/y 轴不能相同: {x_axis!r}")
    if x_axis not in AXES or y_axis not in AXES:
        raise KeyError(f"未知坐标轴；可选 {sorted(AXES)}")

    field, qlabel, zlog_suggest = _resolve_quantity(tbl, quantity, transmission_L, ig)
    xs, ys, field2, hull = _prepare_axes(tbl, x_axis, y_axis, field)

    if zlog is None:
        zlog = zlog_suggest

    if outfile is None:
        d = os.path.dirname(os.path.abspath(tbl.filepath))
        outfile = os.path.join(
            d, f"{tbl.basename}_{quantity}_{x_axis}-{y_axis}.png")
    if title is None:
        title = f"{qlabel} of {tbl.species_label}"

    return _plot_heatmap(
        x=xs, y=ys, field=field2, quantity_label=qlabel, title=title,
        xlabel=axis_label(x_axis), ylabel=axis_label(y_axis),
        cmap=cmap, vmin=vmin, vmax=vmax, xlog=xlog, ylog=ylog, zlog=zlog,
        figsize=figsize, outfile=outfile, hull_xy=hull,
    )


def _resolve_quantity(tbl: CN4Table, quantity: str,
                      transmission_L: float | None, ig: int):
    """解析物理量名 -> ``(二维场 (ndens,ntemp), 色条标签, 建议对数色标)``。

    ⚠️ 返回场的数值**已换算为显示单位**（标签所述单位）。
    """
    q = quantity.lower()

    # ---- 透射率：exp(-kappa_abs * rho * L)，无量纲 ----
    if q == "transmission":
        L = 0.01 if transmission_L is None else float(transmission_L)
        kappa = _arr2d(tbl, "opac_planck_abs", ig)      # cm^2/g
        rho = _arr2d(tbl, "rho")                        # g/cm^3
        return np.exp(-kappa * rho * L), (
            f"Transmission (L={L:g} cm)"), False

    # ---- 群不透明度 ----
    if q.startswith("opac_"):
        name = q[len("opac_"):]
        if name not in OPACITY_NAMES:
            raise KeyError(
                f"未知不透明度 {quantity!r}；可选 "
                f"{['opac_' + k for k in OPACITY_NAMES]}、transmission")
        label = OPACITY_NAMES[name][0]
        return _arr2d(tbl, q, ig), f"{label} (cm$^2$/g)", True

    # ---- 等熵声速：cm/s -> um/ns ----
    if q == "cs":
        from .cn4_paths import sound_speed
        return velocity_umns(sound_speed(tbl)), (
            r"Sound speed $c_s$ (um/ns)"), True

    # ---- 压力/内能与组合量：走显示单位换算 ----
    if q in ("p_ion", "p_ele", "e_ion", "e_ele", "dpion_dt", "dpele_dt",
             "cv_ion", "cv_ele"):
        meta = _QUANTITY_META[q]
        return _arr2d(tbl, q) * display_scale(q), meta[0], meta[1]

    # ---- 其余 EOS 物理量（zbar/dzdt/deion_dn/deele_dn/nele/rho） ----
    if q in _QUANTITY_META:
        meta = _QUANTITY_META[q]
        return _arr2d(tbl, q), meta[0], meta[1]

    # 兜底：交给 CN4Table 抛 KeyError（信息更准确）
    try:
        tbl.quantity(q)
    except Exception as exc:            # noqa: BLE001 - 转成统一错误类型
        raise CN4ParseError(
            f"未知物理量 {quantity!r}；可选 "
            f"{list(SUPPORTED_QUANTITIES)}") from exc
    raise CN4ParseError(f"未知物理量 {quantity!r}")


def _prepare_axes(tbl: CN4Table, x_axis: str, y_axis: str, field: np.ndarray):
    """构造 ``(xs, ys, field_plot, hull)``。

    约定：目标 ``field_plot`` 形状必须为 ``(nY, nX)`` —— 与
    ``meshgrid(xs, ys)`` 的默认 ``'xy'`` 索引一致（行 = y，列 = x）。

    两种情况：
      1. 两轴均 1D（``T``/``tele``/``nion``/``rho``）-> 规则网格，必要时转置
      2. 含 ``nele`` 轴 -> 该轴本质是 2D 派生量，做 ``log`` 空间散点插值，
         并返回凸包顶点用于绘制数据边界虚线
    """
    dims = {x_axis: AXES[x_axis]["dim"], y_axis: AXES[y_axis]["dim"]}

    # ---- 情况 1：规则网格 ----
    if all(v == 1 for v in dims.values()):
        x1 = _axis_values(tbl, x_axis)
        y1 = _axis_values(tbl, y_axis)
        x_is_T = x_axis in ("T", "tele")
        y_is_T = y_axis in ("T", "tele")
        if x_is_T and not y_is_T:
            # cn4 场存储 (ndens, ntemp) = (n_y, n_x) -> 已匹配
            return x1, y1, field, None
        if y_is_T and not x_is_T:
            # 需转置成 (ntemp, ndens) = (n_y, n_x)
            return x1, y1, field.T, None
        raise ValueError(
            f"两轴需至少一个为温度轴 (T/tele)：got x={x_axis}, y={y_axis}")

    # ---- 情况 2：含 nele（2D 派生量） -> log 空间散点插值 ----
    from scipy.interpolate import griddata
    from scipy.spatial import ConvexHull

    nele = np.asarray(tbl.nele_flat(), dtype=float).reshape(tbl.ndens, tbl.ntemp)
    T_grid, NI_grid = np.meshgrid(_axis_values(tbl, "T"), _axis_values(tbl, "nion"))
    vals = field.ravel()

    # 仅保留有限且**正值** n_e 的点（NaN 会破坏 griddata / ConvexHull；
    # zbar -> 0 的中性区 n_e = 0 无法进对数插值，按"数据边界外"处理而非整图报错）
    ne_r, T_r = nele.ravel(), T_grid.ravel()
    ok = np.isfinite(ne_r) & (ne_r > 0) & np.isfinite(T_r) & np.isfinite(vals)
    if ok.sum() < 3:
        raise CN4ParseError("有效数据点不足 3 个，无法在 (T, n_e) 平面插值")
    pts = np.column_stack([np.log10(T_r[ok]), np.log10(ne_r[ok])])
    vals = vals[ok]

    nT, nE = tbl.ntemp, tbl.ndens
    T_new = np.logspace(np.log10(np.nanmin(T_grid)), np.log10(np.nanmax(T_grid)), nT)
    ne_pos = nele[nele > 0]
    if ne_pos.size == 0:
        raise CN4ParseError("n_e 无正值，无法对数插值")
    ne_min, ne_max = float(ne_pos.min()), float(ne_pos.max())
    ne_new = np.logspace(np.log10(ne_min), np.log10(ne_max), nE)

    hull_xy = None
    if len(pts) >= 3:
        hull = ConvexHull(pts)
        hull_xy = np.column_stack([10.0 ** pts[hull.vertices, 0],
                                   10.0 ** pts[hull.vertices, 1]])

    T_log, ne_log = np.log10(T_new), np.log10(ne_new)
    if x_axis in ("T", "tele"):
        # 目标 (nY=nE, nX=nT) -> meshgrid(T, ne) 默认 'xy' 索引
        Xg, Yg = np.meshgrid(T_log, ne_log)
        return T_new, ne_new, griddata(pts, vals, (Xg, Yg), method="linear"), hull_xy
    # y_axis == 'T' -> 目标 (nY=nT, nX=nE)
    # meshgrid 需 'ij' 索引才能让 X[i,j]=T_log[i] 匹配 pts 的 (T, ne) 顺序
    Xg, Yg = np.meshgrid(T_log, ne_log, indexing="ij")
    return ne_new, T_new, griddata(pts, vals, (Xg, Yg), method="linear"), hull_xy


def _plot_heatmap(*, x, y, field, quantity_label, title, xlabel, ylabel,
                  cmap="cubehelix", vmin=None, vmax=None,
                  xlog=True, ylog=True, zlog=False,
                  figsize=(10.0, 7.5), outfile=None, hull_xy=None,
                  nan_color="white") -> str:
    """二维彩图底层原语 —— **已上提至 :mod:`..plotting.gridmap`**（统一绘图模块）。

    本函数保留为**向后兼容的薄委托**：:mod:`.cn4_paths` 与既有测试仍按
    此签名调用；实际绘制与样式全部由
    :func:`..plotting.gridmap.plot_heatmap` 承担（任意 eosop 族共用）。
    """
    from ..plotting.gridmap import plot_heatmap
    return plot_heatmap(
        x=x, y=y, field=field,
        xlabel=xlabel, ylabel=ylabel, clabel=quantity_label, title=title,
        outfile=outfile, cmap=cmap, vmin=vmin, vmax=vmax,
        xlog=xlog, ylog=ylog, zlog=zlog, figsize=figsize,
        hull_xy=hull_xy, nan_color=nan_color,
        error_cls=CN4ParseError,
    )


# ----------------------------------------------------------------
# 任务 A′ —— 群不透明度专题
# ----------------------------------------------------------------

def plot_group_opacity_heatmap(
    tbl: CN4Table, opac_name: str = "rosseland", ig: int = 1, *,
    outfile: str | None = None, cmap: str = "cubehelix",
    figsize: tuple[float, float] = (10.0, 7.5),
) -> str:
    """单群单种不透明度彩图：x=T (eV)，y=n_ion (cm^-3)，色=不透明度 (cm^2/g, log)。"""
    return plot_quantity_heatmap(
        tbl, f"opac_{opac_name}", x_axis="T", y_axis="nion",
        ig=ig, outfile=outfile, cmap=cmap, zlog=True, figsize=figsize)


def plot_opacity_group_figure(
    tbl: CN4Table, ig: int, *,
    outfile: str | None = None,
    transmission_L: float = 0.01,
    cmap: str = "cubehelix",
    figsize: tuple[float, float] = (18.0, 13.0),
    y_axis: str = "nion",
) -> str:
    """单个能群的 2x2 大图。

    子图：(a) Rosseland　(b) Planck 吸收　(c) Planck 发射　(d) 透射率。
    每张子图 x=T (eV, log)，y 由 ``y_axis`` 指定（``nion``/``rho``/``nele``，
    log）；不透明度单位 cm^2/g，透射率无量纲 0~1。

    ``y_axis`` 支持用户 2026-09-15 规约的 ne-T / rho-T 双坐标出图：
    同一能群可分别以 n_ion-T（默认，向后兼容）、rho-T、n_e-T 三种平面绘制。
    """
    import matplotlib.colors as mcolors

    if y_axis not in ("nion", "rho", "nele"):
        raise KeyError(f"未知 y 轴 {y_axis!r}；可选 nion/rho/nele")
    if not 1 <= ig <= tbl.ngrups:
        raise CN4ParseError(f"群号 ig={ig} 越界 (1..{tbl.ngrups})")
    plt = _plt()

    lo, hi = float(tbl.group_bounds[ig - 1]), float(tbl.group_bounds[ig])
    rho = _arr2d(tbl, "rho")
    kap_abs = _arr2d(tbl, "opac_planck_abs", ig)

    panels = [
        ("(a) Rosseland opacity", _arr2d(tbl, "opac_rosseland", ig),
         "Rosseland opacity (cm$^2$/g)", cmap, True),
        ("(b) Planck absorption opacity", kap_abs,
         "Planck absorption opacity (cm$^2$/g)", cmap, True),
        ("(c) Planck emission opacity", _arr2d(tbl, "opac_planck_ems", ig),
         "Planck emission opacity (cm$^2$/g)", cmap, True),
        (f"(d) Transmission  $e^{{-\\kappa_{{abs}}\\rho L}}$, $L$={transmission_L:g} cm",
         np.exp(-kap_abs * rho * transmission_L), "Transmission", "viridis", False),
    ]

    # y 轴三选一：nion / rho（1D 规则网格）或 nele（2D 逐点派生轴）
    if y_axis == "nele":
        X = np.tile(np.asarray(_axis_values(tbl, "T"), dtype=float),
                    (tbl.ndens, 1))
        Y = np.asarray(tbl.nele_flat(), dtype=float).reshape(
            tbl.ndens, tbl.ntemp)
    else:
        X, Y = np.meshgrid(_axis_values(tbl, "T"),
                           _axis_values(tbl, y_axis))
    fig, axes = plt.subplots(2, 2, figsize=figsize)

    for ax, (sub_title, field, cbl, cm_, use_log) in zip(axes.ravel(), panels):
        fplot = np.ma.masked_invalid(field)
        if use_log:
            fplot = np.ma.masked_where(fplot <= 0, fplot)
            norm = mcolors.LogNorm(
                vmin=10.0 ** np.floor(np.log10(float(fplot.min()))),
                vmax=10.0 ** np.ceil(np.log10(float(fplot.max()))))
        else:
            norm = mcolors.Normalize(vmin=float(fplot.min()),
                                     vmax=float(fplot.max()))
        cm = plt.get_cmap(cm_).copy()
        cm.set_bad("white")
        mesh = ax.pcolormesh(X, Y, fplot, cmap=cm, norm=norm,
                             shading="auto", rasterized=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(axis_label("T"))
        ax.set_ylabel(axis_label(y_axis))
        ax.set_title(sub_title, fontsize=config.PLOT_LABEL_FONTSIZE)
        _style_axes(ax, tick_size=config.PLOT_TICK_FONTSIZE, spine_lw=2.0)
        _colorbar(fig, mesh, ax, cbl)

    fig.suptitle(
        f"{tbl.species_label} group {ig} ({lo:.2e} - {hi:.2e} eV)",
        fontsize=config.PLOT_TITLE_FONTSIZE, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.965))

    if outfile is None:
        d = os.path.dirname(os.path.abspath(tbl.filepath))
        outfile = os.path.join(d, f"{tbl.basename}_group{ig}_all.png")
    return _save(fig, outfile, tag=f"group{ig}")


#: y 轴 -> 文件名后缀（``nion`` 保持历史 ``_all`` 命名以向后兼容）。
Y_AXIS_SUFFIX: dict[str, str] = {
    "nion": "_all", "nele": "_ne-T", "rho": "_rho-T",
}


def plot_all_opacity_figures(
    tbl: CN4Table, *, outdir: str | os.PathLike = "plots",
    transmission_L: float = 0.01, igs: Sequence[int] | None = None,
    y_axes: Sequence[str] = ("nion",), verbose: bool = True,
) -> list[str]:
    """为全部（或指定）能群生成单群 2x2 大图，返回输出路径列表。

    ``y_axes`` 支持同一能群多坐标出图（用户 2026-09-15 规约）：
    传 ``("nele", "rho")`` 即可得 ``_ne-T`` / ``_rho-T`` 两个变体；
    默认 ``("nion",)`` 维持历史 ``_groupN_all.png`` 文件名。
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    bad = [y for y in y_axes if y not in Y_AXIS_SUFFIX]
    if bad:
        raise KeyError(f"未知 y 轴 {bad}；可选 {sorted(Y_AXIS_SUFFIX)}")
    ig_list = list(igs) if igs else list(range(1, tbl.ngrups + 1))
    outs: list[str] = []
    for ya in y_axes:
        for ig in ig_list:
            if not 1 <= ig <= tbl.ngrups:
                continue
            out = outdir / f"{tbl.basename}_group{ig}{Y_AXIS_SUFFIX[ya]}.png"
            outs.append(plot_opacity_group_figure(
                tbl, ig, outfile=str(out), transmission_L=transmission_L,
                y_axis=ya))
            if verbose:
                print(f"  [ok] group {ig} ({ya}-T) -> {out}")
    return outs


#: step01 双坐标规约（用户 2026-09-15）：每种彩图同时以这两种 y 轴出图。
DUAL_Y_AXES: tuple[str, ...] = ("nele", "rho")


def plot_all_quantities_dual_axes(
    tbl: CN4Table, *, outdir: str | os.PathLike = "dual_plots",
    y_axes: Sequence[str] = DUAL_Y_AXES,
    quantities: Sequence[str] | None = None,
    ig: int = 1, transmission_L: float = 0.01,
    verbose: bool = True,
) -> dict:
    """step01 规约总入口：**每种彩图同时以 ne-T 与 rho-T 两种坐标绘制**。

    默认 ``quantities`` = 12 个 EOS 二维场 + 3 类群不透明度（``ig=1``），
    共 15 量 × 2 坐标 = **30 张**；派生量（``cs``/``transmission``）不默认
    参与。文件名沿用既有约定：``<basename>_<q>_T-nele.png`` /
    ``<basename>_<q>_T-rho.png``。

    单量失败（如某场无有效正值）只记入 ``errors``，不中断整批。

    Returns:
        ``{"plots": [路径], "errors": [(量, 轴, 消息)], "n_plots"}``
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if quantities is None:
        from .cn4_io import BLOCK_SPEC, OPACITY_SPEC
        quantities = ([a for a, _l, _u, _s in BLOCK_SPEC]
                      + [a for a, _l, _u, _s in OPACITY_SPEC])
    bad = [y for y in y_axes if y not in Y_AXIS_SUFFIX]
    if bad:
        raise KeyError(f"未知 y 轴 {bad}；可选 {sorted(Y_AXIS_SUFFIX)}")

    plots: list[str] = []
    errors: list[tuple[str, str, str]] = []
    for q in quantities:
        for ya in y_axes:
            out = outdir / f"{tbl.basename}_{q}_T-{ya}.png"
            try:
                plots.append(plot_quantity_heatmap(
                    tbl, q, "T", ya, ig=ig,
                    transmission_L=transmission_L,
                    outfile=str(out)))
                if verbose:
                    print(f"  [ok] {q} ({ya}-T) -> {out}")
            except Exception as exc:                          # noqa: BLE001
                errors.append((q, ya, str(exc)))
                if verbose:
                    print(f"  [!] {q} ({ya}-T): {exc}")
    return {"plots": plots, "errors": errors, "n_plots": len(plots)}


# ================================================================
# 任务 B —— 一维变化曲线
# ================================================================

def _pick_indices(n_total: int, idxs, max_n: int = 6) -> list[int]:
    """选曲线索引：用户指定则原样（去重排序）；否则均匀取 ``max_n`` 条。"""
    if idxs is not None:
        return sorted({int(i) for i in idxs})
    if n_total <= max_n:
        return list(range(n_total))
    return [round(i * (n_total - 1) / (max_n - 1)) for i in range(max_n)]


def _auto_log(field2d: np.ndarray) -> bool:
    """量纲跨越 >4 个数量级且全正 -> 建议对数 y 轴。"""
    v = np.asarray(field2d, dtype=float)
    vmin, vmax = np.nanmin(v), np.nanmax(v)
    return bool(vmin > 0 and (np.log10(vmax) - np.log10(vmin)) > 4)


def plot_vs_temperature(
    tbl: CN4Table, quantity: str = "zbar", *,
    density_idx=None, ig: int = 1, xlog: bool = True,
    ylog: bool | None = None, outfile: str | None = None,
    title: str | None = None, n_curves: int = 6,
    figsize: tuple[float, float] = (10.0, 7.5),
) -> str:
    """固定密度行，绘制物理量随温度 ``T`` (eV) 的变化；多条曲线 = 不同 ``n_ion``。

    Args:
        density_idx: 密度行索引列表；``None`` = 均匀取 ``n_curves`` 条
        ig: 不透明度群号（``opac_*`` / ``transmission`` 时有效）
    """
    plt = _plt()
    field, qlabel, _ = _resolve_quantity(tbl, quantity, None, ig)
    idxs = _pick_indices(tbl.ndens, density_idx, n_curves)
    Ts = _axis_values(tbl, "T")
    nions = _axis_values(tbl, "nion")

    fig, ax = plt.subplots(figsize=figsize)
    for i in idxs:
        ax.plot(Ts, field[i], lw=config.PLOT_LINEWIDTH, marker="o",
                ms=config.PLOT_MARKERSIZE - 2,
                label=f"$n_i$ = {nions[i]:.2e} cm$^{{-3}}$")
    if xlog:
        ax.set_xscale("log")
    if ylog is None:
        ylog = _auto_log(field[idxs])
    if ylog:
        ax.set_yscale("log")

    ax.set_xlabel(axis_label("T"))
    ax.set_ylabel(qlabel)
    ax.set_title(title or f"{qlabel} vs Temperature of {tbl.species_label}")
    ax.grid(True, which="both", alpha=0.3)
    _style_axes(ax, spine_lw=2.0)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE)
    fig.tight_layout()

    if outfile is None:
        d = os.path.dirname(os.path.abspath(tbl.filepath))
        outfile = os.path.join(d, f"{tbl.basename}_{quantity}_vs_T.png")
    return _save(fig, outfile, tag=f"{quantity}_vs_T")


def plot_vs_density(
    tbl: CN4Table, quantity: str = "zbar", *,
    temp_idx=None, ig: int = 1, xlog: bool = True,
    ylog: bool | None = None, outfile: str | None = None,
    title: str | None = None, n_curves: int = 6,
    figsize: tuple[float, float] = (10.0, 7.5),
) -> str:
    """固定温度列，绘制物理量随离子数密度 ``n_ion`` (cm^-3) 的变化。"""
    plt = _plt()
    field, qlabel, _ = _resolve_quantity(tbl, quantity, None, ig)
    idxs = _pick_indices(tbl.ntemp, temp_idx, n_curves)
    Ts = _axis_values(tbl, "T")
    nions = _axis_values(tbl, "nion")

    fig, ax = plt.subplots(figsize=figsize)
    for j in idxs:
        ax.plot(nions, field[:, j], lw=config.PLOT_LINEWIDTH, marker="s",
                ms=config.PLOT_MARKERSIZE - 2,
                label=f"$T$ = {Ts[j]:.2e} eV")
    if xlog:
        ax.set_xscale("log")
    if ylog is None:
        ylog = _auto_log(field[:, idxs])
    if ylog:
        ax.set_yscale("log")

    ax.set_xlabel(axis_label("nion"))
    ax.set_ylabel(qlabel)
    ax.set_title(title or f"{qlabel} vs Ion Density of {tbl.species_label}")
    ax.grid(True, which="both", alpha=0.3)
    _style_axes(ax, spine_lw=2.0)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE)
    fig.tight_layout()

    if outfile is None:
        d = os.path.dirname(os.path.abspath(tbl.filepath))
        outfile = os.path.join(d, f"{tbl.basename}_{quantity}_vs_nion.png")
    return _save(fig, outfile, tag=f"{quantity}_vs_nion")


# ================================================================
# 目录级批处理（用户关注的"多文件下如何绘制"）
# ================================================================

def plot_cn4_directory(
    paths: Sequence[str | os.PathLike],
    *,
    outdir: str | os.PathLike,
    quantities: Sequence[str] = ("zbar", "p_ion", "e_ele"),
    axes_pairs: Sequence[tuple[str, str]] = (("T", "nion"), ("T", "nele"),
                                             ("T", "rho")),
    curves: Sequence[str] = ("zbar",),
    opacity_figures: bool = False,
    transmission_L: float = 0.01,
    limit: int = 0,
    verbose: bool = True,
) -> dict:
    """对一批 cn4 文件批量出图（多文件流水线的绘图入口）。

    设计要点（针对多文件场景）
    --------------------------
    1. **逐文件独立**：单个文件解析/出图失败只记录到 ``errors``，
       不中断整批（科研数据常有单点异常）。
    2. **即时释放**：每张图落盘后立即 ``plt.close(fig)``，
       figure 句柄不累积（数十张图不会触发 pyplot 警告）。
    3. **可裁量**：``quantities`` / ``axes_pairs`` / ``curves`` /
       ``opacity_figures`` 决定出图矩阵规模，避免批量爆炸。
    4. **结果可审计**：返回 ``{"n_files", "n_plots", "plots", "errors"}``。

    Args:
        paths: cn4 文件路径序列（由调用方提供，通常来自 ``load_cn4_dir``）
        outdir: 所有图的落盘根目录（按文件名建子目录）
        quantities: 每个轴组合要画的物理量
        axes_pairs: ``(x_axis, y_axis)`` 组合；
            ⚠️ 含 ``nele`` 时需 scipy 散点插值，代价较高
        curves: 需要出一维曲线（vs T 与 vs nion）的物理量
        opacity_figures: 是否为每个能群出 2x2 大图（大图数量 = ngrups）
        limit: 最多处理前 N 个文件（0 = 全部）

    Returns:
        汇总字典
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    files = list(paths)
    if limit:
        files = files[:limit]

    plots: list[str] = []
    errors: list[tuple[str, str]] = []

    for fp in files:
        stem = Path(str(fp)).stem
        sub = outdir / stem
        try:
            from .cn4_io import load_cn4
            tbl = load_cn4(fp)
        except Exception as exc:                      # noqa: BLE001
            errors.append((str(fp), f"parse: {exc}"))
            if verbose:
                print(f"  [!] parse failed: {fp} -> {exc}")
            continue

        made_here = 0
        # —— 二维彩图矩阵 ——
        for (xa, ya) in axes_pairs:
            for q in quantities:
                try:
                    plots.append(plot_quantity_heatmap(
                        tbl, q, xa, ya,
                        outfile=sub / f"{stem}_{q}_{xa}-{ya}.png"))
                    made_here += 1
                except Exception as exc:              # noqa: BLE001
                    errors.append((str(fp), f"heatmap {q} {xa}-{ya}: {exc}"))

        # —— 一维曲线 ——
        for q in curves:
            for fn, tag in ((plot_vs_temperature, "vs_T"),
                            (plot_vs_density, "vs_nion")):
                try:
                    plots.append(fn(tbl, q,
                                    outfile=sub / f"{stem}_{q}_{tag}.png"))
                    made_here += 1
                except Exception as exc:              # noqa: BLE001
                    errors.append((str(fp), f"curve {q} {tag}: {exc}"))

        # —— 群不透明度大图 ——
        if opacity_figures:
            try:
                plots.extend(plot_all_opacity_figures(
                    tbl, outdir=sub, transmission_L=transmission_L))
                made_here += tbl.ngrups
            except Exception as exc:                  # noqa: BLE001
                errors.append((str(fp), f"opacity figures: {exc}"))

        if verbose:
            print(f"  [ok] {stem}: {made_here} figures")

    if verbose:
        print(f"[cn4.plots] {len(files)} files, {len(plots)} figures, "
              f"{len(errors)} errors -> {outdir}")

    return {
        "n_files": len(files),
        "n_plots": len(plots),
        "plots": plots,
        "errors": errors,
    }
