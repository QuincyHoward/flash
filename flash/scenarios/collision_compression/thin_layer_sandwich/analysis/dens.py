"""空间剖面图 — 从 FLASH chk 输出绘制 Tele/Nele/密度空间分布。

替代历史丢失的 ``analysis/dens.py``。
从 sim_output/ 中的 lasslab_hdf5_chk_* 文件读取末态空间剖面并绘图。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


def plot_tele_nele_spatial_profiles(
    sim_output_dir: str | Path,
    out_dir: str | Path,
    center_zoom_um: Optional[float] = None,
    var_names: Optional[List[str]] = None,
    dpi: int = 300,
) -> Dict[str, Path]:
    """从 chk 文件绘制末态空间剖面图。

    Args:
        sim_output_dir: 含 lasslab_hdf5_chk_* 的目录
        out_dir: 图片输出目录
        center_zoom_um: 中心放大半宽 (um), None=全范围
        var_names: 需要绘制的变量 (默认 dens/tele/ye)

    Returns:
        {name: Path} — 生成的图片路径 (可能为空)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sim_output_dir = Path(sim_output_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chk_files = sorted(sim_output_dir.glob("lasslab_hdf5_chk_*"))
    if not chk_files:
        # 回退: 任何 *chk* / *plt* 文件
        chk_files = sorted(sim_output_dir.glob("*chk*")) or sorted(sim_output_dir.glob("*plt*"))
    if not chk_files:
        return {}

    var_names = var_names or ["dens", "tele", "ye"]
    results: Dict[str, Path] = {}

    # 取最后一个文件 (末态)
    import h5py

    with h5py.File(str(chk_files[-1]), "r") as f:
        names = list(f.keys())
        xc = None
        data: Dict[str, np.ndarray] = {}
        for name in names:
            if name.startswith("x") and isinstance(f[name], h5py.Dataset):
                xc = np.asarray(f[name][()], dtype=np.float64)
            elif name in var_names and isinstance(f[name], h5py.Dataset):
                d = np.asarray(f[name][()], dtype=np.float64)
                if d.ndim == 1:
                    data[name] = d
        # 部分输出用 unk 数组 + 名字映射, 这里只支持直接数据集
        if xc is None or not data:
            return {}

    x_um = xc * 1e4
    mask = np.ones_like(x_um, dtype=bool)
    if center_zoom_um is not None:
        mask = np.abs(x_um) <= center_zoom_um

    n_vars = len([v for v in var_names if v in data])
    if n_vars == 0:
        return {}

    fig, axes = plt.subplots(1, n_vars, figsize=(6 * n_vars, 5), squeeze=False)
    for ax, vname in zip(axes[0], var_names):
        if vname not in data:
            continue
        ax.plot(x_um[mask], data[vname][mask], "b-", lw=2.0)
        ax.set_xlabel("x (um)", fontweight="bold")
        ax.set_title(vname, fontweight="bold")
        ax.grid(True, alpha=0.3)
    fig.suptitle(f"Final Profiles — {chk_files[-1].name}", fontweight="bold", y=1.02)
    plt.tight_layout()
    p = out_dir / "spatial_profiles.png"
    fig.savefig(str(p), dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    results["spatial_profiles"] = p
    return results
