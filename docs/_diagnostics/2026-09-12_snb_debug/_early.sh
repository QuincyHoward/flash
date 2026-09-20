#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
echo "=== 步骤 96-200 (dt 初始演化 + 首个异常) ==="
sed -n '96,200p' "$LOG"
