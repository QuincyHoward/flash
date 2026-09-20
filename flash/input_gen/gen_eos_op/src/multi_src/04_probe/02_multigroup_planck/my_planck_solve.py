import os, math, statistics

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
    l0, l1 = L[0], L[1]
    hdr = [l0[j:j+15] for j in range(0, len(l0), 15)]
    tabno, kind = hdr[0].strip(), hdr[1].strip()
    n1, n2 = int(round(float(hdr[2]))), int(round(float(hdr[3])))
    body = []
    for l in L[2:]:
        body.extend(strip15(l))
    nv = len(body)
    print('=' * 74)
    print('%s' % p)
    print('  table=%s kind=%s  hdr n1=%d n2=%d  body=%d' % (tabno, kind, n1, n2, nv))
    print('  nv/n1=%.4f  nv/n2=%.4f  nv/(n1*n2)=%.4f' % (nv / n1, nv / n2, nv / (n1 * n2)))

    # try: the header two numbers are LOG10 ranges (rho: 1.0 .. 2.8 => 10^1..10^2.8)
    # hypothesis: values are grouped as [rho_block][T_block][2D], with rho/T counts
    # derived from the file. Test simple block splits:
    for nrho in [n1, n2, 20, 30, 43, 50, 42]:
        for nT in [n1, n2, 20, 30, 43, 50, 42]:
            if nrho + nT + nrho * nT == nv:
                print('  *** CLOSED: nrho=%d nT=%d  (%d+%d+%d) ***' % (nrho, nT, nrho + nT, nrho * nT, nrho * nT))
    # detect by scanning a range
    found = []
    for nrho in range(2, 400):
        if (nv - nrho) > 0 and (nv - nrho) % (nrho + 1) == 0:
            nt = (nv - nrho) // (nrho + 1)
            if 2 <= nt <= 400:
                found.append((nrho, nt))
    print('  candidate (nrho,nT) with nv = nrho+nT+nrho*nT :', found[:12])

for p in ['matter++/mat_Gd/Gd100PLANCK',
          'matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Au-1.0/Au100PLANCK',
          'matter++/CH/CHSi1_mopp100',
          'matter++/mat_Be-1.0/opbe',
          'matter++/mat_Gd/Gd20PLANCK']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        analyze(p)
