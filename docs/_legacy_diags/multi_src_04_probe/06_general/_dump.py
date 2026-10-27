# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"
def dump(rel, n=40, maxlen=240):
    fp = os.path.join(ROOT, rel)
    print("=" * 78); print("FILE: %s  bytes=%d" % (rel, os.path.getsize(fp)))
    raw = open(fp, "rb").read(200000)
    if not raw:
        print("<EMPTY>"); return
    nl = raw.count(b"\x00"); pr = sum(1 for b in raw if 9<=b<=13 or 32<=b<=126)/len(raw)
    print("BIN-DIAG len=%d nul=%d printable=%.3f" % (len(raw), nl, pr))
    for i, L in enumerate(raw.decode("latin-1").splitlines()[:n]):
        print("L%03d| %s" % (i+1, L[:maxlen]))
    print()
for r in sys.argv[1:]:
    dump(r)
