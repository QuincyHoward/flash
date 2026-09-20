"""专项: gr_hypre* 全部键 + 诊断变量键 + 边界 (SNB 崩塌三前提核查)。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
DEPLOY = f"$HOME/{user}/SNBOneCH_ml_deploy"

cmds = [
 ("hypre_all", f"grep -nE 'gr_hypre' {DEPLOY}/snbonech_ml.par 2>&1"),
 ("mgd_all", f"grep -nE '^mgd_' {DEPLOY}/snbonech_ml.par 2>&1 | head -30"),
 ("diff_all", f"grep -nE '^diff_' {DEPLOY}/snbonech_ml.par 2>&1"),
 ("eos_all", f"grep -nE '^eos_' {DEPLOY}/snbonech_ml.par 2>&1 | head -25"),
 ("ed_power", f"grep -nE 'ed_(power|pulse|time|wavelength|irrad|beam)' {DEPLOY}/snbonech_ml.par 2>&1 | head -20"),
 ("turn_on", f"grep -nE 'turn_on|useLaser|laser' {DEPLOY}/snbonech_ml.par 2>&1 | head -20"),
 ("refine", f"grep -nE 'refine|derefine|lrefine' {DEPLOY}/snbonech_ml.par 2>&1 | head -25"),
 ("grid", f"grep -nE '^geometry|^xmin|^xmax|^nblock|^nxb|^iProcs|^iprocs' {DEPLOY}/snbonech_ml.par 2>&1"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_nce_par_full.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
