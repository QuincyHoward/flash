"""读取 chk_0000 (初始条件) 的物理场, 判定初始态是否已非物理。

用 h5py 直读 (非 yt): +ug 下全为叶子块, 无需 leaf 过滤。
"""
import sys
from pathlib import Path

import numpy as np
import h5py

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
sys.path.insert(0, str(FLASH_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402
from flash.scenarios.runner import get_sim_user_dir  # noqa: E402

user = get_sim_user_dir()
OBJ = f"$HOME/{user}/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj"
LOC = FLASH_ROOT / "_nce_chk0000.h5"

lines = []
with RemoteSession(credential_name="flash_ssh", verbose=False) as s:
    ok = s.download(f"{OBJ}/snbonechug_hdf5_chk_0000", str(LOC))
    lines.append(f"download chk_0000: {ok}  size={LOC.stat().st_size if LOC.exists() else -1}")

if LOC.exists():
    with h5py.File(str(LOC), "r") as f:
        lines.append("top keys: " + ", ".join(list(f.keys())[:12]))
        # 块结构
        nb = f["/number of blocks"][()] if "/number of blocks" in f else None
        lines.append(f"number of blocks = {nb}")
        # 变量逐个统计
        for v in ["dens", "pres", "temp", "tele", "tion", "velx", "ye", "sumy",
                  "nele", "nion"]:
            if v not in f:
                lines.append(f"  {v:6s}: <absent>")
                continue
            try:
                d = f[v][()]
                d = np.asarray(d)
                lines.append(f"  {v:6s}: shape={d.shape} min={np.nanmin(d):.6e} "
                             f"max={np.nanmax(d):.6e} nan={int(np.isnan(d).sum())}")
            except Exception as e:  # noqa: BLE001
                lines.append(f"  {v:6s}: ERR {e}")
        # 坐标
        if "coordinates" in f:
            c = np.asarray(f["coordinates"][()]).ravel()
            lines.append(f"  coord: n={c.size} min={c.min():.6e} max={c.max():.6e} "
                         f"dx={c[1]-c[0]:.6e}")
        # 诊断变量 (SNB)
        dk = [k for k in f.keys() if k.startswith(("qesh", "mgd", "sh_", "diff"))]
        lines.append("  diag vars: " + ", ".join(dk[:14]))

LOC_out = FLASH_ROOT / "_nce_chk0000_report.txt"
LOC_out.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
