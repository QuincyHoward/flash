#!/bin/bash
# 编译 FLASH LaserSlab 1D
set -e

# 用户名解析: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
# 用户名必须通过 flash._core.credentials 设置, 请勿硬编码
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/flash_user_lib.sh"
FLASH_SIM_USER_DIR="${FLASH_SIM_USER_DIR:-$(resolve_flash_user)}"
FLASH_HOME="$HOME/$FLASH_SIM_USER_DIR/FLASH/FLASH4.8"
MPI_PATH=/usr/local/mpich
HDF5_PATH=/usr/local/hdf5
HYPRE_PATH=/usr/local/hypre

# 设置环境变量
export MPI_HOME="$MPI_PATH"
export HDF5_HOME="$HDF5_PATH"
export HDF5_ROOT="$HDF5_PATH"
export HYPRE_HOME="$HYPRE_PATH"
export PATH="$MPI_PATH/bin:$HDF5_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${LD_LIBRARY_PATH:-}"

echo "=== Step 6: 编译 FLASH LaserSlab 1D ==="
echo "FLASH_HOME: $FLASH_HOME"
echo "mpicc: $(which mpicc)"
echo "mpirun: $(which mpirun)"

cd "$FLASH_HOME"
rm -rf object/

echo ""
echo "--- FLASH setup (LaserSlab 1D) ---"
./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio \
    species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
    -objdir=object -parfile=example1d.par 2>&1 | tail -20

echo ""
echo "--- 编译 FLASH ---"
cd object/
make -j$(nproc) 2>&1 | tail -10

if [ -f flash4 ]; then
    echo ""
    echo "========================================="
    echo "  FLASH 编译成功！"
    echo "  可执行文件: $(pwd)/flash4"
    echo "  大小: $(du -sh flash4 | cut -f1)"
    echo "========================================="
else
    echo ""
    echo "========================================="
    echo "  FLASH 编译失败！"
    echo "========================================="
    echo "错误日志 (最后30行):"
    make 2>&1 | tail -30 || true
    exit 1
fi
