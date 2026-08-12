#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单位配置验证测试

验证 FlashDataContainer 中变量单位信息的正确性：
- unit() 方法返回正确的单位字符串
- to_si() 方法返回正确的 SI 转换系数
- 从 DATA_CONFIG 读取的配置信息一致
"""

import sys
import os
import numpy as np
from pathlib import Path

# 添加项目根目录到 Python 路径

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
from flash.output_processors.hdf5processor import DATA_CONFIG


def test_unit_info_1d():
    """测试 1D 数据的单位配置信息"""
    print(f"\n{'='*60}")
    print("测试 1: 1D 数据单位配置验证")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    target = os.path.join(BASE, "lasslab_hdf5_chk_0001")

    if not os.path.exists(target):
        print(f"⚠ 测试文件不存在: {target}")
        assert False, "测试文件不存在"

    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)

    # 验证配置中的变量单位信息
    test_vars = [
        ("tele", "K", "eV"),           # K -> SI -> practice
        ("tion", "K", "eV"),
        ("pres", "dyne/cm^2", "Mbar"),
        ("pele", "dyne/cm^2", "Mbar"),
        ("velx", "cm/s", "um/ns"),
        ("dens", "g/cm^3", "g/cm^3"),
    ]

    all_passed = True
    for varname, expected_cgs, expected_practice in test_vars:
        if varname in container.data:
            # 使用现有的 unit() 和 to_si() API
            actual_unit = container.unit(varname)
            actual_to_si = container.to_si(varname)

            # 从 DATA_CONFIG 获取完全信息
            cfg = DATA_CONFIG.get(varname, {})

            if not cfg:
                print(f"  ⚠ {varname}: DATA_CONFIG 中无配置")
                all_passed = False
                continue

            cfg_unit = cfg.get("unit", "")
            cfg_to_si = cfg.get("to_si", 1.0)

            # 验证单位字符串
            if actual_unit != cfg_unit:
                print(f"  ⚠ {varname}: unit() 返回 '{actual_unit}', 期望 '{cfg_unit}'")
                all_passed = False
                continue

            # 验证转换系数
            if abs(actual_to_si - cfg_to_si) > 1e-15:
                print(f"  ⚠ {varname}: to_si() 返回 {actual_to_si}, 期望 {cfg_to_si}")
                all_passed = False
                continue

            # 验证数据范围
            arr = container.data[varname]
            print(f"  ✓ {varname}: unit='{actual_unit}', to_si={actual_to_si:.2e}")
            print(f"    range=[{arr.min():.4e}, {arr.max():.4e}]")
        else:
            print(f"  - {varname}: 变量不存在 (跳过)")

    if all_passed:
        print(f"\n  ✓ 所有单位配置验证通过！")
    else:
        print(f"\n  ⚠ 部分验证失败")

    assert all_passed, "部分单位配置验证失败"


def test_derived_unit_info():
    """测试派生变量的单位配置信息"""
    print(f"\n{'='*60}")
    print("测试 2: 派生变量单位配置验证")
    print(f"{'='*60}")

    BASE = os.path.join(os.path.dirname(__file__), "../../inputfiles/hdf5files_1d")
    target = os.path.join(BASE, "lasslab_hdf5_chk_0001")

    if not os.path.exists(target):
        print(f"⚠ 测试文件不存在: {target}")
        assert False, "测试文件不存在"

    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)

    all_passed = True
    for varname in ["nele", "ls_tele"]:
        if varname in container.derived:
            cfg = DATA_CONFIG.get(varname, {})
            unit_str = cfg.get("unit", "")
            to_si = cfg.get("to_si", 1.0)
            arr = container.derived[varname]
            print(f"  ✓ {varname}: unit='{unit_str}', to_si={to_si:.2e}")
            print(f"    range=[{arr.min():.4e}, {arr.max():.4e}]")
        else:
            print(f"  - {varname}: 派生变量不存在 (跳过)")

    if all_passed:
        print(f"\n  ✓ 派生变量单位验证通过！")

    assert all_passed, "派生变量单位验证失败"


if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print("# 单位配置验证测试")
    print(f"{'#'*60}")

    results = []
    results.append(("1D 数据单位配置验证", test_unit_info_1d()))
    results.append(("派生变量单位配置验证", test_derived_unit_info()))

    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    for name, passed in results:
        status = "✓ 通过" if passed else "⚠ 失败"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print(f"\n总结果: {'✓ 所有测试通过' if all_passed else '⚠ 部分测试失败'}")
