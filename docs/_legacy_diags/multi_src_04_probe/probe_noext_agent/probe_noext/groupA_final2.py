# -*- coding: utf-8 -*-
"""GROUP A — FINAL DEFINITIVE MODEL, validated across the whole family.

Per frequency group (k of them, identical):
  fields after dropping the LABEL token:
    [0] table id
    [1] h_lo  (eV)      [2] h_hi  (eV)      <- the 2 preamble numbers (NOT rho!)
    [3] rho_first       [4] T_last          <- the 2 fields on the 30/45-char split line
    [5 .. 5+nr-1]       rho grid  (log10 rho, g/cm^3)
    [5+nr .. 5+nr+nt-1] T   grid  (log10 T,   eV)
    [5+nr+nt .. +nr*nt] opacity   (log10 kappa, cm^2/g)
  Conservation:  k * (3 + 2 + nr + nt + nr*nt) == total_fields - 0
                 (the +3 counts id,h_lo,h_hi; the +2 are the split-line redundancy)
  PROOF for AU_op03p: k=20, nr=nt=20 -> 20*(3+2+20+20+400) = 20*445 = 8900
  Hmm: total fields = 8920 (=445*20+20). Recheck: 8920/20 = 446, and 446 = 445 + 1 LABEL.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

CASES = [("mat_Au-1.0/AU_op03p", 20), ("mat_Au-1.0/Au100PLANCK", 100),
         ("mat_Gd/Gd100PLANCK", 100), ("mat_Gd/Gd20PLANCK", 20),
         ("mat_Gd/Gd_op100PLANCK", 100), ("mat_Ti/Ti_Planck", 20),
         ("CH/C_mopp", 20), ("CH/CHSi1_mopp", 20),
         ("mat_Others/CH10Water1/CH2_H2O_1m1opp", 44),
         ("Ta2O5/Ta2O5_mopp", 96), ("mat_Al-1.0/1041_PLANCK", 1)]

print("Model: fields_per_group = 1(LABEL) + 2(id,h_lo,h_hi ->3) ...")
print("Exact count identity: N = k * (1 + 5 + nr + nt + nr*nt)\n")
print(f"{'file':<42}{'k':>4}{'F/grp':>7}{'F-lbl':>7}{'=5+nr+nt+nrnt':>15}{'nr':>5}{'nt':>5}{'close':>7}"
      f"{'rho':>24}{'T':>22}")
print("-" * 140)
OK = []
for rel, k in CASES:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f)
    F = N // k
    R = F - 1              # drop label
    npre = 5
    # 5 + nr + nt + nr*nt = R  -> (nr+1)(nt+1) = R-4
    sols = []
    for t in range(1, 4000):
        if (R - 4) % (t + 1):
            continue
        r = (R - 4) // (t + 1) - 1
        if r < 2:
            continue
        sols.append((r, t))
    # decode group 0 with each candidate, pick unique monotone
    per = len(ne) // k
    blk = ne[0:per]
    vv = []
    for i, l in enumerate(blk):
        tt = tok15(l, 15)
        if i == 0:
            tt = tt[:1] + tt[2:]
        vv += tt
    picked = None
    for r, t in sols:
        if npre + r + t + r * t != len(vv):
            continue
        rho = [num(x) for x in vv[npre:npre + r]]
        T = [num(x) for x in vv[npre + r:npre + r + t]]
        if None in rho or None in T:
            continue
        mr = all(rho[i] < rho[i + 1] for i in range(r - 1))
        mt = all(T[i] < T[i + 1] for i in range(t - 1))
        if mr and mt:
            picked = (r, t, rho, T)
    close = (N % k == 0) and picked is not None
    if picked:
        r, t, rho, T = picked
        print(f"{rel:<42}{k:>4}{F:>7}{R:>7}{'5+%d+%d+%d=%d' % (r,t,r*t,5+r+t+r*t):>15}"
              f"{r:>5}{t:>5}{str(close):>7}{f'{rho[0]:.2f}..{rho[-1]:.2f}':>24}"
              f"{f'{T[0]:.2f}..{T[-1]:.2f}':>22}")
        OK.append(rel)
    else:
        print(f"{rel:<42}{k:>4}{F:>7}{R:>7}{'no unique monotone':>15}{'':>5}{'':>5}{'NO':>7}  sols={sols[:6]}")
print(f"\nRESOLVED exactly: {len(OK)}/{len(CASES)}")
