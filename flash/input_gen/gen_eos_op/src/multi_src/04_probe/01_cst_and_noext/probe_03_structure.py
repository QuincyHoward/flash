# -*- coding: utf-8 -*-
"""probe_03_structure: the ncol=5/6 anomaly, blank lines, block structure, closure."""
import os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
inv = json.load(open(os.path.join(HERE, "cst_inventory.json"), encoding="utf-8"))

def L(p):
    return open(p, "r", encoding="utf-8", errors="replace").read().splitlines()

def dump_anomalies(rel, tag):
    p = [r for r in inv if r["rel"] == rel][0]["path"]
    ls = L(p)
    print("\n===== %s  (%s)  total lines=%d =====" % (rel, tag, len(ls)))
    print("L0:", repr(ls[0])); print("L1:", repr(ls[1]))
    # find lines whose split != 4 after header
    anom = []
    for i, ln in enumerate(ls):
        if i < 2: continue
        n = len(ln.split())
        if n != 4:
            anom.append((i, n, ln))
    print("anomalous line count (split != 4):", len(anom))
    print("first 12 anomalies:")
    for i, n, ln in anom[:12]:
        print("   idx=%5d ncol=%d repr=%r" % (i, n, ln))
    print("last 6 anomalies:")
    for i, n, ln in anom[-6:]:
        print("   idx=%5d ncol=%d repr=%r" % (i, n, ln))
    # position of anomalies: are they periodic?
    idxs = [a[0] for a in anom]
    if len(idxs) > 2:
        diffs = Counter(idxs[i+1]-idxs[i] for i in range(len(idxs)-1))
        print("gap histogram (top):", diffs.most_common(8))
    return p, ls, anom

p1, ls1, a1 = dump_anomalies("mat_Ne/Ne.cst", "DE")
p2, ls2, a2 = dump_anomalies("mat_He/Untitled.CST", "EN")
p3, ls3, a3 = dump_anomalies("Ta2O5/Ta2O5.cst", "DE")

print("\n\n### ARE ANOMALIES ONE EXTRA TOKEN OR A WRAPPED LINE? ###")
for p, ls, a, tag in ((p1, ls1, a1, "DE-mat_Ne"), (p2, ls2, a2, "EN-mat_He")):
    print("\n-- %s --" % tag)
    for i, n, ln in a[:6]:
        print("  prev idx=%d repr=%r" % (i-1, ls[i-1]))
        print("  anom idx=%d repr=%r" % (i, ln))
        print("  next idx=%d repr=%r" % (i+1, ls[i+1]))

print("\n\n### BLANK LINES ###")
for rel in ("mat_Ne/Ne.cst", "mat_He/Untitled.CST", "mat_B/B.cst"):
    p = [r for r in inv if r["rel"] == rel][0]["path"]
    ls = L(p)
    blanks = [i for i, ln in enumerate(ls) if not ln.strip()]
    print("%-24s blanks=%d at indices %s" % (rel, len(blanks), blanks[:20]))

print("\n\n### CLOSURE: ln(lines) and column-1 value census ###")
for r in inv:
    ls = L(r["path"])
    n = len(ls)
    # count data lines
    data = [x for x in ls[2:] if x.strip()]
    # column 0 (density) monotone non-decreasing?
    try:
        v0 = []
        for x in data:
            t = x.split()
            if len(t) == 4:
                try: v0.append(float(t[0]))
                except: v0.append(None)
        mono = all(v0[i] <= v0[i+1] for i in range(len(v0)-1) if v0[i] is not None and v0[i+1] is not None)
    except Exception as e:
        mono = "err:" + str(e)
    print("%-26s lines=%6d data=%6d  col0_monotone=%s  last_col0=%r" %
          (r["rel"], n, len(data), mono, data[-1].split()[0] if data else None))
