#!/bin/bash
set -e;F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8;S=$F/source/Simulation/SimulationMain/QC/grid_rede;O=$F/QC/object_grid_rede;D=$(dirname "$0");R=/tmp/flash_$(date +%s)
mkdir -p "$S";for f in Config Simulation_data.F90 Simulation_init.F90 Simulation_initBlock.F90 Makefile grid_rede.par *.cn4;do [ -f "$D/$f" ] && cp "$D/$f" "$S/";done
cd $F;rm -rf "$O";./setup -auto QC/grid_rede -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/object_grid_rede;cd $O;make -j$(nproc)
mkdir -p "$R";cp $O/flash4 "$R"/;cp "$S"/*.cn4 "$R"/;cp "$S"/grid_rede.par "$R"/flash.par;cd "$R";mpirun -np 1 ./flash4;echo "Output: $R"
