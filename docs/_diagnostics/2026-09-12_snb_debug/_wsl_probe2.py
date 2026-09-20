"""WSL 侧深度探针: 定位 flash4 进程归属 + 本场景实际 objdir。"""
import subprocess, time

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_probe2.txt"

CMDS = [
    ("flash4_cmdlines", "ps -eo pid,etime,args 2>/dev/null | grep '[f]lash4' | head -8"),
    ("flash4_cwd", "for p in $(pgrep -f '[f]lash4' | head -3); do echo \"PID $p: $(readlink /proc/$p/cwd 2>/dev/null)\"; done"),
    ("all_objdirs", "ls -dt /root/QC/FLASH/FLASHSNB/FLASH4.8/object/*/ 2>/dev/null | head -20"),
    ("snb1ch_obj", "ls -la /root/QC/FLASH/FLASHSNB/FLASH4.8/object/SNBOneCH_obj/ 2>/dev/null | head -8"),
    ("py_procs", "ps -eo pid,etime,args 2>/dev/null | grep '[S]NBOneCH_ml.py' | head -5"),
    ("setup_procs", "ps -eo pid,etime,args 2>/dev/null | grep -E '[s]etup|[m]ake|[g]fortran' | head -10"),
    ("snb_tree_recent", "find /root/QC/FLASH/FLASHSNB/FLASH4.8/object -maxdepth 1 -newermt '-30 minutes' 2>/dev/null | head -10"),
    ("home_recent", "find /root -maxdepth 1 -newermt '-30 minutes' 2>/dev/null | head -20"),
    ("checkpoint_out", "ls -dt /root/QC/FLASH/FLASHSNB/FLASH4.8/*snbonech* /root/*snbonech* 2>/dev/null | head -10"),
]

lines = [f"# WSL deep probe {time.strftime('%F %T')}", ""]
for name, cmd in CMDS:
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", cmd],
                           capture_output=True, text=True, errors="replace", timeout=90)
        body = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        lines.append(f"### {name}")
        lines.append(body if body else "(empty)")
        if err:
            lines.append(f"[stderr] {err}")
        lines.append("")
    except Exception as e:
        lines.append(f"### {name}\n[EXC] {e!r}\n")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT)
