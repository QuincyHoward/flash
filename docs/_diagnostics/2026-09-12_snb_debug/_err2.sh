#!/bin/bash
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
echo "=== 全部 ERROR/ABORT 行 ==="
grep -nE 'ERROR|ABORT|FATAL|not found|Error message|abort' "$OBJ/wsl_run_snbonech.log" | head -30
echo ""
echo "=== 尾部 40 行 ==="
tail -40 "$OBJ/wsl_run_snbonech.log"
echo ""
echo "=== objdir cn4 链接 ==="
ls -l "$OBJ"/*.cn4 2>/dev/null
echo ""
echo "=== par 中所有 eos_/op_ 表名 (去重) ==="
grep -oE '(eos_[A-Za-z0-9]+TableFile|op_[A-Za-z0-9]+FileName) *= *"[^"]+"' "$OBJ/flash.par" \
  | sed -E 's/.*"([^"]+)".*/\1/' | sort -u
