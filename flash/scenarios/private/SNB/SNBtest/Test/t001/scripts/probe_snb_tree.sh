#!/usr/bin/env bash
# probe_snb_tree.sh - FLASHSNB 树当前状态探测（只读, 不修改）
# 用法: wsl bash /mnt/e/.../t001/scripts/probe_snb_tree.sh
set -u
SNB="$HOME/QC/FLASH/FLASHSNB/FLASH4.8"
SRC="$SNB/source/physics"
STAGE="/mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/scenarios/private/SNB/SNBtest/src/SNB"

echo "=== [0] tree root ==="
ls "$SNB" 2>&1 | head -20

echo "=== [1] tree Unsplit diff_advanceTherm vs staged app/physics-tree ==="
U="$SRC/Diffuse/DiffuseMain/Unsplit/diff_advanceTherm.F90"
if [ -f "$U" ]; then
  echo "tree Unsplit: lines=$(wc -l < "$U") QESH=$(grep -c QESH "$U") anisoFullState=$(grep -c anisoFullState "$U")"
  echo "Conductivity calls in tree Unsplit:"; grep -n "call Conductivity_\|use Conductivity_interface" "$U" | head
else
  echo "MISSING: $U"
fi

echo "=== [2] tree Conductivity unit contents ==="
ls "$SRC/materialProperties/Conductivity/" 2>&1
IF="$SRC/materialProperties/Conductivity/Conductivity_interface.F90"
if [ -f "$IF" ]; then
  echo "interface anisoFullState refs: $(grep -c anisoFullState "$IF")"
  echo "interface module procedure list:"; grep -n "procedure\|module procedure" "$IF" | head -20
fi

echo "=== [3] tree ConductivityMain variants ==="
ls "$SRC/materialProperties/Conductivity/ConductivityMain/" 2>&1

echo "=== [4] staged app overrides vs tree targets ==="
declare -A MAP=(
  ["diff_advanceTherm.F90"]="$SRC/Diffuse/DiffuseMain/Unsplit/diff_advanceTherm.F90"
  ["Conductivity.F90"]="$SRC/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/Conductivity.F90"
  ["Grid_advanceDiffusion.F90"]=""
  ["Driver_evolveFlash.F90"]="$SNB/source/Driver/DriverMain/Driver_evolveFlash.F90"
  ["hy_uhd_dataReconstOneStep.F90"]="$SRC/Hydro/HydroMain/unsplit/hy_uhd_dataReconstOneStep.F90"
  ["hy_uhd_DataReconstructNormalDir_PPM.F90"]="$SRC/Hydro/HydroMain/unsplit/hy_uhd_DataReconstructNormalDir_PPM.F90"
  ["hy_uhd_getRiemannState.F90"]="$SRC/Hydro/HydroMain/unsplit/hy_uhd_getRiemannState.F90"
  ["hy_uhd_ragelike.F90"]="$SRC/Hydro/HydroMain/unsplit/multiTemp/hy_uhd_ragelike.F90"
)
APP="$STAGE/SNB_1D_laser/SNB_1D_laser"
for f in "${!MAP[@]}"; do
  t="${MAP[$f]}"
  if [ -z "$t" ]; then
    echo "$f: tree location = $(find "$SNB/source" -name "$f" 2>/dev/null | tr '\n' ' ')"
    continue
  fi
  if [ ! -f "$t" ]; then echo "$f: TARGET MISSING ($t)"; continue; fi
  if cmp -s "$APP/$f" "$t"; then echo "$f: SAME as tree"; else
    echo "$f: DIFFERS from tree ($(diff "$APP/$f" "$t" | grep -c '^[<>]') lines) target=$t"
  fi
done

echo "=== [5] physics-tree extra units not in tree? ==="
for u in Conductivity_aniso.F90 Conductivity_anisoFullState.F90 Conductivity_interface.F90; do
  s="$STAGE/physics/physics/materialProperties/Conductivity/$u"
  t="$SRC/materialProperties/Conductivity/$u"
  if [ -f "$t" ]; then
    cmp -s "$s" "$t" && echo "$u: SAME" || echo "$u: DIFFERS ($(diff "$s" "$t" | grep -c '^[<>]') lines)"
  else
    echo "$u: NOT IN TREE (needs deploy)"
  fi
done
ls -d "$SRC/materialProperties/Conductivity/ConductivityAniso" 2>/dev/null || echo "ConductivityAniso/: NOT IN TREE (needs deploy)"

echo "=== [6] Grid_advanceDiffusion in tree ==="
find "$SNB/source/Grid" -name "Grid_advanceDiffusion*" 2>/dev/null

echo "=== [7] existing objdir / app in tree ==="
ls -d "$SNB/SNB_1D_laser" "$SNB"/obj* 2>/dev/null
find "$SNB" -maxdepth 1 -name "SNB*" 2>/dev/null

echo "=== [8] toolchain ==="
which gfortran mpif90 mpiexec 2>&1
gfortran --version 2>&1 | head -1
echo "=== [9] existing NonLTConduct outputs in tree? ==="
find "$SNB" -maxdepth 2 -name "NonLTConduct*" 2>/dev/null | head
