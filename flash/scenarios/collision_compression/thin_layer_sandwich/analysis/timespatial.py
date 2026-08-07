"""时空演化图 — 从 result.h5 绘制 t-x 密度/温度热图。

替代历史丢失的 ``analysis/timespatial.py``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


def plot_time_spatial(
    result_h5: str | Path,
    save_path: str | Path = "analysis_time_spatial.png",
    var_names: Optional[list] = None,
    xlim_um: Optional[tuple] = None,
    dpi: int = 300,
) -> Path:
    """从 result.h5 绘制 t-x 时空热图 (多变量并排)。

    Args:
        result_h5: 引擎 result.h5 路径
        save_path: PNG 保存路径
        var_names: 变量列表 (默认 ["dens", "tele"])
        xlim_um: x 范围 (um), None=全范围
        dpi: 输出 DPI

    Returns:
        save_path (Path)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import h5py

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    var_names = var_names or ["dens", "tele"]

    with h5py.File(str(result_h5), "r") as f:
        t = np.asarray(f["t"][:], dtype=np.float64)
        x = np.asarray(f["x"][:], dtype=np.float64)
        data = {v: np.asarray(f[v][()], dtype=np.float64) for v in var_names if v in f}

    if not data or len(t) < 2:
        raise RuntimeError("result.h5 无可用数据 (字段缺失或时间点不足)")

    x_um = x * 1e4
    t_ns = t * 1e9
    mask = np.ones_like(x_um, dtype=bool)
    if xlim_um is not None:
        mask = (x_um >= xlim_um[0]) & (x_um <= xlim_um[1])

    n_vars = len(data)
    fig, axes = plt.subplots(1, n_vars, figsize=(7 * n_vars, 5.5), squeeze=False)
    cmaps = {"dens": "inferno", "tele": "plasma", "ye": "viridis", "pres": "magma"}
    for ax, (vname, arr) in zip(axes[0], data.items()):
        im = ax.pcolormesh(x_um[mask], t_ns, arr[:, mask],
                           shading="auto", cmap=cmaps.get(vname, "viridis"))
        ax.set_xlabel("x (um)", fontweight="bold")
        ax.set_ylabel("Time (ns)", fontweight="bold")
        ax.set_title(vname, fontweight="bold")
        plt.colorbar(im, ax=ax, shrink=0.85)
    fig.suptitle("Time-Spatial Evolution", fontweight="bold", y=1.02)
    plt.tight_layout()
    fig.savefig(str(save_path), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return save_path
