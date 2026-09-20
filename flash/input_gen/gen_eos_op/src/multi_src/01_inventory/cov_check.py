import re, json, os

p = 'src/multi_docs/MultiEOSOP格式说明.md'
t = open(p, encoding='utf-8').read()

inv = json.load(open('.workbuddy/tmp/inv_matter.json', encoding='utf-8'))
suf = inv['suffix']

# normalize: the doc may mention suffix with different case / without dot / as name
def mentioned(s):
    name = s.lstrip('.')
    pats = [s, name]
    for q in pats:
        if not q:
            continue
        if q in t:
            return True
    return False

rows = []
for s, n in sorted(suf.items(), key=lambda kv: -kv[1]):
    rows.append((s, n, mentioned(s)))

print('=== SUFFIX COVERAGE IN DOC (n=%d) ===' % len(rows))
miss = []
for s, n, m in rows:
    flag = 'OK ' if m else 'MISS'
    print('%-30s %5d  %s' % (s, n, flag))
    if not m:
        miss.append((s, n))

print('\n=== NOT MENTIONED (%d) ===' % len(miss))
for s, n in miss:
    print('%-30s %5d' % (s, n))

# also check the doc's own claim lists
print('\n=== doc self-claims ===')
for kw in ['76 种', '73 种', '72 种', '全部已解', '无未解', '未解后缀']:
    print('%-12s %d' % (kw, t.count(kw)))
