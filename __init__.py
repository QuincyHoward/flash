"""FLASH plasma simulation package.

This package provides a Python interface for the FLASH high-energy-density
physics simulation code. It supports both standalone mode (without PhySimX)
and plugin mode (as part of PhySimX).

Standalone mode (without PhySimX installed):
    >>> from flash import FlashSimulator
    >>> sim = FlashSimulator(mock=True)
    >>> result = sim.simulate(request)

Plugin mode (with PhySimX installed):
    >>> from flash import FlashSimulator  # Same API
    >>> sim = FlashSimulator(mock=True)

The package automatically detects whether physimx_core is installed:
- If yes: uses physimx_core (plugin mode, full pydantic validation)
- If no: uses vendored _core/ (standalone mode, dataclass-based)

AI Agent Notes:
    This package includes CLAUDE.md, _MODULE_DESCRIPTIONS, and .workbuddy/
    for automatic discovery by AI coding agents.
"""

# =======================================================================
# Smart Import Layer
# =======================================================================
# Priority 1: physimx_core installed (plugin mode, full features)
# Priority 2: standalone (fallback to vendored _core/)

_STANDALONE = False

try:
    # Plugin mode: use physimx_core (full features, pydantic validation)
    from physimx_core.interface import BaseSimulator
    from physimx_core.schema import (
        CapabilityCard,
        InputVar,
        OutputVar,
        PhysicsDomain,
        SimulationRequest,
        SimulationResult,
        SimulationStatus,
        SimulatorType,
    )

    _STANDALONE = False
except ImportError:
    # Standalone mode: use vendored _core/ (dataclass-based)
    from ._core.interface import BaseSimulator
    from ._core.schema import (
        CapabilityCard,
        InputVar,
        OutputVar,
        PhysicsDomain,
        SimulationRequest,
        SimulationResult,
        SimulationStatus,
        SimulatorType,
    )

    _STANDALONE = True


# =======================================================================
# Core Exports
# =======================================================================

from .interface import FlashSimulator
from .config import FlashConfig, get_default_config

# Optional exports (may not exist in all versions)
try:
    from .flash_run.env.env_manager import (
        FlashEnvironment,
        FlashEnvManager,
        get_env_manager,
    )
except ImportError:
    FlashEnvironment = None
    FlashEnvManager = None
    get_env_manager = None

try:
    from .flash_run.remote.remote_deploy import FlashRemoteDeploy
except ImportError:
    FlashRemoteDeploy = None

try:
    from .test.math_test import LaserSlabCa1D, FlashMathTest
except ImportError:
    LaserSlabCa1D = None
    FlashMathTest = None


# =======================================================================
# __all__ and Metadata
# =======================================================================

__all__ = [
    # Core
    "FlashSimulator",
    "FlashConfig",
    "get_default_config",
    # Environment management
    "FlashEnvironment",
    "FlashEnvManager",
    "get_env_manager",
    # Remote deployment
    "FlashRemoteDeploy",
    # Physics tests
    "LaserSlabCa1D",
    "FlashMathTest",
    # Base classes (for extension)
    "BaseSimulator",
    # Schema (for type hints)
    "CapabilityCard",
    "InputVar",
    "OutputVar",
    "PhysicsDomain",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
    "SimulatorType",
]

__version__ = "1.0.0"
__standalone__ = _STANDALONE


# =======================================================================
# Module-level docstring for AI agents
# =======================================================================


def __dir__():
    """Return list of public attributes (for AI agents)."""
    return sorted(__all__)


# Warm-up: pre-import common submodules (improves tab completion)
import sys as _sys

if "flash" in _sys.modules:
    # Pre-import common submodules for better UX
    _common_submodules = [
        "flash.config",
        "flash._core.credentials",
        "flash.flash_run",
        "flash.input_gen",
        "flash.output_processors",
    ]
    for _mod in _common_submodules:
        try:
            __import__(_mod)
        except ImportError:
            pass
