#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
# 只保留 step 行并取前 60 行 + 关键转折
echo "=== FIRST 40 step lines ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | head -40
echo
echo "=== step 400-460 (dt 演化) ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | sed -n '400,460p'
echo
echo "=== step 900-960 ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | sed -n '900,960p'
echo
echo "=== 首个 dt<1e-14 出现处 ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | awk 'NF>=4 && $3+0 < 1e-14 {print NR": "$0; c++; if(c>=8) exit}'
echo
echo "=== dt 最小值/最大值的步数分布 (每 2000 步采样) ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | awk 'NR%2000==1 {print NR": "$0}'
echo
echo "=== LAST 5 step lines ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | tail -5
