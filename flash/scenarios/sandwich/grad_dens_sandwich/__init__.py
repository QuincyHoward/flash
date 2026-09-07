"""grad_dens_sandwich — HE-CH-Si-CH-HE 渐变密度 CH 场景

完全自包含, 不依赖 flash_demo/。

关键特性:
  - 超高斯激光脉冲 (order=4, 1ns FWHM, 5e14 W/cm²)
  - CH 密度梯度: 由 ch_posx_1/ch_dens_1, ch_posx_2/ch_dens_2 控制
"""

from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

_HERE = Path(__file__).parent.resolve()

# 本地 defaults 文件
def _load_defaults(filename):
    """加载本地的 defaults.py, 使用唯一模块名避免缓存冲突"""
    path = _HERE / filename
    mod_name = "grad_dens_defaults"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    sys.path.insert(0, str(_HERE))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(_HERE))
    return mod

_D = _load_defaults("defaults.py")

# 本地共享模块
sys.path.insert(0, str(_HERE))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("grad_dens_par_builder", str(_HERE / "par_builder.py"))
_pb = _ilu.module_from_spec(_spec)
sys.modules["grad_dens_par_builder"] = _pb
_spec.loader.exec_module(_pb)
_build_par, BeamConfig = _pb.build_par, _pb.BeamConfig

from flash.scenarios.base import SimulationScenario
from flash.scenarios.registry import register


# ── 超高斯脉冲生成器 ──────────────────────────────────────

def make_super_gaussian_pulse(
    peak_power: float = 5e14,
    center_time: float = 0.6e-9,
    fwhm: float = 1.0e-9,
    order: int = 4,
    n_points: int = 120,
    time_start: float = 0.0,
    time_end: float = 1.2e-9,
    threshold_ratio: float = 1e-6,
) -> List[Tuple[float, float]]:
    """生成超高斯脉冲 P(t)=P0*exp(-ln2*[2(t-t0)/FWHM]^(2*order))

    Returns:
        [(t1, p1), (t2, p2), ...] 用于 ed_time/ed_power
    """
    times = np.linspace(time_start, time_end, n_points)
    exponent = (2.0 * (times - center_time) / fwhm) ** (2 * order) * np.log(2.0)
    powers = peak_power * np.exp(-exponent)
    powers = np.clip(powers, 0.0, None)
    threshold = peak_power * threshold_ratio
    valid = powers > threshold
    result = list(zip(times[valid].tolist(), powers[valid].tolist()))
    # Ensure first point is at t=0.0 with power=0.0 (FLASH requires strictly increasing times)
    if result:
        t0, p0 = result[0]
        if t0 > 0.0 and p0 > 0.0:
            result.insert(0, (0.0, 0.0))
        elif t0 == 0.0 and p0 > 0.0:
            # Overwrite first point: start at t=0 with power=0
            result[0] = (0.0, 0.0)
    return result


# ── 默认超高斯脉冲 ────────────────────────────────────────
_DEFAULT_SUPER_GAUSSIAN = make_super_gaussian_pulse(
    peak_power=5e14,
    center_time=0.6e-9,
    fwhm=1.0e-9,
    order=4,
)


# ── .par 生成器 ────────────────────────────────────────────

def _make_build_par(def_mod):
    _overrides = {
        "eos_chamTableFile": def_mod.EOS_CHAM_FILE,
        "eos_targTableFile": def_mod.EOS_TARG_FILE,
        "op_chamFileName": def_mod.EOS_CHAM_FILE,
        "op_targFileName": def_mod.EOS_TARG_FILE,
        "eos_polyTableFile": def_mod.EOS_POLY_FILE,
        "op_polyFileName": def_mod.EOS_POLY_FILE,
    }
    for attr, pname in [("MS_TARG_A", "ms_targA"),
                         ("MS_TARG_Z", "ms_targZ"),
                         ("MS_CHAM_A", "ms_chamA"),
                         ("MS_CHAM_Z", "ms_chamZ"),
                         ("MS_POLY_A", "ms_polyA"),
                         ("MS_POLY_Z", "ms_polyZ")]:
        if hasattr(def_mod, attr):
            _overrides[pname] = getattr(def_mod, attr)

    def _build_par_clojure(params):
        tmax_val = params.get("tmax", max(params.get("laser_times", [0])) + 0.1e-9)
        pulse = list(zip(params.get("laser_times", []), params.get("laser_powers", [])))
        beams = [
            BeamConfig(1, lens_x=-0.1, target_x=0,
                       wavelength=params.get("laser_wavelength", 0.351), pulse_number=1),
            BeamConfig(2, lens_x=0.1, target_x=0,
                       wavelength=params.get("laser_wavelength", 0.351), pulse_number=1),
        ]
        _merged_overrides = dict(_overrides)
        for _tkey in ["sim_teleCham", "sim_teleTarg", "sim_telePoly",
                       "sim_tionCham", "sim_tionTarg", "sim_tionPoly",
                       "sim_tradCham", "sim_tradTarg", "sim_tradPoly"]:
            if _tkey in params:
                _merged_overrides[_tkey] = params[_tkey]

        # CH 密度梯度控制点覆盖 (ch_num + 10 组)
        if "ch_num" in params:
            _merged_overrides["ch_num"] = params["ch_num"]
        _ch_keys = []
        for _i in range(1, 11):
            _ch_keys.append(f"ch_posx_{_i}")
            _ch_keys.append(f"ch_dens_{_i}")
        for _ckey in _ch_keys:
            if _ckey in params:
                _merged_overrides[_ckey] = params[_ckey]

        _tele_cham = params.get("sim_teleCham", 3500.00)
        if abs(_tele_cham - 290.11375) > 1.0:
            warnings.warn(
                f"场景 'grad_dens_sandwich' "
                f"初始温度已设为 {_tele_cham:.2f} K（非室温 290.11375 K）。\n"
                f"  原因: 新 EOS/opacity 表在 290K 时扩散求解器可能产生负时间步。"
            )

        _par_result = _build_par(
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
            overrides=_merged_overrides,
        )
        # Post-filter: remove sim_polyHeight (computed from ch_posx in Fortran)
        result_lines = []
        for _l in _par_result.split("\n"):
            _s = _l.strip()
            if _s.startswith("sim_polyHeight") and "=" in _s and not _s.startswith("#"):
                continue  # skip
            result_lines.append(_l)
        return "\n".join(result_lines)
    return _build_par_clojure


# ── 通用网格生成 / 插值 (复用 thin_layer_sandwich 工具) ──

def _make_build_grid(def_mod):
    def _grid_fn(params):
        from flash.scenarios.sandwich.thin_layer_sandwich.interpolator import (
            build_variable_grid as bvg,
        )
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
        from flash.scenarios.sandwich.thin_layer_sandwich.interpolator import (
            interpolate_flash_to_grid,
        )
        return interpolate_flash_to_grid(
            flash_files=[str(f) for f in flash_files],
            t_grid=t_grid, x_grid=x_grid,
            var_names=var_names,
        )
    return _interp_fn


# ── 场景实例化 ────────────────────────────────────────────

GRAD_DENS_SETUP = (
    "-1d +cartesian -nxb=16 "
    "-maxblocks=2048 +hdf5typeio species=cham,targ,poly "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=240"
)

_DEFAULT_TIMES = [t for t, _ in _DEFAULT_SUPER_GAUSSIAN]
_DEFAULT_POWERS = [p for _, p in _DEFAULT_SUPER_GAUSSIAN]
_DEFAULT_TMAX = max(_DEFAULT_TIMES) + 0.2e-9

class _AutoGenScenario(SimulationScenario):
    """sim_input 非py输入文件由 gen_flash_inputs.py 按需自动生成的场景。"""

    def _gen_module_name(self) -> str:
        return "flash.scenarios.sandwich.grad_dens_sandwich.gen_flash_inputs"

    def ensure_sim_input(self) -> None:
        d = self.sim_input_dir
        if (d / "Config").exists() and any(d.glob("*.par")):
            return
        import importlib as _il
        gen = _il.import_module(self._gen_module_name())
        if not gen.ensure_generated():
            raise FileNotFoundError(
                f"场景 {self.name} 输入文件生成失败, 见 gen_flash_inputs 日志")


scenario_grad = _AutoGenScenario(
    name="grad_dens_sandwich",
    description="HE-CH-Si-CH-HE 渐变密度 CH 超高斯激光 (order=4, 1ns, 5e14 W/cm²)",
    run_dir_name="runs_grad_dens_sandwich",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "sim_input",
    sim_name=_D.SIM_NAME,
    flash_setup_args=GRAD_DENS_SETUP,
    default_params={
        "sim_rhoPoly": _D.DEFAULT_RHO_POLY,
        "sim_targHeight": _D.DEFAULT_TARG_HEIGHT,
        "sim_rhoTarg": _D.DEFAULT_RHO_TARG,
        "sim_rhoCham": _D.DEFAULT_RHO_CHAM,
        "laser_wavelength": _D.DEFAULT_WAVELENGTH,
        "laser_times": _DEFAULT_TIMES,
        "laser_powers": _DEFAULT_POWERS,
        "tmax": _DEFAULT_TMAX,
        "dtinit": _D.DEFAULT_DTINIT,
        "dtmin": _D.DEFAULT_DTMIN,
        "xmin_cm": _D.XMIN_CM,
        "xmax_cm": _D.XMAX_CM,
        "nblockx": _D.NBX,
        "lrefine_max": _D.LR8,
        "lrefine_min": _D.LR1,
        "output_t_min": _D.OUTPUT_T_MIN,
        "output_t_max": _D.OUTPUT_T_MAX,
        "output_t_step": _D.OUTPUT_T_STEP,
        "plot_interval_step": _D.DEFAULT_PLOT_INTERVAL_STEP,
        # CH 密度梯度控制点 (ch_num + 10 组)
        "ch_num": 0,
        "ch_posx_1": 0.0,  "ch_dens_1": 0.0,
        "ch_posx_2": 0.0,  "ch_dens_2": 0.0,
        "ch_posx_3": 0.0,  "ch_dens_3": 0.0,
        "ch_posx_4": 0.0,  "ch_dens_4": 0.0,
        "ch_posx_5": 0.0,  "ch_dens_5": 0.0,
        "ch_posx_6": 0.0,  "ch_dens_6": 0.0,
        "ch_posx_7": 0.0,  "ch_dens_7": 0.0,
        "ch_posx_8": 0.0,  "ch_dens_8": 0.0,
        "ch_posx_9": 0.0,  "ch_dens_9": 0.0,
        "ch_posx_10": 0.0, "ch_dens_10": 0.0,
        # 初始温度 (新 EOS 表需要高温)
        "sim_teleCham": 3500.00,
        "sim_teleTarg": 3500.00,
        "sim_telePoly": 3500.00,
        "sim_tionCham": 3500.00,
        "sim_tionTarg": 3500.00,
        "sim_tionPoly": 3500.00,
        "sim_tradCham": 3500.00,
        "sim_tradTarg": 3500.00,
        "sim_tradPoly": 3500.00,
    },
    default_output_fields=[
        "dens", "poly", "targ", "ye", "sumy",
        "tele", "tion", "trad", "pele", "pion", "prad", "pres", "velx",
    ],
    build_par=_make_build_par(_D),
    build_grid=_make_build_grid(_D),
    interpolate=_make_interpolate(),
)

register("grad_dens_sandwich",
         "flash.scenarios.sandwich.grad_dens_sandwich", "scenario_grad")
