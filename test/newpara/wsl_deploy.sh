#!/bin/bash
# WSL Deploy Script — NewPara Multi-Zone Test
# 在 WSL 环境中执行完整的 setup → make → run 流程
set -e
set -o pipefail

FLASH_HOME="$HOME/${FLASH_SIM_USER_DIR:-hello}/FLASH/FLASH4.8"
OBJ_DIR="hello/LaserSlab_newpara_test"
SIM_PATH="hello/LaserSlab_newpara_test"
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$SIM_PATH"
FLASH_BIN="$FLASH_HOME/$OBJ_DIR/flash4"
PAR_FILE="laserslab_newpara.par"

echo "=== WSL Deploy: NewPara Multi-Zone Test ==="

echo ""
echo "[Step 1] Setup..."
cd "$FLASH_HOME"
./setup -auto "$SIM_PATH" -1d +cartesian -nxb=16 +hdf5typeio \
    species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
    -objdir="$OBJ_DIR" -parfile="$PAR_FILE" 2>&1 | tail -20
echo "  Setup done."

echo ""
echo "[Step 2] Make..."
cd "$FLASH_HOME/$OBJ_DIR"
make -j4 2>&1 | tail -20
echo "  Make done."

echo ""
echo "[Step 3] Copy EOS + .par..."
cp "$SIM_SRC_DIR"/*.cn4 ./
cp "$SIM_SRC_DIR/$PAR_FILE" ./
echo "  Input files ready."

echo ""
echo "[Step 4] Run FLASH..."
mpirun -np 1 ./flash4 -par_file "$PAR_FILE" 2>&1 | tee flash_run.log
FLASH_EXIT=${PIPESTATUS[0]}
echo "  FLASH exit code: $FLASH_EXIT"

echo ""
echo "=== Output files ==="
ls -la lasslab_hdf5_* 2>/dev/null | head -20
echo ""
echo "=== Done (exit=$FLASH_EXIT) ==="
exit $FLASH_EXIT
