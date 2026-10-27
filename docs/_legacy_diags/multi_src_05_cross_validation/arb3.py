import os

R = 'src/Multi1D++Portable20241128'

def lines_of(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n') if l.strip()]

def nf(l):
    return len(l) // 15

def f15(l):
    return [float(l[j:j+15]) for j in range(0, (len(l)//15)*15, 15)]

# Decisive structural statement to test:
# GROUP = [2-value band line] + 111 lines = 446 values total
#   of which: 2 (band) + 444
# And 444 = 4 (per-group header?) + 440 (nr+nt+nr*nt)
# OR 444 = nr+nt+nr*nt + 4
# Let's look at the FIRST FOUR values after the band line of group 0 vs group 1.
p = 'matter++/mat_Au-1.0/AU_op03p'
L = lines_of(p)
L = [l for l in L if not any(k in l for k in ('PLANCK', 'ROSSELAND', 'EPS', 'ZEFF'))]
print('lines after dropping headers = %d' % len(L))
short = [i for i, l in enumerate(L) if len(l) == 30]

for k in range(4):
    s = short[k]
    band = f15(L[s])
    body = []
    e = short[k+1] if k+1 < len(short) else len(L)
    for l in L[s+1:e]:
        body.extend(f15(l))
    print('=== group %d: band=%s  body_values=%d ===' % (k, band, len(body)))
    print('  first 12 :', ['%.6g' % x for x in body[:12]])
    print('  next  4  :', ['%.6g' % x for x in body[12:16]])
    print('  last 6   :', ['%.6g' % x for x in body[-6:]])
    # position of the monotone rho run
    i = 0
    while i+1 < len(body) and body[i+1] > body[i]:
        i += 1
    print('  monotone increasing run length = %d (ends at idx %d)' % (i+1, i))
    j = i+1
    while j+1 < len(body) and body[j+1] > body[j]:
        j += 1
    print('  second run length = %d (idx %d..%d)' % (j-i, i+1, j))
    print('  leftover after 2 runs = %d' % (len(body) - (j+1)))
