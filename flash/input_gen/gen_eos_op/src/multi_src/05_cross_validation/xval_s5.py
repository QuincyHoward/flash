# -*- coding: utf-8 -*-
"""Drive eos_final: run all readers over the target files and print structure."""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
MATTER = EF.MATTER
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s5.txt')
L = []
def P(s=''):
    L.append(str(s))

P("=" * 100); P("SESAME 301 STRUCTURAL PARSE"); P("=" * 100)
for rel in [r'Ta2O5\PowerLawTa2O5_EOS.SESAME', r'Ta2O5\PowerLawTa2O5_EOS.SESAME_',
            r'SiO2\eos_21.sesame', r'SiO2\eos_22.sesame', r'SiO2\eos_23.sesame',
            r'SiO2\eos_24.sesame', r'SiO2\opc_1022.sesame_PLANCK']:
    path = os.path.join(MATTER, rel)
    P(""); P("-" * 100)
    P("FILE %s" % rel)
    if not os.path.exists(path):
        P("  MISSING"); continue
    try:
        r = EF.read_sesame301(path)
    except Exception as e:
        P("  ERR %r" % e); continue
    P("  N=%d  201 hdr=[matid=%g 201?=%g ver=%g ntab=%d]" %
      (r['N'], r['h201'][0], r['h201'][1], r['h201'][2], r['ntab']))
    P("  all_closed=%s consumed=%d leftover=%d" % (r['all_closed'], r['consumed'], r['leftover']))
    for k, rec in enumerate(r['records']):
        P("    rec%d start=%d tabno=%d ne=%d nr=%d c=%g closure=%s blen=%d" %
          (k, rec['start'], rec['tabno'], rec['ne'], rec['nr'], rec['c'],
           rec['closure'], len(rec.get('body', []))))
        if rec['closure'] == 'OK':
            b = rec['body']
            P("       scalars = %s" % ['%.6g' % x for x in b[0:3]])
            P("       eblk first 3 rows (T,P,E per density):")
            for j in range(min(3, rec['ne'])):
                P("          %s" % ['%.6g' % x for x in b[3 + 3 * j: 6 + 3 * j]])
            P("       dblk first 3 rows (T,P,E per energy):")
            for j in range(min(3, rec['nr'])):
                off = 3 + 3 * rec['ne'] + 3 * j
                P("          %s" % ['%.6g' % x for x in b[off:off + 3]])
            break

P(""); P("=" * 100); P("MULTI OPACITY STRUCTURAL PARSE"); P("=" * 100)
OPF = [r'mat_Ce\Ce.PLANCK', r'mat_Ce\Ce.ROSS', r'mat_Ce\Ce.EPS', r'mat_Ce\Ce.ZEFF',
       r'mat_C-1.0\C_1G.PLANCK', r'mat_C-1.0\C_20GSNOP.PLANCK', r'mat_C-1.0\C_20GSNOP.ZEFF',
       r'mat_C-1.0\C_Z.dat', r'mat_C-1.0\Carbon.Planck', r'mat_C-1.0\Carbon.Zeff',
       r'mat_Ti\Ti_Planck', r'mat_Ti\Ti_Ross', r'mat_Ti\Ti_EPS', r'mat_Ti\Ti_EPS',
       r'mat_Ti\SNOP_NLTE.PLANCK', r'mat_Ti\SNOP_NLTE.ZEFF', r'mat_Ti\SNOP_LTE.PLANCK',
       r'mat_Au-1.0\Au100PLANCK', r'mat_Au-1.0\SNOP.PLANCK', r'mat_Au-1.0\SNOP.ZEFF',
       r'mat_He\SNOP.PLANCK', r'mat_Gd\Gd20PLANCK', r'mat_Gd\Gd20ZEFF',
       r'mat_Gd\Gd100PLANCK', r'mat_Al-1.0\1041_PLANCK']
for rel in OPF:
    path = os.path.join(MATTER, rel)
    P(""); P("-" * 100)
    P("FILE %s" % rel)
    if not os.path.exists(path):
        P("  MISSING"); continue
    try:
        r = EF.read_multi_opacity(path)
    except Exception as e:
        P("  ERR %r" % e); continue
    P("  L0 |%s|" % r['line0'])
    P("  L1 |%s|  -> %s" % (r['line1'], r['line1nums']))
    P("  cat=%s tableid=%s l0nums=%s n_body=%d nlines=%d" %
      (r['category'], r['tableid'], r['l0nums'], r['n_body'], r['nlines']))
    P("  candidates (nm,NR,NT,diff): %s" % r.get('candidates'))
    if r['closure'] == 'OK':
        P("  *** CLOSURE OK [%s] form=%s NR=%d NT=%d" % (r['how'], r['form'], r['nr'], r['nt']))
        P("      rho_log10 = %s" % ['%.6g' % x for x in r['rho_log10']])
        P("      rho g/cc  = %s" % ['%.6g' % x for x in r['rho_grid']])
        P("      T_log10 first6=%s last4=%s  monotonic=%s" %
          (['%.6g' % x for x in r['T_log10'][:6]], ['%.6g' % x for x in r['T_log10'][-4:]],
           all(r['T_log10'][i] < r['T_log10'][i + 1] for i in range(len(r['T_log10']) - 1))))
        v = r['vals']
        P("      values n=%d  min=%.6g max=%.6g" % (len(v), min(v), max(v)))
    else:
        P("  *** CLOSURE FAILED")

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
