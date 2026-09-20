# -*- coding: utf-8 -*-
import io, os
B = 'src/Multi1D++Portable20241128/matter++/'

def parse_feos_head(path):
    with io.open(path, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    lines = txt.splitlines()
    head = ''.join(lines[0:2])
    fl = [head[i:i + 15] for i in range(0, 300, 15)]
    v = [float(x) for x in fl]
    return v, lines, txt

print('#### .feos row0/row1 decode (15-char fixed width, %15.8le)')
print('%-24s %4s %4s %4s %8s %9s %7s %6s %6s %5s' % ('file', 'FV', 'NR', 'NT', 'Nel', 'RhoRef', 'TRef', 'B0', 'SN', 'Atot'))
files = ['mat_Al-1.0/Al.feos', 'mat_B/B.feos', 'Ta2O5/Ta2O5.feos', 'mat_Others/SiO2.feos', 'mat_Ba/Ba.feos', 'mat_Ce/Cerium.feos']
for p in files:
    v, lines, txt = parse_feos_head(B + p)
    NR = int(round(v[1])) - 1; NT = int(round(v[2])) - 1; Nel = int(round(v[3])) - 1
    print('%-24s %4.0f %4d %4d %4d %8.4g %9.4g %7.3g %6.0f %6.3f' %
          (os.path.basename(p), v[0], NR, NT, Nel, v[6], v[7], v[8], v[9], v[17]))
    # counting: 20 header fields + (Nel+1)*3 + (NR+1) + (NT+1) + 13*(NR+1)*(NT+1)
    nfields = 20 + 3 * (Nel + 1) + (NR + 1) + (NT + 1) + 13 * (NR + 1) * (NT + 1)
    nchars = len(txt.replace('\n', '').replace('\r', ''))
    print('       predict fields=%-9d chars=%-9d  actual_chars=%-9d  delta=%d' % (nfields, nfields * 15, nchars, nchars - nfields * 15))

print()
print('#### .301 counting: 4 + NR + NT + 3*NR*NT  (4x16)')
import re
for p in ['mat_Al-1.0/FEOS/Al.feos.301', 'mat_B/B.301', 'mat_Au-1.0/Au.301']:
    fp = B + p
    with io.open(fp, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    lines = txt.splitlines()
    print('%-28s L1=|%s|' % (p, lines[0]))
    print('       L1len=%d  L2len=%d  totalchars=%d  nlines=%d' % (len(lines[0]), len(lines[1]), len(txt.replace('\n', '').replace('\r', '')), len(lines)))
