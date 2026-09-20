#!/bin/bash
# 解析 He/CH BADGER cn4 表头的真实物理含义: 密度轴 + 温度轴 (单位)
SIM="/root/QC/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNBOneCH_ml"
for t in CH-BADGER-TOPS-Final.cn4 He-BADGER-TOPS-Final.cn4 ; do
  echo "############ $t ############"
  echo "--- 第 1..5 行 (头部) ---"
  head -5 "$SIM/$t" | cat -A | sed 's/\$$//' | head -5
  echo "--- 数字行 (跳过注释) ---"
  grep -vE '^[[:space:]]*[A-Za-z#]' "$SIM/$t" | head -3
  echo ""
done
