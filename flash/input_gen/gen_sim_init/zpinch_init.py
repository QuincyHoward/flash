"""ZPinch Simulation_init.F90 生成器 —— 官方 stock 逐字快照 (v1 模板)。

隔离说明: 独立文件, 不触碰 gen_sim_init/generator.py 的激光渲染器。

源: FLASH4.8 source/Simulation/SimulationMain/magnetoHD/ZPinch (随 Gitee 分发的
官方文件快照; EOS 表 Be/DD-006-imx.cn4 不在此, 随 setup DATAFILES 获取)。
"""

from pathlib import Path

ZPINCH_SIM_INIT_F90 = r'''!!****if* source/Simulation/SimulationMain/magnetoHD/SZP/Simulation_init
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

!! Format is easy enough to emulate, main thing is to remember to add new variables (like ones placed in config or par file) to this one, and all other relevant files.


subroutine Simulation_init()
  use Simulation_data
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get, RuntimeParameters_mapStrToInt
  use Logfile_interface, ONLY : Logfile_stamp
  use Driver_interface, ONLY : Driver_getMype, Driver_getComm

  implicit none

#include "constants.h"
#include "Flash.h"

  character(len=MAX_STRING_LENGTH) :: str

  call Driver_getMype(MESH_COMM,sim_meshMe)
  call Driver_getMype(GLOBAL_COMM, sim_globalMe)
  call Driver_getComm(GLOBAL_COMM,sim_globalComm)

  call RuntimeParameters_get('sim_fill_dens', sim_fill_dens)
  call RuntimeParameters_get('sim_fill_tele', sim_fill_tele)
  call RuntimeParameters_get('sim_fill_tion', sim_fill_tion)
  call RuntimeParameters_get('sim_fill_trad', sim_fill_trad)
  call RuntimeParameters_get('sim_fill_maxTemp', sim_fill_maxTemp)
  call RuntimeParameters_get('sim_fill_minTemp', sim_fill_minTemp)
  call RuntimeParameters_get('sim_fill_ctr', sim_fill_ctr)
  call RuntimeParameters_get('sim_fill_sigma', sim_fill_sigma)
  call RuntimeParameters_get('sim_fill_minDens', sim_fill_minDens)

  call RuntimeParameters_get('sim_line_dens', sim_line_dens)
  call RuntimeParameters_get('sim_line_tele', sim_line_tele)
  call RuntimeParameters_get('sim_line_tion', sim_line_tion)
  call RuntimeParameters_get('sim_line_trad', sim_line_trad)
  call RuntimeParameters_get('sim_line_maxTemp', sim_line_maxTemp)
  call RuntimeParameters_get('sim_line_minTemp', sim_line_minTemp)
  call RuntimeParameters_get('sim_line_ctr', sim_line_ctr)
  call RuntimeParameters_get('sim_line_sigma', sim_line_sigma)
  call RuntimeParameters_get('sim_line_minDens', sim_line_minDens)

  call RuntimeParameters_get('sim_vacu_dens', sim_vacu_dens)
  call RuntimeParameters_get('sim_vacu_tele', sim_vacu_tele)
  call RuntimeParameters_get('sim_vacu_tion', sim_vacu_tion)
  call RuntimeParameters_get('sim_vacu_trad', sim_vacu_trad)
  call RuntimeParameters_get('sim_vacu_maxTemp', sim_vacu_maxTemp)
  call RuntimeParameters_get('sim_vacu_minTemp', sim_vacu_minTemp)

  call RuntimeParameters_get('sim_rhoType', sim_rhoType)
  call RuntimeParameters_get('sim_innerRadius', sim_innerRadius)
  call RuntimeParameters_get('sim_thickness', sim_thickness)
  call RuntimeParameters_get('sim_pert', sim_pert)
  call RuntimeParameters_get('sim_seed', sim_seed)

  call RuntimeParameters_get('sim_trajOutputInterval', sim_trajOutputInterval)
  call RuntimeParameters_get('sim_trajOutputIntervalNearStag',sim_trajOutputIntervalNearStag)
  call RuntimeParameters_get('sim_rNearStag', sim_rNearStag)


  call RuntimeParameters_get('smallX', sim_smallX)

#ifdef FLASH_USM_MHD
  call RuntimeParameters_get('killdivb',sim_killdivb)
#endif

  call RuntimeParameters_get('geometry', str)
  call RuntimeParameters_mapStrToInt(str, sim_geometry)

  call RuntimeParameters_get('xmin', sim_xmin)
  call RuntimeParameters_get('xmax', sim_xmax)
  call RuntimeParameters_get('ymin', sim_ymin)
  call RuntimeParameters_get('ymax', sim_ymax)

end subroutine Simulation_init
'''


class ZPinchSimInitGenerator:
    """Simulation_init.F90 生成器 (官方 stock 逐字快照)。"""

    def generate(self) -> str:
        """返回文件文本 (与官方 stock 逐字节一致, LF 行尾)。"""
        return ZPINCH_SIM_INIT_F90

    def save(self, output_path) -> Path:
        """写出文件, 返回路径。"""
        p = Path(output_path)
        p.write_text(self.generate(), encoding="utf-8", newline="\n")
        return p
