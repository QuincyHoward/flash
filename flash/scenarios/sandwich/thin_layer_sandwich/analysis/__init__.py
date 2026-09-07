"""
analysis 子包 — 仿真数据分析与诊断

提供三层靶场景的仿真后处理分析功能，包括:
  - 300ps 滑动窗口分析 (core.sliding_window_300ps)
  - 统一网格插值 (core.interpolate_to_uniform_grid)
  - TXN (nele×tele) 完整分析管线 (txn.compute_analysis)
  - Tele/Nele 双轴时序图 + 空间剖面 (dens.py → tele_nele)
  - 四子图时空演化 (timespatial.plot_time_spatial)
  - 基础统计计算 (compute_mean / max / cv / norm)

独立于优化框架，可被测试脚本或 viz 子包调用。
"""

from __future__ import annotations

from .core import (
    sliding_window_300ps,
    interpolate_to_uniform_grid,
    compute_mean,
    compute_max,
    compute_cv,
    compute_norm,
)
from .txn import (
    compute_analysis as compute_txn_analysis,
    plot_time_series as plot_txn_timeseries,
)
from .dens import (
    plot_tele_nele_time_series,
    plot_tele_nele_spatial_profiles,
)
from .timespatial import plot_time_spatial

__all__ = [
    "sliding_window_300ps",
    "interpolate_to_uniform_grid",
    "compute_mean",
    "compute_max",
    "compute_cv",
    "compute_norm",
    "compute_txn_analysis",
    "plot_txn_timeseries",
    "plot_tele_nele_time_series",
    "plot_tele_nele_spatial_profiles",
    "plot_time_spatial",
]
