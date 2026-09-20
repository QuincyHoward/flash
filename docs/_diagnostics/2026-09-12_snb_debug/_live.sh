#!/bin/bash
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
LOG="$OBJ/wsl_run_snbonech.log"
echo "=== cn4 in objdir ==="
ls -l "$OBJ"/*.cn4 2>/dev/null | sed 's#.*/##'
echo ""
echo "=== 错误检查 ==="
grep -cE 'ERROR|ABORT' "$LOG" 2>/dev/null || echo "no log/0"
grep -nE 'ERROR|ABORT' "$LOG" 2>/dev/null | head -5
echo ""
echo "=== 时间步 (末尾 8 行) ==="
tail -8 "$LOG" 2>/dev/null
echo ""
echo "=== 步数统计 ==="
grep -cE '^ *[0-9]+ ' "$LOG" 2>/dev/null
echo ""
echo "=== 进程是否存活 ==="
pgrep -a flash4 2>/dev/null | head -3 || echo "no flash4 process"
echo ""
echo "=== 输出文件 ==="
ls -la "$OBJ"/snbonechug_* 2>/dev/null | tail -8
echo ""
echo "=== 日志大小/行数 ==="
wc -lc "$LOG" 2>/dev/null
