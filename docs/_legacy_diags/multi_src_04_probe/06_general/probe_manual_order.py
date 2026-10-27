# -*- coding: utf-8 -*-
"""Verify the tail block = e0[nr] (cold energy), per the local MULTI manual.

The manual (doc/MULTI使用的SESAME数据文件格式.docx) states the layout:

    4        | MID, normal-density(unused), nr, ne
    nr       | rho grid  (rho_min ... rho_max)
    ne       | de  grid  (de_min ... de_max)        <- energy INCREMENTS from cold
    nr       | e0[nr]    COLD ENERGY per rho        <- ** THE TRAILING BLOCK **
    nr*ne    | P[ne*nr]  pressure
    nr*ne    | T[ne*nr]  temperature (Kelvin)

    "即参数个数为 4+2*nr+ne+2*nr*ne"

So the record order is  hdr, rho, de, e0, P, T  -- NOT hdr, rho, de, P, T, e0!

My earlier reader assumed  hdr, rho, T, blk1, blk2, tail  which happens to
partition the SAME total, but assigns e0 to the wrong slot and shifts
everything.  Let me re-read with the manual's order and see whether the
semantics snap into place.

Sanity predictions if the manual is right:
  * the block I called "tail" is really e0, and it must be NEGATIVE-capable,
    monotone-ish in rho, and identical for two materials only if their
    cold curves coincide (unlikely) -> so check Au vs Ta2O5 again.
  * the block I called "blk2" (the last one, T in Kelvin per manual) must be
    in KELVIN, i.e. much larger than eV numbers.
"""
import os
import glob

ROOT = os.path.join('src', 'Multi1D++Portable20241128')


def read_sesame(path):
    raw = open(path, 'rb').read()
    rows = [r for r in raw.replace(b'\r\n', b'\n').split(b'\n') if r.strip()]
    vals = []
    for r in rows:
        for j in range(0, len(r), 15):
            seg = r[j:j + 15]
            if seg.strip():
                try:
                    vals.append(float(seg))
                except ValueError:
                    pass
    return vals


def load(p):
    v = read_sesame(p)
    nr, nt = int(v[2]), int(v[3])
    off = 4
    rho = v[off:off + nr]; off += nr
    de = v[off:off + nt]; off += nt
    e0 = v[off:off + nr]; off += nr            # <-- trailing-by-manual position
    n2 = nr * nt
    P = v[off:off + n2]; off += n2
    T = v[off:off + n2]; off += n2
    rest = v[off:]
    return dict(p=p, n=len(v), nr=nr, nt=nt, rho=rho, de=de, e0=e0, P=P, T=T, rest=rest)


print('Manual order: hdr(4) + rho(nr) + de(ne) + e0(nr) + P(nr*ne) + T(nr*ne)')
print('predicted size = 4 + 2*nr + ne + 2*nr*ne')
print()

for p in sorted(glob.glob(os.path.join(ROOT, '**', '*.sesame'), recursive=True)
                + glob.glob(os.path.join(ROOT, '**', '*.SESAME'), recursive=True)):
    d = load(p)
    nr, nt = d['nr'], d['nt']
    pred = 4 + 2 * nr + nt + 2 * nr * nt
    print('=' * 90)
    print('%-42s n=%-8d nr=%-4d ne=%-5d  pred=%-8d  exact=%s  leftover=%d'
          % (os.path.basename(p), d['n'], nr, nt, pred, d['n'] == pred, len(d['rest'])))
    print('  rho   = %s' % ['%.6g' % x for x in d['rho'][:6]])
    print('  de    = %s' % ['%.6g' % x for x in d['de'][:6]])
    print('  e0    = %s' % ['%.6g' % x for x in d['e0'][:8]])
    print('  P[0:6]= %s' % ['%.6g' % x for x in d['P'][:6]])
    print('  T[0:6]= %s' % ['%.6g' % x for x in d['T'][:6]])

    # manual says T is in KELVIN.  eV values are ~1e0..1e5; K values ~1e4..1e9
    tmax = max(d['T']); tmin = min(d['T'])
    print('  T range = %.6g .. %.6g   (K? max/11604 = %.6g eV)'
          % (tmin, tmax, tmax / 11604.519))
    print('  P range = %.6g .. %.6g   P/rho first = %s'
          % (min(d['P']), max(d['P']),
             ['%.6g' % (d['P'][i] / d['rho'][i]) for i in range(min(len(d['rho']), 6)) if d['rho'][i]]))
    print()

# focus on Au, the hand-checkable one
print('#' * 90)
d = load(os.path.join(ROOT, 'matter++', 'mat_Au', 'Au_2003POPHammerRosen_EOS.SESAME'))
nr, nt = d['nr'], d['nt']
print('Au: nr=%d nt=%d' % (nr, nt))
print('  rho =', d['rho'])
print('  de  =', ['%.6g' % x for x in d['de']])
print('  e0  =', ['%.6g' % x for x in d['e0']])
print()
print('  P as [nt][nr] (manual: P[(0~nr-1)+nr*i] , i = energy index):')
Pm = [d['P'][i * nr:(i + 1) * nr] for i in range(nt)]
Tm = [d['T'][i * nr:(i + 1) * nr] for i in range(nt)]
print('    %-12s %s' % ('i', ' '.join('%12s' % ('r=%.4g' % r) for r in d['rho'])))
for i in (0, 1, 2, nt - 1):
    print('    %-12d %s' % (i, ' '.join('%12.6g' % x for x in Pm[i])))
print()
print('  T as [nt][nr]:')
for i in (0, 1, 2, nt - 1):
    print('    %-12d %s' % (i, ' '.join('%12.6g' % x for x in Tm[i])))
print()
print('  P/rho per row (should be ~const at fixed energy if P ~ (gamma-1)*rho*e):')
for i in (0, nt // 2, nt - 1):
    print('    i=%-6d %s' % (i, ' '.join('%12.6g' % (Pm[i][j] / d['rho'][j]) for j in range(nr))))
