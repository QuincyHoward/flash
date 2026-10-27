# -*- coding: utf-8 -*-
"""probe_00_env: locate roots, count candidates. No fancy ops."""
import os, sys, json

HERE = os.path.abspath(os.path.dirname(__file__))          # .../.workbuddy/tmp
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))     # gen_eos_op
print("HERE =", HERE)
print("REPO =", REPO)

cand = [
    os.path.join(REPO, "src", "Multi1D++Portable20241128", "matter++"),
    os.path.join(REPO, "..", "src", "Multi1D++Portable20241128", "matter++"),
    os.path.join(REPO, "..", "..", "src", "Multi1D++Portable20241128", "matter++"),
]
for c in cand:
    print(("OK  " if os.path.isdir(c) else "MISS"), os.path.abspath(c))

# also walk up from cwd looking for src/Multi1D++Portable20241128
p = os.getcwd()
for _ in range(8):
    test = os.path.join(p, "src", "Multi1D++Portable20241128", "matter++")
    if os.path.isdir(test):
        print("FOUND-UP", test)
    p = os.path.dirname(p)
