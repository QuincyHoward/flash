# -*- coding: utf-8 -*-
import re, os, collections

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
SRC = BASE + "/src/Multi1D++Portable20241128"
OUT = BASE + "/.workbuddy/tmp/auditB2.txt"

with open(DOC, encoding='utf-8') as f:
    text = f.read()
LINES = text.split('\n')

# index all real files under SRC (relative posix)
tree = set()
dirs = set()
for root, ds, fs in os.walk(SRC):
    rel = os.path.relpath(root, SRC).replace('\\', '/')
    if rel != '.':
        dirs.add(rel)
    for fn in fs:
        tree.add((rel + '/' + fn) if rel != '.' else fn)
print("files under SRC:", len(tree), "dirs:", len(dirs))

WWW = {}
def www_all(p):
    """return any real path whose tail matches p"""
    hits = []
    for f in tree:
        if f == p or f.endswith('/' + p):
            hits.append(f)
    return hits
def www_suffix(p):
    return [f for f in tree if f.endswith(p)]

# also index docext/ and doc/ at repo root
EXTRA_ROOTS = {}
for cand in ['docext', 'doc', 'pdfext', 'ionmix', 'src']:
    d = os.path.join(BASE, cand)
    if os.path.isdir(d):
        EXTRA_ROOTS[cand] = d
        for root, ds, fs in os.walk(d):
            rel = os.path.relpath(root, BASE).replace('\\','/')
            for fn in fs:
                tree.add(rel + '/' + fn)
print("total indexed files:", len(tree))
print("extra roots:", list(EXTRA_ROOTS.keys()))

# token candidates
NOISE = re.compile(r'^[\[\(]|(^|\W)(cm3?|cm\^3|cm²|g/cc|g/cm3|g/cm\^3|J/cm3|J/g|kJ/g|J/kg|g/mol|km/s|m/s|um/ns|µm/ns|eV|keV|K|1/K|J/gK|Mbar|GPa|erg|dyne)[\]\)]?$')
def is_noise(t):
    if re.search(r'(^\d|[\d⁰-⁹])', t) and ('/' in t) and re.search(r'^[\d\s()\[\]−\-+=/·.×^⁰-⁹]+$', t):
        return True
    if t in ('g/cm3','dyne/cm2','J/cm3','km/s','um/ns','m/s','J/g','g/mol','kJ/g','µm/ns','1/K','J/gK','g/cm^3','dyne/cm²','J/cm³','J/kg'):
        return True
    if re.search(r'(split|float|rstrip|ceil|\\(t|r|n|d)|\{)/', t):
        return True
    return False

cand = collections.OrderedDict()
for i, ln in enumerate(LINES, 1):
    # include bracketed [S-Lx] prefixes so we can learn the implicit dir
    for m in re.finditer(r'\[S-L[123]\]\s*`?([A-Za-z_][^`\s]{1,150})`?', ln):
        pass
    for m in re.finditer(r'`([^`]{3,170})`', ln):
        tok = m.group(1).strip()
        if '/' not in tok:
            continue
        cand.setdefault(tok.replace('\\','/'), []).append(i)

results = {'OK':0, 'OK_TAIL':0, 'MISSING':[], 'NOISE':0}
missing_dir = []
for p, lns in cand.items():
    if is_noise(p):
        results['NOISE'] += 1
        continue
    # strip leading [S-Lx] / [S-UNK] tags
    q = re.sub(r'^\[[^\]]*\]\s*', '', p).strip()
    if not q or '/' not in q:
        results['NOISE'] += 1
        continue
    if q in dirs or q.rstrip('/') in dirs:
        results['OK'] += 1
        continue
    if q in tree:
        results['OK'] += 1
        continue
    # tail match
    tail = q.lstrip('./')
    hits = www_suffix(tail)
    if hits:
        results['OK_TAIL'] += 1
        continue
    # dir tail
    base = tail.rstrip('/').split('/')[-1]
    dhits = [d for d in dirs if d == base or d.endswith('/'+base)]
    if dhits:
        results['OK_TAIL'] += 1
        continue
    results['MISSING'].append((q, lns))

lines_out = []
def P(*a): lines_out.append(' '.join(str(x) for x in a))
P("="*30, "AUDIT B v2 (prefix/tail resolution)", "="*30)
P("candidate tokens: %d  noise filtered: %d" % (len(cand), results['NOISE']))
P("resolved OK (exact): %d   resolved OK (tail/dir match): %d" % (results['OK'], results['OK_TAIL']))
P("UNRESOLVED: %d" % len(results['MISSING']))
P("")
P("-- UNRESOLVED path-like tokens (raw, first 6 line refs each) --")
for p, lns in results['MISSING']:
    P("  %-70s [L%s]" % (p, ','.join(str(x) for x in lns[:6])))
with open(OUT,'w',encoding='utf-8',newline='\n') as f:
    f.write('\n'.join(lines_out))
print('\n'.join(lines_out[:8]))
print("unresolved:", len(results['MISSING']))
