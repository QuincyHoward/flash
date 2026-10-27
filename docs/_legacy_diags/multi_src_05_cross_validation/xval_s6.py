# -*- coding: utf-8 -*-
"""Determine the EXACT record structure of an opacity file by looking at the raw
line-by-line value counts.  No guessing: we print the boundary structure."""
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s6.txt')
L = []
def P(s=''):
    L.append(str(s))

def analyse(rel):
    path = os.path.join(EF.MATTER, rel)
    P(""); P("=" * 100); P("FILE %s" % rel); P("=" * 100)
    if not os.path.exists(path):
        P("  MISSING"); return
    ls = [l for l in EF.lines_of(path) if l.strip()]
    P("  nlines=%d" % len(ls))
    for i in range(min(6, len(ls))):
        P("  L%-4d len=%3d |%s|" % (i, len(ls[i]), ls[i]))
    P("  ...")
    for i in range(max(0, len(ls) - 3), len(ls)):
        P("  L%-4d len=%3d |%s|" % (i, len(ls[i]), ls[i]))
    # per-line value counts (fixed 15)
    counts = [len(EF.floats_fixed(l, 15)) for l in ls]
    P("  value-count histogram over lines 2..: %s"
      % sorted(set(counts[2:]))[:12])
    P("  first 8 line counts  : %s" % counts[:8])
    P("  last  8 line counts  : %s" % counts[-8:])
    tot = sum(counts[2:])
    P("  total values on lines 2..end = %d" % tot)
    # where does the count change? (boundary detection)
    ch = [i for i in range(2, len(counts)) if counts[i] != counts[i - 1]]
    P("  line indices where count changes: %s" % ch[:20])
    # print the values around the first change
    if ch:
        j = ch[0]
        P("  --- raw numbers around first boundary (line %d):" % j)
        for k in range(max(2, j - 2), min(len(ls), j + 3)):
            P("    L%d len=%d nvals=%d |%s|" % (k, len(ls[k]), counts[k], ls[k]))
    # dump the numeric tail of line 1 if it looks like a grid
    P("  L1 numbers = %s" % ['%.6g' % x for x in EF.floats_any(ls[1])[:12]])
    P("  L2 numbers = %s" % ['%.6g' % x for x in EF.floats_fixed(ls[2], 15)[:12]])

for rel in [r'mat_Ce\Ce.PLANCK', r'mat_Ce\Ce.ZEFF', r'mat_C-1.0\C_1G.PLANCK',
            r'mat_C-1.0\C_Z.dat', r'mat_Ti\SNOP_NLTE.PLANCK', r'mat_Au-1.0\Au100PLANCK',
            r'mat_He\SNOP.PLANCK']:
    analyse(rel)

# also inspect the .session SESAME write by the matlab writer if present
P(""); P("=" * 100); P("LOOK FOR THE WRITER / DOC OF THE OPACITY FORMAT"); P("=" * 100)
for pat in ['matlab', 'src']:
    pass

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
