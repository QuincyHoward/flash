"""thin_layer_sandwich — Al/CH/He 与 Si/CH/He 三层靶激光烧蚀场景

两个场景:
  - thin_layer_sandwich_si: Si 靶 (新 Z 表 EOS, 5e14 W/cm², 3500K)
  - thin_layer_sandwich_al: Al 靶 (FLASH 分发旧表, 5e11 W/cm², 290K)

共享 interpolator (时空插值引擎) 与 par_builder (.par 生成器)。
"""

from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_HERE = Path(__file__).parent.resolve()


# ── 本地 defaults 加载 (si/al 各自唯一模块名, 避免缓存冲突) ──

def _load_defaults(filename: str, mod_name: str):
    path = _HERE / filename
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    sys.path.insert(0, str(_HERE))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(_HERE))
    return mod


_D_SI = _load_defaults("defaults_si.py", "thin_layer_si_defaults")
_D_AL = _load_defaults("defaults_al.py", "thin_layer_al_defaults")

# 本地共享模块
sys.path.insert(0, str(_HERE))
from par_builder import build_par as _build_par, BeamConfig  # noqa: E402

from flash.scenarios.base import SimulationScenario  # noqa: E402
from flash.scenarios.registry import register  # noqa: E402


# ── .par 构建闭包 ──────────────────────────────────────

def _make_build_par(def_mod):
    _overrides = {
        "eos_chamTableFile": def_mod.EOS_CHAM_FILE,
        "eos_targTableFile": def_mod.EOS_TARG_FILE,
        "op_chamFileName": def_mod.EOS_CHAM_FILE,
        "op_targFileName": def_mod.EOS_TARG_FILE,
        "ms_targA": def_mod.MS_TARG_A,
        "ms_targZ": def_mod.MS_TARG_Z,
        "ms_chamA": def_mod.MS_CHAM_A,
        "ms_chamZ": def_mod.MS_CHAM_Z,
        "ms_polyA": def_mod.MS_POLY_A,
        "ms_polyZ": def_mod.MS_POLY_Z,
        "sim_teleCham": getattr(def_mod, "SIM_TELE_CHAM", 3500.0),
        "sim_teleTarg": getattr(def_mod, "SIM_TELE_TARG", 3500.0),
        "sim_telePoly": getattr(def_mod, "SIM_TELE_POLY", 3500.0),
        "sim_tionCham": getattr(def_mod, "SIM_TION_CHAM", 3500.0),
        "sim_tionTarg": getattr(def_mod, "SIM_TION_TARG", 3500.0),
        "sim_tionPoly": getattr(def_mod, "SIM_TION_POLY", 3500.0),
        "sim_tradCham": getattr(def_mod, "SIM_TRAD_CHAM", 3500.0),
        "sim_tradTarg": getattr(def_mod, "SIM_TRAD_TARG", 3500.0),
        "sim_tradPoly": getattr(def_mod, "SIM_TRAD_POLY", 3500.0),
    }

    def _build_par_clojure(params):
        tmax_val = params.get("tmax", max(params.get("laser_times", [0])) + 0.1e-9)
        pulse = list(zip(params.get("laser_times", []), params.get("laser_powers", [])))
        beams = [
            BeamConfig(1, lens_x=-0.1, target_x=0,
                       wavelength=params.get("laser_wavelength", def_mod.DEFAULT_WAVELENGTH),
                       pulse_number=1),
            BeamConfig(2, lens_x=0.1, target_x=0,
                       wavelength=params.get("laser_wavelength", def_mod.DEFAULT_WAVELENGTH),
                       pulse_number=1),
        ]
        merged = dict(_overrides)
        merged["eos_polyTableFile"] = def_mod.EOS_POLY_FILE
        merged["op_polyFileName"] = def_mod.EOS_POLY_FILE
        for _tkey in ["sim_teleCham", "sim_teleTarg", "sim_telePoly",
                      "sim_tionCham", "sim_tionTarg", "sim_tionPoly",
                      "sim_tradCham", "sim_tradTarg", "sim_tradPoly"]:
            if _tkey in params:
                merged[_tkey] = params[_tkey]

        return _build_par(
            sim_name=def_mod.SIM_NAME,
            xmin_cm=params.get("xmin_cm", def_mod.XMIN_CM),
            xmax_cm=params.get("xmax_cm", def_mod.XMAX_CM),
            nblockx=params.get("nblockx", def_mod.NBX),
            lrefine_max=params.get("lrefine_max", def_mod.LR8),
            lrefine_min=params.get("lrefine_min", def_mod.LR1),
            nxb=def_mod.NXB,
            sim_rhoPoly=params.get("sim_rhoPoly", def_mod.DEFAULT_RHO_POLY),
            sim_targHeight=params.get("sim_targHeight", def_mod.DEFAULT_TARG_HEIGHT),
            sim_rhoTarg=params.get("sim_rhoTarg", def_mod.DEFAULT_RHO_TARG),
            sim_rhoCham=params.get("sim_rhoCham", def_mod.DEFAULT_RHO_CHAM),
            tmax=tmax_val,
            dtinit=params.get("dtinit", def_mod.DEFAULT_DTINIT),
            dtmin=params.get("dtmin", def_mod.DEFAULT_DTMIN),
            dtmax=params.get("dtmax", tmax_val * 1.05),
            plot_interval_step=params.get("plot_interval_step",
                                          def_mod.DEFAULT_PLOT_INTERVAL_STEP),
            laser_pulse=pulse,
            beams=beams,
            overrides=merged,
        )
    return _build_par_clojure


# ── 网格 / 插值 (共享 interpolator) ─────────────────────

def _make_build_grid(def_mod):
    def _grid_fn(params):
        from interpolator import build_variable_grid as bvg
        t_max = min(
            params.get("output_t_max", def_mod.OUTPUT_T_MAX),
            params.get("tmax", max(params.get("laser_times", [0])) + 0.1e-9),
        )
        return bvg(
            t_min=params.get("output_t_min", def_mod.OUTPUT_T_MIN),
            t_max=t_max,
            t_step=params.get("output_t_step", def_mod.OUTPUT_T_STEP),
        )
    return _grid_fn


def _make_interpolate():
    def _interp_fn(flash_files, t_grid, x_grid, var_names):
        from interpolator import interpolate_flash_to_grid
        return interpolate_flash_to_grid(
            flash_files=[str(f) for f in flash_files],
            t_grid=t_grid, x_grid=x_grid,
            var_names=var_names,
        )
    return _interp_fn


# ── 场景实例化 ──────────────────────────────────────────

SETUP_BASE = (
    "-1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio "
    "species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10"
)


def _default_times_powers(def_mod):
    pulse = def_mod.DEFAULT_LASER_PULSE
    times = [t for t, _ in pulse]
    powers = [p for _, p in pulse]
    return times, powers


def _build_scenario(name: str, def_mod) -> SimulationScenario:
    times, powers = _default_times_powers(def_mod)
    tmax_default = def_mod.DEFAULT_TMAX
    return SimulationScenario(
        name=name,
        description={
            "thin_layer_sandwich_si": "Si/CH/He 三层靶 5e14 W/cm² 激光烧蚀 (新 Z 表)",
            "thin_layer_sandwich_al": "Al/CH/He 三层靶 5e11 W/cm² 激光烧蚀 (旧 EOS 表)",
        }[name],
        run_dir_name="runs",
        scenario_dir=_HERE,
        sim_input_dir=_HERE / ("sim_input_si" if "si" in name else "sim_input_al"),
        sim_name=def_mod.SIM_NAME,
        flash_setup_args=SETUP_BASE,
        default_params={
            "sim_rhoPoly": def_mod.DEFAULT_RHO_POLY,
            "sim_targHeight": def_mod.DEFAULT_TARG_HEIGHT,
            "sim_rhoTarg": def_mod.DEFAULT_RHO_TARG,
            "sim_rhoCham": def_mod.DEFAULT_RHO_CHAM,
            "laser_wavelength": def_mod.DEFAULT_WAVELENGTH,
            "laser_times": times,
            "laser_powers": powers,
            "tmax": tmax_default,
            "dtinit": def_mod.DEFAULT_DTINIT,
            "dtmin": def_mod.DEFAULT_DTMIN,
            "xmin_cm": def_mod.XMIN_CM,
            "xmax_cm": def_mod.XMAX_CM,
            "nblockx": def_mod.NBX,
            "lrefine_max": def_mod.LR8,
            "lrefine_min": def_mod.LR1,
            "output_t_min": def_mod.OUTPUT_T_MIN,
            "output_t_max": def_mod.OUTPUT_T_MAX,
            "output_t_step": def_mod.OUTPUT_T_STEP,
            "plot_interval_step": def_mod.DEFAULT_PLOT_INTERVAL_STEP,
            "sim_teleCham": getattr(def_mod, "SIM_TELE_CHAM", 3500.0),
            "sim_teleTarg": getattr(def_mod, "SIM_TELE_TARG", 3500.0),
            "sim_telePoly": getattr(def_mod, "SIM_TELE_POLY", 3500.0),
            "sim_tionCham": getattr(def_mod, "SIM_TION_CHAM", 3500.0),
            "sim_tionTarg": getattr(def_mod, "SIM_TION_TARG", 3500.0),
            "sim_tionPoly": getattr(def_mod, "SIM_TION_POLY", 3500.0),
            "sim_tradCham": getattr(def_mod, "SIM_TRAD_CHAM", 3500.0),
            "sim_tradTarg": getattr(def_mod, "SIM_TRAD_TARG", 3500.0),
            "sim_tradPoly": getattr(def_mod, "SIM_TRAD_POLY", 3500.0),
        },
        default_output_fields=[
            "dens", "poly", "targ", "ye", "sumy",
            "tele", "tion", "trad", "pele", "pion", "prad", "pres", "velx",
        ],
        build_par=_make_build_par(def_mod),
        build_grid=_make_build_grid(def_mod),
        interpolate=_make_interpolate(),
    )


scenario_si = _build_scenario("thin_layer_sandwich_si", _D_SI)
scenario_al = _build_scenario("thin_layer_sandwich_al", _D_AL)

register("thin_layer_sandwich_si",
         "flash.scenarios.collision_compression.thin_layer_sandwich", "scenario_si")
register("thin_layer_sandwich_al",
         "flash.scenarios.collision_compression.thin_layer_sandwich", "scenario_al")
