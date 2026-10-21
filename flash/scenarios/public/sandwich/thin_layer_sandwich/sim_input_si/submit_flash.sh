#!/bin/bash
#SBATCH --job-name=grid_rede --output=grid_rede_%j.log --partition=v5_192 --ntasks=4 --time=01:00:00
F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8;S=$F/source/Simulation/SimulationMain/QC/grid_rede;O=$F/QC/object_grid_rede;D=$(dirname "$0");R=$SLURM_SUBMIT_DIR/${SLURM_JOB_NAME}_run
module load mpi/hpcx/2.17.1 hdf5/1.14.3 python/3.10.8
mkdir -p "$S" "$R";cp "$D"/* "$S"/;cd $F;./setup -auto QC/grid_rede -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/object_grid_rede;cd $O;make -j$(nproc)
cp $O/flash4 "$R"/;cp "$S"/*.cn4 "$R"/;cp "$S"/grid_rede.par "$R"/flash.par;cd "$R";srun ./flash4
