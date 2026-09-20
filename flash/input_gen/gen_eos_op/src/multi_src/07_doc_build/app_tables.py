# -*- coding: utf-8 -*-
import re
P = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md'
lines = open(P, encoding='utf-8', newline='').read().split('\n')
ts = set()
for ln in lines:
    for m in re.finditer(r'\bT(\d{1,2})\b', ln):
        ts.add(int(m.group(1)))
print('T numbers used:', sorted(ts))
print('max =', max(ts), ' missing =', [n for n in range(0, max(ts)+1) if n not in ts])
print()
# appendix section boundaries
apps = []
for i, ln in enumerate(lines, 1):
    if re.match(r'^## 附录 [A-F]\b', ln):
        apps.append((i, ln.strip()))
    if ln.startswith('## 附录') or re.match(r'^# ', ln):
        pass
for i, t in apps:
    print('L%-6d %s' % (i, t))
# find end
for i, ln in enumerate(lines, 1):
    if re.match(r'^## 附录 [A-F]\b', ln) or ln.startswith('## '):
        pass
print()
print('total lines', len(lines))
# list tables in appendices
inapp = False
for i, ln in enumerate(lines, 1):
    if re.match(r'^# 附录\b', ln) or re.match(r'^## 附录\b', ln):
        inapp = True
        print('>>> APPENDIX START L%d: %s' % (i, ln.strip()))
    if inapp and ln.strip().startswith('|') and not ln.strip().startswith('|---'):
        # heading row = first of a block
        prev = lines[i-2] if i >= 2 else ''
        if not prev.strip().startswith('|'):
            print('   table starts L%-6d %s' % (i, ln.strip()[:90]))
