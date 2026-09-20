#!/bin/bash
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
L="$OBJ/wsl_run_snbonech.log"
echo "=== dt 历史 (首次触底的位置) ==="
awk 'NR>97 && NF>=10 {print NR": "$0}' "$L" | awk 'NR%1==0' | head -3
echo "..."
awk 'NR>97 && NF>=10 {print $1, $2, $3, $7, $8, $9}' "$L" | awk '$4<1e-15' | head -5
echo ""
echo "=== dt 触底的步号 (第一次) ==="
awk 'NR>97 && NF>=10 {if ($6<1e-15) {print "step="$1" t="$2" dt="$6" dtHX="$9; exit}}' "$L"
echo ""
echo "=== 采样: 每隔 10000 步 ==="
awk 'NR>97 && NF>=10 {n=$1; if (n%20000==0) print n, $2, $3, $7, $8, $9}' "$L" | head -12
echo ""
echo "=== 边界条件 (v/ele cond) ==="
grep -nE 'boundary_type|xl_boundary|xr_boundary|diff_eleX|dr_|_boundary' "$OBJ/flash.par" | head -25
echo ""
echo "=== 左边界附近网格 / xmin xmax ==="
grep -nE '^(xmin|xmax|xl_boundary_type|xr_boundary_type)' "$OBJ/flash.par"
