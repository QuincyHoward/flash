# -*- coding: utf-8 -*-
import io, os
B = 'src/Multi1D++Portable20241128/matter++/'

def load(p):
    with io.open(B + p, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    lines = txt.splitlines()
    head = ''.join(lines[0:2])
    v = [float(head[i:i + 15]) for i in range(0, 300, 15)]
    nchars = len(txt.replace('\n', '').replace('\r', ''))
    return v, nchars, len(lines)

print('%-22s %4s %4s %4s %9s %11s %11s %11s %8s' % ('file', 'NR', 'NT', 'Nel', 'headf', 'total_chars', 'remain_chars', 'rem/15', 'perGRID'))
for p in ['mat_Al-1.0/Al.feos', 'mat_B/B.feos', 'Ta2O5/Ta2O5.feos', 'mat_Others/SiO2.feos', 'mat_Ba/Ba.feos']:
    v, nch, nl = load(p)
    NR = int(round(v[1])) - 1; NT = int(round(v[2])) - 1; Nel = int(round(v[3])) - 1
    headf = 20 + 3 * (Nel + 1) + (NR + 1) + (NT + 1)
    rem = nch - headf * 15
    pergrid = rem / 15.0 / ((NR + 1) * (NT + 1))
    print('%-22s %4d %4d %4d %9d %11d %11d %11.2f %8.3f' %
          (os.path.basename(p), NR, NT, Nel, headf, nch, rem, rem / 15.0, pergrid))
