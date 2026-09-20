# -*- coding: utf-8 -*-
"""对 C:\\Users\\Administrator\\.workbuddy\\tmp 做相关性分类盘点。"""
import os, json, re

D = r'C:\Users\Administrator\.workbuddy\tmp'
OUT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\.workbuddy\tmp\inv_classified.txt'

# 与 MultiEOSOP格式说明.md 直接相关的关键词
KW = [
    'multi', 'eosop', 'sesame', 'feos', 'mpqeos', 'hyades', 'ionmix', 'cn4', 'cnr',
    'ledcop', 'atomic', 'tops', 'snop', 'thermos', 'opacity', 'opac', 'planck',
    'rosseland', 'ross', 'zeff', 'mexport', 'cst', 'coldopacity', 'hug',
    'noext', 'bare', 'multigroup', 'probe', 'cst_naming', 'cross_val', 'xval',
    'material', 'matter', 'base', 'user', 'modinfo', 'checksum', 'arbitration',
    'audit', 'anchor', 'candidate', 'dot', 'iff_', 'cold', 'feeos', 'kev',
    'src_doc', 'formats', 'explore', 'doc_conventions', 'deliverables',
    'web_verify', 'missed', 'sample_index', 'plan_multi', 'ionmix', 'snb',
]

lines = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    lines.append(s)

rows = []
for root, dirs, files in os.walk(D):
    rel = os.path.relpath(root, D)
    for f in files:
        p = os.path.join(root, f)
        try:
            sz = os.path.getsize(p)
        except OSError:
            sz = -1
        rp = os.path.normpath(os.path.join(rel, f)) if rel != '.' else f
        rows.append((rp, sz))

rows.sort()

P('TOTAL FILES:', len(rows))
P()

# 分类
def classify(rp, sz):
    low = rp.lower()
    base = os.path.basename(low)
    ext = os.path.splitext(low)[1]
    # 子目录名优先
    parts = rp.replace('\\', '/').split('/')
    sub = parts[0] if len(parts) > 1 else ''
    if sub == 'multi_doc_parts':
        return 'A_doc_parts'
    if sub == 'probe_noext':
        return 'B_probe_noext'
    if sub == 'docext' or sub == 'pdfext':
        return 'C_doc_extract'
    if sub == 'legacy':
        return 'D_legacy'
    if sub in ('ne_smoke', 'fit_check_r15', 'vendor'):
        return 'E_unrelated_' + sub
    # 关键字命中
    for k in KW:
        if k in low:
            return 'F_kw_' + k
    return 'Z_other'

from collections import defaultdict
buckets = defaultdict(list)
for rp, sz in rows:
    buckets[classify(rp, sz)].append((rp, sz))

for k in sorted(buckets, key=lambda x: (x[0], x)):
    lst = buckets[k]
    tot = sum(s for _, s in lst)
    P('### %s  (%d files, %d bytes)' % (k, len(lst), tot))
    for rp, sz in lst[:400]:
        P('   %-64s %10d' % (rp, sz))
    P()

open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('written', OUT, len('\n'.join(lines)))

# 摘要打印
print()
print('=== BUCKET SUMMARY ===')
for k in sorted(buckets):
    lst = buckets[k]
    print('%-28s %4d files  %12d B' % (k, len(lst), sum(s for _, s in lst)))
