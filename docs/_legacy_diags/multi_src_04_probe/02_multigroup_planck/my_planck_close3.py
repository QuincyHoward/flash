import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def strip15(s):
    v = []
    for j in range(0, len(s) - 14, 15):
        seg = s[j:j+15]
        try:
            v.append(float(seg))
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
    tabno = hdr[0].strip()
    kind = hdr[1].strip()
    n1 = int(round(float(hdr[2])))
    n2 = int(round(float(hdr[3])))
    print('=' * 74)
    print(p)
    print('  table=%s  kind=%s  n1=%d  n2=%d' % (tabno, kind, n1, n2))
    print('  L1 nums =', strip15(l1))

    body = []
    for l in L[2:]:
        vals = strip15(l)
        body.extend(vals)
    nv = len(body)
    print('  body values = %d' % nv)
    print('  expected nr+nt+nr*nt = %d   leftover = %d' % (n1 + n2 + n1 * n2, nv - (n1 + n2 + n1 * n2)))

    # now verify orientation: rho block then T block
    if nv == n1 + n2 + n1 * n2:
        rho = body[:n1]
        T = body[n1:n1 + n2]
        vals = body[n1 + n2:]
        print('  rho[0..3] =', rho[:4])
        print('  rho[-3..] =', rho[-3:])
        print('  T[0..3]   =', T[:4])
        print('  T[-3..]   =', T[-3:])
        vm = min(vals)
        vx = max(vals)
        print('  values min=%.5f max=%.5f  (log10 range? %s)' % (vm, vx, 'YES' if -12 < vm and vx < 12 else 'NO'))
        # orientation test: compare variance along the two axes
        import statistics
        A = [vals[i * n2:(i + 1) * n2] for i in range(n1)]   # assume [i_rho][i_T]
        colvar = [statistics.pvariance([A[i][j] for i in range(n1)]) for j in range(n2)]
        rowvar = [statistics.pvariance(A[i]) for i in range(n1)]
        print('  mean within-column var (rho inner?) = %.4f' % (sum(colvar) / len(colvar)))
        print('  mean within-row    var (T   inner?) = %.4f' % (sum(rowvar) / len(rowvar)))
        # monotonic check of first row and first column
        print('  row0[0:6] =', ['%.3f' % x for x in A[0][:6]])
        print('  col0[0:6] =', ['%.3f' % A[i][0] for i in range(min(6, n1))])

for p in ['matter++/mat_Gd/Gd100PLANCK',
          'matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Au-1.0/Au100PLANCK',
          'matter++/CH/CHSi1_mopp100',
          'matter++/CH/CHSi1_mopp',
          'matter++/mat_Be-1.0/opbe',
          'matter++/mat_Gd/Gd20PLANCK']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        analyze(p)
    else:
        print('MISSING', p)
