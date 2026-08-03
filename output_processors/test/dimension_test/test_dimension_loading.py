#!/usr/bin/env python3

import sys
import os
import numpy as np
from pathlib import Path

# -*- coding: utf-8 -*-
"""
1D/2D/3D 数据加载测试

测试 FlashDataLoader 对 1D、2D、3D 数据的加载能力。
"""

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash.output_processors.loader.data_loader import FlashDataLoader


def test_1d_loading():
    """测试 1D 数据加载"""
    print(f"\n{'='*60}")
    print("测试 1: 1D 数据加载")
    print(f"{'='*60}")
    
    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    target = os.path.join(BASE, "lasslab_hdf5_chk_0001")
    
    if not os.path.exists(target):
        print(f"⚠ 测试文件不存在: {target}")
        assert False, "测试文件不存在"
    
    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)
    
    # 检查维度
    if container.ndim != 1:
        print(f"  ⚠ 维度错误: 期望 1D, 实际 {container.ndim}D")
        assert False, "维度错误: 期望 1D"
    
    print(f"  维度: {container.ndim}D ✓")
    print(f"  块数: {container.nblocks}")
    print(f"  每块网格数: nx={container.nx}")
    
    # 检查坐标
    if container.x is None:
        print(f"  ⚠ x 坐标不存在")
        assert False, "x 坐标不存在"
    
    print(f"  x 坐标: shape={container.x.shape}")
    print(f"  x range: [{container.x.min():.6e}, {container.x.max():.6e}]")
    
    # 检查数据
    if "dens" not in container.data:
        print(f"  ⚠ dens 变量不存在")
        assert False, "dens 变量不存在"
    
    dens = container.data["dens"]
    print(f"  dens shape: {dens.shape}")
    
    # 检查单位转换 (使用现有 API)
    tele_unit = container.unit("tele")
    tele_to_si = container.to_si("tele")
    print(f"  tele: unit='{tele_unit}', to_si={tele_to_si:.2e}")
    
    print(f"\n  ✓ 1D 数据加载测试通过")


def test_2d_loading():
    """测试 2D 数据加载"""
    print(f"\n{'='*60}")
    print("测试 2: 2D 数据加载")
    print(f"{'='*60}")
    
    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_2d")
    
    if not os.path.exists(BASE):
        print(f"⚠ 测试文件夹不存在: {BASE}")
        assert False, "测试文件夹不存在"
    
    # 查找第一个文件
    files = os.listdir(BASE)
    if len(files) == 0:
        print(f"  ⚠ 文件夹为空")
        assert False, "文件夹为空"
    
    target = os.path.join(BASE, files[0])
    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)
    
    # 检查维度
    if container.ndim != 2:
        print(f"  ⚠ 维度错误: 期望 2D, 实际 {container.ndim}D")
        assert False, "维度错误: 期望 2D"
    
    print(f"  维度: {container.ndim}D ✓")
    print(f"  块数: {container.nblocks}")
    print(f"  每块网格数: nx={container.nx}, ny={container.ny}")
    
    # 检查坐标
    if container.x is None:
        print(f"  ⚠ x 坐标不存在")
        assert False, "x 坐标不存在"
    
    if container.y is None:
        print(f"  ⚠ y 坐标不存在")
        assert False, "y 坐标不存在"
    
    print(f"  x 坐标: shape={container.x.shape}")
    print(f"  y 坐标: shape={container.y.shape}")
    print(f"  x range: [{container.x.min():.6e}, {container.x.max():.6e}]")
    print(f"  y range: [{container.y.min():.6e}, {container.y.max():.6e}]")
    
    # 检查数据
    if "dens" not in container.data:
        print(f"  ⚠ dens 变量不存在")
        assert False, "dens 变量不存在"
    
    dens = container.data["dens"]
    print(f"  dens shape: {dens.shape}")
    
    print(f"\n  ✓ 2D 数据加载测试通过")


def test_3d_loading():
    """测试 3D 数据加载"""
    print(f"\n{'='*60}")
    print("测试 3: 3D 数据加载")
    print(f"{'='*60}")
    
    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_3d")
    
    if not os.path.exists(BASE):
        print(f"⚠ 测试文件夹不存在: {BASE}")
        assert False, "测试文件夹不存在"
    
    # 查找第一个文件
    files = os.listdir(BASE)
    if len(files) == 0:
        print(f"  ⚠ 文件夹为空")
        assert False, "文件夹为空"
    
    target = os.path.join(BASE, files[0])
    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)
    
    # 检查维度
    if container.ndim != 3:
        print(f"  ⚠ 维度错误: 期望 3D, 实际 {container.ndim}D")
        assert False, "维度错误: 期望 3D"
    
    print(f"  维度: {container.ndim}D ✓")
    print(f"  块数: {container.nblocks}")
    print(f"  每块网格数: nx={container.nx}, ny={container.ny}, nz={container.nz}")
    
    # 检查坐标
    if container.x is None:
        print(f"  ⚠ x 坐标不存在")
        assert False, "x 坐标不存在"
    
    if container.y is None:
        print(f"  ⚠ y 坐标不存在")
        assert False, "y 坐标不存在"
    
    if container.z is None:
        print(f"  ⚠ z 坐标不存在")
        assert False, "z 坐标不存在"
    
    print(f"  x 坐标: shape={container.x.shape}")
    print(f"  y 坐标: shape={container.y.shape}")
    print(f"  z 坐标: shape={container.z.shape}")
    print(f"  x range: [{container.x.min():.6e}, {container.x.max():.6e}]")
    print(f"  y range: [{container.y.min():.6e}, {container.y.max():.6e}]")
    print(f"  z range: [{container.z.min():.6e}, {container.z.max():.6e}]")
    
    # 检查数据
    if "dens" not in container.data:
        print(f"  ⚠ dens 变量不存在")
        assert False, "dens 变量不存在"
    
    dens = container.data["dens"]
    print(f"  dens shape: {dens.shape}")
    
    print(f"\n  ✓ 3D 数据加载测试通过")


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print("# 1D/2D/3D 数据加载测试")
    print(f"{'#'*60}")
    
    results = []
    results.append(("1D 数据加载", test_1d_loading()))
    results.append(("2D 数据加载", test_2d_loading()))
    results.append(("3D 数据加载", test_3d_loading()))
    
    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    for name, passed in results:
        status = "✓ 通过" if passed else "⚠ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    print(f"\n总结果: {'✓ 所有测试通过' if all_passed else '⚠ 部分测试失败'}")
