# -*- coding: utf-8 -*-
"""DISAMBIGUATE nr vs nt physically: the layout is [2 preamble][nr rho values][nt T values][nr*nt data].
Accept the split whose rho-block is monotone increasing AND whose T-block is monotone increasing."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def solve(rel):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f); nl = len(ne)
    spl = [i for i, l in enumerate(ne) if len(l) % 60 != 0]
    L = len(ne[spl[0]]) if spl else 60
    nb = len(spl) if spl else 1
    nfull = (nl - nb * 2) // nb if spl else (nl - 1)
    V = 4 + (L // 15) + 4 * nfull
    vals = nums(f[:V])         # nucleus values
    print("=" * 100)
    print(f"{rel}   nb={nb} L={L} nfull={nfull} V={V}")
    print(f"  preamble : {vals[0]}, {f[1]!r}, {vals[2]}, {vals[3]}")
    print(f"  splitflds: {f[4:4+L//15]}")
    W = V - 6
    found = []
    for t in range(1, 2000):
        if (W - t) > 0 and (W - t) % (t + 1) == 0:
            r = (W - t) // (t + 1)
            # layout from value index 6: rho(r), T(t), data(r*t)
            rho = vals[6:6 + r]
            T = vals[6 + r:6 + r + t]
            if None in rho or None in T:
                continue
            mono_r = all(rho[i] < rho[i + 1] for i in range(len(rho) - 1))
            mono_t = all(T[i] < T[i + 1] for i in range(len(T) - 1))
            if mono_r and mono_t:
                found.append((r, t, mono_r, mono_t))
    print(f"  candidate (nr,nt) with BOTH rho and T strictly increasing: {found}")
    for r, t, _, _ in found:
        rho = vals[6:6 + r]
        T = vals[6 + r:6 + r + t]
        dat = vals[6 + r + t:6 + r + t + r * t]
        print(f"    nr={r} rho: {rho[0]:.4f} .. {rho[-1]:.4f}  ({len(rho)} pts)")
        print(f"    nt={t}  T  : {T[0]:.4f} .. {T[-1]:.4f}  ({len(T)} pts)")
        if dat:
            print(f"    data : {dat[0]:.4f} .. {dat[-1]:.4f}  (n={len(dat)})  "
                  f"all data present={len(dat)==r*t}  V-6-r-t={V-6-r-t}")
    return found


print("### AU_op03p  (expected nr=nt=20 from X/Y/Z closure of 8920 = 20*446)")
solve("mat_Au-1.0/AU_op03p")
print("\n\n### Gd_op100PLANCK (168600/100=1686 = 6+40+40+1600 -> nr=nt=40)")
solve("mat_Gd/Gd_op100PLANCK")
print("\n\n### Gd100PLANCK (158600/100=1586 ; candidates (526,2),(92,16),(50,30),(30,50))")
solve("mat_Gd/Gd100PLANCK")
print("\n\n### Ti_Ross (odd)")
solve("mat_Ti/Ti_Ross")
print("\n\n### CHSi1_mopp (946 -> no factorization?)")
solve("CH/CHSi1_mopp")
print("\n\n### C_mopp")
solve("CH/C_mopp")
print("\n\n### opbe")
solve("mat_Be-1.0/opbe")
print("\n\n### 1041_PLANCK")
solve("mat_Al-1.0/1041_PLANCK")
