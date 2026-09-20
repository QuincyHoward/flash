# -*- coding: utf-8 -*-
"""probe_06_final_closure: exact closure arithmetic for cst files."""
import os, json, re
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
inv = json.load(open(os.path.join(HERE, "cst_inventory.json"), encoding="utf-8"))
def L(p): return open(p, "r", encoding="utf-8", errors="replace").read().splitlines()

print("### EXACT CLOSURE: N = 1 + B*(title + hdr + K data)   with stride 125 = 1+B*K? ###")
print("Hypothesis: total lines N = B * 125 + 1  where B = #isotherms; each block = 1 title + 1 hdr + 123 data\n")
allok = True
for r in inv:
    ls = L(r["path"])
    n = len(ls)
    idx = [i for i, ln in enumerate(ls) if "sotherm" in ln]
    B = len(idx)
    pred = B * 125 + 1
    ok = (pred == n)
    if not ok: allok = False
    print("%-26s N=%6d  B=%3d  B*125+1=%6d  %s  stride=%s" % (
        r["rel"], n, B, pred, "OK " if ok else "BAD",
        (idx[1]-idx[0]) if len(idx) > 1 else "-"))
print("  ALL CLOSE:", allok)

print("\n### per-isotherm data-line count (block = 123 data) ###")
for r in inv[:3]:
    ls = L(r["path"])
    idx = [i for i, ln in enumerate(ls) if "sotherm" in ln] + [len(ls)]
    counts = Counter()
    for k in range(len(idx)-1):
        start = idx[k]
        end = idx[k+1]
        blk = ls[start:end]
        # within block: line0=title, line1=hdr, rest=data
        ndata = sum(1 for ln in blk[2:] if len(ln.split()) >= 4 and any(c.isdigit() for c in ln))
        titles = sum(1 for ln in blk if "sotherm" in ln)
        hdrs = sum(1 for ln in blk if "dichte" in ln or "density" in ln)
        counts[(len(blk), titles, hdrs, ndata)] += 1
    print("  %-22s block-signature histogram: %s" % (r["rel"], dict(counts)))

print("\n### EN file per-isotherm data count (all blocks) ###")
ls = L([r for r in inv if r["cls"] == "EN"][0]["path"])
idx = [i for i, ln in enumerate(ls) if "sotherm" in ln] + [len(ls)]
c = Counter()
for k in range(len(idx)-1):
    blk = ls[idx[k]:idx[k+1]]
    ndata = sum(1 for ln in blk if not any(ch.isalpha() for ch in ln) and ln.strip())
    c[ndata] += 1
print("  EN per-block data-count histogram:", dict(c))
