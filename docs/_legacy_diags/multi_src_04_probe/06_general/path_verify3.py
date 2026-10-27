# -*- coding: utf-8 -*-
"""Correct path validator: document paths are written relative to
src/Multi1D++Portable20241128/ (matter++/... , doc/...), so try that prefix too."""
import os, re

ROOT = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op'
DOC = os.path.join(ROOT, 'src/multi_docs/MultiEOSOP格式说明.md')
PRIMARY = 'src/Multi1D++Portable20241128'
BASES = [PRIMARY + '/', '', PRIMARY + '/matter++/']
# prefix candidates applied when a token does not resolve as-is
PREFIXES = ['', PRIMARY + '/', PRIMARY + '/matter++/', 'matter++/']

files = set(); dirs = set()
for base in [os.path.join(ROOT, PRIMARY), ROOT]:
    for dp, dns, fns in os.walk(base):
        rel = os.path.relpath(dp, ROOT).replace('\\', '/')
        dirs.add(rel.lower())
        for fn in fns:
            r = (rel + '/' + fn) if rel != '.' else fn
            files.add(r); files.add(r.lower())

def resolve(t):
    low = t.lower().rstrip('/')
    for p in PREFIXES:
        c = (p + low).lower()
        if c in files or c in dirs:
            return True
    return False

lines = open(DOC, encoding='utf-8', newline='').read().split('\n')
UNITS = {'J/cm3','J/g','J/kg','J/gK','MJ/kg','cm/s','km/s','m/s','um/ns','cm2/g','cm3/g',
         'erg/g','erg/cm3','dyne/cm2','g/cc','g/cm3','g/cm**3','g/mol','1/K','eV/cm2/g',
         'min/max','seen/expected'}
NEG = ['不存在','并不存在','误写','错误拼接','原写','更正','不得写','非 ','不是']
tok_re = re.compile(r'`([^`\n]{3,120})`')
bad = {}
for i, ln in enumerate(lines, 1):
    for m in tok_re.finditer(ln):
        t = m.group(1).strip()
        if t in UNITS or '*' in t or '{' in t or '/' not in t:
            continue
        low = t.lower()
        if not re.search(r'\.(dat|feos|cnr|cn4|hug|lbf|txt|md|pdf|doc|docx|f|py|ini|ist|ise|isc|cst|mexport|xlsx|xml|zeff|opj|inp|par|data|tbl|docs?)$', low) and \
           not re.match(r'^(matter\+\+|doc|docext|pdfext|ionmix|eosop_pro|src|\.workbuddy)(/|$)', low):
            continue
        # strip trailing section/quote decorations
        t2 = re.split(r'[ §\"\']', t)[0]
        ctx = ln[max(0, m.start()-30):m.end()+10]
        negated = any(n in ctx for n in NEG)
        ok = resolve(t2) or resolve(t)
        if not ok and not negated:
            bad.setdefault(t2, set()).add(i)
        elif not ok and negated:
            pass

print('UNRESOLVED (excluding negation quotes):', len(bad))
for k, v in sorted(bad.items()):
    print('  %-58s lines=%s' % (k, sorted(v)[:12]))
