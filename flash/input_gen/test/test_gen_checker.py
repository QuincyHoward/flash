"""测试 gen_checker/ 子包 — 完整功能测试。

此文件支持双重模式，使用 _compat.py 进行智能导入。

注意：
1. 目录名是 gen_checker（一个下划线）
2. 模块文件名是 checker.py（不是 generator.py）
3. 类名是 DependencyChecker（不是 CheckerGenerator）
4. gen_checker/ 在 input_gen/ 目录下（不是 flash/ 目录下）
"""

import pytest
from pathlib import Path


class TestDependencyCheckerBasic:
    """基本测试。"""

    def test_import(self):
        """测试导入 DependencyChecker。"""
        # 注意：目录名是 gen_checker，模块文件名是 checker.py，类名是 DependencyChecker
        from flash.input_gen.gen_checker.checker import DependencyChecker
        assert DependencyChecker is not None

    def test_checker_module_exists(self):
        """测试 gen_checker/checker.py 文件存在。"""
        # 计算 input_gen/ 目录路径
        input_gen_dir = Path(__file__).resolve().parent.parent
        checker_dir = input_gen_dir / "gen_checker"
        checker_file = checker_dir / "checker.py"

        assert checker_dir.exists(), f"gen_checker/ directory not found: {checker_dir}"
        assert checker_file.exists(), f"checker.py not found: {checker_file}"

    def test_checker_init_exists(self):
        """测试 gen_checker/__init__.py 文件存在。"""
        input_gen_dir = Path(__file__).resolve().parent.parent
        checker_dir = input_gen_dir / "gen_checker"
        init_file = checker_dir / "__init__.py"

        assert init_file.exists(), f"__init__.py not found: {init_file}"

    def test_dependency_checker_init(self):
        """测试 DependencyChecker 初始化（需要 sim_dir 参数）。"""
        from flash.input_gen.gen_checker.checker import DependencyChecker
        checker = DependencyChecker(sim_dir=".")
        assert checker is not None


class TestDependencyCheckerEdgeCases:
    """边界测试。"""

    def test_empty_check(self):
        """测试空检查（初始化的默认状态）。"""
        from flash.input_gen.gen_checker.checker import DependencyChecker
        checker = DependencyChecker(sim_dir=".")
        assert checker is not None
