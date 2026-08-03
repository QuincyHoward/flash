"""
gen_sim_data — Simulation_data.F90 文件生成

从 scenarios/flash_demo/LaserSlab1d/Simulation_data.F90 模板生成。
Simulation_data.F90 定义 FLASH 仿真运行时参数变量。
"""

from .generator import SimDataGenerator

__all__ = ["SimDataGenerator"]
