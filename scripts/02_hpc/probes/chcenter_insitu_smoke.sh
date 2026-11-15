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
# ★ 2026-11-11 可移植化：ch_center 目录经 discovery 按名解析（场景移动免疫），
#   不再字面量硬编码包路径；runpy 以 __main__ 语义执行场景主脚本。
"$TARGET/.venv-hpc-nce/bin/python" -c "import runpy, sys; from pathlib import Path; from flash.scenarios.core.scene_reg.discovery import resolve_scene_meta; d = Path(resolve_scene_meta('ch_center').source).parent; runpy.run_path(str(d / 'laserslab1d_local_custom.py'), run_name='__main__')"
echo $? > "$PKG/chcenter_insitu.done"
