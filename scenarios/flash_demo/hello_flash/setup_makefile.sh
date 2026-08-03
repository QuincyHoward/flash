#!/bin/bash
# 配置 FLASH Makefile.h
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

echo "=== 配置 Makefile.h ==="

# 检查模板文件
TEMPLATE="$FLASH_HOME/sites/Prototypes/Linux/Makefile.h"
if [ ! -f "$TEMPLATE" ]; then
    echo "ERROR: Makefile.h template not found at $TEMPLATE"
    echo "Available sites:"
    ls "$FLASH_HOME/sites/Prototypes/" 2>/dev/null || true
    exit 1
fi

# 复制模板
cp "$TEMPLATE" "$FLASH_HOME/Makefile.h"
echo "Copied Makefile.h template"

# 替换路径
sed -i "s|^MPI_PATH\s*=.*|MPI_PATH = $MPI_PATH|" "$FLASH_HOME/Makefile.h"
sed -i "s|^HDF5_PATH\s*=.*|HDF5_PATH = $HDF5_PATH|" "$FLASH_HOME/Makefile.h"
sed -i "s|^HYPRE_PATH\s*=.*|HYPRE_PATH = $HYPRE_PATH|" "$FLASH_HOME/Makefile.h"

echo "Paths updated:"
grep -E "^(MPI_PATH|HDF5_PATH|HYPRE_PATH)" "$FLASH_HOME/Makefile.h"

# 添加 LIB_LAPACK
if ! grep -q "^LIB_LAPACK" "$FLASH_HOME/Makefile.h"; then
    sed -i "/^HYPRE_PATH/a LIB_LAPACK = -llapack -lblas -lgfortran" "$FLASH_HOME/Makefile.h"
    echo "Added LIB_LAPACK = -llapack -lblas -lgfortran"
fi

# 注释掉 FLASHBINARY ifeq 块
_sl=$(grep -n "FLASHBINARY" "$FLASH_HOME/Makefile.h" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$_sl" ]; then
    _el=$(tail -n +"$_sl" "$FLASH_HOME/Makefile.h" | grep -n "^endif" 2>/dev/null | head -1 | cut -d: -f1)
    if [ -n "$_el" ]; then
        _el=$((_sl + _el - 1))
        sed -i "${_sl},${_el}s/^/#/" "$FLASH_HOME/Makefile.h"
        echo "Commented FLASHBINARY ifeq block (lines ${_sl}-${_el})"
    fi
fi

echo "Makefile.h 配置完成"
