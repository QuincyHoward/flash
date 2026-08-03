"""ch_center — CH 靶中心演化场景

CH 泡沫靶 + 两侧 He + 两束 351nm 激光相向 (5e14 W/cm²)。
共享 thin_layer_sandwich 的 interpolator, 内联 par_builder。
"""

from __future__ import annotations

import sys
from pathlib import Path

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

# 本地场景目录
_HERE = Path(__file__).parent.resolve()

from interpolator import (
    build_variable_grid as _build_variable_grid,
    interpolate_flash_to_grid as _interpolate,
)

from flash.scenarios.base import SimulationScenario
from flash.scenarios.registry import register


# ── .par 构建 ──────────────────────────────────────────

def _build_par(params: dict) -> str:
    """生成 CH 中心演化的 .par 文件"""
    laser_times = params.get("laser_times", [0, 4e-11, 1.04e-9, 1.08e-9])
    laser_powers = params.get("laser_powers", [0, 5e14, 5e14, 0])
    tmax = params.get("tmax", 1.2e-9)
    xmin = params.get("xmin", -0.01)
    xmax = params.get("xmax", 0.01)
    nblockx = params.get("nblockx", 8)
    lrefine_max = params.get("lrefine_max", 5)
    lrefine_min = params.get("lrefine_min", 1)
    nend = 10000000

    lines = []
    def _add(key, value, comment=""):
        comment = f"  # {comment}" if comment else ""
        if isinstance(value, float):
            lines.append(f"{key:<30} = {value:.6e}{comment}")
        elif isinstance(value, bool):
            sv = ".true." if value else ".false."
            lines.append(f"{key:<30} = {sv}{comment}")
        elif isinstance(value, str):
            lines.append(f'{key:<30} = "{value}"{comment}')
        else:
            lines.append(f"{key:<30} = {value}{comment}")

    _add("run_comment", "CH Center Evolution - Auto-generated")
    _add("log_file", "lasslab.log")
    _add("basenm", "lasslab_")

    # ── I/O ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  I/O PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("checkpointFileIntervalTime", 1.0)
    _add("checkpointFileIntervalStep", 20)
    _add("plotFileIntervalStep", 500)
    _add("plotFileNumber", 0)
    _add("restart", False)
    _add("checkpointFileNumber", 0)
    _add("plot_var_1", "dens")
    _add("plot_var_2", "depo")
    _add("plot_var_3", "tele")
    _add("plot_var_4", "tion")
    _add("plot_var_5", "trad")

    # ── Opacity ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  RADIATION/OPACITY PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("op_chamAbsorb", "op_tabpa")
    _add("op_chamEmiss", "op_tabpe")
    _add("op_chamFileName", "he-imx-005.cn4")
    _add("op_chamFileType", "ionmix4")
    _add("op_chamTrans", "op_tabro")
    _add("op_targAbsorb", "op_tabpa")
    _add("op_targEmiss", "op_tabpe")
    _add("op_targFileName", "polystyrene-imx-008.cn4")
    _add("op_targFileType", "ionmix4")
    _add("op_targTrans", "op_tabro")
    _add("rt_dtFactor", 0.02)
    _add("rt_mgdBounds_1", 0.1)
    _add("rt_mgdBounds_2", 1.0)
    _add("rt_mgdBounds_3", 10.0)
    _add("rt_mgdBounds_4", 100.0)
    _add("rt_mgdBounds_5", 1000.0)
    _add("rt_mgdBounds_6", 1.0e4)
    _add("rt_mgdBounds_7", 1.0e5)
    _add("rt_mgdFlCoef", 1.0)
    _add("rt_mgdFlMode", "fl_harmonic")
    _add("rt_mgdNumGroups", 6)
    _add("rt_mgdXlBoundaryType", "vacuum")
    _add("rt_mgdXrBoundaryType", "vacuum")
    _add("rt_useMGD", True)

    # ── Laser ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  LASER PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("ed_gradOrder", 2)
    _add("ed_laserIOMaxNumberOfPositions", 10000)
    _add("ed_laserIOMaxNumberOfRays", 128)
    _add("ed_maxRayCount", 10000)
    _add("ed_numberOfBeams", 2)
    _add("ed_numberOfPulses", 1)
    _add("ed_useLaserIO", False)
    n_sec = len(laser_times)
    _add("ed_numberOfSections_1", n_sec)
    for i, (t, p) in enumerate(zip(laser_times, laser_powers), 1):
        _add(f"ed_time_1_{i}", t)
        _add(f"ed_power_1_{i}", p)
    _add("ed_lensX_1", -1.0)
    _add("ed_targetX_1", 0.0)
    _add("ed_pulseNumber_1", 1)
    _add("ed_wavelength_1", params.get("wavelength_um", 0.351))
    _add("ed_crossSectionFunctionType_1", "uniform")
    _add("ed_numberOfRays_1", 1)
    _add("ed_gridType_1", "regular1D")
    _add("ed_gridnRadialTics_1", 512)
    _add("ed_lensX_2", 1.0)
    _add("ed_targetX_2", 0.0)
    _add("ed_pulseNumber_2", 1)
    _add("ed_wavelength_2", params.get("wavelength_um", 0.351))
    _add("ed_crossSectionFunctionType_2", "uniform")
    _add("ed_numberOfRays_2", 1)
    _add("ed_gradOrder", 2)
    _add("ed_gridType_2", "regular1D")
    _add("ed_gridnRadialTics_2", 512)

    # ── Conduction ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  CONDUCTION PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("diff_eleFlCoef", 0.06)
    _add("diff_eleFlMode", "fl_larsen")
    _add("diff_eleXlBoundaryType", "neumann")
    _add("diff_eleXrBoundaryType", "neumann")
    _add("diff_thetaImplct", 1)
    _add("diff_useEleCond", True)
    _add("useConductivity", True)
    _add("useDiffuse", True)

    # ── Heat exchange ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  HEAT EXCHANGE PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("useHeatexchange", True)
    _add("hx_dtFactor", 1e100)

    # ── EOS ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  EOS PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("eosModeInit", "dens_temp_gather")
    _add("eos_chamEosType", "eos_tab")
    _add("eos_chamSubType", "ionmix4")
    _add("eos_chamTableFile", "he-imx-005.cn4")
    _add("eos_targEosType", "eos_tab")
    _add("eos_targSubType", "ionmix4")
    _add("eos_targTableFile", "polystyrene-imx-008.cn4")
    _add("eos_useLogTables", False)
    _add("smallt", 1.0)
    _add("smallx", 1e-99)

    # ── Hydro ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  HYDRO PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("useHydro", True)
    _add("order", 3)
    _add("slopeLimiter", "minmod")
    _add("LimitedSlopeBeta", 1)
    _add("charLimiting", True)
    _add("use_avisc", True)
    _add("cvisc", 0.1)
    _add("use_flattening", False)
    _add("use_steepening", False)
    _add("use_upwindTVD", False)
    _add("RiemannSolver", "hllc")
    _add("entropy", False)
    _add("shockDetect", False)
    _add("use_hybridOrder", True)
    _add("xl_boundary_type", "outflow")
    _add("xr_boundary_type", "outflow")

    # ── Initial conditions ──
    _add("ms_chamA", params.get("ms_chamA", 4.0026))
    _add("ms_chamZ", params.get("ms_chamZ", 2.0))
    _add("ms_targA", params.get("ms_targA", 6.5))
    _add("ms_targZ", params.get("ms_targZ", 3.5))
    _add("ms_targZMin", params.get("ms_targZMin", 0.02))
    _add("sim_rhoCham", params.get("sim_rhoCham", 1e-6))
    _add("sim_rhoTarg", params.get("sim_rhoTarg", 1.0))
    _add("sim_targetHeight", params.get("sim_targetHeight_um", 30) * 1e-4)
    _add("sim_targetRadius", 1)
    _add("sim_teleCham", params.get("sim_teleCham", 290.11375))
    _add("sim_teleTarg", params.get("sim_teleTarg", 290.11375))
    _add("sim_tionCham", params.get("sim_tionCham", 290.11375))
    _add("sim_tionTarg", params.get("sim_tionTarg", 290.11375))
    _add("sim_tradCham", params.get("sim_tradCham", 290.11375))
    _add("sim_tradTarg", params.get("sim_tradTarg", 290.11375))
    _add("sim_vacuumHeight", params.get("sim_vacuumHeight", 700e-4))

    # ── Time ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  TIME PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("tstep_change_factor", 1.1)
    _add("cfl", params.get("cfl", 0.2))
    _add("dt_diff_factor", 1e100)
    _add("tmax", tmax)
    _add("dtmin", params.get("dtmin", 1e-16))
    _add("dtinit", params.get("dtinit", 1e-16))
    _add("dtmax", params.get("dtmax", tmax*1.05))
    _add("nend", nend)

    # ── Mesh ──
    lines.append("")
    lines.append("##############################")
    lines.append("#  MESH PARAMETERS")
    lines.append("##############################")
    lines.append("")
    _add("geometry", "cartesian")
    _add("xmin", xmin)
    _add("xmax", xmax)
    _add("nblockx", nblockx)
    _add("lrefine_max", lrefine_max)
    _add("lrefine_min", lrefine_min)
    _add("refine_var_1", "dens")
    _add("refine_var_2", "tele")

    _add("useEnergyDeposition", True)
    _add("useOpacity", True)

    return "\n".join(lines)


# ── 网格生成 ──────────────────────────────────────────

def _build_grid(params: dict):
    xmin = params.get("xmin", -0.01)
    xmax = params.get("xmax", 0.01)
    t_max = min(
        params.get("output_t_max", 1.0e-9),
        params.get("tmax", 1.2e-9),
    )
    return _build_variable_grid(
        t_min=params.get("output_t_min", 0.0),
        t_max=t_max,
        t_step=params.get("output_t_step", 10e-12),
    )


def _interpolate_fn(flash_files, t_grid, x_grid, var_names):
    return _interpolate(
        flash_files=[str(f) for f in flash_files],
        t_grid=t_grid, x_grid=x_grid,
        var_names=var_names,
    )


# ── 场景实例 ──────────────────────────────────────────

scenario = SimulationScenario(
    name="ch_center",
    description="CH 靶中心时域演化 5e14 W/cm²",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "flash_input",
    sim_name="LaserSlab1D_new",
    run_dir_name="runs_ch_center",
    flash_setup_args=(
        "-1d +cartesian -nxb=16 "
        "-maxblocks=2048 +hdf5typeio species=cham,targ "
        "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
    ),
    default_params={
        "tmax": 1.2e-9,
        "laser_times": [0, 4e-11, 1.04e-9, 1.08e-9],
        "laser_powers": [0, 5e14, 5e14, 0],
        "wavelength_um": 0.351,
        "xmin": -0.01,
        "xmax": 0.01,
        "nblockx": 8,
        "lrefine_max": 5,
        "lrefine_min": 1,
        "sim_rhoCham": 1e-6,
        "sim_rhoTarg": 1.0,
        "sim_targetHeight_um": 30,
        "sim_teleCham": 290.11375,
        "sim_teleTarg": 290.11375,
        "sim_tionCham": 290.11375,
        "sim_tionTarg": 290.11375,
        "sim_tradCham": 290.11375,
        "sim_tradTarg": 290.11375,
        "ms_chamA": 4.0026,
        "ms_chamZ": 2.0,
        "ms_targA": 6.5,
        "ms_targZ": 3.5,
        "ms_targZMin": 0.02,
        "sim_vacuumHeight": 700e-4,
        "output_t_min": 0.0,
        "output_t_max": 1.0e-9,
        "output_t_step": 10e-12,
        "cfl": 0.2,
        "dtinit": 1e-16,
        "dtmin": 1e-16,
    },
    default_output_fields=[
        "dens", "tele", "tion", "trad", "ye", "sumy", "pres",
    ],
    build_par=_build_par,
    build_grid=_build_grid,
    interpolate=_interpolate_fn,
)

register("ch_center", "flash.scenarios.center_evolution.ch_center", "scenario")
