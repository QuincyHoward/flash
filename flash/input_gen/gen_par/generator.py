"""
.par 参数文件生成器 — ParGeneratorExtended (自包含)
══════════════════════════════════════════════════

完全自包含，不依赖外部模板文件。
默认值从 LaserSlab 模板提取后硬编码在 defaults.py 中。
"""

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
#  行尾注释字典: 参数名 → 说明 (generate 时自动对齐追加到行尾 "# ...")
#  模式化参数 (ed_time_1_N / op_{sp}FileName / sim_rho{Cap} 等) 由
#  _inline_comment() 的动态规则处理, 不在此表中。
# ============================================================================
PARAM_COMMENTS: Dict[str, str] = {
    # I/O
    "run_comment": "run description",
    "log_file": "runtime log file name",
    "basenm": "basename for all output files",
    "checkpointFileIntervalTime": "checkpoint interval [s]",
    "checkpointFileIntervalStep": "checkpoint interval [steps]",
    "checkpointFileNumber": "first checkpoint file number",
    "plotFileNumber": "first plotfile number",
    "plotFileIntervalStep": "plotfile interval [steps]",
    "plotFileIntervalTime": "plotfile interval [s]",
    "restart": "restart from checkpoint?",
    # Radiation / MGD
    "rt_useMGD": "enable multi-group diffusion",
    "rt_mgdNumGroups": "number of MDS radiation groups",
    "diff_useEleCond": "enable electron conduction",
    "diff_eleFlMode": "electron flux limiter mode",
    "diff_eleFlCoef": "electron flux limiter coefficient",
    "diff_thetaImplct": "implicitness factor (1 = fully implicit)",
    # Hydro / Heat exchange
    "useHeatexchange": "enable electron-ion heat exchange",
    "useHydro": "enable hydrodynamics",
    "useDiffuse": "enable diffusion units",
    "useConductivity": "enable conductivity unit",
    # PPMLR hydro solver (unsplit PPM + Riemann solvers)
    "order": "Interpolation order (first/second/third/fifth order)",
    "slopeLimiter": "Slope limiters (minmod, mc, vanLeer, hybrid, limited)",
    "LimitedSlopeBeta": "Slope parameter for the \"limited\" slope by Toro",
    "charLimiting": "Characteristic limiting vs. Primitive limiting",
    "use_avisc": "use artificial viscosity (originally for PPM)",
    "cvisc": "coefficient for artificial viscosity",
    "use_flattening": "use flattening (dissipative) (originally for PPM)",
    "use_steepening": "use contact steepening (originally for PPM)",
    "use_upwindTVD": "use upwind biased TVD slope for PPM (need nguard=6)",
    "RiemannSolver": "Riemann solver (Roe, HLL, HLLC, LLF, Marquina, hybrid)",
    "entropy": "Entropy fix for the Roe solver",
    "shockDetect": "shock detection sensor (used by use_hybridOrder)",
    "use_hybridOrder": "Enforce Riemann density jump",
    # Time
    "tmax": "simulation end time [s]",
    "dtinit": "initial time step [s]",
    "dtmin": "minimum time step [s]",
    "dtmax": "maximum time step [s]",
    "nend": "maximum number of steps",
    # Mesh
    "geometry": "domain geometry (cartesian/cylindrical/spherical)",
    "xmin": "domain left edge [cm]",
    "xmax": "domain right edge [cm]",
    "ymin": "domain bottom edge [cm]",
    "ymax": "domain top edge [cm]",
    "zmin": "domain back edge [cm]",
    "zmax": "domain front edge [cm]",
    "nblockx": "number of blocks along x",
    "nblocky": "number of blocks along y",
    "nblockz": "number of blocks along z",
    "refine_var_1": "AMR refinement criterion variable",
    "iProcs": "MPI process grid along x",
    "jProcs": "MPI process grid along y",
    "kProcs": "MPI process grid along z",
    # Laser (scalar keys; ed_time_1_N/ed_power_1_N 由动态规则处理)
    "ed_numberOfPulses": "number of laser pulses",
    "ed_numberOfBeams": "number of laser beams",
    "ed_lensX_1": "beam 1 lens position [cm]",
    "ed_targetX_1": "beam 1 target position [cm]",
    "ed_pulseNumber_1": "beam 1 pulse number",
    "ed_wavelength_1": "beam 1 wavelength [um]",
    "ed_crossSectionFunctionType_1": "beam 1 cross-section profile",
    "ed_gridType_1": "beam 1 ray grid type",
    "ed_gridnRadialTics_1": "beam 1 radial tics count",
    "ed_numberOfRays_1": "beam 1 number of rays",
    "ed_numberOfSections_1": "beam 1 pulse power sections",
    "ed_maxRayCount": "max rays per block for tracing",
    "ed_gradOrder": "laser deposition gradient order",
    "ed_useLaserIO": "enable laser ray IO",
    "ed_laserIOMaxNumberOfPositions": "laser IO max positions",
    "ed_laserIOMaxNumberOfRays": "laser IO max rays",
    "ed_maxPulseSections": "max pulse power sections",
    "ed_irradVarName": "laser energy deposition variable",
    # EOS / misc
    "eos_useLogTables": "EOS tables use log interpolation",
    "sim_initGeom": "initial geometry (slab/sphere)",
    "sim_smallX": "minimum species mass fraction",
    "sim_vacuumHeight": "vacuum region thickness [cm]",
}


@dataclass
class BeamConfig:
    """单个激光光束配置。

    用于描述 FLASH 仿真中的激光光束。
    对于 1D 仿真只需 beam_id, lens_x, target_x。
    对于 2D/3D 还需 lens_y/z 和椭圆参数。

    Attributes:
        beam_id: 光束编号 (1-based)
        lens_x, lens_y, lens_z: 透镜坐标 (cm)
        target_x, target_y, target_z: 目标坐标 (cm)
        pulse_number: 关联的脉冲编号
        wavelength: 波长 (um)
        cross_section_type: 截面类型 ("uniform", "gaussian2D")
        number_of_rays: 光线数
        grid_type: 网格类型 ("regular1D", "radial2D", "square2D")
        grid_radial_tics: 径向网格刻度数
        target_semi_axis_major: 目标椭圆长半轴 (2D/3D)
        target_semi_axis_minor: 目标椭圆短半轴 (2D/3D)
        gaussian_radius_major: 高斯光斑长半径
        gaussian_radius_minor: 高斯光斑短半径
        gaussian_exponent: 高斯指数
        lens_semi_axis_major: 透镜椭圆长半轴
        semi_axis_major_torsion_axis: 扭转轴
        semi_axis_major_torsion_angle: 扭转角度
    """
    beam_id: int = 1
    lens_x: float = -0.1
    lens_y: float = 0.0
    lens_z: float = 0.0
    target_x: float = 0.014
    target_y: float = 0.0
    target_z: float = 0.0
    pulse_number: int = 1
    wavelength: float = 1.053
    cross_section_type: str = "uniform"
    number_of_rays: int = 1
    grid_type: str = "regular1D"
    grid_radial_tics: int = 512
    target_semi_axis_major: Optional[float] = None
    target_semi_axis_minor: Optional[float] = None
    gaussian_radius_major: Optional[float] = None
    gaussian_radius_minor: Optional[float] = None
    gaussian_exponent: Optional[float] = None
    lens_semi_axis_major: Optional[float] = None
    semi_axis_major_torsion_axis: Optional[str] = None
    semi_axis_major_torsion_angle: Optional[float] = None
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .defaults import PARAMS_1D, PARAMS_2D, PARAMS_3D, DIMENSION_PARAMS


class ParGeneratorExtended:
    """.par 参数文件生成器 (自包含)。

    支持维度感知的默认参数加载。
    1D → PARAMS_1D (135 参数)
    2D → PARAMS_2D (163 参数)
    3D → PARAMS_3D (186 参数)
    """

    DIMENSION_TEMPLATES: Dict[int, str] = {
        1: "example1d.par",
        2: "example.par",
        3: "example3d.par",
    }

    def __init__(self, simulation_name: str = "LaserSlab", dimension: int = 1):
        """初始化 ParGeneratorExtended。

        Args:
            simulation_name: 仿真名称
            dimension: 仿真维度 (1/2/3)，用于加载对应默认参数
        """
        self.simulation_name = simulation_name
        self._params: Dict[str, Any] = {}
        self._pulses: List[Dict[str, Any]] = []
        self._beams: List[Dict[str, Any]] = []

        if dimension in DIMENSION_PARAMS:
            self._params = copy.deepcopy(DIMENSION_PARAMS[dimension])
        elif dimension in self.DIMENSION_TEMPLATES:
            raise ValueError(f"Unsupported dimension: {dimension}. Use 1, 2, or 3.")
        else:
            raise ValueError(f"Unsupported dimension: {dimension}. Use 1, 2, or 3.")

    def set_dimension(self, dim: int) -> "ParGeneratorExtended":
        """切换仿真维度，重新加载默认参数，保留已设置的参数。

        Args:
            dim: 仿真维度 (1/2/3)

        Returns:
            self (链式调用)
        """
        if dim in DIMENSION_PARAMS:
            old_params = self._params
            self._params = copy.deepcopy(DIMENSION_PARAMS[dim])
            # 保留用户之前设置过的非默认参数
            for k, v in old_params.items():
                if k not in DIMENSION_PARAMS[dim] or DIMENSION_PARAMS[dim][k] != v:
                    self._params[k] = v
        else:
            raise ValueError(f"Unsupported dimension: {dim}. Use 1, 2, or 3.")
        return self

    def set(self, key: str, value: Any) -> "ParGeneratorExtended":
        """设置单个参数。"""
        self._params[key] = value
        return self

    def get(self, key: str, default: Any = None) -> Any:
        """获取参数值。"""
        return self._params.get(key, default)

    def set_pulse(
        self,
        times: Union[List[float], np.ndarray],
        powers: Union[List[float], np.ndarray],
    ) -> "ParGeneratorExtended":
        """设置单脉冲。

        Args:
            times: 时间点数组 (s)
            powers: 功率点数组 (W)
        """
        pulse = {"pulse_id": 1, "times": np.asarray(times), "powers": np.asarray(powers)}
        self._pulses = [pulse]
        self._sync_pulses_to_params()
        return self

    def set_pulses(self, pulses: List[Dict[str, Any]]) -> "ParGeneratorExtended":
        """设置多脉冲。"""
        self._pulses = pulses
        self._sync_pulses_to_params()
        return self

    def add_pulse(self, pulse: Dict[str, Any]) -> "ParGeneratorExtended":
        """添加一个脉冲。"""
        self._pulses.append(pulse)
        self._sync_pulses_to_params()
        return self

    def set_beams(self, beams: List[Any]) -> "ParGeneratorExtended":
        """设置光束配置。

        Args:
            beams: BeamConfig 对象列表或字典列表
        """
        self._beams = beams
        self._sync_beams_to_params()
        return self

    def add_beam(self, beam: Any) -> "ParGeneratorExtended":
        """添加一个光束。"""
        self._beams.append(beam)
        self._sync_beams_to_params()
        return self

    def set_material(self, material: Any, target: bool = True) -> "ParGeneratorExtended":
        """设置材料参数。

        Args:
            material: Material 对象（具有 name, rho, A, Z, file 等属性）
            target: True=靶材, False=腔室气体
        """
        prefix = "targ" if target else "cham"
        self._params[f"sim_rho{prefix.capitalize()}"] = material.rho
        self._params[f"ms_{prefix}A"] = material.A
        self._params[f"ms_{prefix}Z"] = material.Z
        self._params[f"eos_{prefix}TableFile"] = material.file
        self._params[f"op_{prefix}FileName"] = material.file
        return self

    def set_domain(
        self,
        xmin: float = 0.0,
        xmax: float = 160e-4,
        nblockx: int = 4,
    ) -> "ParGeneratorExtended":
        """设置域和网格参数。"""
        self._params["xmin"] = xmin
        self._params["xmax"] = xmax
        self._params["nblockx"] = nblockx
        return self

    def set_time(
        self,
        tmax: float = 1e-9,
        dtinit: float = 1e-15,
        dtmin: float = 1e-16,
        dtmax: Optional[float] = None,
    ) -> "ParGeneratorExtended":
        """设置时间步长参数。"""
        self._params["tmax"] = tmax
        self._params["dtinit"] = dtinit
        self._params["dtmin"] = dtmin
        if dtmax is not None:
            self._params["dtmax"] = dtmax
        return self

    def _sync_pulses_to_params(self):
        """将脉冲数据同步到 _params。"""
        n_pulses = len(self._pulses)
        self._params["ed_numberOfPulses"] = n_pulses

        # 清除旧脉冲参数
        keys_to_remove = [k for k in self._params if k.startswith("ed_numberOfSections_")
                          or k.startswith("ed_time_") or k.startswith("ed_power_")]
        for k in keys_to_remove:
            self._params.pop(k, None)

        for pulse in self._pulses:
            pid = pulse.get("pulse_id", 1)
            times = np.asarray(pulse["times"])
            powers = np.asarray(pulse["powers"])
            n_sections = len(times)
            self._params[f"ed_numberOfSections_{pid}"] = n_sections
            for i, (t, p) in enumerate(zip(times, powers), 1):
                self._params[f"ed_time_{pid}_{i}"] = float(t)
                self._params[f"ed_power_{pid}_{i}"] = float(p)

    def _sync_beams_to_params(self):
        """将光束数据同步到 _params。"""
        n_beams = len(self._beams)
        self._params["ed_numberOfBeams"] = n_beams

        # 清除旧光束参数
        beam_prefixes = ["ed_lens", "ed_target", "ed_pulseNumber_", "ed_wavelength_",
                         "ed_crossSectionFunctionType_", "ed_numberOfRays_",
                         "ed_gridType_", "ed_gridnRadialTics_"]
        keys_to_remove = [k for k in self._params
                          if any(k.startswith(p) for p in beam_prefixes)]
        for k in keys_to_remove:
            self._params.pop(k, None)

        for i, beam in enumerate(self._beams):
            bid = getattr(beam, "beam_id", i + 1) if hasattr(beam, "beam_id") else i + 1
            if hasattr(beam, "lens_x"):
                self._params[f"ed_lensX_{bid}"] = beam.lens_x
                self._params[f"ed_targetX_{bid}"] = beam.target_x
                self._params[f"ed_pulseNumber_{bid}"] = getattr(beam, "pulse_number", 1)
                self._params[f"ed_wavelength_{bid}"] = getattr(beam, "wavelength", 1.053)
                self._params[f"ed_crossSectionFunctionType_{bid}"] = getattr(beam, "cross_section_type", "uniform")
                self._params[f"ed_numberOfRays_{bid}"] = getattr(beam, "number_of_rays", 1)
                self._params[f"ed_gridType_{bid}"] = getattr(beam, "grid_type", "regular1D")
                self._params[f"ed_gridnRadialTics_{bid}"] = getattr(beam, "grid_radial_tics", 512)
            elif isinstance(beam, dict):
                # dict-based beam
                self._params[f"ed_lensX_{bid}"] = beam.get("lens_x", -0.1)
                self._params[f"ed_targetX_{bid}"] = beam.get("target_x", 0.014)

    # ── 格式化输出 ─────────────────────────────────────

    def generate(self) -> str:
        """生成完整的 .par 文件内容字符串。

        Returns:
            .par 格式的字符串
        """
        lines = []
        dim = self._detect_dimension()

        lines.append(f'run_comment = "LaserSlab {dim}D Simulation - Generated by ParGeneratorExtended"')
        lines.append('log_file    = "lasslab.log"')
        lines.append(f'basenm      = "lasslab_"')
        lines.append("")

        # 按类别分段输出
        sections = self._build_sections()
        for sec_lines in sections:
            lines.extend(sec_lines)

        # 行尾注释: 对齐追加 "# 说明" (含 lrefine 分辨率注释)
        lines = self._apply_inline_comments(lines)

        return "\n".join(lines)

    def _detect_dimension(self) -> int:
        """尝试从参数推断维度。

        优先级: nblockz > nblocky > ed_numberOfRays_1 > 默认1D
        - 有 nblockz → 3D
        - 有 nblocky → 2D
        - ed_numberOfRays_1 > 1000 → 3D
        - 否则 → 1D
        """
        if "nblockz" in self._params:
            return 3
        if "nblocky" in self._params:
            return 2
        if "ed_numberOfRays_1" in self._params:
            nrays = self._params.get("ed_numberOfRays_1", 0)
            if nrays > 1000:
                return 3
        return 1

    def _build_sections(self) -> List[List[str]]:
        """按类别构建参数段。"""
        sections = []

        # I/O
        sections.append(self._section_block("I/O PARAMETERS", [
            "checkpointFileIntervalTime", "checkpointFileIntervalStep",
            "plotFileNumber", "plotFileIntervalStep",
        ] + [k for k in self._params if k.startswith("plot_var_")]
          + ["restart", "checkpointFileNumber"]))

        # Radiation/Opacity
        rad_keys = [k for k in self._params if k.startswith("rt_") or k.startswith("op_")]
        sections.append(self._section_block("RADIATION/OPACITY PARAMETERS", rad_keys))

        # Laser
        laser_keys = [k for k in self._params if k.startswith("ed_")]
        sections.append(self._section_block("LASER PARAMETERS", laser_keys))

        # Conduction
        cond_keys = [k for k in self._params if k.startswith("diff_") or k in ("useDiffuse", "useConductivity")]
        sections.append(self._section_block("CONDUCTION PARAMETERS", cond_keys))

        # Heat Exchange
        sections.append(self._section_block("HEAT EXCHANGE PARAMETERS", ["useHeatexchange"]))

        # EOS
        eos_keys = [k for k in self._params if k.startswith("eos") or k in ("smallt", "smallx")]
        sections.append(self._section_block("EOS PARAMETERS", eos_keys))

        # Hydro
        hydro_keys = [k for k in self._params if k.startswith("useHydro")
                      or k.startswith("order") or k.startswith("slope")
                      or k.startswith("Limited") or k.startswith("char")
                      or k.startswith("cvisc") or k.startswith("use_")
                      or k.startswith("Riemann") or k.startswith("entropy")
                      or k.startswith("shock") or k.startswith("xl_")
                      or k.startswith("xr_") or k.startswith("yl_")
                      or k.startswith("yr_") or k.startswith("zl_")
                      or k.startswith("zr_")]
        sections.append(self._section_block("HYDRO PARAMETERS", hydro_keys))

        # Initial Conditions
        init_keys = [k for k in self._params if k.startswith("sim_")
                     or k.startswith("ms_")]
        sections.append(self._section_block("INITIAL CONDITIONS", init_keys))

        # Time
        time_keys = [k for k in self._params if k.startswith("tstep")
                     or k.startswith("cfl") or k.startswith("dt_")
                     or k.startswith("rt_dt") or k.startswith("hx_")
                     or k in ("tmax", "dtmin", "dtinit", "dtmax", "nend")]
        sections.append(self._section_block("TIME PARAMETERS", time_keys))

        # Mesh
        mesh_keys = [k for k in self._params if k.startswith("geometry")
                     or k.startswith("xmin") or k.startswith("xmax")
                     or k.startswith("ymin") or k.startswith("ymax")
                     or k.startswith("zmin") or k.startswith("zmax")
                     or k.startswith("nblock") or k.startswith("lrefine")
                     or k.startswith("refine_var") or k.startswith("iGrid")
                     or k.startswith("jGrid") or k.startswith("kGrid")
                     or k.startswith("iProcs") or k.startswith("jProcs") or k.startswith("kProcs")]
        sections.append(self._section_block("MESH PARAMETERS", mesh_keys))

        # Remaining (unclassified)
        all_section_keys = set()
        for sec in sections:
            for line in sec:
                for k in self._params:
                    if k in line:
                        all_section_keys.add(k)
        remaining = [k for k in self._params if k not in all_section_keys]
        if remaining:
            sections.append(self._section_block("ADDITIONAL PARAMETERS", remaining))

        return sections

    def _section_block(self, title: str, keys: List[str]) -> List[str]:
        """生成一个参数段。"""
        lines = []
        if title:
            lines.append("")
            lines.append("##########################")
            lines.append("#                        #")
            lines.append(f"#     {title:26s}#")
            lines.append("#                        #")
            lines.append("##########################")
            lines.append("")

        for key in keys:
            if key in self._params:
                lines.append(self._format_param(key, self._params[key]))

        return lines

    def _inline_comment(self, key: str) -> Optional[str]:
        """返回参数 key 的行尾注释内容 (不含 '#'); 无注释返回 None。

        静态表 PARAM_COMMENTS 优先, 其余按模式规则动态生成
        (ed_time/ed_power 脉冲序列、rt_mgdBounds 能群边界、
        op_/eos_/ms_/sim_ 物种参数族)。
        """
        if key in PARAM_COMMENTS:
            return PARAM_COMMENTS[key]
        # lrefine: 理论网格分辨率 (简化格式: 公式 + 结果)
        if key in ("lrefine_max", "lrefine_min"):
            return self._lrefine_resolution_content(key)
        # 激光脉冲序列
        m = re.fullmatch(r"ed_time_1_(\d+)", key)
        if m:
            return f"laser pulse time, beam 1 section {m.group(1)} [s]"
        m = re.fullmatch(r"ed_power_1_(\d+)", key)
        if m:
            return f"laser pulse power, beam 1 section {m.group(1)} [W/cm2]"
        # MGD 能群边界
        m = re.fullmatch(r"rt_mgdBounds_(\d+)", key)
        if m:
            return f"MGD radiation group boundary {m.group(1)}"
        # plot_var 白名单条目 (易漏配, 特别提示)
        m = re.fullmatch(r"plot_var_(\d+)", key)
        if m:
            return f"plotfile output variable whitelist #{m.group(1)}"
        # 物种表绑定 / 材料参数族: op_{sp}{Sfx} / eos_{sp}{Sfx} / ms_{sp}{A|Z}
        m = re.fullmatch(r"op_([A-Za-z0-9]+)(Absorb|Emiss|Trans|FileType|FileName)", key)
        if m:
            sfx = {"Absorb": "absorption mode", "Emiss": "emission mode",
                   "Trans": "transmission mode", "FileType": "opacity file type",
                   "FileName": "opacity table file"}[m.group(2)]
            return f"{m.group(1)} opacity {sfx}"
        m = re.fullmatch(r"eos_([A-Za-z0-9]+)(EosType|SubType|TableFile)", key)
        if m:
            sfx = {"EosType": "EOS type", "SubType": "EOS subtype",
                   "TableFile": "EOS table file"}[m.group(2)]
            return f"{m.group(1)} {sfx}"
        m = re.fullmatch(r"ms_([A-Za-z0-9]+)(A|Z)", key)
        if m:
            return f"{m.group(2)}-related: {'atomic weight' if m.group(2) == 'A' else 'atomic number'} ({m.group(1)})"
        # sim_{rho|tele|tion|trad|zmin|eos}{Cap}
        m = re.fullmatch(r"sim_(rho|tele|tion|trad|zmin|eos)([A-Za-z0-9]+)", key)
        if m:
            what = {"rho": "initial density [g/cm3]",
                    "tele": "initial electron temperature [K]",
                    "tion": "initial ion temperature [K]",
                    "trad": "initial radiation temperature [K]",
                    "zmin": "minimum zbar allowed",
                    "eos": "EOS type"}[m.group(1)]
            return f"{m.group(2).lower()} {what}"
        # 场景自定义几何参数 (sim_*Radius / sim_*Height)
        m = re.fullmatch(r"sim_([A-Za-z0-9]+)(Radius|Height)", key)
        if m:
            return f"layer geometry: {m.group(1)} {m.group(2).lower()} [cm]"
        return None

    def _apply_inline_comments(self, lines: List[str]) -> List[str]:
        """为可注释参数行追加行尾注释, '#' 按全局对齐列统一。"""
        commentable: List[tuple] = []   # (行索引, 注释内容)
        align_col = 0
        for i, line in enumerate(lines):
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*", line)
            if not m:
                continue
            c = self._inline_comment(m.group(1))
            if c:
                commentable.append((i, c))
                align_col = max(align_col, len(line))
        align_col += 2
        for i, c in commentable:
            lines[i] = lines[i].ljust(align_col) + "# " + c
        return lines

    def _lrefine_resolution_content(self, key: str) -> Optional[str]:
        """lrefine_max/min 对应的理论网格分辨率注释内容 (简化格式)。

        公式: res = dir_delta/(nxb*nblock*2^(lrefine-1))
          dir_delta = xmax - xmin (沿 x), nblock = nblockx,
          nxb = 每 block 网格数 (缺省 16, 与 setup -nxb 一致)。
        """
        p = self._params
        try:
            lrefine = int(p.get(key))
            nblockx = int(p.get("nblockx"))
            xmin = float(p.get("xmin"))
            xmax = float(p.get("xmax"))
        except (TypeError, ValueError):
            return None
        nxb = int(p.get("nxb", 16))
        dir_delta = xmax - xmin
        if dir_delta <= 0 or nblockx <= 0 or nxb <= 0 or lrefine < 1:
            return None
        res = dir_delta / (nxb * nblockx * 2 ** (lrefine - 1))
        return f"res = dir_delta/(nxb*nblock*2^({key}-1)) = {res:.6e} cm"

    def _format_param(self, key: str, value: Any) -> str:
        """格式化单个参数为 .par 格式。"""
        if isinstance(value, bool):
            return f"{key} = {'.true.' if value else '.false.'}"
        elif isinstance(value, str):
            return f'{key} = "{value}"'
        elif isinstance(value, float):
            abs_val = abs(value)
            if abs_val == 0.0:
                return f"{key} = 0.0"
            elif abs_val < 0.01 or abs_val >= 10000:
                return f"{key} = {value:.15e}"
            else:
                return f"{key} = {value:.15g}"
        else:
            return f"{key} = {value}"

    def save(self, output_path: Union[str, Path]) -> Path:
        """生成并保存 .par 文件。

        Args:
            output_path: 输出文件路径

        Returns:
            保存的文件路径
        """
        content = self.generate()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8", newline="\n")
        return out

    def preview(self) -> str:
        """打印预览。"""
        content = self.generate()
        print(content)
        return content
