"""清理 WSL 侧超订残留输出 + 确认状态。"""
import subprocess

BASE = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
CMDS = [
    ("cleanup", f"rm -f {BASE}/snbonechug_* {BASE}/wsl_run_snbonech.log; echo CLEANED"),
    ("verify", f"ls {BASE}/snbonechug_* 2>/dev/null | wc -l"),
    ("procs", "pgrep -c -f '[f]lash4' || echo 0"),
]
for name, cmd in CMDS:
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", cmd],
                       capture_output=True, text=True, errors="replace", timeout=120)
    print(f"### {name}: {(r.stdout or '').strip()} {(r.stderr or '').strip()}")
