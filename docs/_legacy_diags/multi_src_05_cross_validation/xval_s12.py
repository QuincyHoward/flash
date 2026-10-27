# -*- coding: utf-8 -*-
"""Confirm the exact repetition structure of the M-variant opacity tables."""
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s12.txt')
L = []
def P(s=''):
    L.append(str(s))

for rel in [r'mat_Ce\Ce.PLANCK', r'mat_Au-1.0\Au100PLANCK', r'mat_Ce\Ce.ZEFF']:
    path = os.path.join(EF.MATTER, rel)
    P(""); P("=" * 100); P("FILE %s" % rel); P("=" * 100)
    ls = [l for l in EF.lines_of(path) if l.strip()]
    nlines = len(ls)
    l0 = ls[0]
    hdr = [float(x) for x in l0[26:].split()]
    NR = int(round(hdr[0])); NT = int(round(hdr[1])) if len(hdr) > 1 else None
    P("  nlines=%d  header NR=%s NT=%s" % (nlines, NR, NT))
    # body from L2 on
    v = []
    for l in ls[2:]:
        v.extend(EF.floats_fixed(l, 15))
    N = len(v)
    P("  body N (L2..) = %d" % N)
    # Hypothesis: body = NR + NR + NT + NR*NT  (rho, T-dup, T, values)
    forms = {
        'NR+NR+NT+NR*NT (rho,T,T,vals)': 2 * NR + NT + NR * NT,
        'NR+NT+NT+NR*NT (rho,T,T?)':     NR + 2 * NT + NR * NT,
        'NR+NT+NR*NT':                   NR + NT + NR * NT,
        'NR+NR+NR+NT+NR*NT':             3 * NR + NT + NR * NT,
    }
    for nm, val in forms.items():
        P("    %-32s = %8d  diff=%8d %s" % (nm, val, N - val, 'MATCH' if N == val else ''))
    # Directly test: is v[NR:2NR] == v[2NR:2NR+NT] for NT==NR ?
    if NT == NR:
        A = v[NR:2 * NR]; B = v[2 * NR:3 * NR]
        P("  v[NR:2NR]  = %s" % ['%.6g' % x for x in A[:8]])
        P("  v[2NR:3NR] = %s" % ['%.6g' % x for x in B[:8]])
        P("  A == B ? %s" % (A == B))
    # generic: check if v[NR:NR+K] equals v[NR+K:NR+2K] for K=NT
    if NT:
        K = NT
        A = v[NR:NR + K]; B = v[NR + K:NR + 2 * K]
        P("  generic K=NT=%d : v[NR:NR+K] == v[NR+K:NR+2K] ? %s" % (K, A == B))
        P("    A first6 = %s" % ['%.6g' % x for x in A[:6]])
        P("    B first6 = %s" % ['%.6g' % x for x in B[:6]])
    # try to find the period of the repeating block after the rho grid
    P("  --- search for a repeating block of length k in v[NR:]")
    for k in (20, 30, 50, 100, 112, 250, 500):
        if NR + k <= N and v[NR:NR + k] == v[NR + k:NR + 2 * k]:
            P("      PERIOD %d found: v[%d:%d] == v[%d:%d]" % (k, NR, NR + k, NR + k, NR + 2 * k))
    # print the first 12 line-2-onwards blocks of 4 values to eyeball
    P("  first 14 lines from L2 (4 values each):")
    for i in range(2, min(16, nlines)):
        P("    L%-4d %s" % (i, ['%.6g' % x for x in EF.floats_fixed(ls[i], 15)]))
    # where do values start?  find first line whose values are NOT monotonic
    P("  where does the monotonic run break?")
    run = 0
    for i in range(2, nlines):
        fv = EF.floats_fixed(ls[i], 15)
        if all(fv[j] < fv[j + 1] for j in range(len(fv) - 1)):
            run += len(fv)
        else:
            P("    monotonic run ends after %d values (first break at L%d: %s)" % (run, i, fv))
            break
    # find the SECOND break (after the T grid duplicate)
    run2 = run
    for i in range(2, nlines):
        pass

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
