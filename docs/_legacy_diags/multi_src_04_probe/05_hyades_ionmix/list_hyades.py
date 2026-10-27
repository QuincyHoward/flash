import os
base = r'src/Multi1D++Portable20241128/matter++/hyades'
rows = []
for root, dirs, files in os.walk(base):
    for f in files:
        p = os.path.join(root, f)
        try:
            sz = os.path.getsize(p)
        except Exception:
            sz = -1
        rows.append((p.replace(base, 'HY'), sz))
rows.sort()
for p, sz in rows:
    print(sz, p)
print('TOTAL FILES', len(rows))
