"""检查 snbonech_ml.par 的关键参数 (初态/SNB/网格/激光/温度)。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
DEPLOY = f"$HOME/{user}/SNBOneCH_ml_deploy"
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

KEYS = ["dtmax", "dtmin", "cfl", "tmax", "tinitial", "iProcs", "nblockx",
        "gr_hypreUseFloor", "gr_hypreFloor", "gr_hypreSolverType",
        "gr_hypreIter", "gr_hypreRelTol", "hypre_abstol",
        "diff_eleFlMode", "diff_eleFlCoef", "diff_eleXlBoundaryType",
        "diff_eleXrBoundaryType", "diff_eleFlBoundaryType",
        "mgd_meshgroups", "mgd_normtype", "mgd_snbtabulated",
        "eos_singleSpeciesA", "eos_singleSpeciesZ",
        "refine_var", "turn_on_burn", "energyDeposition",
        "ed_maxPulseSections", "ed_numberOfSections", "laser",
        "sim_xmin", "sim_xmax", "sim_zmin", "smallpres", "smalltemp",
        "hydrogenMassFraction"]
cmds = [("par_keys", f"grep -nE '^({'|'.join(KEYS)})[[:space:]]*=' {DEPLOY}/snbonech_ml.par 2>&1 | head -60"),
        ("laser_sec", f"grep -nA3 'ed_numberOfSections' {DEPLOY}/snbonech_ml.par 2>&1 | head -20"),
        ("par_size", f"wc -l {DEPLOY}/snbonech_ml.par")]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip())
        lines.append("")
(FLASH_ROOT / "_nce_par_keys.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
