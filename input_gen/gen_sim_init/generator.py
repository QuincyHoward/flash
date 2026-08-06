"""
Simulation_init.F90 文件生成器 (自包含)
═══════════════════════════════════════

内容从 LaserSlab/Simulation_init.F90 模板提取后硬编码。
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union


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


class SimInitGenerator:
    """Simulation_init.F90 文件生成器 (自包含)。

    内容从 LaserSlab/Simulation_init.F90 提取并硬编码。
    """

    def generate(self, params: Optional[Dict[str, Any]] = None) -> str:
        """生成 Simulation_init.F90 内容。

        Args:
            params: 可选参数（预留，暂不处理）

        Returns:
            Simulation_init.F90 内容字符串
        """
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
        out.write_text(content, encoding="utf-8")
        return out
