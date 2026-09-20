# -*- coding: utf-8 -*-
"""检查 WSL 端 SNBOneCH_ml 运行进度 (只读)。"""
import io
import os
import subprocess

DISTRO = "Ubuntu-22.04"
BASE = "/root/QC/FLASH/FLASHSNB/FLASH4.8"
DEPLOY = f"{BASE}/SNBOneCH_ml_deploy"
OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_progress.txt"


def run(cmd, timeout=240):
    p = subprocess.run(
        ["wsl", "-d", DISTRO, "--", "bash", "-lc", cmd],
        capture_output=True, timeout=timeout)
    return (p.stdout or b"").decode("utf-8", "replace"), \
           (p.stderr or b"").decode("utf-8", "replace"), p.returncode


SCRIPT = r"""
echo "=== PROC ==="
ps -eo pid,etime,pcpu,pmem,comm,args --sort=-pcpu 2>/dev/null | grep -E 'flash4|mpiexec|mpirun|setup|make' | grep -v grep | head -20
echo "=== NPROC ==="
ps -eo comm 2>/dev/null | grep -c '^flash4$'
echo "=== NXB IN MAKEFILE ==="
OBJ="$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
grep -m1 -oE 'DNXB=[0-9]+' "$OBJ/Makefile" 2>/dev/null || echo "(objdir 未生成)"
echo "=== FLASH4 BINARY ==="
ls -la "$OBJ/flash4" 2>/dev/null || echo "(无 flash4)"
echo "=== DEPLOY DIR ==="
ls -la "$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_deploy" 2>/dev/null | head -30
echo "=== LOG TAIL ==="
LOG=$(ls -t "$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_deploy"/run_*_out.txt 2>/dev/null | head -1)
echo "logfile=$LOG"
[ -n "$LOG" ] && tail -c 1200 "$LOG"
echo
echo "=== T STEP TRACE (last 12) ==="
[ -n "$LOG" ] && grep -E '^ *[0-9]+ ' "$LOG" | tail -12
echo "=== ERRORS ==="
[ -n "$LOG" ] && grep -icE 'ERROR|abort|nan' "$LOG"
echo "=== CHK COUNT ==="
find "$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_deploy" "$HOME/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj" -maxdepth 3 -name '*_chk_*' 2>/dev/null | wc -l
echo "=== PROBE_END ==="
"""


def main():
    out, err, rc = run(SCRIPT)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)
        if err:
            fh.write("\n--- stderr ---\n" + err)
    print(out)
    if err.strip():
        print("[stderr]", err[-600:])


main()
