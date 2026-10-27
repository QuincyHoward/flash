# -*- coding: utf-8 -*-
"""GROUP A: solve grid dims from V per group (the 2 preamble values are
   (h_lo, h_hi) so the grid block is V-4, laid out as nr + nt + nr*nt ... or
   V-4 = 2 + nr + nt + nr*nt.  Test both; require monotone rho and T."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

# (rel, groups k, expected per-group V from the pair model)
CASES = [("mat_Au-1.0/AU_op03p", 20), ("mat_Au-1.0/Au100PLANCK", 100),
         ("mat_Gd/Gd100PLANCK", 100), ("mat_Gd/Gd20PLANCK", 20),
         ("mat_Gd/Gd_op100PLANCK", 100), ("mat_Ti/Ti_Planck", 20),
         ("CH/C_mopp", 20), ("CH/CHSi1_mopp", 20),
         ("mat_Others/CH10Water1/CH2_H2O_1m1opp", 44),
         ("Ta2O5/Ta2O5_mopp", 96), ("mat_Al-1.0/1041_PLANCK", 1)]

print(f"{'file':<42}{'k':>5}{'V':>7}{'sol(nr,nt)':>14}{'4+p+2+nrnt':>12}{'mono?':>7}"
      f"{'rho range':>26}{'T range':>26}")
print("-" * 150)
out = {}
for rel, k in CASES:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    per = len(ne) // k
    blk = ne[0:per]
    # flatten stanza values
    vals = []
    for l in blk:
        vals += [num(x) for x in tok15(l, 15)]
    vals = [x for x in vals if x is not None]
    V = len(vals)
    # try layout candidates by locating a strictly-increasing rho run then T run
    best = None
    for npre in (4, 6):
        W = V - npre
        for t in range(1, 2000):
            if W - t <= 0 or (W - t) % (t + 1):
                continue
            r = (W - t) // (t + 1)
            if r < 2 or t < 2:
                continue
            off = npre
            rho = vals[off:off + r]
            T = vals[off + r:off + r + t]
            if len(rho) < r or len(T) < t:
                continue
            mr = all(rho[i] < rho[i + 1] for i in range(len(rho) - 1))
            mt = all(T[i] < T[i + 1] for i in range(len(T) - 1))
            if mr and mt:
                best = (npre, r, t, rho, T)
                break
        if best:
            break
    if best:
        npre, r, t, rho, T = best
        print(f"{rel:<42}{k:>5}{V:>7}{f'({r},{t})':>14}{npre+2+r*t:>12}{'YES':>7}"
              f"{f'{rho[0]:.3f}..{rho[-1]:.3f} ({r})':>26}{f'{T[0]:.3f}..{T[-1]:.3f} ({t})':>26}")
        out[rel] = dict(k=k, V=V, npre=npre, nr=r, nt=t)
    else:
        print(f"{rel:<42}{k:>5}{V:>7}{'--':>14}{'':>12}{'no':>7}")
        out[rel] = dict(k=k, V=V, nr=None, nt=None)
json.dump(out, open(os.path.join(OUT, "groupA_grids.json"), "w"), indent=1, default=str)
