import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def f15(s):
    v = []
    for j in range(0, len(s) - 14, 15):
        v.append(float(s[j:j+15]))
    rem = s[(len(s) // 15) * 15:]
    if rem.strip():
        v.append(float(rem))
    return v

def analyze(p):
    L = [l for l in read(p) if l.strip()]
    l0 = L[0]
    print('=' * 74)
    print(p)
    # parse header line 0: tableno, kind, 'M', n1, n2
    # positions: use 15-col chunks
    c = f15(l0)
    print('  L0 chunks(15) =', c)
    print('  L1 chunks(15) =', f15(L[1]))
    n1, n2 = c[-2], c[-1]
    print('  n1=%.0f n2=%.0f' % (n1, n2))
    data_lines = L[2:]
    nvals = 0
    for l in data_lines:
        nvals += len(f15(l))
    print('  data lines=%d  data values=%d' % (len(data_lines), nvals))
    print('  closure nr+nt+nr*nt : %.0f  (leftover %.0f)' % (n1+n2+n1*n2, nvals-(n1+n2+n1*n2)))
    print('  closure 1+nr+nt+nr*nt: %.0f  (leftover %.0f)' % (1+n1+n2+n1*n2, nvals-(1+n1+n2+n1*n2)))

for p in ['matter++/mat_Gd/Gd100PLANCK',
          'matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Au-1.0/Au100PLANCK',
          'matter++/CH/CHSi1_mopp100',
          'matter++/CH/CHSi1_mopp',
          'matter++/mat_Be-1.0/opbe']:
    if os.path.exists(os.path.join(R, p)):
        analyze(p)
    else:
        print('MISSING', p)
