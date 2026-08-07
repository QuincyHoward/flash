"""独立 .par 文件生成器 — 不依赖 physimx_sim

直接从 defaults.py 获取默认值，用 Python dict + string formatting 生成 FLASH .par 文件。

支持:
  - 任意数量的激光脉冲段 (ed_numberOfSections_X)
  - 多束激光 (BeamConfig)
  - 自动清理残留参数 (如 ed_time_1_5 当 numberOfSections=4 时)
"""

from __future__ import annotations
import os, sys
from typing import Dict, List, Optional, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
import defaults as D


# ============================================================
# Beam 配置
# ============================================================

class BeamConfig:
    """单束激光参数"""
    def __init__(self, beam_id: int, lens_x: float, target_x: float,
                 wavelength: float = D.DEFAULT_WAVELENGTH,
                 pulse_number: int = 1,
                 nrays: int = 1, grid_type: str = "regular1D",
                 grid_ntics: int = 512,
                 cross_section: str = "uniform"):
        self.beam_id = beam_id
        self.lens_x = lens_x
        self.target_x = target_x
        self.wavelength = wavelength
        self.pulse_number = pulse_number
        self.nrays = nrays
        self.grid_type = grid_type
        self.grid_ntics = grid_ntics
        self.cross_section = cross_section


# ============================================================
# .par 构建器
# ============================================================

# 所有 1D 默认参数 (从 input_gen/gen_par/defaults.py PARAMS_1D 提取)
_PARAMS_1D: Dict[str, object] = {
    "LimitedSlopeBeta": 1.0,
    "RiemannSolver": "hllc",
    "cfl": 0.4,
    "charLimiting": True,
    "checkpointFileIntervalStep": 20,
    "checkpointFileIntervalTime": 1.0,
    "checkpointFileNumber": 0,
    "cvisc": 0.1,
    "diff_eleFlCoef": 0.06,
    "diff_eleFlMode": "fl_larsen",
    "diff_eleXlBoundaryType": "neumann",
    "diff_eleXrBoundaryType": "neumann",
    "diff_thetaImplct": 1.0,
    "diff_useEleCond": True,
    "dt_diff_factor": 1e100,
    "ed_crossSectionFunctionType_1": "uniform",
    "ed_gradOrder": 2,
    "ed_gridType_1": "regular1D",
    "ed_gridnRadialTics_1": 512,
    "ed_laserIOMaxNumberOfPositions": 10000,
    "ed_laserIOMaxNumberOfRays": 128,
    "ed_maxRayCount": 10000,
    "ed_numberOfBeams": 1,
    "ed_numberOfPulses": 1,
    "ed_numberOfRays_1": 1,
    "ed_numberOfSections_1": 5,
    "ed_useLaserIO": False,
    "entropy": False,
    "eosModeInit": "dens_temp_gather",
    "eos_chamEosType": "eos_tab",
    "eos_chamSubType": "ionmix4",
    "eos_chamTableFile": D.EOS_CHAM_FILE,
    "eos_targEosType": "eos_tab",
    "eos_targSubType": "ionmix4",
    "eos_targTableFile": D.EOS_TARG_FILE,
    "eos_useLogTables": False,
    "geometry": "cartesian",
    "hx_dtFactor": 1e100,
    "ms_chamA": 4.002602,
    "ms_chamZ": 2.0,
    "ms_targA": 26.9815386,
    "ms_targZ": 13.0,
    "ms_targZMin": 0.02,
    "nend": 10000000,
    "op_chamAbsorb": "op_tabpa",
    "op_chamEmiss": "op_tabpe",
    "op_chamFileName": D.EOS_CHAM_FILE,
    "op_chamFileType": "ionmix4",
    "op_chamTrans": "op_tabro",
    "op_targAbsorb": "op_tabpa",
    "op_targEmiss": "op_tabpe",
    "op_targFileName": D.EOS_TARG_FILE,
    "op_targFileType": "ionmix4",
    "op_targTrans": "op_tabro",
    "order": 3,
    "plotFileNumber": 0,
    "plot_var_1": "dens",
    "plot_var_2": "depo",
    "plot_var_3": "tele",
    "plot_var_4": "tion",
    "plot_var_5": "trad",
    "plot_var_6": "ye  ",
    "plot_var_7": "sumy",
    "plot_var_8": "cham",
    "plot_var_9": "targ",
    "plot_var_10": "poly",
    "refine_var_1": "dens",
    "refine_var_2": "tele",
    "restart": False,
    "rt_dtFactor": 0.02,
    "rt_mgdBounds_1": 0.1,
    "rt_mgdBounds_2": 1.0,
    "rt_mgdBounds_3": 10.0,
    "rt_mgdBounds_4": 100.0,
    "rt_mgdBounds_5": 1000.0,
    "rt_mgdBounds_6": 10000.0,
    "rt_mgdBounds_7": 100000.0,
    "rt_mgdFlCoef": 1.0,
    "rt_mgdFlMode": "fl_harmonic",
    "rt_mgdNumGroups": 6,
    "rt_mgdXlBoundaryType": "vacuum",
    "rt_mgdXrBoundaryType": "vacuum",
    "rt_useMGD": True,
    "shockDetect": False,
    "sim_teleCham": 290.11375,
    "sim_teleTarg": 290.11375,
    "sim_tionCham": 290.11375,
    "sim_tionTarg": 290.11375,
    "sim_tradCham": 290.11375,
    "sim_tradTarg": 290.11375,
    "slopeLimiter": "minmod",
    "smallt": 1.0,
    "smallx": 1e-99,
    "tstep_change_factor": 1.1,
    "useConductivity": True,
    "useDiffuse": True,
    "useEnergyDeposition": True,
    "useHeatexchange": True,
    "useHydro": True,
    "useOpacity": True,
    "use_avisc": True,
    "use_flattening": False,
    "use_hybridOrder": True,
    "use_steepening": False,
    "use_upwindTVD": False,
    "xl_boundary_type": "outflow",
    "xr_boundary_type": "outflow",
}


def _fmt(v: object) -> str:
    """将参数值格式化为 FLASH .par 文件中的字符串"""
    if isinstance(v, bool):
        return ".true." if v else ".false."
    if isinstance(v, float):
        # 科学计数法，紧凑形式
        return f"{v:.15g}"
    if isinstance(v, int):
        return str(v)
    return str(v)


def build_par(
    sim_name: str = D.SIM_NAME,
    xmin_cm: float = D.XMIN_CM,
    xmax_cm: float = D.XMAX_CM,
    nblockx: int = D.NBX,
    lrefine_max: int = D.LR8,
    lrefine_min: int = D.LR1,
    nxb: int = D.NXB,
    # 材料参数
    sim_ployHeight: float = D.DEFAULT_POLY_HEIGHT,
    sim_rhoPoly: float = D.DEFAULT_RHO_POLY,
    sim_targHeight: float = D.DEFAULT_TARG_HEIGHT,
    sim_rhoTarg: float = D.DEFAULT_RHO_TARG,
    sim_rhoCham: float = D.DEFAULT_RHO_CHAM,
    # 时间控制
    tmax: float = D.DEFAULT_TMAX,
    dtinit: float = D.DEFAULT_DTINIT,
    dtmin: float = D.DEFAULT_DTMIN,
    dtmax: float = D.DEFAULT_DTMAX,
    # 输出控制
    plot_interval_step: int = D.DEFAULT_PLOT_INTERVAL_STEP,
    # 激光脉冲
    laser_pulse: Optional[List[Tuple[float, float]]] = None,
    # 激光光束
    beams: Optional[List[BeamConfig]] = None,
    # CH EOS/op 文件名
    eos_poly_table: str = D.EOS_POLY_FILE,
    # 额外参数 (覆盖默认)
    overrides: Optional[Dict[str, object]] = None,
) -> str:
    """生成 FLASH .par 文件内容字符串

    Args:
        sim_name: 仿真名称 (用于 basenm)
        xmin_cm, xmax_cm: 域边界 (cm)
        nblockx: 初始分块数
        lrefine_max, lrefine_min: AMR 细化层级
        nxb: 每块单元数 (必须匹配 Flash.h 中的 NXB)
        sim_ployHeight: CH 半厚 (cm)
        sim_rhoPoly: CH 密度 (g/cm^3)
        sim_targHeight: Al 半厚 (cm)
        sim_rhoTarg: Al 密度 (g/cm^3)
        sim_rhoCham: He 填充密度 (g/cm^3)
        tmax, dtinit, dtmin, dtmax: 时间控制
        plot_interval_step: 每多少步输出一个 plot 文件
        laser_pulse: [(time_s, power_Wcm2), ...] 脉冲波形
        beams: 光束配置列表
        overrides: 额外参数覆盖

    Returns:
        .par 文件内容字符串 (LF 换行)
    """
    # 从默认值开始
    params = dict(_PARAMS_1D)

    # 应用覆盖
    params["xmin"] = xmin_cm
    params["xmax"] = xmax_cm
    params["nblockx"] = nblockx
    params["lrefine_max"] = lrefine_max
    params["lrefine_min"] = lrefine_min
    params["tmax"] = tmax
    params["dtinit"] = dtinit
    params["dtmin"] = dtmin
    params["dtmax"] = dtmax
    params["plotFileIntervalStep"] = plot_interval_step

    # 材料参数
    params["sim_rhoTarg"] = sim_rhoTarg
    params["sim_rhoPoly"] = sim_rhoPoly
    params["sim_rhoCham"] = sim_rhoCham
    params["sim_targHeight"] = sim_targHeight
    params["sim_polyHeight"] = sim_ployHeight
    params["eos_polyEosType"] = "eos_tab"
    params["eos_polySubType"] = "ionmix4"
    params["eos_polyTableFile"] = eos_poly_table
    params["op_polyAbsorb"] = "op_tabpa"
    params["op_polyEmiss"] = "op_tabpe"
    params["op_polyTrans"] = "op_tabro"
    params["op_polyFileType"] = "ionmix4"
    params["op_polyFileName"] = eos_poly_table
    # CH 材料属性 (polystyrene: (C8H8)n)
    params["ms_polyA"] = 6.5
    params["ms_polyZ"] = 3.5
    params["sim_telePoly"] = 290
    params["sim_tionPoly"] = 290
    params["sim_tradPoly"] = 290

    # 激光脉冲
    if laser_pulse is not None:
        n_sections = len(laser_pulse)
        params["ed_numberOfSections_1"] = n_sections
        for i, (t, p) in enumerate(laser_pulse, start=1):
            params[f"ed_time_1_{i}"] = t
            params[f"ed_power_1_{i}"] = p
        # 清理残留: 删除参数 dict 中多余的 ed_time/ed_power
        for suffix in range(n_sections + 1, 1000):
            tkey = f"ed_time_1_{suffix}"
            pkey = f"ed_power_1_{suffix}"
            if tkey in params:
                del params[tkey]
            if pkey in params:
                del params[pkey]
            if tkey not in params and pkey not in params:
                break  # 连续两个都不存在 → 结束

    # 光束配置
    if beams is not None:
        params["ed_numberOfBeams"] = len(beams)
        for b in beams:
            bid = b.beam_id
            params[f"ed_lensX_{bid}"] = b.lens_x
            params[f"ed_targetX_{bid}"] = b.target_x
            params[f"ed_pulseNumber_{bid}"] = b.pulse_number
            params[f"ed_wavelength_{bid}"] = b.wavelength
            params[f"ed_crossSectionFunctionType_{bid}"] = b.cross_section
            params[f"ed_numberOfRays_{bid}"] = b.nrays
            params[f"ed_gridType_{bid}"] = b.grid_type
            params[f"ed_gridnRadialTics_{bid}"] = b.grid_ntics

    # 应用用户覆盖
    if overrides:
        params.update(overrides)

    # 构建 .par 文件内容
    lines = [
        f'run_comment = "{sim_name} 1D Simulation - Auto-generated"',
        'log_file    = "lasslab.log"',
        f'basenm      = "lasslab_"',
        "",
    ]

    # 按类别分组
    sections = [
        ("I/O PARAMETERS", [
            "checkpointFileIntervalTime", "checkpointFileIntervalStep",
            "plotFileIntervalStep", "plotFileNumber", "restart",
            "checkpointFileNumber",
        ] + [k for k in params if k.startswith("plot_var_")]),
        ("RADIATION/OPACITY PARAMETERS", [
            k for k in params if k.startswith("rt_") or k.startswith("op_")
        ]),
        ("LASER PARAMETERS / Energy Deposition", [
            k for k in params if k.startswith("ed_")
        ]),
        ("CONDUCTION PARAMETERS", [
            k for k in params if k.startswith("diff_")
        ]),
        ("HEAT EXCHANGE PARAMETERS", ["useHeatexchange", "hx_dtFactor"]),
        ("EOS PARAMETERS", [
            k for k in params if k.startswith("eos_") or k in ("eosModeInit", "smallt", "smallx")
        ]),
        ("HYDRO PARAMETERS", [
            "useHydro", "order", "slopeLimiter", "LimitedSlopeBeta",
            "charLimiting", "use_avisc", "cvisc", "use_flattening",
            "use_steepening", "use_upwindTVD", "RiemannSolver",
            "entropy", "shockDetect", "use_hybridOrder",
            "xl_boundary_type", "xr_boundary_type",
        ]),
        ("INITIAL CONDITIONS", [
            k for k in params if k.startswith("sim_") or k.startswith("ms_")
        ]),
        ("TIME PARAMETERS", [
            "tstep_change_factor", "cfl", "dt_diff_factor", "rt_dtFactor",
            "hx_dtFactor", "tmax", "dtmin", "dtinit", "dtmax", "nend",
        ]),
        ("MESH PARAMETERS", [
            "geometry", "xmin", "xmax", "nblockx",
            "lrefine_max", "lrefine_min",
        ] + [k for k in params if k.startswith("refine_var_")]),
        ("ADDITIONAL PARAMETERS", [
            k for k in params if k not in set().union(*[set(s[1]) for s in [
                ("I/O PARAMETERS", []),
                ("RADIATION/OPACITY PARAMETERS", []),
                ("LASER PARAMETERS / Energy Deposition", []),
                ("CONDUCTION PARAMETERS", []),
                ("HEAT EXCHANGE PARAMETERS", []),
                ("EOS PARAMETERS", []),
                ("HYDRO PARAMETERS", []),
                ("INITIAL CONDITIONS", []),
                ("TIME PARAMETERS", []),
                ("MESH PARAMETERS", []),
            ]])
        ]),
    ]

    # 加入分辨率注释
    res_min = (xmax_cm - xmin_cm) * 1e4 / (nxb * nblockx * 2 ** (lrefine_max - 1))
    res_max = (xmax_cm - xmin_cm) * 1e4 / (nxb * nblockx * 2 ** (lrefine_min - 1))

    for i, (title, keys) in enumerate(sections):
        if title == "MESH PARAMETERS":
            lines.append(f"    # res_min={res_min:.4f}um (lref={lrefine_max})")
            lines.append(f"    # res_max={res_max:.4f}um (lref={lrefine_min})")

    # 输出参数
    written_keys = set()
    for title, keys in sections:
        actual_keys = [k for k in keys if k in params and k not in written_keys]
        if not actual_keys:
            continue
        lines.append("")
        lines.append("#" * 30)
        lines.append(f"#  {title}")
        lines.append("#" * 30)
        lines.append("")
        for key in actual_keys:
            val = params[key]
            lines.append(f"{key:30s} = {_fmt(val)}")
            written_keys.add(key)

    lines.append("")
    return "\n".join(lines)
