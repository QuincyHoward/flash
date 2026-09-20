# -*- coding: utf-8 -*-
"""精确统计：在"公式闭合"的 404 个归属文件中，数值型表头第 2 字段的取值分布。"""
import os, collections

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++')


def isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


dist = collections.Counter()
ex = {}
txtdist = collections.Counter()
for dp, _, fn in os.walk(M):
    for f in fn:
        p = os.path.join(dp, f)
        try:
            raw = open(p, 'rb').read().replace(b'\r\n', b'\n')
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
        D = -(-(NR + NT + NR * NT) // 4)
        n30 = sum(1 for l in L if len(l) == 30)
        n = len(L)
        ok_single = (n30 == 0 and n == 1 + D)
        ok_multi = (n30 > 0 and n == n30 * (2 + D))
        if not (ok_single or ok_multi):
            continue
        rel = os.path.relpath(p, M)
        if isnum(fld[1]):
            k = fld[1]
            dist[k] += 1
            ex.setdefault(k, []).append(rel)
        else:
            txtdist[fld[1]] += 1

print('闭合归属文件中：文本型 kind 分布')
for k, v in txtdist.most_common():
    print('   %-16s %3d' % (k, v))
print()
print('闭合归属文件中：数值型第 2 字段取值分布（共 %d 个数值型文件）' % sum(dist.values()))
for k, v in dist.most_common():
    print('   %-18s %3d   e.g. %s' % (k, v, ex[k][0]))
print()
print('数值型取值种类数 =', len(dist))
