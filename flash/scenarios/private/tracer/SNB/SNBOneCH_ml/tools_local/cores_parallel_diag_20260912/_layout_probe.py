import os, json
from pathlib import Path
import numpy as np
import h5py

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")
f = CP / "n131" / "snbonechug_hdf5_chk_0000"

print("="*100)
print("DIRECT LAYOUT INSPECTION:", f.name)
print("="*100)
with h5py.File(str(f), "r") as h:
    def walk(g, prefix="", depth=0):
        if depth > 2:
            return
        for k in g.keys():
            o = g[k]
            if isinstance(o, h5py.Group):
                print(f"{prefix}{k}/   (group)")
                walk(o, prefix + "  ", depth + 1)
            else:
                print(f"{prefix}{k:28s} shape={str(o.shape):16s} dtype={o.dtype}")
    walk(h)

    print("\n--- coordinates sample (first 5 blocks, cm -> um) ---")
    c = h["coordinates"][:]
    print("shape:", c.shape, "dtype:", c.dtype)
    print(c[:5] * 1e4)

    print("\n--- block size sample ---")
    bs = h["block size"][:]
    print("shape:", bs.shape)
    print(bs[:3])

    print("\n--- real scalars ---")
    rs = h["real scalars"][:]
    for name, val in rs:
        n = name.decode().strip() if isinstance(name, bytes) else str(name).strip()
        print(f"   {n:40s} = {val}")

    print("\n--- integer scalars ---")
    isc = h["integer scalars"][:]
    for name, val in isc:
        n = name.decode().strip() if isinstance(name, bytes) else str(name).strip()
        print(f"   {n:40s} = {val}")

    print("\n--- dens shape/attrs ---")
    d = h["dens"]
    print("shape:", d.shape, "dtype:", d.dtype)
    print("attrs:", dict(d.attrs))
    da = d[:]
    print("da.shape:", da.shape)
    print("dens[:,0,0,:] first block, first 6 cells:", da[0,0,0,:6])
    print("dens min/max:", da.min(), da.max())

    print("\n--- is there a per-cell x dataset? ---")
    for k in h.keys():
        if "coord" in k.lower() or "x" == k.lower() or "pos" in k.lower():
            print("  candidate:", k, h[k].shape)
