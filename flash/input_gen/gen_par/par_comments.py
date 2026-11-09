"""par_comments — FLASH .par 行尾释义纯函数模块 (方案 A 抽取, 2026-11-07)

将 ParGeneratorExtended 的行尾注释能力抽为纯函数, 供两类调用方共用:
  1. gen_par/generator.py       — 标准生成器 (方法委托到本模块)
  2. 各场景自包含 build_par()   — 在 return 前调用 apply_inline_comments()

纯 stdlib (re/typing), 无 numpy 依赖, 满足场景"无 numpy 系统 python 亦可
生成 par"的自包含约束。

组成:
  PARAM_COMMENTS                   — 静态参数释义字典 (参数名 → 说明)
  lrefine_resolution_content(...)  — lrefine_max/min 理论分辨率注释
  inline_comment(key, params)      — 单键释义 (静态表优先, 其余按模式规则)
  apply_inline_comments(lines, params) — 全局对齐 '#' 列后逐行追加注释
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ============================================================================
#  行尾注释字典: 参数名 → 说明 (generate 时自动对齐追加到行尾 "# ...")
#  模式化参数 (ed_time_1_N / op_{sp}FileName / sim_rho{Cap} 等) 由
#  inline_comment() 的动态规则处理, 不在此表中。
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
    # ── 2026-11-07 补全 (SandwichTxN par 未注释键盘点) ──
    "cfl": "CFL number",
    "dt_diff_factor": "diffusion timestep limiter factor",
    "eosModeInit": "initial EOS mode (e.g. dens_temp_gather)",
    "hx_dtFactor": "heat-exchange timestep limiter factor",
    "rt_dtFactor": "radiation timestep limiter factor",
    "rt_mgdFlCoef": "MGD flux limiter coefficient",
    "rt_mgdFlMode": "MGD flux limiter mode",
    "rt_mgdXlBoundaryType": "MGD left boundary type",
    "rt_mgdXrBoundaryType": "MGD right boundary type",
    "smallt": "minimum temperature floor",
    "smallx": "minimum mass fraction floor",
    "tstep_change_factor": "timestep growth factor per step",
    "useEnergyDeposition": "enable laser energy deposition unit",
    "useOpacity": "enable opacity unit",
    "xl_boundary_type": "left domain boundary condition",
    "xr_boundary_type": "right domain boundary condition",
    "diff_eleXlBoundaryType": "electron conduction left BC",
    "diff_eleXrBoundaryType": "electron conduction right BC",
}


def lrefine_resolution_content(key: str, params: Dict[str, Any]) -> Optional[str]:
    """lrefine_max/min 对应的理论网格分辨率注释内容 (简化格式)。

    公式: res = dir_delta/(nxb*nblock*2^(lrefine-1))
      dir_delta = xmax - xmin (沿 x), nblock = nblockx,
      nxb = 每 block 网格数 (缺省 16, 与 setup -nxb 一致)。
    """
    try:
        lrefine = int(params.get(key))
        nblockx = int(params.get("nblockx"))
        xmin = float(params.get("xmin"))
        xmax = float(params.get("xmax"))
    except (TypeError, ValueError):
        return None
    nxb = int(params.get("nxb", 16))
    dir_delta = xmax - xmin
    if dir_delta <= 0 or nblockx <= 0 or nxb <= 0 or lrefine < 1:
        return None
    res = dir_delta / (nxb * nblockx * 2 ** (lrefine - 1))
    return f"res = dir_delta/(nxb*nblock*2^({key}-1)) = {res:.6e} cm"


def inline_comment(key: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """返回参数 key 的行尾注释内容 (不含 '#'); 无注释返回 None。

    静态表 PARAM_COMMENTS 优先, 其余按模式规则动态生成
    (ed_time/ed_power 脉冲序列、rt_mgdBounds 能群边界、
    op_/eos_/ms_/sim_ 物种参数族、lrefine 分辨率)。
    params 仅 lrefine 分辨率注释需要 (xmin/xmax/nblockx/nxb)。
    """
    if key in PARAM_COMMENTS:
        return PARAM_COMMENTS[key]
    # lrefine: 理论网格分辨率 (简化格式: 公式 + 结果)
    if key in ("lrefine_max", "lrefine_min"):
        if params is None:
            return None
        return lrefine_resolution_content(key, params)
    # 激光脉冲序列
    m = re.fullmatch(r"ed_time_1_(\d+)", key)
    if m:
        return f"laser pulse time, beam 1 section {m.group(1)} [s]"
    m = re.fullmatch(r"ed_power_1_(\d+)", key)
    if m:
        return f"laser pulse power, beam 1 section {m.group(1)} [W/cm2]"
    # 多光束泛化 (beam N, N >= 2; beam 1 由静态表与上面两条覆盖)
    m = re.fullmatch(
        r"ed_(lensX|targetX|pulseNumber|wavelength|crossSectionFunctionType"
        r"|gridType|gridnRadialTics|numberOfRays|numberOfSections)_(\d+)", key)
    if m:
        what = {"lensX": "lens position [cm]",
                "targetX": "target position [cm]",
                "pulseNumber": "pulse number",
                "wavelength": "wavelength [um]",
                "crossSectionFunctionType": "cross-section profile",
                "gridType": "ray grid type",
                "gridnRadialTics": "radial tics count",
                "numberOfRays": "number of rays",
                "numberOfSections": "pulse power sections"}[m.group(1)]
        return f"beam {m.group(2)} {what}"
    # AMR 细化判据变量 (泛化到任意序号)
    m = re.fullmatch(r"refine_var_(\d+)", key)
    if m:
        return f"AMR refinement criterion variable #{m.group(1)}"
    # MGD 能群边界
    m = re.fullmatch(r"rt_mgdBounds_(\d+)", key)
    if m:
        return f"MGD radiation group boundary {m.group(1)}"
    # plot_var 白名单条目 (易漏配, 特别提示)
    m = re.fullmatch(r"plot_var_(\d+)", key)
    if m:
        return f"plotfile output variable whitelist #{m.group(1)}"
    # 物种表绑定 / 材料参数族: op_{sp}{Sfx} / eos_{sp}{Sfx} / ms_{sp}{A|Z|ZMin}
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
    m = re.fullmatch(r"ms_([A-Za-z0-9]+?)(A|Z|ZMin)", key)
    if m:
        what = {"A": "atomic weight", "Z": "atomic number",
                "ZMin": "minimum mean ionization"}[m.group(2)]
        return f"{m.group(1)} {what}"
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


def apply_inline_comments(lines: List[str],
                          params: Optional[Dict[str, Any]] = None) -> List[str]:
    """为可注释参数行追加行尾注释, '#' 按全局对齐列统一。

    与 ParGeneratorExtended._apply_inline_comments 行为一致;
    抽为纯函数以便各场景自包含 build_par 直接调用。
    """
    commentable: List[tuple] = []   # (行索引, 注释内容)
    align_col = 0
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*", line)
        if not m:
            continue
        c = inline_comment(m.group(1), params)
        if c:
            commentable.append((i, c))
            align_col = max(align_col, len(line))
    align_col += 2
    for i, c in commentable:
        lines[i] = lines[i].ljust(align_col) + "# " + c
    return lines
