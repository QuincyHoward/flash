# -*- coding: utf-8 -*-
"""Determine the EXACT index alignment of the rho/T/data blocks.
For AU_op03p stanza0 we KNOW: rho must be strictly increasing, T strictly increasing.
Scan every (npre, nr) where npre=number of preamble values after dropping LABEL,
nr+nt+nr*nt = B - npre, and report which gives rho AND T strictly increasing."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

p = os.path.join(MAT, "mat_Au-1.0", "AU_op03p")
d = raw(p)
ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
blk = ne[0:112]
print("lines of stanza 0:")
for i, l in enumerate(blk[:4]):
    print(f"  L{i} len={len(l)} tok={tok15(l,15)}")
vals_raw = []
for i, l in enumerate(blk):
    t = tok15(l, 15)
    if i == 0:
        t = t[:1] + t[2:]
    vals_raw += t
print("\nALL fields of stanza 0 (dropping LABEL):")
for i, s in enumerate(vals_raw[:60]):
    print(f"  [{i:>3}] {s!r}  -> {num(s)}")
print(f"  ... total {len(vals_raw)}")

B = len(vals_raw)
print(f"\nB = {B}")
hits = []
for npre in range(0, 12):
    R = B - npre
    for t in range(1, 300):
        if R - t <= 0 or (R - t) % (t + 1):
            continue
        r = (R - t) // (t + 1)
        if r < 2:
            continue
        rho = [num(x) for x in vals_raw[npre:npre + r]]
        T = [num(x) for x in vals_raw[npre + r:npre + r + t]]
        if None in rho or None in T:
            continue
        mr = all(rho[i] < rho[i + 1] for i in range(r - 1))
        mt = all(T[i] < T[i + 1] for i in range(t - 1))
        if mr and mt:
            hits.append((npre, r, t, rho, T))
print(f"\nSOLUTIONS with both rho and T strictly increasing: {[(h[0],h[1],h[2]) for h in hits]}")
for npre, r, t, rho, T in hits:
    print(f"  npre={npre} nr={r} nt={t}")
    print(f"    rho = {[round(x,3) for x in rho]}")
    print(f"    T   = {[round(x,3) for x in T]}")
    dat = [num(x) for x in vals_raw[npre + r + t:npre + r + t + r * t]]
    print(f"    data[{len(dat)}] first5 = {[round(x,4) for x in dat[:5]]}")
    print(f"    data last5 = {[round(x,4) for x in dat[-5:]]}")
    print(f"    consumed = {npre + r + t + r*t} of B={B}  leftover={B-(npre+r+t+r*t)}")
print(f"\n  residual fields after npre=2,r=20,t=20: idx 42,43,44 =",
      [vals_raw[i] for i in range(42, min(46, B))])
