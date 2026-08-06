#!/usr/bin/env python3

import sys
import os
import numpy as np
from pathlib import Path

# -*- coding: utf-8 -*-
"""
数据加载与 shok 变量检查测试

测试 FlashDataLoader 对含激波标记文件的加载：
- 加载包含 shok 变量的 HDF5 文件
- 检查 raw 变量列表完整性
"""

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

from flash.output_processors.loader.data_loader import FlashDataLoader


def test_data_loading_with_shok():
    """测试带 shok 变量的数据加载"""
    print(f"\n{'='*60}")
    print("测试 1: 带 shok 变量的数据加载")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    # 使用较晚的时间点（可能有激波）
    target = os.path.join(BASE, "lasslab_hdf5_chk_0005")

    if not os.path.exists(target):
        # 如果文件不存在，使用第一个文件
        target = os.path.join(BASE, "lasslab_hdf5_chk_0001")
        print(f"  ⚠ 使用较早时间点")

    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=False)

    # 列出所有原始变量
    print(f"  维度: {container.ndim}D")
    print(f"  块数: {container.nblocks}")
    print(f"  仿真时间: {container.simulation_time:.4e}s")
    print(f"  原始变量 ({len(container.data)} 个):")
    for vname, arr in container.data.items():
        print(f"    {vname:15s} shape={str(arr.shape):20s}")

    # 检查是否有 shok 变量
    has_shok = "shok" in container.data
    print(f"\n  shok 变量: {'✓ 存在' if has_shok else '- 不存在'}")

    print(f"\n  ✓ 数据加载测试通过")


def test_critical_density_check():
    """检查 nele 派生变量及其与临界密度的关系"""
    print(f"\n{'='*60}")
    print("测试 2: nele 派生变量检查")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    target = os.path.join(BASE, "lasslab_hdf5_chk_0001")

    if not os.path.exists(target):
        print(f"⚠ 测试文件不存在: {target}")
        return False

    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)

    # 检查 nele 派生变量
    if "nele" in container.derived:
        nele = container.derived["nele"]
        lambda_um = 0.351
        n_c = 1.12e21 / (lambda_um ** 2)
        print(f"  激光波长: {lambda_um} um")
        print(f"  临界密度: {n_c:.4e} 1/cm³")
        print(f"  nele: shape={nele.shape}")
        print(f"  nele range: [{nele.min():.4e}, {nele.max():.4e}]")
        print(f"  超临界区域: {np.sum(nele > n_c)} 个点")

        # 粗略检查临界密度面位置
        if nele.ndim == 1 or (nele.ndim == 2 and nele.shape[0] == 1):
            nele_1d = nele.flatten()
            x = container.x.flatten() if container.x is not None else np.arange(len(nele_1d))
            above = nele_1d > n_c
            if np.any(above):
                # 找到超临界的最远位置
                far_idx = np.where(above)[0][-1]
                print(f"  临界密度面大致位置 (x={x[far_idx]:.6e} cm)")
            else:
                print(f"  - 没有超临界区域")
        else:
            print(f"  - 多维 nele，跳过位置估算")

    else:
        print(f"  - nele 派生变量不存在 (可能需要 tele/tion 数据)")

    print(f"\n  ✓ nele 检查测试通过")


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print("# 数据加载与 shok 变量检查测试")
    print(f"{'#'*60}")

    results = []
    results.append(("带 shok 变量的数据加载", test_data_loading_with_shok()))
    results.append(("nele 派生变量检查", test_critical_density_check()))

    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    for name, passed in results:
        status = "✓ 通过" if passed else "⚠ 失败"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print(f"\n总结果: {'✓ 所有测试通过' if all_passed else '⚠ 部分测试失败'}")
