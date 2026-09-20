"""诊断 chk_0000 下载问题: 远端大小 vs 本地大小, 打印文件头字节。"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
LOC = FLASH_ROOT / "_nce_chk0000.h5"

lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    out, _, rc = s.run(f"stat -c '%s' {OBJ}/snbonechug_hdf5_chk_0000 2>&1", timeout=30)
    lines.append(f"remote size: {out.strip()} (rc={rc})")
    out, _, rc = s.run(f"ls -la {OBJ}/ | head -20", timeout=30)
    lines.append("ls:\n" + out)
    # 重新下载到不同文件名
    L2 = FLASH_ROOT / "_nce_chk0000_v2.h5"
    ok = s.download(f"{OBJ}/snbonechug_hdf5_chk_0000", str(L2))
    lines.append(f"re-download: {ok} size={L2.stat().st_size if L2.exists() else -1}")

for p in [LOC, FLASH_ROOT / "_nce_chk0000_v2.h5"]:
    if p.exists():
        with open(p, "rb") as fh:
            head = fh.read(16)
        lines.append(f"{p.name}: size={p.stat().st_size} head={head!r}")

(FLASH_ROOT / "_nce_dl_diag.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
