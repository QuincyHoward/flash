#!/bin/bash
# run_flash.sh — GradDensSandwich WSL 自动编译运行脚本
set -e

SIM_NAME="grad_dens_sandwich"
RUN_ID="${2:-000001}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASH_HOME="${FLASH_HOME:-$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8}"
SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/QC/${SIM_NAME}_${RUN_ID}"
OBJ_DIR="$FLASH_HOME/QC/object_${SIM_NAME}_${RUN_ID}"
RUN_DIR="/tmp/flash_${SIM_NAME}_${RUN_ID}"

echo "=== 清理旧目录 ==="
rm -rf "$SRC_DIR" "$OBJ_DIR"
mkdir -p "$SRC_DIR"

echo "=== 复制源文件 ==="
cp "$SCRIPT_DIR"/*.F90 "$SRC_DIR/"
cp "$SCRIPT_DIR"/Config "$SRC_DIR/"
cp "$SCRIPT_DIR"/Makefile "$SRC_DIR/"
cp "$SCRIPT_DIR"/*.cn4 "$SRC_DIR/"
cp "$SCRIPT_DIR"/*.par "$SRC_DIR/${SIM_NAME}_${RUN_ID}.par"

echo "=== setup ==="
cd "$FLASH_HOME"
./setup -auto "QC/${SIM_NAME}_${RUN_ID}" -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 ed_maxPulseSections=240 -objdir="QC/object_${SIM_NAME}_${RUN_ID}" 2>&1

echo "=== make ==="
cd "$OBJ_DIR"
make -j7 2>&1

echo "=== 运行 ==="
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR"
cp "$OBJ_DIR"/flash4 "$RUN_DIR/"
cp "$SRC_DIR"/*.cn4 "$RUN_DIR/"
cp "$SRC_DIR/${SIM_NAME}_${RUN_ID}.par" "$RUN_DIR/flash.par"
touch "$RUN_DIR/lasslab.dat"
cd "$RUN_DIR"
echo "Start: $(date)"
timeout 900 mpirun -np 7 ./flash4 2>&1 || echo "EXIT_CODE=$?"
echo "End: $(date)"
echo "=== HDF5 ==="
ls -lh "$RUN_DIR"/lasslab_hdf5_chk_* 2>/dev/null | wc -l
