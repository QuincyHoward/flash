import os

R = 'src/Multi1D++Portable20241128'

def lines_of(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n') if l.strip()]

def nf(l):
    return len(l) // 15

# Group boundary = the 2-value (30-char) line.
# Between consecutive 2-value lines there are exactly 112 lines incl. the leading one.
p = 'matter++/mat_Au-1.0/AU_op03p'
L = lines_of(p)
nr = nt = 20
expect = nr + nt + nr * nt          # 440
print('expect per group = %d' % expect)

short = [i for i, l in enumerate(L) if len(l) == 30]
print('2-value lines at:', short)

# Method A: cutting between 2-value lines
segs = []
for k, s in enumerate(short):
    e = short[k + 1] if k + 1 < len(short) else len(L)
    segs.append(L[s:e])
print('\nMethod A: %d segments (from each 2-value line to next)' % len(segs))
for k, s in enumerate(segs[:4]):
    nv = sum(nf(x) for x in s)
    print('  seg%-2d lines=%-4d first=%r  values=%d  (excl. band line: %d)' % (
        k, len(s), s[0][:32], nv, nv - 2))

# Method B: group = band line + data up to (and including) just before next band line
segs2 = []
for k, s in enumerate(short):
    e = short[k + 1] if k + 1 < len(short) else len(L)
    body = L[s + 1:e]
    segs2.append(body)
print('\nMethod B: data-only per group')
ok = 0
for k, b in enumerate(segs2):
    nv = sum(nf(x) for x in b)
    if nv == expect:
        ok += 1
    if k < 3 or nv != expect:
        print('  grp%-2d lines=%-4d values=%d %s' % (k, len(b), nv, 'OK' if nv == expect else 'BAD'))
print('closing at %d = %d/%d' % (expect, ok, len(segs2)))

# the last group: does it terminate at EOF?
print('\nlast segment lines=%d values=%d' % (len(segs2[-1]), sum(nf(x) for x in segs2[-1])))
