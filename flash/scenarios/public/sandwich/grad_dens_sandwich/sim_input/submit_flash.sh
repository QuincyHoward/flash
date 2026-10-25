#!/bin/bash
#SBATCH -J grad_dens_sandwich
#SBATCH -o grad_dens_sandwich_%j.out
#SBATCH -e grad_dens_sandwich_%j.err
#SBATCH -N 1
#SBATCH -n 7
#SBATCH --time=01:00:00

set -e
SIM_NAME="grad_dens_sandwich"
RUN_ID="${2:-000001}"
# ★ 模块加载（2026-10-26 补）：原脚本**不加载任何 module** ⇒ 编译/运行
#   缺 MPI 与 HDF5 环境（上次作业在更早的 par 拷贝处就 FAILED，尚未暴露）。
#   归一到 ch_center 场景已实测通过的组合。
module purge >/dev/null 2>&1
module load mpich/3.2-gcc9.3
module load hdf5/1.8.18
F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8
S=$F/source/Simulation/SimulationMain/QC/${SIM_NAME}_${RUN_ID}
O=$F/QC/object_${SIM_NAME}_${RUN_ID}
R=/tmp/flash_${SIM_NAME}_$$

mkdir -p "$S"
# ★★ 2026-10-26 实测修复：sbatch 下 `$0` = spool 目录里的脚本副本
#   （/var/spool/slurm/d/jobNNNN/），**不是**提交目录 ⇒ `dirname "$0"`
#   解析出的路径里没有 par/cn4 ⇒ 作业立刻 FAILED：
#     "cp: cannot stat '/var/spool/slurm/d/job4924446/*.par': No such file"
#   ⇒ 优先用 SLURM_SUBMIT_DIR（提交时的 cwd），退回 PWD；
#     两者都不含 par 时才用 dirname（直接 bash 执行的场景）。
#   ★ glob 在 [ ] 内不展开 ⇒ 用 compgen 计数做判据。
SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
_n_par=$(compgen -G "$SCRIPT_DIR/*.par" | wc -l)
if [ "$_n_par" -eq 0 ]; then
    echo "  SCRIPT_DIR 无 par 文件，回退 dirname \$0"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
echo "  SCRIPT_DIR = $SCRIPT_DIR (par x $(compgen -G "$SCRIPT_DIR/*.par" | wc -l))"
for f in Config Simulation_data.F90 Simulation_init.F90 Simulation_initBlock.F90 Grid_markRefineDerefine.F90 Makefile *.cn4; do
    [ -f "$SCRIPT_DIR/$f" ] && cp "$SCRIPT_DIR/$f" "$S/"
done
cp "$SCRIPT_DIR"/*.par "$S/${SIM_NAME}_${RUN_ID}.par"

cd $F
rm -rf "$O"
./setup -auto "QC/${SIM_NAME}_${RUN_ID}" -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 ed_maxPulseSections=240 -objdir="QC/object_${SIM_NAME}_${RUN_ID}"
cd $O
make -j7

mkdir -p "$R"
cp $O/flash4 "$R/"
cp "$S"/*.cn4 "$R/"
cp "$S/${SIM_NAME}_${RUN_ID}.par" "$R"/flash.par
cd "$R"
# ★ 用 srun 而非 mpirun（2026-10-26 归一）：SLURM 作业内用 mpirun 会与
#   SLURM 的进程分配打架（ch_center 场景已实测 srun 路径可用）。
srun -n ${SLURM_NTASKS:-7} ./flash4
echo "=== Output: $R ==="
