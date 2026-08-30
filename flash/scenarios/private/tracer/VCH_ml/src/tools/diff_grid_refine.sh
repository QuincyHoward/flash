#!/bin/bash
# 对比参考 runfiles 与 WSL FLASH4.8 paramesh 源码的 Grid_markRefine 文件
REF='/mnt/e/ProgramsPATH/VMware/SharedFiles/Ubuntu24/FLASHWorkspace/FLASHProjectData/data/input/CH_CH_02um8.00e-02/CH_CH_02um8.00e-022026/hdf5files_20260517_081325/runfiles'
for f in Grid_markRefineDerefine Grid_markRefineSpecialized; do
  echo "===== $f ====="
  tr -d '\r' < "$REF/$f.F90" > "/tmp/ref_$f.F90"
  diff "/tmp/ref_$f.F90" "/root/QC/FLASH/FLASH4.8/source/Grid/GridMain/paramesh/$f.F90" > "/tmp/d_$f.txt"
  echo "diff lines: $(wc -l < /tmp/d_$f.txt)"
  head -50 "/tmp/d_$f.txt"
done
