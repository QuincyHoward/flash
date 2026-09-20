import os, re, collections, json

ROOT = 'src/Multi1D++Portable20241128'
M = os.path.join(ROOT, 'matter++')

# 1) full inventory
allfiles = []
for dp, dn, fn in os.walk(M):
    for f in fn:
        p = os.path.join(dp, f)
        try:
            sz = os.path.getsize(p)
        except OSError:
            sz = -1
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        allfiles.append((rel, sz))

print('=== matter++ TOTAL ===')
print('files', len(allfiles), 'bytes', sum(s for _, s in allfiles))
dirs = set(os.path.dirname(r) for r, _ in allfiles)
print('dirs with files', len(dirs))

# 2) suffix histogram (multi-suffix aware)
def suffixes(rel):
    b = os.path.basename(rel)
    parts = b.split('.')
    if len(parts) == 1:
        return ['(no-ext)']
    # collect all suffixes from right, but also full tail forms
    out = []
    for i in range(1, len(parts)):
        out.append('.' + '.'.join(parts[i:]))
    if b.startswith('.') or (len(parts) >= 2 and parts[0] == ''):
        out.append(b)
    return out

last = collections.Counter()
for r, _ in allfiles:
    b = os.path.basename(r)
    if b.startswith('.'):
        last[b] += 1
    elif '.' in b:
        last['.' + b.rsplit('.', 1)[1]] += 1
    else:
        last['(no-ext)'] += 1

print('\n=== LAST-SUFFIX HISTOGRAM (n=%d) ===' % len(last))
for k, v in last.most_common():
    print('%-24s %5d' % (k, v))

# 3) bytes per last suffix
byb = collections.Counter()
for r, s in allfiles:
    b = os.path.basename(r)
    if b.startswith('.'):
        k = b
    elif '.' in b:
        k = '.' + b.rsplit('.', 1)[1]
    else:
        k = '(no-ext)'
    byb[k] += s

print('\n=== BYTES PER SUFFIX (top 40) ===')
for k, v in byb.most_common(40):
    print('%-24s %14d' % (k, v))

json.dump({'n_files': len(allfiles), 'n_bytes': sum(s for _, s in allfiles),
           'suffix': {k: v for k, v in last.items()},
           'suffix_bytes': {k: v for k, v in byb.items()}},
          open('.workbuddy/tmp/inv_matter.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nwrote inv_matter.json')
