# -*- coding: utf-8 -*-
"""Group-A boundary logic FIXED.
A stanza header line is a 60-char line whose IMMEDIATELY PRECEDING line is a
non-60-char line (the previous stanza's split line), OR is line 0.
That is: split lines BOUND stanzas. So:
   starts = [0] + [i+1 for i where len(ne[i]) % 60 != 0]
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def stanzas(rel):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    nl = len(ne)
    starts = [0]
    for i in range(nl - 1):
        if len(ne[i]) % 60 != 0:
            starts.append(i + 1)
    out = []
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else nl
        out.append(ne[st:en])
    return out, ne


for rel in ["mat_Au-1.0/AU_op03p", "CH/C_mopp", "CH/CHSi1_mopp",
            "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Al-1.0/1041_PLANCK"]:
    st, ne = stanzas(rel)
    print("=" * 100)
    print(f"{rel}   nstanzas(detected)={len(st)}  total_lines={len(ne)}")
    for k in range(min(6, len(st))):
        blk = st[k]
        sig = [len(l) for l in blk[:5]]
        print(f"  st{k}: nlines={len(blk)} lens(first5)={sig}")
        print(f"        hdr={blk[0][:60]!r}")
        if len(blk) > 1:
            print(f"        l1 ={blk[1][:60]!r}")
        if len(blk) > 2:
            print(f"        l2 ={blk[2][:60]!r}")
    print(f"  stanza line-count histogram: "
          f"{ {L: sum(1 for b in st if len(b)==L) for L in sorted(set(len(b) for b in st))} }")

print("\n\n#### KEY INSIGHT CHECK: does every stanza have the SAME value count?")
for rel in ["mat_Au-1.0/AU_op03p", "CH/C_mopp", "CH/CHSi1_mopp",
            "mat_Others/CH10Water1/CH2_H2O_1m1opp"]:
    st, ne = stanzas(rel)
    vs = [sum(len(l) // 15 for l in b) for b in st]
    print(f"  {rel:<44} V per stanza = {sorted(set(vs))}  counts={ {v: vs.count(v) for v in set(vs)} }")
