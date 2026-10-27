# -*- coding: utf-8 -*-
import io, os
B = 'src/Multi1D++Portable20241128/matter++/'
def analyze(p, drop_lead=False):
    with io.open(B + p, 'r', encoding='cp936', errors='replace') as f:
        txt = f.read().replace('\x1a', '')
    lines = txt.splitlines()
    head = ''.join(lines[0:2])
    v = [float(head[i:i + 15]) for i in range(0, 300, 15)]
    NR = int(round(v[1])) - 1; NT = int(round(v[2])) - 1; Nel = int(round(v[3])) - 1
    nch = len(txt.replace('\n', '').replace('\r', ''))
    return NR, NT, Nel, nch, len(lines)

for p in ['mat_Others/SiO2.feos']:
    NR, NT, Nel, nch, nl = analyze(p)
    pred_nospace = (20 + 3 * (Nel + 1) + (NR + 1) + (NT + 1) + (18 + Nel) * (NR + 1) * (NT + 1))
    # no-space: each 15-wide field writes 16 chars (sign always) -> actually 16 per field
    pred16 = pred_nospace * 16
    print('%s NR=%d NT=%d Nel=%d lines=%d actual=%d pred15=%d pred16=%d' %
          (p, NR, NT, Nel, nl, nch, pred_nospace * 15, pred16))
    print('  actual - pred15 = %d = lines-2? %s' % (nch - pred_nospace * 15, nch - pred_nospace * 15 == nl - 2))
