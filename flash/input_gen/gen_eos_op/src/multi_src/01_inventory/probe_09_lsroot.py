# -*- coding: utf-8 -*-
"""probe_09_lsroot: list Multi1D++ root, find C/C++ sources outside matter++."""
import os, io, json

REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
R = os.path.join(REPO, "src", "Multi1D++Portable20241128")
OUT = os.path.join(REPO, ".workbuddy", "tmp", "out_09.txt")

buf = []
buf.append("isdir=%s" % os.path.isdir(R))
if os.path.isdir(R):
    items = sorted(os.listdir(R))
    buf.append("top entries (%d):" % len(items))
    for it in items:
        p = os.path.join(R, it)
        buf.append("  %-40s %s" % (it, "DIR" if os.path.isdir(p) else "file"))

    # find sources
    exts = (".c", ".cpp", ".h", ".hpp", ".H", ".C", ".cc", ".cxx")
    hits = []
    for dp, dn, fn in os.walk(R):
        low = dp.replace("\\", "/").lower()
        if "/matter++" in low or "/doc" in low or "/.git" in low or "/interface" in low:
            continue
        for f in fn:
            if f.endswith(exts):
                hits.append(os.path.join(dp, f))
    buf.append("\nC/C++ sources outside matter++/doc: %d" % len(hits))
    for h in sorted(hits):
        buf.append("  " + h.replace(R, "."))

open(OUT, "w", encoding="utf-8").write("\n".join(buf))
print("written", OUT)
