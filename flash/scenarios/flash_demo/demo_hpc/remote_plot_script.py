#!/usr/bin/env python3
"""
FLASH HDF5 输出文件超算端绘图脚本
在超算上直接运行，生成图片，避免下载大量 HDF5 原始文件

依赖: h5py, numpy, matplotlib (超算 python/3.9.6 模块均提供)
用法:
  module load python/3.9.6
  python remote_plot_script.py --input_dir /path/to/outputfiles --output_dir /path/to/plots
"""

import sys
import os
import argparse
import numpy as np

# 强制设置 matplotlib 非交互后端（必须在 import matplotlib 之前）
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# ── PPT-friendly plot style (fonts >= 18, English only) ──
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass
import matplotlib.colors as mcolors


def check_dependencies():
    """检查必要依赖是否在超算上可用"""
    missing = []
    try:
        import h5py
        print(f"[INFO] h5py version: {h5py.__version__}")
    except ImportError as e:
        missing.append(f"h5py: {e}")
    try:
        import matplotlib
        print(f"[INFO] matplotlib version: {matplotlib.__version__}")
    except ImportError as e:
        missing.append(f"matplotlib: {e}")
    try:
        import numpy
        print(f"[INFO] numpy version: {numpy.__version__}")
    except ImportError as e:
        missing.append(f"numpy: {e}")
    if missing:
        print("[ERROR] 缺少依赖:")
        for m in missing:
            print(f"  - {m}")
        print("[HINT] 请确保已运行: module load python/3.9.6")
        return False
    return True


def find_hdf5_files(directory: str, pattern: str = "hdf5_plt_cnt_") -> list:
    """查找目录中的 HDF5 文件，按文件名排序
    
    FLASH 输出文件不一定有 .h5 扩展名，所以只凭 pattern 匹配
    同时打印目录内容以便调试
    """
    files = []
    try:
        all_items = os.listdir(directory)
        # 调试：打印目录内容（最多15个）
        print(f"  [DEBUG] 目录内容（共 {len(all_items)} 项，显示前15个）:")
        for item in sorted(all_items)[:15]:
            full = os.path.join(directory, item)
            if os.path.isdir(full):
                print(f"    [DIR]  {item}/")
            else:
                print(f"    [FILE] {item}")
        if len(all_items) > 15:
            print(f"    ... 还有 {len(all_items)-15} 项未显示")
        
        for f in all_items:
            if pattern in f:
                full_path = os.path.join(directory, f)
                if os.path.isfile(full_path):
                    files.append(full_path)
    except Exception as e:
        print(f"[WARN] 无法读取目录 {directory}: {e}")
        return []
    files.sort()
    print(f"  [DEBUG] 找到 {len(files)} 个匹配 '{pattern}' 的文件")
    return files


def read_time_from_hdf5(f) -> float:
    """
    从 FLASH HDF5 文件中读取时间
    FLASH 4.8 时间存储位置（按优先级）：
    1. 根组属性: current_time
    2. 根组属性: time
    3. 数据集: time, Time
    4. real scalars compound dataset (遍历 name 字段匹配 "time")
    """
    time = None
    
    # 方法1: 根组属性 current_time（FLASH 标准位置）
    if "current_time" in f.attrs:
        try:
            time = float(f.attrs["current_time"])
            return time
        except Exception:
            pass
    
    # 方法2: 根组属性 time
    if time is None and "time" in f.attrs:
        try:
            time = float(f.attrs["time"])
            return time
        except Exception:
            pass
    
    # 方法3: 根组数据集
    if time is None:
        for key in ["time", "Time", "t_step", "time_n"]:
            if key in f:
                try:
                    time = float(f[key][()])
                    return time
                except Exception:
                    pass
    
    # 方法4: real scalars compound dataset
    if time is None and "real scalars" in f:
        try:
            rs = f["real scalars"]
            # real scalars 是 1D compound array，每个元素有 (name, value)
            # name 是长度为80的字符串（S80），value 是 float64
            for row in rs:
                name_raw = row[0]  # name 字段
                if isinstance(name_raw, bytes):
                    name_str = name_raw.decode('utf-8', errors='replace').strip().lower()
                else:
                    name_str = str(name_raw).strip().lower()
                if "time" in name_str and "timestep" not in name_str:
                    time = float(row[1])  # value 字段
                    return time
        except Exception as e:
            print(f"  [DEBUG] 从 real scalars 读取时间失败: {e}")
    
    return time


def read_flash_1d_data(filepaths: list) -> dict:
    """
    读取 FLASH 1D HDF5 plot 文件，返回时序数据
    使用单元格中心坐标与 AMR 块拼合算法（同 plot_dens_easy_hpc.py）。

    FLASH 4.8 格式:
    - 所有数据集在根组
    - 物理量形状: (nblocks, Nz, Ny, Nx) (C/h5py 顺序)
    - bounding box: (nblocks, 3, 2), 1D: bbox[:, 0, :] = xmin, xmax
    - 时间: current_time 属性 或 real scalars compound dataset
    """
    import h5py

    times = []
    dens_all_time = []   # list of 1D arrays
    x_common = None

    for i, fpath in enumerate(filepaths):
        try:
            with h5py.File(fpath, 'r') as f:
                # ---- 读取时间 ----
                time = read_time_from_hdf5(f)
                if time is None:
                    print(f"  [WARN] {os.path.basename(fpath)} 无时间信息，跳过")
                    continue
                if abs(time) < 1e-15:
                    continue   # 跳过初始时刻
                times.append(time)

                # ---- 读取密度数据 ----
                dens_raw = None
                if "dens" in f:
                    dens_raw = f["dens"][:]  # (nblocks, 1, 1, nx)

                if dens_raw is None and "unknown names" in f:
                    # 通过 unknown names 映射查找 dens
                    try:
                        raw_names = f["unknown names"][:]
                        name_list = []
                        for n in raw_names:
                            if isinstance(n, bytes):
                                name_list.append(n.decode('utf-8', errors='replace').strip())
                            elif isinstance(n, str):
                                name_list.append(n.strip())
                            else:
                                try:
                                    nm = n[0] if hasattr(n, '__getitem__') else str(n)
                                    if isinstance(nm, bytes):
                                        nm = nm.decode('utf-8', errors='replace').strip()
                                    name_list.append(str(nm).strip())
                                except:
                                    name_list.append(str(n).strip())
                        if "dens" in name_list:
                            dens_idx = name_list.index("dens")
                            ds_name = f"var_{dens_idx+1:04d}"
                            if ds_name in f:
                                dens_raw = f[ds_name][:]
                    except:
                        pass

                if dens_raw is None:
                    if i < 5:
                        print(f"  [INFO] {os.path.basename(fpath)} 可用数据集（前30个）:")
                        for k in list(f.keys())[:30]:
                            print(f"    {k}: {f[k].shape if hasattr(f[k], 'shape') else type(f[k])}")
                    print(f"  [WARN] {os.path.basename(fpath)} 未找到 dens 数据，跳过")
                    continue

                # ---- 单元格中心坐标重建 + AMR 块拼合 ----
                bbox = f["bounding box"][:dens_raw.shape[0]]  # (nblocks, 3, 2)
                nblocks, nz, ny, nx = dens_raw.shape
                dense = dens_raw[:, 0, 0, :]  # (nblocks, nx)

                x_list = []
                d_list = []
                for b in range(nblocks):
                    xmin = float(bbox[b, 0, 0])
                    xmax = float(bbox[b, 0, 1])
                    dx = (xmax - xmin) / nx
                    xs = np.linspace(xmin + dx / 2, xmax - dx / 2, nx)
                    x_list.append(xs)
                    d_list.append(dense[b, :])

                x_all = np.concatenate(x_list)
                d_all = np.concatenate(d_list)

                # 排序 + 去重（与 plot_dens_easy_hpc.py 一致）
                idx = np.argsort(x_all, kind="mergesort")
                x_sorted = x_all[idx]
                d_sorted = d_all[idx]
                unique_x, inverse = np.unique(x_sorted, return_inverse=True)
                if len(unique_x) < len(x_sorted):
                    d_unique = np.zeros_like(unique_x)
                    np.add.at(d_unique, inverse, d_sorted)
                    counts = np.bincount(inverse)
                    d_unique /= counts
                    x_coords = unique_x
                    dens_profile = d_unique
                else:
                    x_coords = x_sorted
                    dens_profile = d_sorted

                # 插值到公共网格（所有时间点使用相同 x 坐标）
                if x_common is None:
                    x_common = np.linspace(x_coords[0], x_coords[-1], 200)
                dens_interp = np.interp(x_common, x_coords, dens_profile)
                dens_all_time.append(dens_interp)

                if (i + 1) % 20 == 0:
                    print(f"  [INFO] 已处理 {i+1}/{len(filepaths)} 个文件...")

        except Exception as e:
            print(f"  [ERROR] 处理 {os.path.basename(fpath)} 失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    if len(times) == 0:
        print("[ERROR] 没有成功读取任何数据")
        return {}

    return {
        "times": np.array(times),
        "dens_profiles": np.array(dens_all_time),
        "x_common": x_common,
    }


def plot_on_supercomputer(input_dir: str, output_dir: str):
    """在超算上读取 HDF5 文件并生成图片"""
    print(f"\n[RemotePlot] 开始处理:")
    print(f"  输入目录: {input_dir}")
    print(f"  输出目录: {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    # 查找 plot 文件
    plot_files = find_hdf5_files(input_dir, "hdf5_plt_cnt_")
    
    # 如果没找到，尝试放宽条件
    if not plot_files:
        print("[WARN] 未找到 hdf5_plt_cnt_ 文件，尝试查找包含 'plt' 的文件...")
        plot_files = find_hdf5_files(input_dir, "plt")
    
    if not plot_files:
        print(f"[ERROR] 在 {input_dir} 中未找到任何 plot 文件")
        print(f"[ERROR] 请检查输入目录路径是否正确")
        # 尝试列出父目录
        parent = os.path.dirname(input_dir.rstrip('/'))
        if parent and os.path.isdir(parent):
            print(f"[DEBUG] 父目录 {parent} 内容:")
            for item in sorted(os.listdir(parent))[:20]:
                print(f"    {item}")
        return False

    print(f"[RemotePlot] 找到 {len(plot_files)} 个 plot 文件")

    data = read_flash_1d_data(plot_files)
    if not data:
        print("[ERROR] 数据读取失败")
        return False

    times = data["times"]
    dens_profiles = data["dens_profiles"]
    x_common = data["x_common"]

    print(f"[RemotePlot] 数据读取完成: {len(times)} 个时间步")
    print(f"  时间范围: {times[0]:.2e} - {times[-1]:.2e} s ({times[0]*1e9:.4f} - {times[-1]*1e9:.4f} ns)")

    dens_center = dens_profiles[:, len(x_common) // 2]
    times_ns = times * 1e9

    plot_files_generated = []

    # 图1: 中心位置密度随时间变化
    print("[RemotePlot] 生成图1: 中心密度随时间变化...")
    plt.figure(figsize=(10, 6))
    plt.plot(times_ns, dens_center, 'b-', linewidth=2)
    plt.xlabel('Time (ns)')
    plt.ylabel('Density (g/cm^3)')
    plt.title('Density at Center vs Time')
    plt.grid(True, alpha=0.3)
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    plt.tight_layout()
    p = os.path.join(output_dir, 'dens_vs_time_center.png')
    plt.savefig(p, dpi=200)
    plt.close()
    print(f"  ✓ 已保存: {p}")
    plot_files_generated.append(p)

    # 图2: 密度演化 2D 热图
    print("[RemotePlot] 生成图2: 密度演化2D热图...")
    if len(times_ns) > 1 and dens_profiles.max() > 0:
        plt.figure(figsize=(12, 6))
        vmin = max(dens_profiles.min(), 1e-30)
        vmax = dens_profiles.max()
        try:
            im = plt.imshow(dens_profiles, aspect='auto', origin='lower',
                            extent=[x_common[0]*100, x_common[-1]*100, times_ns[0], times_ns[-1]],
                            cmap='hot',
                            norm=mcolors.LogNorm(vmin=vmin, vmax=vmax))
            plt.colorbar(im, label='Density (g/cm^3)')
        except Exception as e:
            print(f"  [WARN] LogNorm failed, using linear colors: {e}")
            im = plt.imshow(dens_profiles, aspect='auto', origin='lower',
                            extent=[x_common[0]*100, x_common[-1]*100, times_ns[0], times_ns[-1]],
                            cmap='hot')
            plt.colorbar(im, label='Density (g/cm^3)')
        plt.xlabel('Position (cm)')
        plt.ylabel('Time (ns)')
        plt.title('Density Evolution')
        plt.tight_layout()
        p = os.path.join(output_dir, 'dens_heatmap_2d.png')
        plt.savefig(p, dpi=200)
        plt.close()
        print(f"  ✓ 已保存: {p}")
        plot_files_generated.append(p)

    # 图3: 多个时间点的密度空间分布对比
    print("[RemotePlot] 生成图3: 多时间密度对比...")
    plt.figure(figsize=(12, 6))
    n_curves = min(5, len(times))
    indices = np.linspace(0, len(times)-1, n_curves, dtype=int)
    colors = plt.cm.viridis(np.linspace(0, 1, n_curves))

    for idx, color in zip(indices, colors):
        label = f't = {times_ns[idx]:.2f} ns'
        plt.plot(x_common*100, dens_profiles[idx, :], color=color, linewidth=2, label=label)

    plt.xlabel('Position (cm)')
    plt.ylabel('Density (g/cm^3)')
    plt.title('Density Profiles at Different Times')
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    plt.tight_layout()
    p = os.path.join(output_dir, 'dens_multiple_times.png')
    plt.savefig(p, dpi=200)
    plt.close()
    print(f"  ✓ 已保存: {p}")
    plot_files_generated.append(p)

    # 图4: 最后时刻的密度剖面
    print("[RemotePlot] 生成图4: 最后时刻密度剖面...")
    plt.figure(figsize=(12, 6))
    plt.plot(x_common*100, dens_profiles[-1, :], 'r-', linewidth=2)
    plt.xlabel("x (cm)")
    plt.ylabel(r"density (g/cm$^3$)")
    plt.title(f"Density Profile at t={times_ns[-1]:.2f} ns")
    plt.grid(True, alpha=0.3)
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    plt.tight_layout()
    p = os.path.join(output_dir, 'dens_spatial_final.png')
    plt.savefig(p, dpi=200)
    plt.close()
    print(f"  ✓ 已保存: {p}")
    plot_files_generated.append(p)

    print(f"\n[RemotePlot] 完成! 共生成 {len(plot_files_generated)} 张图片:")
    for pf in plot_files_generated:
        print(f"  - {pf}")

    return True


def main():
    parser = argparse.ArgumentParser(description="FLASH HDF5 超算端绘图脚本")
    parser.add_argument("--input_dir", type=str, required=True,
                        help="HDF5 输出文件目录 (超算上的路径)")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="图片输出目录 (超算上的路径)")

    args = parser.parse_args()

    print("=" * 60)
    print("  FLASH HDF5 超算端绘图脚本")
    print(f"  输入: {args.input_dir}")
    print(f"  输出: {args.output_dir}")
    print("=" * 60)

    # 先检查依赖
    if not check_dependencies():
        sys.exit(1)

    success = plot_on_supercomputer(args.input_dir, args.output_dir)

    if success:
        print("\n✓ 绘图完成!")
        sys.exit(0)
    else:
        print("\n✗ 绘图失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
