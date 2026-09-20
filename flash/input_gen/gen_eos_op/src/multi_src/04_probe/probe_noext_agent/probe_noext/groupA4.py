# -*- coding: utf-8 -*-
"""PROOF: The 30-char split line = (rho_first, T_last) of the CURRENT sub-table.
Each of the 20 sub-tables carries a full nr+nt grid + nr*nt data.
Verify: file's line-stream partitions exactly at the 30-char lines; and
        the boundary of subtable k is byte-aligned at the split line."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

p = os.path.join(MAT, "mat_Au-1.0", "AU_op03p")
d = raw(p)
ls = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
print("n content lines =", len(ls))
splitidx = [i for i, l in enumerate(ls) if len(l) != 60]
print("indices of non-60 lines =", splitidx[:25])
print("count =", len(splitidx))

print("\n--- Around the 2nd split line ---")
for i in range(110, 120):
    print(f"  L{i} len={len(ls[i])} {ls[i]!r}")
print("\n--- Around the 80th (last) split line ---")
for i in range(2230, 2241):
    print(f"  L{i} len={len(ls[i])} {ls[i]!r}")

# Count fields per sub-table region
print("\n--- Per-region field counts ---")
bounds = [-1] + splitidx + [len(ls) - 1]
tot = 0
for k in range(1, len(bounds) - 1):
    a, b = bounds[k], bounds[k + 1]
    nf = sum(len(ls[j]) // 15 for j in range(a, b + 1))
    tot += nf
    if k <= 4 or k >= len(bounds) - 3:
        print(f"  region {k}: lines {a+1}..{b}  fields={nf}")
# header is line 0
hdrf = len(ls[0]) // 15
print(f"  header line0: fields={hdrf}")
print(f"  sum regions = {tot}  +header = {tot+hdrf}  vs N15 = {len(all_tokens(p,15)[0])}")

# Alternative: maybe the 30-char line belongs to the PREVIOUS or NEXT stanza
print("\n--- ALTERNATIVE: stanza = [30-line][60 lines][60-line hdr][30-line] ... ---")
print("  region k from splitidx[k]+1 .. splitidx[k+1] :")
for k in range(0, 5):
    a, b = splitidx[k] + 1, splitidx[k + 1]
    nf = sum(len(ls[j]) // 15 for j in range(a, b + 1))
    print(f"    k={k}: lines {a+1}..{b}  fields={nf}   firstL={ls[a][:60]!r}")
