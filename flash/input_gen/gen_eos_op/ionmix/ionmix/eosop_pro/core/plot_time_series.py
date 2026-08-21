# -*- coding: utf-8 -*-
"""
IONMIX / FLASH 时间演化绘图框架 (任务C: rho/nion/nele/tele 随时间变化)
======================================================================

IONMIX 自身输出是 (T, n_i) 静态表格, 不包含时间维度。
"随时间变化" 的数据来源是 FLASH 辐射流体模拟的 HDF5 时间序列输出:
    flash_hdf5/*plt_cnt*.hdf5  或  优化引擎的 result.h5

本模块提供两类接口:
  1. 通用绘图函数 plot_time_series(): 输入已提取的 (t, 空间剖面) 直接绘图
  2. FLASH HDF5 提取器 flash_extract(): 从 FLASH 输出文件提取
     某一物理量在 x 剖面上的时间演化 (依赖 output_processors.data_loader)

时间演化图的两种形式:
  A. 时间-空间彩图 (t, x) -> 物理量: 展示波前传播/加热演化
  B. 特征点时间曲线: 固定空间位置 (如靶中心 x=0), 物理量(t)

用法示例:
    # 形式A: (t, x) 彩图
    plot_time_series(times, xgrid, field_2d, xlabel="x (cm)",
                     quantity_label="Electron density (cm$^{-3}$)")

    # 形式B: 中心点时间曲线
    plot_center_series(times, xgrid, field_2d, x_center=0.0)

    # 从 FLASH HDF5 提取 (自动扫描同目录 hdf5 文件, 按时间排序)
    from plot_time_series import flash_extract
    times, xgrid, field = flash_extract("run_dir", var="tele", out_h5="result.h5")
"""

import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from plot_utils import setup_style, FONT_SIZE_LABEL, FONT_SIZE_TICK, save_fig


def plot_time_series(
    times: np.ndarray,          # (nt,) s
    xgrid: np.ndarray,          # (nx,) cm
    field: np.ndarray,          # (nt, nx) 物理量场
    xlabel: str = "x (cm)",
    quantity_label: str = "Quantity",
    title: str = "",
    cmap: str = "inferno",
    zlog: bool = None,          # None=自动
    outfile: str = None,
    figsize: tuple = (11.0, 8.0),
) -> str:
    """
    形式A: 时间-空间二维彩图 (t, x) -> 物理量, 展示演化过程。
    x 轴: 时间 (s, 线性或对数), y 轴: 空间坐标 x (cm), 颜色: 物理量。
    """
    import matplotlib.colors as mcolors
    setup_style()
    fig, ax = plt.subplots(figsize=figsize)
    X, Y = np.meshgrid(times, xgrid)
    fplot = np.ma.masked_invalid(field).T       # (nx, nt) 对齐 meshgrid
    if zlog is None:
        zlog = np.nanmin(field) > 0 and (
            np.log10(np.nanmax(field)) - np.log10(np.nanmin(field)) > 4)
    norm = (mcolors.LogNorm() if zlog else None)
    sm = ax.pcolormesh(X, Y, fplot, cmap=cmap, norm=norm,
                       shading="auto", rasterized=True)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(xlabel)
    if title:
        ax.set_title(title)
    for spine in ax.spines.values():
        spine.set_linewidth(2.0)
    ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(quantity_label, fontsize=FONT_SIZE_LABEL)
    cbar.ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    cbar.outline.set_linewidth(2.0)
    fig.tight_layout()
    return _save(fig, outfile, title or "time_series", quantity_label)


def plot_center_series(
    times: np.ndarray,          # (nt,) s
    xgrid: np.ndarray,          # (nx,) cm
    field: np.ndarray,          # (nt, nx)
    x_center: float = 0.0,      # 特征空间位置 (cm), 取最近网格点
    ylog: bool = True,
    xlog: bool = False,
    quantity_label: str = "Quantity",
    outfile: str = None,
) -> str:
    """
    形式B: 特征点 (默认靶中心 x_center) 的物理量随时间演化曲线。
    """
    setup_style()
    i = int(np.argmin(np.abs(xgrid - x_center)))
    fig, ax = plt.subplots(figsize=(10.0, 7.0))
    ax.plot(times, field[:, i], lw=2.5, marker="o", ms=5,
            label=f"x = {xgrid[i]:.4e} cm")
    if xlog:
        ax.set_xscale("log")
    if ylog:
        ax.set_yscale("log")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(quantity_label)
    ax.set_title(f"{quantity_label} at x={xgrid[i]:.3e} cm")
    ax.legend(fontsize=FONT_SIZE_TICK)
    for spine in ax.spines.values():
        spine.set_linewidth(2.0)
    ax.tick_params(labelsize=FONT_SIZE_TICK, width=2.0, length=6)
    fig.tight_layout()
    return _save(fig, outfile, f"center_{quantity_label}", quantity_label)


# ---------------------------------------------------------------
# FLASH HDF5 提取器 (未来对接 output_processors.data_loader)
# ---------------------------------------------------------------

def flash_extract(
    run_dir: str,
    var: str = "tele",
    out_h5: str = None,
    xvar: str = "x",
) -> tuple:
    """
    从 FLASH 输出目录提取变量沿 x 剖面的时间演化。

    自动扫描 run_dir 下按时间排序的 hdf5 文件:
        - 裸 FLASH 输出: *_plt_cnt_*.hdf5 / *hdf5_plt_cnt_*
        - 优化引擎聚合: result.h5 (含 ed_time 数据集)
    若 out_h5 提供且存在, 优先读取 (数据格式见使用说明书)。

    Returns:
        (times (nt,), xgrid (nx,), field (nt, nx))
    """
    # 优先: 显式聚合文件
    if out_h5 and os.path.exists(out_h5):
        return _read_h5(out_h5, var)
    files = sorted(glob.glob(os.path.join(run_dir, "*.h5"))) + \
            sorted(glob.glob(os.path.join(run_dir, "*.hdf5")))
    if not files:
        raise FileNotFoundError(f"run_dir 下未找到 hdf5 文件: {run_dir}")
    times, xgrid, fields = [], None, []
    for fp in files:
        t, x, f = _read_single_flash(fp, var, xvar)
        times.append(t)
        xgrid = x
        fields.append(f)
    order = np.argsort(times)
    return (np.array([times[i] for i in order]),
            xgrid,
            np.array([fields[i] for i in order]))


def _read_single_flash(fp, var, xvar):
    """读取单个 FLASH plot 文件: 返回 (time, xgrid, field1d)"""
    import h5py
    with h5py.File(fp, "r") as h:
        time = float(h["sim time"][()]) if "sim time" in h else 0.0
        if xvar not in h:
            raise KeyError(f"{fp} 中无 {xvar} 数据")
        x = h[xvar][()]
        if var not in h:
            raise KeyError(f"{fp} 中无 {var} 数据 (可选: {list(h.keys())})")
        f = h[var][()]
    return time, np.asarray(x), np.asarray(f)


def _read_h5(fp, var):
    """读取优化引擎聚合 result.h5: 含 ed_time 时间数组"""
    import h5py
    with h5py.File(fp, "r") as h:
        keys = list(h.keys())
        # 寻找时间数组与变量
        tkey = "ed_time" if "ed_time" in h else \
               next((k for k in keys if "time" in k.lower()), None)
        if tkey is None:
            raise KeyError(f"{fp} 中未找到时间数组, keys={keys}")
        times = h[tkey][()]
        vkey = var if var in h else next(
            (k for k in keys if var.lower() in k.lower()), None)
        if vkey is None:
            raise KeyError(f"{fp} 中未找到变量 {var}, keys={keys}")
        f = h[vkey][()]
        xkey = "x" if "x" in h else next(
            (k for k in keys if k.lower() in ("x", "xgrid", "position")), None)
        x = h[xkey][()] if xkey else np.arange(f.shape[1])
    return np.asarray(times), np.asarray(x), np.asarray(f)


def _save(fig, outfile, tag, qlabel):
    """保存图像: 默认按 tag 生成文件名于 cwd"""
    if outfile is None:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)
        outfile = os.path.join(os.getcwd(), f"{safe}.png")
    return save_fig(fig, outfile, tag)


if __name__ == "__main__":
    # 自测: 合成高斯波包传播
    t = np.linspace(0, 3.1e-9, 50)
    x = np.linspace(-100e-4, 100e-4, 200)
    T, X = np.meshgrid(t, x)
    field = np.exp(-((X - 5e-3 * T / 3.1e-9) ** 2) / (2 * (10e-4) ** 2)) * 1e20
    print(plot_time_series(t, x, field.T, title="Test wave",
                           quantity_label="Density (cm$^{-3}$)",
                           outfile="_test_ts.png"))
    os.remove("_test_ts.png")
