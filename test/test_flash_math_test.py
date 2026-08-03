"""
FLASH math_test 模块测试 — test_flash_math_test.py
═══════════════════════════════════════

测试 flash/math_test.py 中的 LaserSlabCa1D, FlashMathTest 等。
"""

import math
import os
import tempfile

import numpy as np
import pytest

from flash.test.math_test import (
    LaserSlabCa1D,
    FlashMathTest,
    MultimodalInput,
    SimDimension,
    PulseShape,
    quick_test_1d,
)

# ────────────────────────────────────────────
# LaserSlabCa1D 测试
# ────────────────────────────────────────────


class TestLaserSlabCa1D:
    """LaserSlabCa1D 1D 快速数学测试。"""

    def test_run_returns_dict(self):
        """run() 返回字典。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        assert isinstance(result, dict)

    def test_run_has_dens(self):
        """run() 返回含 dens 键。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        assert "dens" in result

    def test_run_has_tele(self):
        """run() 返回含 tele 键。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        assert "tele" in result

    def test_run_has_zbar(self):
        """run() 返回含 zbar 键。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        assert "zbar" in result

    def test_run_dens_positive(self):
        """dens 全部 > 0。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        dens = result["dens"]
        assert np.all(dens > 0), "密度应全部为正"

    def test_run_tele_positive(self):
        """tele 全部 > 0。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        tele = result["tele"]
        assert np.all(tele > 0), "电子温度应全部为正"

    def test_run_shock_front_in_range(self):
        """
        shock_front 位置在 [0, L] 范围内。
        LaserSlabCa1D 默认 L = x_max_cm = 0.1 cm
        """
        sim = LaserSlabCa1D()
        result = sim.run()
        L = 0.1  # cm (x_max_cm default)
        shock = result["shock_front"]
        if isinstance(shock, np.ndarray):
            shock_val = np.max(shock)
        else:
            shock_val = shock
        assert 0.0 <= shock_val <= L

    def test_run_reproducible(self):
        """相同参数两次运行结果一致（确定性）。"""
        sim1 = LaserSlabCa1D()
        sim2 = LaserSlabCa1D()
        r1 = sim1.run()
        r2 = sim2.run()
        for key in r1:
            if isinstance(r1[key], np.ndarray):
                np.testing.assert_allclose(r1[key], r2[key], rtol=1e-12)
            else:
                assert r1[key] == r2[key]

    def test_custom_constructor(self):
        """
        使用自定义参数构造 LaserSlabCa1D。
        实际 API：波长、功率、靶材等作为构造参数。
        """
        sim = LaserSlabCa1D(
            wavelength_nm=532.0,
            peak_power_w_cm2=5e13,
            pulse_duration_s=3e-9,
            target_material="CH",
            nx=200,
        )
        result = sim.run()
        assert "dens" in result
        assert "tele" in result

    def test_quick_test_1d_saves_hdf5(self):
        """quick_test_1d() 自动保存 HDF5 文件到 CWD。"""
        import h5py

        result = quick_test_1d()
        h5_path = os.path.join(os.getcwd(), "quick_test_1d.h5")
        try:
            assert os.path.exists(h5_path), "quick_test_1d.h5 未被创建"
            with h5py.File(h5_path, "r") as f:
                assert "dens" in f
                assert "tele" in f
        finally:
            if os.path.exists(h5_path):
                try:
                    os.remove(h5_path)
                except OSError:
                    pass  # 清理失败不影响测试结果 (如沙箱限制删除)


# ────────────────────────────────────────────
# FlashMathTest 测试
# ────────────────────────────────────────────


class TestFlashMathTest:
    """FlashMathTest 测试（通过 config=MultimodalInput 构造）。"""

    def test_1d_dimension(self):
        """1D 测试不抛异常。"""
        config = MultimodalInput(dimension=SimDimension.D1, nx=100)
        fmt = FlashMathTest(config=config)
        result = fmt.run()
        assert isinstance(result, dict)

    def test_2d_dimension(self):
        """2D 测试不抛异常。"""
        config = MultimodalInput(dimension=SimDimension.D2, nx=50, ny=50)
        fmt = FlashMathTest(config=config)
        result = fmt.run()
        assert isinstance(result, dict)

    def test_3d_dimension(self):
        """3D 测试不抛异常。"""
        config = MultimodalInput(dimension=SimDimension.D3, nx=30, ny=30, nz=30)
        fmt = FlashMathTest(config=config)
        result = fmt.run()
        assert isinstance(result, dict)

    def test_quick_test_1d_keys(self):
        """quick_test_1d() 返回含峰值参数的字典。"""
        result = quick_test_1d()
        assert "peak_tele_eV" in result
        assert "avg_final_dens" in result
        assert "shock_front_final_cm" in result

    def test_quick_test_1d_peak_tele(self):
        """peak_tele_eV 在合理范围（单位 eV）。"""
        result = quick_test_1d()
        tele_ev = result["peak_tele_eV"]
        # quick_test_1d 默认参数下 ~0.89 eV，合理范围 0.1~1e5 eV
        assert tele_ev > 0.1
        assert tele_ev < 1e5


# ────────────────────────────────────────────
# MultimodalInput 测试
# ────────────────────────────────────────────


class TestMultimodalInput:
    """MultimodalInput 测试。"""

    def test_default_creation(self):
        """默认构造不抛异常。"""
        inp = MultimodalInput()
        assert inp.peak_power_w_cm2 > 0
        assert inp.target_density_g_cm3 > 0

    def test_custom_creation(self):
        """自定义参数构造。"""
        inp = MultimodalInput(
            peak_power_w_cm2=5e13,
            target_density_g_cm3=1.0,
            dimension=SimDimension.D2,
            nx=100,
            ny=100,
        )
        assert inp.peak_power_w_cm2 == 5e13
        assert inp.dimension == SimDimension.D2

    def test_sim_dimension_enum(self):
        """SimDimension Enum 完整性。"""
        assert SimDimension.D1.value == 1
        assert SimDimension.D2.value == 2
        assert SimDimension.D3.value == 3

    def test_pulse_shape_enum(self):
        """PulseShape Enum 完整性。"""
        assert PulseShape.GAUSSIAN is not None
        assert PulseShape.SQUARE is not None

    def test_wavelength_nm_field(self):
        """wavelength_nm 字段存在且合理。"""
        inp = MultimodalInput()
        assert 100.0 < inp.wavelength_nm < 10000.0

    def test_dimension_field(self):
        """dimension 字段存在。"""
        inp = MultimodalInput(dimension=SimDimension.D1)
        assert inp.dimension == SimDimension.D1


# ────────────────────────────────────────────
# 物理合理性验证
# ────────────────────────────────────────────


class TestMathTestPhysics:
    """math_test 模块物理合理性验证。"""

    def test_electron_density_magnitude(self):
        """dens 数量级合理（单位 g/cm³）。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        dens = result["dens"]
        assert np.all(dens > 1e-6)
        assert np.all(dens < 1e2)

    def test_shock_front_velocity(self):
        """冲击波位置在合理范围。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        shock = result["shock_front"]
        if isinstance(shock, np.ndarray):
            shock_val = shock[-1]
        else:
            shock_val = shock
        assert shock_val > 0.0

    def test_temperature_range(self):
        """电子温度 tele 在合理范围（单位 K）。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        tele = result["tele"]
        assert np.all(tele > 299.0)
        assert np.all(tele < 1e9)

    def test_zbar_range(self):
        """电离度 zbar 在 [0, Z] 区间。"""
        sim = LaserSlabCa1D()
        result = sim.run()
        zbar = result["zbar"]
        assert np.all(zbar >= 0.0)
        assert np.all(zbar <= 13.0)
