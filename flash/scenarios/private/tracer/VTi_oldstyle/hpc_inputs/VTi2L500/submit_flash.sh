#!/bin/bash
#SBATCH --job-name=VTi2L500
#SBATCH -p v5_192
#SBATCH -N 1
#SBATCH --ntasks=7
#SBATCH --output=VTi2L500_out.txt
#SBATCH --error=VTi2L500_err.txt

set -e

echo "[1/6] Loading environment modules..."
module purge
module load mpich/3.2-gcc9.3
module load hdf5/1.8.18
source /public1/soft/oneAPI/2022.1/setvars.sh >/dev/null 2>&1 || true

FLASH_HOME="$HOME/QC/FLASH/FLASH4.8"
PAR_FILE="flash.par"
OBJ_DIR="QC/LaserSlab_VTi2L500"
FLASH_BIN="$FLASH_HOME/$OBJ_DIR/flash4"
SETUP_CMD="./setup -auto QC/LaserSlab_VTi2L500 -1d +cartesian -nxb=16 +hdf5typeio species=cham,targ,shld,samp +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 ed_maxPulseSections=300 -maxblocks=2000 -objdir=QC/LaserSlab_VTi2L500 -parfile=flash.par"
BUILD_CORES=32
SIM_PATH="QC/LaserSlab_VTi2L500"

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"

echo ""
echo "[2/6] Copying source files to SimulationMain..."
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$SIM_PATH"
mkdir -p "$SIM_SRC_DIR"
cp "$SCRIPT_DIR"/Config "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Simulation_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Grid_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/*.cn4 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR/$PAR_FILE" "$SIM_SRC_DIR"/ 2>/dev/null || true
echo "  Source files ready in SimulationMain."

echo ""
echo "[3/6] Checking and compiling FLASH..."
cd "$FLASH_HOME"
if [ -d "$OBJ_DIR" ] && [ -f "$FLASH_BIN" ]; then
    echo "  Binary exists, skipping setup+make."
else
    echo "  No usable binary — wiping stale objdir before setup..."
    rm -rf "$OBJ_DIR"
    echo "  Running setup..."
    eval $SETUP_CMD
    echo "  Setup done. Compiling..."
    cd $OBJ_DIR
    make -j$BUILD_CORES
    echo "  Compilation done."
fi

echo ""
echo "[4/6] Copying input files..."
cd "$FLASH_HOME/$OBJ_DIR"
cp "$SCRIPT_DIR/$PAR_FILE" ./ 2>/dev/null || true
cp "$SCRIPT_DIR"/*.cn4 ./ 2>/dev/null || true
echo "  Input files ready."

echo ""
echo "[5/7] Cleaning stale frames/logs left by any previous run in objdir..."
# ★ 必须清理: 上一轮(含被 scancel 的)会留下 lasslab.log 与半截 chk/plt,
#   末尾的 mv 会把它们和新产物混到一个 outputfiles_* 里, 且轮询步数会读到旧 log。
rm -f lasslab_hdf5_chk_* lasslab_hdf5_plt_cnt_* lasslab_forced_hdf5_plt_cnt_* \
      lasslab*.log lasslab*.h5 flash_run.log 2>/dev/null || true
echo "  objdir cleaned: $(ls lasslab* 2>/dev/null | wc -l) leftover lasslab* files"

echo ""
echo "[6/7] Running FLASH simulation (mpiexec)..."
TOTAL_TASKS=${SLURM_NTASKS:-4}
mpiexec -n $TOTAL_TASKS $FLASH_BIN -par_file $PAR_FILE 2>&1 | tee flash_run.log
FLASH_EXIT=${PIPESTATUS[0]}
echo "  FLASH exit code: $FLASH_EXIT"

echo ""
echo "[7/7] Collecting output files..."
OUTPUT_DIR="$SCRIPT_DIR/outputfiles_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"
mv *.h5 *chk* *plt* flash_run.log "$OUTPUT_DIR"/ 2>/dev/null || true

echo ""
echo "=== Summary ==="
echo "  Output dir: $OUTPUT_DIR"
echo "  HDF5 files: $(ls "$OUTPUT_DIR"/*.h5 2>/dev/null | wc -l)"
echo "  FLASH exit:  $FLASH_EXIT"
echo "=== Done ==="

exit $FLASH_EXIT
