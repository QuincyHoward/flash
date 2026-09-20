# -*- coding: utf-8 -*-
"""Find truly bare internal section refs like '见 §3.5' / '见 3.5 节' WITHOUT an owner prefix."""
import re
P = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md'
lines = open(P, encoding='utf-8', newline='').read().split('\n')
owners = ['FEOS', 'SESAME', 'Hyades', 'IONMIX', 'SNOP', 'LEDCOP', 'ATOMIC', 'MPQeos', 'Thermos']
# look for patterns that explicitly cite an internal section: 见 §3.5 / 见 3.5 节 / 详见 §3.6 etc.
pat = re.compile(r'(见|参见|详见|据|如)\s*§?\s*(3\.[5-9]|6\.[3-9]|[4-9]\.\d+|1[0-4]\.\d+)\s*(节)?')
hits = 0
for i, ln in enumerate(lines, 1):
    for m in pat.finditer(ln):
        # skip if the number is part of a longer dotted id (e.g. 9.3.5, 12.3)
        st = m.start(2)
        prev = ln[st-1] if st > 0 else ''
        nxt = ln[m.end(2)] if m.end(2) < len(ln) else ''
        if prev.isdigit() or prev == '.' or nxt.isdigit():
            continue
        ctx = ln[max(0, m.start()-50):m.end()+15]
        if any(o in ln[max(0, m.start()-40):m.end()] for o in owners):
            continue
        hits += 1
        print('L%-6d ...%s...' % (i, ctx))
print('TOTAL bare internal refs =', hits)
