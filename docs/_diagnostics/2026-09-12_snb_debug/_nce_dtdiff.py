"""提取运行日志中 dt_Diff 的演化 + 前沿位置, 判断失稳是否空间局域在 He|CH 界面。"""
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
 ("dt_series", f"awk 'NF>7 && $1 ~ /^[0-9]+$/ {{print $1, $2, $3, $(NF-1), $(NF-2)}}' "
               f"{OBJ}/wsl_run_snbonech.log 2>/dev/null | "
               f"awk 'NR%40==1 || NR<8' | head -30"),
 ("x_front", f"awk 'NF>7 && $1 ~ /^[0-9]+$/ {{print $1, $2, $4}}' "
             f"{OBJ}/wsl_run_snbonech.log 2>/dev/null | sed -n '1p;50p;100p;200p;300p;400p'"),
 ("hypre_first10", f"grep -n 'Nonconv' {OBJ}/wsl_run_snbonech.log 2>/dev/null | head -6"),
 ("geometry_par", f"grep -nE '^(geometry|xmin|xmax|nblockx|iProcs|lrefine)' {DEPLOY}/snbonech_ml.par"),
 ("blockcount", f"grep -nE 'number of blocks|nblock' {OBJ}/wsl_run_snbonech.log 2>/dev/null | head -5"),
 ("guardcell", f"grep -nE 'guard|nguard|nguard' {DEPLOY}/snbonech_ml.par 2>&1 | head -8"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_nce_dtdiff.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
