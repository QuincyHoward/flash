# -*- coding: utf-8 -*-
"""Group A: decode the sub-table header line and prove the master closure.
Hypothesis:
  Each sub-table = [60-char header: id, LABEL, band_lo, band_hi]
                 + [30-char line: nr, nt]
                 + next odd(4a+111) values = rho-grid(4a, log10 rho) + T-grid(3, log10 T) + nr*nt data
  The 30-char line ALSO carries the FIRST TWO values of the rho grid.
  File = nb sub-tables (the frequency groups), all identical grids.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

A_SET = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/Au100PLANCK", "mat_Gd/Gd100PLANCK",
         "mat_Gd/Gd20PLANCK", "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck",
         "mat_Be-1.0/opbe", "mat_Al-1.0/1041_PLANCK", "CH/CHSi1_mopp",
         "CH/CH_mopp20", "CH/C_mopp", "Ta2O5/Ta2O5_mopp", "mat_Ti/Ti_Ross"]


def measure(rel, verbose=True):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ls = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    # find short trailing line of subtable 1
    # locate index of first line with len!=60 after line 0
    idx = None
    for i in range(1, len(ls)):
        if len(ls[i]) != 60:
            idx = i
            break
    L = len(ls[idx])
    a = (L - 30) // 15          # number of leading rho grid values on the 30-char line
    f1, t1 = all_tokens(p, 15)
    N = len(f1)
    nb = -(N - 6) // (a - 111)
    V = N / nb                  # values per subtable (fractional-safe)
    rho = a + 4 * a             # total rho grid count expected = 5a ? try
    # solve: V = 6 + rho + nt + rho*nt ; rho=5a
    rho = 5 * a
    nt = (V - 6 - rho) / (rho + 1)
    if verbose:
        print("=" * 96)
        print(f"{rel}")
        print(f"  hdr       : {ls[0][:60]!r}")
        print(f"  split line: idx={idx} len={L} a=(L-30)/15={a}")
        print(f"            : {ls[idx]!r}")
        print(f"  N15={N}  nb={nb}  V={V}  rho=5a={rho}  nt={nt}")
        ok = (nb > 0) and (N % nb == 0) and abs(nt - round(nt)) < 1e-9
        print(f"  CLOSURE   : nb*(6+rho+nt+rho*nt) == N ? "
              f"{nb*(6+rho+round(nt)+rho*round(nt))} == {N} -> "
              f"{nb*(6+rho+round(nt)+rho*round(nt))==N}   integral_nt={abs(nt-round(nt))<1e-9}")
        print(f"  band check: header bands should span 0..200 eV; grid lo/hi = "
              f"{num(f1[4])},{num(f1[5])} .. final rho={num(f1[4+rho-1])}, "
              f"first T={num(f1[4+rho])}, last T={num(f1[4+rho+round(nt)-1])}")
        print(f"  subtable 2 hdr: {ls[idx+1][:60]!r}")
    return dict(rel=rel, N=N, nb=nb, a=a, rho=rho, nt=nt, V=V)


print("#" * 100)
print("# GROUP A MASTER CLOSURE:  N = nb * (6 + 5a + nt + 5a*nt),  nt = 3 + 4a")
print("#" * 100)
rows = []
for rel in A_SET:
    r = measure(rel)
    rows.append(r)
    print()

print("=" * 104)
print("SUMMARY TABLE")
print("=" * 104)
print(f"{'file':<34}{'N':>9}{'nb':>5}{'a':>4}{'rho=5a':>7}{'nt':>5}{'nt=3+4a':>9}{'V':>8}{'closure':>10}")
for r in rows:
    cl = r['nb'] * (6 + r['rho'] + round(r['nt']) + r['rho'] * round(r['nt'])) == r['N']
    print(f"{r['rel']:<34}{r['N']:>9}{r['nb']:>5}{r['a']:>4}{r['rho']:>7}{r['nt']:>5.0f}"
          f"{3+4*r['a']:>9}{r['V']:>8.1f}{str(cl):>10}")
