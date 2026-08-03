#!/usr/bin/env python3
"""
对比图: 纯 h5py (extract_var_yt_style) vs yt 提取 FLASH AMR 数据
晚时间 FLASH 输出文件 (1D chk_0039, 2D plt_0049, 3D plt_0020)
坐标系统自动检测: Cartesian / Cylindrical
3D 增加 xOy (投影到 xy 平面) 和 yOz (投影到 yz 平面) 对比
"""

import sys, os, time, warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# ── PPT-friendly plot style (fonts >= 18, English only) ──
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass

# ── 路径 ─────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PROJECT_DIR)  # output_processors/
OUTPUT_DIR = os.path.join(PARENT_DIR, "outputfiles", "test")
os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(PROJECT_DIR, "..", "..", ".."))
from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File

# ── 晚时间测试文件 ────────────────────────────────────────────
TEST_FILES = {
    "1D": {"path": os.path.join(PARENT_DIR, "inputfiles/hdf5files_1d/lasslab_hdf5_chk_0039")},
    "2D": {"path": os.path.join(PARENT_DIR, "inputfiles/hdf5files_2d/lasslab_hdf5_plt_cnt_0049")},
    "3D": {"path": os.path.join(PARENT_DIR, "inputfiles/hdf5files_3d/lasslab_hdf5_plt_cnt_0020")},
}


def extract_with_yt(hdf5_path, ndim=1):
    """使用 yt 提取数据"""
    import yt
    ds = yt.load(hdf5_path)
    ad = ds.all_data()
    dens_yt = ad["dens"].to_ndarray().flatten()

    # 检测坐标系统
    has_cartesian = False
    try:
        _ = ad["x"]
        has_cartesian = True
    except:
        try:
            _ = ad[("flash", "x")]
            has_cartesian = True
        except:
            has_cartesian = False

    if ndim == 1:
        try:
            x_yt = ad["x"].to_ndarray().flatten()
        except:
            x_yt = np.arange(len(dens_yt))
        idx = np.argsort(x_yt, kind="mergesort")
        return x_yt[idx], dens_yt[idx]

    elif ndim == 2:
        # 2D FLASH 柱坐标: FLASH 的 x=r(径向), y=z(轴向), z=θ(角度)
        # yt 中 ('flash','r')=径向, ('flash','z')=轴向
        x_yt = ad[("flash", "r")].to_ndarray().flatten()
        y_yt = ad[("flash", "z")].to_ndarray().flatten()
        return x_yt, y_yt, dens_yt

    else:  # ndim == 3
        if has_cartesian:
            x_yt = ad["x"].to_ndarray().flatten()
            y_yt = ad["y"].to_ndarray().flatten()
            z_yt = ad["z"].to_ndarray().flatten()
        else:
            x_yt = ad[("flash", "r")].to_ndarray().flatten()
            y_yt = ad[("flash", "theta")].to_ndarray().flatten()
            z_yt = ad[("flash", "z")].to_ndarray().flatten()
        return x_yt, y_yt, z_yt, dens_yt


def extract_with_h5py(hdf5_path, var_name="dens"):
    """纯 h5py yt 风格提取"""
    ff = FlashHDF5File(hdf5_path)
    result = ff.extract_var_yt_style(var_name)
    ff.close()
    return result


# ── 工具函数 ──────────────────────────────────────────────────
def stats_string(diff, ref):
    """返回差异统计字符串"""
    abs_diff = np.abs(diff)
    rel_diff = np.abs(diff) / np.maximum(np.abs(ref), 1e-30)
    return (f"max|diff|={np.max(abs_diff):.4e}, "
            f"mean|diff|={np.mean(abs_diff):.4e}, "
            f"RMSE={np.sqrt(np.mean(diff**2)):.4e}, "
            f"max|rel|={np.max(rel_diff):.4e}")


# ── 1D 对比 ──────────────────────────────────────────────────
def compare_1d():
    print("=" * 60)
    print("1D 对比: h5py vs yt")
    print("=" * 60)
    hdf5_path = TEST_FILES["1D"]["path"]

    t0 = time.time()
    x_h5, d_h5 = extract_with_h5py(hdf5_path, "dens")
    t_h5 = time.time() - t0
    t0 = time.time()
    x_yt, d_yt = extract_with_yt(hdf5_path, ndim=1)
    t_yt = time.time() - t0
    print(f"  h5py: {len(x_h5)} pts, {t_h5:.3f}s")
    print(f"  yt:   {len(x_yt)} pts, {t_yt:.3f}s")

    x_common = np.union1d(np.round(x_h5, 12), np.round(x_yt, 12))
    x_common.sort()
    d_h5_interp = np.interp(x_common, x_h5, d_h5)
    d_yt_interp = np.interp(x_common, x_yt, d_yt)
    diff = d_h5_interp - d_yt_interp
    rel_diff = diff / np.maximum(np.abs(d_yt_interp), 1e-30)

    stats = {"N": len(x_h5), "N_yt": len(x_yt), "match": len(x_h5) == len(x_yt),
              "max_abs_diff": float(np.max(np.abs(diff))),
              "mean_abs_diff": float(np.mean(np.abs(diff))),
              "rmse": float(np.sqrt(np.mean(diff ** 2))),
              "max_rel_diff": float(np.max(np.abs(rel_diff))),
              "mean_rel_diff": float(np.mean(np.abs(rel_diff))),
              "time_h5": t_h5, "time_yt": t_yt}
    print(f"  {stats_string(diff, d_yt_interp)}")
    print(f"  点数匹配: {'✓' if stats['match'] else '✗'} ({len(x_h5)} vs {len(x_yt)})")

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    ax = axes[0]
    ax.plot(x_h5, d_h5, "b-", lw=2, alpha=0.7, label=f"h5py ({len(x_h5)} pts)")
    ax.plot(x_yt, d_yt, "r--", lw=1.5, alpha=0.7, label=f"yt ({len(x_yt)} pts)")
    ax.set_ylabel("Density [g/cm³]")
    ax.set_title("1D: h5py vs yt (Density, late-time)", fontweight="bold")
    ax.legend(fontsize=12); ax.grid(True, alpha=0.3); ax.tick_params(labelsize=12)

    ax = axes[1]
    ax.semilogy(x_common, np.abs(diff), "k.", ms=2, alpha=0.5)
    ax.axhline(stats["mean_abs_diff"], color="r", ls="--", lw=1, label=f"mean = {stats['mean_abs_diff']:.2e}")
    ax.axhline(stats["rmse"], color="orange", ls="--", lw=1, label=f"RMSE = {stats['rmse']:.2e}")
    ax.set_ylabel("|diff| [g/cm³]")
    ax.set_title(f"1D |diff| (max={stats['max_abs_diff']:.2e})")
    ax.legend(fontsize=11); ax.grid(True, alpha=0.3); ax.tick_params(labelsize=12)

    ax = axes[2]
    ax.semilogy(x_common, np.abs(rel_diff) + 1e-30, "b.", ms=2, alpha=0.5)
    ax.axhline(stats["mean_rel_diff"], color="r", ls="--", lw=1, label=f"mean = {stats['mean_rel_diff']:.2e}")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("|rel diff|")
    ax.set_title(f"1D |rel diff| (max={stats['max_rel_diff']:.2e})")
    ax.legend(fontsize=11); ax.grid(True, alpha=0.3); ax.tick_params(labelsize=12)

    plt.tight_layout()
    savepath = os.path.join(OUTPUT_DIR, "comparison_1d_h5py_vs_yt.png")
    plt.savefig(savepath, dpi=200, bbox_inches="tight"); plt.close()
    print(f"  图已保存")
    return stats


# ── 2D 对比（使用 (r, z) 坐标，固定 z 线提取对比） ────────────
def compare_2d():
    print("\n" + "=" * 60)
    print("2D 对比: h5py vs yt")
    print("=" * 60)
    hdf5_path = TEST_FILES["2D"]["path"]

    t0 = time.time()
    x_h5, y_h5, d_h5 = extract_with_h5py(hdf5_path, "dens")
    t_h5 = time.time() - t0
    t0 = time.time()
    x_yt, y_yt_, d_yt = extract_with_yt(hdf5_path, ndim=2)
    t_yt = time.time() - t0
    print(f"  h5py: {len(x_h5)} pts, {t_h5:.3f}s")
    print(f"  yt:   {len(x_yt)} pts, {t_yt:.3f}s")

    stats = {"N": len(x_h5), "N_yt": len(x_yt), "match": len(x_h5) == len(x_yt),
              "time_h5": t_h5, "time_yt": t_yt}

    # 检测坐标系统
    ff = FlashHDF5File(hdf5_path)
    cs = ff.coordinate_system
    cl = ff.coord_labels
    ff.close()
    r_label = cl[0]
    z_label = cl[1]

    # 固定 z(轴向) 做线提取对比
    y_unique = np.unique(np.round(y_h5, 10))
    z_fixed = float(y_unique[len(y_unique) // 2])  # 取中间 z 位置
    dz = 1e-10

    # h5py 线提取
    mask_h5 = np.abs(y_h5 - z_fixed) < dz
    r_h5_lo = x_h5[mask_h5]
    d_h5_lo = d_h5[mask_h5]
    si = np.argsort(r_h5_lo)
    r_h5_lo, d_h5_lo = r_h5_lo[si], d_h5_lo[si]
    print(f"  Lineout at {z_label.split('[')[0].strip()}={z_fixed:.4e}: h5py {len(r_h5_lo)} pts, yt {np.sum(np.abs(y_yt_-z_fixed)<dz)} pts")

    # yt 线提取
    mask_yt = np.abs(y_yt_ - z_fixed) < dz
    if np.sum(mask_yt) > 0:
        r_yt_lo = x_yt[mask_yt]
        d_yt_lo = d_yt[mask_yt]
        si = np.argsort(r_yt_lo)
        r_yt_lo, d_yt_lo = r_yt_lo[si], d_yt_lo[si]

        # 对齐 h5py 和 yt 的线（插值到统一 r 坐标）
        r_common = np.union1d(np.round(r_h5_lo, 10), np.round(r_yt_lo, 10))
        r_common.sort()
        d_h5_interp = np.interp(r_common, r_h5_lo, d_h5_lo)
        d_yt_interp = np.interp(r_common, r_yt_lo, d_yt_lo)
        diff = d_h5_interp - d_yt_interp
        rel_diff = diff / np.maximum(np.abs(d_yt_interp), 1e-30)

        stats.update({
            "max_abs_diff": float(np.max(np.abs(diff))),
            "mean_abs_diff": float(np.mean(np.abs(diff))),
            "rmse": float(np.sqrt(np.mean(diff**2))),
            "max_rel_diff": float(np.max(np.abs(rel_diff))),
            "mean_rel_diff": float(np.mean(np.abs(rel_diff))),
        })
        print(f"  Lineout diff: max|diff|={stats['max_abs_diff']:.4e}, mean|diff|={stats['mean_abs_diff']:.4e}")
    else:
        print(f"  ⚠ yt 在 z={z_fixed:.4e} 无数据点")
        r_yt_lo, d_yt_lo = np.array([]), np.array([])

    # 绘图: 2x3 grid
    fig, axes = plt.subplots(2, 3, figsize=(18, 11))

    # (a) h5py (r,z) scatter
    ax = axes[0, 0]
    sc = ax.scatter(x_h5, y_h5, c=d_h5, s=8, cmap="viridis", alpha=0.6)
    plt.colorbar(sc, ax=ax, label="Density [g/cm³]")
    ax.axhline(z_fixed, color="r", ls="--", lw=1, alpha=0.5)
    ax.set_title(f"h5py ({len(x_h5)} pts)", fontweight="bold")
    ax.set_xlabel(r_label); ax.set_ylabel(z_label)

    # (b) yt (r,z) scatter
    ax = axes[0, 1]
    sc = ax.scatter(x_yt, y_yt_, c=d_yt, s=8, cmap="viridis", alpha=0.6)
    plt.colorbar(sc, ax=ax, label="Density [g/cm³]")
    ax.axhline(z_fixed, color="r", ls="--", lw=1, alpha=0.5)
    ax.set_title(f"yt ({len(x_yt)} pts)", fontweight="bold")
    ax.set_xlabel(r_label); ax.set_ylabel(z_label)

    # (c) Lineout 对比
    ax = axes[0, 2]
    ax.plot(r_h5_lo, d_h5_lo, "b-", lw=2, alpha=0.7, label=f"h5py ({len(r_h5_lo)} pts)")
    if len(r_yt_lo) > 0:
        ax.plot(r_yt_lo, d_yt_lo, "r--", lw=1.5, alpha=0.7, label=f"yt ({len(r_yt_lo)} pts)")
    ax.set_xlabel(r_label)
    ax.set_ylabel("Density [g/cm³]")
    ax.set_title(f"Lineout at {z_label.split('[')[0].strip()}={z_fixed:.3e} cm")
    ax.legend(fontsize=11); ax.grid(True, alpha=0.3)

    # (d) 差异
    ax = axes[1, 0]
    if len(r_yt_lo) > 0:
        ax.semilogy(r_common, np.abs(diff), "k.", ms=2, alpha=0.5)
        ax.axhline(stats["mean_abs_diff"], color="r", ls="--", lw=1, label=f"mean = {stats['mean_abs_diff']:.2e}")
        ax.axhline(stats["rmse"], color="orange", ls="--", lw=1, label=f"RMSE = {stats['rmse']:.2e}")
        ax.set_ylabel("|diff| [g/cm³]")
        ax.set_title(f"|diff| along lineout (max={stats['max_abs_diff']:.2e})")
        ax.legend(fontsize=11); ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, "No lineout data", ha="center", va="center")
    ax.set_xlabel(r_label)

    # (e) 密度分布直方图
    ax = axes[1, 1]
    ax.hist(d_h5, bins=80, alpha=0.5, label=f"h5py (N={len(d_h5)})", density=True)
    ax.hist(d_yt, bins=80, alpha=0.5, label=f"yt (N={len(d_yt)})", density=True)
    ax.set_xlabel("Density [g/cm³]")
    ax.set_ylabel("PDF")
    ax.set_title("Density Distribution", fontweight="bold")
    ax.legend(fontsize=10); ax.grid(True, alpha=0.3)

    # (f) 统计信息
    ax = axes[1, 2]
    ax.axis("off")
    info = (f"2D Comparison\n{'='*20}\n"
            f"Points: h5py={len(x_h5)}, yt={len(x_yt)}\n"
            f"Match: {'✓' if stats['match'] else '✗'}\n"
            f"System: {cs}\n"
            f"h5py: {t_h5:.3f}s | yt: {t_yt:.3f}s\n"
            f"Speedup: {t_yt/max(t_h5,1e-6):.0f}x\n"
            f"File: {os.path.basename(hdf5_path)}\n\n"
            f"Lineout at {z_label.split('[')[0].strip()}={z_fixed:.3e}\n"
            f"max|diff|: {stats.get('max_abs_diff', 0):.2e}\n"
            f"mean|diff|: {stats.get('mean_abs_diff', 0):.2e}\n"
            f"max|rel|: {stats.get('max_rel_diff', 0):.2e}")
    ax.text(0.1, 0.95, info, transform=ax.transAxes,
            verticalalignment="top", family="monospace")

    plt.tight_layout()
    savepath = os.path.join(OUTPUT_DIR, "comparison_2d_h5py_vs_yt.png")
    plt.savefig(savepath, dpi=200, bbox_inches="tight"); plt.close()
    print(f"  图已保存")
    return stats


# ── 3D 对比（xOy/yOz 投影 + 轴线提取对比） ──────────────────
def compare_3d():
    print("\n" + "=" * 60)
    print("3D 对比: h5py vs yt")
    print("=" * 60)
    hdf5_path = TEST_FILES["3D"]["path"]

    t0 = time.time()
    x_h5, y_h5, z_h5, d_h5 = extract_with_h5py(hdf5_path, "dens")
    t_h5 = time.time() - t0
    t0 = time.time()
    x_yt, y_yt, z_yt, d_yt = extract_with_yt(hdf5_path, ndim=3)
    t_yt = time.time() - t0
    print(f"  h5py: {len(x_h5)} pts, {t_h5:.3f}s")
    print(f"  yt:   {len(x_yt)} pts, {t_yt:.3f}s")

    stats = {"N": len(x_h5), "N_yt": len(x_yt), "match": len(x_h5) == len(x_yt),
              "time_h5": t_h5, "time_yt": t_yt}

    # 最大投影
    def max_project(data_dict):
        xy_keys = {}
        for xi, yi, di in zip(data_dict["x"], data_dict["y"], data_dict["d"]):
            key = (np.round(xi, 10), np.round(yi, 10))
            if key not in xy_keys or di > xy_keys[key]:
                xy_keys[key] = di
        xs = np.array([k[0] for k in xy_keys.keys()])
        ys = np.array([k[1] for k in xy_keys.keys()])
        ds = np.array(list(xy_keys.values()))
        return xs, ys, ds

    def max_project_yz(data_dict):
        yz_keys = {}
        for yi, zi, di in zip(data_dict["y"], data_dict["z"], data_dict["d"]):
            key = (np.round(yi, 10), np.round(zi, 10))
            if key not in yz_keys or di > yz_keys[key]:
                yz_keys[key] = di
        ys = np.array([k[0] for k in yz_keys.keys()])
        zs = np.array([k[1] for k in yz_keys.keys()])
        ds = np.array(list(yz_keys.values()))
        return ys, zs, ds

    h5_dict = {"x": x_h5, "y": y_h5, "z": z_h5, "d": d_h5}
    yt_dict = {"x": x_yt, "y": y_yt, "z": z_yt, "d": d_yt}

    proj_xoy_h5 = max_project(h5_dict)
    proj_xoy_yt = max_project(yt_dict)
    proj_yoz_h5 = max_project_yz(h5_dict)
    proj_yoz_yt = max_project_yz(yt_dict)
    print(f"  xOy: h5py={len(proj_xoy_h5[0])} pts, yt={len(proj_xoy_yt[0])} pts")
    print(f"  yOz: h5py={len(proj_yoz_h5[0])} pts, yt={len(proj_yoz_yt[0])} pts")

    # 轴线提取: 固定 y=中间值, 沿 x 做线对比
    y_unique = np.unique(np.round(y_h5, 10))
    y_fixed = float(y_unique[len(y_unique) // 2])
    dy = 1e-10
    mask_h5_ax = np.abs(y_h5 - y_fixed) < dy
    r_ax_h5 = x_h5[mask_h5_ax]
    d_ax_h5 = d_h5[mask_h5_ax]
    si = np.argsort(r_ax_h5)
    r_ax_h5, d_ax_h5 = r_ax_h5[si], d_ax_h5[si]
    print(f"  Lineout at y={y_fixed:.4e}: h5py {len(r_ax_h5)} pts")

    mask_yt_ax = np.abs(y_yt - y_fixed) < dy
    if np.sum(mask_yt_ax) > 0:
        r_ax_yt = x_yt[mask_yt_ax]; d_ax_yt = d_yt[mask_yt_ax]
        si = np.argsort(r_ax_yt); r_ax_yt, d_ax_yt = r_ax_yt[si], d_ax_yt[si]
        r_common = np.union1d(np.round(r_ax_h5, 10), np.round(r_ax_yt, 10))
        r_common.sort()
        d_h5_interp = np.interp(r_common, r_ax_h5, d_ax_h5)
        d_yt_interp = np.interp(r_common, r_ax_yt, d_ax_yt)
        diff = d_h5_interp - d_yt_interp
        stats.update({
            "max_abs_diff": float(np.max(np.abs(diff))),
            "mean_abs_diff": float(np.mean(np.abs(diff))),
            "rmse": float(np.sqrt(np.mean(diff**2))),
            "max_rel_diff": float(np.max(np.abs(diff) / np.maximum(np.abs(d_yt_interp), 1e-30))),
        })
        print(f"  Lineout diff: max|diff|={stats['max_abs_diff']:.4e}")
    else:
        r_ax_yt, d_ax_yt = np.array([]), np.array([])

    # 绘图: 2x3
    fig, axes = plt.subplots(2, 3, figsize=(20, 11))

    # (a) xOy h5py, (b) xOy yt
    for idx, (label, x, y, d) in enumerate([
        (f"h5py ({len(proj_xoy_h5[0])} pts)", *proj_xoy_h5),
        (f"yt ({len(proj_xoy_yt[0])} pts)", *proj_xoy_yt),
    ]):
        sc = axes[0, idx].scatter(x, y, c=d, s=10, cmap="viridis", alpha=0.7, edgecolors="none")
        plt.colorbar(sc, ax=axes[0, idx], label="Density [g/cm³]")
        axes[0, idx].set_title(f"xOy {label}", fontweight="bold")
        axes[0, idx].set_xlabel("x [cm]")
        axes[0, idx].set_ylabel("y [cm]")
        axes[0, idx].set_aspect("equal")

    # (c) xOy info
    ax = axes[0, 2]
    ax.axis("off"); ax.text(0.1, 0.7, f"xOy Projection\n\nh5py: {len(proj_xoy_h5[0])} pts\nyt: {len(proj_xoy_yt[0])} pts", family="monospace")

    # (d) yOz h5py, (e) yOz yt
    for idx, (label, y, z, d) in enumerate([
        (f"h5py ({len(proj_yoz_h5[0])} pts)", *proj_yoz_h5),
        (f"yt ({len(proj_yoz_yt[0])} pts)", *proj_yoz_yt),
    ]):
        sc = axes[1, idx].scatter(y, z, c=d, s=10, cmap="viridis", alpha=0.7, edgecolors="none")
        plt.colorbar(sc, ax=axes[1, idx], label="Density [g/cm³]")
        axes[1, idx].set_title(f"yOz {label}", fontweight="bold")
        axes[1, idx].set_xlabel("y [cm]")
        axes[1, idx].set_ylabel("z [cm]")
        axes[1, idx].set_aspect("equal")

    # (f) yOz diff + 轴线对比
    ax = axes[1, 2]
    ax.axis("off")
    info = (f"3D Comparison\n{'='*20}\n"
            f"Full 3D: h5py={len(x_h5)}, yt={len(x_yt)}\n"
            f"Match: {'✓' if stats['match'] else '✗'}\n"
            f"h5py: {t_h5:.3f}s | yt: {t_yt:.3f}s\n"
            f"Speedup: {t_yt/max(t_h5,1e-6):.0f}x\n"
            f"File: {os.path.basename(hdf5_path)}\n\n"
            f"Lineout at y={y_fixed:.4e}\n"
            f"max|diff|: {stats.get('max_abs_diff', 0):.2e}\n"
            f"mean|diff|: {stats.get('mean_abs_diff', 0):.2e}")
    ax.text(0.1, 0.95, info, transform=ax.transAxes,
            verticalalignment="top", family="monospace")

    plt.tight_layout()
    savepath = os.path.join(OUTPUT_DIR, "comparison_3d_h5py_vs_yt.png")
    plt.savefig(savepath, dpi=200, bbox_inches="tight"); plt.close()
    print(f"  图已保存")
    print(f"  Full 3D match: {'✓' if stats['match'] else '✗'} ({len(x_h5)} vs {len(x_yt)})")
    return stats


def print_summary(all_stats):
    print("\n" + "=" * 80)
    print("差异对比摘要（晚时间文件）")
    print("=" * 80)
    print(f"{'Dim':<6} {'N(h5py)':<10} {'N(yt)':<10} {'Match':<8} "
          f"{'max|diff|':<14} {'mean|diff|':<14} {'RMSE':<14} "
          f"{'max|rel|':<14} {'t_h5[s]':<8} {'t_yt[s]':<8} {'Speedup':<8}")
    print("-" * 110)
    for dim, s in all_stats.items():
        match_str = "✓" if s["match"] else f"✗"
        speedup = f"{s['time_yt']/max(s['time_h5'],1e-6):.0f}x" if "time_h5" in s and "time_yt" in s else "-"
        print(f"{dim:<6} {s['N']:<10} {s['N_yt']:<10} {match_str:<8} "
              f"{s.get('max_abs_diff', 0):<14.4e} {s.get('mean_abs_diff', 0):<14.4e} "
              f"{s.get('rmse', 0):<14.4e} {s.get('max_rel_diff', 0):<14.4e} "
              f"{s['time_h5']:<8.3f} {s['time_yt']:<8.3f} {speedup:<8}")


if __name__ == "__main__":
    print("#" * 60)
    print("# 纯 h5py vs yt: FLASH AMR 晚时间数据对比")
    print("# 坐标系统: 自动检测 (Cartesian/Cylindrical)")
    print("# 3D: xOy + yOz 最大投影对比")
    print("#" * 60)

    all_stats = {}
    all_stats["1D"] = compare_1d()
    all_stats["2D"] = compare_2d()
    all_stats["3D"] = compare_3d()
    print_summary(all_stats)
    print(f"\n所有对比图已保存至: {OUTPUT_DIR}/")
