#!/bin/bash
# 提取 run3 日志的完整时间步表头 + 前 25 步 (含 dt_Diff 首次出现), 以及物理量列含义
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
echo "=== 表头 ==="
sed -n '95,100p' "$OBJ/wsl_run3.log"
echo "=== 前 27 步 ==="
sed -n '97,125p' "$OBJ/wsl_run3.log"
echo "=== 初始化关键行 ==="
grep -nEi 'dens|temp|tele|tion|nele|nion|sumy|ye|zbar|initial' "$OBJ/wsl_run3.log" | head -40
