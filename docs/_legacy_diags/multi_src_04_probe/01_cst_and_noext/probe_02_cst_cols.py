# -*- coding: utf-8 -*-
"""probe_02_cst_cols: column layout, char-position tables, T in line0, INF census, closure."""
import os, json, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")

inv = json.load(open(os.path.join(HERE, "cst_inventory.json"), encoding="utf-8"))

def lines(p):
    return open(p, "r", encoding="utf-8", errors="replace").read().splitlines()

# ---------- 1. temperature in line0, across all files ----------
print("### LINE-0 TEMPERATURE SCAN ###")
tpat = re.compile(r"(\d+(?:\.\d+)?)")
tset = Counter()
for r in inv:
    m = tpat.search(r["l0"] or "")
    t = m.group(1) if m else "<none>"
    tset[t] += 1
    if r["cls"] == "EN":
        print("  EN file line0:", repr(r["l0"]))
print("distinct T tokens in line0:", dict(tset))
print("=> all files identical line0?", len(set(x["l0"] for x in inv)) == 1,
      "| distinct l0 count:", len(set(x["l0"] for x in inv)))

# ---------- 2. char-position tables of data lines ----------
print("\n### CHARACTER-POSITION TABLE (col index -> char) ###")
def pos_table(line, upto=None):
    s = line if upto is None else line[:upto]
    out = []
    for i, ch in enumerate(s):
        out.append("%2d:%s" % (i, ch if ch != " " else "_"))
    return " ".join(out)

for r in inv:
    if r["cls"] == "EN":
        print("\n-- EN %s --" % r["rel"])
        L = lines(r["path"])
        for k in (1, 2, 3):
            print("L%d len=%d repr=%s" % (k, len(L[k]), repr(L[k])))
        print("L1 pos:", pos_table(L[1]))
        print("L2 pos:", pos_table(L[2]))
        # find a line with a high column-3 magnitude, likely 6+ chars
        break

# German sample
for r in inv:
    if r["cls"] == "DE" and r["rel"].startswith("mat_B/"):
        print("\n-- DE %s --" % r["rel"])
        L = lines(r["path"])
        for k in (1, 2, 3, 4, 5):
            print("L%d len=%d repr=%s" % (k, len(L[k]), repr(L[k])))
        print("L1 pos:", pos_table(L[1], 90))
        print("L2 pos:", pos_table(L[2], 90))
        break

# ---------- 3. whitespace-split vs fixed-width feasibility ----------
print("\n### SPLIT-FIELD-COUNT CENSUS (all data lines of each file) ###")
def census(p, skip):
    cnt = Counter()
    lens = Counter()
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        f.readline(); f.readline()
        for ln in f:
            ln = ln.rstrip("\n")
            if not ln.strip():
                cnt["<blank>"] += 1
                continue
            cnt["ncol=%d" % len(ln.split())] += 1
            lens[len(ln)] += 1
    return cnt, lens

for r in inv[:6] + [x for x in inv if x["cls"] == "EN"]:
    if r["cls"] == "EN":
        continue
sub = [r for r in inv if r["rel"] in ("mat_B/B.cst", "mat_Ne/Ne.cst", "mat_He/Untitled.CST", "Ta2O5/Ta2O5.cst")]
for r in sub:
    c, l = census(r["path"], 2)
    print("%-26s split=%s" % (r["rel"], dict(c)))
    print("%-26s lenTop=%s" % ("", l.most_common(6)))

# ---------- 4. INF census ----------
print("\n### -1.#INF00 / non-IEEE infinity census ###")
tot_inf = Counter()
percol = Counter()
for r in inv:
    with open(r["path"], "r", encoding="utf-8", errors="replace") as f:
        hdr = [f.readline(), f.readline()]
        for i, ln in enumerate(f):
            if "#INF" in ln or "#IND" in ln or "NAN" in ln.upper() or "nan" in ln:
                tok = [t for t in ln.split() if "#" in t.upper()]
                for t in tok:
                    percol[t] += 1
                    key = t
                tot_inf[r["rel"]] += 1
print("files with INF:", len(tot_inf), "/", len(inv))
print("total lines containing INF:", sum(tot_inf.values()))
print("distinct INF tokens:", dict(percol))

# which column
print("\n### INF by column index (split) ###")
colcensus = Counter()
for r in inv:
    with open(r["path"], "r", encoding="utf-8", errors="replace") as f:
        f.readline(); f.readline()
        for ln in f:
            if "#INF" in ln:
                parts = ln.split()
                for ci, p in enumerate(parts):
                    if "#INF" in p:
                        colcensus[(r["cls"], ci, p)] += 1
for k in sorted(colcensus, key=lambda x: -colcensus[x])[:20]:
    print("  cls=%-2s col=%d token=%-14s n=%d" % (k[0], k[1], k[2], colcensus[k]))

# ---------- 5. python float() behavior on INF literal ----------
print("\n### Python float() on MSVC infinity literals ###")
for s in ["-1.#INF00e+000", "-1.#INF00e+00", "1.#INF00e+000", "-1.#IND00e+000", "-1.#QNAN0e+000", "nan", "inf"]:
    try:
        v = float(s)
        print("  float(%-16r) = %r  isinf=%s isnan=%s" % (s, v, v != v or v in (float('inf'), float('-inf')), v != v))
    except Exception as e:
        print("  float(%-16r) -> %s: %s" % (s, type(e).__name__, e))

print("\n### numpy behaviour (if available) ###")
try:
    import numpy as np
    a = np.array(["-1.#INF00e+000", "1.0", "nan"], dtype=str)
    try:
        print("  np.array(...).astype(float64) ->", a.astype(np.float64))
    except Exception as e:
        print("  astype raise:", type(e).__name__, e)
    try:
        print("  np.genfromtxt -> n/a inline")
    except Exception as e:
        pass
except ImportError:
    print("  numpy not available")
