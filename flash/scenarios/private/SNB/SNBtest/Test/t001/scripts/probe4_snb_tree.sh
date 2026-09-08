#!/usr/bin/env bash
set -u
STAGE="/mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/scenarios/private/SNB/SNBtest/src/SNB"
PHY="$STAGE/physics/physics"
C="$PHY/materialProperties/Conductivity"

echo "=== [A] staged SpitzerHighZ/Makefile ==="
cat "$C/ConductivityMain/SpitzerHighZ/Makefile"
echo "=== [B] staged SpitzerHighZ 文件 vs 其 Makefile 引用 ==="
ls "$C/ConductivityMain/SpitzerHighZ/"
echo "=== [C] staged ConductivityMain 顶层文件列表 ==="
ls "$C/ConductivityMain/" | head -30
echo "=== [D] staged ConductivityMain/Constant/Makefile（对照） ==="
cat "$C/ConductivityMain/Constant/Makefile" 2>/dev/null | head -15
echo "=== [E] tree SpitzerHighZ/Makefile（现状） ==="
cat "$HOME/QC/FLASH/FLASHSNB/FLASH4.8/source/physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/Makefile"
echo "=== [F] staged Conductivity 顶层 Makefile 全文 ==="
cat "$C/Makefile"
echo "=== [G] staged Conductivity_data.F90 在哪些目录 ==="
find "$C" -name "Conductivity_data.F90"
echo "=== [H] staged Conductivity_fullState.F90 在哪些目录 ==="
find "$C" -name "Conductivity_fullState.F90"
echo "=== [I] FLASHSNB 树大小（评估备份成本） ==="
du -sh "$HOME/QC/FLASH/FLASHSNB/FLASH4.8/source" 2>/dev/null
du -sh "$HOME/QC/FLASH/FLASHSNB/FLASH4.8" 2>/dev/null
df -h /root | tail -1
