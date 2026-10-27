#!/usr/bin/env bash
# t003 辅助: 对比"仓库示例副本(未打补丁)"与"WSL FLASHSNB 工作副本(含 6 补丁)"
# 用法: wsl -d Ubuntu-22.04 bash <此脚本路径>
set -u

W="${FLASHSNB_SRC:?请设置 FLASHSNB_SRC=<WSL 内 FLASHSNB 工作副本>/source/Simulation/SimulationMain/SNB_1D_laser}"
R="$(cd "$(dirname "$0")/../../../../../.." && pwd)/flash/scenarios/private/SNB/SNBtest/src/SNB/SNB_1D_laser/SNB_1D_laser"   # 8 级向上到仓库根

echo "仓库副本 = $R"
echo "工作副本 = $W"
echo

for f in diff_advanceTherm.F90 Conductivity.F90 Driver_evolveFlash.F90 \
         Grid_advanceDiffusion.F90 hy_uhd_DataReconstructNormalDir_PPM.F90 \
         hy_uhd_dataReconstOneStep.F90 hy_uhd_getRiemannState.F90 \
         hy_uhd_ragelike.F90 Config Makefile Simulation_data.F90 \
         Simulation_init.F90 Simulation_initBlock.F90 mgd_qesh.F90; do
  if [ ! -f "$R/$f" ]; then
    echo "== $f : 仓库缺失 =="
    continue
  fi
  if [ ! -f "$W/$f" ]; then
    echo "== $f : 工作副本缺失 =="
    continue
  fi
  n=$(diff -u "$R/$f" "$W/$f" | grep -cE '^[+-][^+-]' || true)
  if [ "$n" -eq 0 ]; then
    echo "== $f : 完全相同 =="
  else
    echo "== $f : 差异 $n 行 =="
    diff -u "$R/$f" "$W/$f" | sed -n '3,60p'
  fi
  echo
done
