#!/bin/bash
#SBATCH -J grad_dens_sandwich
#SBATCH -o grad_dens_sandwich_%%j.out
#SBATCH -e grad_dens_sandwich_%%j.err
#SBATCH -N 1
#SBATCH -n 7
#SBATCH --time=01:00:00

set -e
SIM_NAME="grad_dens_sandwich"
RUN_ID="${2:-000001}"
F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8
S=$F/source/Simulation/SimulationMain/QC/${SIM_NAME}_${RUN_ID}
O=$F/QC/object_${SIM_NAME}_${RUN_ID}
R=/tmp/flash_${SIM_NAME}_$$

mkdir -p "$S"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
mpirun -np 7 ./flash4
echo "=== Output: $R ==="
