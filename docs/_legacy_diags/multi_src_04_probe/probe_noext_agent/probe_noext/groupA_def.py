# -*- coding: utf-8 -*-
"""GROUP A — DEFINITIVE VALIDATION.

PROVEN LAYOUT (each of the k frequency-group blocks, identical structure):
  line  0  : 60 chars, cols 1-15 = table id, 16-30 = LABEL, 31-45 = h_lo (eV), 46-60 = h_hi (eV)
  then the numeric stream, aligned by *dropping the LABEL field*:
    [0]=tid [1]=h_lo [2]=h_hi [3..]=rho grid + T grid + data   (all %15.7e)
  Counting (writer layout, outputMULTIOpacity.m:39-68):
    per group:  3 + (nr + nt) + nr*nt   values after dropping LABEL
    bytes     : 60 (hdr line) + 15*(nr+nt+nr*nt) rounded up to 60-char lines + split line
  Conservation:  k * (3 + nr + nt + nr*nt) == total_fields - (label fields dropped)
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

CASES = [("mat_Au-1.0/AU_op03p", 20, 20, 20), ("mat_Au-1.0/AU_op03r", 20, 20, 20),
         ("mat_Au-1.0/AU_op03e", 20, 20, 20),
         ("mat_Au-1.0/Au100PLANCK", 100, 30, 50), ("mat_Au-1.0/Au100ROSS", 100, 30, 50),
         ("mat_Au-1.0/Au100EPS", 100, 30, 50),
         ("mat_Gd/Gd100PLANCK", 100, 30, 50), ("mat_Gd/Gd_op100PLANCK", 100, 40, 40),
         ("mat_Gd/Gd20PLANCK", 20, 20, 20), ("mat_Ti/Ti_Planck", 20, 20, 20),
         ("CH/C_mopp", 20, 19, 96), ("CH/CHSi1_mopp", 20, 19, 93),
         ("mat_Others/CH10Water1/CH2_H2O_1m1opp", 44, 19, 96),
         ("Ta2O5/Ta2O5_mopp", 96, 19, 54),
         ("mat_Al-1.0/1041_PLANCK", 1, 31, 46)]

print(f"{'file':<42}{'k':>4}{'nr':>5}{'nt':>5}{'3+nr+nt+nrnt':>14}{'(N-#lbl)/k':>12}{'close':>7}"
      f"{'rho[0..]':>22}{'T[0..]':>20}{'monotone':>10}")
print("-" * 138)
BAD = []
for rel, k, nr, nt in CASES:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f)
    V = 3 + nr + nt + nr * nt
    got = (N - k) // k         # drop one LABEL field per group
    close = (k * V == N - k)
    # decode group 0
    per = len(ne) // k
    blk = ne[0:per]
    vals = []
    for i, l in enumerate(blk):
        t = tok15(l, 15)
        if i == 0:
            t = t[:1] + t[2:]     # drop LABEL
        vals += [num(x) for x in t]
    vals = [x for x in vals if x is not None]
    rho = vals[3:3 + nr]
    T = vals[3 + nr:3 + nr + nt]
    mr = all(rho[i] < rho[i + 1] for i in range(len(rho) - 1))
    mt = all(T[i] < T[i + 1] for i in range(len(T) - 1))
    if not close:
        BAD.append((rel, N, k * V + k))
    print(f"{rel:<42}{k:>4}{nr:>5}{nt:>5}{V:>14}{got:>12}{str(close):>7}"
          f"{f'{rho[0]:.2f}..{rho[-1]:.2f}({nr})':>22}{f'{T[0]:.2f}..{T[-1]:.2f}({nt})':>20}"
          f"{('rho+T' if mr and mt else ('rho' if mr else ('T' if mt else 'neither'))):>10}")
print("\nFAILURES:", BAD if BAD else "NONE - all closed exactly")
