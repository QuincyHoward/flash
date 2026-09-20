#!/bin/bash
# 在 WSL 内为 objdir 补齐所有 cn4 符号链接, 并校验 par 引用的每个表都在。
set -u
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
SIM="/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNBOneCH_ml"

echo "=== STEP1: 源目录 cn4 ==="
ls -1 "$SIM"/*.cn4

echo "=== STEP2: 建立链接 ==="
cd "$OBJ" || exit 9
for f in "$SIM"/*.cn4 ; do
  b="$(basename "$f")"
  ln -sf "$f" "$b"
  echo "LINK $b"
done

echo "=== STEP3: objdir cn4 现状 ==="
ls -1 "$OBJ"/*.cn4

echo "=== STEP4: par 引用的表逐一检查 ==="
MISS=0
for t in $(grep -oE '(eos_[A-Za-z0-9]+TableFile|op_[A-Za-z0-9]+FileName)[[:space:]]*=[[:space:]]*"[^"]+"' "$OBJ/flash.par" \
           | sed -E 's/.*"([^"]+)".*/\1/' | sort -u) ; do
  if [ -e "$OBJ/$t" ] ; then
    echo "OK   $t"
  else
    echo "MISS $t"
    MISS=$((MISS+1))
  fi
done
echo "MISS_COUNT=$MISS"
exit 0
