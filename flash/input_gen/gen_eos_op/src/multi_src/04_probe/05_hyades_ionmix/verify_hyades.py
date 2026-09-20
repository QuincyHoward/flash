# -*- coding: utf-8 -*-
import io, os, re

def count_tokens(path):
    """count whitestoken numeric tokens after line 2 (1p5e15.8 free-ish)"""
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        lines = f.read().splitlines()
    body = []
    for ln in lines[2:]:
        toks = ln.split()
        for t in toks:
            body.append(t)
    return lines, body

def fmt_1p3e158_head(line2):
    """verify format 1x,i5,4x,1p3e15.8,3x,i5  -> col1-2 blank? Let's index."""
    print('  raw     :|%s|' % line2)
    print('  [0:6]   :|%s|' % line2[0:6])
    print('  [5:5]   :|%s|' % line2[5:5])
    print('  [6:9]   :|%s|' % line2[6:9])
    print('  [9:24]  :|%s|' % line2[9:24])
    print('  [24:39] :|%s|' % line2[24:39])
    print('  [39:54] :|%s|' % line2[39:54])
    print('  [54:57] :|%s|' % line2[54:57])
    print('  [57:62] :|%s|' % line2[57:62])

cases = [
    ('sesame/eos_2051.dat', 2051),
    ('sesame/eos_41.dat', 41),
    ('Opacity/opc_1151.dat', 1151),
    ('Opacity/opc_1491.dat', 1491),
    ('Opacity/opc_1051.dat', 1051),
    ('Opacity/opc_1121.dat', 1121),
    ('Opacity/opc_1201.dat', 1201),
    ('Opacity/opc_1281.dat', 1281),
    ('Opacity/opc_1371.dat', 1371),
    ('Opacity/opc_1401.dat', 1401),
    ('Opacity/opc_1461.dat', 1461),
    ('qeos/qeos_115.dat', 115),
    ('qeos/qeos_381.dat', 381),
    ('qeos/qeos_391.dat', 391),
    ('qeos/qeos_392.dat', 392),
    ('qeos/qeos_402.dat', 402),
    ('qeos/qeos_411.dat', 411),
    ('qeos/qeos_422.dat', 422),
    ('qeos/qeos_466.dat', 466),
    ('qeos/qeos_481.dat', 481),
    ('qeos/qeos_52.dat', 52),
    ('qeos/qeos_115.dat', 115),
]
base = 'src/Multi1D++Portable20241128/matter++/hyades/'
print('### HEADER FORMAT CHECK (eos_2051 L2)')
with io.open(base + 'sesame/eos_2051.dat', 'r', encoding='cp936', errors='replace') as f:
    f.readline()
    l2 = f.readline().rstrip('\r\n')
fmt_1p3e158_head(l2)

print()
print('%-28s %8s %6s %6s %8s %8s %10s %6s' % ('file', 'L2decl', 'NR', 'NT', 'tokens', 'expect', 'delta', 'ok'))
for name, num in cases:
    p = base + name
    if not os.path.exists(p):
        print('MISSING', p); continue
    lines, body = count_tokens(p)
    l2 = lines[1]
    # NR NT are first two tokens on line 3
    nr = int(lines[2].split()[0]); nt = int(lines[2].split()[1])
    L = int(l2.split()[-1])
    exp = 2 + nr + nt + 2 * nr * nt
    print('%-28s %8d %6d %6d %8d %8d %10d %6s' % (name, L, nr, nt, len(body), exp, len(body) - exp, 'OK' if len(body) == exp else 'DIFF'))

print()
print('### EXTERNAL OPACITY HEADER on opc_1051 (line1 = GOLD ZOT)')
print('### ionpot.dat head')
with io.open(base + 'ionpot.dat', 'r', encoding='cp936', errors='replace') as f:
    for i in range(20):
        ln = f.readline()
        if not ln: break
        print('  %2d|%s' % (i + 1, ln.rstrip()))
