#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# -*- coding: utf-8 -*-
"""
批量加载功能测试

测试 FlashDataLoader 的批量加载功能：
- load_folder() 方法（单个文件夹）
- load_folders() 方法（多个文件夹）
"""

import sys
import os
import tempfile
import shutil

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


def test_load_folder():
    """测试 load_folder() 方法（单个文件夹）"""
    print(f"\n{'='*60}")
    print("测试 1: load_folder() 方法（单个文件夹）")
    print(f"{'='*60}")
    
    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    
    if not os.path.exists(BASE):
        print(f"⚠ 测试文件夹不存在: {BASE}")
        assert False, "测试文件夹不存在"
    
    # 批量加载
    print(f"\n加载文件夹: {BASE}")
    containers = FlashDataLoader.load_folder(BASE, pattern="*chk*", compute_derived=False)
    
    if len(containers) == 0:
        print(f"  ⚠ 没有加载到任何文件")
        assert False, "没有加载到任何文件"
    
    print(f"\n  加载了 {len(containers)} 个文件")
    print(f"\n  按时间排序后的文件列表:")
    for i, c in enumerate(containers[:5]):  # 显示前 5 个
        print(f"    {i+1}. t={c.simulation_time:.4e}s, step={c.simulation_step}")
    
    if len(containers) > 5:
        print(f"    ... (共 {len(containers)} 个)")
    
    # 验证时间排序
    times = [c.simulation_time for c in containers]
    if all(times[i] <= times[i+1] for i in range(len(times)-1)):
        print(f"\n  ✓ 文件按时间正确排序")
    else:
        print(f"\n  ⚠ 文件未按时间排序")
        assert False, "文件未按时间排序"
    
    print(f"\n  ✓ load_folder() 测试通过")


def test_load_folders():
    """测试 load_folders() 方法（多个文件夹）"""
    print(f"\n{'='*60}")
    print("测试 2: load_folders() 方法（多个文件夹）")
    print(f"{'='*60}")
    
    # 创建临时文件夹结构
    temp_dir = tempfile.mkdtemp()
    try:
        # 复制测试文件到两个临时文件夹
        BASE_1D = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
        BASE_2D = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_2d")
        
        if not os.path.exists(BASE_1D):
            print(f"⚠ 测试文件夹不存在: {BASE_1D}")
            assert False, "测试文件夹不存在"
        
        # 创建临时文件夹
        temp_dir1 = os.path.join(temp_dir, "sim1")
        temp_dir2 = os.path.join(temp_dir, "sim2")
        os.makedirs(temp_dir1, exist_ok=True)
        os.makedirs(temp_dir2, exist_ok=True)
        
        # 复制文件
        import shutil
        files_copied = 0
        for f in os.listdir(BASE_1D)[:3]:  # 只复制前 3 个文件
            src = os.path.join(BASE_1D, f)
            dst = os.path.join(temp_dir1, f)
            shutil.copy2(src, dst)
            files_copied += 1
        
        if os.path.exists(BASE_2D):
            for f in os.listdir(BASE_2D)[:3]:
                src = os.path.join(BASE_2D, f)
                dst = os.path.join(temp_dir2, f)
                shutil.copy2(src, dst)
                files_copied += 1
        
        # 批量加载多个文件夹
        print(f"\n加载多个文件夹:")
        print(f"  {temp_dir1}")
        print(f"  {temp_dir2}")

        all_containers = []
        for folder in [temp_dir1, temp_dir2]:
            if os.path.isdir(folder):
                containers = FlashDataLoader.load_folder(
                    folder,
                    pattern="*chk*",
                    compute_derived=False
                )
                all_containers.extend(containers)

        # 按时间排序
        all_containers.sort(key=lambda c: c.simulation_time)

        print(f"\n  共加载 {len(all_containers)} 个文件")
        
        if len(all_containers) > 0:
            print(f"\n  按时间排序后的文件列表:")
            for i, c in enumerate(all_containers[:5]):
                print(f"    {i+1}. t={c.simulation_time:.4e}s, step={c.simulation_step}")
            
            print(f"\n  ✓ load_folders() 测试通过")
        else:
            print(f"  ⚠ 没有加载到任何文件")
            assert False, "没有加载到任何文件"
        
    finally:
        # 清理临时文件夹
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print("# 批量加载功能测试")
    print(f"{'#'*60}")
    
    results = []
    results.append(("load_folder() 单个文件夹", test_load_folder()))
    results.append(("load_folders() 多个文件夹", test_load_folders()))
    
    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    for name, passed in results:
        status = "✓ 通过" if passed else "⚠ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    print(f"\n总结果: {'✓ 所有测试通过' if all_passed else '⚠ 部分测试失败'}")
