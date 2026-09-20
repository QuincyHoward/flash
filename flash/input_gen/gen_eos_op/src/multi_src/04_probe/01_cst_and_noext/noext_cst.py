import os, re, collections

R = 'src/Multi1D++Portable20241128'
M = os.path.join(R, 'matter++')

noext = []
for dp, dn, fn in os.walk(M):
    for f in fn:
        if '.' not in f:
            noext.append(os.path.join(dp, f))

print('=== no-extension files: %d ===' % len(noext))

# classify by header line 0 pattern
kinds = collections.Counter()
detail = []
for p in noext:
    raw = open(p, 'rb').read(200)
    l0 = raw.split(b'\n')[0].decode('latin-1')
    m = re.match(r'^\s*(\d+)\s+(\w+)\s+(\w)', l0)
    if m:
        tbl, kind, mode = m.group(1), m.group(2), m.group(3)
        kinds[(kind, mode)] += 1
        detail.append((os.path.relpath(p, R).replace('\\', '/'), tbl, kind, mode, os.path.getsize(p)))
    else:
        kinds[('OTHER', l0[:20])] += 1
        detail.append((os.path.relpath(p, R).replace('\\', '/'), '?', 'OTHER', l0[:20], os.path.getsize(p)))

print('\n(kind, mode) histogram:')
for k, v in kinds.most_common():
    print('  %-22s %d' % (str(k), v))

print('\n=== all no-ext files ===')
for r, tbl, kind, mode, sz in sorted(detail):
    print('  %-52s tbl=%-9s %-10s %s  %d' % (r, tbl, kind, mode, sz))

# .CST survey
print('\n=== all *.CST / *.cst ===')
for dp, dn, fn in os.walk(M):
    for f in fn:
        if f.lower().endswith('.cst'):
            p = os.path.join(dp, f)
            raw = open(p, 'rb').read(300)
            l0 = raw.split(b'\n')[0]
            l1 = raw.replace(b'\r\n', b'\n').split(b'\n')[1] if b'\n' in raw else b''
            lang = 'DE' if b'Molek' in l1 else ('EN' if b'Particle' in l1 else '??')
            print('  %-44s %10d  %s | %s' % (os.path.relpath(p, R).replace('\\', '/'),
                  os.path.getsize(p), lang, l1[:60].decode('latin-1')))
