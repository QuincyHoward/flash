# -*- coding: utf-8 -*-
"""FINAL verification of the MULTI opacity layout.

Established:
  * line 0 holds NR and NT (identical to the NR/NT in the MULTI input deck).
  * the "M" variant stores the 4 axis numbers  <rho1, rho2, T1, T2>  on LINE 1
    (file has 2240 lines; lines 2.. hold the grids and values).
  * the "bare"/ZEFF variant OMITS those 4 numbers, so line 1 IS the rho grid
    (file has 111 lines).
  * therefore the record is
        rho[NR] , T[NT] , values[NR*NT]
    with an OPTIONAL 4-number axis-label block on line 1.
"""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s9.txt')
L = []
def P(s=''):
    L.append(str(s))

OPF = [
    (r'mat_Ce\Ce.PLANCK', 20, 20, True), (r'mat_Ce\Ce.ROSS', 20, 20, True),
    (r'mat_Ce\Ce.EPS', 20, 20, True), (r'mat_Ce\Ce.ZEFF', 20, 20, False),
    (r'mat_C-1.0\C_1G.PLANCK', 20, 20, False), (r'mat_C-1.0\C_20GSNOP.PLANCK', 20, 20, True),
    (r'mat_C-1.0\C_20GSNOP.ZEFF', 20, 20, False), (r'mat_C-1.0\C_Z.dat', 43, 43, False),
    (r'mat_C-1.0\Carbon.Planck', 20, 20, True), (r'mat_C-1.0\Carbon.Zeff', 20, 20, False),
    (r'mat_Ti\Ti_Planck', 20, 20, True), (r'mat_Ti\Ti_Ross', 20, 20, True),
    (r'mat_Ti\Ti_EPS', 20, 20, True),
    (r'mat_Ti\SNOP_NLTE.PLANCK', 20, 20, True), (r'mat_Ti\SNOP_NLTE.ZEFF', 20, 20, False),
    (r'mat_Au-1.0\Au100PLANCK', 30, 50, True), (r'mat_Au-1.0\SNOP.PLANCK', 20, 20, True),
    (r'mat_He\SNOP.PLANCK', 20, 20, True), (r'mat_Gd\Gd20PLANCK', 20, 20, True),
    (r'mat_Gd\Gd20ZEFF', 20, 20, False),
]
P("CLOSURE TEST  N_lines>=30  => 4 axis numbers on line 1")
P("              N_lines<30   => no axis numbers (line 1 = rho grid)")
P("")
P("%-24s %4s %4s %7s %7s %7s %-14s %s" %
  ("file", "NR", "NT", "nlines", "N(L2..)", "N(L1..)", "form", "verdict"))
P("-" * 104)
allok = True
for rel, NR, NT, has4 in OPF:
    path = os.path.join(EF.MATTER, rel)
    if not os.path.exists(path):
        P("%-24s MISSING" % rel); continue
    ls = [l for l in EF.lines_of(path) if l.strip()]
    v2 = []
    for l in ls[2:]:
        v2.extend(EF.floats_fixed(l, 15))
    v1 = []
    for l in ls[1:]:
        v1.extend(EF.floats_fixed(l, 15))
    need = NR + NT + NR * NT
    nlines = len(ls)
    use_L1 = (nlines < 30)
    N = len(v1) if use_L1 else len(v2)
    form = 'L1..(no axis)' if use_L1 else 'L2..(4 axis on L1)'
    ok = (N == need)
    allok = allok and ok
    # cross-check: the 4 axis numbers on line 1 must MATCH the ends of the grids
    extra = ''
    if ok and not use_L1:
        ax = EF.floats_any(ls[1])
        if len(ax) >= 4:
            extra = "axis=(%.6g,%.6g,%.6g,%.6g)" % tuple(ax[:4])
    P("%-24s %4d %4d %7d %7d %7d %-14s %s %s" %
      (rel.split('\\')[-1], NR, NT, nlines, len(v2), len(v1), form,
       'OK' if ok else 'MISMATCH', extra))
P("")
P("ALL CLOSE EXACTLY: %s" % allok)

# ---- now show the resolved grids/values for Ce.PLANCK and Ce.ZEFF ----
P("")
P("=" * 100)
P("RESOLVED STRUCTURE")
P("=" * 100)
for rel, NR, NT in [(r'mat_Ce\Ce.PLANCK', 20, 20), (r'mat_Ce\Ce.ZEFF', 20, 20)]:
    path = os.path.join(EF.MATTER, rel)
    ls = [l for l in EF.lines_of(path) if l.strip()]
    use_L1 = len(ls) < 30
    src = ls[1:] if use_L1 else ls[2:]
    v = []
    for l in src:
        v.extend(EF.floats_fixed(l, 15))
    rhoL = v[:NR]; TL = v[NR:NR + NT]; val = v[NR + NT:]
    P("")
    P("FILE %s" % rel)
    P("  axis block (line1) = %s" % (EF.floats_any(ls[1]) if not use_L1 else '(none - line1 is data)'))
    P("  rho_log10 = %s" % ['%.6g' % x for x in rhoL])
    P("  rho g/cc  = %s" % ['%.6g' % (10 ** x) for x in rhoL])
    P("  T_log10   = %s" % ['%.6g' % x for x in TL])
    P("  T (10^x)  = %s" % ['%.6g' % (10 ** x) for x in TL])
    P("  values n=%d  min=%.6g max=%.6g" % (len(val), min(val), max(val)))
    if len(val) == NR * NT:
        V = [val[i * NT:(i + 1) * NT] for i in range(NR)]
        P("  orientation A  values[i_rho][i_T] : row0 = %s" % ['%.4g' % x for x in V[0][:6]])
        P("                                        row19= %s" % ['%.4g' % x for x in V[-1][:6]])
        VT = [val[i * NR:(i + 1) * NR] for i in range(NT)]
        P("  orientation B  values[i_T][i_rho] : row0 = %s" % ['%.4g' % x for x in VT[0][:6]])
        P("                                        row19= %s" % ['%.4g' % x for x in VT[-1][:6]])

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
