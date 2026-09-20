#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
echo "=== log head 60 (含 dt 列定义) ==="
head -60 "$LOG"
echo
echo "=== 搜 dt_ 相关列标题 ==="
grep -n -iE "dt_|variable|column" "$LOG" | head -30
