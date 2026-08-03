"""
多光束脉冲激光形状绘图器 — PulsePlotter

绘制单/多束激光脉冲的时间-功率曲线。
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # 非交互后端
    import matplotlib.pyplot as plt
    # ── PPT-friendly plot style (fonts >= 18, English only) ──
    try:
        from output_processors.plotter.plot_style import apply_plot_style
        apply_plot_style()
    except ImportError:
        pass
except ImportError:
    plt = None  # type: ignore


class PulsePlotter:
    """多光束脉冲激光形状绘图器。

    功能:
        - 绘制单束脉冲的时间-功率曲线
        - 叠加显示多束脉冲
        - 标注峰值功率、脉宽等关键参数
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
            "legend.fontsize": 10,
        })

    def plot_pulse(
        self,
        times: np.ndarray,
        powers: np.ndarray,
        title: str = "Laser Pulse Shape",
        save_path: Optional[Union[str, Path]] = None,
        beam_label: Optional[str] = None,
    ) -> Optional[Path]:
        """绘制单束脉冲形状。

        Args:
            times: 时间点数组 (s)
            powers: 功率数组 (W)
            title: 图表标题
            save_path: 保存路径，为 None 时显示
            beam_label: 光束标签（图例用）

        Returns:
            保存的文件路径，或 None
        """
        if plt is None:
            raise ImportError("matplotlib is required for PulsePlotter")

        fig, ax = plt.subplots(figsize=(8, 5))

        label = beam_label or "Pulse"
        ax.plot(times , powers * 1e-12, "b-", linewidth=2, label=label)

        # 标注峰值
        idx_peak = np.argmax(powers)
        peak_pw = powers[idx_peak] * 1e-12
        peak_t = times[idx_peak]
        ax.plot(peak_t, peak_pw, "ro", markersize=8)
        ax.annotate(
            f"Peak: {peak_pw:.2f} TW/cm2",
            xy=(peak_t, peak_pw),
            xytext=(peak_t + 0.1, peak_pw * 0.9),
            arrowprops=dict(arrowstyle="->", color="red"),
        )

        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Power (TW/cm2)")

        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

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

    def plot_multi_pulse(
        self,
        pulses: List[Tuple[np.ndarray, np.ndarray]],
        labels: Optional[List[str]] = None,
        title: str = "Multi-beam Pulse Shapes",
        save_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """绘制多束脉冲叠加图。

        Args:
            pulses: [(times, powers), ...] 列表
            labels: 每束脉冲的标签
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的文件路径，或 None
        """
        if plt is None:
            raise ImportError("matplotlib is required for PulsePlotter")

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ["b", "r", "g", "orange", "purple", "cyan"]
        for i, (times, powers) in enumerate(pulses):
            label = labels[i] if labels and i < len(labels) else f"Beam {i + 1}"
            color = colors[i % len(colors)]
            ax.plot(times , powers * 1e-12, color=color, linewidth=2, label=label)

            # 标注峰值
            idx_peak = np.argmax(powers)
            ax.plot(times[idx_peak] , powers[idx_peak] * 1e-12, "o", color=color, markersize=6)

        ax.set_xlabel("Time (ns)")
        ax.set_ylabel("Power (TW/cm2)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

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
