"""
viz 子包 — 可视化模块

提供激光脉冲绘制、预诊断图生成等功能。
"""

from __future__ import annotations

from .pulse import plot_pulse, plot_pulse_with_profile
from .pre_diagnose import generate_initial_density, generate_laser_pulse_annotated

__all__ = [
    "plot_pulse",
    "plot_pulse_with_profile",
    "generate_initial_density",
    "generate_laser_pulse_annotated",
]
