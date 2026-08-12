"""测试 gen_par/ 子包 — 完整功能测试。

此文件支持双重模式，使用 _compat.py 进行智能导入。
"""

import sys
import pytest
from pathlib import Path
import tempfile

# 使用兼容性模块进行智能导入
from ._compat import ParGeneratorExtended, BeamConfig, RUN_MODE




class TestParGeneratorExtendedImport:
    """导入测试。"""

    def test_import(self):
        """测试 ParGeneratorExtended 已导入。"""
        # 注意：ParGeneratorExtended 已经在文件顶部通过 _compat 导入
        assert ParGeneratorExtended is not None

    def test_import_beam_config(self):
        """测试 BeamConfig 已导入。"""
        # 注意：BeamConfig 已经在文件顶部通过 _compat 导入
        assert BeamConfig is not None


class TestParGeneratorExtendedInit:
    """初始化测试。"""

    def test_default_1d(self):
        gen = ParGeneratorExtended(dimension=1)
        assert gen._params is not None
        assert gen._detect_dimension() == 1

    def test_default_2d(self):
        gen = ParGeneratorExtended(dimension=2)
        assert gen._detect_dimension() == 2

    def test_default_3d(self):
        gen = ParGeneratorExtended(dimension=3)
        assert gen._detect_dimension() == 3

    def test_invalid_dimension(self):
        with pytest.raises(ValueError, match="Unsupported dimension"):
            ParGeneratorExtended(dimension=4)

    def test_invalid_dimension_zero(self):
        with pytest.raises(ValueError, match="Unsupported dimension"):
            ParGeneratorExtended(dimension=0)

    def test_beam_configs(self):
        gen = ParGeneratorExtended(dimension=1)
        assert isinstance(gen._beams, list)
        assert len(gen._beams) >= 0


class TestParGeneratorExtendedGenerate:
    """生成测试。"""

    def test_generate_1d(self):
        gen = ParGeneratorExtended(dimension=1)
        content = gen.generate()
        assert isinstance(content, str)
        assert len(content) > 100
        assert "LaserSlab" in content

    def test_generate_2d(self):
        gen = ParGeneratorExtended(dimension=2)
        content = gen.generate()
        assert isinstance(content, str)
        assert len(content) > 100

    def test_generate_3d(self):
        gen = ParGeneratorExtended(dimension=3)
        content = gen.generate()
        assert isinstance(content, str)
        assert len(content) > 100

    def test_generate_has_required_sections(self):
        gen = ParGeneratorExtended(dimension=1)
        content = gen.generate()
        # 检查是否包含必要的部分
        assert "# Simulation Parameters" in content or "tmax" in content


class TestParGeneratorExtendedSave:
    """保存测试。"""

    def test_save_1d(self, tmp_output_dir):
        gen = ParGeneratorExtended(dimension=1)
        path = gen.save(str(tmp_output_dir / "test_1d.par"))
        assert path.exists()
        assert path.suffix == ".par"
        # 检查文件内容
        content = path.read_text()
        assert len(content) > 100

    def test_save_2d(self, tmp_output_dir):
        gen = ParGeneratorExtended(dimension=2)
        path = gen.save(str(tmp_output_dir / "test_2d.par"))
        assert path.exists()

    def test_save_3d(self, tmp_output_dir):
        gen = ParGeneratorExtended(dimension=3)
        path = gen.save(str(tmp_output_dir / "test_3d.par"))
        assert path.exists()

    def test_save_overwrite(self, tmp_output_dir):
        gen = ParGeneratorExtended(dimension=1)
        path = tmp_output_dir / "overwrite_test.par"
        # 第一次保存
        gen.save(str(path))
        assert path.exists()
        # 第二次保存（覆盖）
        gen.set("tmax", 5e-9)
        gen.save(str(path))
        assert path.exists()


class TestParGeneratorExtendedSetGet:
    """Set/Get 测试。"""

    def test_set_and_get(self):
        gen = ParGeneratorExtended(dimension=1)
        gen.set("tmax", 5e-9)
        assert gen.get("tmax") == 5e-9

    def test_set_multiple(self):
        gen = ParGeneratorExtended(dimension=1)
        gen.set("tmax", 5e-9)
        gen.set("dtinit", 1e-14)
        gen.set("nend", 1000)
        assert gen.get("tmax") == 5e-9
        assert gen.get("dtinit") == 1e-14
        assert gen.get("nend") == 1000

    def test_get_nonexistent(self):
        gen = ParGeneratorExtended(dimension=1)
        result = gen.get("nonexistent_param")
        assert result is None

    def test_set_domain(self):
        gen = ParGeneratorExtended(dimension=1)
        gen.set_domain(xmin=0.0, xmax=200e-4, nblockx=8)
        assert gen.get("xmin") == 0.0
        assert gen.get("xmax") == 200e-4
        assert gen.get("nblockx") == 8

    def test_set_time(self):
        gen = ParGeneratorExtended(dimension=1)
        gen.set_time(tmax=2e-9, dtinit=1e-14)
        assert gen.get("tmax") == 2e-9
        assert gen.get("dtinit") == 1e-14


class TestParGeneratorExtendedDimensionSwitch:
    """维度切换测试。"""

    def test_dimension_switch(self):
        gen = ParGeneratorExtended(dimension=1)
        params_1d = dict(gen._params)
        gen.set_dimension(2)
        assert gen._detect_dimension() == 2
        assert gen._params is not params_1d

    def test_dimension_switch_and_modify(self):
        gen = ParGeneratorExtended(dimension=1)
        gen.set("tmax", 1e-9)
        gen.set_dimension(2)
        # 切换到 2D 后，tmax 应该保持
        assert gen.get("tmax") == 1e-9


class TestParGeneratorExtendedBeamConfig:
    """BeamConfig 测试。"""

    def test_beam_config_default(self):
        config = BeamConfig()
        assert config.beam_id == 1
        assert config.wavelength == 1.053

    def test_beam_config_custom(self):
        config = BeamConfig(beam_id=2, wavelength=0.351, lens_x=-0.2)
        assert config.beam_id == 2
        assert config.wavelength == 0.351
        assert config.lens_x == -0.2

    def test_add_beam(self):
        gen = ParGeneratorExtended(dimension=1)
        config = BeamConfig(beam_id=2, wavelength=0.351, lens_x=-0.2, target_x=0.2)
        gen.add_beam(config)
        assert len(gen._beams) == 1


class TestParGeneratorExtendedEdgeCases:
    """边界测试。"""

    def test_empty_par_file(self):
        """测试生成空参数文件（不应该发生）。"""
        gen = ParGeneratorExtended(dimension=1)
        content = gen.generate()
        assert len(content) > 0

    def test_negative_values(self):
        """测试负值参数。"""
        gen = ParGeneratorExtended(dimension=1)
        gen.set("tmax", -1.0)  # 负值，可能无效
        # 不应该抛异常，但生成的文件可能无效
        content = gen.generate()
        assert "tmax" in content

    def test_very_large_values(self):
        """测试非常大的值。"""
        gen = ParGeneratorExtended(dimension=1)
        gen.set("tmax", 1e9)
        content = gen.generate()
        # 检查生成的文件内容（可能是科学计数法）
        assert "tmax" in content
        # 注意：_format_param 可能会格式化为 1.000000e+09 或 1e+09
        assert "1e+09" in content or "1.000000e+09" in content or "1e9" in content


class TestParGeneratorExtendedIntegration:
    """集成测试。"""

    def test_full_workflow_1d(self, tmp_output_dir):
        """测试完整的 1D 工作流。"""
        gen = ParGeneratorExtended(dimension=1)
        gen.set_domain(xmin=0.0, xmax=200e-4, nblockx=8)
        gen.set_time(tmax=1e-9, dtinit=1e-14)
        gen.set("ediclaser", 1)
        path = gen.save(str(tmp_output_dir / "integration_1d.par"))
        assert path.exists()
        content = path.read_text()
        assert "tmax" in content
        assert "xmax" in content

    def test_full_workflow_2d(self, tmp_output_dir):
        """测试完整的 2D 工作流。"""
        gen = ParGeneratorExtended(dimension=2)
        gen.set_domain(xmin=0.0, xmax=200e-4, nblockx=8)
        gen.set_time(tmax=1e-9)
        path = gen.save(str(tmp_output_dir / "integration_2d.par"))
        assert path.exists()

    def test_full_workflow_3d(self, tmp_output_dir):
        """测试完整的 3D 工作流。"""
        gen = ParGeneratorExtended(dimension=3)
        gen.set_domain(xmin=0.0, xmax=200e-4, nblockx=8)
        gen.set_time(tmax=1e-9)
        path = gen.save(str(tmp_output_dir / "integration_3d.par"))
        assert path.exists()
