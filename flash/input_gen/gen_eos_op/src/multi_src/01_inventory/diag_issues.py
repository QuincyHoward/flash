# -*- coding: utf-8 -*-
import os, re, collections
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(DOC, encoding='utf-8').read()
L = txt.split('\n')

print('=== §15.x headings with line numbers ===')
for i, l in enumerate(L):
    if re.match(r'^#{3,4}\s+15\.\d+', l):
        print(i + 1, l[:90])

print()
print('=== broken refs: context ===')
targets = ['§0.1', '§1.1', '§1.2', '§1.4', '§16.1', '§16.2', '§16.3', '§2.3', '§2.4',
           '§23.5.6', '§3.5.2', '§3.6.1', '§3.6.10', '§3.6.6', '§3.6.8', '§3.6.9',
           '§3.7', '§6.4']
for t in targets:
    print('---', t)
    for i, l in enumerate(L):
        if t in l:
            # print surrounding ~120 chars
            for m in re.finditer(re.escape(t), l):
                a = max(0, m.start() - 90)
                b = min(len(l), m.end() + 60)
                print('   L%d: ...%s...' % (i + 1, l[a:b]))
            break

print()
print('=== A_eff strings present ===')
for i, l in enumerate(L):
    if '141.13' in l or 'A_eff' in l or 'Atot' in l:
        print('   L%d: %s' % (i + 1, l[:170]))
