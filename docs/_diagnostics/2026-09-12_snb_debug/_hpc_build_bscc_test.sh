#!/bin/bash
#SBATCH --job-name=SNB_build_bscc
#SBATCH -p v6_384
#SBATCH -N 1
#SBATCH --ntasks=8
#SBATCH --output=SNB_build_%j_out.txt
#SBATCH --error=SNB_build_%j_err.txt
set -e
# BSCC-T6: 显式用 mpich mpiexec + hdf5/mpich 运行库 (登录无 mpich PATH)
export PATH=/public1/soft/mpich/3.2/bin:$PATH
export H5LIB=$(grep -E '^HDF5_PATH[[:space:]]*=' ~/QC/FLASH/FLASHSNB/FLASH4.8/Makefile.h | head -1 | sed 's/^HDF5_PATH[[:space:]]*=[[:space:]]*//')
[ -n "$H5LIB" ] && export LD_LIBRARY_PATH="$H5LIB/lib:/public1/soft/mpich/3.2/lib:$LD_LIBRARY_PATH"
echo "[env] H5LIB=$H5LIB mpiexec=$(which mpiexec)"
cd ~/QC/FLASH/FLASHSNB/FLASH4.8
echo "=== [1/3] setup ==="
rm -rf SNB_1D_laser_obj
eval ./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=SNB_1D_laser_obj 2>&1 | tail -30
ls -d SNB_1D_laser_obj || { echo SETUP_FAIL; exit 2; }
echo "=== [2/3] mgd_qesh 链接 ==="
cd SNB_1D_laser_obj
ln -sf ../source/Simulation/SimulationMain/SNB_1D_laser/mgd_qesh.F90 mgd_qesh.F90 2>/dev/null || true
echo "=== [3/3] make ==="
make -j8 2>&1 | tail -40
ls -la flash4 && echo BUILD_OK
