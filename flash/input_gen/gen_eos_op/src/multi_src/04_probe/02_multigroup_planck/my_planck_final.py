import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def f15(l):
    return [float(l[j:j+15]) for j in range(0, (len(l) // 15) * 15, 15)]

def analyze(p):
    L = [l for l in read(p) if l.strip()]
    nr = int(round(float(L[0][30:45])))
    nt = int(round(float(L[0][45:60])))
    tabno = L[0][0:15].strip()
    kind = L[0][15:30].strip()
    print('=' * 78)
    print('%s  table=%s kind=%s nr=%d nt=%d' % (p, tabno, kind, nr, nt))

    # split into groups at every short (30-char) line
    groups = []
    cur = None
    for i, l in enumerate(L):
        if i == 0:
            continue                      # the file-level header line
        if ('PLANCK' in l) or ('ROSSELAND' in l) or ('EPS' in l) or ('ZEFF' in l):
            continue                      # any repeated file-level header
        if len(l) == 30:
            if cur is not None:
                groups.append(cur)
            cur = {'hdr_line': l, 'lines': []}
        elif cur is not None:
            cur['lines'].append(l)
    if cur is not None:
        groups.append(cur)

    print('  groups found (by 30-char separators) = %d' % len(groups))
    expect = nr + nt + nr * nt
    ok = 0
    for k, g in enumerate(groups):
        vals = []
        for l in g['lines']:
            vals.extend(f15(l))
        band = f15(g['hdr_line'])
        status = 'OK' if len(vals) == expect else 'MISMATCH(%d)' % len(vals)
        if len(vals) == expect:
            ok += 1
        if k < 6 or status != 'OK':
            print('    grp%-3d band=%s  vals=%d  %s' % (k, ['%.4g' % x for x in band], len(vals), status))
    print('  groups closing at nr+nt+nr*nt = %d/%d' % (ok, len(groups)))

for p in ['matter++/mat_Au-1.0/AU_op03p',
          'matter++/mat_Gd/Gd20PLANCK',
          'matter++/mat_Gd/Gd100PLANCK',
          'matter++/CH/CHSi1_mopp',
          'matter++/mat_Be-1.0/opbe',
          'matter++/CH/CHSi1_mopp100']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        analyze(p)
