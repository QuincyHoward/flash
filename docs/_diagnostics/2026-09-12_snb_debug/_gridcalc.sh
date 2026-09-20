#!/bin/bash
pkill -9 -f flash4 2>/dev/null
pkill -9 -f mpiexec 2>/dev/null
sleep 2
echo "剩余进程: $(ps -eo args | grep -E 'flash4|mpiexec' | grep -v grep | wc -l)"
echo
echo "=== 目标: dx <= 0.03um = 3e-6 cm; 域宽 0.05 cm ==="
python3 - <<'PY'
dom = 0.05          # cm
target = 3e-6       # cm  (0.03 um)
n_cells = dom/target
print(f"所需最小单元数 = {dom:.6g}/{target:.3g} = {n_cells:.0f}")
for n in (4, 8, 16, 131):
    # +ug: iProcs 必须 == mpiexec -n; nxb 按 2 的幂取
    import math
    need = n_cells/n
    nxb = 2**math.ceil(math.log2(need))
    if nxb < 8: nxb = 8
    dx = dom/(n*nxb)
    print(f"  n={n:4d}  nxb={nxb:6d}  总格={n*nxb:8d}  dx={dx:.4e} cm = {dx*1e4:.5f} um "
          f"{'✓ OK' if dx <= target else '✗ 过粗'}")
PY
