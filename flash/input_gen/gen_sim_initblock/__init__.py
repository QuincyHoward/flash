"""
gen_sim_initblock — Simulation_initBlock.F90 生成器 (自包含)

代码从 block/ 复制并独立维护，无外部依赖。
"""

from .generator import BlockGenerator
from .grid import GridBuilder, Region, GridSpec
from .visualizer import BlockVisualizer

__all__ = [
    "BlockGenerator",
    "GridBuilder",
    "Region",
    "GridSpec",
    "BlockVisualizer",
]
