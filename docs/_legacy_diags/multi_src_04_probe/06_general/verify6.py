# -*- coding: utf-8 -*-
import io, os, re

base = 'src/Multi1D++Portable20241128/matter++/hyades/'
# 1p5e15.8 => each field 15 wide: sign + d.ddddddddE+xx = 1+1+1+8+4 =15
FW = 15
pat = re.compile(r'[-+]?\d\.\d{8}E[-+]\d{2,3}')

def parse_fixed(path):
    """Concatenate body lines (strip CR/LF and DOS EOF), then chop by 15."""
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        raw = f.read()
    raw = raw.replace('\x1a', '')
    lines = raw.splitlines()
    body = ''.join(lines[2:])
    toks = []
    i = 0
    while i + FW <= len(body):
        chunk = body[i:i + FW]
        toks.append(chunk)
        i += FW
    rest = body[i:]
    return lines, toks, rest

def report(name):
    p = base + name
    lines, toks, rest = parse_fixed(p)
    l2 = lines[1]
    t3 = lines[2].split()
    nr = int(round(float(t3[0]))); nt = int(round(float(t3[1])))
    L = int(l2.split()[-1])
    exp = 2 + nr + nt + 2 * nr * nt
    bad = [t for t in toks if not pat.fullmatch(t)]
    print('%-24s L2=%-6d NR=%-4d NT=%-4d exp=%-6d fixed15=%-6d delta=%-5d rest=%r badfield=%d' %
          (name, L, nr, nt, exp, len(toks), len(toks) - exp, rest[:20], len(bad)))
    if bad:
        print('     bad samples:', bad[:5])

names = ['sesame/eos_2051.dat', 'sesame/eos_41.dat', 'sesame/eos_11.dat',
         'sesame/eos_44.dat', 'sesame/eos_21.dat',
         'Opacity/opc_1151.dat', 'Opacity/opc_1051.dat', 'Opacity/opc_1491.dat',
         'Opacity/opc_1121.dat', 'Opacity/opc_1201.dat', 'Opacity/opc_1281.dat',
         'Opacity/opc_1371.dat', 'Opacity/opc_1401.dat', 'Opacity/opc_1461.dat',
         'Opacity/opc_1022.dat', 'Opacity/opc_1052.dat',
         'qeos/qeos_115.dat', 'qeos/qeos_381.dat',
         'qeos/qeos_391.dat', 'qeos/qeos_392.dat', 'qeos/qeos_402.dat',
         'qeos/qeos_411.dat', 'qeos/qeos_422.dat', 'qeos/qeos_466.dat',
         'qeos/qeos_481.dat', 'qeos/qeos_52.dat',
         'qeos/QEOS_2115.DAT', 'qeos/QEOS_3115.DAT']
print('fixed-width 15 field analysis (1p5e15.8)')
for n in names:
    report(n)
