# -*- coding: utf-8 -*-
"""probe_08_noext: enumerate ALL extensionless files under matter++/, group by pattern."""
import os, json, re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op"
ROOT = os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++")

noext = []
for dp, dns, fns in os.walk(ROOT):
    for fn in fns:
        if os.path.splitext(fn)[1] == "":
            p = os.path.join(dp, fn)
            try:
                sz = os.path.getsize(p)
            except OSError:
                sz = -1
            noext.append((os.path.relpath(p, ROOT).replace("\\", "/"), sz))

print("TOTAL extensionless files under matter++/:", len(noext))
print("=" * 100)

# top-level dir histogram
d0 = Counter(x[0].split("/")[0] for x in noext)
print("\n### by material dir ###")
for k in sorted(d0):
    print("  %-22s %d" % (k, d0[k]))

print("\n### full list (path, size) ###")
for rel, sz in sorted(noext):
    print("  %-52s %8d" % (rel, sz))

# --- classify by basename pattern ---
print("\n### basename patterns ###")
def pat(name):
    b = os.path.basename(name)
    # numeric-only or numeric_ieos
    if re.fullmatch(r"\d+", b): return "<all-digits>"
    if re.fullmatch(r"\d+_ieos", b): return "<digits>_ieos"
    if re.fullmatch(r"\d+_[A-Za-z0-9]+", b): return "<digits>_<token>"
    m = re.match(r"^([A-Za-z][A-Za-z0-9\-]*?)_(.*)$", b)
    if m:
        return "<mat>_" + m.group(2)
    return "<bare:%s>" % b

pc = Counter(pat(x[0]) for x in noext)
print("\n  pattern -> count")
for k, v in pc.most_common():
    print("    %-34s %d" % (k, v))

json.dump(noext, open(os.path.join(HERE, "noext_inventory.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
