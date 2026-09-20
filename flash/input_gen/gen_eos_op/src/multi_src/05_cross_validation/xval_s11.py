# -*- coding: utf-8 -*-
"""Resolve the opacity layout by DIRECT structural evidence:
count the values on every line and find the exact line where the rho grid ends.
"""
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s11.txt')
L = []
def P(s=''):
    L.append(str(s))

for rel in [r'mat_Ce\Ce.PLANCK', r'mat_Ce\Ce.ZEFF', r'mat_Au-1.0\Au100PLANCK']:
    path = os.path.join(EF.MATTER, rel)
    P(""); P("=" * 100); P("FILE %s" % rel); P("=" * 100)
    ls = [l for l in EF.lines_of(path) if l.strip()]
    P("  nlines = %d" % len(ls))
    P("  L0 (len %d): |%s|" % (len(ls[0]), ls[0]))
    P("  L1 (len %d): |%s|" % (len(ls[1]), ls[1]))
    # line by line value counts for the first 20 lines
    P("")
    P("  per-line value counts (first 25 lines):")
    for i in range(min(25, len(ls))):
        nv = len(EF.floats_fixed(ls[i], 15))
        P("    L%-4d len=%3d nvals=%d |%s|" % (i, len(ls[i]), nv, ls[i][:78]))
    # cumulative count after each line
    P("")
    P("  cumulative value count at line boundaries:")
    cum = 0
    marks = []
    for i, l in enumerate(ls):
        nv = len(EF.floats_fixed(l, 15))
        cum += nv
        if i < 12 or i in (20, 21, 22, 23, 24, 25, 110, 111, 112):
            P("    after L%-4d cum=%d" % (i, cum))
    # Find which cum value equals NR, NR+NT, NR+NT+NR*NT for candidate NR,NT
    counts = [len(EF.floats_fixed(l, 15)) for l in ls]
    cums = []
    c = 0
    for nv in counts:
        c += nv
        cums.append(c)
    P("")
    P("  total values in whole file = %d" % cums[-1])
    # search: does some prefix end exactly at 20?  at 40?
    for target in (19, 20, 21, 39, 40, 41, 100, 400):
        idx = [i for i, v in enumerate(cums) if v == target]
        if idx:
            P("    prefix ends exactly at %d after line index %s" % (target, idx[:6]))

# ------------------------------------------------------------------
# The decisive structural question: what is the LAST value of the
# apparent rho block, and what immediately follows?
# ------------------------------------------------------------------
P("")
P("=" * 100)
P("DECISIVE: what follows the 20-value rho block?")
P("=" * 100)
for rel in [r'mat_Ce\Ce.PLANCK', r'mat_Ce\Ce.ZEFF']:
    path = os.path.join(EF.MATTER, rel)
    ls = [l for l in EF.lines_of(path) if l.strip()]
    P("")
    P("FILE %s" % rel)
    # values from L2 onward (so we do NOT include line1)
    v = []
    for l in ls[2:]:
        v.extend(EF.floats_fixed(l, 15))
    P("  values from L2..: N=%d" % len(v))
    P("  v[0:24]  = %s" % ['%.6g' % x for x in v[:24]])
    P("  v[16:56] = %s" % ['%.6g' % x for x in v[16:56]])
    P("  v[96:140]= %s" % ['%.6g' % x for x in v[96:140]])
    P("  --- hypothesis: T grid = v[20:40], then values")
    P("      v[20:40] = %s" % ['%.6g' % x for x in v[20:40]])
    P("      v[40:60] = %s" % ['%.6g' % x for x in v[40:60]])
    P("  --- hypothesis: T grid = v[20:120] (NT=100)")
    P("      v[20:40]  = %s" % ['%.6g' % x for x in v[20:40]])
    P("      v[100:120]= %s" % ['%.6g' % x for x in v[100:120]])
    P("      N-20-100 = %d  (NR*100 = %d)  diff=%d" % (len(v) - 120, 20 * 100, len(v) - 120 - 2000))

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
