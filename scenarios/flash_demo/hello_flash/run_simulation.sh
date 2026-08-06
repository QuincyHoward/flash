#!/bin/bash
# 运行 FLASH LaserSlab 1D 仿真
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

export PATH="$MPI_PATH/bin:$HDF5_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${LD_LIBRARY_PATH:-}"

FLASH_EXE="$FLASH_HOME/object/flash4"
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/LaserSlab"
RUN_DIR="$FLASH_HOME/run_laserslab"

echo "=== 运行 LaserSlab 1D 仿真 ==="
echo "FLASH_EXE: $FLASH_EXE"
echo "RUN_DIR: $RUN_DIR"

# 准备运行目录
rm -rf "$RUN_DIR"
mkdir -p "$RUN_DIR"
cd "$RUN_DIR"

# 复制 EOS 表
echo "复制 EOS 数据表..."
cp "$SIM_SRC_DIR/al-imx-003.cn4" "$RUN_DIR/" 2>/dev/null && echo "  + al-imx-003.cn4" || echo "  WARNING: 未找到 al-imx-003.cn4"
cp "$SIM_SRC_DIR/he-imx-005.cn4"  "$RUN_DIR/" 2>/dev/null && echo "  + he-imx-005.cn4"  || echo "  WARNING: 未找到 he-imx-005.cn4"

# 复制参数文件
if [ -f "$SIM_SRC_DIR/example1d.par" ]; then
    cp "$SIM_SRC_DIR/example1d.par" "$RUN_DIR/flash.par"
    echo "  + flash.par"
else
    echo "ERROR: 找不到 example1d.par"
    exit 1
fi

echo ""
echo "启动 FLASH 仿真 (mpirun -np 1)..."
echo "日志: $RUN_DIR/flash_output.log"
echo ""

# 运行仿真
"$MPI_PATH/bin/mpirun" -np 1 "$FLASH_EXE" 2>&1 | tee "$RUN_DIR/flash_output.log"

echo ""

# 验证输出
_chk_cnt=$(ls "$RUN_DIR/"*hdf5_chk_* 2>/dev/null | wc -l || echo 0)
if [ "$_chk_cnt" -gt 0 ]; then
    echo "========================================="
    echo "  仿真成功！生成了 $_chk_cnt 个 checkpoint 文件"
    echo "========================================="
    ls -lh "$RUN_DIR/"*hdf5_chk_* 2>/dev/null
else
    echo "========================================="
    echo "  仿真失败：未找到 checkpoint 文件"
    echo "========================================="
    echo "日志末尾 (最后30行):"
    tail -30 "$RUN_DIR/flash_output.log" 2>/dev/null || true
    exit 1
fi
