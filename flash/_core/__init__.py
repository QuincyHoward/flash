"""Built-in mini-core.

Defines the base simulator interface, the dataclass schema and the credential
store used throughout this package. It has no external framework dependency —
the package is fully self-contained.
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
