# -*- coding: utf-8 -*-
"""Hexdump the boundary region of AU_op03p to see the TRUE physical record layout."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *

p = os.path.join(MAT, "mat_Au-1.0", "AU_op03p")
d = raw(p)
print("size", len(d))
print("first 1600 bytes:")


def dump(b, base=0):
    for off in range(0, len(b), 60):
        chunk = b[off:off + 60]
        print(f"{base+off:>8}: {chunk!r}")


dump(d[:1560])

print("\n\n--- Now: token-by-token with byte offsets for first 140 values (w=15) ---")
f, tail = all_tokens(p, 15)
for i in range(140):
    print(f"  tok[{i:>4}] @byte{i*15:>7}  {f[i]!r}")
