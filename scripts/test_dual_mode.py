#!/usr/bin/env python3
"""
测试 flash 独立包模式下的导入功能。

运行方法：
   cd /path/to/flash/            # 项目根
   python -m scripts.test_dual_mode
"""

import sys
import os
from pathlib import Path


def test_imports():
    """测试 flash 独立包模式的导入。"""
    print("🔍 Testing imports in standalone mode...")
    print()

    try:
        from flash.input_gen.gen_par.generator import ParGeneratorExtended

        print("  ✅ Import ParGeneratorExtended (standalone mode)")
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")

    try:
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator

        print("  ✅ Import ShellScriptGenerator (standalone mode)")
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")


def test_pytest():
    """测试 pytest 运行。"""
    print()
    print("🧪 Testing pytest in standalone mode...")
    print()

    import subprocess

    cmd = [sys.executable, "-m", "pytest", "flash/input_gen/test/test_gen_par.py", "-v", "--tb=no"]

    print(f"  - Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).resolve().parent.parent.parent)

    # 打印输出（只打印最后 20 行）
    lines = result.stdout.strip().split("\n")
    for line in lines[-20:]:
        print(f"    {line}")

    if result.returncode == 0:
        print()
        print("  ✅ pytest passed!")
    else:
        print()
        print("  ❌ pytest failed!")


def main():
    """主函数。"""
    print("=" * 60)
    print("Flash Standalone Package Import Test")
    print("=" * 60)
    print()

    print("📙 Current mode: standalone (flash 独立包)")
    print()

    # 测试导入
    test_imports()

    # 测试 pytest
    test_pytest()

    print()
    print("=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
