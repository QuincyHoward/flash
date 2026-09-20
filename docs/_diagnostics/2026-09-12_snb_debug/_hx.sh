#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
echo "=== par: 热交换 / 传导 / 边界 相关键 ==="
grep -nE "useHeatexchange|hx_|useDiffuse|diff_|useConduct|useRadTrans|rt_|op_|eos_" "$OBJ/flash.par" | grep -vE "^\s*#" | head -60
echo
echo "=== par: 边界条件键 ==="
grep -nE "BoundaryType|boundary|xlbound|nrefine|bc_" "$OBJ/flash.par" | head -40
