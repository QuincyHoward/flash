#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行所有测试并保存输出

此脚本会运行所有测试子目录中的测试，并将输出保存到相应的 test_output.txt 文件中。
"""

import sys
import os
import subprocess
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


# 测试配置
TEST_DIRS = [
    "unit_conversion",
    "loader",
    "derived_variables",
    "shock_position",
    "batch_loading",
    "lazy_loading",
    "dimension_test",
    "parallel",
]

def run_test(test_script: str, output_file: str) -> bool:
    """运行单个测试并保存输出"""
    print(f"\n{'='*60}")
    print(f"运行测试: {test_script}")
    print(f"{'='*60}")
    
    try:
        # 运行测试
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # 合并 stdout 和 stderr
        output = result.stdout
        if result.stderr:
            output += "\n" + "="*60 + "\n"
            output += "STDERR:\n"
            output += "="*60 + "\n"
            output += result.stderr
        
        # 保存输出
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        
        # 打印输出
        print(output)
        
        # 返回结果
        if result.returncode == 0:
            print(f"  ✓ 测试通过")
            return True
        else:
            print(f"  ⚠ 测试失败 (returncode={result.returncode})")
            return False
        
    except subprocess.TimeoutExpired:
        print(f"  ⚠ 测试超时")
        return False
    except Exception as e:
        print(f"  ⚠ 测试运行错误: {e}")
        return False


def main():
    """运行所有测试"""
    print(f"\n{'#'*60}")
    print("# 运行所有测试")
    print(f"{'#'*60}")
    
    # 切换到项目根目录
    os.chdir(PROJECT_ROOT)
    print(f"\n工作目录: {os.getcwd()}")
    
    # 运行所有测试
    results = {}
    for test_dir in TEST_DIRS:
        test_dir_path = os.path.join(PROJECT_ROOT, "output_processors", "test", test_dir)
        if not os.path.exists(test_dir_path):
            print(f"\n⚠ 测试目录不存在: {test_dir_path}")
            continue
        
        # 查找测试脚本
        test_scripts = [f for f in os.listdir(test_dir_path) if f.startswith("test_") and f.endswith(".py")]
        
        for test_script in test_scripts:
            test_script_path = os.path.join(test_dir_path, test_script)
            output_file = os.path.join(test_dir_path, "test_output.txt")
            
            passed = run_test(test_script_path, output_file)
            results[test_script] = passed
    
    # 打印测试摘要
    print(f"\n{'='*60}")
    print("测试摘要")
    print(f"{'='*60}")
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "⚠ 失败"
        print(f"  {test_name}: {status}")
    
    all_passed = all(passed for _, passed in results.items())
    print(f"\n总结果: {'✓ 所有测试通过' if all_passed else '⚠ 部分测试失败'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
