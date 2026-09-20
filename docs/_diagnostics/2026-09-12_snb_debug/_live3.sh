#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
echo "=== dt 演化采样 (每 1500 行) ==="
grep -E '^[[:space:]]*[0-9]+ ' "$LOG" | awk 'NR%1500==1 {print NR": "$0}'
echo
echo "=== dtmin / dtmax 生效值 ==="
grep -nE "dtmin|dtmax" "$OBJ/flash.par" | head -5
echo
echo "=== 是否有 WARN/负温度/NaN ==="
echo -n "eos_nr WARN: "; grep -c "eos_nr WARN" "$LOG" || true
echo -n "Nonconv: "; grep -c "Nonconv" "$LOG" || true
echo -n "ERROR/ABORT: "; grep -cE "ERROR|ABORT" "$LOG" || true
echo
echo "=== 前 10 个 Nonconv (含步号上下文) ==="
grep -n "Nonconv" "$LOG" | head -10
echo
echo "=== 第 95-115 行 (初始 dt 序列) ==="
sed -n '95,115p' "$LOG"
