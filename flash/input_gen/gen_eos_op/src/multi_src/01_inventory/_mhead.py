# -*- coding: utf-8 -*-
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
R = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"
M = os.path.join(R, "matter++")

def h(rel, n=10, maxlen=170):
    fp = os.path.join(M, rel)
    if not os.path.exists(fp):
        print("### %-46s  <MISSING>" % rel); return
    sz = os.path.getsize(fp)
    raw = open(fp, "rb").read(3000)
    print("### %s  (%d bytes)" % (rel.replace("\\", "/"), sz))
    if not raw:
        print("    <EMPTY>"); print(); return
    nul = raw.count(b"\x00")
    pr = sum(1 for b in raw if 9 <= b <= 13 or 32 <= b <= 126) / len(raw)
    kind = "TEXT" if (nul == 0 and pr > 0.90) else "BINARY"
    print("    [%s] nul=%d printable=%.3f" % (kind, nul, pr))
    if kind == "BINARY":
        print("    hex: " + raw[:48].hex(" "))
    else:
        for i, L in enumerate(raw.decode("latin-1").splitlines()[:n]):
            print("    L%02d| %s" % (i + 1, L[:maxlen]))
    print()

if __name__ == "__main__":
    for a in sys.argv[1:]:
        h(a)
