"""ZPinch Simulation_initBlock.F90 生成器 —— 官方 stock 逐字快照 (v1 模板)。

复杂度判定: select case(sim_rhoType) 三区几何 + 随机扰动 + solnData 直写,
与激光系 BlockGenerator/GridBuilder (矩形区域模型) 零兼容 → 独立隔离文件。

源: FLASH4.8 source/Simulation/SimulationMain/magnetoHD/ZPinch (随 Gitee 分发的
官方文件快照; EOS 表 Be/DD-006-imx.cn4 不在此, 随 setup DATAFILES 获取)。
"""

from pathlib import Path

ZPINCH_INITBLOCK_F90 = r'''!!****if* source/Simulation/SimulationMain/magnetoHD/SZP/Simulation_initBlock
!!
!! NAME
!!
!!  Simulation_initBlock
!!
!!
!! SYNOPSIS
!!
!!  call Simulation_initBlock(integer(IN) :: blockID)
!!
!!
!!
!!
!! DESCRIPTION
!!
!!  Initializes fluid data (density, pressure, velocity, etc.) for
!!  a specified block.
!!
!! ARGUMENTS
!!
!!  blockID -        the number of the block to initialize
!!
!!
!!
!!***

subroutine Simulation_initBlock(blockId)
  use Simulation_data
  use Grid_data
  use Grid_interface, ONLY : Grid_getBlkIndexLimits, &
       Grid_getCellCoords, Grid_getBlkPtr, Grid_releaseBlkPtr
  use Driver_interface, ONLY: Driver_abortFlash
  use RadTrans_interface, ONLY: RadTrans_mgdEFromT
  use rt_data, ONLY : rt_useMGD

#include "Flash_mpi_implicitNone.fh"

#include "constants.h"
#include "Flash.h"

  integer, intent(in) :: blockId
  real, dimension(MDIM) :: del
  integer :: i, j, k, n, nn, blkSeed 
  integer :: blkLimits(2, MDIM)
  integer :: blkLimitsGC(2, MDIM)
  integer :: axis(MDIM)
  integer :: sizeX, sizeY, sizeZ, datasize
  real, allocatable :: xcent(:), ycent(:), zcent(:), randoms(:)
  real :: radius, tradActual, rand
  real :: rho, tele, trad, tion, dx, dy, dz
  integer :: species
  real, pointer, dimension(:,:,:,:) :: solnData,facexData,faceyData,facezData
  real :: veloc
  real :: romax, romin, kr, r0
  real :: vacu_tradActual
  integer :: error

#ifndef FILL_SPEC
  integer :: FILL_SPEC = 1, LINE_SPEC = 2, VACU_SPEC = 3
#endif


  !! get the coordinate information for the current block from the database
  call Grid_getBlkIndexLimits(blockId,blkLimits,blkLimitsGC)
  sizeX = blkLimitsGC(HIGH,IAXIS)-blkLimitsGC(LOW,IAXIS)+1
  sizeY = blkLimitsGC(HIGH,JAXIS)-blkLimitsGC(LOW,JAXIS)+1
  sizeZ = blkLimitsGC(HIGH,KAXIS)-blkLimitsGC(LOW,KAXIS)+1
  datasize = sizeX*sizeY*sizeZ
  allocate(xcent(sizeX))
  allocate(ycent(sizeY))
  allocate(zcent(sizeZ))
  allocate(randoms(datasize))
  xcent = 0.0
  ycent = 0.0
  zcent = 0.0

  call Grid_getCellCoords(IAXIS, blockId, CENTER, .true., xcent, sizeX)
  if (NDIM >= 2) call Grid_getCellCoords(JAXIS, blockId, CENTER, .true., ycent, sizeY)
  if (NDIM == 3) call Grid_getCellCoords(KAXIS, blockId, CENTER, .true., zcent, sizeZ)

  call Grid_getDeltas(blockID,del)
  dx = del(1)
  dy = del(2)
  dz = del(3)

  call Grid_getBlkPtr(blockID,solnData,CENTER)
       
#if NFACE_VARS > 0
  if (sim_killdivb) then
     call Grid_getBlkPtr(blockID,facexData,FACEX)
     if (NDIM >= 2) call Grid_getBlkPtr(blockID,faceyData,FACEY)
     if (NDIM == 3) call Grid_getBlkPtr(blockID,facezData,FACEZ)
  endif
#endif


  !! Set up array of pseudo-random numbers ranging from -1 to 1
  !! Random number generator is seeded with a different number for each block
  !! via blockId multiplication but any given simulation is repeatable as long
  !! as sim_seed, number of blocks, and number of procs remains unchanged.
  blkSeed = sim_seed*blockId
  call random_seed(blkSeed)
  do nn = 1, datasize
     call random_number(rand)
     randoms(nn) = rand*2. - 1.
  enddo


  !------------------------------------------------------------------------------

  vacu_tradActual = 0.

  !! Loop over cells and set the initial state
  nn = 1
  do k = blkLimitsGC(LOW,KAXIS),blkLimitsGC(HIGH,KAXIS)
     do j = blkLimitsGC(LOW,JAXIS),blkLimitsGC(HIGH,JAXIS)
        do i = blkLimitsGC(LOW,IAXIS),blkLimitsGC(HIGH,IAXIS)

           axis(IAXIS) = i
           axis(JAXIS) = j
           axis(KAXIS) = k

           radius = xcent(i)

           species = FILL_SPEC
           select case (sim_rhoType) 
           case (0) !! step-function type (ie, 0 Gaussians, solid liner)
              if (radius >= sim_innerRadius) then
                 if (radius <= sim_innerRadius + sim_thickness) then
                    species = LINE_SPEC
                 else
                    species = VACU_SPEC
                 endif
              endif
              if (species == FILL_SPEC) then
                 rho = sim_fill_dens
              elseif (species == LINE_SPEC) then
                 rho = sim_line_dens*(1. + sim_pert*randoms(nn))
                 nn = nn + 1
              else
                 rho = sim_vacu_dens
              endif
           case (1) !! 1 Gaussian for liner, fill is constant
              if (radius >= sim_innerRadius) then
                 species = LINE_SPEC
                 rho = sim_line_dens*exp(-(radius-sim_line_ctr)**2/(2.*sim_line_sigma**2))

                 if (rho <= sim_vacu_dens) species = VACU_SPEC

              endif
              if (species == FILL_SPEC) then
                 rho = sim_fill_dens
              elseif (species == LINE_SPEC) then
                 rho = rho*(1. + sim_pert*randoms(nn))
                 nn = nn + 1
              else
                 rho = max(rho,sim_line_minDens)  !! density floor in vacuum
              endif
           case (2) !! 2 Gaussians for fill and liner, summed
              rho = sim_line_minDens + &
                    sim_fill_dens*exp(-(radius-sim_fill_ctr)**2/(2.*sim_fill_sigma**2)) + &
                    sim_line_dens*exp(-(radius-sim_line_ctr)**2/(2.*sim_line_sigma**2))
              if (radius >= sim_innerRadius) then
                 if (radius <= sim_innerRadius + sim_thickness) then
                    species = LINE_SPEC
                    !! Assign "vacuum" species based on unperturbed density
                    if (rho <= sim_vacu_dens) species = VACU_SPEC
                 else
                    species = VACU_SPEC
                 endif
              endif
              if (species == LINE_SPEC) then
                 rho = rho*(1. + sim_pert*randoms(nn))
                 nn = nn + 1
              endif
           case (11) !! double Gaussians (piecewise, not summed)
              if (radius >= sim_innerRadius) then
                 species = LINE_SPEC
              endif
              if (species == FILL_SPEC) then
                 romax = sim_fill_dens
                 romin = sim_fill_minDens
                 kr = -1./(2.*sim_fill_sigma**2)
                 r0 = sim_fill_ctr
                 rho = (romax - romin)*exp(kr*(radius-r0)**2) + romin
              elseif (species == LINE_SPEC) then
                 romax = sim_line_dens
                 romin = sim_line_minDens
                 kr = -1./(2.*sim_line_sigma**2)
                 r0 = sim_line_ctr
                 rho = (romax - romin)*exp(kr*(radius-r0)**2) + romin

                 !! Assign "vacuum" species based on density
                 !!if (rho <= sim_vacu_dens) species = VACU_SPEC

                 !! Assign vacuum species based on position
                 if (radius >= sim_innerRadius + sim_thickness) then
                    species = VACU_SPEC
                    rho = sim_vacu_dens
                 endif
              endif


              !! Add perturbation
              if (species == LINE_SPEC) then
                 rho = rho*(1. + sim_pert*randoms(nn))
                 nn = nn + 1
              endif
           end select


           veloc = 0.
           if (species == FILL_SPEC) then
              tele = sim_fill_tele
              tion = sim_fill_tion
              trad = sim_fill_trad
           elseif (species == LINE_SPEC) then
              tele = sim_line_tele
              tion = sim_line_tion
              trad = sim_line_trad
           else
              tele = sim_vacu_tele
              tion = sim_vacu_tion
              trad = sim_vacu_trad
           endif

           solnData(DENS_VAR,i,j,k) = rho
           solnData(TEMP_VAR,i,j,k) = tele

#ifdef FLASH_3T
           solnData(TION_VAR,i,j,k) = tion
           solnData(TELE_VAR,i,j,k) = tele

           ! Set up radiation energy density:
           call RadTrans_mgdEFromT(blockId, axis, trad, tradActual)
           solnData(TRAD_VAR,i,j,k) = tradActual
           if (.not. rt_useMGD) then
              vacu_tradActual = tradActual
           else
              if (species == VACU_SPEC) vacu_tradActual = tradActual
           endif
#endif

           if (NSPECIES > 0) then
              ! Fill mass fractions in solution array if we have any SPECIES defined.
              do n = SPECIES_BEGIN,SPECIES_END
                 if (n==species) then
                    solnData(n,i,j,k) = 1.0e0-(NSPECIES-1)*sim_smallX
                 else
                    solnData(n,i,j,k) = sim_smallX
                 endif
              enddo
           endif

           !! velocities initially zero
           solnData(VELX_VAR,i,j,k) = veloc
           solnData(VELY_VAR:VELZ_VAR,i,j,k) = 0.0

           !! B-fields initially zero
           solnData(MAGX_VAR:MAGZ_VAR,i,j,k) = 0.0
#if NFACE_VARS > 0
           if (sim_killdivb) then
              facexData(MAG_FACE_VAR,i,j,k) = 0.
              if (NDIM >= 2) faceyData(MAG_FACE_VAR,i,j,k) = 0.
              if (NDIM == 3) facezData(MAG_FACE_VAR,i,j,k) = 0.
           endif
#endif

#ifdef BDRY_VAR
           solnData(BDRY_VAR,i,j,k) = -1.0
#endif

        enddo
     enddo
  enddo

  !! Make sure every proc has same sim_vacu_tradActual
  !!call MPI_AllReduce (vacu_tradActual, sim_vacu_tradActual, 1, FLASH_REAL, MPI_MAX, sim_globalComm, error)
  sim_vacu_tradActual = vacu_tradActual

  !! Make sure face B-fields are definitely zero
#if NFACE_VARS > 0
  if (sim_killdivb) then
     facexData(MAG_FACE_VAR,:,:,:) = 0.
     if (NDIM >= 2) faceyData(MAG_FACE_VAR,:,:,:) = 0.
     if (NDIM == 3) facezData(MAG_FACE_VAR,:,:,:) = 0.
     facexData(MAGI_FACE_VAR,:,:,:) = 0.
     if (NDIM >= 2) faceyData(MAGI_FACE_VAR,:,:,:) = 0.
     if (NDIM == 3) facezData(MAGI_FACE_VAR,:,:,:) = 0.
  endif
#endif

  call Grid_releaseBlkPtr(blockID,solnData,CENTER)

#if NFACE_VARS > 0
  if (sim_killdivb) then
     call Grid_releaseBlkPtr(blockID,facexData,FACEX)
     if (NDIM >= 2) call Grid_releaseBlkPtr(blockID,faceyData,FACEY)
     if (NDIM == 3) call Grid_releaseBlkPtr(blockID,facezData,FACEZ)
  endif
#endif
  deallocate(xcent)
  deallocate(ycent)
  deallocate(zcent)
  deallocate(randoms)

  return

end subroutine Simulation_initBlock
'''


class ZPinchBlockGenerator:
    """Simulation_initBlock.F90 生成器 (官方 stock 逐字快照)。"""

    def generate(self) -> str:
        """返回文件文本 (与官方 stock 逐字节一致, LF 行尾)。"""
        return ZPINCH_INITBLOCK_F90

    def save(self, output_path) -> Path:
        """写出文件, 返回路径。"""
        p = Path(output_path)
        p.write_text(self.generate(), encoding="utf-8", newline="\n")
        return p
