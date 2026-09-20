#!/bin/bash
# 对比 chk_0000 与 chk_0001 的全局标量 (用 flash4 自带的不能再读; 改读 dat/log)
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
echo "=== snbonech.log 关键列 (t, dt, dt_hydro, dt_Diff, dt_HeatXc, CFL) 首尾 ==="
grep -nE '^ *[0-9]+ ' "$OBJ/wsl_run3.log" | head -3
echo "..."
grep -nE '^ *[0-9]+ ' "$OBJ/wsl_run3.log" | tail -5
echo ""
echo "=== 运行时参数错误/警告汇总 ==="
grep -nE 'WARNING|ERROR|ignoring unknown|outside|clamp|extrapolat' "$OBJ/wsl_run3.log" | head -40
echo ""
echo "=== .dat 能量文件 ==="
ls -la "$OBJ"/snbonechug*.dat
echo ""
echo "=== log 行数 ==="
wc -l "$OBJ/wsl_run3.log"
