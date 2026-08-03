"""
网格和物质划分可视化
═════════════════

使用 matplotlib 绘制仿真域的空间网格和物质分配图。

支持:
  - 1D: 密度/物种沿 x 轴的分布线图
  - 2D: 密度分布彩色图
  - 区域边界标注
  - 图例 (物质种类)
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# ── PPT-friendly plot style (fonts >= 18, English only) ──
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass
from matplotlib.patches import Rectangle, FancyBboxPatch
from .grid import GridBuilder, Region


class BlockVisualizer:
    """网格和物质划分可视化器。
    
    用法:
        builder = GridBuilder.from_laserslab_1d()
        viz = BlockVisualizer(builder)
        viz.plot_1d("grid_preview.png")
    """
    
    def __init__(self, builder: GridBuilder):
        self.builder = builder
        self._setup_style()
    
    @staticmethod
    def _setup_style():
        """设置 matplotlib 样式."""
        plt.rcParams.update({
            'figure.dpi': 150,
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'legend.fontsize': 10,
            'figure.facecolor': 'white',
            'axes.facecolor': '#f8f9fa',
            'axes.grid': True,
            'grid.alpha': 0.3,
        })
    
    # ============================================================
    # 1D 可视化
    # ============================================================
    
    def plot_1d(
        self,
        save_path: Optional[str] = None,
        n_points: int = 500,
        figsize: Tuple[float, float] = (14, 5),
        show_plot: bool = False,
    ) -> plt.Figure:
        """绘制 1D 密度和物种分布图。
        
        Args:
            save_path: 保存路径 (None 则不保存)
            n_points: 采样点数
            figsize: 图大小 (宽, 高)
            show_plot: 是否显示
        
        Returns:
            matplotlib Figure 对象
        """
        x, density, species = self.builder.sample_1d(n_points)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # --- 左图: 密度分布 ---
        ax1.plot(x * 1e4, density, 'b-', linewidth=1.5, label='Density (g/cm³)')
        ax1.set_xlabel('x (um)')
        ax1.set_ylabel('Density (g/cm³)')
        ax1.set_title('Initial Density Distribution')
        ax1.legend(loc='upper right')
        
        # 标注区域边界
        for region in self.builder.regions:
            if region.x_range:
                for boundary in region.x_range:
                    ax1.axvline(x=boundary * 1e4, color='red', 
                               linestyle='--', alpha=0.4, linewidth=0.8)
            # 区域标签
            if region.x_range:
                mid = (region.x_range[0] + region.x_range[1]) / 2 * 1e4
                ymax = ax1.get_ylim()[1]
                ax1.text(mid, ymax * 0.9, region.name, ha='center', color='red', alpha=0.7,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # --- 右图: 物种分布 ---
        species_numeric = np.zeros(len(species))
        unique_species = list(dict.fromkeys(species))  # 保持顺序
        
        species_colors = {}
        default_colors = ['#e8f4f8', '#fce4d6']  # light blue, light orange
        for i, sp in enumerate(unique_species):
            sp_idx = [j for j, s in enumerate(species) if s == sp]
            if sp_idx:
                specie_value = i + 1
                species_numeric[sp_idx[0]:sp_idx[-1]+1] = specie_value
                species_colors[sp] = default_colors[i % len(default_colors)]
        
        ax2.fill_between(x * 1e4, 0, species_numeric, 
                         step='mid', alpha=0.7, color='#d4edda')
        ax2.set_xlabel('x (um)')
        ax2.set_ylabel('Species ID')
        ax2.set_title('Material Species Distribution')
        ax2.set_yticks([1, 2])
        ax2.set_yticklabels(unique_species[:2] if len(unique_species) >= 2 else unique_species)
        
        # 标注区域
        for region in self.builder.regions:
            if region.x_range:
                mid = (region.x_range[0] + region.x_range[1]) / 2 * 1e4
                ax2.text(mid, 0.5, f"{region.name}\n({region.species})", 
                        ha='center', color='#333')
                for boundary in region.x_range:
                    ax2.axvline(x=boundary * 1e4, color='gray', 
                               linestyle='--', alpha=0.4)
        
        fig.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=200, bbox_inches='tight')
        
        if show_plot:
            plt.show()
        else:
            plt.close(fig)
        
        return fig
    
    # ============================================================
    # 2D 可视化
    # ============================================================
    
    def plot_2d(
        self,
        save_path: Optional[str] = None,
        nx: int = 200,
        ny: int = 100,
        figsize: Tuple[float, float] = (10, 8),
        show_plot: bool = False,
    ) -> plt.Figure:
        """绘制 2D 密度分布彩色图。
        
        Args:
            save_path: 保存路径
            nx, ny: 采样分辨率
            figsize: 图大小
            show_plot: 是否显示
        """
        X, Y, density = self.builder.sample_2d(nx, ny)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 转换单位为 um
        extent = [
            self.builder.spec.domain_x[0] * 1e4,
            self.builder.spec.domain_x[1] * 1e4,
            self.builder.spec.domain_y[0] * 1e4,
            self.builder.spec.domain_y[1] * 1e4,
        ]
        
        im = ax.imshow(density, extent=extent, origin='lower', 
                      aspect='auto', cmap='viridis')
        plt.colorbar(im, ax=ax, label='Density (g/cm³)')
        
        # 绘制区域边界
        for region in self.builder.regions:
            if region.x_range and region.y_range:
                x0, x1 = region.x_range[0] * 1e4, region.x_range[1] * 1e4
                y0, y1 = region.y_range[0] * 1e4, region.y_range[1] * 1e4
                rect = plt.Rectangle((x0, y0), x1 - x0, y1 - y0,
                                     fill=False, edgecolor='red', 
                                     linewidth=1.5, linestyle='--')
                ax.add_patch(rect)
                
                # 标签
                ax.text((x0 + x1) / 2, (y0 + y1) / 2, region.name,
                       ha='center', va='center',
                       color='white', fontweight='bold',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
        
        ax.set_xlabel('x (um)')
        ax.set_ylabel('y (um)')
        ax.set_title('2D Initial Density Distribution')
        
        fig.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(save_path, dpi=200, bbox_inches='tight')
        
        if show_plot:
            plt.show()
        else:
            plt.close(fig)
        
        return fig
    
    # ============================================================
    # 总结报告
    # ============================================================
    
    def summary(self) -> str:
        """生成网格构建的文本摘要."""
        lines = []
        lines.append("=" * 60)
        lines.append("  FLASH Simulation Grid Summary")
        lines.append("=" * 60)
        lines.append(f"  Dimension:  {self.builder.spec.dim}D")
        lines.append(f"  Geometry:   {self.builder.spec.geometry}")
        lines.append(f"  Domain X:   [{self.builder.spec.domain_x[0]*1e4:.1f}, {self.builder.spec.domain_x[1]*1e4:.1f}] um")
        if self.builder.spec.dim >= 2:
            lines.append(f"  Domain Y:   [{self.builder.spec.domain_y[0]*1e4:.1f}, {self.builder.spec.domain_y[1]*1e4:.1f}] um")
        lines.append(f"  Blocks:     {self.builder.spec.nblocks_x} x {self.builder.spec.nblocks_y} x {self.builder.spec.nblocks_z}")
        lines.append(f"  Cells/block: {self.builder.spec.nxb} x {self.builder.spec.nyb} x {self.builder.spec.nzb}")
        lines.append("")
        lines.append("  Regions:")
        for i, region in enumerate(self.builder.regions, 1):
            lines.append(f"    {i}. {region.name}")
            lines.append(f"       Species: {region.species} | Target: {region.is_target}")
            if region.x_range:
                lines.append(f"       X: [{region.x_range[0]*1e4:.1f}, {region.x_range[1]*1e4:.1f}] um")
            if region.y_range:
                lines.append(f"       Y: [{region.y_range[0]*1e4:.1f}, {region.y_range[1]*1e4:.1f}] um")
            lines.append(f"       rho={region.rho:.2e}, T={region.tele:.1f} K")
        
        return "\n".join(lines)
    
    def save_summary(self, filepath: str):
        """保存摘要到文本文件."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        Path(filepath).write_text(self.summary(), encoding="utf-8")
