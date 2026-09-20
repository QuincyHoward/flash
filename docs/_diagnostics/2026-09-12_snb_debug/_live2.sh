#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
echo "=== 进程 ==="
ps -eo pid,etimes,pcpu,args | grep -E "flash4|mpiexec|make|setup" | grep -v grep | head -10
echo
echo "=== objdir flash.par 关键键 (确认已用新 par) ==="
if [ -f "$OBJ/flash.par" ]; then
  grep -nE "^(rt_mgdFlMode|RiemannSolver|gr_hypreUseFloor|iProcs|tmax)" "$OBJ/flash.par"
else
  echo "(flash.par 尚未生成)"
fi
echo
echo "=== 日志/输出 ==="
if [ -f "$OBJ/wsl_run_snbonech.log" ]; then
  echo "log lines: $(wc -l < $OBJ/wsl_run_snbonech.log)"
  grep -c "Nonconv" "$OBJ/wsl_run_snbonech.log" 2>/dev/null | sed 's/^/Nonconv: /'
  echo "--- tail 6 ---"
  tail -6 "$OBJ/wsl_run_snbonech.log"
else
  echo "(运行日志尚未生成; 可能还在 make)"
fi
echo
echo "=== make 日志尾 ==="
if [ -f "$OBJ/make_snb.log" ]; then tail -3 "$OBJ/make_snb.log"; fi
echo
echo "=== flash4 是否存在 ==="
ls -la "$OBJ/flash4" 2>&1 | head -2
