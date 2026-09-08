#!/usr/bin/env bash
# setup_snb_t001.sh - SNB_1D_laser setup（在 WSL 中执行, 树根运行）
# 指令与 运行指令.txt 一致, 仅 objdir 改为 SNB_1D_laser_obj（与 app 主目录分离）
set -euo pipefail
SNB="$HOME/QC/FLASH/FLASHSNB/FLASH4.8"
cd "$SNB"

rm -rf SNB_1D_laser_obj
echo "=== setup 开始 ==="
./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio species=cham,tar1,tar2,tar3 \
  +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 -objdir=SNB_1D_laser_obj
echo "=== setup 结束, exit=$? ==="

echo "=== objdir 核对 ==="
ls -d SNB_1D_laser_obj && ls SNB_1D_laser_obj | head -20
echo "--- flash.par tmax ---"
grep -n "^tmax" SNB_1D_laser_obj/flash.par
echo "--- SimulationMain 来源核对 ---"
ls SNB_1D_laser_obj/SimulationMain/SNB_1D_laser/ 2>/dev/null | head
echo "--- setup 使用的 sim 路径 (setup 输出中查找) ---"
