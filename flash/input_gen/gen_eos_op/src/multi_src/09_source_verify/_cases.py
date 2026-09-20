# -*- coding: utf-8 -*-
import os, sys, io, collections, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
R = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"

# 1) section names across all .case files
secs = collections.Counter()
allcase = []
for d in sorted(os.listdir(R)):
    if not d.startswith("cases_"): continue
    p = os.path.join(R, d)
    for dp, dn, fn in os.walk(p):
        for f in fn:
            if f.lower().endswith(".case"):
                allcase.append(os.path.join(dp, f))
for fp in allcase:
    try: txt = open(fp, "rb").read().decode("latin-1")
    except: continue
    for L in txt.splitlines():
        s = L.strip()
        if s.startswith("&"): secs[s] += 1
print("=== .case sections (total %d case files) ===" % len(allcase))
for k, v in secs.most_common(): print("  %-24s %d" % (k, v))
print()

# 2) matlab structure
ml = os.path.join(R, "matlab")
c = collections.Counter(); n = 0; tot = 0
subdirs = collections.Counter()
for dp, dn, fn in os.walk(ml):
    rel = os.path.relpath(dp, ml).replace("\\", "/")
    for f in fn:
        e = os.path.splitext(f)[1].lower() or "<none>"; c[e] += 1; n += 1
        subdirs[rel] += 1
        try: tot += os.path.getsize(os.path.join(dp, f))
        except: pass
print("=== matlab/ : n=%d bytes=%d ===" % (n, tot))
print("ext:", dict(c))
print("top-level entries:", sorted(os.listdir(ml))[:40])
print("subdirs:", dict(subdirs))
