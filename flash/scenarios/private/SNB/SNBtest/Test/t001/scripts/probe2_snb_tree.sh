#!/usr/bin/env bash
# probe2_snb_tree.sh - 二轮探测：影子机制与缺失单元细节
set -u
SNB="$HOME/QC/FLASH/FLASHSNB/FLASH4.8"
STAGE="/mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/scenarios/private/SNB/SNBtest/src/SNB"
PHY="$STAGE/physics/physics"

echo "=== [A] setup script exists ==="
ls -la "$SNB/setup" "$SNB/bin/setup" 2>&1 | head -5

echo "=== [B] Driver/DriverMain contents (Driver_evolveFlash missing?) ==="
ls "$SNB/source/Driver/DriverMain/" 2>&1 | head -40

echo "=== [C] tree SimulationMain/SNB_1D_laser contents ==="
ls "$SNB/source/Simulation/SimulationMain/SNB_1D_laser/" 2>&1

echo "=== [D] tree root SNB_1D_laser app dir contents ==="
ls "$SNB/SNB_1D_laser/" 2>&1 | head -30

echo "=== [E] module names: app vs tree diff_advanceTherm ==="
grep -n "^module\|^end module" "$STAGE/SNB_1D_laser/SNB_1D_laser/diff_advanceTherm.F90" | head -5
grep -n "^module\|^end module" "$SNB/source/physics/Diffuse/DiffuseMain/Unsplit/diff_advanceTherm.F90" | head -5

echo "=== [F] staged Conductivity_interface: module procedures ==="
grep -n "module procedure\|interface \|end interface\|^module\|only :" "$PHY/materialProperties/Conductivity/Conductivity_interface.F90" | head -30

echo "=== [G] staged ConductivityMain/Conductivity_fullState exists? ==="
find "$PHY/materialProperties/Conductivity/ConductivityMain" -maxdepth 1 -name "*.F90" | head
diff -q "$PHY/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/Conductivity.F90" "$SNB/source/physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/Conductivity.F90" 2>&1

echo "=== [H] staged vs tree Conductivity Config/Makefile/init/finalize ==="
for f in Config Makefile Conductivity_init.F90 Conductivity_finalize.F90; do
  s="$PHY/materialProperties/Conductivity/$f"; t="$SNB/source/physics/materialProperties/Conductivity/$f"
  if [ -f "$t" ]; then cmp -s "$s" "$t" && echo "$f: SAME" || echo "$f: DIFFERS ($(diff "$s" "$t" | grep -c '^[<>]') lines)"; fi
done

echo "=== [I] staged Conductivity unit top-level file list ==="
ls "$PHY/materialProperties/Conductivity/"

echo "=== [J] who calls Conductivity_fullState in staged tree ==="
grep -rln "Conductivity_fullState" "$PHY" | grep -v anisoFullState | head

echo "=== [K] tree Diffuse unit state: Unsplit Makefile/Config ==="
ls "$SNB/source/physics/Diffuse/DiffuseMain/Unsplit/" | head -20

echo "=== [L] staged physics tree Diffuse Unsplit listing ==="
ls "$PHY/Diffuse/DiffuseMain/Unsplit/" | head -20
