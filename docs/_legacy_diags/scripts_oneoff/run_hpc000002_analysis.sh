#!/bin/bash
set -e
cd /mnt/e/PhySimX/PhySimX/simulation/flash_test/sandwich/flash
SC=flash/scenarios/private/Sandwich/TxN/SandwichTxN
echo "=== analyze ==="
python3 "$SC/scripts/analyze_output.py" "$SC/runs/hpc_000002/sim_output" 2>&1 | tail -9
echo "=== refine check ==="
python3 "$SC/scripts/plot_refine_levels.py" "$SC/runs/hpc_000002" 2>&1 | grep -E "wrote|VIOLATES| OK|run dir" | head -14
