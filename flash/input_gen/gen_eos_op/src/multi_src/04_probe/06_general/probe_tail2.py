# -*- coding: utf-8 -*-
"""Chase the trailing block: is it a *constant* (per-file) or a rho-dependent curve?

Findings so far:
  eos_21  tail ~ 2.90399e8   (constant over rho, then slight drift)
  eos_22  tail ~ 1.16043e9   (near-constant, arch shape)
  Au      tail = 1.16044e7 (rho=0.01) .. 3.66e7 (rho=100)
  Ta2O5   tail = 1.16044e7 (rho=0.01) ..    <- SAME first value as Au!

KEY:  Au tail[rho=0.01] == Ta2O5 tail[rho=0.01] == 1.16044e7
      eos_22 tail[0]     == 1.16043e9      = 100 x 1.16043e7
      eos_21 tail[0]     == 2.90399e8      =  25.0 x 1.16160e7

Hypothesis A: the tail is the *cold curve* or a reference isotherm.
Hypothesis B: the tail is rho * Cs^2 or similar (a squared sound speed scale).
Hypothesis C: the tail is the *upper rho grid limit* related quantity.
Hypothesis D: the tail is actually the SECOND grid (nr values of something).
"""
import os
import glob
import math

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
    T = v[off:off + nt]; off += nt
    n2 = nr * nt
    b1 = v[off:off + n2]; off += n2
    b2 = v[off:off + n2]; off += n2
    tail = v[off:off + nr]
    M = lambda b: [b[t * nr:(t + 1) * nr] for t in range(nt)]
    return dict(p=p, n=len(v), nr=nr, nt=nt, rho=rho, T=T,
                b1=M(b1), b2=M(b2), tail=tail)


samples = []
for pat in ('**/*.sesame', '**/*.SESAME'):
    for p in sorted(glob.glob(os.path.join(ROOT, pat), recursive=True)):
        samples.append(load(p))

for d in samples:
    nr, nt, rho, T, b1, b2, tail = (d['nr'], d['nt'], d['rho'], d['T'],
                                    d['b1'], d['b2'], d['tail'])
    print('=' * 90)
    print('%-42s nr=%-4d nt=%-5d  table_id=%g' % (os.path.basename(d['p']), nr, nt, read_sesame(d['p'])[0]))
    print('  rho[0]=%-12.6g rho[-1]=%-12.6g' % (rho[0], rho[-1]))
    print('  T[0]  =%-12.6g T[-1]  =%-12.6g' % (T[0], T[-1]))
    print('  tail[0]=%-14.6g tail[-1]=%-14.6g  const? %s'
          % (tail[0], tail[-1],
             'YES' if max(tail) / min(tail) < 1.001 else 'near'))
    # Hypothesis: tail == cold curve of block2 (T index 0) ? or of block1?
    c2 = b2[0]
    c1 = b1[0]
    print('  b2[T=0]  = %s' % ['%.6g' % x for x in c2[:6]])
    print('  b1[T=0]  = %s' % ['%.6g' % x for x in c1[:6]])
    print('  tail     = %s' % ['%.6g' % x for x in tail[:6]])
    # compare tail to b2[T=0]
    if len(tail) == len(c2):
        same = all(abs(tail[i] - c2[i]) <= 1e-6 * max(1.0, abs(c2[i])) for i in range(nr))
        print('  tail == b2[T=0] ? %s' % same)
        same1 = all(abs(tail[i] - c1[i]) <= 1e-6 * max(1.0, abs(c1[i])) for i in range(nr))
        print('  tail == b1[T=0] ? %s' % same1)
    # ratio to rho[-1]^2
    print('  tail[0]/rho[-1]**2 = %.6g' % (tail[0] / (rho[-1] ** 2)))
    print('  tail[0]/T[-1]      = %.6g' % (tail[0] / T[-1]))
    # is tail ~ tail[0] * (rho/rho[0])**x?
    if nr >= 3 and rho[0] > 0 and tail[0] > 0:
        print('  tail[-1]/tail[0] = %.6g   rho[-1]/rho[0] = %.6g' % (tail[-1] / tail[0], rho[-1] / rho[0]))
    print()
