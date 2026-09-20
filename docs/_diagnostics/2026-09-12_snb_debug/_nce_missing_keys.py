"""核查 par 生成源与缺失键: 对比 SNB 包 Config 的 REQUESTS 与场景 par。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
DEPLOY = f"$HOME/{user}/SNBOneCH_ml_deploy"
SNB = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8"

cmds = [
 ("local_grep_count", f"grep -c '' {DEPLOY}/snbonech_ml.par; echo '--- total lines above'"),
 ("hypre_any", f"grep -icE 'hypre|floor' {DEPLOY}/snbonech_ml.par"),
 ("mgd_any", f"grep -icE 'mgd' {DEPLOY}/snbonech_ml.par"),
 ("head_20", f"head -20 {DEPLOY}/snbonech_ml.par"),
 ("ref_unit_par", f"ls {SNB}/source/Simulation/SimulationMain/SNB_1D_laser/*.par 2>&1"),
 ("ref_hypre", f"grep -nE 'gr_hypreUseFloor|gr_hypreFloor|dtmax' "
               f"{SNB}/source/Simulation/SimulationMain/SNB_1D_laser/flash.par 2>&1"),
 ("ref_mgd", f"grep -cE '^mgd_' {SNB}/source/Simulation/SimulationMain/SNB_1D_laser/flash.par 2>&1"),
 ("ref_mgd_sample", f"grep -E '^mgd_' {SNB}/source/Simulation/SimulationMain/SNB_1D_laser/flash.par 2>&1 | head -12"),
 ("unit_cn4", f"ls -la {SNB}/source/Simulation/SimulationMain/SNBOneCH_ml/*.cn4 2>&1"),
]
lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    for label, cmd in cmds:
        out, err, rc = s.run(cmd, timeout=60)
        lines.append(f"── {label} (rc={rc}) ──")
        lines.append((out or "").rstrip() or "(EMPTY)")
        lines.append("")
(FLASH_ROOT / "_nce_missing_keys.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
