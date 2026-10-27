# -*- coding: utf-8 -*-
import io, os

def analyze(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        lines = f.read().splitlines()
    l2 = lines[1]
    t3 = lines[2].split()
    nr = int(round(float(t3[0]))); nt = int(round(float(t3[1])))
    L = int(l2.split()[-1])
    exp = 2 + nr + nt + 2 * nr * nt
    toks = []
    per_line = {}
    for i, ln in enumerate(lines[2:], start=3):
        t = ln.split()
        per_line[i] = len(t)
        toks.extend(t)
    return dict(L=L, nr=nr, nt=nt, exp=exp, got=len(toks), nl=len(lines), pl=per_line)

base = 'src/Multi1D++Portable20241128/matter++/hyades/'
names = ['sesame/eos_2051.dat', 'sesame/eos_41.dat', 'sesame/eos_11.dat',
         'sesame/eos_44.dat', 'sesame/eos_115.dat',
         'Opacity/opc_1151.dat', 'Opacity/opc_1051.dat', 'Opacity/opc_1491.dat',
         'Opacity/opc_1121.dat', 'Opacity/opc_1201.dat', 'Opacity/opc_1281.dat',
         'Opacity/opc_1371.dat', 'Opacity/opc_1401.dat', 'Opacity/opc_1461.dat',
         'Opacity/opc_1022.dat', 'Opacity/opc_1052.dat',
         'qeos/qeos_115.dat', 'qeos/qeos_381.dat',
         'qeos/qeos_391.dat', 'qeos/qeos_392.dat', 'qeos/qeos_402.dat',
         'qeos/qeos_411.dat', 'qeos/qeos_422.dat', 'qeos/qeos_466.dat',
         'qeos/qeos_481.dat', 'qeos/qeos_52.dat',
         'qeos/QEOS_2115.DAT', 'qeos/QEOS_3115.DAT']
print('%-26s %8s %5s %5s %9s %9s %7s %6s' % ('file', 'L2decl', 'NR', 'NT', 'expect', 'tokens', 'delta', 'nl'))
for n in names:
    p = base + n
    if not os.path.exists(p):
        print('MISSING', n); continue
    r = analyze(p)
    print('%-26s %8d %5d %5d %9d %9d %7d %6d' % (n, r['L'], r['nr'], r['nt'], r['exp'], r['got'], r['got'] - r['exp'], r['nl']))
