# -*- coding: utf-8 -*-
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"
print("ROOT exists:", os.path.isdir(ROOT))
print("=" * 70)
try:
    top = sorted(os.listdir(ROOT))
except Exception as e:
    print("ERR", e); sys.exit(1)
for name in top:
    p = os.path.join(ROOT, name)
    if os.path.isdir(p):
        n = 0; nb = 0
        for dp, dn, fn in os.walk(p):
            n += len(fn)
            for f in fn:
                try: nb += os.path.getsize(os.path.join(dp, f))
                except: pass
        print(f"[DIR ] {name:<34} files={n:<6} bytes={nb}")
    else:
        try: sz = os.path.getsize(p)
        except: sz = -1
        print(f"[FILE] {name:<34} bytes={sz}")
