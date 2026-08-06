#!/usr/bin/env python3
"""
FLASH 1D LaserSlab 密度场 (dens) 时空分布分析脚本
=====================================================
读取 FLASH 仿真输出的 HDF5 checkpoint 文件，提取密度场 dens，
绘制各时间步 density vs x 分布曲线并保存。

FLASH checkpoint HDF5 文件内部结构:
  / "unknown names"  — 变量名列表 (4字符/变量), shape: (nvars,)
  / "coordinates"    — block 中心坐标, shape: (nblocks, ndim)
  / "block size"     — block 物理尺寸, shape: (nblocks, ndim)
  / "bounding box"   — block 边界框, shape: (nblocks, ndim, 2) [min, max]
  / "node type"      — 1=叶节点(leaf), 2=父节点
  / "refine level"   — AMR 细化层级, shape: (nblocks,)
  / "unk"            — 流体变量数据, shape: (nblocks, nvars, nzb, nyb, nxb)
  / "integer scalars"— 整型标量 [nstep, ...]
  / "real scalars"   — 浮点标量 [time, dt, ...]

依赖: h5py, numpy, matplotlib
安装: pip install h5py numpy matplotlib
"""

import os
import sys
import glob
import warnings
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ── PPT 友好绘图规范 (字体≥18, 全英文) ──
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))
try:
    from output_processors.plotter.plot_style import apply_plot_style, english
    apply_plot_style()   # 全局: 字体≥18, 全英文, dpi=200
except ImportError:
    pass  # plot_style 不可用时保持原行为

# 尝试导入 h5py
try:
    import h5py
except ImportError:
    print("错误: 需要安装 h5py 库")
    print("  运行: pip install h5py numpy matplotlib")
    sys.exit(1)

warnings.filterwarnings("ignore", category=UserWarning)


# ============================================================
# Configuration
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
# Source suffix: "" for local WSL, "from_ssh1" or "from_ssh2" for remote
SOURCE_SUFFIX = os.environ.get("FLASH_SOURCE_SUFFIX", "")
# HDF5 checkpoint file directory
INPUT_DIR = SCRIPT_DIR / "outputfiles" / f"hdf5files{SOURCE_SUFFIX}" / "laserslab1d"
# Analysis plot output directory
OUTPUT_DIR = SCRIPT_DIR / "outputfiles" / f"plots{SOURCE_SUFFIX}"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIELD_NAME = "dens"
CHK_PATTERN = "*hdf5_chk_*"
MAX_BLOCKS_PLOT = 200   # max blocks to plot in 1D


# ============================================================
# 辅助函数
# ============================================================

def scan_checkpoint_files(input_dir, pattern="*hdf5_chk_*"):
    """扫描 inputfiles 目录, 返回按编号排序的 checkpoint 文件列表"""
    pattern_full = os.path.join(input_dir, pattern)
    files = sorted(glob.glob(pattern_full))
    if not files:
        # 也尝试 *.h5 和 *chk* 模式
        for alt in ["*chk*", "*.h5"]:
            files = sorted(glob.glob(os.path.join(input_dir, alt)))
            if files:
                break
    return files


def read_flash_chk_info(filepath):
    """读取 FLASH checkpoint 文件的基本信息（变量名、时间、步数、block 信息）"""
    with h5py.File(filepath, "r") as f:
        # 变量名
        unk_names_raw = f["unknown names"][:]
        if isinstance(unk_names_raw[0], (bytes, np.bytes_)):
            var_names = [n.decode("utf-8").strip().replace("\x00", "") for n in unk_names_raw]
        else:
            var_names = [str(n).strip() for n in unk_names_raw]

        # 标量: real scalars / integer scalars 是结构化数组
        # dtype: {'names': ['name', 'value'], 'formats': ['S80', '<f4'/'<f8'], ...}
        rs = f["real scalars"]
        isc = f["integer scalars"]
        # real scalars: [time, dt, dtold, tmax, ...]
        time = float(rs["value"][0])
        # integer scalars: [nstep, nbegin, ...]
        nstep = int(isc["value"][0])

        # block 信息
        node_type = f["node type"][:]
        bbox = f["bounding box"][:]       # (nblocks, ndim, 2)
        refine_level = f["refine level"][:]
        nblocks = len(node_type)
        ndim = bbox.shape[1]

        return {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "var_names": var_names,
            "time": time,
            "nstep": nstep,
            "node_type": node_type,
            "bbox": bbox,
            "refine_level": refine_level,
            "nblocks": nblocks,
            "ndim": ndim,
        }


def extract_1d_density(filepath, info):
    """从 1D FLASH checkpoint 文件中提取密度场的 (x, dens) 数据 (仅叶节点)
    
    注意: FLASH checkpoint 文件中每个变量是单独的 HDF5 dataset
    (如 dens, velx, temp 等), 而不是合并的 unk 数组.
    每个变量 shape: (nblocks, nzb, nyb, nxb) = (nblocks, 1, 1, nxb)
    """
    with h5py.File(filepath, "r") as f:
        # 检查 dens 变量是否存在 (作为独立 dataset 或 unknown_names 中)
        if FIELD_NAME not in f:
            # 尝试模糊匹配
            matches = [k for k in f.keys() if FIELD_NAME in k.lower()
                       and isinstance(f[k], h5py.Dataset)
                       and len(f[k].shape) >= 4]
            if not matches:
                raise ValueError(f"文件 {info['filename']} 中未找到字段 '{FIELD_NAME}'。"
                                 f"可用变量: {info['var_names']}")
            dens_key = matches[0]
        else:
            dens_key = FIELD_NAME

        nblocks = info["nblocks"]
        bbox = info["bbox"]
        node_type = info["node_type"]

        # dens 数据: shape (nblocks, 1, 1, nxb)
        dens_data = f[dens_key][:]
        nxb = dens_data.shape[-1]

        # 收集叶节点数据
        x_all = []
        dens_all = []

        for ib in range(nblocks):
            if node_type[ib] != 1:  # 只取叶节点
                continue

            # 该 block 在 x 方向的 cell 中心坐标
            xmin, xmax = bbox[ib, 0, 0], bbox[ib, 0, 1]
            x_cells = np.linspace(xmin, xmax, nxb, endpoint=False) \
                      + (xmax - xmin) / (2 * nxb)   # cell 中心

            # dens 数据: dens_data[ib, 0(z), 0(y), :(x)]
            dens_block = dens_data[ib, 0, 0, :]

            x_all.append(x_cells)
            dens_all.append(dens_block)

        if not x_all:
            raise RuntimeError(f"文件 {info['filename']} 中没有叶节点数据")

        x_all = np.concatenate(x_all)
        dens_all = np.concatenate(dens_all)

        # 按 x 排序 (AMR 不同 block 可能乱序)
        sort_idx = np.argsort(x_all)
        x_all = x_all[sort_idx]
        dens_all = dens_all[sort_idx]

        return x_all, dens_all


def plot_density_evolution(all_data, output_dir, field_name="dens"):
    """绘制密度场随时间的空间分布变化图"""
    if not all_data:
        print("没有数据可绘制")
        return

    # --- 使用 viridis 色带映射时间 ---
    times = np.array([d["time"] for d in all_data])
    norm = plt.Normalize(times.min(), times.max())
    cmap = plt.cm.viridis

    # --- 图 1: Density vs spatial position (one line per timestep) ---
    fig1, ax1 = plt.subplots(figsize=(14, 7))

    for i, d in enumerate(all_data):
        t = d["time"]
        color = cmap(norm(t))
        ax1.plot(
            d["x"] * 1e6,          # convert to micrometers
            d["dens"],
            color=color,
            linewidth=0.8,
            alpha=0.85,
            label=f"t={t*1e12:.3f} ps"
        )

    ax1.set_xlabel("x (um)")
    ax1.set_ylabel(f"{field_name} (g/cm^3)")
    ax1.set_title(
        f"FLASH 1D LaserSlab -- {field_name} Spatial Evolution\n"
        f"{len(all_data)} timesteps"
    )
    ax1.set_yscale("log")
    ax1.grid(True, alpha=0.3, linestyle="--")

    # colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig1.colorbar(sm, ax=ax1, aspect=50, pad=0.02)
    cbar.set_label("Time (s)")

    # 图例只显示前 8 条和最后一条
    if len(all_data) > 10:
        handles, labels = ax1.get_legend_handles_labels()
        selected_idx = list(range(0, len(all_data), max(1, len(all_data)//8)))
        if len(all_data)-1 not in selected_idx:
            selected_idx.append(len(all_data)-1)
        ax1.legend(
            [handles[j] for j in selected_idx],
            [labels[j] for j in selected_idx], loc="upper right", ncol=2
        )
    else:
        ax1.legend(loc="upper right", ncol=2)

    path1 = os.path.join(output_dir, "density_vs_x_evolution.png")
    fig1.savefig(path1, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig1)
    print(f"  ✓ 保存: {path1}")

    # --- Figure 2: Density time evolution (fixed x slice) ---
    fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(16, 6))

    # 2a: Full-region pseudocolor (x-t density spectrum)
    if len(all_data) >= 2:
        # Find common x grid
        x_ref = all_data[0]["x"]
        dens_matrix = np.zeros((len(all_data), len(x_ref)))
        for i, d in enumerate(all_data):
            # Interpolate to common grid
            dens_matrix[i, :] = np.interp(x_ref, d["x"], d["dens"])

        xx, tt = np.meshgrid(x_ref * 1e6, times * 1e12)  # um, ps
        im = ax2a.pcolormesh(xx, tt, np.log10(dens_matrix), shading="auto", cmap="inferno")
        ax2a.set_xlabel("x (um)")
        ax2a.set_ylabel("Time (ps)")
        ax2a.set_title(f"log10({field_name}) x-t Spectrum")
        cbar2 = fig2.colorbar(im, ax=ax2a, aspect=40, pad=0.02)
        cbar2.set_label(f"log10({field_name})")

    # 2b: Max and mean density evolution over time
    max_dens = np.array([d["dens"].max() for d in all_data])
    mean_dens = np.array([d["dens"].mean() for d in all_data])

    ax2b.plot(times * 1e12, max_dens, "o-", color="#E74C3C", linewidth=1.2,
              markersize=4, label="max(dens)", alpha=0.8)
    ax2b.plot(times * 1e12, mean_dens, "s-", color="#3498DB", linewidth=1.2,
              markersize=4, label="mean(dens)", alpha=0.8)
    ax2b.set_xlabel("Time (ps)")
    ax2b.set_ylabel(f"{field_name} (g/cm^3)")
    ax2b.set_title("Density Statistics Evolution")
    ax2b.set_yscale("log")
    ax2b.legend()
    ax2b.grid(True, alpha=0.3, linestyle="--")

    path2 = os.path.join(output_dir, "density_heatmap_and_stats.png")
    fig2.savefig(path2, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig2)
    print(f"  ✓ 保存: {path2}")

    # --- Figure 3: Key snapshots comparison (first/middle/last) ---
    fig3, ax3 = plt.subplots(figsize=(12, 7))

    snap_indices = [0, len(all_data)//2, len(all_data)-1]
    # Deduplicate
    snap_indices = sorted(set(max(0, min(len(all_data)-1, i)) for i in snap_indices))
    colors_snap = ["#3498DB", "#F39C12", "#E74C3C"]  # blue/orange/red
    labels_snap = ["Initial", "Middle", "Final"]

    for j, (idx, c, lbl) in enumerate(zip(snap_indices, colors_snap, labels_snap)):
        d = all_data[idx]
        ax3.plot(d["x"] * 1e6, d["dens"], color=c, linewidth=1.5,
                 label=f"{lbl}: t={d['time']*1e12:.3f} ps")

    ax3.set_xlabel("x (um)")
    ax3.set_ylabel(f"{field_name} (g/cm^3)")
    ax3.set_title(f"FLASH 1D LaserSlab -- {field_name} Snapshots")
    ax3.set_yscale("log")
    ax3.legend(loc="upper right")
    ax3.grid(True, alpha=0.3, linestyle="--")

    path3 = os.path.join(output_dir, "density_snapshots.png")
    fig3.savefig(path3, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig3)
    print(f"  ✓ 保存: {path3}")

    return [path1, path2, path3]


def print_hdf5_structure(filepath, max_depth=3):
    """打印 HDF5 文件的内部组织结构 (调试用)"""
    def _print_group(name, obj, depth=0, prefix=""):
        indent = "  " * depth
        if isinstance(obj, h5py.Group):
            print(f"{indent}[Group] {name}/")
        elif isinstance(obj, h5py.Dataset):
            print(f"{indent}[Dataset] {name}  shape={obj.shape}  dtype={obj.dtype}")

    print(f"\n{'='*60}")
    print(f"HDF5 文件结构: {os.path.basename(filepath)}")
    print(f"{'='*60}")
    with h5py.File(filepath, "r") as f:
        f.visititems(_print_group)
    print(f"{'='*60}\n")


# ============================================================
# 主流程
# ============================================================

def main():
    source_label = SOURCE_SUFFIX.replace("from_", " (") + ")" if SOURCE_SUFFIX else " (local WSL)"
    print("=" * 60)
    print(f"  FLASH 1D LaserSlab -- Density Spatiotemporal Analysis{source_label}")
    print("=" * 60)
    print(f"Input dir:  {INPUT_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")
    print()

    # 1. 扫描 checkpoint 文件
    chk_files = scan_checkpoint_files(INPUT_DIR, CHK_PATTERN)
    if not chk_files:
        print(f"错误: 在 {INPUT_DIR} 中未找到任何 checkpoint 文件 (*chk*)")
        print("请先运行 run_flash.sh 生成仿真数据")
        sys.exit(1)

    print(f"找到 {len(chk_files)} 个 checkpoint 文件:")
    for f in chk_files:
        print(f"  - {os.path.basename(f)}")
    print()

    # 2. 打印第一个文件的结构 (帮助理解数据组织)
    print_hdf5_structure(chk_files[0])

    # 3. 逐个读取并提取密度场
    print(f"读取并提取 '{FIELD_NAME}' 字段...")
    all_data = []

    for i, fp in enumerate(chk_files):
        fname = os.path.basename(fp)
        try:
            info = read_flash_chk_info(fp)
            x, dens = extract_1d_density(fp, info)

            all_data.append({
                "filename": fname,
                "time": info["time"],
                "nstep": info["nstep"],
                "nblocks": info["nblocks"],
                "x": x,
                "dens": dens,
            })
            print(f"  [{i+1}/{len(chk_files)}] {fname}  "
                  f"t={info['time']*1e12:.4f} ps  "
                  f"nstep={info['nstep']}  "
                  f"x=[{x.min()*1e6:.2f}, {x.max()*1e6:.2f}] μm  "
                  f"dens=[{dens.min():.2e}, {dens.max():.2e}] g/cm³  "
                  f"cells={len(x)}")
        except Exception as e:
            print(f"  [{i+1}/{len(chk_files)}] {fname}  错误: {e}")
            continue

    if not all_data:
        print("错误: 未能成功读取任何 checkpoint 文件")
        sys.exit(1)

    # 按时间排序
    all_data.sort(key=lambda d: d["time"])
    print(f"\n成功读取 {len(all_data)} 个时间步的数据\n")

    # 4. 绘图并保存
    print("绘制密度场时空演化图...")
    output_files = plot_density_evolution(all_data, OUTPUT_DIR, FIELD_NAME)

    # 5. 摘要
    t_span = all_data[-1]["time"] - all_data[0]["time"]
    print(f"\n{'='*60}")
    print(f"  分析完成!")
    print(f"  时间范围: {all_data[0]['time']*1e12:.3f} ~ {all_data[-1]['time']*1e12:.3f} ps")
    print(f"  时间跨度: {t_span*1e12:.3f} ps")
    print(f"  时间步数: {len(all_data)}")
    print(f"  输出图片: {len(output_files)} 张 (位于 {OUTPUT_DIR}/)")
    print(f"{'='*60}")
    print()

    return output_files


if __name__ == "__main__":
    main()
