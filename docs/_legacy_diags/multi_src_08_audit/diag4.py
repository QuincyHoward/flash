import re, os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
L = open(DOC, encoding='utf-8').read().split('\n')

print('=== L6414-6424 ===')
for i in range(6413, 6425):
    print('%6d | %s' % (i + 1, L[i]))

print()
print('=== 所有 "§3.5.2" 出现处（含上下文 70） ===')
for i, l in enumerate(L):
    for m in re.finditer(r'§\s*3\.5\.2', l):
        a = max(0, m.start() - 80)
        print('%6d | ...%s...' % (i + 1, l[a:m.end() + 30]))
