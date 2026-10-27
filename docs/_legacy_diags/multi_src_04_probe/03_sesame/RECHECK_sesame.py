# -*- coding: utf-8 -*-
"""Re-verify the SESAME size formula n = 4 + 2*nr + ne + 2*nr*ne
using the CORRECT field assignment:  line0 = [sentinel, x, nr, ne]
(i.e. nr = nums[2], ne = nums[3]) -- NOT nums[0]=matid as I wrongly assumed."""
import os, io, re, math
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(SRC, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'RECHECK_sesame.txt')
NUMRE = re.compile(r'[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?')

def lines(p):
    b = open(p, 'rb').read()
    if b.startswith(b'\xef\xbb\xbf'): b = b[3:]
    t = b.decode('utf-8', 'replace').replace('\r\n', '\n').replace('\r', '\n')
    return [l for l in t.split('\n') if l.strip()]

def floats15(s):
    out = []
    for i in range(0, len(s), 15):
        c = s[i:i+15].strip()
        if not c: continue
        try:
            out.append(float(c.replace('D','E').replace('d','e')))
        except ValueError:
            for t in NUMRE.findall(c):
                out.append(float(t.replace('D','E').replace('d','e')))
    return out

L = []
def P(s=''): L.append(str(s))

# find all .sesame / .SESAME* files
targets = []
for root, dirs, files in os.walk(MATTER):
    for f in files:
        fl = f.lower()
        if fl.endswith('.sesame') or fl.endswith('.sesame_') or fl.endswith('.sesame_planck') \
           or fl.endswith('.sesame_rosseland') or fl.endswith('.sesame_ross'):
            targets.append(os.path.join(root, f))
targets.sort()

P("RECHECK: n = 4 + 2*nr + ne + 2*nr*ne   with  nr = nums[2], ne = nums[3]")
P("=" * 96)
P("%-52s %9s %6s %6s %9s %9s %s" % ("file", "N", "nr", "ne", "formula", "diff", "verdict"))
P("-" * 96)
ok = 0; bad = 0
for p in targets:
    ls = lines(p)
    if not ls: continue
    f = []
    for l in ls:
        f.extend(floats15(l))
    N = len(f)
    rel = os.path.relpath(p, MATTER)
    if len(f) < 4:
        P("%-52s %9d  too short" % (rel, N)); continue
    sent = f[0]
    h = f[1:4]
    # try nr=nums[2], ne=nums[3]  and also nr=nums[1],ne=nums[2] for comparison
    marks = []
    for nm, (nr_i, ne_i) in (('nr=nums[2],ne=nums[3]', (2, 3)), ('nr=nums[1],ne=nums[2]', (1, 2))):
        try:
            nr = int(round(f[nr_i])); ne = int(round(f[ne_i]))
        except Exception:
            continue
        if nr <= 0 or ne <= 0: continue
        need = 4 + 2*nr + ne + 2*nr*ne
        marks.append((nm, nr, ne, need, N-need))
    # pick the one that closes
    hit = [m for m in marks if m[4] == 0]
    if hit:
        nm, nr, ne, need, d = hit[0]
        ok += 1
        P("%-52s %9d %6d %6d %9d %9d  CLOSES  <%s>" % (rel[:52], N, nr, ne, need, d, nm))
    else:
        bad += 1
        P("%-52s %9d   NO CLOSURE" % (rel[:52], N))
        for nm, nr, ne, need, d in marks:
            P("        %-24s nr=%5d ne=%5d need=%9d diff=%9d" % (nm, nr, ne, need, d))
P("-" * 96)
P("CLOSED = %d ; FAILED = %d ; total = %d" % (ok, bad, len(targets)))
P("")
P("FIRST-LINE SAMPLES:")
for p in targets[:12]:
    ls = lines(p)
    rel = os.path.relpath(p, MATTER)
    f = []
    for l in ls[:3]:
        f.extend(floats15(l))
    P("  %-52s L0|%s|" % (rel[:52], ls[0][:72]))
    P("  %-52s   nums[0:4]=%s" % ("", ['%.7g' % x for x in f[:4]]))

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
