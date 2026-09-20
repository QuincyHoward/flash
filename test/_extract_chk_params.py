# -*- coding: utf-8 -*-
"""从 _dl_test/chk0000_test.h5 提取运行时参数 + 变量清单 + 头部标量"""
import h5py

CHK = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_dl_test\chk0000_test.h5"

with h5py.File(CHK, "r") as f:
    keys = list(f.keys())
    print("=== ALL ROOT KEYS (%d) ===" % len(keys))
    print(keys)

    for name in ("real scalars", "integer scalars",
                 "real runtime parameters", "integer runtime parameters",
                 "logical runtime parameters", "string runtime parameters"):
        if name in f:
            print("\n=== %s ===" % name.upper())
            d = f[name]
            names = [n.decode() if isinstance(n, bytes) else n for n in d["name"][:]]
            vals = d["value"][:]
            for n, v in zip(names, vals):
                v2 = v.decode() if isinstance(v, bytes) else v
                if isinstance(v2, float):
                    print(f"  {n} = {v2:.10g}")
                else:
                    print(f"  {n} = {v2}")
        else:
            print("\n=== %s : ABSENT ===" % name.upper())

    if "unknown names" in f:
        unk = f["unknown names"][:]
        names = [n.decode() if isinstance(n, bytes) else n for n in unk]
        print("\n=== UNKNOWN NAMES (%d) ===" % len(names))
        print(names)
    else:
        # per-variable layout: variable datasets are the non-structural keys
        structural = {"block size", "bounding box", "coordinates", "gid",
                      "node type", "refine level", "which child",
                      "unknown names", "unknown cvars", "unknown facevarsx",
                      "unknown facevarsy", "unknown facevarsz",
                      "real scalars", "integer scalars", "real runtime parameters",
                      "integer runtime parameters", "logical runtime parameters",
                      "string runtime parameters", "file format version",
                      "sim info", "setup call", "physics", "packages",
                      "memory stat", "particle attributes", "striped hdf5"}
        vars_present = [k for k in keys if k not in structural]
        print("\n=== VARIABLE DATASETS (%d) ===" % len(vars_present))
        print(vars_present)
