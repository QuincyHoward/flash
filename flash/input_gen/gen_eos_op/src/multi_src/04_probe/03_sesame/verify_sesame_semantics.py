# -*- coding: utf-8 -*-
"""Independently re-verify which of the two .sesame data blocks is E and which is P.

Claim under test (document 15.2.4):
    block A = specific internal energy E   (A(T->0) -> 0 ; A ∝ rho at fixed T)
    block B = pressure P                   (B ∝ rho at fixed T)

Method: parse with the 15-char fixed-width reader, then
  (1) check A(T_min) ~ 0
  (2) check B/rho constant across rho at fixed T
  (3) check A/rho constant across rho at fixed T
  (4) check A rises monotonically with T
"""
import glob
import os

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


def analyse(path):
    v = read_sesame(path)
    tid, mode, nr, nt = v[0], v[1], int(v[2]), int(v[3])
    off = 4
    rho = v[off:off + nr]; off += nr
    T = v[off:off + nt]; off += nt
    n2 = nr * nt
    A = v[off:off + n2]; off += n2
    B = v[off:off + n2]; off += n2
    tail = v[off:off + nr]

    print('=' * 78)
    print(os.path.basename(path))
    print('  n=%d nr=%d nt=%d  formula=%d' % (len(v), nr, nt, 4 + 2 * nr + nt + 2 * n2 + nr))
    print('  table_id=%g  rho=[%s]' % (tid, ', '.join('%.4g' % x for x in rho)))
    print('  T min=%.4g  max=%.4g' % (T[0], T[-1]))

    def resh(col):
        return [col[t * nr:(t + 1) * nr] for t in range(nt)]

    Ar, Br = resh(A), resh(B)

    # (1) A at coldest temperature
    print('  [1] A(T_min)  = [%s]   (expect ~0 for E)' % ', '.join('%.4g' % x for x in Ar[0]))
    print('      B(T_min)  = [%s]' % ', '.join('%.4g' % x for x in Br[0]))

    # (2)(3) proportionality at hottest temperature
    t = nt - 1
    print('  [2] hottest T=%.4g eV' % T[t])
    print('      %-10s %14s %16s %10s %14s %10s' % ('rho', 'A', 'B', 'A/rho', 'B/A', 'B/rho'))
    for i in range(nr):
        a, b, r = Ar[t][i], Br[t][i], rho[i]
        ba = (b / a) if a else float('nan')
        print('      %-10.4g %14.6g %16.6g %10.5f %14.6g %10.5f' % (r, a, b, a / r, ba, b / r))

    # (4) monotonicity in T
    mono = all(Ar[t + 1][0] >= Ar[t][0] for t in range(nt - 1))
    print('  [4] A(rho_0) monotonically increasing in T: %s' % mono)
    print('  [tail] n=%d  = [%s]' % (len(tail), ', '.join('%.4g' % x for x in tail[:8])
                                     + (' ...' if len(tail) > 8 else '')))


for p in sorted(glob.glob(os.path.join(ROOT, '**', '*.SESAME'), recursive=True)):
    if os.path.getsize(p) < 200000:      # the small, human-checkable ones
        analyse(p)
