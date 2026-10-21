"""
io 子包 — 文件 I/O 与数据持久化

包含:
  - flash_reader:   FLASH HDF5 输出读取
  - result_saver:   分析结果保存 (CSV/NPZ/JSON)
  - input_saver:    FLASH 输入文件保存 (.par / pulse / params)
"""

from __future__ import annotations

from .flash_reader import (
    read_flash_hdf5_center,
    read_flash_output_timeseries,
    build_raw_from_engine,
)
from .result_saver import (
    save_analysis_csv,
    save_analysis_npz,
    save_analysis_json,
    save_analysis_data,
)
from .input_saver import (
    save_flash_input,
    save_pulse_data,
    save_input_params,
)

__all__ = [
    "read_flash_hdf5_center",
    "read_flash_output_timeseries",
    "build_raw_from_engine",
    "save_analysis_csv",
    "save_analysis_npz",
    "save_analysis_json",
    "save_analysis_data",
    "save_flash_input",
    "save_pulse_data",
    "save_input_params",
]
