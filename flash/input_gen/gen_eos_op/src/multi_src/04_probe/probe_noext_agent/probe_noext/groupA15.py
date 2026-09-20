# -*- coding: utf-8 -*-
"""GROUP A: correct grid solve.
Stanza = [line0: tid | LABEL | h_lo | h_hi]  (4 fields)
         [split line: s fields]  -> these ARE rho[0..s-1] then T last? no: we PROVED
         for AU_op03p the layout is 2 preamble + nr rho + nt T + nr*nt data, and the
         split line's 2 fields are the first 2 of the rho grid.
So: after the header line (4 fields: tid,LABEL,h_lo,h_hi), the REMAINING values
    R = V - 4 are: [rho(nr)][T(nt)][data(nr*nt)] with nr + nt + nr*nt = R.
For AU_op03p R = 446-4 = 442 ; solutions of r+t+r*t=442 -> (r+1)(t+1)=443 prime -> none.
   => so the 2 split fields are NOT both rho. For AU_op03p the working layout was
      R = 4 (hdr) + 2 (split as preamble) ... i.e. preamble is 6.
      R6 = 440 = nr+nt+nr*nt -> (nr+1)(nt+1)=441=21*21 -> nr=nt=20.  ***UNIQUE***
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def solve_group(rel, k, verbose=True):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    per = len(ne) // k
    blk = ne[0:per]
    # values AFTER the 60-char header line
    body = []
    for l in blk[1:]:
        body += [num(x) for x in tok15(l, 15)]
    body = [x for x in body if x is not None]
    B = len(body)
    res = []
    for npre in (0, 1, 2, 4):
        R = B - npre
        if R <= 0:
            continue
        # R = nr + nt + nr*nt  -> (nr+1)(nt+1) = R+1
        for tt in range(1, 3000):
            if (R + 1) % (tt + 1):
                continue
            rr = (R + 1) // (tt + 1) - 1
            if rr < 2:
                continue
            off = npre
            rho = [x for x in body[off:off + rr]]
            T = [x for x in body[off + rr:off + rr + tt]]
            if off + rr + tt + rr * tt != B + 0 and npre + rr + tt + rr * tt != B:
                continue
            mr = all(rho[i] < rho[i + 1] for i in range(len(rho) - 1)) if len(rho) > 1 else False
            mt = all(T[i] < T[i + 1] for i in range(len(T) - 1)) if len(T) > 1 else False
            res.append((npre, rr, tt, B, mr, mt, rho, T))
    # prefer solutions with BOTH monotone
    good = [r for r in res if r[4] and r[5] and r[6]]
    if verbose:
        print("=" * 104)
        print(f"{rel}  k(stanzas)={k}  per-stanza lines={per}  header={ne[0][:60]!r}")
        print(f"  fields after header line B={B}")
        for npre, rr, tt, B, mr, mt, rho, T in res:
            tag = "OK " if (mr and mt) else "   "
            print(f"   {tag}npre={npre} nr={rr} nt={tt}  chk nr+nt+nrnt={rr+tt+rr*tt} "
                  f"(B-npre={B-npre})  mono_rho={mr} mono_T={mt}"
                  + (f"  rho {rho[0]:.3f}..{rho[-1]:.3f}  T {T[0]:.3f}..{T[-1]:.3f}" if good and (mr and mt) else ""))
        if not res:
            print("   NO integer solution of nr+nt+nr*nt = B-npre for npre in (0,1,2,4)")
    return good


CASES = [("mat_Au-1.0/AU_op03p", 20), ("mat_Gd/Gd20PLANCK", 20),
         ("mat_Ti/Ti_Planck", 20), ("mat_Al-1.0/1041_PLANCK", 1)]
for rel, k in CASES:
    solve_group(rel, k)

print("\n\n########## AU_op03p: DIRECT verification of nr=nt=20 layout ##########")
p = os.path.join(MAT, "mat_Au-1.0", "AU_op03p")
d = raw(p)
ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
blk = ne[0:112]
vals = []
for l in blk:
    vals += [num(x) for x in tok15(l, 15)]
vals = [x for x in vals if x is not None]
print("  stanza0 first 8 vals:", [f"{v:.4f}" for v in vals[:8]])
print("  NOTE field1 (LABEL) was dropped -> so vals align as:")
print("    [0]=tid [1]=h_lo [2]=h_hi [3]=split_rho0 [4]=split_rho1 ...")
rho = vals[3:23]
T = vals[23:43]
print(f"  rho (20) = {[round(x,3) for x in rho]}")
print(f"  T   (20) = {[round(x,3) for x in T]}")
print(f"  monotone rho={all(rho[i]<rho[i+1] for i in range(19))} T={all(T[i]<T[i+1] for i in range(19))}")
print(f"  data starts at idx 43: {[round(x,4) for x in vals[43:48]]}")
print(f"  total vals={len(vals)}  3+40+400={3+40+400}")
