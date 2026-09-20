import subprocess

D = "Ubuntu-22.04"

def run_wsl(cmd, timeout=180):
    p = subprocess.run(["wsl", "-d", D, "--", "bash", "-lc", cmd],
                       capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    if err.strip() and "dirname: command not found" not in err and "cd: null directory" not in err:
        out += "\n[STDERR]\n" + err
    return out

SH = r"""#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
LOG=$OBJ/wsl_run_snbonech.log
echo "=== LOG TAIL (40) ==="
tail -40 "$LOG"
echo
echo "=== COUNTS ==="
echo -n "Nonconv: "; grep -c "Nonconv" "$LOG" || true
echo -n "eos_nr WARN: "; grep -c "eos_nr WARN" "$LOG" || true
echo -n "ERROR_ABORT: "; grep -cE "ERROR|ABORT" "$LOG" || true
echo -n "TOTAL_LINES: "; wc -l < "$LOG"
echo
echo "=== LAST 12 Nonconv ==="
grep -n "Nonconv" "$LOG" | tail -12
echo
echo "=== FIRST 8 Nonconv ==="
grep -n "Nonconv" "$LOG" | head -8
echo
echo "=== dt_HeatXc occurrences ==="
grep -c "dt_HeatXc" "$LOG" || true
"""

with open(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_logdump.sh", "w",
          encoding="utf-8", newline="\n") as f:
    f.write(SH)

print(run_wsl("cp -f /mnt/e/PhySimX/PhySimX/simulation/flash_test/layer3/flash/_logdump.sh /tmp/_logdump.sh "
              "&& sed -i 's/\\r$//' /tmp/_logdump.sh && bash /tmp/_logdump.sh"))
