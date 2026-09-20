# -*- coding: utf-8 -*-
"""Audit B v4: extract path then verify by progressively stripping CJK/space suffix."""
import re, os, collections

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
SRC = BASE + "/src/Multi1D++Portable20241128"
OUT = BASE + "/.workbuddy/tmp/auditB4.txt"

with open(DOC, encoding='utf-8') as f:
    text = f.read()
LINES = text.split('\n')

tree, dirs = set(), set()
for root, ds, fs in os.walk(SRC):
    rel = os.path.relpath(root, SRC).replace('\\','/')
    if rel != '.': dirs.add(rel)
    for fn in fs:
        tree.add((rel+'/'+fn) if rel!='.' else fn)
for c in ['docext','doc','pdfext','ionmix','src','.workbuddy']:
    d = os.path.join(BASE, c)
    if os.path.isdir(d):
        for root, ds, fs in os.walk(d):
            rel = os.path.relpath(root, BASE).replace('\\','/')
            if rel != '.': dirs.add(rel)
            for fn in fs: tree.add(rel+'/'+fn)
for d in ['.workbuddy/tmp', 'extern', 'python', 'Matlab', 'XOP']:
    fp = os.path.join(BASE, d)
    dirs.add(d)
    if os.path.isdir(fp):
        for root, ds, fs in os.walk(fp):
            rel = os.path.relpath(root, BASE).replace('\\','/')
            dirs.add(rel)
            for fn in fs: tree.add(rel+'/'+fn)
print("files:", len(tree), "dirs:", len(dirs))

ROOTS = ('matter++','doc','docext','pdfext','src','ionmix','extern','XOP','python','Matlab',
         '.workbuddy','eosop_pro','mat_','ATOMIC','Thermos','Hyades','hyades','SNOP','Ionmix',
         'FEOS','QEOS','qeos','sesame','Opacity','Crystal','XrayMassCoef','RadiativeCoolingRates',
         'HeatCapacity','PROPACEOS','ColdOpacity','Density','density','workbuddy','ionmix')

def try_resolve(t):
    """t = raw path candidate; strip trailing CJK/space/punct progressively."""
    t = t.strip().strip('`').strip()
    if t.startswith('./'): t = t[2:]
    # cut at first char that is CJK, whitespace, or full-width punct
    cut = re.search(r'[\s\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', t)
    if cut: t = t[:cut.start()]
    t = t.rstrip('/')
    if not t: return None
    return t

cand = collections.OrderedDict()
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'`([^`\n]{3,200})`', ln):
        raw = m.group(1)
        if '/' not in raw: continue
        t0 = raw
        # allow [S-Lx] prefix
        t0 = re.sub(r'^\[[^\]]*\]\s*', '', t0)
        if not any(t0.startswith(r) for r in ROOTS): continue
        t = try_resolve(t0)
        if not t: continue
        cand.setdefault(t, {'lns':[], 'raw':set()})
        cand[t]['lns'].append(i)
        cand[t]['raw'].add(raw[:60])

OK, OKTAIL, MISS, GLOB = 0, 0, [], 0
for p, d in cand.items():
    if any(ch in p for ch in '*?<>{'): 
        GLOB += 1; continue
    if p in tree or p in dirs:
        OK += 1; continue
    if [f for f in tree if f == p or f.endswith('/'+p)] or [x for x in dirs if x==p or x.endswith('/'+p)]:
        OKTAIL += 1; continue
    MISS.append((p, sorted(set(d['lns']))))

lo = ["="*30, "AUDIT B v4", "="*30,
      "distinct resolved path tokens: %d" % len(cand),
      "  exact OK: %d" % OK,
      "  tail OK: %d" % OKTAIL,
      "  GLOB/wildcard (not checked): %d" % GLOB,
      "  *** UNRESOLVED (likely NON-EXISTENT): %d ***" % len(MISS), ""]
for p, lns in MISS:
    lo.append("  %-62s %d refs   L%s" % (p, len(lns), ','.join(map(str,lns[:10]))))
open(OUT,'w',encoding='utf-8',newline='\n').write('\n'.join(lo))
print('\n'.join(lo[:10]))
