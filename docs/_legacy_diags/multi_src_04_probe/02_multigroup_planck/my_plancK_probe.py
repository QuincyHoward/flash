import os, re, math

R = 'src/Multi1D++Portable20241128'

def tokens(p, maxlines=None):
    """Read a MULTI-opacity-style file, strip CRLF, split every line into
    15-char fields, tolerate overflow into the last field (60 vs 64)."""
    raw = open(p, 'rb').read().replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    lines = [l for l in raw.split(b'\n')]
    out = []
    for i, l in enumerate(lines):
        if maxlines is not None and i >= maxlines:
            break
        s = l.decode('latin-1')
        out.append(s)
    return out

def fields15(s):
    """Split a numeric line into 15-char fields; remainder spills into last."""
    vals = []
    for j in range(0, len(s) - 14, 15):
        seg = s[j:j+15]
        try:
            vals.append(float(seg))
        except ValueError:
            return None
    rem = s[(len(s) // 15) * 15:]
    if rem.strip():
        try:
            vals.append(float(rem))
        except ValueError:
            return None
    return vals

def probe(p, label):
    fp = os.path.join(R, p)
    if not os.path.exists(fp):
        print('  MISSING', p); return
    sz = os.path.getsize(fp)
    L = tokens(fp)
    print('=' * 74)
    print('%s   %s  (%d B, %d lines)' % (label, p, sz, len(L)))
    for i in range(min(3, len(L))):
        print('  L%-2d len=%-4d %r' % (i, len(L[i]), L[i][:100]))
    # last lines too - check for header-at-end
    for i in range(max(0, len(L) - 3), len(L)):
        print('  L%-2d len=%-4d %r' % (i, len(L[i]), L[i][:100]))
    # width histogram
    import collections
    h = collections.Counter(len(l) for l in L if l.strip())
    print('  width hist:', dict(h.most_common(6)))
    return L

print('############ GROUP: bare-name PLANCK family ############')
probe('matter++/mat_Gd/Gd100PLANCK', 'A1')
probe('matter++/mat_Au-1.0/AU_op03p', 'A2 (136040 B)')
probe('matter++/CH/CHSi1_mopp100', 'A3')

print()
print('############ reference .PLANCK ############')
probe('matter++/mat_Gd/Gd100.PLANCK', 'REF')
