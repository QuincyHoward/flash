"""
激光光线/光斑位置绘图器 — RayPlotter

绘制激光光线路径和光斑在目标上的位置。
支持 2D 和 3D 两种渲染模式。
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import numpy as np

# 简易 BeamConfig 类（自包含，不依赖 par/）
class _BeamConfig:
    """用于绘图的光束配置数据结构。"""
    def __init__(self, beam_id=1, lens_x=-0.1, lens_y=0.0, lens_z=0.0,
                 target_x=0.014, target_y=0.0, target_z=0.0,
                 target_semi_axis_major=None, target_semi_axis_minor=None):
        self.beam_id = beam_id
        self.lens_x = lens_x
        self.lens_y = lens_y
        self.lens_z = lens_z
        self.target_x = target_x
        self.target_y = target_y
        self.target_z = target_z
        self.target_semi_axis_major = target_semi_axis_major
        self.target_semi_axis_minor = target_semi_axis_minor

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse
    # ── PPT-friendly plot style (fonts >= 18, English only) ──
    try:
        from output_processors.plotter.plot_style import apply_plot_style
        apply_plot_style()
    except ImportError:
        pass
except ImportError:
    plt = None  # type: ignore
    Ellipse = None  # type: ignore


class RayPlotter:
    """激光光线/光斑位置绘图器。

    功能:
        - 2D: 显示光线从透镜到目标的路径
        - 2D: 显示光斑在目标上的位置和形状（椭圆/圆）
        - 3D: 3D 渲染光线和光斑（俯视图）
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

    def _normalize_beams(self, beams):
        """将 BeamConfig 或 dict 归一化为 _BeamConfig 列表。"""
        if isinstance(beams, _BeamConfig):
            return [beams]
        if isinstance(beams, list):
            if all(isinstance(b, _BeamConfig) for b in beams):
                return beams
            if all(isinstance(b, dict) for b in beams):
                return [_BeamConfig(**b) for b in beams]
        return list(beams)

    def plot_rays_2d(
        self,
        beams: list,
        domain_x: tuple = (-0.1, 0.02),
        domain_y: tuple = (-0.04, 0.04),
        title: str = "Laser Ray Paths (2D)",
        save_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """绘制 2D 激光光线路径。

        每条光线从透镜位置 (lens_x, lens_y) 到目标位置 (target_x, target_y)。
        对于 2D, y 轴表示空间的 y 方向。

        Args:
            beams: BeamConfig 对象列表或字典列表
            domain_x: x 轴范围 (xmin, xmax) in cm
            domain_y: y 轴范围 (ymin, ymax) in cm
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的文件路径，或 None
        """
        if plt is None:
            raise ImportError("matplotlib is required for RayPlotter")

        beam_list = self._normalize_beams(beams)
        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ["b", "r", "g", "orange", "purple", "cyan"]
        for i, beam in enumerate(beam_list):
            color = colors[i % len(colors)]
            # 从透镜到目标画线
            ax.plot(
                [beam.lens_x, beam.target_x],
                [beam.lens_y, beam.target_y],
                color=color, linewidth=1.5, linestyle="-",
                label=f"Beam {beam.beam_id}",
            )
            # 透镜位置
            ax.plot(beam.lens_x, beam.lens_y, "D", color=color, markersize=10)
            # 目标位置（靶点）
            ax.plot(beam.target_x, beam.target_y, "*", color=color, markersize=12)

        # 标注
        ax.set_xlabel("x (cm)")
        ax.set_ylabel("y (cm)")
        ax.set_title(title)
        ax.legend()
        ax.set_xlim(domain_x)
        ax.set_ylim(domain_y)
        ax.grid(True, alpha=0.3)
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

    def plot_rays_3d(
        self,
        beams: list,
        title: str = "Laser Ray Paths (3D)",
        save_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """绘制 3D 激光光线路径（俯视投影图）。

        Args:
            beams: BeamConfig 对象列表
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的文件路径，或 None
        """
        if plt is None:
            raise ImportError("matplotlib is required for RayPlotter")

        beam_list = self._normalize_beams(beams)
        fig, ax = plt.subplots(figsize=(10, 8))

        colors = ["b", "r", "g", "orange", "purple", "cyan"]
        for i, beam in enumerate(beam_list):
            color = colors[i % len(colors)]
            # 使用 lens_x/lens_z 和 target_x/target_z 作为 xz 平面
            ax.plot(
                [beam.lens_x, beam.target_x],
                [beam.lens_z, beam.target_z],
                color=color, linewidth=1.5, linestyle="-",
                label=f"Beam {beam.beam_id}",
            )
            ax.plot(beam.lens_x, beam.lens_z, "D", color=color, markersize=10)
            ax.plot(beam.target_x, beam.target_z, "*", color=color, markersize=12)

            # 标注光束编号
            mid_x = (beam.lens_x + beam.target_x) / 2
            mid_z = (beam.lens_z + beam.target_z) / 2
            ax.text(mid_x, mid_z, f"B{beam.beam_id}",
                    color=color, ha="center")

        ax.set_xlabel("x (cm)")
        ax.set_ylabel("z (cm)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
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

    def plot_spot_positions(
        self,
        beams: list,
        title: str = "Laser Spot Positions",
        save_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """绘制激光光斑位置。

        显示各光束在目标位置的光斑形状（圆或椭圆）。
        对于 2D: yz 平面。对于未设置椭圆参数的，使用默认圆形。

        Args:
            beams: BeamConfig 对象列表
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的文件路径，或 None
        """
        if plt is None or Ellipse is None:
            raise ImportError("matplotlib is required for RayPlotter")

        beam_list = self._normalize_beams(beams)
        fig, ax = plt.subplots(figsize=(8, 8))

        colors = ["b", "r", "g", "orange", "purple", "cyan"]
        for i, beam in enumerate(beam_list):
            color = colors[i % len(colors)]

            # 光斑中心（目标位置）
            cx, cy = beam.target_y, beam.target_z

            # 如果设置了椭圆参数，使用椭圆；否则用默认圆
            if beam.target_semi_axis_major is not None:
                width = 2 * beam.target_semi_axis_major
                height = 2 * (beam.target_semi_axis_minor or beam.target_semi_axis_major)
                ellipse = Ellipse(
                    (cx, cy), width, height,
                    edgecolor=color, facecolor=color, alpha=0.3, linewidth=2,
                )
                ax.add_patch(ellipse)
            else:
                # 默认光斑半径
                radius = 50e-4
                circle = plt.Circle(
                    (cx, cy), radius,
                    edgecolor=color, facecolor=color, alpha=0.3, linewidth=2,
                )
                ax.add_patch(circle)

            ax.plot(cx, cy, f"{color}*", markersize=12)
            ax.text(cx, cy, f"  B{beam.beam_id}", color=color)

        # 标注 domain 边界
        ax.axhline(y=0, color="gray", linestyle=":", alpha=0.5)
        ax.axvline(x=0, color="gray", linestyle=":", alpha=0.5)

        ax.set_xlabel("y (cm)")
        ax.set_ylabel("z (cm)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
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
