"""
pulse_helpers — FLASH 激光脉冲形状辅助生成器

提供多种脉冲形式:
  - trapezoid (梯形方波, 默认)
  - super-gaussian (超高斯波)
  - custom (自定义 ed_time*/ed_power* 数据)
"""

from .pulse_shapes import (
    gen_pulse,
    make_trapezoid,
    make_super_gaussian,
    make_custom,
    resolve_pulse_data,
    PulseData,
)
