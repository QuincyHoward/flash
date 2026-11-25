"""sandwich_txn_cylindrical2d_one — CH/Si/CH 二维 R-Z 每侧单束（共 2 束）场景。

本文件完全自包含，不 import 任何兄弟场景；物理常量复制自
../SandwichTxN/sandwich_txn.py（2026-11-22 核对），仅作只读参考。

几何：FLASH 2D R-Z，网格 x = r∈[0,900] um，y = z∈[-450,450] um；靶在 z=0。
靶：Si 0.92 um / CH 致密 1 um×2 / CH 泡沫 50 um×2，半径 650 um。
激光：上下各 1 束、共 2 束，每束 1600 J，沿对称轴正入射；45° 等腰梯形收敛：
lens 半径 1400 um → 靶面半径 400 um（lens 距靶 1000 um，侧壁恰 45°）。
3Din2D 开启，ed_power 为总瓦特，峰值 1.6e12 W。
脉冲：0 / 0.3ns / 1.0ns / 1.3ns 四点梯形，半宽 1 ns，边沿各 0.3 ns。
AMR：r<=425 um 且 |z|<=4.5 um 最高细化；CH 降级；He 最低。

CLI：gen / run [--tmax] / validate
短验证：SANDWICH_TXN_CYL2D_ONE_TMAX=1e-11 或 run --tmax 1e-11。
"""

from __future__ import annotations

import os
import shutil
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_HERE = Path(__file__).parent.resolve()
_REPO = _HERE
for _ in range(12):
    if (_REPO / "pyproject.toml").is_file():
        break
    _REPO = _REPO.parent
else:
    raise RuntimeError("sandwich_txn_cartesian2d: 无法定位仓库根 (需 pyproject.toml)")
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from flash.scenarios.core.engine.base import SimulationScenario
from flash.scenarios.core.engine.simulator import FlashSimulatorEngine

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 物理常量（复制自 1D SandwichTxN，2026-11-22） ─────────────────
XMIN_CM, XMAX_CM = 0.0, 0.09      # r 方向（R-Z 网格 x = r）
YMIN_CM, YMAX_CM = -0.045, 0.045  # z 方向（R-Z 网格 y = z）

DEFAULT_TARG_HEIGHT = 0.46e-4       # Si 半厚 (cm)
DEFAULT_POLY_HEIGHT = 1.46e-4       # 致密 CH 外边界半厚 (cm)
DEFAULT_FOAM_HEIGHT = 51.46e-4      # CH 泡沫外边界半厚 (cm)
DEFAULT_RHO_TARG = 2.3
DEFAULT_RHO_POLY = 1.0
DEFAULT_RHO_FOAM = 0.294
DEFAULT_RHO_CHAM = 1e-6
DEFAULT_TEMP = 290.11375

TARGET_RADIUS_CM = 0.065            # 靶半径 650 um (直径 1300 um)
RADIAL_CORE_CM = 0.0425             # 横向细化核心半宽 425 um (直径 850 um)
AXIAL_CORE_CM = 4.5e-4              # 纵向细化核心半厚 4.5 um (约 9 um 宽)

EOS_TARG_FILE = "Z14_1.00-20260708_0850.cn4"
EOS_POLY_FILE = "Z06_0.50-Z01_0.50-20260708_0850.cn4"
EOS_CHAM_FILE = "Z02_1.00-20260708_0851.cn4"
CN4_TABLE_SOURCES = {
    n: f"Gen_eos_op_data/{n[:-4]}/{n}"
    for n in (EOS_TARG_FILE, EOS_POLY_FILE, EOS_CHAM_FILE)
}

MS_TARG_A, MS_TARG_Z = 28.0855, 14
MS_POLY_A, MS_POLY_Z = 6.5, 3.5
MS_CHAM_A, MS_CHAM_Z = 4.002602, 2

NXB = 16
NBX, NBY = 12, 8
LREF_MAX, LREF_MIN = 8, 1
MAXBLOCKS = 8192

PEAK_POWER = 1.6e12                  # W（3Din2D 总功率），单束 1600 J / 1 ns
WAVELENGTH = 0.351                   # um
TARGET_SEMI_CM = 0.04                # 靶面半径 400 um
LENS_SEMI_CM = 0.14                  # lens 半径 1400 um（45° 收敛侧壁）

DEFAULT_TMAX = 1.6e-9
ENV_TMAX_NAME = "SANDWICH_TXN_CYL2D_ONE_TMAX"
_TMAX_ENV = os.environ.get(ENV_TMAX_NAME, "").strip()

# 3D 光束：沿 z 轴（对称轴）正入射，lens 在 z=±0.1，target 在原点。
BEAMS = [
    {"id": 1, "lx": 0.0, "ly": 0.0, "lz": 0.1, "tx": 0.0, "ty": 0.0, "tz": 0.0},
    {"id": 2, "lx": 0.0, "ly": 0.0, "lz": -0.1, "tx": 0.0, "ty": 0.0, "tz": 0.0},
]

SCENE_SPEC = {
    "geometry": "cylindrical",
    "radial_core_cm": RADIAL_CORE_CM,
    "target_radius_cm": TARGET_RADIUS_CM,
    "axial_core_cm": AXIAL_CORE_CM,
    "beam_count": 2,
    "beam_energy_j": 1600.0,
    "power_unit": "W",
    "peak_power": PEAK_POWER,
    "incidence_deg": 0.0,
}


def trapezoid_pulse(i0: float = PEAK_POWER) -> List[Tuple[float, float]]:
    """严格四点梯形：(0,0), (0.3ns,I0), (1.0ns,I0), (1.3ns,0)。"""
    return [(0.0, 0.0), (0.3e-9, float(i0)), (1.0e-9, float(i0)), (1.3e-9, 0.0)]


DEFAULT_LASER_PULSE = trapezoid_pulse()

# ── FLASH 源输入（以 1D 已验证模板为基准做 2D 定点改写） ────────────
SIM_INPUT_TEXT = {
    "Config": r'''
# 2D R-Z CH/Si/CH, copied from 1D SandwichTxN template (2026-11-22)
REQUIRES Driver
REQUIRES physics/Hydro
USESETUPVARS ThreeT
IF ThreeT
   REQUESTS physics/Diffuse/DiffuseMain/Unsplit
   REQUESTS physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer
   REQUESTS physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ
ENDIF
DATAFILES Z14_1.00-20260708_0850.cn4
DATAFILES Z02_1.00-20260708_0851.cn4
DATAFILES Z06_0.50-Z01_0.50-20260708_0850.cn4

D sim_initGeom Use a spherical target if sphere, default to slab
PARAMETER sim_initGeom STRING "slab" ["slab","sphere"]
D sim_targetRadius Target transverse half-width
PARAMETER sim_targetRadius REAL 0.065
D sim_radialCore Transverse refinement core half-width
PARAMETER sim_radialCore REAL 0.0425
D sim_axialCore Axial refinement core half-thickness
PARAMETER sim_axialCore REAL 4.5e-4
D sim_targHeight Si half-thickness
PARAMETER sim_targHeight REAL 0.46e-4
D sim_polyHeight Dense CH outer half-thickness
PARAMETER sim_polyHeight REAL 1.46e-4
D sim_foamHeight CH foam outer half-thickness
PARAMETER sim_foamHeight REAL 51.46e-4
D sim_rhoTarg Initial Si density
PARAMETER sim_rhoTarg REAL 2.3
D sim_rhoPoly Initial dense CH density
PARAMETER sim_rhoPoly REAL 1.0
D sim_rhoFoam Initial CH foam density
PARAMETER sim_rhoFoam REAL 0.294
D sim_rhoCham Initial He density
PARAMETER sim_rhoCham REAL 1e-6
D sim_teleTarg initial temperature
PARAMETER sim_teleTarg REAL 290.11375
D sim_tionTarg initial temperature
PARAMETER sim_tionTarg REAL 290.11375
D sim_tradTarg initial temperature
PARAMETER sim_tradTarg REAL 290.11375
D sim_telePoly initial temperature
PARAMETER sim_telePoly REAL 290.11375
D sim_tionPoly initial temperature
PARAMETER sim_tionPoly REAL 290.11375
D sim_tradPoly initial temperature
PARAMETER sim_tradPoly REAL 290.11375
D sim_teleCham initial temperature
PARAMETER sim_teleCham REAL 290.11375
D sim_tionCham initial temperature
PARAMETER sim_tionCham REAL 290.11375
D sim_tradCham initial temperature
PARAMETER sim_tradCham REAL 290.11375
D sim_zminTarg target minimum zbar allowed
PARAMETER sim_zminTarg REAL 0.0
D sim_eosTarg target EOS type
PARAMETER sim_eosTarg STRING "eos_tab" ["eos_tab","eos_gam"]
D sim_eosCham chamber EOS type
PARAMETER sim_eosCham STRING "eos_gam" ["eos_tab","eos_gam"]
VARIABLE lase TYPE: PER_VOLUME
D ms_polyA CH atomic mass
PARAMETER ms_polyA REAL 6.5
D ms_polyZ CH atomic number
PARAMETER ms_polyZ REAL 3.5
D eos_polyEosType Poly EOS type
PARAMETER eos_polyEosType STRING "eos_tab" ["eos_tab","eos_gam"]
D eos_polySubType Poly EOS subtype
PARAMETER eos_polySubType STRING "ionmix4" ["ionmix4"]
D eos_polyTableFile Poly EOS table
PARAMETER eos_polyTableFile STRING "polystyrene-imx-008.cn4"
D op_polyAbsorb Poly absorption opacity
PARAMETER op_polyAbsorb STRING "op_tabpa"
D op_polyEmiss Poly emission opacity
PARAMETER op_polyEmiss STRING "op_tabpe"
D op_polyTrans Poly transport opacity
PARAMETER op_polyTrans STRING "op_tabro"
D op_polyFileType Poly opacity file type
PARAMETER op_polyFileType STRING "ionmix4"
''',
    "Makefile": r'''
Simulation += Simulation_data.o
''',
    "Simulation_data.F90": r'''
module Simulation_data
  implicit none
#include "constants.h"
  real, save :: sim_targetRadius, sim_radialCore, sim_axialCore
  real, save :: sim_targHeight, sim_polyHeight, sim_foamHeight
  real, save :: sim_rhoTarg, sim_rhoPoly, sim_rhoFoam, sim_rhoCham
  real, save :: sim_teleTarg, sim_tionTarg, sim_tradTarg
  real, save :: sim_telePoly, sim_tionPoly, sim_tradPoly
  real, save :: sim_teleCham, sim_tionCham, sim_tradCham
  real, save :: sim_smallX
  character(len=MAX_STRING_LENGTH), save :: sim_initGeom
end module Simulation_data
''',
    "Simulation_init.F90": r'''
subroutine Simulation_init()
  use Simulation_data
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get
  implicit none
#include "constants.h"
#include "Flash.h"
  call RuntimeParameters_get('sim_targetRadius', sim_targetRadius)
  call RuntimeParameters_get('sim_radialCore', sim_radialCore)
  call RuntimeParameters_get('sim_axialCore', sim_axialCore)
  call RuntimeParameters_get('sim_targHeight', sim_targHeight)
  call RuntimeParameters_get('sim_polyHeight', sim_polyHeight)
  call RuntimeParameters_get('sim_foamHeight', sim_foamHeight)
  call RuntimeParameters_get('sim_rhoTarg', sim_rhoTarg)
  call RuntimeParameters_get('sim_rhoPoly', sim_rhoPoly)
  call RuntimeParameters_get('sim_rhoFoam', sim_rhoFoam)
  call RuntimeParameters_get('sim_rhoCham', sim_rhoCham)
  call RuntimeParameters_get('sim_teleTarg', sim_teleTarg)
  call RuntimeParameters_get('sim_tionTarg', sim_tionTarg)
  call RuntimeParameters_get('sim_tradTarg', sim_tradTarg)
  call RuntimeParameters_get('sim_telePoly', sim_telePoly)
  call RuntimeParameters_get('sim_tionPoly', sim_tionPoly)
  call RuntimeParameters_get('sim_tradPoly', sim_tradPoly)
  call RuntimeParameters_get('sim_teleCham', sim_teleCham)
  call RuntimeParameters_get('sim_tionCham', sim_tionCham)
  call RuntimeParameters_get('sim_tradCham', sim_tradCham)
  call RuntimeParameters_get('smallX', sim_smallX)
  call RuntimeParameters_get('sim_initGeom', sim_initGeom)
end subroutine Simulation_init
''',
    "Simulation_initBlock.F90": r'''
!! 2D R-Z: grid x = r (transverse), grid y = z (axial); target is a disk
!! of radius sim_targetRadius centred at r=0, layers symmetric in z.
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
  integer :: blkLimits(2, MDIM), blkLimitsGC(2, MDIM), axis(MDIM)
  real, allocatable :: xcent(:), ycent(:), zcent(:)
  real :: rho, tele, tion, trad, tradActual, axial, transverse
  integer :: species
#ifndef CHAM_SPEC
  integer :: CHAM_SPEC = 1, TARG_SPEC = 2, POLY_SPEC = 3
#endif
  call Grid_getBlkIndexLimits(blockId, blkLimits, blkLimitsGC)
  allocate(xcent(blkLimitsGC(HIGH, IAXIS)))
  call Grid_getCellCoords(IAXIS, blockId, CENTER, .true., xcent, blkLimitsGC(HIGH, IAXIS))
  allocate(ycent(blkLimitsGC(HIGH, JAXIS)))
  call Grid_getCellCoords(JAXIS, blockId, CENTER, .true., ycent, blkLimitsGC(HIGH, JAXIS))
  allocate(zcent(blkLimitsGC(HIGH, KAXIS)))
  call Grid_getCellCoords(KAXIS, blockId, CENTER, .true., zcent, blkLimitsGC(HIGH, KAXIS))

  do k = blkLimits(LOW,KAXIS), blkLimits(HIGH,KAXIS)
     do j = blkLimits(LOW,JAXIS), blkLimits(HIGH,JAXIS)
        do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)
           axis(IAXIS) = i
           axis(JAXIS) = j
           axis(KAXIS) = k
           axial = ycent(j)
           transverse = xcent(i)
           species = CHAM_SPEC
           if (transverse <= sim_targetRadius) then
              if (abs(axial) <= sim_targHeight) then
                 species = TARG_SPEC
              else if (abs(axial) <= sim_foamHeight) then
                 species = POLY_SPEC
              end if
           end if
           if (species == TARG_SPEC) then
              rho = sim_rhoTarg; tele = sim_teleTarg
              tion = sim_tionTarg; trad = sim_tradTarg
           else if (species == POLY_SPEC) then
              if (abs(axial) <= sim_polyHeight) then
                 rho = sim_rhoPoly
              else
                 rho = sim_rhoFoam
              end if
              tele = sim_telePoly; tion = sim_tionPoly; trad = sim_tradPoly
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
           if (NSPECIES > 0) then
              do n = SPECIES_BEGIN, SPECIES_END
                 if (n == species) then
                    call Grid_putPointData(blockId, CENTER, n, EXTERIOR, axis, &
                         1.0e0 - (NSPECIES - 1) * sim_smallX)
                 else
                    call Grid_putPointData(blockId, CENTER, n, EXTERIOR, axis, sim_smallX)
                 end if
              end do
           end if
        end do
     end do
  end do
  deallocate(xcent, ycent, zcent)
end subroutine Simulation_initBlock
''',
    "Grid_markRefineDerefine.F90": r'''
!! 2D R-Z layered refinement, bounding-box intersection.
!! high   : r <= sim_radialCore AND |z| <= sim_axialCore
!! medium : inside target disc AND within foam axial extent
!! low    : everything else (He and target edge outside the transverse core)
subroutine Grid_markRefineDerefine()
  use Grid_interface, ONLY : Grid_getListOfBlocks, Grid_getBlkBoundBox
  use tree, ONLY : newchild, refine, derefine, stay, nodetype, lrefine, lrefine_max, lrefine_min
  use Simulation_data, ONLY : sim_targetRadius, sim_radialCore, sim_axialCore, sim_foamHeight
  implicit none
#include "constants.h"
#include "Flash.h"
  integer :: i, lb, blockCount
  integer, dimension(MAXBLOCKS) :: blkList
  real, dimension(LOW:HIGH, MDIM) :: boundBox
  logical :: inRadCore, inAxCore, inTarget, inFoam
  integer :: hiTarget, loTarget, medTarget, edgeTarget

  newchild(:) = .FALSE.
  refine(:)   = .FALSE.
  derefine(:) = .FALSE.
  stay(:)     = .FALSE.

  hiTarget   = lrefine_max
  loTarget   = max(lrefine_min, lrefine_max - 1)
  medTarget  = max(lrefine_min + 1, lrefine_max - 3)
  edgeTarget = max(lrefine_min, lrefine_max - 4)

  call Grid_getListOfBlocks(ACTIVE_BLKS, blkList, blockCount)
  do i = 1, blockCount
     lb = blkList(i)
     if (nodetype(lb) /= LEAF) cycle
     call Grid_getBlkBoundBox(lb, boundBox)
     inRadCore = boundBox(HIGH,IAXIS) <= sim_radialCore
     inAxCore  = boundBox(HIGH,JAXIS) >= -sim_axialCore .and. &
                 boundBox(LOW,JAXIS)  <=  sim_axialCore
     inTarget  = boundBox(HIGH,IAXIS) <= sim_targetRadius
     inFoam    = boundBox(HIGH,JAXIS) >= -sim_foamHeight .and. &
                 boundBox(LOW,JAXIS)  <=  sim_foamHeight
     if (inRadCore .and. inAxCore) then
        if (lrefine(lb) < loTarget) then
           refine(lb) = .TRUE.; derefine(lb) = .FALSE.
        else if (lrefine(lb) > hiTarget) then
           refine(lb) = .FALSE.; derefine(lb) = .TRUE.
        end if
     else if (inTarget .and. inFoam) then
        if (lrefine(lb) < medTarget) then
           refine(lb) = .TRUE.; derefine(lb) = .FALSE.
        else if (lrefine(lb) > medTarget) then
           refine(lb) = .FALSE.; derefine(lb) = .TRUE.
        end if
     else if (inTarget) then
        if (lrefine(lb) > edgeTarget) then
           refine(lb) = .FALSE.; derefine(lb) = .TRUE.
        end if
     else
        if (lrefine(lb) > lrefine_min) then
           refine(lb) = .FALSE.; derefine(lb) = .TRUE.
        end if
     end if
  end do
  where (nodetype(:) .NE. LEAF)
     refine(:) = .FALSE.
     derefine(:) = .FALSE.
  end where
end subroutine Grid_markRefineDerefine
''',
}

# ── par 构建 ────────────────────────────────────────────────────────
_PARAMS_BASE: Dict[str, object] = {
    "LimitedSlopeBeta": 1.0,
    "RiemannSolver": "hllc",
    "cfl": 0.2,
    "charLimiting": True,
    "checkpointFileIntervalTime": 1e-11,
    "checkpointFileIntervalStep": 2000000000,
    "checkpointFileNumber": 0,
    "cvisc": 0.1,
    "diff_eleFlCoef": 0.08,
    "diff_eleFlMode": "fl_minmax",
    "diff_eleXlBoundaryType": "neumann",
    "diff_eleXrBoundaryType": "neumann",
    "diff_eleYlBoundaryType": "neumann",
    "diff_eleYrBoundaryType": "neumann",
    "diff_thetaImplct": 1.0,
    "diff_useEleCond": True,
    "dt_diff_factor": 1e100,
    "ed_adjustBeamsTargetIntensity": False,
    "ed_gradOrder": 2,
    "ed_laser3Din2D": True,
    "ed_laser3Din2DwedgeAngle": 0.1,
    "ed_printBeams": True,
    "ed_laserIOMaxNumberOfPositions": 10000,
    "ed_laserIOMaxNumberOfRays": 128,
    "ed_maxRayCount": 10000,
    "ed_useLaserIO": False,
    "entropy": False,
    "eosModeInit": "dens_temp_gather",
    "eos_useLogTables": False,
    "geometry": "cylindrical",
    "hx_dtFactor": 1e100,
    "nend": 10000000,
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
    "shockDetect": True,
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
    "xl_boundary_type": "axisymmetric",
    "xr_boundary_type": "outflow",
    "yl_boundary_type": "outflow",
    "yr_boundary_type": "outflow",
}


def _fmt(v: object) -> str:
    if isinstance(v, bool):
        return ".true." if v else ".false."
    if isinstance(v, float):
        return f"{v:.15g}"
    return str(v)


def build_par(tmax: float = DEFAULT_TMAX, plot_interval_step: int = 30000,
              peak: float = PEAK_POWER, overrides: Optional[Dict[str, object]] = None) -> str:
    """生成二维笛卡尔四束场景 .par 内容（LF）。"""
    p = dict(_PARAMS_BASE)
    p.update({
        "xmin": XMIN_CM, "xmax": XMAX_CM, "ymin": YMIN_CM, "ymax": YMAX_CM,
        "nblockx": NBX, "nblocky": NBY,
        "lrefine_max": LREF_MAX, "lrefine_min": LREF_MIN,
        "tmax": tmax, "dtinit": 1e-16, "dtmin": 1e-16, "dtmax": 1e-9,
        "plotFileIntervalStep": plot_interval_step,
        "sim_targetRadius": TARGET_RADIUS_CM,
        "sim_radialCore": RADIAL_CORE_CM,
        "sim_axialCore": AXIAL_CORE_CM,
        "sim_targHeight": DEFAULT_TARG_HEIGHT,
        "sim_polyHeight": DEFAULT_POLY_HEIGHT,
        "sim_foamHeight": DEFAULT_FOAM_HEIGHT,
        "sim_rhoTarg": DEFAULT_RHO_TARG,
        "sim_rhoPoly": DEFAULT_RHO_POLY,
        "sim_rhoFoam": DEFAULT_RHO_FOAM,
        "sim_rhoCham": DEFAULT_RHO_CHAM,
        "eos_chamEosType": "eos_gam",
        "eos_chamSubType": "ionmix4",
        "eos_chamTableFile": EOS_CHAM_FILE,
        "eos_targEosType": "eos_tab",
        "eos_targSubType": "ionmix4",
        "eos_targTableFile": EOS_TARG_FILE,
        "eos_polyEosType": "eos_tab",
        "eos_polySubType": "ionmix4",
        "eos_polyTableFile": EOS_POLY_FILE,
        "op_chamAbsorb": "op_tabpa", "op_chamEmiss": "op_tabpe",
        "op_chamTrans": "op_tabro", "op_chamFileType": "ionmix4",
        "op_chamFileName": EOS_CHAM_FILE,
        "op_targAbsorb": "op_tabpa", "op_targEmiss": "op_tabpe",
        "op_targTrans": "op_tabro", "op_targFileType": "ionmix4",
        "op_targFileName": EOS_TARG_FILE,
        "op_polyAbsorb": "op_tabpa", "op_polyEmiss": "op_tabpe",
        "op_polyTrans": "op_tabro", "op_polyFileType": "ionmix4",
        "op_polyFileName": EOS_POLY_FILE,
        "ms_chamA": MS_CHAM_A, "ms_chamZ": MS_CHAM_Z,
        "ms_targA": MS_TARG_A, "ms_targZ": MS_TARG_Z, "ms_targZMin": 0.02,
        "ms_polyA": MS_POLY_A, "ms_polyZ": MS_POLY_Z,
    })
    for k in ("sim_teleCham", "sim_teleTarg", "sim_telePoly",
              "sim_tionCham", "sim_tionTarg", "sim_tionPoly",
              "sim_tradCham", "sim_tradTarg", "sim_tradPoly"):
        p[k] = DEFAULT_TEMP

    pulse = trapezoid_pulse(peak)
    p["ed_numberOfPulses"] = 1
    p["ed_numberOfSections_1"] = len(pulse)
    for i, (t, power) in enumerate(pulse, start=1):
        p[f"ed_time_1_{i}"] = t
        p[f"ed_power_1_{i}"] = power

    p["ed_numberOfBeams"] = len(BEAMS)
    for b in BEAMS:
        bid = b["id"]
        p.update({
            f"ed_lensX_{bid}": b["lx"], f"ed_lensY_{bid}": b["ly"],
            f"ed_lensZ_{bid}": b["lz"],
            f"ed_targetX_{bid}": b["tx"], f"ed_targetY_{bid}": b["ty"],
            f"ed_targetZ_{bid}": b["tz"],
            f"ed_targetSemiAxisMajor_{bid}": TARGET_SEMI_CM,
            f"ed_targetSemiAxisMinor_{bid}": TARGET_SEMI_CM,
            f"ed_lensSemiAxisMajor_{bid}": LENS_SEMI_CM,
            f"ed_gridType_{bid}": "radial2D",
            f"ed_gridnRadialTics_{bid}": 48,
            f"ed_numberOfRays_{bid}": 4096,
            f"ed_crossSectionFunctionType_{bid}": "gaussian2D",
            f"ed_gaussianExponent_{bid}": 4.0,
            f"ed_gaussianRadiusMajor_{bid}": TARGET_SEMI_CM,
            f"ed_gaussianRadiusMinor_{bid}": TARGET_SEMI_CM,
            f"ed_semiAxisMajorTorsionAxis_{bid}": "x",
            f"ed_semiAxisMajorTorsionAngle_{bid}": 0.0,
            f"ed_pulseNumber_{bid}": 1,
            f"ed_wavelength_{bid}": WAVELENGTH,
        })
    if overrides:
        p.update(overrides)

    # 用标准 gen_par 模板排版（reset_to 保证不引入未声明参数）
    try:
        from flash.input_gen.gen_par.generator import ParGeneratorExtended
        gen = ParGeneratorExtended("sandwich_txn_cylindrical2d_one", dimension=2)
        gen.reset_to(p)
        text = gen.generate()
        text = text.replace(
            'run_comment = "LaserSlab 2D Simulation - Generated by ParGeneratorExtended"',
            'run_comment = "sandwich_txn_cylindrical2d_one 2D R-Z 3Din2D 2xnormal 1.6e12 W"', 1)
        return text
    except ImportError:
        warnings.warn("gen_par 不可用，使用自包含裸排版")
        return _build_par_bare(p)


def _build_par_bare(p: Dict[str, object]) -> str:
    lines = [
        'run_comment = "sandwich_txn_cartesian2d bare fallback"',
        'log_file    = "lasslab.log"',
        'basenm      = "lasslab_"',
        "",
    ]
    groups = [
        ("I/O PARAMETERS", lambda k: k.startswith(("checkpoint", "plot", "restart"))),
        ("RADIATION/OPACITY PARAMETERS", lambda k: k.startswith(("rt_", "op_"))),
        ("LASER PARAMETERS", lambda k: k.startswith("ed_")),
        ("CONDUCTION PARAMETERS", lambda k: k.startswith("diff_") or k in ("useDiffuse", "useConductivity")),
        ("HEAT EXCHANGE PARAMETERS", lambda k: k in ("useHeatexchange", "hx_dtFactor")),
        ("EOS PARAMETERS", lambda k: k.startswith("eos_") or k in ("smallt", "smallx", "eosModeInit")),
        ("HYDRO PARAMETERS", lambda k: k.startswith("use_") or k in (
            "useHydro", "order", "slopeLimiter", "cfl", "LimitedSlopeBeta", "RiemannSolver")),
        ("INITIAL CONDITIONS", lambda k: k.startswith(("sim_", "ms_"))),
        ("TIME PARAMETERS", lambda k: k in (
            "tmax", "dtinit", "dtmin", "dtmax", "nend", "tstep_change_factor", "dt_diff_factor")),
        ("MESH PARAMETERS", lambda k: k in (
            "geometry", "xmin", "xmax", "ymin", "ymax", "nblockx", "nblocky",
            "lrefine_max", "lrefine_min") or k.startswith("refine_var_")),
    ]
    written = set()
    for title, pred in groups:
        keys = [k for k in p if pred(k) and k not in written]
        if not keys:
            continue
        lines += ["", "#" * 30, f"#  {title}", "#" * 30, ""]
        width = max(len(k) for k in keys)
        for k in keys:
            lines.append(f"{k:<{width}} = {_fmt(p[k])}")
            written.add(k)
    rest = [k for k in p if k not in written]
    if rest:
        lines += ["", "#" * 30, "#  ADDITIONAL PARAMETERS", "#" * 30, ""]
        for k in rest:
            lines.append(f"{k} = {_fmt(p[k])}")
    return "\n".join(lines) + "\n"


def build_grid_fn(params: Dict[str, object]):
    """引擎要求的时间/空间输出网格（仅用于 result.h5 容器，不影响 FLASH 输入）。"""
    import numpy as np
    tmax = float(params.get("tmax", DEFAULT_TMAX))
    dt = min(1e-11, tmax / 10.0) if tmax > 0 else 1e-11
    t_grid = np.arange(0.0, tmax + dt * 0.5, dt)
    x_grid = np.linspace(XMIN_CM, XMAX_CM, 128)
    return t_grid, x_grid


class _Scenario(SimulationScenario):
    """自包含场景：自行生成 FLASH 输入。"""

    _REQUIRED = tuple(SIM_INPUT_TEXT)

    def ensure_sim_input(self) -> None:
        d = self.sim_input_dir
        need = [f for f in (*self._REQUIRED, *CN4_TABLE_SOURCES)
                if not (d / f).exists()]
        par_dst = d / "sandwich_txn_cylindrical2d_one.par"
        if not need and par_dst.exists():
            return
        d.mkdir(parents=True, exist_ok=True)
        for name, content in SIM_INPUT_TEXT.items():
            if not (d / name).exists():
                (d / name).write_text(content, encoding="utf-8", newline="\n")
        eos_root = _REPO / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        for name, rel in CN4_TABLE_SOURCES.items():
            dst = d / name
            if dst.exists():
                continue
            table = eos_root / rel
            if not table.exists():
                raise FileNotFoundError(f"中央表库缺少 {name}: {table}")
            shutil.copy2(table, dst)
        if not par_dst.exists():
            tmax = float(_TMAX_ENV) if _TMAX_ENV else DEFAULT_TMAX
            par_dst.write_text(build_par(tmax=tmax), encoding="utf-8", newline="\n")


SETUP_ARGS = (
    "-2d +cylindrical -nxb=12 -nyb=8 -maxblocks=8192 "
    "+hdf5typeio species=cham,targ,poly "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxBeams=2 ed_maxPulseSections=240"
)

scenario = _Scenario(
    name="SandwichTxN_cylindrical2d_one",
    description="CH/Si/CH 二维 R-Z 每侧单束正入射 3Din2D，45° 梯形收敛 2800um->800um，峰值 1.6e12 W",
    scenario_dir=_HERE,
    sim_input_dir=_HERE / "sim_input_si",
    sim_name="sandwich_txn_cylindrical2d_one",
    flash_setup_args=SETUP_ARGS,
    basenm="lasslab_",
    run_dir_name="runs",
    default_params={"tmax": float(_TMAX_ENV) if _TMAX_ENV else DEFAULT_TMAX},
    build_par=lambda params: build_par(tmax=float(params.get("tmax", DEFAULT_TMAX))),
    build_grid=build_grid_fn,
)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="sandwich_txn_cylindrical2d_one")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_gen = sub.add_parser("gen", help="生成 sim_input_si")
    p_gen.add_argument("--force", action="store_true")
    p_gen.add_argument("--tmax", default="")
    p_run = sub.add_parser("run", help="运行 FLASH")
    p_run.add_argument("--nproc", type=int, default=4)
    p_run.add_argument("--tmax", default="")
    p_run.add_argument("--mode", default="wsl")
    p_run.add_argument("--timeout", type=int, default=900)
    p_val = sub.add_parser("validate", help="生成几何验证多子图")
    p_val.add_argument("--depo", default="", help="可选 depo 数据文件 (.par/.h5/.dat)")
    args = ap.parse_args(argv)

    if args.cmd == "gen":
        d = _HERE / "sim_input_si"
        if args.force:
            shutil.rmtree(d, ignore_errors=True)
        scenario.ensure_sim_input()
        if args.tmax:
            (d / "sandwich_txn_cylindrical2d_one.par").write_text(
                build_par(tmax=float(args.tmax)), encoding="utf-8", newline="\n")
            print(f"[gen] tmax -> {args.tmax}")
        print(f"[gen] 输入就绪: {d}")
        return 0
    if args.cmd == "run":
        params = None
        if args.tmax:
            params = {"tmax": float(args.tmax)}
            (_HERE / "sim_input_si" / "sandwich_txn_cylindrical2d_one.par").write_text(
                build_par(tmax=float(args.tmax)), encoding="utf-8", newline="\n")
        engine = FlashSimulatorEngine(scenario, mode=args.mode)
        res = engine.run(params_override=params, runs_dir=str(_HERE / "runs"),
                         mpi_nproc=args.nproc, flash_timeout=args.timeout, mode=args.mode)
        print(f"[run] success={res.success} n_chk={res.n_chk} run_dir={res.run_dir}")
        if not res.success:
            print(f"[run] FAIL: {res.error_message}")
            return 1
        return 0
    if args.cmd == "validate":
        import subprocess
        cmd = [sys.executable, str(_HERE / "scripts" / "geometry_validation.py")]
        if args.depo:
            cmd += ["--depo", args.depo]
        return subprocess.run(cmd).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
