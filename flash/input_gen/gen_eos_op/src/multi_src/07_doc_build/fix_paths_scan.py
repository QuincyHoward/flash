# -*- coding: utf-8 -*-
"""Build a real file index and extract all path-like tokens from the doc,
then resolve them (exact -> tail -> dir)."""
import os, re, sys, json

ROOT = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op'
DOC = os.path.join(ROOT, 'src/multi_docs/MultiEOSOP格式说明.md')

# ---- 1. build index ----
PRIMARY = os.path.join(ROOT, 'src/Multi1D++Portable20241128')
files = set()      # relative paths, forward slashes
dirs = set()
for base in [PRIMARY, ROOT]:
    if not os.path.isdir(base):
        continue
    for dp, dns, fns in os.walk(base):
        rel = os.path.relpath(dp, ROOT).replace('\\', '/')
        dirs.add(rel)
        for fn in fns:
            r = (rel + '/' + fn) if rel != '.' else fn
            files.add(r)
            files.add(r.lower())
print('INDEX files=%d dirs=%d' % (len(files), len(dirs)))

# basename -> list of full rel paths (for tail matching)
base2paths = {}
for f in files:
    if f.lower() != f:  # keep case-sensitive originals only
        base2paths.setdefault(os.path.basename(f), []).append(f)

lines = open(DOC, encoding='utf-8', newline='').read().split('\n')
print('DOC lines=%d' % len(lines))

# ---- 2. extract backtick tokens ----
tok_re = re.compile(r'`([^`\n]{2,200})`')
path_re = re.compile(r'^[\w./\-{}\*+]+\.(?:dat|feos|cnr|hug|lbf|txt|md|pdf|doc|docx|py|f|ini|dat|cn4|ise|ist|xml|inp|op|zeff|eos|tbl|off|h5|json|csv|plt|chk|man|MANUAL|obj|o|a|so)$', re.I)
dirish_re = re.compile(r'^[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-{}\*+]+)+/?$')

tokens = {}   # token -> set(lines)
for i, ln in enumerate(lines, 1):
    for m in tok_re.finditer(ln):
        t = m.group(1).strip()
        if ('/' in t or t.count('.') >= 1) and (path_re.match(t) or dirish_re.match(t)):
            # skip obvious non-paths
            if t.startswith(('http', 'pip ', 'python', 'md5', '0x', 'utf-8', 'e.', 'i.e')):
                continue
            if re.match(r'^[A-Za-z0-9_]+$', t):
                continue
            tokens.setdefault(t, set()).add(i)

print('TOKENS=%d' % len(tokens))

def resolve(t):
    tt = t.strip()
    if tt in files or tt.lower() in files:
        return 'exact', tt
    # strip leading ./
    cands = []
    # tail match
    bn = os.path.basename(tt)
    if bn in base2paths:
        ps = base2paths[bn]
        # prefer path whose suffix matches the token suffix
        best = [p for p in ps if p.endswith(tt) or p.endswith(tt.lstrip('./'))]
        if best:
            return 'tail-exact', sorted(best)[0]
        cands = sorted(ps)
        if len(cands) == 1:
            return 'tail', cands[0]
        return 'multi', cands
    # dir match
    if tt in dirs or tt.rstrip('/') in dirs:
        return 'dir', tt
    # maybe token is a prefix-dir like matter++/mat_Al-1.0
    for d in dirs:
        if d.endswith(tt) or tt.endswith(d):
            return 'dir-tail', d
    return 'MISSING', None

results = {}
unres = []
for t in sorted(tokens):
    st, hit = resolve(t)
    results[t] = (st, hit, sorted(tokens[t]))
    if st in ('MISSING', 'multi'):
        unres.append((t, st, hit, sorted(tokens[t])))

print('\n=== UNRESOLVED (%d) ===' % len(unres))
for t, st, hit, lns in unres:
    print('[%s] %-60s lines=%s -> %s' % (st, t, lns[:10], hit))

json.dump({k: [v[0], v[1], v[2]] for k, v in results.items()},
          open(os.path.join(ROOT, '.workbuddy/tmp/paths_resolve.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
