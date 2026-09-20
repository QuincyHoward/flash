"""取参考单元 SNB_1D_laser/flash.par 的关键参数作为"作者可用基线"对照。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
REF = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/source/Simulation/SimulationMain/SNB_1D_laser/flash.par"

KEYS = ["gr_hypreUseFloor", "dtmax", "cfl", "tstep_change_factor", "useDiffuse",
        "sim_teleCham", "eos_chamTableFile", "sim_rhoCham", "iProcs", "nblockx",
        "smallt", "diff_eleFlMode", "diff_eleFlCoef", "use_3dFullCTU",
        "eos_maxNewton", "sim_teleSamp", "sim_rhoSamp", "sim_teleShld"]
cmds = [("ref_keys", "grep -nE '^(" + "|".join(KEYS) + ")' " + REF + " 2>&1"),
        ("ref_lines", f"wc -l {REF} 2>&1"),
        ("ref_hypre_all", f"grep -nE 'gr_hypre' {REF} 2>&1"),
        ("ref_diff_all", f"grep -nE '^diff_|^useDiff' {REF} 2>&1"),
        ("ref_boundary", f"grep -nE 'BoundaryType|^xl_|^xr_' {REF} 2>&1 | head -20"),
       ]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_ref_par.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
