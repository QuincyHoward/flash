# -*- coding: utf-8 -*-
"""P1 fix: normalize chapter references 第 N 章 -> 第N章 (remove spaces around digits)."""
import re, shutil, os, sys

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
BAK = DOC + ".bak"

with open(DOC, encoding='utf-8') as f:
    text = f.read()

if not os.path.exists(BAK):
    shutil.copy2(DOC, BAK)
    print("backup written:", BAK)
else:
    print("backup already exists, skipping:", BAK)

pat = re.compile(r'第\s+(\d+)\s+章')
n = len(pat.findall(text))
new = pat.sub(lambda m: '第%s章' % m.group(1), text)

# fallback: 第 N章 / 第N 章  (already covered by above since \s* both sides)
print("replacements made:", n)

with open(DOC, 'w', encoding='utf-8', newline='\n') as f:
    f.write(new)
print("written.")
