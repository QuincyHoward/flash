#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 FlashDataLoader 数据加载功能

比较 FlashDataLoader.load() 与 FlashHDF5File.read_var() 的结果差异
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
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash.output_processors.loader.data_loader import FlashDataLoader
from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File


def test_yt_style_extraction():
    """测试数据加载（普通加载与 HDF5 直接读取的比较）"""

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

    # 方法1: FlashDataLoader 加载
    print("\n" + "="*60)
    print("方法1: FlashDataLoader.load()")
    print("="*60)
    loader1 = FlashDataLoader(test_file)
    container1 = loader1.load(compute_derived=False)

    print(f"  数据形状: dens {container1.data['dens'].shape}")
    print(f"  x 坐标数: {len(container1.x)}")
    print(f"  密度范围: [{np.min(container1.data['dens']):.6e}, {np.max(container1.data['dens']):.6e}]")

    # 方法2: FlashHDF5File 直接读取
    print("\n" + "="*60)
    print("方法2: FlashHDF5File.read_var()")
    print("="*60)
    ff = FlashHDF5File(test_file)
    dens_raw = ff.read_var("dens")
    grid = ff.read_grid()
    x_global = grid["x_global"]
    x_raw = np.concatenate(x_global) if isinstance(x_global, list) else x_global
    d_raw = dens_raw.reshape(-1)
    # 按 x 排序
    idx = np.argsort(x_raw, kind="mergesort")
    x_raw, d_raw = x_raw[idx], d_raw[idx]
    ff.close()

    print(f"  数据形状: dens {d_raw.shape}")
    print(f"  x 坐标数: {len(x_raw)}")
    print(f"  密度范围: [{np.min(d_raw):.6e}, {np.max(d_raw):.6e}]")

    # 比较差异
    print("\n" + "="*60)
    print("差异比较")
    print("="*60)

    # 检查数据点数量
    dens1 = container1.data['dens']
    n1 = dens1.shape[0] if dens1.ndim == 1 else np.prod(dens1.shape)
    n2 = len(d_raw)
    print(f"  数据点数量: Loader={n1}, HDF5={n2}")

    # 比较密度值
    x_loader = container1.x
    if x_loader is not None and len(x_loader) == len(x_raw):
        max_abs_diff = np.max(np.abs(dens1.reshape(-1) - d_raw))
        max_rel_diff = np.max(np.abs(dens1.reshape(-1) - d_raw) / np.maximum(np.abs(d_raw), 1e-30))

        print(f"  最大绝对差异: {max_abs_diff:.6e}")
        print(f"  最大相对差异: {max_rel_diff:.6e}")

        if max_rel_diff < 1e-3:
            print(f"  ✅ 差异很小（相对误差 < 0.1%），两种方法结果一致")
        else:
            print(f"  ⚠️ 差异较大，可能需要进一步检查")
    else:
        print(f"  - 数据点数量不同或 x 坐标不可用，跳过直接比较")

    # 保存结果到文件
    output_dir = os.path.join(os.path.dirname(__file__), "test_output")
    os.makedirs(output_dir, exist_ok=True)

    # 保存 Loader 结果
    output1 = os.path.join(output_dir, "dens_loader.csv")
    with open(output1, "w") as f:
        f.write("x_cm,dens_g_per_cm3\n")
        x_arr = container1.x if container1.x is not None else np.arange(len(dens1.reshape(-1)))
        for x_val, d_val in zip(x_arr, dens1.reshape(-1)):
            f.write(f"{x_val},{d_val}\n")
    print(f"\n  Loader 结果已保存: {output1}")

    # 保存 HDF5 直接读取结果
    output2 = os.path.join(output_dir, "dens_hdf5.csv")
    with open(output2, "w") as f:
        f.write("x_cm,dens_g_per_cm3\n")
        for x_val, d_val in zip(x_raw, d_raw):
            f.write(f"{x_val},{d_val}\n")
    print(f"  HDF5 直接读取结果已保存: {output2}")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    test_yt_style_extraction()
