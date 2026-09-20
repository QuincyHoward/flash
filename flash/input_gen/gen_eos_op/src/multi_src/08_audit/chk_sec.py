# -*- coding: utf-8 -*-
import re
P = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md'
lines = open(P, encoding='utf-8', newline='').read().split('\n')
pat = re.compile(r'§?\s*(3\.[567]|6\.4)\b')
for i, ln in enumerate(lines, 1):
    for m in pat.finditer(ln):
        s = max(0, m.start() - 60)
        ctx = ln[s:m.end() + 20]
        print('L%-6d [%s]  ...%s...' % (i, m.group(1), ctx))
