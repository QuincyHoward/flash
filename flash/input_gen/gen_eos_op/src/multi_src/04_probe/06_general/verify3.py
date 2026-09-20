# -*- coding: utf-8 -*-
import io, os, traceback

base = 'src/Multi1D++Portable20241128/matter++/hyades/'
p = base + 'sesame/eos_2051.dat'
with io.open(p, 'r', encoding='cp936', errors='replace') as f:
    lines = f.read().splitlines()
print('nlines', len(lines))
print('L1 repr', repr(lines[0]))
print('L2 repr', repr(lines[1]))
print('L3 repr', repr(lines[2]))
print('L3 split', lines[2].split())
try:
    nr = int(lines[2].split()[0]); nt = int(lines[2].split()[1])
    print('nr nt', nr, nt)
except Exception:
    traceback.print_exc()
L = int(lines[1].split()[-1])
print('L', L)
exp = 2 + nr + nt + 2 * nr * nt
toks = []
for ln in lines[2:]:
    toks.extend(ln.split())
print('expect', exp, 'tokens', len(toks), 'delta', len(toks) - exp)
