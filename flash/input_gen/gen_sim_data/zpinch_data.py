"""ZPinch Simulation_data.F90 生成器 —— 官方 stock 逐字快照 (v1 模板)。

隔离说明: 独立文件, 不触碰 gen_sim_data/generator.py 的激光渲染器。

源: FLASH4.8 source/Simulation/SimulationMain/magnetoHD/ZPinch (随 Gitee 分发的
官方文件快照; EOS 表 Be/DD-006-imx.cn4 不在此, 随 setup DATAFILES 获取)。
"""

from pathlib import Path

ZPINCH_SIM_DATA_F90 = r'''!!****if* source/Simulation/SimulationMain/magnetoHD/SZP/Simulation_data
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

  integer, save :: sim_meshMe

  !! *** Runtime Parameters *** !!
  real, save :: sim_fill_dens
  real, save :: sim_fill_tele
  real, save :: sim_fill_tion
  real, save :: sim_fill_trad
  real, save :: sim_fill_maxTemp
  real, save :: sim_fill_minTemp
  real, save :: sim_fill_ctr
  real, save :: sim_fill_sigma
  real, save :: sim_fill_minDens

  real, save :: sim_line_dens
  real, save :: sim_line_tele
  real, save :: sim_line_tion
  real, save :: sim_line_trad
  real, save :: sim_line_maxTemp
  real, save :: sim_line_minTemp
  real, save :: sim_line_ctr
  real, save :: sim_line_sigma
  real, save :: sim_line_minDens

  real, save :: sim_vacu_dens
  real, save :: sim_vacu_tele
  real, save :: sim_vacu_tion
  real, save :: sim_vacu_trad
  real, save :: sim_vacu_maxTemp
  real, save :: sim_vacu_minTemp

  integer, save :: sim_rhoType
  real, save :: sim_innerRadius
  real, save :: sim_thickness
  real, save :: sim_pert
  integer, save :: sim_seed

  real, save :: sim_trajOutputInterval
  real, save :: sim_trajOutputIntervalNearStag
  real, save :: sim_rNearStag

  logical, save :: sim_killdivb = .FALSE.
  real, save :: sim_smallX
  integer, save :: sim_geometry

  real, save :: sim_xmin
  real, save :: sim_xmax
  real, save :: sim_ymin
  real, save :: sim_ymax

  integer, save :: sim_globalMe
  integer, save :: sim_globalComm

  real, save :: sim_vacu_tradActual

end module Simulation_data
'''


class ZPinchSimDataGenerator:
    """Simulation_data.F90 生成器 (官方 stock 逐字快照)。"""

    def generate(self) -> str:
        """返回文件文本 (与官方 stock 逐字节一致, LF 行尾)。"""
        return ZPINCH_SIM_DATA_F90

    def save(self, output_path) -> Path:
        """写出文件, 返回路径。"""
        p = Path(output_path)
        p.write_text(self.generate(), encoding="utf-8", newline="\n")
        return p
