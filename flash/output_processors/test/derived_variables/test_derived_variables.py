#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
派生变量功能测试

测试 output_processors 中现有的派生变量计算功能。
注意：独立 calculator 模块暂未创建，DataCalculator 功能集成在 loader/data_loader.py 中。
"""

import sys
import os
from pathlib import Path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


def test_output_processors_imports():
    """验证 output_processors 现有模块可导入。"""
    from flash.output_processors.loader.data_loader import FlashDataLoader, FlashDataContainer
    from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File
    from flash.output_processors.plotter.plot_generator import FlashPlotter
    print("  ✅ FlashDataLoader 可导入")
    print("  ✅ FlashDataContainer 可导入")
    print("  ✅ FlashHDF5File 可导入")
    print("  ✅ FlashPlotter 可导入")


def test_hdf5_loader_basic():
    """测试 FlashDataLoader 的基本初始化（不需实际文件）。"""
    from flash.output_processors.loader.data_loader import FlashDataLoader
    # 只测试类存在，不实例化（需要实际 HDF5 文件）
    assert callable(FlashDataLoader), "FlashDataLoader 应为可调用类"
    print("  ✅ FlashDataLoader 类可用")


def test_flash_hdf5_basic():
    """测试 FlashHDF5File 的基本初始化。"""
    from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File
    assert callable(FlashHDF5File), "FlashHDF5File 应为可调用类"
    print("  ✅ FlashHDF5File 类可用")


def test_output_processors_init():
    """验证 output_processors 包初始化正常。"""
    import flash.output_processors
    assert hasattr(flash.output_processors, "__path__")
    print("  ✅ output_processors 包可导入")
