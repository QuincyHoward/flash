#!/bin/bash
# 收集 HDF5 文件到 hello_flash/outputfiles/ 目录
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 用户名解析: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
# 用户名必须通过 flash._core.credentials 设置, 请勿硬编码
source "$SCRIPT_DIR/flash_user_lib.sh"
FLASH_SIM_USER_DIR="${FLASH_SIM_USER_DIR:-$(resolve_flash_user)}"
FLASH_HOME="$HOME/$FLASH_SIM_USER_DIR/FLASH/FLASH4.8"
RUN_DIR="$FLASH_HOME/run_laserslab"
HELLO_DIR="$SCRIPT_DIR"

HDF5_COLLECT_DIR="$HELLO_DIR/outputfiles/hdf5files/laserslab1d"
PLOTS_DIR="$HELLO_DIR/outputfiles/plots"

echo "=== 收集 HDF5 文件 ==="
mkdir -p "$HDF5_COLLECT_DIR"
mkdir -p "$PLOTS_DIR"

_copied=0
for f in "$RUN_DIR/"*hdf5_chk_*; do
    [ -f "$f" ] || continue
    cp "$f" "$HDF5_COLLECT_DIR/"
    _copied=$((_copied+1))
done

# 也复制 plt 文件 (如有)
_plt_copied=0
for f in "$RUN_DIR/"*hdf5_plt_*; do
    [ -f "$f" ] || continue
    cp "$f" "$HDF5_COLLECT_DIR/"
    _plt_copied=$((_plt_copied+1))
done

echo "已复制 $_copied 个 checkpoint + $_plt_copied 个 plotfile"
echo "目标: $HDF5_COLLECT_DIR"
ls "$HDF5_COLLECT_DIR/" | head -20
echo "..."
echo "总计: $(ls "$HDF5_COLLECT_DIR/" | wc -l) 个文件"
