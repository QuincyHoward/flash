"""远端就地分析初始 chk: 用远端 python3 + h5py 统计 dens/pres/temp 极值。
避免 10MB SFTP 下载不稳定问题。
"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"

RPROBE = f"""python3 - <<'PYEOF'
import h5py, numpy as np
p = "{OBJ}/snbonechug_hdf5_chk_0000"
f = h5py.File(p, "r")
print("keys:", len(list(f.keys())))
print("nblocks:", f["/number of blocks"][()] if "/number of blocks" in f else "?")
for v in ["dens","pres","temp","tele","tion","ye","sumy","velx","nele","nion"]:
    if v not in f:
        print(f"  {{v:6s}} <absent>"); continue
    d = np.asarray(f[v][()])
    print(f"  {{v:6s}} shape={{d.shape}} min={{np.nanmin(d):.6e}} max={{np.nanmax(d):.6e}} nan={{int(np.isnan(d).sum())}}")
c = np.asarray(f["coordinates"][()]).ravel()
print("coord: n=%d min=%.6e max=%.6e dx=%.6e" % (c.size, c.min(), c.max(), c[1]-c[0]))
dk = sorted([k for k in f.keys() if k.startswith(("qesh","mgd","sh_","diff","eos"))])
print("diag:", dk[:16])
PYEOF"""

lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    # 远端 python
    out, err, rc = s.run("which python3 || which python", timeout=30)
    lines.append(f"python: {out.strip()} (rc={rc}, err={err.strip()[:100]})")
    out, err, rc = s.run("python3 -c 'import h5py,numpy; print(\"h5py OK\")' 2>&1", timeout=60)
    lines.append(f"h5py probe: {out.strip()[:200]} (rc={rc})")
    out, err, rc = s.run(RPROBE, timeout=180)
    lines.append(f"── chk_0000 stats (rc={rc}) ──")
    lines.append(out or "")
    if err and err.strip():
        lines.append("[stderr] " + err.strip()[:400])

(FLASH_ROOT / "_nce_chk_remote.txt").write_text("\n".join(lines), encoding="utf-8")
print("WROTE")
