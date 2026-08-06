"""
FLASH 模拟器测试 — test_flash_simulator.py
═══════════════════════════════════════════════════

测试 FlashSimulator（interface.py）及其内部 mock 物理函数。
"""

import math
import numpy as np
import pytest

try:
    from physimx_core.schema import SimulationRequest, SimulatorType, SimulationStatus, CapabilityCard

    _HAS_PHYSIMX_CORE = True
except ImportError:
    try:
        from flash._core.schema import SimulationRequest, SimulatorType, SimulationStatus, CapabilityCard

        _HAS_PHYSIMX_CORE = True
    except ImportError:
        _HAS_PHYSIMX_CORE = False

# ────────────────────────────────────────────
# FlashSimulator 测试
# ────────────────────────────────────────────

if not _HAS_PHYSIMX_CORE:
    pytest.skip("SimulationRequest/SimulatorType not available", allow_module_level=True)


class TestFlashSimulator:
    """FlashSimulator mock 模式测试。"""

    @pytest.fixture
    def sim(self):
        from flash import FlashSimulator

        return FlashSimulator(mock=True, verbose=False)

    def test_capability(self, sim):
        """capability() 返回正确的 CapabilityCard。"""
        card = sim.capability()
        assert card.simulator_name == "FLASH"
        assert card.simulator_type is not None
        assert len(card.physics_domains) > 0

    def test_simulate_returns_all_keys(self, sim):
        """simulate() 返回所有 output keys。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2},
        )
        result = sim.simulate(req)
        expected_keys = {
            "max_temperature",
            "avg_density",
            "radiation_intensity",
            "ionization_fraction",
            "radiation_spectrum",
        }
        assert set(result.output_data.keys()) >= expected_keys

    def test_simulate_reproducible(self, sim):
        """相同输入产生相同输出（确定性 mock）。"""
        req1 = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2},
        )
        req2 = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2},
        )
        r1 = sim.simulate(req1)
        r2 = sim.simulate(req2)
        for key in r1.output_data:
            v1 = r1.output_data[key]
            v2 = r2.output_data[key]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                assert math.isclose(v1, v2, rel_tol=1e-9), f"{key}: {v1} != {v2}"
            else:
                # 列表/数组类型：逐一比较
                if hasattr(v1, "__iter__") and hasattr(v2, "__iter__"):
                    np.testing.assert_allclose(v1, v2, rtol=1e-9)

    def test_simulate_batch(self, sim):
        """批量模拟全部成功。"""
        requests = [
            SimulationRequest(
                simulator_type=SimulatorType.FLASH,
                params={"temperature": T, "density": 1e-2},
            )
            for T in [5000.0, 8000.0, 10000.0]
        ]
        results = sim.simulate_batch(requests)
        assert len(results) == 3
        assert all(r.status == SimulationStatus.SUCCESS for r in results)

    def test_simulate_invalid_params(self, sim):
        """无效参数（temperature < 1e3）返回 FAILED。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 500.0, "density": 1e-2},
        )
        result = sim.simulate(req)
        assert result.status == SimulationStatus.FAILED

    def test_simulate_result_status(self, sim):
        """result.status 是 SUCCESS。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2},
        )
        result = sim.simulate(req)
        assert result.status == SimulationStatus.SUCCESS

    def test_simulate_execution_time_positive(self, sim):
        """execution_time 为正数。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2},
        )
        result = sim.simulate(req)
        assert result.execution_time > 0

    def test_simulate_request_id_preserved(self, sim):
        """result.request_id 与输入一致。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2},
        )
        result = sim.simulate(req)
        assert result.request_id == req.request_id


# ────────────────────────────────────────────
# Mock 物理函数测试
# ────────────────────────────────────────────


class TestMockPhysics:
    """interface.py 中 mock 物理函数的独立测试。"""

    def test_planck_radiation_intensity_monotonic(self):
        """_planck_radiation_intensity 随温度单调递增。"""
        from flash.interface import _planck_radiation_intensity

        T = [1e3, 5e3, 1e4, 5e4, 1e5]
        vals = [_planck_radiation_intensity(t) for t in T]
        for i in range(len(vals) - 1):
            assert vals[i] < vals[i + 1], f"在 T={T[i]} 处不单调: {vals[i]} >= {vals[i+1]}"

    def test_planck_radiation_intensity_zero_temp(self):
        """T=0 时返回 0。"""
        from flash.interface import _planck_radiation_intensity

        assert _planck_radiation_intensity(0.0) == pytest.approx(0.0, abs=1e-30)

    def test_planck_radiation_intensity_negative_temp(self):
        """负数温度不崩溃（返回正数或 0）。"""
        from flash.interface import _planck_radiation_intensity

        val = _planck_radiation_intensity(-1000.0)
        assert isinstance(val, (int, float))
        assert val >= 0

    def test_saha_ionization_fraction_range(self):
        """_saha_ionization_fraction 输出在 [0, 1] 区间。"""
        from flash.interface import _saha_ionization_fraction

        for T in [1e3, 5e3, 1e4, 5e4]:
            for rho in [1e-4, 1e-3, 1e-2]:
                f = _saha_ionization_fraction(T, rho)
                assert 0.0 <= f <= 1.0, f"T={T}, rho={rho}: f={f} 超出 [0,1]"

    def test_saha_ionization_fraction_zero_temp(self):
        """T=0 或 density=0 时返回 0。"""
        from flash.interface import _saha_ionization_fraction

        assert _saha_ionization_fraction(0.0, 1e-3) == 0.0
        assert _saha_ionization_fraction(5000.0, 0.0) == 0.0

    def test_saha_ionization_fraction_physics_trend(self):
        """
        物理趋势验证:
          - 高温 → 高电离
          - 高密 → 低电离（复合占优）
        """
        from flash.interface import _saha_ionization_fraction

        f_low = _saha_ionization_fraction(5e3, 1e-3)
        f_high = _saha_ionization_fraction(5e4, 1e-3)
        assert f_high > f_low, "高温应导致更高电离"

        f_low_rho = _saha_ionization_fraction(1e4, 1e-4)
        f_high_rho = _saha_ionization_fraction(1e4, 1e-1)
        assert f_high_rho < f_low_rho, "高密度应导致更低电离"

    def test_planck_spectrum_positive(self):
        """_planck_spectrum 所有能量值 > 0。"""
        from flash.interface import _planck_spectrum

        spec = _planck_spectrum(1e4, n_bins=32)
        assert all(v > 0 for v in spec), "光谱中有非正值"

    def test_planck_spectrum_shape(self):
        """
        光谱形状合理性:
          - 低温: 峰值在低端
          - 高温: 峰值向高端移动
        """
        from flash.interface import _planck_spectrum

        spec_low = _planck_spectrum(5e3, n_bins=32)
        spec_high = _planck_spectrum(5e4, n_bins=32)
        peak_low = np.argmax(spec_low)
        peak_high = np.argmax(spec_high)
        assert peak_high > peak_low, "高温时光谱峰值应向高能端移动"

    def test_planck_spectrum_normalization(self):
        """_planck_spectrum 返回值之和 ≈ 1（归一化）。"""
        from flash.interface import _planck_spectrum

        for T in [5e3, 1e4, 5e4]:
            spec = _planck_spectrum(T, n_bins=32)
            total = sum(spec)
            assert abs(total - 1.0) < 1e-6, f"T={T}: 归一化和={total}, 期望 1.0"

    def test_planck_spectrum_n_bins(self):
        """n_bins 参数控制返回列表长度。"""
        from flash.interface import _planck_spectrum

        for n in [16, 32, 64]:
            spec = _planck_spectrum(1e4, n_bins=n)
            assert len(spec) == n

    def test_mock_physics_constants(self):
        """物理常量值合理性验证。"""
        from flash.interface import KB_EV, C_LIGHT, H_PLANCK

        assert 8.0e-5 < KB_EV < 9.0e-5
        assert 2.9e8 < C_LIGHT < 3.1e8
        assert 4.0e-15 < H_PLANCK < 4.2e-15


# ────────────────────────────────────────────
# FlashSimulator 边界条件测试
# ────────────────────────────────────────────


class TestFlashSimulatorBoundary:
    """FlashSimulator 边界条件和异常处理。"""

    @pytest.fixture
    def sim(self):
        from flash import FlashSimulator

        return FlashSimulator(mock=True, verbose=False)

    def test_magnetic_field_zero(self, sim):
        """magnetic_field=0 时不抛异常，且 radiation_intensity 不受影响。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-2, "magnetic_field": 0.0},
        )
        result = sim.simulate(req)
        assert result.status == SimulationStatus.SUCCESS
        assert "radiation_intensity" in result.output_data

    def test_very_high_temperature(self, sim):
        """极高温度（1e6 K）不崩溃（可能返回 FAILED）。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 1e6, "density": 1e-2},
        )
        result = sim.simulate(req)
        # 不崩溃即可，极高温度可能通过或失败
        assert result.status in (SimulationStatus.SUCCESS, SimulationStatus.FAILED)

    def test_very_low_density(self, sim):
        """极低密度（1e-6 g/cm³）不崩溃。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"temperature": 8000.0, "density": 1e-6},
        )
        result = sim.simulate(req)
        assert result.status in (SimulationStatus.SUCCESS, SimulationStatus.FAILED)

    def test_simulate_empty_params(self, sim):
        """空 params 时不崩溃（返回 SUCCESS 或 FAILED 均可）。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={},
        )
        result = sim.simulate(req)
        # 不崩溃即可
        assert result is not None
        assert result.status is not None

    def test_simulate_missing_temperature(self, sim):
        """缺少 temperature 时不崩溃（返回 SUCCESS 或 FAILED 均可）。"""
        req = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={"density": 1e-2},
        )
        result = sim.simulate(req)
        # 不崩溃即可
        assert result is not None
        assert result.status is not None
