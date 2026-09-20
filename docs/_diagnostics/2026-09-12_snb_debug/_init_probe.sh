#!/bin/bash
OBJ=/root/QC/FLASH/FLASHSNB/FLASH4.8/SNBOneCH_ml_ug_obj
cd "$OBJ" || exit 9
echo "=== 文件清单 ==="
ls -la snbonechug_hdf5_plt_cnt_0000 snbonechug_hdf5_chk_0000 2>&1
echo
echo "=== 初始 plt 中的变量 ==="
python3 - <<'PYEOF'
import h5py, numpy as np
f = h5py.File("snbonechug_hdf5_plt_cnt_0000", "r")
print("keys:", sorted(list(f.keys()))[:40])
if "real scalars" in f:
    for k in f["real scalars"][:]:
        name = k[0].decode() if isinstance(k[0], bytes) else str(k[0])
        print("SCALAR", name, k[1])
have = [n for n in ["dens","pres","temp","velx","vely","velz","tele","tion","sumy","ye","nele","nion"] if n in f]
print("HAVE:", have)
for n in have:
    d = f[n][:]
    print(f"{n:6s} shape={d.shape} min={np.nanmin(d):.6e} max={np.nanmax(d):.6e}")
f.close()
PYEOF
