# -*- coding: utf-8 -*-
"""GROUP D (ieos) and GROUP E (eos) closure.

Group D header (line 0):  id(15) | Zbar_info(?) | nr(15) | nt(15)   -- looks like
     ' 5.27100000e+03 0.00000000e+00 5.00000000e+01 2.50000000e+01'  -> nr=50, nt=25
     ' 7.59000000e+03 0.00000000e+00 1.01000000e+02 1.00000000e+02'  -> nr=101, nt=100
     ' 5.00010010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02'  -> nr=123, nt=100
Group E header (line 0):  SESAME EOS 301: id | Zbar | A | rho0 ... need nr, nt.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

D = [("mat_CELIA/DD_ieos", 50, 25), ("mat_CELIA/DT_ieos", 50, 25),
     ("mat_C-1.0/CH_ieos", 101, 100), ("mat_CELIA/CH_ieos", 101, 100),
     ("CH/CH_ieos", 101, 100),
     ("mat_C-1.0/Carbon_DLC_ieos_i", 123, 100),
     ("mat_C-1.0/Carbon_DLC_ieos_e", 123, 100),
     ("mat_C-1.0/Carbon_Polystyrene_ieos_e", 101, 100),
     ("mat_Others/CH10Water1/CH10Water1_ieos", 26, 50),
     ("mat_Ti/422_ieos", 43, 22), ("mat_Al-1.0/41_ieos", 44, 22),
     ("mat_Al-1.0/42_ieos", 84, 53), ("mat_C-1.0/511_ieos", 101, 25)]

print("GROUP D (ieos): header = [id][?][nr][nt]  ; data = rho(nr) + T(nt) + nr*nt values?")
print(f"{'file':<44}{'N15':>8}{'nr':>5}{'nt':>5}{'2+nr+nt+nrnt':>14}{'4+nr+nt+nrnt':>14}{'close4':>8}")
print("-" * 104)
for rel, nr, nt in D:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    f, tail = all_tokens(p, 15)
    N = len(f)
    c2 = 2 + nr + nt + nr * nt
    c4 = 4 + nr + nt + nr * nt
    print(f"{rel:<44}{N:>8}{nr:>5}{nt:>5}{c2:>14}{c4:>14}"
          f"{str(c4==N or c2==N):>8}   d2={N-c2} d4={N-c4}")

print("\n\nGROUP E (eos): SESAME 301 layout per MULTI docx: 4+2nr+nt+2nr*nt")
E = [("mat_Al-1.0/AL_eos", 66, 74), ("mat_Be-1.0/BE_eos", None, None),
     ("mat_C-1.0/C_EOS", None, None), ("mat_Ti/Ti_eos", None, None),
     ("mat_DT-1.0/DT_EOS", None, None), ("mat_Au-1.0/AU_eos", None, None),
     ("mat_Au-1.0/AU_eosd", None, None), ("mat_Be-1.0/BE_eos_e", None, None),
     ("mat_DT-1.0/DT_EOS_e", None, None), ("mat_DT-1.0/DT_EOS_i", None, None)]
for rel, nr, nt in E:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    he = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f)
    print("\n" + "-" * 96)
    print(f"{rel}  bytes={len(d)}  N15={N} leftover={tail!r}")
    print(f"  L0 = {he[0][:60]!r}")
    print(f"  L0 tok = {tok15(he[0],15)}")
    # brute force which (nr,nt) closes 4+2nr+nt+2nr*nt == N
    hits = []
    for n in range(2, 400):
        for t in range(2, 400):
            if 4 + 2 * n + t + 2 * n * t == N:
                hits.append((n, t))
    print(f"  4+2nr+nt+2nr*nt==N solutions {hits[:8]}")
    hits2 = [(n, t) for n in range(2, 400) for t in range(2, 400)
             if 4 + n + t + 2 * n * t == N]
    print(f"  4+nr+nt+2nr*nt==N solutions {hits2[:8]}")
