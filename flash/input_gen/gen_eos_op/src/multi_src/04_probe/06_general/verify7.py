# -*- coding: utf-8 -*-
import io, os, re

base = 'src/Multi1D++Portable20241128/matter++/hyades/'
FW = 15
num = re.compile(r'\s*[-+]?(\d+\.\d*|\.\d+|\d+)([EeDd][-+]?\d+)?\s*$')

def check(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read().replace('\x1a', '')
    lines = raw.splitlines()
    body = ''.join(lines[2:])
    toks = [body[i:i + FW] for i in range(0, len(body) - FW + 1, FW)]
    bad = [t for t in toks if not num.match(t)]
    t3 = lines[2].split()
    nr = int(round(float(t3[0]))); nt = int(round(float(t3[1])))
    L = int(lines[1].split()[-1])
    exp = 2 + nr + nt + 2 * nr * nt
    # 3-digit exponent detection (would break fixed 15 width)
    e3 = [t for t in toks if re.search(r'[Ee][-+]\d{3}', t)]
    return dict(name=path, L=L, nr=nr, nt=nt, exp=exp, got=len(toks),
                tail=len(body) % FW, bad=len(bad), bads=bad[:3], e3=len(e3), e3s=e3[:3])

names = ['sesame/eos_2051.dat', 'sesame/eos_41.dat', 'sesame/eos_11.dat',
         'sesame/eos_44.dat', 'sesame/eos_21.dat', 'sesame/eos_51.dat',
         'Opacity/opc_1151.dat', 'Opacity/opc_1491.dat', 'Opacity/opc_1121.dat',
         'Opacity/opc_1052.dat',
         'qeos/qeos_115.dat', 'qeos/qeos_392.dat', 'qeos/qeos_466.dat',
         'qeos/QEOS_3115.DAT']
print('%-24s %6s %5s %5s %9s %9s %5s %5s %6s %6s' % ('file', 'L2', 'NR', 'NT', 'expect', 'got', 'delta', 'tail', 'bad', 'e3'))
for n in names:
    r = check(base + n)
    print('%-24s %6d %5d %5d %9d %9d %5d %5d %6d %6d' % (r['name'].split('/')[-1], r['L'], r['nr'], r['nt'], r['exp'], r['got'], r['got'] - r['exp'], r['tail'], r['bad'], r['e3']))
    if r['bad']:
        print('        bad:', r['bads'])
    if r['e3']:
        print('        3-digit-exp:', r['e3s'])
