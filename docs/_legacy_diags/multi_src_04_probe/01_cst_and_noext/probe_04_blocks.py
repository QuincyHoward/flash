# -*- coding: utf-8 -*-
"""probe_04_blocks: exact block structure, isotherm count, per-block grid, closure."""
import os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")
inv = json.load(open(os.path.join(HERE, "cst_inventory.json"), encoding="utf-8"))

def L(p): return open(p, "r", encoding="utf-8", errors="replace").read().splitlines()

print("### BLOCK STRUCTURE: title-line indices & isotherm temperatures ###\n")
summary = []
for r in inv:
    ls = L(r["path"])
    n = len(ls)
    # title lines = lines that are NOT 4 numeric fields
    titles = []
    for i, ln in enumerate(ls):
        t = ln.split()
        try:
            [float(x) for x in t]
            isnum = True
        except Exception:
            isnum = False
        if not isnum:
            titles.append((i, ln))
    # The *data-header* line (Moleküldichte / Particle density) is also non-numeric
    hdrs = [x for x in titles if "dichte" in x[1] or "density" in x[1]]
    iso = [x for x in titles if "sotherm" in x[1]]
    nums = [re.search(r"(\d+)", x[1]).group(1) for x in iso] if iso else []
    summary.append(dict(rel=r["rel"], n=n, ntitle=len(titles), nhdr=len(hdrs),
                        niso=len(iso), nnum=n - len(titles),
                        tmin=nums[0] if nums else None, tmax=nums[-1] if nums else None,
                        iso_lineno=[x[0] for x in iso]))
    print("%-26s lines=%6d numeric=%6d hdr=%2d iso=%3d T:[%s .. %s]" %
          (r["rel"], n, n - len(titles), len(hdrs), len(iso),
           nums[0] if nums else "-", nums[-1] if nums else "-"))

print("\n### Arithmetic check: numeric + hdr + iso == lines ? ###")
ok = True
for s in summary:
    lhs = s["nnum"] + s["nhdr"] + s["niso"]
    if lhs != s["n"]:
        ok = False
        print("  MISMATCH", s["rel"], lhs, s["n"])
print("  all close:", ok)

print("\n### data-per-isotherm = numeric / niso ###")
c = Counter()
for s in summary:
    q = s["nnum"] / s["niso"]
    c[q] += 1
    print("%-26s numeric/iso = %.4f" % (s["rel"], q))
print("  ratio histogram:", dict(c))

print("\n### How many distinct isotherm T values? (per file, first/last) ###")
for s in summary[:4] + [x for x in summary if x["rel"] == "mat_He/Untitled.CST"]:
    p = [r for r in inv if r["rel"] == s["rel"]][0]["path"]
    ls = L(p)
    iso = [ln for ln in ls if "sotherm" in ln]
    Ts = [re.search(r"(\d+)", ln).group(1) for ln in iso]
    print("%-26s niso=%d first5=%s last3=%s" % (s["rel"], len(Ts), Ts[:5], Ts[-3:]))

print("\n### HDR count detail (DE should be 1? EN seems to repeat) ###")
for s in summary:
    if s["nhdr"] != s["niso"]:
        print("  %-26s nhdr=%d niso=%d" % (s["rel"], s["nhdr"], s["niso"]))

print("\n### EN-specific: title/header alternation pattern ###")
ls = L([r for r in inv if r["cls"] == "EN"][0]["path"])
for i in range(120, 132):
    print("  idx=%5d repr=%r" % (i, ls[i]))
