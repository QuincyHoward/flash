"""WSL 性能诊断: 131 核超订检测 + 步进速率。"""
import subprocess, time

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_perf.txt"
BASE = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

CMDS = [
    ("cores", "nproc; echo '---'; grep -c ^processor /proc/cpuinfo"),
    ("loadavg", "cat /proc/loadavg"),
    ("flash4_count", "pgrep -c -f '[f]lash4'"),
    ("steplines", f"grep -E '^ *[0-9]+ ' {BASE}/wsl_run_snbonech.log 2>/dev/null | tail -15"),
    ("step_count", f"grep -cE '^ *[0-9]+ ' {BASE}/wsl_run_snbonech.log 2>/dev/null"),
    ("log_size", f"ls -la {BASE}/wsl_run_snbonech.log"),
    ("chk_count", f"ls {BASE}/snbonechug_hdf5_chk_* 2>/dev/null | wc -l"),
    ("mem", "free -g | head -2"),
]

lines = [f"# WSL perf probe {time.strftime('%F %T')}", ""]
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
