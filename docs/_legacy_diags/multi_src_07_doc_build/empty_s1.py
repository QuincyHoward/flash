# -*- coding: utf-8 -*-
import re
P = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md'
lines = open(P, encoding='utf-8', newline='').read().split('\n')
print('=== rows whose last cell is a bare [S-L1] ===')
for i, ln in enumerate(lines, 1):
    cells = [c.strip() for c in ln.strip().strip('|').split('|')] if ln.strip().startswith('|') else []
    if cells and cells[-1] in ('[S-L1]', '`[S-L1]`'):
        print('L%-6d %s' % (i, ln.strip()[:150]))
print()
print('=== bare [S-L4] rows ===')
for i, ln in enumerate(lines, 1):
    cells = [c.strip() for c in ln.strip().strip('|').split('|')] if ln.strip().startswith('|') else []
    if cells and cells[-1] in ('[S-L4]', '`[S-L4]`'):
        print('L%-6d %s' % (i, ln.strip()[:150]))
