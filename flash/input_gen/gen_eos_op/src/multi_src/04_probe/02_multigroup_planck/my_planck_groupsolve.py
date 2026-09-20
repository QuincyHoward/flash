import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def strip15(s):
    v = []
    for j in range(0, len(s) - 14, 15):
        try:
            v.append(float(s[j:j+15]))
        except ValueError:
            v.append(None)
    rem = s[(len(s) // 15) * 15:]
    if rem.strip():
        try:
            v.append(float(rem))
        except ValueError:
            v.append(None)
    return v

def solve(p):
    L = [l for l in read(p) if l.strip()]
    hdr = [L[0][j:j+15] for j in range(0, 60, 15)]
    nrho, nT = int(round(float(hdr[2]))), int(round(float(hdr[3])))
    body = []
    for l in L[2:]:
        body.extend(strip15(l))
    D = body[nrho + nT:]
    nD = len(D)
    print('=' * 76)
    print('%s  nrho=%d nT=%d  2D len=%d' % (p, nrho, nT, nD))
    G = nrho * nT
    print('  G=nrho*nT=%d   nD/G=%.6f   nD%%G=%d' % (G, nD / G, nD % G))
    # hypothesis: k groups each = (1 + G) = G+1  (one extra number per group)
    for extra in range(0, 6):
        step = G + extra
        if step and nD % step == 0:
            k = nD // step
            print('  *** nD = %d groups x (G+%d=%d) ***' % (k, extra, step))
        # or groups = G then one header AFTER each group: k*(G)+k-1 or k*(G+1)
    # hypothesis with per-group grid re-emitted
    for extra in range(0, 4):
        step = 2 * (nrho + nT) + G + extra
        if nD % step == 0:
            print('  *** nD = %d x (2*(nrho+nT)+G+%d=%d) ***' % (nD // step, extra, step))

for p in ['matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Gd/Gd20PLANCK',
          'matter++/mat_Gd/Gd100PLANCK',
          'matter++/CH/CHSi1_mopp',
          'matter++/mat_Be-1.0/opbe']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        solve(p)
