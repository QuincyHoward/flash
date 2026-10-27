# -*- coding: utf-8 -*-
import re, os, collections, json, io, sys

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
OUT = BASE + "/.workbuddy/tmp/audit_raw.txt"

with open(DOC, encoding='utf-8') as f:
    text = f.read()
LINES = text.split('\n')
buf = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    buf.append(s)

# ================= AUDIT A =================
P("="*30, "AUDIT A: provenance tags", "="*30)
tags = ['S-L1','S-L2','S-L3','S-L4','S-UNK','S-WEB','S-IMG']
cnt = {}
for t in tags:
    cnt[t] = len(re.findall(r'\[' + t + r'\]', text))
for t in tags:
    P("  [%s] = %d" % (t, cnt[t]))
P("  total tag mentions = %d" % sum(cnt.values()))

# A: find tag occurrences without expected payload
P("\n-- A1: [S-L1] occurrences, flag ones lacking 手册/文档名 or §/节 --")
n_l1_bad = 0
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'\[S-L1\]', ln):
        a = max(0, m.start()-90); b = min(len(ln), m.end()+90)
        seg = ln[a:b]
        has_doc = bool(re.search(r'(MANUAL|Manual|manual|README|Readme|Readme\.txt|\.pdf|\.docx?|\.txt|文档|手册|手册名|Section|§|附录)', seg))
        has_sec = bool(re.search(r'(§|节|Section|Sec\.|附录|第\s*\d+|\d+\.\d+)', seg))
        if not (has_doc and has_sec):
            n_l1_bad += 1
            P("   L%-6d [doc=%d sec=%d] %s" % (i, has_doc, has_sec, seg.replace('\n',' ')))
P("  [S-L1] lacking doc-or-section context: %d" % n_l1_bad)

P("\n-- A2: [S-L2] occurrences lacking path or snippet --")
n_l2_bad = 0
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'\[S-L2\]', ln):
        a = max(0, m.start()-100); b = min(len(ln), m.end()+100)
        seg = ln[a:b]
        has_path = bool(re.search(r'[A-Za-z0-9_\-\.]+/[A-Za-z0-9_\-\./]+', seg)) or ('`' in seg and '/' in seg)
        has_snip = bool(re.search(r'(首行|原文|声明|第\s*\d+\s*行|内嵌|='"'"'|=")', seg))
        if not (has_path and has_snip):
            n_l2_bad += 1
            P("   L%-6d [path=%d snip=%d] %s" % (i, has_path, has_snip, seg.replace('\n',' ')))
P("  [S-L2] lacking path-or-snippet context: %d" % n_l2_bad)

P("\n-- A3: [S-L4] occurrences: check dimension chain markers --")
n_l4 = 0
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'\[S-L4\]', ln):
        n_l4 += 1
        a = max(0, m.start()-100); b = min(len(ln), m.end()+110)
        seg = ln[a:b]
        has_chain = bool(re.search(r'(→|->|换算|量纲|推导|除以|乘以|×|倍|=)', seg))
        if not has_chain:
            P("   L%-6d [NO-CHAIN] %s" % (i, seg.replace('\n',' ')))
P("  [S-L4] total = %d (only no-chain ones listed above)" % n_l4)

P("\n-- A4: [S-WEB] occurrences --")
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'\[S-WEB\]', ln):
        a = max(0, m.start()-130); b = min(len(ln), m.end()+130)
        P("   L%-6d %s" % (i, ln[a:b].replace('\n',' ')))

P("\n-- A5: ALL [S-UNK] occurrences with context --")
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'\[S-UNK\]', ln):
        a = max(0, m.start()-140); b = min(len(ln), m.end()+80)
        P("   L%-6d %s" % (i, ln[a:b].replace('\n',' ')))

with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(buf))
print("part A written, lines:", len(buf))
