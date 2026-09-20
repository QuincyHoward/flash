# -*- coding: utf-8 -*-
"""FINAL: the M-variant opacity file holds MULTIPLE 112-line tables back to back,
each preceded by its own 2-line header."""
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eos_final as EF
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xval_s13.txt')
L = []
def P(s=''):
    L.append(str(s))

CASES = [(r'mat_Ce\Ce.PLANCK', 20, 20), (r'mat_Ce\Ce.ROSS', 20, 20),
         (r'mat_Ce\Ce.EPS', 20, 20), (r'mat_Ce\Ce.ZEFF', 20, 20),
         (r'mat_C-1.0\C_1G.PLANCK', 20, 20), (r'mat_C-1.0\C_Z.dat', 43, 43),
         (r'mat_Ti\SNOP_NLTE.PLANCK', 20, 20), (r'mat_Au-1.0\Au100PLANCK', 30, 50),
         (r'mat_C-1.0\1041_PLANCK', 20, 20)]
P("%-24s %5s %5s %7s %8s %6s %8s %s" %
  ("file", "NR", "NT", "nlines", "per_tab", "n_tab", "nlines/nt", "record (lines)"))
P("-" * 106)
for rel, NR, NT in CASES:
    path = os.path.join(EF.MATTER, rel)
    if not os.path.exists(path):
        P("%-24s MISSING" % rel); continue
    ls = [l for l in EF.lines_of(path) if l.strip()]
    nl = len(ls)
    per = NR + NT + NR * NT              # values per table
    rec_lines = 2 + (per + 3) // 4       # header(1) + axis(1) + ceil(per/4)
    nt = nl / rec_lines
    P("%-24s %5d %5d %7d %8d %6s %8s %s" %
      (rel.split('\\')[-1], NR, NT, nl, per,
       ('%.2f' % nt) if nt != int(nt) else str(int(nt)),
       '', '2+ceil(%d/4)=%d' % (per, rec_lines)))

P("")
P("=" * 100)
P("VERIFY: each 112-line record starts with a 2-line header")
P("=" * 100)
for rel, NR, NT in [(r'mat_Ce\Ce.PLANCK', 20, 20), (r'mat_Ce\Ce.ZEFF', 20, 20),
                    (r'mat_C-1.0\C_Z.dat', 43, 43)]:
    path = os.path.join(EF.MATTER, rel)
    ls = [l for l in EF.lines_of(path) if l.strip()]
    per = NR + NT + NR * NT
    rec = 2 + (per + 3) // 4
    P(""); P("FILE %s  rec_lines=%d  nlines=%d  n_rec=%d" %
             (rel, rec, len(ls), len(ls) // rec))
    for k in range(len(ls) // rec):
        i = k * rec
        P("  --- record %d starts at line %d" % (k, i))
        P("      header0: |%s|" % ls[i][:70])
        P("      header1: |%s|" % ls[i + 1][:70])
        # first 3 data lines
        P("      data   : %s" % ['%.6g' % x for x in EF.floats_fixed(ls[i + 2], 15)])
        P("               %s" % ['%.6g' % x for x in EF.floats_fixed(ls[i + 3], 15)])
        if k >= 3:
            P("      ... (stopping after 4 records)")
            break

with io.open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("WROTE", OUT, os.path.getsize(OUT))
