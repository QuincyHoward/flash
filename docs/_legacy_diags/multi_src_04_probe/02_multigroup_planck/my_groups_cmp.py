import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def f15(l):
    return [float(l[j:j+15]) for j in range(0, (len(l) // 15) * 15, 15)]

def groups_of(p):
    L = [l for l in read(p) if l.strip()]
    nr = int(round(float(L[0][30:45])))
    nt = int(round(float(L[0][45:60])))
    G = []
    cur = None
    for i, l in enumerate(L):
        if i == 0:
            continue
        if any(k in l for k in ('PLANCK', 'ROSSELAND', 'EPS', 'ZEFF')):
            continue
        if len(l) == 30:
            if cur is not None:
                G.append(cur)
            cur = {'band': f15(l), 'lines': []}
        elif cur is not None:
            cur['lines'].append(l)
    if cur is not None:
        G.append(cur)
    return L, nr, nt, G

# Also compare Gd20 vs Gd100: are the first groups identical? (same grid, more bands)
for p in ['matter++/mat_Gd/Gd20PLANCK', 'matter++/mat_Gd/Gd100PLANCK']:
    L, nr, nt, G = groups_of(p)
    print('%s nr=%d nt=%d groups=%d' % (p, nr, nt, len(G)))
    # first band list
    print('  first 8 bands:', [b[0] for b in (g['band'] for g in G)][:8])

print()
# check the CHSi1_mopp (20 groups) vs mopp100 (100 groups) grids
for p in ['matter++/CH/CHSi1_mopp', 'matter++/CH/CHSi1_mopp100']:
    L, nr, nt, G = groups_of(p)
    print('%s nr=%d nt=%d groups=%d' % (p, nr, nt, len(G)))

print()
# Confirm: table number vs kind for all bare PLANCK/ROSS/EPS files
import collections
pat = collections.defaultdict(list)
for dp, dn, fn in os.walk(os.path.join(R, 'matter++')):
    for f in fn:
        fp = os.path.join(dp, f)
        if '.' in f:
            continue
        try:
            raw = open(fp, 'rb').read(80)
        except OSError:
            continue
        l0 = raw.split(b'\n')[0].decode('latin-1')
        j = l0.find('PLANCK')
        k = l0.find('ROSSELAND')
        e = l0.find('EPS ')
        if j < 0 and k < 0 and e < 0:
            continue
        kind = 'PLANCK' if j >= 0 else ('ROSSELAND' if k >= 0 else 'EPS')
        tab = l0[:15].strip()
        pat[kind].append((f, tab))
for kind, lst in pat.items():
    print('%-10s n=%d' % (kind, len(lst)))
    for f, tab in sorted(lst)[:6]:
        print('    %-28s table=%s' % (f, tab))
