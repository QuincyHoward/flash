# -*- coding: utf-8 -*-
"""VERIFY: N = 4 + NR + NT + NR*NT for the MULTI opacity family, and locate the
4 extra numbers.  Also: prove the array orientation by physical plausibility."""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s8.txt')
L = []
def P(s=''):
    L.append(str(s))

OPF = [
    (r'mat_Ce\Ce.PLANCK', 20, 20), (r'mat_Ce\Ce.ROSS', 20, 20), (r'mat_Ce\Ce.EPS', 20, 20),
    (r'mat_Ce\Ce.ZEFF', 20, 20),
    (r'mat_C-1.0\C_1G.PLANCK', 20, 20), (r'mat_C-1.0\C_20GSNOP.PLANCK', 20, 20),
    (r'mat_C-1.0\C_20GSNOP.ZEFF', 20, 20), (r'mat_C-1.0\C_Z.dat', 43, 43),
    (r'mat_C-1.0\Carbon.Planck', 20, 20), (r'mat_C-1.0\Carbon.Zeff', 20, 20),
    (r'mat_Ti\Ti_Planck', 20, 20), (r'mat_Ti\Ti_Ross', 20, 20), (r'mat_Ti\Ti_EPS', 20, 20),
    (r'mat_Ti\SNOP_NLTE.PLANCK', 20, 20), (r'mat_Ti\SNOP_NLTE.ZEFF', 20, 20),
    (r'mat_Au-1.0\Au100PLANCK', 30, 50), (r'mat_Au-1.0\SNOP.PLANCK', 20, 20),
    (r'mat_He\SNOP.PLANCK', 20, 20), (r'mat_Gd\Gd20PLANCK', 20, 20),
    (r'mat_Gd\Gd20ZEFF', 20, 20),
]
P("FORM TEST:  N == 4 + NR + NT + NR*NT ?")
P("")
P("%-34s %5s %5s %9s %9s %7s %s" % ("file", "NR", "NT", "N", "4+NR+NT+NR*NT", "diff", "verdict"))
P("-" * 100)
allok = True
for rel, NR, NT in OPF:
    path = os.path.join(EF.MATTER, rel)
    if not os.path.exists(path):
        P("%-34s MISSING" % rel); continue
    ls = [l for l in EF.lines_of(path) if l.strip()]
    vals = []
    for l in ls[2:]:
        vals.extend(EF.floats_fixed(l, 15))
    N = len(vals)
    need = 4 + NR + NT + NR * NT
    ok = (N == need)
    allok = allok and ok
    P("%-34s %5d %5d %9d %9d %7d %s" % (rel.split('\\')[-1], NR, NT, N, need, N - need,
                                        'OK' if ok else 'MISMATCH'))
P("")
P("ALL CLOSE EXACTLY: %s" % allok)

# ---- locate the 4 extra numbers on Ce.PLANCK ----
P("")
P("=" * 100)
P("LOCATE THE 4 EXTRA NUMBERS  (Ce.PLANCK, NR=NT=20)")
P("=" * 100)
path = os.path.join(EF.MATTER, r'mat_Ce\Ce.PLANCK')
ls = [l for l in EF.lines_of(path) if l.strip()]
vals = []
for l in ls[2:]:
    vals.extend(EF.floats_fixed(l, 15))
NR = NT = 20
for off in (0, 1, 2, 3, 4):
    rhoL = vals[off:off + NR]
    TL = vals[off + NR:off + NR + NT]
    rest = vals[off + NR + NT:]
    P("")
    P("offset=%d : rho_log10 = %s" % (off, ['%.4g' % x for x in rhoL]))
    P("           T_log10   = %s" % ['%.4g' % x for x in TL])
    P("           remaining = %d  (NR*NT=%d)  diff=%d" % (len(rest), NR * NT, len(rest) - NR * NT))
    if len(rest) == NR * NT:
        P("           ==> 4 extra numbers are the FIRST FOUR: %s" % ['%.6g' % x for x in vals[:4]])
        P("               (line 1 of the file = %s)" % ['%.6g' % x for x in EF.floats_any(ls[1])])

# ---- for Ce.ZEFF line1 IS the grid, so NO extra 4 ----
P("")
P("=" * 100)
P("CONTRAST: Ce.ZEFF (has 3 header numbers incl. Z, and NO 4 extra values)")
P("=" * 100)
path = os.path.join(EF.MATTER, r'mat_Ce\Ce.ZEFF')
ls = [l for l in EF.lines_of(path) if l.strip()]
P("  L0 |%s|" % ls[0])
P("  L1 |%s|" % ls[1])
vals = []
for l in ls[1:]:
    vals.extend(EF.floats_fixed(l, 15))
N = len(vals)
NR = NT = 20
P("  N(from L1..) = %d ; NR+NT+NR*NT = %d ; diff = %d" % (N, NR + NT + NR * NT, N - (NR + NT + NR * NT)))
P("  first 20 = %s" % ['%.4g' % x for x in vals[:20]])
P("  next  20 = %s" % ['%.4g' % x for x in vals[20:40]])
P("  next   8 = %s" % ['%.4g' % x for x in vals[40:48]])

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
