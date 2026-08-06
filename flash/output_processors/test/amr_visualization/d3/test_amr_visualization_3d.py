"""
AMR Visualization Test - 3D

测试3D数据的AMR网格可视化：
- 使用 extract_var_yt_style 提取扁平化坐标数据
- 用 scatter 散点图显示切片
- 不同层级用不同颜色表示
"""
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 无头模式
import matplotlib.pyplot as plt
# ── PPT-friendly plot style (fonts >= 18, English only) ──
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass
from matplotlib.colors import Normalize
import h5py
from pathlib import Path

# 添加项目路径 - flash目录

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None  # 已安装环境 (site-packages): 静默跳过
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File


def visualize_3d_amr_slice(filepath, output_path=None, slice_axis='z', slice_index=None):
    """
    可视化3D AMR网格的切片
    
    参数:
        filepath: FLASH输出文件路径
        output_path: 输出图片路径
        slice_axis: 切片轴 ('x', 'y', 'z')
        slice_index: 切片索引 (如果为None，则使用中间切片)
    """
    print(f"=== 3D AMR Visualization (slice along {slice_axis}-axis): {filepath} ===")
    
    # 使用 extract_var_yt_style 获取扁平化坐标数据
    hdf5_file = FlashHDF5File(filepath)
    cs = hdf5_file.coordinate_system
    cl = hdf5_file.coord_labels
    print(f"  Coordinate system: {cs}")
    
    # 提取 yt 风格数据（坐标已排序去重）
    x_flat, y_flat, z_flat, dens_flat = hdf5_file.extract_var_yt_style('dens')
    hdf5_file.close()
    
    print(f"  Total cells: {len(dens_flat)}")
    print(f"  Coord ranges: x=[{x_flat.min():.4e},{x_flat.max():.4e}], "
          f"y=[{y_flat.min():.4e},{y_flat.max():.4e}], "
          f"z=[{z_flat.min():.4e},{z_flat.max():.4e}]")
    
    # 选择切片
    dz = (z_flat.max() - z_flat.min()) / 50
    z_mid = np.median(z_flat)
    if slice_index is not None:
        z_slice = z_flat.min() + slice_index * (z_flat.max() - z_flat.min()) / max(z_flat.shape[0]//z_flat.max(), 1)
        z_slice = min(z_slice, z_flat.max())
    else:
        z_slice = z_mid
    
    # 取 z 切片附近的点
    mask = np.abs(z_flat - z_slice) < dz
    slice_x_flat = x_flat[mask]
    slice_y_flat = y_flat[mask]
    slice_d_flat = dens_flat[mask]
    
    print(f"  Slice at z={z_slice:.4e} cm: {len(slice_x_flat)} cells")
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子图1: 密度分布（切片 scatter）
    sc1 = ax1.scatter(slice_x_flat, slice_y_flat, c=slice_d_flat, 
                      s=15, cmap='hot', alpha=0.8, edgecolors='none')
    ax1.set_xlabel('x [cm]')
    ax1.set_ylabel('y [cm]')
    ax1.set_title(f'3D Density: z-slice at {z_slice:.3e} cm ({len(slice_x_flat)} cells)')
    ax1.set_aspect('equal')
    plt.colorbar(sc1, ax=ax1, label='Density (g/cm³)')
    
    # 子图2: 全 3D xOy 最大投影
    # 按 (x,y) 分组取最大 dens
    xy_max = {}
    for xi, yi, di in zip(x_flat, y_flat, dens_flat):
        key = (np.round(xi, 10), np.round(yi, 10))
        if key not in xy_max or di > xy_max[key]:
            xy_max[key] = di
    proj_x = np.array([k[0] for k in xy_max.keys()])
    proj_y = np.array([k[1] for k in xy_max.keys()])
    proj_d = np.array(list(xy_max.values()))
    
    sc2 = ax2.scatter(proj_x, proj_y, c=proj_d, 
                      s=15, cmap='hot', alpha=0.8, edgecolors='none')
    ax2.set_xlabel('x [cm]')
    ax2.set_ylabel('y [cm]')
    ax2.set_title(f'3D xOy Max-Projection ({len(proj_x)} cells)')
    ax2.set_aspect('equal')
    plt.colorbar(sc2, ax=ax2, label='Density (g/cm³)')
    
    plt.tight_layout()
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print(f"  ✓ 3D visualization completed (slice along {slice_axis}-axis)")


def test_3d_visualization():
    """测试3D AMR可视化"""
    print("=" * 60)
    print("3D AMR Visualization Test")
    print("=" * 60)
    
    # 查找测试文件
    output_processors_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    inputfiles_dir = os.path.join(output_processors_dir, 'inputfiles')
    test_file_3d = os.path.join(inputfiles_dir, 'hdf5files_3d')
    
    # 查找第一个3D测试文件
    if os.path.exists(test_file_3d):
        files = [f for f in os.listdir(test_file_3d) if not f.endswith('.png')]
        if files:
            test_file_3d = os.path.join(test_file_3d, files[0])
        else:
            test_file_3d = None
    else:
        test_file_3d = None
    
    if test_file_3d is None or not os.path.exists(test_file_3d):
        print(f"  ✗ 3D test file not found")
        return
    
    print(f"Using test file: {test_file_3d}")
    
    # 测试3D可视化（切片）
    output_path = os.path.join(os.path.dirname(__file__), 'amr_3d.png')
    visualize_3d_amr_slice(test_file_3d, output_path, slice_axis='z')
    
    print("\n" + "=" * 60)
    print("3D AMR Visualization Test Completed")
    print("=" * 60)


if __name__ == '__main__':
    test_3d_visualization()
