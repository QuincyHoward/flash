# -*- coding: utf-8 -*-
"""CORRECTED Group-A model.
File = [STANCHION 0] [STANCHION 1] ... [STANCHION nb-1]
Each STANCHION = 
    line A_len  : 60 chars, 4 fields:  tid, LABEL(freq-band type), h_lo, h_hi
    line B_len  : 30 chars, 2 fields:  A = rho_first,  B = T_last
    then nfull full 60-char lines, 4 fields each
Counts per stanchion: nlines_s = 2 + nfull ; N15_s = 6 + 4*nfull
=> nlines = nb*(2+nfull) ; N15 = nb*(6+4*nfull)
   => nfull = (N15 - 3*nlines)/nb - ... solve: nb = (4*nlines - N15)/2
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

SET = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/Au100PLANCK", "mat_Gd/Gd100PLANCK",
       "mat_Gd/Gd20PLANCK", "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck",
       "mat_Ti/Ti_Ross", "mat_Be-1.0/opbe", "CH/C_mopp", "CH/CHSi1_mopp",
       "Ta2O5/Ta2O5_mopp", "mat_Others/CH10Water1/CH2_H2O_1m1opp",
       "mat_Al-1.0/1041_PLANCK", "mat_Al-1.0/1041_ROSS", "CH/CH_mopp20",
       "mat_C-1.0/CH_mopp20", "mat_CHBr/C50H38Br12_mopp"]

print("Equation set:  nlines = nb*(2+nfull) ;  N15 = nb*(6+4*nfull)")
print("  => nb = (4*nlines - N15)/2 ,  nfull = N15/nb - 1.5 ... check with nlines\n")
print(f"{'file':<42}{'N15':>8}{'nlines':>7}{'nb':>6}{'nfull':>7}{'chk_nl':>8}{'chk_N15':>9}{'ok':>5}")
print("-" * 100)
for rel in SET:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f); nl = len(ne)
    nb2 = 4 * nl - N
    if nb2 % 2: 
        print(f"{rel:<42}{N:>8}{nl:>7}  ODD nb2={nb2}"); continue
    nb = nb2 // 2
    nfull = N // nb - 1   # (6+4nfull)/... -> N/nb = 6+4nfull -> nfull=(N/nb-6)/4
    nfull = (N // nb - 6) // 4
    ok1 = nb * (2 + nfull) == nl
    ok2 = nb * (6 + 4 * nfull) == N
    print(f"{rel:<42}{N:>8}{nl:>7}{nb:>6}{nfull:>7}{nb*(2+nfull):>8}{nb*(6+4*nfull):>9}{str(ok1 and ok2):>5}")

print("\n" + "=" * 100)
print("STANCHION LINE-LENGTH SIGNATURE (which lines are the 30-char ones)")
print("=" * 100)
for rel in ["mat_Au-1.0/AU_op03p", "mat_Be-1.0/opbe", "mat_Al-1.0/1041_PLANCK",
            "CH/CHSi1_mopp", "mat_Others/CH10Water1/CH2_H2O_1m1opp", "CH/C_mopp"]:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    from collections import Counter
    c = Counter(len(l) for l in ne)
    print(f"  {rel:<44} {dict(sorted(c.items()))}")
    idx = [i for i, l in enumerate(ne) if len(l) % 30 != 0 or len(l) == 30]
    print(f"      30-char line indices (first 6): {[i for i,l in enumerate(ne) if len(l)==30][:6]}")
