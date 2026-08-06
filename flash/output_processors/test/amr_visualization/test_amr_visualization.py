"""
AMR Visualization Test

测试生成1/2/3D数据的AMR网格可视化：
- 使用线画出网格
- 用dens彩图填充格子
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

from flash.output_processors.loader.data_loader import FlashDataLoader
from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File


def visualize_1d_amr(filepath, output_path=None):
    """
    可视化1D AMR网格
    
    参数:
        filepath: FLASH输出文件路径
        output_path: 输出图片路径
    """
    print(f"=== 1D AMR Visualization: {filepath} ===")
    
    # 加载数据
    loader = FlashDataLoader(filepath)
    container = loader.load(use_cell_centers=False, return_global_coords=True)
    
    # 获取数据
    x = container.x
    dens = container.data['dens'].flatten()
    refine_level = container.refine_level.flatten()
    bbox = container.bbox
    
    print(f"  x shape: {x.shape}")
    print(f"  dens shape: {dens.shape}")
    print(f"  refine_level shape: {refine_level.shape}")
    print(f"  Unique refine levels: {np.unique(refine_level)}")
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 子图1: 密度分布
    ax1.plot(x, dens, 'k-', linewidth=2, label='Density')
    ax1.set_xlabel('Position (cm)')
    ax1.set_ylabel('Density (g/cm³)')
    ax1.set_title('1D Density Distribution')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 子图2: AMR网格层级
    # 获取块边界
    nblocks = len(refine_level)
    
    # 为每个块绘制背景色表示层级
    for i in range(nblocks):
        x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
        level = refine_level[i]
        
        # 使用透明度表示层级
        alpha = 0.1 + 0.15 * level  # level越高，颜色越深
        color = plt.cm.viridis(alpha)
        
        ax2.axvspan(x_min, x_max, alpha=alpha, color=plt.cm.viridis(0.3 + 0.7*level/8))
    
    # 绘制网格线（块边界）
    for i in range(nblocks):
        x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
        ax2.axvline(x=x_min, color='red', linestyle='--', alpha=0.5, linewidth=0.5)
        ax2.axvline(x=x_max, color='red', linestyle='--', alpha=0.5, linewidth=0.5)
    
    # 绘制密度曲线
    ax2.plot(x, dens, 'k-', linewidth=2, label='Density')
    
    # 创建颜色条表示层级
    norm = Normalize(vmin=1, vmax=8)
    sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax2)
    cbar.set_label('Refine Level')
    
    ax2.set_xlabel('Position (cm)')
    ax2.set_ylabel('Density (g/cm³)')
    ax2.set_title('1D AMR Grid (colored by refine level)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print("  ✓ 1D visualization completed")


def visualize_2d_amr(filepath, output_path=None):
    """
    可视化2D AMR网格
    
    参数:
        filepath: FLASH输出文件路径
        output_path: 输出图片路径
    """
    print(f"=== 2D AMR Visualization: {filepath} ===")
    
    # 加载数据
    loader = FlashDataLoader(filepath)
    container = loader.load(use_cell_centers=False, return_global_coords=True)
    
    # 获取数据和坐标
    x = container.x
    y = container.y
    dens = container.data['dens']
    refine_level = container.refine_level
    bbox = container.bbox
    
    print(f"  x shape: {x.shape}")
    print(f"  y shape: {y.shape}")
    print(f"  dens shape: {dens.shape}")
    print(f"  refine_level shape: {refine_level.shape}")
    print(f"  Unique refine levels: {np.unique(refine_level)}")
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子图1: 密度分布（使用pcolormesh）
    # 需要创建2D网格
    X, Y = np.meshgrid(x, y, indexing='ij')
    
    # 绘制密度分布
    im = ax1.pcolormesh(X, Y, dens, cmap='hot', shading='auto')
    ax1.set_xlabel('X (cm)')
    ax1.set_ylabel('Y (cm)')
    ax1.set_title('2D Density Distribution')
    ax1.set_aspect('equal')
    plt.colorbar(im, ax=ax1, label='Density (g/cm³)')
    
    # 子图2: AMR网格层级
    # 绘制每个块的边界框
    nblocks = len(refine_level)
    
    # 首先绘制密度背景
    im2 = ax2.pcolormesh(X, Y, dens, cmap='hot', shading='auto', alpha=0.7)
    
    # 为每个块绘制边界框
    for i in range(nblocks):
        x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
        y_min, y_max = bbox[i, 1, 0], bbox[i, 1, 1]
        level = refine_level[i]
        
        # 根据层级设置颜色
        color = plt.cm.viridis(0.3 + 0.7*level/8)
        
        # 绘制矩形边界
        rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                           fill=False, edgecolor=color, linewidth=2,
                           linestyle='-', alpha=0.8)
        ax2.add_patch(rect)
        
        # 在块中心标注层级
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        ax2.text(x_center, y_center, str(level),
                horizontalalignment='center',
                verticalalignment='center', fontweight='bold',
                color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
    
    # 创建颜色条表示层级
    norm = Normalize(vmin=1, vmax=8)
    sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax2)
    cbar.set_label('Refine Level')
    
    ax2.set_xlabel('X (cm)')
    ax2.set_ylabel('Y (cm)')
    ax2.set_title('2D AMR Grid (colored by refine level)')
    ax2.set_aspect('equal')
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print("  ✓ 2D visualization completed")


def visualize_1d_from_3d(filepath, output_path=None):
    """
    从3D文件中提取1D数据并可视化AMR网格
    
    参数:
        filepath: FLASH输出文件路径
        output_path: 输出图片路径
    """
    print(f"=== 1D Visualization from 3D file: {filepath} ===")
    
    # 使用FlashDataLoader读取数据（它会自动拼接块数据）
    loader = FlashDataLoader(filepath)
    container = loader.load(use_cell_centers=False, return_global_coords=True)
    
    # 获取数据
    x = container.x
    dens = container.data['dens']
    
    # 获取refine_level和bbox
    refine_level = container.refine_level if hasattr(container, 'refine_level') else None
    bbox = container.bbox if hasattr(container, 'bbox') else None
    
    print(f"  x shape: {x.shape}")
    print(f"  dens shape: {dens.shape}")
    if refine_level is not None:
        print(f"  refine_level shape: {refine_level.shape}")
        print(f"  Unique refine levels: {np.unique(refine_level)}")
    else:
        print("  No refine_level data")
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 子图1: 密度分布
    dd = dens.flatten() if hasattr(dens, 'flatten') and dens.ndim > 1 else dens
    ax1.plot(x, dd, 'k-', linewidth=2, label='Density')
    ax1.set_xlabel('Position (cm)')
    ax1.set_ylabel('Density (g/cm³)')
    ax1.set_title('1D Density Distribution (using FlashDataLoader)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 子图2: AMR网格层级
    if refine_level is not None and bbox is not None:
        # 获取块边界
        nblocks = len(refine_level)
        
        # 为每个块绘制背景色表示层级
        for i in range(nblocks):
            x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
            level = refine_level[i]
            
            # 使用颜色表示层级
            color = plt.cm.viridis(0.3 + 0.7*level/8)
            
            ax2.axvspan(x_min, x_max, alpha=0.3, color=color)
        
        # 绘制网格线（块边界）
        for i in range(nblocks):
            x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
            ax2.axvline(x=x_min, color='red', linestyle='--', alpha=0.5, linewidth=0.5)
            ax2.axvline(x=x_max, color='red', linestyle='--', alpha=0.5, linewidth=0.5)
    
    # 绘制密度曲线
    dd = dens.flatten() if hasattr(dens, 'flatten') and dens.ndim > 1 else dens
    ax2.plot(x, dd, 'k-', linewidth=2, label='Density')
    
    # 创建颜色条表示层级
    if refine_level is not None:
        norm = Normalize(vmin=1, vmax=8)
        sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax2)
        cbar.set_label('Refine Level')
    
    ax2.set_xlabel('Position (cm)')
    ax2.set_ylabel('Density (g/cm³)')
    ax2.set_title('1D AMR Grid (colored by refine level)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print("  ✓ 1D visualization completed")


def visualize_2d_from_3d(filepath, output_path=None):
    """
    从3D文件中提取2D数据并可视化AMR网格
    
    参数:
        filepath: FLASH输出文件路径
        output_path: 输出图片路径
    """
    print(f"=== 2D Visualization from 3D file: {filepath} ===")
    
    # 使用FlashHDF5File读取数据
    hdf5_file = FlashHDF5File(filepath)
    
    # 读取网格
    grid_data = hdf5_file.read_grid(use_cell_centers=False, return_global_coords=True)
    
    # 读取密度
    dens = hdf5_file.read_dataset('dens')
    
    # 读取refine_level
    try:
        refine_level = hdf5_file.read_dataset('refine level')
    except:
        refine_level = None
    
    # 读取bounding box
    try:
        bbox = hdf5_file.read_dataset('bounding box')
    except:
        bbox = None
    
    # 获取坐标
    x = grid_data['x_1d']
    y = grid_data.get('y_1d', None)
    
    if y is None:
        print("  ✗ No y coordinates found")
        return
    
    # 对于3D数据，提取2D切片（沿着xy平面，在z的中间）
    if dens.ndim == 3:  # 1D数据
        print("  ✗ 1D data, cannot extract 2D slice")
        return
    elif dens.ndim == 4:  # 2D数据
        dens_2d = dens[:, :, 0]
    else:  # 3D数据
        dens_2d = dens[:, :, dens.shape[2]//2]
    
    print(f"  x shape: {x.shape}")
    print(f"  y shape: {y.shape}")
    print(f"  dens_2d shape: {dens_2d.shape}")
    if refine_level is not None:
        print(f"  refine_level shape: {refine_level.shape}")
        print(f"  Unique refine levels: {np.unique(refine_level)}")
    else:
        print("  No refine_level data")
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子图1: 密度分布（使用pcolormesh）
    X, Y = np.meshgrid(x, y, indexing='ij')
    
    # 绘制密度分布
    im = ax1.pcolormesh(X, Y, dens_2d, cmap='hot', shading='auto')
    ax1.set_xlabel('X (cm)')
    ax1.set_ylabel('Y (cm)')
    ax1.set_title('2D Density Distribution (extracted from 3D file)')
    ax1.set_aspect('equal')
    plt.colorbar(im, ax=ax1, label='Density (g/cm³)')
    
    # 子图2: AMR网格层级
    if refine_level is not None and bbox is not None:
        # 绘制每个块的边界框
        nblocks = len(refine_level)
        
        # 首先绘制密度背景
        im2 = ax2.pcolormesh(X, Y, dens_2d, cmap='hot', shading='auto', alpha=0.7)
        
        # 为每个块绘制边界框
        for i in range(nblocks):
            x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
            y_min, y_max = bbox[i, 1, 0], bbox[i, 1, 1]
            level = refine_level[i]
            
            # 根据层级设置颜色
            color = plt.cm.viridis(0.3 + 0.7*level/8)
            
            # 绘制矩形边界
            rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                               fill=False, edgecolor=color, linewidth=2,
                               linestyle='-', alpha=0.8)
            ax2.add_patch(rect)
            
            # 在块中心标注层级
            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2
            ax2.text(x_center, y_center, str(level),
                    horizontalalignment='center',
                    verticalalignment='center', fontweight='bold',
                    color='white',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
        
        # 创建颜色条表示层级
        norm = Normalize(vmin=1, vmax=8)
        sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax2)
        cbar.set_label('Refine Level')
    
    ax2.set_xlabel('X (cm)')
    ax2.set_ylabel('Y (cm)')
    ax2.set_title('2D AMR Grid (colored by refine level)')
    ax2.set_aspect('equal')
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print("  ✓ 2D visualization completed")
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子图1: 密度分布（使用pcolormesh）
    # 需要创建2D网格
    X, Y = np.meshgrid(x, y, indexing='ij')
    
    # 绘制密度分布
    im = ax1.pcolormesh(X, Y, dens, cmap='hot', shading='auto')
    ax1.set_xlabel('X (cm)')
    ax1.set_ylabel('Y (cm)')
    ax1.set_title('2D Density Distribution')
    ax1.set_aspect('equal')
    plt.colorbar(im, ax=ax1, label='Density (g/cm³)')
    
    # 子图2: AMR网格层级
    # 绘制每个块的边界框
    nblocks = len(refine_level)
    
    # 首先绘制密度背景
    im2 = ax2.pcolormesh(X, Y, dens, cmap='hot', shading='auto', alpha=0.7)
    
    # 为每个块绘制边界框
    for i in range(nblocks):
        x_min, x_max = bbox[i, 0, 0], bbox[i, 0, 1]
        y_min, y_max = bbox[i, 1, 0], bbox[i, 1, 1]
        level = refine_level[i]
        
        # 根据层级设置颜色
        color = plt.cm.viridis(0.3 + 0.7*level/8)
        
        # 绘制矩形边界
        rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                           fill=False, edgecolor=color, linewidth=2,
                           linestyle='-', alpha=0.8)
        ax2.add_patch(rect)
        
        # 在块中心标注层级
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        ax2.text(x_center, y_center, str(level),
                horizontalalignment='center',
                verticalalignment='center', fontweight='bold',
                color='white',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.5))
    
    # 创建颜色条表示层级
    norm = Normalize(vmin=1, vmax=8)
    sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax2)
    cbar.set_label('Refine Level')
    
    ax2.set_xlabel('X (cm)')
    ax2.set_ylabel('Y (cm)')
    ax2.set_title('2D AMR Grid (colored by refine level)')
    ax2.set_aspect('equal')
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print("  ✓ 2D visualization completed")


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
    
    # 使用FlashHDF5File读取数据
    hdf5_file = FlashHDF5File(filepath)
    
    # 读取网格
    grid_data = hdf5_file.read_grid(use_cell_centers=False, return_global_coords=True)
    
    # 读取密度
    dens = hdf5_file.read_dataset('dens')
    
    # 读取refine_level
    try:
        refine_level = hdf5_file.read_dataset('refine level')
    except:
        refine_level = None
    
    # 读取bounding box
    try:
        bbox = hdf5_file.read_dataset('bounding box')
    except:
        bbox = None
    
    # 获取坐标
    x = grid_data['x']
    y = grid_data['y'] if 'y' in grid_data else None
    z = grid_data['z'] if 'z' in grid_data else None
    
    print(f"  x shape: {x.shape}")
    print(f"  y shape: {y.shape if y is not None else 'None'}")
    print(f"  z shape: {z.shape if z is not None else 'None'}")
    print(f"  dens shape: {dens.shape}")
    if refine_level is not None:
        print(f"  refine_level shape: {refine_level.shape}")
        print(f"  Unique refine levels: {np.unique(refine_level)}")
    else:
        print("  No refine_level data")
    
    # 选择切片
    if slice_axis == 'x':
        slice_data = dens[slice_index if slice_index else dens.shape[0]//2, :, :]
        slice_x = y
        slice_y = z
        xlabel, ylabel = 'Y (cm)', 'Z (cm)'
    elif slice_axis == 'y':
        slice_data = dens[:, slice_index if slice_index else dens.shape[1]//2, :]
        slice_x = x
        slice_y = z
        xlabel, ylabel = 'X (cm)', 'Z (cm)'
    else:  # 'z'
        slice_data = dens[:, :, slice_index if slice_index else dens.shape[2]//2]
        slice_x = x
        slice_y = y
        xlabel, ylabel = 'X (cm)', 'Y (cm)'
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子图1: 密度分布（切片）
    X, Y = np.meshgrid(slice_x, slice_y, indexing='ij')
    im = ax1.pcolormesh(X, Y, slice_data, cmap='hot', shading='auto')
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)
    ax1.set_title(f'3D Density Distribution (slice along {slice_axis}-axis)')
    ax1.set_aspect('equal')
    plt.colorbar(im, ax=ax1, label='Density (g/cm³)')
    
    # 子图2: AMR网格层级（切片）
    # 对于3D，我们只能显示切片的网格
    # 这里简化为显示2D投影
    im2 = ax2.pcolormesh(X, Y, slice_data, cmap='hot', shading='auto', alpha=0.7)
    
    # 为简化，这里只显示密度分布
    # 完整的3D AMR网格可视化需要更复杂的处理
    ax2.set_xlabel(xlabel)
    ax2.set_ylabel(ylabel)
    ax2.set_title(f'3D AMR Grid (slice along {slice_axis}-axis)')
    ax2.set_aspect('equal')
    
    plt.tight_layout()
    
    # 保存图片
    if output_path:
        plt.savefig(output_path, dpi=200)
        print(f"  Saved to: {output_path}")
    
    plt.close()
    print(f"  ✓ 3D visualization completed (slice along {slice_axis}-axis)")


def test_amr_visualization():
    """测试AMR可视化"""
    print("=" * 60)
    print("AMR Visualization Test")
    print("=" * 60)
    
    # 使用固定的测试文件（优先查找相对路径，允许不存在时优雅跳过）
    test_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "test", "temp_delete", "grid_rede", "output", "t0.h5")
    
    if not os.path.exists(test_file):
        print(f"  ✗ Test file not found: {test_file}")
        return
    
    print(f"Using test file: {test_file}")
    
    # 测试1D可视化（提取x轴数据）
    print("\n" + "=" * 60)
    print("Testing 1D visualization (extracting x-axis data)")
    print("=" * 60)
    output_path = os.path.join(os.path.dirname(__file__), 'amr_1d.png')
    visualize_1d_from_3d(test_file, output_path)
    
    # 测试2D可视化（提取xy平面切片）
    print("\n" + "=" * 60)
    print("Testing 2D visualization (extracting xy-plane slice)")
    print("=" * 60)
    output_path = os.path.join(os.path.dirname(__file__), 'amr_2d.png')
    visualize_2d_from_3d(test_file, output_path)
    
    print("\n" + "=" * 60)
    print("AMR Visualization Test Completed")
    print("=" * 60)


if __name__ == '__main__':
    test_amr_visualization()
