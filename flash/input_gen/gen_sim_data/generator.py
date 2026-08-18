"""
Simulation_data.F90 文件生成器 (自包含)
═══════════════════════════════════════

内容从 LaserSlab1d/Simulation_data.F90 模板提取后硬编码。
支持多物种 (multi-species) 生成：传入物种定义列表即可为每个物种
渲染对应的运行时参数声明。
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


def _build_multi_species_data_f90(species_defs: List[dict]) -> str:
    """从物种定义列表生成多物种 Simulation_data.F90。

    每个物种渲染一组运行时参数声明：几何 (radius/height) + 热物理量
    (rho/tele/tion/trad) + zmin + eos 类型。cham 不写 geometry。

    Args:
        species_defs: 形如 [{"name": "cham", "file": ..., "rho": ...,
            "A": ..., "Z": ..., "radius": ..., "height": ...}, ...]
    """
    lines = [
        "!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_data",
        "!!",
        "!! NAME",
        "!!  Simulation_data",
        "!!",
        "!! SYNOPSIS",
        "!!  Use Simulation_data",
        "!!",
        "!! DESCRIPTION",
        "!!",
        "!!  Store the simulation data",
        "!!",
        "!!",
        "!!***",
        "module Simulation_data",
        "",
        "  implicit none",
        "",
        '#include "constants.h"',
        "",
        "  !! *** Runtime Parameters *** !!",
    ]

    for sp in species_defs:
        name = sp["name"]
        cap = name.capitalize()
        lines.append(f"  !! {cap} !!")
        rad = sp.get("radius_param") or f"sim_{name}Radius"
        hei = sp.get("height_param") or f"sim_{name}Height"
        if "radius" in sp and sp["radius"] is not None:
            lines.append(f"  real, save :: {rad}")
        if "height" in sp and sp["height"] is not None:
            lines.append(f"  real, save :: {hei}")
        lines.append("")
        lines.append(f"  real,    save :: sim_rho{cap}")
        lines.append(f"  real,    save :: sim_tele{cap}")
        lines.append(f"  real,    save :: sim_tion{cap}")
        lines.append(f"  real,    save :: sim_trad{cap}")
        lines.append(f"  real,    save :: sim_zmin{cap}")
        lines.append(f"  integer, save :: sim_eos{cap}")
        lines.append(f"  !! {cap} !!")
        lines.append("")

    lines.extend([
        "  logical, save :: sim_killdivb = .FALSE.",
        "  real, save :: sim_smallX",
        "  character(len=MAX_STRING_LENGTH), save :: sim_initGeom",
        "",
        "",
        "end module Simulation_data",
        "",
    ])
    return "\n".join(lines)


class SimDataGenerator:
    """Simulation_data.F90 文件生成器 (自包含)。

    内容从 LaserSlab1d/Simulation_data.F90 提取并硬编码。
    """

    def generate(self, species: Optional[List[dict]] = None) -> str:
        """生成 Simulation_data.F90 内容。

        Args:
            species: 物种定义列表。若为 None 或空，返回默认两物种
                (targ/cham) 模板。

        Returns:
            Simulation_data.F90 内容字符串
        """
        if species:
            return _build_multi_species_data_f90(species)
        return DEFAULT_SIM_DATA_F90

    def save(
        self,
        output_path: Union[str, Path],
        species: Optional[List[dict]] = None,
    ) -> Path:
        """生成并保存 Simulation_data.F90。"""
        content = self.generate(species=species)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8", newline="\n")
        return out
