# -*- coding: utf-8 -*-
"""probe_05_closure: verify 125*(N-1)+1 structure, delta-token hypothesis, EN char check."""
import os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
inv = json.load(open(os.path.join(HERE, "cst_inventory.json"), encoding="utf-8"))
def L(p): return open(p, "r", encoding="utf-8", errors="replace").read().splitlines()

print("### CLOSURE MODEL: T(1) title+1 hdr; N-1 blocks of 125 lines ###")
allok = True
for r in inv:
    ls = L(r["path"])
    n = len(ls)
    ntitle = sum(1 for ln in ls if any(c.isalpha() for c in ln))
    # model: 2 + 125*(batch-1) = n
    if (n - 2) % 125 == 0:
        batches = (n - 2) // 125 + 1
        recomputed = 2 + 125 * (batches - 1)
    else:
        batches = None; recomputed = None
    ok = (recomputed == n)
    if not ok: allok = False
    print("%-26s n=%6d  batches=%s  2+125*(B-1)=%s  OK=%s" % (r["rel"], n, batches, recomputed, ok))
print("  ALL CLOSE:", allok)

print("\n### Does the DE variant use 'ncol=5' because of trailing space in the TITLE only? ###")
for rel in ("mat_Ne/Ne.cst", "Ta2O5/Ta2O5.cst", "mat_B/B.cst"):
    p = [r for r in inv if r["rel"] == rel][0]["path"]
    ls = L(p)
    iso = [ln for ln in ls if "sotherm" in ln]
    sp = Counter(ln.endswith(" ") for ln in iso)
    print("%-22s title endswith-space: %s" % (rel, dict(sp)))
    # every 125th line is title -> confirm pure periodic
    idx = [i for i, ln in enumerate(ls) if "sotherm" in ln]
    d = Counter(idx[i+1]-idx[i] for i in range(len(idx)-1))
    print("%-22s title gaps: %s  first idx=%d" % (rel, dict(d), idx[0]))

print("\n### DE variant: is there a header line after each title, or only after the first? ###")
for rel in ("mat_Ne/Ne.cst", "mat_B/B.cst", "Ta2O5/Ta2O5.cst"):
    p = [r for r in inv if r["rel"] == rel][0]["path"]
    ls = L(p)
    for i in (0, 1, 2, 125, 126, 127, 250, 251, 252):
        print("   %-20s idx=%4d %r" % (rel, i, ls[i]))
    print()

print("\n### EN: is 'MBar' <-> 'load' genuinely glued (no space)? ###")
p = [r for r in inv if r["cls"] == "EN"][0]["path"]
ls = L(p)
h = ls[1]
i = h.find("MBar")
print("  slice:", repr(h[i:i+12]), "  chars:", [h[i+k] for k in range(12)])
print("  'MBar]load state' in h ?", "MBar]load state" in h)
print("  'MBar] load state' in h ?", "MBar] load state" in h)

print("\n### Column count sanity for DE data lines & EN data lines (split) ###")
for rel in ("mat_B/B.cst", "mat_Ne/Ne.cst", "mat_He/Untitled.CST"):
    p = [r for r in inv if r["rel"] == rel][0]["path"]
    ls = L(p)
    c = Counter(len(ln.split()) for ln in ls if not any(ch.isalpha() for ch in ln))
    print("  %-22s numeric-line split census: %s" % (rel, dict(c)))
