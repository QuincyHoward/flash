# -*- coding: utf-8 -*-
import io, os
B = 'src/Multi1D++Portable20241128/matter++/'
p = B + 'mat_Others/SiO2.feos'
with io.open(p, 'r', encoding='cp936', errors='replace') as f:
    txt = f.read().replace('\x1a', '')
lines = txt.splitlines()
print('nlines', len(lines))
from collections import Counter
c = Counter(len(l) for l in lines)
for k in sorted(c): print('  len=%d  count=%d' % (k, c[k]))
print('first 3 line lens', [len(l) for l in lines[:3]])
print('a mid line len', len(lines[1000]))
