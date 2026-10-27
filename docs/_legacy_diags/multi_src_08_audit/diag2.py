import re, os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
L = open(DOC, encoding='utf-8').read().split('\n')

print('=== 4.1.x headings ===')
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+4\.1(\.\d+)?\b', l):
        print('%6d  %s' % (i + 1, l[:100]))

print()
print('=== 表 T30 / T31 出现处 ===')
for i, l in enumerate(L):
    if re.search(r'表\s*T(30|31)\b', l):
        print('%6d  %s' % (i + 1, l[:130]))

print()
print('=== 所有 "**表 Tnn" 定义行 ===')
for i, l in enumerate(L):
    m = re.match(r'^\*\*表\s*T(\d+)', l.strip())
    if m:
        print('%6d  T%-3s %s' % (i + 1, m.group(1), l.strip()[:110]))

print()
print('=== "表 T6/T17..T22/T64" 是否真不存在 ===')
for n in [6, 17, 18, 19, 20, 21, 22, 64]:
    hits = [i + 1 for i, l in enumerate(L) if re.search(r'表\s*T%d\b' % n, l)]
    print('  T%-3d hits=%s' % (n, hits[:8]))
