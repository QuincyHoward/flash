"""FLASH plasma simulation plugin for PhySimX.

This module provides ``FlashSimulator``, which wraps the FLASH
high-energy-density physics code.

Two operating modes
-------------------

* **Mock mode** (``mock=True`` or no executable given, the default).
  Returns physically-motivated random data computed from closed-form
  formulas (Planck radiation, Saha ionization, ...). This lets the full
  PhySimX pipeline be developed and demonstrated without a local
  FLASH install.
* **Real mode** (``mock=False`` and a ``flash_executable`` path).
  Writes a FLASH ``.par`` input file, runs the binary as a subprocess,
  and parses ``flash.dat`` / HDF5 outputs. Not implemented in the MVP.

Examples
--------

Mock mode::

    >>> from flash import FlashSimulator
    >>> sim = FlashSimulator(mock=True)
    >>> result = sim.simulate(...)
    >>> result.success
    True

Real mode (requires local FLASH build)::

    >>> sim = FlashSimulator(flash_executable="/opt/flash/flash")
    >>> result = sim.simulate(...)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ===========================================================================
# Smart Import Layer (standalone + plugin dual mode)
# ===========================================================================
# Try physimx_core first (plugin mode, full pydantic validation)
# Fall back to vendored _core/ (standalone mode, dataclass-based)

try:
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
except ImportError:
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


# ===========================================================================
# Mock physics helpers (closed-form, deterministic)
# ===========================================================================

#: Boltzmann constant in eV/K (used by mock Saha / Planck)
KB_EV = 8.617333262145e-5
#: Speed of light in vacuum (m/s)
C_LIGHT = 2.99792458e8
#: Planck constant in eV·s
H_PLANCK = 4.135667696e-15


def _planck_radiation_intensity(temperature: float) -> float:
    """σ·T⁴  (Stefan–Boltzmann) — used as mock total radiation.

    Returns intensity in arbitrary units (a.u.).
    """
    sigma = 5.670374419e-8  # W·m⁻²·K⁻⁴
    return sigma * temperature**4 / 1e10  # rescale to "nice" a.u.


def _saha_ionization_fraction(temperature: float, density: float) -> float:
    """Crude Saha-like ionization fraction (mock).

    Higher temperature ⇒ more ionized.  Higher density ⇒ less ionized
    (recombination wins).  Output is clipped to [0, 1].
    """
    if temperature <= 0 or density <= 0:
        return 0.0
    raw = (temperature / 1e4) ** 0.7 / (density * 1e3) ** 0.15
    return max(0.0, min(1.0, raw))


def _planck_spectrum(temperature: float, n_bins: int = 32) -> list:
    """Planck black-body spectrum binned over [0.1, 10] keV.

    Returns intensity per bin (a.u.) – the *shape* matches a real
    Planck curve, with peaks shifted by temperature.
    """
    energies_ev = [0.1 + i * 9.9 / n_bins for i in range(n_bins)]
    spectrum = []
    for ev in energies_ev:
        # Planck formula: B(E) ~ E^3 / (exp(E/kT) - 1)
        if temperature <= 0:
            spectrum.append(0.0)
            continue
        x = ev / (KB_EV * temperature)
        if x > 500:  # avoid overflow
            val = 0.0
        else:
            val = ev**3 / (math.exp(x) - 1.0)
        spectrum.append(val)
    # Normalize so the area is 1 (a.u.)
    total = sum(spectrum) or 1.0
    return [v / total for v in spectrum]


# ===========================================================================
# FLASH input-file generator (small subset, demo-only)
# ===========================================================================


def _default_work_dir() -> str:
    """Return 'flash_work' directory.

    优先级:
      1. 入口脚本所在目录 (用户脚本/CLI 场景) — 前提是**不在** Python 安装目录内
      2. 当前工作目录 (pytest / 交互式解释器等场景)

    修复 (2026-08-06): 入口脚本为 pytest 等工具时 (位于 site-packages),
    原逻辑会在 Python 安装目录下创建 flash_work/ → PermissionError。
    """
    try:
        import __main__ as main_mod

        if hasattr(main_mod, "__file__") and main_mod.__file__:
            main_dir = Path(main_mod.__file__).resolve().parent
            # 排除 Python 自身安装目录 (Anaconda/venv 的 site-packages 等)
            if not str(main_dir).lower().startswith(str(Path(sys.prefix).resolve()).lower()):
                return str(main_dir / "flash_work")
    except Exception:
        pass
    return str(Path.cwd() / "flash_work")


def _generate_flash_input(params: Dict[str, Any], work_dir: Path) -> Path:
    """Write a minimal FLASH-style ``.par`` input file and return its path.

    Only a handful of demo parameters are serialised; a real
    implementation would cover the full FLASH setup.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    inp = work_dir / "flash_input.par"

    lines: list[str] = [
        "# FLASH input file – auto-generated by PhySimX",
        f"# Timestamp: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    for k, v in params.items():
        if isinstance(v, float):
            lines.append(f"{k}  =  {v:.6e}")
        else:
            lines.append(f"{k}  =  {v}")

    inp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inp


def _parse_flash_output(output_path: Path) -> Dict[str, Any]:
    """Parse a real FLASH ``flash.dat`` / HDF5 dump.

    Not implemented in the MVP; returns an empty dict so the
    real-mode code-path compiles.  Override in production.
    """
    return {}


# ===========================================================================
# FlashSimulator
# ===========================================================================


class FlashSimulator(BaseSimulator):
    """FLASH simulator plugin (HEDP / ICF plasma code).

    Parameters
    ----------
    flash_executable : str | Path | None
        Path to the FLASH binary.  When *None* the simulator
        runs in **mock mode** and never calls an external program.
    work_dir : str | Path | None
        Directory used for input / output files.  When ``None`` (the
        default) it resolves to ``flash_work/`` relative to the
        entry-point script's folder (based on ``__main__.__file__``),
        falling back to the current working directory in interactive
        environments.
    mock : bool | None
        Force mock mode.  ``None`` ⇒ auto-detect from
        ``flash_executable`` being set.
    verbose : bool
        Print detailed progress messages (default ``True``).
    """

    def __init__(
        self,
        flash_executable: Optional[os.PathLike | str] = None,
        work_dir: os.PathLike | str | None = None,
        mock: Optional[bool] = None,
        verbose: bool = True,
    ) -> None:
        self.flash_executable = os.fspath(flash_executable) if flash_executable else None
        self.work_dir = Path(work_dir) if work_dir is not None else Path(_default_work_dir())
        self.mock = mock if mock is not None else (flash_executable is None)
        self.verbose = verbose

    # ---- BaseSimulator contract -----------------------------------------

    def capability(self) -> CapabilityCard:
        return CapabilityCard(
            simulator_name="FLASH",
            simulator_type=SimulatorType.FLASH,
            version="4.8-mock" if self.mock else "4.8",
            physics_domains=[
                PhysicsDomain.HEDP,
                PhysicsDomain.ICF,
                PhysicsDomain.PLASMA,
            ],
            supported_dimensions=[1, 2, 3],
            input_schema={
                "temperature": InputVar(low=1e3, high=1e5, unit="K"),
                "density": InputVar(low=1e-6, high=1e2, unit="g/cm^3"),
                "magnetic_field": InputVar(low=0.0, high=50.0, unit="T"),
            },
            output_schema={
                "ionization_fraction": OutputVar(dimensions=["time", "charge_state"]),
                "radiation_spectrum": OutputVar(dimensions=["energy"]),
                "max_temperature": OutputVar(dimensions=[]),
                "avg_density": OutputVar(dimensions=[]),
                "radiation_intensity": OutputVar(dimensions=[]),
            },
            estimated_runtime="minutes to hours",
            parallel_scalable=True,
            requires_license=False,
            homepage="https://flash.rochester.edu/",
            documentation="https://flash.rochester.edu/documentation/",
        )

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        t0 = time.perf_counter()

        if self.verbose:
            print(f"\n[FlashSimulator] request_id={request.request_id}")
            print(f"  mode  = {'MOCK' if self.mock else 'REAL'}")
            print(f"  params: {request.params}")
            print(f"  work_dir: {request.work_dir or self.work_dir}")

        # 1. Validate
        try:
            self.validate_params(request.params)
        except ValueError as exc:
            if self.verbose:
                print(f"  [FlashSimulator] validation FAILED: {exc}")
            return SimulationResult(
                request_id=request.request_id,
                status=SimulationStatus.FAILED,
                execution_time=time.perf_counter() - t0,
                error_message=str(exc),
                metadata={"mode": "mock" if self.mock else "real"},
            )

        # 2. Generate input file
        work = Path(request.work_dir) if request.work_dir else self.work_dir
        work = work / request.request_id
        inp_path = _generate_flash_input(request.params, work)
        if self.verbose:
            print(f"  [FlashSimulator] wrote input file: {inp_path}")

        # 3. Run
        if self.mock:
            output_data = self._mock_run(request.params)
            status = SimulationStatus.SUCCESS
            error_message = None
        else:
            output_data, status, error_message = self._real_run(inp_path, request.timeout)

        execution_time = time.perf_counter() - t0

        if self.verbose:
            print(f"  [FlashSimulator] status={status.value} " f"time={execution_time:.3f}s")
            if status == SimulationStatus.SUCCESS:
                print(f"  [FlashSimulator] output_data keys: " f"{list(output_data.keys())}")

        return SimulationResult(
            request_id=request.request_id,
            status=status,
            output_data=output_data,
            raw_output_path=inp_path,
            execution_time=execution_time,
            error_message=error_message,
            metadata={
                "mode": "mock" if self.mock else "real",
                "flash_executable": self.flash_executable,
                "work_dir": str(work),
            },
        )

    # ---- mock physics (closed-form, deterministic) ---------------------

    def _mock_run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return physically-motivated deterministic output.

        The random seed is derived from the input parameters so that
        the same input always produces the same output – important for
        reproducible optimisation.
        """
        seed_str = json.dumps(params, sort_keys=True, default=str)
        seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16) % (2**32)
        rng = random.Random(seed)

        T = float(params.get("temperature", 3000.0))
        rho = float(params.get("density", 1e-3))
        B = float(params.get("magnetic_field", 0.0))

        if self.verbose:
            print(f"  [FlashSimulator] mock seed={seed} T={T:.2e} K, " f"rho={rho:.2e} g/cm^3, B={B:.2f} T")

        # Closed-form mock signals:
        radiation = _planck_radiation_intensity(T) * rng.uniform(0.8, 1.2)
        ionization = _saha_ionization_fraction(T, rho)
        spectrum = _planck_spectrum(T, n_bins=32)
        # Add a small (deterministic) noise to spectrum
        spectrum = [max(0.0, v * rng.gauss(1.0, 0.05)) for v in spectrum]
        # Re-normalise
        total = sum(spectrum) or 1.0
        spectrum = [v / total for v in spectrum]

        max_temp = T * rng.uniform(0.95, 1.10)
        # Magnetic field can enhance peak temperature slightly
        max_temp *= 1.0 + 0.01 * B

        return {
            "max_temperature": max_temp,
            "avg_density": rho * rng.uniform(0.95, 1.05),
            "radiation_intensity": radiation,
            "radiation_spectrum": spectrum,
            "ionization_fraction": ionization,
        }

    # ---- real run (placeholder) ----------------------------------------

    def _real_run(
        self, inp_path: Path, timeout: Optional[float]
    ) -> Tuple[Dict[str, Any], SimulationStatus, Optional[str]]:
        """Run the real FLASH executable.

        Not implemented in the MVP; this method shows the intended
        integration point.
        """
        if self.flash_executable is None:
            return (
                {},
                SimulationStatus.FAILED,
                "flash_executable not provided",
            )
        cmd = [self.flash_executable, "-par_file", str(inp_path)]
        try:
            subprocess.run(
                cmd,
                cwd=self.work_dir,
                timeout=timeout,
                check=True,
                capture_output=True,
                text=True,
            )
            output_data = _parse_flash_output(self.work_dir / "flash.dat")
            return output_data, SimulationStatus.SUCCESS, None
        except subprocess.TimeoutExpired:
            return {}, SimulationStatus.TIMEOUT, "FLASH timed out"
        except subprocess.CalledProcessError as exc:
            return {}, SimulationStatus.FAILED, str(exc)
        except FileNotFoundError as exc:
            return {}, SimulationStatus.FAILED, f"FLASH binary not found: {exc}"
