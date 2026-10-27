# -*- coding: utf-8 -*-
import os
hits = []
for root, dirs, files in os.walk('src/Multi1D++Portable20241128'):
    for fn in files:
        low = fn.lower()
        if low.endswith('.cn4') or low.endswith('.cnr') or 'ledcop' in low or 'atomic' in low or 'tops' in low or 'ionmix' in low:
            hits.append(os.path.join(root, fn))
hits.sort()
for h in hits:
    print(os.path.getsize(h), h)
print('TOTAL', len(hits))
print()
# also ionmix dirs
for root, dirs, files in os.walk('.'):
    if 'ionmix' in root.lower():
        print('DIR', root, len(files))
