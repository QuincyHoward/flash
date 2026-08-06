"""测试 gen_shell_script/ 子包 — 完整功能测试。

此文件支持双重模式，使用 _compat.py 进行智能导入。
"""

import pytest
from pathlib import Path
import tempfile


class TestShellScriptGeneratorBasic:
    """基本测试。"""

    def test_import(self):
        """测试导入 ShellScriptGenerator。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        assert ShellScriptGenerator is not None

    def test_init_default(self):
        """测试默认初始化。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator()
        assert gen is not None
        assert gen.config is not None
        assert "dimension" in gen.config
        assert "platform" in gen.config

    def test_init_with_config(self):
        """测试使用自定义配置初始化。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"dimension": 2, "platform": "hpc"})
        assert gen.config["dimension"] == 2
        assert gen.config["platform"] == "hpc"


class TestShellScriptGeneratorGenerate:
    """生成脚本测试。"""

    def test_generate_wsl_script(self):
        """测试生成 WSL 脚本（返回字符串）。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"dimension": 1, "platform": "local"})
        content = gen.generate_wsl_script()
        assert isinstance(content, str)
        assert len(content) > 0
        assert "#!/bin/bash" in content
        assert "FLASH_HOME" in content

    def test_generate_slurm_script(self):
        """测试生成 SLURM 脚本（返回字符串）。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"dimension": 1, "platform": "hpc"})
        content = gen.generate_slurm_script()
        assert isinstance(content, str)
        assert len(content) > 0
        assert "#!/bin/bash" in content
        assert "#SBATCH" in content

    def test_generate_windows_script(self):
        """测试生成 Windows 脚本（返回字符串）。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"dimension": 1, "platform": "local"})
        content = gen.generate_windows_script()
        assert isinstance(content, str)
        assert len(content) > 0
        assert "@echo off" in content


class TestShellScriptGeneratorSave:
    """保存脚本测试。"""

    def test_save_wsl_script(self, tmp_path):
        """测试保存 WSL 脚本到文件。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"dimension": 1, "platform": "local"})
        content = gen.generate_wsl_script()

        # 手动保存到文件
        script_path = tmp_path / "run_flash.sh"
        script_path.write_text(content, encoding="utf-8")

        assert script_path.exists()
        assert script_path.stat().st_size > 0
        assert "#!/bin/bash" in script_path.read_text(encoding="utf-8")

    def test_save_slurm_script(self, tmp_path):
        """测试保存 SLURM 脚本到文件。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"dimension": 1, "platform": "hpc"})
        content = gen.generate_slurm_script()

        # 手动保存到文件
        script_path = tmp_path / "run_flash.slurm"
        script_path.write_text(content, encoding="utf-8")

        assert script_path.exists()
        assert script_path.stat().st_size > 0
        assert "#SBATCH" in script_path.read_text(encoding="utf-8")


class TestShellScriptGeneratorClassMethods:
    """类方法测试。"""

    def test_load_resource_config(self):
        """测试 load_resource_config 类方法。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        config = ShellScriptGenerator.load_resource_config()
        assert isinstance(config, dict)
        assert "local" in config or "hpc" in config

    def test_get_dimension_config(self):
        """测试 get_dimension_config 类方法。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        dim_config = ShellScriptGenerator.get_dimension_config(dimension=1, platform="local")
        assert isinstance(dim_config, dict)

    def test_build_setup_cmd(self):
        """测试 build_setup_cmd 静态方法。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        cmd = ShellScriptGenerator.build_setup_cmd()
        assert isinstance(cmd, str)
        assert "./setup" in cmd

    def test_extract_sim_path(self):
        """测试 extract_sim_path 静态方法。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        cmd = "./setup -auto LaserSlab -1d +cartesian"
        sim_path = ShellScriptGenerator.extract_sim_path(cmd)
        assert sim_path == "LaserSlab"


class TestShellScriptGeneratorEdgeCases:
    """边界测试。"""

    def test_empty_config(self):
        """测试使用空配置。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={})
        assert gen.config is not None

    def test_invalid_platform(self):
        """测试无效的平台（应该回退到默认行为）。"""
        from flash.input_gen.gen_shell_script.generator import ShellScriptGenerator
        gen = ShellScriptGenerator(config={"platform": "invalid_platform"})
        # 不应该抛异常
        content = gen.generate_wsl_script()
        assert len(content) > 0
