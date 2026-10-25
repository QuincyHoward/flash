#!/bin/bash
#SBATCH --job-name=grid_rede --output=grid_rede_%j.log --partition=v5_192 --ntasks=4 --time=01:00:00
F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8;S=$F/source/Simulation/SimulationMain/QC/grid_rede;O=$F/QC/object_grid_rede;R=$SLURM_SUBMIT_DIR/${SLURM_JOB_NAME}_run
# ★★ 2026-10-26 实测修复：sbatch 下 `$0` = spool 目录里的脚本副本
#   （/var/spool/slurm/d/jobNNNN/），不是提交目录 ⇒ `dirname "$0"`
#   解析出的路径没有 par/cn4 ⇒ 作业立刻 FAILED
#   （grad_dens_sandwich 实测："cp: cannot stat '.../jobNNNN/*.par'"）。
#   ⇒ 优先 SLURM_SUBMIT_DIR，退回 PWD，最后才用 dirname（直接 bash 场景）。
D=${SLURM_SUBMIT_DIR:-$PWD};_np=$(compgen -G "$D/*.par" | wc -l);[ "$_np" -eq 0 ] && D=$(dirname "$0");echo "  D = $D (par x $(compgen -G "$D/*.par" | wc -l))"
# ★★ 2026-10-26 实测修复（链接失败 'ld: cannot find -lmpifort/-lmpi'）：
#   根因 = **任何 `module load` 都会污染 ifort/mpiifort 的隐式 MPI 库路径**
#   （module 设的 LIBRARY_PATH/CPATH 指向旧 Intel 2018 环境，屏蔽了
#     oneAPI 2022.1 自带的 libmpifort）⇒ 链接必 FAIL。
#   实测对照（超算）：无 module ⇒ OK；load mpich ⇒ FAIL；
#     load hdf5/1.8.18 ⇒ FAIL（连显式 -L 都救不回）。
#   ★ FLASH 的 Makefile.h 已**硬编码**绝对路径（LINK=.../mpiifort、
#     -I/public1/soft/hdf5/1.8.18/include）⇒ 本就不需要任何 module。
#   ⇒ 解法：不加载 module，改用绝对路径 + 显式 LIBRARY_PATH/LD_LIBRARY_PATH。
MPIIFORT_DIR=/public1/soft/oneAPI/2022.1/mpi/latest/bin
IMPI_LIB=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release
IMPI_LIB2=/public1/soft/oneAPI/2022.1/mpi/latest/lib
HDF5_LIB=/public1/soft/hdf5/1.8.18/lib
export PATH="$MPIIFORT_DIR:$PATH"
export LIBRARY_PATH="$IMPI_LIB:$IMPI_LIB2:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="$IMPI_LIB:$IMPI_LIB2:$HDF5_LIB:${LD_LIBRARY_PATH:-}"
mkdir -p "$S" "$R";cp "$D"/* "$S"/;cd $F;./setup -auto QC/grid_rede -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/object_grid_rede;cd $O;make -j$(nproc)
cp $O/flash4 "$R"/;cp "$S"/*.cn4 "$R"/;cp "$S"/grid_rede.par "$R"/flash.par;cd "$R";srun -n ${SLURM_NTASKS:-4} ./flash4
