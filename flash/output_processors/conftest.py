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
    _ROOT = None  # 已安装环境 (site-packages): 静默跳过
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
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
