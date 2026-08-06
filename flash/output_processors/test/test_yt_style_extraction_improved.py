#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 FlashHDF5File 数据提取方式比较

比较 read_var() + read_grid() (现有 API) 与 hdf5_to_csv 风格提取的结果
"""

import sys
import os
import numpy as np
from pathlib import Path

# 添加项目根目录到路径

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None  # 已安装环境 (site-packages): 静默跳过
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File
from flash.output_processors.loader.data_loader import FlashDataLoader


def extract_var_flatten(hdf5_file, var_name='dens'):
    """使用 FlashHDF5File 现有 API 提取扁平化数据"""
    with FlashHDF5File(hdf5_file) as f:
        data = f.read_var(var_name)  # (nblocks, nx)
        grid = f.read_grid()
        x_global = grid["x_global"]  # list of per-block x arrays
        x_flat = np.concatenate(x_global) if isinstance(x_global, list) else x_global
        d_flat = data.reshape(-1)
        # Sort by x
        idx = np.argsort(x_flat, kind="mergesort")
        return x_flat[idx], d_flat[idx]


def test_yt_style_extraction_improved():
    """测试数据提取方式比较"""

    # 查找测试文件
    test_dir = os.path.join(os.path.dirname(__file__), "../inputfiles/hdf5files_1d")
    if not os.path.exists(test_dir):
        print(f"测试目录不存在: {test_dir}")
        return

    # 查找 HDF5 文件
    hdf5_files = [f for f in os.listdir(test_dir) if "plt_cnt" in f or "chk" in f]
    if not hdf5_files:
        print(f"未找到 HDF5 文件 in {test_dir}")
        return

    test_file = os.path.join(test_dir, hdf5_files[0])
    print(f"测试文件: {test_file}")

    # 方法1: extract_var_flatten (现有 API)
    print("\n" + "="*60)
    print("方法1: extract_var_flatten (现有 API)")
    print("="*60)
    x1, dens1 = extract_var_flatten(test_file, "dens")

    print(f"  数据形状: dens {dens1.shape}")
    print(f"  x 坐标数: {len(x1)}")
    print(f"  密度范围: [{np.min(dens1):.6e}, {np.max(dens1):.6e}]")

    # 方法2: FlashDataLoader (参考)
    print("\n" + "="*60)
    print("方法2: FlashDataLoader (参考)")
    print("="*60)
    loader = FlashDataLoader(test_file)
    container = loader.load(compute_derived=False)

    dens2 = container.data["dens"]
    x2 = container.x

    if x2 is not None:
        dens2_flat = dens2.reshape(-1)
        x2_flat = x2.reshape(-1) if hasattr(x2, 'reshape') else x2
        print(f"  数据形状: dens {dens2_flat.shape}")
        print(f"  x 坐标数: {len(x2_flat)}")
        print(f"  密度范围: [{np.min(dens2_flat):.6e}, {np.max(dens2_flat):.6e}]")
    else:
        print(f"  x 坐标不可用")
        dens2_flat = dens2.reshape(-1) if hasattr(dens2, 'reshape') else dens2

    # 比较差异
    print("\n" + "="*60)
    print("差异比较: extract_var_flatten vs FlashDataLoader")
    print("="*60)

    n1 = len(dens1)
    n2 = len(dens2_flat) if 'dens2_flat' in dir() else dens2.shape[0]
    print(f"  数据点数量: extract={n1}, Loader={n2}")

    if n1 == n2 and x2 is not None:
        x2_f = x2_flat
        max_abs_diff = np.max(np.abs(dens1 - dens2_flat))
        max_rel_diff = np.max(np.abs(dens1 - dens2_flat) / np.maximum(np.abs(dens2_flat), 1e-30))

        print(f"  最大绝对差异: {max_abs_diff:.6e}")
        print(f"  最大相对差异: {max_rel_diff:.6e}")

        if max_rel_diff < 1e-3:
            print(f"  ✅ 差异很小（相对误差 < 0.1%），结果一致")
        else:
            print(f"  ⚠️ 差异较大，可能需要进一步检查")
    else:
        print(f"  - 数据点数量不同或 x 坐标不可用，使用插值比较")
        if x2 is not None and len(x1) > 0 and len(x2_flat) > 0:
            dens1_interp = np.interp(x2_flat, x1, dens1)
            max_abs_diff = np.max(np.abs(dens1_interp - dens2_flat))
            max_rel_diff = np.max(np.abs(dens1_interp - dens2_flat) / np.maximum(np.abs(dens2_flat), 1e-30))
            print(f"  最大绝对差异 (插值后): {max_abs_diff:.6e}")
            print(f"  最大相对差异 (插值后): {max_rel_diff:.6e}")
            if max_rel_diff < 1e-3:
                print(f"  ✅ 差异很小（相对误差 < 0.1%），结果一致")
            else:
                print(f"  ⚠️ 差异较大，可能需要进一步检查")
        else:
            print(f"  - 无法比较")

    # 与 yt 的比较（如果可用）
    print("\n" + "="*60)
    print("与 yt 的比较")
    print("="*60)
    print(f"  注意: 需要与 yt 提取的结果进行比较")
    print(f"  yt 提取的点数通常为 block 总单元格数")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    test_yt_style_extraction_improved()
