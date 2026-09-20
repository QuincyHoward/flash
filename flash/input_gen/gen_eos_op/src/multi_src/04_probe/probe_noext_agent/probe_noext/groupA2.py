# -*- coding: utf-8 -*-
"""Group A deep structure: find the TRUE nr/nt by scanning line lengths and
locating the rho-grid / T-grid / data block boundaries."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def structure(rel, verbose=True):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ls = [l.rstrip(b"\r") for l in d.split(b"\n")]
    if ls and ls[-1] == b"":
        ls = ls[:-1]
    lens = [len(l) for l in ls]
    if verbose:
        print("=" * 100)
        print(rel, os.path.getsize(p))
    # run-length encode the line lengths, recording 1-based line numbers
    runs = []
    i = 0
    while i < len(lens):
        j = i
        while j + 1 < len(lens) and lens[j + 1] == lens[i]:
            j += 1
        runs.append((i + 1, j + 1, lens[i], j - i + 1))
        i = j + 1
    if verbose:
        for a, b, L, c in runs[:14]:
            f = L // 15
            print(f"  lines {a:>6}-{b:<6} len={L:>4} fields={f:>3} count={c}")
        if len(runs) > 14:
            print(f"  ... {len(runs)} runs total")
    return ls, lens, runs


def grid_analysis(rel):
    ls, lens, runs = structure(rel)
    # find where full-60 lines stop and short lines appear
    print(f"\n--- GRID SCAN {rel}")
    # A: token stream approach. Determine block boundaries by the writer rule.
    f, tail = all_tokens(os.path.join(MAT, rel.replace("/", os.sep)), 15)
    print(f"  N15={len(f)} leftover={tail!r}")
    # Scan for candidate nr: assume rho grid = first nr values, and the rho grid
    # should be monotone increasing and smooth. Then T grid follows.
    v = nums(f)
    # print first 60 values with index
    for i in range(0, min(70, len(v))):
        print(f"    v[{i:>5}] = {f[i]!r}")


for r in ["mat_Au-1.0/AU_op03p"]:
    grid_analysis(r)

print("\n\n### Line-length runs for the whole Group-A set (to spot uniform grids)")
for rel in ["mat_Au-1.0/AU_op03p", "mat_Gd/Gd100PLANCK", "mat_Gd/Gd20PLANCK",
            "mat_Gd/Gd_op100PLANCK", "mat_Al-1.0/1041_PLANCK", "CH/CHSi1_mopp",
            "CH/CH_mopp20", "CH/C_mopp", "Ta2O5/Ta2O5_mopp", "mat_Ti/Ti_Planck",
            "mat_Be-1.0/opbe", "mat_Ti/Ti_Ross"]:
    structure(rel)
    print()
