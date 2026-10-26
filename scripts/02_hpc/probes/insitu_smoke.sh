#!/bin/bash
# insitu_smoke.sh — SNBOneCH_m hpc-insitu 冒烟（超算登录节点执行）
TARGET=/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim
PKG=/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim_pkg
source /public1/soft/modules/module.sh 2>/dev/null || true
module load python/3.10.8
cd "$TARGET"
export PYTHONUNBUFFERED=1
export FLASH_VENV_DIR="$TARGET/.venv-hpc-nce"
# ★ 源码树优先于 venv site-packages (wheel 0.1.7 无 insitu_runner/slurm_control)
export PYTHONPATH="$TARGET"
"$TARGET/.venv-hpc-nce/bin/python" flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py \
    --mode hpc-insitu --tmax 1.0e-11
echo $? > "$PKG/insitu_smoke.done"
