# -*- coding: utf-8 -*-
"""Stage 1c: print the list of files in the shortlisted dirs (names + sizes) so we can see everything cheaply."""
import os, io
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'xval_s1c_names.txt')
TARGETS = ['mat_Ce', 'Ta2O5', 'mat_Au-1.0', 'mat_C-1.0', 'mat_Ti', 'mat_He', 'mat_B', 'SiO2', 'CH', 'mat_Gd', 'mat_Al-1.0']
lines = []
for m in TARGETS:
    d = os.path.join(MATTER, m)
    lines.append("=" * 90)
    lines.append("DIR %s  exists=%s" % (m, os.path.isdir(d)))
    if not os.path.isdir(d):
        continue
    rows = []
    for root, dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            try: sz = os.path.getsize(p)
            except OSError: sz = -1
            rows.append((os.path.relpath(p, d).replace('\\', '/'), sz))
    rows.sort()
    for r, sz in rows:
        lines.append("   %-52s %10d" % (r, sz))
    lines.append("   TOTAL %d files" % len(rows))
with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
