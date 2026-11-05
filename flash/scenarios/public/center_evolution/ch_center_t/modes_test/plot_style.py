"""统一绘图风格 — 英文科研文献插图规范。

铁律（用户跨项目约定）：
  * 图中所有文字（坐标轴/标题/图例/刻度）必须是英文；
  * 任何字体大小 >= 18pt；
  * 默认字体 Times New Roman（Linux 上无该字体时按 serif 栈回退，
    并在 apply_style() 返回实际生效的字体族，供报告记录）。

本模块被 run_mode_test.py / analyze_modes.py 共同引用，
保证五模式对比图与单模式诊断图风格逐字节一致。
"""
from __future__ import annotations

from typing import Dict, List

import matplotlib

matplotlib.use("Agg")  # 无显示环境（WSL/超算）必须
import matplotlib.pyplot as plt  # noqa: E402

#: Times New Roman 优先；Linux 常见度量兼容替代品随后
FONT_STACK: List[str] = [
    "Times New Roman",
    "Liberation Serif",
    "Nimbus Roman No9 L",
    "DejaVu Serif",
]

#: 模式展示顺序（对比图图例/曲线顺序的唯一来源）
MODE_ORDER: List[str] = ["win-wsl", "win-hpc", "wsl-wsl", "wsl-hpc", "hpc-insitu"]

#: 每模式的视觉标识（颜色/标记/英文图例文本）
MODE_STYLE: Dict[str, Dict[str, str]] = {
    "win-wsl": {"color": "#1f77b4", "marker": "o",
                "label": "Windows -> WSL"},
    "win-hpc": {"color": "#d62728", "marker": "s",
                "label": "Windows -> HPC (remote)"},
    "wsl-wsl": {"color": "#2ca02c", "marker": "^",
                "label": "WSL -> WSL"},
    "wsl-hpc": {"color": "#9467bd", "marker": "D",
                "label": "WSL -> HPC (remote)"},
    "hpc-insitu": {"color": "#ff7f0e", "marker": "v",
                   "label": "HPC -> HPC (insitu)"},
}

#: 模式中文说明（仅用于 README / 报告正文，不出现在图上）
MODE_DESC_CN: Dict[str, str] = {
    "win-wsl": "Windows 中执行 python 脚本 -> WSL FLASH",
    "win-hpc": "Windows 中执行 python 脚本 -> 超算 FLASH（上传/提交/分析/下载）",
    "wsl-wsl": "WSL 中执行 python 脚本 -> WSL FLASH",
    "wsl-hpc": "WSL 中执行 python 脚本 -> 超算 FLASH（上传/提交/分析/下载）",
    "hpc-insitu": "超算中执行 python 脚本 -> 超算 FLASH（就地 sbatch）",
}


def apply_style() -> str:
    """应用全局绘图风格，返回实际生效的字体族名（供报告记录）。"""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": FONT_STACK,
        "font.size": 18,
        "axes.titlesize": 20,
        "axes.labelsize": 18,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "legend.fontsize": 18,
        "legend.title_fontsize": 18,
        "figure.titlesize": 20,
        "axes.linewidth": 1.2,
        "lines.linewidth": 2.0,
        "lines.markersize": 7,
        "grid.alpha": 0.3,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "axes.unicode_minus": False,
    })
    from matplotlib.font_manager import findfont, FontProperties
    resolved = findfont(FontProperties(family="serif"))
    for name in FONT_STACK:
        if name.lower().replace(" ", "") in resolved.lower().replace(" ", ""):
            return name
    return resolved
