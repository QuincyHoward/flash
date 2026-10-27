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
    print('%s  nrho=%d nT=%d 2D=%d' % (p, nrho, nT, nD))
    G = nrho * nT
    # Hypothesis set, evaluated for all combos of small extras
    for a in range(0, 4):
        for b in range(0, 4):
            step = G + a * nrho + b * nT
            if step > 0 and nD % step == 0:
                k = nD // step
                if 1 <= k <= 5000:
                    print('  HIT: nD = %d x (G + %d*nrho + %d*nT = %d)' % (k, a, b, step))
    # hypothesis: single group count k, size G, plus k*(nrho+nT) grid repeats?
    for k in range(1, 400):
        if nD == k * (G + nrho + nT):
            print('  HIT2: k=%d x (G+nrho+nT=%d)' % (k, G + nrho + nT))
    # hypothesis: k*(G) + (k+1)*something
    for k in range(1, 400):
        rest = nD - k * G
        if rest > 0 and rest % (k + 1) == 0 and rest // (k + 1) < 60:
            print('  HIT3: k=%d, rest=%d, rest/(k+1)=%d' % (k, rest, rest // (k + 1)))

for p in ['matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Gd/Gd20PLANCK',
          'matter++/mat_Gd/Gd100PLANCK',
          'matter++/CH/CHSi1_mopp',
          'matter++/mat_Be-1.0/opbe',
          'matter++/CH/CHSi1_mopp100']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        solve(p)
