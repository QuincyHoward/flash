# -*- coding: utf-8 -*-
"""Final identification attempt for the trailing nRho block.

Established:
  * tail is NOT proportional to rho in the big files (nearly constant over 8 decades)
  * tail[rho=0.01] is IDENTICAL (1.16044e7) for Au and Ta2O5 -> not material specific
  * tail spans 1.16e7 .. 1.18e9 across the six samples

The near-constancy in rho, plus material-independence at a shared rho point,
points at a *reference constant*, not a per-material curve.

Test the strongest candidate:  the tail is the
  "cold curve / reference pressure"  OR
  the  rho * c_s^2  evaluated with a *fixed* reference sound speed
  OR  simply a *unit-conversion* helper table.

Also test the arithmetic relationships among the observed constants:
    1.16044e7   (Au, Ta2O5, eos_22 first grid point)
    1.16043e9   (eos_22)
    1.17759e9   (eos_23)
    1.16884e9   (eos_24)
    2.90399e8   (eos_21)
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
    return dict(p=p, v=v, nr=nr, nt=nt, rho=rho, T=T, b1=M(b1), b2=M(b2), tail=tail)


samples = {}
for p in sorted(glob.glob(os.path.join(ROOT, '**', '*.sesame'), recursive=True)
                + glob.glob(os.path.join(ROOT, '**', '*.SESAME'), recursive=True)):
    samples[os.path.basename(p)] = load(p)

C = {
    'eos_21.sesame': 2.90399e8,
    'eos_22.sesame': 1.16043e9,
    'eos_23.sesame': 1.17759e9,
    'eos_24.sesame': 1.16884e9,
    'PowerLawTa2O5_EOS.SESAME': 1.16044e7,
    'Au_2003POPHammerRosen_EOS.SESAME': 1.16044e7,
}

print('=== relationships among the tail constants ===')
ks = list(C)
for i, a in enumerate(ks):
    for b in ks[i + 1:]:
        r = C[a] / C[b]
        print('  %-32s / %-32s = %-12.6g   (1/%-.6g)' % (a, b, r, 1 / r))

print()
print('=== reference: 1 eV = 1.1604519e4 K   =>  1 eV in "1e3 K" = 11.6045 ===')
print('    1.16044e7 / 1.1604519e4 = %.6f' % (1.16044e7 / 1.1604519e4))
print('    1.16043e9 / 1.1604519e4 = %.6f' % (1.16043e9 / 1.1604519e4))
print('    2.90399e8 / 1.1604519e4 = %.6f' % (2.90399e8 / 1.1604519e4))
print()
print('=== reference: 1 J = 1e7 erg; 1 Mbar*cm3/g = 1e12 erg/g  -> 1e5 ratio ===')
for k in ks:
    print('  %-34s / 1e7 = %-14.6g   /1e12 = %-12.6g' % (k, C[k] / 1e7, C[k] / 1e12))

print()
print('=== does tail[0] equal rho[0] * something? ===')
for name, d in samples.items():
    r0, t0 = d['rho'][0], d['tail'][0]
    if r0:
        print('  %-34s rho[0]=%-12.6g tail[0]=%-14.6g tail/rho=%-14.6g'
              % (name, r0, t0, t0 / r0))

print()
print('=== compare tail to the LAST column of block2 (a fixed rho, all T)? ===')
for name, d in samples.items():
    nr, nt = d['nr'], d['nt']
    last_rho_col_b2 = [d['b2'][t][nr - 1] for t in range(nt)]
    print('  %-34s b2[:,rho_max]: min=%-12.6g max=%-12.6g   tail[0]=%-12.6g'
          % (name, min(last_rho_col_b2), max(last_rho_col_b2), d['tail'][0]))

print()
print('=== is the tail simply a *constant* repeated (a header leftover)? ===')
for name, d in samples.items():
    t = d['tail']
    sp = (max(t) - min(t)) / (abs(max(t)) or 1)
    print('  %-34s n=%-4d spread=%.4g   %s'
          % (name, len(t), sp, 'CONSTANT' if sp < 1e-3 else ('NEAR-CONST' if sp < 0.1 else 'CURVE')))
