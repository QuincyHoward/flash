!!****if* source/Simulation/SimulationMain/LaserSlab/Simulation_initBlock
!!
!! NAME
!!  Simulation_initBlock
!!
!! SYNOPSIS
!!  call Simulation_initBlock(integer(IN) :: blockID)
!!
!! DESCRIPTION
!!
!!  Initializes fluid data for a specified block.
!!  Grid resolution detection test setup with 3 material layers:
!!
!!    Layer 1 — Al (targ):  |x| <= sim_targHeight   (0.2 um, high-Z)
!!    Layer 2 — CH (poly):  sim_targHeight < |x| <= sim_polyHeight (100 um)
!!    Layer 3 — He (cham):  |x| > sim_polyHeight    (chamber fill)
!!
!!  The large density contrast (Al: 2.7, CH: 1.1, He: 1e-6 g/cm³)
!!  drives AMR refinement at material interfaces.
!!
!!***
subroutine Simulation_initBlock(blockId)
  use Simulation_data
  use Grid_interface, ONLY : Grid_getBlkIndexLimits, &
       Grid_getCellCoords, Grid_putPointData, &
       Grid_getBlkPtr, Grid_releaseBlkPtr

  use Driver_interface, ONLY: Driver_abortFlash
  use RadTrans_interface, ONLY: RadTrans_mgdEFromT

  implicit none

#include "constants.h"
#include "Flash.h"

  integer, intent(in) :: blockId

  integer :: i, j, k, n
  integer :: blkLimits(2, MDIM)
  integer :: blkLimitsGC(2, MDIM)
  integer :: axis(MDIM)
  real, allocatable :: xcent(:), ycent(:), zcent(:)
  real :: tradActual
  real :: rho, tele, trad, tion
  integer :: species
  real, pointer, dimension(:,:,:,:) :: facexData, faceyData
  real :: frac, trans_width
  logical :: is_transition
#if NDIM > 0
  real, pointer, dimension(:,:,:,:) :: facezData
#endif

#ifndef CHAM_SPEC
  integer :: CHAM_SPEC = 1, TARG_SPEC = 2, POLY_SPEC = 3
#endif

  ! get the coordinate information for the current block from the database
  call Grid_getBlkIndexLimits(blockId,blkLimits,blkLimitsGC)

  allocate(xcent(blkLimitsGC(HIGH, IAXIS)))
  call Grid_getCellCoords(IAXIS, blockId, CENTER, .true., &
       xcent, blkLimitsGC(HIGH, IAXIS))
  allocate(ycent(blkLimitsGC(HIGH, JAXIS)))
  call Grid_getCellCoords(JAXIS, blockId, CENTER, .true., &
       ycent, blkLimitsGC(HIGH, JAXIS))
  allocate(zcent(blkLimitsGC(HIGH, KAXIS)))
  call Grid_getCellCoords(KAXIS, blockId, CENTER, .true., &
       zcent, blkLimitsGC(HIGH, KAXIS))

#if NFACE_VARS > 0
  if (sim_killdivb) then
     call Grid_getBlkPtr(blockID,facexData,FACEX)
     call Grid_getBlkPtr(blockID,faceyData,FACEY)
     if (NDIM>2) call Grid_getBlkPtr(blockID,facezData,FACEZ)
  endif
#endif

  ! Loop over cells and set the initial state
  do k = blkLimits(LOW,KAXIS),blkLimits(HIGH,KAXIS)
     do j = blkLimits(LOW,JAXIS),blkLimits(HIGH,JAXIS)
        do i = blkLimits(LOW,IAXIS),blkLimits(HIGH,IAXIS)

           axis(IAXIS) = i
           axis(JAXIS) = j
           axis(KAXIS) = k

           ! Default: chamber (He)
           species = CHAM_SPEC
           is_transition = .false.

           if (sim_initGeom == "slab") then
              if (NDIM == 1) then
                 ! Symmetric slab geometry around x=0
                 if (abs(xcent(i)) <= sim_targHeight) then
                    ! Al layer: |x| <= sim_targHeight
                    species = TARG_SPEC
                 else if (abs(xcent(i)) <= sim_polyHeight) then
                    ! CH layer: sim_targHeight < |x| <= sim_polyHeight
                    species = POLY_SPEC
                 end if
              end if
           end if

           if (.not. is_transition) then
              if (species == TARG_SPEC) then
              rho  = sim_rhoTarg
              tele = sim_teleTarg
              tion = sim_tionTarg
              trad = sim_tradTarg
           else if (species == POLY_SPEC) then
              rho  = sim_rhoPoly
              tele = sim_telePoly
              tion = sim_tionPoly
              trad = sim_tradPoly
           else
              rho  = sim_rhoCham
              tele = sim_teleCham
              tion = sim_tionCham
              trad = sim_tradCham
           end if
           end if

           call Grid_putPointData(blockId, CENTER, DENS_VAR, EXTERIOR, axis, rho)
           call Grid_putPointData(blockId, CENTER, TEMP_VAR, EXTERIOR, axis, tele)

#ifdef FLASH_3T
           call Grid_putPointData(blockId, CENTER, TION_VAR, EXTERIOR, axis, tion)
           call Grid_putPointData(blockId, CENTER, TELE_VAR, EXTERIOR, axis, tele)

           ! Set up radiation energy density:
           call RadTrans_mgdEFromT(blockId, axis, trad, tradActual)
           call Grid_putPointData(blockId, CENTER, TRAD_VAR, EXTERIOR, axis, tradActual)
#endif
           if (NSPECIES > 0) then
              ! Fill mass fractions:
              !   dominant species -> 1.0 - (NSPECIES-1)*sim_smallX
              !   others          -> sim_smallX
              do n = SPECIES_BEGIN, SPECIES_END
                 if (n == species) then
                    call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, &
                         1.0e0 - (NSPECIES - 1) * sim_smallX)
                 else
                    call Grid_putPointData(blockID, CENTER, n, EXTERIOR, axis, sim_smallX)
                 end if
              enddo
           end if

#ifdef BDRY_VAR
           call Grid_putPointData(blockId, CENTER, BDRY_VAR, EXTERIOR, axis, -1.0)
#endif
         enddo
     enddo
  enddo

#if NFACE_VARS > 0
  if (sim_killdivb) then
     do k = blkLimits(LOW,KAXIS),blkLimits(HIGH,KAXIS)
        do j = blkLimits(LOW,JAXIS),blkLimits(HIGH,JAXIS)
           do i = blkLimits(LOW,IAXIS),blkLimits(HIGH,IAXIS)+1
              facexData(MAG_FACE_VAR,i,j,k)= 0.0
           enddo
        enddo
     enddo
     do k = blkLimits(LOW,KAXIS),blkLimits(HIGH,KAXIS)
        do j = blkLimits(LOW,JAXIS),blkLimits(HIGH,JAXIS)+K2D
           do i = blkLimits(LOW,IAXIS),blkLimits(HIGH,IAXIS)
              faceyData(MAG_FACE_VAR,i,j,k)= 0.0
           enddo
        enddo
     enddo
     if (NDIM>2) then
        do k = blkLimits(LOW,KAXIS),blkLimits(HIGH,KAXIS)+K3D
           do j = blkLimits(LOW,JAXIS),blkLimits(HIGH,JAXIS)
              do i = blkLimits(LOW,IAXIS),blkLimits(HIGH,IAXIS)
                 facezData(MAG_FACE_VAR,i,j,k)= 0.0
              enddo
           enddo
        enddo
     endif
     call Grid_releaseBlkPtr(blockID,facexData,FACEX)
     call Grid_releaseBlkPtr(blockID,faceyData,FACEY)
     if (NDIM>2) call Grid_releaseBlkPtr(blockID,facezData,FACEZ)
  endif
#endif
  deallocate(xcent)
  deallocate(ycent)
  deallocate(zcent)

  return

end subroutine Simulation_initBlock
