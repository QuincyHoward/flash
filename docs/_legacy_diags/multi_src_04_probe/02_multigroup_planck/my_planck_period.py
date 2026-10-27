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

body = []
for l in L[2:]:
    body.extend(strip15(l))
print('nrho=%d nT=%d total=%d' % (nrho, nT, len(body)))

# the 2D data starts at index nrho+nT=40
D = body[nrho + nT:]
print('2D block length = %d' % len(D))

# Find where a "reset to minimum" occurs: compute local minima positions
mins = []
for i in range(1, len(D) - 1):
    if None in (D[i-1],D[i],D[i+1]): continue
    if D[i] < D[i - 1] and D[i] <= D[i + 1] and D[i] < D[i - 1] - 0.5:
        mins.append(i)
print('large dip positions (first 40):', mins[:40])
if len(mins) > 2:
    diffs = [mins[i + 1] - mins[i] for i in range(len(mins) - 1)]
    import collections
    print('dip spacing hist:', collections.Counter(diffs).most_common(10))

# alternative: test whether D can be cut into equal chunks k where each chunk
# starts with a small value. Try k in divisors of len(D)
print('\nchunk size candidates (len %d):' % len(D))
for k in range(2, 5000):
    if len(D) % k == 0:
        chunks = len(D) // k
        if chunks > 2 and chunks < 400:
            starts = [D[i * k] for i in range(chunks)]
            # score: how often chunk start is a local min relative to chunk body
            good = sum(1 for i in range(chunks) if None not in D[i*k:(i+1)*k] and starts[i] is not None and starts[i] <= min(D[i * k:(i + 1) * k]) + 1e-9)
            if good > chunks * 0.7:
                print('  k=%-6d chunks=%-5d starts_are_min=%d/%d' % (k, chunks, good, chunks))
