# -*- coding: utf-8 -*-
"""Enumerate the 150 no-extension data files under matter++/ and dump first-line signatures."""
import os, json
root = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
mat = os.path.join(root, "src", "Multi1D++Portable20241128", "matter++")
print("matter++ exists:", os.path.isdir(mat))
if not os.path.isdir(mat):
    # try to find
    for d, sds, fns in os.walk(os.path.join(root, "src")):
        if d.endswith("matter++"):
            mat = d
            print("found at", d)
            break

# bookkeeping names to EXCLUDE? No - include all, they are group G
rows = []
for dirpath, dirnames, filenames in os.walk(mat):
    for fn in filenames:
        if os.path.splitext(fn)[1] == "":
            fp = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(fp)
            except Exception:
                sz = -1
            rel = os.path.relpath(fp, mat).replace("\\", "/")
            rows.append((rel, sz, fn))
rows.sort()
print("TOTAL no-extension files under matter++/:", len(rows))
os.makedirs(os.path.join(root, ".workbuddy", "tmp", "probe_noext"), exist_ok=True)
with open(os.path.join(root, ".workbuddy", "tmp", "probe_noext", "noext_list.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
for rel, sz, fn in rows:
    print(f"{sz:>10}  {rel}")
