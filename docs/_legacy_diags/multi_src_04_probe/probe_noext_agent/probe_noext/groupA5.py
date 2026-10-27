# -*- coding: utf-8 -*-
"""Derive the true sub-table count. AU_op03p: 136040 bytes.
Line stream: 1 header + nb stanchions. Stanchion j = [60-char hdr L][30-char L][A_j 60-char lines]
bytes = 60 + sum_j ( 60 + 30 + 60*A_j ) + 2240 newlines
=> 136040 = 60 + 2240 + sum_j (90 + 60 A_j) = 2300 + 90 nb + 60 * 2199
=> nb = (136040 - 2300 - 131940)/90"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

for rel in ["mat_Au-1.0/AU_op03p", "mat_Gd/Gd100PLANCK", "mat_Gd/Gd20PLANCK",
            "mat_Gd/Gd_op100PLANCK", "mat_Ti/Ti_Planck", "mat_Be-1.0/opbe",
            "CH/C_mopp", "CH/CHSi1_mopp", "Ta2O5/Ta2O5_mopp",
            "mat_Others/CH10Water1/CH2_H2O_1m1opp", "mat_Al-1.0/1041_PLANCK",
            "mat_Ti/Ti_Ross"]:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    sz = os.path.getsize(p)
    d = raw(p)
    ls = [l.rstrip(b"\r") for l in d.split(b"\n")]
    nlines_total = d.count(b"\n") + (0 if d.endswith(b"\n") else 1)
    nonempty = [l for l in ls if l != b""]
    nlines = len(nonempty)
    # bytes = 15*N15 + sum(len of short lines' leftovers) + newlines
    f, tail = all_tokens(p, 15)
    short = [l for l in nonempty if len(l) % 15 != 0]
    extra = sum(len(l) - (len(l) // 15) * 15 for l in short)
    nl = d.count(b"\n") + d.count(b"\r") - d.count(b"\r\n") * 0
    nl = d.count(b"\n") + d.count(b"\r")
    print(f"{rel:<44} size={sz:>9} N15={len(f):>7} tail={len(tail)} "
          f"nonempty_lines={nlines:>6} short10/30/45={sum(1 for l in nonempty if len(l) in (10,30,45)):>4} "
          f"misfit_bytes={extra} nl_chars={nl:>6} reconstruct={15*len(f)+extra+nl}")
