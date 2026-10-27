# -*- coding: utf-8 -*-
"""Correct solve for the Group-A stanchion reproduction.
Unknowns per file: nb (#sub-tables = #frequency groups), A (#full 60-char lines per stanza).
Equations (file header = 1 line with 4 fields):
   E1: nlines = 1 + nb*(2 + A)
   E2: N15    = 4 + nb*(6 + 4*A)
Eliminate A: A = (nlines-1)/nb - 2.  Sub into E2:
   N15 = 4 + nb*(6 + 4*((nlines-1)/nb - 2)) = 4 + nb*(4*(nlines-1)/nb - 2) = 4 + 4*(nlines-1) - 2*nb
=> nb = (4 + 4*(nlines-1) - N15)/2
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

SET = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/Au100PLANCK", "mat_Gd/Gd100PLANCK",
       "mat_Gd/Gd20PLANCK", "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck",
       "mat_Ti/Ti_Ross", "mat_Be-1.0/opbe", "CH/C_mopp", "CH/CHSi1_mopp",
       "Ta2O5/Ta2O5_mopp", "mat_Others/CH10Water1/CH2_H2O_1m1opp",
       "mat_Al-1.0/1041_PLANCK", "mat_Al-1.0/1041_ROSS"]

print(f"{'file':<42}{'N15':>8}{'nlines':>7}{'nb':>6}{'A':>5}{'V':>7}{'nr':>5}{'nt':>5}{'6+nr+nt+nrnt':>13}{'ok':>6}")
print("-" * 118)
for rel in SET:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f); nlines = len(ne)
    Nb = 4 + 4 * (nlines - 1) - N
    if Nb % 2:
        print(f"{rel:<42} Nb odd -> {Nb}"); continue
    nb = Nb // 2
    A = (nlines - 1) // nb - 2
    V = (N - 4) // nb
    sols = [( (V-6-t)//(t+1), t) for t in range(1, 400) if (V-6-t) > 0 and (V-6-t) % (t+1) == 0]
    sq = [s for s in sols if s[0] == s[1]]
    nr, nt = (sq or sols or [(None, None)])[0]
    chk = 6 + nr + nt + nr*nt if nr else 0
    print(f"{rel:<42}{N:>8}{nlines:>7}{nb:>6}{A:>5}{V:>7}{str(nr):>5}{str(nt):>5}{chk:>13}{str(chk==V):>6}"
          f"  sols={sols[:5]}")
