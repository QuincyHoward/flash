#!/bin/bash
# chcenter_insitu_smoke.sh — ch_center hpc-insitu 端到端冒烟（超算登录节点执行）
TARGET=$HOME/PhySimX/PhySimX/simulation/flash/flash_sim
PKG=$HOME/PhySimX/PhySimX/simulation/flash/flash_sim_pkg
source /public1/soft/modules/module.sh 2>/dev/null || true
module load python/3.10.8
cd "$TARGET"
export PYTHONUNBUFFERED=1
export FLASH_VENV_DIR="$TARGET/.venv-hpc-nce"
export PYTHONPATH="$TARGET"
export FLASH_RUN_MODE="hpc-insitu"
export FLASH_NO_MODULE_PURGE=1   # NC-E: QC 通用树按 Intel MPI 链接, 禁 purge
"$TARGET/.venv-hpc-nce/bin/python" flash/scenarios/public/center_evolution/ch_center/laserslab1d_local_custom.py
echo $? > "$PKG/chcenter_insitu.done"
