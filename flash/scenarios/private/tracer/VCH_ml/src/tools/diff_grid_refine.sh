#!/bin/bash
# 对比参考 runfiles 与 WSL FLASH4.8 paramesh 源码的 Grid_markRefine 文件
REF="${FLASH_OLD_VM_RUNFILES:?请先 export FLASH_OLD_VM_RUNFILES=<旧 VM 参考算例 runfiles 目录>}"
for f in Grid_markRefineDerefine Grid_markRefineSpecialized; do
  echo "===== $f ====="
  tr -d '\r' < "$REF/$f.F90" > "/tmp/ref_$f.F90"
  diff "/tmp/ref_$f.F90" "${FLASH4_PARAMESH_SRC:?请先 export FLASH4_PARAMESH_SRC=<WSL 内 FLASH4.8 源码 Tree>/source/Grid/GridMain/paramesh}/$f.F90" > "/tmp/d_$f.txt"
  echo "diff lines: $(wc -l < /tmp/d_$f.txt)"
  head -50 "/tmp/d_$f.txt"
done
