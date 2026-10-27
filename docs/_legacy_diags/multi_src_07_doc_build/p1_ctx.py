# -*- coding: utf-8 -*-
import re, sys

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
with open(DOC, encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')

pat_sp = re.compile(r'第\s+\d+\s+章')
print("=== ALL spaced 第 N 章 occurrences w/ context ===")
for i, ln in enumerate(lines, 1):
    if pat_sp.search(ln):
        # find all
        for m in pat_sp.finditer(ln):
            a = max(0, m.start()-28); b = min(len(ln), m.end()+28)
            print("%6d | %s" % (i, ln[a:b].replace('\t',' ')))
