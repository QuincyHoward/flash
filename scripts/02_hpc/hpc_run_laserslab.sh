#!/bin/bash
# 超算 LaserSlab 1D 运行脚本 (上传后执行)
# 用户名: 环境变量 FLASH_SIM_USER_DIR → 默认 hello (勿硬编码用户名)
set -e
SIM_USER_DIR="${FLASH_SIM_USER_DIR:-hello}"
FLASH_HOME=$HOME/$SIM_USER_DIR/FLASH/FLASH4.8
MPI=/public1/soft/oneAPI/2022.1/mpi/latest
export PATH=$MPI/bin:$PATH
export LD_LIBRARY_PATH=/public1/soft/hdf5/1.8.18/lib:$HOME/$SIM_USER_DIR/FLASH/local/hypre/lib:$LD_LIBRARY_PATH

RUN_DIR=$HOME/$SIM_USER_DIR/FLASH/run_laserslab_hpc_test
cd "$RUN_DIR"
echo "=== 运行仿真 (mpirun -np 4) ==="
mpirun -np 4 "$FLASH_HOME/object/flash4" 2>&1 | tail -15
echo ""
echo "=== 检查输出 ==="
CHK=$(ls *hdf5_chk_* 2>/dev/null | wc -l)
PLT=$(ls *hdf5_plt_cnt_* 2>/dev/null | wc -l)
echo "checkpoint: $CHK, plot: $PLT"
ls -lh *hdf5* 2>/dev/null | head -8
echo "RUN_FINISHED"
