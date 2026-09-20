# -*- coding: utf-8 -*-
"""Group A: MULTI multi-group opacity tables. Test the writer-derived closure:
   total_fields == 4 + nr + nt + nr*nt   (writer: outputMULTIOpacity.m)
   on the SNOP-produced files where we KNOW nr=nt=20.
   Also test alternative layouts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

files = [
    "mat_Au-1.0/AU_op03p", "mat_Au-1.0/AU_op03r", "mat_Au-1.0/AU_op03e",
    "mat_Au-1.0/Au100PLANCK", "mat_Au-1.0/Au100EPS", "mat_Au-1.0/Au100ROSS",
    "mat_Gd/Gd100PLANCK", "mat_Gd/Gd100EPS", "mat_Gd/Gd100ROSS",
    "mat_Gd/Gd20PLANCK", "mat_Gd/Gd20EPS", "mat_Gd/Gd20ROSS",
    "mat_Gd/Gd_op100PLANCK", "mat_Gd/Gd_op100EPS", "mat_Gd/Gd_op100ROSS",
    "mat_Be-1.0/opbe",
    "mat_Ti/Ti_Planck", "mat_Ti/Ti_Ross", "mat_Ti/Ti_EPS",
    "mat_Al-1.0/1041_PLANCK", "mat_Al-1.0/1041_ROSS",
    "Ta2O5/Ta2O5_mopp", "Ta2O5/Ta2O5_mopr",
    "CH/C_mopp", "CH/C_mopr", "CH/CHSi1_mopp", "CH/CHSi1_mopr",
    "CH/CH_mopp20", "CH/CH_mopr20", "CH/CHSi10_mopp", "CH/CHSi10_mopr",
    "mat_C-1.0/CHSi1_mopp", "mat_C-1.0/CH_mopp20",
    "mat_CHBr/C50H38Br12_mopp", "mat_CHBr/C50H38Br12_mopr",
    "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Others/CH10Water1/CH2_H2O_1m1opr",
    "mat_Others/CH10Water1/CH2_H2O_1m1Z",
]

print("#" * 110)
print("# A1. First line + line-length histogram + fixed-width-15 token count")
print("#" * 110)
res = {}
for rel in files:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    if not os.path.isfile(p):
        print(f"MISSING {rel}")
        continue
    d = raw(p)
    ls = d.split(b"\n")
    lens = {}
    for ln in ls:
        L = len(ln.rstrip(b"\r"))
        if L:
            lens[L] = lens.get(L, 0) + 1
    f, tail = all_tokens(p, 15)
    hdr = ls[0].rstrip(b"\r")
    hdr2 = ls[1].rstrip(b"\r") if len(ls) > 1 else b""
    res[rel] = (len(f), tail, len(d))
    print(f"\n-- {rel}  bytes={len(d)}  nlines={len(ls)}  fields15={len(f)}  leftover={len(tail)}")
    print(f"   L0 len={len(hdr)} {hdr[:120]!r}")
    print(f"   L1 len={len(hdr2)} {hdr2[:120]!r}")
    print(f"   line-length histogram: {sorted(lens.items())[:12]}")
    print(f"   L2 tok = {tok15(ls[2]) if len(ls)>2 else None}")
    print(f"   L3 tok = {tok15(ls[3]) if len(ls)>3 else None}")

print()
print("#" * 110)
print("# A2. CLOSURE TEST: which (nr,nt,ng) formula closes?  4+nr+nt+nr*nt+ng*nr*nt  vs  4+nr+nt+ng*nr*nt")
print("#" * 110)


def closure(N, nr, nt, ng):
    """Return list of (label, residual)"""
    cands = [
        ("4+2nr+nt+2nr*nt      (SESAME EOS P47)", 4 + 2 * nr + nt + 2 * nr * nt),
        ("4+nr+nt+nr*nt", 4 + nr + nt + nr * nt),
        ("4+nr+nt+nr*nt+(ng+1)*nr*nt", 4 + nr + nt + nr * nt + (ng + 1) * nr * nt),
        ("4+nr+nt+ng*nr*nt", 4 + nr + nt + ng * nr * nt),
        ("4+2+nr+nt+ng*nr*nt", 4 + 2 + nr + nt + ng * nr * nt),
        ("4+2+nr+nt+nr*nt+(ng+1)*nr*nt", 4 + 2 + nr + nt + nr * nt + (ng + 1) * nr * nt),
        ("4+2+ng+nr+nt+ng*nr*nt", 4 + 2 + ng + nr + nt + ng * nr * nt),
        ("4+nr+nt+ng*(nr+nt)+nr*nt", 4 + nr + nt + ng * (nr + nt) + nr * nt),
    ]
    return [(l, N - v) for l, v in cands]


for rel, (N, tail, sz) in res.items():
    print(f"\n{rel}:  N15={N}  leftover={len(tail)}")
    for ng in (1, 20, 22, 24, 30, 40, 41, 43, 50, 69, 96, 100):
        for nr, nt in ((20, 20), (30, 50), (43, 43), (50, 69), (100, 100), (41, 50), (20, 30)):
            for lb, r in closure(N, nr, nt, ng):
                if r == 0:
                    print(f"   *** CLOSES: nr={nr} nt={nt} ng={ng}  {lb}")
    # also scan the exact residual of the writer formula with nr=nt=20,ng=20
    for nr, nt, ng in ((20, 20, 20), (20, 20, 21), (30, 50, 1)):
        rs = closure(N, nr, nt, ng)
        print(f"   [nr={nr},nt={nt},ng={ng}] " + "  ".join(f"{l}={r}" for l, r in rs[:4]))
