#!/bin/bash
#SBATCH --job-name=grid_rede --output=grid_rede_%j.log --partition=v5_192 --ntasks=4 --time=01:00:00
F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8;S=$F/source/Simulation/SimulationMain/QC/grid_rede;O=$F/QC/object_grid_rede;R=$SLURM_SUBMIT_DIR/${SLURM_JOB_NAME}_run
# ★★ 2026-10-26 实测修复：sbatch 下 `$0` = spool 目录里的脚本副本
#   （/var/spool/slurm/d/jobNNNN/），不是提交目录 ⇒ `dirname "$0"`
#   解析出的路径没有 par/cn4 ⇒ 作业立刻 FAILED
#   （grad_dens_sandwich 实测："cp: cannot stat '.../jobNNNN/*.par'"）。
#   ⇒ 优先 SLURM_SUBMIT_DIR，退回 PWD，最后才用 dirname（直接 bash 场景）。
D=${SLURM_SUBMIT_DIR:-$PWD};_np=$(compgen -G "$D/*.par" | wc -l);[ "$_np" -eq 0 ] && D=$(dirname "$0");echo "  D = $D (par x $(compgen -G "$D/*.par" | wc -l))"
# ★ 模块归一（2026-10-26 实测）：超算上**不存在** mpi/hpcx/2.17.1 与
#   hdf5/1.14.3（"Unable to locate a modulefile"）⇒ 作业必然失败。
#   改用 ch_center 场景已实测通过的 mpich/3.2-gcc9.3 + hdf5/1.8.18。
module load mpich/3.2-gcc9.3 hdf5/1.8.18
mkdir -p "$S" "$R";cp "$D"/* "$S"/;cd $F;./setup -auto QC/grid_rede -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/object_grid_rede;cd $O;make -j$(nproc)
cp $O/flash4 "$R"/;cp "$S"/*.cn4 "$R"/;cp "$S"/grid_rede.par "$R"/flash.par;cd "$R";srun -n ${SLURM_NTASKS:-4} ./flash4
