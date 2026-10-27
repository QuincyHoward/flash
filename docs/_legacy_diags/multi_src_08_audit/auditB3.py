# -*- coding: utf-8 -*-
"""Audit B strict: only tokens that LOOK like relative file paths."""
import re, os, collections

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
SRC = BASE + "/src/Multi1D++Portable20241128"
OUT = BASE + "/.workbuddy/tmp/auditB3.txt"

with open(DOC, encoding='utf-8') as f:
    text = f.read()
LINES = text.split('\n')

tree, dirs = set(), set()
for root, ds, fs in os.walk(SRC):
    rel = os.path.relpath(root, SRC).replace('\\','/')
    if rel != '.': dirs.add(rel)
    for fn in fs:
        tree.add((rel+'/'+fn) if rel!='.' else fn)
for cand in ['docext','doc','pdfext','ionmix','src','.workbuddy']:
    d = os.path.join(BASE, cand)
    if os.path.isdir(d):
        for root, ds, fs in os.walk(d):
            rel = os.path.relpath(root, BASE).replace('\\','/')
            if rel != '.': dirs.add(rel)
            for fn in fs: tree.add(rel+'/'+fn)
print("indexed files:", len(tree), "dirs:", len(dirs))

# STRICT pattern: token must contain a '/', start with a path-ish word,
# and have an extension OR end with '/'
PATH_ROOT = re.compile(
    r'^(?:\.?\.?/)?'
    r'(?:matter\+\+|doc|docext|pdfext|src|ionmix|extern|XOP|Matlab|python|tools|scripts|\.workbuddy|'
    r'eosop_pro|src_doc_core|multi_docs|ColdOpacity|ATOMIC|Thermos|Hyades|hyades|SNOP|Ionmix|'
    r'mat_[A-Za-z0-9_\-]+|FEOS|QEOS|qeos|sesame|Opacity|Crystal|XrayMassCoef|RadiativeCoolingRates|'
    r'HeatCapacity|PROPACEOS|Density|density)'
    r'(?:/[^`\s]*)*/?$'
)
# exclude tokens with CJK explanatory text stuck on, spaces, punctuation sentences
def looks_like_path(tok):
    t = re.sub(r'^\[[^\]]*\]\s*', '', tok).strip()
    if ' ' in t or '\t' in t: return None
    if re.search(r'[\u4e00-\u9fff，。；：（）"“”]', t): return None
    if t.endswith(('。','，','、','；','：','）','）',')','|')): return None
    if not PATH_ROOT.match(t): return None
    return t

cand = collections.OrderedDict()
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'`([^`]{3,200})`', ln):
        r = looks_like_path(m.group(1))
        if r: cand.setdefault(r, []).append(i)
    # also catch markdown links / bare paths in text
    for m in re.finditer(r'(?<![\w`/])((?:matter\+\+|doc|docext|pdfext|ionmix|hyades|sesame|qeos|ATOMIC|Thermos|Ionmix|mat_[A-Za-z0-9_\-]+)/[A-Za-z0-9_\-./]+)', ln):
        r = looks_like_path(m.group(1))
        if r: cand.setdefault(r, []).append(i)

OK, OKTAIL, MISS = 0, 0, []
for p, lns in cand.items():
    q = p.lstrip('./')
    if q in tree or q in dirs or q.rstrip('/') in dirs or q in ('matter++',):
        OK += 1; continue
    if [f for f in tree if f.endswith('/'+q)] or [d for d in dirs if d==q or d.endswith('/'+q)]:
        OKTAIL += 1; continue
    MISS.append((q, sorted(set(lns))))

lo = ["="*30, "AUDIT B v3 (STRICT)", "="*30,
      "distinct path-like tokens: %d" % len(cand),
      "resolved exact: %d ; resolved tail: %d ; UNRESOLVED: %d" % (OK, OKTAIL, len(MISS)),
      "", "-- UNRESOLVED PATH-LIKE TOKENS --"]
for p, lns in MISS:
    lo.append("  %-68s %d hits  L%s" % (p, len(lns), ','.join(map(str,lns[:8]))))
open(OUT,'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo[:6]))
print("MISS:", len(MISS))
