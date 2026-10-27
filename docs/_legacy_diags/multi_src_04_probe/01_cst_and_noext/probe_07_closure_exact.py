# -*- coding: utf-8 -*-
"""probe_07_closure_exact: nail N = f(B). Check trailing line / final newline."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
inv = json.load(open(os.path.join(HERE, "cst_inventory.json"), encoding="utf-8"))

for rel in ("mat_B/B.cst", "mat_Ne/Ne.cst", "Ta2O5/Ta2O5.cst", "mat_He/Untitled.CST"):
    p = [r for r in inv if r["rel"] == rel][0]["path"]
    b = open(p, "rb").read()
    t = b.decode("utf-8")
    ls = t.splitlines()
    print("== %s ==" % rel)
    print("  bytes=%d  splitlines=%d  split('\\n')=%d  endswith \\n? %s  trailing=%r" %
          (len(b), len(ls), len(t.split("\n")), t.endswith("\n"), t[-30:]))
    idx = [i for i, ln in enumerate(ls) if "sotherm" in ln]
    B = len(idx)
    print("  B=%d  last title idx=%d  lines after last title:%d" % (B, idx[-1], len(ls)-idx[-1]))
    print("  N=1+B*125? -> %d vs N=%d  diff=%d" % (1 + B*125, len(ls), len(ls)-(1+B*125)))
    print("  N=B*125+2? -> %d  " % (B*125+2))
    print("  model N = 2 + 125*(B-1) + 125 = %d" % (2 + 125*(B-1) + 125))
    print("  exact: B=101 -> 1 + 125*101 = %d ; B=97 -> %d" % (1+125*101, 1+125*97))
    print()
