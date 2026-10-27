# -*- coding: utf-8 -*-
"""GENERAL Group-A parser v2 — robust boundary detection.

Observation: the split line is the LAST line of a stanza (it holds the final rho value
+ the final T value). So stanza boundaries are determined by the split-line indices
themselves, not by a fixed count. Handle both 30-char and 45-char split lines.

Layout of one stanza (all values, in file order):
  [0] table id, [1] LABEL (PLANCK M / ROSSELAND M / EPS M), [2] band lo, [3] band hi
  [4 .. 4+s-1]  s = L/15 split-line fields -> these are rho[?] and T[n-1] redundancy
  then full lines' fields.
The WRITER layout for the canonical 20x20 case (which we PROVED):
  total stanza values V, with  6 + nr + nt + nr*nt = V,
  layout:  0..5 = preamble(4) + split(2),  6..6+nr-1 = rho, 6+nr..6+nr+nt-1 = T, rest = data
This exact model closed for AU_op03p / Gd_op100PLANCK / Gd100PLANCK.
For files where it does not close, the split-line count s>2 (45-char lines) or an
extra sub-header line exists -> report honestly.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def parse(rel, verbose=True):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    nl = len(ne)
    # index lines that are stanza headers: length 60 AND next line length != 60
    # (a stanza = hdr(60) + split(!=60... but 45 or 30) + fulls(60))
    # Simpler: split lines are those whose index immediately follows a 60-line whose
    # NEXT line is not 60-wide; detect by len%60 != 0 -> split lines
    spl = [i for i, l in enumerate(ne) if len(l) % 60 != 0]
    # for the 45 case: 45%60=45 !=0  ok. for 30: ok.
    nb = len(spl)
    if nb == 0:
        nb = 1
        starts = [0]
    else:
        starts = [s - 1 for s in spl]   # hdr line index of each stanza
    recs = []
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else nl
        blk = ne[st:en]
        hdr = blk[0]
        L = len(blk[1]) if len(blk) > 1 else 60
        s = L // 15
        V = sum(len(l) // 15 for l in blk)
        W = V - 6
        cands = []
        for t in range(1, 3000):
            if W - t > 0 and (W - t) % (t + 1) == 0:
                r = (W - t) // (t + 1)
                vals = []
                for l in blk:
                    vals += nums(tok15(l, 15))
                vals = [x for x in vals if x is not None]
                if len(vals) < 6 + r + t:
                    continue
                rho = vals[6:6 + r]
                T = vals[6 + r:6 + r + t]
                if len(rho) < r or len(T) < t:
                    continue
                mr = all(rho[i] < rho[i + 1] for i in range(len(rho) - 1))
                mt = all(T[i] < T[i + 1] for i in range(len(T) - 1))
                if mr and mt:
                    cands.append((r, t))
        recs.append(dict(hdr=hdr.decode("latin-1"), L=L, s=s, V=V, nlines=len(blk),
                         cands=cands))
    if verbose:
        print("=" * 104)
        print(f"{rel}   nb(stanzas)={nb}  filevals={len(all_tokens(p,15)[0])}")
        for k, r in enumerate(recs[:4]):
            print(f"  st{k}: hdr={r['hdr'][:60]!r}")
            print(f"        L={r['L']} splitfields={r['s']} nlines={r['nlines']} V={r['V']} "
                  f"cands(nr,nt)={r['cands']}")
        if nb > 4:
            print(f"  ... ({nb-4} more stanzas)")
        # global consistency
        Vs = set(r['V'] for r in recs)
        cs = set(tuple(r['cands']) for r in recs)
        print(f"  ALL stanzas same V? {len(Vs)==1} {Vs}")
        print(f"  ALL stanzas same cand set? {len(cs)==1} {cs}")
    return recs


FILES = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/Au100PLANCK", "mat_Gd/Gd100PLANCK",
         "mat_Gd/Gd20PLANCK", "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck",
         "mat_Be-1.0/opbe", "CH/C_mopp", "CH/CHSi1_mopp", "Ta2O5/Ta2O5_mopp",
         "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Al-1.0/1041_PLANCK",
         "mat_Ti/Ti_Ross"]
for rel in FILES:
    parse(rel)
