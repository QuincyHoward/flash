# -*- coding: utf-8 -*-
"""读初始 chk/plt, 诊断初始条件 (先 plt 0000 快速看)。"""
import h5py, numpy as np, os, sys

D = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output"

def probe(path, label):
    print("=" * 70)
    print(f"### {label}: {os.path.basename(path)}  ({os.path.getsize(path)/1e6:.2f} MB)")
    print("=" * 70)
    with h5py.File(path, "r") as f:
        keys = sorted(f.keys())
        # 标量
        if "real scalars" in f:
            for row in f["real scalars"][:]:
                nm = row[0].decode() if isinstance(row[0], bytes) else str(row[0])
                if nm.lower() in ("time", "dt", "dtmin", "dtmax", "tmax", "nstep",
                                  "sim time", "simulation time", "timestep"):
                    print(f"   SCALAR {nm:20s} = {row[1]:.6e}")
        # 变量
        cands = ["dens", "pres", "temp", "velx", "vely", "velz",
                 "tele", "tion", "trad", "sumy", "ye", "nele", "nion",
                 "ener", "eint", "game", "gamc", "eos_gamc", "magx", "magy", "magz"]
        have = [n for n in cands if n in f]
        print(f"   vars({len(have)}): {have}")
        for n in have:
            d = f[n][:].ravel()
            fin = d[np.isfinite(d)]
            print(f"     {n:8s} n={d.size:6d} min={fin.min():+.6e} max={fin.max():+.6e}"
                  f"  nan={int(np.isnan(d).sum())} nonfinite={int((~np.isfinite(d)).sum())}")
        # 坐标
        for g in ("coordinates", "node type", "block size", "bounding box",
                  "gid", "refine level"):
            if g in f:
                a = f[g][:]
                print(f"   {g:14s} shape={a.shape} "
                      + (f"min={np.min(a):.6e} max={np.max(a):.6e}" if a.size and np.issubdtype(a.dtype, np.number) else ""))
    print()

probe(os.path.join(D, "snbonechug_hdf5_plt_cnt_0000"), "INITIAL PLT")
