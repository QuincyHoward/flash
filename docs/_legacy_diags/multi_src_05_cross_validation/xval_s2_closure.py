# -*- coding: utf-8 -*-
"""Stage 2: closure tests for the .sesame / .feos / bare-name opacity readers."""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_readers as ER

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'xval_s2_closure.txt')

lines = []
def P(s=''):
    lines.append(str(s))

def dump_first_numbers(path, k=24, width=15):
    s = ER.read_text(path)
    ls = [l for l in ER.split_lines(s) if l.strip()]
    f = []
    for l in ls:
        try:
            f.extend(ER.floats_fixed(l, width))
        except Exception:
            f.extend(ER.floats_free(l))
    return ls, f[:k], len(f)

# =========================== A. SESAME family =====================================
P("#" * 96)
P("# A. SESAME-FAMILY  (.SESAME / .sesame / .SESAME_)")
P("#" * 96)
SES = [
    r'Ta2O5\PowerLawTa2O5_EOS.SESAME',
    r'Ta2O5\PowerLawTa2O5_EOS.SESAME_',
    r'SiO2\eos_21.sesame',
    r'SiO2\eos_22.sesame',
    r'SiO2\eos_23.sesame',
    r'SiO2\eos_24.sesame',
    r'SiO2\opc_1022.sesame_PLANCK',
    r'SiO2\opc_1022.sesame_ROSSELAND',
    r'SiO2\SiO2_EOS.dat',
]
for rel in SES:
    path = os.path.join(MATTER, rel)
    P("")
    P("-" * 96)
    P("FILE %s   exists=%s  size=%s" % (rel, os.path.exists(path),
                                        os.path.getsize(path) if os.path.exists(path) else '-'))
    if not os.path.exists(path):
        continue
    try:
        ls, fk, ntot = dump_first_numbers(path)
        P("  first lines:")
        for l in ls[:4]:
            P("     |%s|" % l)
        P("  first 24 numbers: %s" % fk)
        P("  total numbers parsed (15-wide chunking): %d" % ntot)
    except Exception as e:
        P("  parse error: %r" % e)
        continue
    try:
        r = ER.read_sesame(path)
        P("  header_first4 = %s" % r.get('header_first4'))
        P("  nr=%s ne=%s closure=%s check=%s leftover=%s" %
          (r.get('nr'), r.get('ne'), r.get('closure'),
           r.get('closure_check'), r.get('leftover')))
        if r.get('closure') == 'OK':
            rg = r['rho_grid']
            P("  rho_grid  n=%d  min=%.6g max=%.6g" % (len(rg), min(rg), max(rg)))
            P("  rho_grid  first6=%s" % ['%.6g' % x for x in rg[:6]])
            P("  E_grid    n=%d  min=%.6g max=%.6g  (Mbar*cm^3/g)" %
              (len(r['E_grid']), min(r['E_grid']), max(r['E_grid'])))
            P("  E_inc     first6=%s" % ['%.6g' % x for x in r['E_inc'][:6]])
            P("  e0        first6=%s" % ['%.6g' % x for x in r['e0'][:6]])
            P("  T(K)      min=%.6g max=%.6g" % (min(min(x) for x in r['T']),
                                                 max(max(x) for x in r['T'])))
            P("  P(Mbar)   min=%.6g max=%.6g" % (min(min(x) for x in r['P']),
                                                 max(max(x) for x in r['P'])))
            P("  P row0    = %s" % ['%.6g' % x for x in r['P'][0][:6]])
            P("  T row0    = %s" % ['%.6g' % x for x in r['T'][0][:6]])
    except Exception as e:
        P("  read_sesame error: %r" % e)

# =========================== B. FEOS ==============================================
P("")
P("#" * 96)
P("# B. FEOS  (.feos)")
P("#" * 96)
FEOS = [r'mat_Ce\Cerium.feos', r'Ta2O5\Ta2O5.feos', r'mat_B\B.feos',
        r'mat_Al-1.0\Al.feos']
for rel in FEOS:
    path = os.path.join(MATTER, rel)
    P("")
    P("-" * 96)
    P("FILE %s  exists=%s size=%s" % (rel, os.path.exists(path),
                                      os.path.getsize(path) if os.path.exists(path) else '-'))
    if not os.path.exists(path):
        continue
    try:
        r = ER.read_feos(path)
        P("  line0 RAW: |%s|" % r['h0raw'])
        P("  line0 parsed: %s" % ['%g' % x for x in r['h0']])
        P("     names    : %s" % r['h0_names'])
        P("  line1 RAW: |%s|" % r['h1raw'])
        P("  line1 parsed: %s" % ['%g' % x for x in r['h1']])
        P("     names    : %s" % r['h1_names'])
        P("  nlines=%d  numbers after 2 header lines = %d" % (r['nlines'], r['n_rest']))
        nr = int(round(r['h0'][1])); nt = int(round(r['h0'][2]))
        P("  NRho=%d NT=%d  -> nr*nt*? ..." % (nr, nt))
        for k, label in [(2, '2*nr*nt'), (3, '3*nr*nt'), (4, '4*nr*nt'), (5, '5*nr*nt'),
                         (6, '6*nr*nt'), (7, '7*nr*nt'), (8, '8*nr*nt')]:
            P("       %-10s = %d   ; n_rest - that = %d" % (label, k * nr * nt, r['n_rest'] - k * nr * nt))
    except Exception as e:
        P("  read_feos error: %r" % e)

# =========================== C. MULTI bare-name opacity ============================
P("")
P("#" * 96)
P("# C. MULTI BARE-NAME OPACITY TABLES  (*PLANCK* / *ROSS* / *EPS / *.ZEFF)")
P("#" * 96)
BARE = [
    r'mat_Ce\Ce.PLANCK', r'mat_Ce\Ce.ROSS', r'mat_Ce\Ce.EPS', r'mat_Ce\Ce.ZEFF',
    r'mat_Ti\Ti_Planck', r'mat_Ti\Ti_Ross', r'mat_Ti\Ti_EPS',
    r'mat_C-1.0\C_1G.PLANCK', r'mat_C-1.0\C_20GSNOP.PLANCK',
    r'mat_C-1.0\C_20GSNOP.ZEFF', r'mat_C-1.0\C_Z.dat',
    r'mat_C-1.0\Carbon.Planck', r'mat_C-1.0\Carbon.Zeff',
    r'mat_C-1.0\C_EOS', r'mat_C-1.0\CH_ieos', r'mat_C-1.0\511_ieos',
    r'mat_Au-1.0\Au100PLANCK', r'mat_Au-1.0\SNOP.PLANCK',
    r'mat_Ti\SNOP_NLTE.PLANCK',
]
for rel in BARE:
    path = os.path.join(MATTER, rel)
    P("")
    P("-" * 96)
    P("FILE %s  exists=%s size=%s" % (rel, os.path.exists(path),
                                      os.path.getsize(path) if os.path.exists(path) else '-'))
    if not os.path.exists(path):
        continue
    try:
        r = ER.read_multi_opacity(path)
        P("  line0  RAW : |%s|" % r['line0'])
        P("  head14     : |%s|" % r['line0_head14'])
        P("  hdr nums L0: %s" % ['%g' % x for x in r['header_line0_numbers']])
        P("  hdr nums L1: %s" % ['%g' % x for x in r['header_line1_numbers']])
        P("  n_body=%d  n_lines=%d  linewidths=%s" %
          (r['n_body'], r['n_lines'], r['line_widths']))
        # closure test
        h = r['header_line0_numbers']
        cands = []
        if len(h) >= 2:
            a = int(round(h[0])); b = int(round(h[1]))
            for nm, nr_, nt_ in [('h0,h1', a, b), ('h1,h0', b, a)]:
                nb = r['n_body']
                need = nr_ + nt_ + nr_ * nt_
                cands.append((nm, nr_, nt_, need, nb - need))
                need2 = 2 * nr_ + nt_ + nr_ * nt_
                cands.append((nm + '+extra_r', nr_, nt_, need2, nb - need2))
            for nm, nr_, nt_, need, diff in cands:
                P("    closure[%-12s] nr=%d nt=%d  need=%d  n_body=%d  diff=%d %s" %
                  (nm, nr_, nt_, need, r['n_body'], diff,
                   '  <== CLOSES' if diff == 0 else ''))
    except Exception as e:
        P("  read_multi_opacity error: %r" % e)

# =========================== D. cst ==============================================
P("")
P("#" * 96)
P("# D. .cst (Rostock)")
P("#" * 96)
for rel in [r'mat_Ce\Cerium.cst', r'Ta2O5\Ta2O5.cst', r'mat_B\B.cst', r'mat_He\Untitled.CST']:
    path = os.path.join(MATTER, rel)
    P("")
    P("-" * 96)
    P("FILE %s exists=%s" % (rel, os.path.exists(path)))
    if not os.path.exists(path):
        continue
    try:
        r = ER.read_cst(path)
        P("  title   : %s" % r['title'])
        P("  headers : %s" % r['headers'])
        P("  n_rows  : %d" % r['n_rows'])
        if r['n_rows']:
            P("  first row n,rho,P,Q = %s" % ['%.6g' % x for x in
              [r['numdens'][0], r['rho'][0], r['P'][0], r['Q'][0]]])
            P("  last  row n,rho,P,Q = %s" % ['%.6g' % x for x in
              [r['numdens'][-1], r['rho'][-1], r['P'][-1], r['Q'][-1]]])
            P("  numdens min/max = %.6g / %.6g" % (min(r['numdens']), max(r['numdens'])))
            P("  rho     min/max = %.6g / %.6g" % (min(r['rho']), max(r['rho'])))
            P("  P       min/max = %.6g / %.6g" % (min(r['P']), max(r['P'])))
            P("  Q       min/max = %.6g / %.6g" % (min(r['Q']), max(r['Q'])))
    except Exception as e:
        P("  read_cst error: %r" % e)

# =========================== E. 301 mexport ======================================
P("")
P("#" * 96)
P("# E. .301 / .304 / .305  (SESAME mexport-style)")
P("#" * 96)
for rel in [r'mat_Ce\Cerium.301', r'Ta2O5\Ta2O5.301', r'mat_B\B.301']:
    path = os.path.join(MATTER, rel)
    P("")
    P("-" * 96)
    P("FILE %s exists=%s" % (rel, os.path.exists(path)))
    if not os.path.exists(path):
        continue
    for w in (15,):
        try:
            r = ER.read_301(path, w)
            P("  line0        : |%s|" % r['line0'])
            P("  matid=%s table=%s" % (r['matid'], r['tableno']))
            P("  line0_fields : %s" % ['%g' % x for x in r['line0_fields']])
            P("  line_widths  : %s" % r['line_widths'])
            P("  n_body(width=%d) = %d" % (w, r['n_body']))
            P("  body_head    : %s" % ['%.6g' % x for x in r['body_head'][:16]])
            P("  body_tail    : %s" % ['%.6g' % x for x in r['body_tail']])
            P("  closure guesses (nr=123,nt=140?):")
            for nr_ in (123,):
                for nt_ in (140,):
                    for expr, val in [('nr+nt+nr*nt', nr_ + nt_ + nr_ * nt_),
                                      ('nr+nt+2*nr*nt', nr_ + nt_ + 2 * nr_ * nt_),
                                      ('2*nr+nt+nr*nt', 2 * nr_ + nt_ + nr_ * nt_)]:
                        P("      %-14s = %d  diff=%d" % (expr, val, r['n_body'] - val))
        except Exception as e:
            P("  read_301 error: %r" % e)

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
