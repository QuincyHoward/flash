# -*- coding: utf-8 -*-
import re, sys, os, json, collections

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"

with open(DOC, encoding='utf-8') as f:
    text = f.read()
lines = text.split('\n')
print("=== BASELINE ===")
print("lines(split) =", len(lines))

# ---------- problem 1: chapter headings ----------
print("\n=== [P1] chapter headings with/without space ===")
for i, ln in enumerate(lines, 1):
    if re.match(r'^\s*#{1,4}\s*第\s*\d+\s*章', ln):
        print("%6d | %r" % (i, ln))
print("\n--- all lines containing 第 3 章 style WITH space (第 + space + digits + space + 章) ---")
pat_sp = re.compile(r'第\s+\d+\s+章')
c = 0
for i, ln in enumerate(lines, 1):
    for m in pat_sp.finditer(ln):
        c += 1
print("spaced occurrences:", c)
pat_nosp = re.compile(r'第\d+章')
print("nospace occurrences:", len(pat_nosp.findall(text)))
print("total 第N章 mentions:", len(re.findall(r'第\s*\d+\s*章', text)))
