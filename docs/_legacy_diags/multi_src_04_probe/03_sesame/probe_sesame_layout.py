# -*- coding: utf-8 -*-
"""Determine the TRUE layout of .sesame blocks.

Symptom: with the naive 'outer=T, inner=rho' reshape, A/rho is constant while
B/rho is not, and the size formula overshoots (143 vs 146, 419 vs 425).

Hypothesis to test: the two blocks are NOT both nT x nRho.  Try the
alternatives and see which one makes BOTH blocks well-behaved:
   L1: A=[nT][nRho], B=[nT][nRho]           (document's claim)
   L2: A=[nT][nRho], B=[nRho][nT]           (transposes)
   L3: both [nRho][nT]
   L4: A and B are interleaved, or there is an extra block
"""
import os

P = os.path.join('src', 'Multi1D++Portable20241128', 'matter++', 'mat_Au',
                 'Au_2003POPHammerRosen_EOS.SESAME')


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


v = read_sesame(P)
print('total values           =', len(v))
print('first 8                =', v[:8])

tid, mode, nr, nt = v[0], v[1], int(v[2]), int(v[3])
print('hdr: id=%g mode=%g nr=%d nt=%d' % (tid, mode, nr, nt))

off = 4
rho = v[off:off + nr]; off += nr
T = v[off:off + nt]; off += nt
print('rho =', rho)
print('T   =', ['%.6g' % x for x in T])
print('after grids, offset   =', off)
print('remaining             =', len(v) - off, '  nr*nt =', nr * nt)

rest = v[off:]
print()
print('--- remainder analysis ---')
print('len(rest)                = %d' % len(rest))
print('2*nr*nt                  = %d' % (2 * nr * nt))
print('len(rest) - 2*nr*nt      = %d' % (len(rest) - 2 * nr * nt))
print('nr                       = %d' % nr)
print('so trailing block size   = %d  (= nr ? %s)' % (len(rest) - 2 * nr * nt,
                                                     len(rest) - 2 * nr * nt == nr))

n2 = nr * nt
blk1 = rest[:n2]
blk2 = rest[n2:2 * n2]
tail = rest[2 * n2:]

print()
print('tail (%d) = %s' % (len(tail), ['%.6g' % x for x in tail]))

# ---- test layouts ---------------------------------------------------------
print()
print('=== layout tests on blk1 / blk2 ===')


def as_Tmajor(blk):
    return [blk[t * nr:(t + 1) * nr] for t in range(nt)]


def as_Rmajor(blk):
    return [blk[r * nt:(r + 1) * nt] for r in range(nr)]


def ratio_constancy(groups, denom):
    """max relative spread of group[i]/denom[i] across i."""
    worst = 0.0
    for g in groups:
        vals = [(g[i] / denom[i]) for i in range(len(denom)) if denom[i]]
        if len(vals) < 2:
            continue
        lo, hi = min(vals), max(vals)
        if hi:
            worst = max(worst, abs(hi - lo) / abs(hi))
    return worst


for name, blk in (('blk1', blk1), ('blk2', blk2)):
    for lname, grp in (('T-major [nT][nRho]', as_Tmajor(blk)),
                       ('R-major [nRho][nT]', as_Rmajor(blk))):
        spread_r = ratio_constancy(grp, rho)
        print('  %s %-22s  max rel-spread of col/rho = %.4g' % (name, lname, spread_r))

print()
print('=== raw first rows of each block (as written, 4 per line) ===')
for i in range(0, 24, 4):
    print('  blk1[%2d:%2d] = %s' % (i, i + 4, ['%12.6g' % x for x in blk1[i:i + 4]]))
print()
for i in range(0, 24, 4):
    print('  blk2[%2d:%2d] = %s' % (i, i + 4, ['%12.6g' % x for x in blk2[i:i + 4]]))
