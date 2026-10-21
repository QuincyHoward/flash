#!/bin/bash
# 本地 WSL 快速运行 (setup + make + mpirun)
set -e
FLASH_HOME="$HOME/QC/FLASH/FLASH4.8"
OBJ_DIR="QC/LaserSlab_VTi1L500"
cd "$FLASH_HOME"
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$OBJ_DIR"
mkdir -p "$SIM_SRC_DIR"
cp Simulation_*.F90 Grid_*.F90 *.cn4 flash.par Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true
[ -d "$OBJ_DIR" ] || ./setup -auto QC/LaserSlab_VTi1L500 -1d +cartesian -nxb=16 +hdf5typeio \
  species=cham,targ,shld,samp +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
  ed_maxPulseSections=300 -maxblocks=2000 -objdir=QC/LaserSlab_VTi1L500 -parfile=flash.par
cd "$OBJ_DIR"
[ -x flash4 ] || make -j8
mpirun -n 1 ./flash4 -par_file flash.par
