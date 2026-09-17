#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""声速模块 —— 绘图层：γ 场图 / 等熵声速场图 / 两项占比 / γ(T) 拟合图。

规约（与包内一致）
------------------
- 全 ASCII 图上文本（``style.assert_ascii`` 强制守卫）
- 字号走 ``config.PLOT_*``（PPT 级，>18pt）
- 图上数值一律 ``:.1e``（r15 规约）
- viridis / DPI 450 / 保存后立即 ``close(fig)``
- 热力图统一走 ``gridmap.plot_heatmap`` 原语；折线图自绘后用公开
  ``style.assert_ascii`` + ``savefig`` + ``close``（不碰包私有 _save）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from eosop_pro import config
from eosop_pro.plotting import style
from eosop_pro.plotting.gridmap import plot_heatmap

__all__ = [
    "plot_gamma_field", "plot_cs_field",
    "plot_thermal_fraction_field", "plot_gamma_T_fit",
]

_XLABEL = "Temperature T (eV)"
_YLABEL = "Number density n (cm^-3)"


def _axes(tbl) -> tuple[np.ndarray, np.ndarray]:
    """(temperature eV, density 数密度 cm^-3) 1D 轴。"""
    return (np.asarray(tbl.temperature, dtype=float),
            np.asarray(tbl.density, dtype=float))


def plot_gamma_field(tbl, gamma: np.ndarray, species_label: str,
                     outfile: str | Path) -> str:
    """有效 γ 场图（线性色标 vmin=1 vmax=2，理论带 5/3 居中）。

    ``species_label`` 取 ``"ion"`` / ``"ele"``（ASCII，进 title/文件名语义）。
    """
    style.apply_style()
    T, n = _axes(tbl)
    return plot_heatmap(
        x=T, y=n, field=gamma,
        xlabel=_XLABEL, ylabel=_YLABEL,
        clabel=f"Effective gamma_{species_label} = 1 + P/(rho e)",
        title=f"Effective gamma_{species_label} field "
              "(single-atom ideal-gas anchor 5/3)",
        outfile=outfile, vmin=1.0, vmax=2.0,
        xlog=True, ylog=True, zlog=False,
    )


def plot_cs_field(tbl, cs_umns: np.ndarray, outfile: str | Path) -> str:
    """严格等熵声速场图（对数色标，um/ns）。"""
    style.apply_style()
    T, n = _axes(tbl)
    return plot_heatmap(
        x=T, y=n, field=cs_umns,
        xlabel=_XLABEL, ylabel=_YLABEL,
        clabel="Sound speed c_s (um/ns)",
        title="Isentropic sound speed c_s^2 = (dP/drho)_s",
        outfile=outfile, xlog=True, ylog=True, zlog=True,
    )


def plot_thermal_fraction_field(tbl, frac: np.ndarray,
                                outfile: str | Path) -> str:
    """热熵项占 c_s^2 比值场（线性 0-1；单原子理想气体锚 0.40）。"""
    style.apply_style()
    T, n = _axes(tbl)
    return plot_heatmap(
        x=T, y=n, field=frac,
        xlabel=_XLABEL, ylabel=_YLABEL,
        clabel="Thermal-entropy term fraction of c_s^2",
        title="c_s^2 thermal term fraction (ideal-gas anchor 0.40)",
        outfile=outfile, xlog=True, ylog=True, zlog=False,
        vmin=0.0, vmax=1.0,
    )


def plot_gamma_T_fit(tbl, gamma_row_i: np.ndarray, gamma_row_e: np.ndarray,
                     fit_i: tuple[float, float, float],
                     fit_e: tuple[float, float, float],
                     outfile: str | Path) -> str:
    """固定密度行 ``γ(T)`` 双曲线 + 幂律拟合 + 5/3 理论横线（log-log）。

    ``fit_i`` / ``fit_e`` 为 :func:`sv_physics.fit_gamma_powerlaw` 的
    ``(a, b, r2)``；图例数值一律 ``:.1e``（常数数据 R^2 偏低是预期，
    因为 SS_tot 很小）。
    """
    plt = style.apply_style()
    T = np.asarray(tbl.temperature, dtype=float)
    rho_mid = float(np.asarray(tbl.density, dtype=float)[tbl.ndens // 2])

    fig, ax = plt.subplots(figsize=config.PLOT_FIGSIZE)
    m = np.isfinite(T) & (T > 0)

    ai, bi, r2i = fit_i
    ae, be, r2e = fit_e
    ax.plot(T[m], gamma_row_i[m], "o-", ms=config.PLOT_MARKERSIZE,
            label=f"gamma_i (fit a={ai:.1e}, b={bi:.1e}, R2={r2i:.1e})")
    ax.plot(T[m], gamma_row_e[m], "s--", ms=config.PLOT_MARKERSIZE,
            label=f"gamma_e (fit a={ae:.1e}, b={be:.1e}, R2={r2e:.1e})")
    if np.isfinite(ai) and bi != 0:
        ax.plot(T[m], ai * T[m] ** bi, ":", color="black", lw=2.0,
                label="power-law fits")
    ax.axhline(5.0 / 3.0, color="red", lw=2.0, ls="-.", alpha=0.9,
               label="single-atom ideal-gas anchor 5/3")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(_XLABEL)
    ax.set_ylabel(r"Effective gamma = 1 + P/(rho e)")
    ax.set_title(f"gamma(T) at n = {rho_mid:.1e} cm^-3 "
                 "(mid-density row)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=config.PLOT_LEGEND_FONTSIZE, loc="best")
    ax.tick_params(labelsize=config.PLOT_TICK_FONTSIZE)

    style.assert_ascii(fig)
    fig.savefig(outfile, dpi=config.PLOT_DPI, bbox_inches="tight")
    plt.close(fig)
    return str(outfile)
