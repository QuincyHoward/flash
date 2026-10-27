import os, json
from pathlib import Path
import numpy as np
import h5py

CP = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_output\hpc_flash_ssh\cores_parallel")
f = CP / "n131" / "snbonechug_hdf5_chk_0000"

with h5py.File(str(f), "r") as h:
    c = h["coordinates"][:]
    xtop = np.sort(c[:, 0])
    dxtop = np.diff(xtop) * 1e4
    print("nblocks:", len(xtop))
    print("coords sorted x (um) first 6:", np.round(xtop[:6]*1e4, 6))
    print("coords sorted x (um) last 6 :", np.round(xtop[-6:]*1e4, 6))
    print("unique diffs (um):", np.unique(np.round(dxtop, 6)))
    print("expected uniform dx_top = 500um/131 =", 500/131)

    b = h["bounding box"][:]
    print("\nbounding box block0:", b[0]*1e4, " block-1:", b[-1]*1e4)

    bs = h["block size"][:, 0] * 1e4
    print("\nblock size (um) unique:", np.unique(np.round(bs, 9)))
    print("block size * 128 (um) =", np.unique(np.round(bs*128, 6)))

    rl = h["refine level"][:]
    print("\nrefine level unique:", np.unique(rl))
    print("refine level hist :", dict(zip(*np.unique(rl, return_counts=True))))
