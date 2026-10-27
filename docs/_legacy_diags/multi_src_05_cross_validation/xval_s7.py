# -*- coding: utf-8 -*-
"""Definitive opacity-table structure: locate the block boundary between
the rho grid / T grid / value block from the raw token stream, and confirm
NR, NT against the line-boundary evidence."""
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s7.txt')
L = []
def P(s=''):
    L.append(str(s))

def stream(path):
    ls = [l for l in EF.lines_of(path) if l.strip()]
    vals = []
    for l in ls[2:]:
        vals.extend(EF.floats_fixed(l, 15))
    return ls, vals

# For each file: header NR,NT and the block boundary TR isn't given; the file
# stores  RHO[NR] , T[NT] , VALS[NR*NT]   -- but what is TRANS "TR"?
# In MULTI, T is stored in eV as  T = T1*exp10(t)  ... we test NT=112? and NT=100
CASES = [
    (r'mat_Ce\Ce.PLANCK', 20, 20, 112),
    (r'mat_Ce\Ce.ZEFF',   20, 20, 112),
    (r'mat_C-1.0\C_1G.PLANCK', 20, 20, 112),
    (r'mat_C-1.0\C_Z.dat', 43, 43, 112),
]
for rel, NR, NT, TR in CASES:
    path = os.path.join(EF.MATTER, rel)
    P(""); P("=" * 100)
    P("FILE %s   NR=%d NT=%d" % (rel, NR, NT))
    P("=" * 100)
    if not os.path.exists(path):
        P("  MISSING"); continue
    ls, vals = stream(path)
    N = len(vals)
    P("  N=%d" % N)
    forms = [
        ('NR + NR*TR',               NR + NR * 112),
        ('NR + TR + NR*TR',          NR + TR + NR * TR),
        ('NR+NT + NR*NT',            NR + NT + NR * NT),
        ('NR+NT + NR*TR',            NR + NT + NR * 112),
        ('NR+NR*NT',                 NR + NR * NT),
        ('NR*NT + NR + NT',          NR * NT + NR + NT),
    ]
    for nm, v in forms:
        P("    %-22s = %8d   diff=%8d %s" % (nm, v, N - v, '<== MATCH' if N == v else ''))
    # find the run of increasing values at the start (the rho grid)
    P("  first 25 values: %s" % ['%.6g' % x for x in vals[:25]])
    # detect monotonic increasing prefix
    k = 0
    while k + 1 < N and vals[k + 1] > vals[k]:
        k += 1
    P("  longest increasing prefix length = %d" % (k + 1))
    P("  values[%d:%d] = %s" % (k - 2, k + 6, ['%.6g' % x for x in vals[max(0, k - 2):k + 6]]))
    # NOW: check whether after a certain index the sequence restarts low
    for cand in (NR, 112, 20, 43):
        if cand > N:
            continue
        P("  --- hypothesis NR_stored=%d : vals[%d:%d]=%s ; vals[%d:%d]=%s"
          % (cand, 0, min(cand, 8), ['%.6g' % x for x in vals[:min(cand, 8)]],
             cand, min(cand + 6, N), ['%.6g' % x for x in vals[cand:min(cand + 6, N)]]))

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
