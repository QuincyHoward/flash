"""停止 WSL 上的 131 核超订运行 (infinite-time due to oversubscription)。"""
import subprocess

CMDS = [
    ("kill_mpi", "pkill -f 'mpiexec -n 131' ; pkill -f '[f]lash4' ; echo KILL_SENT"),
    ("verify", "sleep 3; pgrep -c -f '[f]lash4' || echo 0"),
]

for name, cmd in CMDS:
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", cmd],
                       capture_output=True, text=True, errors="replace", timeout=120)
    print(f"### {name}\n{(r.stdout or '').strip()}\n{(r.stderr or '').strip()}\n")
