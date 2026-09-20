"""核查初态: chk_0000 的 tele/dens/pres 极值 + par 的 sim_tele*/sim_rho* 取值。
用 FLASH 自带 h5dump (远端有) 避免 h5py 缺失与 SFTP 大文件问题。
"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
DEPLOY = f"$HOME/{user}/SNBOneCH_ml_deploy"

RSTAT = f"""python3 - <<'PYEOF'
import struct, sys
# 纯 python 读 HDF5? 不行. 改用 h5dump 若可用, 否则跳过.
PYEOF"""

cmds = [
 ("h5dump_which", "which h5dump h5ls 2>&1"),
 ("h5ls_chk", f"h5ls -r {OBJ}/snbonechug_hdf5_chk_0000 2>&1 | head -40"),
 ("tele_stat", f"h5dump -d /tele -y -w 200 {OBJ}/snbonechug_hdf5_chk_0000 2>&1 | head -30"),
 ("sim_tele_par", f"grep -nE '^sim_tele|^sim_rho|^sim_tion|^sim_trad' {DEPLOY}/snbonech_ml.par 2>&1"),
 ("small_keys", f"grep -nE '^(small|eos_|useDiffuse|use_3d)' {DEPLOY}/snbonech_ml.par 2>&1 | head -30"),
 ("hypre_solver", f"grep -inE 'hypre|solver|reltol|abstol' {DEPLOY}/snbonech_ml.par 2>&1 | head -20"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=90)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_nce_initstate.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
