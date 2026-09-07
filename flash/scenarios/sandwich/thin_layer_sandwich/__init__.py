"""thin_layer_sandwich — Si/CH/He 与 Al/CH/He 三层靶场景

完全自包含, 不依赖 flash_demo/。
"""

from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path

_HERE = Path(__file__).parent.resolve()

# 本地 defaults 文件
def _load_defaults(filename):
    """加载本地的 defaults_{si,al}.py, 避免模块名冲突"""
    path = _HERE / filename
    mod_name = filename.replace(".py", "")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(_HERE))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(_HERE))
    return mod

_DSI = _load_defaults("defaults_si.py")
_DAL = _load_defaults("defaults_al.py")

# 本地共享模块 (par_builder 从本目录找 defaults.py)
sys.path.insert(0, str(_HERE))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("thin_layer_par_builder", str(_HERE / "par_builder.py"))
_pb = _ilu.module_from_spec(_spec)
sys.modules["thin_layer_par_builder"] = _pb
_spec.loader.exec_module(_pb)
_build_par, BeamConfig = _pb.build_par, _pb.BeamConfig
from interpolator import (
    build_variable_grid,
    interpolate_flash_to_grid,
    DEFAULT_OUTPUT_FIELDS,
)

from flash.scenarios.base import SimulationScenario
from flash.scenarios.registry import register

# ── 新子包导入 ──────────────────────────────────────────
try:
    from . import io as io
    from . import analysis as analysis
    from . import viz as viz
except ImportError:
    pass


# ── 通用 .par 生成器 ──────────────────────────────────────

def _make_build_par(def_mod):
    """根据场景 defaults 模块生成 build_par 闭包"""
    # 从 defaults 提取 EOS + 原子参数覆盖
    _overrides = {
        "eos_chamTableFile": def_mod.EOS_CHAM_FILE,
        "eos_targTableFile": def_mod.EOS_TARG_FILE,
        "op_chamFileName": def_mod.EOS_CHAM_FILE,
        "op_targFileName": def_mod.EOS_TARG_FILE,
        "eos_polyTableFile": def_mod.EOS_POLY_FILE,
        "op_polyFileName": def_mod.EOS_POLY_FILE,
    }
    # 如 defaults 中有原子参数定义则一并覆盖
    for attr, pname in [("MS_TARG_A", "ms_targA"),
                         ("MS_TARG_Z", "ms_targZ"),
                         ("MS_CHAM_A", "ms_chamA"),
                         ("MS_CHAM_Z", "ms_chamZ"),
                         ("MS_POLY_A", "ms_polyA"),
                         ("MS_POLY_Z", "ms_polyZ")]:
        if hasattr(def_mod, attr):
            _overrides[pname] = getattr(def_mod, attr)

    def _build_par_clojure(params):
        tmax_val = max(params.get("laser_times", [0])) + 0.1e-9
        pulse = list(zip(params.get("laser_times", []), params.get("laser_powers", [])))
        beams = [
            BeamConfig(1, lens_x=-0.1, target_x=0,
                       wavelength=params.get("laser_wavelength", 0.351), pulse_number=1),
            BeamConfig(2, lens_x=0.1, target_x=0,
                       wavelength=params.get("laser_wavelength", 0.351), pulse_number=1),
        ]
        # 合并用户传入的温度覆盖
        _merged_overrides = dict(_overrides)
        for _tkey in ["sim_teleCham", "sim_teleTarg", "sim_telePoly",
                       "sim_tionCham", "sim_tionTarg", "sim_tionPoly",
                       "sim_tradCham", "sim_tradTarg", "sim_tradPoly"]:
            if _tkey in params:
                _merged_overrides[_tkey] = params[_tkey]
        # 透传其他 .par 参数（如 checkpointFileIntervalStep 等）
        for _par_key in ["checkpointFileIntervalStep", "checkpointFileIntervalTime",
                         "plotFileIntervalStep", "plotFileNumber"]:
            if _par_key in params:
                _merged_overrides[_par_key] = params[_par_key]

        # 检测并警示非室温初始温度（主要是 Si 场景因扩散求解器稳定性需要高温）
        _tele_cham = params.get("sim_teleCham", 290.11375)
        if abs(_tele_cham - 290.11375) > 1.0:
            warnings.warn(
                f"场景 '{def_mod.__name__.replace('defaults_', '').replace('defaults', '')}' "
                f"初始温度已设为 {_tele_cham:.2f} K（非室温 290.11375 K）。\n"
                f"  原因: 新 EOS/opacity 表在 290K 时扩散求解器可能产生负时间步。\n"
                f"  如需恢复室温，请在 params_overrides 中显式传入 sim_teleCham=290.11375 等参数。"
            )

        return _build_par(
            sim_name=def_mod.SIM_NAME,
            xmin_cm=params.get("xmin_cm", def_mod.XMIN_CM),
            xmax_cm=params.get("xmax_cm", def_mod.XMAX_CM),
            nblockx=params.get("nblockx", def_mod.NBX),
            lrefine_max=params.get("lrefine_max", def_mod.LR8),
            lrefine_min=params.get("lrefine_min", def_mod.LR1),
            nxb=def_mod.NXB,
            sim_polyHeight=params.get("sim_polyHeight", def_mod.DEFAULT_POLY_HEIGHT),
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
    return _build_par_clojure


# ── 通用网格生成 / 插值器 ─────────────────────────────────

def _make_build_grid(def_mod):
    def _grid_fn(params):
        from interpolator import build_variable_grid as bvg
        t_max = min(
            params.get("output_t_max", def_mod.OUTPUT_T_MAX),
            max(params.get("laser_times", [0])) + 0.1e-9,
        )
        return bvg(
            t_min=params.get("output_t_min", def_mod.OUTPUT_T_MIN),
            t_max=t_max,
            t_step=params.get("output_t_step", def_mod.OUTPUT_T_STEP),
        )
    return _grid_fn


def _make_interpolate():
    def _interp_fn(flash_files, t_grid, x_grid, var_names):
        return interpolate_flash_to_grid(
            flash_files=[str(f) for f in flash_files],
            t_grid=t_grid, x_grid=x_grid,
            var_names=var_names,
        )
    return _interp_fn


# ── 场景实例化 ────────────────────────────────────────────

def _make_auto_gen_cls(variant: str):
    """为 si/al 变体生成带 sim_input 自动生成的场景类。"""
    gen_mod = f"flash.scenarios.sandwich.thin_layer_sandwich.gen_flash_inputs"

    class _AutoGenScenario(SimulationScenario):
        def _gen_module_name(self) -> str:
            return gen_mod

        def ensure_sim_input(self) -> None:
            d = self.sim_input_dir
            if (d / "Config").exists() and any(d.glob("*.par")):
                return
            import importlib as _il
            gen = _il.import_module(self._gen_module_name())
            if not gen.ensure_generated(variant):
                raise FileNotFoundError(
                    f"场景 {self.name} 输入文件生成失败, 见 gen_flash_inputs 日志")

    return _AutoGenScenario


THIN_LAYER_SETUP = (
    "-1d +cartesian -nxb=16 "
    "-maxblocks=2048 +hdf5typeio species=cham,targ,poly "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=240"
)

# ------ Si 场景 ------

scenario_si = _make_auto_gen_cls('si')(
    name="thin_layer_sandwich_si",
    description="Si/CH/He 三层靶 5e14 W/cm² 激光烧蚀 (新 EOS 表)",
    run_dir_name="runs_thin_layer_sandwich_si",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "sim_input_si",
    sim_name=_DSI.SIM_NAME,
    flash_setup_args=THIN_LAYER_SETUP,
    default_params={
        "sim_polyHeight": _DSI.DEFAULT_POLY_HEIGHT,
        "sim_rhoPoly": _DSI.DEFAULT_RHO_POLY,
        "sim_targHeight": _DSI.DEFAULT_TARG_HEIGHT,
        "sim_rhoTarg": _DSI.DEFAULT_RHO_TARG,
        "sim_rhoCham": _DSI.DEFAULT_RHO_CHAM,
        "laser_wavelength": _DSI.DEFAULT_WAVELENGTH,
        "laser_times": [t for t, _ in _DSI.DEFAULT_LASER_PULSE],
        "laser_powers": [p for _, p in _DSI.DEFAULT_LASER_PULSE],
        "tmax": _DSI.DEFAULT_TMAX,
        "dtinit": _DSI.DEFAULT_DTINIT,
        "dtmin": _DSI.DEFAULT_DTMIN,
        "xmin_cm": _DSI.XMIN_CM,
        "xmax_cm": _DSI.XMAX_CM,
        "nblockx": _DSI.NBX,
        "lrefine_max": _DSI.LR8,
        "lrefine_min": _DSI.LR1,
        "output_t_min": _DSI.OUTPUT_T_MIN,
        "output_t_max": _DSI.OUTPUT_T_MAX,
        "output_t_step": _DSI.OUTPUT_T_STEP,
        "plot_interval_step": _DSI.DEFAULT_PLOT_INTERVAL_STEP,
        # Si 场景使用新 EOS 表 (Z02/Z06/Z14, 起始 0.01 eV ≈ 116 K) 和 eos_gam，
        # 但 FLASH 扩散求解器在 290K 低温下 opacity 插值会计算负时间步。
        # 提升初始温度至 3500K 可保证扩散求解器在低密度 He/CH 界面稳定。
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
    default_output_fields=DEFAULT_OUTPUT_FIELDS,
    build_par=_make_build_par(_DSI),
    build_grid=_make_build_grid(_DSI),
    interpolate=_make_interpolate(),
)

# ------ Al 场景 ------

scenario_al = _make_auto_gen_cls('al')(
    name="thin_layer_sandwich_al",
    description="Al/CH/He 三层靶 5e11 W/cm² 激光烧蚀 (原始 EOS 表)",
    run_dir_name="runs_thin_layer_sandwich_al",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "sim_input_al",
    sim_name=_DAL.SIM_NAME,
    flash_setup_args=THIN_LAYER_SETUP,
    default_params={
        "sim_polyHeight": _DAL.DEFAULT_POLY_HEIGHT,
        "sim_rhoPoly": _DAL.DEFAULT_RHO_POLY,
        "sim_targHeight": _DAL.DEFAULT_TARG_HEIGHT,
        "sim_rhoTarg": _DAL.DEFAULT_RHO_TARG,
        "sim_rhoCham": _DAL.DEFAULT_RHO_CHAM,
        "laser_wavelength": _DAL.DEFAULT_WAVELENGTH,
        "laser_times": [t for t, _ in _DAL.DEFAULT_LASER_PULSE],
        "laser_powers": [p for _, p in _DAL.DEFAULT_LASER_PULSE],
        "tmax": _DAL.DEFAULT_TMAX,
        "dtinit": _DAL.DEFAULT_DTINIT,
        "dtmin": _DAL.DEFAULT_DTMIN,
        "xmin_cm": _DAL.XMIN_CM,
        "xmax_cm": _DAL.XMAX_CM,
        "nblockx": _DAL.NBX,
        "lrefine_max": _DAL.LR8,
        "lrefine_min": _DAL.LR1,
        "output_t_min": _DAL.OUTPUT_T_MIN,
        "output_t_max": _DAL.OUTPUT_T_MAX,
        "output_t_step": _DAL.OUTPUT_T_STEP,
        "plot_interval_step": _DAL.DEFAULT_PLOT_INTERVAL_STEP,
    },
    default_output_fields=DEFAULT_OUTPUT_FIELDS,
    build_par=_make_build_par(_DAL),
    build_grid=_make_build_grid(_DAL),
    interpolate=_make_interpolate(),
)

register("thin_layer_sandwich_si",
         "flash.scenarios.sandwich.thin_layer_sandwich", "scenario_si")
register("thin_layer_sandwich_al",
         "flash.scenarios.sandwich.thin_layer_sandwich", "scenario_al")
