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

def analyze(p):
    L = [l for l in read(p) if l.strip()]
    hdr = [L[0][j:j+15] for j in range(0, 60, 15)]
    nrho = int(round(float(hdr[2])))
    nT = int(round(float(hdr[3])))
    body = []
    for l in L[2:]:
        body.extend(strip15(l))
    nv = len(body)
    print('=' * 74)
    print('%s  table=%s  nrho=%d nT=%d  total=%d' % (p, hdr[0].strip(), nrho, nT, nv))
    print('  log10(rho) grid [0:%d] = %s .. %s' % (nrho, body[0], body[nrho - 1]))
    print('  log10(T)   grid [%d:%d] = %s .. %s' % (nrho, nrho + nT, body[nrho], body[nrho + nT - 1]))
    rem = nv - nrho - nT
    print('  remainder = %d' % rem)
    for ng in range(1, 5000):
        if rem % ng == 0 and rem // ng == nrho * nT:
            print('  *** remainder = %d groups x %d (nrho*nT) ***' % (ng, nrho * nT))
    # check whether remainder is multiple of nrho*nT
    import math
    print('  rem/(nrho*nT) = %.6f' % (rem / (nrho * nT)))
    # try grid-first blocks: maybe rho then T then value-blocks of size nT (T fastest) 
    if rem % nT == 0:
        print('  rem/nT = %d' % (rem // nT))
    if rem % nrho == 0:
        print('  rem/nrho = %d' % (rem // nrho))

for p in ['matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Gd/Gd100PLANCK',
          'matter++/mat_Gd/Gd20PLANCK',
          'matter++/CH/CHSi1_mopp',
          'matter++/CH/CHSi1_mopp100',
          'matter++/mat_Be-1.0/opbe',
          'matter++/mat_Au-1.0/Au100PLANCK']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        analyze(p)
