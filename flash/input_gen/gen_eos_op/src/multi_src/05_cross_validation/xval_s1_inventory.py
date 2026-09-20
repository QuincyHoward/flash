# -*- coding: utf-8 -*-
"""Stage 1: material -> format-family coverage map for matter++/"""
import os, sys, re, io, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MATTER = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')
OUT_TXT = os.path.join(os.path.dirname(__file__), 'xval_s1_inventory.txt')

print("cwd resolution: __file__ =", __file__)
print("ROOT  =", ROOT)
print("MATTER=", MATTER)
print("MATTER exists:", os.path.isdir(MATTER))
if not os.path.isdir(MATTER):
    # try alternate walk-up
    p = os.path.dirname(__file__)
    for _ in range(6):
        cand = os.path.join(p, 'src', 'Multi1D++Portable20241128', 'matter++')
        if os.path.isdir(cand):
            MATTER = cand; ROOT = p
            print("FOUND alt MATTER =", MATTER)
            break
        p = os.path.dirname(p)
print("USING MATTER =", MATTER)

# family definitions: (family name, predicate on lowercase basename)
# order matters only for reporting
FAMILIES = [
    ('sesame',        lambda b: b == 'sesame' or (b.endswith('.sesame') and '_planck' not in b and '_rosseland' not in b and not re.search(r'\.sesame_', b))),
    ('sesame_PLANCK', lambda b: b.endswith('.sesame_planck')),
    ('sesame_ROSSELAND', lambda b: b.endswith('.sesame_rosseland') or b.endswith('.sesame_ross')),
    ('feos',          lambda b: b.endswith('.feos')),
    ('301',           lambda b: b.endswith('.301')),
    ('304',           lambda b: b.endswith('.304')),
    ('305',           lambda b: b.endswith('.305')),
    ('mexport',       lambda b: b.endswith('.mexport')),
    ('cst',           lambda b: b.endswith('.cst')),
    ('hyades',        lambda b: b.endswith('.hyades')),
    ('PLANCK',        lambda b: b.endswith('.planck')),
    ('ROSS',          lambda b: b.endswith('.ross') or b.endswith('.rosseland')),
    ('EPS',           lambda b: b.endswith('.eps')),
    ('ZEFF',          lambda b: b.endswith('.zeff')),
    ('MGOP_PLANCK',   lambda b: b.endswith('.multigroupopacity_planck')),
    ('MGOP_ROSS',     lambda b: b.endswith('.multigroupopacity_rosseland')),
    ('GRAY_PLANCK',   lambda b: b.endswith('.grayopacity_planck')),
    ('GRAY_ROSS',     lambda b: b.endswith('.grayopacity_rosseland')),
    ('cn4',           lambda b: b.endswith('.cn4')),
    ('cnr',           lambda b: b.endswith('.cnr')),
    ('eos_bare',      lambda b: b.endswith('_eos') or b.endswith('_eos_e') or b.endswith('_eos_i')),
    ('ieos_bare',     lambda b: b.endswith('_ieos')),
    ('EOS_up',        lambda b: b.endswith('_EOS')),
    ('opp',           lambda b: b.endswith('_opp') or b.endswith('.opp')),
    ('opr',           lambda b: b.endswith('_opr') or b.endswith('.opr')),
    ('mop',           lambda b: '_mop' in b),
    ('op03',          lambda b: '_op03' in b),
    ('bare_PLANCK',   lambda b: 'planck' in b and not b.endswith('.planck') and not b.endswith('.sesame_planck') and not b.endswith('.multigroupopacity_planck') and not b.endswith('.grayopacity_planck')),
    ('bare_ROSSELAND',lambda b: ('ross' in b) and not b.endswith('.ross') and not b.endswith('.rosseland') and not b.endswith('.sesame_rosseland') and not b.endswith('.multigroupopacity_rosseland') and not b.endswith('.grayopacity_rosseland')),
]

def classify(b):
    bl = b.lower()
    hits = []
    for name, pred in FAMILIES:
        try:
            if pred(bl):
                hits.append(name)
        except Exception:
            pass
    return hits

# walk
mats = {}
allfiles = []
for dirpath, dirnames, filenames in os.walk(MATTER):
    rel = os.path.relpath(dirpath, MATTER)
    rel = '' if rel == '.' else rel
    files = [f for f in filenames if os.path.isfile(os.path.join(dirpath, f))]
    if not files:
        continue
    allfiles.extend([os.path.join(rel, f) if rel else f for f in files])
    fam = set()
    keep = []
    for f in files:
        h = classify(f)
        if h:
            fam.update(h)
            keep.append((f, ','.join(h)))
    if fam or rel:
        mats[rel] = {'families': sorted(fam), 'files': sorted(keep), 'nfiles': len(files)}

lines = []
def P(s=''):
    print(s)
    lines.append(s)

P("=" * 100)
P("Stage 1 inventory : material -> format-family coverage")
P("MATTER ROOT = " + MATTER)
P("total files walked = %d ; total dirs with files = %d" % (len(allfiles), len(mats)))
P("=" * 100)

withfam = {k: v for k, v in mats.items() if v['families']}
ranked = sorted(withfam.items(), key=lambda kv: (-len(kv[1]['families']), kv[0]))

P("")
P("### TOP 25 by number of distinct families")
P("")
P("%-38s %4s  %s" % ("material dir", "#fam", "families"))
P("-" * 100)
for k, v in ranked[:25]:
    P("%-38s %4d  %s" % (k[:38], len(v['families']), ','.join(v['families'])))

P("")
P("### ALL material dirs with family hits")
P("")
for k, v in ranked:
    P("[%s]  (%d distinct: %s)" % (k, len(v['families']), ','.join(v['families'])))
    for f, h in v['files']:
        P("        %-58s -> %s" % (f, h))

P("")
P("### dirs WITHOUT any classified file (context)")
for k in sorted(mats):
    if not mats[k]['families']:
        P("  %-50s nfiles=%d  sample=%s" % (k, mats[k]['nfiles'], [f for f,_ in mats[k]['files'][:0]] or []))

with io.open(OUT_TXT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')

# also dump raw suffix histogram for unclassified files
from collections import Counter
c = Counter()
for path in allfiles:
    b = os.path.basename(path)
    if not classify(b):
        ext = os.path.splitext(b)[1].lower() or '(noext)'
        c[ext] += 1
P("")
P("### suffix histogram of UNCLASSIFIED files (top 40)")
for ext, n in c.most_common(40):
    P("  %-20s %d" % (ext, n))

with io.open(OUT_TXT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(lines) + '\n')
print("\nWROTE:", OUT_TXT, os.path.getsize(OUT_TXT), "bytes")
