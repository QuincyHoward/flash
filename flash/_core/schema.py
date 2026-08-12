"""Schema — dataclass definitions of the simulation contract.

This module provides dataclass-based versions of the schema classes
used by every simulator in this package.

Dataclasses keep the package dependency-free (no pydantic needed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# =======================================================================
# Enums
# =======================================================================

class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class SimulatorType(str, Enum):
    FLASH = "FLASH"
    FLYCHK = "FLYCHK"
    UNKNOWN = "UNKNOWN"


class PhysicsDomain(str, Enum):
    HEDP = "HEDP"          # High-Energy-Density Physics
    ICF = "ICF"            # Inertial Confinement Fusion
    LASER = "LASER"        # Laser-Plasma Interaction
    MAGNETIC = "MAGNETIC"  # Magnetic Fusion
    PLASMA = "PLASMA"      # Plasma Physics
    GENERAL = "GENERAL"    # General plasma physics


# =======================================================================
# Data Models (dataclass-based, no pydantic dependency)
# =======================================================================

@dataclass
class InputVar:
    """Input variable specification."""
    low: float
    high: float
    unit: str = ""


@dataclass
class OutputVar:
    """Output variable specification."""
    dimensions: List[str] = field(default_factory=list)
    unit: str = ""


@dataclass
class SimulationRequest:
    """Simulation request (standalone version, dataclass-based)."""
    request_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    simulator_type: Optional[SimulatorType] = None
    params: Dict[str, Any] = field(default_factory=dict)
    work_dir: Optional[Path] = None
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Simulation result (standalone version, dataclass-based)."""
    request_id: str = ""
    status: SimulationStatus = SimulationStatus.PENDING
    output_data: Dict[str, Any] = field(default_factory=dict)
    raw_output_path: Optional[Path] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == SimulationStatus.SUCCESS


@dataclass
class CapabilityCard:
    """Simulator capability declaration (standalone, dataclass-based)."""
    simulator_name: str = ""
    simulator_type: SimulatorType = SimulatorType.UNKNOWN
    version: str = ""
    physics_domains: List[PhysicsDomain] = field(default_factory=list)
    supported_dimensions: List[int] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    estimated_runtime: str = ""
    parallel_scalable: bool = False
    requires_license: bool = False
    homepage: str = ""
    documentation: str = ""
    physics_domain: PhysicsDomain = PhysicsDomain.GENERAL  # legacy compat
    input_vars: Dict[str, InputVar] = field(default_factory=dict)
    output_vars: Dict[str, OutputVar] = field(default_factory=dict)
    description: str = ""


__all__ = [
    "SimulationStatus", "SimulatorType", "PhysicsDomain",
    "InputVar", "OutputVar", "SimulationRequest", "SimulationResult",
    "CapabilityCard",
]
