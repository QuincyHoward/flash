"""核查远端运行中 par 是否含 gr_hypreUseFloor, 并看运行日志是否已稳定。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
DEPLOY = f"$HOME/{user}/SNBOneCH_ml_deploy"

cmds = [
 ("objdir_par_hypre", f"grep -nE 'gr_hypreUseFloor|^dtmax' {OBJ}/flash.par 2>&1"),
 ("objdir_par_mtime", f"ls -la {OBJ}/flash.par 2>&1"),
 ("deploy_par_hypre", f"grep -nE 'gr_hypreUseFloor' {DEPLOY}/snbonech_ml.par 2>&1"),
 ("runlog_tail", f"tail -18 {OBJ}/wsl_run_snbonech.log 2>&1"),
 ("runlog_first", f"sed -n '100,130p' {OBJ}/wsl_run_snbonech.log 2>&1"),
 ("hypre_fail", f"grep -c 'Nonconv' {OBJ}/wsl_run_snbonech.log 2>/dev/null"),
 ("maxsum", f"awk 'NF>7 && $(NF-2)+0 > 1e10 {{c++}} END {{print \"blast_lines=\"c+0}}' "
            f"{OBJ}/wsl_run_snbonech.log 2>&1"),
 ("laststep", f"tail -3 {OBJ}/wsl_run_snbonech.log 2>&1"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_nce_verify_fix.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
