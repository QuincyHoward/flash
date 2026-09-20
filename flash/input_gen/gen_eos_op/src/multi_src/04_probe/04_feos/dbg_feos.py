# -*- coding: utf-8 -*-
import io
B = 'src/Multi1D++Portable20241128/matter++/'
p = B + 'mat_Al-1.0/Al.feos'
with io.open(p, 'r', encoding='cp936', errors='replace') as f:
    txt = f.read().replace('\x1a', '')
lines = txt.splitlines()
print('nlines', len(lines))
print('L1 repr', repr(lines[0]))
print('L2 repr', repr(lines[1]))
head = ''.join(lines[0:2])
print('headlen', len(head))
fields = [head[i:i + 15] for i in range(0, len(head) - 14, 15)]
print('nfields', len(fields))
for i, f in enumerate(fields[:22]):
    print('  %2d |%s|' % (i, f))
