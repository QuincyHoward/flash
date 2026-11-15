"""ZPinch Simulation_adjustEvolution.F90 生成器 —— 官方 stock 逐字快照 (v1 模板)。

职责 (用户约定): 本模块 (gen_sim_adjustevo) 只负责 Simulation_adjustEvolution.F90
的生成; 其他文件分别由 gen_config / gen_makefile / gen_sim_data /
gen_sim_init / gen_sim_initblock 负责; par 由 gen_par/zpinch_par.py 负责。
隔离说明: 独立子包, 与激光系生成器零 import、零共享状态。

源: FLASH4.8 source/Simulation/SimulationMain/magnetoHD/ZPinch (随 Gitee 分发的
官方文件快照; EOS 表 Be/DD-006-imx.cn4 不在此, 随 setup DATAFILES 获取)。
"""

from pathlib import Path

ZPINCH_ADJUST_EVO_F90 = r'''!!****if* source/Simulation/SimulationMain/magnetoHD/SZP/Simulation_adjustEvolution
!!
!! NAME
!!  Simulation_adjustEvolution
!!
!!
!! SYNOPSIS
!!  Simulation_adjustEvolution( integer(IN) :: blkcnt,
!!                              integer(IN) :: blklst(blkcnt),
!!                              integer(IN) :: nstep,
!!                              real(IN) :: dt,
!!                              real(IN) :: stime )
!!
!! DESCRIPTION
!!  This routine is called every cycle. It can be used to adjust
!!  the simulation while it is running.
!!  
!! ARGUMENTS
!!  blkcnt - number of blocks
!!  blklist - block list
!!  nstep - current cycle number
!!  dt - current time step length
!!  stime - current simulation time
!!
!!***
subroutine Simulation_adjustEvolution(blkcnt, blklst, nstep, dt, stime)
  use Simulation_data
  use Driver_data,         ONLY : dr_dtOld
  use Driver_interface,  ONLY : Driver_abortFlash
  use Grid_interface,  ONLY : Grid_getSingleCellVol, Grid_getDeltas, &
                              Grid_getBlkIndexLimits, Grid_getBlkPtr, Grid_fillGuardCells, &
                              Grid_releaseBlkPtr, Grid_getCellCoords, Grid_getSingleCellVol
  use Eos_interface, ONLY: Eos_wrapped
  use MagneticResistivity_data, ONLY: res_vacFrac, res_vacDens
  use rt_data, ONLY : rt_useMGD

#ifdef FLASH_GRID_PARAMESH
  use Grid_interface,   ONLY: Grid_getBlkRefineLevel
#endif

#include "Flash_mpi_implicitNone.fh"

#include "constants.h"
#include "Flash.h"

  integer, intent(in) :: blkcnt
  integer, intent(in) :: blklst(blkcnt)
  integer, intent(in) :: nstep
  real, intent(in) :: dt
  real, intent(in) :: stime

  integer :: blkLimitsGC(LOW:HIGH,MDIM)
  integer :: blkLimits(LOW:HIGH,MDIM)
  integer :: i, j, k, lb, blockID, istat, sizeX, sizeY, sizeZ
  real, pointer, dimension(:,:,:,:) :: U
  real :: delta(MDIM)
  real :: dx, dy
  real, allocatable, dimension(:) :: xCent
  real :: told, tnow, bphi, bx, by, bz, rCent, phi, dr, curr_now
  real :: rEdge, rEdge_blk
  real :: velEdge_blk, velEdge, rInner_blk, rInner, velInner_blk, velInner
  real :: tradActual
  integer :: axis(MDIM)
  logical, save :: firstCall = .TRUE.
  character(len=MAX_STRING_LENGTH) :: fName
  logical :: fExists  
  integer :: fUnit
  integer :: ut_getFreeFileUnit
  integer :: ntimeWrite
  integer, save :: nCount = 0
  integer :: error
  real :: grInner, gvelInner, grEdge, gvelEdge !! global quantities
  real, save :: t1(10)
  real, save :: rInnerOld(10) = 0.2
  real, save :: rEdgeOld(10) = 0.3
  integer :: ii
  logical, save :: nearStagnation = .FALSE.

  integer :: EosMode
  real :: oldTele, oldTion, oldTrad
  logical :: tempChanged

  !! AMR stuff
  integer :: lrefine(blkcnt), prevBlk_lrefine


  told = 0.0
  tnow = stime
  if (tnow > 0.) told = tnow - dr_dtOld
  told = max(0.0,told)

  if (firstCall) then
     rInnerOld(:) = sim_innerRadius
     rEdgeOld(:) = sim_innerRadius + sim_thickness
     do ii = 1, 10
        t1(ii) = told + (ii-1)*1.e-10
     end do
  endif

  !! Initialize rEdge, which is actually found later in first do loops
  rEdge = 0.
  velEdge = 0.
  rInner = 0.
  velInner = 0.

  call Grid_fillGuardCells(CENTER,ALLDIR)

  prevBlk_lrefine = 1
  do lb = 1, blkcnt
     blockID = blklst(lb)

#ifdef FLASH_GRID_PARAMESH
     call Grid_getBlkRefineLevel(blockID,lrefine(lb))
#else
     lrefine(lb) = 1
#endif

     call Grid_getBlkIndexLimits(blockID,blkLimits,blkLimitsGC)
     sizeX = blkLimitsGC(HIGH,IAXIS)

     call Grid_getBlkPtr(blockID, U, CENTER)

     allocate(xCent(sizeX),  stat=istat)
     xCent = 0.0
     call Grid_getCellCoords(IAXIS,blockID, CENTER,    .true., xCent,   sizeX)

     call Grid_getDeltas(blockID, delta)
     dx = delta(IAXIS)
     dy = delta(JAXIS)
     if (sim_geometry == CARTESIAN) then
        dr = sqrt(dx**2+dy**2)
     elseif (sim_geometry == CYLINDRICAL) then
        dr = dx
     end if

     !! Find liner edge and its radial velocity
     !! Note, for a 2D sim, this could be altered to give averages over j
     rEdge_blk = 0.
     velEdge_blk = 0.
     rInner_blk = 0.
     velInner_blk = 0.
     do k = blkLimits(LOW,KAXIS), blkLimits(HIGH,KAXIS)
        do j = blkLimits(LOW,JAXIS), blkLimits(HIGH,JAXIS)
           do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)
              if (U(VACU_SPEC,i,j,k) <= res_vacFrac) then
                 rEdge_blk = xCent(i) + 0.5*dr
                 velEdge_blk = U(VELX_VAR,i,j,k)
              end if
              if (U(FILL_SPEC,i,j,k) > 0.5) then
                 rInner_blk = xCent(i) + 0.5*dr
                 velInner_blk = U(VELX_VAR,i,j,k)
              end if
           end do
        end do
     end do
     if (lrefine(lb) >= prevBlk_lrefine) then
        if (rEdge_blk > rEdge) velEdge = velEdge_blk
        rEdge = max(rEdge_blk,rEdge)
        if (rInner_blk > rInner) velInner = velInner_blk
        rInner = max(rInner_blk,rInner)
     endif

     call Grid_releaseBlkPtr(blockID, U, CENTER)
     deallocate(xCent)
     prevBlk_lrefine = lrefine(lb)
  end do   !! block loop

  call MPI_Reduce (rInner, grInner, 1, FLASH_REAL, MPI_MAX, MASTER_PE, sim_globalComm, error)
  call MPI_AllReduce (rEdge, grEdge, 1, FLASH_REAL, MPI_MAX, sim_globalComm, error)

  !! Output radius and velocity info
  if (sim_globalMe == MASTER_PE) then

     if (grInner <= sim_rNearStag) then 
        if (.not. nearStagnation) then
           !! increase trajectory output frequency
           nearStagnation = .true.
           nCount = floor(tnow/sim_trajOutputIntervalNearStag)
        end if
     else
        if (nearStagnation) then
           !! reset trajectory output frequency
           nearStagnation = .false.
           nCount = floor(tnow/sim_trajOutputInterval)
        end if
     end if

     fName = "trajectory.dat"
     inquire(file=fName, exist=fExists)
     fUnit = ut_getFreeFileUnit()
     open(unit=fUnit, file=fName, position='APPEND')
     if (firstCall) then
        write(fUnit,'(5(a20, 1x))') "#time (ns)", &
                                    "rInner (um)", &
                                    "velInner (um/ns)", &
                                    "rOuter (um)", &
                                    "velOuter (um/ns)"
     else
        if (nearStagnation) then
           ntimeWrite = floor(tnow/sim_trajOutputIntervalNearStag)
        else
           ntimeWrite = floor(tnow/sim_trajOutputInterval)
        end if
        if (ntimeWrite >= nCount) then
           !! Velocities are like moving averages
           !! t1 and 'Old" values used are from 10 output periods ago
           !! In the first 10 periods, velocities calculated are
           !! always zero, which is usually also physically correct.
           if (nCount > 0) then
              gvelInner = (grInner - rInnerOld(1))/(tnow-t1(1))
              gvelEdge = (grEdge - rEdgeOld(1))/(tnow-t1(1))
           else
              gvelInner = 0.0
              gvelEdge = 0.0
           end if
           if (nCount < 10) then
              !! In first 10 output periods, this helps get rid of rounding
              !! errors to keep calculated velocities zero.
              rInnerOld(:) = grInner
              rEdgeOld(:) = grEdge
           else
              do ii = 1, 9
                 rInnerOld(ii) = rInnerOld(ii+1)
                 rEdgeOld(ii) = rEdgeOld(ii+1)
              end do
              rInnerOld(10) = grInner
              rEdgeOld(10) = grEdge
           end if
           do ii = 1, 9
              t1(ii) = t1(ii+1)
           end do
           t1(10) = tnow
           write(fUnit,'(5(es20.13, 1x))') tnow*1.e9, &
                                           grInner*1.e4, &
                                           gvelInner*1.e-5, & 
                                           grEdge*1.e4, &
                                           gvelEdge*1.e-5 
           nCount = nCount + 1
        end if
     end if
     close(fUnit)
  end if


  do lb = 1, blkcnt
     blockID = blklst(lb)

     call Grid_getBlkIndexLimits(blockID,blkLimits,blkLimitsGC)
     call Grid_getBlkPtr(blockID, U, CENTER)

     tempChanged = .false.
 
     do k = blkLimits(LOW,KAXIS), blkLimits(HIGH,KAXIS)
        do j = blkLimits(LOW,JAXIS), blkLimits(HIGH,JAXIS)
           do i = blkLimits(LOW,IAXIS), blkLimits(HIGH,IAXIS)

              ! *************************************************************** !
              ! *           FORCE VACUUM SPECIES AT LOW RHO                   * !
              ! *************************************************************** !
              if (U(LINE_SPEC,i,j,k) >= (1.-res_vacFrac) .and. U(DENS_VAR,i,j,k) <= sim_vacu_dens*(1.-sim_pert)) then
                 U(LINE_SPEC,i,j,k) = sim_smallX
                 U(FILL_SPEC,i,j,k) = sim_smallX
                 U(VACU_SPEC,i,j,k) = 1.0e0-(NSPECIES-1)*sim_smallX
              end if


              ! *************************************************************** !
              ! *                DENSITY FLOOR IN VACUUM                      * !
              ! *************************************************************** !
              if (U(VACU_SPEC,i,j,k) > res_vacFrac .and. U(DENS_VAR,i,j,k) < sim_line_minDens) then
                 U(DENS_VAR,i,j,k) = sim_line_minDens
              end if


              ! *************************************************************** !
              ! *          APPLY FLOOR AND CEILING TO TEMPERATURES            * !
              ! *************************************************************** !
              oldTele = U(TELE_VAR,i,j,k)
              oldTion = U(TION_VAR,i,j,k)
              if (U(VACU_SPEC,i,j,k) > res_vacFrac) then
                 U(TELE_VAR,i,j,k) = min(U(TELE_VAR,i,j,k),sim_vacu_maxTemp)
                 U(TION_VAR,i,j,k) = min(U(TION_VAR,i,j,k),sim_vacu_maxTemp)
                 U(TELE_VAR,i,j,k) = max(U(TELE_VAR,i,j,k),sim_vacu_minTemp)
                 U(TION_VAR,i,j,k) = max(U(TION_VAR,i,j,k),sim_vacu_minTemp)
                 U(TEMP_VAR,i,j,k) = U(TELE_VAR,i,j,k)
              elseif (U(FILL_SPEC,i,j,k) > 0.5) then
                 U(TELE_VAR,i,j,k) = min(U(TELE_VAR,i,j,k),sim_fill_maxTemp)
                 U(TION_VAR,i,j,k) = min(U(TION_VAR,i,j,k),sim_fill_maxTemp)
                 U(TELE_VAR,i,j,k) = max(U(TELE_VAR,i,j,k),sim_fill_minTemp)
                 U(TION_VAR,i,j,k) = max(U(TION_VAR,i,j,k),sim_fill_minTemp)
                 U(TEMP_VAR,i,j,k) = U(TELE_VAR,i,j,k)
              else !! liner
                 U(TELE_VAR,i,j,k) = min(U(TELE_VAR,i,j,k),sim_line_maxTemp)
                 U(TION_VAR,i,j,k) = min(U(TION_VAR,i,j,k),sim_line_maxTemp)
                 U(TELE_VAR,i,j,k) = max(U(TELE_VAR,i,j,k),sim_line_minTemp)
                 U(TION_VAR,i,j,k) = max(U(TION_VAR,i,j,k),sim_line_minTemp)
                 U(TEMP_VAR,i,j,k) = U(TELE_VAR,i,j,k)
              end if
              if (oldTele /= U(TELE_VAR,i,j,k) .or. oldTion /= U(TION_VAR,i,j,k)) tempChanged = .true.

              oldTrad = U(TRAD_VAR,i,j,k)
              if (.not. rt_useMGD) then
                 U(TRAD_VAR,i,j,k) = sim_vacu_tradActual
              else
                 if (U(VACU_SPEC,i,j,k) > res_vacFrac) then
                    U(TRAD_VAR,i,j,k) = sim_vacu_tradActual
                 end if
              end if
              if (oldTrad /= U(TRAD_VAR,i,j,k)) tempChanged = .true.

              !if (U(FILL_SPEC,i,j,k) > 0.5 .and. U(FILL_SPEC,i+1,j,k) < 0.5) then
              !   PRINT*, "fill press. = ", U(PRES_VAR,i,j,k)
              !   PRINT*, "line press. = ", U(PRES_VAR,i+1,j,k)
              !   STOP
              !endif

           end do
        end do
     end do

     !! Call Eos if the temperature has been changed by floor or ceiling
     !! This ensures that the pressures are consistent with the changed temperature
     if (tempChanged) then
        EosMode = MODE_DENS_TEMP_GATHER
        call Eos_wrapped(EosMode, blkLimits, blockID) 
     endif

     call Grid_releaseBlkPtr(blockID, U, CENTER)

  end do   !! block loop


  call Grid_fillGuardCells(CENTER,ALLDIR)

  firstCall = .FALSE.

  return

end subroutine Simulation_adjustEvolution
'''


class SimAdjustEvoGenerator:
    """Simulation_adjustEvolution.F90 生成器 (官方 stock 逐字快照)。"""

    def generate(self) -> str:
        """返回文件文本 (与官方 stock 逐字节一致, LF 行尾)。"""
        return ZPINCH_ADJUST_EVO_F90

    def save(self, output_path) -> Path:
        """写出文件, 返回路径。"""
        p = Path(output_path)
        p.write_text(self.generate(), encoding="utf-8", newline="\n")
        return p
