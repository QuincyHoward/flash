import subprocess, os, sys

DISTRO = "Ubuntu-22.04"

def run_wsl(cmd, timeout=120):
    p = subprocess.run(
        ["wsl", "-d", DISTRO, "--", "bash", "-lc", cmd],
        capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out + ("\n[STDERR]\n" + err if err.strip() else "")

# 1) 看当前 flash4 进程
rc, out = run_wsl("ps -eo pid,etimes,pcpu,args | grep -E 'flash4|mpiexec' | grep -v grep")
print("=== 当前 flash4/mpiexec 进程 ===")
print(out.strip() or "(无)")

# 2) 杀掉所有 flash4 / mpiexec
rc, out = run_wsl("pkill -9 -f flash4 ; pkill -9 -f mpiexec ; sleep 2 ; "
                  "ps -eo pid,args | grep -E 'flash4|mpiexec' | grep -v grep | wc -l")
print("=== kill 后残留进程数 ===")
print(out.strip())

# 3) 检查 deploy 目录状态
rc, out = run_wsl("ls -la ~/QC/SNBOneCH_ml_deploy/ 2>&1 | head -30")
print("=== deploy 目录 ===")
print(out.strip())

# 4) 检查 WSL 负载
rc, out = run_wsl("uptime ; echo '---' ; nproc")
print("=== WSL 负载 ===")
print(out.strip())
