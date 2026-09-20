"""WSL 状态检查 + 清理旧 objdir 残留 (幂等, 不删源码/objdir 本身)。"""
import subprocess
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
out_lines = []


def wsl(cmd, timeout=120):
    p = subprocess.run(["wsl", "-d", "Ubuntu", "-e", "bash", "-lc", cmd],
                       capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or ""), p.returncode


for label, cmd in [
    ("cores", "nproc; grep -c ^processor /proc/cpuinfo"),
    ("loadavg", "cat /proc/loadavg"),
    ("flash4_procs", "pgrep -c flash4 2>/dev/null || echo 0"),
    ("snb_home", "ls -d ~/FLASH/FLASHSNB/FLASH4.8 2>&1 | head -2"),
    ("objdir", "ls -d ~/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj 2>&1"),
    ("objdir_out", "ls ~/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/snbonech* 2>/dev/null | head -5; echo ---"),
    ("flash4_bin", "ls -la ~/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/flash4 2>&1"),
]:
    try:
        o, rc = wsl(cmd)
    except Exception as e:  # noqa: BLE001
        o, rc = f"EXC {e}", -1
    out_lines.append(f"── {label} (rc={rc}) ──")
    out_lines.append(o.strip() or "(EMPTY)")
    out_lines.append("")

(FLASH_ROOT / "_wsl_state.txt").write_text("\n".join(out_lines), encoding="utf-8")
print("WROTE")
