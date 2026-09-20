#!/bin/bash
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
SIM="/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNBOneCH_ml"
echo "=== 目标文件是否真实可见 (多次采样) ==="
for i in 1 2 3 4 5; do
  if [ -r "$SIM/CH-BADGER-TOPS-Final.cn4" ]; then
    sz=$(stat -c %s "$SIM/CH-BADGER-TOPS-Final.cn4" 2>/dev/null)
    echo "sample $i: VISIBLE size=$sz"
  else
    echo "sample $i: *** INVISIBLE ***"
  fi
done
echo ""
echo "=== 链接可达性测试 ==="
for t in CH-BADGER-TOPS-Final.cn4 CH-QC-1-001.cn4 He-BADGER-TOPS-Final.cn4 ; do
  if [ -f "$OBJ/$t" ]; then echo "OK   -f $t"; else echo "FAIL -f $t"; fi
  if [ -e "$OBJ/$t" ]; then echo "OK   -e $t"; else echo "FAIL -e $t"; fi
done
echo ""
echo "=== 源目录归属与挂载 ==="
stat -c '%n -> %s bytes, dev=%d' "$SIM"/CH-BADGER-TOPS-Final.cn4 2>/dev/null
df -h "$SIM" /root 2>/dev/null | head -6
echo ""
echo "=== 改为实体复制 ==="
cd "$OBJ" || exit 9
rm -f "$OBJ"/*.cn4
for f in "$SIM"/*.cn4 ; do
  [ -r "$f" ] || { echo "SKIP unreadable $f"; continue; }
  cp -f "$f" "$OBJ/$(basename "$f")" && echo "COPIED $(basename "$f") $(stat -c %s "$f")"
done
echo "--- 复制后 ---"
ls -l "$OBJ"/*.cn4
