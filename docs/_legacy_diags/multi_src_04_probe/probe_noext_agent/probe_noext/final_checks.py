# -*- coding: utf-8 -*-
"""Final confirmations: (1) Group B 186/280-byte relation, (2) Group H closure,
   (3) Group A table-number convention, (4) Ce.INPUT cross-check."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

print("### B1. Group B: 186-B vs 280-B relation")
b186 = os.path.join(MAT, "mat_Ge", "Ge_2002FED_Planck")
b280 = os.path.join(MAT, "Thermos", "mat_Mo", "Mo_Ideal_Gas")
print(" 186:", raw(b186))
print(" 280:", raw(b280))
print(" HEAD 186 == HEAD(280, upto 186)?", raw(b280)[:186 - 1] == raw(b186)[:186 - 1])

print("\n### B2. Group B: 305-B IDEAL_GAS/IEOS relation -> is 305 = 280 + 25?")
a = raw(os.path.join(MAT, "mat_Be-1.0", "BE_eos_i"))
b = raw(os.path.join(MAT, "Thermos", "mat_Mo", "Mo_Ideal_Gas"))
print(" 305 first 245:", a[:245])
print(" 280 first 245:", b[:245])

print("\n### H. Ta2O5_1G_MULTI: closure  nr+nt+nr*nt+2 == N?  and vs Ta2O5_1G_MULTI.dat_MULTI")
p = os.path.join(MAT, "Ta2O5", "Ta2O5_1G_MULTI")
f, tail = all_tokens(p, 15)
N = len(f)
print(f" N15={N} tail={tail!r}")
hdr = f[:4]
print(f" hdr = {hdr}")
import math
for n in range(2, 200):
    for t in range(2, 200):
        if 4 + n + t + n * t == N or 2 + n + t + n * t == N or n + t + n * t == N:
            print(f"  CLOSES nr={n} nt={t}  (4+n+t+n*t={4+n+t+n*t}, 2+..={2+n+t+n*t}, ..,={n+t+n*t})")

print("\n### A-convention check: table numbers")
for rel in ["mat_Be-1.0/opbe", "CH/CHSi1_mopp", "CH/C_mopp", "mat_Au-1.0/AU_op03p",
            "mat_Gd/Gd100PLANCK", "mat_Gd/Gd100EPS", "mat_Gd/Gd100ROSS", "mat_Gd/Gd100ZEFF",
            "mat_Ti/Ti_Planck", "Ta2O5/Ta2O5_mopp", "Ta2O5/Ta2O5_mopr", "mat_Au-1.0/Au100ZEFF"]:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    l0 = d.split(b"\n")[0].rstrip(b"\r")
    print(f"  {rel:<36} {l0[:60]!r}")
print("\n  Ce.INPUT:")
ce = os.path.join(MAT, "mat_Ce", "Ce.INPUT")
print("   exists:", os.path.isfile(ce))
if os.path.isfile(ce):
    txt = open(ce, encoding="latin-1").read()
    for kw in ("NPLA", "NROSS", "NEPS", "NRHO", "NT"):
        for m in re.finditer(kw, txt):
            print("   ", txt[max(0, m.start()-40):m.start()+80].replace("\r", "").replace("\n", " | "))
