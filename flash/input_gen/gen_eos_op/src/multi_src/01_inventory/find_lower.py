# -*- coding: utf-8 -*-
import io, os

def show(path, nline=40, enc='cp936'):
    print('=' * 100)
    print('FILE:', path)
    if not os.path.exists(path):
        print('  MISSING'); return
    print('  BYTES:', os.path.getsize(path))
    with io.open(path, 'r', encoding=enc, errors='replace') as f:
        for i in range(nline):
            ln = f.readline()
            if not ln: break
            print('  L%-3d |%s| (len=%d)' % (i + 1, ln.rstrip('\r\n'), len(ln.rstrip('\r\n'))))

# locate LEDCOP / ATOMIC / ionmix samples
roots = ['src/Multi1D++Portable20241128/matter++']
import re
hits = []
for root, dirs, files in os.walk('src/Multi1D++Portable20241128'):
    for fn in files:
        low = fn.lower()
        if any(k in low for k in ['.cn4', '.cnr', 'nofree', 'avsqfree', 'coldopacity', 'multiigroup', 'multigroup', 'grayopacity']):
            hits.append(os.path.join(root, fn))
hits.sort()
for h in hits[:60]:
    print(os.path.getsize(h), h)
print('TOTAL', len(hits))
