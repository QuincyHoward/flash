"""
tele_nele — 电子温度/密度诊断分析

替代原有的 dens 分析模块, 提供:
  - plot_tele_nele_time_series: 双 y 轴时序图 (tele 红左轴 + nele 蓝右轴)
  - plot_tele_nele_spatial_profiles: 双子图空间剖面 (tele / nele)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

NA = 6.02214076e23


# ── tele / nele 双轴时间序列图 ───────────────────────────

def plot_tele_nele_time_series(
    times_s: np.ndarray,
    tele_series: np.ndarray,
    nele_series: np.ndarray,
    save_prefix: str,
    *,
    window_result: Optional[Dict[str, Any]] = None,
    tele_label: str = "Tele (K)",
    nele_label: str = "Nele (cm⁻³)",
    title: str = "Electron Temperature & Density vs Time",
) -> Dict[str, str]:
    """绘制 tele(红,左轴) + nele(蓝,右轴) 双轴时间序列图, 可选最优窗口标注。

    Args:
        times_s: 时间数组 (s)
        tele_series: 电子温度序列 (K)
        nele_series: 电子密度序列 (cm⁻³)
        save_prefix: 保存路径前缀 (不含扩展名)
        window_result: sliding_window_txn() 的结果, 含 best_start_ns/best_end_ns/tele_mean_window/nele_mean_window
        tele_label: 左轴标签
        nele_label: 右轴标签
        title: 图标题

    Returns:
        {变量名: 路径} 字典
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    times_ns = times_s * 1e9

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # 左轴: tele (红色)
    color_tele = "red"
    ax1.set_xlabel("Time (ns)", fontsize=16)
    ax1.set_ylabel(tele_label, color=color_tele, fontsize=16)
    ax1.plot(times_ns, tele_series, color=color_tele, linewidth=2.0,
             label="Tele")
    ax1.tick_params(axis="y", labelcolor=color_tele, labelsize=14)
    ax1.tick_params(axis="x", labelsize=14)
    ax1.grid(True, alpha=0.3)

    # 右轴: nele (蓝色)
    ax2 = ax1.twinx()
    color_nele = "blue"
    ax2.set_ylabel(nele_label, color=color_nele, fontsize=16)
    ax2.plot(times_ns, nele_series, color=color_nele, linewidth=2.0,
             linestyle="--", label="Nele")
    ax2.tick_params(axis="y", labelcolor=color_nele, labelsize=14)

    # 最优 300ps 窗口标注
    if window_result is not None:
        ws = window_result.get("best_start_ns", 3.0)
        we = window_result.get("best_end_ns", 3.0)
        tele_mw = window_result.get("tele_mean_window", 0.0)
        nele_mw = window_result.get("nele_mean_window", 0.0)
        txn_eff = window_result.get("txn_effective", 0.0)

        ax1.axvspan(ws, we, color="green", alpha=0.15,
                    label=f"Best 300ps (txn_norm={txn_eff:.3f})")
        ax1.axvline(x=ws, color="green", linestyle="--", alpha=0.5)
        ax1.axvline(x=we, color="green", linestyle="--", alpha=0.5)
        # 水平参考线: 窗口均值
        ax1.axhline(y=tele_mw, color="red", linestyle=":", alpha=0.5,
                    label=f"Tele mean={tele_mw:.3e}")
        ax2.axhline(y=nele_mw, color="blue", linestyle=":", alpha=0.5,
                    label=f"Nele mean={nele_mw:.3e}")

    # 合并图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=12, loc="upper left")

    fig.suptitle(title, fontsize=18, fontweight="bold")

    plt.tight_layout()
    path = save_prefix + "_time_series.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)

    return {"tele_nele_time_series": path}


# ── tele / nele 空间剖面双子图 ───────────────────────────

def plot_tele_nele_spatial_profiles(
    output_dir: Path,
    plots_dir: Path,
    *,
    center_zoom_um: Optional[float] = None,
    n_timesteps: int = 20,
) -> Dict[str, str]:
    """绘制 tele / nele 空间剖面双子图 (多时间步叠加)。

    从 result.h5 或 FLASH plt 文件读取数据, 绘制两个子图:
      - 上: tele(x) 随时间的演化
      - 下: nele(x) 随时间的演化

    Args:
        output_dir: 输出目录 (含 result.h5 或 plt 文件)
        plots_dir: 图片保存目录
        center_zoom_um: 中心区域放大半宽 (um), None=全范围
        n_timesteps: 采样时间步数

    Returns:
        {变量名: 路径} 字典
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ── 读取数据 ──
    result_h5 = output_dir / "result.h5"
    if not result_h5.exists():
        # 尝试父目录
        for p in [output_dir.parent / "database" / "flash_out" / "result.h5",
                   output_dir.parent.parent / "database" / "flash_out" / "result.h5"]:
            if p.exists():
                result_h5 = p
                break

    if not result_h5.exists():
        # 回退: 从 plt 文件读取
        return _plot_spatial_from_plt(output_dir, plots_dir, center_zoom_um, n_timesteps)

    import h5py
    try:
        with h5py.File(str(result_h5), "r") as f:
            t = np.array(f["t"][:], dtype=float)
            x = np.array(f["x"][:], dtype=float)
            tele = np.array(f["tele"][()], dtype=float)
            ye = np.array(f["ye"][()], dtype=float)
            dens = np.array(f["dens"][()], dtype=float)
    except Exception:
        return {}

    nele = ye * dens * NA
    t_ns = t * 1e9

    # 空间: 全范围 + 中心±5um 放大
    zoom_um = 5.0
    x_all = x * 1e4  # cm → um
    mask_zoom = np.abs(x_all) <= zoom_um
    x_zoom = x_all[mask_zoom]

    nt = len(t)
    step = max(1, nt // n_timesteps)
    cmap = plt.cm.viridis
    norm = plt.Normalize(float(t_ns[0]), float(t_ns[-1])) if nt > 1 else plt.Normalize(0, 1)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    # axes: (0,0)=tele全 (0,1)=tele放 (1,0)=nele全 (1,1)=nele放

    for idx, (var, label, unit, data_full, data_zoom) in enumerate([
        ("Tele",  "Tele",  "K",      tele,  tele[:, mask_zoom]),
        ("Nele",  "Nele",  "cm\u207b\u00b3", nele,  nele[:, mask_zoom]),
    ]):
        # 全范围
        ax = axes[idx][0]
        for i in range(0, nt, step):
            ax.plot(x_all, data_full[i, :], color=cmap(norm(t_ns[i])),
                    alpha=0.7, lw=0.8)
        ax.set_ylabel(f"{label} ({unit})", fontsize=14)
        if idx == 0:
            ax.set_title(f"{label} Spatial Profile (Full)", fontsize=16, fontweight="bold")
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=12)

        # 中心±5um 放大
        ax = axes[idx][1]
        for i in range(0, nt, step):
            ax.plot(x_zoom, data_zoom[i, :], color=cmap(norm(t_ns[i])),
                    alpha=0.7, lw=0.8)
        if idx == 0:
            ax.set_title(f"{label} Spatial Profile (Center \u00b1{zoom_um:.0f} \u00b5m)",
                         fontsize=16, fontweight="bold")
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=12)
        ax.set_xlim(-zoom_um, zoom_um)

    # 共用 x 轴标签
    for ax in axes[1]:
        ax.set_xlabel("x (\u00b5m)", fontsize=14)

    # 共用 colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, shrink=0.6, pad=0.02)
    cbar.set_label("Time (ns)", fontsize=14)
    cbar.ax.tick_params(labelsize=12)

    fig.suptitle("Electron Temperature & Density Spatial Profiles",
                 fontsize=18, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    path = str(plots_dir / "analysis_spatial.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return {"tele_nele_spatial": path}


def _plot_spatial_from_plt(
    output_dir: Path,
    plots_dir: Path,
    center_zoom_um: Optional[float] = None,
    n_timesteps: int = 20,
) -> Dict[str, str]:
    """从 FLASH plt 文件回退绘制 tele/nele 空间剖面。"""
    import matplotlib.pyplot as plt
    import h5py

    plot_files = sorted(output_dir.glob("**/*hdf5_plt_cnt*"))
    if not plot_files:
        plot_files = sorted(output_dir.glob("**/*hdf5*plt*"))
    if not plot_files:
        return {}

    times_ns: list = []
    tele_profiles: list = []
    nele_profiles: list = []

    for pf in plot_files:
        try:
            with h5py.File(str(pf), "r") as f:
                coords = f["coordinates"][:]
                x = coords[:, 0] if coords.ndim == 2 else coords
                tele_arr = f["tele"][:]
                ye_arr = f["ye"][:]
                dens_arr = f["dens"][:]
                t = 0.0
                if "timestep" in f:
                    t = float(f["timestep"].attrs.get("time", 0.0))
                elif "time" in f.attrs:
                    t = float(f.attrs["time"])
            idx = np.argsort(x)
            tele_profiles.append(tele_arr[idx])
            nele_profiles.append((ye_arr * dens_arr * NA)[idx])
            times_ns.append(t * 1e9)
        except Exception:
            continue

    if not tele_profiles:
        return {}

    x_sorted = np.sort(x)
    x_plot = x_sorted * 1e4
    if center_zoom_um is not None:
        mask = np.abs(x_plot) <= center_zoom_um
        x_plot = x_plot[mask]

    sort_idx = np.argsort(times_ns)
    times_ns_sorted = [times_ns[i] for i in sort_idx]
    tele_sorted = [tele_profiles[i] for i in sort_idx]
    nele_sorted = [nele_profiles[i] for i in sort_idx]

    step = max(1, len(tele_sorted) // n_timesteps)
    cmap = plt.cm.viridis
    norm = plt.Normalize(times_ns_sorted[0], times_ns_sorted[-1]) if len(times_ns_sorted) > 1 else plt.Normalize(0, 1)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    for i in range(0, len(tele_sorted), step):
        color = cmap(norm(times_ns_sorted[i]))
        ax1.plot(x_plot, tele_sorted[i], color=color, alpha=0.7, lw=0.8)
        ax2.plot(x_plot, nele_sorted[i], color=color, alpha=0.7, lw=0.8)

    ax1.set_ylabel("Tele (K)", fontsize=16)
    ax1.set_title("Electron Temperature Spatial Profiles", fontsize=18, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(labelsize=14)

    ax2.set_xlabel("x (μm)", fontsize=16)
    ax2.set_ylabel("Nele (cm⁻³)", fontsize=16)
    ax2.set_title("Electron Density Spatial Profiles", fontsize=18, fontweight="bold")
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(labelsize=14)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=[ax1, ax2], shrink=0.6, pad=0.02)
    cbar.set_label("Time (ns)", fontsize=14)

    plt.tight_layout()
    path = str(plots_dir / "analysis_spatial.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return {"tele_nele_spatial": path}
