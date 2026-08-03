"""
FLASH NewPara — 密度网格分析脚本 (独立版 v3)
══════════════════════════════════════════
FLASH 1D plot文件：用 bbox 重构 x 坐标。
"""

import sys, os
import h5py
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
from pathlib import Path

TEST_DIR = Path(__file__).parent
OUTPUT_DIR = TEST_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print(" FLASH NewPara — 密度网格分析 v3")
print("=" * 65)


def read_plot_h5(path):
    """读取 FLASH 1D plot HDF5，用 bbox 重建 x 坐标。"""
    with h5py.File(str(path), "r") as f:
        keys = list(f.keys())
        dens_data = f["dens"][:]  # (nblocks, 1, 1, NXB)
        bbox = f["bounding box"][:]  # (nblocks, 3, 2)
        nblocks = bbox.shape[0]
        nx = dens_data.shape[3]

        all_x = []
        all_d = []
        species_data = {}

        for b in range(nblocks):
            xmin = bbox[b, 0, 0]
            xmax = bbox[b, 0, 1]
            dx = (xmax - xmin) / nx
            x_center = np.linspace(xmin + dx / 2, xmax - dx / 2, nx)
            block_dens = dens_data[b, 0, 0, :]
            all_x.append(x_center)
            all_d.append(block_dens)

            for sp in ["cham", "targ", "poly"]:
                if sp in keys:
                    if sp not in species_data:
                        species_data[sp] = []
                    species_data[sp].append(f[sp][b, 0, 0, :])

        x_arr = np.concatenate(all_x)
        d_arr = np.concatenate(all_d)

        # Sort by x
        idx = np.argsort(x_arr)
        x_sorted = x_arr[idx]
        d_sorted = d_arr[idx]

        sp_sorted = {}
        for sp, arr_list in species_data.items():
            sp_arr = np.concatenate(arr_list)[idx]
            sp_sorted[sp] = sp_arr

        return x_sorted, d_sorted, sp_sorted


# ── 1. 初始密度 ──
plt_initial = sorted(OUTPUT_DIR.glob("lasslab_hdf5_plt_cnt_0000*"))
if plt_initial:
    print(f"\n[1/3] 初始密度: {plt_initial[0].name}")
    x0, d0, sp0 = read_plot_h5(plt_initial[0])
    print(f"  x 范围: [{x0.min():.6e}, {x0.max():.6e}] cm = [{x0.min()*1e4:.2f}, {x0.max()*1e4:.2f}] μm")
    print(f"  密度范围: [{d0.min():.4e}, {d0.max():.4f}] g/cm³")

    # 验证三区
    vac = d0[x0 < 0.014]
    targ = d0[(x0 >= 0.014) & (x0 < 0.016)]
    poly = d0[x0 >= 0.016]
    print(f"  真空: mean={vac.mean():.4e}, n={len(vac)}")
    print(f"  铝靶: mean={targ.mean():.4f}, n={len(targ)}")
    print(f"  CH靶: mean={poly.mean():.4f}, n={len(poly)}")

    if abs(targ.mean() - 2.7) < 0.1 and abs(poly.mean() - 1.0) < 0.1:
        print("  ✅ 三区验证通过!")
    else:
        print("  ⚠️ 三区验证异常")

    # 图1: 密度 + 物种
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    ax1.plot(x0 * 1e4, d0, "b-", lw=1.5)
    ax1.axvline(140, color="orange", ls="--", alpha=0.7, label="vac→targ")
    ax1.axvline(160, color="purple", ls="--", alpha=0.7, label="targ→poly")
    ax1.set_xlabel("x (um)"); ax1.set_ylabel("Density (g/cm^3)")
    ax1.set_title("Initial Density — NewPara Multi-Zone")
    ax1.legend(); ax1.grid(True, alpha=0.3)

    for sp_name, sp_arr in sp0.items():
        ax2.plot(x0 * 1e4, sp_arr, label=sp_name, lw=1.5)
    ax2.set_xlabel("x (um)"); ax2.set_ylabel("Mass Fraction")
    ax2.set_title("Species Mass Fractions (Initial)")
    ax2.legend(); ax2.grid(True, alpha=0.3)

    fig.savefig(str(PLOTS_DIR / "dens_initial_profile.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK initial density plot")

    # 图2: 三区标注图
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x0 * 1e4, d0, "g-", lw=2)
    ax.axvline(140, color="orange", ls="--", alpha=0.7, label="vac→targ")
    ax.axvline(160, color="purple", ls="--", alpha=0.7, label="targ→poly")
    ax.fill_between([x0.min()*1e4, 140], 0, 3, alpha=0.08, color="blue", label="vacuum (He)")
    ax.fill_between([140, 160], 0, 3, alpha=0.08, color="red", label="Al target (rho=2.7)")
    ax.fill_between([160, x0.max()*1e4], 0, 3, alpha=0.08, color="green", label="CH target (poly rho=1.0)")
    ax.set_xlabel("x (um)"); ax.set_ylabel("Density (g/cm^3)")
    ax.set_title("Initial Density - Three-Zone Structure (Parameterized)")
    ax.legend(); ax.grid(True, alpha=0.3)
    ax.set_ylim(-0.1, 3.1)
    fig.savefig(str(PLOTS_DIR / "dens_zones_validation.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK three-zone validation plot")

# ── 2. 最终密度 ──
plt_final = sorted(OUTPUT_DIR.glob("lasslab_hdf5_plt_cnt_0308*"))
if plt_final:
    print(f"\n[2/3] 最终密度: {plt_final[0].name}")
    x1, d1, sp1 = read_plot_h5(plt_final[0])
    print(f"  密度范围: [{d1.min():.4e}, {d1.max():.4f}] g/cm³")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x1 * 1e4, d1, "r-", lw=1.5)
    ax.axvline(140, color="gray", ls="--", alpha=0.5)
    ax.axvline(160, color="gray", ls="--", alpha=0.5)
    ax.set_xlabel("x (um)"); ax.set_ylabel("Density (g/cm^3)")
    ax.set_title("Final Density — NewPara Multi-Zone (t=2ns)")
    ax.grid(True, alpha=0.3)
    fig.savefig(str(PLOTS_DIR / "dens_final_profile.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ 最终密度图")

# ── 3. 初始 vs 最终对比 ──
if plt_initial and plt_final:
    print(f"\n[3/3] 初始 vs 最终对比")
    x0, d0, _ = read_plot_h5(plt_initial[0])
    x1, d1, _ = read_plot_h5(plt_final[0])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x0 * 1e4, d0, "b-", lw=1.5, alpha=0.7, label="t=0 (初始)")
    ax.plot(x1 * 1e4, d1, "r-", lw=1.5, alpha=0.7, label="t=2ns (最终)")
    ax.axvline(140, color="gray", ls="--", alpha=0.3)
    ax.axvline(160, color="gray", ls="--", alpha=0.3)
    ax.set_xlabel("x (um)"); ax.set_ylabel("Density (g/cm^3)")
    ax.set_title("Density Evolution — NewPara Multi-Zone")
    ax.legend(); ax.grid(True, alpha=0.3)
    ax.set_yscale("log")
    fig.savefig(str(PLOTS_DIR / "dens_evolution_comparison.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK evolution comparison plot")

print(f"\n✅ 分析完成! 所有图像: {PLOTS_DIR}")
