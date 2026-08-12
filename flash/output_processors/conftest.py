"""
pytest conftest.py - shared fixtures for output_processors tests.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path

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


@pytest.fixture(scope="session")
def sample_h5_file():
    """Fixture: path to a sample HDF5 file for testing."""
    # TODO: Add path to a small test HDF5 file
    return None


@pytest.fixture(scope="session")
def flash_data_loader():
    """Fixture: FlashDataLoader instance."""
    from flash.output_processors.loader import FlashDataLoader
    return FlashDataLoader


@pytest.fixture(scope="session")
def flash_hdf5_file():
    """Fixture: FlashHDF5File class."""
    from flash.output_processors.hdf5processor import FlashHDF5File
    return FlashHDF5File


@pytest.fixture(scope="session", autouse=True)
def _auto_generate_test_data():
    """自动生成 output_processors 测试数据 (inputfiles/ 被 .gitignore 排除)。

    克隆/发布环境中 inputfiles/ 缺失会导致 13 个用例失败。
    本 fixture 在测试会话开始时检查缺失并调用 gen_test_data.py 生成
    合成 FLASH HDF5 (与 FlashHDF5File/FlashDataLoader 读取逻辑兼容),
    保证测试自愈。已存在时幂等跳过。
    """
    from flash.output_processors.test.gen_test_data import ensure_test_data
    ensure_test_data()
