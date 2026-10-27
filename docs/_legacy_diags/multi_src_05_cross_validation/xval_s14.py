# -*- coding: utf-8 -*-
"""CROSS-VALIDATION on a real shared (rho,T) grid.

KEY INSIGHT for an honest P-vs-P test:
  mat_Ce contains Cerium.data.txt, a tabulation of the SAME FEOS run that wrote
  Cerium.feos / Cerium.cst / Cerium.301.  Its columns are
      i_rho  i_T  rho  T  P_tot  P_e  P_i  ... (see header parse)
  and it uses the SAME rho grid as Cerium.cst (6.77e-05 ... 3.807e+02 g/cc).
  So we can anchor `.feos` against `.cst`/`.data.txt` on identical (rho,T) nodes.

We also run the pure `.feos` vs `.cst` number-density consistency check.
"""
import os, io, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_readers as ER
MATTER = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')),
                      'src', 'Multi1D++Portable20241128', 'matter++')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s14.txt')
L = []
def P(s=''):
    L.append(str(s))

# ---------------------------------------------------------------- data.txt structure
P("=" * 100); P("A. Cerium.data.txt  -- column identification"); P("=" * 100)
p = os.path.join(MATTER, r'mat_Ce\Cerium.data.txt')
ls = [l for l in ER.lines_of(p) if l.strip()]
P("  nlines=%d" % len(ls))
for i in range(4):
    P("  L%d: |%s|" % (i, ls[i]))
rows = [ER.floats_any(l) for l in ls]
P("  ncols = %d" % len(rows[0]))
P("  first row  = %s" % ['%.8g' % x for x in rows[0]])
P("  second row = %s" % ['%.8g' % x for x in rows[1]])
# index columns
ir = 0; it = 1
rho_all = sorted(set(round(r[ir], 12) for r in rows))
T_all = sorted(set(round(r[it], 12) for r in rows))
P("  distinct i_rho values = %d" % len(rho_all))
P("  distinct i_T   values = %d" % len(T_all))
P("  i_rho max=%g  i_T max=%g" % (max(r[ir] for r in rows), max(r[it] for r in rows)))
P("  col2 (rho?) first12 distinct = %s" % ['%.6g' % x for x in
  sorted(set(round(r[2], 12) for r in rows))[:12]])
P("  col3 (T?)   first12 distinct = %s" % ['%.6g' % x for x in
  sorted(set(round(r[3], 12) for r in rows))[:12]])
P("  col-2 (T?)  first6 = %s" % ['%.6g' % x for x in rows[0][-2:]])
# identify: which column has 123 distinct values (=NRho) and which has 97 (=NT)
P("  -- column cardinalities (which are the two axes?):")
for c in range(len(rows[0])):
    vals = set(round(r[c], 12) for r in rows)
    if 2 <= len(vals) <= 200:
        P("     col %2d : %3d distinct  min=%.6g max=%.6g" % (c, len(vals),
          min(vals), max(vals)))

# ---------------------------------------------------------------- .cst as the T=0 row
P("")
P("=" * 100); P("B. Cerium.cst  vs  Cerium.data.txt at T=0 (number density check)")
P("=" * 100)
cst = ER.read_cst(os.path.join(MATTER, r'mat_Ce\Cerium.cst'))
P("  cst: title=%r  n_rows=%d" % (cst['title'], cst['n_rows']))
P("  cst rho range = %.6g .. %.6g g/cc" % (min(cst['rho']), max(cst['rho'])))
P("  cst numdens range = %.6g .. %.6g 1/cc" % (min(cst['numdens']), max(cst['numdens'])))
# rows with rho>0
pos = [(n, r) for n, r in zip(cst['numdens'], cst['rho']) if r > 0]
P("  positive-density rows = %d" % len(pos))
# derive A_eff from  n = rho*NA/A
NA = 6.02214076e23
Aeff = [r * NA / n for n, r in pos if n > 0]
P("  A_eff = rho*NA/n on positive rows: min=%.4f max=%.4f mean=%.4f" %
  (min(Aeff), max(Aeff), sum(Aeff) / len(Aeff)))
P("  -> compare with FEOS header Atot:")
fh = ER.read_feos_header(os.path.join(MATTER, r'mat_Ce\Cerium.feos'))
P("     feos h1 = %s" % ['%.8g' % x for x in fh['h1']])
P("     feos Atot(h1[7]) = %s   Ztot(h1[8]) = %s" % (fh['Atot'], fh['Ztot']))

# ---------------------------------------------------------------- feos header & grid
P("")
P("=" * 100); P("C. Cerium.feos  header"); P("=" * 100)
P("  h0 = %s" % ['%.8g' % x for x in fh['h0']])
P("  h1 = %s" % ['%.8g' % x for x in fh['h1']])
P("  NRho=%s  NT=%s" % (fh['NRho'], fh['NT']))

# ---------------------------------------------------------------- opacity cross-check
P("")
P("=" * 100); P("D. OPACITY cross-check: Ce.PLANCK records"); P("=" * 100)
op = ER.read_opacity(os.path.join(MATTER, r'mat_Ce\Ce.PLANCK'))
P("  nlines=%d NR=%d NT=%d per_record=%d rec_lines=%d n_records=%d truncated_last=%s" %
  (op['nlines'], op['nr'], op['nt'], op['per_record_values'], op['rec_lines'],
   op['n_records'], op['truncated_last']))
P("  total values accounted = %d ; file has %d lines" %
  (op['n_records'] * op['per_record_values'],
   2 + len(op['records']) * (1 + (op['per_record_values'] + 3) // 4)))
P("  rho grid (g/cc) = %s ... %s   (n=%d)" %
  ('%.4g' % op['rho_grid'][0], '%.4g' % op['rho_grid'][-1], len(op['rho_grid'])))
P("  T grid (eV)     = %s ... %s   (n=%d)" %
  ('%.4g' % op['T_grid'][0], '%.4g' % op['T_grid'][-1], len(op['T_grid'])))
P("  first 6 record bands (eV) and value ranges:")
for r in op['records'][:6]:
    v = r['vals']
    P("    rec%2d band=%-22s vals[%d] log10 range %.4g .. %.4g" %
      (r['idx'], str(['%.4g' % x for x in r['band_eV']]) if r['band_eV'] else 'None',
       len(v), min(v), max(v) if v else 0))
P("  last 3 record bands:")
for r in op['records'][-3:]:
    v = r['vals']
    P("    rec%2d band=%s vals[%d] log10 range %.4g .. %.4g" %
      (r['idx'], str(['%.4g' % x for x in r['band_eV']]) if r['band_eV'] else 'None',
       len(v), min(v), max(v) if v else 0))

P("")
P("=" * 100); P("E. Ce.ROSS / Ce.EPS comparison on identical grid"); P("=" * 100)
for f in ('Ce.ROSS', 'Ce.EPS', 'Ce.PLANCK'):
    o = ER.read_opacity(os.path.join(MATTER, 'mat_Ce', f))
    r0 = o['records'][0]
    P("  %-12s NR=%2d NT=%2d nrec=%2d rec0 band=%s rho[:3]=%s vals[:4]=%s" %
      (f, o['nr'], o['nt'], o['n_records'],
       ['%.3g' % x for x in r0['band_eV']] if r0['band_eV'] else 'None',
       ['%.4g' % x for x in o['rho_log10'][:3]], ['%.4g' % x for x in r0['vals'][:4]]))
# identical grid?
oo = {}
for f in ('Ce.ROSS', 'Ce.EPS', 'Ce.PLANCK'):
    oo[f] = ER.read_opacity(os.path.join(MATTER, 'mat_Ce', f))
same_grid = all(oo['Ce.PLANCK']['rho_log10'] == oo[f]['rho_log10'] for f in ('Ce.ROSS', 'Ce.EPS'))
same_T = all(oo['Ce.PLANCK']['T_log10'] == oo[f]['T_log10'] for f in ('Ce.ROSS', 'Ce.EPS'))
P("  rho grid identical across the 3 families: %s" % same_grid)
P("  T   grid identical across the 3 families: %s" % same_T)

with io.open(OUT, 'w', encoding='utf-8') as fh2:
    fh2.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
