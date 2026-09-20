import os

R = 'src/Multi1D++Portable20241128'

def read(p):
    raw = open(os.path.join(R, p), 'rb').read().replace(b'\r\n', b'\n')
    return [l.decode('latin-1') for l in raw.split(b'\n')]

def strip15(s):
    v = []
    for j in range(0, len(s) - 14, 15):
        try:
            v.append(float(s[j:j+15]))
        except ValueError:
            v.append(None)
    rem = s[(len(s) // 15) * 15:]
    if rem.strip():
        try:
            v.append(float(rem))
        except ValueError:
            v.append(None)
    return v

p = 'matter++/mat_Au-1.0/AU_op03p'
L = [l for l in read(p) if l.strip()]
hdr = [L[0][j:j+15] for j in range(0, 60, 15)]
nrho, nT = int(round(float(hdr[2]))), int(round(float(hdr[3])))
print('nrho=%d nT=%d' % (nrho, nT))

# Show lines 2..10 and structural positions
print('\n--- first 12 lines ---')
for i in range(min(12, len(L))):
    print('L%-3d %r' % (i, L[i][:75]))

# Where does the 2D data start? after 40 values = 10 lines
print('\n--- lines 10..24 (data start) ---')
for i in range(9, min(25, len(L))):
    print('L%-3d %r' % (i, L[i][:75]))

# Now: hypothesis - each group is a header line + nrho*nT values
# test group sizes
body_vals_per_line = 4
start = 2 + 10   # header lines occupy first 40 values = 10 lines
print('\n2D starts at line', start)

# try: for various values per group, see where a line has anomalous content
n = nrho * nT
rem = sum(len(strip15(l)) for l in L[2:]) - nrho - nT
print('rem=%d' % rem)
for g in [1,2,3,5,10,20,22,25,50,100,105,106]:
    tot = g * n
    print('  g=%-4d g*n=%d  vs rem=%d  diff=%d' % (g, tot, rem, rem - tot))

# maybe the count includes nrho+nt per GROUP? i.e. g*(nrho+nt+nrho*nt)
for g in range(1, 200):
    if rem == g * (nrho + nT + nrho * nT):
        print('  *** rem == %d * (nrho+nT+nrho*nT) ***' % g)
# maybe g*nrho*nT + (g-1)*something
for g in range(1, 200):
    d = rem - g * n
    if d >= 0 and d % max(1, (g - 1)) == 0 and g > 1 and (d // (g - 1)) < 30:
        print('  g=%-4d g*n=%-7d extra=%-6d extra/(g-1)=%.2f' % (g, g * n, d, d / (g - 1)))
