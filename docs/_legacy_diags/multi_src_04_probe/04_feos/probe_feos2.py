# -*- coding: utf-8 -*-
import io, os
def show(path, n, enc='cp936', lim=200):
    print('=' * 100); print('FILE:', path, os.path.getsize(path) if os.path.exists(path) else 'MISSING')
    if not os.path.exists(path): return
    with io.open(path, 'r', encoding=enc, errors='replace') as f:
        for i in range(n):
            ln = f.readline()
            if not ln: break
            s = ln.rstrip('\r\n'); print('  L%-3d len=%-4d |%s|' % (i + 1, len(s), s[:lim]))
B = 'src/Multi1D++Portable20241128/matter++/'
show(B + 'mat_Al-1.0/FEOS/Al.feos', 8)
show(B + 'mat_B/FEOS/B.feos', 8)
show(B + 'hyades/qeos/qeos_392.dat.feos', 6)
show(B + 'hyades/sesame/eos_41.dat.feos', 6)
# find all .feos
import glob
fs = []
for root, dirs, files in os.walk('src/Multi1D++Portable20241128'):
    for fn in files:
        if fn.lower().endswith('.feos'):
            p = os.path.join(root, fn); fs.append((os.path.getsize(p), p))
fs.sort()
for s, p in fs: print(s, p)
print('TOTAL .feos', len(fs))
