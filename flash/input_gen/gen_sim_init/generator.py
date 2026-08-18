"""
Simulation_init.F90 文件生成器 (自包含)
═══════════════════════════════════════

内容从 LaserSlab/Simulation_init.F90 模板提取后硬编码。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union


DEFAULT_SIM_INIT_F90 = """\
!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_init
!!
!! NAME
!!
!!  Simulation_init
!!
!!
!! SYNOPSIS
!!
!!  Simulation_init()
!!
!!
!! DESCRIPTION
!!
!!  Initializes all the parameters needed for a particular simulation
!!
!!
!! ARGUMENTS
!!
!!  
!!
!! PARAMETERS
!!
!!***

subroutine Simulation_init()
  use Simulation_data
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get
  use Logfile_interface, ONLY : Logfile_stamp
  
  implicit none

#include "constants.h"
#include "Flash.h"

  real :: xmin, xmax, ymin, ymax
  integer :: lrefine_max, nblockx, nblocky
  character(len=MAX_STRING_LENGTH) :: str

  call RuntimeParameters_get('sim_targetRadius', sim_targetRadius)
  call RuntimeParameters_get('sim_targetHeight', sim_targetHeight)
  call RuntimeParameters_get('sim_vacuumHeight', sim_vacuumHeight)
  
  call RuntimeParameters_get('sim_rhoTarg', sim_rhoTarg)
  call RuntimeParameters_get('sim_teleTarg', sim_teleTarg)
  call RuntimeParameters_get('sim_tionTarg', sim_tionTarg)
  call RuntimeParameters_get('sim_tradTarg', sim_tradTarg)

  call RuntimeParameters_get('sim_rhoCham', sim_rhoCham)
  call RuntimeParameters_get('sim_teleCham', sim_teleCham)
  call RuntimeParameters_get('sim_tionCham', sim_tionCham)
  call RuntimeParameters_get('sim_tradCham', sim_tradCham)

  call RuntimeParameters_get('smallX', sim_smallX)

  call RuntimeParameters_get('sim_initGeom', sim_initGeom)

#ifdef FLASH_USM_MHD
  call RuntimeParameters_get('killdivb', sim_killdivb)
#endif
end subroutine Simulation_init
"""


def _build_multi_species_init_f90(species_defs: List[dict]) -> str:
    """从物种定义列表生成多物种 Simulation_init.F90。

    每个物种产生对应 RuntimeParameters_get 调用（几何 + 热物理量 + smallX）。
    """
    lines = [
        "!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_init",
        "!!",
        "!! NAME",
        "!!",
        "!!  Simulation_init",
        "!!",
        "!!",
        "!! SYNOPSIS",
        "!!",
        "!!  Simulation_init()",
        "!!",
        "!!",
        "!! DESCRIPTION",
        "!!",
        "!!  Initializes all the parameters needed for a particular simulation",
        "!!",
        "!!",
        "!! ARGUMENTS",
        "!!",
        "!!",
        "!!",
        "!! PARAMETERS",
        "!!",
        "!!***",
        "",
        "subroutine Simulation_init()",
        "  use Simulation_data",
        "  use RuntimeParameters_interface, ONLY : RuntimeParameters_get",
        "  use Logfile_interface, ONLY : Logfile_stamp",
        "  ",
        "  implicit none",
        "  ",
        '#include "constants.h"',
        '#include "Flash.h"',
        "",
        "  real :: xmin, xmax, ymin, ymax",
        "  integer :: lrefine_max, nblockx, nblocky",
        "  character(len=MAX_STRING_LENGTH) :: str",
    ]

    for sp in species_defs:
        name = sp["name"]
        cap = name.capitalize()
        lines.append(f"  !! {cap} !!")
        rad = sp.get("radius_param") or f"sim_{name}Radius"
        hei = sp.get("height_param") or f"sim_{name}Height"
        if "radius" in sp and sp["radius"] is not None:
            lines.append(f"  call RuntimeParameters_get('{rad}', {rad})")
        if "height" in sp and sp["height"] is not None:
            lines.append(f"  call RuntimeParameters_get('{hei}', {hei})")
        lines.append("")
        lines.append(f"  call RuntimeParameters_get('sim_rho{cap}', sim_rho{cap})")
        lines.append(f"  call RuntimeParameters_get('sim_tele{cap}', sim_tele{cap})")
        lines.append(f"  call RuntimeParameters_get('sim_tion{cap}', sim_tion{cap})")
        lines.append(f"  call RuntimeParameters_get('sim_trad{cap}', sim_trad{cap})")
        lines.append(f"  !! {cap} !!")
        lines.append("")

    lines.extend([
        "  call RuntimeParameters_get('smallX', sim_smallX)",
        "",
        "  call RuntimeParameters_get('sim_initGeom', sim_initGeom)",
        "",
        "#ifdef FLASH_USM_MHD",
        "  call RuntimeParameters_get('killdivb', sim_killdivb)",
        "#endif",
        "end subroutine Simulation_init",
        "",
    ])
    return "\n".join(lines)


class SimInitGenerator:
    """Simulation_init.F90 文件生成器 (自包含)。

    内容从 LaserSlab/Simulation_init.F90 提取并硬编码。
    """

    def generate(self, params: Optional[Dict[str, Any]] = None) -> str:
        """生成 Simulation_init.F90 内容。

        Args:
            params: 可选参数（预留，暂不处理）。若含 "species" 键（物种定义
                列表），生成多物种版本；否则返回默认两物种模板。

        Returns:
            Simulation_init.F90 内容字符串
        """
        if params and params.get("species"):
            return _build_multi_species_init_f90(params["species"])
        return DEFAULT_SIM_INIT_F90

    def save(
        self,
        output_path: Union[str, Path],
        params: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """生成并保存 Simulation_init.F90。"""
        content = self.generate(params=params)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8", newline="\n")
        return out
