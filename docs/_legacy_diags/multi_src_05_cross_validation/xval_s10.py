# -*- coding: utf-8 -*-
"""FINAL: the M-variant stores the rho grid TWICE.
Verify:  body = 2*NR + NT + NR*NT   (M-variant, NR,NT on line 0)
         body =    NR + NT + NR*NT   (bare/ZEFF variant, NR,NT on line 0)
and confirm the duplicated block is bit-identical."""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s10.txt')
L = []
def P(s=''):
    L.append(str(s))

CASES = [
    (r'mat_Ce\Ce.PLANCK', 20, 20), (r'mat_Ce\Ce.ROSS', 20, 20), (r'mat_Ce\Ce.EPS', 20, 20),
    (r'mat_Ce\Ce.ZEFF', 20, 20),
    (r'mat_C-1.0\C_1G.PLANCK', 20, 20), (r'mat_C-1.0\C_20GSNOP.PLANCK', 20, 20),
    (r'mat_C-1.0\C_20GSNOP.ZEFF', 20, 20), (r'mat_C-1.0\C_Z.dat', 43, 43),
    (r'mat_C-1.0\Carbon.Planck', 20, 20), (r'mat_C-1.0\Carbon.Zeff', 20, 20),
    (r'mat_Ti\Ti_Planck', 20, 20), (r'mat_Ti\Ti_Ross', 20, 20), (r'mat_Ti\Ti_EPS', 20, 20),
    (r'mat_Ti\SNOP_NLTE.PLANCK', 20, 20), (r'mat_Ti\SNOP_NLTE.ZEFF', 20, 20),
    (r'mat_Ti\SNOP_LTE.PLANCK', 20, 20),
    (r'mat_Au-1.0\Au100PLANCK', 30, 50), (r'mat_Au-1.0\SNOP.PLANCK', 20, 20),
    (r'mat_He\SNOP.PLANCK', 20, 20), (r'mat_Gd\Gd20PLANCK', 20, 20),
    (r'mat_Gd\Gd20ZEFF', 20, 20), (r'mat_Al-1.0\1041_PLANCK', 20, 20),
]
P("%-24s %4s %4s %7s %8s %8s %8s  %s" %
  ("file", "NR", "NT", "nlines", "body", "2NR+NT+NR*NT", "NR+NT+NR*NT", "which form"))
P("-" * 104)
nres = {}
for rel, NR, NT in CASES:
    path = os.path.join(EF.MATTER, rel)
    if not os.path.exists(path):
        P("%-24s MISSING" % rel); continue
    ls = [l for l in EF.lines_of(path) if l.strip()]
    # body = everything after line 1 (line 0 = header, line 1 = axis/dup-rho)
    src = ls[2:] if len(ls) >= 30 else ls[1:]
    v = []
    for l in src:
        v.extend(EF.floats_fixed(l, 15))
    N = len(v)
    f_dup = 2 * NR + NT + NR * NT
    f_single = NR + NT + NR * NT
    which = 'M  (rho twice)' if N == f_dup else ('bare (rho once)' if N == f_single else '???')
    nres[rel] = (NR, NT, N, which)
    P("%-24s %4d %4d %7d %8d %8d %8d  %s" %
      (rel.split('\\')[-1], NR, NT, len(ls), N, f_dup, f_single, which))

# confirm the duplicated block is bit-identical on Ce.PLANCK
P("")
P("=" * 100)
P("CONFIRM the duplication on Ce.PLANCK (M variant)")
P("=" * 100)
for rel, NR, NT in [(r'mat_Ce\Ce.PLANCK', 20, 20), (r'mat_Ce\Ce.ROSS', 20, 20),
                    (r'mat_Au-1.0\Au100PLANCK', 30, 50)]:
    path = os.path.join(EF.MATTER, rel)
    ls = [l for l in EF.lines_of(path) if l.strip()]
    src = ls[2:] if len(ls) >= 30 else ls[1:]
    v = []
    for l in src:
        v.extend(EF.floats_fixed(l, 15))
    A = v[:NR]; B = v[NR:2 * NR]
    P("")
    P("FILE %s NR=%d" % (rel, NR))
    P("  block A (v[0:%d])      = %s" % (NR, ['%.6g' % x for x in A]))
    P("  block B (v[%d:%d]) = %s" % (NR, 2 * NR, ['%.6g' % x for x in B]))
    P("  A == B BIT-IDENTICAL ? %s" % (A == B))
    P("  A == B to 1e-12 rel  ? %s" % all(abs(a - b) <= 1e-12 * max(1, abs(a))
                                            for a, b in zip(A, B)))
    TL = v[2 * NR:2 * NR + NT]
    P("  T grid (v[%d:%d])  = %s" % (2 * NR, 2 * NR + NT, ['%.6g' % x for x in TL]))
    P("  values remaining = %d  == NR*NT = %d ? %s" %
      (len(v) - 2 * NR - NT, NR * NT, len(v) - 2 * NR - NT == NR * NT))

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
