import os, collections

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
print('header:', [x.strip() for x in hdr])
print('L1:', strip15(L[1]))
print('L2:', strip15(L[2]))
print()

# Walk line by line, print cumulative count, and look for monotone runs
# (rho block increasing, then T block increasing, then a 2D block)
body = []
owner = []   # (lineindex, col)
for li, l in enumerate(L[2:], start=2):
    for j, v in enumerate(strip15(l)):
        body.append(v); owner.append((li, j))
print('total values', len(body))

# find the longest strictly-increasing run from start (the rho grid)
n = len(body)
i = 0
while i + 1 < n and body[i + 1] is not None and body[i] is not None and body[i + 1] > body[i]:
    i += 1
print('strictly increasing run from start: %d values (index 0..%d)' % (i + 1, i))
print('  first 8:', body[:8])
print('  last 8 of run:', body[max(0, i - 7):i + 1])

# then check next block
s = i + 1
print('  value at %d = %r' % (s, body[s]))
j = s
while j + 1 < n and body[j + 1] is not None and body[j] is not None and body[j + 1] > body[j]:
    j += 1
print('second increasing run: %d values (from %d to %d)' % (j - s + 1, s, j))
print('  first 8:', body[s:s + 8])
print('  last 8:', body[max(s, j - 7):j + 1])
rem = n - (j + 1)
print('remaining after two runs: %d' % rem)

# does remaining factor nicely?
for a in range(2, 200):
    if rem % a == 0:
        b = rem // a
        if b <= 400:
            print('   rem %d = %d x %d' % (rem, a, b))
