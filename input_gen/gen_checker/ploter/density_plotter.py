"""
初始密度分布绘图器 — DensityPlotter

绘制 FLASH 仿真初始状态的密度分布。
支持 1D (线图)、2D (伪彩色)、3D (切片) 三种模式。
"""

from pathlib import Path
from typing import Optional, Union

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # ── PPT-friendly plot style (fonts >= 18, English only) ──
    try:
        from output_processors.plotter.plot_style import apply_plot_style
        apply_plot_style()
    except ImportError:
        pass
except ImportError:
    plt = None  # type: ignore


class DensityPlotter:
    """初始密度分布绘图器。

    功能:
        - 1D: 密度沿 x 轴的线图（标注靶材/腔室边界）
        - 2D: 密度伪彩色图（标注区域边界）
        - 3D: 密度切片图（z=0 或 y=0 平面切片）
    """

    def __init__(self):
        self._setup_style()

    @staticmethod
    def _setup_style():
        if plt is None:
            return
        plt.style.use("seaborn-v0_8-darkgrid")
        plt.rcParams.update({
            "figure.dpi": 120,
            "savefig.dpi": 150,
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 13,
        })

    def plot_1d(
        self,
        x: np.ndarray,
        density: np.ndarray,
        species: Optional[np.ndarray] = None,
        region_boundaries: Optional[list] = None,
        title: str = "Initial Density Distribution (1D)",
        save_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """绘制 1D 密度分布。

        Args:
            x: 空间坐标数组 (cm)
            density: 密度数组 (g/cm^3)
            species: 物种标识数组（可选，用于着色）
            region_boundaries: 区域边界位置列表 [(name, x_pos), ...]
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的文件路径，或 None
        """
        if plt is None:
            raise ImportError("matplotlib is required for DensityPlotter")

        fig, ax = plt.subplots(figsize=(9, 5))

        ax.plot(x * 1e4, density, "b-", linewidth=2, label="Density")

        # 标注区域边界
        if region_boundaries:
            colors = ["r", "g", "orange"]
            for i, (name, pos) in enumerate(region_boundaries):
                color = colors[i % len(colors)]
                ax.axvline(x=pos * 1e4, color=color, linestyle="--", alpha=0.7)
                ax.text(pos * 1e4, ax.get_ylim()[1] * 0.9, name,
                        rotation=90, color=color)

        ax.set_xlabel("x (um)")
        ax.set_ylabel("Density (g/cm$^3$)")
        ax.set_title(title)
        if region_boundaries:
            ax.legend()
        ax.grid(True, alpha=0.3)

        ax.set_ylim(min(density) * 0.9, max(density) * 1.1)

        # 使用对数刻度如果密度跨度大
        # if density.max() / max(density.min(), 1e-10) > 100:
        #     ax.set_yscale("log")

        plt.tight_layout()
        if save_path:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(path))
            plt.close(fig)
            return path
        else:
            plt.show()
            return None

    def plot_2d(
        self,
        x: np.ndarray,
        y: np.ndarray,
        density_2d: np.ndarray,
        title: str = "Initial Density Distribution (2D)",
        save_path: Optional[Union[str, Path]] = None,
        region_boundaries: Optional[list] = None,
    ) -> Optional[Path]:
        """绘制 2D 密度伪彩色图。

        Args:
            x: x 坐标数组 (cm)，1D
            y: y 坐标数组 (cm)，1D
            density_2d: 密度二维数组 (ny, nx)
            title: 图表标题
            save_path: 保存路径
            region_boundaries: 区域边界虚线 [(name, x_pos, y_pos), ...]

        Returns:
            保存的文件路径，或 None
        """
        if plt is None:
            raise ImportError("matplotlib is required for DensityPlotter")

        fig, ax = plt.subplots(figsize=(10, 7))

        X, Y = np.meshgrid(x * 1e4, y * 1e4)
        pcm = ax.pcolormesh(X, Y, density_2d, shading="auto", cmap="viridis")
        cbar = fig.colorbar(pcm, ax=ax, label="Density (g/cm$^3$)")

        # 区域边界
        if region_boundaries:
            colors = ["r", "w", "orange"]
            for i, (name, x_pos, y_pos) in enumerate(region_boundaries):
                color = colors[i % len(colors)]
                ax.axvline(x=x_pos * 1e4, color=color, linestyle="--", alpha=0.7)
                ax.text(x_pos * 1e4, y[-1] * 1e4 * 0.95, name, color=color, rotation=90)

        ax.set_xlabel("x (um)")
        ax.set_ylabel("y (um)")
        ax.set_title(title)
        ax.set_aspect("equal")

        plt.tight_layout()
        if save_path:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(path))
            plt.close(fig)
            return path
        else:
            plt.show()
            return None

    def plot_3d_slice(
        self,
        x: np.ndarray,
        y: np.ndarray,
        density_slice: np.ndarray,
        slice_label: str = "z=0",
        title: str = "Initial Density Distribution (3D Slice)",
        save_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """绘制 3D 密度切片图。

        Args:
            x: x 坐标数组 (cm)
            y: y 坐标数组 (cm)
            density_slice: 密度切片二维数组
            slice_label: 切片位置标签
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的文件路径，或 None
        """
        return self.plot_2d(
            x, y, density_slice,
            title=f"{title} ({slice_label})",
            save_path=save_path,
        )
