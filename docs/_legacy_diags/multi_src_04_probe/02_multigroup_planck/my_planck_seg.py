import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

p = 'matter++/mat_Au-1.0/AU_op03p'
L = [l for l in read(p) if l.strip()]
print('line0 (header): %r' % L[0])
print('line1 (short):  %r' % L[1])
print('line2..:        %r' % L[2][:70])
print()

# 20 short lines at 1,113,225,...  -> spacing 112
# So structure repeats every 112 lines starting at line 1.
# Segment 1 = lines[1:113] = 112 lines: 1 short(2 vals) + 111 lines*4 = 2+444=446 vals
seg = L[1:113]
nv = sum(len(l) // 15 for l in seg)
print('segment length lines=%d, values=%d' % (len(seg), nv))
print('  first line of segment: %r' % seg[0])
print('  second line: %r' % seg[1][:70])
print('  last line  : %r' % seg[-1][:70])

# how many segments
segs = []
i = 1
while i < len(L):
    j = min(i + 112, len(L))
    segs.append(L[i:j])
    i = j
print('\nnumber of segments =', len(segs))
for k, s in enumerate(segs[:4]):
    nvk = sum(len(l) // 15 for l in s)
    print('  seg%d: lines=%d values=%d  head=%r' % (k, len(s), nvk, s[0]))

# check all segments same size
sizes = set(sum(len(l) // 15 for l in s) for s in segs)
print('distinct segment value-counts:', sizes)

# 30 lines appear at index 1,113,... i.e. every 112. nrho=20,nT=20
nr, nt = 20, 20
print()
print('nr=%d nt=%d' % (nr, nt))
print('hypothesis: each segment = 1 group; segment has 2 (short-line) + ? ')
print('  values per segment =', list(sizes))
# 446 vals per segment. try nr+nt+? 
for extra in range(0, 460):
    if 2 + extra == 446:
        pass
print('  446 - 2 =', 446 - 2)
print('  446 / 20 =', 446 / 20)
print('  (446-2)/20 =', (446 - 2) / 20)
