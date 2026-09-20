"""WSL 侧运行状态探针 (修正路径: objdir 直接在 FLASHSNB 根下)。"""
import subprocess, time

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_wsl_probe3.txt"
BASE = "/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

CMDS = [
    ("objdir", f"ls -d {BASE} && echo EXISTS"),
    ("flash4", f"ls -la {BASE}/flash4"),
    ("obj_files", f"ls {BASE} | head -12 && echo '--- count:' && ls {BASE} | wc -l"),
    ("runlog_tail", f"tail -40 {BASE}/wsl_run_snbonech.log 2>&1"),
    ("runlog_grep", f"grep -E 'step|SimTime|dt=|reached|RUN_EXIT|Error|ABORT|negative' {BASE}/wsl_run_snbonech.log 2>/dev/null | tail -30"),
    ("outputs", f"ls -la {BASE}/snbonechug_* 2>/dev/null | tail -20"),
    ("output_count", f"ls {BASE}/snbonechug_* 2>/dev/null | wc -l"),
    ("par_check", f"grep -E 'tmax|dtmax|iProcs|nblockx|gr_hypreUseFloor|diff_eleFlMode' {BASE}/snbonech_ml.par 2>/dev/null | head -20"),
    ("simtime", f"ls -la {BASE}/snbonechug_chk_* 2>/dev/null | tail -5"),
]

lines = [f"# WSL run probe {time.strftime('%F %T')}", ""]
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
