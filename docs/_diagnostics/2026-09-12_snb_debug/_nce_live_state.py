"""直查 NC-E 远端状态: 部署目录绝对路径 + 内容 + 作业队列。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
sys.path.insert(0, str(FLASH_ROOT / "flash"))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
DEPLOY = f"$HOME/{user}/SNBOneCH_ml_deploy"

lines = [f"SIM_USER_DIR = {user}", f"DEPLOY = {DEPLOY}", ""]
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in [
        ("HOME", "printf '%s\\n' \"$HOME\""),
        ("USER", "whoami"),
        ("deploy_ls", f"ls -la {DEPLOY}/ 2>&1"),
        ("tilde_dir", "ls -la ./~ 2>&1 | head -20"),
        ("squeue", "squeue -u $(whoami) -o '%.10i %.20j %.8T %.10M' 2>&1"),
        ("objdir", f"ls -d {DEPLOY} 2>&1; ls -la $HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj/flash4 2>&1"),
        ("build_out", f"ls -t {DEPLOY}/build_*_out.txt 2>/dev/null | head -1 | xargs -r tail -25"),
        ("sacct", "sacct -u $(whoami) --starttime today --format=JobID,JobName%16,State,Elapsed --noheader 2>/dev/null | tail -12"),
    ]:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip())
        if err and err.strip():
            lines.append(f"[stderr] {err.strip()[:300]}")
        lines.append("")

Path(FLASH_ROOT / "_nce_live_state.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
