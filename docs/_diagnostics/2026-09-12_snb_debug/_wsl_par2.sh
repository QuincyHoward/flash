#!/bin/bash
# 1) 列出 run3 日志中所有初始化物理量; 2) 检查 chk_0000/0001 是否存在; 3) 看 par 初始条件键
OBJ="/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
echo "=== chk/plt 文件 ==="
ls -la "$OBJ"/snbonechug_* 2>/dev/null

echo ""
echo "=== par: 初始/密度/温度/SNB 相关键 ==="
grep -nE '^(sim_|eos_|op_|gr_hypre|useSNB|snb_|snp_|electro|tele|tion)' "$OBJ/flash.par" | head -80
