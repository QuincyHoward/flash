# -*- coding: utf-8 -*-
"""probe_01_cst: enumerate every *.cst / *.CST under matter++/ and classify."""
import os, io, json, hashlib

REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")

def find_all(root, exts):
    out = []
    for dp, dns, fns in os.walk(root):
        for fn in fns:
            e = os.path.splitext(fn)[1]
            if e.lower() in exts:
                out.append(os.path.join(dp, fn))
    return sorted(out)

def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()

def dec_lines(b, encs=("utf-8", "cp1252", "latin-1")):
    for e in encs:
        try:
            t = b.decode(e)
            return t.splitlines(), e
        except UnicodeDecodeError:
            continue
    t = b.decode("latin-1", "replace")
    return t.splitlines(), "latin-1(replace)"

def classify(l0, l1):
    blob = (l0 or "") + "||" + (l1 or "")
    if "Molek" in blob or "Isotherme" in blob or "Ladungszustand" in blob:
        return "DE"
    if "Particle density" in blob or "Isotherm T" in blob or "load state" in blob:
        return "EN"
    return "OTHER"

files = find_all(ROOT, {".cst"})
rows = []
for p in files:
    b = read_bytes(p)
    lines, enc = dec_lines(b)
    l0 = lines[0] if len(lines) > 0 else None
    l1 = lines[1] if len(lines) > 1 else None
    l2 = lines[2] if len(lines) > 2 else None
    cls = classify(l0, l1)
    rel = os.path.relpath(p, ROOT)
    rows.append(dict(rel=rel.replace("\\", "/"), path=p, size=len(b), nl=len(lines),
                     enc=enc, cls=cls, l0=l0, l1=l1, l2=l2,
                     md5=hashlib.md5(b).hexdigest()))

print("TOTAL .cst/.CST files:", len(rows))
print("=" * 100)
for i, r in enumerate(rows, 1):
    print("%2d [%s] %-42s size=%7d lines=%6d enc=%s" % (i, r["cls"], r["rel"], r["size"], r["nl"], r["enc"]))
print("=" * 100)
from collections import Counter
print("class counts:", dict(Counter(r["cls"] for r in rows)))
print("ext counts:", dict(Counter(os.path.splitext(r["rel"])[1] for r in rows)))

print("\n--- FIRST 3 LINES (repr) ---")
for i, r in enumerate(rows, 1):
    print("%2d [%s] %s" % (i, r["cls"], r["rel"]))
    print("     L0:", repr(r["l0"]))
    print("     L1:", repr(r["l1"]))
    print("     L2:", repr(r["l2"]))

with open(os.path.join(os.path.dirname(__file__), "cst_inventory.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
