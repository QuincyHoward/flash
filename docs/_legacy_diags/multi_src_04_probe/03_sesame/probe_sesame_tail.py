# -*- coding: utf-8 -*-
"""Identify the trailing nRho block.

Candidate physical quantities to test against the tail values of Au:
  rho = [0.01, 0.1, 1, 10, 20, 100]
  tail= [1.16044e7, 1.52212e7, 2.02138e7, 2.71055e7, 2.9654e7, 3.66186e7]

Tests:
  T1  tail is a cold pressure / cold energy at T -> 0, read off blk2/blk1?
  T2  tail == some function of the rho grid only (a cold curve)
  T3  compare with a *different* file having the same rho grid
  T4  compare Ta2O5 tail (rho 0.01/10/50) with Au tail - same numbers at rho=0.01!
         Au   tail[0] = 1.16044e7
         Ta2O5 tail[0] = 1.16044e7
      IDENTICAL at rho=0.01 -> the tail is NOT material-specific?
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


print('Tail values across ALL .sesame/.SESAME samples:')
print()
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, '**', '*.sesame'), recursive=True)
                + glob.glob(os.path.join(ROOT, '**', '*.SESAME'), recursive=True)):
    v = read_sesame(p)
    nr, nt = int(v[2]), int(v[3])
    off = 4 + nr + nt + 2 * nr * nt
    tail = v[off:off + nr]
    rho = v[4:4 + nr]
    rows.append((os.path.basename(p), nr, nt, rho, tail))

seen = set()
for name, nr, nt, rho, tail in rows:
    key = (tuple(rho), tuple(tail[:3]))
    if key in seen:
        continue
    seen.add(key)
    print('  %-40s nr=%-4d nt=%-5d' % (name, nr, nt))
    print('      rho  = %s' % ['%.6g' % x for x in rho])
    print('      tail = %s' % ['%.6g' % x for x in tail])
    print('      tail/rho   = %s' % ['%.6g' % (t / r) for t, r in zip(tail, rho)])
    print()

print('=== cross-material comparison at identical rho ===')
for name, nr, nt, rho, tail in rows:
    if rho and abs(rho[0] - 0.01) < 1e-12:
        print('  %-40s tail[rho=0.01] = %.8g' % (name, tail[0]))

print()
print('=== does the tail match a power law in rho? ===')
import math
for name, nr, nt, rho, tail in rows:
    if nr >= 3:
        # log-log slope between consecutive points
        sl = []
        for i in range(nr - 1):
            if rho[i] > 0 and rho[i + 1] > 0 and tail[i] > 0 and tail[i + 1] > 0:
                sl.append(math.log(tail[i + 1] / tail[i]) / math.log(rho[i + 1] / rho[i]))
        print('  %-38s log-log slopes = %s' % (name, ['%.4f' % s for s in sl]))
