#!/bin/bash
# ============================================================
# FLASH 4.8 One-Click Install & LaserSlab 1D Simulation
# ============================================================
# Usage: bash FLASH_one_click_install.sh [PKG_DIR]
#   PKG_DIR: directory containing source tarballs
#            (defaults to script's own directory)
#
# Install FLASH at ~/FLASH/FLASH4.8
# Build MPICH, HDF5, HYPRE from source in src/
# Run LaserSlab 1D simulation and density analysis
#
# All install paths are controlled by variables below.
# ============================================================
set -eo pipefail

# ============================================================
# Configurable Paths (change these to customize)
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PKG_DIR="${1:-${PKG_DIR:-$SCRIPT_DIR}}"

export FLASH_PARENT="${FLASH_PARENT:-$HOME/FLASH}"
export FLASH_HOME="${FLASH_HOME:-$FLASH_PARENT/FLASH4.8}"
export BUILD_DIR="${BUILD_DIR:-$HOME/tmp_flash_build}"

export MPI_PATH="${MPI_PATH:-/usr/local/mpich}"
export HDF5_PATH="${HDF5_PATH:-/usr/local/hdf5}"
export HYPRE_PATH="${HYPRE_PATH:-/usr/local/hypre}"

# Source package names
MPICH_TAR="mpich-3.2.tar.gz"
MPICH_DIR="mpich-3.2"
HDF5_TAR="hdf5-1.8.12.tar.gz"
HDF5_DIR="hdf5-1.8.12"
HYPRE_TAR="hypre-2.9.0b.tar.gz"
HYPRE_DIR="hypre-2.9.0b"
FLASH_TAR="FLASH4.8.tar.gz"

NPROC="${NPROC:-$(nproc)}"

# ============================================================
# Privilege detection
# ============================================================
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

# ============================================================
# Environment refresh (update PATH & libs for current session)
# ============================================================
refresh_env() {
    export MPI_HOME="$MPI_PATH"
    export PATH="$MPI_PATH/bin:$HDF5_PATH/bin:$PATH"
    export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${LD_LIBRARY_PATH:-}"
    export HDF5_HOME="$HDF5_PATH"
    export HDF5_ROOT="$HDF5_PATH"
    export HYPRE_HOME="$HYPRE_PATH"
}

# ============================================================
# Append env vars to ~/.bashrc (idempotent)
# ============================================================
write_bashrc() {
    local mark="# >>> FLASH env (auto-generated) <<<"
    # Remove old FLASH block if present
    if grep -q "FLASH env (auto-generated)" "$HOME/.bashrc" 2>/dev/null; then
        sed -i "/# >>> FLASH env/,/# <<< FLASH env/d" "$HOME/.bashrc"
    fi
    cat >> "$HOME/.bashrc" << BEOF
${mark}
export MPI_HOME=${MPI_PATH}
export HDF5_HOME=${HDF5_PATH}
export HDF5_ROOT=${HDF5_PATH}
export HYPRE_HOME=${HYPRE_PATH}
export PATH=\$MPI_HOME/bin:\$HDF5_HOME/bin:\$PATH
export LD_LIBRARY_PATH=\$MPI_HOME/lib:\$HDF5_HOME/lib:\$HYPRE_HOME/lib:\$LD_LIBRARY_PATH
# <<< FLASH env
BEOF
    echo "  ~/.bashrc updated with FLASH environment variables"
}

# ============================================================
# Idempotency checks
# ============================================================
is_mpich_ok()   { [ -x "$MPI_PATH/bin/mpicc" ]; }
is_hdf5_ok()    { [ -f "$HDF5_PATH/lib/libhdf5.a" ] || [ -f "$HDF5_PATH/lib/libhdf5.so" ]; }
is_hypre_ok()   { ls "$HYPRE_PATH/lib/libHYPRE"* &>/dev/null; }
is_flash_setup(){ [ -f "$FLASH_HOME/Makefile.h" ]; }
is_flash_built(){ [ -f "$FLASH_HOME/object/flash4" ]; }
is_sim_done()   { ls "$FLASH_HOME/run_laserslab/"*hdf5_chk_* &>/dev/null; }

# ============================================================
# Banner
# ============================================================
START_TIME=$(date +%s)
echo "============================================"
echo "  FLASH 4.8 — One-Click Install & 1D Test"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo "Package dir:  $PKG_DIR"
echo "Build dir:    $BUILD_DIR"
echo "FLASH home:   $FLASH_HOME"
echo "MPI path:     $MPI_PATH"
echo "HDF5 path:    $HDF5_PATH"
echo "HYPRE path:   $HYPRE_PATH"
echo "CPU cores:    $NPROC"
echo "User:         $(whoami) (uid=$(id -u))"
echo ""

# ============================================================
# Step 0 — System dependencies
# ============================================================
step0_deps() {
    echo "========================================"
    echo "  [0/8] System dependencies"
    echo "========================================"

    $SUDO apt-get update -y -qq 2>&1 | tail -1

    echo "Installing compilers & libraries..."
    $SUDO apt-get install -y -qq \
        gcc g++ gfortran \
        gcc-9 g++-9 gfortran-9 \
        make \
        python3 python3-pip python-is-python3 \
        zlib1g-dev \
        libopenblas-dev liblapack-dev liblapacke-dev \
        wget \
        2>&1 | tail -5

    # Set gcc-9 as default (required for MPICH 3.2 compatibility)
    $SUDO update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 50 2>/dev/null || true
    $SUDO update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 50 2>/dev/null || true
    $SUDO update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-9 50 2>/dev/null || true
    $SUDO update-alternatives --set gcc /usr/bin/gcc-9 2>/dev/null || true
    $SUDO update-alternatives --set g++ /usr/bin/g++-9 2>/dev/null || true
    $SUDO update-alternatives --set gfortran /usr/bin/gfortran-9 2>/dev/null || true

    # Ensure bare 'python' exists
    if ! command -v python &>/dev/null; then
        $SUDO ln -sf "$(command -v python3)" /usr/local/bin/python 2>/dev/null || true
    fi

    echo "gcc:       $(gcc --version 2>/dev/null | head -1)"
    echo "g++:       $(g++ --version 2>/dev/null | head -1)"
    echo "gfortran:  $(gfortran --version 2>/dev/null | head -1)"
    echo ""
}

# ============================================================
# Step 1 — Copy source packages to build dir
# ============================================================
step1_prepare() {
    echo "========================================"
    echo "  [1/8] Prepare source packages"
    echo "========================================"
    mkdir -p "$BUILD_DIR"

    local missing=0
    for pkg in "$MPICH_TAR" "$HDF5_TAR" "$HYPRE_TAR" "$FLASH_TAR"; do
        if [ -f "$PKG_DIR/$pkg" ]; then
            cp "$PKG_DIR/$pkg" "$BUILD_DIR/"
            echo "  OK  $pkg  ($(du -sh "$PKG_DIR/$pkg" | cut -f1))"
        else
            echo "  MISSING: $PKG_DIR/$pkg"
            missing=1
        fi
    done

    if [ "$missing" -eq 1 ]; then
        echo ""
        echo "ERROR: Missing source packages in $PKG_DIR"
        echo "Required: mpich-3.2.tar.gz, hdf5-1.8.12.tar.gz,"
        echo "          hypre-2.9.0b.tar.gz, FLASH4.8.tar.gz"
        exit 1
    fi
    echo ""
}

# ============================================================
# Step 2 — Build MPICH 3.2
# ============================================================
step2_mpich() {
    echo "========================================"
    echo "  [2/8] Build MPICH 3.2"
    echo "========================================"
    if is_mpich_ok; then
        echo "  SKIP: already installed at $MPI_PATH"
        refresh_env
        return 0
    fi

    cd "$BUILD_DIR"
    rm -rf "$MPICH_DIR"
    tar -xzf "$MPICH_TAR"
    cd "$MPICH_DIR"

    echo "Configure MPICH (gcc-9 for ABI compatibility)..."
    ./configure --prefix="$MPI_PATH" \
        CC=gcc-9 CXX=g++-9 FC=gfortran-9 F77=gfortran-9 \
        2>&1 | tail -3

    echo "Build MPICH ($NPROC cores)..."
    make -j"$NPROC" 2>&1 | tail -3

    echo "Install MPICH..."
    $SUDO make install 2>&1 | tail -3

    refresh_env
    echo "MPICH: $(mpicc --version 2>&1 | head -1)"
    echo ""
}

# ============================================================
# Step 3 — Build HDF5 1.8.12 (parallel + Fortran)
# ============================================================
step3_hdf5() {
    echo "========================================"
    echo "  [3/8] Build HDF5 1.8.12"
    echo "========================================"
    if is_hdf5_ok; then
        echo "  SKIP: already installed at $HDF5_PATH"
        refresh_env
        return 0
    fi

    cd "$BUILD_DIR"
    rm -rf "$HDF5_DIR"
    tar -xzf "$HDF5_TAR"
    cd "$HDF5_DIR"

    # HDF5 configure needs bare 'gfortran' (not mpif90)
    if ! command -v gfortran &>/dev/null; then
        local gf
        gf=$(which gfortran-9 2>/dev/null || which gfortran-11 2>/dev/null || echo "")
        if [ -n "$gf" ]; then
            $SUDO ln -sf "$gf" /usr/local/bin/gfortran 2>/dev/null || true
        fi
    fi

    local MPI_INC="-I$MPI_PATH/include"
    local MPI_LIB="-L$MPI_PATH/lib"

    echo "Configure HDF5 (parallel + Fortran)..."
    # Key: FC=gfortran (bare), inject MPI via FCFLAGS/FFLAGS/LIBS
    ./configure --prefix="$HDF5_PATH" \
        --enable-parallel \
        --enable-fortran \
        CC=mpicc FC=gfortran F77=gfortran \
        FCFLAGS="$MPI_INC" FFLAGS="$MPI_INC" \
        LIBS="$MPI_LIB -lmpi -lmpifort" \
        2>&1 | tail -3

    echo "Build HDF5 ($NPROC cores)..."
    make -j"$NPROC" 2>&1 | tail -3

    echo "Install HDF5..."
    $SUDO make install 2>&1 | tail -3

    refresh_env
    echo "HDF5 installed at $HDF5_PATH"
    echo ""
}

# ============================================================
# Step 4 — Build HYPRE 2.9.0b
# ============================================================
step4_hypre() {
    echo "========================================"
    echo "  [4/8] Build HYPRE 2.9.0b"
    echo "========================================"
    if is_hypre_ok; then
        echo "  SKIP: already installed at $HYPRE_PATH"
        refresh_env
        return 0
    fi

    cd "$BUILD_DIR"
    rm -rf "$HYPRE_DIR"
    tar -xzf "$HYPRE_TAR"
    cd "$HYPRE_DIR/src"

    echo "Configure HYPRE..."
    ./configure --prefix="$HYPRE_PATH" \
        CC=mpicc CXX=mpicxx FC=gfortran-9 F77=gfortran-9 \
        2>&1 | tail -3

    echo "Build HYPRE ($NPROC cores)..."
    make -j"$NPROC" 2>&1 | tail -3

    echo "Install HYPRE..."
    $SUDO make install 2>&1 | tail -3

    refresh_env
    echo "HYPRE installed at $HYPRE_PATH"
    echo ""
}

# ============================================================
# Step 5 — Install FLASH 4.8 + configure Makefile.h
# ============================================================
step5_flash_install() {
    echo "========================================"
    echo "  [5/8] Install FLASH 4.8 + Makefile.h"
    echo "========================================"
    if is_flash_setup; then
        echo "  SKIP: FLASH already unpacked & configured"
        refresh_env
        return 0
    fi

    # Unpack FLASH to ~/FLASH/FLASH4.8
    mkdir -p "$FLASH_PARENT"
    cd "$FLASH_PARENT"
    rm -rf "$FLASH_HOME"
    echo "Unpacking FLASH 4.8..."
    tar -xzf "$BUILD_DIR/$FLASH_TAR"

    # Copy Makefile.h template
    local template="$FLASH_HOME/sites/Prototypes/Linux/Makefile.h"
    if [ ! -f "$template" ]; then
        echo "ERROR: Makefile.h template not found: $template"
        exit 1
    fi
    cp "$template" "$FLASH_HOME/Makefile.h"
    echo "Makefile.h copied from template."

    # Update paths
    sed -i "s|^MPI_PATH\s*=.*|MPI_PATH = $MPI_PATH|"   "$FLASH_HOME/Makefile.h"
    sed -i "s|^HDF5_PATH\s*=.*|HDF5_PATH = $HDF5_PATH|"  "$FLASH_HOME/Makefile.h"
    sed -i "s|^HYPRE_PATH\s*=.*|HYPRE_PATH = $HYPRE_PATH|" "$FLASH_HOME/Makefile.h"
    echo "  MPI_PATH  => $MPI_PATH"
    echo "  HDF5_PATH => $HDF5_PATH"
    echo "  HYPRE_PATH => $HYPRE_PATH"

    # Add LIB_LAPACK
    if ! grep -q "^LIB_LAPACK" "$FLASH_HOME/Makefile.h"; then
        sed -i "/^HYPRE_PATH/a LIB_LAPACK = -llapack -lblas -lgfortran" "$FLASH_HOME/Makefile.h"
        echo "  + LIB_LAPACK = -llapack -lblas -lgfortran"
    fi

    # Comment out FLASHBINARY ifeq block
    local sl
    sl=$(grep -n "FLASHBINARY" "$FLASH_HOME/Makefile.h" 2>/dev/null | head -1 | cut -d: -f1) || true
    if [ -n "$sl" ]; then
        local el
        el=$(tail -n +"$sl" "$FLASH_HOME/Makefile.h" | grep -n "^endif" 2>/dev/null | head -1 | cut -d: -f1) || true
        if [ -n "$el" ]; then
            el=$((sl + el - 1))
            sed -i "${sl},${el}s/^/#/" "$FLASH_HOME/Makefile.h"
            echo "  FLASHBINARY ifeq commented (lines $sl-$el)"
        fi
    fi

    refresh_env
    echo ""
    echo "--- Makefile.h key settings ---"
    grep -E "^(MPI_PATH|HDF5_PATH|HDF4_PATH|HYPRE_PATH|LIB_LAPACK)" "$FLASH_HOME/Makefile.h" 2>/dev/null || true
    echo "-------------------------------"
    echo ""
}

# ============================================================
# Step 6 — Compile FLASH (LaserSlab 1D)
# ============================================================
step6_flash_compile() {
    echo "========================================"
    echo "  [6/8] Compile FLASH (LaserSlab 1D)"
    echo "========================================"
    if is_flash_built; then
        echo "  SKIP: FLASH already compiled ($(du -sh "$FLASH_HOME/object/flash4" | cut -f1))"
        refresh_env
        return 0
    fi

    cd "$FLASH_HOME"
    rm -rf object/

    echo "FLASH setup (LaserSlab 1D)..."
    ./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio \
        species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=object -parfile=example1d.par 2>&1 | tail -10

    echo ""
    echo "Compiling FLASH ($NPROC cores)..."
    cd object/
    make -j"$NPROC" 2>&1 | tail -5

    if [ -f flash4 ]; then
        echo ""
        echo "FLASH compiled successfully! ($(du -sh flash4 | cut -f1))"
    else
        echo ""
        echo "ERROR: FLASH compilation failed!"
        exit 1
    fi
    echo ""
}

# ============================================================
# Step 7 — Run LaserSlab 1D simulation
# ============================================================
step7_run_sim() {
    echo "========================================"
    echo "  [7/8] Run LaserSlab 1D simulation"
    echo "========================================"
    if is_sim_done; then
        local cnt
        cnt=$(ls "$FLASH_HOME/run_laserslab/"*hdf5_chk_* 2>/dev/null | wc -l)
        echo "  SKIP: simulation already done ($cnt checkpoint files)"
        return 0
    fi

    local SIM_DIR="$FLASH_HOME/source/Simulation/SimulationMain/LaserSlab"
    local RUN_DIR="$FLASH_HOME/run_laserslab"

    rm -rf "$RUN_DIR"
    mkdir -p "$RUN_DIR"
    cd "$RUN_DIR"

    # Copy EOS tables
    echo "Copying EOS tables..."
    cp "$SIM_DIR/al-imx-003.cn4" "$RUN_DIR/" 2>/dev/null && echo "  + al-imx-003.cn4" || true
    cp "$SIM_DIR/he-imx-005.cn4" "$RUN_DIR/" 2>/dev/null && echo "  + he-imx-005.cn4" || true

    # Copy .par file (use existing, do NOT generate)
    if [ -f "$SIM_DIR/example1d.par" ]; then
        cp "$SIM_DIR/example1d.par" "$RUN_DIR/flash.par"
        echo "  + flash.par"
    else
        echo "ERROR: example1d.par not found in $SIM_DIR"
        exit 1
    fi

    echo ""
    echo "Launching FLASH (mpirun -np 1)..."
    "$MPI_PATH/bin/mpirun" -np 1 "$FLASH_HOME/object/flash4" 2>&1 | \
        tee flash_output.log | \
        grep -E "(Wrote|Step|completed|exiting|ERROR|SUCCESS|tmax|nend)" || true

    # Verify output
    local chk_cnt
    chk_cnt=$(ls *hdf5_chk_* 2>/dev/null | wc -l)
    if [ "$chk_cnt" -gt 0 ]; then
        echo ""
        echo "SUCCESS: $chk_cnt checkpoint file(s) generated"
        ls -lh *hdf5_chk_* 2>/dev/null
    else
        echo ""
        echo "WARNING: No checkpoint files. Check flash_output.log"
    fi
    echo ""
}

# ============================================================
# Step 8 — Density analysis & plot (embedded Python)
# ============================================================
step8_analyze() {
    echo "========================================"
    echo "  [8/8] Density analysis & plot"
    echo "========================================"

    local RUN_DIR="$FLASH_HOME/run_laserslab"
    local OUT_DIR="$FLASH_HOME/analysis_output"
    rm -rf "$OUT_DIR"
    mkdir -p "$OUT_DIR"

    # Install Python deps
    echo "Installing h5py, numpy, matplotlib..."
    python3 -m pip install --quiet h5py numpy matplotlib 2>&1 | tail -3 || \
        $SUDO pip3 install --quiet h5py numpy matplotlib 2>&1 | tail -3 || true

    python3 << 'PYEOF'
import os, sys, glob, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import h5py

warnings.filterwarnings("ignore")

RUN_DIR = os.path.expanduser("~/FLASH/FLASH4.8/run_laserslab")
OUT_DIR = os.path.expanduser("~/FLASH/FLASH4.8/analysis_output")
os.makedirs(OUT_DIR, exist_ok=True)

chk_files = sorted(glob.glob(os.path.join(RUN_DIR, "*hdf5_chk_*")))
if not chk_files:
    chk_files = sorted(glob.glob(os.path.join(RUN_DIR, "*chk*")))
if not chk_files:
    print("ERROR: No checkpoint files found in", RUN_DIR)
    sys.exit(1)

print(f"Found {len(chk_files)} checkpoint files")

all_data = []
for fp in chk_files:
    try:
        with h5py.File(fp, "r") as f:
            t = float(f["real scalars"]["value"][0])
            ns = int(f["integer scalars"]["value"][0])
            nt = f["node type"][:]
            bb = f["bounding box"][:]

            if "dens" in f:
                dd = f["dens"][:]
            else:
                matches = [k for k in f.keys() if "dens" in k.lower() and isinstance(f[k], h5py.Dataset)]
                if not matches:
                    continue
                dd = f[matches[0]][:]

            nxb = dd.shape[-1]
            xa, da = [], []
            for ib in range(len(nt)):
                if nt[ib] != 1:
                    continue
                xmn, xmx = float(bb[ib,0,0]), float(bb[ib,0,1])
                dx = (xmx-xmn)/nxb
                xc = np.linspace(xmn+dx/2, xmx-dx/2, nxb)
                xa.append(xc)
                da.append(dd[ib,0,0,:])
            if not xa:
                continue
            x = np.concatenate(xa)
            d = np.concatenate(da)
            si = np.argsort(x)
            all_data.append({"time":t,"nstep":ns,"x":x[si],"dens":d[si]})
            print(f"  {os.path.basename(fp)}: t={t*1e12:.3f}ps  nstep={ns}  cells={len(x)}")
    except Exception as e:
        print(f"  {os.path.basename(fp)}: ERROR - {e}")

all_data.sort(key=lambda d: d["time"])
print(f"\nExtracted {len(all_data)} time steps")
if not all_data:
    sys.exit(0)

# Plot 1: Density vs x (all time steps)
fig1, ax1 = plt.subplots(figsize=(14,7))
times = np.array([d["time"] for d in all_data])
norm = plt.Normalize(times.min(), times.max())
for d in all_data:
    ax1.plot(d["x"]*1e6, d["dens"], color=plt.cm.viridis(norm(d["time"])), lw=0.8, alpha=0.85)
ax1.set_xlabel("x (um)", fontsize=13)
ax1.set_ylabel("density (g/cm^3)", fontsize=13)
ax1.set_title(f"FLASH 1D LaserSlab - Density vs x ({len(all_data)} snapshots)", fontsize=14)
ax1.set_yscale("log")
ax1.grid(True, alpha=0.3, ls="--")
sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=norm)
sm.set_array([])
fig1.colorbar(sm, ax=ax1, aspect=50, pad=0.02).set_label("Time (s)", fontsize=11)
p1 = os.path.join(OUT_DIR, "density_vs_x_evolution.png")
fig1.savefig(p1, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig1)
print(f"  Saved: {os.path.basename(p1)}")

# Plot 2: x-t heatmap + statistics
fig2, (ax2a, ax2b) = plt.subplots(1,2, figsize=(16,6))
if len(all_data) >= 2:
    xr = all_data[0]["x"]
    dm = np.zeros((len(all_data), len(xr)))
    for i,d in enumerate(all_data):
        dm[i,:] = np.interp(xr, d["x"], d["dens"])
    xx,tt = np.meshgrid(xr*1e6, times*1e12)
    im = ax2a.pcolormesh(xx, tt, np.log10(np.maximum(dm, 1e-30)), shading="auto", cmap="inferno")
    ax2a.set_xlabel("x (um)"); ax2a.set_ylabel("Time (ps)")
    ax2a.set_title("log10(density) x-t spectrum")
    fig2.colorbar(im, ax=ax2a)

mx = [d["dens"].max() for d in all_data]
mn = [d["dens"].mean() for d in all_data]
ax2b.plot(times*1e12, mx, "o-", color="#E74C3C", lw=1.2, ms=4, label="max(density)")
ax2b.plot(times*1e12, mn, "s-", color="#3498DB", lw=1.2, ms=4, label="mean(density)")
ax2b.set_xlabel("Time (ps)"); ax2b.set_ylabel("density (g/cm^3)")
ax2b.set_title("Density statistics vs time")
ax2b.set_yscale("log"); ax2b.legend(); ax2b.grid(True, alpha=0.3, ls="--")
p2 = os.path.join(OUT_DIR, "density_heatmap_and_stats.png")
fig2.savefig(p2, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig2)
print(f"  Saved: {os.path.basename(p2)}")

# Plot 3: First / Middle / Last snapshots
fig3, ax3 = plt.subplots(figsize=(12,7))
colors = ["#3498DB","#F39C12","#E74C3C"]
N = len(all_data)
for idx,c in zip([0, N//2, N-1], colors):
    d = all_data[idx]
    ax3.plot(d["x"]*1e6, d["dens"], color=c, lw=1.5, label=f"t={d['time']*1e12:.1f}ps (step {d['nstep']})")
ax3.set_xlabel("x (um)"); ax3.set_ylabel("density (g/cm^3)")
ax3.set_title("FLASH 1D LaserSlab - First / Middle / Last")
ax3.set_yscale("log"); ax3.legend(); ax3.grid(True, alpha=0.3, ls="--")
p3 = os.path.join(OUT_DIR, "density_snapshots.png")
fig3.savefig(p3, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig3)
print(f"  Saved: {os.path.basename(p3)}")

t_span = all_data[-1]["time"] - all_data[0]["time"]
print(f"\n{'='*60}")
print(f"  Analysis complete!")
print(f"  Time: {all_data[0]['time']*1e12:.3f} ~ {all_data[-1]['time']*1e12:.3f} ps")
print(f"  Span: {t_span*1e12:.3f} ps  |  Snapshots: {len(all_data)}")
print(f"{'='*60}")
PYEOF

    echo ""
    echo "Generated images:"
    ls -lh "$OUT_DIR/"*.png 2>/dev/null || echo "  (no PNG files)"
    echo ""
}

# ============================================================
# Summary
# ============================================================
print_summary() {
    local elapsed=$(($(date +%s) - START_TIME))
    local h=$((elapsed/3600))
    local m=$(((elapsed%3600)/60))
    local s=$((elapsed%60))
    echo "============================================"
    echo "  FLASH One-Click Install — DONE!"
    echo "  Time:  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Total: ${h}h ${m}m ${s}s"
    echo "============================================"
    echo "  FLASH:        $FLASH_HOME"
    echo "  Simulation:   $FLASH_HOME/run_laserslab/"
    echo "  PNG plots:    $FLASH_HOME/analysis_output/"
    echo "  MPI:          $MPI_PATH"
    echo "  HDF5:         $HDF5_PATH"
    echo "  HYPRE:        $HYPRE_PATH"
    echo "============================================"
}

# ============================================================
# Main
# ============================================================
main() {
    step0_deps
    step1_prepare
    step2_mpich
    step3_hdf5
    step4_hypre
    step5_flash_install
    write_bashrc
    step6_flash_compile
    step7_run_sim
    step8_analyze
    print_summary
}

main
