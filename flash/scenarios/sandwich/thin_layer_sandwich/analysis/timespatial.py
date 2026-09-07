"""
timespatial — 时空演化诊断图

从引擎 result.h5 读取数据，绘制 txn / tele / nele / dens 的
时空变化 2×2 四子图。x 轴限制在 CH 中心 ±5 um 区域，
y 轴为完整时间范围。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

NA = 6.02214076e23


def plot_time_spatial(
    result_h5_path: Path,
    save_path: Path,
    *,
    center_half_width_um: float = 5.0,
    field_names: Optional[list] = None,
    title: str = "Spatiotemporal Evolution (CH Center ±5 um)",
) -> Path:
    """绘制 txn / tele / nele / dens 四子图时空演化图。

    Args:
        result_h5_path: 引擎 result.h5 文件路径
        save_path: PNG 保存路径
        center_half_width_um: 空间裁剪半宽 (um), 默认 ±5 um
        field_names: 要显示的变量列表, 默认 ["txn", "tele", "nele", "dens"]
        title: 总标题

    Returns:
        save_path: 保存的文件路径
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import h5py

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 读取 result.h5 ──
    try:
        with h5py.File(str(result_h5_path), "r") as f:
            t = np.array(f["t"][:], dtype=float)
            x = np.array(f["x"][:], dtype=float)
            dens = np.array(f["dens"][()], dtype=float)
            tele = np.array(f["tele"][()], dtype=float)
            ye = np.array(f["ye"][()], dtype=float)
    except Exception as exc:
        raise FileNotFoundError(f"无法读取 result.h5: {exc}") from exc

    # ── 计算 nele 和 txn ──
    nele = ye * dens * NA
    txn = tele * nele

    # ── 空间裁剪: ±center_half_width_um ──
    half_cm = center_half_width_um * 1e-4
    x_mask = np.abs(x) <= half_cm
    x_cropped = x[x_mask] * 1e4  # 转换为 um

    dens_c = dens[:, x_mask]
    tele_c = tele[:, x_mask]
    nele_c = nele[:, x_mask]
    txn_c = txn[:, x_mask]

    t_ns = t * 1e9  # 转换为 ns

    # ── 预定义变量配置 ──
    var_config = {
        "txn":  (txn_c,           r"txn = $n_e \times T_e$",  None),
        "tele": (tele_c,          r"$T_e$ (K)",               None),
        "nele": (nele_c,          r"$n_e$ (cm$^{-3}$)",       None),
        "dens": (dens_c,          r"Density (g/cm$^3$)",       None),
    }

    if field_names is None:
        field_names = ["txn", "tele", "nele", "dens"]

    # ── 2×2 子图 ──
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle(title, fontsize=18, fontweight="bold")

    for idx, fname in enumerate(field_names):
        if fname not in var_config:
            continue
        data, label, _ = var_config[fname]
        ax = axes[idx // 2][idx % 2]

        # imshow: 时间沿 y 轴, 空间沿 x 轴
        # origin="lower" + extent=[x0,x1, y0,y1]:
        #   data[0,:] (t=0) → 底部 y=y0 = t_ns[0]
        #   data[-1,:] (t=max) → 顶部 y=y1 = t_ns[-1]
        extent = [
            float(x_cropped[0]), float(x_cropped[-1]),
            float(t_ns[0]), float(t_ns[-1]),
        ]
        im = ax.imshow(
            data,
            aspect="auto",
            origin="lower",
            extent=extent,
            interpolation="bilinear",
        )

        cbar = fig.colorbar(im, ax=ax, shrink=0.85)
        cbar.set_label(label, fontsize=12)

        ax.set_xlabel("x (μm)", fontsize=14)
        ax.set_ylabel("Time (ns)", fontsize=14)
        ax.set_title(fname.upper(), fontsize=16, fontweight="bold")
        ax.tick_params(labelsize=12)

    fig.savefig(str(save_path), dpi=150)
    plt.close(fig)

    return save_path
