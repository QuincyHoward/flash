"""Vendored mini-core for standalone operation.

These are local copies of physimx_core base classes.
They are ONLY used when physimx_core is not installed.

When physimx_core IS installed, flash/__init__.py will import from
physimx_core instead (see the smart import layer in flash/__init__.py).
"""

from .interface import BaseSimulator
from .schema import (
    CapabilityCard, InputVar, OutputVar, PhysicsDomain,
    SimulationRequest, SimulationResult, SimulationStatus, SimulatorType,
)
# 从新的模块化 credentials 包导入
from .credentials import (
    get_credential_manager,
    get_user_name,
    set_user_name,
    mask_secret,
    collect_ssh_accounts,
    get_primary_ssh,
    set_primary_ssh,
    interactive_menu as credentials_menu,
)

__all__ = [
    "BaseSimulator",
    "CapabilityCard", "InputVar", "OutputVar", "PhysicsDomain",
    "SimulationRequest", "SimulationResult", "SimulationStatus", "SimulatorType",
    "get_credential_manager",
    "get_user_name",
    "set_user_name",
    "mask_secret",
    "collect_ssh_accounts",
    "get_primary_ssh",
    "set_primary_ssh",
    "credentials_menu",
]
