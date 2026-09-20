# -*- coding: utf-8 -*-
import os, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
R = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"
M = os.path.join(R, "matter++")
DIRS = """mat_Bi mat_CH2 mat_CHBr mat_Cl mat_Co mat_Cr mat_Dy mat_F mat_Gd mat_He
mat_K mat_N mat_Na mat_Ne mat_P mat_Pd mat_Sc mat_Sm CHBr3at%""".split()

for d in DIRS:
    p = os.path.join(M, d)
    print("=" * 78)
    if not os.path.isdir(p):
        print("MISSING DIR:", d); continue
    items = []
    for dp, dn, fn in os.walk(p):
        rel = os.path.relpath(dp, p).replace("\\", "/")
        for f in sorted(fn):
            fp = os.path.join(dp, f)
            try: sz = os.path.getsize(fp)
            except: sz = -1
            items.append((("" if rel == "." else rel + "/") + f, sz))
    items.sort()
    tot = sum(s for _, s in items)
    print("### %s   files=%d bytes=%d" % (d, len(items), tot))
    for n, s in items:
        print("  %9d  %s" % (s, n))
