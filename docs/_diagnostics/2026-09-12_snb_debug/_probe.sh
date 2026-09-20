#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
echo "=== 前 99 行完整 (含初始条件回显) ==="
sed -n '60,99p' "$LOG"
echo
echo "=== 查 dens/temp/vel 相关 WARN/异常 ==="
grep -inE "warn|nan|inf|negativ|bad|invalid" "$LOG" | head -25
echo
echo "=== par 中的 sim_ 剖面参数 ==="
grep -nE "^(sim_|xmin|xmax|nblock|lrefine|iProcs|dtmin|dtmax|tmax|smallt|rt_|gr_hypre|eos_|op_)" $OBJ/flash.par | head -80
