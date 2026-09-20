# -*- coding: utf-8 -*-
"""FINAL Group-A proof: sub-table = 110 full lines + 1 split line = 111 lines.
  token count per sub-table = 4 (hdr) + 110*4 + 2 = 446
  446 = 6 + nr + nt + nr*nt  with nr=20, nt=20 -> 6+20+20+400 = 446  *** EXACT ***"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

print("### Verify the arithmetic identity: 4+110*4+2 = 6+20+20+20*20 ?")
print("   4+440+2 =", 4 + 440 + 2, " ; 6+20+20+400 =", 6 + 20 + 20 + 400)
print("   MATCH:", 4 + 440 + 2 == 6 + 20 + 20 + 400)

A_SET = ["mat_Au-1.0/AU_op03p", "mat_Au-1.0/AU_op03r", "mat_Au-1.0/AU_op03e",
         "mat_Au-1.0/Au100PLANCK", "mat_Au-1.0/Au100EPS", "mat_Au-1.0/Au100ROSS",
         "mat_Gd/Gd100PLANCK", "mat_Gd/Gd100EPS", "mat_Gd/Gd100ROSS",
         "mat_Gd/Gd20PLANCK", "mat_Gd/Gd20EPS", "mat_Gd/Gd20ROSS",
         "mat_Gd/Gd_op100PLANCK", "mat_Gd/Gd_op100EPS", "mat_Gd/Gd_op100ROSS",
         "mat_Ti/Ti_Planck", "mat_Ti/Ti_Ross", "mat_Ti/Ti_EPS",
         "mat_Be-1.0/opbe",
         "CH/C_mopp", "CH/C_mopr", "CH/CHSi1_mopp", "CH/CHSi1_mopr",
         "CH/CH_mopp20", "CH/CH_mopr20", "CH/CHSi10_mopp", "CH/CHSi10_mopr",
         "CHBr3at%/C50H47Br3_mopp", "CHBr3at%/C50H47Br3_mopr",
         "Ta2O5/Ta2O5_mopp", "Ta2O5/Ta2O5_mopr",
         "mat_C-1.0/CHSi1_mopp", "mat_C-1.0/CHSi1_mopr", "mat_C-1.0/CH_mopp20",
         "mat_CHBr/C50H38Br12_mopp", "mat_CHBr/C50H38Br12_mopr",
         "mat_CHBr/CHBr3at%/C50H47Br3_mopp", "mat_CHBr/CHBr3at%/C50H47Br3_mopr",
         "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Others/CH10Water1/CH2_H2O_1m1opr",
         "mat_Others/CH10Water2/CH2_H2O_2m1opp", "mat_Others/CH10Water2/CH2_H2O_2m1opr",
         "mat_Ti/Ti_EPS"]

print("\n" + "=" * 112)
print(f"{'file':<44}{'N15':>8}{'nlines':>7}{'nsplit':>7}{'746*nb':>9}{'N-746nb':>9}{'ok':>4}")
print("=" * 112)
bad = []
for rel in A_SET:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    if not os.path.isfile(p):
        print("MISSING", rel); continue
    d = raw(p)
    ls = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    nsp = sum(1 for l in ls if len(l) != 60)
    f, tail = all_tokens(p, 15)
    N = len(f)
    nb = nsp
    ok = (N - 746 * nb == 0)
    if not ok: bad.append(rel)
    print(f"{rel:<44}{N:>8}{len(ls):>7}{nsp:>7}{746*nb:>9}{N-746*nb:>9}{str(ok):>4}")
print("\nFAILURES:", bad)
