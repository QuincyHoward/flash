# -*- coding: utf-8 -*-
"""GENERAL Group-A parser (handles 30- and 45-char split lines).
Stanza = [hdr 60-char line: tid,LABEL,band_lo,band_hi] [split line: L chars = L/15 fields]
         [nfull full-width lines of 4 fields]
Split-line fields are part of the grid. Total stanza values:
   V = 4 + L/15 + 4*nfull
Grid interpretation:
   V = 6 + nr + nt + nr*nt        (writer layout: 2 preamble + nr + nt + nr*nt)
Then nr, nt recovered by   nr*(nt+1) = V - 6 - nt.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

SET = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/Au100PLANCK", "mat_Gd/Gd100PLANCK",
       "mat_Gd/Gd20PLANCK", "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck",
       "mat_Ti/Ti_Ross", "mat_Be-1.0/opbe", "CH/C_mopp", "CH/C_mopr",
       "CH/CHSi1_mopp", "CH/CHSi1_mopr", "CH/CH_mopp20", "CH/CH_mopr20",
       "Ta2O5/Ta2O5_mopp", "Ta2O5/Ta2O5_mopr",
       "mat_Others/CH10Water1/CH2_H2O_1m1opp",
       "mat_Al-1.0/1041_PLANCK", "mat_Al-1.0/1041_ROSS",
       "mat_C-1.0/CHSi1_mopp", "mat_C-1.0/CH_mopp20",
       "mat_CHBr/C50H38Br12_mopp", "mat_CHBr/CHBr3at%/C50H47Br3_mopp",
       "CHBr3at%/C50H47Br3_mopp", "mat_Au-1.0/Au100ZEFF", "mat_Gd/Gd100ZEFF",
       "mat_Ti/Ti_EPS"]

res = {}
print(f"{'file':<42}{'nb':>5}{'L':>4}{'nfull':>7}{'V':>6}{'nr':>5}{'nt':>5}{'nr*nt':>8}{'close':>7}")
print("-" * 96)
for rel in SET:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    if not os.path.isfile(p):
        print(f"{rel:<42} MISSING"); continue
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f); nl = len(ne)
    # split lines = lines whose length is NOT a multiple of 60
    spl = [i for i, l in enumerate(ne) if len(l) % 60 != 0]
    L = len(ne[spl[0]]) if spl else None
    nb = len(spl)
    nfull = (nl - nb * 2) // nb
    V = 4 + (L // 15 if L else 0) + 4 * nfull
    # solve nr,nt
    nr = nt = None; sols = []
    W = V - 6
    for t in range(1, 2000):
        if (W - t) > 0 and (W - t) % (t + 1) == 0:
            sols.append(((W - t) // (t + 1), t))
    sq = [s for s in sols if s[0] == s[1]]
    # pick the solution whose nt equals the count of distinct monotone runs -> use square then first
    nr, nt = (sq or sols or [(None, None)])[0]
    close = (nr is not None) and (6 + nr + nt + nr * nt == V) and \
            (nb * (2 + nfull) == nl) and (nb * V == N)
    res[rel] = dict(nb=nb, L=L, nfull=nfull, V=V, nr=nr, nt=nt,
                    sols=sols[:8], close=close, N=N, nl=nl)
    print(f"{rel:<42}{nb:>5}{str(L):>4}{nfull:>7}{V:>6}{str(nr):>5}{str(nt):>5}"
          f"{(nr*nt if nr else 0):>8}{str(close):>7}  sols={sols[:5]}")

json.dump(res, open(os.path.join(OUT, "groupA_solved.json"), "w"), indent=1)
print("\nwrote groupA_solved.json")
