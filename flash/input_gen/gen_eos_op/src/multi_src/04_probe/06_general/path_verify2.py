# -*- coding: utf-8 -*-
"""Refined path validator: only counts tokens that are REAL file-path-looking
tokens (contain a slash AND a known data-file extension or a known dir prefix),
excluding units, variable lists, wildcards, and tmp artifacts."""
import os, re

ROOT = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op'
DOC = os.path.join(ROOT, 'src/multi_docs/MultiEOSOP格式说明.md')
PRIMARY = os.path.join(ROOT, 'src/Multi1D++Portable20241128')

files = set()
dirs = set()
for base in [PRIMARY, ROOT]:
    for dp, dns, fns in os.walk(base):
        rel = os.path.relpath(dp, ROOT).replace('\\', '/')
        dirs.add(rel.lower())
        for fn in fns:
            r = (rel + '/' + fn) if rel != '.' else fn
            files.add(r); files.add(r.lower())
base2 = {}
for f in files:
    if f.lower() != f:
        base2.setdefault(f.split('/')[-1].lower(), []).append(f)

lines = open(DOC, encoding='utf-8', newline='').read().split('\n')

# unit-like tokens to exclude
UNITS = {'J/cm3','J/g','J/kg','J/gK','MJ/kg','cm/s','km/s','m/s','um/ns','cm2/g','cm3/g',
         'erg/g','erg/cm3','dyne/cm2','g/cc','g/cm3','g/cm**3','g/mol','1/K','eV/cm2/g',
         'min/max','seen/expected','J/cm³','Mbar·cm³/g'}
# negation context markers
NEG = ['不存在', '并不存在', '误写', '错误拼接', '原写', '把', '系把', '更正', '不得写']

tok_re = re.compile(r'`([^`\n]{3,120})`')
real = {}
for i, ln in enumerate(lines, 1):
    for m in tok_re.finditer(ln):
        t = m.group(1).strip()
        if t in UNITS or '*' in t or '{' in t:
            continue
        if '/' not in t:
            continue
        low = t.lower()
        if not re.search(r'\.(dat|dat\.feos|dat\.par|feos|cnr|cn4|hug|lbf|txt|md|pdf|doc|docx|f|py|ini|ist|ise|isc|cst|mexport|xlsx|xml|zeff|opj|inp|par|tab|data|NoFree|AvSqFree)$', low) and \
           not re.match(r'^(matter\+\+|doc|docext|pdfext|ionmix|eosop_pro|src|\.workbuddy)(/|$)', low):
            continue
        # negation context
        ctx = ln[max(0, m.start()-30):m.end()+10]
        if any(n in ctx for n in NEG):
            real.setdefault(t, ('NEGATED-OK', set()))[1].add(i)
            continue
        hit = None
        if t in files or low in files:
            hit = 'exact'
        elif low.split('/')[-1] in base2 and len(base2[low.split('/')[-1]]) == 1:
            hit = 'tail: ' + base2[low.split('/')[-1]][0]
        real.setdefault(t, [hit, set()])[1].add(i)

bad = {k: v for k, v in real.items() if v[0] is None}
neg = {k: v for k, v in real.items() if v[0] == 'NEGATED-OK'}
print('REAL path tokens checked:', len(real))
print('  resolved     :', len(real) - len(bad) - len(neg))
print('  negated/quote:', len(neg))
print('  UNRESOLVED   :', len(bad))
print()
for k, v in sorted(bad.items()):
    print('  MISSING %-55s lines=%s' % (k, sorted(v[1])))
