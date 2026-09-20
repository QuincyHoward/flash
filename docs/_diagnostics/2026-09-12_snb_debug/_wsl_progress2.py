# -*- coding: utf-8 -*-
import io
import subprocess

DISTRO = "Ubuntu-22.04"
OBJ = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_progress2.txt"

SCRIPT = r"""
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
echo "=== HOME ==="; echo "HOME=$HOME"
echo "=== OBJDIR ==="; ls -la $OBJ/ 2>&1 | head -25
echo "=== NXB ==="; grep -m1 -oE 'DNXB=[0-9]+' $OBJ/Makefile 2>&1
echo "=== SETUPCALL ==="; grep -m1 'setup' $OBJ/setup_call 2>/dev/null; ls $OBJ/*.log 2>/dev/null | head
echo "=== LOG ==="; ls -la $OBJ/wsl_run_snbonech.log 2>&1
echo "=== LOG TAIL ==="; tail -c 1500 $OBJ/wsl_run_snbonech.log 2>&1
echo
echo "=== STEP TRACE ==="; grep -E '^ *[0-9]+ ' $OBJ/wsl_run_snbonech.log 2>/dev/null | tail -15
echo "=== GREP ERR ==="; grep -icE 'ERROR|abort|Nonconv' $OBJ/wsl_run_snbonech.log 2>/dev/null
echo "=== CHK ==="; ls -la $OBJ/*_chk_* 2>&1 | tail -6
echo "=== END ==="
"""


def run(cmd, timeout=240):
    p = subprocess.run(["wsl", "-d", DISTRO, "--", "bash", "-lc", cmd],
                       capture_output=True, timeout=timeout)
    return (p.stdout or b"").decode("utf-8", "replace"), \
           (p.stderr or b"").decode("utf-8", "replace")


out, err = run(SCRIPT)
with io.open(OUT, "w", encoding="utf-8") as fh:
    fh.write(out)
print(out)
if err.strip():
    print("[stderr]", err[-400:])
