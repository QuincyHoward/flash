# -*- coding: utf-8 -*-
"""Stage 4 (v2): corrected layouts.
 (a) SESAME 301 body structure/orientation on the small PowerLaw table.
 (b) MULTI opacity: header variants + closure via NR*NT factorisation.
"""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_readers as ER

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(HERE, 'xval_s4.txt')
lines = []
def P(s=''):
    lines.append(str(s))

# ---------------------------------------------------------------------------------
# (a) SESAME 301 body
# ---------------------------------------------------------------------------------
def sesame_nums(path):
    s = ER.read_text(path)
    ls = [l for l in ER.split_lines(s) if l.strip()]
    f = []
    for l in ls:
        f.extend(ER.floats_fixed(l, 15))
    return ls, f

P("#" * 100)
P("# (a) SESAME 301 HEADER + BODY  (Ta2O5 PowerLaw, small table)")
P("#" * 100)
for rel in [r'Ta2O5\PowerLawTa2O5_EOS.SESAME', r'Ta2O5\PowerLawTa2O5_EOS.SESAME_']:
    path = os.path.join(MATTER, rel)
    ls, f = sesame_nums(path)
    P("")
    P("FILE %s   N=%d" % (rel, len(f)))
    P("  LINE 0 |%s|" % ls[0])
    P("  LINE 1 |%s|" % ls[1])
    P("  first 12 nums: %s" % ['%.7g' % x for x in f[:12]])
    h201 = f[0:4]
    P("  [0:4] 201 header: matid=%g  tabno=%g  version=%g  **ntab_following=%g**"
      % tuple(h201))
    h301 = f[4:9]
    P("  [4:9] 301 header: ntab(301)=%g  **nr=%g**  **ne=%g**  rho_min=%g  rho_max=%g"
      % tuple(h301))
    nr = int(round(h301[1])); ne = int(round(h301[2]))
    b = f[9:]
    need = 3 + 3 * ne + 3 * nr
    P("  body from idx 9: len=%d ; 3+3*ne+3*nr = %d ; CLOSES=%s" % (len(b), need, len(b) == need))
    if len(b) == need:
        P("    body[0:3] = %s   (3 scalars)" % ['%.7g' % x for x in b[0:3]])
        P("    rho grid candidates: body[0:nr] = %s" % ['%.7g' % x for x in b[0:nr]])
        P("    scalar row:          body[nr:nr+3] = %s" % ['%.7g' % x for x in b[nr:nr + 3]])
        P("    --- first block (3*ne), rows of 3:")
        for k in range(3):
            off = 3 + 3 * k
            P("       e-row %d = %s" % (k, ['%.7g' % x for x in b[off:off + 3]]))
        P("    --- second block (3*nr), rows of 3:")
        off2 = 3 + 3 * ne
        for k in range(3):
            off = off2 + 3 * k
            P("       d-row %d = %s" % (k, ['%.7g' % x for x in b[off:off + 3]]))
        P("    INTERPRETATION: 3+3*ne+3*nr is the shape of a 301 record written as")
        P("      row(i_E) = [T(i_E,i_d), P(i_E,i_d), E(i_E,i_d)] for each density d,")
        P("      then row(i_dens) = [T(i_d,i_E), P(i_d,i_E), E(i_d,i_E)] for each energy.")

# ---------------------------------------------------------------------------------
# (b) MULTI opacity via the new reader
# ---------------------------------------------------------------------------------
P("")
P("#" * 100)
P("# (b) MULTI OPACITY: HEADER VARIANTS + CLOSURE")
P("#" * 100)
OPF = [
    r'mat_Ce\Ce.PLANCK', r'mat_Ce\Ce.ROSS', r'mat_Ce\Ce.EPS', r'mat_Ce\Ce.ZEFF',
    r'mat_C-1.0\C_1G.PLANCK', r'mat_C-1.0\C_20GSNOP.PLANCK', r'mat_C-1.0\C_20GSNOP.ZEFF',
    r'mat_C-1.0\C_Z.dat', r'mat_C-1.0\Carbon.Planck', r'mat_C-1.0\Carbon.Zeff',
    r'mat_Ti\Ti_Planck', r'mat_Ti\Ti_Ross', r'mat_Ti\Ti_EPS',
    r'mat_Ti\SNOP_NLTE.PLANCK', r'mat_Ti\SNOP_NLTE.ROSS', r'mat_Ti\SNOP_NLTE.ZEFF',
    r'mat_Ti\SNOP_LTE.PLANCK',
    r'mat_Au-1.0\Au100PLANCK', r'mat_Au-1.0\SNOP.PLANCK', r'mat_Au-1.0\SNOP.ZEFF',
    r'mat_He\SNOP.PLANCK', r'mat_Gd\Gd20PLANCK', r'mat_Gd\Gd20ZEFF',
    r'mat_Gd\Gd20EPS', r'mat_Gd\Gd20ROSS',
    r'mat_Al-1.0\1041_PLANCK', r'mat_Al-1.0\Al_Z67.dat',
    r'SiO2\SiO2.MultiGroupOpacity_PLANCK',
]
for rel2 in OPF:
    path = os.path.join(MATTER, rel2)
    P("")
    P("-" * 100)
    if not os.path.exists(path):
        P("MISSING %s" % rel2); continue
    s = ER.read_text(path)
    ls = [l.rstrip('\n') for l in ER.split_lines(s) if l.strip()]
    P("FILE %s  nlines=%d" % (rel2, len(ls)))
    P("  L0 |%s|" % ls[0])
    P("  L1 |%s|" % ls[1])
    try:
        r = ER.read_multi_opacity(path)
    except Exception as e:
        P("  reader err %r" % e); continue
    h = r['header']
    P("  tableid=%r cat=%r nums_on_L0=%s" % (h['tableid'], h['category'], h['nums']))
    P("  L1 nums = %s" % r.get('line1'))
    if r['closure'] == 'OK':
        P("  CLOSURE OK via %s : NR=%d NT=%d" % (r['closure_how'], r['nr'], r['nt']))
        rg = r['rho_grid']; tl = r['T_log10']
        P("    rho grid  = %.4g .. %.4g g/cc  (first6=%s)" % (rg[0], rg[-1],
                                                            ['%.4g' % x for x in rg[:6]]))
        P("    T  10^log10 first6 = %s last=%s" % (['%.4g' % x for x in tl[:6]],
                                                   ['%.4g' % x for x in tl[-3:]]))
        v = r['vals_log10']
        flat = [x for row in v for x in row]
        P("    values(rows=NR=%d, cols=NT=%d) log10 range %.4g .. %.4g" %
          (len(v), len(v[0]), min(flat), max(flat)))
        P("    first data row = %s" % ['%.4g' % x for x in v[0][:6]])
    else:
        P("  CLOSURE FAILED, n_body=%d, candidates=%s" % (r['n_body'], r['candidates']))

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
