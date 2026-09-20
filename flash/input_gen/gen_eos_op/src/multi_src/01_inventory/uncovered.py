import os, collections, json

M = 'src/Multi1D++Portable20241128/matter++'

targets = {'(no-ext)': None, '.gif': None, '.js': None, '.bak': None, '.html': None, '.CST': None}
buckets = collections.defaultdict(list)

for dp, dn, fn in os.walk(M):
    for f in fn:
        p = os.path.join(dp, f)
        b = os.path.basename(f)
        if b.startswith('.'):
            k = b
        elif '.' in b:
            k = '.' + b.rsplit('.', 1)[1]
        else:
            k = '(no-ext)'
        if k in targets:
            buckets[k].append((os.path.relpath(p, 'src/Multi1D++Portable20241128').replace('\\', '/'),
                               os.path.getsize(p)))

for k, lst in buckets.items():
    print('=' * 70)
    print('%s  n=%d' % (k, len(lst)))
    exts = collections.Counter(os.path.splitext(x[0])[1].lower() for x in lst)
    print('  inner-ext hist:', dict(exts.most_common(12)))
    # distinct parent dirs
    pdirs = collections.Counter(os.path.dirname(x[0]) for x in lst)
    print('  top dirs:', [d for d, _ in pdirs.most_common(8)])
    for r, s in sorted(lst, key=lambda z: -z[1])[:8]:
        print('   %12d  %s' % (s, r))
    print()
