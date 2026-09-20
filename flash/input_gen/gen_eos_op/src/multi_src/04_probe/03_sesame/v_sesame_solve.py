import os, re

M = 'src/Multi1D++Portable20241128/matter++/'
tok = re.compile(rb'[+-]?\d*\.?\d+(?:[EeDd][+-]?\d+)?')

files = []
for dp, dn, fn in os.walk(M):
    for f in fn:
        if f.lower().endswith(('.sesame', '.sesame_')) and not f.lower().endswith(('planck', 'rosseland')):
            files.append(os.path.join(dp, f))

print('%-46s %9s %7s %7s %9s %s' % ('file', 'tokens', 'nr', 'ne', 'expect', 'verdict'))
for p in sorted(files):
    raw = open(p, 'rb').read()
    t = [float(x) for x in tok.findall(raw)]
    n = len(t)
    # candidate formulae
    nr = ne = None
    # try: n = 4 + 2*nr + ne + 2*nr*ne  (with sentinel counted among the 4 header)
    # solve for integer nr, ne
    sols = []
    for a in range(1, 400):
        # n - 4 - 2a = ne(1 + 2a)  -> ne = (n-4-2a)/(1+2a)
        num = n - 4 - 2 * a
        den = 1 + 2 * a
        if num > 0 and num % den == 0:
            sols.append((a, num // den))
    for a in range(1, 400):
        # n = 5 + 2*nr + ne + 2*nr*ne   (sentinel extra)
        num = n - 5 - 2 * a
        den = 1 + 2 * a
        if num > 0 and num % den == 0:
            sols.append((a, num // den, 'sentinel-aligned'))
    name = os.path.relpath(p, M)
    print('%-46s %9d %7s %7s %9s' % (name, n, '-', '-', '-'), sols[:4])
