"""Standalone simulator registry (minimal, no physimx_core dependency).

When physimx_core is not installed, this module provides a basic registry
for FlashSimulator so that registry-dependent tests can pass.
"""

from typing import Any, Dict, Optional

_registry: Dict[str, Any] = {}


def register_simulator(name: str, simulator_class: Any) -> None:
    """Register a simulator class by name."""
    _registry[name.lower()] = simulator_class


def get_simulator(name: str) -> Optional[Any]:
    """Get a registered simulator class by name."""
    return _registry.get(name.lower())


def list_simulators() -> list:
    """List all registered simulator names."""
    return list(_registry.keys())


# Auto-register FlashSimulator if available
try:
    from flash.interface import FlashSimulator
    register_simulator("flash", FlashSimulator)
except ImportError:
    pass


__all__ = ["register_simulator", "get_simulator", "list_simulators"]
