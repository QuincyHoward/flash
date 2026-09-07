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
!!  Store the simulation data for GridReDe simulation
!!  (3-species: cham=He, targ=Al, poly=CH)
!!
!!***
module Simulation_data

  implicit none

#include "constants.h"

  !! *** Runtime Parameters *** !!

  ! Geometry
  real, save :: sim_targHeight
  real, save :: sim_polyHeight

  ! Al (target) material
  real,    save :: sim_rhoTarg
  real,    save :: sim_teleTarg
  real,    save :: sim_tionTarg
  real,    save :: sim_tradTarg

  ! CH (poly) material
  real,    save :: sim_rhoPoly
  real,    save :: sim_telePoly
  real,    save :: sim_tionPoly
  real,    save :: sim_tradPoly

  ! He (chamber) material
  real,    save :: sim_rhoCham
  real,    save :: sim_teleCham
  real,    save :: sim_tionCham
  real,    save :: sim_tradCham

  logical, save :: sim_killdivb = .FALSE.
  real, save :: sim_smallX
  character(len=MAX_STRING_LENGTH), save :: sim_initGeom

end module Simulation_data
