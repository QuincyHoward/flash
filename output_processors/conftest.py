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
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
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
