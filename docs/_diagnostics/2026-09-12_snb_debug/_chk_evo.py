# -*- coding: utf-8 -*-
"""读多个 chk, 看边界单元 (-0.04 附近) 的 tele/velx/dens 演化。"""
import h5py, numpy as np, os, glob

D = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output"
chks = sorted(glob.glob(os.path.join(D, "snbonechug_hdf5_chk_*")))
print(f"chk 数量: {len(chks)}")
show = chks[:1] + chks[len(chks)//2:len(chks)//2+1] + chks[-1:]

for path in show:
    print("=" * 72)
    print(os.path.basename(path))
    with h5py.File(path, "r") as f:
        keys = set(f.keys())
        # 时间
        t = None
        if "real scalars" in f:
            for row in f["real scalars"][:]:
                nm = row[0].decode() if isinstance(row[0], bytes) else str(row[0])
                if nm.lower() in ("time", "sim time", "simulation time"):
                    t = row[1]
        print(f"  time = {t}")
        # 坐标
        if "coordinates" in f:
            c = f["coordinates"][:]
            print(f"  coords: nblocks={c.shape[0]} xmin={c[:,0].min():.5e} xmax={c[:,0].max():.5e}")
        for v in ("dens", "tele", "tion", "trad", "velx", "pres", "sumy", "ye", "nele"):
            if v not in keys:
                continue
            d = f[v][:]
            fin = d[np.isfinite(d)]
            neg = int((fin < 0).sum())
            print(f"  {v:6s} n={d.size:5d} min={fin.min():+.6e} max={fin.max():+.6e} neg={neg}")
        # 速度最大单元位置
        if "velx" in keys:
            d = f["velx"][:]
            i = int(np.nanargmax(np.abs(d)))
            print(f"  |velx|max at flat-index {i} = {d.flat[i]:+.6e}")
    print()
