#!/bin/bash
#SBATCH --job-name=FLASH_batch
#SBATCH -p v5_192
#SBATCH -N 1
#SBATCH --ntasks=4
#SBATCH --output=FLASH_batch_out.txt
#SBATCH --error=FLASH_batch_err.txt
# Note: SelectType=select/linear → entire node allocated regardless of --ntasks.
# --mem and --ntasks limits are advisory only; the scheduler allocates full nodes.

set -e

# ── Step 1: Load environment ──
echo "[1/6] Loading environment modules..."
module purge
module load mpich/3.2-gcc9.3
module load hdf5/1.8.18

FLASH_HOME="$HOME/QC/FLASH/FLASH4.8"
PAR_FILE="laserslab_custom.par"
OBJ_DIR="QC/LaserSlab_custom"
FLASH_BIN="$FLASH_HOME/$OBJ_DIR/flash4"
SETUP_CMD="./setup -auto QC/LaserSlab_custom -1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=QC/LaserSlab_custom -parfile=laserslab_custom.par"
BUILD_CORES=4
SIM_USER_DIR="QC"
SIM_PATH="QC/LaserSlab_custom"

# Get script directory (uses SLURM_SUBMIT_DIR when submitted via sbatch, PWD as fallback)
SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"

# ── Step 2: Copy source files to SimulationMain ──
echo ""
echo "[2/6] Copying source files to SimulationMain..."
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/$SIM_PATH"
mkdir -p "$SIM_SRC_DIR"
echo "  Simulation source dir: $SIM_SRC_DIR"
# Copy all FLASH setup source files
cp "$SCRIPT_DIR"/Config "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Makefile "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR"/Simulation_*.F90 "$SIM_SRC_DIR"/ 2>/dev/null || true
# Copy data files (.cn4, .par)
cp "$SCRIPT_DIR"/*.cn4 "$SIM_SRC_DIR"/ 2>/dev/null || true
cp "$SCRIPT_DIR/$PAR_FILE" "$SIM_SRC_DIR"/ 2>/dev/null || true
echo "  Source files ready in SimulationMain."

# ── Step 3: Setup + Compile ──
echo ""
echo "[3/6] Checking and compiling FLASH..."
cd "$FLASH_HOME"

if [ -d "$OBJ_DIR" ] && [ -f "$FLASH_BIN" ]; then
    echo "  Binary exists, skipping setup+make."
else
    echo "  Running setup..."
    eval $SETUP_CMD
    echo "  Setup done. Compiling..."
    cd $OBJ_DIR
    make -j$BUILD_CORES
    echo "  Compilation done."
fi

# ── Step 4: Copy input files to run dir ──
echo ""
echo "[4/6] Copying input files..."
cd "$FLASH_HOME/$OBJ_DIR"
cp "$SCRIPT_DIR/$PAR_FILE" ./ 2>/dev/null || echo "  WARNING: par file not in submit dir, using existing"
cp "$SCRIPT_DIR"/*.cn4 ./ 2>/dev/null || true
echo "  Input files ready."

# ── Step 5: Run FLASH ──
echo ""
echo "[5/6] Running FLASH simulation (srun)..."
# TOTAL_TASKS from SLURM (#SBATCH -n), or default to 4 for direct execution
TOTAL_TASKS=${SLURM_NTASKS:-4}
srun -n $TOTAL_TASKS $FLASH_BIN -par_file $PAR_FILE 2>&1 | tee flash_run.log
FLASH_EXIT=${PIPESTATUS[0]}
echo "  FLASH exit code: $FLASH_EXIT"

# ── Step 6: Collect output ──
echo ""
echo "[6/6] Collecting output files..."
OUTPUT_DIR="$SCRIPT_DIR/outputfiles_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"
mv *.h5 *chk* *plt* flash_run.log "$OUTPUT_DIR"/ 2>/dev/null || true

# Summary
echo ""
echo "=== Summary ==="
echo "  Output dir: $OUTPUT_DIR"
nfiles=$(ls "$OUTPUT_DIR"/*.h5 2>/dev/null | wc -l)
echo "  HDF5 files: $nfiles"
echo "  FLASH exit:  $FLASH_EXIT"
echo "=== Done ==="

exit $FLASH_EXIT
