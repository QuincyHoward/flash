"""
pulse_helpers — FLASH 激光脉冲形状辅助生成器

提供多种脉冲形式:
  - trapezoid (梯形方波, 默认)
  - super-gaussian (超高斯波)
  - custom (自定义 ed_time*/ed_power* 数据)

用法:
  from pulse_helpers import gen_pulse, PulseData

  # 梯形方波
  data = gen_pulse("trapezoid", peak_power=5e14, rise_time=0.1e-9, flat_time=1.4e-9)

  # 超高斯波
  data = gen_pulse("super-gaussian", peak_power=5e14, center_time=0.8e-9, fwhm=0.5e-9)

  # 自定义 (直接传入 ed_time/ed_power 数据)
  data = gen_pulse("custom", ed_times=[0, 0.1e-9, 1.0e-9, 1.08e-9],
                            ed_powers=[0, 5e14, 5e14, 0])
"""

from .pulse_shapes import (
    gen_pulse,
    make_trapezoid,
    make_super_gaussian,
    make_custom,
    resolve_pulse_data,
    PulseData,
)
