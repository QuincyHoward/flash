import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def nums(s):
    """Split numeric line into as many 15-char fields as fit; spill into last."""
    v = []
    for j in range(0, len(s) - 14, 15):
        seg = s[j:j+15]
        v.append(float(seg))
    rem = s[(len(s) // 15) * 15:]
    if rem.strip():
        v.append(float(rem))
    return v

def analyze(p):
    L = [l for l in read(p) if l.strip()]
    l0, l1 = L[0], L[1]
    print('=' * 74)
    print(p)
    print('  header L0 = %r' % l0)
    print('  header L1 = %r' % l1)
    # positional split of header into 15-char columns
    hdr = [l0[j:j+15] for j in range(0, len(l0), 15)]
    print('  L0 cols15 =', [repr(x) for x in hdr])
    tail = nums(l0[30:])          # the two numbers after 'M'
    print('  numeric tail of L0 =', tail)
    n1, n2 = int(round(tail[0])), int(round(tail[1]))
    print('  n1=%d  n2=%d' % (n1, n2))
    print('  L1 nums =', nums(l1))

    data = L[2:]
    nv = sum(len(nums(l)) for l in data)
    print('  data lines=%d  values=%d' % (len(data), nv))
    for name, expr in [('nr+nt+nr*nt', n1 + n2 + n1 * n2),
                       ('1+nr+nt+nr*nt', 1 + n1 + n2 + n1 * n2),
                       ('2+nr+nt+nr*nt', 2 + n1 + n2 + n1 * n2),
                       ('nr+nt+2*nr*nt', n1 + n2 + 2 * n1 * n2)]:
        print('    %-16s = %-10d leftover %d' % (name, expr, nv - expr))

for p in ['matter++/mat_Gd/Gd100PLANCK',
          'matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Au-1.0/Au100PLANCK',
          'matter++/CH/CHSi1_mopp100',
          'matter++/CH/CHSi1_mopp',
          'matter++/mat_Be-1.0/opbe']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        analyze(p)
    else:
        print('MISSING', p)
