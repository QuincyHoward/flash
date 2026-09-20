import re, os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
L = open(DOC, encoding='utf-8').read().split('\n')
print('lines', len(L))
# 打印 §15.12 之后所有 heading + 关键行
start = None
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+15\.12\b', l):
        start = i; break
for i in range(start, len(L)):
    l = L[i]
    if re.match(r'^#{1,4}\s', l):
        print('%6d  %s' % (i + 1, l[:100]))
