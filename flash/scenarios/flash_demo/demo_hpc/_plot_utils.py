"""
极简版 FLASH 1D HDF5 数据提取与绘图工具
═══════════════════════════════════════════

仅依赖 h5py + numpy + matplotlib，不依赖 output_processors 或 yt。

用法:
    from flash.scenarios.flash_demo.demo_hpc._plot_utils import extract_1d_profile, save_density_plot

    x, y = extract_1d_profile("lasslab_hdf5_plt_cnt_0066", "dens")
    save_density_plot(x, y, "output.png")
"""

import h5py
import numpy as np
from pathlib import Path


def extract_1d_profile(filepath: str, varname: str = "dens") -> tuple:
    """从 FLASH 1D HDF5 文件中提取变量的一维剖面。

    FLASH 1D 数据布局:
      - 物理量数组形状: (nblocks, NZ, NY, NX) → 1D 时 NZ=NY=1
      - dens[:, 0, 0, :] → (nblocks, NX)
      - bounding box: (nblocks, 3, 2) → b[:, 0, :] = 每块的 xmin, xmax

    Args:
        filepath: FLASH HDF5 文件路径（chk 或 plt）
        varname:  变量名 (默认 "dens")

    Returns:
        (x_sorted, y_sorted): 已按 x 升序排列的一维数组
    """
    with h5py.File(str(filepath), "r") as f:
        data = f[varname][:]        # (nblocks, NZ, NY, NX)
        bbox = f["bounding box"][:]  # (nblocks, 3, 2)

    ndim = data.ndim
    if ndim == 4:
        # (nblocks, NZ, NY, NX) — 取中间的 NZ/NY 层
        arr = data[:, 0, 0, :]  # (nblocks, NX)
    elif ndim == 3:
        # (nblocks, NY, NX) — 1D 取中间行
        arr = data[:, 0, :]     # (nblocks, NX)
    else:
        arr = data               # (nblocks, NX)

    nblocks, nx = arr.shape
    # FLASH 数据值存储在单元格中心，不是网格节点上
    # 单元格宽度: dx = (xmax - xmin) / nx
    # 第一个单元格中心: xmin + dx/2
    # 最后一个单元格中心: xmax - dx/2
    dx = (bbox[:, 0, 1] - bbox[:, 0, 0]) / nx   # (nblocks,) 每块 dx
    xmin_c = bbox[:, 0, 0] + dx / 2              # (nblocks,) 首单元格中心
    xmax_c = bbox[:, 0, 1] - dx / 2              # (nblocks,) 末单元格中心
    t = np.linspace(0, 1, nx)                    # 归一化坐标 [0,1]
    # 从单元格中心线性插值得到所有点的物理坐标
    # xmin_c[:, None] * (1 - t) + xmax_c[:, None] * t → (nblocks, NX)
    x = (xmin_c[:, None] * (1 - t) + xmax_c[:, None] * t).ravel()
    y = arr.ravel()

    # 按 x 排序（使用稳定的 mergesort 保证跨平台确定性）
    idx = np.argsort(x, kind="mergesort")
    x_sorted = x[idx]
    y_sorted = y[idx]

    # 合并重复 x 坐标处的值（取平均），解决 AMR 块边界处坐标重复问题
    unique_x, inverse = np.unique(x_sorted, return_inverse=True)
    if len(unique_x) < len(x_sorted):
        y_unique = np.zeros_like(unique_x)
        np.add.at(y_unique, inverse, y_sorted)
        counts = np.bincount(inverse)
        y_unique /= counts
        return unique_x, y_unique

    return x_sorted, y_sorted


def extract_center_value(filepath: str, varname: str = "dens") -> tuple:
    """提取 FLASH 1D 文件的中心位置变量值和仿真时间。

    Returns:
        (x_center, y_center, sim_time): 中心位置坐标、变量值、仿真时间 [s]
    """
    x, y = extract_1d_profile(filepath, varname)
    mid = len(y) // 2
    with h5py.File(str(filepath), "r") as f:
        # 从 real scalars 读时间 (compound dataset, dict-style 访问)
        rs = f["real scalars"][:]
        sim_time = 0.0
        for rec in rs:
            name = rec["name"].decode("utf-8").strip() if isinstance(rec["name"], bytes) else str(rec["name"]).strip()
            if name == "time":
                sim_time = float(rec["value"])
                break
    return x[mid], y[mid], sim_time


def plot_profile(ax, x: np.ndarray, y: np.ndarray, *,
                 label: str = None, color=None, linewidth: float = 1.5):
    """在指定 axes 上绘制一维剖面。"""
    ax.plot(x, y, color=color, linewidth=linewidth,
            label=label or "")
    ax.set_xlabel("x [cm]")
    ax.grid(True, alpha=0.3)


def save_density_plot(x: np.ndarray, y: np.ndarray, save_path: str, *,
                      title: str = None, dpi: int = 150):
    """Save the density distribution plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
# ── PPT-friendly plot style (fonts >= 18, English only) ──
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, y, "b-", linewidth=1.5)
    ax.set_xlabel("x [cm]")
    ax.set_ylabel(r"Density [g/cm$^3$]")
    ax.set_title(title or "Density Distribution")
    ax.grid(True, alpha=0.3)
    fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
