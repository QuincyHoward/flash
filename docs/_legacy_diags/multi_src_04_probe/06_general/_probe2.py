# -*- coding: utf-8 -*-
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"

def walk_list(sub):
    base = os.path.join(ROOT, sub)
    out = []
    for dp, dn, fn in os.walk(base):
        rel = os.path.relpath(dp, ROOT).replace("\\", "/")
        for f in sorted(fn):
            fp = os.path.join(dp, f)
            try: sz = os.path.getsize(fp)
            except: sz = -1
            out.append((rel + "/" + f, sz))
    return out

def head(fp, n=8, maxlen=200):
    try:
        with open(fp, "rb") as fh:
            raw = fh.read(4096)
    except Exception as e:
        return "READ-ERR: %s" % e
    if not raw:
        return "<EMPTY FILE>"
    nul = raw.count(b"\x00")
    printable = sum(1 for b in raw if 9 <= b <= 13 or 32 <= b <= 126)
    ratio = printable / len(raw)
    txt = raw.decode("latin-1")
    lines = txt.splitlines()[:n]
    res = ["BIN-DIAG: len=%d nul=%d printable=%.2f -> %s" % (
        len(raw), nul, ratio, "TEXT" if (nul == 0 and ratio > 0.90) else "BINARY/MIXED")]
    for i, L in enumerate(lines):
        res.append("L%02d| %s" % (i + 1, L[:maxlen]))
    return "\n".join(res)

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "list":
        for sub in sys.argv[2:]:
            print("### " + sub)
            for p, s in walk_list(sub):
                print("%10d  %s" % (s, p))
            print()
    elif mode == "head":
        n = int(sys.argv[2])
        for p in sys.argv[3:]:
            fp = p if os.path.isabs(p) else os.path.join(ROOT, p)
            print("=" * 78)
            print("FILE: %s  bytes=%d" % (p, os.path.getsize(fp) if os.path.exists(fp) else -1))
            print(head(fp, n))
            print()
