"""
test_interface.py — 测试 flash.interface 模块

测试目标：
  - FlashSimulator 的核心接口
  - simulate() 方法
  - capability() 方法
  - batch_simulate() 方法

测试数据位置：
  - 输入：flash/inputfiles/
  - 输出：flash/outputfiles/
"""

import pytest
import numpy as np
from pathlib import Path


class TestFlashSimulatorInterface:
    """测试 FlashSimulator 接口。"""

    def test_import(self):
        """测试模块导入。"""
        try:
            from flash.interface import FlashSimulator

            assert FlashSimulator is not None
        except ImportError as e:
            pytest.fail(f"Failed to import FlashSimulator: {e}")

    def test_init_mock(self):
        """测试初始化（mock模式）。"""
        from flash.interface import FlashSimulator

        simulator = FlashSimulator(mock=True, verbose=False)
        assert simulator is not None
        assert simulator.mock is True

    def test_capability(self, flash_simulator):
        """测试 capability() 方法。"""
        cap = flash_simulator.capability()
        assert cap is not None
        assert hasattr(cap, "simulator_name")
        assert cap.simulator_name == "FLASH"

    def test_simulate_single(self, flash_simulator, sample_request):
        """测试单次仿真。"""
        result = flash_simulator.simulate(sample_request)
        assert result is not None
        assert hasattr(result, "success")
        assert result.success is True

    def test_simulate_output_data(self, flash_simulator, sample_request):
        """测试仿真输出数据。"""
        result = flash_simulator.simulate(sample_request)
        assert result.output_data is not None
        assert len(result.output_data) > 0

        # 检查必要的输出字段
        expected_keys = ["max_temperature", "avg_density", "radiation_intensity"]
        for key in expected_keys:
            assert key in result.output_data, f"{key} not in output_data"

    def test_simulate_reproducibility(self, flash_simulator):
        """测试仿真可重现性（相同输入 → 相同输出）。"""
        try:
            from flash._core.schema import SimulationRequest, SimulatorType
        except ImportError:
            pytest.skip("Standalone schema not available")

        params = {"temperature": 5000.0, "density": 1e-2}
        req1 = SimulationRequest(simulator_type=SimulatorType.FLASH, params=params)
        req2 = SimulationRequest(simulator_type=SimulatorType.FLASH, params=params)

        result1 = flash_simulator.simulate(req1)
        result2 = flash_simulator.simulate(req2)

        # 验证输出相同
        assert result1.output_data["max_temperature"] == result2.output_data["max_temperature"]
        assert result1.output_data["radiation_intensity"] == result2.output_data["radiation_intensity"]

    def test_simulate_invalid_params(self, flash_simulator):
        """测试非法参数处理。"""
        try:
            from flash._core.schema import SimulationRequest, SimulatorType
        except ImportError:
            pytest.skip("Standalone schema not available")

        # 温度超出范围
        req = SimulationRequest(simulator_type=SimulatorType.FLASH, params={"temperature": 10.0})  # 太低
        result = flash_simulator.simulate(req)
        assert result.success is False
        assert result.error_message is not None

    def test_batch_simulate(self, flash_simulator):
        """测试批量仿真。"""
        try:
            from flash._core.schema import SimulationRequest, SimulatorType
        except ImportError:
            pytest.skip("Standalone schema not available")

        requests = [
            SimulationRequest(
                simulator_type=SimulatorType.FLASH, params={"temperature": 3000.0 + i * 1000.0, "density": 1e-3}
            )
            for i in range(3)
        ]

        results = flash_simulator.simulate_batch(requests, parallel=False)
        assert len(results) == 3
        assert all(r.success for r in results)


class TestFlashSimulatorRegistry:
    """测试 FlashSimulator 在注册表中的注册。"""

    def test_registry_registration(self):
        """测试FlashSimulator已注册到_core.registry。"""
        from flash._core.registry import list_simulators, get_simulator

        simulators = list_simulators()
        assert "flash" in simulators

        FlashSimulator = get_simulator("flash")
        assert FlashSimulator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
