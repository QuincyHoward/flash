import os

R = 'src/Multi1D++Portable20241128'

def lines_of(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n') if l.strip()]

# Decisive test on AU_op03p: 2240 lines total, 20 short(30-char) lines.
# Claim X (mine): each group = 30-char band line + data lines (nr+nt+nr*nt vals)
# Claim Y (probe-noext): each block = [id,LABEL,h_lo,h_hi] + [rho_first, T_last] + grids + kappa
p = 'matter++/mat_Au-1.0/AU_op03p'
L = lines_of(p)
print('lines=%d' % len(L))
for i in range(0, 16):
    print('  L%-3d len=%-3d %r' % (i, len(L[i]), L[i][:90]))
print('  ...')
for i in range(len(L) - 4, len(L)):
    print('  L%-3d len=%-3d %r' % (i, len(L[i]), L[i][:90]))

# Count line-length pattern
import collections
print('\nlength hist:', collections.Counter(len(l) for l in L).most_common())
# find positions of 30-char lines
short = [i for i, l in enumerate(L) if len(l) == 30]
print('30-char lines at:', short[:8], '... total', len(short))
# spacing
print('spacings:', [short[i+1]-short[i] for i in range(min(5, len(short)-1))])

# now the key: examine the FIRST group region in detail line by line
print('\n--- lines 0..14 with 15-char field dump ---')
for i in range(0, 15):
    l = L[i]
    fs = [l[j:j+15] for j in range(0, (len(l)//15)*15, 15)]
    print('  L%-3d %s' % (i, [x.strip() for x in fs]))
