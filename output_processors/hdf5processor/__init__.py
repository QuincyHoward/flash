"""
hdf5processor — FLASH HDF5 输出文件的核心 I/O 层

负责:
  - 打开/读取 FLASH 的 HDF5 输出文件（checkpoint 和 plot 文件）
  - 自动检测数据的空间维度（1D/2D/3D）
  - 解析 AMR 块结构、边界框、坐标
  - 仿真时间/激光脉冲参数的提取
  - 变量元数据 data_config 注册表
  - 派生变量 data_calculator 计算
  - 全场统计、切片分析
  - 提供物理坐标网格的重建
"""

from .flash_hdf5 import (
    FlashHDF5File,
    DataCalculator,
    DATA_CONFIG,
    VAR_ALIASES,
    NA,
)
