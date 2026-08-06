#!/usr/bin/env python3

import sys
import os
import time
from pathlib import Path

# -*- coding: utf-8 -*-
"""
批量加载与容器元数据测试

测试 FlashDataLoader 和 FlashDataContainer 的核心功能：
- 单个文件加载与元数据访问
- 批量文件夹加载 (load_folder)
- 批量与单文件加载的数据一致性
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


def test_container_metadata():
    """测试 FlashDataContainer 的元数据访问"""
    print(f"\n{'='*60}")
    print("测试 1: 容器元数据访问")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    target = os.path.join(BASE, "lasslab_hdf5_chk_0001")

    if not os.path.exists(target):
        print(f"⚠ 测试文件不存在: {target}")
        assert False, "测试文件不存在"

    # 加载
    print(f"\n加载文件...")
    start = time.time()
    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)
    load_time = time.time() - start
    print(f"  加载时间: {load_time:.4f}s")

    # 检查元数据
    print(f"\n  元数据:")
    print(f"    时间: {container.simulation_time:.4e}s")
    print(f"    步数: {container.simulation_step}")
    print(f"    维度: {container.ndim}D")
    print(f"    块数: {container.nblocks}")
    print(f"    变量数: {len(container.data)}")

    # 检查数据访问
    dens = container.data["dens"]
    print(f"  密度形状: {dens.shape}")
    print(f"  密度范围: [{dens.min():.4e}, {dens.max():.4e}]")

    # 检查派生变量
    if container.derived:
        print(f"  派生变量数: {len(container.derived)}")
        for vname in list(container.derived.keys())[:3]:
            print(f"    {vname}: shape={container.derived[vname].shape}")

    print(f"\n  ✓ 容器元数据测试通过")


def test_folder_loading():
    """测试 FlashDataLoader.load_folder() 批量加载"""
    print(f"\n{'='*60}")
    print("测试 2: 批量文件夹加载 (load_folder)")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")

    if not os.path.exists(BASE):
        print(f"⚠ 测试文件夹不存在: {BASE}")
        assert False, "测试文件夹不存在"

    # 批量加载
    print(f"\n批量加载文件夹: {BASE}")
    start = time.time()
    containers = FlashDataLoader.load_folder(BASE, pattern="*chk*", compute_derived=False)
    load_time = time.time() - start

    print(f"  创建了 {len(containers)} 个容器")
    print(f"  加载总时间: {load_time:.4f}s")
    print(f"  平均每个文件: {load_time / len(containers) * 1000:.2f}ms" if containers else "  (无文件)")

    # 检查元数据（不访问 data 验证这是"懒"的）
    if containers:
        print(f"\n  前 5 个文件的元数据:")
        for i, c in enumerate(containers[:5]):
            print(f"    {i+1}. t={c.simulation_time:.4e}s, vars={len(c.data)}")

    print(f"\n  ✓ 批量加载测试通过")


def test_single_vs_batch_consistency():
    """对比单文件加载与批量加载的数据一致性"""
    print(f"\n{'='*60}")
    print("测试 3: 单文件 vs 批量加载一致性")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")

    if not os.path.exists(BASE):
        print(f"⚠ 测试文件夹不存在: {BASE}")
        assert False, "测试文件夹不存在"

    # 单文件加载
    print(f"\n单文件加载...")
    start = time.time()
    loader = FlashDataLoader(os.path.join(BASE, "lasslab_hdf5_chk_0001"))
    single = loader.load(compute_derived=False)
    single_time = time.time() - start
    print(f"  时间: {single_time:.4f}s")

    # 批量加载
    print(f"\n批量加载...")
    start = time.time()
    batch_list = FlashDataLoader.load_folder(BASE, pattern="*chk_0001", compute_derived=False)
    batch_time = time.time() - start
    if not batch_list:
        print(f"  ⚠ 批量加载未找到文件")
        assert False, "批量加载未找到文件"

    batch = batch_list[0]
    print(f"  时间: {batch_time:.4f}s")

    # 验证数据一致性
    print(f"\n验证数据一致性...")
    all_consistent = True

    if single.simulation_time != batch.simulation_time:
        print(f"  ⚠ simulation_time 不一致: {single.simulation_time} vs {batch.simulation_time}")
        all_consistent = False
    else:
        print(f"  ✓ simulation_time 一致 ({single.simulation_time:.4e}s)")

    if single.data["dens"].shape != batch.data["dens"].shape:
        print(f"  ⚠ dens shape 不一致: {single.data['dens'].shape} vs {batch.data['dens'].shape}")
        all_consistent = False
    else:
        print(f"  ✓ dens shape 一致 ({single.data['dens'].shape})")

    if all_consistent:
        print(f"\n  ✓ 数据一致性测试通过")
    else:
        print(f"\n  ⚠ 数据一致性存在差异")

    assert all_consistent, "数据一致性存在差异"


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print("# 批量加载与容器元数据测试")
    print(f"{'#'*60}")

    results = []
    results.append(("容器元数据访问", test_container_metadata()))
    results.append(("批量文件夹加载", test_folder_loading()))
    results.append(("单文件 vs 批量一致性", test_single_vs_batch_consistency()))

    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    for name, passed in results:
        status = "✓ 通过" if passed else "⚠ 失败"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print(f"\n总结果: {'✓ 所有测试通过' if all_passed else '⚠ 部分测试失败'}")
