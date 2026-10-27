# -*- coding: utf-8 -*-
"""Resolve E-vs-P and the tail block, using correct T-major indexing.

Established facts (from probe_sesame_layout.py):
  blk1 T-major is proportional to rho  (rel-spread 4.6e-8)
  blk1 at coldest T is identically 0
  blk2 at coldest T = 644.79 * rho     (rho in g/cc)

So blk2 is the one that behaves like pressure at low T.
Question 1: which block is E and which is P?
Question 2: what is the trailing nRho block?
"""
import os

ROOT = os.path.join('src', 'Multi1D++Portable20241128', 'matter++')


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


def load(path):
    v = read_sesame(path)
    nr, nt = int(v[2]), int(v[3])
    off = 4
    rho = v[off:off + nr]; off += nr
    T = v[off:off + nt]; off += nt
    n2 = nr * nt
    blk1 = v[off:off + n2]; off += n2
    blk2 = v[off:off + n2]; off += n2
    tail = v[off:off + nr]
    M = lambda b: [b[t * nr:(t + 1) * nr] for t in range(nt)]
    return dict(path=path, n=len(v), nr=nr, nt=nt, rho=rho, T=T,
                b1=M(blk1), b2=M(blk2), tail=tail)


A = load(os.path.join(ROOT, 'mat_Au', 'Au_2003POPHammerRosen_EOS.SESAME'))
B = load(os.path.join(ROOT, 'Ta2O5', 'PowerLawTa2O5_EOS.SESAME'))

for d in (A, B):
    print('=' * 84)
    print(os.path.basename(d['path']))
    nr, nt, rho, T = d['nr'], d['nt'], d['rho'], d['T']
    # rho grid: is the FIRST grid really rho or is it T?
    print('  grid1 =', ['%.6g' % x for x in d['rho']], ' monotonic:', all(
        d['rho'][i] < d['rho'][i + 1] for i in range(nr - 1)))
    print('  grid2 =', ['%.6g' % x for x in T], ' monotonic:', all(
        T[i] < T[i + 1] for i in range(nt - 1)))
    print('  grid2/grid1 magnitude ratio = %.4g  (T/rho ~ 1e5 means grid2 is T in eV)'
          % (T[-1] / rho[-1]))

    def show(blk, tag):
        print('  --- %s ---' % tag)
        print('       %-12s %-14s %-14s %-12s' % ('rho', 'blk[coldest T]', 'blk[hottest T]', 'blk/rho cold'))
        cold, hot = blk[0], blk[nt - 1]
        for i in range(nr):
            print('       %-12.6g %-14.6g %-14.6g %-12.6g'
                  % (rho[i], cold[i], hot[i], (cold[i] / rho[i]) if rho[i] else 0))

    show(d['b1'], 'BLOCK 1')
    show(d['b2'], 'BLOCK 2')

    print('  TAIL (%d) = %s' % (len(d['tail']), ['%.6g' % x for x in d['tail']]))
    print('  tail/rho = %s' % ['%.6g' % (x / r) for x, r in zip(d['tail'], rho)])
    print('  tail**(3/5) approx = %s' % ['%.6g' % (abs(x) ** 0.6) for x in d['tail']])
    print()

# ---- physical sanity check ------------------------------------------------
print('=' * 84)
print('PHYSICAL CHECK on Au (rho=1, reading down T):')
nr, nt, rho, T = A['nr'], A['nt'], A['rho'], A['T']
j = rho.index(1.0)
print('  %-14s %-16s %-16s %-14s' % ('T [eV]', 'blk1', 'blk2', 'blk2/blk1'))
for t in (0, 6, 12, 18, 24, 30):
    a, b = A['b1'][t][j], A['b2'][t][j]
    print('  %-14.6g %-16.6g %-16.6g %-14.6g' % (T[t], a, b, (b / a) if a else float('nan')))

print()
print('  Ideal-gas expectation: P = (1+Zbar)*rho*k*T/(A*mp)  ->  P/E should scale like')
print('  (gamma-1) ~ 2/3 for a monatomic gas if E is per-volume thermal energy.')
print('  Check whether blk2/blk1 approaches a constant at high T.')
for t in range(nt - 1, max(nt - 8, 0), -1):
    a, b = A['b1'][t][j], A['b2'][t][j]
    print('    T=%-12.6g  b1=%-14.6g b2=%-14.6g  b2/b1=%.6g' % (T[t], a, b, (b / a) if a else 0))
