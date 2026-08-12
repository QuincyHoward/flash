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
!!
!!  ═══════════════════════════════════════════════════════════════
!!  MODIFIED VERSION — This file is a modified version of the FLASH
!!  Center's source/Simulation/SimulationMain/LaserSlab/Simulation_data,
!!  adapted for a new physics setup. Per FLASH License Agreement §4(a),
!!  this notice declares that this file has been changed from the
!!  original FLASH Code; the original FLASH header is preserved intact
!!  per §4(c).
!!  This product includes software developed by and/or derived from the
!!  Flash Center for Computational Science (https://flash.rochester.edu)
!!  to which the U.S. Government retains certain rights. (FLASH §4(b))
!!  FLASH: https://flash.rochester.edu
!!  ═══════════════════════════════════════════════════════════════
!!
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
