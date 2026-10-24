"""FLASH plasma simulation package.

This package provides a Python interface for the FLASH high-energy-density
physics simulation code. It is fully self-contained: the base classes and
schema live in the vendored ``_core/`` subpackage, so the only requirements
are the ones declared in ``pyproject.toml``.

    >>> from flash import FlashSimulator
    >>> sim = FlashSimulator(mock=True)
    >>> result = sim.simulate(request)

AI Agent Notes:
    This package includes CLAUDE.md, _MODULE_DESCRIPTIONS, and .workbuddy/
    for automatic discovery by AI coding agents.
"""

# =======================================================================
# Core base classes and schema (vendored, no external simulation framework)
# =======================================================================

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

#: Retained for backwards compatibility: this package is always standalone.
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

#: ★ 2026-10-24（解耦计划 B0）：`FlashRemoteDeploy` 改为**惰性**。
#: 原写法虽包在 try 里，但仍是**急切执行** —— `remote_deploy.py` 模块级
#: `import paramiko`，导致 `import flash` 就拉起 paramiko+cryptography，
#: 使「基础设施层零重依赖」名不副实。现由模块级 `__getattr__` 按需提供，
#: 且保持旧语义（paramiko 缺失时返回 None 而不是抛错）。
_LAZY_IMPORTS = {
    "FlashRemoteDeploy": (".flash_run.remote.remote_deploy", "FlashRemoteDeploy"),
}

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

#: Package version.
#: ★ Read from installed distribution metadata so it can never drift from
#:   ``pyproject.toml`` (it was hard-coded at "0.1.0" while pyproject said
#:   0.1.7 — a silent inconsistency that misleads `pip show` / bug reports).
#:   Fall back to parsing the source-tree ``pyproject.toml`` when running
#:   from a checkout that was never installed.
def _resolve_version() -> str:
    # ① 源码树里有 pyproject.toml ⇒ 以它为准
    #    （editable 安装的 dist-info 仍写着**安装时**的版本，
    #      改 pyproject 后不重装就会读到旧值 —— 实测 0.1.7 vs 0.1.11）
    try:
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if pyproject.is_file():
            with open(pyproject, "rb") as fh:
                return str(tomllib.load(fh)["project"]["version"])
    except Exception:  # noqa: BLE001 - 版本号解析失败不应阻断 import
        pass
    # ② 否则用已安装发行版的元数据（wheel 安装场景）
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _pkg_version

        try:
            return _pkg_version("flash-sim")
        except PackageNotFoundError:
            pass
    except ImportError:  # pragma: no cover
        pass
    return "unknown"


__version__ = _resolve_version()
__standalone__ = _STANDALONE


# =======================================================================
# Module-level docstring for AI agents
# =======================================================================


def __dir__():
    """Return list of public attributes (for AI agents)."""
    return sorted(__all__)


def __getattr__(name):
    """PEP 562 惰性导出（见文件头 `_LAZY_IMPORTS`）。

    语义保持：子模块 import 失败时返回 None（旧 `try/except ImportError`
    行为），不向调用方抛错 —— 否则 `from flash import FlashRemoteDeploy`
    会在无 paramiko 的环境里硬失败。
    """
    try:
        mod_name, attr = _LAZY_IMPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    from importlib import import_module

    try:
        value = getattr(import_module(mod_name, __name__), attr)
    except ImportError:
        value = None
    globals()[name] = value
    return value


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
