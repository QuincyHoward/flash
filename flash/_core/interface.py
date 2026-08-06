"""Standalone interface — BaseSimulator for standalone mode.

This module provides the BaseSimulator abstract class for use when
physimx_core is not installed (standalone mode).

When physimx_core IS installed, flash/__init__.py will import from
physimx_core.interface instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import CapabilityCard, InputVar, SimulationRequest, SimulationResult


class BaseSimulator(ABC):
    """Abstract base class for all physics simulation plugins.

    A simulator plugin must implement:
      - ``capability()``  → declare what physics it can simulate.
      - ``simulate(request)`` → run one simulation and return results.

    Optionally, it may also implement:
      - ``simulate_batch(requests)`` → run many simulations (parallel-capable).
    """

    @abstractmethod
    def capability(self) -> CapabilityCard:
        """Return a machine-readable declaration of this simulator's capabilities."""
        ...

    @abstractmethod
    def simulate(self, request: SimulationRequest) -> SimulationResult:
        """Execute one simulation and return structured results.

        Parameters
        ----------
        request : SimulationRequest
            Input containing parameters, work_dir, etc.

        Returns
        -------
        SimulationResult
            Output. ``result.success`` indicates whether the simulation converged.
        """
        ...

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Validate simulation parameters.
        
        Default implementation checks temperature range.
        Raises ValueError if validation fails.
        """
        cap = self.capability()
        input_schema = cap.input_schema
        for key, spec in input_schema.items():
            if key in params:
                val = params[key]
                if spec.low is not None and val < spec.low:
                    raise ValueError(f"{key}={val} < minimum {spec.low}")
                if spec.high is not None and val > spec.high:
                    raise ValueError(f"{key}={val} > maximum {spec.high}")

    # ----- optional overrides (with sensible defaults) -------------------

    def simulate_batch(
        self,
        requests: list[SimulationRequest],
        parallel: bool = False,
        max_workers: int = 4,
    ) -> list[SimulationResult]:
        """Run multiple simulations, optionally in parallel.

        The default implementation calls ``self.simulate`` in a loop.
        Plugins that support native parallelism should override this method.
        """
        import concurrent.futures

        if not parallel:
            return [self.simulate(req) for req in requests]

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.simulate, req) for req in requests]
            return [f.result() for f in concurrent.futures.as_completed(futures)]


__all__ = ["BaseSimulator"]
