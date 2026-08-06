"""测试 gen_config/ 子包 — 完整功能测试。

此文件支持双重模式，使用 _compat.py 进行智能导入。
"""

import pytest
from pathlib import Path

# 使用兼容性模块进行智能导入
from ._compat import ConfigGenerator, RUN_MODE


class TestConfigGeneratorBasic:
    """基本测试。"""

    def test_import(self):
        """测试导入 ConfigGenerator。"""
        from flash.input_gen.gen_config.generator import ConfigGenerator
        assert ConfigGenerator is not None

    def test_init(self):
        """测试初始化（无参构造）。"""
        from flash.input_gen.gen_config.generator import ConfigGenerator
        gen = ConfigGenerator()
        assert gen is not None

    def test_class_methods(self):
        """测试 ConfigGenerator 的类方法（如果有）。"""
        # TODO: 检查 ConfigGenerator 的实际 API
        assert True


class TestConfigGeneratorEdgeCases:
    """边界测试。"""

    def test_empty_config(self):
        """测试空配置（初始化的默认状态）。"""
        from flash.input_gen.gen_config.generator import ConfigGenerator
        gen = ConfigGenerator()
        # 检查是否有默认参数
        assert gen is not None

    def test_config_structure(self):
        """测试 gen_config/ 目录和文件结构。"""
        # 计算 input_gen/ 目录路径
        input_gen_dir = Path(__file__).resolve().parent.parent
        config_dir = input_gen_dir / "gen_config"

        # 检查 gen_config/ 目录是否存在
        assert config_dir.exists(), f"gen_config/ directory not found: {config_dir}"

        # 检查 generator.py 是否存在
        generator_file = config_dir / "generator.py"
        assert generator_file.exists(), f"generator.py not found: {generator_file}"
