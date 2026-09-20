# -*- coding: utf-8 -*-
"""Verify the local Al.feos line widths + locate all local FEOS-family files."""
import os, sys, glob
sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
OUT = os.path.join(ROOT, ".workbuddy", "tmp", "al_feos_probe.out")
buf = []
def p(*a):
    buf.append(" ".join(str(x) for x in a))

# find local FEOS-family files anywhere under the working tree of interest
p("=== LOCAL FEOS-family files (search from layer3) ===")
root3 = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3"
pats = ["*.feos", "*.mexport", "*.cst", "*.critical.dat", "*.data.txt",
        "*.ist", "*.isc", "*.ise", "*.mnt", "*.hug", "*.301", "*.304", "*.305"]
found = {}
for pat in pats:
    hits = glob.glob(os.path.join(root3, "**", pat), recursive=True)
    found[pat] = hits
    p(f"--- {pat}: {len(hits)}")
    for h in hits[:25]:
        p("    ", h, os.path.getsize(h), "bytes")

# Detailed probe of Al.feos
cands = found.get("*.feos", [])
for c in cands:
    p("=" * 78)
    p("DETAIL:", c, os.path.getsize(c), "bytes")
    p("=" * 78)
    try:
        with open(c, "r", errors="replace") as f:
            raw = f.read()
    except PermissionError as e:
        p("  SKIP (locked):", e)
        continue
    lines = raw.split("\n")
    p("total lines:", len(lines))
    p("first 6 lines (len, content):")
    for i, l in enumerate(lines[:6]):
        p(f"  [{i}] len={len(l)} | {l}")
    # collect length histogram of the numeric body
    from collections import Counter
    cnt = Counter(len(l.rstrip()) for l in lines if l.strip())
    p("line-length histogram (top 12):")
    for L, n in cnt.most_common(12):
        p(f"   len={L}: {n} lines")
    # check the 15-char hypothesis
    p("first data-looking line, split every 15 chars:")
    for l in lines:
        if len(l) >= 60 and any(ch.isdigit() for ch in l):
            for s in range(0, min(len(l), 150), 15):
                p(f"   [{s:3d}:{s+15:3d}] {l[s:s+15]!r}")
            break
    p("")

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(buf))
print("wrote", OUT, len(buf), "lines")
