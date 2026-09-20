# -*- coding: utf-8 -*-
"""Clean per-stanchion count. For AU_op03p:
   1 file header (1 line, 4 fields)
   nb stanchions, each = 1 hdr line (4 f) + 1 split line (2 f) + A_j full 60-lines (4 f each)
   nlines = 1 + nb*(2+A_j) = 2240 ; N15 = 4 + nb*(6+4*A_j) = 8920
   Solve per file: nb*(6+4A) = N15-4 ; nb*(2+A) = nlines-1
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

SET = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/Au100PLANCK", "mat_Gd/Gd100PLANCK",
       "mat_Gd/Gd20PLANCK", "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck",
       "mat_Be-1.0/opbe", "CH/C_mopp", "CH/CHSi1_mopp", "Ta2O5/Ta2O5_mopp",
       "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Al-1.0/1041_PLANCK"]

print(f"{'file':<44}{'N15':>8}{'nlines':>7}{'nb':>6}{'A':>5}{'vals/st':>8}{'nr':>4}{'nt':>4}{'6+nr+nt+nrnt':>14}{'ok':>5}")
for rel in SET:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f); nlines = len(ne)
    # nb from:  nb*(2+A)=nlines-1 ; nb*(6+4A)=N-4
    # -> divide: nb = (N-4-2*(nlines-1))/2
    nb = (N - 4 - 2 * (nlines - 1)) // 2
    A = (nlines - 1) // nb - 2
    V = (N - 4) // nb                  # values inside one stanchion
    # V = 6 + nr + nt + nr*nt  =>  nr*(nt+1) = V-6-nt
    sols = []
    for t in range(1, 400):
        if (V - 6 - t) > 0 and (V - 6 - t) % (t + 1) == 0:
            sols.append(((V - 6 - t) // (t + 1), t))
    sq = [s for s in sols if s[0] == s[1]]
    pick = (sq or sols or [(None, None)])[0]
    nr, nt = pick
    chk = 6 + nr + nt + nr * nt if nr else 0
    print(f"{rel:<44}{N:>8}{nlines:>7}{nb:>6}{A:>5}{V:>8}{str(nr):>5}{str(nt):>5}{chk:>10}{str(chk==V):>6}"
          f"   all_sols={sols[:6]}")
