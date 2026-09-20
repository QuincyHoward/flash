#!/bin/bash
# NC-E 4864358 收尾诊断: 步进效率 / dt 历史 / HYPRE 统计 / 初末态对比
OBJ=$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
L=$OBJ/wsl_run_snbonech.log
echo "=== 日志总行数 ==="; wc -l "$L"
echo
echo "=== 头 40 行 (setup 参数回显) ==="; head -40 "$L"
echo
echo "=== 前 10 步 ==="; grep -E '^ *[0-9]+ ' "$L" | head -10
echo
echo "=== dt 演化 (每 800 步采样) ==="
grep -E '^ *[0-9]+ ' "$L" | awk 'NR%800==1 {print $1, $2, $3, $4, $5}'
echo
echo "=== Nonconv 统计 ==="
echo "Nonconv 总次数: $(grep -c 'Nonconv' "$L")"
echo "component 分布:"; grep -oE 'component=[0-9]+' "$L" | sort | uniq -c
echo "ierr 分布:"; grep -oE 'ierr=[0-9]+' "$L" | sort | uniq -c
echo
echo "=== WARN 内容 ==="; grep -E 'WARN' "$L" | head -10
echo
echo "=== chk 文件 (总数 + 首末) ==="
ls "$OBJ"/snbonechug_hdf5_chk_* 2>/dev/null | wc -l
ls -la "$OBJ"/snbonechug_hdf5_chk_0000 "$OBJ"/snbonechug_hdf5_chk_0023 2>&1
echo
echo "=== 步效率 (9073 步 / 3484 s) ==="
echo "3484.33 / 9073 = 0.384 s/step"
echo "目标 1.6 ns 若 dt 仍 9e-15 => 1.6e-9/9e-15 = 177778 步 => 19.0 h"
echo "=== END ==="
