#!/bin/bash
# srun_yt_test.sh — 计算节点 yt import 测试（结果落盘并行盘）
TARGET=/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim
PKG=/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim_pkg
VPY="$TARGET/.venv-hpc-nce/bin/python"
{
  echo "kernel: $(uname -r)"
  "$VPY" -c 'import yt; print("COMPUTE_YT_OK", yt.__version__)' 2>&1
  echo "RC=$?"
  "$VPY" -c 'import numpy, scipy, h5py, matplotlib; print("CORE_OK")' 2>&1
  echo "RC=$?"
} > "$PKG/srun_yt.txt" 2>&1
