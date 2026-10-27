import os, re
root = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
p = os.path.join(root, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(p, encoding='utf-8').read()
L = txt.split('\n')
print('chars =', len(txt), ' lines =', len(L))
# find all headings
pat = re.compile(r'^(#{1,4})\s+(.*)$')
print('=== headings (level<=3) ===')
for i, l in enumerate(L):
    m = pat.match(l)
    if m and len(m.group(1)) <= 3:
        print(f'{i+1}\t{m.group(1)} {m.group(2)}')
