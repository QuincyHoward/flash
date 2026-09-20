# -*- coding: utf-8 -*-
"""UNIFY Group D+E: header line = [id][Zbar_or_A][nr][nt]; body = 2nr+nt+2nr*nt.
Verify by locating the two monotone grids in the value stream right after the header."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

CASES = [("mat_CELIA/DD_ieos", 50, 25), ("mat_CELIA/DT_ieos", 50, 25),
         ("mat_C-1.0/CH_ieos", 101, 100), ("CH/CH_ieos", 101, 100),
         ("mat_C-1.0/Carbon_DLC_ieos_i", 123, 100),
         ("mat_C-1.0/Carbon_Polystyrene_ieos_e", 101, 100),
         ("mat_Others/CH10Water1/CH10Water1_ieos", 26, 50),
         ("mat_Ti/422_ieos", 43, 22), ("mat_Al-1.0/41_ieos", 44, 22),
         ("mat_Al-1.0/42_ieos", 84, 53), ("mat_C-1.0/511_ieos", 101, 25),
         ("mat_Al-1.0/AL_eos", 66, 74), ("mat_Be-1.0/BE_eos", 101, 50),
         ("mat_Ti/Ti_eos", 45, 100), ("mat_DT-1.0/DT_EOS", 50, 25),
         ("mat_DT-1.0/DT_EOS_e", 50, 25), ("mat_Au-1.0/AU_eos", 101, 23),
         ("mat_Au-1.0/AU_eosd", 101, 23), ("mat_C-1.0/C_EOS", 101, 23)]


def verify(rel, nr, nt):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    he = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f)
    # header consumed as 4 fields -> stream starts at index 4
    v = nums(f[4:])
    v = [x for x in v if x is not None]
    # SESAME 301: rho(nr) T(nt) then Frho.. P.. E.. : 2nr + nt + 2nr*nt
    ind = 0
    rho = v[ind:ind + nr]; ind += nr
    T = v[ind:ind + nt];   ind += nt
    Frho = v[ind:ind + nr]; ind += nr
    body = v[ind:ind + 2 * nr * nt]; ind += 2 * nr * nt
    mr = all(rho[i] < rho[i + 1] for i in range(len(rho) - 1))
    mt = all(T[i] < T[i + 1] for i in range(len(T) - 1))
    print(f"{rel:<44} hdr={f[0].strip()}|{f[1].strip()}|{f[2].strip()}|{f[3].strip()}")
    print(f"   N={N}  formula 4+2nr+nt+2nr*nt = {4+2*nr+nt+2*nr*nt}  MATCH={N==4+2*nr+nt+2*nr*nt}"
          f"  consumed={4+ind}  leftover={N-4-ind}")
    print(f"   rho[{nr}] {rho[0]:.4g}..{rho[-1]:.4g} mono={mr}   "
          f"T[{nt}] {T[0]:.4g}..{T[-1]:.4g} mono={mt}   Frho[0]={Frho[0]:.4g} Frho[-1]={Frho[-1]:.4g}")
    return N == 4 + 2 * nr + nt + 2 * nr * nt and mr and mt


print("### Verification of 4+2nr+nt+2nr*nt with monotone rho,T")
print("=" * 118)
ok = 0
for rel, nr, nt in CASES:
    if verify(rel, nr, nt):
        ok += 1
    print()
print(f"CLOSED+MONOTONE: {ok}/{len(CASES)}")
