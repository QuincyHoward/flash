#!/bin/bash
# clean_sandwich_txn_wsl.sh — 清理 WSL 本地 FLASH 树中 sandwich_txn 旧输入输出
rm -rf $HOME/QC/FLASH/FLASH4.8/source/Simulation/SimulationMain/QC/sandwich_txn_* \
       $HOME/QC/FLASH/FLASH4.8/QC/object_sandwich_txn_* \
       /tmp/flash_sandwich_txn_* /tmp/.flash_compile_sandwich_txn.lock
echo "local FLASH tree:"
ls $HOME/QC/FLASH/FLASH4.8/QC/ | grep sandwich || echo "  (no sandwich_txn artifacts)"
ls /tmp/ | grep -i "flash_sandwich" || echo "  (no /tmp run dirs)"
