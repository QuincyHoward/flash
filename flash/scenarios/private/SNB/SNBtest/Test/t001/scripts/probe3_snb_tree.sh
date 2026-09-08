#!/usr/bin/env bash
# probe3: setup 机制核查
set -u
SNB="$HOME/QC/FLASH/FLASHSNB/FLASH4.8"
STAGE="/mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/scenarios/private/SNB/SNBtest/src/SNB"
PHY="$STAGE/physics/physics"

echo "=== [A] bin/setup 内容与 sim 搜索路径 ==="
ls "$SNB/bin/" | head -20
grep -rn "simdir\|SimulationMain" "$SNB/bin/setup" 2>/dev/null | head -20

echo "=== [B] setup Perl: 模拟目录覆盖单元文件的机制 ==="
grep -rn "override\|takes precedence\|same name" "$SNB/bin/setup" 2>/dev/null | head -20

echo "=== [C] DriverMain/Unsplit 内容 ==="
ls "$SNB/source/Driver/DriverMain/Unsplit/" | head

echo "=== [D] tree ConductivityMain 各变体是否有 fullState ==="
ls "$SNB/source/physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/"

echo "=== [E] staged Conductivity Makefile vs tree 的差异 ==="
diff "$PHY/materialProperties/Conductivity/Makefile" "$SNB/source/physics/materialProperties/Conductivity/Makefile"

echo "=== [F] staged ConductivityMain Makefile vs tree ==="
diff "$PHY/materialProperties/Conductivity/ConductivityMain/Makefile" "$SNB/source/physics/materialProperties/Conductivity/ConductivityMain/Makefile" | head -20

echo "=== [G] staged ConductivityMain/SpitzerHighZ 文件列表 ==="
ls "$PHY/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ/"

echo "=== [H] staged vs tree ConductivityMain/cond_commonData 等 ==="
for f in cond_commonData.F90 cond_commonInit.F90 cond_getCv.F90; do
  s="$PHY/materialProperties/Conductivity/ConductivityMain/$f"; t="$SNB/source/physics/materialProperties/Conductivity/ConductivityMain/$f"
  cmp -s "$s" "$t" && echo "$f: SAME" || echo "$f: DIFFERS ($(diff "$s" "$t" 2>/dev/null | grep -c '^[<>]') lines)"
done

echo "=== [I] staged localAPI vs tree localAPI ==="
diff -rq "$PHY/materialProperties/Conductivity/localAPI" "$SNB/source/physics/materialProperties/Conductivity/localAPI" 2>&1 | head

echo "=== [J] app Config 中 REQUIRES/REQUESTS 核对（完整） ==="
grep -n "REQUIRES\|REQUESTS" "$STAGE/SNB_1D_laser/SNB_1D_laser/Config"

echo "=== [K] 上次失败 objdir 大小/状态 ==="
du -sh "$SNB/SNB_1D_laser" 2>/dev/null; ls "$SNB/SNB_1D_laser/flash4" 2>/dev/null || echo "(无 flash4 可执行文件)"
ls "$SNB/SNB_1D_laser/flash.par" 2>/dev/null && diff "$SNB/SNB_1D_laser/flash.par" "$STAGE/SNB_1D_laser/SNB_1D_laser/flash.par" >/dev/null 2>&1 && echo "par SAME as staged" || echo "par DIFFERS or missing"
