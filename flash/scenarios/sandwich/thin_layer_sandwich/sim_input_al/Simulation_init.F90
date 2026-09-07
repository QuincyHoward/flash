!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_init
!!
!! NAME
!!  Simulation_init
!!
!! SYNOPSIS
!!  Simulation_init()
!!
!! DESCRIPTION
!!
!!  Initializes all runtime parameters for GridReDe simulation
!!
!!***
subroutine Simulation_init()
  use Simulation_data
  use RuntimeParameters_interface, ONLY : RuntimeParameters_get
  use Logfile_interface, ONLY : Logfile_stamp

  implicit none

#include "constants.h"
#include "Flash.h"

  ! Geometry
  call RuntimeParameters_get('sim_targHeight', sim_targHeight)
  call RuntimeParameters_get('sim_polyHeight', sim_polyHeight)

  ! Al (target)
  call RuntimeParameters_get('sim_rhoTarg', sim_rhoTarg)
  call RuntimeParameters_get('sim_teleTarg', sim_teleTarg)
  call RuntimeParameters_get('sim_tionTarg', sim_tionTarg)
  call RuntimeParameters_get('sim_tradTarg', sim_tradTarg)

  ! CH (poly)
  call RuntimeParameters_get('sim_rhoPoly', sim_rhoPoly)
  call RuntimeParameters_get('sim_telePoly', sim_telePoly)
  call RuntimeParameters_get('sim_tionPoly', sim_tionPoly)
  call RuntimeParameters_get('sim_tradPoly', sim_tradPoly)

  ! He (chamber)
  call RuntimeParameters_get('sim_rhoCham', sim_rhoCham)
  call RuntimeParameters_get('sim_teleCham', sim_teleCham)
  call RuntimeParameters_get('sim_tionCham', sim_tionCham)
  call RuntimeParameters_get('sim_tradCham', sim_tradCham)

  call RuntimeParameters_get('smallX', sim_smallX)
  call RuntimeParameters_get('sim_initGeom', sim_initGeom)

end subroutine Simulation_init
