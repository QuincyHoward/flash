"""WSL 侧进度探针: 检查 SNBOneCH_ml_ug_obj 编译/运行状态。"""
import subprocess, os, time

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_probe.txt"
OBJ = "~/QC/FLASH/FLASHSNB/FLASH4.8/object/SNBOneCH_ml_ug_obj"

CMDS = [
    ("tree_root", "ls -d ~/QC/FLASH/FLASHSNB/FLASH4.8 2>&1 | head -3"),
    ("objdir_exists", f"test -d {OBJ} && echo YES || echo NO"),
    ("flash4", f"ls -la {OBJ}/flash4 2>&1 | head -3"),
    ("obj_count", f"ls {OBJ} 2>/dev/null | wc -l"),
    ("o_count", f"ls {OBJ}/*.o 2>/dev/null | wc -l"),
    ("flash4_procs", "ps -eo comm,etime,pcpu 2>/dev/null | grep -E 'flash4|f95|gfortran|make' | head -15"),
    ("recent_files", f"find {OBJ} -newermt '-6 minutes' -type f 2>/dev/null | head -15"),
    ("scenario_units", "ls ~/QC/FLASH/FLASHSNB/FLASH4.8/Simulation/SimulationMain/ 2>/dev/null | grep -i snbonech"),
    ("ug_par", "ls -la ~/snbonechug_* 2>/dev/null | head -10"),
    ("out_files", "ls -la ~/SNBOneCH_ml*/ ~/snbonech* 2>/dev/null | head -20"),
]

lines = [f"# WSL probe {time.strftime('%F %T')}", ""]
for name, cmd in CMDS:
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", cmd],
                           capture_output=True, text=True, errors="replace", timeout=60)
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
