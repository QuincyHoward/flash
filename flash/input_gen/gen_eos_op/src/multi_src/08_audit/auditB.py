# -*- coding: utf-8 -*-
import re, os, collections, glob

BASE = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
DOC = BASE + "/src/multi_docs/MultiEOSOP格式说明.md"
OUT = BASE + "/.workbuddy/tmp/audit_BCDEF.txt"
SRC = BASE + "/src/Multi1D++Portable20241128"

with open(DOC, encoding='utf-8') as f:
    text = f.read()
LINES = text.split('\n')
buf = []
def P(*a):
    buf.append(' '.join(str(x) for x in a))

# ============ AUDIT B: path references ============
P("="*30, "AUDIT B: path references", "="*30)
print("src exists?", os.path.isdir(SRC))

# candidate relative paths: backticked tokens containing a '/' and a known extension or dir
cand = collections.OrderedDict()   # path -> list of line numbers
for i, ln in enumerate(LINES, 1):
    for m in re.finditer(r'`([^`]{2,160})`', ln):
        tok = m.group(1).strip()
        if '/' not in tok and '\\' not in tok:
            continue
        if re.search(r'\s', tok) and not tok.endswith(('.dat','.txt','.md','.pdf','.f')):
            # allow spaces in filenames like "Hyades 数据格式说明.txt"? keep if has extension
            if not re.search(r'\.(dat|txt|doc|docx|pdf|f|par|ist|info|readme|ini|xml|xlsx|cst|tab1|tab2|hug|cn4|cnr|feos|301|eos|NoFree|ZeFF|Zeff|mexport|critical\.dat|md|MANUAL|PLANCK|ROSSELAND|readme)$', tok, re.I):
                continue
        tok2 = tok.replace('\\', '/')
        # drop pure wildcard/glob or placeholder
        if tok2.startswith('...') or tok2.startswith('/'):
            continue
        if re.match(r'^[A-Za-z]:', tok2):
            tok2 = tok2
        cand.setdefault(tok2, []).append(i)

# normalize: figure out root
def resolve(p):
    p = p.strip()
    if p.startswith('./'):
        p = p[2:]
    roots = [SRC, BASE, SRC + "/doc", BASE + "/doc", BASE + "/src"]
    out = []
    for r in roots:
        fp = os.path.join(r, p)
        if os.path.exists(fp):
            out.append(fp)
    return out

exists_cnt = 0
missing = []
for p, lns in cand.items():
    if any(ch in p for ch in '*?<>'):
        continue
    # skip obvious non-paths (units, code)
    if p.startswith(('http', 'Mbar', 'GPa', 'MJ/', 'erg', 'g/cc', 'cm', 'eV/', 'keV', '10^', 'x/', 'n/', 'ρ/')):
        continue
    if resolve(p):
        exists_cnt += 1
    else:
        missing.append((p, lns))

P("candidate path-like tokens: %d" % len(cand))
P("exists (any root): %d" % exists_cnt)
P("missing candidates: %d" % len(missing))
P("\n-- MISSING (raw) --")
for p, lns in missing:
    P("  %s   [lines %s]" % (p, ','.join(str(x) for x in lns[:6])))

with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(buf))
print("audit B stage written; missing:", len(missing))
