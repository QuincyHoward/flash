"""取消当前已发散的 NC-E 作业, 并清理 objdir 输出 (幂等: 不删除源码/objdir 本身)。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

cmds = [
 ("cancel_all", "scancel -u $(whoami) --me 2>&1; echo CANCEL_RC=$?"),
 ("squeue_after", "sleep 3; squeue -u $(whoami) -o '%.10i %.20j %.8T' 2>&1"),
 ("clean_out", f"cd {OBJ} && rm -f snbonechug_* wsl_run_snbonech.log _t_start _t_end 2>&1; echo CLEAN_DONE; ls snbonechug_* 2>&1 | head -3"),
 ("keep_flash4", f"ls -la {OBJ}/flash4 2>&1"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=120)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_nce_cancel.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
