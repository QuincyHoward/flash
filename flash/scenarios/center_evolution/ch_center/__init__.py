"""ch_center — CH 靶中心演化场景

CH 泡沫靶 + 两侧 He + 两束 351nm 激光相向 (5e14 W/cm²)。
使用 flash.scenarios.interpolator 的共享时空插值, 内联 par_builder。
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: find flash project root by searching upward for marker
# (源码工作区模式: 注入仓库根到 sys.path; wheel 安装模式: flash 包已在
#  site-packages, 找不到 pyproject.toml 时静默跳过, 不抛错)
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None  # 安装模式: 无仓库根, 跳过 sys.path 注入
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# 本地场景目录
_HERE = Path(__file__).parent.resolve()

from flash.scenarios.base import SimulationScenario
from flash.scenarios.interpolator import (
    build_variable_grid as _build_variable_grid,
    interpolate_flash_to_grid as _interpolate,
)
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
    _add("op_chamFileName", "Z02_1.00-20260708_0851.cn4")
    _add("op_chamFileType", "ionmix4")
    _add("op_chamTrans", "op_tabro")
    _add("op_targAbsorb", "op_tabpa")
    _add("op_targEmiss", "op_tabpe")
    _add("op_targFileName", "Z06_0.50-Z01_0.50-20260708_0850.cn4")
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
    _add("eos_chamTableFile", "Z02_1.00-20260708_0851.cn4")
    _add("eos_targEosType", "eos_tab")
    _add("eos_targSubType", "ionmix4")
    _add("eos_targTableFile", "Z06_0.50-Z01_0.50-20260708_0850.cn4")
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
        xmin=xmin,
        xmax=xmax,
        nx=params.get("output_nx", 2000),
    )


def _interpolate_fn(flash_files, t_grid, x_grid, var_names):
    return _interpolate(
        flash_files=[str(f) for f in flash_files],
        t_grid=t_grid, x_grid=x_grid,
        var_names=var_names,
    )


# ── sim_input 完整性检查与编写指引 ──────────────────────
#
# 按 FLASH License Agreement §3, FLASH 分发的源文件 (F90/Config/Makefile)
# 不随 flash-sim 发布包分发, 用户需自行获取 FLASH 后按下列指引编写/对照。
# 自研 IONMIX 生成的 EOS/不透明度表 (Z*.cn4) 随包分发, 无版权障碍。

# 每个必需文件: (文件名, 是否随包分发, 用途说明)
_REQUIRED_SIM_INPUT = {
    "Config": (
        False,
        "FLASH 编译配置: REQUIRES/REQUESTS 声明所需物理模块 (Hydro/Diffuse/"
        "Heatexchange/Conductivity), PARAMETER 声明所有 sim_* 运行时参数, "
        "DATAFILES 声明随包分发的自研 EOS 表 (*.cn4)",
    ),
    "Makefile": (
        False,
        "FLASH 编译清单: 列出需要编译的额外源文件 (如 `Simulation += Simulation_data.o`)",
    ),
    "Simulation_data.F90": (
        False,
        "模块 Simulation_data: 声明所有 sim_* 运行时参数变量 (靶/腔体材料密度、"
        "温度、几何参数) 的 Fortran `save` 变量",
    ),
    "Simulation_init.F90": (
        False,
        "子程序 Simulation_init(): 通过 RuntimeParameters_get 从 .par 读取所有 "
        "sim_* 参数并存入 Simulation_data 模块变量",
    ),
    "Simulation_initBlock.F90": (
        False,
        "子程序 Simulation_initBlock(blockId): 按空间位置 (xcent) 为每个网格单元"
        "设置初始密度/温度/物种丰度 (靶区 vs 腔体区), 写入 Grid",
    ),
}


def _print_file_pseudocode(fname: str, reason: str) -> None:
    """缺失文件时打印主要内容总结与编写伪代码。"""
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"  [缺失] {fname} — {reason}")
    print(f"{bar}")
    if fname == "Config":
        print("""
  ## Config 编写伪代码 (FLASH 编译配置)
  # REQUIRES 声明基础模块:
  REQUIRES Driver
  REQUIRES physics/Hydro
  # 3T (双温+辐射) 需要额外模块:
  USESETUPVARS ThreeT
  IF ThreeT
     REQUESTS physics/Diffuse/DiffuseMain/Unsplit
     REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer
     REQUESTS physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ
  ENDIF
  # 声明运行时参数 (与 Simulation_data.F90 变量一一对应):
  PARAMETER sim_rhoTarg  REAL 2.7          ! 靶密度 (g/cm³)
  PARAMETER sim_rhoCham  REAL 2.655e-07    ! 腔体密度 (g/cm³)
  PARAMETER sim_teleTarg REAL 290.11375    ! 靶电子温度 (K)
  ...  (其余 sim_* 参数类推)
  # 声明 EOS/不透明度表 (自研表随包分发):
  DATAFILES Z02_1.00-20260708_0851.cn4
  DATAFILES Z06_0.50-Z01_0.50-20260708_0850.cn4
""")
    elif fname == "Makefile":
        print("""
  ## Makefile 编写伪代码
  # 将自定义源文件追加到编译清单 (FLASH 自动编译 SimulationMain 下的标准文件):
  Simulation += Simulation_data.o
  # 注: Simulation_init.F90 / Simulation_initBlock.F90 由 FLASH 默认规则编译,
  #     无需在此列出; 仅额外自定义源文件需要。
""")
    elif fname == "Simulation_data.F90":
        print("""
  ## Simulation_data.F90 编写伪代码 (模块: 声明 sim_* 变量)
  module Simulation_data
    implicit none
  #include "constants.h"
    ! 几何参数
    real, save :: sim_targetRadius, sim_targetHeight, sim_vacuumHeight
    ! 靶材料 (targ)
    real,    save :: sim_rhoTarg, sim_teleTarg, sim_tionTarg, sim_tradTarg
    real,    save :: sim_zminTarg
    integer, save :: sim_eosTarg
    ! 腔体材料 (cham)
    real,    save :: sim_rhoCham, sim_teleCham, sim_tionCham, sim_tradCham
    integer, save :: sim_eosCham
    ! 其他
    logical, save :: sim_killdivb = .FALSE.
    real, save :: sim_smallX
    character(len=MAX_STRING_LENGTH), save :: sim_initGeom
  end module Simulation_data
  # 注: 变量名必须与 Config 中 PARAMETER 及 .par 中键名完全一致。
""")
    elif fname == "Simulation_init.F90":
        print("""
  ## Simulation_init.F90 编写伪代码 (子程序: 读取 .par 参数)
  subroutine Simulation_init()
    use Simulation_data
    use RuntimeParameters_interface, ONLY : RuntimeParameters_get
    implicit none
  #include "constants.h"
  #include "Flash.h"
    ! 逐参数读取 (与 Simulation_data 变量一一对应):
    call RuntimeParameters_get('sim_targetRadius', sim_targetRadius)
    call RuntimeParameters_get('sim_rhoTarg',      sim_rhoTarg)
    call RuntimeParameters_get('sim_teleTarg',     sim_teleTarg)
    call RuntimeParameters_get('sim_rhoCham',      sim_rhoCham)
    call RuntimeParameters_get('sim_teleCham',     sim_teleCham)
    ...  (其余 sim_* 参数类推)
  end subroutine Simulation_init
  # 注: 所有 RuntimeParameters_get 的键必须与 .par 中键名一致。
""")
    elif fname == "Simulation_initBlock.F90":
        print("""
  ## Simulation_initBlock.F90 编写伪代码 (子程序: 初始化网格单元状态)
  subroutine Simulation_initBlock(blockId)
    use Simulation_data
    use Grid_interface, ONLY : Grid_getBlkIndexLimits, Grid_getCellCoords, &
         Grid_putPointData
    use RadTrans_interface, ONLY : RadTrans_mgdEFromT
    implicit none
  #include "constants.h"
  #include "Flash.h"
    integer, intent(in) :: blockId
    integer :: i, j, k, n
    integer :: blkLimits(2, MDIM), blkLimitsGC(2, MDIM)
    integer :: axis(MDIM)
    real, allocatable :: xcent(:), ycent(:), zcent(:)
    real :: rho, tele, trad, tion, tradActual
    integer :: species
    ! 物种编号 (由 setup 的 species=cham,targ 定义):
    integer :: CHAM_SPEC = 1, TARG_SPEC = 2

    call Grid_getBlkIndexLimits(blockId, blkLimits, blkLimitsGC)
    allocate(xcent(blkLimitsGC(HIGH, IAXIS)))
    call Grid_getCellCoords(IAXIS, blockId, CENTER, .true., xcent, blkLimitsGC(HIGH, IAXIS))

    do k = blkLimits(LOW,KAXIS), blkLimits(HIGH,KAXIS)
      do j = blkLimits(LOW,JAXIS), blkLimits(HIGH,JAXIS)
        do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)
          axis(IAXIS) = i; axis(JAXIS) = j; axis(KAXIS) = k
          ! 按 x 位置判定靶区/腔体区 (阈值 = 靶半径, 与 .par sim_targetRadius 对应):
          species = CHAM_SPEC
          if (abs(xcent(i)) <= sim_targetRadius) species = TARG_SPEC
          if (species == TARG_SPEC) then
             rho = sim_rhoTarg; tele = sim_teleTarg
             tion = sim_tionTarg; trad = sim_tradTarg
          else
             rho = sim_rhoCham; tele = sim_teleCham
             tion = sim_tionCham; trad = sim_tradCham
          end if
          call Grid_putPointData(blockId, CENTER, DENS_VAR, EXTERIOR, axis, rho)
          call Grid_putPointData(blockId, CENTER, TEMP_VAR, EXTERIOR, axis, tele)
  #ifdef FLASH_3T
          call Grid_putPointData(blockId, CENTER, TION_VAR, EXTERIOR, axis, tion)
          call Grid_putPointData(blockId, CENTER, TELE_VAR, EXTERIOR, axis, tele)
          call RadTrans_mgdEFromT(blockId, axis, trad, tradActual)
          call Grid_putPointData(blockId, CENTER, TRAD_VAR, EXTERIOR, axis, tradActual)
  #endif
          ! 物种丰度 (唯一占优物种=1, 其余=sim_smallX):
          if (NSPECIES > 0) then
            do n = SPECIES_BEGIN, SPECIES_END
              if (n == species) then
                call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, 1.0e0-(NSPECIES-1)*sim_smallX)
              else
                call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, sim_smallX)
              end if
            end do
          end if
        end do
      end do
    end do
    deallocate(xcent)
  end subroutine Simulation_initBlock
  # 注: 靶半径阈值 (sim_targetRadius) 需与 .par 中设置一致, 才能正确定位靶区。
""")
    else:
        print(f"  [未知文件] {fname}: 请参考 FLASH 文档 https://flash.rochester.edu\n")


def _check_sim_input() -> None:
    """检查场景必需 FLASH 源文件, 缺失时给出提示。

    源码仓库模式 (本目录含 gen_flash_inputs.py 生成器): 缺失文件将由
    gen_flash_inputs.py / laserslab1d_local_custom.py 步骤 1 自动生成,
    此处仅打印一行提示, 不打印编写伪代码 (避免误导)。
    wheel 安装模式 (无生成器): 打印编写指引与伪代码。
    """
    missing = []
    for fname, (ships, _desc) in _REQUIRED_SIM_INPUT.items():
        if not (_HERE / "flash_input" / fname).exists():
            missing.append((fname, ships))
    if not missing:
        return
    auto_gen = (_HERE / "gen_flash_inputs.py").exists()
    print("\n" + "=" * 72)
    print("  ⚠️  ch_center 场景缺少以下 FLASH 源文件 (不随发布包分发):")
    print("  " + "=" * 68)
    for fname, ships in missing:
        print(f"    - {fname}" + ("  (自研表随包分发, 无需编写)" if ships else ""))
    if auto_gen:
        print("\n  说明: 本仓库为源码模式, 上述文件由自动生成器补齐 —")
        print("    运行 laserslab1d_local_custom.py (步骤 1 自动检查生成) 或")
        print("    python flash/scenarios/center_evolution/ch_center/gen_flash_inputs.py")
        print("    生成后本提示自动消失, 无需手动编写。")
    else:
        print("\n  说明: 按 FLASH License Agreement §3, FLASH 分发的源文件不可再分发,")
        print("  请从 https://flash.rochester.edu 获取 FLASH 后, 参照 FLASH 自带")
        print("  SimulationMain/LaserSlab 示例文件修改, 或按下方伪代码自行编写。")
        print("  完整参考实现见源码仓库 scenarios/center_evolution/ch_center/flash_input/。")
        for fname, _ships in missing:
            if not _ships:
                _print_file_pseudocode(fname, _REQUIRED_SIM_INPUT[fname][1])


# 场景实例化后立即执行完整性检查 (导入时打印一次)
_check_sim_input()


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
