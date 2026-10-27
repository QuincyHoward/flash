# -*- coding: utf-8 -*-
"""复核：单群/多群表头第 2 字段的全部取值分布（检验"恒为 6.0"是否成立）。"""
import os, collections

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')


def isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


vals = collections.Counter()
examples = {}
kindcnt = collections.Counter()
for dp, _, fn in os.walk(M):
    for f in fn:
        p = os.path.join(dp, f)
        try:
            raw = open(p, 'rb').read(4000).replace(b'\r\n', b'\n')
        except OSError:
            continue
        L = [x.decode('latin-1') for x in raw.split(b'\n') if x.strip()]
        if not L or len(L[0]) != 60:
            continue
        fld = [L[0][j:j + 15].strip() for j in range(0, 60, 15)]
        if not (isnum(fld[2]) and isnum(fld[3])):
            continue
        try:
            NR, NT = int(float(fld[2])), int(float(fld[3]))
        except ValueError:
            continue
        if not (2 <= NR <= 500 and 2 <= NT <= 500):
            continue
        rel = os.path.relpath(p, M)
        if isnum(fld[1]):
            k = 'NUM:' + fld[1]
        else:
            k = 'TXT:' + fld[1]
        vals[k] += 1
        kindcnt[k.split(':')[0]] += 1
        examples.setdefault(k, []).append(rel)

print('=== 表头第 2 字段的全部取值（按出现次数） ===')
for k, v in vals.most_common(40):
    print('  %-22s %4d   e.g. %s' % (k, v, examples[k][0]))
print()
print('数值型 vs 文本型: ', dict(kindcnt))
print()
print('=== 数值型第 2 字段的取值集合（去重） ===')
numset = sorted({k.split(':', 1)[1] for k in vals if k.startswith('NUM:')},
                key=lambda x: float(x))
print('  ', numset)
print()
print('=== 每种数值型取值的文件举例 ===')
for nv in numset:
    lst = examples['NUM:' + nv]
    print('  %-14s (%d)  %s' % (nv, len(lst), '; '.join(lst[:3])))
