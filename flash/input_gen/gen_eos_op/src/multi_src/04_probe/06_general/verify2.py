# -*- coding: utf-8 -*-
import io, os, traceback

def analyze(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        lines = f.read().splitlines()
    l2 = lines[1]
    nr = int(lines[2].split()[0]); nt = int(lines[2].split()[1])
    L = int(l2.split()[-1])
    exp = 2 + nr + nt + 2 * nr * nt
    # token count over lines 3+
    toks = []
    badlines = []
    for i, ln in enumerate(lines[2:], start=3):
        t = ln.split()
        if len(t) not in (5,) and len(t) > 0:
            badlines.append((i, len(t), ln[:80]))
        toks.extend(t)
    return dict(path=path, L=L, nr=nr, nt=nt, exp=exp, got=len(toks), bad=badlines)

base = 'src/Multi1D++Portable20241128/matter++/hyades/'
names = ['sesame/eos_2051.dat', 'sesame/eos_41.dat', 'sesame/eos_11.dat',
         'Opacity/opc_1151.dat', 'Opacity/opc_1051.dat', 'Opacity/opc_1491.dat',
         'Opacity/opc_1121.dat', 'Opacity/opc_1201.dat', 'Opacity/opc_1281.dat',
         'Opacity/opc_1371.dat', 'Opacity/opc_1401.dat', 'Opacity/opc_1461.dat',
         'Opacity/opc_1022.dat', 'qeos/qeos_115.dat', 'qeos/qeos_381.dat',
         'qeos/qeos_391.dat', 'qeos/qeos_392.dat', 'qeos/qeos_402.dat',
         'qeos/qeos_411.dat', 'qeos/qeos_422.dat', 'qeos/qeos_466.dat',
         'qeos/qeos_481.dat', 'qeos/qeos_52.dat']
print('%-26s %8s %6s %6s %9s %9s %7s' % ('file', 'L2decl', 'NR', 'NT', 'expect', 'tokens', 'delta'))
for n in names:
    p = base + n
    if not os.path.exists(p):
        print('MISSING', n); continue
    try:
        r = analyze(p)
        print('%-26s %8d %6d %6d %9d %9d %7d%s' % (n, r['L'], r['nr'], r['nt'], r['exp'], r['got'], r['got'] - r['exp'], '  BADLINES=%d' % len(r['bad']) if r['bad'] else ''))
    except Exception:
        print('ERR', n)
        traceback.print_exc()

# inspect weird file
print()
print('### inspect Opacity/opc_1051.dat lines 3..14 token counts')
with io.open(base + 'Opacity/opc_1051.dat', 'r', encoding='cp936', errors='replace') as f:
    for i in range(1, 15):
        ln = f.readline().rstrip('\r\n')
        print('%2d ntoks=%d |%s|' % (i, len(ln.split()), ln))
print()
print('### inspect qeos/qeos_115.dat tail')
with io.open(base + 'qeos/qeos_115.dat', 'r', encoding='cp936', errors='replace') as f:
    txt = f.read().splitlines()
print('total lines', len(txt))
for i in range(max(0, len(txt) - 4), len(txt)):
    print('%d |%s|' % (i + 1, txt[i][:120]))
