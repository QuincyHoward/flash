import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def f15_exact(s):
    """Return list of 15-char fields, flagging the residual."""
    vals = []
    for j in range(0, len(s) - 14, 15):
        vals.append(s[j:j+15])
    res = s[(len(s) // 15) * 15:]
    return vals, res

# Re-examine the true line structure: maybe lines are NOT all 4x15.
# The .PLANCK files: check whether some lines carry only 2 values (the header-ish rows)
p = 'matter++/mat_Au-1.0/AU_op03p'
L = [l for l in read(p) if l.strip()]
print('total nonblank lines', len(L))
# count values per line by splitting on sign boundaries is unreliable;
# instead measure line length distribution
import collections
h = collections.Counter(len(l) for l in L)
print('length hist:', dict(h.most_common(8)))

# Identify lines whose length is 30 (2 fields) - these are the "grid" separator lines
short = [i for i, l in enumerate(L) if len(l) == 30]
print('lines with length 30 (count=%d):' % len(short), short[:20])
mid = [i for i, l in enumerate(L) if len(l) not in (30, 60)]
print('lines with other lengths:', [(i, len(L[i])) for i in mid[:20]])

# So: line0 = header(60), line1..k = grid lines (mix of 60 and 30),
# then data lines all 60. Count values properly.
tot = 0
for l in L:
    n = len(l) // 15
    tot += n
print('total 15-char fields across all lines =', tot)
print('header says nr=%s nt=%s' % (L[0][30:45].strip(), L[0][45:60].strip()))
nr = int(float(L[0][30:45])); nt = int(float(L[0][45:60]))
print('nr=%d nt=%d  nr+nt=%d  nr+nt+nr*nt=%d' % (nr, nt, nr + nt, nr + nt + nr * nt))
print('actual total fields = %d' % tot)
print('leftover vs 1+nr+nt+nr*nt = %d' % (tot - (1 + nr + nt + nr * nt)))
print('leftover vs nr+nt+nr*nt   = %d' % (tot - (nr + nt + nr * nt)))
