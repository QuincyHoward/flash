#!/usr/bin/env bash
# make_snb_t001.sh - 编译 SNB_1D_laser_obj（在 WSL 中执行）
set -uo pipefail
SNB="$HOME/QC/FLASH/FLASHSNB/FLASH4.8"
cd "$SNB/SNB_1D_laser_obj"
echo "=== make -j4 开始 $(date) ==="
make -j4 2>&1
RC=$?
echo "=== make 结束 exit=$RC $(date) ==="
if [ -x ./flash4 ]; then echo "flash4 可执行文件生成 OK"; ls -la flash4; else echo "flash4 未生成"; fi
exit $RC
