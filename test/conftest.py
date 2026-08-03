"""conftest.py — flash 模块测试的共享固件（fixtures）

flash 独立包模式：flash/ 是最顶层包目录。
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# ── 路径设置：将 flash/ 的父目录加入 sys.path ─────
# flash/ 的父目录含有 __init__.py，该文件已通过 try-except
# 安全处理了 physimx_core 缺失的情况。

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


@pytest.fixture(scope="module")
def flash_simulator():
    """创建FlashSimulator mock实例。"""
    try:
        from flash import FlashSimulator

        simulator = FlashSimulator(mock=True, verbose=False)
        yield simulator
    except ImportError:
        pytest.skip("FlashSimulator not available")


@pytest.fixture(scope="function")
def sample_request():
    """创建示例SimulationRequest（使用 vendored _core 模式）。"""
    try:
        from flash._core.schema import SimulationRequest, SimulatorType

        request = SimulationRequest(
            simulator_type=SimulatorType.FLASH,
            params={
                "temperature": 5000.0,
                "density": 1e-2,
                "magnetic_field": 1.0,
            },
        )
        return request
    except ImportError as e:
        pytest.skip(f"flash._core.schema not available: {e}")


@pytest.fixture(scope="function")
def temp_par_file(tmp_path):
    """创建临时.par参数文件。"""
    par_content = """
# FLASH parameter file for testing
geometry = 1
ndim = 1
nblockx = 4
nblocky = 1
nblockz = 1
"""
    par_file = tmp_path / "test_flash.par"
    par_file.write_text(par_content)
    return par_file


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录。"""
    data_dir = Path(__file__).parent / "inputfiles"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def output_dir():
    """测试输出目录。"""
    out_dir = Path(__file__).parent / "outputfiles"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir
