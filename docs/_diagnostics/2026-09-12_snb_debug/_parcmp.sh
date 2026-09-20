#!/bin/bash
OUR=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/flash.par
REF=/root/QC/FLASH/FLASH4.8/SNB_1D_laser/flash.par
echo "=== OUR: HYPRE / SNB / MGD 关键键 ==="
grep -nE "^(gr_hypre|rt_mgd|rt_useMGD|rt_useRadTrans|useRadTrans|diff_|hx_|RiemannSolver|entropy|useHydro|hy_)" "$OUR"
echo
echo "=== REF: HYPRE / SNB / MGD 关键键 (含注释) ==="
grep -nE "gr_hypre|rt_mgd|rt_useMGD|rt_useRadTrans|useRadTrans|diff_ele|RiemannSolver|entropy" "$REF"
echo
echo "=== OUR: 是否启用 RadTrans ==="
grep -nE "useRadTrans|rt_useRadTrans|RadTrans" "$OUR" || echo "(无)"
echo
echo "=== OUR: iProcs / nblock / domain ==="
grep -nE "^(iProcs|nblockx|nblocky|nblockz|xmin|xmax|ymin|ymax|nzb|nxb|dtmin|dtmax|tmax|tstep_change_factor|gr_hypreUseFloor|gr_hypreFloor)" "$OUR"
