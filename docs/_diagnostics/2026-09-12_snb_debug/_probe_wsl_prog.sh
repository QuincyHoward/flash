#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
echo "=== OBJ EXISTS ==="
test -d "$OBJ" && echo "YES: $OBJ" || echo "NO"
echo "=== NXB ==="
grep -m1 -oE 'DNXB=[0-9]+' "$OBJ/Makefile" 2>&1
echo "=== SETUP CALL ==="
ls "$OBJ"/setup_call 2>/dev/null && head -c 400 "$OBJ"/setup_call 2>/dev/null
echo
echo "=== LOG FILE ==="
ls -la "$OBJ"/wsl_run_snbonech.log 2>&1
echo "=== LOG TAIL 1500 ==="
tail -c 1500 "$OBJ"/wsl_run_snbonech.log 2>&1
echo
echo "=== STEP TRACE (last 15) ==="
grep -E '^ *[0-9]+ ' "$OBJ"/wsl_run_snbonech.log 2>/dev/null | tail -15
echo "=== ERROR/NONCONV COUNT ==="
grep -icE 'ERROR|abort|Nonconv' "$OBJ"/wsl_run_snbonech.log 2>/dev/null
echo "=== CHK FILES ==="
ls -la "$OBJ"/*_chk_* 2>&1 | tail -8
echo "=== END ==="
