# -*- coding: utf-8 -*-
"""① 检查 chk_0000 初始分层的空间结构 (按 x 排序看每格 sumy/ye/dens/tele)。
② 检查 chk_0001 第 1 步后是否已均匀化 (定位破坏发生的时刻)。"""
import h5py, numpy as np, os, glob

D = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output"

def load(path):
    with h5py.File(path, "r") as f:
        keys = set(f.keys())
        out = {}
        for v in ("dens", "tele", "tion", "trad", "velx", "pres", "sumy", "ye",
                  "nele", "nion", "cham", "shld", "samp", "tar1", "tar2", "tar3",
                  "tar4", "tar6"):
            if v in keys:
                out[v] = np.asarray(f[v][:]).ravel()
        if "coordinates" in f:
            out["_coords"] = np.asarray(f["coordinates"][:])
        if "block size" in f:
            out["_bs"] = np.asarray(f["block size"][:])
        return out

for fn in ("snbonechug_hdf5_chk_0000", "snbonechug_hdf5_chk_0001",
           "snbonechug_hdf5_chk_0002", "snbonechug_hdf5_chk_0010"):
    path = os.path.join(D, fn)
    if not os.path.exists(path):
        print(f"(missing {fn})"); continue
    d = load(path)
    print("=" * 78)
    print(fn, "  vars:", sorted(k for k in d if not k.startswith("_")))
    n = len(d["dens"])
    # 打印前 6 / 后 6 格的剖面
    print(f"  {'idx':>5s} {'dens':>12s} {'tele':>12s} {'velx':>12s} {'pres':>12s} {'sumy':>10s} {'ye':>10s}")
    for i in list(range(6)) + list(range(n - 6, n)):
        print(f"  {i:5d} {d['dens'][i]:12.4e} {d['tele'][i]:12.4e} "
              f"{d['velx'][i]:12.4e} {d['pres'][i]:12.4e} "
              f"{d['sumy'][i]:10.3e} {d['ye'][i]:10.3e}")
    # 物种质量分数剖面 (若有)
    for sp in ("cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4", "tar6"):
        if sp in d:
            a = d[sp]
            nz = int((a > 1e-30).sum())
            print(f"    {sp:5s}: nonzero={nz:4d}/{n}  min={a.min():.3e} max={a.max():.3e}")
    print()
