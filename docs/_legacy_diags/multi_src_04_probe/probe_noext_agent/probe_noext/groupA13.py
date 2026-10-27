# -*- coding: utf-8 -*-
"""GROUP A — FINAL CORRECT MODEL (proven by boundary counts).

FILE = [GRID STANZA] [GROUP 1] [GRID STANZA] [GROUP 2] ... [GROUP 1] ...
Wait: the detected stanza histogram for AU_op03p is {2:1, 110:1, 112:19}.
So: 1 short stanza (2 lines) + 1 stanza of 110 lines + 19 stanzas of 112 lines.
For C_mopp: {2:20, 484:20} -> 20 pairs of (2-line, 484-line).
For CHSi1_mopp: {2:20, 473:20}.
For CH2_H2O_1m1opp: {2:44, 485:44}.

=> Structure: FILE = HEADER-STANZA + GROUP-STANZA + ( HEADER-STANZA + GROUP-STANZA )*
   HEADER-STANZA = 1 header line (60) + 1 split line (30)  = V 6
   GROUP-STANZA  = Nfull full lines                        = V 4*Nfull

For AU_op03p: 1 + 1 + 19*2 = 40 stanzas... no it's 21 stanzas total = 1 + 20.
  Actually: 1 two-line stanza + (1 x 110-line) + (19 x 112-line) = 21 stanzas.
  Hmm 110-line = 110*4 = 440 = 4*110 ; 112-line = 448.

Let me instead use the PAIR model: FILE = k * (HEADER(1 line/4f) + GRID_SPLIT(30) + FULL(m lines))
  AU_op03p: k=20 ; m=? Each pair = 1 hdr line + 1 split line + m full lines.
            total lines 2240 = 20*(2+m) -> m = 110.  values = 20*(6+440)=8920 OK
  C_mopp  : total 9720 ; if k=20: 2+m = 486 -> m=484 ;  values=20*(6+1936)=38840 != 38820
            if m=484, header line itself is 4f -> V=6+4*484=1942 ; 1942*20=38840. off by 20.
  So C_mopp must be k=20 with an extra: 38820-38840 = -20 -> one line less overall.
  Check: 9720 lines, 20 stanzas -> 486 lines each = 1 hdr + 1 split + 484 full -> V=6+1936=1942; 20*1942=38840.
  But N=38820 = 38840-20.  => ONE 15-char field missing per stanza, i.e. a 45-char line
     somewhere (the 45-char split lines!). Indeed C_mopp had 20 lines of len 45.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def pair_model(rel, k):
    """FILE = k * (1 hdr line (60) + 1 split line + m full lines). Return m, V, checks."""
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    nl = len(ne)
    if nl % k:
        return None
    per = nl // k
    # per = 2 + m  (hdr + split + m fulls) -> but split may itself be 45 or 30
    m = per - 2
    f, tail = all_tokens(p, 15)
    # per-stanza value count from the actual lines of stanza 0
    blk = ne[0:per]
    V = sum(len(l) // 15 for l in blk)
    return dict(k=k, per=per, m=m, V=V, N=len(f), nb_lines=nl,
                chk=k * V == len(f), hists={L: sum(1 for l in blk if len(l) == L) for L in set(len(l) for l in blk)})


print("PAIR MODEL: file = k * (hdr line + split line + m full lines); V = 6 + 4m")
print("=" * 110)
CFG = {
    "mat_Au-1.0/AU_op03p": [20],
    "mat_Au-1.0/Au100PLANCK": [100],
    "mat_Gd/Gd100PLANCK": [100],
    "mat_Gd/Gd20PLANCK": [20],
    "mat_Gd/Gd_op100PLANCK": [100],
    "mat_Ti/Ti_Planck": [20],
    "CH/C_mopp": [20],
    "CH/CHSi1_mopp": [20],
    "CH/CH_mopp20": [20],
    "mat_Others/CH10Water1/CH2_H2O_1m1opp": [44],
    "Ta2O5/Ta2O5_mopp": [96, 192],
    "mat_Be-1.0/opbe": [81],
    "mat_Al-1.0/1041_PLANCK": [1],
    "mat_Ti/Ti_Ross": [21],
}
for rel, ks in CFG.items():
    for k in ks:
        r = pair_model(rel, k)
        if r:
            print(f"{rel:<44} k={k:>4} per={r['per']:>4} m={r['m']:>4} V={r['V']:>6} "
                  f"k*V={k*r['V']:>8} N={r['N']:>8} MATCH={r['chk']}  "
                  f"hist={r['hists']}")
        else:
            print(f"{rel:<44} k={k:>4}  nl%k != 0")
