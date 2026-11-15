@echo off
wsl mkdir -p ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede
wsl cp /mnt/%~d0/%~p0*.* ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede/
wsl bash -c "cd ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8 && ./setup -auto QC/grid_rede -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/object_grid_rede"
wsl bash -c "cd ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8/QC/object_grid_rede && make -j$(nproc)"
wsl bash -c "mkdir -p /tmp/run_grid_rede && cp ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8/QC/object_grid_rede/flash4 /tmp/run_grid_rede/ && cp ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede/*.cn4 /tmp/run_grid_rede/ && cp ~/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/grid_rede/grid_rede.par /tmp/run_grid_rede/flash.par && cd /tmp/run_grid_rede && mpirun -np 1 ./flash4"
