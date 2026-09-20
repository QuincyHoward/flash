import re, os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
L = open(DOC, encoding='utf-8').read().split('\n')

for n in [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 35, 36, 64]:
    hits = [(i + 1, L[i].strip()[:110]) for i, l in enumerate(L)
            if re.search(r'表\s*T%d(?![0-9])' % n, l)]
    print('### T%d  (%d hits)' % (n, len(hits)))
    for ln, s in hits[:8]:
        print('   %6d  %s' % (ln, s))
    print()

print('=' * 70)
print('§13 区间内对 T30/T31 的引用 (L8100-8350)')
for i in range(8099, min(8350, len(L))):
    if re.search(r'表\s*T(30|31)', L[i]):
        print('   %6d  %s' % (i + 1, L[i].strip()[:150]))

print()
print('=' * 70)
print('全文所有 "表 T30" / "表 T31" 引用行')
for i, l in enumerate(L):
    if re.search(r'表\s*T(30|31)(?![0-9])', l):
        print('   %6d  %s' % (i + 1, l.strip()[:150]))
