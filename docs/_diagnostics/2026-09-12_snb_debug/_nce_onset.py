"""定位失稳起始点: 找首帧出现非物理量级 (>=1e10) 的步数, 并比对 chk 帧的 ρmax/Tmax。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

# 逐列: step | time | dt | coords | dt2 | sum1 | sum2 | cfl
cmds = [
    ("head_30", f"head -40 {OBJ}/wsl_run_snbonech.log 2>&1"),
    ("first_blast", f"awk 'NF>6 && $(NF-2)+0 > 1e10 {{print NR\": \"$0; exit}}' "
                    f"{OBJ}/wsl_run_snbonech.log 2>&1"),
    ("grep_nan", f"grep -inE 'nan|inf|abort|negative' {OBJ}/wsl_run_snbonech.log 2>/dev/null | head -8"),
    ("hypre_fail_count", f"grep -c 'Nonconv' {OBJ}/wsl_run_snbonech.log 2>/dev/null"),
    ("hypre_first", f"grep -n 'Nonconv' {OBJ}/wsl_run_snbonech.log 2>/dev/null | head -3"),
    ("laser_prof", f"cat {OBJ}/snbonechug_LaserEnergyProfile.dat 2>/dev/null | tail -5"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip())
        lines.append("")

Path(FLASH_ROOT / "_nce_onset.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
