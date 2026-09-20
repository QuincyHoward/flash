# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
R = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"
def h(rel, n=8, maxlen=150):
    fp = os.path.join(R, rel)
    if not os.path.exists(fp):
        print("### %-52s <MISSING>" % rel); return
    sz = os.path.getsize(fp)
    raw = open(fp, "rb").read(2500)
    print("### %s  (%d B)" % (rel, sz))
    if not raw: print("    <EMPTY>"); print(); return
    nul = raw.count(b"\x00")
    pr = sum(1 for b in raw if 9 <= b <= 13 or 32 <= b <= 126) / len(raw)
    if nul or pr < 0.90:
        print("    [BINARY] nul=%d printable=%.3f hex=%s" % (nul, pr, raw[:32].hex(" ")))
    else:
        for i, L in enumerate(raw.decode("utf-8", "replace").splitlines()[:n]):
            print("    L%02d| %s" % (i + 1, L[:maxlen]))
    print()
for a in sys.argv[1:]: h(a)
