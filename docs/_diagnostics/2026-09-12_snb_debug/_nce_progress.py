"""查看 NC-E 运行日志尾部: 步数/dt/ρmax (判定是否正常推进)。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

cmds = [
    ("log_tail", f"tail -25 {OBJ}/wsl_run_snbonech.log 2>&1"),
    ("step_count", f"grep -c 'step:' {OBJ}/wsl_run_snbonech.log 2>/dev/null"),
    ("max_step", f"grep -oE 'step: *[0-9]+' {OBJ}/wsl_run_snbonech.log 2>/dev/null | tail -1"),
    ("dt_vals", f"grep -oE 'dt *=[^,]*' {OBJ}/wsl_run_snbonech.log 2>/dev/null | tail -5"),
    ("outputs", f"ls -la {OBJ}/snbonechug_* 2>/dev/null | tail -8"),
    ("err_tail", f"tail -15 {OBJ}/wsl_run_snbonech.log 2>&1 | grep -iE 'error|nan|abort|warn' | tail -6"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip())
        lines.append("")

Path(FLASH_ROOT / "_nce_progress.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
