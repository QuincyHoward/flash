#!/bin/bash
# 读 NC-E 上 RUNNING 作业 4864358 的真实运行日志 (run.sh 把 stdout 重定向进了 objdir)
OBJ=$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
echo "=== OBJDIR ==="
ls -la "$OBJ" 2>&1 | head -30
echo
echo "=== 日志文件 ==="
ls -la "$OBJ"/wsl_run_snbonech.log 2>&1
echo
echo "=== 日志尾部 2000 字节 ==="
tail -c 2000 "$OBJ"/wsl_run_snbonech.log 2>&1
echo
echo "=== 步进轨迹 (最后 15 步) ==="
grep -E '^ *[0-9]+ ' "$OBJ"/wsl_run_snbonech.log 2>/dev/null | tail -15
echo
echo "=== 步数统计 ==="
grep -cE '^ *[0-9]+ ' "$OBJ"/wsl_run_snbonech.log 2>/dev/null
echo
echo "=== Nonconv / WARN / ABORT ==="
grep -c 'Nonconv' "$OBJ"/wsl_run_snbonech.log 2>/dev/null
grep -cE 'WARN' "$OBJ"/wsl_run_snbonech.log 2>/dev/null
grep -cE 'ERROR|ABORT' "$OBJ"/wsl_run_snbonech.log 2>/dev/null
echo
echo "=== RUN_EXIT 标记 ==="
grep -E 'RUN_EXIT|WALL_SECONDS|RUN_DONE' "$OBJ"/wsl_run_snbonech.log 2>/dev/null
echo
echo "=== 输出文件 (chk/plt) ==="
ls -la "$OBJ"/snbonechug_hdf5_chk_* "$OBJ"/snbonechug_hdf5_plt_cnt_* 2>&1 | tail -10
echo
echo "=== 当前时刻 (real scalars 里的 t) ==="
grep -A2 'real scalars' "$OBJ"/wsl_run_snbonech.log 2>/dev/null | head -5
echo "=== END ==="
