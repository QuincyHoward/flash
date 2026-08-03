"""
Simulation_data.F90 文件生成器 (自包含)
═══════════════════════════════════════

内容从 LaserSlab1d/Simulation_data.F90 模板提取后硬编码。
"""

from pathlib import Path
from typing import List, Optional, Union


DEFAULT_SIM_DATA_F90 = """\
!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_data
!!
!! NAME
!!  Simulation_data
!!
!! SYNOPSIS
!!  Use Simulation_data
!!
!! DESCRIPTION
!!
!!  Store the simulation data
!!
!! 
!!***
module Simulation_data

  implicit none

#include "constants.h"

  !! *** Runtime Parameters *** !!  
  real, save :: sim_targetRadius
  real, save :: sim_targetHeight
  real, save :: sim_vacuumHeight

  real,    save :: sim_rhoTarg  
  real,    save :: sim_teleTarg 
  real,    save :: sim_tionTarg 
  real,    save :: sim_tradTarg 
  real,    save :: sim_zminTarg
  integer, save :: sim_eosTarg

  real,    save :: sim_rhoCham  
  real,    save :: sim_teleCham 
  real,    save :: sim_tionCham 
  real,    save :: sim_tradCham 
  integer, save :: sim_eosCham  

  logical, save :: sim_killdivb = .FALSE.
  real, save :: sim_smallX
  character(len=MAX_STRING_LENGTH), save :: sim_initGeom


end module Simulation_data
"""


class SimDataGenerator:
    """Simulation_data.F90 文件生成器 (自包含)。

    内容从 LaserSlab1d/Simulation_data.F90 提取并硬编码。
    """

    def generate(self, species: Optional[List[str]] = None) -> str:
        """生成 Simulation_data.F90 内容。

        Args:
            species: species 列表（预留，暂不处理）

        Returns:
            Simulation_data.F90 内容字符串
        """
        return DEFAULT_SIM_DATA_F90

    def save(
        self,
        output_path: Union[str, Path],
        species: Optional[List[str]] = None,
    ) -> Path:
        """生成并保存 Simulation_data.F90。"""
        content = self.generate(species=species)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return out
