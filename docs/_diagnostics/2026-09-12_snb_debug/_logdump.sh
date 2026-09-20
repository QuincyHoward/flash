#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
echo "=== LOG TAIL (40) ==="
tail -40 "$LOG"
echo
echo "=== COUNTS ==="
echo -n "Nonconv: "; grep -c "Nonconv" "$LOG" || true
echo -n "eos_nr WARN: "; grep -c "eos_nr WARN" "$LOG" || true
echo -n "ERROR_ABORT: "; grep -cE "ERROR|ABORT" "$LOG" || true
echo -n "TOTAL_LINES: "; wc -l < "$LOG"
echo
echo "=== LAST 12 Nonconv ==="
grep -n "Nonconv" "$LOG" | tail -12
echo
echo "=== FIRST 8 Nonconv ==="
grep -n "Nonconv" "$LOG" | head -8
echo
echo "=== dt_HeatXc occurrences ==="
grep -c "dt_HeatXc" "$LOG" || true
